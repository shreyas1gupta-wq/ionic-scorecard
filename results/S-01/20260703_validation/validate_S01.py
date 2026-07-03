# -*- coding: utf-8 -*-
"""
S-01 formal validation battery (Quant Head, Arjun Rao) — 2026-07-03.
Slice: iv_rv >= 1.4 AND iv < 1.0 short-straddle harvest of rv_iv_vol.parquet.
Tests: walk-forward grid, plateau, Deflated Sharpe (Bailey-LopezdePrado),
       PBO via CSCV, trade bootstrap, crash-proxy stress.
Booking: EXIT period (monthly EW portfolio on exit-month). Denominator: short_ret
         is already return-on-premium (mirror of long_ret), stable.
Seeds fixed. No overwrite. Guards imported from lib/guards.py.
"""
from __future__ import annotations
import sys, os, json, hashlib
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats

ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
sys.path.insert(0, os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "lib"))
import guards as G  # noqa: E402

DATA = os.path.join(ROOT, "intraday_options_strategy", "buying", "rv_iv_vol.parquet")
OUTDIR = os.path.join(ROOT, "results", "S-01", "20260703_validation")
RET = "short_ret"          # short-straddle side = what S-01 harvests
SEED = 20260703
rng = np.random.default_rng(SEED)

# ---------------- load + lineage ----------------
df = pd.read_parquet(DATA)
FULL_ROWS = len(df)
for c in ("exp", "entry", "exit"):
    df[c + "_dt"] = pd.to_datetime(df[c])
df["exit_ym"] = df["exit_dt"].dt.to_period("M")

def slice_it(d, iv_rv_thr, iv_cap):
    return d[(d["iv_rv"] >= iv_rv_thr) & (d["iv"] < iv_cap)].copy()

# S-01 as-specified (iv_rv>=1.4 & iv<1.0)
S01 = slice_it(df, 1.4, 1.0)
SLICE_ROWS = len(S01)

lineage = {
    "data_file": DATA,
    "data_max_bytes_mtime": datetime.fromtimestamp(os.path.getmtime(DATA)).isoformat(),
    "full_file_rows": int(FULL_ROWS),
    "s01_slice_def": "iv_rv>=1.4 AND iv<1.0",
    "s01_slice_rows": int(SLICE_ROWS),
    "prompt_claimed_rows_3468_is": "FULL FILE not slice; actual S-01 slice=%d" % SLICE_ROWS,
    "return_col": RET,
    "entry_range": [str(df.entry_dt.min().date()), str(df.entry_dt.max().date())],
    "exit_range": [str(df.exit_dt.min().date()), str(df.exit_dt.max().date())],
    "exit_year_counts": {int(k): int(v) for k, v in S01["exit_dt"].dt.year.value_counts().sort_index().items()},
    "seed": SEED,
    "short_ret_equals_neg_long_ret_rows": int((S01[RET] + S01["long_ret"]).abs().gt(1e-9).sum()),
}

# monthly EW portfolio booked on EXIT month (fixes fake-low-variance)
def monthly_series(sl):
    return sl.groupby("exit_ym")[RET].mean().sort_index()

# ---------------- helper: Deflated Sharpe ----------------
def sharpe_ann(r, periods=12):
    r = np.asarray(r, float)
    if r.std(ddof=1) == 0 or len(r) < 3:
        return 0.0
    return r.mean() / r.std(ddof=1) * np.sqrt(periods)

def deflated_sharpe(returns, n_trials, periods=12):
    """Bailey & Lopez de Prado (2014) DSR on a return series (monthly)."""
    r = np.asarray(returns, float)
    r = r[~np.isnan(r)]
    T = len(r)
    if T < 4:
        return {"sr": 0.0, "dsr": 0.0, "note": "T<4"}
    sr = r.mean() / r.std(ddof=1)           # per-period (non-annualized) SR
    g3 = stats.skew(r, bias=False)
    g4 = stats.kurtosis(r, fisher=False, bias=False)  # non-excess kurtosis
    # expected max SR under n independent trials (SR0)
    e = np.euler_gamma
    z1 = stats.norm.ppf(1 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    sr0 = (1 - e) * z1 + e * z2            # var of trial SRs assumed ~1 (standardized); scale below
    # standardize sr0 by the sampling variance of SR across trials.
    # Under BdP, benchmark SR* = sqrt(Var[SR_trials]) * expected_max. We use the cross-trial std.
    return sr, g3, g4, T, sr0

def dsr_full(returns, sr_trials, n_trials, periods=12):
    r = np.asarray(returns, float); r = r[~np.isnan(r)]
    T = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3 = stats.skew(r, bias=False)
    g4 = stats.kurtosis(r, fisher=False, bias=False)
    e = np.euler_gamma
    z1 = stats.norm.ppf(1 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    emax = (1 - e) * z1 + e * z2                     # E[max] of N standard-normal-ish SRs
    var_sr_trials = np.var(sr_trials, ddof=1) if len(sr_trials) > 1 else 0.0
    sr_star = np.sqrt(var_sr_trials) * emax          # deflated benchmark (per-period units)
    # DSR = Prob( SR_hat > SR* ) accounting for non-normal moments (BdP eq.)
    denom = np.sqrt(max(1 - g3 * sr + (g4 - 1) / 4.0 * sr**2, 1e-12))
    dsr = stats.norm.cdf(((sr - sr_star) * np.sqrt(T - 1)) / denom)
    return {
        "sr_perperiod": float(sr), "sr_ann": float(sr * np.sqrt(periods)),
        "skew": float(g3), "kurt_nonexcess": float(g4), "T": int(T),
        "n_trials": int(n_trials), "emax": float(emax),
        "var_sr_trials": float(var_sr_trials), "sr_star": float(sr_star),
        "dsr": float(dsr), "pass_dsr": bool(dsr > 0.95),
    }

# ================= TEST 1: WALK-FORWARD =================
# Honest note: sample is 2021-06..2026-06 but >75% of rows are 2024+.
# We use expanding-window folds: train through year Y-end, validate the following calendar year.
grid_ivrv = [1.2, 1.4, 1.6]
grid_ivcap = [0.8, 1.0, 1.2]
grid = [(a, b) for a in grid_ivrv for b in grid_ivcap]   # 9 cells

def cell_metric(sl):
    """objective for param selection = mean monthly EW return (exit-booked)."""
    ms = monthly_series(sl)
    if len(ms) < 2:
        return np.nan, ms
    return ms.mean(), ms

# folds: choose params on train (entry_dt <= cutoff), score OOS on validate year
folds = [
    ("train<=2023-12-31", "2024", "2023-12-31", 2024),
    ("train<=2024-12-31", "2025", "2024-12-31", 2025),
    ("train<=2025-12-31", "2026", "2025-12-31", 2026),
]
wf_rows = []
for label, valname, cutoff, valyear in folds:
    cut = pd.Timestamp(cutoff)
    train_mask_base = df["entry_dt"] <= cut
    val_mask_base = df["exit_dt"].dt.year == valyear
    # pick best cell on TRAIN
    best = None
    for (ir, ic) in grid:
        tr = slice_it(df[train_mask_base], ir, ic)
        m, _ = cell_metric(tr)
        if np.isnan(m):
            continue
        if best is None or m > best[0]:
            best = (m, ir, ic, len(tr))
    if best is None:
        wf_rows.append({"fold": label, "val": valname, "chosen": None, "oos_mean": None, "n_val": 0})
        continue
    _, ir, ic, ntr = best
    va = slice_it(df[val_mask_base], ir, ic)
    oos_m, _ = cell_metric(va)
    wf_rows.append({
        "fold": label, "val": valname, "chosen_iv_rv": ir, "chosen_iv_cap": ic,
        "n_train": int(ntr), "n_val": int(len(va)),
        "oos_mean_monthly": None if np.isnan(oos_m) else round(float(oos_m), 4),
    })
wf_oos_means = [r["oos_mean_monthly"] for r in wf_rows if r.get("oos_mean_monthly") is not None]
wf_oos_avg = float(np.mean(wf_oos_means)) if wf_oos_means else float("nan")
WF_PASS = bool(len(wf_oos_means) >= 2 and all(x > 0 for x in wf_oos_means))

# ================= TEST 2: PLATEAU =================
# full-sample grid, mean monthly EW return per cell
grid_vals = {}
for (ir, ic) in grid:
    m, _ = cell_metric(slice_it(df, ir, ic))
    grid_vals[(ir, ic)] = m
best_cell = max(grid_vals, key=lambda k: (grid_vals[k] if not np.isnan(grid_vals[k]) else -1e9))
best_val = grid_vals[best_cell]
neigh = [grid_vals[k] for k in grid_vals if k != best_cell and not np.isnan(grid_vals[k])]
neigh_med = float(np.median(neigh))
spike_ratio = (best_val - neigh_med) / abs(neigh_med) if neigh_med != 0 else np.inf
PLATEAU_PASS = bool(abs(spike_ratio) <= 0.20)

# ================= TEST 3: DEFLATED SHARPE =================
# trials SR distribution = the 9 grid cells' monthly SRs; honest trials N = 9 grid + 4 historical = 13
grid_sr = []
for (ir, ic) in grid:
    _, ms = cell_metric(slice_it(df, ir, ic))
    if len(ms) >= 3:
        grid_sr.append(ms.mean() / ms.std(ddof=1))
N_TRIALS = 13
port = monthly_series(S01)               # the S-01 monthly EW series (exit-booked)
dsr_res = dsr_full(port.values, grid_sr, N_TRIALS, periods=12)
DSR_PASS = dsr_res["pass_dsr"]

# ================= TEST 4: PBO via CSCV =================
# Build a matrix of per-month returns across the 9 grid configs, split into S=12 blocks.
all_months = sorted(df["exit_ym"].unique())
config_month = {}   # (ir,ic) -> Series indexed by month
for (ir, ic) in grid:
    ms = monthly_series(slice_it(df, ir, ic))
    config_month[(ir, ic)] = ms.reindex(all_months)
M = pd.DataFrame(config_month)          # months x 9 configs
M = M.dropna(how="all")
def cscv_pbo(Mdf, S=12):
    from itertools import combinations
    months = list(Mdf.index)
    nblk = S
    blocks = np.array_split(np.arange(len(months)), nblk)
    idx = list(range(nblk))
    logits = []
    for combo in combinations(idx, nblk // 2):
        is_blk = np.concatenate([blocks[i] for i in combo])
        oos_blk = np.concatenate([blocks[i] for i in idx if i not in combo])
        IS = Mdf.iloc[is_blk]
        OOS = Mdf.iloc[oos_blk]
        is_sr = IS.mean() / (IS.std(ddof=1) + 1e-12)
        oos_sr = OOS.mean() / (OOS.std(ddof=1) + 1e-12)
        star = is_sr.idxmax()                       # config best IN-sample
        # OOS rank of that config (fraction of configs it beats OOS)
        r = oos_sr.rank()  # 1..N
        rel = r[star] / len(oos_sr)
        rel = min(max(rel, 1e-6), 1 - 1e-6)
        logits.append(np.log(rel / (1 - rel)))
    logits = np.array(logits)
    pbo = float((logits <= 0).mean())               # prob OOS rank below median
    return pbo, len(logits)
PBO, n_combos = cscv_pbo(M, S=12)
PBO_PASS = bool(PBO < 0.25)

# ================= TEST 5: BOOTSTRAP =================
r_slice = S01[RET].values
B = 1000
boot_means = np.array([rng.choice(r_slice, size=len(r_slice), replace=True).mean() for _ in range(B)])
p5 = float(np.percentile(boot_means, 5))
BOOT_PASS = bool(p5 > 0)

# ================= TEST 6: CRASH PROXY =================
# Synthesize a month where every open straddle realizes -2.5x..-3x premium simultaneously
# on 4-6 concurrent positions. Report book hit vs RISK_LIMITS 1%/position.
# Inverse-IV sizing per RISK_LIMITS: size ∝ 1/entry-IV, ref 25% IV; per-position risk cap 1% of book.
# We model: each position budgeted so max-loss (worst-case MTM) = 1% of book at ref.
# A -2.5x to -3x premium realization means loss = (2.5..3)x the premium collected.
# If premium collected per position sized so that a "normal" max-loss ~1% book, a 3x blow = 3% book/pos.
concurrent = [4, 5, 6]
shock_mult = [2.5, 3.0]
per_pos_budget = 0.01     # 1% book risk per position (RISK_LIMITS)
crash = {}
for n in concurrent:
    for s in shock_mult:
        # worst-case: each pos loses s * (premium). If 1% book was the *modeled* worst case,
        # a realization s times worse = s% book per position.
        book_hit = n * s * per_pos_budget
        crash[f"{n}pos_x{s}"] = round(book_hit, 4)
worst_hit = max(crash.values())
# RISK_LIMITS escalation: single-day book loss >3% halts trading; COVID stress survives if DD<20%
CRASH_PASS = bool(worst_hit < 0.20)      # survives book-level 20% DD threshold
CRASH_HALT_TRIGGER = bool(worst_hit > 0.03)

# ---------------- degenerate detectors ----------------
trades = S01.rename(columns={RET: "ret"})[["sym", "ret"]].copy()
flags = G.degenerate_flags(port.reset_index(drop=True).rename("ret"), trades=trades, ret_col="ret", sym_col="sym")
win_rate = float((S01[RET] > 0).mean())
wl = float(S01[RET][S01[RET] > 0].mean() / abs(S01[RET][S01[RET] <= 0].mean() + 1e-12))

# ---------------- assemble metrics ----------------
metrics = {
    "test1_walk_forward": {"folds": wf_rows, "oos_mean_avg": round(wf_oos_avg, 4) if wf_oos_means else None, "PASS": WF_PASS},
    "test2_plateau": {"best_cell": list(best_cell), "best_val": round(float(best_val), 4),
                      "neighborhood_median": round(neigh_med, 4), "spike_ratio": round(float(spike_ratio), 4),
                      "PASS": PLATEAU_PASS},
    "test3_deflated_sharpe": {**{k: (round(v, 4) if isinstance(v, float) else v) for k, v in dsr_res.items()},
                              "PASS": DSR_PASS},
    "test4_pbo_cscv": {"PBO": round(PBO, 4), "n_combos": n_combos, "S": 12, "PASS": PBO_PASS},
    "test5_bootstrap": {"B": B, "p5_mean_ret": round(p5, 4), "median_mean": round(float(np.median(boot_means)), 4),
                        "PASS": BOOT_PASS},
    "test6_crash_proxy": {"book_hits": crash, "worst_hit": round(worst_hit, 4),
                          "survives_20pct_DD": CRASH_PASS, "triggers_3pct_halt": CRASH_HALT_TRIGGER,
                          "PASS": CRASH_PASS},
    "degenerate": {"guard_flags": flags, "win_rate": round(win_rate, 4), "win_loss_ratio": round(wl, 4)},
    "slice_summary": {"rows": SLICE_ROWS, "mean_short_ret": round(float(S01[RET].mean()), 4),
                      "std_short_ret": round(float(S01[RET].std()), 4),
                      "n_months_exit": int(port.shape[0]), "n_symbols": int(S01.sym.nunique())},
}

with open(os.path.join(OUTDIR, "config.json"), "w", encoding="utf-8") as f:
    json.dump({"lineage": lineage, "grid": {"iv_rv": grid_ivrv, "iv_cap": grid_ivcap},
               "folds": [f[0] + "->" + f[1] for f in folds]}, f, indent=2)
with open(os.path.join(OUTDIR, "metrics.json"), "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

# ---------------- console table ----------------
def pf(b): return "PASS" if b else "FAIL"
print("=" * 68)
print("S-01 VALIDATION BATTERY  |  slice iv_rv>=1.4 & iv<1.0  | rows=%d" % SLICE_ROWS)
print("=" * 68)
print("1 WALK-FORWARD   %s  OOS-mean-avg=%s  folds=%d" % (pf(WF_PASS), metrics["test1_walk_forward"]["oos_mean_avg"], len(wf_oos_means)))
for r in wf_rows:
    print("     %s -> val %s: chose iv_rv=%s iv_cap=%s  n_val=%s  OOS=%s" % (
        r["fold"], r["val"], r.get("chosen_iv_rv"), r.get("chosen_iv_cap"), r.get("n_val"), r.get("oos_mean_monthly")))
print("2 PLATEAU        %s  best=%.4f  neigh_med=%.4f  spike=%.1f%%" % (pf(PLATEAU_PASS), best_val, neigh_med, spike_ratio * 100))
print("3 DEFLATED SR    %s  DSR=%.4f  SR_ann=%.2f  T=%d  N_trials=%d" % (pf(DSR_PASS), dsr_res["dsr"], dsr_res["sr_ann"], dsr_res["T"], N_TRIALS))
print("4 PBO (CSCV)     %s  PBO=%.1f%%  combos=%d  S=12" % (pf(PBO_PASS), PBO * 100, n_combos))
print("5 BOOTSTRAP      %s  5th-pctile mean=%.4f (B=1000)" % (pf(BOOT_PASS), p5))
print("6 CRASH PROXY    %s  worst book hit=%.1f%%  (3%% halt=%s, 20%% DD=%s)" % (
    pf(CRASH_PASS), worst_hit * 100, CRASH_HALT_TRIGGER, not CRASH_PASS))
print("-" * 68)
print("DEGENERATE FLAGS:", flags if flags else "none")
print("  win_rate=%.1f%%  W/L=%.2f" % (win_rate * 100, wl))
print("=" * 68)
