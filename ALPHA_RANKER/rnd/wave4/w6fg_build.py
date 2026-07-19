"""
W6FG: Forward-Growth / Theme dimension + Value-vs-Growth (GARP) divergence classifier.
Devika Menon (fm-equities) + Quant Head coordination, 2026-07-17.

STEP 1 of the task: build PIT fundamentals-derived growth-acceleration / margin-
inflection / theme-tag factors, earnings-confirmed composite, and the GARP
quadrant, then run them through the ONE evaluation harness (rnd/lib/harness.py)
so results are directly comparable to every other card in cards/ (no bespoke
scoring path — RESEARCH_PROTOCOL.md S3).

No lookahead: fundamentals are joined to the monthly panel grid via merge_asof
on `available_date <= date` (backward), per symbol. Restated filings (same
fiscal_year, multiple available_date) are collapsed to the FIRST disclosed
available_date (min), never the latest restatement, to avoid using
information not knowable at the time.
"""
import sys, json, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import harness as H

ALPHA_DIR = Path(__file__).resolve().parent.parent.parent
OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("W6FG STEP 1: building PIT forward-growth factors")
print("=" * 70)

# ---------------------------------------------------------------------------
# 1. Load raw fundamentals, pivot to wide per (symbol, fiscal_year)
# ---------------------------------------------------------------------------
mf = pd.read_parquet(ALPHA_DIR / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet")
metrics_needed = ["sales", "operating profit", "net profit", "opm %", "cwip", "fixed assets", "borrowings"]
mf = mf[mf["metric_norm"].isin(metrics_needed)].copy()

# PIT-safe: collapse restatements to the FIRST disclosed available_date per (symbol,fy)
first_avail = mf.groupby(["nse_symbol", "fiscal_year"])["available_date"].transform("min")
mf = mf[mf["available_date"] == first_avail]
# if still dup metric rows within a (symbol,fy,metric) after this filter, take first
mf = mf.drop_duplicates(subset=["nse_symbol", "fiscal_year", "metric_norm"], keep="first")

wide = mf.pivot_table(index=["nse_symbol", "fiscal_year"], columns="metric_norm",
                       values="value", aggfunc="first")
avail = mf.groupby(["nse_symbol", "fiscal_year"])["available_date"].min()
wide = wide.join(avail.rename("available_date"))
wide = wide.reset_index().sort_values(["nse_symbol", "fiscal_year"])
print(f"[DATA] wide fundamentals panel: {wide.shape[0]} symbol-fiscal_year rows, "
      f"{wide['nse_symbol'].nunique()} symbols, FY range {wide.fiscal_year.min()}-{wide.fiscal_year.max()}")

# ---------------------------------------------------------------------------
# 2. Derived PIT factors per (symbol, fiscal_year) — using ONLY t, t-1, t-2, t-3
#    same-symbol prior rows (shift within group, chronologically sorted, so no
#    cross-symbol or future-fiscal-year leakage).
# ---------------------------------------------------------------------------
g = wide.groupby("nse_symbol", group_keys=False)

def _safe_growth(cur, prev):
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where((prev > 0) & np.isfinite(prev) & np.isfinite(cur), cur / prev - 1.0, np.nan)
    return out

wide["sales_l1"] = g["sales"].shift(1)
wide["sales_l2"] = g["sales"].shift(2)
wide["op_l1"] = g["operating profit"].shift(1)
wide["cwip_l1"] = g["cwip"].shift(1)
wide["opm_l1"] = g["opm %"].shift(1)
wide["opm_l2"] = g["opm %"].shift(2)
wide["opm_l3"] = g["opm %"].shift(3)
wide["fixed_assets_l0"] = wide["fixed assets"]

wide["rev_growth_t"] = _safe_growth(wide["sales"].values, wide["sales_l1"].values)
wide["rev_growth_t1"] = _safe_growth(wide["sales_l1"].values, wide["sales_l2"].values)
wide["rev_accel"] = wide["rev_growth_t"] - wide["rev_growth_t1"]   # growth ACCELERATION (2nd derivative)

wide["op_growth_t"] = _safe_growth(wide["operating profit"].values, wide["op_l1"].values)
wide["cwip_growth_t"] = _safe_growth(wide["cwip"].values, wide["cwip_l1"].values)
wide["cwip_intensity"] = wide["cwip"] / wide["fixed_assets_l0"].replace(0, np.nan)

wide["opm_trail3"] = wide[["opm_l1", "opm_l2", "opm_l3"]].mean(axis=1, skipna=True)
wide["margin_inflection"] = wide["opm %"] - wide["opm_trail3"]     # margin INFLECTION vs own trailing 3Y avg

# earnings confirmation gate: operating profit actually growing (not just a
# revenue/story number) — this is the "theme+earnings=stays" discipline.
wide["earnings_confirm"] = (wide["op_growth_t"] > 0).astype(float)
wide.loc[wide["op_growth_t"].isna(), "earnings_confirm"] = np.nan

keep_cols = ["nse_symbol", "fiscal_year", "available_date", "rev_growth_t", "rev_accel",
             "op_growth_t", "cwip_growth_t", "cwip_intensity", "margin_inflection", "earnings_confirm",
             "opm %"]
fund_derived = wide[keep_cols].rename(columns={"nse_symbol": "symbol"}).copy()
fund_derived["available_date"] = pd.to_datetime(fund_derived["available_date"])
n_have_accel = fund_derived["rev_accel"].notna().sum()
n_have_confirm = fund_derived["earnings_confirm"].notna().sum()
print(f"[DATA] rev_accel available: {n_have_accel}/{len(fund_derived)} rows "
      f"(needs 3 consecutive FY of sales); earnings_confirm available: {n_have_confirm}")
fund_derived.to_parquet(OUT_DIR / "_w6fg_fund_derived.parquet", index=False)

# ---------------------------------------------------------------------------
# 3. Theme tag from sector_map (macro_sector/sub_sector text match) — a STATIC
#    structural tag, disclosed as such: this alone carries no PIT timing info,
#    it is deliberately tested for whether it adds anything beyond dynamic
#    accel/margin/earnings signals (task's story-chasing concern).
# ---------------------------------------------------------------------------
smap = pd.read_parquet(ALPHA_DIR / "data" / "universe" / "sector_map.parquet")
theme_kw = r"renewable|solar|green|defence|electronics manufactur|\bems\b|capital goods|power|infrastructure|clean energy|battery|semiconductor"
txt = (smap["macro_sector"].fillna("") + " | " + smap["sub_sector"].fillna("")).str.lower()
smap["theme_dummy"] = txt.str.contains(theme_kw, regex=True, na=False).astype(float)
print(f"[DATA] sector_map: {len(smap)} symbols, theme_dummy=1 for {int(smap['theme_dummy'].sum())} "
      f"({smap['theme_dummy'].mean():.1%})")
smap[["symbol", "macro_sector", "sub_sector", "theme_dummy"]].to_parquet(
    OUT_DIR / "_w6fg_theme_tag.parquet", index=False)

# ---------------------------------------------------------------------------
# 4. Load the monthly panel grid (panel_long — full 2005-2025 history) and the
#    canonical 7-leg value/quality score, asof-merge fundamentals PIT.
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
      f"non-null rev_accel: {fund_on_grid['rev_accel'].notna().sum()}")

fund_on_grid = fund_on_grid.merge(smap[["symbol", "theme_dummy"]], on="symbol", how="left")
fund_on_grid = fund_on_grid.merge(c7, on=["date", "symbol"], how="left")
fund_on_grid.to_parquet(OUT_DIR / "_w6fg_fund_on_grid.parquet", index=False)
print(f"[DATA] staleness check (median days between panel date and fundamentals "
      f"available_date used): "
      f"{(fund_on_grid['date'] - fund_on_grid['available_date']).dt.days.median()}")

print("STEP 1 done. Output:", OUT_DIR / "_w6fg_fund_on_grid.parquet")
