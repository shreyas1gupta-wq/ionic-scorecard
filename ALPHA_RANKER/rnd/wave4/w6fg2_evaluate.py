"""
W6FG2 STEP 2: score COMPOSITE_V2_CONFIRMED (multi-year gate) through the ONE
harness, then run drop-one (leave-one-year-out, leave-one-sector-out) + era
split robustness at 5Y (the composite's best horizon per FORWARD_GROWTH_DIVERGENCE.md),
and re-test the GARP "story" cell (Q2: expensive+growing) split by the NEW gate
to see whether it now separates multibagger-from-trap in the RIGHT direction
(V1 went backwards -- confirmed underperformed unconfirmed within Q2).

Deterministic: no randomization anywhere in this script except the harness's
own placebo shuffle (fixed seed=42, inherited from harness.py defaults) which
does not affect any number reported to the Principal.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import harness as H

ALPHA_DIR = Path(__file__).resolve().parent.parent.parent
OUT_DIR = Path(__file__).resolve().parent
CARDS_DIR = OUT_DIR / "cards_w6fg2"
CARDS_DIR.mkdir(parents=True, exist_ok=True)

fog = pd.read_parquet(OUT_DIR / "_w6fg2_fund_on_grid.parquet")
panel = pd.read_parquet(ALPHA_DIR / "rnd" / "panel" / "panel_long.parquet")
panel["date"] = pd.to_datetime(panel["date"])
fog["date"] = pd.to_datetime(fog["date"])

# ---------------------------------------------------------------------------
# same z-scoring / composite construction as V1 (w6fg_evaluate.py) -- only the
# GATE changes, so any difference in results is attributable to the gate, not
# to a different composite definition.
# ---------------------------------------------------------------------------
def _cs_z(df, col):
    def _z(s):
        mu, sd = s.mean(), s.std(ddof=1)
        if not sd or np.isnan(sd):
            return pd.Series(np.nan, index=s.index)
        return (s - mu) / sd
    return df.groupby("date")[col].transform(_z)

fog["z_accel"] = _cs_z(fog, "rev_accel")
fog["z_margin_infl"] = _cs_z(fog, "margin_inflection")
fog["composite_raw"] = fog[["z_accel", "z_margin_infl"]].mean(axis=1, skipna=True) + fog["theme_dummy"].fillna(0)

penalty = fog["composite_raw"].min() - 10.0
fog["composite_v2_confirmed"] = np.where(
    fog["earnings_confirm_v2"] == 1, fog["composite_raw"],
    np.where(fog["earnings_confirm_v2"] == 0, penalty, np.nan))

# V1 gate on the SAME rows/composite, for an apples-to-apples before/after
fog["composite_v1_confirmed"] = np.where(
    fog["earnings_confirm_v1"] == 1, fog["composite_raw"],
    np.where(fog["earnings_confirm_v1"] == 0, penalty, np.nan))

n_v2_1 = int((fog["earnings_confirm_v2"] == 1).sum())
n_v2_0 = int((fog["earnings_confirm_v2"] == 0).sum())
print(f"[DATA] on panel grid: earnings_confirm_v2==1: {n_v2_1} obs, ==0: {n_v2_0} obs, "
      f"NaN: {fog['earnings_confirm_v2'].isna().sum()}")

fog.to_parquet(OUT_DIR / "_w6fg2_scored.parquet", index=False)

# ---------------------------------------------------------------------------
# A. Main harness run: COMPOSITE_V2_CONFIRMED at 1M/1Y/5Y, return_basis=excess
#    (matches V1's primary basis) -- this is the pre-registered headline test.
# ---------------------------------------------------------------------------
results = {}
fseries = fog.dropna(subset=["composite_v2_confirmed"])[["date", "symbol", "composite_v2_confirmed"]].rename(
    columns={"composite_v2_confirmed": "factor"}).set_index(["date", "symbol"])["factor"]
for hz in ("1M", "1Y", "5Y"):
    card = H.evaluate(fseries, horizon=hz, return_basis="excess",
                       factor_id=f"W6FG2_COMPOSITE_V2_CONFIRMED_{hz}",
                       family="W6FG2", panel=panel, panel_source="real", cards_dir=CARDS_DIR)
    results[f"V2_{hz}"] = card
    icir = card.get("ic", {}).get("ic_ir")
    nwt = card.get("ic", {}).get("newey_west_t")
    nobs = card.get("n_obs")
    print(f"W6FG2_COMPOSITE_V2_CONFIRMED_{hz:4s} n_obs={nobs!s:>7} IC_IR={icir!s:>8} NW-t={nwt!s:>8} -> {card.get('verdict')}")

# 5Y resid robustness (matches V1's robustness check)
fseries_resid = fseries.copy()
card_resid = H.evaluate(fseries_resid, horizon="5Y", return_basis="resid",
                         factor_id="W6FG2_COMPOSITE_V2_CONFIRMED_5Y_resid",
                         family="W6FG2", panel=panel, panel_source="real", cards_dir=CARDS_DIR)
results["V2_5Y_resid"] = card_resid
print(f"W6FG2_COMPOSITE_V2_CONFIRMED_5Y_resid    n_obs={card_resid.get('n_obs')!s:>7} "
      f"IC_IR={card_resid.get('ic',{}).get('ic_ir')!s:>8} NW-t={card_resid.get('ic',{}).get('newey_west_t')!s:>8} "
      f"-> {card_resid.get('verdict')}")

# V1 gate re-run on the identical rows/universe for a same-data comparison
fseries_v1 = fog.dropna(subset=["composite_v1_confirmed"])[["date", "symbol", "composite_v1_confirmed"]].rename(
    columns={"composite_v1_confirmed": "factor"}).set_index(["date", "symbol"])["factor"]
card_v1_5y = H.evaluate(fseries_v1, horizon="5Y", return_basis="excess",
                         factor_id="W6FG2_COMPOSITE_V1_CONFIRMED_5Y_REFCHECK",
                         family="W6FG2", panel=panel, panel_source="real", cards_dir=CARDS_DIR)
results["V1_5Y_refcheck"] = card_v1_5y
print(f"W6FG2_COMPOSITE_V1_CONFIRMED_5Y_REFCHECK n_obs={card_v1_5y.get('n_obs')!s:>7} "
      f"IC_IR={card_v1_5y.get('ic',{}).get('ic_ir')!s:>8} NW-t={card_v1_5y.get('ic',{}).get('newey_west_t')!s:>8} "
      f"-> {card_v1_5y.get('verdict')}")

# ---------------------------------------------------------------------------
# B. Drop-one (leave-one-year-out on rebalance-date calendar year, leave-one-
#    sector-out on macro_sector) + era split (first_half/second_half by date
#    median), computed directly on the SAME IC methodology the harness uses
#    (Spearman rank IC per date, then mean across dates) -- for the 5Y horizon
#    (the composite's best/most relevant horizon per the brief).
# ---------------------------------------------------------------------------
lbl5y_excess = "fwd_ret_5Y_excess"
base_cols = ["date", "symbol", "mktcap_log"]
p5 = panel[base_cols + [lbl5y_excess]].rename(columns={lbl5y_excess: "target_eval"})
merged5 = fseries.rename("factor").reset_index().merge(p5, on=["date", "symbol"], how="inner").dropna(
    subset=["factor", "target_eval"])
merged5 = merged5.merge(fog[["date", "symbol", "macro_sector"]], on=["date", "symbol"], how="left")
merged5["year"] = merged5["date"].dt.year

def _mean_ic(df, min_names=20):
    ics = df.groupby("date").apply(
        lambda g: stats.spearmanr(g["factor"], g["target_eval"])[0] if len(g) >= min_names else np.nan,
        include_groups=False)
    return float(ics.dropna().mean()) if ics.notna().any() else float("nan")

full_ic = _mean_ic(merged5)
print(f"\n[DIAG] 5Y full-sample IC (Spearman, mean of per-date IC): {full_ic:.4f}  n_obs={len(merged5)}")

# leave-one-year-out
years = sorted(merged5["year"].unique())
year_drop_ics = {}
for y in years:
    sub = merged5[merged5["year"] != y]
    year_drop_ics[int(y)] = _mean_ic(sub)
sign_flips_year = sum(1 for v in year_drop_ics.values() if not np.isnan(v) and np.sign(v) != np.sign(full_ic))
worst_year = min(((v, y) for y, v in year_drop_ics.items() if not np.isnan(v)),
                  key=lambda t: t[0] * np.sign(full_ic)) if year_drop_ics else (np.nan, None)

# leave-one-sector-out
sectors = sorted(merged5["macro_sector"].dropna().unique())
sector_drop_ics = {}
for s in sectors:
    sub = merged5[merged5["macro_sector"] != s]
    sector_drop_ics[s] = _mean_ic(sub)
sign_flips_sector = sum(1 for v in sector_drop_ics.values() if not np.isnan(v) and np.sign(v) != np.sign(full_ic))
worst_sector = min(((v, s) for s, v in sector_drop_ics.items() if not np.isnan(v)),
                    key=lambda t: t[0] * np.sign(full_ic)) if sector_drop_ics else (np.nan, None)

# era split: first half vs second half of dates chronologically
dates_sorted = sorted(merged5["date"].unique())
mid = dates_sorted[len(dates_sorted) // 2]
first_half = merged5[merged5["date"] < mid]
second_half = merged5[merged5["date"] >= mid]
ic_first = _mean_ic(first_half)
ic_second = _mean_ic(second_half)
era_holds = bool((not np.isnan(ic_first)) and (not np.isnan(ic_second))
                  and np.sign(ic_first) == np.sign(full_ic) and np.sign(ic_second) == np.sign(full_ic))

dropone_summary = {
    "factor": "W6FG2_COMPOSITE_V2_CONFIRMED_5Y",
    "full_ic": full_ic,
    "n_obs": int(len(merged5)),
    "n_years_leaveout": len(years),
    "n_sign_flips_leaveout_year": int(sign_flips_year),
    "worst_year_drop": [worst_year[1], worst_year[0]],
    "n_sectors_leaveout": len(sectors),
    "n_sign_flips_leaveout_sector": int(sign_flips_sector),
    "worst_sector_drop": [worst_sector[1], worst_sector[0]],
    "era_ic_first_half": ic_first,
    "era_ic_second_half": ic_second,
    "era_holds": era_holds,
    "years_covered": years,
}
print(f"[DIAG] drop-one-year: {sign_flips_year}/{len(years)} sign flips, worst={worst_year}")
print(f"[DIAG] drop-one-sector: {sign_flips_sector}/{len(sectors)} sign flips, worst={worst_sector}")
print(f"[DIAG] era split: first_half IC={ic_first:.4f}, second_half IC={ic_second:.4f}, holds={era_holds}")

with open(OUT_DIR / "_w6fg2_dropone_era.json", "w", encoding="utf-8") as fh:
    json.dump(dropone_summary, fh, indent=2, default=str)

# ---------------------------------------------------------------------------
# C. GARP "story" cell (Q2: expensive + growing) re-split by the NEW multi-
#    year gate -- does it now separate multibagger from trap in the RIGHT
#    direction (V1 went backwards: confirmed underperformed unconfirmed)?
# ---------------------------------------------------------------------------
def _garp_story_split(horizon_label, fwd_col):
    p = panel[["date", "symbol", fwd_col]].rename(columns={fwd_col: "fwd_ret"})
    d = fog[["date", "symbol", "composite_raw", "value7leg_score", "earnings_confirm_v2"]].merge(
        p, on=["date", "symbol"], how="inner").dropna(subset=["composite_raw", "value7leg_score", "fwd_ret"])
    # median split per date (matches FORWARD_GROWTH_DIVERGENCE.md S4 methodology)
    d["val_med"] = d.groupby("date")["value7leg_score"].transform("median")
    d["gr_med"] = d.groupby("date")["composite_raw"].transform("median")
    q2 = d[(d["value7leg_score"] < d["val_med"]) & (d["composite_raw"] > d["gr_med"])].copy()  # expensive(low 7leg)+growing
    q2_confirmed = q2[q2["earnings_confirm_v2"] == 1]["fwd_ret"]
    q2_unconfirmed = q2[q2["earnings_confirm_v2"] == 0]["fwd_ret"]
    if len(q2_confirmed) > 5 and len(q2_unconfirmed) > 5:
        tstat, pval = stats.ttest_ind(q2_confirmed, q2_unconfirmed, equal_var=False)
    else:
        tstat, pval = float("nan"), float("nan")
    return {
        "horizon": horizon_label,
        "n_q2_total": int(len(q2)),
        "confirmed_mean": float(q2_confirmed.mean()) if len(q2_confirmed) else float("nan"),
        "confirmed_std": float(q2_confirmed.std()) if len(q2_confirmed) else float("nan"),
        "confirmed_n": int(len(q2_confirmed)),
        "unconfirmed_mean": float(q2_unconfirmed.mean()) if len(q2_unconfirmed) else float("nan"),
        "unconfirmed_std": float(q2_unconfirmed.std()) if len(q2_unconfirmed) else float("nan"),
        "unconfirmed_n": int(len(q2_unconfirmed)),
        "t_stat": float(tstat), "p_value": float(pval),
        "right_direction": bool(not np.isnan(tstat) and
                                 (q2_confirmed.mean() > q2_unconfirmed.mean())),
    }

story_1y = _garp_story_split("1Y", "fwd_ret_1Y_raw")
story_5y = _garp_story_split("5Y", "fwd_ret_5Y_raw")
print(f"\n[DIAG] Q2 'story' cell split (V2 multi-year gate), 1Y: confirmed={story_1y['confirmed_mean']:.4f} "
      f"(n={story_1y['confirmed_n']}) vs unconfirmed={story_1y['unconfirmed_mean']:.4f} (n={story_1y['unconfirmed_n']}), "
      f"t={story_1y['t_stat']:.2f} p={story_1y['p_value']:.4f}, right_direction={story_1y['right_direction']}")
print(f"[DIAG] Q2 'story' cell split (V2 multi-year gate), 5Y: confirmed={story_5y['confirmed_mean']:.4f} "
      f"(n={story_5y['confirmed_n']}) vs unconfirmed={story_5y['unconfirmed_mean']:.4f} (n={story_5y['unconfirmed_n']}), "
      f"t={story_5y['t_stat']:.2f} p={story_5y['p_value']:.4f}, right_direction={story_5y['right_direction']}")

with open(OUT_DIR / "_w6fg2_story_cell_split.json", "w", encoding="utf-8") as fh:
    json.dump({"1Y": story_1y, "5Y": story_5y}, fh, indent=2, default=str)

# ---------------------------------------------------------------------------
# save headline summary
# ---------------------------------------------------------------------------
with open(OUT_DIR / "_w6fg2_all_cards_summary.json", "w", encoding="utf-8") as fh:
    json.dump({k: {kk: vv for kk, vv in v.items() if kk not in ("regime_breakdown",)}
               for k, v in results.items()}, fh, indent=2, default=str)

print("\nSTEP 2 done.")
