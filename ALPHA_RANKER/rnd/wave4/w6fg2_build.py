"""
W6FG2 STEP 1: rebuild the forward-growth PIT fundamentals with a MULTI-YEAR
earnings-confirmation gate, replacing the single-year op-profit sign-flip gate
that BACKFIRED in FORWARD_GROWTH_DIVERGENCE.md (rnd/wave4/FORWARD_GROWTH_DIVERGENCE.md
S3-4): the crude "op_growth_t > 0" test fired too LATE relative to the real
inflection (base-effect artifact) and, within the GARP "story" quadrant,
confirmed names UNDERPERFORMED unconfirmed ones -- backwards from the intended
"theme+earnings=stays" discipline.

FIX (this script): confirmation must PERSIST across years, not flip once.
Three ingredients, each requiring the SAME-DIRECTION signal to hold in BOTH the
current fiscal year (t) AND the prior fiscal year (t-1) -- i.e. a 2-year
persistence test, using only same-symbol PAST rows (shift, PIT-safe, no
cross-symbol/future leakage):

  (a) op_growth_persistent  = op profit YoY growth > 0 at BOTH t and t-1
                              (replaces the single-year "op_growth_t>0" flag --
                              a name that turned positive this year AND stayed
                              positive last year cannot be a same-period base-
                              effect blip that reverses)
  (b) margin_holds          = margin_inflection (opm% - trailing3Y avg) > 0 at
                              BOTH t and t-1 (the margin improvement must still
                              be there a year later, not a one-quarter/one-year
                              base-effect spike that mean-reverts)
  (c) cwip_converting       = cwip growth DECELERATING vs prior year
                              (cwip_growth_t <= cwip_growth_t1) -- capex-in-
                              progress is completing/converting into revenue-
                              generating fixed assets, not still in an
                              unconverted ramp phase

CONFIRM_V2 = 1 iff ALL THREE hold (strict AND, deterministic, pre-registered
before looking at 5Y results -- no post-hoc threshold tuning); 0 if all three
inputs are computable and at least one fails; NaN if any required lag is
missing (insufficient history to judge -- excluded, not assumed good or bad).

No lookahead: identical PIT construction discipline as w6fg_build.py
(restatements collapsed to FIRST disclosed available_date; all derived cols
use only prior same-symbol fiscal-year rows via .shift() within a
chronologically-sorted groupby).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ALPHA_DIR = Path(__file__).resolve().parent.parent.parent
OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("W6FG2 STEP 1: multi-year earnings-confirmation gate (PIT)")
print("=" * 70)

# ---------------------------------------------------------------------------
# 1. Load raw fundamentals, pivot to wide per (symbol, fiscal_year) -- same
#    PIT-safe restatement handling as w6fg_build.py
# ---------------------------------------------------------------------------
mf = pd.read_parquet(ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet")
metrics_needed = ["sales", "operating profit", "net profit", "opm %", "cwip", "fixed assets", "borrowings"]
mf = mf[mf["metric_norm"].isin(metrics_needed)].copy()

first_avail = mf.groupby(["nse_symbol", "fiscal_year"])["available_date"].transform("min")
mf = mf[mf["available_date"] == first_avail]
mf = mf.drop_duplicates(subset=["nse_symbol", "fiscal_year", "metric_norm"], keep="first")

wide = mf.pivot_table(index=["nse_symbol", "fiscal_year"], columns="metric_norm",
                       values="value", aggfunc="first")
avail = mf.groupby(["nse_symbol", "fiscal_year"])["available_date"].min()
wide = wide.join(avail.rename("available_date"))
wide = wide.reset_index().sort_values(["nse_symbol", "fiscal_year"])
print(f"[DATA] wide fundamentals panel: {wide.shape[0]} symbol-fiscal_year rows, "
      f"{wide['nse_symbol'].nunique()} symbols, FY range {wide.fiscal_year.min()}-{wide.fiscal_year.max()}")

# ---------------------------------------------------------------------------
# 2. Multi-year lags -- t-1, t-2, t-3, t-4 same-symbol shifts (chronological,
#    PIT-safe: shift() only ever looks at earlier rows of the SAME symbol).
# ---------------------------------------------------------------------------
g = wide.groupby("nse_symbol", group_keys=False)

def _safe_growth(cur, prev):
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where((prev > 0) & np.isfinite(prev) & np.isfinite(cur), cur / prev - 1.0, np.nan)
    return out

wide["sales_l1"] = g["sales"].shift(1)
wide["sales_l2"] = g["sales"].shift(2)
wide["sales_l3"] = g["sales"].shift(3)
wide["op_l1"] = g["operating profit"].shift(1)
wide["op_l2"] = g["operating profit"].shift(2)
wide["cwip_l1"] = g["cwip"].shift(1)
wide["cwip_l2"] = g["cwip"].shift(2)
wide["opm_l1"] = g["opm %"].shift(1)
wide["opm_l2"] = g["opm %"].shift(2)
wide["opm_l3"] = g["opm %"].shift(3)
wide["opm_l4"] = g["opm %"].shift(4)
wide["fixed_assets_l0"] = wide["fixed assets"]

# current-year (t) factors -- identical definitions to w6fg_build.py (V1)
wide["rev_growth_t"] = _safe_growth(wide["sales"].values, wide["sales_l1"].values)
wide["rev_growth_t1"] = _safe_growth(wide["sales_l1"].values, wide["sales_l2"].values)
wide["rev_accel"] = wide["rev_growth_t"] - wide["rev_growth_t1"]

wide["op_growth_t"] = _safe_growth(wide["operating profit"].values, wide["op_l1"].values)
wide["cwip_growth_t"] = _safe_growth(wide["cwip"].values, wide["cwip_l1"].values)
wide["cwip_intensity"] = wide["cwip"] / wide["fixed_assets_l0"].replace(0, np.nan)

wide["opm_trail3"] = wide[["opm_l1", "opm_l2", "opm_l3"]].mean(axis=1, skipna=True)
wide["margin_inflection"] = wide["opm %"] - wide["opm_trail3"]

# prior-year (t-1) versions of the SAME factors -- this is the new, multi-year
# piece: every "t" factor above gets a "t-1" twin computed the identical way,
# one fiscal year earlier, so persistence can be tested.
wide["rev_growth_t2"] = _safe_growth(wide["sales_l2"].values, wide["sales_l3"].values)
wide["rev_accel_t1"] = wide["rev_growth_t1"] - wide["rev_growth_t2"]

wide["op_growth_t1"] = _safe_growth(wide["op_l1"].values, wide["op_l2"].values)
wide["cwip_growth_t1"] = _safe_growth(wide["cwip_l1"].values, wide["cwip_l2"].values)

wide["opm_trail3_l1"] = wide[["opm_l2", "opm_l3", "opm_l4"]].mean(axis=1, skipna=True)
wide["margin_inflection_t1"] = wide["opm_l1"] - wide["opm_trail3_l1"]

# ---------------------------------------------------------------------------
# 3. Multi-year CONFIRM_V2 gate -- persistence, not single-year sign-flip.
#    Each sub-condition is NaN-safe: comparisons with NaN evaluate False in
#    numpy, so we explicitly track "computable" per sub-condition and only
#    emit CONFIRM_V2 when all three are computable; otherwise NaN (excluded).
# ---------------------------------------------------------------------------
op_growth_persistent = (wide["op_growth_t"] > 0) & (wide["op_growth_t1"] > 0)
op_computable = wide["op_growth_t"].notna() & wide["op_growth_t1"].notna()

margin_holds = (wide["margin_inflection"] > 0) & (wide["margin_inflection_t1"] > 0)
margin_computable = wide["margin_inflection"].notna() & wide["margin_inflection_t1"].notna()

cwip_converting = wide["cwip_growth_t"] <= wide["cwip_growth_t1"]
cwip_computable = wide["cwip_growth_t"].notna() & wide["cwip_growth_t1"].notna()

all_computable = op_computable & margin_computable & cwip_computable
confirm_v2_bool = op_growth_persistent & margin_holds & cwip_converting
wide["earnings_confirm_v2"] = np.where(all_computable, confirm_v2_bool.astype(float), np.nan)

# also keep the individual sub-flags for diagnostics (which ingredient binds)
wide["sub_op_persistent"] = np.where(op_computable, op_growth_persistent.astype(float), np.nan)
wide["sub_margin_holds"] = np.where(margin_computable, margin_holds.astype(float), np.nan)
wide["sub_cwip_converting"] = np.where(cwip_computable, cwip_converting.astype(float), np.nan)

# keep V1's single-year gate alongside for direct before/after comparison
wide["earnings_confirm_v1"] = np.where(wide["op_growth_t"].notna(),
                                        (wide["op_growth_t"] > 0).astype(float), np.nan)

n_v2_confirm = int((wide["earnings_confirm_v2"] == 1).sum())
n_v2_unconf = int((wide["earnings_confirm_v2"] == 0).sum())
n_v2_nan = int(wide["earnings_confirm_v2"].isna().sum())
print(f"[DATA] earnings_confirm_v2 (multi-year, all 3 conditions computable): "
      f"confirmed(1)={n_v2_confirm}, unconfirmed(0)={n_v2_unconf}, NaN(insufficient history)={n_v2_nan} "
      f"of {len(wide)} symbol-FY rows")
print(f"[DATA] sub-condition hit rates (of computable rows): "
      f"op_persistent={op_growth_persistent[op_computable].mean():.3f} (n={op_computable.sum()}), "
      f"margin_holds={margin_holds[margin_computable].mean():.3f} (n={margin_computable.sum()}), "
      f"cwip_converting={cwip_converting[cwip_computable].mean():.3f} (n={cwip_computable.sum()})")

keep_cols = ["nse_symbol", "fiscal_year", "available_date", "rev_growth_t", "rev_accel",
             "rev_accel_t1", "op_growth_t", "op_growth_t1", "cwip_growth_t", "cwip_growth_t1",
             "cwip_intensity", "margin_inflection", "margin_inflection_t1",
             "earnings_confirm_v1", "earnings_confirm_v2",
             "sub_op_persistent", "sub_margin_holds", "sub_cwip_converting", "opm %"]
fund_derived = wide[keep_cols].rename(columns={"nse_symbol": "symbol"}).copy()
fund_derived["available_date"] = pd.to_datetime(fund_derived["available_date"])
fund_derived.to_parquet(OUT_DIR / "_w6fg2_fund_derived.parquet", index=False)

# ---------------------------------------------------------------------------
# 4. Theme tag -- unchanged from V1 (re-read, not re-derived, no drift risk)
# ---------------------------------------------------------------------------
smap = pd.read_parquet(ALPHA_DIR / "data" / "universe" / "sector_map.parquet")
theme_kw = r"renewable|solar|green|defence|electronics manufactur|\bems\b|capital goods|power|infrastructure|clean energy|battery|semiconductor"
txt = (smap["macro_sector"].fillna("") + " | " + smap["sub_sector"].fillna("")).str.lower()
smap["theme_dummy"] = txt.str.contains(theme_kw, regex=True, na=False).astype(float)

# ---------------------------------------------------------------------------
# 5. Asof-merge onto the monthly panel grid (panel_long, full 2005-2025) +
#    canonical 7-leg value/quality score -- identical merge_asof(backward)
#    discipline as w6fg_build.py.
# ---------------------------------------------------------------------------
panel = pd.read_parquet(ALPHA_DIR / "rnd" / "panel" / "panel_long.parquet")
panel["date"] = pd.to_datetime(panel["date"])
c7 = pd.read_parquet(ALPHA_DIR / "rnd" / "panel" / "canonical_7leg_scores.parquet")
c7["date"] = pd.to_datetime(c7["date"])
c7 = c7.rename(columns={"score": "value7leg_score"})[["date", "symbol", "value7leg_score"]]

grid = panel[["date", "symbol"]].drop_duplicates().sort_values(["symbol", "date"]).copy()
grid["symbol"] = grid["symbol"].astype(str)

fd = fund_derived.dropna(subset=["available_date"]).sort_values(["symbol", "available_date"]).copy()
fd["symbol"] = fd["symbol"].astype(str)
merged_rows = []
for sym, gdf in grid.groupby("symbol"):
    fsub = fd[fd.symbol == sym]
    if fsub.empty:
        continue
    m = pd.merge_asof(gdf.sort_values("date"), fsub.sort_values("available_date"),
                       left_on="date", right_on="available_date", by="symbol",
                       direction="backward")
    merged_rows.append(m)
fund_on_grid = pd.concat(merged_rows, ignore_index=True)
print(f"[DATA] fundamentals asof-merged onto panel grid: {fund_on_grid.shape[0]} rows, "
      f"non-null earnings_confirm_v2: {fund_on_grid['earnings_confirm_v2'].notna().sum()}")

fund_on_grid = fund_on_grid.merge(smap[["symbol", "theme_dummy"]], on="symbol", how="left")
fund_on_grid = fund_on_grid.merge(smap[["symbol", "macro_sector"]], on="symbol", how="left")
fund_on_grid = fund_on_grid.merge(c7, on=["date", "symbol"], how="left")
fund_on_grid.to_parquet(OUT_DIR / "_w6fg2_fund_on_grid.parquet", index=False)
staleness = (fund_on_grid["date"] - fund_on_grid["available_date"]).dt.days.median()
print(f"[DATA] staleness check (median days panel-date vs fundamentals available_date used): {staleness}")

print("STEP 1 done. Output:", OUT_DIR / "_w6fg2_fund_on_grid.parquet")
