"""
ALPHA_RANKER shared evaluation harness — the anti-overfit gate.
Every factor experiment in the research loop MUST pass through evaluate() here.
One code path = no per-agent divergence (RESEARCH_PROTOCOL.md S3).

Owner: Dr. Sameer Bhat (Overfit & Sensitivity Analyst).
See ALPHA_RANKER/rnd/RESEARCH_PROTOCOL.md S3, S4 for the contract this implements.

[DATA] = read from disk verified. [INFERENCE] = derived/estimated by this module,
labelled where it appears in outputs. Nothing here is fabricated silently.
"""
from __future__ import annotations

import json
import math
import os
import time
import itertools
import warnings
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

# --------------------------------------------------------------------------
# Paths (all relative to repo root, resolved from this file's location)
# --------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent                       # ALPHA_RANKER/rnd
ALPHA_DIR = RND_DIR.parent                            # ALPHA_RANKER
REPO_ROOT = ALPHA_DIR.parent                          # NIFTY 500

PANEL_PATH = RND_DIR / "panel" / "panel.parquet"
TRIALS_PATH = RND_DIR / "trials_counter.json"
CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "reports"
COST_STANDARDS_PATH = REPO_ROOT / "Shreyas_Ionic_AMC" / "06_TRADING_DESK" / "COST_STANDARDS.md"
PRICES_DIR = ALPHA_DIR / "data" / "prices"
UNIVERSE_CSV = ALPHA_DIR / "data" / "universe" / "nifty_total_market_750.csv"

HORIZONS = ("1M", "1Y", "5Y")
# assumed monthly rebalance grid (RESEARCH_PROTOCOL.md S1: "monthly (weekly for 1M)").
# This harness evaluates on the monthly grid uniformly for all horizons; the
# weekly-1M refinement is a documented simplification, not a silent one.
HORIZON_PERIODS = {"1M": 1, "1Y": 12, "5Y": 60}

# How many YEARS each horizon's forward-return LABEL already spans. Used only
# by annualize_ls_return() below (CONSOLIDATION.md "HARNESS FIXES NEEDED" item
# 4, Manoj Pillai / ops-engineer repair pass, 2026-07-17). A 1M label is 1/12
# of a year (needs *12 to annualize); a 1Y label IS already annual (*1); a 5Y
# label is a 5-year CUMULATIVE return (needs /5, not *12).
HORIZON_YEARS = {"1M": 1.0 / 12.0, "1Y": 1.0, "5Y": 5.0}

DEFAULT_KILL_THRESHOLDS = {
    "ic_ir_min": 0.20,          # backlog.json _meta.kill_default
    "lag_test_delta_max": 0.25,
    "pbo_max": 0.50,
    "placebo_ic_max_abs": 0.02,
    "dsr_min": 0.0,
}

CARDS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
(RND_DIR / "panel").mkdir(parents=True, exist_ok=True)


# ==========================================================================
# 0. small utilities
# ==========================================================================
def _to_native(o):
    """Recursively convert numpy/pandas scalars to JSON-native python types."""
    if isinstance(o, dict):
        return {str(k): _to_native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_to_native(v) for v in o]
    if isinstance(o, (np.generic,)):
        return o.item()
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.isoformat()
    if isinstance(o, float) and math.isnan(o):
        return None
    if isinstance(o, np.ndarray):
        return _to_native(o.tolist())
    return o


def _nw_variance(x: np.ndarray, lag: int) -> float:
    """Newey-West (Bartlett-kernel) long-run variance of the sample mean of x."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    xc = x - x.mean()
    gamma0 = float(np.dot(xc, xc) / n)
    var = gamma0
    lag = max(0, min(lag, n - 2))
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        gamma_k = float(np.dot(xc[:-k], xc[k:]) / n)
        var += 2.0 * w * gamma_k
    return max(var, 1e-12) / n


def newey_west_tstat(x: pd.Series, horizon_periods: int) -> dict:
    """NW t-stat that mean(x)==0, with lag = horizon_periods (overlap-induced
    autocorrelation for horizons longer than the rebalance step)."""
    x = pd.Series(x).dropna()
    n = len(x)
    if n < 3:
        return {"t_stat": float("nan"), "n": n, "lag": horizon_periods}
    lag = max(1, horizon_periods - 1)
    nw_var = _nw_variance(x.values, lag)
    se = math.sqrt(nw_var) if nw_var > 0 else float("nan")
    t = float(x.mean() / se) if se and not math.isnan(se) else float("nan")
    return {"t_stat": t, "n": n, "lag": lag}


def _read_cost_standards_bps() -> dict:
    """Blend COST_STANDARDS.md (if APPROVED) into an approximate one-way-name
    round-trip cost in bps per market-cap tier. [INFERENCE]: this is an
    arithmetic combination of the approved per-item rates (STT + slippage
    floor doubled for round trip + exchange/GST/stamp), not an independent
    number. Falls back to a flat 25bps round-trip flagged DRAFT if the file
    is missing or not marked APPROVED."""
    fallback = {"tier_bps_rt": {"large": 25, "mid": 25, "small": 25, "micro": 25},
                "source": "FALLBACK_DRAFT_25bps_flat", "approved": False}
    try:
        txt = COST_STANDARDS_PATH.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return fallback
    approved = "STATUS: APPROVED" in txt
    if not approved:
        return fallback
    # Slippage floors (one-way bps), per COST_STANDARDS "Slippage floors" table.
    slip_1w = {"large": 10, "mid": 20, "small": 35, "micro": 50}
    stt_delivery_rt_bps = 20.0        # 0.1% both sides
    exch_gst_stamp_rt_bps = 3.0       # exchange txn + GST + stamp, blended, small
    tiers = {t: 2 * s + stt_delivery_rt_bps + exch_gst_stamp_rt_bps for t, s in slip_1w.items()}
    return {"tier_bps_rt": tiers, "source": str(COST_STANDARDS_PATH), "approved": True}


def _mktcap_tier(mktcap_log: pd.Series) -> pd.Series:
    """Cross-sectional (per-date) quantile bucketing of mktcap_log into
    large/mid/small/micro, approximating NIFTY-500-style cap tiers.
    [INFERENCE]: quantile buckets, not official index membership cutoffs."""
    q = mktcap_log.rank(pct=True)
    return pd.cut(q, bins=[-0.01, 0.20, 0.50, 0.80, 1.01],
                  labels=["micro", "small", "mid", "large"]).astype(str)


def _increment_trials(family: str) -> int:
    """Atomically (best-effort file-lock) increment the global + per-family
    honest-trials counter used for DSR deflation (RESEARCH_PROTOCOL.md S0.4)."""
    lock_path = TRIALS_PATH.with_suffix(".lock")
    acquired = False
    for _ in range(100):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            acquired = True
            break
        except FileExistsError:
            time.sleep(0.05)
    try:
        if TRIALS_PATH.exists():
            data = json.loads(TRIALS_PATH.read_text(encoding="utf-8"))
        else:
            data = {"total_trials": 0, "by_family": {}}
        data["total_trials"] = int(data.get("total_trials", 0)) + 1
        fam = family or "unknown"
        data.setdefault("by_family", {})
        data["by_family"][fam] = int(data["by_family"].get(fam, 0)) + 1
        TRIALS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data["total_trials"]
    finally:
        if acquired:
            try:
                os.remove(lock_path)
            except OSError:
                pass


# ==========================================================================
# 1. Panel loading / synthetic fallback
# ==========================================================================
def _label_cols(horizon: str) -> dict:
    return {b: f"fwd_ret_{horizon}_{b}" for b in ("raw", "excess", "resid")}


def build_synthetic_panel(n_symbols: int = 40, n_dates: int = 60, seed: int = 17,
                           inject_signal: bool = False) -> pd.DataFrame:
    """Small synthetic panel matching the real panel schema, for developing/
    unit-testing the harness mechanics when panel.parquet does not exist yet.
    [INFERENCE]/synthetic — NOT for scoring real factors, only plumbing tests.
    If inject_signal, a hidden 'true_factor' column is correlated with the
    forward-return labels so IC-calculation correctness can be checked."""
    rng = np.random.default_rng(seed)
    symbols = [f"SYN{i:03d}" for i in range(n_symbols)]
    dates = pd.bdate_range("2019-01-31", periods=n_dates, freq="ME")
    sectors = rng.choice(["IT", "Financials", "Pharma", "Industrials", "Consumer"], n_symbols)
    rows = []
    for d_i, d in enumerate(dates):
        mktcap = rng.normal(9, 1.5, n_symbols)
        beta = np.clip(rng.normal(1.0, 0.3, n_symbols), 0.2, 2.5)
        vol21 = np.abs(rng.normal(0.20, 0.06, n_symbols))
        vol63 = vol21 * rng.normal(1.0, 0.1, n_symbols)
        vol126 = vol21 * rng.normal(1.0, 0.15, n_symbols)
        vol252 = vol21 * rng.normal(1.0, 0.2, n_symbols)
        idio = vol252 * rng.uniform(0.5, 0.9, n_symbols)
        hidden = rng.normal(0, 1, n_symbols)
        regime_trend = rng.choice(["up", "down", "chop"], 1)[0]
        regime_vol = rng.choice(["low", "normal", "high"], 1)[0]
        regime_leader = rng.choice(["broad", "narrow"], 1)[0]
        for i, sym in enumerate(symbols):
            row = {
                "date": d, "symbol": sym, "sector": sectors[i],
                "mktcap_log": mktcap[i], "regime_trend": regime_trend,
                "regime_vol": regime_vol, "regime_leader": regime_leader,
                "beta_252": beta[i], "vol_21": vol21[i], "vol_63": vol63[i],
                "vol_126": vol126[i], "vol_252": vol252[i], "idio_vol_252": idio[i],
                "ff_beta_mkt": beta[i], "ff_beta_smb": rng.normal(0, 0.3),
                "ff_beta_hml": rng.normal(0, 0.3), "ff_beta_wml": rng.normal(0, 0.3),
                "_hidden_signal": hidden[i],
            }
            for h in HORIZONS:
                base_noise = rng.normal(0, 0.10)
                sig = hidden[i] * 0.03 if inject_signal else 0.0
                raw = sig + base_noise
                row[f"fwd_ret_{h}_raw"] = raw
                row[f"fwd_ret_{h}_excess"] = raw - 0.01
                row[f"fwd_ret_{h}_resid"] = raw - 0.01 - 0.5 * rng.normal(0, 0.05)
            rows.append(row)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def build_price_derived_panel(n_symbols: int = 150, seed: int = 7) -> pd.DataFrame:
    """Builds a REAL, price-derived demo panel from ALPHA_RANKER/data/prices
    (a subset of the NIFTY-750 universe, for runtime/token reasons — disclosed,
    not the full universe) so the __main__ demo can prove the whole path works
    on genuine market data rather than random noise. Used ONLY when
    panel.parquet does not exist. Regime labels are a simplified [INFERENCE]
    proxy (equal-weight-index trend/vol terciles), not the official
    results/regime_timeline.parquet."""
    rng = np.random.default_rng(seed)
    files = sorted(PRICES_DIR.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no price files under {PRICES_DIR}")
    if len(files) > n_symbols:
        files = list(rng.choice(files, size=n_symbols, replace=False))

    sector_map = {}
    if UNIVERSE_CSV.exists():
        u = pd.read_csv(UNIVERSE_CSV)
        sector_map = dict(zip(u["Symbol"], u["Industry"]))

    px = {}
    for f in files:
        try:
            d = pd.read_parquet(f)
        except Exception:
            continue
        if "Adj Close" not in d.columns or len(d) < 300:
            continue
        s = d["Adj Close"].copy()
        s.index = pd.to_datetime(s.index)
        px[f.stem] = s
    if len(px) < 10:
        raise RuntimeError("too few readable price files to build demo panel")

    prices = pd.DataFrame(px).sort_index()
    prices = prices.loc[:, prices.notna().sum() > 260]
    rets = prices.pct_change()
    mkt_ret = rets.mean(axis=1)  # equal-weight universe proxy = "market"

    # monthly rebalance grid = last trading day of each month present in data
    month_ends = prices.groupby(prices.index.to_period("M")).apply(lambda x: x.index.max())
    month_ends = pd.DatetimeIndex(sorted(month_ends.values))
    month_ends = month_ends[(month_ends >= prices.index[252]) if len(prices) > 252 else slice(None)]

    vol21 = rets.rolling(21).std() * math.sqrt(252)
    vol63 = rets.rolling(63).std() * math.sqrt(252)
    vol126 = rets.rolling(126).std() * math.sqrt(252)
    vol252 = rets.rolling(252).std() * math.sqrt(252)

    # rolling 252d beta to the equal-weight proxy (min 126 obs), per RESEARCH_PROTOCOL S2
    cov = rets.rolling(252, min_periods=126).cov(mkt_ret)
    var_m = mkt_ret.rolling(252, min_periods=126).var()
    beta = cov.div(var_m, axis=0)
    idio_vol = (rets.sub(beta.mul(mkt_ret, axis=0))).rolling(252, min_periods=126).std() * math.sqrt(252)

    mkt_trend = mkt_ret.rolling(200).mean()
    mkt_vol = mkt_ret.rolling(63).std() * math.sqrt(252)
    vol_terciles = mkt_vol.rank(pct=True)

    fwd_days = {"1M": 21, "1Y": 252, "5Y": 1260}
    rows = []
    for d in month_ends:
        if d not in prices.index:
            continue
        loc = prices.index.get_loc(d)
        row_syms = prices.columns
        trend_val = mkt_trend.get(d, np.nan)
        rtrend = "chop"
        if not pd.isna(trend_val):
            rtrend = "up" if trend_val > 0 else "down"
        vt = vol_terciles.get(d, np.nan)
        rvol = "normal" if pd.isna(vt) else ("low" if vt < 0.33 else ("high" if vt > 0.66 else "normal"))
        for sym in row_syms:
            b = beta.at[d, sym] if d in beta.index else np.nan
            iv = idio_vol.at[d, sym] if d in idio_vol.index else np.nan
            v21 = vol21.at[d, sym] if d in vol21.index else np.nan
            v63 = vol63.at[d, sym] if d in vol63.index else np.nan
            v126 = vol126.at[d, sym] if d in vol126.index else np.nan
            v252 = vol252.at[d, sym] if d in vol252.index else np.nan
            price_now = prices.at[d, sym]
            if pd.isna(price_now) or price_now <= 0:
                continue
            row = {
                "date": d, "symbol": sym,
                "sector": sector_map.get(sym, "Unknown"),
                "mktcap_log": float(np.log(max(price_now, 1e-6))),  # price proxy, NOT true mktcap
                "regime_trend": rtrend, "regime_vol": rvol, "regime_leader": "broad",
                "beta_252": b, "vol_21": v21, "vol_63": v63, "vol_126": v126,
                "vol_252": v252, "idio_vol_252": iv,
                "ff_beta_mkt": b, "ff_beta_smb": np.nan, "ff_beta_hml": np.nan, "ff_beta_wml": np.nan,
            }
            for h, nd in fwd_days.items():
                if loc + nd < len(prices.index):
                    fd_date = prices.index[loc + nd]
                    fut = prices.at[fd_date, sym] if sym in prices.columns else np.nan
                    fut_mkt_now = mkt_ret.loc[d:fd_date].add(1).prod() - 1 if not pd.isna(fut) else np.nan
                    if not pd.isna(fut) and fut > 0:
                        raw = fut / price_now - 1.0
                        b_use = 1.0 if pd.isna(b) else b
                        excess = raw - fut_mkt_now                       # simple market-relative
                        resid = raw - b_use * fut_mkt_now                # CAPM residual, alpha dropped (documented simplification)
                        row[f"fwd_ret_{h}_raw"] = raw
                        row[f"fwd_ret_{h}_excess"] = excess
                        row[f"fwd_ret_{h}_resid"] = resid
                    else:
                        row[f"fwd_ret_{h}_raw"] = np.nan
                        row[f"fwd_ret_{h}_excess"] = np.nan
                        row[f"fwd_ret_{h}_resid"] = np.nan
                else:
                    row[f"fwd_ret_{h}_raw"] = np.nan
                    row[f"fwd_ret_{h}_excess"] = np.nan
                    row[f"fwd_ret_{h}_resid"] = np.nan
            rows.append(row)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_panel(prefer_real: bool = True, build_demo_if_missing: bool = True) -> tuple[pd.DataFrame, str]:
    """Returns (panel_df, source_tag). source_tag in
    {'real','synthetic','price_derived_demo'} — always disclosed to the caller
    and stamped into the card so nobody mistakes a demo run for a real result."""
    if prefer_real and PANEL_PATH.exists():
        return pd.read_parquet(PANEL_PATH), "real"
    if build_demo_if_missing:
        warnings.warn(
            f"[INFERENCE] {PANEL_PATH} not found — building a price-derived demo "
            "panel from real market data (subset of universe) for harness "
            "development. This is NOT the production panel."
        )
        return build_price_derived_panel(), "price_derived_demo"
    warnings.warn(f"[INFERENCE] {PANEL_PATH} not found — using a fully synthetic panel.")
    return build_synthetic_panel(), "synthetic"


# ==========================================================================
# 2. factor alignment
# ==========================================================================
def _normalize_factor(factor) -> pd.DataFrame:
    """Coerce a Series/DataFrame indexed by (date,symbol) into a tidy
    DataFrame with columns ['date','symbol','factor']."""
    if isinstance(factor, pd.Series):
        f = factor.rename("factor").reset_index()
    else:
        f = factor.copy()
        if "factor" not in f.columns:
            value_cols = [c for c in f.columns if c not in ("date", "symbol")]
            if len(value_cols) == 1:
                f = f.rename(columns={value_cols[0]: "factor"})
            else:
                raise ValueError("factor DataFrame must have exactly one value "
                                  "column, or be named 'factor'")
        f = f.reset_index() if not {"date", "symbol"}.issubset(f.columns) else f
    if "date" not in f.columns or "symbol" not in f.columns:
        # MultiIndex names might differ; try positional index levels
        f = f.reset_index()
        cols_lower = {c.lower(): c for c in f.columns}
        if "date" in cols_lower and "symbol" in cols_lower:
            f = f.rename(columns={cols_lower["date"]: "date", cols_lower["symbol"]: "symbol"})
        else:
            raise ValueError("factor must be indexed/columned by (date, symbol)")
    f["date"] = pd.to_datetime(f["date"])
    return f[["date", "symbol", "factor"]].dropna(subset=["factor"])


# ==========================================================================
# 3. core stat pieces
# ==========================================================================
def _cross_sectional_ic(merged: pd.DataFrame, min_names: int, target_col: str = "target_eval") -> pd.Series:
    def _ic(g):
        if len(g) < min_names:
            return np.nan
        rho, _ = stats.spearmanr(g["factor"], g[target_col])
        return rho
    return merged.groupby("date").apply(_ic, include_groups=False)


def _decile_stats(merged: pd.DataFrame, min_names: int):
    """Per-date decile assignment on `factor` (fixed columns: factor,
    target_eval, target_raw, symbol, date). Returns:
      - decile_table: per-date decile means of target_eval (for monotonicity)
      - ls_ret: long(top)-short(bottom) decile spread of target_raw (tradeable)
      - top_sets: per-date set of top-decile symbols (for turnover)."""
    ls_rows = []
    decile_means = []
    top_sets = {}
    for d, g in merged.groupby("date"):
        if len(g) < min_names:
            continue
        try:
            g = g.assign(decile=pd.qcut(g["factor"].rank(method="first"), 10, labels=False, duplicates="drop"))
        except ValueError:
            continue
        if g["decile"].nunique() < 3:
            continue
        dmeans = g.groupby("decile")["target_eval"].mean()
        decile_means.append(dmeans)
        top_d = g["decile"].max()
        bot_d = g["decile"].min()
        top_ret = g.loc[g["decile"] == top_d, "target_raw"].mean()
        bot_ret = g.loc[g["decile"] == bot_d, "target_raw"].mean()
        ls_rows.append({"date": d, "ls_ret": top_ret - bot_ret})
        top_sets[d] = set(g.loc[g["decile"] == top_d, "symbol"])
    ls = pd.DataFrame(ls_rows).set_index("date")["ls_ret"] if ls_rows else pd.Series(dtype=float)
    decile_table = pd.DataFrame(decile_means) if decile_means else pd.DataFrame()
    return ls, decile_table, top_sets


def _turnover(top_sets: dict) -> float:
    dates = sorted(top_sets.keys())
    if len(dates) < 2:
        return float("nan")
    fracs = []
    for i in range(1, len(dates)):
        cur, prev = top_sets[dates[i]], top_sets[dates[i - 1]]
        if not cur:
            continue
        new_names = cur - prev
        fracs.append(len(new_names) / len(cur))
    return float(np.mean(fracs)) if fracs else float("nan")


def annualize_ls_return(mean_period_return: float, horizon: str) -> float:
    """Horizon-aware annualization of a long-short decile-spread return.

    BUG THIS FIXES (CONSOLIDATION.md "HARNESS FIXES NEEDED" item 4, flagged
    again in the 2026-07-17 wave): evaluate() below annualizes
    `ls_ret_raw.mean()` by a hardcoded `periods_per_year=12` regardless of
    horizon. That is correct ONLY for 1M, because the 1M forward-return label
    is itself a 1-month return sampled on the monthly rebalance grid, so
    *12 gives an honest annual figure. For 1Y the label is ALREADY a 1-year
    return (no further scaling needed — the old code inflated it ~12x). For
    5Y the label is a 5-YEAR CUMULATIVE return (needs /5 to get to an annual
    rate — the old code inflated it ~60x).

    `mean_period_return` must be the RAW, non-annualized mean of the
    horizon's long-short spread (`ls_ret_raw.mean()`), not the already-*12
    `ann_return_LS` the old code path produces.

    Non-destructive / additive (Manoj Pillai, ops-engineer, 2026-07-17): this
    is a NEW function called from evaluate() to populate a NEW, separate card
    field (`long_short.ann_return_LS_horizon_aware` /
    `costs.net_of_cost_ann_return_horizon_aware`). The OLD `ann_return_LS` /
    `net_of_cost_ann_return` fields and the verdict()/PROMOTE-PARK-KILL gate
    (which reads the OLD `net_of_cost_ann_return` field) are left completely
    untouched, so historical cards stay reproducible and no existing
    ranking/verdict changes — only new cards gain an honest, additional,
    correctly-scaled magnitude alongside the old (documented-buggy) one.
    pragmatic_score_v2.py achieves the same correction independently by
    inverting the old *12 straight from `ann_return_LS`, so it does not
    depend on this function having been called — this is for future
    evaluate() runs to get the right number natively instead of needing the
    inversion trick.
    """
    if mean_period_return is None or (isinstance(mean_period_return, float) and math.isnan(mean_period_return)):
        return float("nan")
    hy = HORIZON_YEARS.get(horizon, 1.0 / 12.0)
    return float(mean_period_return) / hy


def _expected_max_sharpe(n_trials: int, sigma_sr: float = 1.0) -> float:
    """Bailey & Lopez de Prado (2014) approximation for the expected maximum
    Sharpe ratio across n_trials independent trials, assuming trial-SR
    variance sigma_sr (default 1.0 — [INFERENCE]: we only track a trial
    COUNT, not the distribution of trial Sharpes, so we use the standard
    unit-variance simplification quoted in practitioner DSR writeups)."""
    if n_trials <= 1:
        return 0.0
    gamma = 0.5772156649015329  # Euler-Mascheroni
    z1 = stats.norm.ppf(1 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1 - 1.0 / (n_trials * math.e))
    return sigma_sr * ((1 - gamma) * z1 + gamma * z2)


def dsr_from_stats(sr_hat: float, skew: float, kurtosis: float, n_obs: int, n_trials: int) -> dict:
    """DSR computed from already-derived per-period stats (sr_hat, skew,
    kurtosis, n_obs) plus an EXPLICIT trial count, factored out of
    compute_dsr() so a caller can re-deflate with a different n_trials
    (e.g. per-family instead of the global cross-program counter) without
    re-deriving the raw return series. [INFERENCE]: same Bailey & Lopez de
    Prado (2014) formula as compute_dsr; sigma_sr=1.0 unit-variance
    simplification, same as the original.
    Added 2026-07-17 (Sameer Bhat) — CONSOLIDATION.md harness-fix item 2:
    the GLOBAL trial count (300+) was crushing every card's DSR toward 0;
    this lets pragmatic_score_v2.py recompute DSR per-family without
    touching compute_dsr()'s existing global-count behavior."""
    if n_obs is None or n_obs < 5 or sr_hat is None or (isinstance(sr_hat, float) and math.isnan(sr_hat)):
        return {"dsr": float("nan"), "sr_hat": sr_hat, "sr0_expected_max": float("nan"),
                "skew": skew, "kurtosis": kurtosis, "n_obs": n_obs, "n_trials": n_trials}
    sr0 = _expected_max_sharpe(n_trials)
    denom = 1 - skew * sr_hat + ((kurtosis - 1) / 4.0) * sr_hat ** 2
    denom = max(denom, 1e-6)
    z = (sr_hat - sr0) * math.sqrt(n_obs - 1) / math.sqrt(denom)
    dsr = float(stats.norm.cdf(z))
    return {"dsr": dsr, "sr_hat": sr_hat, "sr0_expected_max": sr0,
            "skew": skew, "kurtosis": kurtosis, "n_obs": n_obs, "n_trials": n_trials}


def compute_dsr(returns: pd.Series, n_trials: int) -> dict:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014). returns = a
    per-period (not annualized) return series for the strategy under test."""
    r = pd.Series(returns).dropna()
    n = len(r)
    if n < 5 or r.std(ddof=1) == 0:
        return {"dsr": float("nan"), "sr_hat": float("nan"), "sr0_expected_max": float("nan"),
                "skew": float("nan"), "kurtosis": float("nan"), "n_obs": n, "n_trials": n_trials}
    sr_hat = float(r.mean() / r.std(ddof=1))
    skew = float(stats.skew(r, bias=False))
    kurt = float(stats.kurtosis(r, fisher=False, bias=False))  # non-excess, normal=3
    return dsr_from_stats(sr_hat, skew, kurt, n, n_trials)


def compute_pbo_cscv(returns: pd.Series, n_blocks: int = 12) -> dict:
    """Single-factor CSCV/PBO adaptation. RESEARCH_PROTOCOL requires PBO via
    CSCV; the classic Bailey/Borwein/Lopez de Prado/Zhu (2014) formulation
    ranks MULTIPLE competing strategy variants within each IS/OOS split. This
    harness evaluates ONE factor at a time, so we adapt the same
    combinatorially-symmetric machinery to a single return series:
      1. split the chronological return series into n_blocks contiguous blocks
      2. enumerate all C(n_blocks, n_blocks/2) ways to pick half as "training"
      3. for each combo, compute Sharpe on the training half and on the
         complementary ("testing") half
      4. PBO = P(testing Sharpe < median testing Sharpe | training Sharpe >
         median training Sharpe) — i.e. among the splits where this factor
         looked in-sample-best (above its own cross-split median), what
         fraction of the time did its OOS half fall below the cross-split
         OOS median. [INFERENCE]: documented adaptation, not the literal
         multi-strategy paper procedure.
    """
    r = pd.Series(returns).dropna()
    n = len(r)
    if n < n_blocks * 2:
        n_blocks = max(4, (n // 2) * 2 // 2)
        n_blocks = max(4, n_blocks - (n_blocks % 2))
    if n < 8:
        return {"pbo": float("nan"), "n_combos": 0, "n_blocks": n_blocks, "n_obs": n}
    blocks = np.array_split(np.arange(n), n_blocks)
    block_ids = list(range(n_blocks))
    half = n_blocks // 2
    combos = list(itertools.combinations(block_ids, half))
    is_sr, oos_sr = [], []
    for combo in combos:
        train_idx = np.concatenate([blocks[b] for b in combo])
        test_idx = np.concatenate([blocks[b] for b in block_ids if b not in combo])
        tr = r.values[train_idx]
        te = r.values[test_idx]
        sr_tr = tr.mean() / tr.std(ddof=1) if tr.std(ddof=1) > 0 else 0.0
        sr_te = te.mean() / te.std(ddof=1) if te.std(ddof=1) > 0 else 0.0
        is_sr.append(sr_tr)
        oos_sr.append(sr_te)
    is_sr, oos_sr = np.array(is_sr), np.array(oos_sr)
    med_is, med_oos = np.median(is_sr), np.median(oos_sr)
    flagged = is_sr > med_is
    if flagged.sum() == 0:
        pbo = float("nan")
    else:
        pbo = float((oos_sr[flagged] < med_oos).mean())
    return {"pbo": pbo, "n_combos": len(combos), "n_blocks": n_blocks, "n_obs": n,
            "median_is_sharpe": float(med_is), "median_oos_sharpe": float(med_oos)}


def purged_walk_forward_splits(dates: list, horizon: str, n_splits: int = 5) -> list:
    """Expanding-window walk-forward splits with PURGE+EMBARGO = horizon
    length either side of the test fold, so overlapping forward-return
    windows can't leak across the train/test boundary (RESEARCH_PROTOCOL S1,
    S3). dates must be sorted, unique, at the harness's rebalance frequency
    (monthly). Returns list of {"train": [...], "test": [...]} date lists."""
    dates = sorted(pd.to_datetime(pd.Index(dates).unique()))
    n = len(dates)
    embargo = HORIZON_PERIODS.get(horizon, 1)
    if n < n_splits * 2:
        n_splits = max(1, n // 4)
    fold_edges = np.array_split(np.arange(n), n_splits)
    splits = []
    for fold in fold_edges:
        if len(fold) == 0:
            continue
        test_idx = set(fold.tolist())
        lo, hi = min(test_idx), max(test_idx)
        purge_lo, purge_hi = max(0, lo - embargo), min(n - 1, hi + embargo)
        train_idx = [i for i in range(n) if i < purge_lo or i > purge_hi]
        splits.append({
            "train": [dates[i] for i in train_idx],
            "test": [dates[i] for i in sorted(test_idx)],
            "embargo_periods": embargo,
        })
    return splits


# ==========================================================================
# 4. verdict
# ==========================================================================
def verdict(card: dict, thresholds: dict = None) -> str:
    """PROMOTE / PARK / KILL per RESEARCH_PROTOCOL.md S4 + backlog.json
    _meta.kill_default. KILL takes priority; anything not KILLed but with a
    weak net-of-cost or monotonicity result PARKs rather than PROMOTEs."""
    th = {**DEFAULT_KILL_THRESHOLDS, **(thresholds or {})}
    ic_ir = card.get("ic", {}).get("ic_ir")
    lag_delta = card.get("lag_test", {}).get("lag_test_delta")
    pbo = card.get("pbo", {}).get("pbo")
    placebo_ic = card.get("placebo", {}).get("placebo_ic")
    dsr = card.get("dsr", {}).get("dsr")

    def _nan(x):
        return x is None or (isinstance(x, float) and math.isnan(x))

    kill_reasons = []
    if not _nan(ic_ir) and ic_ir < th["ic_ir_min"]:
        kill_reasons.append(f"IC_IR {ic_ir:.3f} < {th['ic_ir_min']}")
    if not _nan(lag_delta) and lag_delta > th["lag_test_delta_max"]:
        kill_reasons.append(f"lag_test_delta {lag_delta:.3f} > {th['lag_test_delta_max']}")
    if not _nan(pbo) and pbo > th["pbo_max"]:
        kill_reasons.append(f"PBO {pbo:.3f} > {th['pbo_max']}")
    if not _nan(placebo_ic) and abs(placebo_ic) > th["placebo_ic_max_abs"]:
        kill_reasons.append(f"placebo_IC {placebo_ic:.3f} exceeds noise band")
    if not _nan(dsr) and dsr <= th["dsr_min"]:
        kill_reasons.append(f"DSR {dsr:.3f} <= {th['dsr_min']}")

    if kill_reasons:
        return f"KILL ({'; '.join(kill_reasons)})"

    net_cost = card.get("costs", {}).get("net_of_cost_ann_return")
    mono = card.get("deciles", {}).get("monotonicity")
    park_reasons = []
    if not _nan(net_cost) and net_cost <= 0:
        park_reasons.append("net_of_cost non-positive")
    if not _nan(mono) and abs(mono) < 0.5:
        park_reasons.append(f"weak decile monotonicity ({mono:.2f})")
    if park_reasons:
        return f"PARK ({'; '.join(park_reasons)})"
    return "PROMOTE"


# ==========================================================================
# 5. evaluate()
# ==========================================================================
def evaluate(factor, horizon: str, return_basis: str = "resid", factor_id: str = None,
             panel: pd.DataFrame = None, panel_source: str = None, family: str = None,
             cost_bps_override: float = None, min_names_per_date: int = 20, n_cscv_blocks: int = 12,
             n_placebo_shuffles: int = 5, placebo_seed: int = 42, write_card: bool = True,
             cards_dir: Path = None) -> dict:
    """The single evaluation entry point every factor experiment goes through.
    See module docstring / RESEARCH_PROTOCOL.md S3 for the full contract.
    `panel_source` lets a caller that pre-loaded the panel (e.g. via
    load_panel()) pass its provenance tag through so the card never mislabels
    a real-panel result as generic 'caller_supplied' (or vice versa) — this is
    an anti-overfit gate; provenance of the data must never be ambiguous."""
    assert horizon in HORIZONS, f"horizon must be one of {HORIZONS}"
    assert return_basis in ("raw", "excess", "resid"), "return_basis must be raw/excess/resid"
    factor_id = factor_id or f"anon_{int(time.time())}"
    family = family or factor_id.split("_")[0]

    if panel is None:
        panel, panel_source = load_panel()
    elif panel_source is None:
        panel_source = "caller_supplied_unknown_provenance"

    lbl = _label_cols(horizon)
    target_col = lbl[return_basis]
    raw_col = lbl["raw"]
    needed = ["date", "symbol", target_col, raw_col, "regime_trend", "regime_vol", "mktcap_log"]
    missing = [c for c in needed if c not in panel.columns]
    if missing:
        raise ValueError(f"panel missing required columns: {missing}")

    f = _normalize_factor(factor)
    base_cols = ["date", "symbol", "regime_trend", "regime_vol", "mktcap_log"]
    if target_col == raw_col:
        p = panel[base_cols + [target_col]].copy()
        p = p.rename(columns={target_col: "target_eval"})
        p["target_raw"] = p["target_eval"]
    else:
        p = panel[base_cols + [target_col, raw_col]].copy()
        p = p.rename(columns={target_col: "target_eval", raw_col: "target_raw"})
    p["date"] = pd.to_datetime(p["date"])
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])

    n_trials = _increment_trials(family)

    if merged.empty or merged["date"].nunique() < 4:
        card = {
            "factor_id": factor_id, "horizon": horizon, "return_basis": return_basis,
            "status": "FAIL_NO_OVERLAP",
            "note": "factor did not overlap panel on (date,symbol) with enough dates to score",
            "panel_source": panel_source, "n_trials": n_trials,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if write_card:
            _write_card(card, factor_id, cards_dir)
        return card

    # ---- IC series ----
    ic_series = _cross_sectional_ic(merged, min_names_per_date).dropna()
    ic_mean = float(ic_series.mean()) if len(ic_series) else float("nan")
    ic_std = float(ic_series.std(ddof=1)) if len(ic_series) > 1 else float("nan")
    ic_ir = float(ic_mean / ic_std) if ic_std else float("nan")
    nw = newey_west_tstat(ic_series, HORIZON_PERIODS[horizon])

    # ---- deciles / long-short / turnover ----
    # decile means (monotonicity) use the evaluation basis; the long-short
    # spread and turnover use target_raw (tradeable raw forward return).
    ls_ret_raw, decile_table, top_sets_raw = _decile_stats(merged, min_names=min_names_per_date)
    mono = float("nan")
    if not decile_table.empty and decile_table.shape[1] > 2:
        decile_means_overall = decile_table.mean(axis=0)
        mono, _ = stats.spearmanr(decile_means_overall.index.values, decile_means_overall.values)
    periods_per_year = 12
    ann_return_ls = float(ls_ret_raw.mean() * periods_per_year) if len(ls_ret_raw) else float("nan")
    # NEW (additive, not a replacement — see annualize_ls_return() docstring):
    # the honest, horizon-aware annualization. ann_return_ls above is LEFT
    # UNCHANGED (still *12 always) so existing cards/consumers/verdict() are
    # not disturbed; this is a second, correctly-scaled figure.
    ann_return_ls_horizon_aware = (annualize_ls_return(float(ls_ret_raw.mean()), horizon)
                                    if len(ls_ret_raw) else float("nan"))
    hit_rate = float((ls_ret_raw > 0).mean()) if len(ls_ret_raw) else float("nan")
    turnover = _turnover(top_sets_raw)

    # ---- costs ----
    cost_info = _read_cost_standards_bps()
    if cost_bps_override is not None:
        tier_bps = {"large": cost_bps_override, "mid": cost_bps_override,
                    "small": cost_bps_override, "micro": cost_bps_override}
        cost_source, cost_approved = "override", True
    else:
        tier_bps = cost_info["tier_bps_rt"]
        cost_source, cost_approved = cost_info["source"], cost_info["approved"]
    tiers = _mktcap_tier(merged.groupby("symbol")["mktcap_log"].mean())
    tier_counts = tiers.value_counts(normalize=True)
    blended_cost_bps = float(sum(tier_counts.get(t, 0) * tier_bps.get(t, 25) for t in ["large", "mid", "small", "micro"]))
    ann_cost_drag = (turnover if not math.isnan(turnover) else 0.0) * (blended_cost_bps / 10000.0) * periods_per_year
    net_of_cost_ann = ann_return_ls - ann_cost_drag if not math.isnan(ann_return_ls) else float("nan")
    # NEW (additive): cost drag itself is untouched (turnover is measured per
    # MONTHLY rebalance regardless of label horizon, so *12 there is already
    # correct) — only the gross return leg gets the horizon-aware figure.
    net_of_cost_ann_horizon_aware = (ann_return_ls_horizon_aware - ann_cost_drag
                                      if not math.isnan(ann_return_ls_horizon_aware) else float("nan"))

    # ---- DSR / PBO on the LS raw-return series ----
    dsr_res = compute_dsr(ls_ret_raw, n_trials)
    pbo_res = compute_pbo_cscv(ls_ret_raw, n_cscv_blocks)

    # ---- regime breakdown ----
    regime_breakdown = {}
    for rc in ("regime_trend", "regime_vol"):
        by = merged.groupby(["date", rc]).apply(
            lambda g: stats.spearmanr(g["factor"], g["target_eval"])[0] if len(g) >= min_names_per_date else np.nan,
            include_groups=False)
        by = by.reset_index()
        by.columns = ["date", "regime", "ic"]
        regime_breakdown[rc] = by.groupby("regime")["ic"].mean().dropna().to_dict()

    # ---- lag test (+1 rebalance period) ----
    pivot_f = merged.pivot_table(index="date", columns="symbol", values="factor")
    pivot_lag = pivot_f.sort_index().shift(1)
    lag_long = pivot_lag.stack().rename("factor").reset_index()
    lag_merged = lag_long.merge(p[["date", "symbol", "target_eval"]], on=["date", "symbol"], how="inner").dropna()
    ic_lag_series = _cross_sectional_ic(lag_merged, min_names_per_date).dropna()
    ic_lag_mean = float(ic_lag_series.mean()) if len(ic_lag_series) else float("nan")
    lag_delta = (float(abs(ic_lag_mean - ic_mean) / abs(ic_mean))
                 if (not math.isnan(ic_mean) and ic_mean != 0 and not math.isnan(ic_lag_mean))
                 else float("nan"))

    # ---- placebo (shuffle target within date) ----
    rng = np.random.default_rng(placebo_seed)
    placebo_ics = []
    for i in range(n_placebo_shuffles):
        shuffled = merged.copy()
        shuffled["target_eval"] = shuffled.groupby("date")["target_eval"].transform(
            lambda s: rng.permutation(s.values))
        pic = _cross_sectional_ic(shuffled, min_names_per_date).dropna()
        if len(pic):
            placebo_ics.append(pic.mean())
    placebo_ic = float(np.mean(placebo_ics)) if placebo_ics else float("nan")

    card = {
        "factor_id": factor_id, "family": family, "horizon": horizon, "return_basis": return_basis,
        "status": "OK", "panel_source": panel_source, "n_trials": n_trials,
        "n_dates": int(merged["date"].nunique()), "n_obs": int(len(merged)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ic": {"ic_mean": ic_mean, "ic_std": ic_std, "ic_ir": ic_ir,
               "newey_west_t": nw["t_stat"], "nw_lag": nw["lag"], "n_ic_dates": int(len(ic_series))},
        "deciles": {"monotonicity": None if isinstance(mono, float) and math.isnan(mono) else float(mono),
                    "n_decile_dates": int(len(decile_table))},
        "long_short": {"ann_return_LS": ann_return_ls,
                       "ann_return_LS_horizon_aware": ann_return_ls_horizon_aware,
                       "hit_rate": hit_rate, "n_periods": int(len(ls_ret_raw))},
        "turnover": {"avg_top_decile_turnover": turnover},
        "costs": {"blended_cost_bps_roundtrip": blended_cost_bps, "cost_source": cost_source,
                  "cost_approved": cost_approved, "ann_cost_drag": ann_cost_drag,
                  "net_of_cost_ann_return": net_of_cost_ann,
                  "net_of_cost_ann_return_horizon_aware": net_of_cost_ann_horizon_aware},
        "dsr": dsr_res,
        "pbo": pbo_res,
        "regime_breakdown": regime_breakdown,
        "lag_test": {"ic_lag_mean": ic_lag_mean, "lag_test_delta": lag_delta},
        "placebo": {"placebo_ic": placebo_ic, "n_shuffles": n_placebo_shuffles, "seed": placebo_seed},
    }
    card["verdict"] = verdict(card)
    card = _to_native(card)
    if write_card:
        _write_card(card, factor_id, cards_dir)
    return card


def _write_card(card: dict, factor_id: str, cards_dir: Path = None):
    out_dir = cards_dir or CARDS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{factor_id}.json"
    path.write_text(json.dumps(card, indent=2), encoding="utf-8")


def run_experiment(factor_id: str, factor_builder_fn, horizon: str, basis: str = "resid", **kwargs) -> dict:
    """Convenience wrapper: builder_fn(panel_df) -> factor Series/DataFrame,
    then evaluate() it. One line for a worker agent:
        card = run_experiment("H001_65dma", build_65dma_factor, "1M", "resid")
    """
    panel = kwargs.pop("panel", None)
    panel_source = kwargs.pop("panel_source", None)
    if panel is None:
        panel, panel_source = load_panel()
    factor = factor_builder_fn(panel)
    return evaluate(factor, horizon, return_basis=basis, factor_id=factor_id, panel=panel,
                     panel_source=panel_source, **kwargs)


# ==========================================================================
# 6. demo (__main__) — trailing 12-1 momentum on real prices, end to end
# ==========================================================================
def _build_demo_momentum_factor(panel: pd.DataFrame) -> pd.Series:
    """Classic 12-1 momentum: 252d trailing return skipping the most recent
    21d, reconstructed independently from real prices (not read off the
    panel) using the same symbols/dates as the panel, so this is a genuine
    end-to-end test of factor -> harness, not a tautology."""
    dates = sorted(panel["date"].unique())
    symbols = sorted(panel["symbol"].unique())
    px = {}
    for sym in symbols:
        fp = PRICES_DIR / f"{sym}.parquet"
        if not fp.exists():
            continue
        d = pd.read_parquet(fp)
        if "Adj Close" not in d.columns:
            continue
        s = d["Adj Close"]
        s.index = pd.to_datetime(s.index)
        px[sym] = s
    prices = pd.DataFrame(px).sort_index()
    rows = []
    for d in dates:
        if d not in prices.index:
            continue
        loc = prices.index.get_loc(d)
        if loc < 252:
            continue
        p_t21 = prices.iloc[loc - 21]
        p_t252 = prices.iloc[loc - 252]
        mom = (p_t21 / p_t252 - 1.0)
        for sym, val in mom.dropna().items():
            rows.append({"date": d, "symbol": sym, "factor": val})
    out = pd.DataFrame(rows)
    return out.set_index(["date", "symbol"])["factor"]


if __name__ == "__main__":
    print("=" * 70)
    print("ALPHA_RANKER harness self-demo: trailing 12-1 momentum, real prices")
    print("=" * 70)
    panel, src = load_panel()
    print(f"panel_source={src}  rows={len(panel)}  dates={panel['date'].nunique()}  symbols={panel['symbol'].nunique()}")
    mom = _build_demo_momentum_factor(panel)
    print(f"demo factor obs: {len(mom)}")
    card = evaluate(mom, horizon="1Y", return_basis="excess", factor_id="DEMO_mom12m1",
                     family="demo", panel=panel, panel_source=src)
    keep = {k: card[k] for k in ("factor_id", "horizon", "return_basis", "status", "panel_source",
                                  "n_trials", "n_dates", "n_obs", "ic", "deciles", "long_short",
                                  "turnover", "costs", "dsr", "pbo", "lag_test", "placebo", "verdict")}
    print(json.dumps(keep, indent=2))
    print(f"\ncard written to: {CARDS_DIR / 'DEMO_mom12m1.json'}")
