"""Vectorized (merge_asof-based) re-derivation of the same reod_pts per-trade series the
slow row-by-row engine computes -- written as a faster, independently-implemented cross
check after the first (correct but very slow, ~35 rows/CPU-sec) engine appeared stalled
under this session's heavy concurrent-agent CPU load. Logic cross-validated against the
already-published signal_budget_report.json numbers (n and t_nw for sweep_priorday_reclaim
and confluence_stack4) before being trusted for anything else.
"""
from __future__ import annotations
import sys, gc, json, itertools
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
EMA_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729"
SB_DIR = EMA_DIR / "signal_budget"
S1_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1_sensitivity"
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/OVERFIT_AUDIT_20260729"

sys.path.insert(0, str(EMA_DIR)); sys.path.insert(0, str(SB_DIR))
import stage1_signal_test as s1  # noqa
import measure_signal_budget as msb  # noqa

GAMMA_EM = 0.5772156649015329
ALPHA = 0.05


def reod_pts_vectorized(spot: pd.DataFrame, entries: pd.DataFrame) -> pd.DataFrame:
    """Vectorized equivalent of msb.forward_stats()[['reod_pts']]. spot index sorted
    1-min bars with open/close. entries: columns t (Timestamp), dir (+-1)."""
    if entries.empty:
        return pd.DataFrame(columns=["t", "dir", "date", "reod_pts"])
    e = entries[["t", "dir"]].copy().sort_values("t").reset_index(drop=True)
    e["date"] = pd.to_datetime(e["t"]).dt.date

    bars = spot[["open", "close"]].sort_index()
    bar_t = bars.index.to_series(name="bar_t").reset_index(drop=True)

    # --- entry: first bar strictly AFTER t (same-day only, enforced after the merge) ---
    left = e[["t"]].sort_values("t")
    ent = pd.merge_asof(left, bars["open"].rename("entry_px").reset_index().rename(columns={bars.index.name or "index": "bar_t"}),
                         left_on="t", right_on="bar_t", direction="forward", allow_exact_matches=False)
    ent = ent.set_index(left.index)

    # --- exit: last bar with time <= that day's 15:25 ---
    flat_cut = pd.to_datetime(e["date"].astype(str)) + pd.Timedelta(hours=15, minutes=25)
    right = pd.DataFrame({"flat_cut": flat_cut.values}, index=e.index).sort_values("flat_cut")
    exitp = pd.merge_asof(right, bars["close"].rename("exit_px").reset_index().rename(columns={bars.index.name or "index": "bar_t"}),
                           left_on="flat_cut", right_on="bar_t", direction="backward")
    exitp = exitp.set_index(right.index).sort_index()

    out = e.copy()
    out["entry_px"] = ent["entry_px"].reindex(out.index).values
    out["entry_bar_t"] = ent["bar_t"].reindex(out.index).values
    out["exit_px"] = exitp["exit_px"].reindex(out.index).values
    out["exit_bar_t"] = exitp["bar_t"].reindex(out.index).values

    # enforce same-day (entry bar and exit bar must fall on t's date); drop otherwise
    ok = (
        out["entry_px"].notna() & out["exit_px"].notna() &
        (pd.to_datetime(out["entry_bar_t"]).dt.date == out["date"]) &
        (pd.to_datetime(out["exit_bar_t"]).dt.date == out["date"]) &
        (out["entry_bar_t"] > out["t"])
    )
    out = out[ok].copy()
    out["reod_pts"] = out["dir"] * (out["exit_px"] - out["entry_px"])
    return out[["t", "dir", "date", "reod_pts"]]


def sharpe(x):
    x = np.asarray(x, dtype=float); x = x[np.isfinite(x)]
    if len(x) < 2 or x.std(ddof=1) == 0:
        return np.nan
    return float(x.mean() / x.std(ddof=1))


def cscv_pbo(matrix: pd.DataFrame, S: int = 8):
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
        rank = int((sr_te <= sr_te[best_n]).sum())
        omega = min(max(rank / (N + 1), 1e-9), 1 - 1e-9)
        logits.append(float(np.log(omega / (1 - omega))))
    logits = np.array(logits)
    return float((logits <= 0).mean()), logits


def expected_max_sr(N, var_sr):
    if N <= 1 or not np.isfinite(var_sr) or var_sr <= 0:
        return 0.0
    return float(np.sqrt(var_sr) * ((1 - GAMMA_EM) * stats.norm.ppf(1 - 1.0 / N) +
                                     GAMMA_EM * stats.norm.ppf(1 - 1.0 / (N * np.e))))


def dsr(sr_hat, n_obs, skew, kurt_nonexcess, N, var_sr_cross):
    sr0 = expected_max_sr(N, var_sr_cross)
    denom = np.sqrt(max(1 - skew * sr_hat + (kurt_nonexcess - 1) / 4.0 * sr_hat ** 2, 1e-9))
    z = (sr_hat - sr0) * np.sqrt(max(n_obs - 1, 1)) / denom
    return float(stats.norm.cdf(z)), sr0, float(z)


def sidak_alpha(alpha, N):
    return float(1 - (1 - alpha) ** (1.0 / N))


def effective_n(matrix: pd.DataFrame):
    M = matrix.fillna(0.0)
    corr = M.corr().values
    N = corr.shape[0]
    iu = np.triu_indices(N, k=1)
    rho_bar = float(np.nanmean(corr[iu])) if len(iu[0]) else 0.0
    neff_corr = N / (1 + (N - 1) * rho_bar) if (1 + (N - 1) * rho_bar) > 0 else N
    eigvals = np.clip(np.linalg.eigvalsh(corr), 0, None)
    neff_pca = float((eigvals.sum() ** 2) / np.sum(eigvals ** 2)) if eigvals.sum() > 0 else N
    return rho_bar, float(neff_corr), neff_pca


def build_entries():
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
            st_cache[(tf_name, period, mult)] = sig
            entries[f"supertrend_{tf_name}_ATR{period}_x{mult}"] = sig
    entries["volbrk_keltner_squeeze_release"] = msb.keltner_squeeze_release(bars5)
    entries["volbrk_atr_expansion"] = msb.atr_expansion(bars5)
    entries["volbrk_orb_volfilter"] = msb.orb_vol_filter(bars5)
    sweeps = msb.sweep_signals(bars15)
    for name, sig in sweeps.items():
        entries[f"sweep_{name}"] = sig
    wk_brk, wk_rej = msb.level_breakout_reject(bars15, wk_lv)
    mo_brk, mo_rej = msb.level_breakout_reject(bars15, mo_lv)
    rn_brk, rn_rej = msb.round_number_levels(bars15)
    entries.update({"sr_week_breakout": wk_brk, "sr_week_reject": wk_rej,
                     "sr_month_breakout": mo_brk, "sr_month_reject": mo_rej,
                     "sr_round_breakout": rn_brk, "sr_round_reject": rn_rej})
    atrexp15_sig = msb.atr_expansion(bars15)
    st_15 = st_cache[("15min", 10, 3)]
    sr_frames = [wk_brk, wk_rej, mo_brk, mo_rej, rn_brk, rn_rej]
    buckets = msb.confluence_buckets(spot, bars15, st_15, atrexp15_sig, sweeps, sr_frames)
    for k, sig in sorted(buckets.items()):
        entries[f"confluence_stack{k}"] = sig
    return spot, entries


def main():
    print("build_entries...", flush=True)
    spot, entries = build_entries()
    print(f"{len(entries)} raw signal defs", flush=True)

    daily_cols, sr_23, trade_arrays = {}, {}, {}
    for label, sig in entries.items():
        if sig is None or sig.empty:
            continue
        sig = sig.copy()
        sig["date"] = pd.to_datetime(sig["t"]).dt.date
        b = sig[sig["date"] <= msb.BUILD_END]
        if b.empty:
            continue
        f = reod_pts_vectorized(spot, b)
        if f.empty:
            continue
        n_report = {"sweep_priorday_reclaim": 1775, "confluence_stack4": 35,
                    "sweep_intraday_reclaim": 3557}.get(label)
        print(f"[{label}] n_build={len(b)} n_scored={len(f)}"
              + (f"  (report json n={n_report})" if n_report else ""), flush=True)
        daily_cols[label] = f.groupby("date")["reod_pts"].sum()
        sr_23[label] = sharpe(f["reod_pts"].values)
        if label in ("sweep_priorday_reclaim", "confluence_stack4"):
            trade_arrays[label] = f["reod_pts"].values.copy()
        del f
    gc.collect()

    daily_matrix = pd.DataFrame(daily_cols).sort_index()
    daily_matrix.to_csv(OUT / "signal_budget_daily_matrix_reod_FAST.csv")
    print(f"daily matrix {daily_matrix.shape}", flush=True)

    pbo23, logits23 = cscv_pbo(daily_matrix, S=8)
    rho_bar, neff_corr, neff_pca = effective_n(daily_matrix)
    print(f"PBO(N=23,reod,S=8)={pbo23:.4f} rho_bar={rho_bar:.4f} Neff_corr={neff_corr:.2f} Neff_pca={neff_pca:.2f}", flush=True)

    sr_23_vals = np.array([v for v in sr_23.values() if np.isfinite(v)])
    var_sr_23 = float(np.var(sr_23_vals, ddof=1))

    results = {}
    for cand in ["sweep_priorday_reclaim", "confluence_stack4"]:
        x = trade_arrays.get(cand)
        if x is None:
            results[cand] = {"error": "empty"}
            continue
        n_obs = len(x)
        sr_hat = sharpe(x)
        skew = float(stats.skew(x, bias=False))
        kurt = float(stats.kurtosis(x, fisher=False, bias=False))
        t_naive = sr_hat * np.sqrt(n_obs)
        row = {"n_obs": n_obs, "sr_hat": sr_hat, "skew": skew, "kurtosis_nonexcess": kurt,
               "t_naive_recomputed": t_naive,
               "p_naive_one_sided": float(1 - stats.t.cdf(t_naive, df=n_obs - 1))}
        for Nlabel, Nval in [("N23", 23), ("N133", 133), ("N261", 261), ("N394", 394)]:
            d, sr0, z = dsr(sr_hat, n_obs, skew, kurt, Nval, var_sr_23)
            row[f"DSR_{Nlabel}"] = d
            row[f"SR0_{Nlabel}"] = sr0
            row[f"sidak_a_{Nlabel}"] = sidak_alpha(ALPHA, Nval)
        results[cand] = row

    with open(OUT / "signal_budget_dsr_pbo_FAST.json", "w") as fh:
        json.dump({"pbo_N23_reod_S8": pbo23, "rho_bar": rho_bar, "neff_corr": neff_corr,
                    "neff_pca": neff_pca, "var_sr_across_23": var_sr_23,
                    "sr_23_by_cell": sr_23, "candidates": results}, fh, indent=2, default=str)
    print("wrote signal_budget_dsr_pbo_FAST.json", flush=True)

    # ---- S1-F 84-cell ----
    print("\nS1-F 84-cell grid...", flush=True)
    st = pd.read_csv(S1_DIR / "surface_trades.csv", parse_dates=["day"])
    st["cell"] = st["ent"].astype(str) + "|" + st["struct"].astype(str) + "|SL" + st["sl"].astype(str)
    n_cells = st["cell"].nunique()
    pivot = st.pivot_table(index="day", columns="cell", values="net", aggfunc="sum")
    pivot.to_csv(OUT / "s1f_daily_matrix_84cells.csv")
    pbo84, logits84 = cscv_pbo(pivot, S=8)
    rho84, neff84_corr, neff84_pca = effective_n(pivot)
    print(f"PBO(N=84,S=8)={pbo84:.4f} rho_bar={rho84:.4f} Neff_corr={neff84_corr:.2f} Neff_pca={neff84_pca:.2f}", flush=True)
    sr_84 = {cell: sharpe(g["net"].values) for cell, g in st.groupby("cell")}
    sr_84_vals = np.array([v for v in sr_84.values() if np.isfinite(v)])
    var_sr_84 = float(np.var(sr_84_vals, ddof=1))
    primary_cell = "09:20|straddle+0|SL30"
    g = st[st["cell"] == primary_cell]
    x = g["net"].values
    n_obs = len(x); sr_hat = sharpe(x)
    skew = float(stats.skew(x, bias=False)); kurt = float(stats.kurtosis(x, fisher=False, bias=False))
    t_naive = sr_hat * np.sqrt(n_obs)
    d84, sr0_84, z84 = dsr(sr_hat, n_obs, skew, kurt, n_cells, var_sr_84)
    d150, sr0_150, z150 = dsr(sr_hat, n_obs, skew, kurt, 150, var_sr_84)
    s1f_out = {"n_cells": int(n_cells), "primary_cell": primary_cell, "n_obs": int(n_obs),
               "sr_hat": sr_hat, "skew": skew, "kurtosis_nonexcess": kurt,
               "t_naive_recomputed": float(t_naive),
               "p_naive_one_sided": float(1 - stats.t.cdf(t_naive, df=n_obs - 1)),
               "PBO_N84_S8": pbo84, "rho_bar_84": rho84, "neff_corr_84": neff84_corr, "neff_pca_84": neff84_pca,
               "var_sr_across_84": var_sr_84,
               "DSR_N84": d84, "SR0_N84": sr0_84, "DSR_N150": d150, "SR0_N150": sr0_150,
               "sidak_a_N84": sidak_alpha(ALPHA, n_cells), "sidak_a_N150": sidak_alpha(ALPHA, 150),
               "sr_84_by_cell": sr_84}
    with open(OUT / "s1f_dsr_pbo.json", "w") as fh:
        json.dump(s1f_out, fh, indent=2, default=str)
    print("wrote s1f_dsr_pbo.json", flush=True)
    print("DONE.", flush=True)


if __name__ == "__main__":
    main()
