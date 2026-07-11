"""G04 Phase-1 triage: OS-01 (weekly short strangle baseline), OS-07 (laddered), OS-10 (monthly roll).
Author: Arjun Rao (quant-head). FAST/CHEAP pass. Costs at 1x COST_STANDARDS.
Edge in RUPEE POINTS (option premium points) + %-of-SPOT. Book P&L at EXIT (Arjun doctrine).
"""
from __future__ import annotations
import sys, json, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyarrow.compute as pc

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
import chain as C  # noqa
import guards as G  # noqa

# ---- lean IO (memory-safe: projected cols + strike predicate pushdown) ----
_LEGCOLS = ["trading_day", "timestamp", "strike", "option_type", "close", "high", "low", "volume"]

def read_legs(path, strikes):
    """Return 1-min bars for only the given strikes (both CE/PE), projected cols."""
    tbl = pq.read_table(path, columns=_LEGCOLS,
                        filters=[("strike", "in", [int(s) for s in strikes])])
    df = tbl.to_pandas()
    if df.empty:
        return df
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df["td"] = [dt.date.fromisoformat(str(x)[:10]) for x in df["trading_day"]]
    return df

_TDAYS = {}
def exp_tdays(path):
    if path in _TDAYS:
        return _TDAYS[path]
    uniq = pc.unique(pq.read_table(path, columns=["trading_day"])["trading_day"]).to_pylist()
    ds = sorted(dt.date.fromisoformat(str(x)[:10]) for x in uniq)
    _TDAYS[path] = ds
    return ds

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/OPT_SWEEP50_PHASE1_20260707/G04_OS07_OS10"
LOT = 75
TICK = 0.05
REGIME_BREAK = dt.date(2025, 9, 1)

# ---------- daily refs ----------
def _daily(path):
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.date
    return df.set_index("date")["close"].sort_index()

NIFTY = _daily(ROOT / "datasets/index_daily/nifty50.parquet")
VIX = _daily(ROOT / "datasets/index_daily/india_vix.parquet")
NDATES = np.array(NIFTY.index)
VDATES = np.array(VIX.index)

def _asof(series, dates, d):
    i = np.searchsorted(dates, d, side="right") - 1
    return float(series.iloc[i]) if i >= 0 else np.nan

def spot_on(d):  # close AT/BEFORE d
    return _asof(NIFTY, NDATES, d)

def vix_prev(d):  # VIX close strictly BEFORE d (PIT at entry morning)
    i = np.searchsorted(VDATES, d, side="left") - 1
    return float(VIX.iloc[i]) if i >= 0 else np.nan

# ---------- cost model (1x) ----------
def leg_cost_rupees(prem, side):
    V = prem * LOT
    broker = 20.0
    exch = 0.00035 * V
    sebi = 1e-6 * V
    gst = 0.18 * (broker + exch + sebi)
    stt = 0.001 * V if side == "sell" else 0.0
    stamp = 0.00003 * V if side == "buy" else 0.0
    slip = max(TICK, 0.0025 * prem) * LOT
    return broker + exch + sebi + gst + stt + stamp + slip

def roundtrip_cost_points(ce_in, pe_in, ce_out, pe_out, charge_exit=True):
    c = leg_cost_rupees(ce_in, "sell") + leg_cost_rupees(pe_in, "sell")
    if charge_exit:
        c += leg_cost_rupees(max(ce_out, TICK), "buy") + leg_cost_rupees(max(pe_out, TICK), "buy")
    return c / LOT  # -> points

# ---------- chain helpers (operate on a pre-read legdf from read_legs) ----------
def leg_daily_frame(df, strike, otype):
    sub = df[(df["strike"] == strike) & (df["option_type"] == otype)]
    if sub.empty:
        return None
    g = sub.groupby("td").agg(close=("close", "last"), high=("high", "max"),
                              low=("low", "min"), vol=("volume", "sum"))
    return g.sort_index()

def entry_quote(df, strike, otype, day, mode):
    sub = df[(df["strike"] == strike) & (df["option_type"] == otype) & (df["td"] == day)]
    if sub.empty:
        return None
    sub = sub.sort_values("t")
    if mode == "close":
        row = sub.iloc[-1]
        return float(row["close"]) if row["close"] > 0 else None
    s2 = sub[(sub["t"].dt.time >= dt.time(9, 20)) & (sub["volume"] > 0)]
    if s2.empty:
        return None
    return float(s2.iloc[0]["close"])

def pick_strikes(spot, vix, cal_dte, k_sd):
    sd = spot * (vix / 100.0) * np.sqrt(cal_dte / 365.0)
    ce = int(round((spot + k_sd * sd) / 50.0) * 50)
    pe = int(round((spot - k_sd * sd) / 50.0) * 50)
    return ce, pe

# ---------- one strangle trade ----------
def sim_trade(exp, entry_day, k_sd, prof=0.5, stop=2.0, mode="morning"):
    """Returns dict or None (dropped: no-fill / missing data)."""
    sp = spot_on(entry_day)
    vx = vix_prev(entry_day)
    if not np.isfinite(sp) or not np.isfinite(vx):
        return None
    cal_dte = (exp - entry_day).days
    if cal_dte < 3:
        return None
    ce_k, pe_k = pick_strikes(sp, vx, cal_dte, k_sd)
    df = read_legs(mapping[exp], [ce_k, pe_k])
    if df.empty:
        return None
    ce_in = entry_quote(df, ce_k, "CE", entry_day, mode)
    pe_in = entry_quote(df, pe_k, "PE", entry_day, mode)
    if ce_in is None or pe_in is None or ce_in <= 0 or pe_in <= 0:
        return None  # no-fill -> DROP
    credit = ce_in + pe_in
    ce_g = leg_daily_frame(df, ce_k, "CE")
    pe_g = leg_daily_frame(df, pe_k, "PE")
    if ce_g is None or pe_g is None:
        return None
    hold_days = [d for d in sorted(set(ce_g.index) | set(pe_g.index)) if d > entry_day and d <= exp]
    exit_val = None; exit_day = None; reason = None
    for d in hold_days:
        ce_c = ce_g["close"].get(d, np.nan)
        pe_c = pe_g["close"].get(d, np.nan)
        if not np.isfinite(ce_c) or not np.isfinite(pe_c):
            continue
        comb = ce_c + pe_c
        if d >= exp:  # expiry -> intrinsic settle
            se = spot_on(exp)
            exit_val = max(0.0, se - ce_k) + max(0.0, pe_k - se)
            exit_day, reason = d, "expiry"; break
        if comb <= prof * credit:
            exit_val, exit_day, reason = comb, d, "profit"; break
        if comb >= stop * credit:
            exit_val, exit_day, reason = comb, d, "stop"; break
    if exit_val is None:  # never resolved -> settle at last available combined
        se = spot_on(exp)
        exit_val = max(0.0, se - ce_k) + max(0.0, pe_k - se)
        exit_day, reason = exp, "expiry_fallback"
    both_otm_exp = reason in ("expiry", "expiry_fallback") and exit_val <= 0.01
    cost = roundtrip_cost_points(ce_in, pe_in,
                                 max(0.0, se - ce_k) if reason.startswith("expiry") else ce_c,
                                 max(0.0, pe_k - se) if reason.startswith("expiry") else pe_c,
                                 charge_exit=not both_otm_exp)
    pnl_pts = credit - exit_val - cost
    return dict(exp=exp, entry=entry_day, exit=exit_day, reason=reason,
                ce_k=ce_k, pe_k=pe_k, spot=sp, vix=vx, credit=credit,
                exit_val=exit_val, cost=cost, pnl_pts=pnl_pts,
                pct_spot=100.0 * pnl_pts / sp, cal_dte=cal_dte,
                regime="pre" if entry_day < REGIME_BREAK else "post")

# ---------- expiry universe ----------
mapping, exps = C.build_expiry_index()

def tdays(exp):
    return exp_tdays(mapping[exp])

def entry_day_for(exp, target_dte):
    ds = tdays(exp)
    cand = [(abs((exp - d).days - target_dte), d) for d in ds if 3 <= (exp - d).days]
    if not cand:
        return None
    return min(cand)[1]

# ---------- run ----------
import os as _os
_LIMIT = int(_os.environ.get("G04_LIMIT", "0"))

def run_series(mode="morning", target_dte=7, k_sd=1.0, which=exps, tag=""):
    trades = []
    ws = which[:_LIMIT] if _LIMIT else which
    for i, e in enumerate(ws):
        ed = entry_day_for(e, target_dte)
        if ed is None:
            continue
        t = sim_trade(e, ed, k_sd, mode=mode)
        if t:
            trades.append(t)
        if i % 25 == 0:
            print(f"  [{tag}] {i}/{len(ws)} exp={e} trades={len(trades)}", flush=True)
    return pd.DataFrame(trades)

def stats(df, ann):
    if df.empty:
        return {}
    p = df["pct_spot"]
    mean_pts = df["pnl_pts"].mean()
    sd = p.std(ddof=1)
    shp_trade = p.mean() / sd if sd > 0 else np.nan
    skey = "exit" if "exit" in df.columns else ("start_exp" if "start_exp" in df.columns else None)
    eq = (df.sort_values(skey) if skey else df)["pct_spot"].cumsum()
    dd = (eq - eq.cummax()).min()
    p05 = np.percentile(p, 5)
    cvar5 = p[p <= p05].mean()
    return dict(N=int(len(df)), mean_pts=round(mean_pts, 2),
                mean_pct_spot=round(p.mean(), 4), median_pct_spot=round(p.median(), 4),
                win=round((df["pnl_pts"] > 0).mean(), 3),
                sharpe_trade=round(shp_trade, 3), sharpe_ann_optimistic=round(shp_trade * np.sqrt(ann), 3),
                worst_pct_spot=round(p.min(), 3), best_pct_spot=round(p.max(), 3),
                p05_pct_spot=round(p05, 3), cvar5_pct_spot=round(cvar5, 3),
                maxDD_cum_pct_spot=round(dd, 3),
                cum_pct_spot=round(p.sum(), 2),
                wl=round((df.loc[df.pnl_pts > 0, "pct_spot"].mean() /
                          abs(df.loc[df.pnl_pts <= 0, "pct_spot"].mean() + 1e-12)), 3))

results = {}

# ===== OS-01 weekly baseline: morning (primary) + close (sensitivity) =====
os01 = run_series(mode="morning", target_dte=7, k_sd=1.0, tag="OS01m")
os01.to_csv(OUT / "os01_trades.csv", index=False)
results["OS01_morning"] = stats(os01, 52)
os01c = run_series(mode="close", target_dte=7, k_sd=1.0, tag="OS01c")
results["OS01_close"] = stats(os01c, 52)
# regime split (morning)
for r in ("pre", "post"):
    results[f"OS01_{r}"] = stats(os01[os01.regime == r], 52)

# ===== OS-07 ladder proxy (EQUAL per-trade size vs OS-01) =====
# DATA CEILING: weekly contracts carry ~10 DTE of life -> a true 3-tenor / 21-DTE
# ladder (3 overlapping weekly vintages) is NOT CONSTRUCTIBLE on this dataset.
# Strongest constructible proxy: enter every weekly expiry at max-available DTE
# (~10) so consecutive vintages overlap ~2-deep (avg ~1.4 live) and entries stagger
# across days/vols. SAME per-trade size as OS-01 -> tail diff reflects staggering,
# not leverage. Compare per-trade left-tail (p05/CVaR5/worst) + cum-equity maxDD.
os07 = run_series(mode="morning", target_dte=10, k_sd=1.0, tag="OS07")
os07.to_csv(OUT / "os07_proxy_trades.csv", index=False)
results["OS07_proxy_10DTE"] = stats(os07, 52)
results["OS01_baseline_7DTE"] = stats(os01, 52)  # same-size comparator
# regime split for OS-07 proxy
for r in ("pre", "post"):
    results[f"OS07_{r}"] = stats(os07[os07.regime == r], 52)

# ===== OS-10 monthly 30-DTE: close vs roll (thin/uneven N) =====
# monthly = last expiry each month with >=28 DTE data available
df_dte = []
for e in exps:
    ds = tdays(e)
    df_dte.append((e, (e - ds[0]).days))
dte_map = dict(df_dte)
monthly = []
seen = set()
for e in sorted(exps):
    ym = (e.year, e.month)
    monthly = [x for x in monthly]  # keep last per month later
# pick last expiry per month among those with >=28 DTE
by_month = {}
for e in sorted(exps):
    if dte_map[e] >= 28:
        by_month[(e.year, e.month)] = e  # last wins
month_exps = sorted(by_month.values())

os10_close = []
for e in month_exps:
    ed = entry_day_for(e, 30)
    if ed is None or dte_map[e] < 28:
        continue
    t = sim_trade(e, ed, k_sd=1.15, prof=0.5, stop=2.0, mode="morning")
    if t:
        os10_close.append(t)
os10_close = pd.DataFrame(os10_close)
if not os10_close.empty:
    os10_close.to_csv(OUT / "os10_close_trades.csv", index=False)
    results["OS10_close"] = stats(os10_close, 12)

# ROLL variant: on breach of a side, close that side & re-open further-out on NEXT
# available monthly (>=28 DTE), keep other side. Book everything at final exit.
def sim_roll(start_exp, entry_day, k_sd=1.15, max_rolls=2):
    sp = spot_on(entry_day); vx = vix_prev(entry_day)
    if not (np.isfinite(sp) and np.isfinite(vx)):
        return None
    cal = (start_exp - entry_day).days
    ce_k, pe_k = pick_strikes(sp, vx, cal, k_sd)
    df = read_legs(mapping[start_exp], [ce_k, pe_k])
    if df.empty:
        return None
    ce_in = entry_quote(df, ce_k, "CE", entry_day, "morning")
    pe_in = entry_quote(df, pe_k, "PE", entry_day, "morning")
    if not ce_in or not pe_in:
        return None
    total_credit = ce_in + pe_in
    total_paid = 0.0
    cost_pts = 0.0
    cur_exp = start_exp; rolls = 0
    ce_live, pe_live = True, True
    cur_ce_k, cur_pe_k = ce_k, pe_k
    cur_ce_in, cur_pe_in = ce_in, pe_in
    while True:
        days = tdays(cur_exp)
        breached = None; bday = None
        for d in [x for x in days if x > entry_day and x <= cur_exp]:
            s = spot_on(d)
            if ce_live and s > cur_ce_k:
                breached, bday = "CE", d; break
            if pe_live and s < cur_pe_k:
                breached, bday = "PE", d; break
        # cost of legs so far (entry)
        # settle un-breached legs at this expiry
        if breached is None or rolls >= max_rolls:
            se = spot_on(cur_exp)
            ce_out = max(0.0, se - cur_ce_k) if ce_live else 0.0
            pe_out = max(0.0, se - cur_pe_k) * 0 + (max(0.0, cur_pe_k - se) if pe_live else 0.0)
            total_paid += ce_out + pe_out
            cost_pts += roundtrip_cost_points(cur_ce_in if ce_live else 0.0,
                                              cur_pe_in if pe_live else 0.0,
                                              ce_out, pe_out,
                                              charge_exit=(ce_out + pe_out) > 0.01)
            break
        # roll breached side out-and-up to next monthly
        nxt = [e for e in month_exps if e > cur_exp]
        if not nxt:  # cannot roll -> close breached side now at intrinsic-ish
            se = spot_on(bday)
            if breached == "CE":
                total_paid += max(0.0, se - cur_ce_k)
            else:
                total_paid += max(0.0, cur_pe_k - se)
            se2 = spot_on(cur_exp)
            total_paid += (max(0.0, se2 - cur_ce_k) if ce_live and breached != "CE" else 0.0)
            total_paid += (max(0.0, cur_pe_k - se2) if pe_live and breached != "PE" else 0.0)
            cost_pts += roundtrip_cost_points(cur_ce_in, cur_pe_in, 0, 0, charge_exit=True)
            break
        ne = nxt[0]
        s = spot_on(bday); vx2 = vix_prev(bday); cal2 = (ne - bday).days
        nce_k, npe_k = pick_strikes(s, vx2, cal2, k_sd)
        dfn = read_legs(mapping[ne], [nce_k, npe_k])
        if breached == "CE":
            close_val = max(0.0, s - cur_ce_k)  # buy back breached CE ~ intrinsic
            new_in = entry_quote(dfn, nce_k, "CE", bday, "morning")
            if not new_in:
                total_paid += close_val; ce_live = False
            else:
                total_paid += close_val
                total_credit += new_in
                cur_ce_k = nce_k; cur_ce_in = new_in
                cur_exp = ne
        else:
            close_val = max(0.0, cur_pe_k - s)
            new_in = entry_quote(dfn, npe_k, "PE", bday, "morning")
            if not new_in:
                total_paid += close_val; pe_live = False
            else:
                total_paid += close_val
                total_credit += new_in
                cur_pe_k = npe_k; cur_pe_in = new_in
                cur_exp = ne
        cost_pts += 2 * leg_cost_rupees(max(close_val, TICK), "buy") / LOT
        rolls += 1
        entry_day = bday
    pnl = total_credit - total_paid - cost_pts
    return dict(start_exp=start_exp, rolls=rolls, credit=total_credit,
                paid=total_paid, cost=cost_pts, pnl_pts=pnl,
                pct_spot=100.0 * pnl / sp, spot=sp,
                regime="pre" if start_exp < REGIME_BREAK else "post")

os10_roll = []
for e in month_exps:
    ed = entry_day_for(e, 30)
    if ed is None:
        continue
    t = sim_roll(e, ed)
    if t:
        os10_roll.append(t)
os10_roll = pd.DataFrame(os10_roll)
if not os10_roll.empty:
    os10_roll.to_csv(OUT / "os10_roll_trades.csv", index=False)
    results["OS10_roll"] = stats(os10_roll, 12)
    for r in ("pre", "post"):
        if (os10_close.regime == r).any():
            results[f"OS10_close_{r}"] = stats(os10_close[os10_close.regime == r], 12)
        if (os10_roll.regime == r).any():
            results[f"OS10_roll_{r}"] = stats(os10_roll[os10_roll.regime == r], 12)
    # paired roll-vs-close on the SAME start expiries (isolates roll effect)
    merged = os10_close[["exp", "pct_spot"]].rename(columns={"exp": "start_exp", "pct_spot": "close_pct"}).merge(
        os10_roll[["start_exp", "pct_spot"]].rename(columns={"pct_spot": "roll_pct"}), on="start_exp")
    if not merged.empty:
        diff = merged["roll_pct"] - merged["close_pct"]
        results["OS10_roll_minus_close"] = dict(
            n_paired=int(len(merged)),
            mean_diff_pct_spot=round(diff.mean(), 4),
            roll_better_share=round((diff > 0).mean(), 3),
            close_worst=round(merged["close_pct"].min(), 3),
            roll_worst=round(merged["roll_pct"].min(), 3))

# degenerate flags on OS-01
results["OS01_degen_flags"] = G.degenerate_flags(
    os01.sort_values("exit").set_index("exit")["pct_spot"] / 100.0,
    trades=os01.assign(ret=os01["pct_spot"], sym="NIFTY"), ret_col="ret", sym_col="sym")

results["_meta"] = dict(
    n_exps=len(exps), exp_range=[str(exps[0]), str(exps[-1])],
    n_monthly_ge28dte=len(month_exps),
    dte_note="weekly files ~10 DTE life; 3-tenor/21DTE ladder NOT constructible -> OS07 is a 2-deep proxy")

with open(OUT / "summary.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
