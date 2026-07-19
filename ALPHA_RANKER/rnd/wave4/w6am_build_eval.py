"""
W6AM -- STANDALONE ABSOLUTE-RETURN MODEL prototype (Principal directive, 2026-07-17).

NOT the relative-rank->absolute conversion (ABSOLUTE_SCORER_SPEC.md, SUPERSEDED per Principal).
This is its own forward predictor of a stock's absolute (not cross-sectionally demeaned)
forward return, direction, and P(up), per horizon 1M/1Y/5Y.

Owner: Ishaan Gupta (ML/Data Science). Tags: [DATA]=on-record fact, [INFERENCE]=my
construction, [OPINION]=my judgment. Nothing fabricated silently.

DESIGN
------
Base grid: rnd/panel/panel_long.parquet (2005-2025 monthly, full history -- panel.parquet
is only the 2021-2026 short panel and would starve the walk-forward CV of history).

Features (all PIT, all reused from already-built/validated firm modules -- no new
fundamentals plumbing invented here):
  - value_secrel   : build_H014_earnings_yield(panel) peer_relative-demeaned within
                      sub_sector (builders_value.py + sector_analytics.py) -- the
                      sector-bias-audit fix (raw EY is sector-contaminated).
  - quality_cfo_pat, quality_QMJ : capstone_legs.parquet legs (already-validated,
                      already-PIT quality composite legs of the canonical 7-leg model).
  - mom_resid_peer : capstone_legs.parquet leg (peer-relative residual momentum).
  - fwd growth      : rnd/wave4/_w6fg_scored.parquet composite_confirmed / z_accel /
                      margin_inflection / earnings_confirm (the Wave-4/6 forward-growth-
                      divergence agent's already-PIT, earnings-confirmed features --
                      ingested as instructed, not rebuilt).
  - regime          : market_state.parquet EY_hist_zscore_expanding (broad valuation
                      band -- the SAME primary M-term input BROAD_MARKET_VALUATION.md
                      recommends) + breadth_pct_above_200dma (breadth-extreme).
  - beta / market   : beta_252 (rolling realised beta) -- REQUIRED per task brief since
                      absolute returns are dominated by market direction; interacted
                      with the regime z-score (beta_x_valz) so a model can learn that
                      high-beta names carry more of the regime's directional pull.
  - momentum-regime gate: mom_x_valz = mom_resid_peer * valuation z-score (interaction,
                      not a hand-set multiplier -- the model/CV decides the weight; this
                      is how the momentum-extreme rule is expressed for a FITTED model,
                      as opposed to the hand-set-constant scorer in ABSOLUTE_SCORER_SPEC).
  - controls        : mktcap_log, vol_252.

FACTOR_LIBRARY rule (charter): a linear/rank baseline (Ridge here) MUST be run and its
cost-adjusted verdict reported BEFORE any GBM variant is trusted -- both are run, but the
Ridge card is what gates "is there a there there" before the GBM's honesty is assessed.

CV: harness.purged_walk_forward_splits() reused verbatim (embargo = horizon length, same
purge/embargo machinery every rule-factor in this repo goes through -- one code path).

Evaluation: OOS (walk-forward, test-fold-only) predictions per horizon are fed straight
into harness.evaluate() as a "factor" (return_basis="raw", since the target IS the
absolute/raw forward return, not resid/excess) -- this reuses the exact same anti-overfit
battery (IC, IC_IR, decile monotonicity, cost-adjusted long-short, DSR w/ honest trial
count, PBO/CSCV, lag-test, placebo) every rule in this repo is held to. Classification
(P(up)) and calibration are evaluated separately (AUC, Brier, reliability curve) since the
harness has no classification path.

Three models compared per horizon, all walk-forward OOS:
  1. BETA-ONLY  : beta_252, EY_hist_zscore_expanding, breadth_pct_above_200dma, beta_x_valz
                  only -- "how much of absolute-return predictability is just market/beta".
  2. RIDGE FULL : all features, standardized + median-imputed, L2-regularized linear.
  3. GBM FULL   : all features, sklearn HistGradientBoostingRegressor/Classifier (native
                  NaN handling -- no lightgbm installed in this env; HGB is the same
                  histogram-binned-tree family, cheapest capable substitute, documented).

No deep learning (D-011). No fitted-magnitude claims beyond what OOS actually shows.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss

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
MARKET_STATE_PATH = RND_DIR / "panel" / "market_state.parquet"
W6FG_PATH = WAVE4_DIR / "_w6fg_scored.parquet"

OUT_JSON = WAVE4_DIR / "w6am_results.json"
CARDS_DIR = RND_DIR / "cards"

HORIZONS = ("1M", "1Y", "5Y")
MIN_NAMES_PER_DATE = 20
SEED = 17

BETA_ONLY_FEATS = ["beta_252", "valuation_z", "breadth_200dma", "beta_x_valz"]
FULL_FEATS = BETA_ONLY_FEATS + [
    "value_secrel", "quality_cfo_pat", "quality_QMJ", "mom_resid_peer",
    "fwdgrowth_composite", "z_accel", "margin_inflection",
    "mom_x_valz", "mktcap_log", "vol_252",
]


def log(*a):
    print(*a, flush=True)


# ==========================================================================
# 1. Build the feature panel
# ==========================================================================
def build_feature_panel() -> pd.DataFrame:
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    log(f"[DATA] panel_long: {panel.shape}, dates {panel['date'].min().date()}..{panel['date'].max().date()}, "
        f"{panel['symbol'].nunique()} symbols")

    # ---- sector-relative value (the sector-bias-audit fix) ----
    ey_raw = bv.build_H014_earnings_yield(panel)
    ey_secrel = peer_relative(ey_raw, level="sub_sector", method="z", min_peers=3)
    ey_secrel = ey_secrel.rename("value_secrel").reset_index()
    log(f"[DATA] sector-relative EY: {len(ey_secrel)} obs (raw EY had {len(ey_raw)})")

    # ---- quality + momentum legs (already-PIT, already-validated) ----
    legs = pd.read_parquet(CAPSTONE_LEGS_PATH)
    legs["date"] = pd.to_datetime(legs["date"])
    keep_legs = ["quality_cfo_pat", "quality_QMJ", "mom_resid_peer"]
    legs_w = legs[legs["leg"].isin(keep_legs)].pivot_table(
        index=["date", "symbol"], columns="leg", values="value").reset_index()
    log(f"[DATA] capstone_legs pivoted: {legs_w.shape}, legs kept={keep_legs}")

    # ---- forward-growth features (wave-4/6 agent, ingested not rebuilt) ----
    if W6FG_PATH.exists():
        fg = pd.read_parquet(W6FG_PATH)
        fg["date"] = pd.to_datetime(fg["date"])
        fg_w = fg[["date", "symbol", "composite_confirmed", "z_accel", "margin_inflection"]].rename(
            columns={"composite_confirmed": "fwdgrowth_composite"})
        log(f"[DATA] w6fg forward-growth features: {fg_w.shape}, "
            f"dates {fg_w['date'].min().date()}..{fg_w['date'].max().date()}")
    else:
        fg_w = pd.DataFrame(columns=["date", "symbol", "fwdgrowth_composite", "z_accel", "margin_inflection"])
        log("[DATA] w6fg scored file NOT found -- forward-growth features will be all-NaN "
            "(GBM handles natively; Ridge median-imputes + flags).")

    # ---- regime: broad valuation band (market-level, broadcast) + breadth ----
    mkt = pd.read_parquet(MARKET_STATE_PATH)
    mkt["date"] = pd.to_datetime(mkt["date"])
    mkt_feat = mkt[["date", "EY_hist_zscore_expanding", "breadth_pct_above_200dma"]].rename(
        columns={"EY_hist_zscore_expanding": "valuation_z", "breadth_pct_above_200dma": "breadth_200dma"})
    log(f"[DATA] market_state regime cols: {mkt_feat.shape}, "
        f"valuation_z non-null={mkt_feat['valuation_z'].notna().sum()}, "
        f"breadth non-null={mkt_feat['breadth_200dma'].notna().sum()}")

    # ---- assemble ----
    df = panel.merge(ey_secrel, on=["date", "symbol"], how="left")
    df = df.merge(legs_w, on=["date", "symbol"], how="left")
    df = df.merge(fg_w, on=["date", "symbol"], how="left")
    df = df.merge(mkt_feat, on="date", how="left")

    df["beta_x_valz"] = df["beta_252"] * df["valuation_z"]
    df["mom_x_valz"] = df["mom_resid_peer"] * df["valuation_z"]

    log(f"[DATA] assembled feature panel: {df.shape}")
    for c in FULL_FEATS:
        log(f"    {c}: non-null={df[c].notna().sum()} ({100*df[c].notna().mean():.1f}%)")
    return df


# ==========================================================================
# 2. Walk-forward OOS prediction per horizon
# ==========================================================================
def _make_ridge_pipe():
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", Ridge(alpha=5.0, random_state=SEED)),
    ])


def _make_logit_pipe():
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(C=0.5, max_iter=1000, random_state=SEED)),
    ])


def _make_gbm_reg():
    return HistGradientBoostingRegressor(
        max_depth=3, max_iter=150, learning_rate=0.05, l2_regularization=1.0,
        min_samples_leaf=200, random_state=SEED)


def _make_gbm_clf():
    return HistGradientBoostingClassifier(
        max_depth=3, max_iter=150, learning_rate=0.05, l2_regularization=1.0,
        min_samples_leaf=200, random_state=SEED)


def _degenerate_safe_cols(Xtr: np.ndarray, feat_cols: list) -> list:
    """sklearn's HistGradientBoosting binner crashes (sliding_window_view ValueError)
    on any column with <2 distinct non-missing values in the TRAINING fold (e.g. a
    forward-growth feature that is 100% NaN in the earliest folds, before that data
    series starts). [INFERENCE, disclosed]: rather than patch sklearn, drop such
    columns from THIS fold's fit/predict pair only -- documented per-fold in fold_log,
    not silently. Returns the surviving column INDICES (not names)."""
    keep = []
    for j in range(Xtr.shape[1]):
        col = Xtr[:, j]
        col = col[~np.isnan(col)]
        if len(np.unique(col)) >= 2:
            keep.append(j)
    return keep


def walk_forward_oos(df: pd.DataFrame, horizon: str, feat_cols: list) -> dict:
    """Returns dict of model_name -> DataFrame[date,symbol,y_true,y_true_reg,pred_reg,
    pred_proba] pooled across all walk-forward test folds (strict OOS -- a row is
    predicted only by a model trained on dates outside its purge+embargo window)."""
    raw_col = f"fwd_ret_{horizon}_raw"
    sub = df.dropna(subset=[raw_col]).copy()
    sub["y_up"] = (sub[raw_col] > 0).astype(int)

    dates = sorted(sub["date"].unique())
    splits = harness.purged_walk_forward_splits(dates, horizon, n_splits=5)
    log(f"  [{horizon}] {len(dates)} candidate dates -> {len(splits)} purged walk-forward folds "
        f"(embargo={harness.HORIZON_PERIODS[horizon]} periods)")

    rows = {"betaonly": [], "ridge": [], "gbm": [], "gbm_clf": [], "logit": []}
    fold_log = []
    for i, sp in enumerate(splits):
        train = sub[sub["date"].isin(sp["train"])]
        test = sub[sub["date"].isin(sp["test"])]
        if len(train) < 200 or len(test) < 20:
            continue
        fold_log.append({"fold": i, "n_train": int(len(train)), "n_test": int(len(test)),
                          "train_dates": [str(pd.Timestamp(d).date()) for d in sp["train"][:1]] +
                                         (["..."] if len(sp["train"]) > 2 else []) +
                                         [str(pd.Timestamp(d).date()) for d in sp["train"][-1:]],
                          "test_dates": [str(pd.Timestamp(d).date()) for d in sp["test"]]})

        Xtr_full = train[feat_cols].values
        Xte_full = test[feat_cols].values
        Xtr_beta = train[BETA_ONLY_FEATS].values
        Xte_beta = test[BETA_ONLY_FEATS].values
        ytr_reg = train[raw_col].values
        ytr_up = train["y_up"].values

        # GBM-safe column subsets (drop degenerate <2-distinct-value columns per
        # fold -- see _degenerate_safe_cols docstring). Ridge/logit keep full
        # feat_cols (SimpleImputer+StandardScaler handle a zero-variance column
        # gracefully, no crash).
        keep_full = _degenerate_safe_cols(Xtr_full, feat_cols)
        keep_beta = _degenerate_safe_cols(Xtr_beta, BETA_ONLY_FEATS)
        dropped_full = [feat_cols[j] for j in range(len(feat_cols)) if j not in keep_full]
        if dropped_full:
            fold_log[-1]["gbm_cols_dropped_degenerate"] = dropped_full

        # beta-only GBM (isolates pure market/beta-regime predictability)
        m_beta = _make_gbm_reg()
        m_beta.fit(Xtr_beta[:, keep_beta], ytr_reg)
        pred_beta = m_beta.predict(Xte_beta[:, keep_beta])

        # Ridge (linear baseline -- FACTOR_LIBRARY rule: must be checked first)
        m_ridge = _make_ridge_pipe()
        m_ridge.fit(Xtr_full, ytr_reg)
        pred_ridge = m_ridge.predict(Xte_full)

        # GBM full (main ML variant)
        m_gbm = _make_gbm_reg()
        m_gbm.fit(Xtr_full[:, keep_full], ytr_reg)
        pred_gbm = m_gbm.predict(Xte_full[:, keep_full])

        # classification P(up): logit baseline + GBM classifier
        m_logit = _make_logit_pipe()
        m_logit.fit(Xtr_full, ytr_up)
        proba_logit = m_logit.predict_proba(Xte_full)[:, 1]

        m_gbmclf = _make_gbm_clf()
        m_gbmclf.fit(Xtr_full[:, keep_full], ytr_up)
        proba_gbm = m_gbmclf.predict_proba(Xte_full[:, keep_full])[:, 1]

        base = test[["date", "symbol", raw_col, "y_up"]].reset_index(drop=True)
        rows["betaonly"].append(base.assign(pred=pred_beta))
        rows["ridge"].append(base.assign(pred=pred_ridge))
        rows["gbm"].append(base.assign(pred=pred_gbm))
        rows["logit"].append(base.assign(pred=proba_logit))
        rows["gbm_clf"].append(base.assign(pred=proba_gbm))

    out = {k: (pd.concat(v, ignore_index=True) if v else pd.DataFrame()) for k, v in rows.items()}
    out["_fold_log"] = fold_log
    out["_n_dates"] = len(dates)
    out["_n_folds_used"] = len(fold_log)
    return out


# ==========================================================================
# 3. Metrics: pooled R^2, pooled IC, date-avg cross-sectional IC, AUC, calibration
# ==========================================================================
def reg_metrics(pred_df: pd.DataFrame, raw_col: str) -> dict:
    if pred_df.empty:
        return {"status": "NO_OOS_ROWS"}
    y = pred_df[raw_col].values
    p = pred_df["pred"].values
    ss_res = np.sum((y - p) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    pooled_ic, _ = stats.spearmanr(p, y)
    # date-averaged cross-sectional IC (nets out common market-return-per-date component)
    by_date = pred_df.groupby("date").apply(
        lambda g: stats.spearmanr(g["pred"], g[raw_col])[0] if len(g) >= MIN_NAMES_PER_DATE else np.nan,
        include_groups=False)
    xs_ic_mean = float(by_date.dropna().mean()) if by_date.notna().any() else float("nan")
    xs_ic_ir = float(by_date.dropna().mean() / by_date.dropna().std(ddof=1)) if by_date.dropna().shape[0] > 1 else float("nan")
    return {
        "n_obs": int(len(pred_df)), "n_dates": int(pred_df["date"].nunique()),
        "pooled_r2": r2, "pooled_ic_spearman": float(pooled_ic),
        "xsec_ic_mean_dateavg": xs_ic_mean, "xsec_ic_ir_dateavg": xs_ic_ir,
        "n_dates_with_xsec_ic": int(by_date.notna().sum()),
    }


def clf_metrics(pred_df: pd.DataFrame) -> dict:
    if pred_df.empty or pred_df["y_up"].nunique() < 2:
        return {"status": "NO_OOS_ROWS_OR_SINGLE_CLASS"}
    y = pred_df["y_up"].values
    p = pred_df["pred"].values
    auc = float(roc_auc_score(y, p))
    brier_raw = float(brier_score_loss(y, p))
    # reliability curve: decile bins of predicted proba -> actual hit rate
    dfc = pred_df.copy()
    dfc["bin"] = pd.qcut(dfc["pred"].rank(method="first"), 10, labels=False, duplicates="drop")
    rel = dfc.groupby("bin").agg(pred_mean=("pred", "mean"), actual_rate=("y_up", "mean"), n=("y_up", "size"))
    # isotonic recalibration -- NOTE: fit on the SAME pooled OOS pool (disclosed limitation,
    # not a fresh held-out set -- see honesty note in the markdown report).
    from sklearn.isotonic import IsotonicRegression
    iso = IsotonicRegression(out_of_bounds="clip")
    p_cal = iso.fit_transform(p, y)
    brier_cal = float(brier_score_loss(y, p_cal))
    return {
        "n_obs": int(len(pred_df)), "base_rate_up": float(y.mean()),
        "auc_raw": auc, "brier_raw": brier_raw, "brier_isotonic_recal_SAME_POOL": brier_cal,
        "reliability_curve_deciles": rel.reset_index().to_dict(orient="records"),
    }


# ==========================================================================
# 4. main
# ==========================================================================
def main():
    df = build_feature_panel()
    results = {}
    for h in HORIZONS:
        log(f"\n=== HORIZON {h} ===")
        raw_col = f"fwd_ret_{h}_raw"
        oos = walk_forward_oos(df, h, FULL_FEATS)
        if oos["_n_folds_used"] == 0:
            results[h] = {"status": "NO_USABLE_FOLDS", "n_dates": oos["_n_dates"]}
            log(f"  [{h}] NO USABLE FOLDS -- skipping")
            continue

        h_res = {"n_dates_candidate": oos["_n_dates"], "n_folds_used": oos["_n_folds_used"],
                  "fold_log": oos["_fold_log"]}

        # ---- regression: beta-only / ridge / gbm ----
        for name in ("betaonly", "ridge", "gbm"):
            pdf = oos[name]
            m = reg_metrics(pdf, raw_col)
            h_res[f"reg_{name}"] = m
            log(f"  [{h}] reg/{name}: {m}")

            # feed OOS predictions through the SAME harness anti-overfit battery
            # every rule factor in this repo goes through (return_basis='raw' since
            # target is the absolute forward return, not resid/excess).
            if not pdf.empty:
                factor_series = pdf.set_index(["date", "symbol"])["pred"]
                card = harness.evaluate(
                    factor_series, horizon=h, return_basis="raw",
                    factor_id=f"W6AM_{name}_{h}", family="W6AM",
                    panel=df, panel_source="real",
                    min_names_per_date=MIN_NAMES_PER_DATE,
                    cards_dir=CARDS_DIR)
                h_res[f"harness_card_{name}"] = {
                    k: card.get(k) for k in
                    ("status", "n_obs", "n_dates", "ic", "deciles", "long_short", "costs", "dsr", "pbo",
                     "lag_test", "placebo", "verdict")
                }
                log(f"  [{h}] harness verdict/{name}: {card.get('verdict')}")

        # ---- classification: logit / gbm_clf ----
        for name in ("logit", "gbm_clf"):
            pdf = oos[name]
            m = clf_metrics(pdf)
            h_res[f"clf_{name}"] = m
            log(f"  [{h}] clf/{name}: AUC={m.get('auc_raw')}, brier_raw={m.get('brier_raw')}, "
                f"brier_iso={m.get('brier_isotonic_recal_SAME_POOL')}")

        results[h] = h_res

    OUT_JSON.write_text(json.dumps(harness._to_native(results), indent=2), encoding="utf-8")
    log(f"\nWrote {OUT_JSON}")


if __name__ == "__main__":
    main()
