"""Stage 3: SHORT-ONLY ORB engine on 2-week-momentum active symbol-days. Two timeframes:
  5m-ORB : OR = first 5-min bar (09:15-09:19); confirm/enter on 5-min bars; ATR(14) on 5-min series.
  15m-ORB: OR = first 15-min bar (09:15-09:29); confirm/enter on 15-min bars; ATR(14) on 15-min series.
Both anchor at 09:15 (L2 preopen guard applied upstream). 15-min bars DERIVED from cached 5-min (bar15=bar5//3).
SHORT only: enter when a later bar CLOSES < OR-low (close-confirm, not wick). First signal/day only.
Enter NEXT bar OPEN (L5 next-bar, strictly after signal). Stop = entry + 1.0*ATR(14) at signal bar (proven stop).
Exit = EOD flat at last bar close (proven exit). Gap-through honored. Fill guard: next bar vol>0 else DROP (D-031).
Costs: SLIP 15bps/side, DOUBLED to 30bps on stop/gap exit; FIXED ~8.2bps. net_2x = 2x slippage stress.
OUT: trades_5m.csv, trades_15m.csv
"""
import os
import numpy as np, pandas as pd

OUT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_SHORTONLY_20260707/MOM2W"
CACHE = os.path.join(OUT, "cache")
SLIP = 0.0015          # per-side slippage (momentum-50 skews mid-liquid), same as prior 3m test
FIXED = 0.00082        # STT sell 2.5 + exch/GST 1.4 + stamp 0.3 + brokerage 4bps@Rs1L = ~8.2bps
ATR_MULT = 1.0

def wilder_atr(df):
    """df sorted by (date,bar_idx) for ONE symbol & ONE timeframe; continuous TR (across day boundary)."""
    pc = df["close"].shift(1)
    tr = np.maximum(df["high"] - df["low"],
                    np.maximum((df["high"] - pc).abs(), (df["low"] - pc).abs()))
    tr = tr.fillna(df["high"] - df["low"])
    return tr.ewm(alpha=1/14, adjust=False).mean()

def simulate_short_day(day, maxidx):
    """day: dict bar_idx -> (o,h,l,c,vol,atr,seq). Returns trade tuple or None."""
    if 0 not in day:
        return None
    orl = day[0][2]                                   # OR low
    sig = None
    for b in range(1, maxidx):                        # need a next bar for entry
        if b not in day:
            continue
        o, h, l, c, vol, a, sq = day[b]
        if sq < 14 or not np.isfinite(a):
            continue
        if c < orl:                                   # close-confirmed breakdown
            sig = (b, a); break
    if sig is None:
        return None
    sbar, atr_e = sig
    ebar = sbar + 1
    if ebar not in day or day[ebar][4] <= 0:          # fill guard: next bar exists w/ volume
        return None
    entry = day[ebar][0]
    if entry <= 0 or atr_e <= 0:
        return None
    init_stop = entry + ATR_MULT * atr_e              # short stop above entry
    lastbar = max(k for k in day if k <= maxidx)
    ex = xbar = reason = None
    for b in range(ebar, maxidx + 1):
        if b not in day:
            continue
        o, h, l, c, vol, a, sq = day[b]
        if o >= init_stop:
            ex, xbar, reason = o, b, "GAP"; break      # gap-through: fill at open
        if h >= init_stop:
            ex, xbar, reason = init_stop, b, "STOP"; break
    if ex is None:
        ex, xbar, reason = day[lastbar][3], lastbar, "EOD"
    gross = (entry - ex) / entry
    return (sbar, ebar, xbar, reason, entry, ex, atr_e, atr_e / entry, gross)

# ---- active symbol-days ----
act = pd.read_csv(os.path.join(OUT, "active_days.csv"), parse_dates=["date"])
rank_map = {(r.symbol, r.date.normalize()): r.rank for r in act.itertuples()}
active_dates = act.groupby("symbol")["date"].apply(lambda s: set(pd.to_datetime(s).dt.normalize())).to_dict()

# ---- load all 5-min bars ----
bars = pd.concat([pd.read_parquet(os.path.join(CACHE, f"bars5_shard{i}.parquet")) for i in range(8)],
                 ignore_index=True)
bars = bars.dropna(subset=["open", "high", "low", "close"])
bars["date"] = pd.to_datetime(bars["date"])
bars = bars.sort_values(["symbol", "date", "bar_idx"]).reset_index(drop=True)
print("total 5-min bars:", len(bars), "| symbols:", bars["symbol"].nunique())

recs5, recs15 = [], []
COST = lambda reason: (SLIP + SLIP * (2 if reason in ("STOP", "GAP") else 1) + FIXED,
                       2 * (SLIP + SLIP * (2 if reason in ("STOP", "GAP") else 1)) + FIXED)

for sym, g5 in bars.groupby("symbol", sort=False):
    if sym not in active_dates:
        continue
    adates = active_dates[sym]
    g5 = g5.reset_index(drop=True)
    g5 = g5.assign(atr=wilder_atr(g5).values)
    g5["seq"] = np.arange(len(g5))
    # ---- derive 15-min bars for this symbol ----
    g5["bar15"] = g5["bar_idx"] // 3
    a15 = (g5.groupby(["date", "bar15"], sort=True)
             .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                  close=("close", "last"), volume=("volume", "sum")).reset_index()
             .rename(columns={"bar15": "bar_idx"}).sort_values(["date", "bar_idx"]).reset_index(drop=True))
    a15["atr"] = wilder_atr(a15).values
    a15["seq"] = np.arange(len(a15))
    # ---- iterate active days for both timeframes ----
    for dt, d5 in g5.groupby("date", sort=False):
        if dt not in adates:
            continue
        rank = rank_map.get((sym, dt), np.nan)
        ym = dt.strftime("%Y-%m")
        day5 = {int(r.bar_idx): (r.open, r.high, r.low, r.close, r.volume, r.atr, int(r.seq))
                for r in d5.itertuples()}
        t5 = simulate_short_day(day5, 74)
        if t5:
            sbar, ebar, xbar, reason, entry, ex, atr_e, atrpct, gross = t5
            c1, c2 = COST(reason)
            recs5.append((ym, dt.date(), sym, "S", sbar, ebar, xbar, reason, round(entry, 3),
                          round(ex, 3), round(atr_e, 4), round(atrpct, 6), round(gross, 6),
                          round(gross - c1, 6), round(gross - c2, 6), rank))
        d15 = a15[a15["date"] == dt]
        day15 = {int(r.bar_idx): (r.open, r.high, r.low, r.close, r.volume, r.atr, int(r.seq))
                 for r in d15.itertuples()}
        t15 = simulate_short_day(day15, 24)
        if t15:
            sbar, ebar, xbar, reason, entry, ex, atr_e, atrpct, gross = t15
            c1, c2 = COST(reason)
            recs15.append((ym, dt.date(), sym, "S", sbar, ebar, xbar, reason, round(entry, 3),
                           round(ex, 3), round(atr_e, 4), round(atrpct, 6), round(gross, 6),
                           round(gross - c1, 6), round(gross - c2, 6), rank))

cols = ["month", "date", "symbol", "side", "signal_bar", "entry_bar", "exit_bar", "exit_reason",
        "entry", "exit", "atr_entry", "atr_pct", "gross_ret", "net_ret", "net_2x", "mom_rank"]
pd.DataFrame(recs5, columns=cols).to_csv(os.path.join(OUT, "trades_5m.csv"), index=False)
pd.DataFrame(recs15, columns=cols).to_csv(os.path.join(OUT, "trades_15m.csv"), index=False)
print("5m trades:", len(recs5), "| 15m trades:", len(recs15))
print("STAGE3 DONE")
