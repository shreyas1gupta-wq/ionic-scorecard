"""
DEBT 1 -- DSR/PBO on the full trials ledger, correlation-aware (not naive Bonferroni).
Owner: Sameer Bhat (Overfit & Sensitivity). 2026-07-31.

Reuses the firm's OWN existing, already-validated statistical engine
(OVERFIT_AUDIT_20260729/overfit_engine.py: sharpe/cscv_pbo/expected_max_sr/dsr/effective_n)
rather than re-deriving DSR/PBO math from scratch (consolidate-reused-code convention).
That engine already produced real DSR/PBO for SWEEP_E, S1_zscore(killed), CALENDAR,
OVERSHOOT in DSR_D009_20260730/dsr_pbo_results.json. This script:
  1. VERIFIES those by independently recomputing SWEEP_E and CALENDAR from the raw trade
     CSVs (not just re-quoting the JSON).
  2. EXTENDS the same method to the 3 candidates the prior pass never touched: S1-F,
     LD_SELL, THREE_SOLDIERS.
  3. Builds the honest nominal trials ledger across every family run this session.
"""
import numpy as np
import pandas as pd
from scipy import stats
import itertools, json

GAMMA_EM = 0.5772156649015329
R = r"Shreyas_Ionic_AMC/04_RND_LAB/results"


# ---------------------------------------------------------------------------
# Reused engine (verbatim logic from OVERFIT_AUDIT_20260729/overfit_engine.py)
# ---------------------------------------------------------------------------
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
    return float(np.sqrt(var_sr) * (
        (1 - GAMMA_EM) * stats.norm.ppf(1 - 1.0 / N) + GAMMA_EM * stats.norm.ppf(1 - 1.0 / (N * np.e))
    ))


def dsr(sr_hat, n_obs, skew, kurt_nonexcess, N, var_sr_cross):
    sr0 = expected_max_sr(N, var_sr_cross)
    denom = np.sqrt(max(1 - skew * sr_hat + (kurt_nonexcess - 1) / 4.0 * sr_hat ** 2, 1e-9))
    z = (sr_hat - sr0) * np.sqrt(max(n_obs - 1, 1)) / denom
    return float(stats.norm.cdf(z)), sr0, float(z)


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


def candidate_report(name, daily_matrix, headline_series, N_raw_family, label=""):
    """daily_matrix: T x N_cells (day-indexed) for the WHOLE family, used for effective_n + CSCV.
       headline_series: the actual candidate's own daily P&L (Rs or pts) used for Sharpe/skew/DSR."""
    rho_bar, neff_corr, neff_pca = effective_n(daily_matrix)
    x = np.asarray(headline_series, dtype=float)
    x = x[np.isfinite(x)]
    n_obs = len(x)
    sr_hat = sharpe(x)
    skew = float(stats.skew(x))
    kurt = float(stats.kurtosis(x, fisher=False))  # non-excess (normal=3)
    var_sr = np.nanvar([sharpe(daily_matrix.iloc[:, j].dropna().values) for j in range(daily_matrix.shape[1])], ddof=1)
    dsr_corr, sr0_corr, z_corr = dsr(sr_hat, n_obs, skew, kurt, max(neff_corr, 1.001), var_sr)
    pbo, _ = cscv_pbo(daily_matrix, S=8)
    out = dict(candidate=name, label=label, n_obs=n_obs, sharpe_hat=round(sr_hat, 4),
               skew=round(skew, 4), kurt_nonexcess=round(kurt, 4),
               N_raw_measured=daily_matrix.shape[1], N_raw_family_stated=N_raw_family,
               avg_abs_corr=round(rho_bar, 4), N_eff_corr=round(neff_corr, 4),
               N_eff_pca=round(neff_pca, 4), DSR_using_Neff=round(dsr_corr, 4),
               PBO_CSCV=round(pbo, 4))
    return out


results = []

# =============================================================================
# 1. SWEEP_E -- VERIFY the existing DSR_D009 number (DSR 0.9963/PBO 0.000/Neff 1.33)
# =============================================================================
print("=" * 100); print("1. SWEEP_E / SWEEP_11YR family"); print("=" * 100)
sw_cfgs = ["A_intraday_stop30", "B_intraday_trail25", "C_intraday_trail40",
           "D_overnight1_trail40", "E_swing3_trail60", "F_intraday_tgt200"]
# IMPORTANT: use the FLAT "_1lot" files, not "_kelly01" -- kelly01 sizing is the version
# MASTER_STRATEGY_TABLE.md itself flags as DISCREDITED (unbounded lot-count compounding with
# no ruin constraint, maxDD -266%/-319%/-409%, CAGR 1e10-1e17%). A first pass of this script
# used kelly01 and got kurt_nonexcess=54.3 (vs a sane ~4-8 elsewhere) -- a direct symptom of
# that same contamination leaking into what should be a clean multiplicity check. DSR_D009's
# own AF_grid used "no_carry_1lot" for exactly this reason; matching that choice here.
sw_daily = {}
for cfg in sw_cfgs:
    df = pd.read_csv(f"{R}/SWEEP_11YR_20260729/trades_{cfg}_1lot.csv", parse_dates=["date"])
    sw_daily[cfg] = df.groupby(df["date"].dt.normalize())["net"].sum()
sw_matrix = pd.DataFrame(sw_daily).sort_index()
headline = sw_matrix["E_swing3_trail60"].dropna()
rep = candidate_report("SWEEP_E", sw_matrix, headline, N_raw_family=6,
                        label="6 exit-mgmt variants, ONE shared entry signal (1-lot flat sizing, "
                              "matching DSR_D009's own AF_grid convention -- kelly01 rejected, see note above)")
print(rep)
print("Reproduction check vs DSR_D009 published (N_eff=1.330, avg_corr=0.702, DSR=0.9963):")
print(f"  mine: N_eff={rep['N_eff_corr']}, avg_corr={rep['avg_abs_corr']}")
results.append(rep)

# also compute WITH kelly01 for full disclosure of how much the sizing convention matters
sw_daily_k = {}
for cfg in sw_cfgs:
    df = pd.read_csv(f"{R}/SWEEP_11YR_20260729/trades_{cfg}_kelly01.csv", parse_dates=["date"])
    sw_daily_k[cfg] = df.groupby(df["date"].dt.normalize())["net"].sum()
sw_matrix_k = pd.DataFrame(sw_daily_k).sort_index()
headline_k = sw_matrix_k["E_swing3_trail60"].dropna()
rep_k = candidate_report("SWEEP_E_kelly01_DISCREDITED_SIZING", sw_matrix_k, headline_k, N_raw_family=6,
                          label="SAME family, DISCREDITED kelly01 sizing -- shown ONLY to disclose "
                                "sizing-convention sensitivity, NOT a candidate reading")
print("[DISCLOSURE, not a valid candidate reading]", rep_k)
results.append(rep_k)

# =============================================================================
# 2. CALENDAR_1x1_3d_before -- VERIFY existing (DSR 0.576, Neff 1.82, N_raw=24)
# =============================================================================
print("\n" + "=" * 100); print("2. CALENDAR_1x1_3d_before / RATIO_CALENDAR grid_a (24 configs)"); print("=" * 100)
ga = pd.read_csv(f"{R}/RATIO_CALENDAR_20260730/grid_a_trades_raw.csv", parse_dates=["exit_day"])
ga["cfg"] = ga["strike_struct"] + "|" + ga["ratio"] + "|" + ga["exit_variant"]
cal_matrix = ga.pivot_table(index=ga["exit_day"].dt.normalize(), columns="cfg", values="net_pts", aggfunc="sum")
headline_cal = ga[(ga.strike_struct == "ATM_ATM") & (ga.ratio == "1x1") & (ga.exit_variant == "3d_before")] \
    .drop_duplicates(subset=["day0", "near_expiry"]).set_index(pd.to_datetime(
        ga[(ga.strike_struct == "ATM_ATM") & (ga.ratio == "1x1") & (ga.exit_variant == "3d_before")]
        .drop_duplicates(subset=["day0", "near_expiry"])["exit_day"]))["net_pts"]
rep = candidate_report("CALENDAR_1x1_3d_before", cal_matrix, headline_cal, N_raw_family=24,
                        label="grid_a: strike_struct x ratio x exit_variant (verified 24 distinct configs)")
print(rep)
print("Reproduction check vs DSR_D009 published (N_eff=1.818, avg_corr=0.530, DSR=0.576):")
print(f"  mine: N_eff={rep['N_eff_corr']}, avg_corr={rep['avg_abs_corr']}")
print("NOTE: grid_b adds 4 more configs (roll-variant family, separate mechanism, 645 trades) -- "
      "not merged into this matrix (different trade cadence/columns); RATIO_CALENDAR verified total "
      "= 24+4 = 28 distinct configs, NOT the ~140 STRATEGY_DOSSIER.md prose estimate -- that figure "
      "could not be reconciled against any single file in this pass and is likely a stale/rough guess "
      "from an earlier, larger planned grid that was not fully executed. Using 28 (verified) below.")
results.append(rep)

# =============================================================================
# 3. S1-F -- NEW. Family = SELLSIDE_20260710/s1_sensitivity (84-cell surface, the largest
#    homogeneous sub-grid, representative of the ~150-cell family per S1F_SPEC.md:39)
# =============================================================================
print("\n" + "=" * 100); print("3. S1-F / SELLSIDE_20260710 s1_sensitivity (84-cell surface)"); print("=" * 100)
s1sens = pd.read_csv(f"{R}/SELLSIDE_20260710/s1_sensitivity/surface_trades.csv", parse_dates=["day"])
s1sens["cfg"] = s1sens["struct"] + "|" + s1sens["ent"] + "|sl" + s1sens["sl"].astype(str)
s1_matrix = s1sens.pivot_table(index=s1sens["day"].dt.normalize(), columns="cfg", values="net", aggfunc="sum")
# headline = the REGISTERED config: straddle (ATM, i.e. struct=='straddle-0' or similar), ent 09:20, sl 30
cfg_candidates = [c for c in s1_matrix.columns if "straddle" in c.lower() and "09:20" in c and "sl30" in c]
print("candidate registered-config columns found:", cfg_candidates[:5], "... total", len(cfg_candidates))
# fall back: use final_three's actual registered S1 series (cost-modeled) as the headline if available
f3 = pd.read_csv(f"{R}/SELLSIDE_20260710/final_three/final_three_trades.csv", parse_dates=["day"])
headline_s1 = f3[f3.strat == "S1"].groupby(f3["day"].dt.normalize())["net"].sum()
rep = candidate_report("S1-F", s1_matrix, headline_s1, N_raw_family=150,
                        label="84-cell sensitivity surface (struct x entry-time x SL) used as multiplicity "
                              "proxy for the full ~150-cell design family (S1F_SPEC.md:39); headline P&L = "
                              "final_three/S1 (the cost-modeled, registered series)")
print(rep)
print("[INFERENCE] N_raw_family=150 is the SPEC-stated total across ALL S1 design folders "
      "(sensitivity 84 + final_three 3 + defense_strangle 4 + s1s2_core 6+4 + hedged 4 + filters/kelly "
      "sub-grids ~+45 not individually reconciled here); N_eff computed on the 84-cell subgrid only, "
      "since that is the largest homogeneous parameter perturbation and the other sub-families "
      "(hedged structures, defense variants) are STRUCTURALLY different, not just reruns -- treating "
      "them as fully independent would be generous, treating them as fully redundant would understate "
      "risk, so the reported N_eff below is a LOWER BOUND on the true search width, not an exact figure.")
results.append(rep)

# =============================================================================
# 4. OVERSHOOT -- reuse DSR_D009's existing conservative N=5 delta-bucket result, ALSO
#    widen to N=13 (the FINAL_VERDICT.md structure count) as a sensitivity check.
# =============================================================================
print("\n" + "=" * 100); print("4. OVERSHOOT / SPIKE_OVERSHOOT_SELL_20260730"); print("=" * 100)
d009 = json.load(open(f"{R}/DSR_D009_20260730/dsr_pbo_results.json"))
ov = d009["overshoot_delta_neutral_sell"]
print("Existing DSR_D009 result (N=5 delta-buckets, conservative mean=0.30pts convention):")
print(" ", ov["DSR_vs_delta_bucket_family"])
mean_used = ov["conservative_recompute"]["mean_used"]
sd_used = ov["conservative_recompute"]["sd"]
n_used = ov["conservative_recompute"]["n"]
skew_ov = ov["own_recomputation_from_filtered_trades_csv"]["skew"]
kurt_ov = ov["own_recomputation_from_filtered_trades_csv"]["excess_kurt"] + 3  # stored as excess
sr_hat_ov = mean_used / sd_used
# widen to N=13 (FINAL_VERDICT.md's 13 major structures), var_sr_cross unknown across
# structurally-different tests -> use the delta-bucket family's own var_sr_cross as the best
# available proxy (all structures share the same underlying overshoot-decay mechanism)
var_sr_proxy = 0.11661251875610655 ** 2 / 5  # rough back-out is unstable; instead recompute properly below
# Recompute var_sr across the 5 delta-bucket Sharpes directly is unavailable (bucket series not saved);
# report N=13 DSR using the SAME sr0-formula machinery with a conservative var_sr assumption disclosed.
dsr13, sr0_13, z13 = dsr(sr_hat_ov, n_used, skew_ov, kurt_ov, 13, ov["DSR_vs_delta_bucket_family"]["sr0_benchmark"] ** 2)
print(f"Widened to N=13 (structure-level, FINAL_VERDICT.md's full scoreboard) [INFERENCE, var_sr proxy]: "
      f"DSR={dsr13:.4f}, sr0={sr0_13:.4f}, z={z13:.4f}")
results.append(dict(candidate="OVERSHOOT", label="delta-neutral sell, N=5 delta-buckets (DSR_D009, "
                     "illustrative/conservative per its own note)", n_obs=n_used,
                     sharpe_hat=round(sr_hat_ov, 4), skew=round(skew_ov, 4), kurt_nonexcess=round(kurt_ov, 4),
                     N_raw_measured=5, N_raw_family_stated=13, avg_abs_corr=np.nan, N_eff_corr=5,
                     N_eff_pca=np.nan, DSR_using_Neff=round(ov["DSR_vs_delta_bucket_family"]["dsr"], 6),
                     PBO_CSCV=np.nan))
results.append(dict(candidate="OVERSHOOT_widenedN13", label="same headline, N widened to 13 major "
                     "structures per FINAL_VERDICT.md scoreboard [INFERENCE]", n_obs=n_used,
                     sharpe_hat=round(sr_hat_ov, 4), skew=round(skew_ov, 4), kurt_nonexcess=round(kurt_ov, 4),
                     N_raw_measured=13, N_raw_family_stated=13, avg_abs_corr=np.nan, N_eff_corr=13,
                     N_eff_pca=np.nan, DSR_using_Neff=round(dsr13, 6), PBO_CSCV=np.nan))

# =============================================================================
# 5. LD_SELL -- NEW. LONGDATED_SELLING_20260730, 54-config full grid.
# =============================================================================
print("\n" + "=" * 100); print("5. LD_SELL / LONGDATED_SELLING_20260730 (54-config full grid)"); print("=" * 100)
ld = pd.read_csv(f"{R}/LONGDATED_SELLING_20260730/all_trades_full_grid.csv", parse_dates=["entry_day", "exit_day"])
ld["cfg"] = ld["tenor"] + "|" + ld["delta"].astype(str) + "|" + ld["structure"] + "|" + ld["mgmt"]
ld_matrix = ld.pivot_table(index=ld["entry_day"].dt.normalize(), columns="cfg", values="pl_rs_net", aggfunc="sum")
best_cfg_df = pd.read_csv(f"{R}/LONGDATED_SELLING_20260730/best_config_trades.csv", parse_dates=["entry_day"])
headline_ld = best_cfg_df.groupby(best_cfg_df["entry_day"].dt.normalize())["pl_rs_net"].sum() \
    if "pl_rs_net" in best_cfg_df.columns else best_cfg_df.groupby(best_cfg_df["entry_day"].dt.normalize()).iloc[:, -1].sum()
rep = candidate_report("LD_SELL", ld_matrix, headline_ld, N_raw_family=54,
                        label="full grid: tenor x delta x structure x mgmt (verified 54 distinct configs)")
print(rep)
results.append(rep)

# =============================================================================
# 6. THREE_SOLDIERS -- NEW. CANDLE_MTF_20260730, 30 cells (6 filters x 5 exits) for
#    this ONE formation, isolated from the 480-cell grid.
# =============================================================================
print("\n" + "=" * 100); print("6. THREE_SOLDIERS / CANDLE_MTF_20260730 (30-cell sub-grid)"); print("=" * 100)
trades_dict = pd.read_pickle(f"{R}/CANDLE_MTF_20260730/trades.pkl")
ts_keys = [k for k in trades_dict if k.startswith("THREE_SOLDIERS|")]
print(f"THREE_SOLDIERS cells found: {len(ts_keys)}")
ts_daily = {}
for k in ts_keys:
    df = trades_dict[k]
    day_col = "day" if "day" in df.columns else "ds"
    pnl_col = "pnl_o" if "pnl_o" in df.columns else [c for c in df.columns if "pnl" in c.lower()][0]
    ts_daily[k] = df.groupby(pd.to_datetime(df[day_col]).dt.normalize())[pnl_col].sum()
ts_matrix = pd.DataFrame(ts_daily).sort_index()
# headline = the position-capped/non-overlapping corrected series is the honest one per the session
# journal (raw overlapping THREE_SOLDIERS inflated t by 2.9-10.7x); use the filter=none/RR2.0-ish
# middle cell as representative if a specific "adopted" cell isn't separately saved
headline_col = [c for c in ts_matrix.columns if "|none|" in c]
headline_ts = ts_matrix[headline_col[0]] if headline_col else ts_matrix.iloc[:, 0]
rep = candidate_report("THREE_SOLDIERS", ts_matrix, headline_ts, N_raw_family=30,
                        label="6 filters x 5 exits for the ONE formation that survived the random-entry "
                              "placebo (30 of the parent 480-cell candle grid); NOTE raw cells here are "
                              "STILL THE OVERLAPPING version (multiple concurrent positions per the "
                              "session's own Defect-1 finding) -- this DSR uses the overlapping per-trade "
                              "series as-is, so it is upper-bound/optimistic versus the position-capped "
                              "n=758 Newey-West re-test (t_NW 7.85) the desk already ran separately.")
print(rep)
results.append(rep)

# =============================================================================
# WRITE OUT
# =============================================================================
out_df = pd.DataFrame(results)
out_df.to_csv("Shreyas_Ionic_AMC/04_RND_LAB/results/VALIDATION_DEBTS_20260731/dsr_pbo.csv", index=False)
print("\n" + "=" * 100)
print(out_df.to_string(index=False))
print("\nWrote dsr_pbo.csv")
