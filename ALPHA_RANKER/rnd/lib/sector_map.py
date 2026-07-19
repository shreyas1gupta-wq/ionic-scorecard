"""
WAVE-2 W2-sector worker -- sector / sub-sector mapping builder.

Builds ALPHA_RANKER/data/universe/sector_map.parquet: one row per symbol,
columns {symbol, macro_sector, sub_sector, macro_source, sub_source}.

SOURCES (merge, prefer finest -- priority order documented per column):
1. `ALPHA_RANKER/data/universe/nifty_total_market_750.csv` -- `Industry` col,
   22 macro-sector buckets, 751 symbols. This is the SAME column
   `rnd/lib/build_panel.py` joins onto the production panel as `panel.sector`,
   so treating it as the macro_sector authority keeps this map consistent
   with the panel that the harness scores against.
2. `datasets/derived/sector_industry_map.parquet` -- `Sector` col, 79 FINE
   industry buckets (screener.in-style), 2235 symbols. Pre-existing file
   (not built by this worker), used here as the primary SUB-SECTOR source
   (finest classification with the widest coverage found in the repo).
3. `datasets/india_stock_metadata/india.csv` -- `sector` col, 21 buckets
   (FactSet/GICS-style e.g. "Process industries", "Finance"), NSE+BSE,
   5022 tickers. Used as a last-resort fallback for BOTH macro_sector and
   sub_sector where sources 1-2 have no entry.

screener_live/<SYM>.json CHECKED [DATA]: neither top_ratios nor breadcrumbs
carry any sector/industry field in this dataset (grepped for
"sector"/"industry" (any case) across the whole screener_live directory --
zero matches). NOT used as a source; documented here so this isn't silently
re-attempted.

MACRO BUCKETING OF THE 79 FINE SUB-SECTORS [INFERENCE]: source (2) has no
macro parent field, so a fine->macro lookup table (`_FINE_TO_MACRO` below,
built by this worker, all 79 keys covered) buckets each fine sub_sector into
one of ~20 macro categories, reusing the source-1 `Industry` label names
where the concept matches 1:1 (e.g. "Banks"/"Finance"->"Financial Services")
and adding a small number of new macro buckets no NSE Industry class covers
well (e.g. "Agriculture" for Sugar/Agro Chemicals/Plantation/Fertilizers/
Edible Oil). This table is ONLY consulted for symbols absent from source 1
(i.e. the ~1400+ names outside the current 750-constituent list) --
whenever a symbol is covered by source 1, that value wins outright, no
inference involved. Two Sector labels in source (2) are garbled at ingest
("de Oil & Natural Gas", "dit Rating Agencies" -- truncated "Cru[de] Oil..."
/ "Cre[dit] Rating...") and are mapped through as-is with the truncation
preserved in the LOOKUP KEY only (mapped to the sensible completed concept).

PIT CAVEAT: sector/sub-sector membership is treated as ~STATIC (current
classification applied to the whole history), same convention as
`panel.sector` in PANEL_SCHEMA.md ("static, CURRENT industry classification
applied to all historical rows (not PIT-tracked reclassifications)"). A
name that was reclassified mid-sample (rare) will show its CURRENT sector
even for pre-reclassification dates. Mild caveat, not corrected here.

Coverage universe = union of: screener_live scraped symbols (~2180),
nifty_total_market_750 symbols (751), sector_industry_map symbols (2235),
india.csv NSE-market tickers -- i.e. every symbol this repo has fundamentals
or a price series for, not just the 750. No fabrication: symbols with no
match in any of the 3 sources get NaN in both sector columns (explicit, not
silently dropped or backfilled).
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent
REPO_ROOT = ALPHA_DIR.parent

N750_PATH = ALPHA_DIR / "data" / "universe" / "nifty_total_market_750.csv"
SCREENER_DIR = ALPHA_DIR / "data" / "fundamentals" / "screener_live"
FINE_MAP_PATH = REPO_ROOT / "datasets" / "derived" / "sector_industry_map.parquet"
INDIA_META_PATH = REPO_ROOT / "datasets" / "india_stock_metadata" / "india.csv"
OUT_PATH = ALPHA_DIR / "data" / "universe" / "sector_map.parquet"

# --------------------------------------------------------------------------
# Fine (79-bucket, source 2) -> macro lookup [INFERENCE], all 79 keys covered.
# --------------------------------------------------------------------------
_FINE_TO_MACRO = {
    "Finance": "Financial Services",
    "IT - Software": "Information Technology",
    "Textiles": "Textiles",
    "Chemicals": "Chemicals",
    "Pharmaceuticals": "Healthcare",
    "Miscellaneous": "Diversified",
    "Trading": "Services",
    "Auto Ancillaries": "Automobile and Auto Components",
    "Steel": "Metals & Mining",
    "Capital Goods-Non Electrical Equipment": "Capital Goods",
    "Construction": "Construction",
    "FMCG": "Fast Moving Consumer Goods",
    "Realty": "Realty",
    "Capital Goods - Electrical Equipment": "Capital Goods",
    "Entertainment": "Media Entertainment & Publication",
    "Plastic products": "Chemicals",
    "Infrastructure Developers & Operators": "Construction",
    "Banks": "Financial Services",
    "Logistics": "Services",
    "Packaging": "Capital Goods",
    "Consumer Durables": "Consumer Durables",
    "Cement": "Construction Materials",
    "Healthcare": "Healthcare",
    "Retail": "Consumer Services",
    "Sugar": "Agriculture",
    "Castings Forgings & Fastners": "Capital Goods",
    "Engineering": "Capital Goods",
    "Power Generation & Distribution": "Power",
    "Hotels & Restaurants": "Consumer Services",
    "Paper": "Chemicals",
    "Agro Chemicals": "Agriculture",
    "Mining & Mineral products": "Metals & Mining",
    "Plantation & Plantation Products": "Agriculture",
    "Stock/ Commodity Brokers": "Financial Services",
    "Fertilizers": "Agriculture",
    "Diamond Gems and Jewellery": "Consumer Durables",
    "Cables": "Capital Goods",
    "Non Ferrous Metals": "Metals & Mining",
    "Automobile": "Automobile and Auto Components",
    "Diversified": "Diversified",
    "Edible Oil": "Agriculture",
    "E-Commerce/App based Aggregator": "Consumer Services",
    "Media - Print/Television/Radio": "Media Entertainment & Publication",
    "Electronics": "Consumer Durables",
    "Alcoholic Beverages": "Fast Moving Consumer Goods",
    "Telecomm-Service": "Telecommunication",
    "Leather": "Textiles",
    "Education": "Consumer Services",
    "Petrochemicals": "Chemicals",
    "Telecomm Equipment & Infra Services": "Telecommunication",
    "Readymade Garments/ Apparells": "Textiles",
    "Printing & Stationery": "Diversified",
    "Gas Distribution": "Oil Gas & Consumable Fuels",
    "Ceramic Products": "Construction Materials",
    "Tyres": "Automobile and Auto Components",
    "Insurance": "Financial Services",
    "IT - Hardware": "Information Technology",
    "Paints/Varnish": "Chemicals",
    "Computer Education": "Consumer Services",
    "Glass & Glass Products": "Construction Materials",
    "Quick Service Restaurant": "Consumer Services",
    "Refineries": "Oil Gas & Consumable Fuels",
    "Bearings": "Capital Goods",
    "de Oil & Natural Gas": "Oil Gas & Consumable Fuels",  # truncated "Cru[de] Oil & Natural Gas"
    "Shipping": "Services",
    "Cement - Products": "Construction Materials",
    "Infrastructure Investment Trusts": "Realty",
    "Oil Drill/Allied": "Oil Gas & Consumable Fuels",
    "Real Estate Investment Trusts": "Realty",
    "Air Transport Service": "Services",
    "Tobacco Products": "Fast Moving Consumer Goods",
    "Refractories": "Construction Materials",
    "Marine Port & Services": "Services",
    "Power Infrastructure": "Power",
    "dit Rating Agencies": "Financial Services",  # truncated "Cre[dit] Rating Agencies"
    "Ship Building": "Capital Goods",
    "Dry cells": "Consumer Durables",
    "Ferro Alloys": "Metals & Mining",
    "Railways": "Services",
}


def _load_n750() -> pd.DataFrame:
    df = pd.read_csv(N750_PATH)
    df = df.rename(columns={"Symbol": "symbol", "Industry": "macro_n750"})
    return df[["symbol", "macro_n750"]].drop_duplicates("symbol")


def _load_fine_map() -> pd.DataFrame:
    df = pd.read_parquet(FINE_MAP_PATH)
    df = df.rename(columns={"Sector": "sub_fine"})
    df["macro_from_fine"] = df["sub_fine"].map(_FINE_TO_MACRO)
    unmapped = df.loc[df["sub_fine"].notna() & df["macro_from_fine"].isna(), "sub_fine"].unique()
    if len(unmapped):
        # Disclosed, not silently dropped: any fine label this worker didn't
        # anticipate falls back to NaN macro (never fabricated).
        print(f"[sector_map] WARNING: {len(unmapped)} fine sub_sector labels have no "
              f"macro mapping (left NaN): {sorted(unmapped)[:10]}")
    return df[["symbol", "sub_fine", "macro_from_fine"]].drop_duplicates("symbol")


def _load_india_meta() -> pd.DataFrame:
    df = pd.read_csv(INDIA_META_PATH)
    df = df[df["market"] == "NSE"].copy()
    df = df.rename(columns={"ticker": "symbol", "sector": "macro_india"})
    return df[["symbol", "macro_india"]].drop_duplicates("symbol")


def _universe_symbols() -> set[str]:
    syms = set()
    if SCREENER_DIR.exists():
        syms |= {p.stem for p in SCREENER_DIR.glob("*.json")}
    if N750_PATH.exists():
        syms |= set(pd.read_csv(N750_PATH)["Symbol"].astype(str))
    if FINE_MAP_PATH.exists():
        syms |= set(pd.read_parquet(FINE_MAP_PATH)["symbol"].astype(str))
    if INDIA_META_PATH.exists():
        d = pd.read_csv(INDIA_META_PATH)
        syms |= set(d.loc[d["market"] == "NSE", "ticker"].astype(str))
    return syms


def build_sector_map() -> pd.DataFrame:
    universe = sorted(_universe_symbols())
    out = pd.DataFrame({"symbol": universe})

    n750 = _load_n750()
    fine = _load_fine_map()
    india = _load_india_meta()

    out = out.merge(n750, on="symbol", how="left")
    out = out.merge(fine, on="symbol", how="left")
    out = out.merge(india, on="symbol", how="left")

    # macro_sector priority: n750 Industry > fine->macro lookup > india.csv sector
    out["macro_sector"] = out["macro_n750"]
    out["macro_source"] = out["macro_n750"].where(out["macro_n750"].isna(), "n750")
    fill = out["macro_sector"].isna() & out["macro_from_fine"].notna()
    out.loc[fill, "macro_sector"] = out.loc[fill, "macro_from_fine"]
    out.loc[fill, "macro_source"] = "fine_derived"
    fill = out["macro_sector"].isna() & out["macro_india"].notna()
    out.loc[fill, "macro_sector"] = out.loc[fill, "macro_india"]
    out.loc[fill, "macro_source"] = "india_meta"
    out["macro_source"] = out["macro_source"].where(out["macro_sector"].notna(), pd.NA)

    # sub_sector priority: fine (79-bucket) > n750 Industry (coarser fallback) > india.csv sector
    out["sub_sector"] = out["sub_fine"]
    out["sub_source"] = out["sub_fine"].where(out["sub_fine"].isna(), "fine_map")
    fill = out["sub_sector"].isna() & out["macro_n750"].notna()
    out.loc[fill, "sub_sector"] = out.loc[fill, "macro_n750"]
    out.loc[fill, "sub_source"] = "n750_fallback"
    fill = out["sub_sector"].isna() & out["macro_india"].notna()
    out.loc[fill, "sub_sector"] = out.loc[fill, "macro_india"]
    out.loc[fill, "sub_source"] = "india_meta_fallback"
    out["sub_source"] = out["sub_source"].where(out["sub_sector"].notna(), pd.NA)

    final = out[["symbol", "macro_sector", "sub_sector", "macro_source", "sub_source"]].copy()
    final = final.sort_values("symbol").reset_index(drop=True)
    return final


def main():
    df = build_sector_map()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    n = len(df)
    macro_cov = df["macro_sector"].notna().sum()
    sub_cov = df["sub_sector"].notna().sum()
    print(f"[sector_map] wrote {OUT_PATH} rows={n}")
    print(f"[sector_map] macro_sector coverage: {macro_cov}/{n} ({macro_cov/n:.1%})")
    print(f"[sector_map] sub_sector coverage:   {sub_cov}/{n} ({sub_cov/n:.1%})")
    print("[sector_map] macro_source breakdown:\n", df["macro_source"].value_counts(dropna=False).to_string())
    print("[sector_map] sub_source breakdown:\n", df["sub_source"].value_counts(dropna=False).to_string())
    print(f"[sector_map] macro_sector nunique: {df['macro_sector'].nunique()}")
    print(f"[sector_map] sub_sector nunique:   {df['sub_sector'].nunique()}")


if __name__ == "__main__":
    main()
