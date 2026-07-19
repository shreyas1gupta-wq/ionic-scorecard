"""
Tara Singh (E-015, Execution/TCA) -- ALPHA_RANKER return reconciliation.
Builds ONE consistent, deployable net-of-cost decile-LS statistic for:
  - the 7-leg composite (canonical_7leg_pit_scores.parquet, PIT-investable)
  - EY alone (value_EY leg, capstone_legs.parquet, restricted to same universe)
  - momentum alone (mom_resid_plain, rebuilt fresh via run_long_confirm's own
    builder -- the SAME construction the canonical composite uses)
All three go through the identical harness decile machinery, the identical
cost model (COST_STANDARDS.md, APPROVED), the identical horizon-aware
annualization (1Y label = already annual, no *12), and TWO extra realism
gates that are NEW here (not previously applied anywhere in ALPHA_RANKER):
  (a) drop bottom-quintile mktcap (micro-cap) names from the eligible
      cross-section entirely -- liquidity policing, can't reliably short these
  (b) per-date winsorize target_raw at 1%/99% -- kills the handful of
      >>1000% 1Y-return prints (data artifacts / corporate-action-unadjusted
      prices) that inflate a MEAN-based decile spread without touching a
      RANK-based IC.
Outputs: printed table + json dump. No fabrication -- every number here is
computed from on-disk panel_pit.parquet / capstone_legs.parquet /
canonical_7leg_pit_scores.parquet rows, same cost table as harness.py.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

RND_DIR = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\rnd")
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))
import harness  # noqa
import run_long_confirm as LC  # noqa

PANEL_PIT = RND_DIR / "panel" / "panel_pit.parquet"
COMPOSITE_SCORES = RND_DIR / "panel" / "canonical_7leg_pit_scores.parquet"
CAPSTONE_LEGS = RND_DIR / "panel" / "capstone_legs.parquet"

MIN_NAMES = 20
PERIODS_PER_YEAR = 12

print("Loading panel_pit.parquet (PIT-investable universe, survivorship-free)...")
panel_pit = pd.read_parquet(PANEL_PIT)
panel_pit["date"] = pd.to_datetime(panel_pit["date"])
print(f"  rows={len(panel_pit)}  dates={panel_pit['date'].nunique()}  symbols={panel_pit['symbol'].nunique()}")

# corporate-action guard (same as CANONICAL_7LEG_PIT_1Y construction)
guard = panel_pit["disc_event_in_window_1Y"].fillna(0) > 0
print(f"  corp-action guard drops {guard.sum()} rows")
base = panel_pit.loc[~guard, ["date", "symbol", "mktcap_log", "fwd_ret_1Y_raw", "fwd_ret_1Y_resid"]].copy()

# liquidity tier (same quantile method as harness._mktcap_tier) computed PER DATE
def tier_col(df):
    q = df.groupby("date")["mktcap_log"].rank(pct=True)
    df = df.copy()
    df["tier"] = pd.cut(q, bins=[-0.01, 0.20, 0.50, 0.80, 1.01],
                         labels=["micro", "small", "mid", "large"])
    return df

base = tier_col(base)
print(f"  tier counts:\n{base['tier'].value_counts()}")

n_before = len(base)
investable = base[base["tier"] != "micro"].copy()
print(f"  drop micro-cap tier from eligible universe: {n_before} -> {len(investable)} rows")

# per-date winsorization of the RAW target return at 1%/99% -- kills
# corporate-action/unadjusted-price artifacts (max observed fwd_ret_1Y_raw
# before this step, see printed check) without touching rank-based IC.
raw_max_before = investable["fwd_ret_1Y_raw"].max()
raw_min_before = investable["fwd_ret_1Y_raw"].min()
print(f"  fwd_ret_1Y_raw range before winsorize: [{raw_min_before:.2f}, {raw_max_before:.2f}]")

def winsorize(g, col, lo=0.01, hi=0.99):
    lo_v, hi_v = g[col].quantile([lo, hi])
    return g[col].clip(lo_v, hi_v)

investable["target_raw_w"] = investable.groupby("date", group_keys=False).apply(
    lambda g: winsorize(g, "fwd_ret_1Y_raw"), include_groups=False)
print(f"  fwd_ret_1Y_raw range AFTER per-date 1%/99% winsorize: "
      f"[{investable['target_raw_w'].min():.2f}, {investable['target_raw_w'].max():.2f}]")

cost_info = harness._read_cost_standards_bps()
print(f"  cost source approved={cost_info['approved']}  tiers={cost_info['tier_bps_rt']}")


def decile_ls(factor_df, label, use_winsorized=True, promotion_stress=1, era=None):
    """factor_df: DataFrame with columns date, symbol, factor.
    Merges onto `investable`, computes decile top-bottom spread of
    target_raw (or winsorized target_raw_w), turnover, cost drag, net.
    era: optional (start, end) date-string tuple to restrict the sample."""
    tgt_col = "target_raw_w" if use_winsorized else "fwd_ret_1Y_raw"
    m = factor_df.merge(investable[["date", "symbol", tgt_col, "tier"]], on=["date", "symbol"], how="inner")
    m = m.dropna(subset=["factor", tgt_col])
    if era is not None:
        m = m[(m["date"] >= era[0]) & (m["date"] < era[1])]
    ls_rows, top_sets, tier_counts_all = [], {}, []
    for d, g in m.groupby("date"):
        if len(g) < MIN_NAMES:
            continue
        try:
            g = g.assign(decile=pd.qcut(g["factor"].rank(method="first"), 10, labels=False, duplicates="drop"))
        except ValueError:
            continue
        if g["decile"].nunique() < 3:
            continue
        top_d, bot_d = g["decile"].max(), g["decile"].min()
        top_ret = g.loc[g["decile"] == top_d, tgt_col].mean()
        bot_ret = g.loc[g["decile"] == bot_d, tgt_col].mean()
        ls_rows.append({"date": d, "ls": top_ret - bot_ret})
        top_sets[d] = set(g.loc[g["decile"] == top_d, "symbol"])
        tier_counts_all.append(g["tier"].value_counts(normalize=True))
    ls = pd.DataFrame(ls_rows).set_index("date")["ls"] if ls_rows else pd.Series(dtype=float)
    n_periods = len(ls)
    mean_period = float(ls.mean()) if n_periods else float("nan")
    ann_gross = harness.annualize_ls_return(mean_period, "1Y")  # 1Y label already annual -> no *12
    turnover = harness._turnover(top_sets)
    if tier_counts_all:
        tier_dist = pd.concat(tier_counts_all, axis=1).mean(axis=1)
    else:
        tier_dist = pd.Series(dtype=float)
    blended_bps = float(sum(tier_dist.get(t, 0) * cost_info["tier_bps_rt"].get(t, 25)
                            for t in ["large", "mid", "small"]))  # micro excluded (dropped from universe)
    ann_cost_drag = (turnover if not np.isnan(turnover) else 0.0) * (blended_bps / 10000.0) * PERIODS_PER_YEAR
    ann_cost_drag_stressed = ann_cost_drag * promotion_stress
    net = ann_gross - ann_cost_drag
    net_2x = ann_gross - ann_cost_drag_stressed if promotion_stress != 1 else None
    return {
        "label": label, "n_periods": n_periods, "mean_period_ls": mean_period,
        "ann_gross": ann_gross, "turnover": turnover, "blended_cost_bps_rt": blended_bps,
        "ann_cost_drag_1x": ann_cost_drag, "net_1x": net,
        "ann_cost_drag_2x": ann_cost_drag * 2, "net_2x": ann_gross - ann_cost_drag * 2,
        "tier_dist": tier_dist.to_dict(),
    }


results = {}

# ---- 1. composite (7-leg, PIT, min_legs=5, as already built) ----
print("\n=== Composite (canonical_7leg_pit_scores.parquet) ===")
comp = pd.read_parquet(COMPOSITE_SCORES)
comp["date"] = pd.to_datetime(comp["date"])
comp_f = comp.rename(columns={"composite_rank_avg": "factor"})[["date", "symbol", "factor"]]
results["composite_7leg"] = decile_ls(comp_f, "7-leg composite (PIT+liquidity+winsor)")
results["composite_7leg_no_winsor"] = decile_ls(comp_f, "7-leg composite (PIT+liquidity, NO winsor)", use_winsorized=False)

# ---- 2. EY alone (value_EY leg from capstone_legs.parquet) ----
print("=== EY alone (value_EY leg) ===")
legs = pd.read_parquet(CAPSTONE_LEGS)
legs["date"] = pd.to_datetime(legs["date"])
ey = legs[legs["leg"] == "value_EY"][["date", "symbol", "value"]].rename(columns={"value": "factor"})
results["ey_alone"] = decile_ls(ey, "EY alone (PIT+liquidity+winsor)")
results["ey_alone_no_winsor"] = decile_ls(ey, "EY alone (PIT+liquidity, NO winsor)", use_winsorized=False)

# ---- 3. momentum alone (mom_resid_plain, rebuilt fresh, same builder canonical uses) ----
print("=== Momentum alone (mom_resid_plain, fresh build) ===")
panel_long, close, bench = LC.load_all()
dates = LC._panel_dates(panel_long)
mom_plain = LC.build_mom_resid_12_1(close, bench, dates)
mom_f = mom_plain.reset_index()
mom_f.columns = ["date", "symbol", "factor"]
results["momentum_alone"] = decile_ls(mom_f, "Momentum alone (plain, PIT+liquidity+winsor)")
results["momentum_alone_no_winsor"] = decile_ls(mom_f, "Momentum alone (plain, PIT+liquidity, NO winsor)", use_winsorized=False)

# ---- 4. ERA SPLIT: full-history (2005-2020) vs recent (2020-2025) --
#     tests the red-team hypothesis that the edge has decayed and the
#     "true live" number is much closer to the recent-era figure.
print("=== ERA SPLIT (2005-2020 vs 2020-2025) ===")
for name, fdf in [("composite_7leg", comp_f), ("ey_alone", ey), ("momentum_alone", mom_f)]:
    results[f"{name}_era_2005_2020"] = decile_ls(fdf, f"{name} 2005-2020 (PIT+liquidity+winsor)", era=("2005-01-01", "2020-01-01"))
    results[f"{name}_era_2020_2025"] = decile_ls(fdf, f"{name} 2020-2025 (PIT+liquidity+winsor)", era=("2020-01-01", "2026-01-01"))

# ---- 5. candidate: trend/MA65-slope leg (the H002-family single representative
#     already in the frozen 7 -- reconciled the same way for comparability) ----
print("=== Candidate: trend_ma65_slope (H002-family representative) ===")
trend = legs[legs["leg"] == "trend_ma65_slope"][["date", "symbol", "value"]].rename(columns={"value": "factor"})
results["trend_ma65_candidate"] = decile_ls(trend, "Trend MA65-slope candidate (PIT+liquidity+winsor)")

print("\n\n================ SUMMARY (annualized, 1Y horizon) ================")
hdr = f"{'label':45s} {'n_per':>6s} {'gross':>8s} {'cost1x':>8s} {'net1x':>8s} {'cost2x':>8s} {'net2x':>8s} {'turn':>6s}"
print(hdr)
for k, r in results.items():
    print(f"{r['label']:45s} {r['n_periods']:6d} {r['ann_gross']*100:7.2f}% {r['ann_cost_drag_1x']*100:7.2f}% "
          f"{r['net_1x']*100:7.2f}% {r['ann_cost_drag_2x']*100:7.2f}% {r['net_2x']*100:7.2f}% {r['turnover']*100:5.1f}%")

out_path = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\rnd\wave4\reconcile_results.json")
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump({k: {kk: (vv if not isinstance(vv, dict) else vv) for kk, vv in v.items() if kk != "tier_dist"} | {"tier_dist": v["tier_dist"]}
                for k, v in results.items()}, fh, indent=2, default=str)
print(f"\nWritten: {out_path}")
