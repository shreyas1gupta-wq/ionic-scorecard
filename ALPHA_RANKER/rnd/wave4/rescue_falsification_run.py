"""
RESCUE FALSIFICATION -- the placebo the rescreen never ran on ITSELF.
Owner: Dr. Sameer Bhat (Overfit & Sensitivity Analyst). 2026-07-17.

TEST 1 -- NULL-SWEEP FALSIFICATION
  Same MA-slope/distance sweep machinery, exact backlog.json pre-registration:
  H002 = DMA in {20,30,40,50,55,60,65,75,100,120,150,200} x {dist,slope} = 24
  H001 = DMA in {50,65} x {dist,slope,stack} = 6
  -> 30 variants total, all at 1Y (the horizon where this family's real effect
  lives per RESURRECTION_RESCREEN.md S8). Built with the ACTUAL production
  builders (builders_ma.py), same as every card in cards/.

  Rescue score = mean of whichever is available of:
    min(1, |ic_mean|/0.05), |decile monotonicity|, sign_frac across the 6
    regime buckets (bull/bear/sideways x low/normal/high vol)
  -- identical construction to RESURRECTION_RESCREEN.md S2, minus net_LS/
  spread (not rebuildable from scratch here; the doc's own rule is to drop
  unavailable components, not fabricate them).

  Two comparisons, both against the pre-registered bar rescue_score>=0.30:
   (a) REAL block-bootstrap: resample the 45 valid panel dates with
       replacement, recombine each variant's OWN real per-date IC/decile
       stats (no reshuffling -- true signal preserved), report clear-rate.
   (b) NULL shuffle: permute fwd_ret_1Y_resid across symbols WITHIN each date
       (destroys the true cross-section, preserves each date's return
       distribution and regime label), rerun the full 30-variant sweep,
       take the best variant, report clear-rate across ~75 independent
       shuffles.

TEST 2 -- ORTHOGONALITY OF THE 40 TIER-A RESCUES
  Every one of the 40 Tier-A factor_ids in resurrection_candidates.json is
  rebuilt with the ACTUAL production builder (builders_ma.py / builders_mom.py
  -- the same functions harness.evaluate() calls for every card), then
  correlated pairwise via date-by-date Spearman (averaged across all valid
  panel dates -- standard factor-correlation construction). Effective
  independent-bet count via (a) eigenvalue participation ratio (b) connected
  components at |corr|>=0.5.
"""
from __future__ import annotations
import sys, json, time
from pathlib import Path

import numpy as np
import pandas as pd

RND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
import builders_ma
import builders_mom

PANEL_PATH = RND_DIR / "panel" / "panel.parquet"
OUT_JSON = Path(__file__).resolve().parent / "rescue_falsification_results.json"

MIN_NAMES = 20
RESCUE_BAR = 0.30
N_SHUFFLES = 100
N_BOOTSTRAP = 100
SEED = 20260717

t0 = time.time()
panel = pd.read_parquet(PANEL_PATH)
panel["date"] = pd.to_datetime(panel["date"])
regime_lookup = panel.drop_duplicates("date").set_index("date")[["regime_trend", "regime_vol"]]
print(f"[load] panel {panel.shape}, {panel['date'].nunique()} dates, "
      f"{panel['symbol'].nunique()} symbols ({time.time()-t0:.1f}s)")

H002_LENGTHS = [20, 30, 40, 50, 55, 60, 65, 75, 100, 120, 150, 200]
sweep_factors = {}
for n in H002_LENGTHS:
    sweep_factors[f"H002_dist{n}"] = builders_ma.dma_distance_factor(n)(panel)
    sweep_factors[f"H002_slope{n}"] = builders_ma.dma_slope_factor(n)(panel)
for n in (50, 65):
    sweep_factors[f"H001_dist{n}"] = builders_ma.dma_distance_factor(n)(panel)
    sweep_factors[f"H001_slope{n}"] = builders_ma.dma_slope_factor(n)(panel)
    sweep_factors[f"H001_stack{n}"] = builders_ma.dma_stack_factor(n)(panel)
print(f"[build] {len(sweep_factors)} sweep variants built ({time.time()-t0:.1f}s)")

TARGET_COL = "fwd_ret_1Y_resid"
real_target = (panel[["date", "symbol", TARGET_COL]]
               .dropna(subset=[TARGET_COL])
               .set_index(["date", "symbol"])[TARGET_COL])
valid_dates = sorted(real_target.index.get_level_values(0).unique())
print(f"[target] {len(valid_dates)} valid dates for {TARGET_COL}")


def precompute_variant(factor_s: pd.Series, target_s: pd.Series, min_names=MIN_NAMES):
    """One-time (per variant, per target-series) precompute: merged frame +
    factor rank + a FIXED decile bin (from factor only, so it is reusable
    across every null-shuffle rep -- the bin assignment never depends on the
    target)."""
    df = pd.concat([factor_s.rename("factor"), target_s.rename("target")], axis=1).dropna()
    df["n_date"] = df.groupby(level=0)["factor"].transform("size")
    df = df[df["n_date"] >= min_names]
    if df.empty:
        return None
    df["factor_rank"] = df.groupby(level=0)["factor"].rank()
    # decile bin from factor rank fraction (matches qcut ~ equal-frequency bins)
    frac = (df["factor_rank"] - 1) / df["n_date"]
    df["decile_bin"] = np.minimum((frac * 10).astype(int), 9)
    n_bins = df.groupby(level=0)["decile_bin"].transform("nunique")
    df = df[n_bins >= 3]
    return df if not df.empty else None


def score_from_merged(df: pd.DataFrame, target_col="target"):
    """Given a precomputed merged df (with factor_rank/decile_bin/n_date
    columns) and a (possibly re-shuffled) target column, compute ic_mean,
    monotonicity, sign_frac, rescue_score -- fully vectorized (no per-date
    Python loop, no scipy per-group calls)."""
    target_rank = df.groupby(level=0)[target_col].rank()
    d2 = (df["factor_rank"] - target_rank) ** 2
    sum_d2 = d2.groupby(level=0).sum()
    n = df.groupby(level=0)["n_date"].first()
    ic_by_date = 1 - 6 * sum_d2 / (n * (n ** 2 - 1))
    ic_mean = float(ic_by_date.mean())
    if ic_mean == 0 or np.isnan(ic_mean):
        return None

    bin_means = df.groupby([df.index.get_level_values(0), "decile_bin"])[target_col].mean()
    bin_means = bin_means.reset_index()
    bin_means.columns = ["date", "decile_bin", "mean_target"]
    overall = bin_means.groupby("decile_bin")["mean_target"].mean()
    if overall.notna().sum() >= 3:
        # rank correlation via covariance formula (no scipy call)
        x = overall.index.values.astype(float)
        y = overall.values
        xr = pd.Series(x).rank().values
        yr = pd.Series(y).rank().values
        mono = np.corrcoef(xr, yr)[0, 1]
    else:
        mono = np.nan

    dates_idx = ic_by_date.index
    reg = regime_lookup.reindex(dates_idx)
    bucket_means = []
    for col in ("regime_trend", "regime_vol"):
        g = ic_by_date.groupby(reg[col].values).mean()
        bucket_means.extend(g.tolist())
    bucket_means = [b for b in bucket_means if not np.isnan(b)]
    maj_sign = np.sign(ic_mean)
    sign_frac = float(np.mean([np.sign(b) == maj_sign for b in bucket_means])) if bucket_means else np.nan

    comps = [min(1.0, abs(ic_mean) / 0.05)]
    if not np.isnan(mono):
        comps.append(abs(mono))
    if not np.isnan(sign_frac):
        comps.append(sign_frac)
    return {"ic_mean": ic_mean, "mono": float(mono), "sign_frac": sign_frac,
            "rescue_score": float(np.mean(comps)), "n_dates": int(len(ic_by_date))}


# --------------------------------------------------------------------------
# precompute merged frames once per variant (real target)
# --------------------------------------------------------------------------
merged_cache = {}
for name, fac in sweep_factors.items():
    m = precompute_variant(fac, real_target)
    if m is not None:
        merged_cache[name] = m
print(f"[precompute] {len(merged_cache)}/{len(sweep_factors)} variants have usable merged frames "
      f"({time.time()-t0:.1f}s)")

# --------------------------------------------------------------------------
# REAL pass
# --------------------------------------------------------------------------
real_results = {}
for name, df in merged_cache.items():
    r = score_from_merged(df, "target")
    if r:
        real_results[name] = r
real_best_name = max(real_results, key=lambda k: real_results[k]["rescue_score"])
real_best = real_results[real_best_name]
n_real_clear_individually = sum(1 for r in real_results.values() if r["rescue_score"] >= RESCUE_BAR)
print(f"[real] best variant: {real_best_name} rescue_score={real_best['rescue_score']:.3f} "
      f"ic_mean={real_best['ic_mean']:.4f} mono={real_best['mono']:.3f} sign_frac={real_best['sign_frac']:.3f}")
print(f"[real] {n_real_clear_individually}/{len(real_results)} variants individually clear {RESCUE_BAR}")

# --------------------------------------------------------------------------
# REAL BOOTSTRAP -- resample per-date stats (analytic, no raw recompute)
# --------------------------------------------------------------------------
per_variant_ic = {}
per_variant_binmeans = {}
for name, df in merged_cache.items():
    target_rank = df.groupby(level=0)["target"].rank()
    d2 = (df["factor_rank"] - target_rank) ** 2
    sum_d2 = d2.groupby(level=0).sum()
    n = df.groupby(level=0)["n_date"].first()
    ic_by_date = 1 - 6 * sum_d2 / (n * (n ** 2 - 1))
    per_variant_ic[name] = ic_by_date
    bm = df.groupby([df.index.get_level_values(0), "decile_bin"])["target"].mean().unstack()
    per_variant_binmeans[name] = bm

rng = np.random.default_rng(SEED)
boot_clear = 0
boot_scores = []
for b in range(N_BOOTSTRAP):
    samp = rng.choice(valid_dates, size=len(valid_dates), replace=True)
    best = None
    for name in merged_cache:
        ic_by_date = per_variant_ic[name]
        avail = [d for d in samp if d in ic_by_date.index]
        if len(avail) < 4:
            continue
        ic_vals = ic_by_date.reindex(avail)
        ic_mean = float(ic_vals.mean())
        if ic_mean == 0 or np.isnan(ic_mean):
            continue
        bm = per_variant_binmeans[name].reindex(avail)
        overall = bm.mean(axis=0)
        if overall.notna().sum() >= 3:
            xr = pd.Series(overall.index.values.astype(float)).rank().values
            yr = pd.Series(overall.values).rank().values
            mono = np.corrcoef(xr, yr)[0, 1]
        else:
            mono = np.nan
        reg = regime_lookup.reindex(pd.DatetimeIndex(avail))
        bucket_means = []
        for col in ("regime_trend", "regime_vol"):
            g = ic_vals.groupby(reg[col].values).mean()
            bucket_means.extend(g.tolist())
        bucket_means = [x for x in bucket_means if not np.isnan(x)]
        maj_sign = np.sign(ic_mean)
        sign_frac = float(np.mean([np.sign(x) == maj_sign for x in bucket_means])) if bucket_means else np.nan
        comps = [min(1.0, abs(ic_mean) / 0.05)]
        if not np.isnan(mono):
            comps.append(abs(mono))
        if not np.isnan(sign_frac):
            comps.append(sign_frac)
        score = float(np.mean(comps))
        if best is None or score > best:
            best = score
    if best is not None:
        boot_scores.append(best)
        if best >= RESCUE_BAR:
            boot_clear += 1

real_boot_rate = boot_clear / len(boot_scores) if boot_scores else float("nan")
print(f"[real-bootstrap] {boot_clear}/{len(boot_scores)} = {real_boot_rate:.3f} clear {RESCUE_BAR} "
      f"({time.time()-t0:.1f}s)")

# --------------------------------------------------------------------------
# NULL SHUFFLE -- genuinely permute target across symbols WITHIN each date
# --------------------------------------------------------------------------
null_clear = 0
null_scores = []
for s in range(N_SHUFFLES):
    rng_s = np.random.default_rng(SEED + 1000 + s)
    best = None
    for name, df in merged_cache.items():
        shuffled = df["target"].groupby(level=0).transform(
            lambda x: rng_s.permutation(x.values))
        df2 = df.assign(_shuf=shuffled)
        r = score_from_merged(df2, "_shuf")
        if r and (best is None or r["rescue_score"] > best):
            best = r["rescue_score"]
    if best is not None:
        null_scores.append(best)
        if best >= RESCUE_BAR:
            null_clear += 1
    if (s + 1) % 20 == 0:
        print(f"  [null] {s+1}/{N_SHUFFLES} done ({time.time()-t0:.1f}s)")

null_rate = null_clear / len(null_scores) if null_scores else float("nan")
print(f"[null] {null_clear}/{len(null_scores)} = {null_rate:.3f} clear {RESCUE_BAR} on best-of-sweep")
print(f"[null] best-of-sweep dist: mean={np.mean(null_scores):.3f} p50={np.median(null_scores):.3f} "
      f"p90={np.percentile(null_scores,90):.3f} max={np.max(null_scores):.3f}")
p_val = float(np.mean([x >= real_best["rescue_score"] for x in null_scores]))
print(f"[null] P(null best-of-sweep >= real best {real_best['rescue_score']:.3f}) = {p_val:.3f}")

test1_results = {
    "n_variants": len(merged_cache),
    "real_best_variant": real_best_name,
    "real_best": real_best,
    "n_real_variants_clearing_bar_individually": n_real_clear_individually,
    "real_bootstrap_clear_rate": real_boot_rate,
    "real_bootstrap_n": len(boot_scores),
    "null_shuffle_clear_rate": null_rate,
    "null_shuffle_n": len(null_scores),
    "null_best_score_mean": float(np.mean(null_scores)),
    "null_best_score_p50": float(np.median(null_scores)),
    "null_best_score_p90": float(np.percentile(null_scores, 90)),
    "null_best_score_max": float(np.max(null_scores)),
    "empirical_p_null_ge_real": p_val,
    "rescue_bar": RESCUE_BAR,
}

# ==========================================================================
# TEST 2 -- ORTHOGONALITY OF THE 40 TIER-A RESCUES
# ==========================================================================
print("\n=== TEST 2: orthogonality ===")
with open(Path(__file__).resolve().parent / "resurrection_candidates.json") as fh:
    rc = json.load(fh)
tierA = [c for c in rc["forward_test_candidates"] if c.get("confidence_tier") == "A-single-hypothesis"]
print(f"[load] {len(tierA)} Tier-A cards")


def parse_ma(factor_id: str):
    body = factor_id.rsplit("_", 1)[0]
    fam, rest = body.split("_", 1)
    if rest.startswith("slope"):
        return builders_ma.dma_slope_factor(int(rest[len("slope"):]))
    if rest.startswith("dist"):
        return builders_ma.dma_distance_factor(int(rest[len("dist"):]))
    if rest.startswith("stack"):
        return builders_ma.dma_stack_factor(int(rest[len("stack"):]))
    return None


MOM_BUILDERS = {
    "H004_mom_sharpe12m": builders_mom.build_mom_sharpe_12m,
    "H004_mom_sharpe6m": builders_mom.build_mom_sharpe_6m,
    "H004_mom_sharpe3m": builders_mom.build_mom_sharpe_3m,
    "H043_beta_adj_mom": builders_mom.build_beta_adjusted_mom,
    "H003_mom12m1_resid": builders_mom.build_mom_resid_12_1,
    "H041_52whigh_vs_12m1": builders_mom.build_52w_high_proximity,
}

factor_series = {}
for c in tierA:
    fid = c["factor_id"]
    if fid.startswith("H002_") or fid.startswith("H001_"):
        builder = parse_ma(fid)
        s = builder(panel)
    else:
        key = fid if fid in MOM_BUILDERS else fid.rsplit("_", 1)[0]
        if key not in MOM_BUILDERS:
            key = fid
        s = MOM_BUILDERS[key](panel)
    factor_series[fid] = s
print(f"[build] {len(factor_series)} of {len(tierA)} Tier-A factor series built ({time.time()-t0:.1f}s)")

names = list(factor_series.keys())
n = len(names)
corr_sum = np.zeros((n, n))
corr_cnt = np.zeros((n, n))
idx_map = {name: i for i, name in enumerate(names)}

for d in valid_dates:
    cols = {}
    for name in names:
        s = factor_series[name]
        if d in s.index.get_level_values(0):
            cols[name] = s.loc[d]
    if len(cols) < 2:
        continue
    wide = pd.DataFrame(cols).dropna(how="all")
    if len(wide) < MIN_NAMES:
        continue
    rank_wide = wide.rank()
    c = rank_wide.corr(method="pearson", min_periods=MIN_NAMES)
    valid = ~c.isna()
    for a in c.columns:
        ia = idx_map[a]
        for b in c.columns:
            if valid.loc[a, b]:
                corr_sum[ia, idx_map[b]] += c.loc[a, b]
                corr_cnt[ia, idx_map[b]] += 1

with np.errstate(invalid="ignore", divide="ignore"):
    corr_mat = np.where(corr_cnt > 0, corr_sum / np.maximum(corr_cnt, 1), np.nan)
np.fill_diagonal(corr_mat, 1.0)
corr_df = pd.DataFrame(corr_mat, index=names, columns=names)

corr_clean = corr_df.fillna(0.0).values
eigvals = np.linalg.eigvalsh(corr_clean)
eigvals = np.clip(eigvals, 0, None)
pr = (eigvals.sum() ** 2) / (eigvals ** 2).sum()

adj = (np.abs(corr_df.fillna(0.0).values) >= 0.5)
np.fill_diagonal(adj, True)
visited = [False] * n
clusters = []
for i in range(n):
    if visited[i]:
        continue
    stack = [i]
    comp = []
    visited[i] = True
    while stack:
        u = stack.pop()
        comp.append(u)
        for v in range(n):
            if adj[u, v] and not visited[v]:
                visited[v] = True
                stack.append(v)
    clusters.append([names[k] for k in comp])

mean_abs_corr = float(np.nanmean(np.abs(corr_df.values)[~np.eye(n, dtype=bool)]))
print(f"[corr] {n}x{n} matrix built. eigen participation ratio = {pr:.2f} ({time.time()-t0:.1f}s)")
print(f"[corr] connected components at |corr|>=0.5: {len(clusters)} clusters, "
      f"sizes = {sorted([len(cl) for cl in clusters], reverse=True)}")
print(f"[corr] mean |corr| off-diagonal across all pairs: {mean_abs_corr:.3f}")
top_eigvec = None
order = np.argsort(eigvals)[::-1]
top_val = eigvals[order[0]]
print(f"[corr] top eigenvalue = {top_val:.2f} / {n} ({top_val/n*100:.1f}% of total variance)")

test2_results = {
    "n_signals": n,
    "eigen_participation_ratio": float(pr),
    "top_eigenvalue": float(top_val),
    "top_eigenvalue_pct_of_variance": float(top_val / n),
    "n_clusters_at_0.5": len(clusters),
    "clusters": clusters,
    "mean_abs_corr_all_pairs": mean_abs_corr,
}

out = {
    "test1_null_sweep_falsification": test1_results,
    "test2_orthogonality": test2_results,
    "test2_corr_matrix": corr_df.round(3).to_dict(),
}
with open(OUT_JSON, "w") as fh:
    json.dump(out, fh, indent=2, default=float)
print(f"\n[done] wrote {OUT_JSON} ({time.time()-t0:.1f}s total)")
