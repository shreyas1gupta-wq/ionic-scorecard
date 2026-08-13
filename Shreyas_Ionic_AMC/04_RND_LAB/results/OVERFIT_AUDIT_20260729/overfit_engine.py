"""
OVERFIT_AUDIT_20260729 -- honest trials ledger + DSR/PBO engine.
Owner: Dr. Sameer Bhat (overfit-analyst-sameer-bhat), Shreyas_Ionic_AMC risk office.
D-035 binding: method pre-registered in this docstring BEFORE reading any output below.

REUSES existing, already-run signal-generation code verbatim (imported, not re-derived) from:
  - EMA_INTRADAY_BUYING_20260729/stage1_signal_test.py       (load_spot/resample/nw_tstat)
  - EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py
    (supertrend/volbrk/sweep/sr-level/confluence signal generators + forward_stats)
Re-running these generators (rather than trusting only the saved JSON) lets this audit
recover PER-TRADE and PER-DAY return series that the saved JSON does not retain, which
are required for genuine CSCV-PBO and for an empirically-estimated (not assumed)
cross-sectional variance of trial Sharpe ratios in the DSR formula.

ADDS:
  1. Daily P&L aggregation per config (per cell, and per cell x horizon).
  2. CSCV-PBO -- Combinatorially Symmetric Cross-Validation Probability of Backtest
     Overfitting (Bailey, Borwein, Lopez de Prado, Zhu 2014), S=8 blocks (C(8,4)=70
     train/test splits, exactly enumerable -- disclosed simplification from the
     paper's S=16 for tractability).
  3. DSR -- Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014), using the EMPIRICAL
     cross-sectional variance of the N trial Sharpe ratios actually computed here
     (not an assumed value) as V[SR_n], and empirical skew/kurtosis of the flagged
     cell's own trade-level return series.
  4. Bonferroni and Sidak corrected significance thresholds at multiple N definitions.
  5. Effective-independent-trials estimate via (a) average pairwise correlation of the
     daily return matrix, Neff = N / (1 + (N-1)*rho_bar); (b) PCA participation ratio,
     Neff_pca = (sum(eigvals))^2 / sum(eigvals^2).

Pre-registered choices (fixed before inspecting any number produced by this script):
  - Fixed horizon for the cross-config daily matrix = "reod_pts" (flat-by-15:25 exit),
    the same convention win/loss horizon most cells' own argmax already selected, and
    the only horizon common to all 23 cells without re-opening the horizon-search
    question inside the matrix itself.
  - S1-F 84-cell grid: reuse SELLSIDE_20260710/s1_sensitivity/surface_trades.csv verbatim
    (day, ent, struct, sl, net) -- already-run trade-level net pts per cell.
  - alpha = 0.05 one-sided (all reported edges are directional / signed).
"""
from __future__ import annotations

import sys
import gc
import json
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
EMA_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729"
SB_DIR = EMA_DIR / "signal_budget"
S1_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1_sensitivity"
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/OVERFIT_AUDIT_20260729"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(EMA_DIR))
sys.path.insert(0, str(SB_DIR))
import stage1_signal_test as s1  # noqa: E402
import measure_signal_budget as msb  # noqa: E402

GAMMA_EM = 0.5772156649015329  # Euler-Mascheroni constant
ALPHA = 0.05


# ---------------------------------------------------------------------------
# generic stats machinery
# ---------------------------------------------------------------------------

def sharpe(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2 or x.std(ddof=1) == 0:
        return np.nan
    return float(x.mean() / x.std(ddof=1))


def cscv_pbo(matrix: pd.DataFrame, S: int = 8):
    """Combinatorially Symmetric Cross-Validation PBO (Bailey/Borwein/Lopez de Prado/Zhu 2014).
    matrix: T x N daily returns (NaN -> 0, i.e. no trade that config that day)."""
    M = matrix.fillna(0.0).values
    T, N = M.shape
    idx = np.arange(T)
    blocks = np.array_split(idx, S)
    half = S // 2
    logits = []
    for train_sel in itertools.combinations(range(S), half):
        train_idx = np.concatenate([blocks[i] for i in train_sel])
        test_idx = np.concatenate([blocks[i] for i in range(S) if i not in train_sel])
        Mtr, Mte = M[train_idx], M[test_idx]
        with np.errstate(invalid="ignore", divide="ignore"):
            sr_tr = Mtr.mean(axis=0) / Mtr.std(axis=0, ddof=1)
            sr_te = Mte.mean(axis=0) / Mte.std(axis=0, ddof=1)
        sr_tr = np.where(np.isfinite(sr_tr), sr_tr, -np.inf)
        sr_te = np.where(np.isfinite(sr_te), sr_te, -np.inf)
        best_n = int(np.argmax(sr_tr))
        rank = int((sr_te <= sr_te[best_n]).sum())  # 1..N
        omega = min(max(rank / (N + 1), 1e-9), 1 - 1e-9)
        logits.append(float(np.log(omega / (1 - omega))))
    logits = np.array(logits)
    pbo = float((logits <= 0).mean())
    return pbo, logits


def expected_max_sr(N: int, var_sr: float) -> float:
    if N <= 1 or not np.isfinite(var_sr) or var_sr <= 0:
        return 0.0
    return float(np.sqrt(var_sr) * (
        (1 - GAMMA_EM) * stats.norm.ppf(1 - 1.0 / N) + GAMMA_EM * stats.norm.ppf(1 - 1.0 / (N * np.e))
    ))


def dsr(sr_hat: float, n_obs: int, skew: float, kurt_nonexcess: float, N: int, var_sr_cross: float):
    """Deflated Sharpe Ratio, Bailey & Lopez de Prado (2014). kurt_nonexcess: normal=3."""
    sr0 = expected_max_sr(N, var_sr_cross)
    denom = np.sqrt(max(1 - skew * sr_hat + (kurt_nonexcess - 1) / 4.0 * sr_hat ** 2, 1e-9))
    z = (sr_hat - sr0) * np.sqrt(max(n_obs - 1, 1)) / denom
    return float(stats.norm.cdf(z)), sr0, float(z)


def sidak_alpha(alpha: float, N: float) -> float:
    return float(1 - (1 - alpha) ** (1.0 / N))


def bonferroni_alpha(alpha: float, N: float) -> float:
    return float(alpha / N)


def effective_n(matrix: pd.DataFrame):
    M = matrix.fillna(0.0)
    corr = M.corr().values
    N = corr.shape[0]
    iu = np.triu_indices(N, k=1)
    rho_bar = float(np.nanmean(corr[iu])) if len(iu[0]) else 0.0
    neff_corr = N / (1 + (N - 1) * rho_bar) if (1 + (N - 1) * rho_bar) > 0 else N
    eigvals = np.linalg.eigvalsh(corr)
    eigvals = np.clip(eigvals, 0, None)
    neff_pca = float((eigvals.sum() ** 2) / (np.sum(eigvals ** 2))) if eigvals.sum() > 0 else N
    return rho_bar, float(neff_corr), neff_pca


# ---------------------------------------------------------------------------
# 1. Regenerate the 23 signal-budget cells (build period only) with FULL per-trade frames
# ---------------------------------------------------------------------------

def forward_stats_cached(by_day: dict, entries: pd.DataFrame) -> pd.DataFrame:
    """Reimplementation of msb.forward_stats using a PRE-COMPUTED by_day dict
    (avoids recomputing spot.index.date -- an expensive object-array build -- once
    per cell). Logic verified line-for-line identical to measure_signal_budget.forward_stats."""
    HORIZONS = msb.HORIZONS
    out = []
    for _, r in entries.iterrows():
        t0, sgn = r["t"], int(r["dir"])
        day = by_day.get(pd.Timestamp(t0).date())
        if day is None:
            continue
        fwd = day[day.index > t0]
        if fwd.empty:
            continue
        e = float(fwd["open"].iloc[0])
        if not np.isfinite(e) or e <= 0:
            continue
        rec = {"t": t0, "dir": sgn, "entry": e, "date": pd.Timestamp(t0).date()}
        for h in HORIZONS:
            w = fwd[fwd.index <= t0 + pd.Timedelta(minutes=h)]
            if len(w):
                px = float(w["close"].iloc[-1])
                rec[f"r{h}_pct"] = sgn * (px / e - 1)
                rec[f"r{h}_pts"] = sgn * (px - e)
            else:
                rec[f"r{h}_pct"] = np.nan
                rec[f"r{h}_pts"] = np.nan
        flat_cut = pd.Timestamp(pd.Timestamp(t0).date()) + pd.Timedelta(hours=msb.FLAT_H, minutes=msb.FLAT_M)
        flat = fwd[fwd.index <= flat_cut]
        if len(flat):
            px = float(flat["close"].iloc[-1])
            rec["reod_pct"] = sgn * (px / e - 1)
            rec["reod_pts"] = sgn * (px - e)
        else:
            rec["reod_pct"] = rec["reod_pts"] = np.nan
        out.append(rec)
    return pd.DataFrame(out)


def build_entries():
    """Regenerate the 23 signal DEFINITIONS only (timestamps+dir), cheap. Forward-stats
    (the expensive, memory-heavy step) is applied one cell at a time in main()."""
    spot = s1.load_spot()
    bars5 = msb.resample(spot, "5min")
    bars15 = msb.resample(spot, "15min")
    daily = msb.daily_bars(spot)
    wk_lv, mo_lv = msb.week_month_levels(daily)

    entries = {}
    st_cache = {}
    for tf_name, bars in [("5min", bars5), ("15min", bars15)]:
        for period, mult in [(10, 3), (7, 2), (14, 3)]:
            sig = msb.supertrend_flips(bars, period, mult)
            label = f"supertrend_{tf_name}_ATR{period}_x{mult}"
            st_cache[(tf_name, period, mult)] = sig
            entries[label] = sig

    entries["volbrk_keltner_squeeze_release"] = msb.keltner_squeeze_release(bars5)
    entries["volbrk_atr_expansion"] = msb.atr_expansion(bars5)
    entries["volbrk_orb_volfilter"] = msb.orb_vol_filter(bars5)

    sweeps = msb.sweep_signals(bars15)
    for name, sig in sweeps.items():
        entries[f"sweep_{name}"] = sig

    wk_brk, wk_rej = msb.level_breakout_reject(bars15, wk_lv)
    mo_brk, mo_rej = msb.level_breakout_reject(bars15, mo_lv)
    rn_brk, rn_rej = msb.round_number_levels(bars15)
    entries.update({
        "sr_week_breakout": wk_brk, "sr_week_reject": wk_rej,
        "sr_month_breakout": mo_brk, "sr_month_reject": mo_rej,
        "sr_round_breakout": rn_brk, "sr_round_reject": rn_rej,
    })

    atrexp15_sig = msb.atr_expansion(bars15)
    st_15 = st_cache[("15min", 10, 3)]
    sr_frames = [wk_brk, wk_rej, mo_brk, mo_rej, rn_brk, rn_rej]
    buckets = msb.confluence_buckets(spot, bars15, st_15, atrexp15_sig, sweeps, sr_frames)
    for k, sig in sorted(buckets.items()):
        entries[f"confluence_stack{k}"] = sig

    del bars5, bars15, daily, wk_lv, mo_lv, st_cache, sweeps, wk_brk, wk_rej, mo_brk, mo_rej
    del rn_brk, rn_rej, atrexp15_sig, st_15, sr_frames, buckets
    gc.collect()
    return spot, entries


def main():
    print("Regenerating 23 signal-budget cell DEFINITIONS...", flush=True)
    spot, entries = build_entries()
    print(f"  got {len(entries)} raw signal defs; building by_day cache once...", flush=True)
    by_day = {d: g for d, g in spot.groupby(spot.index.date)}
    print(f"  by_day cache: {len(by_day)} sessions", flush=True)

    HCOLS = ["r15_pts", "r30_pts", "r60_pts", "r120_pts", "reod_pts"]

    daily_cols = {}
    sr_23 = {}
    sr_115 = {}
    flagged_frames = {}  # keep full arrays only for the 2 named candidates

    for label, sig in entries.items():
        if sig is None or sig.empty:
            continue
        sig = sig.copy()
        sig["date"] = pd.to_datetime(sig["t"]).dt.date
        b = sig[sig["date"] <= msb.BUILD_END]
        if b.empty:
            continue
        f = forward_stats_cached(by_day, b)
        if f.empty:
            continue
        print(f"  [{label}] n_build={len(b)} n_scored={len(f)}", flush=True)

        daily_cols[label] = f.groupby("date")["reod_pts"].sum()
        sr_23[label] = sharpe(f["reod_pts"].dropna().values)
        for col in HCOLS:
            if col in f.columns:
                x = f[col].dropna().values
                if len(x) >= 10:
                    sr_115[f"{label}::{col}"] = sharpe(x)
        if label in ("sweep_priorday_reclaim", "confluence_stack4"):
            flagged_frames[label] = f.copy()
        del f, sig, b
        gc.collect()

    daily_matrix = pd.DataFrame(daily_cols).sort_index()
    daily_matrix.to_csv(OUT / "signal_budget_daily_matrix_reod.csv")
    print(f"  daily matrix: {daily_matrix.shape}", flush=True)

    pbo23, logits23 = cscv_pbo(daily_matrix, S=8)
    rho_bar, neff_corr, neff_pca = effective_n(daily_matrix)
    print(f"  PBO(N=23, reod, S=8) = {pbo23:.4f}  rho_bar={rho_bar:.4f} "
          f"Neff_corr={neff_corr:.2f} Neff_pca={neff_pca:.2f}", flush=True)

    sr_115_vals = np.array([v for v in sr_115.values() if np.isfinite(v)])
    var_sr_115 = float(np.var(sr_115_vals, ddof=1))
    print(f"  N(cell x horizon) sub-trials with SR computed = {len(sr_115_vals)}; "
          f"var(SR)={var_sr_115:.6f}", flush=True)

    sr_23_vals = np.array([v for v in sr_23.values() if np.isfinite(v)])
    var_sr_23 = float(np.var(sr_23_vals, ddof=1))

    # ---- flagged candidates: sweep_priorday_reclaim, confluence_stack4 ----
    results = {}
    for cand in ["sweep_priorday_reclaim", "confluence_stack4"]:
        f = flagged_frames.get(cand)
        if f is None:
            results[cand] = {"error": "not regenerated (empty in build period)"}
            continue
        x = f["reod_pts"].dropna().values
        n_obs = len(x)
        sr_hat = sharpe(x)
        skew = float(stats.skew(x, bias=False))
        kurt_nonexcess = float(stats.kurtosis(x, fisher=False, bias=False))
        t_naive = sr_hat * np.sqrt(n_obs)
        p_naive_one_sided = float(1 - stats.t.cdf(t_naive, df=n_obs - 1))

        out_row = {
            "n_obs": n_obs, "sr_hat_per_trade": sr_hat, "skew": skew,
            "kurtosis_nonexcess": kurt_nonexcess, "t_naive_recomputed": t_naive,
            "p_naive_one_sided": p_naive_one_sided,
        }
        for N_label, N_val, var_sr in [
            ("N=23_cells_reod", 23, var_sr_23),
            ("N=115_cells_x_horizons", len(sr_115_vals), var_sr_115),
            ("N=133_session_subtrials", 133, var_sr_115),  # conservative: reuse richer var estimate
        ]:
            d, sr0, z = dsr(sr_hat, n_obs, skew, kurt_nonexcess, N_val, var_sr)
            out_row[f"DSR_{N_label}"] = d
            out_row[f"SR0_deflator_{N_label}"] = sr0
            out_row[f"sidak_alpha_{N_label}"] = sidak_alpha(ALPHA, N_val)
            out_row[f"bonferroni_alpha_{N_label}"] = bonferroni_alpha(ALPHA, N_val)
            t_crit = stats.t.ppf(1 - sidak_alpha(ALPHA, N_val), df=n_obs - 1)
            out_row[f"t_crit_sidak_{N_label}"] = float(t_crit)
        results[cand] = out_row

    with open(OUT / "signal_budget_dsr_pbo.json", "w") as fh:
        json.dump({
            "pbo_N23_reod_S8": pbo23,
            "n_logit_splits": len(logits23),
            "logits_N23": logits23.tolist(),
            "rho_bar_daily_returns": rho_bar,
            "neff_corr": neff_corr,
            "neff_pca": neff_pca,
            "var_sr_across_23_reod": var_sr_23,
            "var_sr_across_115_cellxhorizon": var_sr_115,
            "sr_23_by_cell": sr_23,
            "candidates": results,
        }, fh, indent=2, default=str)
    print("Wrote signal_budget_dsr_pbo.json", flush=True)

    # -------------------------------------------------------------------
    # 2. S1-F 84-cell grid (real, already-run data: surface_trades.csv)
    # -------------------------------------------------------------------
    print("\nS1-F 84-cell grid...", flush=True)
    st = pd.read_csv(S1_DIR / "surface_trades.csv", parse_dates=["day"])
    st["cell"] = st["ent"].astype(str) + "|" + st["struct"].astype(str) + "|SL" + st["sl"].astype(str)
    n_cells = st["cell"].nunique()
    print(f"  cells={n_cells}  rows={len(st)}", flush=True)

    pivot = st.pivot_table(index="day", columns="cell", values="net", aggfunc="sum")
    pivot.to_csv(OUT / "s1f_daily_matrix_84cells.csv")
    pbo84, logits84 = cscv_pbo(pivot, S=8)
    rho84, neff84_corr, neff84_pca = effective_n(pivot)
    print(f"  PBO(N=84,S=8) = {pbo84:.4f}  rho_bar={rho84:.4f} Neff_corr={neff84_corr:.2f} "
          f"Neff_pca={neff84_pca:.2f}", flush=True)

    sr_84 = {}
    for cell, g in st.groupby("cell"):
        sr_84[cell] = sharpe(g["net"].values)
    sr_84_vals = np.array([v for v in sr_84.values() if np.isfinite(v)])
    var_sr_84 = float(np.var(sr_84_vals, ddof=1))

    primary_cell = "09:20|straddle+0|SL30"
    g = st[st["cell"] == primary_cell]
    x = g["net"].values
    n_obs = len(x)
    sr_hat = sharpe(x)
    skew = float(stats.skew(x, bias=False))
    kurt_nonexcess = float(stats.kurtosis(x, fisher=False, bias=False))
    t_naive = sr_hat * np.sqrt(n_obs)
    d84, sr0_84, z84 = dsr(sr_hat, n_obs, skew, kurt_nonexcess, n_cells, var_sr_84)
    d150, sr0_150, z150 = dsr(sr_hat, n_obs, skew, kurt_nonexcess, 150, var_sr_84)

    s1f_out = {
        "n_cells_84_verified": int(n_cells),
        "primary_cell": primary_cell,
        "n_obs_primary": int(n_obs),
        "sr_hat_primary_per_trade": sr_hat,
        "skew_primary": skew,
        "kurtosis_nonexcess_primary": kurt_nonexcess,
        "t_naive_recomputed": float(t_naive),
        "p_naive_one_sided": float(1 - stats.t.cdf(t_naive, df=n_obs - 1)),
        "PBO_N84_S8": pbo84,
        "rho_bar_84": rho84,
        "neff_corr_84": neff84_corr,
        "neff_pca_84": neff84_pca,
        "var_sr_across_84": var_sr_84,
        "DSR_N84": d84, "SR0_deflator_N84": sr0_84,
        "DSR_N150_conservative": d150, "SR0_deflator_N150": sr0_150,
        "sidak_alpha_N84": sidak_alpha(ALPHA, n_cells),
        "sidak_alpha_N150": sidak_alpha(ALPHA, 150),
        "sr_84_by_cell": sr_84,
    }
    with open(OUT / "s1f_dsr_pbo.json", "w") as fh:
        json.dump(s1f_out, fh, indent=2, default=str)
    print("Wrote s1f_dsr_pbo.json", flush=True)
    print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()
