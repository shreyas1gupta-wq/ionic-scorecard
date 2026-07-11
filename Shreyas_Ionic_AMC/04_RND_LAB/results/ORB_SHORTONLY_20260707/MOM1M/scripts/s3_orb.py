"""S3: SHORT-ONLY OR-LOW-BREAKDOWN engine. SL 1.0xATR + EOD (the proven-best config from the 3m test).
Self-consistent timeframe: 5m-ORB = OR is first 5-min bar (09:15-09:19), breakdown on subsequent 5-min bars;
15m-ORB = OR is first 15-min bar (09:15-09:29), breakdown on subsequent 15-min bars.
Close-confirmation (not wick). First short signal/day only. Enter NEXT bar open. Causal Wilder ATR(14) on
continuous per-symbol series. Gap-through honored. Fill guard (next-bar volume>0).
Run: s3_orb.py 15   |   s3_orb.py 5
OUT: trades_<tf>m.csv
"""
import os, sys
import numpy as np, pandas as pd
from itertools import groupby as _gb

TF = int(sys.argv[1])                      # 5 or 15
MAXIDX = {15: 24, 5: 74}[TF]               # last intraday bar_idx
OUT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_SHORTONLY_20260707/MOM1M"
CACHE = os.path.join(OUT, "cache")

# costs (COST_STANDARDS, binding) — identical to the 3m test for apples-to-apples
SLIP = 0.0015           # per-side slippage
FIXED = 0.00082         # STT sell 2.5 + exch/GST 1.4 + stamp 0.3 + brokerage 4bps@Rs1L = ~8.2bps
K = 1.00                # stop distance = 1.0 x ATR (proven-best; NOT re-testing 0.25x)

# ---- load bars, causal Wilder ATR(14) on continuous per-symbol series ----
bars = pd.concat([pd.read_parquet(os.path.join(CACHE, f"bars{TF}_shard{i}.parquet")) for i in range(8)],
                 ignore_index=True)
bars = bars.dropna(subset=["open", "high", "low", "close"])
bars = bars.sort_values(["symbol", "date", "bar_idx"]).reset_index(drop=True)
pc = bars.groupby("symbol")["close"].shift(1)
tr = np.maximum(bars["high"] - bars["low"],
                np.maximum((bars["high"] - pc).abs(), (bars["low"] - pc).abs()))
tr = tr.fillna(bars["high"] - bars["low"])
bars["atr"] = tr.groupby(bars["symbol"]).transform(lambda s: s.ewm(alpha=1/14, adjust=False).mean())
bars["seq"] = bars.groupby("symbol").cumcount()

# ---- active symbol-months (in that month's momentum-50 basket) ----
bk = pd.read_csv(os.path.join(OUT, "baskets.csv"))
rank_map = dict(zip(zip(bk["symbol"], bk["month"]), bk["rank"]))
active = set(rank_map.keys())
bars["ym"] = bars["date"].dt.strftime("%Y-%m")
bars = bars[[k in active for k in zip(bars["symbol"], bars["ym"])]].copy()
print(f"TF={TF}m active bars: {len(bars):,} | symbol-days: {bars.groupby(['symbol','date']).ngroups:,}", flush=True)


def simulate_short(entry, ebar, atr_e, day):
    init_stop = entry + K * atr_e
    for b in range(ebar, MAXIDX + 1):
        if b not in day:
            continue
        o, h, l, c = day[b]
        if o >= init_stop:      # gapped through stop at bar open
            return o, b, "GAP"
        if h >= init_stop:
            return init_stop, b, "STOP"
    last = max(b for b in day if b <= MAXIDX)
    return day[last][3], last, "EOD"


recs = []
n_days = n_sig = n_filled = 0
arr = bars[["symbol", "date", "bar_idx", "open", "high", "low", "close", "volume", "atr", "seq"]].to_numpy(object)
for (sym, dt), grp in _gb(arr, key=lambda r: (r[0], r[1])):
    n_days += 1
    bybar = {}
    for row in grp:
        bi = int(row[2])
        bybar[bi] = (float(row[3]), float(row[4]), float(row[5]), float(row[6]),
                     float(row[7]), float(row[8]), int(row[9]))  # o,h,l,c,vol,atr,seq
    if 0 not in bybar:            # need OR bar
        continue
    orl = bybar[0][2]             # OR low
    sig = None
    for b in range(1, MAXIDX):    # need a next bar to enter => stop before MAXIDX
        if b not in bybar:
            continue
        o, h, l, c, vol, a, sq = bybar[b]
        if sq < 14 or not np.isfinite(a):
            continue
        if c < orl:               # SHORT-ONLY: close below OR-low
            sig = (b, a); break
    if sig is None:
        continue
    n_sig += 1
    sbar, atr_e = sig
    ebar = sbar + 1
    if ebar not in bybar or bybar[ebar][4] <= 0:   # fill guard: next bar exists w/ volume>0
        continue
    entry = bybar[ebar][0]
    if entry <= 0 or atr_e <= 0:
        continue
    gd = {b: (v[0], v[1], v[2], v[3]) for b, v in bybar.items()}  # o,h,l,c
    n_filled += 1
    ym = pd.Timestamp(dt).strftime("%Y-%m")
    ex, xbar, reason = simulate_short(entry, ebar, atr_e, gd)
    gross = (entry - ex) / entry                                 # SHORT return, %-of-entry
    stop_exit = reason in ("STOP", "GAP")
    exit_slip = SLIP * (2 if stop_exit else 1)
    cost1 = SLIP + exit_slip + FIXED
    cost2 = 2 * (SLIP + exit_slip) + FIXED
    recs.append((ym, pd.Timestamp(dt).date(), sym, "S", sbar, ebar, xbar, reason,
                 round(entry, 3), round(ex, 3), round(atr_e, 4),
                 round(gross, 6), round(gross - cost1, 6), round(gross - cost2, 6),
                 rank_map.get((sym, ym), np.nan)))

cols = ["month", "date", "symbol", "side", "signal_bar", "entry_bar", "exit_bar", "exit_reason",
        "entry", "exit", "atr_entry", "gross_ret", "net_ret", "net_2x", "mom_rank"]
pd.DataFrame(recs, columns=cols).to_csv(os.path.join(OUT, f"trades_{TF}m.csv"), index=False)
print(f"symbol-days {n_days:,} | short signals {n_sig:,} | filled {n_filled:,}", flush=True)
print(f"STAGE3 TF={TF} DONE", flush=True)
