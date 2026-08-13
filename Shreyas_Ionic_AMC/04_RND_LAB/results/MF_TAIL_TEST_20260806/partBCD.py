# -*- coding: utf-8 -*-
"""PART B/C/D -- fund-level ES90-vs-MDD rank test, regime-coverage census, alternative measures.

Pre-registered before computing (Sameer Bhat, 2026-08-06):
  Universe: ACE direct-plan, GROWTH option only (name has "(G)", not IDCW), Asset Type in
  {Equity, Hybrid} -- debt/commodity/other excluded from the tail-risk ranking exercise
  because their drawdowns are near-flat and a rank test there is not informative (regime
  coverage census in Part C still runs on the FULL direct-growth universe, all asset types).
  Inclusion bar for Part B/D: >=12 monthly NAV points on file (>=11 realised returns) so
  ES90's "worst decile" has at least one real observation beyond the single worst month.
  Rank test: Spearman, ES90 vs MDD, overall and by Category (categories with n>=15 get
  their own row; smaller ones pooled as "Other").
  Stability test (Part D): split each fund's series chronologically into two halves,
  compute each metric per half, Spearman-correlate the cross-fund ranking between halves.
  Funds need >=10 returns total to be split (>=5 usable per half).
"""
import sys
import re
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\C--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500--claude-worktrees-sweet-austin-283067\60624b2b-b530-4e53-8e92-dc9dc2087600\scratchpad")
from tail_lib import (es_90, mdd_from_returns, ulcer_index, cdar_90, downside_deviation,  # noqa: E402
                       monthly_returns_from_navs)

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
FIRM = BASE + r"\.claude\worktrees\sweet-austin-283067\Shreyas_Ionic_AMC"
RESULTS = FIRM + r"\04_RND_LAB\results\MF_TAIL_TEST_20260806"
sys.path.insert(0, FIRM + r"\09_PRODUCT\pr_template\lib")
import acemf  # noqa: E402

ACE_XLSX = r"C:\Users\Shreyas.1Gupta\Downloads\10. V2 Data_31th July_2026.xlsx"

# ---------- load ----------
df, meta = acemf.load(ACE_XLSX, cache_parquet=RESULTS + r"\ace_cache.parquet")
dg_all = acemf.direct_growth(df).copy()

is_growth_name = dg_all["Scheme Name"].astype(str).str.contains(r"\(G\)", regex=True)
is_idcw_name = dg_all["Scheme Name"].astype(str).str.contains("IDCW", case=False, na=False)
dg = dg_all[is_growth_name & ~is_idcw_name].copy()
dg = dg.drop_duplicates(subset=["ISIN Code"])
print(f"ACE direct_growth rows: {len(dg_all)} -> growth-option-only (name-filtered), deduped: {len(dg)}")

# --- DATA BUG CAUGHT: 3009 of 3276 (91.9%) "Inception Date" cells in the ACE extract are raw
# Excel serial-date INTEGERS (e.g. 41449), not python datetimes -- almost entirely in the Debt
# block. pd.to_datetime() on a bare int silently reads it as a Unix-epoch nanosecond count and
# returns a bogus ~1970 date instead of raising. Naively filtering "<1993" would have thrown away
# 92% of the universe as unparseable when it is actually GOOD, recoverable data. Fix: convert
# int/float raw cells via the Excel serial origin (1899-12-30); keep genuine datetimes as-is.
raw = dg["Inception Date"]
is_serial = raw.map(lambda v: isinstance(v, (int, float)) and not isinstance(v, bool))
inception = pd.to_datetime(raw.where(~is_serial), errors="coerce")
serial_num = pd.to_numeric(raw.where(is_serial), errors="coerce")
serial_parsed = pd.to_datetime(serial_num, unit="D", origin="1899-12-30", errors="coerce")
dg["inception"] = inception.fillna(serial_parsed)
print(f"Inception Date raw-type split: {is_serial.sum()} Excel-serial-int cells recovered via "
      f"origin=1899-12-30, {(~is_serial).sum()} already real dates")

bad_incep = (dg["inception"] < pd.Timestamp("1993-01-01")) | (dg["inception"] > pd.Timestamp("2026-08-06"))
print(f"Still-implausible inception dates after the serial-date fix (<1993 or >today, "
      f"genuine bad data / true parse failures): {bad_incep.sum()} of {len(dg)}")
dg.loc[bad_incep, "inception"] = pd.NaT

nm = pd.read_parquet(BASE + r"\datasets\mf_nav\nav_monthend.parquet")
nm["isin"] = nm["isin"].astype(str).str.strip()
nm["date"] = pd.to_datetime(nm["date"])

# ================= PART C: regime coverage census (full direct-growth universe) =================
CRISES = {
    "covid_2020": pd.Timestamp("2020-01-01"),
    "y2018_smallcap": pd.Timestamp("2018-01-01"),
    "y2018_ilfs": pd.Timestamp("2018-09-01"),
    "y2022_selloff": pd.Timestamp("2021-10-01"),
}
has_incep = dg["inception"].notna()
cov = dg[has_incep].copy()
for cname, cstart in CRISES.items():
    cov[f"could_show_{cname}"] = cov["inception"] < cstart
cov["n_crises_could_show"] = cov[[f"could_show_{c}" for c in CRISES]].sum(axis=1)
cov["misses_all_4_by_inception"] = cov["n_crises_could_show"] == 0

n_cov = len(cov)
n_miss_all = cov["misses_all_4_by_inception"].sum()
print(f"\n=== PART C: regime coverage, by INCEPTION DATE (n={n_cov} funds with a valid inception date) ===")
print(f"Miss ALL 4 named episodes (launched after Jun-2022): {n_miss_all} ({n_miss_all/n_cov:.1%})")
for cname in CRISES:
    n_could = cov[f"could_show_{cname}"].sum()
    print(f"  could have shown {cname:16s}: {n_could:5d} ({n_could/n_cov:.1%})")

# now the DATA-availability version: of the funds we can actually match to nav_monthend today,
# how many have on-file NAV history reaching back before each crisis (answers "how many can we
# ACTUALLY score through a stress episode right now", not just "how many are old enough")
isin_first_nav = nm.groupby("isin")["date"].min()
cov["first_nav_on_file"] = cov["ISIN Code"].map(isin_first_nav)
matched = cov[cov["first_nav_on_file"].notna()].copy()
print(f"\nOf those {n_cov}, matched to nav_monthend by ISIN: {len(matched)}")
for cname, cstart in CRISES.items():
    n_data_covers = (matched["first_nav_on_file"] < cstart).sum()
    print(f"  NAV DATA on file actually reaches back before {cname:16s}: {n_data_covers} of {len(matched)}"
          f" ({n_data_covers/len(matched):.1%})")

cov.to_csv(RESULTS + r"\partC_regime_coverage_census.csv", index=False)
print("saved:", RESULTS + r"\partC_regime_coverage_census.csv")

# ================= PART B/D: fund-level metrics on the equity/hybrid, NAV-matched universe =================
uni = dg[dg["Asset Type"].isin(["Equity", "Hybrid"])].copy()
uni = uni.merge(nm[["isin", "date", "nav"]], left_on="ISIN Code", right_on="isin", how="inner")
print(f"\nEquity/Hybrid growth-option funds with >=1 NAV row matched: {uni['ISIN Code'].nunique()} "
      f"(of {len(dg[dg['Asset Type'].isin(['Equity', 'Hybrid'])])} in ACE)")

records = []
for isin, g in uni.groupby("ISIN Code"):
    g = g.sort_values("date")
    rets_s = monthly_returns_from_navs(g["date"].values, g["nav"].astype(float).values)
    n_obs = g["date"].nunique()
    if n_obs < 12 or len(rets_s) == 0:
        continue
    rets = rets_s.values
    cat = g["Category"].iloc[0]
    name = g["Scheme Name"].iloc[0]
    rec = {
        "isin": isin, "name": name, "category": cat, "asset_type": g["Asset Type"].iloc[0],
        "n_nav_obs": n_obs, "n_returns": len(rets),
        "es90": es_90(rets), "mdd": mdd_from_returns(rets),
        "ulcer": ulcer_index(rets), "cdar90": cdar_90(rets),
        "downside_dev": downside_deviation(rets),
    }
    # split-half stability inputs
    if len(rets) >= 10:
        h = len(rets) // 2
        r1, r2 = rets[:h], rets[h:]
        rec.update({
            "es90_h1": es_90(r1), "es90_h2": es_90(r2),
            "mdd_h1": mdd_from_returns(r1), "mdd_h2": mdd_from_returns(r2),
            "ulcer_h1": ulcer_index(r1), "ulcer_h2": ulcer_index(r2),
            "cdar90_h1": cdar_90(r1), "cdar90_h2": cdar_90(r2),
            "downside_dev_h1": downside_deviation(r1), "downside_dev_h2": downside_deviation(r2),
        })
    records.append(rec)

fm = pd.DataFrame(records)
fm.to_csv(RESULTS + r"\partBD_fund_level_metrics.csv", index=False)
print(f"\nfund-level metrics computed for n={len(fm)} funds (>=12 NAV obs). saved:",
      RESULTS + r"\partBD_fund_level_metrics.csv")
print("n_returns distribution:", fm["n_returns"].describe()[["min", "25%", "50%", "75%", "max"]].to_dict())

def safe_spearman(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if np.nanstd(a) == 0 or np.nanstd(b) == 0:
        return np.nan, np.nan  # constant input -- correlation genuinely undefined
    return stats.spearmanr(a, b, nan_policy="omit")


# ---- PART B: rank correlation ES90 vs MDD ----
print("\n=== PART B: Spearman rank correlation, ES90 vs MDD ===")
overall_rho, overall_p = safe_spearman(fm["es90"], fm["mdd"])
print(f"OVERALL (n={len(fm)}): rho={overall_rho:.4f}  p={overall_p:.2e}")

cat_counts = fm["category"].value_counts()
big_cats = cat_counts[cat_counts >= 15].index.tolist()
rows = [{"category": "OVERALL", "n": len(fm), "spearman_rho": overall_rho, "p_value": overall_p}]
for cat in big_cats:
    sub = fm[fm["category"] == cat]
    rho, p = safe_spearman(sub["es90"], sub["mdd"])
    rows.append({"category": cat, "n": len(sub), "spearman_rho": rho, "p_value": p})
    tag = "N/A (near-zero drawdown, constant)" if pd.isna(rho) else f"{rho:.4f}"
    print(f"  {cat:35s} n={len(sub):4d}  rho={tag}")
rank_corr = pd.DataFrame(rows)
rank_corr.to_csv(RESULTS + r"\partB_rank_correlation.csv", index=False)

# overlap of worst-quintile-by-ES90 vs worst-quintile-by-MDD
q = 0.20
worst_es90 = set(fm.nsmallest(int(len(fm) * q), "es90")["isin"])
worst_mdd = set(fm.nsmallest(int(len(fm) * q), "mdd")["isin"])
jacc = len(worst_es90 & worst_mdd) / len(worst_es90 | worst_mdd)
print(f"\nWorst-quintile overlap (ES90-flagged vs MDD-flagged), Jaccard: {jacc:.3f} "
      f"(n_each={len(worst_es90)})")

# ---- category-relative sanity check ----
print("\n=== category medians (sanity check: should order small>mid>large) ===")
med = fm.groupby("category")[["es90", "mdd", "ulcer"]].median().sort_values("mdd")
print(med)
med.to_csv(RESULTS + r"\category_medians.csv")

# ---- PART D: split-half stability per metric ----
print("\n=== PART D: split-half rank stability (higher = more stable fund ranking) ===")
stab = fm.dropna(subset=["es90_h1"]).copy()
print(f"n funds with split-half data: {len(stab)}")
stab_rows = []
for metric in ["es90", "mdd", "ulcer", "cdar90", "downside_dev"]:
    rho, p = safe_spearman(stab[f"{metric}_h1"], stab[f"{metric}_h2"])
    stab_rows.append({"metric": metric, "n": len(stab), "split_half_rho": rho, "p_value": p})
    print(f"  {metric:15s} split-half rho={rho:.4f}  p={p:.2e}")
stab_df = pd.DataFrame(stab_rows)
stab_df.to_csv(RESULTS + r"\partD_stability.csv", index=False)
print("saved:", RESULTS + r"\partD_stability.csv")

# alt-measure vs ES90 rank agreement (does the alternative actually rank funds differently?)
print("\n=== alternative measures vs ES90, rank agreement (full sample) ===")
for metric in ["mdd", "ulcer", "cdar90", "downside_dev"]:
    rho, p = safe_spearman(fm["es90"], fm[metric])
    print(f"  ES90 vs {metric:15s} rho={rho:.4f}  p={p:.2e}")
