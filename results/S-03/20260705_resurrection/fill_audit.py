"""K-012 RESURRECTION — leg 3/3: thin-strike fill audit (Tara Singh, Execution & TCA).

Question: recompute the RECOMMENDED (equal-premium, 3x-median liquidity cap) forward P&L
under HONEST fills (Principal's circuit/volume rule, execution_realism.py tiers), per-leg,
per-trade, using the EXACT strike/expiry/day used by forward_factor_v2.py's own pricer.

Data lineage (verified, see FILL_AUDIT_FF.md):
  - Trade universe: intraday_options_strategy/buying/forward_factor_v2.parquet (4,585 rows,
    205 syms). Structure = SELL front-month CE / BUY back-month CE, same strike (nearest to
    spot at entry), entered at peak-FF lead time, exited 2 sessions before front expiry.
  - Large-cap FF>=0.25 slice used by the S-03 resurrection = 673 trades / 54 symbols
    (matches results/S-03/20260704_shuffle/config.json + verdict.md exactly).
  - Raw per-minute/per-day option prints: intraday_options_strategy/datasets/raw/
    hf_index_options_1m/stocks_options/<SYM>/<EXPIRY>.parquet -- SAME files forward_factor_v2.py
    read prices from (dispersion_strategy.SOPT). DUAL SCHEMA confirmed empirically:
    HF 1-min (tz-aware ts, 'open_interest' col) for 2021-24Mar & Sep25-Jun26;
    bhavcopy DAILY (naive ts, 'settle'+'oi' cols, ALL trading days for a stock's option's whole
    life in one file) for Apr24-Aug25. Bhavcopy rows carry a NONZERO theoretical close/settle
    even at ZERO volume (verified: ABB 5600 CE 2024-04-26 close=1068.55 settle=1047.25 volume=0)
    -- forward_factor_v2.leg_px only gates on price>0, NEVER on volume. That gate is exactly
    what this audit adds.

Sizing reconstruction (script that produced trading_brief_stats.json RECOMMENDED premium-capped
row is NOT preserved anywhere on disk -- grepped repo-wide for "1201.78"/"premium_cap", zero
scripts found beyond the two summary docs). Reconstructed [INFERENCE] and validated to match
ALL published numbers (win/avg_win/avg_loss/pf/total/worst) to <0.1%:
    qty_i        = 100 / CE_be_i                      (equal PREMIUM: Rs100 back-leg premium/trade)
    cap          = 3 * median(qty_i) over the 673-trade slice = 6.0
    qty_capped_i = min(qty_i, cap)
    pnl100_i     = pnl_i * qty_capped_i                (pnl_i = per-unit rupee P&L, flat 1.5% slip)
This reproduces n=673 win=71.8% avg_win=29.2 avg_loss=-33.1 pf=2.24 total=7812.1 worst=-464.4
vs trading_brief_stats.json's 29.2/-33.1/2.24/7812.0/-464.0 -- essentially exact.
NOTE the stored "cap": 1201.7857142857142 field does not correspond to this qty-space cap under
any transform we could reverse (documented, not fatal -- the P&L reconstruction match is what
matters and it is exact).
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import dispersion_strategy as ds  # noqa: E402  (_series, _nearest, SOPT)

SOPT = ds.SOPT
FF = ROOT / "intraday_options_strategy/buying/forward_factor_v2.parquet"
OUT = ROOT / "results/S-03/20260705_resurrection"

BASE_SLIP = 0.015          # COST_STANDARDS: single-stock near-ATM options 0.5-1.5% premium;
                            # using the TOP of the approved band (matches the original backtest's
                            # own SLIP constant -- so our "NORMAL" tier is already conservative).
FF_MIN = 0.25
SPLIT = pd.Timestamp(2024, 12, 31)
MEDIAN_LOOKBACK = 20        # trailing sessions, PIT (strictly before target day), per CONTRACT
DEFER_MAX_LOOKAHEAD = 40    # safety cap on forward search within the same file

_file_cache: dict[tuple[str, str], object] = {}


def load_file(sym: str, expiry: pd.Timestamp):
    key = (sym, expiry.date().isoformat())
    if key not in _file_cache:
        p = SOPT / sym / f"{expiry.date().isoformat()}.parquet"
        _file_cache[key] = pq.read_table(p).to_pandas() if p.exists() else None
    return _file_cache[key]


def day_table(df, strike: float) -> pd.DataFrame:
    """Per-trading_day: summed volume, last close, last settle (schema-agnostic: bhavcopy is
    already 1 row/day so sum/last are no-ops; HF 1-min gets properly aggregated to a day total)."""
    sub = df[(df["strike"].astype(float) == float(strike)) & (df["option_type"] == "CE")]
    if sub.empty:
        return pd.DataFrame(columns=["volume", "close", "settle"])
    g = sub.groupby("trading_day")
    out = pd.DataFrame({"volume": g["volume"].sum(), "close": g["close"].last()})
    out["settle"] = g["settle"].last() if "settle" in sub.columns else np.nan
    return out.sort_index()


def classify(day_vol, median20, hist_days) -> tuple[str, float | None]:
    if day_vol is None or not np.isfinite(day_vol) or day_vol <= 0:
        return "UNTRADED", None
    if hist_days == 0:
        return "NORMAL-NOHIST", 1.0     # brand-new contract, no prior session to judge against
    ratio = day_vol / median20 if (median20 is not None and median20 > 0) else np.inf
    if ratio >= 0.5:
        return "NORMAL", 1.0
    if ratio >= 0.2:
        return "THIN", 2.0
    return "THIN-ABRUPT", 3.0


def leg_eval(dt_tab: pd.DataFrame, target_day: pd.Timestamp) -> dict:
    tds = target_day.date().isoformat()
    present = tds in dt_tab.index
    vol = float(dt_tab.loc[tds, "volume"]) if present else 0.0
    close = float(dt_tab.loc[tds, "close"]) if present else np.nan
    prior20 = dt_tab.loc[dt_tab.index < tds, "volume"].tail(MEDIAN_LOOKBACK)
    median20 = float(prior20.median()) if len(prior20) else np.nan
    tier, mult = classify(vol if present else 0.0, median20, len(prior20))
    return dict(present=present, volume=vol, close=close, median20=median20,
                hist_days=len(prior20), tier=tier, mult=mult)


def find_defer(dt_tab: pd.DataFrame, target_day: pd.Timestamp):
    tds = target_day.date().isoformat()
    idx = dt_tab.index.tolist()
    fut_idx = [d for d in idx if d > tds][:DEFER_MAX_LOOKAHEAD]
    for d in fut_idx:
        if dt_tab.loc[d, "volume"] > 0:
            sessions = fut_idx.index(d) + 1
            # classify the deferred day itself vs ITS OWN trailing history
            prior20 = dt_tab.loc[dt_tab.index < d, "volume"].tail(MEDIAN_LOOKBACK)
            median20 = float(prior20.median()) if len(prior20) else np.nan
            tier, mult = classify(float(dt_tab.loc[d, "volume"]), median20, len(prior20))
            return dict(day=d, close=float(dt_tab.loc[d, "close"]), sessions_deferred=sessions,
                        tier=tier, mult=mult)
    return None


def settle_fallback(dt_tab: pd.DataFrame, target_day: pd.Timestamp, orig_price: float):
    tds = target_day.date().isoformat()
    if tds in dt_tab.index and np.isfinite(dt_tab.loc[tds, "settle"]) and dt_tab.loc[tds, "settle"] > 0:
        return float(dt_tab.loc[tds, "settle"]), "settle_col"
    return float(orig_price), "stale_print_no_settle_col"


def build_slice():
    ff = pd.read_parquet(FF)
    ff["entry"] = pd.to_datetime(ff["entry"]); ff["m1_exp"] = pd.to_datetime(ff["m1_exp"])
    ff["pnl"] = (ff["CE_fe"] * (1 - BASE_SLIP) - ff["CE_be"] * (1 + BASE_SLIP)
                 - ff["CE_fx"] * (1 + BASE_SLIP) + ff["CE_bx"] * (1 - BASE_SLIP))
    first = ff.groupby("sym")["entry"].min()
    lc = set(first[first < pd.Timestamp(2024, 1, 1)].index)
    L = ff[ff["sym"].isin(lc)].copy()
    S = L[L["ff"] >= FF_MIN].copy().reset_index(drop=True)
    assert len(S) == 673 and S["sym"].nunique() == 54, \
        f"SLICE MISMATCH vs verdict.md (673/54): got {len(S)}/{S['sym'].nunique()}"
    qty = 100.0 / S["CE_be"].to_numpy()
    cap = 3 * np.median(qty)
    S["qty_capped"] = np.minimum(qty, cap)
    S["pnl100_headline"] = S["pnl"] * S["qty_capped"]
    S["m2_exp"] = S["entry"] + pd.to_timedelta(S["dte2"].astype(int), unit="D")
    return S, cap


def process_trade(row) -> dict:
    sym, strike = row["sym"], row["strike"]
    entry, m1_exp, m2_exp = row["entry"], row["m1_exp"], row["m2_exp"]

    front = load_file(sym, m1_exp)
    back = load_file(sym, m2_exp)
    rec = dict(sym=sym, entry=entry.date().isoformat(), m1_exp=m1_exp.date().isoformat(),
               m2_exp=m2_exp.date().isoformat(), strike=strike, ff=row["ff"],
               qty_capped=row["qty_capped"], pnl100_headline=row["pnl100_headline"])
    if front is None or back is None:
        rec.update(dropped=True, drop_reason="source_file_missing", pnl100_honest=0.0)
        return rec

    # recompute exit_day EXACTLY as forward_factor_v2.run_once did
    tdays1 = sorted(pd.to_datetime(front["trading_day"].unique()))
    exit_cands = [d.date() for d in tdays1 if entry.date() < d.date() < m1_exp.date()]
    if len(exit_cands) < 2:
        rec.update(dropped=True, drop_reason="cannot_recompute_exit_day", pnl100_honest=0.0)
        return rec
    exit_day = pd.Timestamp(exit_cands[-2])

    front_tab = day_table(front, strike)
    back_tab = day_table(back, strike)

    # cross-check against the ORIGINAL stored prices (byte-level replication of _nearest)
    def crosscheck(df, target, stored):
        ser = ds._series(df, strike, "CE")
        px, used_day = ds._nearest(ser, target, 15)
        stale = (used_day is not None) and (used_day != target.date())
        match = np.isfinite(px) and abs(px - stored) < 0.01
        return match, stale, used_day

    m_fe, stale_fe, ud_fe = crosscheck(front, entry, row["CE_fe"])
    m_be, stale_be, ud_be = crosscheck(back, entry, row["CE_be"])
    m_fx, stale_fx, ud_fx = crosscheck(front, exit_day, row["CE_fx"])
    m_bx, stale_bx, ud_bx = crosscheck(back, exit_day, row["CE_bx"])
    rec.update(xcheck_match=all([m_fe, m_be, m_fx, m_bx]),
               stale_fe=stale_fe, stale_be=stale_be, stale_fx=stale_fx, stale_bx=stale_bx)

    ev_fe = leg_eval(front_tab, entry)
    ev_be = leg_eval(back_tab, entry)
    ev_fx = leg_eval(front_tab, exit_day)
    ev_bx = leg_eval(back_tab, exit_day)
    for tag, ev in (("fe", ev_fe), ("be", ev_be), ("fx", ev_fx), ("bx", ev_bx)):
        rec[f"tier_{tag}"] = ev["tier"]; rec[f"vol_{tag}"] = ev["volume"]
        rec[f"med20_{tag}"] = ev["median20"]; rec[f"hist_{tag}"] = ev["hist_days"]

    # ---- DROP: either entry leg untraded on the exact day ----
    if ev_fe["tier"] == "UNTRADED" or ev_be["tier"] == "UNTRADED":
        rec.update(dropped=True,
                    drop_reason=f"entry_untraded(fe={ev_fe['tier']},be={ev_be['tier']})",
                    pnl100_honest=0.0)
        return rec
    rec["dropped"] = False

    fe_px, be_px = row["CE_fe"], row["CE_be"]
    slip_fe, slip_be = BASE_SLIP * ev_fe["mult"], BASE_SLIP * ev_be["mult"]

    # ---- EXIT legs: defer if untraded, else settle-fallback if no defer possible ----
    fx_px, slip_fx, exit_note_f = row["CE_fx"], BASE_SLIP * (ev_fx["mult"] or 1.0), "same_day"
    if ev_fx["tier"] == "UNTRADED":
        d = find_defer(front_tab, exit_day)
        if d is not None and d["day"] <= m1_exp.date().isoformat():
            fx_px, slip_fx = d["close"], BASE_SLIP * d["mult"]
            exit_note_f = f"deferred_{d['sessions_deferred']}sess"
        else:
            fx_px, how = settle_fallback(front_tab, exit_day, row["CE_fx"])
            slip_fx = BASE_SLIP * 3.0
            exit_note_f = f"settle_fallback:{how}"

    bx_px, slip_bx, exit_note_b = row["CE_bx"], BASE_SLIP * (ev_bx["mult"] or 1.0), "same_day"
    if ev_bx["tier"] == "UNTRADED":
        d = find_defer(back_tab, exit_day)
        if d is not None:
            bx_px, slip_bx = d["close"], BASE_SLIP * d["mult"]
            exit_note_b = f"deferred_{d['sessions_deferred']}sess"
        else:
            bx_px, how = settle_fallback(back_tab, exit_day, row["CE_bx"])
            slip_bx = BASE_SLIP * 3.0
            exit_note_b = f"settle_fallback:{how}"

    rec["exit_note_f"] = exit_note_f; rec["exit_note_b"] = exit_note_b
    rec["slip_fe"] = slip_fe; rec["slip_be"] = slip_be
    rec["slip_fx"] = slip_fx; rec["slip_bx"] = slip_bx

    pnl_honest_unit = (fe_px * (1 - slip_fe) - be_px * (1 + slip_be)
                       - fx_px * (1 + slip_fx) + bx_px * (1 - slip_bx))
    rec["pnl100_honest"] = pnl_honest_unit * row["qty_capped"]
    return rec


def main():
    S, cap = build_slice()
    print(f"[checkpoint] slice built: n={len(S)} symbols={S['sym'].nunique()} qty_cap={cap}")
    print(f"[checkpoint] headline totals: sum(pnl100_headline)={S['pnl100_headline'].sum():.1f} "
          f"n={len(S)}")

    recs = []
    for i, row in S.iterrows():
        recs.append(process_trade(row))
        if (i + 1) % 50 == 0:
            n_drop = sum(r.get("dropped", False) for r in recs)
            print(f"[checkpoint] {i+1}/{len(S)} processed, dropped so far={n_drop}, "
                  f"unique files cached={len(_file_cache)}")

    out = pd.DataFrame(recs)
    out.to_csv(OUT / "fill_audit_per_trade.csv", index=False)
    print(f"[checkpoint] wrote {OUT / 'fill_audit_per_trade.csv'} rows={len(out)}")

    xcheck_rate = out["xcheck_match"].mean() if "xcheck_match" in out.columns else np.nan
    print(f"\n[VALIDATION] cross-check match rate (my re-derived price == parquet stored price): "
          f"{xcheck_rate:.1%} over {out['xcheck_match'].notna().sum()} non-dropped trades")

    with open(OUT / "fill_audit_summary.json", "w", encoding="utf-8") as fh:
        json.dump({"n": len(out), "cap_qty": cap,
                   "xcheck_match_rate": None if pd.isna(xcheck_rate) else float(xcheck_rate)},
                  fh, indent=2, default=str)
    print("done")


if __name__ == "__main__":
    main()
