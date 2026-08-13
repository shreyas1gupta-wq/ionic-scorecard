"""Shared stats/era-split/Bonferroni helpers for every dimension in this study. Era boundaries
and cost model are IDENTICAL to PRICE_LEVELS_20260730 and the SHARED_CONTEXT mandate."""
import numpy as np
import pandas as pd
from scipy import stats

BUILD_END = pd.Timestamp("2024-10-01")
HOLDOUT_START = pd.Timestamp("2026-01-01")


def era_of(dates):
    dates = pd.to_datetime(pd.Series(dates))
    return np.select([dates < BUILD_END, dates >= HOLDOUT_START], ["BUILD", "HOLDOUT"], default="RECENT")


def stat(x):
    x = pd.Series(x).dropna().to_numpy()
    n = len(x)
    if n < 2 or x.std() == 0:
        return dict(n=n, mean=(x.mean() if n else np.nan), t=np.nan)
    t = stats.ttest_1samp(x, 0).statistic
    return dict(n=n, mean=float(x.mean()), t=float(t))


def bonferroni_bar(m, alpha=0.05):
    """Two-sided |t| bar for m independent trials, large-df normal approx (matches the
    PRICE_LEVELS_20260730 convention of quoting this as 'the Bonferroni bar')."""
    return float(stats.norm.ppf(1 - (alpha / m) / 2))


def null_hit_rate(rr):
    """Random-walk null: P(target hit before stop) for stop -S, target +R*S -- exactly 1/(1+R)."""
    return 1.0 / (1.0 + rr)


def concentration(x):
    x = pd.Series(x).dropna()
    if len(x) == 0 or x.sum() == 0:
        return np.nan
    pos = x[x > 0]
    if pos.sum() == 0:
        return np.nan
    return float(pos.max() / x.sum()) if x.sum() > 0 else float(pos.max() / pos.sum())


def random_day_placebo(entries: pd.DataFrame, all_dates, pnl_fn, n_draws=200, seed=20260731):
    """entries: DataFrame with at least ['date','tod_minutes','direction'] (tod_minutes = minutes
    since midnight of the signal bar, direction = +-1). pnl_fn(date, tod_minutes, direction) ->
    net pnl for a placebo trade planted at a RANDOM day, same time-of-day + direction, or np.nan
    if that day/time can't produce a trade (e.g. off session). Returns (p_value, placebo_means).
    Matches the firm's existing random-day-reassignment convention (INDICATOR_MINE_20260730,
    OPENING_PATTERNS_20260730): tests whether ANY day at that time-of-day looks the same, i.e.
    the RANDOM-ENTRY control the mandate asks for, matched on count + time-of-day + direction."""
    rng = np.random.default_rng(seed)
    all_dates = list(all_dates)
    observed = entries["net_pnl"].mean()
    n = len(entries)
    draws = []
    for _ in range(n_draws):
        placebo_dates = rng.choice(all_dates, size=n, replace=True)
        pnls = [pnl_fn(pd.Timestamp(d), tod, dirn) for d, tod, dirn in
                zip(placebo_dates, entries["tod_minutes"], entries["direction"])]
        pnls = np.array(pnls, dtype=float)
        pnls = pnls[np.isfinite(pnls)]
        draws.append(pnls.mean() if len(pnls) else np.nan)
    draws = np.array(draws, float)
    valid = draws[np.isfinite(draws)]
    if len(valid) < n_draws * 0.5:
        return np.nan, draws
    p = float((np.abs(valid) >= abs(observed)).mean())
    return p, draws


def random_entry_placebo(entries: pd.DataFrame, day_arrays: dict, atr_by_date: dict, exit_cfg: dict,
                          all_dates, simulate_exit_fn, n_draws=200, seed=20260731):
    """RANDOM-ENTRY placebo for signals with no discrete 'level' (VWAP bands, order-flow, etc).
    entries needs columns: tmin (minutes-since-midnight of the entry bar), direction (+-1).
    For each draw, reassigns every entry to a RANDOM day (same time-of-day, same direction),
    scales the stop/target by THAT day's own ATR (matched distance-from-spot convention), and
    replays simulate_exit. This is the mandate's 'RANDOM-LEVEL / RANDOM-ENTRY PLACEBO, matched on
    count, time-of-day, and average distance from spot' for signal types that are not a fixed
    intraday price level."""
    rng = np.random.default_rng(seed)
    all_dates = np.array(list(all_dates))
    tmins = entries["tmin"].to_numpy()
    dirs = entries["direction"].to_numpy()
    n = len(entries)
    draws = []
    for _ in range(n_draws):
        placebo_dates = rng.choice(all_dates, size=n, replace=True)
        pnls = []
        for d, tmin, dirn in zip(placebo_dates, tmins, dirs):
            day = day_arrays.get(pd.Timestamp(d))
            atr = atr_by_date.get(pd.Timestamp(d), np.nan)
            if day is None or not np.isfinite(atr) or atr <= 0:
                continue
            idx = int(np.searchsorted(day["tmin"], tmin, side="left"))
            if idx + 1 >= len(day["o"]) or idx < 1:
                continue
            entry_price = day["o"][idx + 1]
            bars_df = pd.DataFrame({"high": day["h"][idx + 1:], "low": day["l"][idx + 1:],
                                     "close": day["c"][idx + 1:]})
            if len(bars_df) < 3:
                continue
            stop = exit_cfg["stop_f"] * atr
            target = exit_cfg["target_f"] * atr
            try:
                res = simulate_exit_fn(bars_df, entry_price, int(dirn), stop=stop, target=target)
            except Exception:
                continue
            pnls.append(res.pnl_pessimistic)
        pnls = np.array(pnls, float)
        draws.append(pnls.mean() if len(pnls) else np.nan)
    draws = np.array(draws, float)
    return draws


def random_level_placebo_stat(levels: pd.DataFrame, sim_fn, seed=20260731):
    """Generic random-LEVEL placebo (PRICE_LEVELS_20260730 convention): anchor held fixed at the
    real system's own anchor; level distance resampled Uniform(0, 2*mean_real_distance), sign
    randomized, same count/anchor. sim_fn(levels_df) -> trades_df with a 'net_pess' column.
    Returns one draw's grouped stats; caller loops seeds and pools."""
    rng = np.random.default_rng(seed)
    dist = (levels["level_price"] - levels["anchor"]).abs()
    mean_dist = dist.groupby(levels.get("level_name", levels.get("system"))).transform("mean")
    sign = rng.choice([-1.0, 1.0], size=len(levels))
    mag = rng.uniform(0.0, 2 * mean_dist.to_numpy())
    placebo = levels.copy()
    placebo["level_price"] = placebo["anchor"].to_numpy() + sign * mag
    return sim_fn(placebo)
