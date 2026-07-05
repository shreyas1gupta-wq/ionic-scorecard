"""K-012 RESURRECTION -- FINAL EVIDENCE LEG: v3 CAUSAL re-test.
Owner: Arjun Rao (Head of Quant). Date: 2026-07-05.
PRE-REGISTERED SINGLE RUN. The spec below is FROZEN -- no parameter is tuned after seeing
results. If it fails, it fails.

FROZEN SPEC v3
1. CAUSAL ENTRY: per expiry cycle, walk lead days in CALENDAR order
   (30->25->20->15->12 sessions before front expiry). Signal fires on the FIRST day D where
   FF >= 0.25, computed from data available at D's close (FF via ds.atm_iv_asof, the SAME pricer
   that built forward_factor_v2.parquet; the causal fix is the ENTRY RULE = first-cross, NOT
   argmax/peak-picking). No window peeking.
2. EX-ANTE LIQUIDITY GATE at D: back-leg (2nd-fwd-month) CE volume>0 on day D (known at D close).
   If gate fails at D, cycle may still signal at a LATER lead where FF>=0.25 AND gate passes.
3. FILLS at D+1 (T3 same-bar rule): both legs filled at the D+1 session's day_table close.
   If back leg untraded at D+1: defer ONE session; still untraded -> DROP (log). Exit = front
   expiry as in v2 (2 sessions before m1 expiry); exit-leg fills volume-checked with Tara's
   find_defer / settle_fallback convention.
4. SIZING (canonical, THE reference formula): qty = min(100 / CE_be, 6.0),
   CE_be = back-leg entry premium actually PAID at D+1 (raw, pre-slippage; slippage applied in pnl).
5. COSTS: Tara's tiered slippage per leg on BASE=0.015: ratio>=0.5 -> 1x, 0.2-0.5 -> 2x,
   <0.2 -> 3x (fill-day volume vs trailing-20-session PIT median of that contract).

DECOMPOSITION LADDER (all CAUSAL entries; only frictions differ), FORWARD cohort:
  (a) v3 causal frictionless NO-GATE  (entry=first FF>=0.25; day_table fills, NO drops, ZERO slip)
  (b) v3 causal GATED, zero slippage  (entry=first FF>=0.25 & gate; honest fills w/ drops; ZERO slip)
  (c) v3 causal GATED + tiered slip   (THE VERDICT NUMBER); also (c) at 2x slippage stress.
  Isolations: (a)->(b) = fill-rate cost; (b)->(c) = slippage cost.
  T9 leak cost = argmax vs causal on a FIXED cohort, matched pricer/slip (anchors, see report).

REUSES Tara's fill_audit loaders verbatim (load_file/day_table/classify/leg_eval/find_defer/
settle_fallback/build_slice) and the dispersion_strategy pricer. Legacy folders read-only.

HARD RULE: rupee points + per-Rs100-deployed only; NEVER pnl/back-premium.
Primary metric = flat-100 mean of pnl100 (drops counted as 0), matching Tara's +3.88 / +10.04
convention; deploy-weighted ratio-of-sums reported alongside.
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
import fill_audit as fa           # noqa: E402  (reuse loaders + build_slice)
import dispersion_strategy as ds  # noqa: E402  (_series/_nearest/atm_iv_asof/price_asof/SOPT)
from forward_factor_strategy import forward_vol  # noqa: E402

OUT = ROOT / "results/S-03/20260705_resurrection"
SOPT = ds.SOPT

LEADS = [30, 25, 20, 15, 12]         # calendar order: earliest (30 sess pre-exp) -> latest (12)
FF_MIN = 0.25
CAP = 6.0                            # qty = min(100/CE_be, 6.0) -- PINNED (not recomputed; no lookahead)
BASE_SLIP = fa.BASE_SLIP             # 0.015
SPLIT = dt.date(2024, 12, 31)        # build/forward split on ENTRY date (matches all prior legs)

_exps_cache: dict[str, list] = {}


def sym_expiries(sym: str) -> list:
    if sym not in _exps_cache:
        _exps_cache[sym] = sorted(dt.date.fromisoformat(p.stem) for p in (SOPT / sym).glob("*.parquet"))
    return _exps_cache[sym]


def ff_grid(cser, d1, d2, m1_exp, m2_exp, tdays1, tdays2):
    """Recompute FF at EACH lead in calendar order (30->12). Returns list of dicts (ascending D)."""
    m2_start = tdays2[0].date()
    grid = []
    for lead in LEADS:
        if lead + 1 >= len(tdays1):
            continue
        cand = max(tdays1[-lead - 1].date(), m2_start)
        if cand >= m1_exp:
            continue
        spot = cser.asof(pd.Timestamp(cand))
        if not np.isfinite(spot):
            continue
        iv1 = ds.atm_iv_asof(d1, spot, cand, m1_exp)
        iv2 = ds.atm_iv_asof(d2, spot, cand, m2_exp)
        if iv1 is None or iv2 is None:
            continue
        T1 = max((m1_exp - cand).days / 365.0, 1e-4)
        T2 = max((m2_exp - cand).days / 365.0, 1e-4)
        fv = forward_vol(iv1, T1, iv2, T2)
        if not fv or fv <= 0:
            continue
        ff = (iv1 - fv) / fv
        common = sorted(set(d1["strike"].unique()) & set(d2["strike"].unique()))
        if not common:
            continue
        k = min(common, key=lambda x: abs(x - spot))
        grid.append(dict(lead=lead, D=cand, ff=float(ff), spot=float(spot), strike=float(k)))
    return grid


def exit_day_for(entry_date, m1_exp, tdays1):
    ex = [d.date() for d in tdays1 if entry_date < d.date() < m1_exp]
    return ex[-2] if len(ex) >= 2 else None


def next_session(sessions, day):
    fut = [d for d in sessions if d > day]
    return fut[0] if fut else None


def ds_price(df, k, day):
    """v2-style CE leg price (bidirectional nearest, max_stale=15). NaN-safe."""
    return ds.price_asof(df, k, "CE", pd.Timestamp(day))


def dt_close_nearest(tab, day_iso):
    """Frictionless fill: day_table close at day_iso, else nearest available close (for rung a)."""
    if day_iso in tab.index and np.isfinite(tab.loc[day_iso, "close"]):
        return float(tab.loc[day_iso, "close"])
    idx = tab.index.tolist()
    if not idx:
        return np.nan
    td = dt.date.fromisoformat(day_iso)
    best = min(idx, key=lambda d: abs((dt.date.fromisoformat(d) - td).days))
    v = tab.loc[best, "close"]
    return float(v) if np.isfinite(v) else np.nan


def pnl_unit(fe, be, fx, bx, s_fe, s_be, s_fx, s_bx):
    """CE calendar: sell front @entry / buy back @entry ; buy front @exit / sell back @exit."""
    return fe * (1 - s_fe) - be * (1 + s_be) - fx * (1 + s_fx) + bx * (1 - s_bx)


def qcap(be):
    return min(100.0 / be, CAP) if (be and np.isfinite(be) and be > 0) else np.nan


def process(row) -> dict:
    sym = row["sym"]
    m1_exp = row["m1_exp"].date() if hasattr(row["m1_exp"], "date") else row["m1_exp"]
    exps = sym_expiries(sym)
    rec = dict(sym=sym, m1_exp=m1_exp.isoformat(),
               st_entry=row["entry"].date().isoformat(), st_ff=float(row["ff"]),
               st_strike=float(row["strike"]),
               st_ce_fe=float(row["CE_fe"]), st_ce_be=float(row["CE_be"]),
               st_ce_fx=float(row["CE_fx"]), st_ce_bx=float(row["CE_bx"]))
    if m1_exp not in exps:
        rec.update(status="m1_not_in_exps"); return rec
    idx = exps.index(m1_exp)
    if idx + 1 >= len(exps):
        rec.update(status="no_m2"); return rec
    m2_exp = exps[idx + 1]
    rec["m2_exp"] = m2_exp.isoformat()

    front = fa.load_file(sym, pd.Timestamp(m1_exp))
    back = fa.load_file(sym, pd.Timestamp(m2_exp))
    if front is None or back is None:
        rec.update(status="file_missing"); return rec
    cser = STOCK[sym].dropna() if sym in STOCK.columns else None
    if cser is None:
        rec.update(status="no_stock_close"); return rec
    tdays1 = sorted(pd.to_datetime(front["trading_day"].unique()))
    tdays2 = sorted(pd.to_datetime(back["trading_day"].unique()))
    if len(tdays1) < 12 or not tdays2:
        rec.update(status="short_series"); return rec
    sessions = [d.date() for d in tdays1]

    grid = ff_grid(cser, front, back, m1_exp, m2_exp, tdays1, tdays2)
    rec["n_leads"] = len(grid)
    if not grid:
        rec.update(status="no_valid_lead"); return rec
    max_ff = max(g["ff"] for g in grid)
    rec["max_ff"] = float(max_ff)
    rec["signal"] = bool(max_ff >= FF_MIN)

    # ---- ARGMAX (engine reproduction of v2) ----
    am = max(grid, key=lambda g: g["ff"])
    am_exit = exit_day_for(am["D"], m1_exp, tdays1)
    rec.update(am_lead=am["lead"], am_D=am["D"].isoformat(), am_ff=am["ff"], am_strike=am["strike"])
    if am_exit is not None:
        am_fe = ds_price(front, am["strike"], am["D"]); am_be = ds_price(back, am["strike"], am["D"])
        am_fx = ds_price(front, am["strike"], am_exit); am_bx = ds_price(back, am["strike"], am_exit)
        rec.update(am_ce_fe=am_fe, am_ce_be=am_be, am_ce_fx=am_fx, am_ce_bx=am_bx,
                   am_exit=am_exit.isoformat())
        # xcheck vs stored (same strike + prices ~ same day => engine == v2)
        rec["am_strike_match"] = abs(am["strike"] - row["strike"]) < 1e-6
        rec["am_px_match"] = all(np.isfinite(x) and abs(x - y) < 0.01 for x, y in
                                 [(am_fe, row["CE_fe"]), (am_be, row["CE_be"]),
                                  (am_fx, row["CE_fx"]), (am_bx, row["CE_bx"])])
        if all(np.isfinite(x) and x > 0 for x in (am_fe, am_be, am_fx, am_bx)):
            q = qcap(am_be)
            rec["am_pnl100_flat"] = pnl_unit(am_fe, am_be, am_fx, am_bx,
                                             BASE_SLIP, BASE_SLIP, BASE_SLIP, BASE_SLIP) * q
            rec["am_pnl100_zero"] = pnl_unit(am_fe, am_be, am_fx, am_bx, 0, 0, 0, 0) * q
            rec["am_deploy"] = q * am_be

    if not rec["signal"]:
        rec.update(status="no_signal_recomputed"); return rec

    # ---- CAUSAL (first FF>=0.25 in calendar order) ----
    ca = next(g for g in grid if g["ff"] >= FF_MIN)
    ca_exit = exit_day_for(ca["D"], m1_exp, tdays1)
    rec.update(ca_lead=ca["lead"], ca_D=ca["D"].isoformat(), ca_ff=ca["ff"], ca_strike=ca["strike"])
    back_tab_ca = fa.day_table(back, ca["strike"])
    ev_gate = fa.leg_eval(back_tab_ca, pd.Timestamp(ca["D"]))
    rec["ca_gatepass"] = bool(ev_gate["volume"] > 0)
    rec["period"] = "FWD" if ca["D"] > SPLIT else "BUILD"   # cohort by causal entry date

    if ca_exit is None:
        rec.update(status="no_exit_day"); return rec

    # A3 anchor: causal entry, ds pricer, flat & zero slip (matched-pricer T9 isolation)
    ca_fe_ds = ds_price(front, ca["strike"], ca["D"]); ca_be_ds = ds_price(back, ca["strike"], ca["D"])
    ca_fx_ds = ds_price(front, ca["strike"], ca_exit); ca_bx_ds = ds_price(back, ca["strike"], ca_exit)
    if all(np.isfinite(x) and x > 0 for x in (ca_fe_ds, ca_be_ds, ca_fx_ds, ca_bx_ds)):
        q = qcap(ca_be_ds)
        rec["ca_pnl100_flat"] = pnl_unit(ca_fe_ds, ca_be_ds, ca_fx_ds, ca_bx_ds,
                                         BASE_SLIP, BASE_SLIP, BASE_SLIP, BASE_SLIP) * q
        rec["ca_pnl100_zero"] = pnl_unit(ca_fe_ds, ca_be_ds, ca_fx_ds, ca_bx_ds, 0, 0, 0, 0) * q
    # argmax on THIS cohort with ds pricer (for T9 vs causal, same cohort) already in am_pnl100_*

    front_tab_ca = fa.day_table(front, ca["strike"])
    # ---- RUNG (a): frictionless no-gate, day_table D+1 fills, no drops, zero slip ----
    d1_sess = next_session(sessions, ca["D"])
    if d1_sess is not None:
        d1_iso = d1_sess.isoformat(); ex_iso = ca_exit.isoformat()
        a_fe = dt_close_nearest(front_tab_ca, d1_iso); a_be = dt_close_nearest(back_tab_ca, d1_iso)
        a_fx = dt_close_nearest(front_tab_ca, ex_iso); a_bx = dt_close_nearest(back_tab_ca, ex_iso)
        if all(np.isfinite(x) and x > 0 for x in (a_fe, a_be, a_fx, a_bx)):
            q = qcap(a_be)
            rec.update(a_fe=a_fe, a_be=a_be, a_fx=a_fx, a_bx=a_bx, a_d1=d1_iso,
                       a_pnl100=pnl_unit(a_fe, a_be, a_fx, a_bx, 0, 0, 0, 0) * q,
                       a_deploy=q * a_be, a_ok=True)
        else:
            rec["a_ok"] = False
    else:
        rec["a_ok"] = False

    # ---- GATED entry: first lead FF>=0.25 AND back-leg CE vol>0 at D ----
    gated = None
    for g in grid:
        if g["ff"] < FF_MIN:
            continue
        bt = fa.day_table(back, g["strike"])
        ev = fa.leg_eval(bt, pd.Timestamp(g["D"]))
        if ev["volume"] > 0:
            gated = (g, bt); break
    if gated is None:
        rec.update(ga_exists=False, b_dropped=True, b_drop_reason="no_gated_lead")
        rec.update(status="ok"); return rec
    g, back_tab_g = gated
    g_exit = exit_day_for(g["D"], m1_exp, tdays1)
    front_tab_g = fa.day_table(front, g["strike"])
    rec.update(ga_exists=True, ga_lead=g["lead"], ga_D=g["D"].isoformat(),
               ga_ff=g["ff"], ga_strike=g["strike"])
    if g_exit is None:
        rec.update(b_dropped=True, b_drop_reason="no_exit_day", status="ok"); return rec

    # ---- RUNGS (b)/(c): honest fills for the GATED entry ----
    # entry fill day = D+1 session; if back untraded, defer one session; else drop
    gd1 = next_session(sessions, g["D"])
    gd2 = next_session(sessions, gd1) if gd1 is not None else None
    chosen = None
    for cand_day in (gd1, gd2):
        if cand_day is None:
            continue
        ev_be = fa.leg_eval(back_tab_g, pd.Timestamp(cand_day))
        ev_fe = fa.leg_eval(front_tab_g, pd.Timestamp(cand_day))
        if ev_be["tier"] != "UNTRADED" and ev_fe["tier"] != "UNTRADED":
            chosen = (cand_day, ev_fe, ev_be); break
        if cand_day is gd1 and ev_be["tier"] != "UNTRADED":
            # front untraded at D+1 but back ok -> still try defer (rare)
            continue
    if chosen is None:
        # determine reason
        rec.update(b_dropped=True,
                   b_drop_reason="entry_untraded_D1_D2",
                   status="ok"); return rec
    fill_day, ev_fe, ev_be = chosen
    rec.update(b_dropped=False, b_fill_day=fill_day.isoformat(),
               tier_fe=ev_fe["tier"], tier_be=ev_be["tier"],
               vol_fe=ev_fe["volume"], vol_be=ev_be["volume"])
    fe_px, be_px = ev_fe["close"], ev_be["close"]

    # exit legs: same_day, else defer (Tara find_defer), else settle_fallback (Tara)
    def resolve_exit(tab, day, orig_close):
        ev = fa.leg_eval(tab, pd.Timestamp(day))
        if ev["tier"] != "UNTRADED":
            return ev["close"], ev["mult"], ev["tier"], "same_day"
        d = fa.find_defer(tab, pd.Timestamp(day))
        if d is not None:
            return d["close"], d["mult"], d["tier"], f"deferred_{d['sessions_deferred']}"
        px, how = fa.settle_fallback(tab, pd.Timestamp(day), orig_close)
        return px, 3.0, "SETTLE", f"settle:{how}"

    fx_px, m_fx, tier_fx, note_fx = resolve_exit(front_tab_g, g_exit, ds_price(front, g["strike"], g_exit))
    bx_px, m_bx, tier_bx, note_bx = resolve_exit(back_tab_g, g_exit, ds_price(back, g["strike"], g_exit))
    rec.update(tier_fx=tier_fx, tier_bx=tier_bx, exit_note_f=note_fx, exit_note_b=note_bx)

    if not all(np.isfinite(x) and x > 0 for x in (fe_px, be_px, fx_px, bx_px)):
        rec.update(b_dropped=True, b_drop_reason="nonpos_price", status="ok"); return rec

    q = qcap(be_px)
    rec["b_qty_capped"] = q; rec["b_deploy"] = q * be_px; rec["b_ce_be"] = be_px
    m_fe, m_be = ev_fe["mult"] or 1.0, ev_be["mult"] or 1.0
    # (b) zero slip
    rec["b_pnl100"] = pnl_unit(fe_px, be_px, fx_px, bx_px, 0, 0, 0, 0) * q
    # (c) tiered 1x
    rec["c1_pnl100"] = pnl_unit(fe_px, be_px, fx_px, bx_px,
                                BASE_SLIP * m_fe, BASE_SLIP * m_be,
                                BASE_SLIP * m_fx, BASE_SLIP * m_bx) * q
    # (c) tiered 2x stress
    rec["c2_pnl100"] = pnl_unit(fe_px, be_px, fx_px, bx_px,
                                2 * BASE_SLIP * m_fe, 2 * BASE_SLIP * m_be,
                                2 * BASE_SLIP * m_fx, 2 * BASE_SLIP * m_bx) * q
    rec["status"] = "ok"
    return rec


STOCK = None


def main():
    global STOCK
    print("[checkpoint] loading stock_close ...", flush=True)
    STOCK = ds.stock_close()
    S, cap = fa.build_slice()
    print(f"[checkpoint] slice n={len(S)} syms={S['sym'].nunique()} cap_qty={cap}", flush=True)

    recs = []
    for i, row in S.iterrows():
        recs.append(process(row))
        if (i + 1) % 50 == 0:
            done = pd.DataFrame(recs)
            nsig = int(done.get("signal", pd.Series(dtype=bool)).sum())
            print(f"[checkpoint] {i+1}/{len(S)} processed | signals={nsig}", flush=True)
            done.to_csv(OUT / "causal_per_trade.csv", index=False)

    out = pd.DataFrame(recs)
    out.to_csv(OUT / "causal_per_trade.csv", index=False)
    print(f"[checkpoint] wrote causal_per_trade.csv rows={len(out)}", flush=True)

    # ---------- engine validation: recomputed argmax vs stored parquet ----------
    v = out[out["am_px_match"].notna()]
    print(f"\n[VALIDATION] engine-vs-v2 argmax: strike_match={v['am_strike_match'].mean():.3f} "
          f"price_match(<0.01)={v['am_px_match'].mean():.3f} over n={len(v)}", flush=True)
    sig = out[out["signal"] == True]  # noqa: E712
    print(f"[VALIDATION] recomputed signals (max_ff>=0.25): {len(sig)}/{len(out)} of stored 673 slice", flush=True)

    def agg(df, col, deploycol=None):
        s = df[col].fillna(0.0)
        flat = s.mean()
        dw = np.nan
        if deploycol is not None and deploycol in df.columns:
            num = s.sum(); den = df[deploycol].fillna(0.0).sum()
            dw = 100.0 * num / den if den > 0 else np.nan
        return flat, dw, int((df[col].notna()).sum())

    def block(df, tag):
        n = len(df)
        # cohort counts
        n_a = int(df["a_ok"].fillna(False).sum()) if "a_ok" in df.columns else 0
        n_b = int((df.get("b_dropped", pd.Series([True] * n, index=df.index)) == False).sum())  # noqa: E712
        a_flat, a_dw, _ = agg(df, "a_pnl100", "a_deploy")
        b_flat, b_dw, _ = agg(df, "b_pnl100", "b_deploy")
        c1_flat, c1_dw, _ = agg(df, "c1_pnl100", "b_deploy")
        c2_flat, c2_dw, _ = agg(df, "c2_pnl100", "b_deploy")
        am_flat, am_dw, _ = agg(df, "am_pnl100_flat", "am_deploy")
        amz_flat, _, _ = agg(df, "am_pnl100_zero", "am_deploy")
        ca_flat, _, _ = agg(df, "ca_pnl100_flat")
        caz_flat, _, _ = agg(df, "ca_pnl100_zero")
        print(f"\n===== COHORT {tag}: n_signals={n} | filled(a)={n_a} filled(b/c)={n_b} =====", flush=True)
        print(f"  ANCHORS (ds pricer, cohort={tag}):", flush=True)
        print(f"    argmax flat-1.5% : flat100={am_flat:+.2f}  (this cohort's argmax; A1 uses argmax-fwd)", flush=True)
        print(f"    argmax zero-slip : flat100={amz_flat:+.2f}", flush=True)
        print(f"    causal flat-1.5% : flat100={ca_flat:+.2f}   <- A3", flush=True)
        print(f"    causal zero-slip : flat100={caz_flat:+.2f}", flush=True)
        print(f"    => T9 leak (argmax-causal, flat-1.5%, same cohort) = {am_flat - ca_flat:+.2f}", flush=True)
        print(f"  LADDER (day_table fills, drops->0):", flush=True)
        print(f"    (a) causal frictionless no-gate : flat100={a_flat:+.2f}  deploy_wtd={a_dw:+.2f}", flush=True)
        print(f"    (b) causal gated zero-slip      : flat100={b_flat:+.2f}  deploy_wtd={b_dw:+.2f}", flush=True)
        print(f"    (c) causal gated tiered 1x      : flat100={c1_flat:+.2f}  deploy_wtd={c1_dw:+.2f}  <== VERDICT", flush=True)
        print(f"    (c) causal gated tiered 2x      : flat100={c2_flat:+.2f}  deploy_wtd={c2_dw:+.2f}  <== STRESS", flush=True)
        print(f"    fill-rate cost (a->b) = {b_flat - a_flat:+.2f} | slippage cost (b->c1) = {c1_flat - b_flat:+.2f}", flush=True)
        # trade stats on filled (b/c1)
        filled = df[df.get("b_dropped", True) == False]  # noqa: E712
        if len(filled):
            pf_num = filled.loc[filled["c1_pnl100"] > 0, "c1_pnl100"].sum()
            pf_den = -filled.loc[filled["c1_pnl100"] <= 0, "c1_pnl100"].sum()
            pf = pf_num / pf_den if pf_den > 0 else np.inf
            win = (filled["c1_pnl100"] > 0).mean()
            aw = filled.loc[filled["c1_pnl100"] > 0, "c1_pnl100"].mean()
            al = filled.loc[filled["c1_pnl100"] <= 0, "c1_pnl100"].mean()
            print(f"    (c1 survivors) n={len(filled)} win={win:.3f} PF={pf:.2f} "
                  f"avg_win={aw:+.2f} avg_loss={al:+.2f} worst={filled['c1_pnl100'].min():+.2f}", flush=True)

    sigdf = out[out["signal"] == True].copy()  # noqa: E712
    for tag in ("BUILD", "FWD"):
        block(sigdf[sigdf["period"] == tag], tag)

    # per-year (by causal entry year), VERDICT metric (c1), FWD+BUILD
    sigdf["ca_year"] = pd.to_datetime(sigdf["ca_D"]).dt.year
    print("\n===== PER-YEAR (causal entry year) -- flat100, drops->0 =====", flush=True)
    print(f"  {'year':>6} {'n_sig':>6} {'n_fill':>6} {'(a)':>8} {'(b)':>8} {'(c1)':>8} {'(c2)':>8}", flush=True)
    for yr, grp in sigdf.groupby("ca_year"):
        nf = int((grp.get("b_dropped", True) == False).sum())  # noqa: E712
        print(f"  {yr:>6} {len(grp):>6} {nf:>6} {grp['a_pnl100'].fillna(0).mean():>+8.2f} "
              f"{grp['b_pnl100'].fillna(0).mean():>+8.2f} {grp['c1_pnl100'].fillna(0).mean():>+8.2f} "
              f"{grp['c2_pnl100'].fillna(0).mean():>+8.2f}", flush=True)

    summary = {
        "engine_argmax_price_match": float(v["am_px_match"].mean()),
        "engine_argmax_strike_match": float(v["am_strike_match"].mean()),
        "n_recomputed_signals": int(len(sig)),
        "n_fwd_signals": int((sigdf["period"] == "FWD").sum()),
        "n_build_signals": int((sigdf["period"] == "BUILD").sum()),
    }
    with open(OUT / "causal_run_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    print("\n[done] summary ->", OUT / "causal_run_summary.json", flush=True)


if __name__ == "__main__":
    main()
