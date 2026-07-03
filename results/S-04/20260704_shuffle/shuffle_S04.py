# -*- coding: utf-8 -*-
"""
S-04 short-strangle (14-DTE, 50% managed) PRE-IC SHUFFLE
Arjun Rao / Quant. Same honest decomposition applied to S-02, adapted for S-04's
"no selection signal" structure => decompose across REGIME, not selection.

Denominator: strangle_managed = signed P&L as fraction of SPOT (STABLE denom).
Book P&L in EXIT period (man_exit month). Margin basis = 12% SPAN (=ret/0.12).
"""
import sys, json, os
import numpy as np, pandas as pd

ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
sys.path.insert(0, ROOT + r"/Shreyas_Ionic_AMC/04_RND_LAB/lib")
import guards as G

OUT = ROOT + r"/results/S-04/20260704_shuffle"
DATA = ROOT + r"/intraday_options_strategy/buying/shortlist_shortvol.parquet"
SEED = 20260704
rng = np.random.default_rng(SEED)

# ----------------------------------------------------------------------------
# 1. PRE-REGISTERED KILL CRITERIA (written before metrics computed)
# ----------------------------------------------------------------------------
PREREG = {
    "registered_claim": "+1.75%/spot forward, 88% hit",
    "kill_criteria": {
        "K1_denominator": "FAIL if strangle_managed is NOT a stable %-of-spot (e.g. any |ret|>0.60 explosion row, or denom not spot). Debit-denominator artifact = instant FAKE.",
        "K2_calm_block_dependence": "FAIL-PRE-IC if >70% of total P&L comes from the 2024-04..2026-06 low-vol block AND the pre-block (2021-23) mean is not independently positive with >=30 trades/year coverage.",
        "K3_tail_honesty": "FAIL if worst correlated-cluster month (all concurrent strangles summed) exceeds -8% of aggregate spot-notional, i.e. a single month can wipe >4x the annual edge, AND management does not materially cut it.",
        "K4_managed_value": "Management sleeve is only a REAL 'signal' if it EITHER adds mean return OR cuts the worst-trade/worst-month tail with bootstrap 95% CI excluding the no-effect (delta=0) line. If it does neither -> the only signal is unconditional short-vol.",
        "K5_margin_reality": "FLAG (not auto-fail) if mean return on 12% SPAN margin < 1%/month OR worst month on margin basis < -50% (margin call / ruin risk).",
        "K6_regime_split": "FAIL-PRE-IC if 2024-26 mean >> 2021-23 mean with non-overlapping bootstrap CIs (edge is a regime artifact, not structural)."
    },
    "verdict_rule": "CLEARS-FOR-IC only if edge survives OUTSIDE the calm block OR is honestly registered as regime-conditional with the crash caveat. Otherwise FAILS-PRE-IC.",
    "note": "S-04 trades EVERY name EVERY cycle (no cross-sectional selection) => shuffle test is REGIME decomposition, not label-permutation. The 50% managed exit is the ONLY discretionary lever -> tested explicitly (K4)."
}

# ----------------------------------------------------------------------------
# 2. LOAD + DENOMINATOR SANITY
# ----------------------------------------------------------------------------
df = pd.read_parquet(DATA)
for c in ["exp", "entry", "man_exit"]:
    df[c] = pd.to_datetime(df[c])
n0 = len(df)

RET = "strangle_managed"   # managed (primary)
HOLD = "strangle_hold"     # hold-to-expiry (comparison)

# EXIT-PERIOD booking: managed trade books in man_exit month; held books in exp month.
# man_exit already == exp for held trades, so exit_ym is correct for both.
df["exit_dt"] = df["man_exit"]
df["exit_ym"] = df["exit_dt"].dt.to_period("M")
df["exit_year"] = df["exit_dt"].dt.year
df["exp_year"] = df["exp"].dt.year

r = df[RET]
denom = {
    "ret_col": RET,
    "denominator_stated": "SPOT",
    "min": float(r.min()), "max": float(r.max()),
    "mean": float(r.mean()), "median": float(r.median()), "std": float(r.std()),
    "rows_abs_gt_0.20": int((r.abs() > 0.20).sum()),
    "rows_abs_gt_0.50": int((r.abs() > 0.50).sum()),
    "rows_abs_gt_0.60_EXPLOSION": int((r.abs() > 0.60).sum()),
    "margin_ratio_median_should_be_8.333": float(
        (df["strangle_managed_margin"] / df[RET])[df[RET].abs() > 1e-9].median()),
    "implied_span_frac_of_spot": float(
        1.0 / (df["strangle_managed_margin"] / df[RET])[df[RET].abs() > 1e-9].median()),
    "K1_denominator_PASS": bool((r.abs() > 0.60).sum() == 0),
}

# ----------------------------------------------------------------------------
# 3a. PER-YEAR + BUILD vs FORWARD (booked in EXIT year), with partial-year flags
# ----------------------------------------------------------------------------
def yr_stats(g, col):
    x = g[col].dropna()
    return dict(n=int(len(x)), mean_pct=round(float(x.mean())*100, 4),
                median_pct=round(float(x.median())*100, 4),
                sum_pct=round(float(x.sum())*100, 2),
                hit=round(float((x > 0).mean())*100, 1),
                worst_pct=round(float(x.min())*100, 3),
                best_pct=round(float(x.max())*100, 3),
                n_expiry_months=int(g["exp"].dt.to_period("M").nunique()))

per_year = {}
for y, g in df.groupby("exit_year"):
    d = yr_stats(g, RET)
    d["partial_year"] = d["n_expiry_months"] < 12
    per_year[int(y)] = d

# build (<=2024-03) vs forward (>=2024-04) using EXIT date
BLK_START = pd.Timestamp("2024-04-01")
BLK_END = pd.Timestamp("2026-06-30")   # low-vol block per Vikram
pre = df[df["exit_dt"] < BLK_START]
blk = df[(df["exit_dt"] >= BLK_START) & (df["exit_dt"] <= BLK_END)]
post = df[df["exit_dt"] > BLK_END]

build_fwd = {
    "pre_2024_04 (build)": yr_stats(pre, RET),
    "low_vol_block_2024_04_to_2026_06": yr_stats(blk, RET),
    "post_2026_06": yr_stats(post, RET),
}

# ----------------------------------------------------------------------------
# 3b. CALM-BLOCK SHARE OF TOTAL P&L
# ----------------------------------------------------------------------------
tot_pnl = float(df[RET].sum())
blk_pnl = float(blk[RET].sum())
pre_pnl = float(pre[RET].sum())
calm_share = {
    "total_pnl_units_of_spot": round(tot_pnl, 3),
    "low_vol_block_pnl": round(blk_pnl, 3),
    "block_share_of_total_pct": round(blk_pnl / tot_pnl * 100, 1),
    "block_share_of_trades_pct": round(len(blk) / n0 * 100, 1),
    "pre_block_pnl": round(pre_pnl, 3),
    "pre_block_mean_pct": round(float(pre[RET].mean())*100, 4),
    "pre_block_n": int(len(pre)),
    "pre_block_hit_pct": round(float((pre[RET] > 0).mean())*100, 1),
    "K2_note": "block_share of P&L vs block_share of trades tells if it's just more trades or fatter per-trade edge",
}

# ----------------------------------------------------------------------------
# 3c. TAIL HONESTY: worst trade, worst MONTH (concurrent summed), correlated cluster
#    Book each trade in exit month; aggregate = SUM of per-trade %-of-spot (equal
#    1-unit-of-spot notional per strangle). worst month = worst correlated cluster.
# ----------------------------------------------------------------------------
def monthly_agg(frame, col):
    # equal-notional: each trade = 1 unit of spot; monthly P&L = sum of ret
    m = frame.groupby("exit_ym")[col].agg(["sum", "mean", "count"])
    return m

m_managed = monthly_agg(df, RET)
m_hold = monthly_agg(df, HOLD)

worst_trade_row = df.loc[df[RET].idxmin(), ["sym", "entry", "exp", "man_exit", "spot", RET, HOLD]]
worst_month_managed = m_managed["sum"].idxmin()
worst_month_hold = m_hold["sum"].idxmin()

# correlated-cluster scenario: in the worst historical month, ALL open strangles
# fire together. Report the summed loss AND per-unit-of-notional avg that month,
# expressed as % of that month's aggregate spot-notional (n trades * 1 unit).
def cluster_scenario(frame, col, month):
    sub = frame[frame["exit_ym"] == month]
    n = len(sub)
    summed = float(sub[col].sum())          # total P&L in units of spot
    per_notional = summed / n if n else 0.0  # avg %-of-spot that month
    return dict(month=str(month), n_positions=n,
                summed_pnl_units_of_spot=round(summed, 3),
                pct_of_month_notional=round(per_notional*100, 3),
                n_losers=int((sub[col] < 0).sum()),
                worst_single_pct=round(float(sub[col].min())*100, 3))

tail = {
    "worst_trade": {
        "sym": worst_trade_row["sym"], "entry": str(worst_trade_row["entry"].date()),
        "exp": str(worst_trade_row["exp"].date()), "exit": str(worst_trade_row["man_exit"].date()),
        "managed_pct": round(float(worst_trade_row[RET])*100, 3),
        "hold_pct": round(float(worst_trade_row[HOLD])*100, 3),
    },
    "worst_month_managed": cluster_scenario(df, RET, worst_month_managed),
    "worst_month_hold": cluster_scenario(df, HOLD, worst_month_hold),
    "worst_5_months_managed": [
        cluster_scenario(df, RET, mm) for mm in m_managed["sum"].nsmallest(5).index],
    "monthly_managed_pnl_std": round(float(m_managed["sum"].std()), 3),
    "monthly_managed_pnl_worst": round(float(m_managed["sum"].min()), 3),
    "avg_positions_per_month": round(float(m_managed["count"].mean()), 1),
    "max_positions_in_a_month": int(m_managed["count"].max()),
}
# K3: worst-month per-notional loss (correlated cluster, avg %-of-spot in worst month)
tail["K3_worst_cluster_pct_of_notional_MANAGED"] = tail["worst_5_months_managed"][0]["pct_of_month_notional"]
tail["K3_worst_cluster_pct_of_notional_HOLD"] = cluster_scenario(df, HOLD, worst_month_hold)["pct_of_month_notional"]

# ----------------------------------------------------------------------------
# 3d. MARGIN-BASIS REALITY (~12% SPAN)
# ----------------------------------------------------------------------------
MG = "strangle_managed_margin"
mg = df[MG]
m_margin_month = df.groupby("exit_ym")[MG].sum()
margin = {
    "mean_per_trade_on_margin_pct": round(float(mg.mean())*100, 3),
    "median_per_trade_on_margin_pct": round(float(mg.median())*100, 3),
    "worst_trade_on_margin_pct": round(float(mg.min())*100, 2),
    "best_trade_on_margin_pct": round(float(mg.max())*100, 2),
    "worst_month_on_margin_pct_summed": round(float(m_margin_month.min())*100, 2),
    "span_frac": 0.12,
    "K5_note": "on 12% SPAN a -X% of spot becomes -8.33X% of margin; ruin/ margin-call risk lives here",
}

# ----------------------------------------------------------------------------
# 4. MANAGED vs HOLD (the ONLY signal S-04 has), same trades, BOOTSTRAP
# ----------------------------------------------------------------------------
paired = df[[RET, HOLD]].dropna()
delta = paired[RET] - paired[HOLD]   # managed minus hold, per trade
n = len(paired)
B = 10000
boot_delta = np.empty(B)
boot_tail_delta = np.empty(B)   # difference in 5th-percentile (tail)
idx_all = np.arange(n)
managed_arr = paired[RET].to_numpy()
hold_arr = paired[HOLD].to_numpy()
for b in range(B):
    s = rng.integers(0, n, n)
    boot_delta[b] = managed_arr[s].mean() - hold_arr[s].mean()
    boot_tail_delta[b] = np.percentile(managed_arr[s], 5) - np.percentile(hold_arr[s], 5)

managed_vs_hold = {
    "n_paired": int(n),
    "mean_managed_pct": round(float(paired[RET].mean())*100, 4),
    "mean_hold_pct": round(float(paired[HOLD].mean())*100, 4),
    "mean_delta_managed_minus_hold_pct": round(float(delta.mean())*100, 4),
    "delta_boot_CI95_pct": [round(float(np.percentile(boot_delta, 2.5))*100, 4),
                            round(float(np.percentile(boot_delta, 97.5))*100, 4)],
    "delta_excludes_zero": bool(np.percentile(boot_delta, 2.5) > 0 or np.percentile(boot_delta, 97.5) < 0),
    "worst_trade_managed_pct": round(float(paired[RET].min())*100, 3),
    "worst_trade_hold_pct": round(float(paired[HOLD].min())*100, 3),
    "p05_managed_pct": round(float(np.percentile(paired[RET], 5))*100, 3),
    "p05_hold_pct": round(float(np.percentile(paired[HOLD], 5))*100, 3),
    "tail_delta_p05_boot_CI95_pct": [round(float(np.percentile(boot_tail_delta, 2.5))*100, 4),
                                     round(float(np.percentile(boot_tail_delta, 97.5))*100, 4)],
    "tail_delta_excludes_zero": bool(np.percentile(boot_tail_delta, 2.5) > 0 or np.percentile(boot_tail_delta, 97.5) < 0),
    "std_managed_pct": round(float(paired[RET].std())*100, 4),
    "std_hold_pct": round(float(paired[HOLD].std())*100, 4),
    "hit_managed_pct": round(float((paired[RET] > 0).mean())*100, 1),
    "hit_hold_pct": round(float((paired[HOLD] > 0).mean())*100, 1),
}

# ----------------------------------------------------------------------------
# 5. REGIME STRESS: 2021-23 (pre-refill) vs 2024-26; worst realized-vol months
#    Bootstrap the mean-difference between the two regimes.
# ----------------------------------------------------------------------------
early_reg = df[df["exit_year"] <= 2023]
late_reg = df[df["exit_year"] >= 2024]
ea = early_reg[RET].to_numpy(); la = late_reg[RET].to_numpy()
ne, nl = len(ea), len(la)
boot_reg = np.empty(B)
for b in range(B):
    boot_reg[b] = la[rng.integers(0, nl, nl)].mean() - ea[rng.integers(0, ne, ne)].mean()

# worst realized-vol months in-sample = the worst-summed months (proxy). Also
# per-year monthly worst.
regime = {
    "early_2021_23": dict(n=ne, mean_pct=round(float(ea.mean())*100, 4),
                          hit_pct=round(float((ea > 0).mean())*100, 1),
                          worst_pct=round(float(ea.min())*100, 3),
                          boot_mean_CI95_pct=[round(float(np.percentile(
                              [ea[rng.integers(0, ne, ne)].mean() for _ in range(2000)], 2.5))*100, 4),
                              round(float(np.percentile(
                              [ea[rng.integers(0, ne, ne)].mean() for _ in range(2000)], 97.5))*100, 4)]),
    "late_2024_26": dict(n=nl, mean_pct=round(float(la.mean())*100, 4),
                         hit_pct=round(float((la > 0).mean())*100, 1),
                         worst_pct=round(float(la.min())*100, 3)),
    "late_minus_early_boot_CI95_pct": [round(float(np.percentile(boot_reg, 2.5))*100, 4),
                                       round(float(np.percentile(boot_reg, 97.5))*100, 4)],
    "regimes_differ (CI excludes 0)": bool(np.percentile(boot_reg, 2.5) > 0 or np.percentile(boot_reg, 97.5) < 0),
    "worst_realized_vol_months_managed_summed": [
        {"month": str(mm), "summed_pnl": round(float(m_managed.loc[mm, "sum"]), 3),
         "n": int(m_managed.loc[mm, "count"])}
        for mm in m_managed["sum"].nsmallest(6).index],
}

# ----------------------------------------------------------------------------
# DEGENERATE DETECTORS (monthly equity as the "daily_ret" proxy)
# ----------------------------------------------------------------------------
# Build a monthly return series on margin basis (real capital) for degeneracy check
monthly_margin_ret = df.groupby("exit_ym")[MG].mean().sort_index()  # avg margin ret per month
flags = G.degenerate_flags(monthly_margin_ret, trades=df.rename(columns={RET: "ret"}),
                           ret_col="ret", sym_col="sym")

# ----------------------------------------------------------------------------
# WRITE
# ----------------------------------------------------------------------------
config = {
    "strategy": "S-04 short-strangle 14-DTE, 5% OTM CE+PE, buy-back at 50% credit else hold to expiry",
    "run": "20260704_shuffle (pre-IC)",
    "analyst": "Arjun Rao / Quant",
    "prereg": PREREG,
    "lineage": {
        "data_file": DATA,
        "full_file_rows": n0,
        "n_symbols": int(df.sym.nunique()),
        "entry_range": [str(df.entry.min().date()), str(df.entry.max().date())],
        "exp_range": [str(df.exp.min().date()), str(df.exp.max().date())],
        "exit_range": [str(df.man_exit.min().date()), str(df.man_exit.max().date())],
        "return_col_primary": RET,
        "return_col_comparison": HOLD,
        "booking": "EXIT-period (man_exit month); held trades book in exp month",
        "margin_basis": "12% SPAN (margin col = ret/0.12, verified ratio ~8.333)",
        "managed_early_close_frac": round(float((df.man_exit < df.exp).mean()), 3),
        "seed": SEED,
    },
    "denominator_sanity": denom,
}
metrics = {
    "per_year_exit_booked": per_year,
    "build_vs_forward": build_fwd,
    "calm_block_share": calm_share,
    "tail_honesty": tail,
    "margin_reality": margin,
    "managed_vs_hold_bootstrap": managed_vs_hold,
    "regime_stress": regime,
    "degenerate_flags": flags,
}

with open(OUT + "/config.json", "w") as f:
    json.dump(config, f, indent=2, default=str)
with open(OUT + "/metrics.json", "w") as f:
    json.dump(metrics, f, indent=2, default=str)

# ---- console summary ----
print("=== DENOMINATOR ===")
print(json.dumps(denom, indent=1))
print("\n=== PER-YEAR (exit-booked) ===")
for y, d in per_year.items():
    print(y, d)
print("\n=== BUILD vs FORWARD ===")
print(json.dumps(build_fwd, indent=1))
print("\n=== CALM BLOCK SHARE ===")
print(json.dumps(calm_share, indent=1))
print("\n=== TAIL HONESTY ===")
print(json.dumps(tail, indent=1, default=str))
print("\n=== MARGIN REALITY (12% SPAN) ===")
print(json.dumps(margin, indent=1))
print("\n=== MANAGED vs HOLD (bootstrap) ===")
print(json.dumps(managed_vs_hold, indent=1))
print("\n=== REGIME STRESS ===")
print(json.dumps(regime, indent=1, default=str))
print("\n=== DEGENERATE FLAGS ===")
print(flags)
print("\nSAVED ->", OUT)
