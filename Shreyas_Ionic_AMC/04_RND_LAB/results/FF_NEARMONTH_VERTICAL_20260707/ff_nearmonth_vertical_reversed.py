"""FF signal -> NEAR-MONTH BULL-CALL VERTICAL (REVERSED) backtest.
Owner: Arjun Rao (Head of Quant). Date: 2026-07-07.

DISTINCT HYPOTHESIS from both K-012 (calendar) and the killed bear-call vertical.
Its own trial count; does NOT merge into either ledger.

WHAT THIS IS, ECONOMICALLY (stated upfront):
  SELL near-month OTM CE  /  BUY near-month ATM CE, SAME expiry.
  Buying the expensive ATM leg + selling the cheaper OTM leg = a NET DEBIT bull-call
  spread = a capped-risk DIRECTIONALLY-BULLISH bet. It is NOT a premium-harvesting /
  credit structure like the killed bear-call. It is the sign-mirror of that structure
  in raw payoff, but costs (always adverse) and the strike-selection rule are NOT
  mirrored, so it is re-run from data, not sign-flipped.

FROZEN SPEC (pre-registered from the task directive before seeing any result):
- ENTRY: reuse the causal first-FF-cross signal verbatim (ca_D, ca_strike=ATM, m1_exp)
  from causal_per_trade.csv (signal==True). LONG leg = ATM (ca_strike). SHORT leg = OTM.
- SHORT-OTM STRIKE (liquidity-informed, NEW per live-chain finding 2026-07-07): among
  OTM1..OTM6 candidates (CE strikes above ca_strike), each must clear an ex-ante floor
  (trailing-5-session median volume strictly BEFORE ca_D, PIT, > 0); among those that
  clear, pick the MOST LIQUID (argmax trailing-5 median volume). None clears -> DROP.
  (Live back-month chain pulls show deeper OTM strikes often carry more OI/vol than the
  nearest OTM; a nearest-that-clears rule would systematically pick the thinner strike.)
- FILLS: D+1 (next session after ca_D); both legs must be tradeable the SAME day; else
  defer one session; still untraded -> DROP. Same-day-close is exploratory only.
- EXIT: both legs together, 2 sessions before m1 expiry. same_day->defer->settle_fallback.
- COSTS: tiered slippage on BASE=0.015; reported 1x AND 2x, PLUS explicit statutory.
- UNITS: denominator-free RUPEE POINTS + %-of-SPOT only. NEVER %-of-premium.
- REGIME split at 2025-09-01. BUILD/FWD split at 2024-12-31 (period col in signals).
- DIRECTIONAL DIAGNOSTIC: this leg is net-long-delta, so a positive result is suspect of
  being market/stock up-drift (beta), not FF alpha. Report underlying spot move over the
  hold and a naked-long-ATM-call comparison so the beta signature is visible.

REUSES fill_audit loaders verbatim + dispersion_strategy pricer/stock_close.
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
MAX_DIST = 6                      # OTM1..OTM6 short-leg search cap (task directive)
TRAIL = 5                         # ex-ante trailing-session median window
SPLIT_REGIME = dt.date(2025, 9, 1)

_exps_cache: dict[str, list] = {}
STOCK = None


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
    ev = fa.leg_eval(tab, pd.Timestamp(day))
    if ev["tier"] != "UNTRADED":
        return ev["close"], ev["mult"], ev["tier"], "same_day"
    d = fa.find_defer(tab, pd.Timestamp(day))
    if d is not None:
        return d["close"], d["mult"], d["tier"], f"deferred_{d['sessions_deferred']}"
    px, how = fa.settle_fallback(tab, pd.Timestamp(day), orig_close)
    return px, 3.0, "SETTLE", f"settle:{how}"


def bull_pnl(a_e, a_x, o_e, o_x, s_ae, s_ax, s_oe, s_ox):
    """Bull-call debit vertical, rupee points/share.
    LONG ATM: BUY entry a_e (slip adds), SELL exit a_x (slip subtracts).
    SHORT OTM: SELL entry o_e (slip subtracts), BUY-back exit o_x (slip adds)."""
    return a_x * (1 - s_ax) - a_e * (1 + s_ae) + o_e * (1 - s_oe) - o_x * (1 + s_ox)


def naked_long_pnl(a_e, a_x, s_ae, s_ax):
    """Naked LONG ATM call: BUY entry / SELL exit (directional-beta reference)."""
    return a_x * (1 - s_ax) - a_e * (1 + s_ae)


def statutory_bull(a_e, a_x, o_e, o_x):
    """Rupee-points/share statutory. Sells = OTM entry + ATM exit. Buys = ATM entry + OTM exit."""
    stt = 0.001 * (o_e + a_x)                     # 0.1% premium, sell side
    exch = 0.00035 * (a_e + a_x + o_e + o_x)      # 0.035% premium, all legs
    gst = 0.18 * exch                             # 18% on exchange txn
    stamp = 0.00003 * (a_e + o_x)                 # 0.003% premium, buy side
    return stt + exch + gst + stamp


def statutory_naked_long(a_e, a_x):
    stt = 0.001 * a_x            # sell at exit
    exch = 0.00035 * (a_e + a_x)
    gst = 0.18 * exch
    stamp = 0.00003 * a_e        # buy at entry
    return stt + exch + gst + stamp


def get_spot(sym, day, atm_strike):
    if STOCK is not None and sym in STOCK.columns:
        s = STOCK[sym].dropna()
        v = s.asof(pd.Timestamp(day))
        if np.isfinite(v) and v > 0:
            return float(v)
    return float(atm_strike)  # ATM strike ~ spot fallback


def process(row) -> dict:
    sym = row["sym"]
    m1_exp = dt.date.fromisoformat(str(row["m1_exp"])[:10])
    ca_D = dt.date.fromisoformat(str(row["ca_D"])[:10])
    atm_strike = float(row["ca_strike"])          # LONG leg
    day_iso = ca_D.isoformat()
    period = row["period"]
    spot = get_spot(sym, ca_D, atm_strike)

    rec = dict(sym=sym, m1_exp=m1_exp.isoformat(), ca_D=day_iso, period=period,
               ca_ff=float(row["ca_ff"]), atm_strike=atm_strike, spot=spot,
               regime="POST_2025-09" if ca_D >= SPLIT_REGIME else "PRE_2025-09")

    front = fa.load_file(sym, pd.Timestamp(m1_exp))
    if front is None:
        rec.update(status="front_file_missing", dropped=True, drop_reason="front_file_missing")
        return rec
    tdays1 = sorted(pd.to_datetime(front["trading_day"].unique()))
    sessions = [d.date() for d in tdays1]
    ce_strikes = set(front.loc[front["option_type"] == "CE", "strike"].astype(float))
    if atm_strike not in ce_strikes:
        rec.update(status="atm_strike_absent", dropped=True, drop_reason="atm_strike_absent")
        return rec

    exit_day = exit_day_for(ca_D, m1_exp, tdays1)
    if exit_day is None:
        rec.update(status="no_exit_day", dropped=True, drop_reason="no_exit_day")
        return rec
    rec["exit_day"] = exit_day.isoformat()
    rec["spot_exit"] = get_spot(sym, exit_day, atm_strike)
    rec["und_ret_pct"] = 100.0 * (rec["spot_exit"] / spot - 1.0) if spot > 0 else np.nan

    # ---- SHORT-OTM STRIKE (ex-ante, trailing-5 median vol > 0, pick MOST LIQUID within OTM1..6) ----
    strikes = sorted(front.loc[front["option_type"] == "CE", "strike"].astype(float).unique())
    higher = [k for k in strikes if k > atm_strike][:MAX_DIST]
    cands = []
    for d, k in enumerate(higher, start=1):
        tab = fa.day_table(front, k)
        med5 = trailing_median_vol(tab, day_iso, TRAIL)
        if np.isfinite(med5) and med5 > 0:
            cands.append((med5, d, k, tab))
    if not cands:
        rec.update(status="ok", dropped=True, drop_reason="no_otm_strike_ex_ante",
                   n_otm_avail=len(higher))
        return rec
    med5, otm_dist, otm_strike, otm_tab = max(cands, key=lambda t: t[0])  # MOST liquid
    rec.update(otm_strike=otm_strike, otm_dist=otm_dist, otm_med5=med5,
               n_otm_cands=len(cands), strike_width=otm_strike - atm_strike)

    atm_tab = fa.day_table(front, atm_strike)

    # ---- ENTRY FILL: D+1 (defer one session); BOTH legs tradeable same day ----
    d1 = next_session(sessions, ca_D)
    d2 = next_session(sessions, d1) if d1 is not None else None
    fill_day = ev_a = ev_o = None
    for cand in (d1, d2):
        if cand is None:
            continue
        ea = fa.leg_eval(atm_tab, pd.Timestamp(cand))
        eo = fa.leg_eval(otm_tab, pd.Timestamp(cand))
        if ea["tier"] != "UNTRADED" and eo["tier"] != "UNTRADED":
            fill_day, ev_a, ev_o = cand, ea, eo
            break
    if fill_day is None:
        rec.update(status="ok", dropped=True, drop_reason="entry_untraded_D1_D2")
        return rec

    a_e, o_e = ev_a["close"], ev_o["close"]        # ATM(long)/OTM(short) ENTRY premia
    m_ae, m_oe = ev_a["mult"] or 1.0, ev_o["mult"] or 1.0
    rec.update(fill_day=fill_day.isoformat(), tier_ae=ev_a["tier"], tier_oe=ev_o["tier"],
               a_e=a_e, o_e=o_e, vol_ae=ev_a["volume"], vol_oe=ev_o["volume"])

    # ---- EXIT FILL ----
    a_x, m_ax, tier_ax, note_ax = resolve_exit(atm_tab, exit_day, ds.price_asof(front, atm_strike, "CE", pd.Timestamp(exit_day)))
    o_x, m_ox, tier_ox, note_ox = resolve_exit(otm_tab, exit_day, ds.price_asof(front, otm_strike, "CE", pd.Timestamp(exit_day)))
    rec.update(a_x=a_x, o_x=o_x, tier_ax=tier_ax, tier_ox=tier_ox, note_ax=note_ax, note_ox=note_ox)

    if not all(np.isfinite(x) and x > 0 for x in (a_e, o_e, a_x, o_x)):
        rec.update(status="ok", dropped=True, drop_reason="nonpos_price")
        return rec

    net_credit = o_e - a_e                          # NEGATIVE => net DEBIT (bull-call)
    rec["net_credit"] = net_credit                  # sign convention: credit +, debit -
    rec["net_debit"] = a_e - o_e
    rec["dropped"] = False
    rec["status"] = "ok"

    # ---- P&L (rupee points/share) ----
    stat_v = statutory_bull(a_e, a_x, o_e, o_x)
    stat_n = statutory_naked_long(a_e, a_x)
    for scale, tag in ((0, "friction0"), (1, "1x"), (2, "2x")):
        pv = bull_pnl(a_e, a_x, o_e, o_x, BASE_SLIP * m_ae * scale, BASE_SLIP * m_ax * scale,
                      BASE_SLIP * m_oe * scale, BASE_SLIP * m_ox * scale)
        pn = naked_long_pnl(a_e, a_x, BASE_SLIP * m_ae * scale, BASE_SLIP * m_ax * scale)
        rec[f"vert_slip_{tag}"] = pv                       # slippage-only
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
    f = df[(df["dropped"] == False) & df[pct_col].notna()].copy()  # noqa: E712
    if len(f) < 8:
        return dict(n=len(f), pertrade_sharpe=None, ann_sharpe_pertrade=None, ann_sharpe_monthly=None)
    r = f[pct_col] / 100.0
    mu, sd = r.mean(), r.std(ddof=1)
    span_yrs = max((pd.to_datetime(f["ca_D"]).max() - pd.to_datetime(f["ca_D"]).min()).days / 365.25, 1e-6)
    tpy = len(f) / span_yrs
    pertrade = mu / sd if sd > 0 else np.nan
    ann_pt = pertrade * np.sqrt(tpy) if np.isfinite(pertrade) else np.nan
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
    print(f"[checkpoint] {len(sig)} FF signals loaded", flush=True)

    recs = []
    for i, row in sig.iterrows():
        recs.append(process(row))
        if (i + 1) % 100 == 0:
            pd.DataFrame(recs).to_csv(OUT / "per_trade_reversed.csv", index=False)
            nd = sum(r.get("dropped", True) for r in recs)
            print(f"[checkpoint] {i+1}/{len(sig)} | dropped={nd}", flush=True)

    out = pd.DataFrame(recs)
    out.to_csv(OUT / "per_trade_reversed.csv", index=False)
    print(f"[checkpoint] wrote per_trade_reversed.csv rows={len(out)}", flush=True)

    result = {"structure": "BULL-CALL DEBIT (SELL OTM / BUY ATM, near-month, same expiry)",
              "n_signals": len(out),
              "n_dropped": int(out["dropped"].sum()),
              "drop_rate": float(out["dropped"].mean()),
              "drop_reasons": out.loc[out["dropped"] == True, "drop_reason"].value_counts().to_dict()}  # noqa: E712

    filled = out[out["dropped"] == False]  # noqa: E712
    result["net_credit_mean"] = float(filled["net_credit"].mean())   # negative => debit
    result["net_debit_mean"] = float(filled["net_debit"].mean())
    result["pct_debit_trades"] = float((filled["net_credit"] < 0).mean())
    result["mean_strike_width"] = float(filled["strike_width"].mean())
    result["mean_otm_dist"] = float(filled["otm_dist"].mean())
    result["und_ret_pct_mean"] = float(filled["und_ret_pct"].mean())
    # directional-beta diagnostic: correlation of spread P&L with underlying move
    result["corr_vertnet1x_undret"] = float(filled["vert_net_1x"].corr(filled["und_ret_pct"]))
    result["corr_nakedlong1x_undret"] = float(filled["naked_net_1x"].corr(filled["und_ret_pct"]))

    cohorts = {"FULL": out, "BUILD": out[out["period"] == "BUILD"], "FWD": out[out["period"] == "FWD"],
               "REGIME_PRE_2025-09": out[out["regime"] == "PRE_2025-09"],
               "REGIME_POST_2025-09": out[out["regime"] == "POST_2025-09"]}

    print("\n===== BULL-CALL DEBIT (REVERSED) : slippage+statutory, %-of-spot =====", flush=True)
    tables = {}
    for name, df in cohorts.items():
        blk = {"vert_net_1x_rs": agg_block(df, "vert_net_1x", f"{name} vert net 1x"),
               "vert_net_2x_rs": agg_block(df, "vert_net_2x", f"{name} vert net 2x"),
               "vert_slip_friction0_rs": agg_block(df, "vert_slip_friction0", f"{name} vert friction0"),
               "vert_pct_1x": agg_block(df, "vert_pctspot_1x", f"{name} vert %spot 1x"),
               "vert_pct_2x": agg_block(df, "vert_pctspot_2x", f"{name} vert %spot 2x"),
               "naked_long_net_1x_rs": agg_block(df, "naked_net_1x", f"{name} nakedlong net 1x"),
               "naked_long_pct_1x": agg_block(df, "naked_pctspot_1x", f"{name} nakedlong %spot 1x"),
               "sharpe_pct_1x": sharpe_stats(df, "vert_pctspot_1x")}
        tables[name] = blk
        v1, v2 = blk["vert_net_1x_rs"], blk["vert_net_2x_rs"]
        p1 = blk["vert_pct_1x"]; sh = blk["sharpe_pct_1x"]
        print(f"  {name:20s} n_fill={v1.get('n_filled',0):4d}/{len(df):4d} "
              f"| Rs 1x={v1.get('mean_rs',0):+.3f} 2x={v2.get('mean_rs',0):+.3f} "
              f"| %spot 1x={p1.get('mean_rs',0):+.4f} "
              f"| win={v1.get('win',0):.3f} PF={v1.get('pf',0):.2f} "
              f"| annSharpe(pt)={sh.get('ann_sharpe_pertrade')}", flush=True)

    out["yr"] = pd.to_datetime(out["ca_D"]).dt.year
    peryear = {}
    print("\n===== PER-YEAR (entry year) vert net 1x =====", flush=True)
    for yr, g in out.groupby("yr"):
        b = agg_block(g, "vert_net_1x", str(yr))
        bp = agg_block(g, "vert_pctspot_1x", str(yr))
        peryear[int(yr)] = {"n_fill": b.get("n_filled", 0), "mean_rs": b.get("mean_rs"),
                            "mean_pctspot": bp.get("mean_rs"), "win": b.get("win")}
        print(f"  {yr}  n_fill={b.get('n_filled',0):4d}  Rs={b.get('mean_rs',0):+.3f}  "
              f"%spot={bp.get('mean_rs',0):+.4f}  win={b.get('win',0):.3f}", flush=True)

    result["tables"] = tables
    result["per_year"] = peryear
    with open(OUT / "summary_reversed.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)
    print("\n[done] summary_reversed.json written", flush=True)
    print(f"[diag] net_credit_mean={result['net_credit_mean']:+.3f} (neg=DEBIT) "
          f"| und_ret_pct_mean={result['und_ret_pct_mean']:+.3f} "
          f"| corr(vert,undret)={result['corr_vertnet1x_undret']:+.3f}", flush=True)


if __name__ == "__main__":
    main()
