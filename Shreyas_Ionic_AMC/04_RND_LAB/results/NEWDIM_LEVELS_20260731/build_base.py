"""NEWDIM_LEVELS_20260731 -- build_base.py
Builds daily/weekly OHLC + ATR14(Wilder, PIT-safe) + range-compression flags (NR7/NR4/pctile)
+ 15-min swing-pivot table, from NIFTY 1-min spot. Mirrors PRICE_LEVELS_20260730/build_daily.py
methodology exactly (same no-lookahead discipline) but adds the compression features this new
mandate needs. Also joins India VIX daily for the regime-conditioning cut.
"""
import pandas as pd
import numpy as np

RAW = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"
VIX_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\indices_close"


def build_daily_weekly(df):
    g = df.groupby("date")
    daily = g.agg(open=("open", "first"), high=("high", "max"),
                   low=("low", "min"), close=("close", "last")).sort_index()
    prev_close = daily["close"].shift(1)
    tr = pd.concat([
        daily["high"] - daily["low"],
        (daily["high"] - prev_close).abs(),
        (daily["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    daily["tr"] = tr
    daily["atr14"] = atr
    daily["atr14_prior"] = daily["atr14"].shift(1)
    daily["prior_close"] = daily["close"].shift(1)
    daily["prior_high"] = daily["high"].shift(1)
    daily["prior_low"] = daily["low"].shift(1)
    daily["day_range"] = daily["high"] - daily["low"]

    # ---- range-compression features, all computed from info through TODAY's own close
    # (fired the NEXT day at open, same discipline as touch_engine's next-bar-open entry) ----
    daily["range_atr_ratio"] = daily["day_range"] / daily["atr14_prior"]
    # NR7 / NR4: today's range is the smallest of the trailing 7 / 4 days (incl today)
    daily["nr7"] = daily["day_range"] == daily["day_range"].rolling(7).min()
    daily["nr4"] = daily["day_range"] == daily["day_range"].rolling(4).min()
    # inside bar: today's H<=prior H and today's L>=prior L
    daily["inside_bar"] = (daily["high"] <= daily["prior_high"]) & (daily["low"] >= daily["prior_low"])
    # trailing-100d percentile rank of range_atr_ratio (as-of today's close; expanding after 100)
    daily["range_pctile_100"] = daily["range_atr_ratio"].rolling(100, min_periods=30).apply(
        lambda x: (x.iloc[:-1] < x.iloc[-1]).mean() if len(x) > 1 else np.nan, raw=False)
    # N-day high/low the breakout is measured against (prior 4 days, EXCLUDING today, so a
    # trade taken tomorrow breaks a level fixed before today's own range even forms)
    daily["prior4_high"] = daily["high"].shift(1).rolling(4).max()
    daily["prior4_low"] = daily["low"].shift(1).rolling(4).min()
    daily["prior7_high"] = daily["high"].shift(1).rolling(7).max()
    daily["prior7_low"] = daily["low"].shift(1).rolling(7).min()
    # 4-day BALANCE-AREA compression (distinct from single-day NR4/NR7): is the trailing 4-day
    # box itself unusually narrow vs ATR? Fully known before D's open (uses D-4..D-1 only).
    daily["box4_width"] = daily["prior4_high"] - daily["prior4_low"]
    daily["box4_ratio"] = daily["box4_width"] / daily["atr14_prior"]
    daily["box4_pctile_100"] = daily["box4_ratio"].rolling(100, min_periods=30).apply(
        lambda x: (x.iloc[:-1] < x.iloc[-1]).mean() if len(x) > 1 else np.nan, raw=False)

    wk_key = daily.index.to_series().dt.to_period("W-FRI")
    wk = daily.groupby(wk_key).agg(open=("open", "first"), high=("high", "max"),
                                    low=("low", "min"), close=("close", "last")).sort_index()
    daily["wk_key"] = wk_key.values
    daily["mo_key"] = daily.index.to_period("M")
    daily = daily.drop(columns=[])
    return daily, wk


def build_swing_pivots(bars15, left=4, right=4):
    """Simple N-bar fractal swing high/low on 15-min resampled bars (for anchored-VWAP swing
    anchor). A bar is a swing high if its high is the max over [-left,+right]; PIT-safe caveat:
    a swing pivot is only KNOWN 'right' bars after it forms -- confirmed_at column records that,
    and downstream VWAP-anchor code must anchor using confirmed_at, never the pivot bar itself."""
    h = bars15["high"].to_numpy()
    l = bars15["low"].to_numpy()
    n = len(h)
    is_sh = np.zeros(n, bool)
    is_sl = np.zeros(n, bool)
    for i in range(left, n - right):
        window_h = h[i - left:i + right + 1]
        window_l = l[i - left:i + right + 1]
        if h[i] == window_h.max() and (window_h == h[i]).sum() == 1:
            is_sh[i] = True
        if l[i] == window_l.min() and (window_l == l[i]).sum() == 1:
            is_sl[i] = True
    out = bars15.copy()
    out["is_swing_high"] = is_sh
    out["is_swing_low"] = is_sl
    out["confirmed_at"] = out.index.to_series().shift(-right)
    return out


def load_vix_daily():
    frames = []
    import glob
    for f in sorted(glob.glob(VIX_DIR + r"\indices_*.parquet")):
        d = pd.read_parquet(f, columns=["Index Name", "Index Date", "Closing Index Value"])
        d = d[d["Index Name"] == "India VIX"]
        frames.append(d)
    v = pd.concat(frames, ignore_index=True)
    v["date"] = pd.to_datetime(v["Index Date"], format="mixed", dayfirst=True)
    v = v[["date", "Closing Index Value"]].rename(columns={"Closing Index Value": "vix_close"})
    v["vix_close"] = pd.to_numeric(v["vix_close"], errors="coerce")
    v = v.dropna().drop_duplicates("date").sort_values("date").set_index("date")
    # PIT: prior day's VIX close is what's usable at today's open
    v["vix_prior"] = v["vix_close"].shift(1)
    v["vix_pctile_252"] = v["vix_prior"].rolling(252, min_periods=60).apply(
        lambda x: (x.iloc[:-1] < x.iloc[-1]).mean() if len(x) > 1 else np.nan, raw=False)
    return v


def main():
    df = pd.read_parquet(RAW)
    df.index = df.index.floor("min")
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df = df[df.index.time >= pd.Timestamp("09:15").time()]
    df["date"] = df.index.normalize()

    daily, wk = build_daily_weekly(df)
    bars15 = df[["open", "high", "low", "close"]].resample("15min").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last")).dropna()
    swing = build_swing_pivots(bars15)
    vix = load_vix_daily()

    daily.to_parquet(f"{OUT}/daily.parquet")
    wk.to_parquet(f"{OUT}/weekly.parquet")
    df.to_parquet(f"{OUT}/bars_1min.parquet")
    swing.to_parquet(f"{OUT}/swing15.parquet")
    vix.to_parquet(f"{OUT}/vix_daily.parquet")

    print("daily", daily.shape, daily.index.min(), daily.index.max())
    print("nr7 true frac", daily["nr7"].mean(), "nr4 true frac", daily["nr4"].mean())
    print("range_pctile_100 nan frac", daily["range_pctile_100"].isna().mean())
    print("swing15", swing.shape, "swing_high frac", swing["is_swing_high"].mean(),
          "swing_low frac", swing["is_swing_low"].mean())
    print("vix", vix.shape, vix.index.min(), vix.index.max())


if __name__ == "__main__":
    main()
