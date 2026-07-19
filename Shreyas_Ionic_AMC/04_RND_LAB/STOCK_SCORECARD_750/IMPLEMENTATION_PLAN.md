# STOCK_SCORECARD_750 Implementation Plan (v2 — verified against real data schemas)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a transparent, percentile-rank composite scorer that assigns every stock in the Nifty-750 universe a 0-100 score across 8 pillars (Quality, Growth, Value-Relative, DCF/Intrinsic-Value, Stage/Technical, Sector&Macro, Ownership Flow, Accumulation) plus 2 overlay gates (Balance-Sheet Safety, Liquidity), with a monthly regime tilt on top.

**Architecture:** A data-foundation module loads PIT-filtered raw fundamentals + prices + ownership + universe once, with column names matching the REAL files (verified 2026-07-17, not assumed). A derived-ratios module converts raw Screener-style line items (sales, net profit, borrowings, ...) into the ratios the pillars need (ROE, ROCE, P/E, ...), since none of those ratios are pre-computed in the source data. 8 pillar functions (grouped into 3 files by data dependency) each independently compute a 0-100 score. An orchestrator applies base weights + regime tilt + overlay gates, isolates failures per pillar-group so one bad data source can't kill the whole run, writes output atomically, and re-weights the composite over only the pillars each stock actually has data for.

**Tech Stack:** Python 3.14, pandas, numpy, pyarrow (parquet), pytest.

**Spec:** `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/MASTER_PLAN.md` (read this first, especially the "Addendum 2026-07-17" section — this plan implements it verbatim).

**v1 -> v2 changelog:** two independent review passes (data-quality lens, ops-robustness lens) verified the real data files and found v1's assumed column/metric names were wrong throughout, and found real robustness gaps. v2 fixes: real schemas everywhere (Task 1), a new derived-ratios module (Task 5) since fundamentals are raw line items not pre-computed ratios, PIT-filtered ownership using pre-computed QoQ columns (Task 9), tiny-sector percentile fallback (Task 2), promoter-pledge-unavailable handling (Task 10), DCF eligibility now checks FCF sign-consistency + beta/price presence not just year-count (Task 7), partial-failure isolation + atomic writes + proper coverage-aware re-weighting in the orchestrator (Task 11).

## Global Constraints
- Python executable: `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe` (the `python` alias is broken on this machine) — always invoke scripts/tests via this full path.
- Every script sets `PYTHONIOENCODING=utf-8` and `PYTHONUNBUFFERED=1` (console is cp1252).
- **No lookahead**: fundamentals AND ownership must be filtered to `available_date <= as_of_date` before any computation touches them.
- **Percentile-rank only** — no z-scores, no ML weights.
- **Missing data is excluded from averages, never zero-filled** — at both the per-pillar metric level AND the composite level (a stock missing a whole pillar gets the composite re-weighted over its remaining pillars, not that pillar's weight silently zeroed).
- All weights, thresholds, and assumption constants live in `build_scorecard.py` — never hardcoded inside a pillar function.
- Output written as both `.parquet` and `.csv`, both via atomic temp-file-then-rename.
- **Real column/metric names below are verified against the actual files on disk (2026-07-17) — do not "fix" them back to more conventional-looking names without re-checking the real file.**
- If executed via subagent-driven-development: max 3 parallel agents (firm rule D-023).
- All file paths below are relative to `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/` unless given as an absolute path to an external dataset.
- **Naming note:** `MASTER_PLAN.md`'s output schema lists short column names (`growth`, `stage`, ...); this plan's pillar functions consistently suffix their output column with `_score`/`_percentile`/`_pct` so a name alone tells you it's computed, not raw. Task 11's orchestrator is the single source of truth for actual final column names.

---

### Task 1: Data foundation (real schemas)

**Files:**
- Create: `lib/data_foundation.py`
- Test: `tests/test_data_foundation.py`

**Interfaces:**
- Produces: `load_universe() -> pd.DataFrame` [symbol, sector, sub_sector]; `load_fundamentals_pit(as_of_date: str) -> pd.DataFrame` [symbol, fiscal_year, period_label, statement, metric, metric_norm, value, available_date, source, is_fresh] — raw line items, e.g. metric_norm in {"sales","net profit","operating profit","opm %","eps in rs","equity capital","reserves","borrowings","borrowing","interest","cash from operating activity","total assets","free cash flow",...}; `load_prices(symbols: list) -> pd.DataFrame` [symbol, date, open, high, low, close, adj_close, volume]; `load_ownership(as_of_date: str) -> pd.DataFrame` [symbol, quarter_end, available_date, FIIs, FIIs_qoq, FIIs_yoy, DIIs, DIIs_qoq, DIIs_yoy, Promoters, Promoters_qoq, Promoters_yoy, Public, Government, Others, ...]

- [ ] **Step 1: Write the failing test for PIT filtering**

```python
# tests/test_data_foundation.py
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from data_foundation import filter_pit

def test_filter_pit_excludes_future_data():
    df = pd.DataFrame({
        "symbol": ["A", "A", "B"],
        "value": [10, 20, 30],
        "available_date": pd.to_datetime(["2024-01-01", "2024-06-01", "2024-03-01"]),
    })
    result = filter_pit(df, as_of_date="2024-04-01")
    assert set(result["value"]) == {10, 30}
    assert len(result) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_data_foundation.py -v`
Expected: FAIL with "cannot import name 'filter_pit'"

- [ ] **Step 3: Write minimal implementation (real column names, verified 2026-07-17)**

```python
# lib/data_foundation.py
import os
import pandas as pd

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

ALPHA_RANKER_DATA = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\data"
FIRM_DATASETS = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"


def filter_pit(df: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    cutoff = pd.Timestamp(as_of_date)
    return df[df["available_date"] <= cutoff].copy()


def load_universe() -> pd.DataFrame:
    symbols = pd.read_csv(f"{ALPHA_RANKER_DATA}/universe/symbols_750.txt", header=None, names=["symbol"])
    # real sector_map.parquet columns: [symbol, macro_sector, sub_sector, macro_source, sub_source]
    sector_map = pd.read_parquet(f"{ALPHA_RANKER_DATA}/universe/sector_map.parquet")
    merged = symbols.merge(sector_map, on="symbol", how="left").rename(columns={"macro_sector": "sector"})
    return merged[["symbol", "sector", "sub_sector"]]


def load_fundamentals_pit(as_of_date: str) -> pd.DataFrame:
    df = pd.read_parquet(f"{ALPHA_RANKER_DATA}/fundamentals/MASTER_fundamentals_pit.parquet")
    # real columns: [key_symbol, nse_symbol, company, fiscal_year, period_label, statement,
    # metric, metric_norm, value, available_date, source, is_fresh] -- no bare "symbol" column.
    # nse_symbol is the NSE ticker (matches universe/prices symbol convention) -- spot-checked
    # in Step 5, not key_symbol (an internal id).
    df = df.rename(columns={"nse_symbol": "symbol"})
    df["available_date"] = pd.to_datetime(df["available_date"])
    # real data has occasional duplicate (symbol, metric_norm, fiscal_year) rows -- keep the
    # last (freshest ingest) deterministically rather than silently averaging duplicates later.
    df = df.drop_duplicates(subset=["symbol", "metric_norm", "fiscal_year"], keep="last")
    return filter_pit(df, as_of_date)


def load_prices(symbols: list) -> pd.DataFrame:
    frames = []
    for sym in symbols:
        path = f"{ALPHA_RANKER_DATA}/prices/{sym}.parquet"
        if os.path.exists(path):
            # real per-symbol files: DatetimeIndex named "Date", columns
            # ['Adj Close','Close','High','Low','Open','Volume'] (Title Case, no "date" column).
            g = pd.read_parquet(path).reset_index()
            g = g.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low",
                                    "Close": "close", "Volume": "volume", "Adj Close": "adj_close"})
            g["symbol"] = sym
            frames.append(g)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["symbol", "date", "open", "high", "low", "close", "adj_close", "volume"])


def load_ownership(as_of_date: str) -> pd.DataFrame:
    # real columns: [symbol, quarter_end, available_date, FIIs, FIIs_qoq, FIIs_yoy, DIIs,
    # DIIs_qoq, DIIs_yoy, Government, ..., Promoters, Promoters_qoq, Promoters_yoy, Public, ...]
    # -- already PIT-stamped and already carries pre-computed QoQ/YoY, unlike v1 assumed.
    df = pd.read_parquet(f"{FIRM_DATASETS}/derived/shareholding_changes.parquet")
    df["available_date"] = pd.to_datetime(df["available_date"])
    return filter_pit(df, as_of_date)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_data_foundation.py -v`
Expected: PASS

- [ ] **Step 5: D-009 spot-check (manual review) — confirm nse_symbol is the right join key and sample real values**

```python
# scratch_d009_check.py (delete after use)
from lib.data_foundation import load_fundamentals_pit, load_universe
u = load_universe()
print(f"Universe: {len(u)} symbols, {u['sector'].isna().sum()} missing sector")
f = load_fundamentals_pit(as_of_date="2026-07-17")
sample = u["symbol"].head(10).tolist()
matched = f[f["symbol"].isin(sample)]
print(f"Matched {matched['symbol'].nunique()}/10 sample symbols via nse_symbol join -- "
      f"if this is low, key_symbol may be the right join key instead, investigate before Task 5.")
print(matched[matched["metric_norm"].isin(["sales", "net profit", "eps in rs"])]
      .sort_values(["symbol", "fiscal_year"]).to_string())

import pandas as pd
screener_deep = pd.read_parquet(
    r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets\screener_deep\screener_annual_pl.parquet")
print("--- cross-check vs firm's own screener_deep pull, same symbols ---")
print(screener_deep[screener_deep["symbol"].isin(sample)].to_string())
```

Post both tables here for Principal/Kavya visual sanity-check — specifically confirm the join-match rate is high (low match rate means `nse_symbol` isn't the right key and Task 5's derived ratios would silently run on a near-empty join).

- [ ] **Step 6: Add the missing DATA_CATALOG.md entry**

Append to `Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_CATALOG.md` (match its existing table's exact column order):

```markdown
| stock_scorecard_fundamentals_pit | ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet | 4,613 symbols, long/tidy RAW line items (not ratios), has available_date (PIT-safe) | screener_live | D-009 spot-checked 2026-07-17 vs screener_deep (Task 1 Step 5) | STOCK_SCORECARD_750 |
```

- [ ] **Step 7: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/data_foundation.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_data_foundation.py" "Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_CATALOG.md"
git commit -m "feat(scorecard): data foundation loaders matching verified real schemas"
```

---

### Task 2: Rank utilities (percentile rank + tiny-sector fallback + coverage-aware averaging)

**Files:**
- Create: `lib/rank_utils.py`
- Test: `tests/test_rank_utils.py`

**Interfaces:**
- Produces: `percentile_rank(df: pd.DataFrame, col: str, group_col: str = None, ascending: bool = True, min_group_size: int = 5) -> pd.Series`; `coverage_aware_average(df: pd.DataFrame, score_cols: list) -> pd.DataFrame` [pillar_score, coverage_pct, coverage_flag]

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rank_utils.py
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from rank_utils import percentile_rank, coverage_aware_average

def test_percentile_rank_sector_neutral():
    df = pd.DataFrame({
        "symbol": ["A", "B", "C", "D", "E", "F"],
        "sector": ["IT", "IT", "IT", "IT", "Cement", "Cement"],
        "roe": [30, 25, 20, 10, 15, 5],
    })
    result = percentile_rank(df, "roe", group_col="sector")
    assert result.loc[df["symbol"] == "A"].iloc[0] > result.loc[df["symbol"] == "D"].iloc[0]
    assert result.loc[df["symbol"] == "E"].iloc[0] > result.loc[df["symbol"] == "F"].iloc[0]
    assert result.loc[df["symbol"] == "E"].iloc[0] > result.loc[df["symbol"] == "D"].iloc[0]

def test_percentile_rank_falls_back_to_universe_for_tiny_sectors():
    # Realty has only 1 member -- a naive sector-neutral rank would trivially give it 100th
    # percentile regardless of its actual ROE. min_group_size=5 forces a universe-wide fallback.
    df = pd.DataFrame({
        "symbol": ["A", "B", "C", "D", "E", "F"],
        "sector": ["IT", "IT", "IT", "IT", "IT", "Realty"],
        "roe": [30, 25, 20, 15, 10, 1],  # Realty's lone stock has the WORST roe in the universe
    })
    result = percentile_rank(df, "roe", group_col="sector", min_group_size=5)
    realty_score = result.loc[df["symbol"] == "F"].iloc[0]
    assert realty_score < 20  # falls back to universe rank (worst of 6) instead of a trivial 100

def test_percentile_rank_ascending_false_inverts():
    df = pd.DataFrame({"symbol": ["A", "B"], "pe": [40, 10]})
    result = percentile_rank(df, "pe", ascending=False)
    assert result.loc[df["symbol"] == "B"].iloc[0] > result.loc[df["symbol"] == "A"].iloc[0]

def test_coverage_aware_average_excludes_missing():
    df = pd.DataFrame({"m1": [80.0, None], "m2": [60.0, 90.0]})
    result = coverage_aware_average(df, ["m1", "m2"])
    assert result["pillar_score"].iloc[0] == 70.0
    assert result["pillar_score"].iloc[1] == 90.0
    assert result["coverage_pct"].iloc[1] == 50.0
    assert result["coverage_flag"].iloc[1] == "Med"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_rank_utils.py -v`
Expected: FAIL with "cannot import name 'percentile_rank'"

- [ ] **Step 3: Write minimal implementation**

```python
# lib/rank_utils.py
import pandas as pd
import numpy as np


def percentile_rank(df: pd.DataFrame, col: str, group_col: str = None, ascending: bool = True,
                     min_group_size: int = 5) -> pd.Series:
    series = df[col] if ascending else -df[col]
    if not group_col:
        return series.rank(pct=True) * 100

    group_sizes = df.groupby(group_col)[col].transform("count")
    within_group = series.groupby(df[group_col]).rank(pct=True) * 100
    universe_wide = series.rank(pct=True) * 100
    return within_group.where(group_sizes >= min_group_size, universe_wide)


def coverage_aware_average(df: pd.DataFrame, score_cols: list) -> pd.DataFrame:
    sub = df[score_cols]
    pillar_score = sub.mean(axis=1, skipna=True)
    coverage_pct = sub.notna().sum(axis=1) / len(score_cols) * 100
    coverage_flag = pd.cut(coverage_pct, bins=[-1, 33.34, 66.67, 100], labels=["Low", "Med", "High"])
    return pd.DataFrame({
        "pillar_score": pillar_score,
        "coverage_pct": coverage_pct,
        "coverage_flag": coverage_flag.astype(str),
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_rank_utils.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/rank_utils.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_rank_utils.py"
git commit -m "feat(scorecard): sector-neutral percentile rank with tiny-sector fallback + coverage-aware averaging"
```

---

### Task 3: Cyclicality tag (real 41-sector taxonomy, case-normalized) + market-cap tercile

**Files:**
- Create: `lib/cyclicality_map.py`
- Test: `tests/test_cyclicality_map.py`

**Interfaces:**
- Produces: `SECTOR_CYCLICALITY: dict`; `tag_cyclicality(df: pd.DataFrame, sector_col: str = "sector") -> pd.Series`; `market_cap_tercile(df: pd.DataFrame, mcap_col: str = "market_cap") -> pd.Series`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cyclicality_map.py
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from cyclicality_map import tag_cyclicality, market_cap_tercile

def test_tag_cyclicality_known_sectors_case_insensitive():
    df = pd.DataFrame({"sector": ["Metals & Mining", "Fast Moving Consumer Goods", "Finance",
                                    "Consumer durables", "Consumer Durables", "UnknownSector"]})
    result = tag_cyclicality(df)
    assert result.iloc[0] == "Cyclical"
    assert result.iloc[1] == "Defensive-Stable"
    assert result.iloc[2] == "Sensitive-hybrid"
    # both case variants of the same real duplicate category must map identically
    assert result.iloc[3] == result.iloc[4]
    assert result.iloc[5] == "Defensive-Stable"  # safe fallback, never null

def test_market_cap_tercile():
    df = pd.DataFrame({"market_cap": [100, 200, 300, 10000, 20000, 30000]})
    result = market_cap_tercile(df)
    assert result.iloc[0] == "Small"
    assert result.iloc[-1] == "Large"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_cyclicality_map.py -v`
Expected: FAIL with "cannot import name 'tag_cyclicality'"

- [ ] **Step 3: Write minimal implementation (real 41 macro_sector values, verified 2026-07-17)**

```python
# lib/cyclicality_map.py
import pandas as pd

# v1 approximation (MASTER_PLAN.md Open Risks) -- static lookup, not a dynamic model.
# Keys are the REAL macro_sector values from sector_map.parquet (verified 2026-07-17, all 41).
# Matching is case-insensitive because the real data has duplicate-by-case categories
# ("Consumer durables" vs "Consumer Durables") -- see MASTER_PLAN.md Addendum.
SECTOR_CYCLICALITY = {
    "metals & mining": "Cyclical", "construction materials": "Cyclical", "capital goods": "Cyclical",
    "automobile and auto components": "Cyclical", "realty": "Cyclical", "construction": "Cyclical",
    "oil gas & consumable fuels": "Cyclical", "chemicals": "Cyclical", "textiles": "Cyclical",
    "non-energy minerals": "Cyclical", "energy minerals": "Cyclical", "process industries": "Cyclical",
    "producer manufacturing": "Cyclical", "transportation": "Cyclical", "forest materials": "Cyclical",
    "fast moving consumer goods": "Defensive-Stable", "healthcare": "Defensive-Stable",
    "health services": "Defensive-Stable", "health technology": "Defensive-Stable",
    "information technology": "Defensive-Stable", "technology services": "Defensive-Stable",
    "electronic technology": "Defensive-Stable", "telecommunication": "Defensive-Stable",
    "communications": "Defensive-Stable", "utilities": "Defensive-Stable", "power": "Defensive-Stable",
    "consumer non-durables": "Defensive-Stable", "consumer durables": "Defensive-Stable",
    "consumer services": "Defensive-Stable", "agriculture": "Defensive-Stable",
    "finance": "Sensitive-hybrid", "financial services": "Sensitive-hybrid",
    "commercial services": "Sensitive-hybrid", "industrial services": "Sensitive-hybrid",
    "distribution services": "Sensitive-hybrid", "retail trade": "Sensitive-hybrid",
    "services": "Sensitive-hybrid", "media entertainment & publication": "Sensitive-hybrid",
}


def tag_cyclicality(df: pd.DataFrame, sector_col: str = "sector") -> pd.Series:
    normalized = df[sector_col].str.strip().str.lower()
    return normalized.map(SECTOR_CYCLICALITY).fillna("Defensive-Stable")


def market_cap_tercile(df: pd.DataFrame, mcap_col: str = "market_cap") -> pd.Series:
    return pd.qcut(df[mcap_col], q=3, labels=["Small", "Mid", "Large"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_cyclicality_map.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/cyclicality_map.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_cyclicality_map.py"
git commit -m "feat(scorecard): sector cyclicality tags (real 41-sector taxonomy, case-normalized) + market-cap tercile"
```

---

### Task 4: Regime classifier + tilt table

**Files:**
- Create: `lib/regime.py`
- Test: `tests/test_regime.py`

**Interfaces:**
- Produces: `classify_valuation_regime(pe_history: pd.Series, current_pe: float) -> str` returns "Cheap"|"Neutral"|"Rich" (returns "Neutral" if `pe_history` is empty — safe fallback, see Task 11 Step 3 note); `TILT_TABLE: dict`; `apply_regime_tilt(base_weights: dict, regime: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_regime.py
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from regime import classify_valuation_regime, apply_regime_tilt, TILT_TABLE

def test_classify_regime_buckets():
    history = pd.Series(range(1, 101))
    assert classify_valuation_regime(history, current_pe=10) == "Cheap"
    assert classify_valuation_regime(history, current_pe=50) == "Neutral"
    assert classify_valuation_regime(history, current_pe=95) == "Rich"

def test_classify_regime_empty_history_defaults_neutral():
    assert classify_valuation_regime(pd.Series(dtype=float), current_pe=50) == "Neutral"

def test_apply_regime_tilt_sums_to_100():
    base = {"quality": 18, "growth": 18, "value_relative": 15, "dcf": 12,
            "stage": 12, "sector_macro": 10, "ownership_flow": 8, "accumulation": 7}
    for regime in ["Cheap", "Neutral", "Rich"]:
        tilted = apply_regime_tilt(base, regime)
        assert abs(sum(tilted.values()) - 100) < 1e-9

def test_neutral_regime_is_identity():
    base = {"quality": 18, "growth": 18, "value_relative": 15, "dcf": 12,
            "stage": 12, "sector_macro": 10, "ownership_flow": 8, "accumulation": 7}
    assert apply_regime_tilt(base, "Neutral") == base
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_regime.py -v`
Expected: FAIL with "cannot import name 'classify_valuation_regime'"

- [ ] **Step 3: Write minimal implementation**

```python
# lib/regime.py

# [ASSUMPTION] Illustrative v1 tilt magnitudes -- need a sensitivity/perturbation pass
# (Sameer Bhat) before trusted. Each row's deltas net to zero by construction.
TILT_TABLE = {
    "Rich":    {"quality": +3, "dcf": +3, "stage": -3, "accumulation": -3},
    "Neutral": {},
    "Cheap":   {"value_relative": +3, "dcf": +3, "growth": +2, "quality": -4, "sector_macro": -4},
}


def classify_valuation_regime(pe_history, current_pe: float) -> str:
    if len(pe_history) == 0:
        return "Neutral"  # safe fallback if the index-valuation source isn't wired yet (Task 11)
    pctile = (pe_history < current_pe).mean() * 100
    if pctile < 33.34:
        return "Cheap"
    if pctile > 66.67:
        return "Rich"
    return "Neutral"


def apply_regime_tilt(base_weights: dict, regime: str) -> dict:
    tilted = dict(base_weights)
    for pillar, delta in TILT_TABLE.get(regime, {}).items():
        tilted[pillar] = tilted[pillar] + delta
    return tilted
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_regime.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/regime.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_regime.py"
git commit -m "feat(scorecard): valuation-regime classifier (Neutral-safe fallback) + weight tilt table"
```

---

### Task 5: Derived ratios (NEW — raw line items -> the ratios pillars need)

**Files:**
- Create: `lib/derived_ratios.py`
- Test: `tests/test_derived_ratios.py`

**Interfaces:**
- Consumes: raw fundamentals shape from Task 1's `load_fundamentals_pit` [symbol, fiscal_year, metric_norm, value, available_date, ...]; prices shape from Task 1 [symbol, date, close, ...]
- Produces: `derive_ratios(raw_fundamentals: pd.DataFrame, prices: pd.DataFrame, as_of_date: str) -> pd.DataFrame` — long-format [symbol, fiscal_year, available_date, metric_norm, value] where metric_norm is now one of: `roe, roce, debt_equity, interest_coverage, accruals_ratio, margin_stability, fcf, revenue_cagr_3y, revenue_cagr_5y, pe, pb, market_cap`. **Does not produce `promoter_pledge_pct` or `beta`** — not derivable from the current fundamentals source (see Task 10 for the balance-sheet-gate handling, and Task 11 for beta being computed separately from price history directly).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_derived_ratios.py
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from derived_ratios import derive_ratios

def _raw_fixture():
    rows = []
    for fy in [2023, 2024, 2025]:
        d = pd.Timestamp(f"{fy}-06-01")
        for metric, val in [("sales", 100 * (1.1 ** (fy - 2023))), ("net profit", 20),
                             ("operating profit", 25), ("equity capital", 10), ("reserves", 90),
                             ("borrowings", 50), ("interest", 5),
                             ("cash from operating activity", 18), ("total assets", 200),
                             ("free cash flow", 15), ("opm %", 25.0), ("eps in rs", 10)]:
            rows.append({"symbol": "A", "fiscal_year": fy, "available_date": d,
                         "metric_norm": metric, "value": val})
    return pd.DataFrame(rows)

def test_derive_ratios_computes_roe_roce_debt_equity():
    raw = _raw_fixture()
    prices = pd.DataFrame({"symbol": ["A"], "date": [pd.Timestamp("2026-01-01")], "close": [200.0]})
    result = derive_ratios(raw, prices, as_of_date="2026-01-01")
    latest = result[(result["symbol"] == "A") & (result["fiscal_year"] == 2025)]
    assert abs(latest[latest["metric_norm"] == "roe"]["value"].iloc[0] - 20 / 100) < 1e-6
    assert abs(latest[latest["metric_norm"] == "roce"]["value"].iloc[0] - 25 / 150) < 1e-6
    assert abs(latest[latest["metric_norm"] == "debt_equity"]["value"].iloc[0] - 50 / 100) < 1e-6

def test_derive_ratios_coalesces_borrowing_spelling_variants():
    # real data has BOTH "borrowing" (singular) and "borrowings" (plural) as separate
    # metric_norm values for different symbols/rows -- must not silently drop either.
    raw = _raw_fixture()
    raw.loc[raw["metric_norm"] == "borrowings", "metric_norm"] = "borrowing"
    prices = pd.DataFrame({"symbol": ["A"], "date": [pd.Timestamp("2026-01-01")], "close": [200.0]})
    result = derive_ratios(raw, prices, as_of_date="2026-01-01")
    de = result[result["metric_norm"] == "debt_equity"]["value"].iloc[-1]
    assert abs(de - 50 / 100) < 1e-6

def test_derive_ratios_pe_pb_market_cap_use_joined_price():
    raw = _raw_fixture()
    prices = pd.DataFrame({"symbol": ["A"], "date": [pd.Timestamp("2026-01-01")], "close": [200.0]})
    result = derive_ratios(raw, prices, as_of_date="2026-01-01")
    assert abs(result[result["metric_norm"] == "pe"]["value"].iloc[0] - 200 / 10) < 1e-6
    shares_approx = 20 / 10
    book_value_per_share = 100 / shares_approx
    assert abs(result[result["metric_norm"] == "pb"]["value"].iloc[0] - 200 / book_value_per_share) < 1e-6
    assert abs(result[result["metric_norm"] == "market_cap"]["value"].iloc[0] - 200 * shares_approx) < 1e-6

def test_derive_ratios_revenue_cagr_3y():
    raw = _raw_fixture()  # sales grows 10%/yr for 3 years in the fixture
    prices = pd.DataFrame({"symbol": ["A"], "date": [pd.Timestamp("2026-01-01")], "close": [200.0]})
    result = derive_ratios(raw, prices, as_of_date="2026-01-01")
    cagr = result[result["metric_norm"] == "revenue_cagr_3y"]
    assert len(cagr) == 0  # fixture only has 3 fiscal years (2023-25) -> can't compute a 3yr CAGR needing 4 points; not fabricated

def test_derive_ratios_skips_negative_denominators_gracefully():
    raw = _raw_fixture()
    raw.loc[(raw["metric_norm"] == "equity capital") & (raw["fiscal_year"] == 2025), "value"] = -500
    raw.loc[(raw["metric_norm"] == "reserves") & (raw["fiscal_year"] == 2025), "value"] = 0
    prices = pd.DataFrame({"symbol": ["A"], "date": [pd.Timestamp("2026-01-01")], "close": [200.0]})
    result = derive_ratios(raw, prices, as_of_date="2026-01-01")  # must not raise
    roe_2025 = result[(result["metric_norm"] == "roe") & (result["fiscal_year"] == 2025)]
    assert len(roe_2025) == 0 or roe_2025["value"].notna().all()  # negative equity -> excluded, not a fabricated negative-of-negative ROE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_derived_ratios.py -v`
Expected: FAIL with "cannot import name 'derive_ratios'"

- [ ] **Step 3: Write minimal implementation**

```python
# lib/derived_ratios.py
import pandas as pd
import numpy as np

RAW_METRICS = ["sales", "net profit", "operating profit", "opm %", "interest", "eps in rs",
               "equity capital", "reserves", "borrowings", "borrowing", "total assets",
               "cash from operating activity", "free cash flow"]


def _pivot_wide(raw_fundamentals: pd.DataFrame) -> pd.DataFrame:
    wide = raw_fundamentals.pivot_table(index=["symbol", "fiscal_year", "available_date"],
                                          columns="metric_norm", values="value", aggfunc="last").reset_index()
    for col in RAW_METRICS:
        if col not in wide.columns:
            wide[col] = np.nan
    wide["total_borrowings"] = wide["borrowings"].fillna(wide["borrowing"])
    wide["equity"] = wide["equity capital"] + wide["reserves"]
    wide.loc[wide["equity"] <= 0, "equity"] = np.nan  # negative/zero equity breaks every ratio below -- exclude, don't fabricate
    return wide


def _long(base: pd.DataFrame, metric_name: str, value) -> pd.DataFrame:
    out = base[["symbol", "fiscal_year", "available_date"]].copy()
    out["metric_norm"] = metric_name
    out["value"] = pd.Series(value).values
    return out[out["value"].notna() & np.isfinite(out["value"])]


def derive_ratios(raw_fundamentals: pd.DataFrame, prices: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    wide = _pivot_wide(raw_fundamentals)
    capital_employed = wide["equity"] + wide["total_borrowings"]
    capital_employed = capital_employed.where(capital_employed > 0)

    pieces = [
        _long(wide, "roe", wide["net profit"] / wide["equity"]),
        _long(wide, "roce", wide["operating profit"] / capital_employed),
        _long(wide, "debt_equity", wide["total_borrowings"] / wide["equity"]),
        _long(wide, "interest_coverage", wide["operating profit"] / wide["interest"].replace(0, np.nan)),
        _long(wide, "accruals_ratio", (wide["net profit"] - wide["cash from operating activity"]) / wide["total assets"].replace(0, np.nan)),
        _long(wide, "fcf", wide["free cash flow"]),
    ]

    wide_sorted = wide.sort_values(["symbol", "fiscal_year"])
    margin_std = wide_sorted.groupby("symbol")["opm %"].transform(lambda s: s.rolling(5, min_periods=3).std())
    pieces.append(_long(wide_sorted, "margin_stability", -margin_std))  # negate: lower volatility -> higher score

    for years, name in [(3, "revenue_cagr_3y"), (5, "revenue_cagr_5y")]:
        pieces.append(_revenue_cagr(wide, years, name))

    pieces.append(_valuation_ratios(wide, prices))
    return pd.concat(pieces, ignore_index=True)


def _revenue_cagr(wide: pd.DataFrame, years: int, metric_name: str) -> pd.DataFrame:
    def cagr(g):
        g = g.sort_values("fiscal_year")
        rev = g["sales"]
        if rev.notna().sum() < years + 1:
            return np.nan
        recent, past = rev.iloc[-1], rev.iloc[-(years + 1)]
        if pd.isna(recent) or pd.isna(past) or past <= 0:
            return np.nan
        return ((recent / past) ** (1 / years) - 1) * 100

    cagr_vals = wide.groupby("symbol").apply(cagr).rename("value").reset_index()
    latest_meta = wide.sort_values("fiscal_year").groupby("symbol").tail(1)[["symbol", "fiscal_year", "available_date"]]
    result = cagr_vals.merge(latest_meta, on="symbol", how="left")
    result["metric_norm"] = metric_name
    return result[result["value"].notna()]


def _valuation_ratios(wide: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """P/E, P/B, market_cap -- none directly reported. Shares outstanding is APPROXIMATED
    as net profit / EPS (no shares-outstanding field exists in the raw data) -- an
    [INFERENCE], not a [DATA] figure; downstream consumers should treat accordingly."""
    latest = wide.sort_values("fiscal_year").groupby("symbol").tail(1).copy()
    latest["shares_out_approx"] = latest["net profit"] / latest["eps in rs"].replace(0, np.nan)
    latest.loc[latest["shares_out_approx"] <= 0, "shares_out_approx"] = np.nan
    latest["book_value_per_share"] = latest["equity"] / latest["shares_out_approx"]

    latest_price = prices.sort_values("date").groupby("symbol")["close"].last().rename("current_price").reset_index()
    latest = latest.merge(latest_price, on="symbol", how="left")

    pe = _long(latest, "pe", latest["current_price"] / latest["eps in rs"].replace(0, np.nan))
    pb = _long(latest, "pb", latest["current_price"] / latest["book_value_per_share"])
    mcap = _long(latest, "market_cap", latest["current_price"] * latest["shares_out_approx"])
    return pd.concat([pe, pb, mcap], ignore_index=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_derived_ratios.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/derived_ratios.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_derived_ratios.py"
git commit -m "feat(scorecard): derive ROE/ROCE/PE/PB/market_cap/etc from raw Screener line items"
```

---

### Task 6: Fundamental pillars, part A — Quality + Growth

**Files:**
- Create: `lib/pillars_fundamental.py` (Value/DCF added in Task 7, same file)
- Test: `tests/test_pillars_fundamental.py`

**Interfaces:**
- Consumes: **derived** ratios shape from Task 5 [symbol, fiscal_year, available_date, metric_norm, value] with metric_norm in {roe, roce, ...}; `percentile_rank`, `coverage_aware_average` (Task 2); `tag_cyclicality` (Task 3)
- Produces: `compute_quality_score(derived_ratios: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame` [symbol, quality_sector_percentile, quality_universe_percentile, quality_coverage_pct]; `compute_growth_score(derived_ratios: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame` [symbol, growth_score, growth_coverage_pct, growth_divergence_flag]

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pillars_fundamental.py
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from pillars_fundamental import compute_quality_score, compute_growth_score

def _quality_fixture():
    rows = []
    for sym, sector, roe, roce in [("A", "Information Technology", 30, 28), ("B", "Information Technology", 10, 12),
                                     ("C", "Construction Materials", 15, 14), ("D", "Construction Materials", 5, 6)]:
        rows += [
            {"symbol": sym, "metric_norm": "roe", "value": roe, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
            {"symbol": sym, "metric_norm": "roce", "value": roce, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        ]
    return pd.DataFrame(rows)

def test_quality_is_sector_neutral():
    f = _quality_fixture()
    universe = pd.DataFrame({"symbol": ["A", "B", "C", "D"],
                              "sector": ["Information Technology", "Information Technology",
                                         "Construction Materials", "Construction Materials"]})
    result = compute_quality_score(f, universe, as_of_date="2026-01-01")
    c_row = result[result["symbol"] == "C"].iloc[0]
    b_row = result[result["symbol"] == "B"].iloc[0]
    assert c_row["quality_sector_percentile"] > b_row["quality_sector_percentile"]
    assert c_row["quality_universe_percentile"] < c_row["quality_sector_percentile"]

def test_quality_uses_multiyear_average_for_cyclical_sectors():
    rows = []
    for y in range(2018, 2026):
        rows.append({"symbol": "A", "metric_norm": "roe", "value": 20 if y == 2025 else 30,
                     "fiscal_year": y, "available_date": pd.Timestamp(f"{y}-06-01")})
        rows.append({"symbol": "B", "metric_norm": "roe", "value": 20 if y == 2025 else 10,
                     "fiscal_year": y, "available_date": pd.Timestamp(f"{y}-06-01")})
    f = pd.DataFrame(rows)
    universe = pd.DataFrame({"symbol": ["A", "B"], "sector": ["Metals & Mining", "Metals & Mining"]})
    result = compute_quality_score(f, universe, as_of_date="2026-01-01")
    a_score = result[result["symbol"] == "A"].iloc[0]["quality_sector_percentile"]
    b_score = result[result["symbol"] == "B"].iloc[0]["quality_sector_percentile"]
    assert a_score > b_score

def test_growth_score_uses_3yr_not_5yr():
    f = pd.DataFrame([
        {"symbol": "A", "metric_norm": "revenue_cagr_3y", "value": 20, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        {"symbol": "A", "metric_norm": "revenue_cagr_5y", "value": 5, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        {"symbol": "B", "metric_norm": "revenue_cagr_3y", "value": 8, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        {"symbol": "B", "metric_norm": "revenue_cagr_5y", "value": 8, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
    ])
    universe = pd.DataFrame({"symbol": ["A", "B"], "sector": ["Information Technology", "Information Technology"]})
    result = compute_growth_score(f, universe, as_of_date="2026-01-01")
    a_row = result[result["symbol"] == "A"].iloc[0]
    assert a_row["growth_divergence_flag"] == True
    b_row = result[result["symbol"] == "B"].iloc[0]
    assert b_row["growth_divergence_flag"] == False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_pillars_fundamental.py -v`
Expected: FAIL with "cannot import name 'compute_quality_score'"

- [ ] **Step 3: Write minimal implementation**

```python
# lib/pillars_fundamental.py
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rank_utils import percentile_rank, coverage_aware_average
from cyclicality_map import tag_cyclicality

QUALITY_METRICS = ["roe", "roce", "accruals_ratio", "margin_stability"]
CYCLICAL_LOOKBACK_YEARS = 8
STANDARD_LOOKBACK_YEARS = 4


def compute_quality_score(derived_ratios: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    universe = universe.copy()
    universe["cyclicality_tag"] = tag_cyclicality(universe)

    df = derived_ratios[derived_ratios["metric_norm"].isin(QUALITY_METRICS)].copy()
    df = df.merge(universe[["symbol", "cyclicality_tag"]], on="symbol", how="left")
    max_year = df["fiscal_year"].max()
    lookback_years = df["cyclicality_tag"].map({"Cyclical": CYCLICAL_LOOKBACK_YEARS}).fillna(STANDARD_LOOKBACK_YEARS)
    df = df[df["fiscal_year"] > (max_year - lookback_years)]

    avg = df.groupby(["symbol", "metric_norm"])["value"].mean().reset_index()
    wide = avg.pivot(index="symbol", columns="metric_norm", values="value").reset_index()
    wide = wide.merge(universe[["symbol", "sector"]], on="symbol", how="left")

    per_metric_sector = pd.DataFrame({"symbol": wide["symbol"]})
    per_metric_universe = pd.DataFrame({"symbol": wide["symbol"]})
    for m in QUALITY_METRICS:
        if m in wide.columns:
            per_metric_sector[m] = percentile_rank(wide, m, group_col="sector")
            per_metric_universe[m] = percentile_rank(wide, m)

    sector_cols = [c for c in QUALITY_METRICS if c in per_metric_sector.columns]
    sector_avg = coverage_aware_average(per_metric_sector, sector_cols)
    universe_avg = coverage_aware_average(per_metric_universe, sector_cols)

    return pd.DataFrame({
        "symbol": wide["symbol"],
        "quality_sector_percentile": sector_avg["pillar_score"],
        "quality_universe_percentile": universe_avg["pillar_score"],
        "quality_coverage_pct": sector_avg["coverage_pct"],
    })


def compute_growth_score(derived_ratios: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    df = derived_ratios[derived_ratios["metric_norm"].isin(["revenue_cagr_3y", "revenue_cagr_5y"])]
    latest = df.sort_values("fiscal_year").groupby(["symbol", "metric_norm"]).tail(1)
    wide = latest.pivot(index="symbol", columns="metric_norm", values="value").reset_index()
    wide = wide.merge(universe[["symbol", "sector"]], on="symbol", how="left")

    wide["growth_score"] = percentile_rank(wide, "revenue_cagr_3y")
    wide["growth_divergence_flag"] = (wide["revenue_cagr_3y"] - wide["revenue_cagr_5y"]).abs() > 10
    wide["growth_coverage_pct"] = wide["revenue_cagr_3y"].notna().astype(float) * 100
    return wide[["symbol", "growth_score", "growth_coverage_pct", "growth_divergence_flag"]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_pillars_fundamental.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/pillars_fundamental.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_pillars_fundamental.py"
git commit -m "feat(scorecard): Quality (sector-neutral, cyclicality-aware) + Growth (3yr-primary) pillars"
```

---

### Task 7: Fundamental pillars, part B — Value-Relative + DCF

**Files:**
- Modify: `lib/pillars_fundamental.py` (append)
- Modify: `tests/test_pillars_fundamental.py` (append)

**Interfaces:**
- Consumes: derived ratios shape (Task 5); `percentile_rank` (Task 2)
- Produces: `compute_value_relative_score(derived_ratios, universe, as_of_date) -> pd.DataFrame` [symbol, value_relative_score, value_coverage_pct]; `compute_dcf_score(derived_ratios, risk_free_rate, erp_assumption, terminal_growth_assumption, universe, as_of_date) -> pd.DataFrame` [symbol, dcf_upside_pct, dcf_score, dcf_discount_rate_used, dcf_terminal_growth_assumed, dcf_fcf_years_used, dcf_coverage_flag]

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_pillars_fundamental.py
from pillars_fundamental import compute_value_relative_score, compute_dcf_score

def test_value_relative_rewards_cheap_vs_own_history_and_sector():
    f = pd.DataFrame([
        {"symbol": "A", "metric_norm": "pe", "value": 30, "fiscal_year": 2023, "available_date": pd.Timestamp("2023-06-01")},
        {"symbol": "A", "metric_norm": "pe", "value": 35, "fiscal_year": 2024, "available_date": pd.Timestamp("2024-06-01")},
        {"symbol": "A", "metric_norm": "pe", "value": 8, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        {"symbol": "B", "metric_norm": "pe", "value": 30, "fiscal_year": 2023, "available_date": pd.Timestamp("2023-06-01")},
        {"symbol": "B", "metric_norm": "pe", "value": 30, "fiscal_year": 2024, "available_date": pd.Timestamp("2024-06-01")},
        {"symbol": "B", "metric_norm": "pe", "value": 30, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        {"symbol": "A", "metric_norm": "pb", "value": 5, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        {"symbol": "B", "metric_norm": "pb", "value": 5, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
    ])
    universe = pd.DataFrame({"symbol": ["A", "B"], "sector": ["Information Technology", "Information Technology"]})
    result = compute_value_relative_score(f, universe, as_of_date="2026-01-01")
    a = result[result["symbol"] == "A"].iloc[0]["value_relative_score"]
    b = result[result["symbol"] == "B"].iloc[0]["value_relative_score"]
    assert a > b

def test_dcf_requires_consistent_sign_fcf_and_beta_price_presence():
    # A: 5yr consistently POSITIVE FCF, has beta/price -> eligible
    # B: 5yr FCF but flips sign (turnaround story) -> NOT eligible despite meeting the year-count bar
    # C: 5yr consistently positive FCF but NO price -> NOT eligible (can't compute upside at all)
    f = pd.DataFrame(
        [{"symbol": "A", "metric_norm": "fcf", "value": 100, "fiscal_year": y, "available_date": pd.Timestamp(f"{y}-06-01")} for y in range(2021, 2026)]
        + [{"symbol": "B", "metric_norm": "fcf", "value": v, "fiscal_year": y, "available_date": pd.Timestamp(f"{y}-06-01")}
           for y, v in zip(range(2021, 2026), [-50, -30, -10, 20, 50])]
        + [{"symbol": "C", "metric_norm": "fcf", "value": 100, "fiscal_year": y, "available_date": pd.Timestamp(f"{y}-06-01")} for y in range(2021, 2026)]
        + [{"symbol": s, "metric_norm": "market_cap", "value": 1000, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")} for s in ["A", "B"]]
        # C deliberately has no market_cap/price-derived signal
    )
    universe = pd.DataFrame({"symbol": ["A", "B", "C"], "sector": ["Information Technology"] * 3})
    result = compute_dcf_score(f, risk_free_rate=0.07, erp_assumption=0.065,
                                 terminal_growth_assumption=0.06, universe=universe, as_of_date="2026-01-01")
    assert result[result["symbol"] == "A"].iloc[0]["dcf_coverage_flag"] == "High"
    assert result[result["symbol"] == "B"].iloc[0]["dcf_coverage_flag"] == "N/A"  # sign-inconsistent FCF
    assert result[result["symbol"] == "C"].iloc[0]["dcf_coverage_flag"] == "N/A"  # no price signal available
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_pillars_fundamental.py -v`
Expected: FAIL with "cannot import name 'compute_value_relative_score'"

- [ ] **Step 3: Write minimal implementation**

```python
# append to lib/pillars_fundamental.py

def compute_value_relative_score(derived_ratios: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    universe = universe[["symbol", "sector"]]
    pe = derived_ratios[derived_ratios["metric_norm"] == "pe"].sort_values("fiscal_year")

    own_hist_raw = pe.groupby("symbol").apply(
        lambda g: (g["value"] < g["value"].iloc[-1]).mean() * 100 if len(g) > 1 else np.nan
    ).rename("pe_vs_own_history_raw").reset_index()
    own_hist_raw["pe_vs_own_history"] = 100 - own_hist_raw["pe_vs_own_history_raw"]

    pe_latest = pe.groupby("symbol").tail(1).merge(universe, on="symbol", how="left")
    pe_latest["pe_vs_sector"] = percentile_rank(pe_latest, "value", group_col="sector", ascending=False)

    pb = derived_ratios[derived_ratios["metric_norm"] == "pb"].sort_values("fiscal_year")
    pb_latest = pb.groupby("symbol").tail(1).merge(universe, on="symbol", how="left")
    pb_latest["pb_vs_sector"] = percentile_rank(pb_latest, "value", group_col="sector", ascending=False) if len(pb_latest) else pd.Series(dtype=float)

    merged = universe[["symbol"]].copy()
    merged = merged.merge(own_hist_raw[["symbol", "pe_vs_own_history"]], on="symbol", how="left")
    merged = merged.merge(pe_latest[["symbol", "pe_vs_sector"]], on="symbol", how="left")
    merged = merged.merge(pb_latest[["symbol", "pb_vs_sector"]], on="symbol", how="left")

    score_cols = ["pe_vs_own_history", "pe_vs_sector", "pb_vs_sector"]
    avg = coverage_aware_average(merged, score_cols)
    merged["value_relative_score"] = avg["pillar_score"]
    merged["value_coverage_pct"] = avg["coverage_pct"]
    return merged[["symbol", "value_relative_score", "value_coverage_pct"]]


MIN_FCF_YEARS_FOR_DCF = 5


def compute_dcf_score(derived_ratios: pd.DataFrame, risk_free_rate: float, erp_assumption: float,
                       terminal_growth_assumption: float, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    fcf = derived_ratios[derived_ratios["metric_norm"] == "fcf"].sort_values("fiscal_year")
    fcf_years = fcf.groupby("symbol")["fiscal_year"].nunique().rename("dcf_fcf_years_used")
    avg_fcf = fcf.groupby("symbol")["value"].mean().rename("avg_fcf")
    sign_consistent = fcf.groupby("symbol")["value"].apply(lambda s: (s > 0).all() or (s < 0).all()).rename("sign_consistent")

    mcap = derived_ratios[derived_ratios["metric_norm"] == "market_cap"].sort_values("fiscal_year")
    price_signal = mcap.groupby("symbol")["value"].last().rename("market_cap_signal")  # presence = a price was successfully joined upstream (Task 5)

    merged = pd.concat([fcf_years, avg_fcf, sign_consistent, price_signal], axis=1).reset_index().rename(columns={"index": "symbol"})
    merged = merged.merge(universe[["symbol", "sector"]], on="symbol", how="left")

    eligible = (merged["dcf_fcf_years_used"].fillna(0) >= MIN_FCF_YEARS_FOR_DCF) & \
               merged["sign_consistent"].fillna(False) & merged["avg_fcf"].gt(0) & merged["market_cap_signal"].notna()

    merged["dcf_discount_rate_used"] = risk_free_rate + erp_assumption  # beta not derivable from current fundamentals source (MASTER_PLAN.md addendum) -- flat CAPM proxy until wired
    merged["dcf_terminal_growth_assumed"] = terminal_growth_assumption

    g = merged["avg_fcf"].clip(lower=1).pct_change().fillna(0.10).clip(-0.30, 0.30)
    r = merged["dcf_discount_rate_used"]
    explicit_pv = sum(merged["avg_fcf"].clip(lower=0) * (1 + g) ** t / (1 + r) ** t for t in range(1, 6))
    terminal_fcf = merged["avg_fcf"].clip(lower=0) * (1 + g) ** 5 * (1 + terminal_growth_assumption)
    terminal_value = terminal_fcf / (r - terminal_growth_assumption).replace(0, np.nan)
    intrinsic_value = explicit_pv + terminal_value / (1 + r) ** 5

    merged["dcf_upside_pct"] = np.nan
    merged["dcf_score"] = np.nan
    merged.loc[eligible, "dcf_upside_pct"] = intrinsic_value[eligible] / merged.loc[eligible, "market_cap_signal"] * 100 - 100
    merged.loc[eligible, "dcf_score"] = percentile_rank(merged[eligible], "dcf_upside_pct", group_col="sector") if eligible.any() else np.nan
    merged["dcf_coverage_flag"] = np.where(eligible, "High", "N/A")
    return merged[["symbol", "dcf_upside_pct", "dcf_score", "dcf_discount_rate_used",
                   "dcf_terminal_growth_assumed", "dcf_fcf_years_used", "dcf_coverage_flag"]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_pillars_fundamental.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/pillars_fundamental.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_pillars_fundamental.py"
git commit -m "feat(scorecard): Value-Relative + DCF (sign-consistency + price-presence eligibility gate)"
```

---

### Task 8: Technical pillars — Stage/Technical + Accumulation (split-adjusted prices)

**Files:**
- Create: `lib/pillars_technical.py`
- Test: `tests/test_pillars_technical.py`

**Interfaces:**
- Consumes: `percentile_rank` (Task 2); prices shape [symbol, date, close, adj_close, volume] (Task 1) — **return-based calcs use `adj_close`**, not `close`
- Produces: `compute_stage_technical_score(prices, universe, as_of_date) -> pd.DataFrame` [symbol, stage_score, stage_timing_tag]; `compute_accumulation_score(prices, universe, as_of_date) -> pd.DataFrame` [symbol, accumulation_score]

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pillars_technical.py
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from pillars_technical import compute_stage_technical_score, compute_accumulation_score

def _uptrend_prices(sym, start_price, drift, n=300):
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    closes = start_price + np.arange(n) * drift
    return pd.DataFrame({"symbol": sym, "date": dates, "close": closes, "adj_close": closes,
                          "volume": 100000})

def test_stage_score_uses_adj_close_not_raw_close():
    # A split 2:1 on day 200 (raw close halves overnight, adj_close is continuous) --
    # a naive raw-close return calc would show a fake ~-50% return; adj_close shows the truth.
    dates = pd.date_range("2025-01-01", periods=300, freq="B")
    adj_close = 100 + np.arange(300) * 0.3  # smooth uptrend, the TRUE economic return
    raw_close = adj_close.copy()
    raw_close[200:] = raw_close[200:] / 2  # split artifact only in raw close
    split_stock = pd.DataFrame({"symbol": "A", "date": dates, "close": raw_close, "adj_close": adj_close, "volume": 100000})
    flat_stock = _uptrend_prices("B", 100, 0.01)
    prices = pd.concat([split_stock, flat_stock], ignore_index=True)
    universe = pd.DataFrame({"symbol": ["A", "B"], "sector": ["IT", "IT"]})
    result = compute_stage_technical_score(prices, universe, as_of_date="2026-01-01")
    a = result[result["symbol"] == "A"].iloc[0]["stage_score"]
    b = result[result["symbol"] == "B"].iloc[0]["stage_score"]
    assert a > b  # A's true (adj_close) trend is much stronger than B's -- would fail if raw close were used

def test_accumulation_score_favors_rising_obv():
    rising_vol = _uptrend_prices("A", 100, 0.3)
    rising_vol["volume"] = np.arange(len(rising_vol)) * 1000 + 50000
    flat = _uptrend_prices("B", 100, 0.3)
    prices = pd.concat([rising_vol, flat], ignore_index=True)
    universe = pd.DataFrame({"symbol": ["A", "B"], "sector": ["IT", "IT"]})
    result = compute_accumulation_score(prices, universe, as_of_date="2026-01-01")
    a = result[result["symbol"] == "A"].iloc[0]["accumulation_score"]
    b = result[result["symbol"] == "B"].iloc[0]["accumulation_score"]
    assert a > b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_pillars_technical.py -v`
Expected: FAIL with "cannot import name 'compute_stage_technical_score'"

- [ ] **Step 3: Write minimal implementation**

```python
# lib/pillars_technical.py
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rank_utils import percentile_rank


def compute_stage_technical_score(prices: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    rows = []
    for sym, g in prices.sort_values("date").groupby("symbol"):
        g = g.reset_index(drop=True)
        adj = g["adj_close"]  # split/dividend-adjusted -- NEVER raw close for return calcs
        ma200 = adj.rolling(200, min_periods=150).mean().iloc[-1]
        last_adj = adj.iloc[-1]
        ret_12m = adj.iloc[-1] / adj.iloc[max(0, len(adj) - 252)] - 1 if len(adj) > 20 else np.nan
        ret_24m = adj.iloc[-1] / adj.iloc[0] - 1 if len(adj) > 20 else np.nan
        rsi14 = _rsi(adj, 14)
        rows.append({"symbol": sym, "above_200ma": last_adj > ma200 if pd.notna(ma200) else False,
                      "ret_12m": ret_12m, "ret_24m": ret_24m, "rsi14": rsi14})
    df = pd.DataFrame(rows).merge(universe[["symbol", "sector"]], on="symbol", how="left")

    ret_12m_rank = percentile_rank(df, "ret_12m")
    ret_24m_rank = percentile_rank(df, "ret_24m")
    rs_vs_sector_rank = percentile_rank(df, "ret_12m", group_col="sector")
    trend_component = (ret_12m_rank + ret_24m_rank + rs_vs_sector_rank) / 3
    df["stage_score"] = np.where(df["above_200ma"], trend_component, trend_component * 0.5)

    df["stage_timing_tag"] = df["rsi14"].apply(
        lambda r: "Extended" if pd.notna(r) and r > 70 else ("Pulled back" if pd.notna(r) and r < 35 else "Neutral")
    )
    return df[["symbol", "stage_score", "stage_timing_tag"]]


def compute_accumulation_score(prices: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    rows = []
    for sym, g in prices.sort_values("date").groupby("symbol"):
        g = g.reset_index(drop=True)
        direction = np.sign(g["adj_close"].diff().fillna(0))  # adjusted, for the same split-safety reason
        obv = (direction * g["volume"]).cumsum()
        window = min(126, len(obv) - 1) if len(obv) > 1 else 1
        obv_slope = (obv.iloc[-1] - obv.iloc[-window]) if len(obv) > window else np.nan
        rows.append({"symbol": sym, "obv_slope": obv_slope})
    df = pd.DataFrame(rows).merge(universe[["symbol", "sector"]], on="symbol", how="left")
    df["accumulation_score"] = percentile_rank(df, "obv_slope")
    return df[["symbol", "accumulation_score"]]


def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if len(rsi) else np.nan
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_pillars_technical.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/pillars_technical.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_pillars_technical.py"
git commit -m "feat(scorecard): Stage/Technical + Accumulation pillars using split-adjusted close"
```

---

### Task 9: Flow pillars — Ownership/Smart-Money Flow (PIT + pre-computed QoQ) + Sector&Macro

**Files:**
- Create: `lib/pillars_flow.py`
- Test: `tests/test_pillars_flow.py`

**Interfaces:**
- Consumes: `percentile_rank` (Task 2); `tag_cyclicality` (Task 3); ownership shape [symbol, quarter_end, available_date, FIIs_qoq, DIIs_qoq, ...] (Task 1, already PIT-filtered by `load_ownership`); prices shape (Task 1)
- Produces: `compute_ownership_flow_score(ownership: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame` [symbol, ownership_flow_score]; `compute_sector_macro_score(prices: pd.DataFrame, universe: pd.DataFrame, regime: str, as_of_date: str) -> pd.DataFrame` [symbol, sector_macro_score]

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pillars_flow.py
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from pillars_flow import compute_ownership_flow_score, compute_sector_macro_score

def test_ownership_flow_favors_sustained_accumulation():
    quarters = pd.period_range("2024Q1", periods=8, freq="Q")
    rising = pd.DataFrame({"symbol": "A", "quarter_end": quarters.to_timestamp(),
                            "available_date": quarters.to_timestamp() + pd.Timedelta(days=25),
                            "FIIs_qoq": np.linspace(0.5, 2.0, 8), "DIIs_qoq": 0.1})
    flat = pd.DataFrame({"symbol": "B", "quarter_end": quarters.to_timestamp(),
                          "available_date": quarters.to_timestamp() + pd.Timedelta(days=25),
                          "FIIs_qoq": 0.0, "DIIs_qoq": 0.0})
    ownership = pd.concat([rising, flat], ignore_index=True)
    universe = pd.DataFrame({"symbol": ["A", "B"], "sector": ["IT", "IT"]})
    result = compute_ownership_flow_score(ownership, universe, as_of_date="2026-01-01")
    a = result[result["symbol"] == "A"].iloc[0]["ownership_flow_score"]
    b = result[result["symbol"] == "B"].iloc[0]["ownership_flow_score"]
    assert a > b

def test_sector_macro_applies_regime_cyclicality_fit():
    dates = pd.date_range("2025-01-01", periods=260, freq="B")
    cyclical = pd.DataFrame({"symbol": "A", "date": dates, "close": 100 + np.arange(260) * 0.2})
    defensive = pd.DataFrame({"symbol": "B", "date": dates, "close": 100 + np.arange(260) * 0.2})
    prices = pd.concat([cyclical, defensive], ignore_index=True)
    universe = pd.DataFrame({"symbol": ["A", "B"], "sector": ["Metals & Mining", "Fast Moving Consumer Goods"]})
    rich = compute_sector_macro_score(prices, universe, regime="Rich", as_of_date="2026-01-01")
    a_rich = rich[rich["symbol"] == "A"].iloc[0]["sector_macro_score"]
    b_rich = rich[rich["symbol"] == "B"].iloc[0]["sector_macro_score"]
    assert b_rich > a_rich
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_pillars_flow.py -v`
Expected: FAIL with "cannot import name 'compute_ownership_flow_score'"

- [ ] **Step 3: Write minimal implementation**

```python
# lib/pillars_flow.py
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rank_utils import percentile_rank
from cyclicality_map import tag_cyclicality

REGIME_CYCLICALITY_FIT = {
    ("Cyclical", "Rich"): -10, ("Cyclical", "Cheap"): +10, ("Cyclical", "Neutral"): 0,
    ("Defensive-Stable", "Rich"): +10, ("Defensive-Stable", "Cheap"): -10, ("Defensive-Stable", "Neutral"): 0,
    ("Sensitive-hybrid", "Rich"): 0, ("Sensitive-hybrid", "Cheap"): 0, ("Sensitive-hybrid", "Neutral"): 0,
}


def compute_ownership_flow_score(ownership: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    # ownership arrives already PIT-filtered (Task 1's load_ownership) and already carries
    # pre-computed FIIs_qoq/DIIs_qoq -- use those directly instead of re-deriving a diff.
    df = ownership.sort_values("quarter_end")
    trend = df.groupby("symbol").apply(
        lambda g: (g["FIIs_qoq"].fillna(0) + g["DIIs_qoq"].fillna(0)).tail(6).mean()
    ).rename("flow_trend").reset_index()
    trend = trend.merge(universe[["symbol", "sector"]], on="symbol", how="left")
    trend["ownership_flow_score"] = percentile_rank(trend, "flow_trend")
    return trend[["symbol", "ownership_flow_score"]]


def compute_sector_macro_score(prices: pd.DataFrame, universe: pd.DataFrame, regime: str, as_of_date: str) -> pd.DataFrame:
    universe = universe.copy()
    universe["cyclicality_tag"] = tag_cyclicality(universe)
    df = prices.merge(universe[["symbol", "sector"]], on="symbol", how="left").sort_values("date")
    window = 126
    close_col = "adj_close" if "adj_close" in df.columns else "close"
    ret = df.groupby("symbol")[close_col].apply(
        lambda s: s.iloc[-1] / s.iloc[-window] - 1 if len(s) > window else np.nan
    ).rename("ret_6m").reset_index()
    ret = ret.merge(universe[["symbol", "sector", "cyclicality_tag"]], on="symbol", how="left")
    sector_avg_ret = ret.groupby("sector")["ret_6m"].transform("mean")
    momentum_rank = percentile_rank(ret.assign(sector_ret=sector_avg_ret), "sector_ret")

    fit_adjustment = ret["cyclicality_tag"].apply(lambda tag: REGIME_CYCLICALITY_FIT.get((tag, regime), 0))
    ret["sector_macro_score"] = (momentum_rank + fit_adjustment).clip(0, 100)
    return ret[["symbol", "sector_macro_score"]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_pillars_flow.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/pillars_flow.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_pillars_flow.py"
git commit -m "feat(scorecard): Ownership Flow (PIT + pre-computed QoQ) + Sector&Macro pillars"
```

---

### Task 10: Overlay gates — Balance-Sheet Safety (pledge-unavailable) + Liquidity (median turnover, size-relative)

**Files:**
- Create: `lib/overlay_gates.py`
- Test: `tests/test_overlay_gates.py`

**Interfaces:**
- Consumes: `market_cap_tercile` (Task 3); derived ratios shape (Task 5); prices shape (Task 1)
- Produces: `compute_balance_sheet_flag(derived_ratios: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame` [symbol, bs_flag]; `compute_liquidity_flag(prices: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame` [symbol, liquidity_flag, is_illiquid]; `apply_overlay_gates(composite, bs_flags, liquidity_flags) -> pd.DataFrame` [...composite, final_score]

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_overlay_gates.py
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from overlay_gates import compute_balance_sheet_flag, compute_liquidity_flag, apply_overlay_gates

def test_balance_sheet_flag_uses_only_debt_equity_and_interest_coverage():
    # promoter_pledge_pct is NOT derivable from the current fundamentals source
    # (MASTER_PLAN.md addendum) -- the gate must work off D/E + Interest Coverage alone.
    f = pd.DataFrame([
        {"symbol": "A", "metric_norm": "debt_equity", "value": 0.3, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        {"symbol": "A", "metric_norm": "interest_coverage", "value": 8, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        {"symbol": "B", "metric_norm": "debt_equity", "value": 4.5, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
        {"symbol": "B", "metric_norm": "interest_coverage", "value": 0.8, "fiscal_year": 2025, "available_date": pd.Timestamp("2025-06-01")},
    ])
    universe = pd.DataFrame({"symbol": ["A", "B"], "sector": ["IT", "IT"]})
    flags = compute_balance_sheet_flag(f, universe, as_of_date="2026-01-01")
    assert flags[flags["symbol"] == "A"].iloc[0]["bs_flag"] == "GREEN"
    assert flags[flags["symbol"] == "B"].iloc[0]["bs_flag"] == "RED"

def test_liquidity_uses_median_turnover_robust_to_single_day_spike():
    dates = pd.date_range("2025-01-01", periods=60, freq="B")
    # 59 days of near-zero turnover + 1 spike day -- mean would be misleadingly high, median won't be
    volumes = [1000] * 59 + [50_000_000]
    prices = pd.DataFrame({"symbol": "A", "date": dates, "close": 100, "volume": volumes})
    universe = pd.DataFrame({"symbol": ["A"], "sector": ["IT"], "market_cap": [500000]})
    result = compute_liquidity_flag(prices, universe, as_of_date="2026-01-01")
    assert result.iloc[0]["liquidity_flag"] == "RED"  # median turnover is still near-zero despite the spike

def test_apply_overlay_gates_caps_red_at_40():
    composite = pd.DataFrame({"symbol": ["A", "B"], "composite_raw": [90.0, 90.0]})
    bs_flags = pd.DataFrame({"symbol": ["A", "B"], "bs_flag": ["GREEN", "RED"]})
    liq_flags = pd.DataFrame({"symbol": ["A", "B"], "liquidity_flag": ["GREEN", "GREEN"], "is_illiquid": [False, False]})
    result = apply_overlay_gates(composite, bs_flags, liq_flags)
    assert result[result["symbol"] == "A"].iloc[0]["final_score"] == 90.0
    assert result[result["symbol"] == "B"].iloc[0]["final_score"] == 40.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_overlay_gates.py -v`
Expected: FAIL with "cannot import name 'compute_balance_sheet_flag'"

- [ ] **Step 3: Write minimal implementation**

```python
# lib/overlay_gates.py
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cyclicality_map import market_cap_tercile


def compute_balance_sheet_flag(derived_ratios: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    # promoter_pledge_pct is NOT available in the current fundamentals source (MASTER_PLAN.md
    # Open Risks) -- gate on D/E + Interest Coverage only until pledge data is sourced separately.
    metrics = ["debt_equity", "interest_coverage"]
    df = derived_ratios[derived_ratios["metric_norm"].isin(metrics)]
    latest = df.sort_values("fiscal_year").groupby(["symbol", "metric_norm"]).tail(1)
    wide = latest.pivot(index="symbol", columns="metric_norm", values="value").reset_index()

    def flag(row):
        red = row.get("debt_equity", 0) > 2.5 or row.get("interest_coverage", 99) < 1.5
        amber = row.get("debt_equity", 0) > 1.5 or row.get("interest_coverage", 99) < 3
        return "RED" if red else ("AMBER" if amber else "GREEN")

    wide["bs_flag"] = wide.apply(flag, axis=1)
    return wide[["symbol", "bs_flag"]]


def compute_liquidity_flag(prices: pd.DataFrame, universe: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    df = prices.copy()
    df["turnover"] = df["close"] * df["volume"]  # raw close x volume -- actual traded value, not adj_close
    # median, not mean -- robust to a single spike day (delisting event, data-entry error)
    med_turnover = df.groupby("symbol")["turnover"].apply(lambda s: s.tail(60).median()).rename("median_turnover_60d").reset_index()

    if "market_cap" in universe.columns:
        universe = universe.assign(mcap_tercile=market_cap_tercile(universe))
    else:
        universe = universe.assign(mcap_tercile="Mid")
    merged = med_turnover.merge(universe[["symbol", "mcap_tercile"]], on="symbol", how="left")
    thresholds = {"Large": 5_00_00_000, "Mid": 1_00_00_000, "Small": 25_00_000}
    merged["min_turnover"] = merged["mcap_tercile"].map(thresholds).fillna(thresholds["Small"])
    merged["is_illiquid"] = merged["median_turnover_60d"] < merged["min_turnover"]
    merged["liquidity_flag"] = np.where(merged["is_illiquid"], "RED", "GREEN")
    return merged[["symbol", "liquidity_flag", "is_illiquid"]]


def apply_overlay_gates(composite: pd.DataFrame, bs_flags: pd.DataFrame, liquidity_flags: pd.DataFrame) -> pd.DataFrame:
    df = composite.merge(bs_flags, on="symbol", how="left").merge(liquidity_flags, on="symbol", how="left")
    score = df["composite_raw"].copy()
    score = np.where(df["bs_flag"] == "RED", np.minimum(score, 40), np.where(df["bs_flag"] == "AMBER", score * 0.85, score))
    score = np.where(df["liquidity_flag"] == "RED", np.minimum(score, 40), score)
    df["final_score"] = score
    return df
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_overlay_gates.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/lib/overlay_gates.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_overlay_gates.py"
git commit -m "feat(scorecard): Balance-Sheet Safety (pledge-unavailable, 2-signal) + median-turnover Liquidity gates"
```

---

### Task 11: Orchestrator — build_scorecard.py (partial-failure isolation, atomic write, coverage-aware re-weighting)

**Files:**
- Create: `build_scorecard.py`
- Test: `tests/test_build_scorecard.py`

**Interfaces:**
- Consumes: every function from Tasks 1-10 (exact names above)
- Produces: `BASE_WEIGHTS: dict`; `assemble_composite(pillar_scores: pd.DataFrame, weights: dict) -> pd.DataFrame`; `main(as_of_date: str) -> pd.DataFrame`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_build_scorecard.py
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from build_scorecard import BASE_WEIGHTS, assemble_composite

def test_base_weights_sum_to_100():
    assert abs(sum(BASE_WEIGHTS.values()) - 100) < 1e-9

def test_assemble_composite_reweights_over_available_pillars_only():
    # Stock A has ALL 8 pillars. Stock B is missing 5 of 8 (e.g. zero price history) --
    # its composite must be re-weighted over the 3 it has, NOT computed as if the missing
    # 5 were zero (which would silently crater its score regardless of how good those 3 are).
    pillar_scores = pd.DataFrame({
        "symbol": ["A", "B"],
        "quality_sector_percentile": [80.0, 80.0], "growth_score": [80.0, 80.0],
        "value_relative_score": [80.0, 80.0], "dcf_score": [80.0, np.nan],
        "stage_score": [80.0, np.nan], "sector_macro_score": [80.0, np.nan],
        "ownership_flow_score": [80.0, np.nan], "accumulation_score": [80.0, np.nan],
    })
    result = assemble_composite(pillar_scores, BASE_WEIGHTS)
    a_score = result[result["symbol"] == "A"].iloc[0]["composite_raw"]
    b_score = result[result["symbol"] == "B"].iloc[0]["composite_raw"]
    assert abs(a_score - 80.0) < 1e-6  # uniform 80 across all 8 -> composite is 80 regardless of weights
    assert abs(b_score - 80.0) < 1e-6  # re-weighted over its 3 available pillars (also uniform 80) -> still 80, NOT dragged toward 0

def test_assemble_composite_all_nan_pillar_row_is_nan_not_zero():
    pillar_scores = pd.DataFrame({
        "symbol": ["Z"], "quality_sector_percentile": [np.nan], "growth_score": [np.nan],
        "value_relative_score": [np.nan], "dcf_score": [np.nan], "stage_score": [np.nan],
        "sector_macro_score": [np.nan], "ownership_flow_score": [np.nan], "accumulation_score": [np.nan],
    })
    result = assemble_composite(pillar_scores, BASE_WEIGHTS)
    assert pd.isna(result.iloc[0]["composite_raw"])  # not silently 0 -- a stock with zero data gets no fabricated score
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_build_scorecard.py -v`
Expected: FAIL with "cannot import name 'BASE_WEIGHTS'"

- [ ] **Step 3: Write minimal implementation**

```python
# build_scorecard.py
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

import numpy as np
import pandas as pd
from data_foundation import load_universe, load_fundamentals_pit, load_prices, load_ownership
from derived_ratios import derive_ratios
from cyclicality_map import tag_cyclicality, market_cap_tercile
from regime import classify_valuation_regime, apply_regime_tilt
from pillars_fundamental import compute_quality_score, compute_growth_score, compute_value_relative_score, compute_dcf_score
from pillars_technical import compute_stage_technical_score, compute_accumulation_score
from pillars_flow import compute_ownership_flow_score, compute_sector_macro_score
from overlay_gates import compute_balance_sheet_flag, compute_liquidity_flag, apply_overlay_gates

BASE_WEIGHTS = {
    "quality": 18, "growth": 18, "value_relative": 15, "dcf": 12,
    "stage": 12, "sector_macro": 10, "ownership_flow": 8, "accumulation": 7,
}

# [ASSUMPTION] labeled per epistemic-conduct rule -- revisit before trusting DCF output.
# beta is NOT derivable from the current fundamentals source (MASTER_PLAN.md addendum), so
# the discount rate is currently risk_free_rate + erp_assumption (a flat CAPM proxy) rather
# than beta-adjusted per stock -- see derived_ratios.py / pillars_fundamental.py compute_dcf_score.
RISK_FREE_RATE = 0.07
ERP_ASSUMPTION = 0.065
TERMINAL_GROWTH_ASSUMPTION = 0.06

PILLAR_SCORE_COLS = {
    "quality": "quality_sector_percentile", "growth": "growth_score", "value_relative": "value_relative_score",
    "dcf": "dcf_score", "stage": "stage_score", "sector_macro": "sector_macro_score",
    "ownership_flow": "ownership_flow_score", "accumulation": "accumulation_score",
}


def assemble_composite(pillar_scores: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Re-weights over only the pillars each row actually has -- a missing pillar is
    excluded from both the numerator and the weight total for that row, not zero-filled."""
    df = pillar_scores.copy()
    cols = [PILLAR_SCORE_COLS[p] for p in weights]
    weight_arr = np.array([weights[p] for p in weights])
    values = df[cols].to_numpy(dtype=float)
    available = ~np.isnan(values)
    weight_sum = (available * weight_arr).sum(axis=1)
    weighted_sum = np.nansum(values * weight_arr, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        # re-weighted average over only the pillars this row has (weight_sum is that row's
        # AVAILABLE weight total, not always 100) -- result stays on the same 0-100 scale
        # as every individual pillar score, exactly like a normal weighted average.
        composite = np.where(weight_sum > 0, weighted_sum / weight_sum, np.nan)
    df["composite_raw"] = composite
    return df


def _safe_pillar_group(label: str, fn):
    try:
        return fn()
    except Exception as e:
        print(f"[build_scorecard] WARNING: pillar group '{label}' failed ({e!r}) -- "
              f"continuing with the rest of the run; affected pillars will be NaN/Low-coverage.")
        return None


def _atomic_write(df: pd.DataFrame, path: str, fmt: str):
    tmp_path = path + ".tmp"
    if fmt == "parquet":
        df.to_parquet(tmp_path)
    else:
        df.to_csv(tmp_path, index=False)
    os.replace(tmp_path, path)  # atomic on the same filesystem -- no truncated file on a mid-write crash


def main(as_of_date: str) -> pd.DataFrame:
    universe = load_universe()
    universe["cyclicality_tag"] = tag_cyclicality(universe)

    raw_fundamentals = load_fundamentals_pit(as_of_date)
    prices = load_prices(universe["symbol"].tolist())
    ratios = derive_ratios(raw_fundamentals, prices, as_of_date)
    universe = universe.merge(ratios[ratios["metric_norm"] == "market_cap"][["symbol", "value"]]
                               .rename(columns={"value": "market_cap"}), on="symbol", how="left")

    # No real NIFTY50 index-level PE/PB TIME SERIES has been located yet (MASTER_PLAN.md open
    # risk, Post-plan item #2) -- classify_valuation_regime needs a stock's/index's OWN PAST
    # values to compare today against; a same-day cross-section of 750 stocks' PEs has no time
    # dimension to classify a regime from (comparing today's cross-sectional median against
    # itself is tautological -- always lands at the 50th percentile, i.e. always "Neutral",
    # which would silently make the regime tilt permanent dead code rather than an honest gap).
    # Default to "Neutral" (no tilt) explicitly until the real index series is confirmed and wired
    # in -- this keeps the regime-tilt code path exercised and correct, just inert for now.
    regime = "Neutral"
    weights = apply_regime_tilt(BASE_WEIGHTS, regime)

    fundamental_pieces = _safe_pillar_group("fundamentals", lambda: (
        compute_quality_score(ratios, universe, as_of_date),
        compute_growth_score(ratios, universe, as_of_date),
        compute_value_relative_score(ratios, universe, as_of_date),
        compute_dcf_score(ratios, RISK_FREE_RATE, ERP_ASSUMPTION, TERMINAL_GROWTH_ASSUMPTION, universe, as_of_date),
    )) or (None, None, None, None)
    quality, growth, value_rel, dcf = fundamental_pieces

    technical_pieces = _safe_pillar_group("technical", lambda: (
        compute_stage_technical_score(prices, universe, as_of_date),
        compute_accumulation_score(prices, universe, as_of_date),
    )) or (None, None)
    stage, accumulation = technical_pieces

    flow_pieces = _safe_pillar_group("flow", lambda: (
        compute_ownership_flow_score(load_ownership(as_of_date), universe, as_of_date),
        compute_sector_macro_score(prices, universe, regime, as_of_date),
    )) or (None, None)
    ownership_flow, sector_macro = flow_pieces

    pillar_scores = universe[["symbol", "sector", "cyclicality_tag"]].rename(
        columns={"cyclicality_tag": "sector_cyclicality_tag"})
    for piece in [quality, growth, value_rel, dcf, stage, sector_macro, ownership_flow, accumulation]:
        if piece is not None:
            pillar_scores = pillar_scores.merge(piece, on="symbol", how="left")
    for col in PILLAR_SCORE_COLS.values():
        if col not in pillar_scores.columns:
            pillar_scores[col] = np.nan  # whole pillar-group failed -- keep the schema stable, NaN not absent

    composite = assemble_composite(pillar_scores, weights)
    composite["regime_state"] = regime

    coverage_cols = [c for c in pillar_scores.columns if c.endswith("_coverage_pct")]
    composite["coverage_pct"] = pillar_scores[coverage_cols].mean(axis=1, skipna=True) if coverage_cols else np.nan
    composite["coverage_flag"] = pd.cut(
        composite["coverage_pct"], bins=[-1, 33.34, 66.67, 100], labels=["Low", "Med", "High"]).astype(str)

    bs_flags = _safe_pillar_group("balance_sheet_gate", lambda: compute_balance_sheet_flag(ratios, universe, as_of_date))
    liquidity_flags = _safe_pillar_group("liquidity_gate", lambda: compute_liquidity_flag(prices, universe, as_of_date))
    if bs_flags is None:
        bs_flags = pd.DataFrame({"symbol": universe["symbol"], "bs_flag": "AMBER"})  # fail safe, not fail open
    if liquidity_flags is None:
        liquidity_flags = pd.DataFrame({"symbol": universe["symbol"], "liquidity_flag": "AMBER", "is_illiquid": False})

    final = apply_overlay_gates(composite, bs_flags, liquidity_flags)
    final["as_of_date"] = as_of_date

    out_dir = os.path.join(os.path.dirname(__file__), "results", as_of_date)
    os.makedirs(out_dir, exist_ok=True)
    _atomic_write(final, os.path.join(out_dir, "scores.parquet"), "parquet")
    _atomic_write(final, os.path.join(out_dir, "scores.csv"), "csv")
    return final


if __name__ == "__main__":
    import datetime
    main(as_of_date=datetime.date.today().isoformat())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_build_scorecard.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/build_scorecard.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_build_scorecard.py"
git commit -m "feat(scorecard): orchestrator with per-pillar-group failure isolation, atomic writes, coverage-aware re-weighting"
```

---

### Task 12: Validation script

**Files:**
- Create: `validate_scorecard.py`
- Test: `tests/test_validate_scorecard.py`

**Interfaces:**
- Consumes: output shape from `main()` (Task 11): `symbol`, `final_score`, `bs_flag`
- Produces: `run_sanity_checks(scores_df: pd.DataFrame, watchlist: list) -> pd.DataFrame` [symbol, expected_tier, actual_final_score, actual_bs_flag, pass]

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validate_scorecard.py
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from validate_scorecard import run_sanity_checks

def test_run_sanity_checks_flags_mismatch():
    scores = pd.DataFrame({
        "symbol": ["A", "B"], "final_score": [85.0, 20.0], "bs_flag": ["GREEN", "RED"],
    })
    watchlist = [{"symbol": "A", "expected_tier": "high"}, {"symbol": "B", "expected_tier": "low"},
                 {"symbol": "C", "expected_tier": "high"}]
    result = run_sanity_checks(scores, watchlist)
    assert result[result["symbol"] == "A"].iloc[0]["pass"] == True
    assert result[result["symbol"] == "B"].iloc[0]["pass"] == True
    assert result[result["symbol"] == "C"].iloc[0]["pass"] == False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_validate_scorecard.py -v`
Expected: FAIL with "cannot import name 'run_sanity_checks'"

- [ ] **Step 3: Write minimal implementation**

```python
# validate_scorecard.py
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
import pandas as pd

TIER_THRESHOLDS = {"high": 70, "low": 30}


def run_sanity_checks(scores_df: pd.DataFrame, watchlist: list) -> pd.DataFrame:
    rows = []
    for item in watchlist:
        match = scores_df[scores_df["symbol"] == item["symbol"]]
        if match.empty:
            rows.append({"symbol": item["symbol"], "expected_tier": item["expected_tier"],
                          "actual_final_score": None, "actual_bs_flag": None, "pass": False})
            continue
        row = match.iloc[0]
        threshold = TIER_THRESHOLDS[item["expected_tier"]]
        passed = row["final_score"] >= threshold if item["expected_tier"] == "high" else row["final_score"] <= threshold
        rows.append({"symbol": item["symbol"], "expected_tier": item["expected_tier"],
                      "actual_final_score": row["final_score"], "actual_bs_flag": row["bs_flag"], "pass": passed})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    scores = pd.read_parquet(sys.argv[1])
    # supply your own watchlist of symbol/expected_tier pairs you can personally vouch for --
    # do not hardcode real company examples here without independently verifying them first.
    watchlist = []
    print(run_sanity_checks(scores, watchlist).to_string())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest tests/test_validate_scorecard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/validate_scorecard.py" "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/tests/test_validate_scorecard.py"
git commit -m "feat(scorecard): sanity-check harness against a Principal-supplied watchlist"
```

---

## Post-plan (not a task — human action, not automatable)
Before trusting this on the real 750-name universe: (1) run Task 1 Step 5's D-009 check and confirm the `nse_symbol` join-match rate is high — if low, `key_symbol` may be the real join key and every fundamentals-driven pillar needs re-pointing; (2) locate a real NIFTY50 index-level PE/PB TIME SERIES (not yet found anywhere in the repo) and wire it into Task 11's `main()` in place of the current hardcoded `regime = "Neutral"` — until then the regime-tilt mechanism is exercised end-to-end but inert (always Neutral, i.e. always the base weights), which is honest but means the whole regime-tilt design isn't actually doing anything yet; (3) source promoter pledge % from elsewhere if the Balance-Sheet-Safety gate's 2-signal version isn't trusted enough on its own; (4) supply `validate_scorecard.py` a real watchlist; (5) skim the `coverage_flag` distribution once run on the real universe.
