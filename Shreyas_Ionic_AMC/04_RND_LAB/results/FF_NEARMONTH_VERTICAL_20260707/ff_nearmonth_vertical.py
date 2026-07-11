"""FF signal -> NEAR-MONTH BEAR-CALL VERTICAL backtest (Candidate B).
Owner: Arjun Rao (Head of Quant). Date: 2026-07-07.

FRESH IDEA by firm process: new VEHICLE (does NOT inherit K-012's kill/P&L), same
validated FF signal population (673 causal signals, causal_per_trade.csv). Pre-registration
frozen from Aakash's memo `04_RND_LAB/ideas/20260707_ff_signal_near_month_vehicle.md` (§6) +
Tara's ex-ante-gate fix (`..._TARA_AUDIT.md`). No parameter tuned after seeing results.

FROZEN SPEC
- ENTRY: reuse the causal first-FF-cross signal (ca_D, ca_strike=ATM, m1_exp) verbatim.
  SELL near-month ATM CE @ ca_strike ; BUY near-month OTM CE @ hedge strike. SAME expiry m1_exp.
- HEDGE STRIKE (Tara ex-ante rule): nearest OTM strike (above ca_strike) whose TRAILING-5-SESSION
  median volume (strictly BEFORE ca_D, PIT) > 0, searched outward up to 8 strikes. None clears -> DROP.
  (Tara audited same-day realized vol -> 2.1% full / 0.5% fwd drop; production gate is ex-ante
  trailing-5 median, per her explicit methodology fix.)
- FILLS: D+1 (next session after ca_D). Both legs must be tradeable on the SAME fill day (a
  vertical executes together). If either UNTRADED at D+1, defer one session; still UNTRADED -> DROP.
  Same-day-close is an EXPLORATORY rung only (cannot enter verdict, lesson 17).
- EXIT: both legs together, 2 sessions before m1 expiry (avoids ITM assignment / STT-on-exercise).
  Exit fills: same_day -> find_defer -> settle_fallback (Tara convention).
- COSTS: tiered slippage on BASE=0.015 (>=0.5x med20 ->1x, 0.2-0.5 ->2x, <0.2 ->3x), reported at
  1x and 2x. PLUS explicit statutory (STT 0.1% sell premium, exch 0.035% all legs, GST 18% on exch,
  stamp 0.003% buy). Brokerage Rs20/order noted separately (sizing-dependent, de minimis per-share).
- UNITS: denominator-free RUPEE POINTS + %-of-SPOT only. NEVER %-of-premium.
- SIZING: defined-risk, does not affect per-share edge; reported per-trade (IC-1: certify PER-TRADE).
- REPORTED ALSO (kill NEW-6): naked short ATM call (Candidate A) same entries/exits, for comparison.

REUSES fill_audit loaders verbatim (load_file/day_table/leg_eval/find_defer/settle_fallback) and
the dispersion_strategy pricer/stock_close. Legacy folders read-only.
"""
from __future__ import annotations

import sys
import json
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "results/S-03/20260705_resurrection"))
sys.path.insert(0, str(ROOT / "intraday_options_strategy/buying"))
import fill_audit as fa           # noqa: E402
import dispersion_strategy as ds  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/FF_NEARMONTH_VERTICAL_20260707"
SIGNALS = ROOT / "results/S-03/20260705_resurrection/causal_per_trade.csv"
SOPT = ds.SOPT

BASE_SLIP = fa.BASE_SLIP          # 0.015
MAX_DIST = 8                      # Aakash pre-reg hedge search cap
TRAIL = 5                         # Tara ex-ante trailing-session median window
SPLIT_OOS = dt.date(2024, 12, 31)  # BUILD/FWD (pre-registered walk-forward split, all K-012 legs)
SPLIT_REGIME = dt.date(2025, 9, 1)  # schema-regime robustness slice (bhavcopy-daily vs HF-1min tail)

_exps_cache: dict[str, list] = {}
STOCK = None


def sym_expiries(sym):
    if sym not in _exps_cache:
        _exps_cache[sym] = sorted(dt.date.fromisoformat(p.stem) for p in (SOPT / sym).glob("*.parquet"))
    return _exps_cache[sym]


def next_session(sessions, day):
    fut = [d for d in sessions if d > day]
    return fut[0] if fut else None


def exit_day_for(entry_date, m1_exp, tdays1):
    ex = [d.date() for d in tdays1 if entry_date < d.date() < m1_exp]
    return ex[-2] if len(ex) >= 2 else None


def trailing_median_vol(tab, day_iso, n):
    prior = tab.loc[tab.index < day_iso, "volume"].tail(n)
    return float(prior.median()) if len(prior) else np.nan


def resolve_exit(tab, day, orig_close):
    """same_day close -> find_defer -> settle_fallback. Returns (px, slip_mult, tier, note)."""
    ev = fa.leg_eval(tab, pd.Timestamp(day))
    if ev["tier"] != "UNTRADED":
        return ev["close"], ev["mult"], ev["tier"], "same_day"
    d = fa.find_defer(tab, pd.Timestamp(day))
    if d is not None:
        return d["close"], d["mult"], d["tier"], f"deferred_{d['sessions_deferred']}"
    px, how = fa.settle_fallback(tab, pd.Timestamp(day), orig_close)
    return px, 3.0, "SETTLE", f"settle:{how}"


def vert_pnl(se, sx, le, lx, s_se, s_sx, s_le, s_lx):
    """Bear-call vertical, rupee points/share: SELL ATM entry/BUY ATM exit ; BUY OTM entry/SELL OTM exit."""
    return se * (1 - s_se) - sx * (1 + s_sx) - le * (1 + s_le) + lx * (1 - s_lx)


def naked_pnl(se, sx, s_se, s_sx):
    """Naked short ATM call (Candidate A): SELL entry / BUY-back exit."""
    return se * (1 - s_se) - sx * (1 + s_sx)


def statutory_vertical(se, sx, le, lx):
    """Rupee-points/share statutory cost. Sells=ATM entry + OTM exit. Buys=OTM entry + ATM exit."""
    stt = 0.001 * (se + lx)                       # 0.1% premium, sell side
    exch = 0.00035 * (se + sx + le + lx)          # 0.035% premium, all legs
    gst = 0.18 * exch                             # 18% on exchange txn
    stamp = 0.00003 * (le + sx)                   # 0.003% premium, buy side
    return stt + exch + gst + stamp


def statutory_naked(se, sx):
    stt = 0.001 * se
    exch = 0.00035 * (se + sx)
    gst = 0.18 * exch
    stamp = 0.00003 * sx
    return stt + exch + gst + stamp


def get_spot(sym, ca_D, ca_strike):
    if STOCK is not None and sym in STOCK.columns:
        s = STOCK[sym].dropna()
        v = s.asof(pd.Timestamp(ca_D))
        if np.isfinite(v) and v > 0:
            return float(v)
    return float(ca_strike)  # ATM strike ~ spot fallback


def process(row) -> dict:
    sym = row["sym"]
    m1_exp = dt.date.fromisoformat(str(row["m1_exp"])[:10])
    ca_D = dt.date.fromisoformat(str(row["ca_D"])[:10])
    short_strike = float(row["ca_strike"])
    day_iso = ca_D.isoformat()
    period = row["period"]
    spot = get_spot(sym, ca_D, short_strike)

    rec = dict(sym=sym, m1_exp=m1_exp.isoformat(), ca_D=day_iso, period=period,
               ca_ff=float(row["ca_ff"]), short_strike=short_strike, spot=spot,
               regime="POST_2025-09" if ca_D >= SPLIT_REGIME else "PRE_2025-09")

    front = fa.load_file(sym, pd.Timestamp(m1_exp))
    if front is None:
        rec.update(status="front_file_missing", dropped=True, drop_reason="front_file_missing")
        return rec
    tdays1 = sorted(pd.to_datetime(front["trading_day"].unique()))
    sessions = [d.date() for d in tdays1]
    if short_strike not in set(front.loc[front["option_type"] == "CE", "strike"].astype(float)):
        rec.update(status="short_strike_absent", dropped=True, drop_reason="short_strike_absent")
        return rec

    exit_day = exit_day_for(ca_D, m1_exp, tdays1)
    if exit_day is None:
        rec.update(status="no_exit_day", dropped=True, drop_reason="no_exit_day")
        return rec
    rec["exit_day"] = exit_day.isoformat()

    # ---- HEDGE STRIKE SELECTION (ex-ante, trailing-5 median vol > 0, nearest within 8) ----
    strikes = sorted(front.loc[front["option_type"] == "CE", "strike"].astype(float).unique())
    higher = [k for k in strikes if k > short_strike][:MAX_DIST]
    hedge_strike, hedge_dist, hedge_tab = None, None, None
    for d, k in enumerate(higher, start=1):
        tab = fa.day_table(front, k)
        med5 = trailing_median_vol(tab, day_iso, TRAIL)
        if np.isfinite(med5) and med5 > 0:
            hedge_strike, hedge_dist, hedge_tab = k, d, tab
            rec["hedge_med5"] = med5
            break
    if hedge_strike is None:
        rec.update(status="ok", dropped=True, drop_reason="no_hedge_strike_ex_ante",
                   n_otm_avail=len(higher))
        return rec
    rec.update(hedge_strike=hedge_strike, hedge_dist=hedge_dist,
               strike_width=hedge_strike - short_strike)

    short_tab = fa.day_table(front, short_strike)

    # ---- ENTRY FILL: D+1 (defer one session); BOTH legs must be tradeable same day ----
    d1 = next_session(sessions, ca_D)
    d2 = next_session(sessions, d1) if d1 is not None else None
    fill_day = ev_s = ev_l = None
    for cand in (d1, d2):
        if cand is None:
            continue
        es = fa.leg_eval(short_tab, pd.Timestamp(cand))
        el = fa.leg_eval(hedge_tab, pd.Timestamp(cand))
        if es["tier"] != "UNTRADED" and el["tier"] != "UNTRADED":
            fill_day, ev_s, ev_l = cand, es, el
            break
    if fill_day is None:
        rec.update(status="ok", dropped=True, drop_reason="entry_untraded_D1_D2")
        return rec

    se, le = ev_s["close"], ev_l["close"]           # short/long ENTRY premia
    m_se, m_le = ev_s["mult"] or 1.0, ev_l["mult"] or 1.0
    rec.update(fill_day=fill_day.isoformat(), tier_se=ev_s["tier"], tier_le=ev_l["tier"],
               se=se, le=le, vol_se=ev_s["volume"], vol_le=ev_l["volume"])

    # ---- EXIT FILL ----
    sx, m_sx, tier_sx, note_sx = resolve_exit(short_tab, exit_day, ds.price_asof(front, short_strike, "CE", pd.Timestamp(exit_day)))
    lx, m_lx, tier_lx, note_lx = resolve_exit(hedge_tab, exit_day, ds.price_asof(front, hedge_strike, "CE", pd.Timestamp(exit_day)))
    rec.update(sx=sx, lx=lx, tier_sx=tier_sx, tier_lx=tier_lx, note_sx=note_sx, note_lx=note_lx)

    if not all(np.isfinite(x) and x > 0 for x in (se, le, sx, lx)):
        rec.update(status="ok", dropped=True, drop_reason="nonpos_price")
        return rec

    net_credit = se - le
    rec["net_credit"] = net_credit
    rec["dropped"] = False
    rec["status"] = "ok"

    # ---- P&L (rupee points/share) ----
    stat_v = statutory_vertical(se, sx, le, lx)
    stat_n = statutory_naked(se, sx)
    for scale, tag in ((0, "friction0"), (1, "1x"), (2, "2x")):
        pv = vert_pnl(se, sx, le, lx, BASE_SLIP * m_se * scale, BASE_SLIP * m_sx * scale,
                      BASE_SLIP * m_le * scale, BASE_SLIP * m_lx * scale)
        pn = naked_pnl(se, sx, BASE_SLIP * m_se * scale, BASE_SLIP * m_sx * scale)
        rec[f"vert_slip_{tag}"] = pv                       # slippage-only (K-012-comparable)
        rec[f"naked_slip_{tag}"] = pn
        if scale > 0:
            rec[f"vert_net_{tag}"] = pv - stat_v           # slippage + statutory (full honesty)
            rec[f"naked_net_{tag}"] = pn - stat_n
            rec[f"vert_pctspot_{tag}"] = 100.0 * (pv - stat_v) / spot
            rec[f"naked_pctspot_{tag}"] = 100.0 * (pn - stat_n) / spot
    rec["vert_pctspot_friction0"] = 100.0 * rec["vert_slip_friction0"] / spot
    rec["statutory_v"] = stat_v
    return rec


def agg_block(df, unit_col, label):
    """Aggregate a rupee-points column: mean, sum, win, PF, avg win/loss, worst, on FILLED trades."""
    f = df[df["dropped"] == False]  # noqa: E712
    n = len(f)
    if n == 0:
        return dict(label=label, n_signals=len(df), n_filled=0)
    s = f[unit_col]
    wins = s[s > 0]; losses = s[s <= 0]
    pf = wins.sum() / (-losses.sum()) if losses.sum() < 0 else np.inf
    return dict(label=label, n_signals=len(df), n_filled=n,
                drop_rate=1 - n / len(df),
                mean_rs=float(s.mean()), sum_rs=float(s.sum()),
                win=float((s > 0).mean()), pf=float(pf) if np.isfinite(pf) else 999.0,
                avg_win=float(wins.mean()) if len(wins) else 0.0,
                avg_loss=float(losses.mean()) if len(losses) else 0.0,
                worst=float(s.min()))


def sharpe_stats(df, pct_col):
    """Per-trade + monthly (exit-month booking) annualized Sharpe on %-of-spot returns."""
    f = df[(df["dropped"] == False) & df[pct_col].notna()].copy()  # noqa: E712
    if len(f) < 8:
        return dict(n=len(f), pertrade_sharpe=None, ann_sharpe_pertrade=None, ann_sharpe_monthly=None)
    r = f[pct_col] / 100.0  # fraction of spot
    mu, sd = r.mean(), r.std(ddof=1)
    span_yrs = max((pd.to_datetime(f["ca_D"]).max() - pd.to_datetime(f["ca_D"]).min()).days / 365.25, 1e-6)
    tpy = len(f) / span_yrs
    pertrade = mu / sd if sd > 0 else np.nan
    ann_pt = pertrade * np.sqrt(tpy) if np.isfinite(pertrade) else np.nan
    # exit-month booking (charter rule): sum P&L in EXIT month, equal 1-spread weight
    f["exit_m"] = pd.to_datetime(f["exit_day"]).dt.to_period("M")
    monthly = f.groupby("exit_m")[pct_col].sum() / 100.0
    ann_m = (monthly.mean() / monthly.std(ddof=1)) * np.sqrt(12) if monthly.std(ddof=1) > 0 else np.nan
    return dict(n=len(f), trades_per_year=float(tpy),
                pertrade_sharpe=float(pertrade) if np.isfinite(pertrade) else None,
                ann_sharpe_pertrade=float(ann_pt) if np.isfinite(ann_pt) else None,
                ann_sharpe_monthly=float(ann_m) if np.isfinite(ann_m) else None)


def main():
    global STOCK
    print("[checkpoint] loading stock_close ...", flush=True)
    STOCK = ds.stock_close()
    sig = pd.read_csv(SIGNALS)
    sig = sig[sig["signal"] == True].reset_index(drop=True)  # noqa: E712
    print(f"[checkpoint] {len(sig)} FF signals loaded (BUILD/FWD split {SPLIT_OOS})", flush=True)

    recs = []
    for i, row in sig.iterrows():
        recs.append(process(row))
        if (i + 1) % 100 == 0:
            pd.DataFrame(recs).to_csv(OUT / "per_trade.csv", index=False)
            nd = sum(r.get("dropped", True) for r in recs)
            print(f"[checkpoint] {i+1}/{len(sig)} | dropped={nd}", flush=True)

    out = pd.DataFrame(recs)
    out.to_csv(OUT / "per_trade.csv", index=False)
    print(f"[checkpoint] wrote per_trade.csv rows={len(out)}", flush=True)

    # ---------- reporting ----------
    result = {"n_signals": len(out),
              "n_dropped": int(out["dropped"].sum()),
              "drop_rate": float(out["dropped"].mean()),
              "drop_reasons": out.loc[out["dropped"] == True, "drop_reason"].value_counts().to_dict()}  # noqa: E712

    cohorts = {"FULL": out, "BUILD": out[out["period"] == "BUILD"], "FWD": out[out["period"] == "FWD"],
               "REGIME_PRE_2025-09": out[out["regime"] == "PRE_2025-09"],
               "REGIME_POST_2025-09": out[out["regime"] == "POST_2025-09"]}

    print("\n===== VERTICAL (Candidate B) : slippage+statutory, %-of-spot =====", flush=True)
    tables = {}
    for name, df in cohorts.items():
        blk = {"vert_net_1x_rs": agg_block(df, "vert_net_1x", f"{name} vert net 1x"),
               "vert_net_2x_rs": agg_block(df, "vert_net_2x", f"{name} vert net 2x"),
               "vert_slip_1x_rs": agg_block(df, "vert_slip_1x", f"{name} vert slip-only 1x"),
               "vert_pct_1x": agg_block(df, "vert_pctspot_1x", f"{name} vert %spot 1x"),
               "vert_pct_2x": agg_block(df, "vert_pctspot_2x", f"{name} vert %spot 2x"),
               "naked_net_1x_rs": agg_block(df, "naked_net_1x", f"{name} naked net 1x"),
               "naked_pct_1x": agg_block(df, "naked_pctspot_1x", f"{name} naked %spot 1x"),
               "sharpe_pct_1x": sharpe_stats(df, "vert_pctspot_1x")}
        tables[name] = blk
        v1, v2 = blk["vert_net_1x_rs"], blk["vert_net_2x_rs"]
        p1 = blk["vert_pct_1x"]; sh = blk["sharpe_pct_1x"]
        print(f"  {name:20s} n_fill={v1.get('n_filled',0):4d}/{len(df):4d} "
              f"| Rs 1x={v1.get('mean_rs',0):+.3f} 2x={v2.get('mean_rs',0):+.3f} "
              f"| %spot 1x={p1.get('mean_rs',0):+.4f} "
              f"| win={v1.get('win',0):.3f} PF={v1.get('pf',0):.2f} "
              f"| annSharpe(pt)={sh.get('ann_sharpe_pertrade')}", flush=True)

    # per-year (by ca_D year) on vert_net_1x
    out["yr"] = pd.to_datetime(out["ca_D"]).dt.year
    peryear = {}
    print("\n===== PER-YEAR (entry year) vert net 1x, Rs-pts & %spot =====", flush=True)
    for yr, g in out.groupby("yr"):
        b = agg_block(g, "vert_net_1x", str(yr))
        bp = agg_block(g, "vert_pctspot_1x", str(yr))
        peryear[int(yr)] = {"n_fill": b.get("n_filled", 0), "mean_rs": b.get("mean_rs"),
                            "mean_pctspot": bp.get("mean_rs"), "win": b.get("win")}
        print(f"  {yr}  n_fill={b.get('n_filled',0):4d}  Rs={b.get('mean_rs',0):+.3f}  "
              f"%spot={bp.get('mean_rs',0):+.4f}  win={b.get('win',0):.3f}", flush=True)

    result["tables"] = tables
    result["per_year"] = peryear
    with open(OUT / "summary.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)
    print("\n[done] summary.json written", flush=True)


if __name__ == "__main__":
    main()
