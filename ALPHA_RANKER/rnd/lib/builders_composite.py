"""
WAVE-2 ALPHA_RANKER composite: rank-average of 4 orthogonal winners.
Owner: quant-head-arjun-rao review pass on a WAVE-2 worker build.

Legs (all REUSED from existing, already-registered builders -- no redefinition,
per RESEARCH_PROTOCOL.md S0.1 "no post-hoc redefinition"):
  trend   = dma_stack_factor(65)            (builders_ma.py,   H001 65DMA-stack, 0-3 ordinal)
  mom     = build_mom_sharpe_12m            (builders_mom.py,  H004 vol-scaled 12m momentum)
  value   = build_H014_earnings_yield       (builders_value.py, H014 EPS/price)
  quality = build_gross_profitability_factor (builders_quality.py, H021 op.profit/assets)

Method: cross-sectional PERCENTILE RANK each leg independently per date (so no
leg's raw scale/outliers dominate), then a weighted average of the 4 ranks.
Default weights are EQUAL (0.25 each) -- this is the "prior" / baseline. A
second constructor supports arbitrary weights for the "recommended weights"
variant this worker's report tests.

Turnover-controlled variant: a name's composite score only UPDATES if its
newly-computed rank-average moves outside a no-trade BAND around its own
previous-period value; otherwise the prior period's score is carried forward
(reduces flip-flopping on marginal rank changes -> fewer round-trips ->
lower cost drag). This is a per-name hysteresis filter applied AFTER the
score is computed, not a redefinition of any leg.

IMPORTANT DISCLOSED FINDING (do not silently drop): H021 gross-profitability,
evaluated standalone via the harness (cards/H021_grossprof.json, 1Y resid),
has ic_ir = -0.82 (strongly NEGATIVE, monotonicity -0.93), with a CLEAN lag
test (0.038) and CLEAN placebo (0.0003) -- i.e. this is a real, PIT-safe
cross-sectional relationship in this data, just with the ECONOMICALLY WRONG
SIGN relative to the Novy-Marx prior. The module docstring of
builders_quality.py already discloses the GP/A proxy is contaminated (op.profit
substitutes for Revenue-COGS because there is no COGS breakout, so it sits
closer to an EBITDA-margin scale than true gross profitability). Per firm
epistemic conduct, this factor's sign is NOT flipped to force it to "work"
(that would be HARKing on an in-sample sign). Instead this module exposes an
explicit `legs=(...)` argument so the composite can be evaluated WITH and
WITHOUT the quality leg, honestly, and the calling report says which is real.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent))

from builders_ma import dma_stack_factor          # noqa: E402
from builders_mom import build_mom_sharpe_12m     # noqa: E402
from builders_value import build_H014_earnings_yield        # noqa: E402
from builders_quality import build_gross_profitability_factor  # noqa: E402

LEG_BUILDERS = {
    "trend":   lambda panel: dma_stack_factor(65)(panel),
    "mom":     build_mom_sharpe_12m,
    "value":   build_H014_earnings_yield,
    "quality": build_gross_profitability_factor,
}

DEFAULT_LEGS = ("trend", "mom", "value", "quality")


def build_legs(panel: pd.DataFrame, legs: tuple = DEFAULT_LEGS) -> pd.DataFrame:
    """Returns a wide (date,symbol)-indexed frame, one column per requested leg,
    INNER-joined (a name must have all requested legs on a given date to be
    scored -- no silent fill)."""
    frames = []
    for name in legs:
        s = LEG_BUILDERS[name](panel).rename(name)
        frames.append(s)
    out = pd.concat(frames, axis=1, join="inner").dropna()
    return out


def leg_correlation_matrix(panel: pd.DataFrame, legs: tuple = DEFAULT_LEGS) -> pd.DataFrame:
    """Per-date Spearman rank correlation among legs, averaged across dates
    (RP-17 orthogonality check) -- more honest than a single pooled correlation
    since it doesn't let one big date panel dominate."""
    wide = build_legs(panel, legs)
    corrs = []
    for _, g in wide.groupby(level="date"):
        if len(g) < 20:
            continue
        corrs.append(g.corr(method="spearman"))
    if not corrs:
        return pd.DataFrame(index=legs, columns=legs, dtype=float)
    return sum(corrs) / len(corrs)


def _pct_rank_by_date(wide: pd.DataFrame) -> pd.DataFrame:
    return wide.groupby(level="date").rank(pct=True)


def build_rank_average_composite(panel: pd.DataFrame, legs: tuple = DEFAULT_LEGS,
                                  weights: dict = None) -> pd.Series:
    """Weighted average of per-date percentile ranks. weights=None -> equal
    weight (the 'prior' baseline named in the task). weights dict values need
    not sum to 1 (renormalized internally)."""
    wide = build_legs(panel, legs)
    ranks = _pct_rank_by_date(wide)
    if weights is None:
        w = pd.Series(1.0, index=legs)
    else:
        w = pd.Series({k: weights.get(k, 0.0) for k in legs})
    w = w / w.sum()
    combo = (ranks * w).sum(axis=1)
    combo.name = "factor"
    return combo


def build_turnover_controlled_composite(panel: pd.DataFrame, legs: tuple = DEFAULT_LEGS,
                                         weights: dict = None, band: float = 0.15) -> pd.Series:
    """Same rank-average score, then a per-name hysteresis filter across the
    panel's own chronological date sequence: a name's OUTPUT score only moves
    to its newly-computed value if it has drifted more than `band` (in
    percentile-rank units, 0-1 scale) from the name's last OUTPUT value;
    otherwise the previous period's output is carried forward unchanged (no
    lookahead -- only ever uses this-name's own past output + this period's
    freshly computed score, both already PIT-safe)."""
    raw = build_rank_average_composite(panel, legs, weights)
    df = raw.reset_index()
    df.columns = ["date", "symbol", "raw"]
    df = df.sort_values(["symbol", "date"])

    def _hysteresis(g: pd.DataFrame) -> pd.Series:
        out = g["raw"].values.copy()
        last = out[0]
        for i in range(1, len(out)):
            if abs(out[i] - last) > band:
                last = out[i]
            else:
                out[i] = last
        return pd.Series(out, index=g.index)

    df["out"] = df.groupby("symbol", group_keys=False).apply(_hysteresis, include_groups=False)
    df = df.set_index(["date", "symbol"])["out"].rename("factor")
    return df


# Convenience named builders for run_experiment() one-liners --------------
def build_COMPO_eqw4(panel: pd.DataFrame) -> pd.Series:
    return build_rank_average_composite(panel, DEFAULT_LEGS, weights=None)


def build_COMPO_eqw3_ex_quality(panel: pd.DataFrame) -> pd.Series:
    return build_rank_average_composite(panel, ("trend", "mom", "value"), weights=None)


def build_COMPO_turnover_band(panel: pd.DataFrame) -> pd.Series:
    return build_turnover_controlled_composite(panel, DEFAULT_LEGS, weights=None, band=0.15)


def build_COMPO_turnover_band_ex_quality(panel: pd.DataFrame) -> pd.Series:
    return build_turnover_controlled_composite(panel, ("trend", "mom", "value"), weights=None, band=0.15)
