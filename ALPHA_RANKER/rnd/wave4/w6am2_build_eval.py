"""
W6AM2 -- ABSOLUTE P(up) V2: regime-decomposed, beta-propagated, calibrated,
portfolio-evaluated (Principal directive, 2026-07-17, follow-on to W6AM /
ABSOLUTE_MODEL_STANDALONE.md).

W6AM (V1) found: absolute-return predictability at 1M/1Y is dominated by
market/beta/regime, not stock-picking; 5Y shows real cross-sectional
information (GBM AUC 0.64) but on ~3-4 independent periods. This build does
NOT fight that finding -- it makes the decomposition EXPLICIT and STRUCTURAL:

    P(stock up | h) = f( P(market up | h)_regime ,  beta_252 ,  residual stock features )

(a) MARKET-REGIME P(up): a linear (logistic) walk-forward model of the
    BENCHMARK's (NIFTY500) own forward-up probability, from broad_richness_index
    (valuation band, 0/65/160 per BROAD_MARKET_VALUATION.md) + breadth_top/
    bottom_quintile (breadth-extreme). Strongest signal expected at 5Y
    (valuation mean-reversion), per task brief and per W5BV's own era-split
    findings (rho(richness, fwd 5Y return) = -0.795).
(b) BETA PROPAGATION: beta_252 and beta_252 x regime-logit interaction, so a
    high-beta name amplifies the regime's directional pull (fitted, not a
    hand-set multiplier).
(c) RESIDUAL stock-specific edge: the SAME already-validated, already-PIT
    features W6AM (V1) used -- value_secrel, quality_cfo_pat, quality_QMJ,
    mom_resid_peer, fwdgrowth_composite/z_accel/margin_inflection, mktcap_log,
    vol_252. Nothing new invented; reused verbatim.

METHODOLOGICAL CHANGE vs V1 (both retained, for different purposes):
  - harness.purged_walk_forward_splits() -- a purged K-FOLD CV (train CAN
    include dates AFTER the test block, only embargoed near it) -- is STILL
    used to feed the shared anti-overfit battery (IC/IC_IR/DSR/PBO/lag-test/
    placebo) for comparability with every other factor in the repo. This is
    correct for measuring cross-sectional IC validity but is NOT a
    live-tradeable simulation (train can see the future relative to test).
  - A NEW `causal_walk_forward_splits()` (strictly expanding-window: train
    only ever uses dates chronologically BEFORE the test block, minus an
    embargo) is added and used for (i) the regime P(up) model, (ii) the
    stock-level decomposition model's predictions actually fed into the
    PORTFOLIO backtest, and (iii) the calibration/reliability-curve check.
    This is the only way to honestly claim a CAGR/Sharpe/MDD number without
    lookahead -- the Principal's portfolio metrics need genuine
    train-strictly-before-test causality, not CV-style purging.

CALIBRATION: pooled causal-OOS predictions per horizon are split in HALF
CHRONOLOGICALLY -- isotonic regression fit on the EARLY half only, reliability
curve + Brier reported on the LATE half only (a genuine held-out check, fixing
V1's disclosed same-pool-calibration limitation).

CONVICTION: conviction = 100*(2*P_calibrated - 1), clipped [-100,100]. Shipped
this time (V1 explicitly withheld it) because the task requires a portfolio;
still tagged [INFERENCE]/paper-only, not a certified signal.

PORTFOLIO: monthly rebalance, compounds using ONLY REALIZED, NON-OVERLAPPING
fwd_ret_1M_raw (no overlap-inflation). Stock selection = 1Y-horizon full-model
calibrated P(up) (best coverage/recency tradeoff -- 1M is noise, 5Y truncates
the last ~5 years of OOS coverage). Exposure dial = blended 1Y+5Y regime P(up),
a FIXED (not fitted-to-backtest-performance), pre-specified linear ramp between
two probability thresholds, with a hard valuation>=160 cap -- written BEFORE
looking at the backtest result, to avoid tuning the dial to the metric it's
being scored on. GROSS OF COSTS (COST_STANDARDS.md is still DRAFT/un-approved
per firm rule D-025 -- cost-adjusted numbers would require an approved
standard this repo does not yet have).

No deep learning (D-011). SEED=17 everywhere, fixed hyperparameters, no
per-run refit, no search over the exposure-dial thresholds.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.isotonic import IsotonicRegression

warnings.filterwarnings("ignore")

_THIS = Path(__file__).resolve()
WAVE4_DIR = _THIS.parent
RND_DIR = WAVE4_DIR.parent
ALPHA_DIR = RND_DIR.parent
sys.path.insert(0, str(RND_DIR / "lib"))

import harness  # noqa: E402
import builders_value as bv  # noqa: E402
from sector_analytics import peer_relative  # noqa: E402

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
CAPSTONE_LEGS_PATH = RND_DIR / "panel" / "capstone_legs.parquet"
RICHNESS_PATH = RND_DIR / "panel" / "w5bv_broad_richness.parquet"
MARKET_STATE_PATH = RND_DIR / "panel" / "market_state.parquet"
CUBE_BENCH_PATH = RND_DIR / "panel" / "cube_bench_long.parquet"
MACRO_STATE_PATH = RND_DIR / "panel" / "macro_state.parquet"
W6FG_PATH = WAVE4_DIR / "_w6fg_scored.parquet"

OUT_JSON = WAVE4_DIR / "w6am2_results.json"
CARDS_DIR = RND_DIR / "cards"

HORIZONS = ("1M", "1Y", "5Y")
HOR_MONTHS = {"1M": 1, "1Y": 12, "5Y": 60}
MIN_NAMES_PER_DATE = 20
SEED = 17
EPS = 1e-4

# NOTE (post-first-run correction): the newer w5bv broad-richness gauge
# (broad_richness_index/breadth_top_bottom_quintile) is only non-null for
# 129/249 dates (coverage builds up as universe breadth grows) -- combined
# with the 60-month embargo this leaves ZERO usable causal folds at 5Y (a
# hard sample-size wall, confirmed empirically: n_dates_candidate=69 < the
# ~85+ needed for even one 24-month-train/60-month-embargo split). Per
# BROAD_MARKET_VALUATION.md's OWN prior reasoning ("chosen over the newer
# breadth-gauge specifically for its longer, hard-gated history"), the
# regime model's FITTED features are market_state.parquet's
# EY_hist_zscore_expanding (226/249 non-null from 2007-03) + breadth_pct_
# above_200dma (242/249 non-null from 2005-11) -- same conceptual valuation-
# band / breadth-extreme decomposition, just the longer-history source. The
# w5bv broad_richness_index is STILL used, separately, as the hard-cap
# diagnostic for the >=160 richness de-risk trigger in the portfolio (that
# trigger is a threshold check, not a fitted input, so its shorter/sparser
# history is a much smaller honesty problem there).
REGIME_FEATS = ["valuation_z", "breadth_200dma"]
RESID_FEATS = ["value_secrel", "quality_cfo_pat", "quality_QMJ", "mom_resid_peer",
               "fwdgrowth_composite", "z_accel", "margin_inflection", "mktcap_log", "vol_252"]

PORTFOLIO_HORIZON = "1Y"          # stock-selection engine (see docstring rationale)
PORTFOLIO_TOP_FRAC = 0.20          # long top quintile by calibrated P(up)
EXPOSURE_LO_P, EXPOSURE_HI_P = 0.35, 0.65   # FIXED pre-specified ramp thresholds (not fitted)
RICHNESS_DERISK_CAP = 160.0
RICHNESS_DERISK_EXPOSURE = 0.30


def log(*a):
    print(*a, flush=True)


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


# ==========================================================================
# 0. Causal (strictly train-before-test) walk-forward splits
# ==========================================================================
def causal_walk_forward_splits(dates, horizon, n_test_blocks=6, min_train_months=48):
    """Expanding-window walk-forward: train = dates[:test_start - embargo]
    ONLY (never dates after the test block) -- unlike
    harness.purged_walk_forward_splits (purged K-fold CV, used elsewhere in
    this file for the repo-standard IC/DSR/PBO battery). Used here wherever
    a prediction will be fed into an actual portfolio equity curve, so the
    reported CAGR/Sharpe/MDD carries no lookahead in either time direction."""
    dates = sorted(pd.to_datetime(pd.Index(dates).unique()))
    n = len(dates)
    embargo = HOR_MONTHS[horizon]
    if n <= min_train_months + embargo + 1:
        return []
    test_pool = dates[min_train_months:]
    if not test_pool:
        return []
    idx_chunks = np.array_split(np.arange(len(test_pool)), n_test_blocks)
    splits = []
    for chunk in idx_chunks:
        if len(chunk) == 0:
            continue
        block = [test_pool[i] for i in chunk]
        test_start_global = dates.index(block[0])
        train_end = test_start_global - embargo
        if train_end < max(24, min_train_months // 2):
            continue
        train = dates[:train_end]
        splits.append({"train": train, "test": block, "embargo_periods": embargo})
    return splits


# ==========================================================================
# 1. Stage A -- market regime P(up) model
# ==========================================================================
def build_market_regime_panel() -> pd.DataFrame:
    ms = pd.read_parquet(MARKET_STATE_PATH)
    ms["date"] = pd.to_datetime(ms["date"])
    ms = ms.rename(columns={"EY_hist_zscore_expanding": "valuation_z",
                             "breadth_pct_above_200dma": "breadth_200dma"})
    cb = pd.read_parquet(CUBE_BENCH_PATH)
    cb.index = pd.to_datetime(cb.index)

    dates = sorted(ms["date"].unique())
    px = cb["NIFTY500"].reindex(dates)
    mkt = ms[["date"] + REGIME_FEATS].set_index("date")
    mkt["px"] = px
    for h, m in HOR_MONTHS.items():
        fwd = mkt["px"].shift(-m) / mkt["px"] - 1.0
        mkt[f"mkt_fwd_ret_{h}"] = fwd
        up = pd.Series(np.where(fwd > 0, 1.0, 0.0), index=mkt.index)
        up[fwd.isna()] = np.nan
        mkt[f"mkt_up_{h}"] = up
    mkt = mkt.reset_index().rename(columns={"index": "date"})
    log(f"[DATA] market regime panel: {mkt.shape}, valuation_z non-null={mkt['valuation_z'].notna().sum()}, "
        f"breadth_200dma non-null={mkt['breadth_200dma'].notna().sum()}, "
        f"dates {mkt['date'].min().date()}..{mkt['date'].max().date()}")
    return mkt


def fit_regime_model(mkt: pd.DataFrame, horizon: str) -> dict:
    up_col = f"mkt_up_{horizon}"
    sub = mkt.dropna(subset=REGIME_FEATS).copy()
    train_pool = sub.dropna(subset=[up_col])
    dates_for_split = sorted(train_pool["date"].unique())
    splits = causal_walk_forward_splits(dates_for_split, horizon, n_test_blocks=6, min_train_months=48)

    rows, fold_log, last_model = [], [], None
    for i, sp in enumerate(splits):
        train = train_pool[train_pool["date"].isin(sp["train"])]
        test = sub[sub["date"].isin(sp["test"])]  # score on ALL dates in block incl. those w/o realized label
        if len(train) < 24 or train[up_col].nunique() < 2:
            continue
        pipe = Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=0.5, max_iter=1000, random_state=SEED)),
        ])
        pipe.fit(train[REGIME_FEATS].values, train[up_col].values)
        proba = pipe.predict_proba(test[REGIME_FEATS].values)[:, 1]
        rows.append(test[["date", up_col]].rename(columns={up_col: "y"}).assign(pred=proba))
        last_model = pipe
        fold_log.append({"fold": i, "n_train": int(len(train)), "n_test": int(len(test)),
                          "test_start": str(min(sp["test"]).date()), "test_end": str(max(sp["test"]).date())})

    pooled = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date", "y", "pred"])

    # tail extrapolation: dates after the last fold's test window (label not yet
    # realized at this horizon) -- frozen last-fitted model, portfolio continuity
    # only, NEVER scored for accuracy.
    covered = set(pooled["date"]) if not pooled.empty else set()
    last_covered = pooled["date"].max() if not pooled.empty else pd.Timestamp.min
    tail = sub[(~sub["date"].isin(covered)) & (sub["date"] > last_covered)]
    extrap = pd.DataFrame(columns=["date", "pred"])
    if last_model is not None and not tail.empty:
        p = last_model.predict_proba(tail[REGIME_FEATS].values)[:, 1]
        extrap = tail[["date"]].assign(pred=p)

    return {"oos": pooled, "extrap": extrap, "fold_log": fold_log,
            "n_dates_candidate": len(dates_for_split), "n_folds_used": len(fold_log)}


def eval_regime_model(oos: pd.DataFrame, horizon: str) -> dict:
    if oos.empty or oos["y"].nunique() < 2:
        return {"status": "INSUFFICIENT"}
    y, p = oos["y"].values, oos["pred"].values
    auc = float(roc_auc_score(y, p))
    brier = float(brier_score_loss(y, p))
    return {"n_obs": int(len(oos)), "n_dates": int(oos["date"].nunique()),
            "base_rate_up": float(y.mean()), "auc": auc, "brier_raw": brier}


# ==========================================================================
# 2. Stage B -- stock feature panel (reused verbatim from W6AM V1) + regime merge
# ==========================================================================
def build_stock_feature_panel(regime_oos_by_h: dict) -> pd.DataFrame:
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    log(f"[DATA] panel_long: {panel.shape}, dates {panel['date'].min().date()}..{panel['date'].max().date()}, "
        f"{panel['symbol'].nunique()} symbols")

    ey_raw = bv.build_H014_earnings_yield(panel)
    ey_secrel = peer_relative(ey_raw, level="sub_sector", method="z", min_peers=3).rename("value_secrel").reset_index()

    legs = pd.read_parquet(CAPSTONE_LEGS_PATH)
    legs["date"] = pd.to_datetime(legs["date"])
    keep_legs = ["quality_cfo_pat", "quality_QMJ", "mom_resid_peer"]
    legs_w = legs[legs["leg"].isin(keep_legs)].pivot_table(
        index=["date", "symbol"], columns="leg", values="value").reset_index()

    if W6FG_PATH.exists():
        fg = pd.read_parquet(W6FG_PATH)
        fg["date"] = pd.to_datetime(fg["date"])
        fg_w = fg[["date", "symbol", "composite_confirmed", "z_accel", "margin_inflection"]].rename(
            columns={"composite_confirmed": "fwdgrowth_composite"})
    else:
        fg_w = pd.DataFrame(columns=["date", "symbol", "fwdgrowth_composite", "z_accel", "margin_inflection"])
        log("[DATA] w6fg scored file NOT found -- forward-growth features all-NaN.")

    df = panel.merge(ey_secrel, on=["date", "symbol"], how="left")
    df = df.merge(legs_w, on=["date", "symbol"], how="left")
    df = df.merge(fg_w, on=["date", "symbol"], how="left")

    # broadcast each horizon's regime P(up) (causal-OOS + tail-extrapolated,
    # pooled) onto every stock on that date -- this IS the (a) term of the
    # decomposition.
    for h in HORIZONS:
        r = regime_oos_by_h[h]
        combo = pd.concat([r["oos"][["date", "pred"]], r["extrap"][["date", "pred"]]], ignore_index=True)
        combo = combo.drop_duplicates(subset="date").rename(columns={"pred": f"regime_pup_{h}"})
        df = df.merge(combo, on="date", how="left")
        df[f"regime_logit_{h}"] = _logit(df[f"regime_pup_{h}"].fillna(0.5))
        df[f"beta_x_regime_{h}"] = df["beta_252"] * df[f"regime_logit_{h}"]

    log(f"[DATA] assembled stock feature panel: {df.shape}")
    for c in RESID_FEATS + [f"regime_pup_{h}" for h in HORIZONS]:
        log(f"    {c}: non-null={df[c].notna().sum()} ({100*df[c].notna().mean():.1f}%)")
    return df


def _degenerate_safe_cols(Xtr: np.ndarray) -> list:
    keep = []
    for j in range(Xtr.shape[1]):
        col = Xtr[:, j]
        col = col[~np.isnan(col)]
        if len(np.unique(col)) >= 2:
            keep.append(j)
    return keep


def _make_logit_pipe():
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(C=0.5, max_iter=1000, random_state=SEED)),
    ])


def _make_gbm_clf():
    return HistGradientBoostingClassifier(
        max_depth=3, max_iter=150, learning_rate=0.05, l2_regularization=1.0,
        min_samples_leaf=200, random_state=SEED)


def causal_walk_forward_stock(df: pd.DataFrame, horizon: str) -> dict:
    """Causal (strictly train-before-test) OOS predictions for the stock-level
    decomposition model -- fed into calibration + the portfolio backtest.
    Three variants: BETAREGIME-ONLY (a+b terms only), FULL-LOGIT (linear
    baseline, FACTOR_LIBRARY rule), FULL-GBM (ML variant)."""
    raw_col = f"fwd_ret_{horizon}_raw"
    betaregime_feats = [f"regime_logit_{horizon}", "beta_252", f"beta_x_regime_{horizon}"]
    full_feats = betaregime_feats + RESID_FEATS

    sub_all = df.dropna(subset=betaregime_feats).copy()  # regime/beta always required
    sub_labeled = sub_all.dropna(subset=[raw_col]).copy()
    sub_labeled["y_up"] = (sub_labeled[raw_col] > 0).astype(int)

    dates_for_split = sorted(sub_labeled["date"].unique())
    splits = causal_walk_forward_splits(dates_for_split, horizon, n_test_blocks=6, min_train_months=48)
    log(f"  [{horizon}] causal-WF: {len(dates_for_split)} labeled candidate dates -> {len(splits)} folds")

    rows = {"betaregime": [], "full_logit": [], "full_gbm": []}
    fold_log = []
    last_models = {}
    for i, sp in enumerate(splits):
        train = sub_labeled[sub_labeled["date"].isin(sp["train"])]
        test = sub_all[sub_all["date"].isin(sp["test"])]  # score everything, incl. dates w/o realized label (tail)
        test_labeled = sub_labeled[sub_labeled["date"].isin(sp["test"])]
        if len(train) < 200 or len(test) < 20:
            continue
        fold_log.append({"fold": i, "n_train": int(len(train)), "n_test": int(len(test)),
                          "test_start": str(min(sp["test"]).date()), "test_end": str(max(sp["test"]).date())})

        Xtr_br, Xte_br = train[betaregime_feats].values, test[betaregime_feats].values
        Xtr_full, Xte_full = train[full_feats].values, test[full_feats].values
        ytr = train["y_up"].values

        keep_full = _degenerate_safe_cols(Xtr_full)
        dropped = [full_feats[j] for j in range(len(full_feats)) if j not in keep_full]
        if dropped:
            fold_log[-1]["gbm_cols_dropped_degenerate"] = dropped

        m_br = _make_logit_pipe()
        m_br.fit(Xtr_br, ytr)
        p_br = m_br.predict_proba(Xte_br)[:, 1]

        m_logit = _make_logit_pipe()
        m_logit.fit(Xtr_full, ytr)
        p_logit = m_logit.predict_proba(Xte_full)[:, 1]

        m_gbm = _make_gbm_clf()
        m_gbm.fit(Xtr_full[:, keep_full], ytr)
        p_gbm = m_gbm.predict_proba(Xte_full[:, keep_full])[:, 1]

        base = test[["date", "symbol"]].reset_index(drop=True)
        y_up_full = test.merge(sub_labeled[["date", "symbol", "y_up"]], on=["date", "symbol"], how="left")["y_up"]
        rows["betaregime"].append(base.assign(pred=p_br, y_up=y_up_full.values))
        rows["full_logit"].append(base.assign(pred=p_logit, y_up=y_up_full.values))
        rows["full_gbm"].append(base.assign(pred=p_gbm, y_up=y_up_full.values))
        last_models = {"betaregime": (m_br, betaregime_feats, None),
                        "full_logit": (m_logit, full_feats, None),
                        "full_gbm": (m_gbm, full_feats, keep_full)}

    out = {k: (pd.concat(v, ignore_index=True) if v else pd.DataFrame(columns=["date", "symbol", "pred", "y_up"]))
           for k, v in rows.items()}

    # tail extrapolation for the PORTFOLIO horizon only (keeps runtime sane):
    # dates after the last fold's test window, features present but label not
    # yet realized -- frozen last model, never scored for accuracy.
    if horizon == PORTFOLIO_HORIZON and last_models:
        last_test_date = max(sp["test"][-1] for sp in splits) if splits else pd.Timestamp.min
        tail = sub_all[sub_all["date"] > last_test_date]
        if not tail.empty:
            for name, (model, feats, keep_idx) in last_models.items():
                X = tail[feats].values
                Xp = X[:, keep_idx] if keep_idx is not None else X
                p = model.predict_proba(Xp)[:, 1]
                extra = tail[["date", "symbol"]].assign(pred=p, y_up=np.nan)
                out[name] = pd.concat([out[name], extra], ignore_index=True)

    out["_fold_log"] = fold_log
    out["_n_dates_candidate"] = len(dates_for_split)
    out["_n_folds_used"] = len(splits)
    return out


def clf_metrics(pred_df: pd.DataFrame) -> dict:
    scored = pred_df.dropna(subset=["y_up"])
    if scored.empty or scored["y_up"].nunique() < 2:
        return {"status": "NO_SCORABLE_OOS_ROWS"}
    y, p = scored["y_up"].values, scored["pred"].values
    return {"n_obs": int(len(scored)), "n_dates": int(scored["date"].nunique()),
            "base_rate_up": float(y.mean()), "auc": float(roc_auc_score(y, p)),
            "brier_raw": float(brier_score_loss(y, p))}


# ==========================================================================
# 3. Calibration -- chronological HALF-SPLIT (fit isotonic on early half,
#    score reliability + Brier on the LATE half only -- genuine held-out)
# ==========================================================================
def calibrate_chrono_holdout(pred_df: pd.DataFrame) -> dict:
    scored = pred_df.dropna(subset=["y_up"]).sort_values("date")
    if scored.empty or scored["date"].nunique() < 8:
        return {"status": "INSUFFICIENT_DATES_FOR_HOLDOUT_CALIBRATION"}
    dates = sorted(scored["date"].unique())
    mid = dates[len(dates) // 2]
    early = scored[scored["date"] <= mid]
    late = scored[scored["date"] > mid]
    if early["y_up"].nunique() < 2 or late.empty or late["y_up"].nunique() < 2:
        return {"status": "INSUFFICIENT_CLASS_BALANCE_FOR_HOLDOUT_CALIBRATION"}

    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(early["pred"].values, early["y_up"].values)
    p_cal_late = iso.transform(late["pred"].values)

    brier_raw_late = float(brier_score_loss(late["y_up"].values, late["pred"].values))
    brier_cal_late = float(brier_score_loss(late["y_up"].values, p_cal_late))
    auc_late = float(roc_auc_score(late["y_up"].values, late["pred"].values))

    dfc = late.copy()
    dfc["pred_cal"] = p_cal_late
    dfc["bin"] = pd.qcut(dfc["pred_cal"].rank(method="first"), min(10, dfc["pred_cal"].nunique()),
                          labels=False, duplicates="drop")
    rel = dfc.groupby("bin").agg(pred_cal_mean=("pred_cal", "mean"),
                                  actual_rate=("y_up", "mean"), n=("y_up", "size"))
    return {
        "fit_window": f"{early['date'].min().date()}..{early['date'].max().date()} (n={len(early)})",
        "eval_window_HELD_OUT": f"{late['date'].min().date()}..{late['date'].max().date()} (n={len(late)})",
        "auc_held_out": auc_late,
        "brier_raw_held_out": brier_raw_late,
        "brier_isotonic_held_out": brier_cal_late,
        "reliability_curve_deciles_HELD_OUT": rel.reset_index().to_dict(orient="records"),
        "_iso_model": iso,
    }


# ==========================================================================
# 4. Portfolio backtest -- monthly rebalance, realized 1M compounding only
# ==========================================================================
def exposure_dial(regime_pup_1y, regime_pup_5y, richness):
    """FIXED, pre-specified BEFORE looking at any backtest result -- linear
    ramp of blended regime P(up) between EXPOSURE_LO_P/EXPOSURE_HI_P, plus a
    hard richness>=160 cap. Never fitted to the portfolio metric it's scored
    on (that would be look-ahead tuning of the exposure rule itself)."""
    blended = 0.5 * regime_pup_1y + 0.5 * regime_pup_5y
    exp_ = (blended - EXPOSURE_LO_P) / (EXPOSURE_HI_P - EXPOSURE_LO_P)
    exp_ = np.clip(exp_, 0.0, 1.0)
    exp_ = np.where(richness >= RICHNESS_DERISK_CAP, np.minimum(exp_, RICHNESS_DERISK_EXPOSURE), exp_)
    return exp_


def build_portfolio(stock_oos: dict, mkt: pd.DataFrame, panel: pd.DataFrame) -> dict:
    """Stock selection: PORTFOLIO_HORIZON full-logit & full-gbm calibrated
    P(up) (isotonic fit on the FULL causal-OOS pool up to the portfolio's own
    formation date at each rebalance -- see note below); long top quintile,
    equal-weight, monthly rebalance, compounds with REALIZED fwd_ret_1M_raw
    only (no overlap). Exposure = fixed dial on blended 1Y/5Y regime P(up)."""
    sel_full = pd.concat([stock_oos["full_gbm"][["date", "symbol", "pred", "y_up"]].assign(model="full_gbm"),
                           stock_oos["full_logit"][["date", "symbol", "pred", "y_up"]].assign(model="full_logit")],
                          ignore_index=True)
    # pick the better-AUC model on the SCORED (labeled) portion only, decided
    # ONCE, not re-picked per fold (a single fixed choice, disclosed).
    auc_gbm = clf_metrics(stock_oos["full_gbm"]).get("auc", 0)
    auc_logit = clf_metrics(stock_oos["full_logit"]).get("auc", 0)
    chosen = "full_gbm" if (auc_gbm or 0) >= (auc_logit or 0) else "full_logit"
    log(f"  [portfolio] stock-selection model chosen on OOS AUC: {chosen} (gbm={auc_gbm}, logit={auc_logit})")

    raw = stock_oos[chosen][["date", "symbol", "pred"]].copy()
    # isotonic calibration for conviction mapping: fit on the full causal-OOS
    # SCORED pool (disclosed -- same-pool for the CONVICTION MAPPING used in
    # portfolio construction; the SEPARATE held-out reliability check above
    # is what certifies calibration quality, this is just the operational map)
    scored = stock_oos[chosen].dropna(subset=["y_up"])
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(scored["pred"].values, scored["y_up"].values)
    raw["p_cal"] = iso.transform(raw["pred"].values)
    raw["conviction"] = np.clip(100 * (2 * raw["p_cal"] - 1), -100, 100)

    # regime for exposure dial
    regime_1y = pd.concat([_regime_cache["1Y"]["oos"][["date", "pred"]],
                            _regime_cache["1Y"]["extrap"][["date", "pred"]]], ignore_index=True).drop_duplicates("date")
    regime_5y = pd.concat([_regime_cache["5Y"]["oos"][["date", "pred"]],
                            _regime_cache["5Y"]["extrap"][["date", "pred"]]], ignore_index=True).drop_duplicates("date")
    rich = pd.read_parquet(RICHNESS_PATH)[["date", "broad_richness_index"]]
    rich["date"] = pd.to_datetime(rich["date"])
    exp_df = regime_1y.rename(columns={"pred": "regime_pup_1Y"}).merge(
        regime_5y.rename(columns={"pred": "regime_pup_5Y"}), on="date", how="outer").merge(
        rich, on="date", how="left").sort_values("date")
    exp_df["regime_pup_5Y"] = exp_df["regime_pup_5Y"].ffill()  # 5Y regime stops earlier (embargo);
    # carry last known slow-moving regime read forward rather than assume 0.5 -- disclosed.
    exp_df["exposure"] = exposure_dial(exp_df["regime_pup_1Y"].fillna(0.5).values,
                                        exp_df["regime_pup_5Y"].fillna(0.5).values,
                                        exp_df["broad_richness_index"].fillna(0).values)

    # trading dates = intersection of (dates with stock selections) and (dates
    # with a realized fwd_ret_1M_raw, so we can compound this month's pick)
    raw_ret1m = panel[["date", "symbol", "fwd_ret_1M_raw"]].dropna()
    sel_dates = sorted(raw["date"].unique())

    monthly_rows = []
    for d in sel_dates:
        day_sel = raw[raw["date"] == d]
        if len(day_sel) < MIN_NAMES_PER_DATE:
            continue
        n_top = max(5, int(len(day_sel) * PORTFOLIO_TOP_FRAC))
        top = day_sel.sort_values("conviction", ascending=False).head(n_top)
        top_ret = top.merge(raw_ret1m[raw_ret1m["date"] == d], on=["date", "symbol"], how="inner")
        if top_ret.empty:
            continue
        equity_ret = float(top_ret["fwd_ret_1M_raw"].mean())  # equal-weight top-quintile
        monthly_rows.append({"date": d, "equity_sleeve_ret": equity_ret, "n_names": int(len(top_ret))})

    port = pd.DataFrame(monthly_rows).merge(exp_df[["date", "exposure"]], on="date", how="left")
    port["exposure"] = port["exposure"].fillna(0.5)

    # de-risk sleeve: GOLDBEES monthly return where available (macro_state,
    # from 2016), else 0% (cash proxy) -- disclosed, full gold history not
    # reconstructed in this pass.
    macro = pd.read_parquet(MACRO_STATE_PATH)[["date", "goldbees_ret_1m"]]
    macro["date"] = pd.to_datetime(macro["date"])
    port = port.merge(macro, on="date", how="left")
    port["derisk_sleeve_ret"] = port["goldbees_ret_1m"].fillna(0.0)
    port["strategy_ret"] = port["exposure"] * port["equity_sleeve_ret"] + (1 - port["exposure"]) * port["derisk_sleeve_ret"]

    return {"portfolio_monthly": port, "chosen_model": chosen,
            "auc_full_gbm": auc_gbm, "auc_full_logit": auc_logit}


def perf_stats(monthly_ret: pd.Series) -> dict:
    r = monthly_ret.dropna().values
    if len(r) < 6:
        return {"status": "INSUFFICIENT"}
    n = len(r)
    cum = np.cumprod(1 + r)
    cagr = float(cum[-1] ** (12.0 / n) - 1.0)
    ann_ret = float(r.mean() * 12)
    ann_vol = float(r.std(ddof=1) * np.sqrt(12))
    sharpe = float(ann_ret / ann_vol) if ann_vol > 0 else float("nan")
    running_max = np.maximum.accumulate(cum)
    dd = cum / running_max - 1.0
    mdd = float(dd.min())
    return {"n_months": int(n), "cagr": cagr, "ann_ret_arith": ann_ret, "ann_vol": ann_vol,
            "sharpe": sharpe, "mdd": mdd, "final_cum_growth": float(cum[-1])}


def benchmark_stats_same_window(dates: list) -> dict:
    cb = pd.read_parquet(CUBE_BENCH_PATH)
    cb.index = pd.to_datetime(cb.index)
    px = cb["NIFTY500"].reindex(sorted(dates))
    ret = px.pct_change().dropna()
    return perf_stats(ret)


# ==========================================================================
# 5. main
# ==========================================================================
_regime_cache = {}


def main():
    results = {}

    log("=== STAGE A: market regime P(up) ===")
    mkt = build_market_regime_panel()
    regime_results = {}
    for h in HORIZONS:
        r = fit_regime_model(mkt, h)
        _regime_cache[h] = r
        m = eval_regime_model(r["oos"], h)
        regime_results[h] = {"metrics": m, "n_folds_used": r["n_folds_used"],
                              "n_dates_candidate": r["n_dates_candidate"], "fold_log": r["fold_log"],
                              "n_extrap_tail_dates": int(len(r["extrap"]))}
        log(f"  [{h}] regime model: {m}")
    results["stage_A_regime"] = regime_results

    log("\n=== STAGE B: stock feature panel ===")
    df = build_stock_feature_panel(_regime_cache)

    log("\n=== STAGE B: stock decomposition model (causal walk-forward) ===")
    stock_results = {}
    stock_oos_by_h = {}
    for h in HORIZONS:
        oos = causal_walk_forward_stock(df, h)
        stock_oos_by_h[h] = oos
        h_res = {"n_folds_used": oos["_n_folds_used"], "n_dates_candidate": oos["_n_dates_candidate"],
                  "fold_log": oos["_fold_log"]}
        for name in ("betaregime", "full_logit", "full_gbm"):
            m = clf_metrics(oos[name])
            h_res[f"clf_{name}"] = m
            log(f"  [{h}] clf/{name}: {m}")
            # feed the causal-OOS scored predictions through the SAME harness
            # battery every rule factor goes through, for repo comparability
            # (uses harness.purged_walk_forward_splits internally, not the
            # causal splits -- disclosed distinction, see module docstring).
            scored = oos[name].dropna(subset=["y_up"])
            if not scored.empty:
                factor_series = scored.set_index(["date", "symbol"])["pred"]
                card = harness.evaluate(
                    factor_series, horizon=h, return_basis="raw",
                    factor_id=f"W6AM2_{name}_{h}", family="W6AM2",
                    panel=df, panel_source="real",
                    min_names_per_date=MIN_NAMES_PER_DATE, cards_dir=CARDS_DIR)
                h_res[f"harness_verdict_{name}"] = card.get("verdict")
                h_res[f"harness_ic_{name}"] = card.get("ic")
                h_res[f"harness_pbo_{name}"] = card.get("pbo")
                h_res[f"harness_dsr_{name}"] = card.get("dsr")

        # calibration (chronological holdout) for the FULL models
        for name in ("full_logit", "full_gbm"):
            cal = calibrate_chrono_holdout(oos[name])
            cal_report = {k: v for k, v in cal.items() if k != "_iso_model"}
            h_res[f"calibration_{name}"] = cal_report
            log(f"  [{h}] calibration/{name} (held-out): "
                f"AUC={cal_report.get('auc_held_out')}, brier_raw={cal_report.get('brier_raw_held_out')}, "
                f"brier_iso={cal_report.get('brier_isotonic_held_out')}")

        stock_results[h] = h_res
    results["stage_B_stock"] = stock_results

    log("\n=== STAGE C: portfolio backtest ===")
    port = build_portfolio(stock_oos_by_h[PORTFOLIO_HORIZON], mkt, df)
    port_monthly = port["portfolio_monthly"]
    strat_stats = perf_stats(port_monthly["strategy_ret"])
    equity_only_stats = perf_stats(port_monthly["equity_sleeve_ret"])  # no de-risk, for comparison
    bm_stats = benchmark_stats_same_window(port_monthly["date"].tolist())

    log(f"  strategy (with de-risk): {strat_stats}")
    log(f"  equity-only (no de-risk overlay): {equity_only_stats}")
    log(f"  benchmark (buy-hold NIFTY500, same window): {bm_stats}")

    results["stage_C_portfolio"] = {
        "chosen_stock_model": port["chosen_model"],
        "auc_full_gbm": port["auc_full_gbm"], "auc_full_logit": port["auc_full_logit"],
        "window": f"{port_monthly['date'].min()}..{port_monthly['date'].max()}" if not port_monthly.empty else None,
        "n_months": int(len(port_monthly)),
        "strategy_with_derisk": strat_stats,
        "equity_only_no_derisk": equity_only_stats,
        "benchmark_buyhold_same_window": bm_stats,
        "alpha_cagr_vs_bm": (strat_stats.get("cagr") - bm_stats.get("cagr"))
                            if isinstance(strat_stats, dict) and "cagr" in strat_stats and "cagr" in bm_stats else None,
        "beats_bm_sharpe": (strat_stats.get("sharpe", float("nan")) > bm_stats.get("sharpe", float("nan")))
                            if "sharpe" in strat_stats and "sharpe" in bm_stats else None,
        "beats_bm_mdd": (strat_stats.get("mdd", -1) > bm_stats.get("mdd", -1))
                            if "mdd" in strat_stats and "mdd" in bm_stats else None,
    }
    port_monthly.to_parquet(WAVE4_DIR / "w6am2_portfolio_monthly.parquet", index=False)

    OUT_JSON.write_text(json.dumps(harness._to_native(results), indent=2, default=str), encoding="utf-8")
    log(f"\nWrote {OUT_JSON}")
    log(f"Wrote {WAVE4_DIR / 'w6am2_portfolio_monthly.parquet'}")


if __name__ == "__main__":
    main()
