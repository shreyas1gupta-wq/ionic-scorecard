"""152_three_posted.py -- Aditya Verma (R&D), 2026-07-30.
Three externally-posted strategies (mean-reversion z-score fade, EWM-trend breakout,
gap-continuation breakout), each as delta-1 futures AND naked long option (0.40-0.80 delta),
per PRE_REGISTRATION.md at results/THREE_POSTED_20260730/. Self-contained, no arguments.
Writes all outputs to its own results dir. Designed for the serial queue runner (1h budget).
"""
from __future__ import annotations

import datetime as dt
import gc
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

t_start = time.time()

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
AMC = ROOT / "Shreyas_Ionic_AMC"
OUT = AMC / "04_RND_LAB" / "results" / "THREE_POSTED_20260730"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(AMC / "04_RND_LAB" / "lib"))
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import guards as G          # noqa: E402
import chain                # noqa: E402

NIFTY_1MIN = ROOT / "intraday_options_strategy" / "datasets" / "processed" / "nifty_1min.parquet"
LOT = 65
FUT_COST_PRE = 4.47 + 0.5     # pre-2024-10-01 round trip + slippage
FUT_COST_POST = 5.97 + 0.5    # post-2024-10-01
OPT_COST_PTS = 1.67           # Rs25/lot/side round trip, this mandate's own number
R_FREE = 0.065
SL_FRAC = 0.60                # exit if premium <= 60% of entry (40% stop)
OPT_DATA_START = dt.date(2021, 5, 24)
HELD_OUT_START = dt.date(2026, 1, 1)
STRUCT_BREAK = dt.date(2024, 10, 1)
WEEKLY_LAUNCH = dt.date(2019, 2, 1)
LOG = []


def log(msg):
    line = f"[{time.time()-t_start:7.1f}s] {msg}"
    print(line, flush=True)
    LOG.append(line)


# ------------------------------------------------------------------ daily bars ----
def build_daily():
    df = pd.read_parquet(NIFTY_1MIN, columns=["open", "high", "low", "close"])
    assert pd.Series(df.index[:5]).dt.time.min() >= dt.time(9, 15), "pre-open bars present!"
    d = df.index.date
    g = df.groupby(d)
    daily = pd.DataFrame({
        "open": g["open"].first(),
        "high": g["high"].max(),
        "low": g["low"].min(),
        "close": g["close"].last(),
    })
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()
    return daily


def add_indicators(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.copy()
    prev_close = d["close"].shift(1)
    tr = pd.concat([
        d["high"] - d["low"],
        (d["high"] - prev_close).abs(),
        (d["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    d["atr14"] = tr.rolling(14).mean()          # today's ATR (uses today's own H/L -- fine,
    d["atr14_y"] = d["atr14"].shift(1)          # ATR "as of yesterday" for causal entry sizing

    d["sma20_y"] = d["close"].shift(1).rolling(20).mean()
    d["std20_y"] = d["close"].shift(1).rolling(20).std()
    d["z_open"] = (d["open"] - d["sma20_y"]) / d["std20_y"]

    ema20 = d["close"].ewm(span=20, adjust=False).mean()
    ema50 = d["close"].ewm(span=50, adjust=False).mean()
    d["ema20_y"] = ema20.shift(1)
    d["ema50_y"] = ema50.shift(1)
    roc10 = d["close"].pct_change(10)
    d["roc10_y"] = roc10.shift(1)
    # Close-based Donchian channel through t-2 (EXCLUDES yesterday t-1) so that
    # "yesterday's close vs the channel" is an apples-to-apples comparison and can
    # actually be positive. (BUG CAUGHT IN SMOKE TEST: high.rolling(20).max().shift(1)
    # includes yesterday's own HIGH, and close <= high always same-day, so
    # close_y - hi20_y was structurally <=0 for every row -- zero signals, ever.)
    d["hi20_y"] = d["close"].shift(2).rolling(20).max()
    d["lo20_y"] = d["close"].shift(2).rolling(20).min()
    d["close_y"] = d["close"].shift(1)
    d["high_y"] = d["high"].shift(1)
    d["low_y"] = d["low"].shift(1)

    # RSI14 (Wilder), causal shift(1)
    chg = d["close"].diff()
    gain = chg.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-chg.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    d["rsi14_y"] = rsi.shift(1)

    # RV percentile (IV-percentile proxy), causal
    logret = np.log(d["close"] / d["close"].shift(1))
    rv20 = logret.rolling(20).std() * np.sqrt(252)
    d["rv20_y"] = rv20.shift(1)
    d["rv_pctile_y"] = d["rv20_y"].rolling(252, min_periods=60).apply(
        lambda s: (s.rank(pct=True).iloc[-1]), raw=False).shift(1)

    d["sma20dma_y"] = d["close"].shift(1).rolling(20).mean()
    d["sma50dma_y"] = d["close"].shift(1).rolling(50).mean()
    return d


def era_tag(day: dt.date) -> str:
    if day < WEEKLY_LAUNCH:
        return "pre-2019"
    if day < STRUCT_BREAK:
        return "2019-Sep2024"
    if day < HELD_OUT_START:
        return "Oct2024-2025"
    return "2026-heldout"


def fut_cost(day: dt.date) -> float:
    return FUT_COST_PRE if day < STRUCT_BREAK else FUT_COST_POST


# ------------------------------------------------------------------ signal builders ----
def sig_meanrev(d: pd.DataFrame, thresh=1.0):
    z = d["z_open"]
    long = z < -thresh
    short = z > thresh
    dirn = pd.Series(0, index=d.index)
    dirn[long] = 1
    dirn[short] = -1
    return dirn


def sig_trend(d: pd.DataFrame, atr_norm=True, k=0.25, k_raw=20.0):
    bull = d["ema20_y"] > d["ema50_y"]
    bear = d["ema20_y"] < d["ema50_y"]
    mom_up = d["roc10_y"] > 0
    mom_dn = d["roc10_y"] < 0
    up_strength = d["close_y"] - d["hi20_y"]
    dn_strength = d["lo20_y"] - d["close_y"]
    if atr_norm:
        up_ok = up_strength >= k * d["atr14_y"]
        dn_ok = dn_strength >= k * d["atr14_y"]
    else:
        up_ok = up_strength >= k_raw
        dn_ok = dn_strength >= k_raw
    long = bull & mom_up & up_ok
    short = bear & mom_dn & dn_ok
    dirn = pd.Series(0, index=d.index)
    dirn[long] = 1
    dirn[short] = -1
    return dirn


def sig_gap(d: pd.DataFrame, atr_norm=True, k=0.2, k_raw=20.0):
    gap_up = d["open"] - d["high_y"]
    gap_dn = d["low_y"] - d["open"]
    if atr_norm:
        up_ok = gap_up >= k * d["atr14_y"]
        dn_ok = gap_dn >= k * d["atr14_y"]
    else:
        up_ok = gap_up >= k_raw
        dn_ok = gap_dn >= k_raw
    dirn = pd.Series(0, index=d.index)
    dirn[up_ok] = 1
    dirn[dn_ok] = -1
    return dirn


# ------------------------------------------------------------------ futures backtests ----
def futures_eod(d: pd.DataFrame, dirn: pd.Series, label: str = "na") -> pd.DataFrame:
    """Same-day open->close trade, direction dirn (1/0/-1)."""
    rows = []
    idx = d.index[dirn != 0]
    for day in idx:
        dd = day.date()
        o, c = d.loc[day, "open"], d.loc[day, "close"]
        side = dirn.loc[day]
        gross = (c - o) * side
        cost = fut_cost(dd)
        rows.append({"date": dd, "dir": side, "entry": o, "exit": c,
                      "gross_pts": gross, "net_pts": gross - cost, "era": era_tag(dd)})
    return pd.DataFrame(rows)


def futures_holdN(d: pd.DataFrame, dirn: pd.Series, n_days: int) -> pd.DataFrame:
    """Entry at open_t, exit at close of day t+n_days-1 (n_days=1 -> same-day close)."""
    rows = []
    dates = d.index
    pos = {dt_: i for i, dt_ in enumerate(dates)}
    for day in dates[dirn != 0]:
        i = pos[day]
        j = i + n_days - 1
        if j >= len(dates):
            continue
        dd = day.date()
        o = d["open"].iloc[i]
        c = d["close"].iloc[j]
        side = dirn.loc[day]
        gross = (c - o) * side
        cost = fut_cost(dd)
        rows.append({"date": dd, "dir": side, "entry": o, "exit": c,
                      "gross_pts": gross, "net_pts": gross - cost, "era": era_tag(dd)})
    return pd.DataFrame(rows)


def futures_trailing(d: pd.DataFrame, dirn: pd.Series, atr_norm=True, k=3.0, k_raw=60.0,
                      max_hold=60) -> pd.DataFrame:
    """Multi-day ATR (or fixed) trailing stop, worst-of-fill convention."""
    dates = d.index
    n = len(dates)
    rows = []
    i = 0
    entered_mask = (dirn != 0).values
    while i < n:
        if not entered_mask[i]:
            i += 1
            continue
        side = dirn.iloc[i]
        entry_day = dates[i]
        entry_price = d["open"].iloc[i]
        atr_at_entry = d["atr14_y"].iloc[i]
        stop_dist = (k * atr_at_entry) if atr_norm else k_raw
        if not np.isfinite(stop_dist) or stop_dist <= 0:
            i += 1
            continue
        best = d["close"].iloc[i]  # running favourable extreme since entry
        exit_price = None
        exit_day = None
        j = i
        for step in range(1, max_hold + 1):
            j = i + step
            if j >= n:
                exit_price = d["close"].iloc[n - 1]
                exit_day = dates[n - 1]
                break
            if side == 1:
                trail = best - stop_dist
                lo = d["low"].iloc[j]
                if lo <= trail:
                    op = d["open"].iloc[j]
                    exit_price = min(op, trail)
                    exit_day = dates[j]
                    break
                best = max(best, d["close"].iloc[j])
            else:
                trail = best + stop_dist
                hi = d["high"].iloc[j]
                if hi >= trail:
                    op = d["open"].iloc[j]
                    exit_price = max(op, trail)
                    exit_day = dates[j]
                    break
                best = min(best, d["close"].iloc[j])
        if exit_price is None:
            exit_price = d["close"].iloc[min(j, n - 1)]
            exit_day = dates[min(j, n - 1)]
        dd = entry_day.date()
        gross = (exit_price - entry_price) * side
        cost = fut_cost(dd)
        rows.append({"date": dd, "exit_date": exit_day.date(), "dir": side,
                      "entry": entry_price, "exit": exit_price,
                      "gross_pts": gross, "net_pts": gross - cost, "era": era_tag(dd)})
        # advance i past this trade's exit to avoid overlapping trailing positions
        i = max(i + 1, (j if exit_day is not None else i + 1))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ placebo ----
def placebo_test(d: pd.DataFrame, real_trades: pd.DataFrame, trade_fn, n_iter=500, seed=42):
    if real_trades.empty:
        return np.nan, np.nan
    n_long = int((real_trades["dir"] == 1).sum())
    n_short = int((real_trades["dir"] == -1).sum())
    n_total = n_long + n_short
    eligible = d.dropna(subset=["atr14_y", "sma20_y"]).index
    if len(eligible) < n_total + 5:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    real_mean = real_trades["net_pts"].mean()
    null_means = []
    for _ in range(n_iter):
        chosen = rng.choice(len(eligible), size=n_total, replace=False)
        days = eligible[chosen]
        dirs = np.array([1] * n_long + [-1] * n_short)
        rng.shuffle(dirs)
        dirn = pd.Series(0, index=d.index)
        dirn.loc[days] = dirs
        tt = trade_fn(d, dirn)
        if not tt.empty:
            null_means.append(tt["net_pts"].mean())
    null_means = np.array(null_means)
    if len(null_means) == 0:
        return np.nan, np.nan
    p = float((null_means >= real_mean).mean())
    return p, float(null_means.mean())


# ------------------------------------------------------------------ BS helpers ----
def bs_price(S, K, T, r, sig, cp):
    if T <= 1e-6 or sig <= 1e-6:
        return max(0.0, (S - K)) if cp == "CE" else max(0.0, (K - S))
    d1 = (np.log(S / K) + (r + 0.5 * sig ** 2) * T) / (sig * np.sqrt(T))
    d2 = d1 - sig * np.sqrt(T)
    if cp == "CE":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def bs_delta(S, K, T, r, sig, cp):
    if T <= 1e-6 or sig <= 1e-6:
        if cp == "CE":
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sig ** 2) * T) / (sig * np.sqrt(T))
    return norm.cdf(d1) if cp == "CE" else norm.cdf(d1) - 1


def solve_iv(price, S, K, T, r, cp):
    try:
        return brentq(lambda s: bs_price(S, K, T, r, s, cp) - price, 1e-3, 3.0, xtol=1e-4)
    except Exception:
        return np.nan


# ------------------------------------------------------------------ options backtest (EOD exit) ----
def first_print(df_slice: pd.DataFrame, after_t, window_min=10):
    w = df_slice[(df_slice["t"] >= after_t) & (df_slice["t"] <= after_t + pd.Timedelta(minutes=window_min))
                 & (df_slice["volume"] > 0)]
    if w.empty:
        return None
    return w.iloc[0]


def options_eod_backtest(d: pd.DataFrame, dirn: pd.Series, strategy_name: str, variant_name: str):
    events = [(day, dirn.loc[day]) for day in d.index[dirn != 0] if day.date() >= OPT_DATA_START]
    log(f"  options[{strategy_name}/{variant_name}]: {len(events)} candidate events "
        f">= {OPT_DATA_START}")
    rows = []
    n_loaded = 0
    cache_evictions = 0
    for day_ts, side in events:
        day = day_ts.date()
        cp = "CE" if side == 1 else "PE"
        exp = chain.nearest_expiry(day, min_dte=1, max_dte=10)
        if exp is None:
            rows.append({"date": day, "dir": side, "dropped": "no_expiry"})
            continue
        try:
            dch = chain.day_chain(exp, day)
        except Exception as e:
            rows.append({"date": day, "dir": side, "dropped": f"chain_err:{e}"})
            continue
        n_loaded += 1
        if n_loaded % 10 == 0:
            chain.load_expiry.cache_clear()
            gc.collect()
            cache_evictions += 1
        if dch.empty:
            rows.append({"date": day, "dir": side, "dropped": "empty_day_chain"})
            continue
        spot_row = None
        try:
            spot_row = d.loc[day_ts, "open"]
        except Exception:
            pass
        if spot_row is None or not np.isfinite(spot_row):
            rows.append({"date": day, "dir": side, "dropped": "no_spot"})
            continue
        S = float(spot_row)
        T = max((exp - day).days, 0) / 365.0
        if T <= 0:
            rows.append({"date": day, "dir": side, "dropped": "zero_dte"})
            continue
        atm_strike = round(S / 50) * 50
        entry_t = pd.Timestamp.combine(day, dt.time(9, 16))
        atm_slice = dch[(dch["strike"] == atm_strike) & (dch["option_type"] == cp)]
        atm_bar = first_print(atm_slice, entry_t)
        if atm_bar is None:
            rows.append({"date": day, "dir": side, "dropped": "no_atm_print"})
            continue
        iv = solve_iv(float(atm_bar["close"]), S, atm_strike, T, R_FREE, cp)
        if not np.isfinite(iv) or iv <= 0:
            rows.append({"date": day, "dir": side, "dropped": "iv_solve_fail"})
            continue
        strikes = np.arange(round((S - 1000) / 50) * 50, round((S + 500) / 50) * 50 + 50, 50)
        best_strike, best_gap = None, 1e9
        for K in strikes:
            delta = abs(bs_delta(S, float(K), T, R_FREE, iv, cp))
            if 0.40 <= delta <= 0.80:
                gap = abs(delta - 0.60)
                if gap < best_gap:
                    best_gap, best_strike = gap, K
        if best_strike is None:
            rows.append({"date": day, "dir": side, "dropped": "no_strike_in_band"})
            continue
        target_slice = dch[(dch["strike"] == best_strike) & (dch["option_type"] == cp)].sort_values("t")
        entry_bar = first_print(target_slice, entry_t)
        if entry_bar is None:
            rows.append({"date": day, "dir": side, "dropped": "no_fill_target_strike"})
            continue
        entry_prem = float(entry_bar["close"])
        entry_delta = bs_delta(S, float(best_strike), T, R_FREE, iv, cp)
        sl_level = entry_prem * SL_FRAC
        day_bars = target_slice[(target_slice["t"] > entry_bar["t"]) & (target_slice["volume"] > 0)]
        sl_hit, exit_prem, exit_t = False, None, None
        for _, bar in day_bars.iterrows():
            if bar["low"] <= sl_level:
                exit_prem = sl_level
                exit_t = bar["t"]
                sl_hit = True
                break
        if exit_prem is None:
            if not day_bars.empty:
                exit_prem = float(day_bars.iloc[-1]["close"])
                exit_t = day_bars.iloc[-1]["t"]
            else:
                exit_prem = entry_prem
                exit_t = entry_bar["t"]
        gross_pts = exit_prem - entry_prem
        net_pts = gross_pts - OPT_COST_PTS
        rows.append({"date": day, "dir": side, "strike": best_strike, "cp": cp,
                      "expiry": exp, "dte": (exp - day).days, "iv": iv, "delta": entry_delta,
                      "entry_prem": entry_prem, "exit_prem": exit_prem, "sl_hit": sl_hit,
                      "gross_pts": gross_pts, "net_pts": net_pts, "era": era_tag(day),
                      "dropped": None})
    chain.load_expiry.cache_clear()
    gc.collect()
    out = pd.DataFrame(rows)
    n_dropped = int(out["dropped"].notna().sum()) if not out.empty else 0
    log(f"  options[{strategy_name}/{variant_name}]: {len(out)-n_dropped} filled, "
        f"{n_dropped} dropped, {n_loaded} expiry-days loaded, {cache_evictions} cache clears")
    return out


# ------------------------------------------------------------------ metrics ----
def cost_stress(net, gross_minus_cost_base_cost, mults=(1.0, 1.5, 2.0, 3.0)):
    out = {}
    for m in mults:
        out[f"net_at_{m}x"] = float((net + gross_minus_cost_base_cost - gross_minus_cost_base_cost * m).mean())
    return out


def summarize(trades: pd.DataFrame, cost_per_trade_col_is_flat: float, label: str) -> dict:
    if trades.empty or "net_pts" not in trades.columns:
        return {"label": label, "n": 0}
    t = trades.dropna(subset=["net_pts"])
    n = len(t)
    if n == 0:
        return {"label": label, "n": 0}
    net = t["net_pts"]
    gross = t["gross_pts"] if "gross_pts" in t.columns else net
    mean_net, mean_gross = float(net.mean()), float(gross.mean())
    median_net = float(net.median())
    wins = net[net > 0]
    losses = net[net <= 0]
    rr = float(wins.mean() / abs(losses.mean())) if len(losses) and losses.mean() != 0 and len(wins) else np.nan
    top1_share = float(net.nlargest(1).sum() / net.sum()) if net.sum() != 0 else np.nan
    top2_share = float(net.nlargest(2).sum() / net.sum()) if net.sum() != 0 else np.nan
    hit = float((net > 0).mean())
    eq = net.cumsum()
    peak = eq.cummax()
    dd_pts = (eq - peak).min()
    ann_pts = mean_net * (252.0 / max(1, (t["date"].max() - t["date"].min()).days)) * n if n > 1 else np.nan
    # points-per-year properly: total net pts / years spanned
    yrs = max((pd.to_datetime(t["date"].max()) - pd.to_datetime(t["date"].min())).days / 365.25, 0.1)
    pts_per_year = float(net.sum() / yrs)
    points_calmar = float(pts_per_year / abs(dd_pts)) if dd_pts < 0 else np.nan
    era_split = {}
    if "era" in t.columns:
        for era, grp in t.groupby("era"):
            era_split[era] = {"n": len(grp), "mean_net": float(grp["net_pts"].mean()),
                               "median_net": float(grp["net_pts"].median())}
    # frequency-dependent robustness
    if n < 100:
        robust = {}
        for frac in (0.05, 0.10, 0.20):
            k = max(1, int(round(n * frac)))
            trimmed = net.sort_values(ascending=False).iloc[k:]
            robust[f"excl_top_{int(frac*100)}pct"] = {
                "n_left": len(trimmed), "mean_net": float(trimmed.mean()) if len(trimmed) else np.nan}
    else:
        robust = {}
        cost_flat = cost_per_trade_col_is_flat
        for m in (1.0, 1.5, 2.0, 3.0):
            adj = gross - cost_flat * m
            robust[f"net_at_{m}x_cost"] = float(adj.mean())
    hard_kill_conc = bool(top1_share > 0.30) if np.isfinite(top1_share) else False
    hard_kill_dd = bool(abs(dd_pts) > 999999)  # placeholder, MDD% needs capital -- see notes
    return {
        "label": label, "n": n, "mean_gross_pts": mean_gross, "mean_net_pts": mean_net,
        "median_net_pts": median_net, "hit_rate": hit, "RR": rr,
        "top1_trade_share_of_profit": top1_share, "top2_trade_share_of_profit": top2_share,
        "maxDD_pts": float(dd_pts), "pts_per_year": pts_per_year, "points_calmar": points_calmar,
        "era_split": era_split, "robustness": robust, "concentration_hard_kill": hard_kill_conc,
    }


# ------------------------------------------------------------------ regime conditioning ----
def regime_table(trades: pd.DataFrame, d: pd.DataFrame, strategy: str, variant: str) -> list[dict]:
    if trades.empty:
        return []
    t = trades.copy()
    t["date_ts"] = pd.to_datetime(t["date"])
    t = t.merge(d[["sma20dma_y", "sma50dma_y", "rsi14_y", "rv_pctile_y", "close"]],
                left_on="date_ts", right_index=True, how="left")
    t["above20"] = t["close"] > t["sma20dma_y"]
    t["above50"] = t["close"] > t["sma50dma_y"]
    t["rsi_band"] = pd.cut(t["rsi14_y"], [-1, 30, 70, 101], labels=["<30", "30-70", ">70"])
    t["rv_tertile"] = pd.qcut(t["rv_pctile_y"], 3, labels=["low", "mid", "high"], duplicates="drop") \
        if t["rv_pctile_y"].notna().sum() >= 10 else np.nan
    t["half"] = np.where(pd.to_datetime(t["date"]) < pd.Timestamp(STRUCT_BREAK), "pre-Oct2024", "post-Oct2024")
    out = []
    for bucket_col in ["above20", "above50", "rsi_band", "rv_tertile"]:
        if bucket_col not in t.columns:
            continue
        for (bucket_val, half), grp in t.groupby([bucket_col, "half"], observed=True):
            if len(grp) == 0:
                continue
            out.append({"strategy": strategy, "variant": variant, "bucket_type": bucket_col,
                        "bucket_value": str(bucket_val), "era_half": half, "n": len(grp),
                        "mean_net_pts": float(grp["net_pts"].mean())})
    return out


# ------------------------------------------------------------------ main ----
def main():
    log("loading daily bars from nifty_1min.parquet")
    daily_raw = build_daily()
    log(f"daily bars: {len(daily_raw)} days {daily_raw.index.min().date()}..{daily_raw.index.max().date()}")
    d = add_indicators(daily_raw)

    all_summaries = []
    regime_rows = []
    fut_trades_store = {}
    opt_trades_store = {}

    # ---------- Strategy 1: mean reversion z-score fade at open ----------
    for variant in ["primary_z1.0"]:
        dirn = sig_meanrev(d, thresh=1.0)
        n_sig = int((dirn != 0).sum())
        log(f"S1 meanrev {variant}: {n_sig} signal days")
        ft = futures_eod(d, dirn, "S1")
        ft2 = futures_holdN(d, dirn, 2)
        p, null_mean = placebo_test(d, ft, futures_eod)
        summ = summarize(ft, FUT_COST_PRE, f"S1_futures_{variant}_eod")
        summ["placebo_p"] = p
        summ["placebo_null_mean"] = null_mean
        summ["secondary_2day_hold_mean_net"] = float(ft2["net_pts"].mean()) if not ft2.empty else np.nan
        all_summaries.append(summ)
        fut_trades_store[f"S1_futures_{variant}"] = ft
        regime_rows += regime_table(ft, d, "S1", variant)

        ot = options_eod_backtest(d, dirn, "S1", variant)
        ot_ok = ot[ot["dropped"].isna()] if not ot.empty and "dropped" in ot.columns else ot
        p_opt, null_mean_opt = placebo_test(
            d[d.index.date >= OPT_DATA_START], ot_ok, futures_eod) if not ot_ok.empty else (np.nan, np.nan)
        osumm = summarize(ot_ok, OPT_COST_PTS, f"S1_options_{variant}_eod")
        osumm["n_events_scanned"] = len(ot)
        osumm["n_dropped"] = int(ot["dropped"].notna().sum()) if not ot.empty else 0
        all_summaries.append(osumm)
        opt_trades_store[f"S1_options_{variant}"] = ot

    # ---------- Strategy 2: trend EWM crossover + momentum + ATR breakout ----------
    for variant, atr_norm in [("atr_normalised", True), ("raw_points", False)]:
        dirn = sig_trend(d, atr_norm=atr_norm)
        n_sig = int((dirn != 0).sum())
        log(f"S2 trend {variant}: {n_sig} signal days")
        ft = futures_trailing(d, dirn, atr_norm=atr_norm)
        p, null_mean = placebo_test(d, ft, lambda dd, dn: futures_trailing(dd, dn, atr_norm=atr_norm)) \
            if not ft.empty else (np.nan, np.nan)
        summ = summarize(ft, FUT_COST_PRE, f"S2_futures_{variant}_trail")
        summ["placebo_p"] = p
        summ["placebo_null_mean"] = null_mean
        summ["n_signal_days"] = n_sig
        all_summaries.append(summ)
        fut_trades_store[f"S2_futures_{variant}"] = ft
        regime_rows += regime_table(ft, d, "S2", variant)

        # options leg only if futures clears cost bar convincingly (see pre-registration)
        gross_mean = ft["gross_pts"].mean() if not ft.empty else np.nan
        clears_bar = np.isfinite(gross_mean) and gross_mean > 6.5 and len(ft) >= 10
        if clears_bar:
            log(f"S2 {variant}: futures gross {gross_mean:.2f} clears cost bar -> building options leg")
            ot = options_eod_backtest(d, dirn, "S2", variant)  # NOTE: EOD approx, not the full roll engine
            osumm = summarize(ot[ot["dropped"].isna()] if not ot.empty else ot, OPT_COST_PTS,
                               f"S2_options_{variant}_APPROX")
            osumm["caveat"] = "APPROX same-day EOD proxy, NOT the multi-day roll engine (see notes)"
            all_summaries.append(osumm)
        else:
            log(f"S2 {variant}: futures gross {gross_mean if np.isfinite(gross_mean) else float('nan'):.2f} "
                f"pts does NOT clear the 6.5pt futures cost bar (or n={len(ft)}<10) -> "
                f"options leg (theta+roll on top of the same signal) NOT built, kill-fast per pre-reg")
            all_summaries.append({"label": f"S2_options_{variant}", "n": 0,
                                   "not_built_reason": "futures signal failed cost bar or n<10; "
                                                        "options leg strictly worse (theta+roll on top "
                                                        "of the same dead/thin direction) -- not built"})

    # ---------- Strategy 3: gap breakout continuation ----------
    for variant, atr_norm in [("atr_normalised", True), ("raw_points", False)]:
        dirn = sig_gap(d, atr_norm=atr_norm)
        n_sig = int((dirn != 0).sum())
        log(f"S3 gap {variant}: {n_sig} signal days")
        ft = futures_eod(d, dirn, "S3")
        ft2 = futures_holdN(d, dirn, 2)
        p, null_mean = placebo_test(d, ft, futures_eod)
        summ = summarize(ft, FUT_COST_PRE, f"S3_futures_{variant}_eod")
        summ["placebo_p"] = p
        summ["placebo_null_mean"] = null_mean
        summ["secondary_2day_hold_mean_net"] = float(ft2["net_pts"].mean()) if not ft2.empty else np.nan
        all_summaries.append(summ)
        fut_trades_store[f"S3_futures_{variant}"] = ft
        regime_rows += regime_table(ft, d, "S3", variant)

        ot = options_eod_backtest(d, dirn, "S3", variant)
        ot_ok = ot[ot["dropped"].isna()] if not ot.empty and "dropped" in ot.columns else ot
        osumm = summarize(ot_ok, OPT_COST_PTS, f"S3_options_{variant}_eod")
        osumm["n_events_scanned"] = len(ot)
        osumm["n_dropped"] = int(ot["dropped"].notna().sum()) if not ot.empty else 0
        all_summaries.append(osumm)
        opt_trades_store[f"S3_options_{variant}"] = ot

    # ---------- write outputs ----------
    for name, tt in fut_trades_store.items():
        tt.to_csv(OUT / f"futures_trades_{name}.csv", index=False)
    for name, tt in opt_trades_store.items():
        tt.to_csv(OUT / f"options_trades_{name}.csv", index=False)
    pd.DataFrame(regime_rows).to_csv(OUT / "regime_conditioning.csv", index=False)
    (OUT / "summary.json").write_text(json.dumps(all_summaries, indent=2, default=str), encoding="utf-8")
    (OUT / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"DONE. wrote {len(fut_trades_store)} futures trade files, {len(opt_trades_store)} options "
        f"trade files, summary.json ({len(all_summaries)} cells), regime_conditioning.csv "
        f"({len(regime_rows)} rows)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        (OUT / "ERROR.txt").write_text(traceback.format_exc(), encoding="utf-8")
        print(traceback.format_exc(), flush=True)
        raise
