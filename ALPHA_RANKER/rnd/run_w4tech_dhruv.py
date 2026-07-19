"""
WAVE-4 TECHNICAL PATTERNS (2026-07-17) -- Dhruv Kapoor (Technical Head), task from
CIO/RND. Principal's frame: chart/technical patterns are tested as a CONFIRMATION/
TIMING overlay on the frozen 7-leg composite, NOT as standalone alpha -- prior art
(KILLED.md, FRAMEWORK_CATALOG.md PRIOR-ART table) already killed ADX-entry,
Weinstein stage-2, mean-reversion-entry and ORB as standalone vehicles; only
MA-65 slope (trend, already IN the 7-leg composite) and ATR-exits survived.
Test protocol per pattern, mechanically coded (no discretionary fitting):
  (a) standalone harness.evaluate() at 1Y/resid on panel_long.parquet
  (b) CLUBBED test: among top-quintile canonical_7leg composite-score names each
      month, does the pattern being present/high improve forward return vs the
      composite alone (same top-quintile, pattern absent/low)?
  (c) ERA-SPLIT pre/post-2015 IC, cap-segment note.

HARD DATA LANDMINE (disclosed up front, not discovered mid-analysis and buried):
cube_volume.parquet (and data/prices/*.parquet Volume column) starts 2021-07-16,
NOT 2005 -- there is NO daily volume history pre-2015 in this repo. Any pattern
whose definition requires volume (VCP, volume-profile approximation) can ONLY be
tested 2021-2025 -- entirely the POST-2015 "manipulation era" by the Principal's
own framing. This means the era-split question ("does it survive into the
manipulation era, or only work in old low-float small-caps") is STRUCTURALLY
UNANSWERABLE for volume-dependent patterns with current data -- reported as a
gap, not silently worked around. Price-only patterns (breakout+retest,
down-channel breakout, flag, efficiency-ratio/chop) use cube_close_long
(2005-2025) and get a real era split.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
CUBE_CLOSE_LONG = RND_DIR / "panel" / "cube_close_long.parquet"
CUBE_VOLUME = RND_DIR / "panel" / "cube_volume.parquet"
CANON_PATH = RND_DIR / "panel" / "canonical_7leg_scores.parquet"
CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "reports"
WAVE4_DIR = RND_DIR / "wave4"
HORIZON = "1Y"
LBL_RAW = "fwd_ret_1Y_raw"
LBL_RESID = "fwd_ret_1Y_resid"
DISC_COL = "disc_event_in_window_1Y"
ERA_CUTOFF = pd.Timestamp("2015-01-01")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 0. load
# ---------------------------------------------------------------------------
def load_all():
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    close = pd.read_parquet(CUBE_CLOSE_LONG)
    close.index = pd.to_datetime(close.index)
    volume = pd.read_parquet(CUBE_VOLUME)
    volume.index = pd.to_datetime(volume.index)
    canon = pd.read_parquet(CANON_PATH)
    canon["date"] = pd.to_datetime(canon["date"])
    return panel, close, volume, canon


def panel_dates(panel):
    return pd.DatetimeIndex(sorted(panel["date"].unique()))


def to_long_factor(wide: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.Series:
    sub = wide.reindex(dates)
    f = sub.stack()
    f.index.names = ["date", "symbol"]
    return f.rename("factor")


# ---------------------------------------------------------------------------
# 1. pattern builders -- price-only, full 2005-2025 history (cube_close_long)
# ---------------------------------------------------------------------------
def build_breakout_retest(close: pd.DataFrame, dates) -> pd.Series:
    """N-day-high breakout, then a pullback that HOLDS above the broken level.
    Mechanical proxy (disclosed [INFERENCE]): rather than verifying the actual
    intraday low touched the level (not available at daily-cube grain without
    a per-symbol loop), we require: (1) a 50d-high breakout occurred 5-20
    trading days ago, (2) current close is 0-8% above that breakout level
    (near it, holding above, not runaway)."""
    h50 = close.rolling(50, min_periods=40).max()
    level = h50.shift(1)
    is_breakout = close > level
    idx = pd.Series(np.arange(len(close)), index=close.index, dtype=float)
    pos_break = pd.DataFrame(np.where(is_breakout, idx.values[:, None], np.nan),
                              index=close.index, columns=close.columns)
    last_break_pos = pos_break.ffill()
    level_break = level.where(is_breakout).ffill()
    days_since = pd.DataFrame(idx.values[:, None] - last_break_pos.values,
                               index=close.index, columns=close.columns)
    ratio = close.div(level_break)
    flag = (days_since >= 5) & (days_since <= 20) & (ratio >= 1.0) & (ratio <= 1.08)
    return to_long_factor(flag.astype(float), dates)


def build_downchannel_breakout(close: pd.DataFrame, dates) -> pd.Series:
    """Linear-channel fit over trailing 120d; flag a break above the upper
    channel band when the trailing channel itself was DOWN-sloping.
    [INFERENCE]: channel width proxied by rolling std of price levels (not a
    true OLS-residual std, which needs a per-window regression) -- disclosed
    approximation, directionally the same idea (dispersion around trend)."""
    n = 120
    t = pd.Series(np.arange(len(close)), index=close.index, dtype=float)
    cov = close.rolling(n, min_periods=100).cov(t)
    var_t = t.rolling(n, min_periods=100).var()
    slope = cov.div(var_t, axis=0)
    mean_close = close.rolling(n, min_periods=100).mean()
    fitted_now = mean_close + slope.mul((n - 1) / 2.0)
    width = close.rolling(n, min_periods=100).std()
    upper = fitted_now + 1.5 * width
    flag = (slope.shift(1) < 0) & (close > upper.shift(1))
    return to_long_factor(flag.astype(float), dates)


def build_flag(close: pd.DataFrame, dates) -> pd.Series:
    """Sharp thrust (>=15% over a 20d window ending 15d ago) -> low-vol
    consolidation (trailing 15d vol < half the thrust window's vol) ->
    continuation breakout above the consolidation range high."""
    thrust_ret = close.shift(15) / close.shift(35) - 1.0
    ret = close.pct_change()
    consolidation_vol = ret.rolling(15, min_periods=10).std()
    thrust_vol = ret.rolling(20, min_periods=15).std().shift(15)
    vol_contraction = consolidation_vol < 0.5 * thrust_vol
    cont_breakout = close > close.rolling(15, min_periods=10).max().shift(1)
    flag = (thrust_ret > 0.15) & vol_contraction & cont_breakout
    return to_long_factor(flag.astype(float), dates)


def build_efficiency_ratio(close: pd.DataFrame, dates, n: int = 20) -> pd.Series:
    """Kaufman efficiency ratio: |net change| / sum(|daily changes|) over n
    days. High = trending, low = choppy/range. Built as a NEGATIVE FILTER
    (per task), not expected to carry standalone directional IC -- tested
    below as a clubbing gate, not a scored factor."""
    net = (close - close.shift(n)).abs()
    path = close.diff().abs().rolling(n, min_periods=int(n * 0.75)).sum()
    er = net / path
    return to_long_factor(er, dates)


# ---------------------------------------------------------------------------
# 2. pattern builders -- volume-dependent, ONLY 2021-2025 (cube_volume floor)
# ---------------------------------------------------------------------------
def build_vcp(close: pd.DataFrame, volume: pd.DataFrame, dates) -> pd.Series:
    """Volatility contraction pattern: vol-of-returns contracting (21d/63d
    ratio < 0.7) AND volume drying up (21d/63d avg volume ratio < 0.7),
    followed within the next 10 sessions by a breakout above the trailing 20d
    high on >=1.3x volume expansion. Binary flag = 1 if any such VCP-breakout
    day occurred in the trailing 10 sessions ending at t."""
    common = close.columns.intersection(volume.columns)
    c = close.reindex(volume.index)[common]
    v = volume[common]
    ret = c.pct_change()
    vol21 = ret.rolling(21, min_periods=15).std()
    vol63 = ret.rolling(63, min_periods=45).std()
    contraction = (vol21 / vol63) < 0.7
    avgvol21 = v.rolling(21, min_periods=15).mean()
    avgvol63 = v.rolling(63, min_periods=45).mean()
    dryup = (avgvol21 / avgvol63) < 0.7
    high20 = c.rolling(20, min_periods=20).max()
    breakout = c > high20.shift(1)
    vol_expansion = v > 1.3 * avgvol21.shift(1)
    vcp_day = contraction.shift(1) & dryup.shift(1) & breakout & vol_expansion
    vcp_flag = vcp_day.rolling(10, min_periods=1).max()
    return to_long_factor(vcp_flag.astype(float), dates)


def build_volprofile_approx(close: pd.DataFrame, volume: pd.DataFrame, dates) -> pd.Series:
    """Volume-profile APPROXIMATION -- disclosed: we have daily Close+Volume,
    not tick/intraday price-at-volume, so a true histogram POC/value-area
    cannot be built. Proxy: 60d volume-weighted-average-price (VWAP) stands
    in for the point-of-control; distance of current close from VWAP,
    z-scored by 60d close-price dispersion, stands in for position vs the
    value area. NOT a real volume profile -- an honest, cheap substitute."""
    common = close.columns.intersection(volume.columns)
    c = close.reindex(volume.index)[common]
    v = volume[common]
    pv = (c * v).rolling(60, min_periods=40).sum()
    vsum = v.rolling(60, min_periods=40).sum()
    vwap60 = pv / vsum
    disp60 = c.rolling(60, min_periods=40).std()
    factor = (c - vwap60) / disp60.replace(0, np.nan)
    return to_long_factor(factor, dates)


# ---------------------------------------------------------------------------
# 3. clubbing test: does the pattern add value ON TOP OF a strong 7-leg score?
# ---------------------------------------------------------------------------
def clubbing_test(pattern: pd.Series, canon: pd.DataFrame, panel: pd.DataFrame,
                   binary: bool = True, quintile_pattern: bool = False) -> dict:
    """Among names in the TOP QUINTILE of composite_rank_avg each month
    (restricted to (date,symbol) where the pattern is actually computable --
    an honest inner join, never fillna(0)-padded), compare forward return
    (fwd_ret_1Y_raw, disc-guarded) for pattern-present vs pattern-absent
    (binary patterns) or top-vs-bottom-tercile-of-pattern (continuous
    patterns, e.g. efficiency ratio / volume-profile z-score)."""
    p2 = panel.copy()
    mask = p2[DISC_COL].fillna(0) > 0
    p2.loc[mask, LBL_RAW] = np.nan
    tgt = p2[["date", "symbol", LBL_RAW]].dropna()

    c = canon.copy()
    c["top_quintile"] = c.groupby("date")["composite_rank_avg"].rank(pct=True) >= 0.8

    pat = pattern.rename("pattern").reset_index()
    m = c.merge(pat, on=["date", "symbol"], how="inner").merge(tgt, on=["date", "symbol"], how="inner")
    m = m[m["top_quintile"]]
    if m.empty:
        return {"status": "NO_OVERLAP", "n": 0}

    if binary:
        grp_hi = m[m["pattern"] >= 0.5]
        grp_lo = m[m["pattern"] < 0.5]
    else:
        m["pat_pct"] = m.groupby("date")["pattern"].rank(pct=True)
        grp_hi = m[m["pat_pct"] >= 0.67]
        grp_lo = m[m["pat_pct"] <= 0.33]

    def _stats(g):
        r = g[LBL_RAW].dropna()
        return {"mean": float(r.mean()) if len(r) else None, "median": float(r.median()) if len(r) else None,
                "n": int(len(r))}

    hi_s, lo_s = _stats(grp_hi), _stats(grp_lo)
    tstat = pval = None
    if hi_s["n"] >= 5 and lo_s["n"] >= 5:
        tt = stats.ttest_ind(grp_hi[LBL_RAW].dropna(), grp_lo[LBL_RAW].dropna(), equal_var=False)
        tstat, pval = float(tt.statistic), float(tt.pvalue)

    def _era(sub, lo_year_incl_hi):
        s = sub[sub["date"] < ERA_CUTOFF] if lo_year_incl_hi == "pre" else sub[sub["date"] >= ERA_CUTOFF]
        return _stats(s)

    era = {
        "pre2015_pattern_present": _era(grp_hi, "pre"), "pre2015_pattern_absent": _era(grp_lo, "pre"),
        "post2015_pattern_present": _era(grp_hi, "post"), "post2015_pattern_absent": _era(grp_lo, "post"),
    }
    return {
        "status": "OK", "n_total_topq_with_pattern_data": int(len(m)),
        "pattern_present_or_high": hi_s, "pattern_absent_or_low": lo_s,
        "delta_mean": (hi_s["mean"] - lo_s["mean"]) if (hi_s["mean"] is not None and lo_s["mean"] is not None) else None,
        "welch_t": tstat, "welch_p": pval,
        "date_min": str(m["date"].min()), "date_max": str(m["date"].max()),
        "n_dates": int(m["date"].nunique()),
        "era_split": era,
    }


def era_split_ic(factor: pd.Series, panel: pd.DataFrame, min_names: int = 20) -> dict:
    p2 = panel.copy()
    mask = p2[DISC_COL].fillna(0) > 0
    p2.loc[mask, LBL_RESID] = np.nan
    tgt = p2[["date", "symbol", LBL_RESID]].dropna()
    f = factor.rename("factor").reset_index()
    m = f.merge(tgt, on=["date", "symbol"], how="inner").dropna()
    if m.empty:
        return {"status": "NO_OVERLAP"}

    def _ic_by(sub):
        rows = []
        for d, g in sub.groupby("date"):
            if len(g) < min_names:
                continue
            rho, _ = stats.spearmanr(g["factor"], g[LBL_RESID])
            if rho == rho:
                rows.append(rho)
        return {"ic_mean": float(np.mean(rows)) if rows else None,
                "ic_ir": float(np.mean(rows) / np.std(rows, ddof=1)) if len(rows) > 1 and np.std(rows, ddof=1) > 0 else None,
                "n_dates": len(rows)}

    pre = m[m["date"] < ERA_CUTOFF]
    post = m[m["date"] >= ERA_CUTOFF]
    return {"status": "OK", "pre2015": _ic_by(pre), "post2015": _ic_by(post),
            "date_min": str(m["date"].min()), "date_max": str(m["date"].max())}


# ---------------------------------------------------------------------------
# 4. main
# ---------------------------------------------------------------------------
def eval_with_disc_guard(factor, panel, factor_id, family):
    p2 = panel.copy()
    mask = p2[DISC_COL].fillna(0) > 0
    p2.loc[mask, [LBL_RAW, LBL_RESID]] = np.nan
    return harness.evaluate(
        factor, HORIZON, return_basis="resid", factor_id=factor_id,
        panel=p2, panel_source="real_panel_long_technical_patterns",
        family=family, write_card=True, cards_dir=CARDS_DIR,
    )


def summarize(card: dict) -> dict:
    ic = card.get("ic", {})
    dec = card.get("deciles", {})
    return {"factor_id": card.get("factor_id"), "status": card.get("status"),
            "ic_mean": ic.get("ic_mean"), "ic_ir": ic.get("ic_ir"), "n_ic_dates": ic.get("n_ic_dates"),
            "mono": dec.get("monotonicity"), "lag_test_delta": card.get("lag_test", {}).get("lag_test_delta"),
            "placebo_ic": card.get("placebo", {}).get("placebo_ic"), "pbo": card.get("pbo", {}).get("pbo"),
            "dsr": card.get("dsr", {}).get("dsr"), "n_obs": card.get("n_obs"),
            "verdict": card.get("verdict")}


def main():
    log("Loading panel_long, cube_close_long, cube_volume, canonical_7leg_scores...")
    panel, close, volume, canon = load_all()
    dates = panel_dates(panel)
    log(f"panel_long: {panel.shape}, {panel['date'].nunique()} dates ({panel['date'].min()}..{panel['date'].max()})")
    log(f"cube_close_long: {close.shape} ({close.index.min()}..{close.index.max()})")
    log(f"cube_volume: {volume.shape} ({volume.index.min()}..{volume.index.max()}) -- HARD FLOOR, no pre-2015 volume")
    log(f"canonical_7leg_scores: {canon.shape}, {canon['date'].nunique()} dates")

    results = {}

    log("Building PRICE-ONLY patterns (full 2005-2025 history)...")
    factors_price = {
        "W4TECH_breakout_retest": (build_breakout_retest(close, dates), True),
        "W4TECH_downchannel_breakout": (build_downchannel_breakout(close, dates), True),
        "W4TECH_flag": (build_flag(close, dates), True),
        "W4TECH_efficiency_ratio": (build_efficiency_ratio(close, dates), False),
    }
    log("Building VOLUME-DEPENDENT patterns (2021-2025 ONLY -- cube_volume floor)...")
    factors_vol = {
        "W4TECH_vcp": (build_vcp(close, volume, dates), True),
        "W4TECH_volprofile_approx": (build_volprofile_approx(close, volume, dates), False),
    }

    all_factors = {**factors_price, **factors_vol}
    family_map = {k: "W4TECH" for k in all_factors}

    for fid, (factor, is_binary) in all_factors.items():
        n_obs = len(factor)
        n_dates_cov = factor.reset_index()["date"].nunique() if n_obs else 0
        log(f"Evaluating {fid} ({n_obs} obs, {n_dates_cov} dates, "
            f"range {factor.reset_index()['date'].min() if n_obs else None}..{factor.reset_index()['date'].max() if n_obs else None})...")
        card = eval_with_disc_guard(factor, panel, fid, family_map[fid])
        s = summarize(card)
        log(f"  standalone -> IC_IR={s['ic_ir']} mono={s['mono']} verdict={s['verdict']}")

        club = clubbing_test(factor, canon, panel, binary=is_binary)
        log(f"  clubbed -> delta_mean={club.get('delta_mean')} welch_t={club.get('welch_t')} "
            f"welch_p={club.get('welch_p')} n={club.get('n_total_topq_with_pattern_data')}")

        era = era_split_ic(factor, panel)
        log(f"  era -> pre2015 IC_ir={era.get('pre2015', {}).get('ic_ir')} "
            f"post2015 IC_ir={era.get('post2015', {}).get('ic_ir')}")

        results[fid] = {"standalone": s, "clubbed": club, "era_split": era,
                         "n_obs": n_obs, "n_dates_covered": n_dates_cov,
                         "date_min": str(factor.reset_index()["date"].min()) if n_obs else None,
                         "date_max": str(factor.reset_index()["date"].max()) if n_obs else None,
                         "volume_dependent": fid in factors_vol}

    out_json = REPORTS_DIR / "W4TECH_patterns_results.json"
    out_json.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    log(f"Wrote {out_json}")

    print("\n" + "=" * 110)
    for fid, r in results.items():
        s = r["standalone"]
        print(f"{fid:35s} IC_IR={str(s['ic_ir']):>8s}  mono={str(s['mono']):>6s}  verdict={s['verdict']}")
    print("=" * 110)


if __name__ == "__main__":
    main()
