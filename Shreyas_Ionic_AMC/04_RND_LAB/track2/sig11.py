"""SIG-11 — Signal stack v1: 8-criteria Minervini trend template (ALL-pass) + 12-1/6m momentum
+ RS cross-sectional percentile (PIT-universe-relative) + breakout-volume confirmation flag.

Per 04_RND_LAB/ideas/20260703_track2_engine_spec.md §2 + ANALYST_CHECKLISTS.md §Minervini.
NO look-ahead: every feature at date `D` uses only rows with date <= D (rolling windows,
right-closed, no centering; RS percentile computed over the PIT-tradable set AS OF D only).

Run: PYTHONIOENCODING=utf-8 python sig11.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib"))
import guards as G  # noqa

sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\track2"))
import data11 as D11

# ---------------------------------------------------------------------------
# Frozen-by-doctrine constants (spec §5 footer: "anything not in the free-param
# table is FROZEN by doctrine" — MA lengths, 52w window, RS threshold, etc.)
# ---------------------------------------------------------------------------
MA_SHORT, MA_MID, MA_LONG = 50, 150, 200          # Minervini canon
MA200_RISE_LOOKBACK = 22                          # sessions, criterion 3
SESSIONS_52W = 252                                # trading sessions ~= 52 weeks
PCT_ABOVE_52W_LOW = 0.30                          # criterion 6
PCT_WITHIN_52W_HIGH = 0.25                        # criterion 7
RS_PCT_GATE = 70.0                                # criterion 8, percentile 0-100
MOM_SKIP = 21                                     # ~1 month, 12-1 momentum skip window
MOM_12M = 252
MOM_6M = 126
RS_BLEND_W12 = 0.6                                # P2 default per §5 (w on 12-1; rest on 6m)
BREAKOUT_VOL_MULT = 1.5                           # §3 entry confirmation
VOL_AVG_WINDOW = 50

CRITERION_COLS = [
    "c1_close_above_150_200",
    "c2_150_above_200",
    "c3_200ma_rising",
    "c4_50_above_150_above_200",
    "c5_close_above_50",
    "c6_above_52w_low",
    "c7_within_52w_high",
    "c8_rs_pct_ge70",
]


def _min_history_mask(g: pd.DataFrame, min_len: int) -> pd.Series:
    """True once a symbol has >= min_len prior+current observations (no-lookahead-safe:
    purely a count of past rows, not a peek at future length)."""
    return (np.arange(1, len(g) + 1) >= min_len)


def _compute_symbol_features(g: pd.DataFrame) -> pd.DataFrame:
    """Per-symbol technical features. `g` must be sorted by date, one symbol only.
    All rolling ops are right-closed (default pandas behavior: window ending at row t
    uses rows t-window+1..t) — no centering, so nothing here peeks forward."""
    g = g.sort_values("date").reset_index(drop=True)
    close = g["close"].astype("float64")
    volume = g["volume"].astype("float64")

    ma50 = close.rolling(MA_SHORT, min_periods=MA_SHORT).mean()
    ma150 = close.rolling(MA_MID, min_periods=MA_MID).mean()
    ma200 = close.rolling(MA_LONG, min_periods=MA_LONG).mean()
    ma200_ago = ma200.shift(MA200_RISE_LOOKBACK)

    hi_252 = close.rolling(SESSIONS_52W, min_periods=SESSIONS_52W).max()
    lo_252 = close.rolling(SESSIONS_52W, min_periods=SESSIONS_52W).min()

    vol_avg_50 = volume.rolling(VOL_AVG_WINDOW, min_periods=VOL_AVG_WINDOW).mean()
    vol_avg_50_prev = vol_avg_50.shift(1)  # "its 50d average" excludes today's own volume
    breakout_vol_today = volume >= BREAKOUT_VOL_MULT * vol_avg_50_prev
    breakout_vol_prior = volume.shift(1) >= BREAKOUT_VOL_MULT * vol_avg_50.shift(2)
    breakout_vol_flag = (breakout_vol_today | breakout_vol_prior).fillna(False)

    # momentum: skip most-recent MOM_SKIP sessions, look back MOM_12M / MOM_6M sessions
    # from that skip point. mom = close[t-skip] / close[t-skip-window] - 1
    close_skip = close.shift(MOM_SKIP)
    mom_12_1 = close_skip / close_skip.shift(MOM_12M) - 1.0
    close_skip_6 = close.shift(MOM_SKIP)
    mom_6_1 = close_skip_6 / close_skip_6.shift(MOM_6M) - 1.0

    out = pd.DataFrame({
        "symbol": g["symbol"].values,
        "date": g["date"].values,
        "close": close.values,
        "volume": volume.values,
        "ma50": ma50.values,
        "ma150": ma150.values,
        "ma200": ma200.values,
        "ma200_ago": ma200_ago.values,
        "hi_252": hi_252.values,
        "lo_252": lo_252.values,
        "breakout_vol_flag": breakout_vol_flag.values,
        "mom_12_1": mom_12_1.values,
        "mom_6_1": mom_6_1.values,
    })
    return out


def _panel_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Vectorized-by-group feature build across the whole panel (all history, all symbols).
    Cached by caller if needed; kept as a plain function here for prefix-equality testability."""
    parts = [
        _compute_symbol_features(g)
        for _, g in panel.sort_values(["symbol", "date"]).groupby("symbol", sort=False)
    ]
    return pd.concat(parts, ignore_index=True)


def compute_signals(panel: pd.DataFrame, asof_date) -> pd.DataFrame:
    """Compute the SIG-11 signal stack for every PIT-tradable symbol as of `asof_date`.

    NO LOOK-AHEAD:
      - `panel` is filtered to date <= asof_date BEFORE any rolling computation, so nothing
        past asof_date can enter an MA/52w/momentum window (this also guarantees prefix
        equality: appending future rows to `panel` cannot change results for `asof_date`,
        since those rows are dropped up front).
      - the PIT universe for the cross-section (RS percentile denominator + ALL_PASS eligibility)
        is `data11.pit_universe(asof_date)` — forward-filled snapshot membership, never a
        current-day constituent list.
      - price-floor eligibility (close >= data11.PRICE_FLOOR) is evaluated on the asof-date
        row only.

    Returns one row per symbol present in the PIT universe AND with a live price print on
    asof_date, columns:
      symbol, date, close,
      c1..c8 (bool, per-criterion), ALL_PASS (bool, all 8 criteria),
      rs_pct (0-100 cross-sectional percentile of the blended momentum score, PIT-set-relative),
      mom_12_1, mom_6_1, mom_blend, breakout_vol_flag, price_floor_ok.

    Symbols with insufficient history (< MA_LONG+MA200_RISE_LOOKBACK sessions, or < SESSIONS_52W
    for the 52w criteria) get all criteria False (cannot pass on missing data) and NaN momentum
    — they are still included in the returned frame (so universe-size accounting is honest) but
    are never ALL_PASS.
    """
    asof = pd.Timestamp(asof_date)
    hist = panel[panel["date"] <= asof]
    if hist.empty:
        return pd.DataFrame(columns=["symbol", "date"] + CRITERION_COLS +
                             ["ALL_PASS", "rs_pct", "mom_12_1", "mom_6_1", "mom_blend",
                              "breakout_vol_flag", "price_floor_ok"])

    universe = D11.pit_universe(asof)
    hist = hist[hist["symbol"].isin(universe)]
    if hist.empty:
        return pd.DataFrame(columns=["symbol", "date"] + CRITERION_COLS +
                             ["ALL_PASS", "rs_pct", "mom_12_1", "mom_6_1", "mom_blend",
                              "breakout_vol_flag", "price_floor_ok"])

    feats = _panel_features(hist)
    snap = feats[feats["date"] == asof].copy()
    if snap.empty:
        return pd.DataFrame(columns=["symbol", "date"] + CRITERION_COLS +
                             ["ALL_PASS", "rs_pct", "mom_12_1", "mom_6_1", "mom_blend",
                              "breakout_vol_flag", "price_floor_ok"])

    snap["price_floor_ok"] = snap["close"] >= D11.PRICE_FLOOR

    c1 = (snap["close"] > snap["ma150"]) & (snap["close"] > snap["ma200"])
    c2 = snap["ma150"] > snap["ma200"]
    c3 = snap["ma200"] > snap["ma200_ago"]
    c4 = (snap["ma50"] > snap["ma150"]) & (snap["ma150"] > snap["ma200"])
    c5 = snap["close"] > snap["ma50"]
    c6 = snap["close"] >= (1.0 + PCT_ABOVE_52W_LOW) * snap["lo_252"]
    c7 = snap["close"] >= (1.0 - PCT_WITHIN_52W_HIGH) * snap["hi_252"]

    # RS percentile: blended momentum score, ranked ONLY across this PIT-tradable snapshot.
    snap["mom_blend"] = RS_BLEND_W12 * snap["mom_12_1"] + (1 - RS_BLEND_W12) * snap["mom_6_1"]
    valid_mom = snap["mom_blend"].notna()
    snap["rs_pct"] = np.nan
    if valid_mom.sum() > 1:
        snap.loc[valid_mom, "rs_pct"] = (
            snap.loc[valid_mom, "mom_blend"].rank(pct=True) * 100.0
        )
    elif valid_mom.sum() == 1:
        snap.loc[valid_mom, "rs_pct"] = 100.0
    c8 = snap["rs_pct"] >= RS_PCT_GATE

    # criteria that depend on NaN inputs must be False, not NaN — fillna before combining
    for name, series in zip(CRITERION_COLS, [c1, c2, c3, c4, c5, c6, c7, c8]):
        snap[name] = series.fillna(False).astype(bool)

    snap["ALL_PASS"] = snap[CRITERION_COLS].all(axis=1)

    cols = ["symbol", "date", "close"] + CRITERION_COLS + [
        "ALL_PASS", "rs_pct", "mom_12_1", "mom_6_1", "mom_blend",
        "breakout_vol_flag", "price_floor_ok",
    ]
    return snap[cols].sort_values("symbol").reset_index(drop=True)


if __name__ == "__main__":
    panel = D11.load_panel()
    for d in ["2023-06-30", "2025-06-30"]:
        sig = compute_signals(panel, d)
        uni = D11.pit_universe(d)
        n_pass = int(sig["ALL_PASS"].sum())
        pct = 100.0 * n_pass / max(len(uni), 1)
        print(f"\n=== asof {d} ===")
        print(f"PIT universe size: {len(uni)}")
        print(f"signal rows (symbol has a print on/before this date & in universe): {len(sig)}")
        print(f"ALL_PASS count: {n_pass}  ({pct:.2f}% of universe)")
        examples = (sig[sig["ALL_PASS"]]
                    .sort_values("rs_pct", ascending=False)
                    .head(5)[["symbol", "rs_pct", "mom_12_1", "close"]])
        print(examples.to_string(index=False))
        if pct > 15.0:
            print("!!! SANITY FLAG: ALL_PASS > 15% of universe — investigate before reporting.")
