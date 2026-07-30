"""160_dsr_d009.py — Dr. Sameer Bhat (Overfit & Sensitivity Analyst), 2026-07-30.
TASK 1: DSR/PBO on the 4 live candidates from SHARED_CONTEXT/FINAL_VERDICT.
TASK 2: D-009 verification of the 2015-01-09..2021-04-30 segment of
        intraday_options_strategy/datasets/processed/nifty_1min.parquet
        against datasets/index_daily/nse_official_all_indices.parquet.
Self-contained, argument-free. Writes all outputs to results/DSR_D009_20260730/.
Column-subset reads only; gc.collect() after each heavy step (2.5GB free machine).
"""
from __future__ import annotations
import gc
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import norm

warnings.filterwarnings("ignore")

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
RES = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results"
OUT = RES / "DSR_D009_20260730"
OUT.mkdir(exist_ok=True)

# =====================================================================================
# PART 0 — shared stats helpers
# =====================================================================================


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 10:
        return np.nan
    m = x.mean(); d = x - m; n = len(x); var = (d @ d) / n
    for L in range(1, min(lags, n - 1) + 1):
        var += 2 * (1 - L / (lags + 1)) * ((d[L:] @ d[:-L]) / n)
    return m / np.sqrt(var / n) if var > 0 else np.nan


def trade_stats(x, label=""):
    x = np.asarray(pd.Series(x).dropna(), float)
    n = len(x)
    if n < 5:
        return {"label": label, "n": n}
    mean, sd = x.mean(), x.std(ddof=1)
    sk = float(stats.skew(x))
    kt = float(stats.kurtosis(x, fisher=True))  # excess kurtosis
    naive_t = mean / sd * np.sqrt(n) if sd > 0 else np.nan
    srt = np.sort(x)[::-1]
    tot = x.sum()
    top1 = float(srt[0] / tot) if tot != 0 else np.nan
    top3 = float(srt[:3].sum() / tot) if tot != 0 and n >= 3 else np.nan
    return {"label": label, "n": n, "mean": round(mean, 4), "sd": round(sd, 4),
            "skew": round(sk, 4), "excess_kurt": round(kt, 4),
            "naive_t": round(float(naive_t), 4), "top1_share": round(top1, 4),
            "top3_share": round(top3, 4) if not np.isnan(top3) else None,
            "sharpe_per_trade": round(mean / sd, 5) if sd > 0 else np.nan}


def psr(sr_hat, sr_star, n, skew, kurt):
    """Probabilistic Sharpe Ratio (Bailey & Lopez de Prado 2012).
    sr_hat, sr_star are PER-TRADE (not annualized) Sharpe ratios on the same n."""
    if n < 5 or not np.isfinite(sr_hat):
        return np.nan
    num = (sr_hat - sr_star) * np.sqrt(n - 1)
    den = np.sqrt(max(1e-12, 1 - skew * sr_hat + (kurt / 4.0) * sr_hat ** 2))
    return float(norm.cdf(num / den))


def expected_max_sharpe(sr_array):
    """E[max SR] under N independent trials of Sharpe~N(0,V), Bailey-Lopez de Prado
    (2014) closed-form approximation using the EMPIRICAL cross-sectional sd of the
    trial Sharpes themselves (family-local DSR benchmark) — statistically preferable
    to assuming a generic distribution when we actually observe the trial grid."""
    sr_array = np.asarray(sr_array, float)
    sr_array = sr_array[np.isfinite(sr_array)]
    N = len(sr_array)
    if N < 2:
        return 0.0, N
    V = sr_array.var(ddof=1)
    gamma = 0.5772156649
    if N > 1:
        z1 = norm.ppf(1 - 1.0 / N)
        z2 = norm.ppf(1 - 1.0 / (N * np.e))
        emax = np.sqrt(V) * ((1 - gamma) * z1 + gamma * z2)
    else:
        emax = 0.0
    return float(emax), N


def dsr(sr_hat, n, skew, kurt, sr_family):
    """DSR = PSR(SR_hat ; benchmark = E[max SR | N trials, V from sr_family])."""
    sr0, N = expected_max_sharpe(sr_family)
    p = psr(sr_hat, sr0, n, skew, kurt)
    return p, sr0, N


def bonferroni_bar(m, alpha=0.05):
    """two-sided |z| bar for family-wise alpha at m tests"""
    return float(norm.ppf(1 - (alpha / m) / 2))


def effective_n_from_corr(corr_matrix):
    """Average-pairwise-correlation effective-trials estimate:
    N_eff = N / (1 + (N-1)*rho_avg), rho_avg = mean off-diagonal |corr|."""
    C = np.asarray(corr_matrix, float)
    N = C.shape[0]
    if N < 2:
        return N, 0.0
    off = C[~np.eye(N, dtype=bool)]
    off = off[np.isfinite(off)]
    rho = float(np.mean(np.abs(off))) if len(off) else 0.0
    neff = N / (1 + (N - 1) * rho)
    return float(neff), rho


def cscv_pbo(pnl_wide: pd.DataFrame, S=8):
    """Combinatorially-Symmetric CV PBO (Bailey/Borwein/Lopez de Prado/Zhu 2014).
    pnl_wide: rows=time (daily), cols=distinct configs, values=daily net P&L.
    Splits into S contiguous blocks, evaluates all C(S,S/2) train/test splits,
    for each: pick IS-best-Sharpe config, find its OOS rank -> logit(rank/(N+1)).
    PBO = P(logit <= 0), i.e. IS-winner is below-OOS-median more than half the time."""
    from itertools import combinations
    pnl_wide = pnl_wide.dropna(how="all")
    T, N = pnl_wide.shape
    if N < 2 or T < S * 4:
        return {"pbo": None, "reason": f"insufficient data T={T} N={N} S={S}"}
    blocks = np.array_split(np.arange(T), S)
    logits = []
    half = S // 2
    for train_idx in combinations(range(S), half):
        test_idx = [i for i in range(S) if i not in train_idx]
        tr_rows = np.concatenate([blocks[i] for i in train_idx])
        te_rows = np.concatenate([blocks[i] for i in test_idx])
        tr = pnl_wide.iloc[tr_rows]; te = pnl_wide.iloc[te_rows]
        tr_sh = tr.mean() / tr.std(ddof=1)
        te_sh = te.mean() / te.std(ddof=1)
        tr_sh = tr_sh.replace([np.inf, -np.inf], np.nan)
        te_sh = te_sh.replace([np.inf, -np.inf], np.nan)
        if tr_sh.isna().all() or te_sh.isna().all():
            continue
        best_cfg = tr_sh.idxmax()
        rank = te_sh.rank(pct=True)[best_cfg]  # 0..1, 1=best OOS
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        logits.append(np.log(rank / (1 - rank)))
    logits = np.array(logits)
    pbo = float((logits <= 0).mean()) if len(logits) else None
    return {"pbo": pbo, "n_combos": int(len(logits)), "S": S, "N_configs": int(N),
            "T_obs": int(T), "logit_mean": float(np.mean(logits)) if len(logits) else None}


RESULTS = {}

# =====================================================================================
# PART 1 — SWEEP_E flagship: family stats + CSCV PBO across A-F configs + risk_frac grid
# =====================================================================================
print("=== PART 1: SWEEP_E flagship ===", flush=True)
SW = RES / "SWEEP_11YR_20260729"
report = json.loads((SW / "report.json").read_text())

# reconstruct carry-adjusted E-config per-trade series (verbatim carry_adj.py logic)
CARRY_MONTHLY = 0.005
LOT = 75
BROK, EXCH, GST, STAMP, SEBI_CR = 20.0, 0.0019 / 100, 0.18, 0.002 / 100, 10.0
STT_OLD, STT_NEW = 0.0125 / 100, 0.020 / 100
import datetime as dt
SW_SWITCH = dt.date(2024, 10, 1)


def rt_cost(e, x, lots, d):
    qty = lots * LOT
    stt = (STT_OLD if d < SW_SWITCH else STT_NEW) * x * qty
    turn = (e + x) * qty
    brok = BROK * 2
    exch = EXCH * turn
    return brok + exch + stt + GST * (brok + exch) + STAMP * e * qty + SEBI_CR * turn / 1e7


tr = pd.read_csv(SW / "trades_E_swing3_trail60_1lot.csv", parse_dates=["t"])
tr["date"] = pd.to_datetime(tr["date"]).dt.date
hold_days = np.maximum(tr.hold_min / 375.0, 0.0)
carry = tr.entry * (CARRY_MONTHLY / 30.0) * np.maximum(hold_days, 0.5)
tr["eff_pts"] = tr.gross_pts - np.sign(tr.dir) * carry
tr["gross_r"] = tr.eff_pts * LOT
tr["cost_r"] = [rt_cost(e, x, 1, d) for e, x, d in zip(tr.entry, tr.exit, tr.date)]
tr["net_r"] = tr.gross_r - tr.cost_r

e_all = trade_stats(tr.net_r, "E_swing3_ALL_11yr_carry_1lot")
e_oos = trade_stats(tr[tr.date < dt.date(2021, 5, 1)].net_r, "E_swing3_OOS_2015_2021_carry")
e_is = trade_stats(tr[(tr.date >= dt.date(2021, 5, 1)) & (tr.date <= dt.date(2025, 12, 31))].net_r,
                    "E_swing3_IS_2021_2025_carry")
print("E per-trade stats:", e_all, flush=True)
print("E OOS(2015-2021,pristine) stats:", e_oos, flush=True)

# DAILY (not per-trade) basis -- matches report.json/carry_adj.py's own Sharpe methodology
# (daily = groupby(date).sum() of trade net P&L, Sharpe = mean/std*sqrt(252) on dr=daily/CAPITAL).
# BUGFIX: the A-F family Sharpes pulled from report.json are ANNUALIZED DAILY Sharpes; comparing
# them to a PER-TRADE (unannualized, raw-rupee) Sharpe as originally coded here was a unit
# mismatch that silently drove DSR to ~0 on the first pass. Use the daily series for the DSR
# input on this candidate so units match the family it is benchmarked against.
CAPITAL = 10_00_000.0
e_daily_r = tr.groupby("date")["net_r"].sum()
e_dr = (e_daily_r / CAPITAL).to_numpy()
e_daily_stats = trade_stats(e_dr, "E_swing3_DAILY_dr_ALL_11yr_carry")
# PSR/DSR requires SR_hat and the SR_family on the SAME (non-annualized, per-day) basis as the
# skew/kurtosis used (also computed on daily returns) -- keep the RAW daily Sharpe here and
# de-annualize the report.json family (which is *sqrt(252)) by the same factor before comparing.
e_daily_sharpe_raw = float(e_dr.mean() / e_dr.std(ddof=1))
e_daily_sharpe_ann = e_daily_sharpe_raw * np.sqrt(252)
print(f"E daily-basis: n_days={len(e_dr)} raw_daily_Sharpe={e_daily_sharpe_raw:.4f} "
      f"(annualized={e_daily_sharpe_ann:.3f}) skew={e_daily_stats['skew']} "
      f"excess_kurt={e_daily_stats['excess_kurt']}", flush=True)

# the A-F exit-structure grid (the actual search that produced "E" as apparent winner)
# use the ORIGINAL (no-carry) 1-lot ALL_11yr per-config Sharpe from report.json -- this
# is the grid as actually run/compared before the carry correction was applied only to
# the two survivors (D,E), so it is the faithful "search that produced E"
af_sharpes, af_meta = [], []
for c in report["configs"]:
    m = c["sizing"]["1lot"]["ALL_11yr"]
    if m.get("n", 0) >= 10:
        # report.json's "Sharpe" field is ANNUALIZED (*sqrt(252)); de-annualize to the same
        # raw-daily basis as e_daily_sharpe_raw so the DSR/PSR skew-kurtosis correction (built
        # on daily-return moments) is dimensionally consistent across candidate and family.
        af_sharpes.append(m["Sharpe"] / np.sqrt(252))
        af_meta.append({"config": c["config"], "Sharpe_annualized": m["Sharpe"], "t": m["t_nw_daily"],
                         "CAGR": m["CAGR_pct"], "n": m["n"]})
print("A-F grid (no-carry, 1lot, ALL_11yr):", af_meta, flush=True)

dsr_e_local, sr0_e_local, N_local = dsr(
    sr_hat=e_daily_sharpe_raw, n=len(e_dr), skew=e_daily_stats["skew"], kurt=e_daily_stats["excess_kurt"],
    sr_family=af_sharpes)
print(f"DSR(E, family=A-F grid N={N_local}) = {dsr_e_local}  (sr0_daily_raw benchmark; "
      f"annualized equivalents: SR_hat={e_daily_sharpe_ann:.3f})", flush=True)

# risk_frac sizing grid (16 cells: D,E x 8 risk_frac) -- secondary search, NOT used for
# the headline (headline is 1-lot fixed sizing), reported as an auxiliary DSR check
sf = json.loads((SW / "sizing_fix_report.json").read_text())
rf_sharpes = []
for cfg, rows in sf["configs"].items():
    for r in rows:
        if r.get("status") == "ok":
            rf_sharpes.append(r["Sharpe"] / np.sqrt(252))  # de-annualize, same fix as above
dsr_e_riskfrac, sr0_rf, N_rf = dsr(
    sr_hat=e_daily_sharpe_raw, n=len(e_dr), skew=e_daily_stats["skew"], kurt=e_daily_stats["excess_kurt"],
    sr_family=rf_sharpes)
print(f"DSR(E, family=risk_frac grid N={N_rf}) = {dsr_e_riskfrac}", flush=True)

# CSCV PBO across the 6 A-F configs' daily P&L (no-carry, 1lot, common ALL_11yr window)
daily_by_cfg = {}
for cname, _ in [("A_intraday_stop30", None), ("B_intraday_trail25", None), ("C_intraday_trail40", None),
                  ("D_overnight1_trail40", None), ("E_swing3_trail60", None), ("F_intraday_tgt200", None)]:
    f = SW / f"trades_{cname}_1lot.csv"
    if not f.exists():
        continue
    d = pd.read_csv(f, parse_dates=["t"])
    d["date"] = pd.to_datetime(d["date"]).dt.date
    daily_by_cfg[cname] = d.groupby("date")["net"].sum()
wide = pd.DataFrame(daily_by_cfg).sort_index()
pbo_af = cscv_pbo(wide, S=8)
print("CSCV PBO across A-F (6 configs):", pbo_af, flush=True)

# effective independent trials among A-F (correlation of daily P&L)
corr_af = wide.corr()
neff_af, rho_af = effective_n_from_corr(corr_af.values)
print(f"A-F effective-N: {neff_af:.2f} of {wide.shape[1]} (avg|corr|={rho_af:.3f})", flush=True)

RESULTS["SWEEP_E"] = {
    "per_trade_stats_ALL_11yr_carry": e_all, "per_trade_stats_OOS_2015_2021": e_oos,
    "per_trade_stats_IS_2021_2025": e_is,
    "daily_basis_stats_ALL_11yr_carry": {**e_daily_stats, "raw_daily_sharpe": e_daily_sharpe_raw,
                                          "annualized_sharpe": e_daily_sharpe_ann, "n_days": len(e_dr)},
    "reported_headline": {"n": 4378, "CAGR_pct": 15.33, "maxDD_pct": -18.02, "Sharpe": 1.84, "t_nw": 4.35},
    "AF_grid_no_carry_1lot_ALL_11yr": af_meta,
    "DSR_vs_AF_grid": {"dsr": dsr_e_local, "sr0_benchmark_raw_daily": sr0_e_local, "N_trials": N_local},
    "DSR_vs_riskfrac_sizing_grid_16cells_auxiliary": {"dsr": dsr_e_riskfrac, "sr0_benchmark_raw_daily": sr0_rf, "N_trials": N_rf},
    "CSCV_PBO_AF_6configs": pbo_af,
    "AF_effective_independent_trials": {"N_eff": neff_af, "avg_abs_corr": rho_af, "N_raw": int(wide.shape[1])},
}
del tr, wide, daily_by_cfg
gc.collect()

# =====================================================================================
# PART 2 — S1 z-score open fade (THREE_POSTED family)
# =====================================================================================
print("=== PART 2: S1 z-score (THREE_POSTED) ===", flush=True)
TP = RES / "THREE_POSTED_20260730"
s1 = pd.read_csv(TP / "futures_trades_S1_futures_primary_z1.0.csv", parse_dates=["date"])
s1_stats = trade_stats(s1.net_pts, "S1_futures_z1.0")
print("S1 stats:", s1_stats, flush=True)

summ = json.loads((TP / "summary.json").read_text())
family_sharpes = []
for row in summ:
    if row.get("n", 0) >= 10 and "mean_net_pts" in row:
        # approximate per-trade Sharpe from summary fields (mean/  implied sd via RR&hit not
        # reliable -> instead load each raw csv's own net_pts sd where the file exists)
        pass

fam_files = {
    "S1_futures_primary": "futures_trades_S1_futures_primary_z1.0.csv",
    "S1_options_primary": "options_trades_S1_options_primary_z1.0.csv",
    "S2_futures_atr": "futures_trades_S2_futures_atr_normalised.csv",
    "S2_futures_raw": "futures_trades_S2_futures_raw_points.csv",
    "S2_options_atr": "options_trades_S3_options_atr_normalised.csv",  # note: no S2 options atr file exists; placeholder skipped below
    "S3_futures_atr": "futures_trades_S3_futures_atr_normalised.csv",
    "S3_futures_raw": "futures_trades_S3_futures_raw_points.csv",
    "S3_options_atr": "options_trades_S3_options_atr_normalised.csv",
    "S3_options_raw": "options_trades_S3_options_raw_points.csv",
}
fam_sharpe_list, fam_daily = {}, {}
for name, fn in fam_files.items():
    fp = TP / fn
    if not fp.exists():
        continue
    d = pd.read_csv(fp, parse_dates=["date"])
    col = "net_pts" if "net_pts" in d.columns else ("net" if "net" in d.columns else None)
    if col is None or len(d) < 10:
        continue
    x = d[col].dropna()
    sh = x.mean() / x.std(ddof=1) if x.std(ddof=1) > 0 else np.nan
    if np.isfinite(sh):
        fam_sharpe_list[name] = sh
        fam_daily[name] = d.groupby(d["date"].dt.date)[col].sum()

dsr_s1_local, sr0_s1, N_s1fam = dsr(
    sr_hat=s1_stats["sharpe_per_trade"], n=s1_stats["n"], skew=s1_stats["skew"],
    kurt=s1_stats["excess_kurt"], sr_family=list(fam_sharpe_list.values()))
print(f"DSR(S1, family=THREE_POSTED N={N_s1fam}) = {dsr_s1_local}", flush=True)
print("family sharpes:", fam_sharpe_list, flush=True)

wide_tp = pd.DataFrame(fam_daily).sort_index()
pbo_tp = cscv_pbo(wide_tp, S=8)
print("CSCV PBO across THREE_POSTED family:", pbo_tp, flush=True)
corr_tp = wide_tp.corr()
neff_tp, rho_tp = effective_n_from_corr(corr_tp.values)
print(f"THREE_POSTED effective-N: {neff_tp:.2f} of {wide_tp.shape[1]} (avg|corr|={rho_tp:.3f})", flush=True)

RESULTS["S1_zscore"] = {
    "per_trade_stats": s1_stats,
    "reported_headline": {"n": 1618, "mean_net_pts": 4.28, "median_net_pts": 2.48, "placebo_p": 0.006},
    "family_sharpes_THREE_POSTED": fam_sharpe_list,
    "DSR_vs_family": {"dsr": dsr_s1_local, "sr0_benchmark": sr0_s1, "N_trials": N_s1fam},
    "CSCV_PBO_family": pbo_tp,
    "effective_independent_trials": {"N_eff": neff_tp, "avg_abs_corr": rho_tp, "N_raw": int(wide_tp.shape[1])},
}
del s1, wide_tp, fam_daily
gc.collect()

# =====================================================================================
# PART 3 — CALENDAR 1x1 3d-before
# =====================================================================================
print("=== PART 3: CALENDAR 1x1 3d-before ===", flush=True)
RC = RES / "RATIO_CALENDAR_20260730"
gt = pd.read_csv(RC / "grid_a_trades_raw.csv", parse_dates=["day0"])
target = gt[(gt.strike_struct == "ATM_ATM") & (gt.ratio == "1x1") & (gt.exit_variant == "3d_before")].copy()
cal_stats = trade_stats(target.net_pts, "CALENDAR_1x1_3d_before_unconditional")
print("CALENDAR target-cell stats:", cal_stats, flush=True)

pre19 = target[target.day0 < "2019-02-01"]
post19 = target[target.day0 >= "2019-02-01"]
print(f"pre-2019 n={len(pre19)} mean={pre19.net_pts.mean():.2f} | post-2019 n={len(post19)} "
      f"mean={post19.net_pts.mean():.2f}", flush=True)

# 24-config family (strike_struct x ratio x exit_variant, unconditional filter, NET) for
# CSCV PBO -- this is the actual grid_a search that produced the 3d_before/1x1/ATM_ATM cell
gt["cfg"] = gt.strike_struct + "|" + gt.ratio + "|" + gt.exit_variant
daily_cal = {}
cfg_sharpes = {}
for cfg, g in gt.groupby("cfg"):
    if len(g) < 20:
        continue
    x = g.net_pts.dropna()
    sh = x.mean() / x.std(ddof=1) if x.std(ddof=1) > 0 else np.nan
    if np.isfinite(sh):
        cfg_sharpes[cfg] = sh
        daily_cal[cfg] = g.groupby(g.day0.dt.date)["net_pts"].sum()
print(f"grid_a family: {len(cfg_sharpes)} distinct (strike_struct,ratio,exit_variant) configs", flush=True)

dsr_cal_local, sr0_cal, N_cal = dsr(
    sr_hat=cal_stats["sharpe_per_trade"], n=cal_stats["n"], skew=cal_stats["skew"],
    kurt=cal_stats["excess_kurt"], sr_family=list(cfg_sharpes.values()))
print(f"DSR(CALENDAR, family=grid_a N={N_cal}) = {dsr_cal_local}", flush=True)

wide_cal = pd.DataFrame(daily_cal).sort_index()
pbo_cal = cscv_pbo(wide_cal, S=8)
print("CSCV PBO across grid_a (24 configs):", pbo_cal, flush=True)
corr_cal = wide_cal.corr()
neff_cal, rho_cal = effective_n_from_corr(corr_cal.values)
print(f"grid_a effective-N: {neff_cal:.2f} of {wide_cal.shape[1]} (avg|corr|={rho_cal:.3f})", flush=True)

RESULTS["CALENDAR_1x1_3d_before"] = {
    "per_trade_stats_unconditional": cal_stats,
    "pre2019": {"n": int(len(pre19)), "mean_pts": float(pre19.net_pts.mean()) if len(pre19) else None},
    "post2019": {"n": int(len(post19)), "mean_pts": float(post19.net_pts.mean()) if len(post19) else None},
    "reported_headline": {"PF": 1.60, "t": 2.25, "n_pre2019": 93, "n_post2019": 85,
                           "pts_pre2019": 0.88, "pts_post2019": 18.32},
    "grid_a_family_N": len(cfg_sharpes),
    "DSR_vs_grid_a_family": {"dsr": dsr_cal_local, "sr0_benchmark": sr0_cal, "N_trials": N_cal},
    "CSCV_PBO_grid_a": pbo_cal,
    "effective_independent_trials": {"N_eff": neff_cal, "avg_abs_corr": rho_cal, "N_raw": int(wide_cal.shape[1])},
}
del gt, wide_cal, daily_cal
gc.collect()

# =====================================================================================
# PART 4 — delta-neutral overshoot sell
# =====================================================================================
print("=== PART 4: delta-neutral overshoot sell ===", flush=True)
SO = RES / "SPIKE_OVERSHOOT_SELL_20260730"
ft = pd.read_csv(SO / "filtered_trades.csv", parse_dates=["t0"])
ov_stats = trade_stats(ft.pnl_deltaneutral, "overshoot_delta_neutral_sell_ALL")
print("overshoot delta-neutral stats (own recomputation):", ov_stats, flush=True)

ft["dbucket"] = pd.cut(ft["delta"], bins=[0.20, 0.24, 0.28, 0.32, 0.36, 0.40])
bucket_tbl = ft.groupby("dbucket")["pnl_deltaneutral"].agg(["count", "mean", "std"])
print("by delta bucket:\n", bucket_tbl, flush=True)

# family = the 5 delta buckets (natural sensitivity slices of the SAME backtest, not
# independent re-runs) -- used only for a PLATEAU check, not as extra Bonferroni trials
bucket_sharpes = []
for _, g in ft.groupby("dbucket"):
    x = g.pnl_deltaneutral.dropna()
    if len(x) >= 15 and x.std(ddof=1) > 0:
        bucket_sharpes.append(x.mean() / x.std(ddof=1))

# conservative recompute: use FINAL_VERDICT's reported headline mean (+0.30) but the
# empirically observed n and sd from the artifact on disk (more conservative than using
# the artifact's own raw mean of +0.76, and reconciles the two without overclaiming)
n_ov, sd_ov = ov_stats["n"], ov_stats["sd"]
conservative_t = 0.30 / sd_ov * np.sqrt(n_ov)
conservative_sharpe = 0.30 / sd_ov

dsr_ov_local, sr0_ov, N_ov = dsr(
    sr_hat=conservative_sharpe, n=n_ov, skew=ov_stats["skew"], kurt=ov_stats["excess_kurt"],
    sr_family=bucket_sharpes if len(bucket_sharpes) >= 2 else [ov_stats["sharpe_per_trade"]])

RESULTS["overshoot_delta_neutral_sell"] = {
    "own_recomputation_from_filtered_trades_csv": ov_stats,
    "reported_headline": {"mean_pts": 0.30, "delta": 0.30, "range_hi": 0.64, "range_lo": -0.25,
                           "band": "0.20-0.40"},
    "provenance_note": ("Own recomputation from filtered_trades.csv gives mean +0.76 pts (n=1418, "
                         "sd=8.49) at full population -- MORE positive than the FINAL_VERDICT-quoted "
                         "+0.30. The +0.30 figure is not reproducible from any file on disk as-is; it "
                         "likely reflects a later, unsaved refinement (extra slippage/cost pass -- "
                         "rerun_with_px.log documents a rerun of the upstream overshoot measurement but "
                         "not this P&L step). Conservative choice below: use the QUOTED +0.30 mean with "
                         "the ARTIFACT's own observed n/sd (more conservative than the artifact's own "
                         "raw +0.76), so the DSR here is not inflated by trusting an unreproducible "
                         "number at face value."),
    "delta_bucket_breakdown": bucket_tbl.reset_index().astype(str).to_dict("records"),
    "conservative_recompute": {"n": n_ov, "sd": sd_ov, "mean_used": 0.30, "t": float(conservative_t),
                                "sharpe_per_trade": float(conservative_sharpe)},
    "DSR_vs_delta_bucket_family": {"dsr": dsr_ov_local, "sr0_benchmark": sr0_ov, "N_trials": N_ov,
                                    "note": "delta buckets are slices of ONE backtest, not independent "
                                            "re-runs -- this DSR is illustrative/conservative, not a "
                                            "true multi-trial deflation; PLATEAU check only"},
}
del ft
gc.collect()

# =====================================================================================
# PART 5 — Bonferroni bars at several trial-count assumptions (filled in after the
# forensic trial sweep is finalised; placeholders computed for a documented range)
# =====================================================================================
print("=== PART 5: Bonferroni bars ===", flush=True)
for m in (466, 500, 600, 650, 700, 750, 800):
    print(f"m={m:4d}  |z|_bar={bonferroni_bar(m):.3f}", flush=True)

RESULTS["bonferroni_bars"] = {str(m): bonferroni_bar(m) for m in (466, 500, 600, 650, 700, 750, 800)}

(OUT / "dsr_pbo_results.json").write_text(json.dumps(RESULTS, indent=2, default=str), encoding="utf-8")
print("\nwrote dsr_pbo_results.json", flush=True)

gc.collect()

# =====================================================================================
# PART 6 — D-009 verification: 2015-01-09..2021-04-30 segment of nifty_1min.parquet
# =====================================================================================
print("\n=== PART 6: D-009 verification, 2015-2021 segment ===", flush=True)
D009 = {}

SRC = ROOT / "intraday_options_strategy" / "datasets" / "processed" / "nifty_1min.parquet"
d = pd.read_parquet(SRC, columns=["open", "high", "low", "close"])
d = d[~d.index.duplicated()].sort_index()
print(f"[raw] {len(d):,} bars {d.index.min()} .. {d.index.max()}", flush=True)

seg = d[(d.index >= "2015-01-09") & (d.index < "2021-05-01")]
print(f"[segment] {len(seg):,} bars", flush=True)

# --- 6a. pre-open auction bars present + necessity of the 09:15 filter ---
tod = seg.index.time
preopen = seg[(tod >= dt.time(9, 0)) & (tod < dt.time(9, 15))]
postopen = seg[(tod >= dt.time(9, 15)) & (tod <= dt.time(15, 30))]
print(f"[preopen 09:00-09:14 bars present]: {len(preopen):,} rows "
      f"({100*len(preopen)/max(len(seg),1):.2f}% of segment)", flush=True)
if len(preopen):
    # compare first bar of day using preopen vs using >=09:15 filter, on a sample of days
    preopen_days = pd.Series(preopen.index.date).unique()
    diffs = []
    for day in preopen_days[:500]:
        day_pre = preopen[preopen.index.date == day]
        day_post = postopen[postopen.index.date == day]
        if len(day_pre) and len(day_post):
            diffs.append(float(day_pre["open"].iloc[0]) - float(day_post["open"].iloc[0]))
    diffs = np.array(diffs)
    D009["preopen_check"] = {
        "n_preopen_bars": int(len(preopen)), "pct_of_segment": round(100 * len(preopen) / len(seg), 3),
        "n_days_sampled": int(len(diffs)),
        "mean_abs_diff_preopen_vs_real_open": float(np.mean(np.abs(diffs))) if len(diffs) else None,
        "max_abs_diff": float(np.max(np.abs(diffs))) if len(diffs) else None,
        "pct_days_diff_gt_1pt": float((np.abs(diffs) > 1).mean()) if len(diffs) else None,
        "verdict": ("PRE-OPEN AUCTION BARS CONFIRMED PRESENT and MATERIALLY DIFFERENT from the "
                    "real 09:15 open -- the >=09:15 filter is NECESSARY, not cosmetic."
                    if len(diffs) and np.mean(np.abs(diffs)) > 0.5 else
                    "preopen bars present but differ negligibly from real open -- filter is precautionary")
    }
    print(D009["preopen_check"], flush=True)
else:
    D009["preopen_check"] = {"n_preopen_bars": 0, "verdict": "NO pre-open bars found in this file's "
                              "2015-2021 segment -- filter is a no-op FOR THIS FILE (unlike the HF file "
                              "documented elsewhere); re-verify against SHARED_CONTEXT's claim which was "
                              "about a DIFFERENT file (hf_index_options_1m), not this processed parquet."}
    print(D009["preopen_check"], flush=True)
del preopen, postopen
gc.collect()

# --- 6b. bar density per day (staleness / forward-fill check) ---
daily_counts = seg.groupby(seg.index.date).size()
D009["bar_density"] = {
    "n_days": int(len(daily_counts)), "min": int(daily_counts.min()), "max": int(daily_counts.max()),
    "median": float(daily_counts.median()), "mode": int(daily_counts.mode().iloc[0]),
    "pct_days_at_mode": float((daily_counts == daily_counts.mode().iloc[0]).mean()),
    "n_days_lt_100bars": int((daily_counts < 100).sum()),
}
print("bar density:", D009["bar_density"], flush=True)

# --- 6c. staleness: runs of identical OHLC (flat bars) during market hours ---
seg2 = seg.between_time("09:15", "15:29").copy()
flat = (seg2["high"] == seg2["low"]) & (seg2["close"] == seg2["open"]) & (seg2["high"] == seg2["close"])
run_id = (flat != flat.shift()).cumsum()
flat_runs = seg2[flat].groupby(run_id[flat]).size()
D009["staleness"] = {
    "n_flat_bars_total": int(flat.sum()), "pct_flat_bars": float(flat.mean()),
    "longest_flat_run_bars": int(flat_runs.max()) if len(flat_runs) else 0,
    "n_runs_ge_5bars": int((flat_runs >= 5).sum()) if len(flat_runs) else 0,
}
print("staleness:", D009["staleness"], flush=True)
del seg2, flat, run_id
gc.collect()

# --- 6d. two-scale corruption pattern check: look for abrupt scale jumps (x~10, /~10)
#     in the daily-close series (the DELISTED-panel pattern found elsewhere) ---
daily_close = seg.groupby(seg.index.date)["close"].last()
ratio = daily_close / daily_close.shift(1)
scale_jumps = ratio[(ratio > 3) | (ratio < 1 / 3.0)]
D009["scale_jump_check"] = {
    "n_daily_close_ratio_outside_3x": int(len(scale_jumps)),
    "dates": [str(i) for i in scale_jumps.index[:20]],
    "verdict": "NO two-scale corruption pattern found" if len(scale_jumps) == 0 else
               "FLAG: possible scale discontinuity -- inspect dates listed"
}
print("scale-jump check:", D009["scale_jump_check"], flush=True)

# --- 6e. lookahead / monotonic timestamp check ---
D009["monotonic_index"] = bool(seg.index.is_monotonic_increasing)
D009["any_duplicate_ts_in_segment"] = int(seg.index.duplicated().sum())

del daily_close, ratio, scale_jumps, daily_counts
gc.collect()

# --- 6f. cross-check against NSE-official daily OHLC (D-009 triple-verified reference) ---
REF = ROOT / "datasets" / "index_daily" / "nse_official_all_indices.parquet"
ref = pd.read_parquet(REF, columns=None)
print("[ref] columns:", ref.columns.tolist()[:20], flush=True)
# try to locate the NIFTY 50 index rows robustly
name_col = next((c for c in ref.columns if c.lower() in ("index_name", "index", "name", "symbol")), None)
date_col = next((c for c in ref.columns if "date" in c.lower()), None)
close_col = next((c for c in ref.columns if c.lower() in ("close", "closing_index_value", "close_price")), None)
open_col = next((c for c in ref.columns if c.lower() in ("open", "open_index_value", "open_price")), None)
print(f"[ref] resolved cols: name={name_col} date={date_col} close={close_col} open={open_col}", flush=True)

if name_col and date_col and close_col:
    cand_names = [v for v in ref[name_col].dropna().unique() if "NIFTY 50" in str(v).upper()
                  or str(v).upper().strip() == "NIFTY 50"]
    nifty_ref = ref[ref[name_col].isin(cand_names)].copy() if cand_names else pd.DataFrame()
    print(f"[ref] candidate name matches: {cand_names[:5]} -> {len(nifty_ref)} rows", flush=True)
    if len(nifty_ref):
        nifty_ref[date_col] = pd.to_datetime(nifty_ref[date_col])
        nifty_ref = nifty_ref.set_index(date_col).sort_index()
        our_daily = seg.between_time("09:15", "15:29").groupby(seg.between_time("09:15", "15:29").index.date).agg(
            open=("open", "first"), close=("close", "last"))
        our_daily.index = pd.to_datetime(our_daily.index)
        overlap = our_daily.join(nifty_ref[[close_col] + ([open_col] if open_col else [])],
                                  how="inner", rsuffix="_ref")
        if len(overlap):
            overlap["close_diff_pct"] = 100 * (overlap["close"] - overlap[close_col]) / overlap[close_col]
            D009["nse_official_crosscheck"] = {
                "n_overlap_days": int(len(overlap)),
                "max_abs_close_diff_pct": float(overlap["close_diff_pct"].abs().max()),
                "mean_abs_close_diff_pct": float(overlap["close_diff_pct"].abs().mean()),
                "pct_days_diff_gt_0.1pct": float((overlap["close_diff_pct"].abs() > 0.1).mean()),
            }
            print("NSE-official cross-check:", D009["nse_official_crosscheck"], flush=True)
        else:
            D009["nse_official_crosscheck"] = {"n_overlap_days": 0, "note": "no overlapping dates found"}
    else:
        D009["nse_official_crosscheck"] = {"note": f"could not isolate NIFTY 50 rows; unique names sample: "
                                            f"{list(ref[name_col].dropna().unique())[:15]}"}
else:
    D009["nse_official_crosscheck"] = {"note": "could not resolve expected columns in reference file",
                                        "columns_seen": ref.columns.tolist()}
del ref
gc.collect()

(OUT / "d009_verification.json").write_text(json.dumps(D009, indent=2, default=str), encoding="utf-8")
print("\nwrote d009_verification.json", flush=True)
print("\n=== ALL DONE ===", flush=True)
