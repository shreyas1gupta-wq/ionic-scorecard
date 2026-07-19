"""WAVE-3 resurrection #1: EVENT-TIME PEAD (post-earnings-announcement drift).
PEAD was KILLED at MONTHLY panel frequency (W2_event_pead_sign_1M: IC_IR -0.19,
lag_test_delta 1.07 -- FAILED, likely because forcing the surprise signal onto a
calendar-month rebalance grid smears/misaligns the true event clock). Re-test
genuinely in EVENT TIME: one row per (symbol, earnings print), abnormal return
measured over a FIXED post-event window [+2 trading days, +45 calendar days]
anchored to the REAL announcement date, not a monthly panel date.

Data (reuses existing PIT-audited builders, no new lookahead surface):
  - builders_w2_event.load_quarterly_pit() -- symbol, period_end, available_date
    (real NSE board-meeting date where matched, else disclosed fallback_45d --
    EXCLUDED here, since a fallback date carries no real event-day anchor),
    np_surprise = (actual net profit - own-trailing-4Q-trend expectation) / |expectation|,
    built entirely from already-public prior prints (no forward info).
  - rnd/panel/cube_close_long.parquet (date x symbol daily close, 2005-2026)
    and cube_bench_long.parquet (NIFTY500 daily index) -- per the task brief,
    used for the daily-granularity abnormal-return measurement.

Method: market-adjusted event study (stock cum-return minus NIFTY500 cum-return
over the identical trading-day window per event) -- a simpler, fully disclosed
alternative to a full FF-residual (the monthly panel's 'resid' basis is not
defined at daily/event granularity here).

Hard gates (per WAVE-3 brief): lag-test + placebo. PBO/DSR not computed (this is
a pooled event-level test, not a calendar-date panel -- the harness's per-date
CSCV/DSR machinery does not apply; disclosed, not silently skipped).
"""
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(_LIB))

import json
import numpy as np
import pandas as pd
from scipy import stats

import builders_w2_event as w2

RND_DIR = _LIB.parent
CUBE_CLOSE = RND_DIR / "panel" / "cube_close_long.parquet"
CUBE_BENCH = RND_DIR / "panel" / "cube_bench_long.parquet"
CARDS_DIR = RND_DIR / "cards"

START_LAG_TDAYS = 2       # skip 2 trading days (avoid the announcement-day gap itself)
END_LAG_CDAYS = 45        # window end = available_date + 45 calendar days


def _event_window_returns(events: pd.DataFrame, close: pd.DataFrame, bench: pd.Series) -> pd.DataFrame:
    """events: symbol, available_date. Returns events + start_date/end_date/
    stock_ret/bench_ret/abn_ret, event-time (per symbol trading-day offsets)."""
    idx = close.index
    n = len(idx)
    col_pos = pd.Series(np.arange(close.shape[1]), index=close.columns)
    vals = close.to_numpy()
    bvals = bench.to_numpy()

    dt_arr = pd.DatetimeIndex(events["available_date"])
    event_pos = idx.searchsorted(dt_arr)                      # first trading day >= available_date
    start_pos = np.clip(event_pos + START_LAG_TDAYS, 0, n - 1)
    end_dt = dt_arr + pd.Timedelta(days=END_LAG_CDAYS)
    end_pos = np.clip(idx.searchsorted(end_dt, side="right") - 1, 0, n - 1)

    sym_ok = events["symbol"].isin(col_pos.index).to_numpy()
    cidx = np.where(sym_ok, col_pos.reindex(events["symbol"]).fillna(-1).to_numpy().astype(int), -1)
    valid = sym_ok & (cidx >= 0) & (event_pos > 0) & (event_pos < n - 1) & (end_pos > start_pos)

    out = events.copy()
    out["event_pos"] = event_pos
    out["start_pos"] = start_pos
    out["end_pos"] = end_pos
    out["start_date"] = idx[np.clip(start_pos, 0, n - 1)]
    out["end_date"] = idx[np.clip(end_pos, 0, n - 1)]

    stock_ret = np.full(len(events), np.nan)
    bench_ret = np.full(len(events), np.nan)
    idxs = np.where(valid)[0]
    if len(idxs):
        c0 = vals[start_pos[idxs], cidx[idxs]]
        c1 = vals[end_pos[idxs], cidx[idxs]]
        b0 = bvals[start_pos[idxs]]
        b1 = bvals[end_pos[idxs]]
        with np.errstate(invalid="ignore", divide="ignore"):
            stock_ret[idxs] = np.where(c0 > 0, c1 / c0 - 1, np.nan)
            bench_ret[idxs] = np.where(b0 > 0, b1 / b0 - 1, np.nan)
    out["stock_ret"] = stock_ret
    out["bench_ret"] = bench_ret
    out["abn_ret"] = out["stock_ret"] - out["bench_ret"]
    return out[valid]


def _winsorize(s: pd.Series, lo=0.01, hi=0.99) -> pd.Series:
    ql, qh = s.quantile(lo), s.quantile(hi)
    return s.clip(ql, qh)


def _shuffled_ic(surprise: np.ndarray, ret: np.ndarray, n_draws=5, seed=42) -> float:
    rng = np.random.default_rng(seed)
    ics = []
    for _ in range(n_draws):
        perm = rng.permutation(len(surprise))
        ic, _ = stats.spearmanr(surprise[perm], ret)
        ics.append(ic)
    return float(np.nanmean(ics))


def main():
    close = pd.read_parquet(CUBE_CLOSE)
    bench_df = pd.read_parquet(CUBE_BENCH)
    bench = bench_df.iloc[:, 0]
    close.index = pd.to_datetime(close.index)
    bench.index = pd.to_datetime(bench_df.index)

    q = w2.load_quarterly_pit()
    q = q[q["date_source"] == "actual"].dropna(subset=["np_surprise"]).copy()
    q = q[["symbol", "period_end", "available_date", "np_surprise", "np_surprise_sign"]]
    q = q.sort_values(["symbol", "period_end"]).reset_index(drop=True)

    # prior-quarter surprise per symbol (for the lag test)
    q["np_surprise_prior_q"] = q.groupby("symbol")["np_surprise"].shift(1)

    print(f"events with real date + surprise: {len(q)}")
    ev = _event_window_returns(q, close, bench)
    print(f"events with a valid abnormal-return window: {len(ev)} "
          f"({len(ev)/len(q):.1%} of candidates; drops = delisted/no-cube-coverage/edge-of-history)")
    print(f"event available_date range: {ev['available_date'].min().date()} -> {ev['available_date'].max().date()}")

    ev["surprise_w"] = _winsorize(ev["np_surprise"])
    ev = ev.dropna(subset=["abn_ret", "surprise_w"])
    print(f"final n (non-NaN abn_ret & surprise): {len(ev)}")

    # ---- IC (event-level Spearman, pooled across all quarters/symbols) ----
    ic, ic_p = stats.spearmanr(ev["surprise_w"], ev["abn_ret"])
    ic_sign, ic_sign_p = stats.spearmanr(ev["np_surprise_sign"], ev["abn_ret"])

    # ---- decile monotonicity + long-short ----
    ev["decile"] = pd.qcut(ev["surprise_w"], 10, labels=False, duplicates="drop")
    dec_mean = ev.groupby("decile")["abn_ret"].mean()
    mono, _ = stats.spearmanr(dec_mean.index, dec_mean.values)
    top = dec_mean.iloc[-1]
    bot = dec_mean.iloc[0]
    ls_spread = top - bot
    hit_rate = float((np.sign(ev["surprise_w"]) == np.sign(ev["abn_ret"])).mean())
    ann_factor = 365.0 / END_LAG_CDAYS
    ls_ann = (1 + ls_spread) ** ann_factor - 1 if ls_spread > -1 else np.nan

    # ---- placebo: shuffle surprise labels across events ----
    placebo_ic = _shuffled_ic(ev["surprise_w"].to_numpy(), ev["abn_ret"].to_numpy())

    # ---- lag test: use PRIOR-quarter's surprise to "predict" THIS window ----
    ev_lag = ev.dropna(subset=["np_surprise_prior_q"]).copy()
    ev_lag["prior_w"] = _winsorize(ev_lag["np_surprise_prior_q"])
    ic_lag, ic_lag_p = stats.spearmanr(ev_lag["prior_w"], ev_lag["abn_ret"]) if len(ev_lag) > 30 else (np.nan, np.nan)
    lag_test_delta = abs(ic_lag - ic) / abs(ic) if (ic not in (0, np.nan) and not np.isnan(ic_lag)) else np.nan

    # ---- sub-window drift decomposition (does drift persist across the window,
    # i.e. is this genuinely EVENT-TIME drift, not a 2-day pop?) ----
    sub_windows = [(2, 10), (10, 20), (20, 45)]
    sub_results = {}
    idx = close.index
    col_pos = pd.Series(np.arange(close.shape[1]), index=close.columns)
    vals = close.to_numpy()
    bvals = bench.to_numpy()
    n = len(idx)
    for a, b in sub_windows:
        dt_arr = pd.DatetimeIndex(ev["available_date"])
        event_pos = idx.searchsorted(dt_arr)
        p0 = np.clip(event_pos + a, 0, n - 1)
        end_dt = dt_arr + pd.Timedelta(days=b)
        p1 = np.clip(idx.searchsorted(end_dt, side="right") - 1, 0, n - 1)
        cidx = col_pos.reindex(ev["symbol"]).fillna(-1).to_numpy().astype(int)
        valid = (cidx >= 0) & (p1 > p0) & (p0 > 0) & (p1 < n - 1)
        sr = np.full(len(ev), np.nan)
        br = np.full(len(ev), np.nan)
        idxs = np.where(valid)[0]
        c0 = vals[p0[idxs], cidx[idxs]]; c1 = vals[p1[idxs], cidx[idxs]]
        b0 = bvals[p0[idxs]]; b1 = bvals[p1[idxs]]
        with np.errstate(invalid="ignore", divide="ignore"):
            sr[idxs] = np.where(c0 > 0, c1 / c0 - 1, np.nan)
            br[idxs] = np.where(b0 > 0, b1 / b0 - 1, np.nan)
        abn = sr - br
        m = ~np.isnan(abn) & ~np.isnan(ev["surprise_w"].to_numpy())
        sub_ic, _ = stats.spearmanr(ev["surprise_w"].to_numpy()[m], abn[m])
        sub_results[f"[+{a}d,+{b}d]"] = {"ic": float(sub_ic), "n": int(m.sum())}

    card = {
        "factor_id": "W3_pead_eventtime",
        "family": "W3_pead",
        "method": "event-time market-adjusted event study (NOT monthly panel harness)",
        "n_events_candidate": int(len(q)),
        "n_events_valid": int(len(ev)),
        "date_range": [str(ev["available_date"].min().date()), str(ev["available_date"].max().date())],
        "window": f"[+{START_LAG_TDAYS}td, +{END_LAG_CDAYS}cd]",
        "ic_continuous_surprise": {"ic": float(ic), "p_value": float(ic_p)},
        "ic_surprise_sign": {"ic": float(ic_sign), "p_value": float(ic_sign_p)},
        "monotonicity": float(mono),
        "decile_means": {str(k): float(v) for k, v in dec_mean.items()},
        "long_short": {"spread_raw_window": float(ls_spread), "spread_ann_approx": float(ls_ann),
                       "hit_rate": hit_rate},
        "placebo_ic": placebo_ic,
        "lag_test": {"ic_prior_quarter_surprise": float(ic_lag) if not np.isnan(ic_lag) else None,
                     "lag_test_delta": float(lag_test_delta) if not np.isnan(lag_test_delta) else None,
                     "n_lag": int(len(ev_lag))},
        "sub_window_drift": sub_results,
        "hard_gate_verdict": None,  # filled below
    }

    # explicit, readable gate logic (money-first: hard gates = lag + placebo only)
    lag_ok = (lag_test_delta is not None) and (not np.isnan(lag_test_delta)) and (lag_test_delta > 0.25)
    placebo_ok = abs(placebo_ic) <= 0.02
    signal_present = abs(ic) >= 0.02 and mono >= 0.5 and ic_p < 0.05
    if not signal_present:
        verdict = "KILL (no economically/statistically meaningful IC or non-monotone deciles)"
    elif not lag_ok:
        verdict = "KILL (lag_test_delta <= 0.25 -- prior-quarter stale surprise explains as much as the real one -> not a genuine event-specific effect)"
    elif not placebo_ok:
        verdict = "KILL (placebo_ic > 0.02 -- shuffle-null not clean)"
    else:
        verdict = "PROMOTE/PARK candidate (passes both hard gates: lag + placebo) -- advisory PBO/DSR N/A (event-level test, not calendar-panel)"
    card["hard_gate_verdict"] = verdict

    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    (CARDS_DIR / "W3_pead_eventtime.json").write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")

    print("\n=== W3_pead_eventtime ===")
    print(f"n_events valid: {len(ev)}")
    print(f"IC (continuous surprise vs abn_ret): {ic:.4f} (p={ic_p:.4f})")
    print(f"IC (surprise SIGN vs abn_ret): {ic_sign:.4f} (p={ic_sign_p:.4f})")
    print(f"monotonicity: {mono:.3f}")
    print(f"decile means: {dec_mean.round(4).to_dict()}")
    print(f"LS spread (raw, ~{END_LAG_CDAYS}d window): {ls_spread:.4f}  ann_approx: {ls_ann:.4f}  hit_rate: {hit_rate:.3f}")
    print(f"placebo_ic (shuffle-null, 5 draws): {placebo_ic:.4f}")
    print(f"lag test -- IC using PRIOR-quarter surprise: {ic_lag}  lag_test_delta: {lag_test_delta}")
    print(f"sub-window drift decomposition: {sub_results}")
    print(f"\nVERDICT: {verdict}")


if __name__ == "__main__":
    main()
