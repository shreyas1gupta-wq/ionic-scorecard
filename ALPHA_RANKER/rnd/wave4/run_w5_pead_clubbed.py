"""WAVE-5 PEAD_CLUBBED: does clubbing the earnings-surprise signal with technical
confirmation (Minervini earnings-breakout pattern: top-decile surprise AND
volume-surge AND gap-up AND uptrend) revive the plain-PEAD signal that was
KILLED at event-time (W3_pead_eventtime: IC -0.003, n=2642)?

Reuses the EXACT event-window construction from run_w3_pead_eventtime.py
(market-adjusted abn_ret over [+2td, +45cd] anchored to available_date) so the
"plain PEAD" baseline here is directly comparable to the killed W3 card.

NO LOOKAHEAD:
  - np_surprise is PIT (available_date = real board-meeting date, from
    builders_w2_event.load_quarterly_pit(), date_source=='actual' only).
  - volume-surge and uptrend use ONLY data at/before the event reaction day
    (event_pos); trailing median volume window explicitly excludes the
    event day and the run-up days immediately before it.
  - gap-up uses the close(event_pos-1) -> close(event_pos) move, i.e. the
    announcement REACTION day itself -- known at end of event_pos, not before.

RECENT-ERA CAVEAT: cube_volume.parquet starts 2021-07-16. The underlying
quarterly-PIT dataset itself is already ~2020+ (candidate pool date range
2020-01-30 -> 2025-11-14, per the W3 card), so restricting to
available_date >= 2021-07-16 removes only a handful of 2020 events -- this
is NOT a large truncation of the existing PEAD test, but it IS true that
NEITHER the plain-PEAD W3 result NOR this clubbed test has any pre-2020
coverage. Flagged, not hidden.

GAP-UP PROXY CAVEAT: no cube_open_long.parquet exists (checked: only
cube_close_long / cube_bench_long / cube_volume). "Gap-up" is therefore
proxied by the close(t-1)->close(t) return on the reaction day, NOT a true
09:15 opening gap. This is a data-availability limitation, disclosed.
"""
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(_LIB))

import json
import numpy as np
import pandas as pd
from scipy import stats

import builders_w2_event as w2
from run_w3_pead_eventtime import _event_window_returns, _winsorize, START_LAG_TDAYS, END_LAG_CDAYS

RND_DIR = _LIB.parent
CUBE_CLOSE = RND_DIR / "panel" / "cube_close_long.parquet"
CUBE_BENCH = RND_DIR / "panel" / "cube_bench_long.parquet"
CUBE_VOLUME = RND_DIR / "panel" / "cube_volume.parquet"
CARDS_DIR = RND_DIR / "cards"
WAVE4_DIR = RND_DIR / "wave4"

VOLUME_START = pd.Timestamp("2021-07-16")   # cube_volume.parquet hard start
MA_WINDOW = 150                              # Minervini "key MA" (150DMA)
VOL_LOOKBACK = 60                            # trailing sessions for "normal" volume
VOL_GAP_DAYS = 3                             # exclude last 3 pre-event sessions from the trailing-median calc (pre-earnings run-up)
GAPUP_THRESH = 0.02                          # +2% reaction-day proxy-gap threshold
MIN_N_FOR_STATS = 30                         # low-t rule: below this, magnitude/mechanism only, no significance claims


def _trailing_ma(close: pd.DataFrame, window: int) -> pd.DataFrame:
    return close.rolling(window, min_periods=window).mean()


def _volume_surge_ratio(vol: pd.DataFrame, event_pos: np.ndarray, cidx: np.ndarray, n: int) -> np.ndarray:
    """max volume in [event_pos, event_pos+2] / trailing median volume in
    [event_pos-VOL_LOOKBACK-VOL_GAP_DAYS, event_pos-VOL_GAP_DAYS) (pre-event, gap-excluded)."""
    vvals = vol.to_numpy()
    out = np.full(len(event_pos), np.nan)
    for i in range(len(event_pos)):
        c = cidx[i]
        if c < 0:
            continue
        e = event_pos[i]
        post_lo, post_hi = e, min(e + 2, n - 1)
        pre_lo = max(e - VOL_LOOKBACK - VOL_GAP_DAYS, 0)
        pre_hi = max(e - VOL_GAP_DAYS, 0)
        if pre_hi - pre_lo < 20 or post_hi < post_lo:
            continue
        post_slice = vvals[post_lo:post_hi + 1, c]
        pre_slice = vvals[pre_lo:pre_hi, c]
        if np.all(np.isnan(post_slice)) or np.all(np.isnan(pre_slice)):
            continue
        post_vol = np.nanmax(post_slice)
        pre_vol = np.nanmedian(pre_slice)
        if pre_vol > 0 and not np.isnan(post_vol):
            out[i] = post_vol / pre_vol
    return out


def _skew_and_tail(x: pd.Series) -> dict:
    x = x.dropna()
    if len(x) < 5:
        return {"skew": None, "p10": None, "p90": None, "upside_over_downside": None}
    sk = float(stats.skew(x))
    p10, p90 = float(x.quantile(0.10)), float(x.quantile(0.90))
    med = float(x.median())
    upside = x[x > 0].mean() if (x > 0).any() else np.nan
    downside = x[x < 0].mean() if (x < 0).any() else np.nan
    ratio = float(abs(upside / downside)) if (downside is not None and downside != 0 and not np.isnan(downside)) else None
    return {"skew": sk, "p10": p10, "p90": p90, "median": med,
            "mean_upside": float(upside) if not np.isnan(upside) else None,
            "mean_downside": float(downside) if not np.isnan(downside) else None,
            "upside_over_downside_abs": ratio}


def _group_stats(name: str, ev: pd.DataFrame) -> dict:
    n = len(ev)
    r = ev["abn_ret"]
    stat = {
        "group": name,
        "n": int(n),
        "low_t_flag": n < MIN_N_FOR_STATS,
        "mean_abn_ret": float(r.mean()) if n else None,
        "median_abn_ret": float(r.median()) if n else None,
        "hit_rate_positive": float((r > 0).mean()) if n else None,
        "hit_rate_vs_plain_sign": None,
    }
    stat.update(_skew_and_tail(r))
    return stat


def main():
    close = pd.read_parquet(CUBE_CLOSE)
    bench_df = pd.read_parquet(CUBE_BENCH)
    bench = bench_df.iloc[:, 0]
    close.index = pd.to_datetime(close.index)
    bench.index = pd.to_datetime(bench_df.index)
    vol = pd.read_parquet(CUBE_VOLUME)
    vol.index = pd.to_datetime(vol.index)
    vol_syms = set(vol.columns)   # true volume-covered symbols, captured BEFORE column-reindex below
    vol = vol.reindex(index=close.index, columns=close.columns)   # align rows+cols to close's frame so event_pos/cidx (computed off close) index correctly

    q = w2.load_quarterly_pit()
    q = q[q["date_source"] == "actual"].dropna(subset=["np_surprise"]).copy()
    q = q[["symbol", "period_end", "available_date", "np_surprise", "np_surprise_sign"]]
    q = q.sort_values(["symbol", "period_end"]).reset_index(drop=True)
    print(f"candidate events (PIT, real date, has surprise): {len(q)}")

    ev = _event_window_returns(q, close, bench)
    ev["surprise_w"] = _winsorize(ev["np_surprise"])
    ev = ev.dropna(subset=["abn_ret", "surprise_w"]).reset_index(drop=True)
    print(f"plain-PEAD (W3-matching, full available range) n = {len(ev)}  "
          f"date range {ev['available_date'].min().date()} -> {ev['available_date'].max().date()}")

    # ---- restrict to volume-covered universe (RECENT-ERA ONLY) ----
    ev_r = ev[(ev["available_date"] >= VOLUME_START) & (ev["symbol"].isin(vol_syms))].copy()
    print(f"recent-era matched subsample (available_date>={VOLUME_START.date()}, symbol has volume coverage): n = {len(ev_r)}")
    print("*** RECENT-ERA-ONLY: this whole test (and its 'plain PEAD' comparator below) covers only "
          f"{ev_r['available_date'].min().date() if len(ev_r) else 'n/a'} -> "
          f"{ev_r['available_date'].max().date() if len(ev_r) else 'n/a'} because cube_volume.parquet starts 2021-07-16. ***")

    if len(ev_r) == 0:
        print("NO EVENTS in recent-era matched subsample -- aborting.")
        return

    # ---- technical features, computed at/around event_pos only (no lookahead) ----
    idx = close.index
    n = len(idx)
    col_pos = pd.Series(np.arange(close.shape[1]), index=close.columns)
    cidx = col_pos.reindex(ev_r["symbol"]).fillna(-1).to_numpy().astype(int)
    event_pos = ev_r["event_pos"].to_numpy()

    # gap-up proxy: close(event_pos-1) -> close(event_pos), the reaction day itself
    cvals = close.to_numpy()
    prev_pos = np.clip(event_pos - 1, 0, n - 1)
    c_prev = np.array([cvals[prev_pos[i], cidx[i]] if cidx[i] >= 0 else np.nan for i in range(len(ev_r))])
    c_evt = np.array([cvals[event_pos[i], cidx[i]] if cidx[i] >= 0 else np.nan for i in range(len(ev_r))])
    with np.errstate(invalid="ignore", divide="ignore"):
        ev_r["gap_ret_proxy"] = np.where(c_prev > 0, c_evt / c_prev - 1, np.nan)
    ev_r["gap_up"] = ev_r["gap_ret_proxy"] > GAPUP_THRESH

    # uptrend: close(event_pos) above trailing 150DMA (trailing window ending at event_pos -- no forward peek)
    ma150 = _trailing_ma(close, MA_WINDOW)
    mvals = ma150.to_numpy()
    ma_at_evt = np.array([mvals[event_pos[i], cidx[i]] if cidx[i] >= 0 else np.nan for i in range(len(ev_r))])
    ev_r["ma150_at_event"] = ma_at_evt
    ev_r["uptrend"] = (~np.isnan(ma_at_evt)) & (c_evt > ma_at_evt)

    # volume surge: max post-print vol[event_pos, event_pos+2] / trailing pre-event median (gap-excluded)
    ev_r["vol_surge_ratio"] = _volume_surge_ratio(vol, event_pos, cidx, n)

    for col in ["gap_ret_proxy", "ma150_at_event", "vol_surge_ratio"]:
        n_valid = ev_r[col].notna().sum()
        print(f"  feature '{col}': {n_valid}/{len(ev_r)} valid ({n_valid/len(ev_r):.1%})")

    # top-decile surprise WITHIN the recent-era matched subsample
    ev_r["decile"] = pd.qcut(ev_r["surprise_w"], 10, labels=False, duplicates="drop")
    top_decile = int(ev_r["decile"].max())
    ev_r["top_decile_surprise"] = ev_r["decile"] == top_decile

    results = {}
    results["plain_PEAD_matched"] = _group_stats("plain_PEAD_matched (recent-era, volume-covered universe, ALL surprises)", ev_r)
    results["random_same_period"] = _group_stats("random_same_period (== full matched universe, same as plain_PEAD_matched by construction)", ev_r)

    ev_top = ev_r[ev_r["top_decile_surprise"]]
    results["surprise_top_decile_only"] = _group_stats("surprise_top_decile_ONLY (no technical filter)", ev_top)

    for Nx in (2.0, 3.0):
        club_vol = ev_top[ev_top["vol_surge_ratio"] > Nx]
        results[f"surprise+volsurge_{Nx}x_only"] = _group_stats(f"surprise_top_decile + volume_surge>{Nx}x (intermediate club A)", club_vol)

    club_trend = ev_top[ev_top["uptrend"]]
    results["surprise+uptrend_only"] = _group_stats("surprise_top_decile + uptrend (intermediate club B)", club_trend)

    club_gap = ev_top[ev_top["gap_up"]]
    results["surprise+gapup_only"] = _group_stats("surprise_top_decile + gap_up (intermediate club C)", club_gap)

    for Nx in (2.0, 3.0):
        full_club = ev_top[(ev_top["vol_surge_ratio"] > Nx) & ev_top["gap_up"] & ev_top["uptrend"]]
        results[f"FULL_CLUB_{Nx}x"] = _group_stats(
            f"FULL CLUB: surprise_top_decile + volsurge>{Nx}x + gap_up>{GAPUP_THRESH:.0%} + uptrend(>{MA_WINDOW}DMA)",
            full_club)

    # hit-rate vs plain PEAD sign-match (does the clubbed subset beat plain PEAD's coin-flip hit rate?)
    plain_hit = results["plain_PEAD_matched"]["hit_rate_positive"]
    for k, v in results.items():
        if v["hit_rate_positive"] is not None and plain_hit is not None:
            v["hit_rate_delta_vs_plain"] = round(v["hit_rate_positive"] - plain_hit, 4)

    card = {
        "factor_id": "W5PC_pead_clubbed",
        "family": "W5_pead_technical_overlay",
        "method": "event-time market-adjusted abn_ret (same construction as W3_pead_eventtime), "
                  "RECENT-ERA restricted (available_date>=2021-07-16, cube_volume coverage), "
                  "technical confirmation = top-decile surprise AND volume-surge AND gap-up-proxy AND uptrend(150DMA)",
        "window": f"[+{START_LAG_TDAYS}td, +{END_LAG_CDAYS}cd]",
        "recent_era_caveat": f"cube_volume.parquet starts {VOLUME_START.date()}; NO pre-2021-07 coverage in this test",
        "gapup_proxy_caveat": "no cube_open_long.parquet exists; gap_up proxied by close(t-1)->close(t) reaction-day return, NOT true 09:15 opening gap",
        "low_t_rule": f"groups with n<{MIN_N_FOR_STATS} are flagged low_t_flag=true -- judge by effect size/mechanism, not p-values",
        "n_candidate_full_history": int(len(q)),
        "n_plain_pead_w3_matching": int(len(ev)),
        "n_recent_era_matched_universe": int(len(ev_r)),
        "results": results,
    }

    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    (CARDS_DIR / "W5PC_pead_clubbed.json").write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")
    ev_r.to_parquet(WAVE4_DIR / "w5pc_event_level.parquet")

    print("\n=== RESULTS TABLE ===")
    for k, v in results.items():
        print(f"{k:32s} n={v['n']:5d}  mean={v['mean_abn_ret']}  hit={v['hit_rate_positive']}  "
              f"skew={v['skew']}  low_t={v['low_t_flag']}")

    print("\nJSON card -> ", CARDS_DIR / "W5PC_pead_clubbed.json")
    print("event-level parquet -> ", WAVE4_DIR / "w5pc_event_level.parquet")


if __name__ == "__main__":
    main()
