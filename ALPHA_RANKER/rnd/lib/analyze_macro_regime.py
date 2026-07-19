"""
Money-first test: does the macro regime (rnd/panel/macro_state.parquet) CONDITION
forward NIFTY 500 market returns (1M/1Y)? Not a cross-sectional harness.evaluate()
run (macro has no cross-sectional variation) -- a time-series bucket-conditioning
test with the hard gates the task specifies: lag-robustness + placebo-shuffle.
PBO is not meaningful for a single macro time series in this form (advisory-skip,
disclosed, not silently omitted).

Regime buckets themselves are already causal (trailing 3M changes / expanding
tercile bands built in macro_state.py using only data <= t) -- no look-ahead in
the FEATURE. This script only tests whether that causal feature conditions the
already-causal forward-return target.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
CARDS_DIR = RND_DIR / "cards"

MACRO_FP = RND_DIR / "panel" / "macro_state.parquet"

REGIME_COLS = ["rate_regime", "risk_regime", "inr_regime"]
HORIZONS = ["1M", "1Y"]


def _bucket_spread(df: pd.DataFrame, regime_col: str, target_col: str) -> dict:
    g = df.dropna(subset=[regime_col, target_col]).groupby(regime_col)[target_col]
    means = g.mean()
    counts = g.count()
    if len(means) < 2:
        return {"spread": np.nan, "means": {}, "counts": {}}
    hi_bucket, lo_bucket = means.idxmax(), means.idxmin()
    spread = means[hi_bucket] - means[lo_bucket]
    return {
        "spread": float(spread),
        "hi_bucket": hi_bucket, "lo_bucket": lo_bucket,
        "means": {k: float(v) for k, v in means.items()},
        "counts": {k: int(v) for k, v in counts.items()},
    }


def _lag_test(df: pd.DataFrame, regime_col: str, target_col: str, orig_spread: float) -> dict:
    """Shift the regime label back one further month (regime known at t-1 used
    against fwd return measured from t) -- robustness check per task's hard-gate
    spec, distinct from (and in addition to) the already-causal construction."""
    shifted = df.copy()
    shifted[regime_col] = shifted[regime_col].shift(1)
    res = _bucket_spread(shifted, regime_col, target_col)
    lag_spread = res["spread"]
    if orig_spread == 0 or pd.isna(orig_spread) or pd.isna(lag_spread):
        delta = np.nan
    else:
        delta = abs(lag_spread - orig_spread) / abs(orig_spread)
    return {"lag_spread": lag_spread, "lag_test_delta": delta}


def _placebo(df: pd.DataFrame, regime_col: str, target_col: str, n_shuffles: int = 200, seed: int = 42) -> dict:
    """Shuffle the regime label across dates (breaks time alignment) and
    recompute the spread -- should collapse toward 0 if the original effect is
    real and not a labeling artifact."""
    rng = np.random.default_rng(seed)
    sub = df.dropna(subset=[regime_col, target_col]).copy()
    spreads = []
    vals = np.array(sub[regime_col].tolist(), dtype=object)
    for _ in range(n_shuffles):
        rng.shuffle(vals)
        sub["_shuf"] = vals
        r = _bucket_spread(sub, "_shuf", target_col)
        if not pd.isna(r["spread"]):
            spreads.append(r["spread"])
    orig_spread = df.dropna(subset=[regime_col, target_col]).pipe(
        lambda d: _bucket_spread(d, regime_col, target_col)["spread"])
    p_value = (float(np.mean(np.array(spreads) >= orig_spread)) if spreads else np.nan)
    return {"placebo_spread_mean": float(np.mean(spreads)) if spreads else np.nan,
            "placebo_spread_std": float(np.std(spreads)) if spreads else np.nan,
            "placebo_p_value_one_sided": p_value,
            "n_shuffles": len(spreads)}


def run() -> list[dict]:
    df = pd.read_parquet(MACRO_FP)
    cards = []
    for horizon in HORIZONS:
        target_col = f"fwd_ret_nifty500_{horizon}"
        for regime_col in REGIME_COLS:
            orig = _bucket_spread(df, regime_col, target_col)
            if pd.isna(orig["spread"]):
                continue
            lag = _lag_test(df, regime_col, target_col, orig["spread"])
            placebo = _placebo(df, regime_col, target_col)

            lag_delta = lag["lag_test_delta"]
            p_val = placebo["placebo_p_value_one_sided"]
            placebo_ok = (not pd.isna(p_val)) and p_val < 0.10
            lag_ok = (not pd.isna(lag_delta)) and lag_delta < 1.0  # spread should not flip/explode
            n_obs = sum(orig["counts"].values())

            if n_obs < 20:
                verdict = "PARK (n too small, <20 month-obs)"
            elif not lag_ok:
                verdict = "KILL (fails lag-robustness gate)"
            elif not placebo_ok:
                verdict = "KILL (fails placebo gate -- spread not distinguishable from shuffled-label noise)"
            else:
                verdict = "PARK (passes hard gates; PBO not computed -- advisory-skip for single macro series; small n, regime-conditioning signal only, not a tradeable factor by itself)"

            card = {
                "id": f"W2_macro_{regime_col}_{horizon}",
                "family": "W2_macro",
                "regime_col": regime_col,
                "target": target_col,
                "n_obs": n_obs,
                "bucket_means": orig["means"],
                "bucket_counts": orig["counts"],
                "spread_hi_minus_lo": orig["spread"],
                "hi_bucket": orig.get("hi_bucket"), "lo_bucket": orig.get("lo_bucket"),
                "lag_test": lag,
                "placebo": placebo,
                "gates": {"lag_ok": lag_ok, "placebo_ok": placebo_ok},
                "pbo": "not computed -- advisory-skip, single macro time series (n=1 candidate, CSCV needs competing variants), disclosed not silent",
                "verdict": verdict,
            }
            cards.append(card)
            (CARDS_DIR / f"W2_macro_{regime_col}_{horizon}.json").write_text(
                json.dumps(card, indent=2, default=str))
    return cards


if __name__ == "__main__":
    cards = run()
    for c in cards:
        print(c["id"], "| spread(hi-lo)=%.4f" % c["spread_hi_minus_lo"],
              "| lag_delta=%.3f" % c["lag_test"]["lag_test_delta"],
              "| placebo_p=%.3f" % c["placebo"]["placebo_p_value_one_sided"],
              "|", c["verdict"])
