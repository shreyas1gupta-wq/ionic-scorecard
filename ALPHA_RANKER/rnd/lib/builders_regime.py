"""
Shared factor builders for the regime/forensic/ensemble worker hypotheses
(H031, H040, H049, H050) in the ALPHA_RANKER research loop.

Every builder returns a (date, symbol)-indexed Series (or a dict of such
Series for multi-variant experiments) consumable by
rnd/lib/harness.py::evaluate() / run_experiment(). Builders only -- this
module never touches production weights (RESEARCH_PROTOCOL.md S5).

[DATA] = read from disk. [INFERENCE] = a construction/simplification choice
made here, disclosed inline and in the resulting card's notes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent          # ALPHA_RANKER/rnd
ALPHA_DIR = RND_DIR.parent             # ALPHA_RANKER
PRICES_DIR = ALPHA_DIR / "data" / "prices"
FORENSIC_PATH = ALPHA_DIR / "results" / "universe_forensic_score.parquet"

HORIZON_PERIODS = {"1M": 1, "1Y": 12, "5Y": 60}

_PRICE_CACHE: dict = {}


# ==========================================================================
# shared primitives
# ==========================================================================
def _load_prices(symbols) -> pd.DataFrame:
    key = tuple(sorted(symbols))
    if key in _PRICE_CACHE:
        return _PRICE_CACHE[key]
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
    df = pd.DataFrame(px).sort_index()
    _PRICE_CACHE[key] = df
    return df


def build_mom12_1(panel: pd.DataFrame) -> pd.Series:
    """12-1 cross-sectional momentum: 252d trailing return skipping the most
    recent 21d. Reconstructed independently from data/prices/*.parquet (NOT
    read off the panel) at the panel's own monthly dates -- a genuine factor,
    not a tautology. This is the H031/H050/K-015-relevant momentum parent
    (matches backlog.json H003's construct)."""
    dates = sorted(panel["date"].unique())
    symbols = sorted(panel["symbol"].unique())
    prices = _load_prices(symbols)
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


def train_oos_split(dates, horizon: str, train_frac: float = 0.65):
    """Simple chronological TRAIN/OOS split with a purge+embargo gap of
    HORIZON_PERIODS[horizon] monthly periods between them, so the OOS
    forward-return window can never overlap the TRAIN estimation window
    (RESEARCH_PROTOCOL.md S1/S3). Returns (train_dates, oos_dates), both
    sorted lists of pd.Timestamp."""
    dates = sorted(pd.to_datetime(pd.Index(dates).unique()))
    n = len(dates)
    embargo = HORIZON_PERIODS.get(horizon, 1)
    cut = int(n * train_frac)
    train_dates = dates[:cut]
    oos_dates = dates[cut + embargo:]
    return train_dates, oos_dates


# ==========================================================================
# H031 -- factor x regime conditioning
# ==========================================================================
def build_regime_conditioned_variant(panel: pd.DataFrame, factor_series: pd.Series,
                                      regime_col: str, horizon: str, basis: str = "resid",
                                      train_frac: float = 0.65, min_names: int = 20) -> dict:
    """Learn a binary per-regime gate from TRAIN-period cross-sectional IC of
    `factor_series` against fwd_ret_<horizon>_<basis>-neutralized target
    (weight=1 if TRAIN mean IC in that regime bucket > 0, else 0 -- the
    simplest, least-overfittable literal reading of 'split a factor's weight
    by regime'), then applies the TRAIN-learned gate to the OOS window only.
    Returns both the conditioned and the (same-window) static factor so the
    two can be evaluated on an IDENTICAL OOS panel slice -- an apples-to-
    apples comparison, per RESEARCH_PROTOCOL S0.7 'replace, don't just add'
    and the K-015 caution (regime overlays must beat the static parent)."""
    f = factor_series.rename("factor").reset_index()
    target_col = f"fwd_ret_{horizon}_{basis}"
    p = panel[["date", "symbol", target_col, regime_col]].copy()
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", target_col])

    # split on dates that ACTUALLY carry a valid (non-NaN) target -- the tail
    # of the panel has no forward return yet at longer horizons (panel is PIT-
    # honest, not fabricated/extrapolated), so splitting on the raw panel date
    # list would push the OOS window into an all-NaN tail. [DISCLOSED FIX]
    dates_all = sorted(merged["date"].unique())
    train_dates, oos_dates = train_oos_split(dates_all, horizon, train_frac)

    train_m = merged[merged["date"].isin(train_dates)]
    ic_rows = []
    for (d, r), g in train_m.groupby(["date", regime_col]):
        if len(g) < min_names:
            continue
        rho, _ = stats.spearmanr(g["factor"], g[target_col])
        ic_rows.append({"date": d, "regime": r, "ic": rho})
    ic_df = pd.DataFrame(ic_rows)
    regime_ic_train = ic_df.groupby("regime")["ic"].mean() if len(ic_df) else pd.Series(dtype=float)
    weights = {r: (1.0 if v > 0 else 0.0) for r, v in regime_ic_train.items()}

    oos_m = merged[merged["date"].isin(oos_dates)].copy()
    oos_m["weight"] = oos_m[regime_col].map(weights).fillna(0.0)
    oos_m["factor_conditioned"] = oos_m["factor"] * oos_m["weight"]

    static_oos = oos_m.set_index(["date", "symbol"])["factor"]
    conditioned_oos = oos_m.set_index(["date", "symbol"])["factor_conditioned"]
    return {
        "conditioned": conditioned_oos,
        "static": static_oos,
        "regime_weights_from_train": weights,
        "regime_ic_train": regime_ic_train.to_dict(),
        "n_train_dates": len(train_dates),
        "n_oos_dates": len(oos_dates),
        "train_dates_span": [str(train_dates[0].date()), str(train_dates[-1].date())] if train_dates else None,
        "oos_dates_span": [str(oos_dates[0].date()), str(oos_dates[-1].date())] if oos_dates else None,
    }


# ==========================================================================
# H040 -- forensic penalty efficacy
# ==========================================================================
def build_forensic_factor(panel: pd.DataFrame) -> pd.Series:
    """Forensic 'safety' factor = -1 * forensic_risk_score_0_100
    (results/universe_forensic_score.parquet), sign-oriented so a POSITIVE IC
    means the factor works as the hypothesis expects (low risk -> higher
    forward residual return; backlog H040 sign='-' on the raw risk score).

    [INFERENCE] / DISCLOSED LIMITATION: this score is a CURRENT snapshot
    (results/universe_forensic_score.parquet has no PIT history), broadcast
    identically to every historical panel date. This is NOT a true walk-
    forward fundamental test -- it answers 'does today's forensic score, if
    it had existed, correlate with what actually happened to these names
    2021-2026', not 'would this have been tradeable in real time'. Because
    the factor is static by construction, the harness's one-day-lag test
    will trivially show ~zero lag_test_delta (the factor literally cannot
    change) -- that reading must NOT be read as certifying PIT-safety."""
    fs = pd.read_parquet(FORENSIC_PATH)[["symbol", "forensic_risk_score_0_100"]].dropna()
    fs = fs.rename(columns={"forensic_risk_score_0_100": "risk_score"})
    dates = sorted(panel["date"].unique())
    universe_syms = set(panel["symbol"].unique())
    fs = fs[fs["symbol"].isin(universe_syms)]
    idx = pd.MultiIndex.from_product([dates, fs["symbol"]], names=["date", "symbol"])
    base = pd.DataFrame(index=idx).reset_index()
    out = base.merge(fs, on="symbol", how="left")
    out["factor"] = -out["risk_score"]
    return out.dropna(subset=["factor"]).set_index(["date", "symbol"])["factor"]


# ==========================================================================
# H050 -- weight-learning vs equal/prior
# ==========================================================================
def build_ensemble_inputs(panel: pd.DataFrame) -> pd.DataFrame:
    """5 standard, cheap, already-available factors, each SIGN-ORIENTED so
    a higher value should predict a higher forward return:
      mom12_1      12-1 trailing momentum (price-derived)              sign +
      inv_idio_vol -idio_vol_252 (low idiosyncratic-vol anomaly)        sign +
      inv_beta     -beta_252 (low-beta anomaly / BAB)                   sign +
      neg_mktcap   -mktcap_log (size premium)                          sign +
      ff_beta_WML  rolling FF6 momentum-factor loading                 sign +
    Returns a tidy (date,symbol)-indexed wide frame, NOT yet standardized."""
    mom = build_mom12_1(panel).rename("mom12_1")
    base = panel[["date", "symbol", "idio_vol_252", "beta_252", "mktcap_log", "ff_beta_WML"]].copy()
    base = base.set_index(["date", "symbol"])
    base["inv_idio_vol"] = -base["idio_vol_252"]
    base["inv_beta"] = -base["beta_252"]
    base["neg_mktcap"] = -base["mktcap_log"]
    out = base[["inv_idio_vol", "inv_beta", "neg_mktcap", "ff_beta_WML"]].join(mom, how="inner")
    return out.dropna()


def _zscore_by_date(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(level="date").transform(lambda s: (s - s.mean()) / (s.std(ddof=0) or np.nan))


def build_rank_average_prior(panel: pd.DataFrame) -> pd.Series:
    """Baseline / prior: equal-weight average of cross-sectional percentile
    ranks of the 5 ensemble inputs -- the 'simple rank-average' comparator
    named in backlog H050."""
    inputs = build_ensemble_inputs(panel)
    ranks = inputs.groupby(level="date").rank(pct=True)
    return ranks.mean(axis=1).rename("factor")


FEAT_COLS = ["mom12_1", "inv_idio_vol", "inv_beta", "neg_mktcap", "ff_beta_WML"]


def build_ridge_learned_combo(panel: pd.DataFrame, horizon: str, basis: str = "resid",
                               train_frac: float = 0.65, alpha: float = 1.0) -> dict:
    """Fama-MacBeth-style ridge: fit a cross-sectional ridge regression of
    fwd_ret_<horizon>_<basis> on the 5 z-scored ensemble inputs AT EACH
    TRAIN date, average the per-date coefficient vectors, then apply the
    single learned weight vector to the OOS window only. Also returns the
    SAME-WINDOW rank-average prior for an apples-to-apples OOS comparison.

    [INFERENCE]: fixed alpha=1.0 in standardized-feature space, no CV grid
    over alpha -- a disclosed simplification (not tuned on the OOS window
    itself, so it does not leak, but it is not a swept hyperparameter)."""
    inputs = build_ensemble_inputs(panel)
    z = _zscore_by_date(inputs).dropna()
    target_col = f"fwd_ret_{horizon}_{basis}"
    tgt = panel.set_index(["date", "symbol"])[target_col]
    data = z.join(tgt, how="inner").dropna()

    # split on dates with an actual valid target only (see note in
    # build_regime_conditioned_variant -- avoids landing OOS in the all-NaN
    # tail of longer-horizon forward returns).
    dates_all = sorted(data.index.get_level_values("date").unique())
    train_dates, oos_dates = train_oos_split(dates_all, horizon, train_frac)

    coefs = []
    for d in train_dates:
        if d not in data.index.get_level_values("date"):
            continue
        g = data.xs(d, level="date")
        if len(g) < 20:
            continue
        X, y = g[FEAT_COLS].values, g[target_col].values
        model = Ridge(alpha=alpha, fit_intercept=True)
        model.fit(X, y)
        coefs.append(model.coef_)
    if not coefs:
        raise RuntimeError("no TRAIN dates had >=20 names to fit the ridge regression")
    w = np.mean(coefs, axis=0)
    weights = dict(zip(FEAT_COLS, w.tolist()))

    oos = data[data.index.get_level_values("date").isin(oos_dates)]
    combo = (oos[FEAT_COLS] * w).sum(axis=1).rename("factor")
    prior_oos = oos[FEAT_COLS].rank(pct=True).mean(axis=1).rename("factor")
    return {
        "learned": combo,
        "prior_oos_window": prior_oos,
        "weights": weights,
        "n_train_dates_fit": len(coefs),
        "n_oos_dates": len(set(oos.index.get_level_values("date"))),
        "train_dates_span": [str(train_dates[0].date()), str(train_dates[-1].date())] if train_dates else None,
        "oos_dates_span": [str(oos_dates[0].date()), str(oos_dates[-1].date())] if oos_dates else None,
    }
