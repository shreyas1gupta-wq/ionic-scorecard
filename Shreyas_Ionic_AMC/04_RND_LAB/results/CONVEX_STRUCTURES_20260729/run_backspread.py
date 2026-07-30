"""STRUCTURE A: 1x2 ratio backspread (sell 1 near/ATM strike, buy 2 further strikes).
Net long optionality by construction (2 long > 1 short lot-units) -> satisfies the
net-hedge-positive count discipline by design, unlike a naive credit-selling backspread.

Unconditional weekly cadence + signal-gated (sweep_priorday_reclaim, sweep_intraday_continue).
Exit: fixed schedule (N trading days before near expiry) at 15:15 close, OR hold-to-expiry
cash-settled at intrinsic from the underlying (landmine #9 -- never read an expiry-day
option settle price).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import lib_convex as lc  # noqa: E402
from signals_convex import daily_first_signals  # noqa: E402

OUT = Path(__file__).parent
START = dt.date(2021, 5, 24)
FORWARD_START = dt.date(2026, 1, 1)
END = dt.date(2026, 6, 3)

ENTRY_MIN_DTE, ENTRY_MAX_DTE = 4, 7   # window in which a new near-expiry becomes tradeable
EXIT_DAYS_BEFORE_EXPIRY = 1


def trading_calendar() -> list[dt.date]:
    idx = lc.spot_index()
    return sorted({d for d in idx.index.date})


TCAL = trading_calendar()
TCAL_POS = {d: i for i, d in enumerate(TCAL)}


def exit_day_before(expiry: dt.date, n: int) -> dt.date | None:
    if expiry not in TCAL_POS:
        # expiry may fall on a day with no spot bars (shouldn't happen) -- fallback: nearest <= expiry
        cands = [d for d in TCAL if d <= expiry]
        if not cands:
            return None
        i = TCAL_POS.get(cands[-1])
    else:
        i = TCAL_POS[expiry]
    j = i - n
    return TCAL[j] if j >= 0 else None


def entry_cycles(min_dte=ENTRY_MIN_DTE, max_dte=ENTRY_MAX_DTE) -> list[tuple[dt.date, dt.date]]:
    """One (entry_window_start_day, near_expiry) per expiry cycle: the first trading day
    on which that expiry is 'nearest' with DTE in [min_dte, max_dte]."""
    out = []
    seen = set()
    for d in TCAL:
        if d < START or d > END:
            continue
        exp = lc.near_weekly(d, min_dte, max_dte)
        if exp is None or exp in seen:
            continue
        out.append((d, exp))
        seen.add(exp)
    return out


def build_legs(otype: str, atm_k: int, width: int, near_exp: dt.date) -> list[lc.Leg]:
    if otype == "CE":
        long_k = atm_k + width * lc.STEP
    else:
        long_k = atm_k - width * lc.STEP
    return [
        lc.Leg(near_exp, otype, side=-1, qty_ratio=1, strike=atm_k),
        lc.Leg(near_exp, otype, side=+1, qty_ratio=2, strike=long_k),
    ]


def try_enter(day: dt.date, t0: pd.Timestamp, near_exp: dt.date, otype: str, width: int):
    spot_at = lc.spot_close_asof(t0)
    if spot_at is None:
        return None
    atm_k = lc.atm_strike(spot_at)
    legs = build_legs(otype, atm_k, width, near_exp)
    frames = [lc.leg_frame(leg.expiry, leg.strike, leg.otype) for leg in legs]
    if any(f.empty for f in frames):
        return None, "leg_no_data"
    fills = [lc.next_open(f, t0) for f in frames]
    if any(f is None for f in fills):
        return None, "leg_no_fill"
    entry_t = max(f[0] for f in fills)
    prices = [f[1] for f in fills]
    vols = [f[2] for f in fills]
    return {"legs": legs, "entry_t": entry_t, "prices": prices, "vols": vols,
            "spot_entry": spot_at, "atm_k": atm_k}, "ok"


def run_cell(label: str, otype_mode: str, width: int, signal_label: str | None,
             exit_days_before: int = EXIT_DAYS_BEFORE_EXPIRY, hold_to_expiry: bool = False):
    """otype_mode: 'CE', 'PE', or 'signal' (direction from the signal picks CE/PE)."""
    cycles = entry_cycles()
    sig = daily_first_signals(signal_label) if signal_label else None
    sig_by_date = {}
    if sig is not None and not sig.empty:
        sig_by_date = {r["date"]: r for _, r in sig.iterrows()}

    trades, skips = [], {"leg_no_data": 0, "leg_no_fill": 0, "no_signal_in_window": 0, "far_no_data": 0}
    equity = lc.EQUITY0
    rows_out = []
    import time as _time
    _t0 = _time.time()
    for _ci, (win_start, near_exp) in enumerate(cycles):
        if _ci % 40 == 0:
            print(f"  [{label}] cycle {_ci}/{len(cycles)} near_exp={near_exp} "
                  f"elapsed={_time.time()-_t0:.1f}s trades_so_far={len(rows_out)}", flush=True)
        # entry-window days: win_start .. (near_exp - min stop buffer)
        window_days = [d for d in TCAL if win_start <= d < near_exp]
        entry_day = entry_t0 = None
        forced_otype = None
        if signal_label:
            hit = None
            for d in window_days:
                if d in sig_by_date:
                    hit = sig_by_date[d]
                    break
            if hit is None:
                skips["no_signal_in_window"] += 1
                continue
            entry_day = hit["date"]
            entry_t0 = hit["t"]
            forced_otype = "CE" if hit["dir"] > 0 else "PE"
        else:
            entry_day = window_days[0]
            entry_t0 = lc.day_snapshot_time(entry_day, "09:20")
            forced_otype = otype_mode

        res, reason = try_enter(entry_day, entry_t0, near_exp, forced_otype, width)
        if res is None:
            skips[reason] = skips.get(reason, 0) + 1
            continue
        legs, prices, vols = res["legs"], res["prices"], res["vols"]
        entry_debit = lc.net_debit(prices, legs)

        exit_day = exit_day_before(near_exp, 0 if hold_to_expiry else exit_days_before)
        if exit_day is None or exit_day <= res["entry_t"].date():
            exit_day = near_exp

        if hold_to_expiry:
            spot_final = lc.spot_close_asof(lc.day_snapshot_time(near_exp, "23:59"))
            if spot_final is None:
                continue
            exit_prices = [lc.intrinsic(spot_final, leg.strike, leg.otype) for leg in legs]
            exit_t = lc.day_snapshot_time(near_exp, "15:29")
        else:
            frames = [lc.leg_frame(leg.expiry, leg.strike, leg.otype) for leg in legs]
            t_exit = lc.day_snapshot_time(exit_day, "15:15")
            exit_prices = []
            ok = True
            for f in frames:
                p = lc.price_at_or_before(f, t_exit)
                if p is None:
                    ok = False
                    break
                exit_prices.append(p)
            if not ok:
                skips["leg_no_fill"] += 1
                continue
            exit_t = t_exit

        exit_val = lc.net_debit(exit_prices, legs)
        lots = lc.size_lots(equity, res["spot_entry"], defined_risk=True)
        lu = lc.lot_units_side(legs)
        fee_rt = 2 * lc.friction_rs(lu) * lots   # entry side + exit side
        gross_rs = (exit_val - entry_debit) * lc.LOT_SIZE * lots
        net_rs = gross_rs - fee_rt
        margin = lc.margin_rs(res["spot_entry"], lots, defined_risk=True)
        equity += net_rs

        # trap-zone check at THIS trade's own exit spot vs its own strikes
        if hold_to_expiry:
            exit_spot = spot_final
        else:
            v = lc.spot_close_asof(exit_t)
            exit_spot = v if v is not None else np.nan
        short_k, long_k = legs[0].strike, legs[1].strike
        lo, hi = sorted([short_k, long_k])
        in_trap = bool(lo <= exit_spot <= hi) if np.isfinite(exit_spot) else None

        rows_out.append({
            "near_exp": near_exp, "entry_day": entry_day, "entry_t": res["entry_t"],
            "otype": forced_otype, "short_k": short_k, "long_k": long_k, "width": width,
            "spot_entry": res["spot_entry"], "entry_debit": entry_debit,
            "exit_t": exit_t, "exit_val": exit_val, "exit_spot": exit_spot, "in_trap_zone": in_trap,
            "lots": lots, "margin_rs": margin, "gross_rs": gross_rs, "fee_rs": fee_rt,
            "net_rs": net_rs, "vol_short_entry": vols[0], "vol_long_entry": vols[1],
            "thin_short": vols[0] < 50 if np.isfinite(vols[0]) else None,
            "thin_long": vols[1] < 50 if np.isfinite(vols[1]) else None,
            "zero_short": vols[0] == 0 if np.isfinite(vols[0]) else None,
            "zero_long": vols[1] == 0 if np.isfinite(vols[1]) else None,
        })

    df = pd.DataFrame(rows_out)
    return df, skips


def summarize(df: pd.DataFrame, label: str) -> dict:
    if df.empty:
        return {"label": label, "n": 0}
    d = df.copy()
    d["date"] = pd.to_datetime(d["entry_day"])
    build = d[d["date"].dt.date <= lc.BUILD_END]
    fwd = d[d["date"].dt.date > lc.BUILD_END]

    def block(x: pd.DataFrame) -> dict:
        if x.empty:
            return {"n": 0}
        gross, fee, net = x["gross_rs"].sum(), x["fee_rs"].sum(), x["net_rs"].sum()
        r = x["net_rs"]
        # NW t-stat (lag-2, matches firm convention elsewhere)
        from numpy import sqrt
        n = len(r)
        mean = r.mean(); s2 = r.var(ddof=1) if n > 1 else np.nan
        if n > 2:
            gamma1 = np.cov(r.values[:-1], r.values[1:])[0, 1] if n > 2 else 0.0
            var_nw = (s2 + 2 * gamma1) / n
            t_nw = mean / sqrt(var_nw) if var_nw > 0 else np.nan
        else:
            t_nw = np.nan
        wins = r[r > 0]; losses = r[r <= 0]
        pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else np.inf
        return {
            "n": int(n), "gross_rs": float(gross), "fee_rs": float(fee), "net_rs": float(net),
            "friction_pct_gross": float(fee / gross) if gross != 0 else None,
            "mean_net_rs": float(mean), "hit_rate": float((r > 0).mean()),
            "median_ret_rs": float(r.median()), "p95_rs": float(r.quantile(0.95)),
            "max_rs": float(r.max()), "min_rs": float(r.min()),
            "largest_winner_share": float(wins.max() / wins.sum()) if len(wins) and wins.sum() > 0 else None,
            "t_nw": float(t_nw) if np.isfinite(t_nw) else None, "PF": float(pf) if np.isfinite(pf) else None,
            "trap_zone_freq": float(x["in_trap_zone"].mean()) if x["in_trap_zone"].notna().any() else None,
            "thin_short_frac": float(x["thin_short"].mean()) if x["thin_short"].notna().any() else None,
            "thin_long_frac": float(x["thin_long"].mean()) if x["thin_long"].notna().any() else None,
            "zero_short_frac": float(x["zero_short"].mean()) if x["zero_short"].notna().any() else None,
            "zero_long_frac": float(x["zero_long"].mean()) if x["zero_long"].notna().any() else None,
        }

    out = {"label": label, "build": block(build), "forward": block(fwd), "all": block(d)}
    return out


def main():
    cells = [
        ("backspread_CE_unconditional_w2", "CE", 2, None, False),
        ("backspread_PE_unconditional_w2", "PE", 2, None, False),
        ("backspread_signal_priorday_reclaim_w2", "signal", 2, "priorday_reclaim", False),
        ("backspread_signal_intraday_continue_w2", "signal", 2, "intraday_continue", False),
        ("backspread_CE_unconditional_w1", "CE", 1, None, False),
        ("backspread_CE_unconditional_w4", "CE", 4, None, False),
        ("backspread_CE_unconditional_w2_holdexpiry", "CE", 2, None, True),
        ("backspread_signal_priorday_reclaim_w2_holdexpiry", "signal", 2, "priorday_reclaim", True),
    ]
    report = {}
    all_trades = {}
    for label, mode, width, sig, hte in cells:
        df, skips = run_cell(label, mode, width, sig, hold_to_expiry=hte)
        summ = summarize(df, label)
        summ["skips"] = skips
        report[label] = summ
        all_trades[label] = df
        df.to_csv(OUT / f"trades_{label}.csv", index=False)
        b, f = summ["build"], summ["forward"]
        print(f"[{label}] build n={b.get('n')} net_mean=Rs{b.get('mean_net_rs')} "
              f"friction%={b.get('friction_pct_gross')} t={b.get('t_nw')} trap%={b.get('trap_zone_freq')} "
              f"| forward n={f.get('n')} net_mean=Rs{f.get('mean_net_rs')} | skips={skips}", flush=True)

    (OUT / "backspread_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("\nDONE -> backspread_report.json")


if __name__ == "__main__":
    sys.exit(main())
