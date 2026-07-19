"""
W5RG -- Regime-conditional MOMENTUM-HORIZON + selective MEAN-REVERSION test.
Owner: Arjun Rao (Quant Head), 2026-07-17. ALPHA_RANKER.

Task (Principal, via CIO office): test whether the best momentum LOOKBACK
(3m / 6m / 12m skip-month) differs by market regime (booming-expanding-PE
bull / normal-choppy / bear-oversold), and whether short-term reversal --
KILLED unconditionally in this codebase (H034_rev5d_1M_resid: verdict KILL,
lag_test_delta 0.992, PBO 0.978 -- see rnd/cards/H034_rev5d_1M_resid.json)
-- comes back to life SELECTIVELY when breadth is oversold-extreme. Also a
low-expectation regime cut of PEAD (dead unconditionally, W3_pead_eventtime:
IC -0.003).

NO LOOKAHEAD, by construction:
  - Regime classification at date t uses ONLY data with timestamp <= t:
    expanding-window percentile ranks (min_periods=24 months, i.e. first 2
    years are UNCLASSIFIED, not forced into a bucket) of breadth and trend
    efficiency; a trailing 3-month change in the (already-expanding,
    already-audited) richness index; sign of trailing 252-trading-day index
    return for trend direction. Nothing here looks at t+1 or beyond to label
    date t.
  - Momentum/reversal FACTORS at date t use price data with index position
    <= loc(t) only (skip-month momentum explicitly excludes the most recent
    21 trading days from the "return" numerator's start, per standard
    Jegadeesh-Titman construction, but the DATA used is still all <= t).
  - Forward target (fwd_ret_1M) uses price data at t+21 trading days --
    that is the point (it is the thing being predicted), never used to
    build the signal itself.
  - PEAD reuses the already PIT-audited builders_w2_event.load_quarterly_pit()
    (available_date-gated) and the same event-window construction as
    rnd/lib/run_w3_pead_eventtime.py.

Data:
  rnd/panel/panel_long.parquet    -- monthly date grid (249 dates, 2005-04
                                      -> 2025-12), used ONLY for the date list.
  rnd/panel/cube_close_long.parquet -- daily close, 976 tickers, 2005-04-01
                                      -> 2025-12-05 -- momentum/reversal built
                                      FRESH from this, not reused from any
                                      panel column.
  rnd/panel/cube_bench_long.parquet -- NIFTY500 daily index level, SAME
                                      calendar as cube_close_long -- trend
                                      direction + efficiency ratio.
  rnd/panel/market_state.parquet  -- breadth_pct_above_200dma (already built
                                      off cube_close_long, reused not
                                      recomputed) + EY_hist_zscore_expanding
                                      (richness input, reused from
                                      w4mkt_regime_test.py's audited formula).
  rnd/lib/builders_w2_event.py + rnd/lib/run_w3_pead_eventtime.py logic --
                                      reused for the PEAD-by-regime cut.

Low-t rule (per task brief): regimes are RARE by construction (esp.
BEAR/OVERSOLD). This script does NOT gate on significance thresholds for the
regime cells -- it reports n honestly, and judges BEAR-regime and
oversold-MR findings by (a) mechanism consistency with the hypothesis and
(b) drop-one robustness across the handful of distinct crisis episodes that
make up the bucket, not by a t-stat computed on N=8.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

RND = Path(__file__).resolve().parents[1]        # ALPHA_RANKER/rnd
ALPHA_ROOT = RND.parent                            # ALPHA_RANKER
sys.path.insert(0, str(RND / "lib"))

PANEL_LONG_PATH = RND / "panel" / "panel_long.parquet"
CUBE_CLOSE_PATH = RND / "panel" / "cube_close_long.parquet"
CUBE_BENCH_PATH = RND / "panel" / "cube_bench_long.parquet"
MARKET_STATE_PATH = RND / "panel" / "market_state.parquet"
CARDS_DIR = RND / "cards"
OUT_DIR = RND / "wave4"

RICHNESS_SCALE = 0.25  # same constant as w4mkt_regime_test.py, reused not refit


def _native(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    if isinstance(o, (set,)):
        return list(o)
    raise TypeError(str(type(o)))


def write_json(obj: dict, path: Path):
    path.write_text(json.dumps(obj, indent=2, default=_native), encoding="utf-8")


# ===========================================================================
# 1. REGIME CLASSIFICATION (monthly, trailing-only)
# ===========================================================================
def expanding_pctrank(s: pd.Series, min_periods: int) -> pd.Series:
    """Percentile rank of s[t] among s[0..t] inclusive -- causal, no lookahead.
    NaN until min_periods observations are available."""
    out = pd.Series(index=s.index, dtype=float)
    vals = s.values
    for i in range(len(vals)):
        if i + 1 < min_periods or pd.isna(vals[i]):
            out.iloc[i] = np.nan
            continue
        hist = vals[: i + 1]
        hist = hist[~pd.isna(hist)]
        out.iloc[i] = (hist <= vals[i]).mean()
    return out


def efficiency_ratio(nav: pd.Series, window: int) -> pd.Series:
    """Kaufman Efficiency Ratio, trailing `window` trading days ending at t
    (causal): |P(t)-P(t-window)| / sum(|daily diffs| over (t-window, t]).
    ~1 = strongly trending (efficient move), ~0 = choppy/range-bound."""
    diffs = nav.diff().abs()
    noise = diffs.rolling(window).sum()
    signal = (nav - nav.shift(window)).abs()
    return (signal / noise.replace(0, np.nan))


def build_regime_panel(dates: list) -> pd.DataFrame:
    bench = pd.read_parquet(CUBE_BENCH_PATH)
    bench.index = pd.to_datetime(bench.index)
    nav = bench["NIFTY500"].sort_index()

    trend_dir_daily = np.sign(nav.pct_change(252))
    er_daily = efficiency_ratio(nav, 126)

    market = pd.read_parquet(MARKET_STATE_PATH)
    market["date"] = pd.to_datetime(market["date"])
    market = market.sort_values("date").set_index("date")

    reg = pd.DataFrame(index=pd.to_datetime(dates)).sort_index()
    reg["breadth_200"] = market.reindex(reg.index)["breadth_pct_above_200dma"]
    reg["EY_z"] = market.reindex(reg.index)["EY_hist_zscore_expanding"]
    reg["richness_index"] = 100.0 * np.exp(-RICHNESS_SCALE * reg["EY_z"])
    reg["richness_chg_3m"] = reg["richness_index"].diff(3)

    # trend_dir / ER sampled at the monthly dates (same calendar as cube_bench)
    reg["trend_dir"] = trend_dir_daily.reindex(reg.index)
    reg["trend_ER"] = er_daily.reindex(reg.index)

    reg["breadth_pctrank_exp"] = expanding_pctrank(reg["breadth_200"], min_periods=24)
    reg["ER_pctrank_exp"] = expanding_pctrank(reg["trend_ER"], min_periods=24)

    def classify(row):
        if pd.isna(row["breadth_pctrank_exp"]) or pd.isna(row["trend_dir"]):
            return "UNCLASSIFIED"
        if row["breadth_pctrank_exp"] <= 0.20 and row["trend_dir"] < 0:
            return "BEAR_OVERSOLD"
        if (row.get("richness_chg_3m", np.nan) is not None and not pd.isna(row["richness_chg_3m"])
                and row["richness_chg_3m"] > 0
                and row["breadth_pctrank_exp"] >= 0.70 and row["trend_dir"] > 0):
            return "BOOMING_BULL"
        if (0.35 <= row["breadth_pctrank_exp"] <= 0.65
                and not pd.isna(row["ER_pctrank_exp"]) and row["ER_pctrank_exp"] <= 0.50):
            return "NORMAL_CHOPPY"
        return "OTHER"

    reg["regime"] = reg.apply(classify, axis=1)
    reg["oversold_extreme"] = reg["breadth_pctrank_exp"] <= 0.20
    return reg


# ===========================================================================
# 2. MOMENTUM + REVERSAL FACTORS, fresh from cube_close_long
# ===========================================================================
def load_cube():
    c = pd.read_parquet(CUBE_CLOSE_PATH)
    c.index = pd.to_datetime(c.index)
    return c.sort_index()


def build_monthly_factors(cube: pd.DataFrame, dates: list) -> pd.DataFrame:
    idx = cube.index
    n = len(idx)
    loc_of = {d: idx.get_loc(pd.Timestamp(d)) for d in dates}
    vals = cube.to_numpy()
    symbols = cube.columns.to_numpy()

    rows = []
    for d in dates:
        loc = loc_of[d]
        i_skip = loc - 21
        i_3m, i_6m, i_12m = loc - 63, loc - 126, loc - 252
        i_5d = loc - 5
        i_fwd = loc + 21
        if i_12m < 0 or i_fwd >= n:
            continue
        p_now = vals[loc]
        p_skip = vals[i_skip]
        p_3m = vals[i_3m]
        p_6m = vals[i_6m]
        p_12m = vals[i_12m]
        p_5d = vals[i_5d]
        p_fwd = vals[i_fwd]

        mom_3m = p_skip / p_3m - 1.0
        mom_6m = p_skip / p_6m - 1.0
        mom_12m = p_skip / p_12m - 1.0
        rev5d = -(p_now / p_5d - 1.0)
        fwd_ret_1m = p_fwd / p_now - 1.0

        df = pd.DataFrame({
            "symbol": symbols, "mom_3m": mom_3m, "mom_6m": mom_6m, "mom_12m": mom_12m,
            "rev5d": rev5d, "fwd_ret_1m": fwd_ret_1m,
        })
        df["date"] = d
        rows.append(df)
    out = pd.concat(rows, ignore_index=True)
    return out


def build_rsi2(cube: pd.DataFrame, dates: list, period: int = 2) -> pd.DataFrame:
    delta = cube.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.rolling(period).mean()
    roll_down = down.rolling(period).mean()
    rs = roll_up / roll_down.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    factor = (50.0 - rsi).reindex(pd.to_datetime(dates))
    factor.index.name = "date"
    long_df = factor.reset_index().melt(id_vars="date", var_name="symbol", value_name="rsi2_factor")
    return long_df


# ===========================================================================
# 3. IC / decile-spread machinery (self-contained, mirrors harness.py logic)
# ===========================================================================
def cross_sectional_ic(merged: pd.DataFrame, factor_col: str, target_col: str, min_names: int = 20) -> pd.Series:
    def _ic(g):
        gg = g.dropna(subset=[factor_col, target_col])
        if len(gg) < min_names:
            return np.nan
        rho, _ = stats.spearmanr(gg[factor_col], gg[target_col])
        return rho
    return merged.groupby("date").apply(_ic, include_groups=False)


def decile_ls(merged: pd.DataFrame, factor_col: str, target_col: str, min_names: int = 20) -> pd.Series:
    rows = {}
    for d, g in merged.groupby("date"):
        gg = g.dropna(subset=[factor_col, target_col])
        if len(gg) < min_names:
            continue
        try:
            dec = pd.qcut(gg[factor_col].rank(method="first"), 10, labels=False, duplicates="drop")
        except ValueError:
            continue
        gg = gg.assign(decile=dec)
        if gg["decile"].nunique() < 3:
            continue
        top_d, bot_d = gg["decile"].max(), gg["decile"].min()
        rows[d] = gg.loc[gg["decile"] == top_d, target_col].mean() - gg.loc[gg["decile"] == bot_d, target_col].mean()
    return pd.Series(rows)


def summarize(ic: pd.Series, ls: pd.Series) -> dict:
    ic_c = ic.dropna()
    ls_c = ls.dropna()
    return {
        "n_months": int(ic_c.shape[0]),
        "ic_mean": float(ic_c.mean()) if len(ic_c) else np.nan,
        "ic_std": float(ic_c.std()) if len(ic_c) else np.nan,
        "ic_ir": float(ic_c.mean() / ic_c.std()) if len(ic_c) > 1 and ic_c.std() > 0 else np.nan,
        "ic_hit_rate_pos": float((ic_c > 0).mean()) if len(ic_c) else np.nan,
        "ls_mean_monthly": float(ls_c.mean()) if len(ls_c) else np.nan,
        "ls_ann_approx": float((1 + ls_c.mean()) ** 12 - 1) if len(ls_c) and ls_c.mean() > -1 else np.nan,
        "ls_hit_rate_pos": float((ls_c > 0).mean()) if len(ls_c) else np.nan,
    }


def drop_one_by_episode(merged: pd.DataFrame, factor_col: str, target_col: str, regime_dates: pd.Index,
                         min_names: int = 20) -> dict:
    """Group the regime's dates into contiguous episodes (gap > 2 months = new
    episode) and recompute IC dropping each episode in turn -- the rare-regime
    equivalent of drop-one, since there is no such thing as 30 independent
    'bear' observations."""
    dts = sorted(regime_dates)
    episodes = []
    cur = [dts[0]] if dts else []
    for prev, d in zip(dts, dts[1:]):
        gap_months = (d.year - prev.year) * 12 + (d.month - prev.month)
        if gap_months > 2:
            episodes.append(cur)
            cur = [d]
        else:
            cur.append(d)
    if cur:
        episodes.append(cur)

    out = {}
    for i, ep in enumerate(episodes):
        keep_dates = [d for d in dts if d not in ep]
        sub = merged[merged["date"].isin(keep_dates)]
        ic = cross_sectional_ic(sub, factor_col, target_col, min_names=min_names)
        s = summarize(ic, pd.Series(dtype=float))
        out[f"episode_{i}_excl_{ep[0].date()}_{ep[-1].date()}"] = {
            "n_months_excluded": len(ep), "ic_mean_excl": s["ic_mean"], "n_months_remaining": s["n_months"],
        }
    out["_episodes_found"] = [f"{ep[0].date()}..{ep[-1].date()} ({len(ep)}mo)" for ep in episodes]
    return out


def placebo_shuffle(merged: pd.DataFrame, factor_col: str, target_col: str, min_names: int = 20,
                     n_draws: int = 10, seed: int = 42) -> float:
    rng = np.random.default_rng(seed)
    ics = []
    for _ in range(n_draws):
        shuffled = merged.copy()
        shuffled[factor_col] = shuffled.groupby("date")[factor_col].transform(
            lambda x: rng.permutation(x.values))
        ic = cross_sectional_ic(shuffled, factor_col, target_col, min_names=min_names)
        ics.append(ic.mean())
    return float(np.nanmean(ics))


def lag_test(merged: pd.DataFrame, factor_col: str, target_col: str, dates_sorted: list,
             min_names: int = 20) -> float:
    """Shift the factor back by one month (use t-1's factor value to 'predict'
    t's target) -- if a STALE signal predicts almost as well, the live signal
    is not doing real work."""
    date_map = {d: dates_sorted[i - 1] for i, d in enumerate(dates_sorted) if i > 0}
    piv = merged.pivot_table(index="date", columns="symbol", values=factor_col)
    piv_lag = piv.reindex(index=[date_map.get(d) for d in piv.index])
    piv_lag.index = piv.index
    lagged_long = piv_lag.reset_index().melt(id_vars="date", var_name="symbol", value_name=f"{factor_col}_lag")
    m2 = merged.merge(lagged_long, on=["date", "symbol"], how="left")
    ic_lag = cross_sectional_ic(m2, f"{factor_col}_lag", target_col, min_names=min_names)
    return float(ic_lag.mean())


# ===========================================================================
# 4. PEAD by regime (reuse builders_w2_event + run_w3_pead_eventtime logic)
# ===========================================================================
def pead_by_regime(regime_panel: pd.DataFrame) -> dict:
    import builders_w2_event as w2

    cube = load_cube()
    bench_df = pd.read_parquet(CUBE_BENCH_PATH)
    bench = bench_df["NIFTY500"]
    bench.index = pd.to_datetime(bench_df.index)

    q = w2.load_quarterly_pit()
    q = q[q["date_source"] == "actual"].dropna(subset=["np_surprise"]).copy()
    q = q[["symbol", "period_end", "available_date", "np_surprise", "np_surprise_sign"]]

    idx = cube.index
    n = len(idx)
    col_pos = pd.Series(np.arange(cube.shape[1]), index=cube.columns)
    vals = cube.to_numpy()
    bvals = bench.to_numpy()

    START_LAG_TDAYS, END_LAG_CDAYS = 2, 45
    dt_arr = pd.DatetimeIndex(q["available_date"])
    event_pos = idx.searchsorted(dt_arr)
    start_pos = np.clip(event_pos + START_LAG_TDAYS, 0, n - 1)
    end_dt = dt_arr + pd.Timedelta(days=END_LAG_CDAYS)
    end_pos = np.clip(idx.searchsorted(end_dt, side="right") - 1, 0, n - 1)
    sym_ok = q["symbol"].isin(col_pos.index).to_numpy()
    cidx = np.where(sym_ok, col_pos.reindex(q["symbol"]).fillna(-1).to_numpy().astype(int), -1)
    valid = sym_ok & (cidx >= 0) & (event_pos > 0) & (event_pos < n - 1) & (end_pos > start_pos)

    ev = q.copy()
    stock_ret = np.full(len(q), np.nan)
    bench_ret = np.full(len(q), np.nan)
    idxs = np.where(valid)[0]
    c0 = vals[start_pos[idxs], cidx[idxs]]
    c1 = vals[end_pos[idxs], cidx[idxs]]
    b0 = bvals[start_pos[idxs]]
    b1 = bvals[end_pos[idxs]]
    with np.errstate(invalid="ignore", divide="ignore"):
        stock_ret[idxs] = np.where(c0 > 0, c1 / c0 - 1, np.nan)
        bench_ret[idxs] = np.where(b0 > 0, b1 / b0 - 1, np.nan)
    ev["stock_ret"] = stock_ret
    ev["bench_ret"] = bench_ret
    ev["abn_ret"] = ev["stock_ret"] - ev["bench_ret"]
    ev = ev[valid].dropna(subset=["abn_ret", "np_surprise"]).copy()

    lo, hi = ev["np_surprise"].quantile([0.01, 0.99])
    ev["surprise_w"] = ev["np_surprise"].clip(lo, hi)

    # map each event's available_date to the TRAILING (nearest PRIOR) monthly
    # regime label -- causal: the regime known as of the event date is the
    # last-classified month-end at or before it.
    reg = regime_panel[["regime"]].dropna().sort_index()
    ev = ev.sort_values("available_date")
    ev = pd.merge_asof(ev, reg.reset_index().rename(columns={"index": "reg_date"}),
                        left_on="available_date", right_on="reg_date", direction="backward")

    out = {"n_events_total_valid": int(len(ev))}
    for regime_name, g in ev.groupby("regime"):
        if len(g) < 15:
            out[regime_name] = {"n": int(len(g)), "note": "n<15, not computed (too small for even a directional read)"}
            continue
        ic, ic_p = stats.spearmanr(g["surprise_w"], g["abn_ret"])
        placebo_ics = []
        rng = np.random.default_rng(42)
        for _ in range(5):
            perm = rng.permutation(len(g))
            pic, _ = stats.spearmanr(g["surprise_w"].to_numpy()[perm], g["abn_ret"])
            placebo_ics.append(pic)
        out[regime_name] = {
            "n": int(len(g)),
            "ic": float(ic), "ic_p": float(ic_p),
            "placebo_ic_mean": float(np.nanmean(placebo_ics)),
            "date_range": [str(g["available_date"].min().date()), str(g["available_date"].max().date())],
        }
    return out


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    panel_long = pd.read_parquet(PANEL_LONG_PATH, columns=["date"])
    dates = sorted(pd.to_datetime(panel_long["date"].unique()))
    print(f"[1] {len(dates)} monthly dates, {dates[0].date()} -> {dates[-1].date()}")

    print("[2] Building regime panel (trailing-only classification)...")
    regime_panel = build_regime_panel(dates)
    regime_counts = regime_panel["regime"].value_counts()
    print(regime_counts)
    regime_panel.to_csv(OUT_DIR / "w5rg_regime_panel.csv")

    print("[3] Loading cube_close_long + building momentum/reversal factors fresh...")
    cube = load_cube()
    factors = build_monthly_factors(cube, dates)
    rsi2 = build_rsi2(cube, dates)
    factors = factors.merge(rsi2, on=["date", "symbol"], how="left")
    print(f"    factors panel: {factors.shape}")

    merged = factors.merge(
        regime_panel.reset_index().rename(columns={"index": "date"})[["date", "regime", "oversold_extreme"]],
        on="date", how="left")
    dates_sorted = sorted(merged["date"].unique())

    # ---------------------------------------------------------------------
    # TEST 1: momentum lookback by regime
    # ---------------------------------------------------------------------
    print("\n[4] TEST 1: momentum lookback IC/LS by regime")
    mom_results = {}
    for regime_name in ["BOOMING_BULL", "NORMAL_CHOPPY", "BEAR_OVERSOLD"]:
        sub = merged[merged["regime"] == regime_name]
        n_months_regime = sub["date"].nunique()
        cell = {"n_months_in_regime": int(n_months_regime)}
        for lb in ["mom_3m", "mom_6m", "mom_12m"]:
            ic = cross_sectional_ic(sub, lb, "fwd_ret_1m")
            ls = decile_ls(sub, lb, "fwd_ret_1m")
            cell[lb] = summarize(ic, ls)
        # drop-one by contiguous episode for the regime's own date set
        regime_dates_idx = pd.DatetimeIndex(sub["date"].unique())
        cell["drop_one_episodes_mom_12m"] = drop_one_by_episode(merged[merged["regime"] == regime_name],
                                                                  "mom_12m", "fwd_ret_1m", regime_dates_idx)
        mom_results[regime_name] = cell
        print(f"  {regime_name}: n_months={n_months_regime}  "
              f"3m_IC={cell['mom_3m']['ic_mean']:.4f}  6m_IC={cell['mom_6m']['ic_mean']:.4f}  "
              f"12m_IC={cell['mom_12m']['ic_mean']:.4f}")

    # unconditional (all classified regimes pooled) for reference
    all_classified = merged[merged["regime"].isin(["BOOMING_BULL", "NORMAL_CHOPPY", "BEAR_OVERSOLD", "OTHER"])]
    uncond = {}
    for lb in ["mom_3m", "mom_6m", "mom_12m"]:
        ic = cross_sectional_ic(merged, lb, "fwd_ret_1m")
        ls = decile_ls(merged, lb, "fwd_ret_1m")
        uncond[lb] = summarize(ic, ls)
    mom_results["UNCONDITIONAL_ALL_MONTHS"] = uncond
    print(f"  UNCONDITIONAL: 3m_IC={uncond['mom_3m']['ic_mean']:.4f}  6m_IC={uncond['mom_6m']['ic_mean']:.4f}  "
          f"12m_IC={uncond['mom_12m']['ic_mean']:.4f}")

    # ---------------------------------------------------------------------
    # TEST 2: selective mean-reversion (oversold-extreme vs unconditional)
    # ---------------------------------------------------------------------
    print("\n[5] TEST 2: selective mean-reversion in oversold-extreme breadth")
    mr_results = {}
    for factor_col in ["rev5d", "rsi2_factor"]:
        uncond_ic = cross_sectional_ic(merged, factor_col, "fwd_ret_1m")
        uncond_ls = decile_ls(merged, factor_col, "fwd_ret_1m")
        oversold = merged[merged["oversold_extreme"] == True]
        os_ic = cross_sectional_ic(oversold, factor_col, "fwd_ret_1m")
        os_ls = decile_ls(oversold, factor_col, "fwd_ret_1m")
        os_dates = pd.DatetimeIndex(oversold["date"].unique())
        drop_one = drop_one_by_episode(oversold, factor_col, "fwd_ret_1m", os_dates)
        placebo = placebo_shuffle(oversold, factor_col, "fwd_ret_1m")
        lag = lag_test(merged, factor_col, "fwd_ret_1m", dates_sorted)
        mr_results[factor_col] = {
            "unconditional": summarize(uncond_ic, uncond_ls),
            "oversold_extreme_only": summarize(os_ic, os_ls),
            "oversold_drop_one_episodes": drop_one,
            "oversold_placebo_ic_mean": placebo,
            "oversold_lag_test_ic_mean": lag,
        }
        print(f"  {factor_col}: unconditional IC={uncond_ic.mean():.4f} (n={uncond_ic.dropna().shape[0]})  "
              f"| oversold-only IC={os_ic.mean():.4f} (n={os_ic.dropna().shape[0]})  "
              f"placebo={placebo:.4f}  lag={lag:.4f}")

    # ---------------------------------------------------------------------
    # TEST 3: PEAD by regime (secondary, low expectation)
    # ---------------------------------------------------------------------
    print("\n[6] TEST 3 (secondary): PEAD by regime")
    try:
        pead_results = pead_by_regime(regime_panel)
        print(json.dumps(pead_results, indent=2, default=_native))
    except Exception as e:
        pead_results = {"error": str(e)}
        print(f"  PEAD-by-regime failed: {e}")

    # ---------------------------------------------------------------------
    # write outputs
    # ---------------------------------------------------------------------
    all_results = {
        "regime_counts": regime_counts.to_dict(),
        "momentum_by_regime": mom_results,
        "selective_mean_reversion": mr_results,
        "pead_by_regime": pead_results,
    }
    write_json(all_results, OUT_DIR / "W5RG_regime_momentum_horizon_results.json")
    write_json(mom_results, CARDS_DIR / "W5RG_momentum_by_regime.json")
    write_json(mr_results, CARDS_DIR / "W5RG_selective_mr.json")
    write_json(pead_results, CARDS_DIR / "W5RG_pead_by_regime.json")
    print("\n[7] Done. Outputs written to rnd/wave4/ and rnd/cards/.")


if __name__ == "__main__":
    main()
