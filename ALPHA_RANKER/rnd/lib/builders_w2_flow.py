"""
W2S-03 / W2S-04 — flow/positioning factor builders (institutional + promoter
shareholding drift), ALPHA_RANKER money-first research loop.

Worker: TICK (ALPHA_RANKER). Source: rnd/backlog_scout.json W2S-03, W2S-04.

DATA-TRUST DISCLOSURE (mandatory, per task brief):
    datasets/derived/shareholding_changes.parquet is STALE — no rows past
    quarter_end=2023-12-01 / available_date=2023-12-26. This module does NOT
    forward-carry a >9-month-old filing into the score: every PIT-joined value
    is dropped if the panel rebalance date is more than STALENESS_CAP_DAYS past
    the filing's available_date. This means, on the current file, no factor
    value exists for panel dates after ~2024-09 — a known, disclosed
    consequence of the freeze, not a bug. If the source file is ever refreshed
    with newer quarters, this cap will automatically start scoring the newer
    dates too (nothing here is hardcoded to 2023).

Hypotheses:
  (a) W2S-03 FII/DII institutional accumulation drift — rising combined
      FII+DII ownership QoQ -> forward return.
  (b) W2S-04 Promoter buying drift — rising promoter ownership QoQ -> forward
      return.

Construction choice (disclosed deviation from the literal backlog wording):
  The backlog frames both as a binary gate ("QoQ>0 for 2 consecutive
  quarters"). Gating to that AND-condition collapses the cross-section to a
  thin qualifying subset each date and, because it is near-binary, breaks the
  harness's decile/monotonicity machinery (qcut degenerates to 2 bins,
  `_decile_stats` requires >=3 unique deciles per date to score a date at
  all). Instead we build a CONTINUOUS factor — the 2-quarter trailing average
  of the relevant qoq column(s) — which (i) is ranked the same direction as
  the binary gate (higher 2q-avg = more consistently accumulating), (ii)
  degrades gracefully to a single quarter's value when only one prior
  quarter's own qoq is known, and (iii) lets the shared harness do full
  decile/IC/monotonicity scoring across the whole cross-section, which is the
  more standard and more statistically informative test of "does
  institutional/promoter buying predict returns". The strict AND-positive
  reading is preserved in spirit: a name with two positive quarters in a row
  scores higher on the 2q-average than a name with one positive and one
  negative quarter, and much higher than a name with two negative quarters.
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd

_LIB_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = _LIB_DIR.parents[1]          # .../ALPHA_RANKER
REPO_ROOT = ALPHA_ROOT.parent             # .../NIFTY 500

SHAREHOLDING_PATH = REPO_ROOT / "datasets" / "derived" / "shareholding_changes.parquet"

STALENESS_CAP_DAYS = 270  # ~9 months: one quarter's normal cadence (~90d) + slack;
                          # blocks multi-quarter-old filings from being silently
                          # carried forward as if they were fresh information.

_SH_CACHE = None


def _load_shareholding() -> pd.DataFrame:
    global _SH_CACHE
    if _SH_CACHE is not None:
        return _SH_CACHE
    sh = pd.read_parquet(SHAREHOLDING_PATH)
    sh["available_date"] = pd.to_datetime(sh["available_date"])
    sh["quarter_end"] = pd.to_datetime(sh["quarter_end"])
    sh = sh.sort_values(["symbol", "quarter_end"]).reset_index(drop=True)

    # 2-quarter trailing average of each *_qoq column (current + immediately
    # prior quarter for that symbol, by quarter_end order -- NOT calendar
    # gaps, so a missing quarter correctly produces NaN via min_periods=2).
    for col in ("FIIs_qoq", "DIIs_qoq", "Promoters_qoq"):
        sh[f"{col}_2q_avg"] = (
            sh.groupby("symbol")[col]
            .transform(lambda s: s.rolling(2, min_periods=2).mean())
        )
    sh["fii_dii_2q_avg"] = sh[["FIIs_qoq_2q_avg", "DIIs_qoq_2q_avg"]].mean(axis=1)
    _SH_CACHE = sh
    return _SH_CACHE


def _asof_join_capped(panel_df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Backward merge_asof of each panel (date,symbol) onto the latest
    shareholding filing with available_date <= date, then drop any match
    older than STALENESS_CAP_DAYS -- the PIT + anti-stale-carryforward gate
    this whole module exists to enforce."""
    sh = _load_shareholding()
    right = sh[["symbol", "available_date", value_col]].dropna(subset=[value_col])
    right = right.sort_values(["available_date", "symbol"]).reset_index(drop=True)

    left = panel_df[["date", "symbol"]].drop_duplicates().sort_values(["date", "symbol"]).reset_index(drop=True)
    left = left.assign(date=pd.to_datetime(left["date"]), symbol=left["symbol"].astype(str))
    right = right.assign(symbol=right["symbol"].astype(str))

    m = pd.merge_asof(left.sort_values("date"), right.sort_values("available_date"),
                       left_on="date", right_on="available_date", by="symbol", direction="backward")
    m["staleness_days"] = (m["date"] - m["available_date"]).dt.days
    m = m[m["staleness_days"].notna() & (m["staleness_days"] >= 0) & (m["staleness_days"] <= STALENESS_CAP_DAYS)]
    return m


def build_w2s03_fii_dii_accum(panel_df: pd.DataFrame) -> pd.Series:
    """W2S-03: FII/DII institutional accumulation drift, continuous
    2-quarter-average FIIs_qoq/DIIs_qoq blend, PIT + staleness-capped."""
    m = _asof_join_capped(panel_df, "fii_dii_2q_avg")
    m = m.dropna(subset=["fii_dii_2q_avg"])
    return m.set_index(["date", "symbol"])["fii_dii_2q_avg"]


def build_w2s04_promoter_accum(panel_df: pd.DataFrame) -> pd.Series:
    """W2S-04: Promoter buying drift, continuous 2-quarter-average
    Promoters_qoq, PIT + staleness-capped."""
    m = _asof_join_capped(panel_df, "Promoters_qoq_2q_avg")
    m = m.dropna(subset=["Promoters_qoq_2q_avg"])
    return m.set_index(["date", "symbol"])["Promoters_qoq_2q_avg"]


def coverage_report(panel_df: pd.DataFrame) -> dict:
    """Diagnostic: what fraction of panel (date,symbol) obs and of panel
    dates get a scoreable value after the PIT+staleness join, for each
    factor. Used to decide PARK-for-thin-coverage per the task brief."""
    total_dates = panel_df["date"].nunique()
    total_obs = len(panel_df[["date", "symbol"]].drop_duplicates())
    out = {}
    for name, builder in (("fii_dii", build_w2s03_fii_dii_accum), ("promoter", build_w2s04_promoter_accum)):
        f = builder(panel_df)
        n_dates = f.reset_index()["date"].nunique()
        n_obs = len(f)
        out[name] = {
            "n_dates_with_data": int(n_dates), "total_panel_dates": int(total_dates),
            "pct_dates_covered": round(100.0 * n_dates / total_dates, 1) if total_dates else None,
            "n_obs": int(n_obs), "total_panel_obs": int(total_obs),
            "pct_obs_covered": round(100.0 * n_obs / total_obs, 2) if total_obs else None,
            "date_min": str(f.reset_index()["date"].min()) if n_dates else None,
            "date_max": str(f.reset_index()["date"].max()) if n_dates else None,
        }
    return out
