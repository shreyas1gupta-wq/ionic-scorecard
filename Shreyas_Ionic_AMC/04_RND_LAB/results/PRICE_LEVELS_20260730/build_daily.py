"""Build daily/weekly OHLC + ATR14 + opening-range tables from NIFTY 1-min spot.
No lookahead: every "prior day"/"prior week"/"ATR" value used on day D is shift(1)'d
so it only reflects information available before D's 09:15 open.
Bank to disk: daily.parquet, weekly.parquet, bars_by_day.parquet (index kept, just re-save
for fast reload).
"""
import pandas as pd
import numpy as np

RAW = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"

def main():
    df = pd.read_parquet(RAW)
    df.index = df.index.floor("min")
    df = df[~df.index.duplicated(keep="first")].sort_index()
    # landmine: keep only bars >= 09:15 (pre-open auction guard, belt-and-braces even though
    # this processed file already appears to start at 09:15)
    df = df[df.index.time >= pd.Timestamp("09:15").time()]
    df["date"] = df.index.normalize()

    # ---------------------------------------------------------------- daily OHLC
    g = df.groupby("date")
    daily = g.agg(open=("open", "first"), high=("high", "max"),
                   low=("low", "min"), close=("close", "last")).sort_index()

    # ---------------------------------------------------------------- ATR14 (Wilder), no lookahead
    prev_close = daily["close"].shift(1)
    tr = pd.concat([
        daily["high"] - daily["low"],
        (daily["high"] - prev_close).abs(),
        (daily["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    daily["tr"] = tr
    daily["atr14"] = atr
    # value usable ON day D = ATR computed through D-1 close (shift 1)
    daily["atr14_prior"] = daily["atr14"].shift(1)
    daily["prior_close"] = daily["close"].shift(1)
    daily["prior_high"] = daily["high"].shift(1)
    daily["prior_low"] = daily["low"].shift(1)
    daily["day_range"] = daily["high"] - daily["low"]

    # ---------------------------------------------------------------- weekly OHLC (W-FRI buckets)
    wk_key = daily.index.to_series().dt.to_period("W-FRI")
    wk = daily.groupby(wk_key).agg(open=("open", "first"), high=("high", "max"),
                                    low=("low", "min"), close=("close", "last"))
    wk = wk.sort_index()
    wk_prev = wk.shift(1)  # prior COMPLETED week, indexed by the week it precedes
    wk_prev.columns = ["prior_wk_open", "prior_wk_high", "prior_wk_low", "prior_wk_close"]
    # map each day -> its week key -> prior week's H/L/C (no lookahead: only fully-completed
    # prior weeks are used, current week's own H/L/C never leak into itself)
    daily["wk_key"] = wk_key.values
    daily = daily.join(wk_prev, on="wk_key")

    # ---------------------------------------------------------------- opening range 15/30/60
    def or_window(mins):
        cutoff = pd.Timestamp("09:15") + pd.Timedelta(minutes=mins)
        sub = df[df.index.time < cutoff.time()]
        o = sub.groupby("date").agg(orh=("high", "max"), orl=("low", "min"))
        return o

    for m in (15, 30, 60):
        o = or_window(m)
        daily[f"or{m}_h"] = o["orh"]
        daily[f"or{m}_l"] = o["orl"]
        daily[f"or{m}_mid"] = (o["orh"] + o["orl"]) / 2

    daily = daily.drop(columns=["wk_key"])
    daily.to_parquet(f"{OUT}/daily.parquet")
    wk.to_parquet(f"{OUT}/weekly.parquet")
    df.to_parquet(f"{OUT}/bars_1min.parquet")

    print("daily rows", len(daily), "weekly rows", len(wk))
    print(daily.tail(3).T)
    print("nan atr14_prior frac", daily["atr14_prior"].isna().mean())
    print("nan prior_wk frac", daily["prior_wk_close"].isna().mean())

if __name__ == "__main__":
    main()
