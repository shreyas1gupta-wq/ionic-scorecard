"""Main cycle runner: weekly futures covered-call/covered-put/collar, 2021-05..2026-06.
Writes CYCLES_RAW.csv (one row per cycle x structure x delta x exit-rule) + a run log.
Pre-registered in PRE_REGISTRATION.md. Run in background: heavy (261 option-expiry file loads).
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import engine as E  # noqa: E402
import chain  # noqa: E402

LOG = HERE / "run_log.txt"


def log(msg: str):
    line = f"[{dt.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    t0 = time.time()
    log("loading nifty_1min raw (full)...")
    df1m = pd.read_parquet(E.NIFTY_1MIN)
    df1m = df1m[df1m.index.time >= dt.time(9, 15)]
    daily = df1m.groupby(df1m.index.date)["close"].last()
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()
    log(f"daily closes: {len(daily)} days {daily.index[0].date()}..{daily.index[-1].date()}")

    trading_days = [d.date() for d in daily.index]

    def next_trading_day(after: dt.date):
        for d in trading_days:
            if d > after:
                return d
        return None

    # precompute ONCE: first close at/after 09:20 per calendar day (avoids rebuilding a
    # 1M-row boolean time-mask on every call -- that repeated allocation is what OOM'd the
    # first attempt of this run)
    _time_arr = df1m.index.time
    _date_arr = df1m.index.date
    _mask920 = _time_arr >= dt.time(9, 20)
    _snap920 = (pd.Series(df1m["close"].values[_mask920], index=_date_arr[_mask920])
                .groupby(level=0).first())

    def spot_at(day: dt.date, after_time=dt.time(9, 20)):
        assert after_time == dt.time(9, 20), "only the precomputed 09:20 snapshot is supported"
        val = _snap920.get(day)
        return float(val) if val is not None else None

    mapping, exps = chain.build_expiry_index()
    exps = [e for e in exps if e <= trading_days[-1]]
    if len(sys.argv) > 1:
        exps = exps[: int(sys.argv[1])]
    log(f"{len(exps)} expiries usable within nifty_1min coverage, {exps[0]}..{exps[-1]}")

    import csv
    import gc

    fieldnames = ["entry_day", "expiry", "structure", "delta", "exit_rule", "is_build",
                  "bullish_signal", "spot_entry", "spot_expiry", "sigma", "net_pnl",
                  "gross_pnl", "margin", "ret_net", "ret_gross", "note"]
    csv_f = open(HERE / "CYCLES_RAW.csv", "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_f, fieldnames=fieldnames)
    writer.writeheader()

    n_rows = 0
    skips = []
    n_cycles = 0
    for i in range(len(exps) - 1):
        prev_exp, exp = exps[i], exps[i + 1]
        entry_day = next_trading_day(prev_exp)
        if entry_day is None or entry_day >= exp:
            skips.append((prev_exp, exp, "no entry day"))
            continue
        try:
            df_exp = chain.load_expiry(exp)
        except Exception as ex:
            skips.append((prev_exp, exp, f"load fail {ex}"))
            continue

        snap = E.snapshot_prices(df_exp, entry_day)
        if snap is None:
            skips.append((entry_day, exp, "no entry snapshot"))
            continue
        spot_entry = spot_at(entry_day)
        if spot_entry is None:
            skips.append((entry_day, exp, "no spot at entry"))
            continue
        spot_expiry = E.spot_close_on(daily, exp)
        if spot_expiry is None:
            skips.append((entry_day, exp, "no spot at expiry"))
            continue

        T = max((exp - entry_day).days / 365.0, 1 / 365.0)
        sigma = E.trailing_ann_vol(daily, entry_day)
        sma20 = E.sma(daily, entry_day)
        if not np.isfinite(sigma) or sigma <= 0 or not np.isfinite(sma20):
            skips.append((entry_day, exp, "no vol/sma history yet"))
            continue

        is_build = exp <= E.BUILD_END
        bullish = spot_entry > sma20

        # trading days strictly between entry_day and exp (for 50%-buyback + expiry-1 check)
        mid_days = [d for d in trading_days if entry_day < d < exp]
        expiry_minus_1 = mid_days[-1] if mid_days else entry_day

        def leg_hold_to_expiry(K, entry_px, opt_type, is_short):
            intrinsic = max(spot_expiry - K, 0) if opt_type == "CE" else max(K - spot_expiry, 0)
            if is_short:
                gross = entry_px * E.LOT - intrinsic * E.LOT
                entry_cost = E.option_leg_cost(entry_px, E.LOT, "sell_open", "order")
            else:
                gross = intrinsic * E.LOT - entry_px * E.LOT
                entry_cost = E.option_leg_cost(entry_px, E.LOT, "buy_open", "order")
            exit_cost = E.option_leg_cost(intrinsic, E.LOT, "na", "exercise") if intrinsic > 0 else 0.0
            return gross, entry_cost + exit_cost, "expiry"

        def leg_buyback(K, entry_px, opt_type):
            """Short leg only: 50%-of-credit buyback, else expiry-1 ITM avoid-exercise, else expiry."""
            for d in mid_days:
                px = E.eod_close(df_exp, d, K, opt_type)
                if px is None:
                    continue
                if px <= 0.5 * entry_px:
                    gross = (entry_px - px) * E.LOT
                    cost = (E.option_leg_cost(entry_px, E.LOT, "sell_open", "order")
                            + E.option_leg_cost(px, E.LOT, "buy_close", "order"))
                    return gross, cost, f"buyback@{d}"
            # not triggered: expiry-1 ITM check
            itm_e1 = (spot_at(expiry_minus_1) or spot_expiry)
            itm = (itm_e1 > K) if opt_type == "CE" else (itm_e1 < K)
            if itm and expiry_minus_1 != entry_day:
                px = E.eod_close(df_exp, expiry_minus_1, K, opt_type)
                if px is not None:
                    gross = (entry_px - px) * E.LOT
                    cost = (E.option_leg_cost(entry_px, E.LOT, "sell_open", "order")
                            + E.option_leg_cost(px, E.LOT, "buy_close", "order"))
                    return gross, cost, "expiry-1_avoid_exercise"
            return leg_hold_to_expiry(K, entry_px, opt_type, True)

        fut_cost = E.futures_cost_pts(entry_day) * E.LOT
        pnl_fut_long = (spot_expiry - spot_entry) * E.LOT - fut_cost
        pnl_fut_short = (spot_entry - spot_expiry) * E.LOT - fut_cost

        for d_target in E.DELTAS:
            ce = E.pick_strike(snap, "CE", spot_entry, T, sigma, d_target)
            pe = E.pick_strike(snap, "PE", spot_entry, T, sigma, d_target)
            if ce is None or pe is None:
                skips.append((entry_day, exp, f"no strike @ delta {d_target}"))
                continue
            tail_pe = E.pick_strike(snap, "PE", spot_entry, T, sigma, E.TAIL_PUT_DELTA)
            tail_ce = E.pick_strike(snap, "CE", spot_entry, T, sigma, E.TAIL_PUT_DELTA)

            for exit_rule in ("expiry", "buyback50"):
                if exit_rule == "expiry":
                    ce_gross, ce_cost, ce_note = leg_hold_to_expiry(ce["K"], ce["px"], "CE", True)
                    pe_gross, pe_cost, pe_note = leg_hold_to_expiry(pe["K"], pe["px"], "PE", True)
                else:
                    ce_gross, ce_cost, ce_note = leg_buyback(ce["K"], ce["px"], "CE")
                    pe_gross, pe_cost, pe_note = leg_buyback(pe["K"], pe["px"], "PE")

                tail_pe_gross = tail_pe_cost = tail_ce_gross = tail_ce_cost = 0.0
                if tail_pe is not None:
                    tail_pe_gross, tail_pe_cost, _ = leg_hold_to_expiry(
                        tail_pe["K"], tail_pe["px"], "PE", False)
                if tail_ce is not None:
                    tail_ce_gross, tail_ce_cost, _ = leg_hold_to_expiry(
                        tail_ce["K"], tail_ce["px"], "CE", False)

                margin_naked = 0.10 * spot_entry * E.LOT
                margin_hedged = 0.05 * spot_entry * E.LOT

                # explicit leg composition per structure: (net_pnl, gross_pnl, margin, note)
                structures = {
                    "naked_cc": (
                        pnl_fut_long + ce_gross - ce_cost,
                        pnl_fut_long + fut_cost + ce_gross,
                        margin_naked, ce_note),
                    "naked_cp": (
                        pnl_fut_short + pe_gross - pe_cost,
                        pnl_fut_short + fut_cost + pe_gross,
                        margin_naked, pe_note),
                }
                if tail_pe is not None:
                    structures["collar"] = (
                        pnl_fut_long + ce_gross - ce_cost + tail_pe_gross - tail_pe_cost,
                        pnl_fut_long + fut_cost + ce_gross + tail_pe_gross,
                        margin_hedged, ce_note)
                if tail_ce is not None:
                    structures["collar_mirror"] = (
                        pnl_fut_short + pe_gross - pe_cost + tail_ce_gross - tail_ce_cost,
                        pnl_fut_short + fut_cost + pe_gross + tail_ce_gross,
                        margin_hedged, pe_note)

                for sname, (net_pnl, gross_pnl, margin, note) in structures.items():
                    rows.append(dict(
                        entry_day=entry_day, expiry=exp, structure=sname, delta=d_target,
                        exit_rule=exit_rule, is_build=is_build, bullish_signal=bullish,
                        spot_entry=spot_entry, spot_expiry=spot_expiry, sigma=sigma,
                        net_pnl=net_pnl, gross_pnl=gross_pnl, margin=margin,
                        ret_net=net_pnl / margin, ret_gross=gross_pnl / margin,
                        note=note,
                    ))
        n_cycles += 1
        # each expiry file decompresses to a large pandas frame (multi-day x ~100+ strikes,
        # several string cols) and is used exactly ONCE in this loop -- lru_cache offers no
        # reuse benefit here and its default maxsize=64 was accumulating enough resident
        # dataframes to crash the process (observed SIGSEGV at ~50 cycles). Clear every cycle.
        chain.load_expiry.cache_clear()
        if n_cycles % 25 == 0:
            log(f"...{n_cycles} cycles done ({time.time()-t0:.0f}s elapsed)")

    log(f"DONE cycles={n_cycles} skips={len(skips)} rows={len(rows)} ({time.time()-t0:.0f}s)")
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "CYCLES_RAW.csv", index=False)
    pd.DataFrame(skips, columns=["a", "b", "reason"]).to_csv(HERE / "SKIPS.csv", index=False)
    log(f"wrote {HERE / 'CYCLES_RAW.csv'} ({len(out)} rows)")


if __name__ == "__main__":
    main()
