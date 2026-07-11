"""Stage 3: 15-min ORB engine, 4 combos, on momentum-50 active symbol-days. Bidirectional, close-confirm,
enter NEXT bar open. Causal Wilder ATR(14) on continuous 15-min series. Gap-through honored. Fill guard.
OUT: trades_combo{1..4}.csv  (1: 0.25xATR+EOD, 2: 0.25xATR+trail, 3: 1.0xATR+EOD, 4: 1.0xATR+trail)
"""
import os
import numpy as np, pandas as pd

OUT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_MOMENTUM50_20260707/MOM3M"
CACHE = os.path.join(OUT, "cache")

# costs (COST_STANDARDS, binding)
SLIP = 0.0015           # per-side slippage (blend large10/mid20 bps), momentum-50 skews mid-liquid
FIXED = 0.00082         # STT sell 2.5 + exch/GST 1.4 + stamp 0.3 + brokerage 4bps@Rs1L = ~8.2bps
TRAIL_MULT = 1.0        # chandelier: highestClose - 1.0*ATR (long)
COMBOS = [("combo1", 0.25, False), ("combo2", 0.25, True),
          ("combo3", 1.00, False), ("combo4", 1.00, True)]

# ---- load 15-min bars, compute causal Wilder ATR(14) on continuous series ----
bars = pd.concat([pd.read_parquet(os.path.join(CACHE, f"bars15_shard{i}.parquet")) for i in range(8)],
                 ignore_index=True)
bars = bars.dropna(subset=["open", "high", "low", "close"])
bars = bars.sort_values(["symbol", "date", "bar_idx"]).reset_index(drop=True)
pc = bars.groupby("symbol")["close"].shift(1)                       # prior 15-min close (across day boundary)
tr = np.maximum(bars["high"] - bars["low"],
                np.maximum((bars["high"] - pc).abs(), (bars["low"] - pc).abs()))
tr = tr.fillna(bars["high"] - bars["low"])
bars["atr"] = tr.groupby(bars["symbol"]).transform(lambda s: s.ewm(alpha=1/14, adjust=False).mean())
bars["seq"] = bars.groupby("symbol").cumcount()                    # warmup guard

# ---- active symbol-months ----
bk = pd.read_csv(os.path.join(OUT, "baskets.csv"))
rank_map = dict(zip(zip(bk["symbol"], bk["month"]), bk["rank"]))
active = set(rank_map.keys())
bars["ym"] = bars["date"].dt.strftime("%Y-%m")
key = list(zip(bars["symbol"], bars["ym"]))
bars = bars[[k in active for k in key]].copy()
print("active 15-min bars:", len(bars), "| symbol-days:", bars.groupby(["symbol", "date"]).ngroups)


def simulate(side, entry, ebar, atr_e, k, trailing, day):
    """day: dict bar_idx -> (o,h,l,c,atr). Returns (exit_price, exit_bar, reason)."""
    if side == "L":
        init_stop = entry - k * atr_e
        mx = entry; atr_prev = atr_e
        for b in range(ebar, 25):
            if b not in day: continue
            o, h, l, c, a = day[b]
            eff = max(init_stop, mx - TRAIL_MULT * atr_prev) if trailing else init_stop
            if o <= eff:  return o, b, "GAP"
            if l <= eff:  return eff, b, ("TRAIL" if (trailing and eff > init_stop + 1e-12) else "STOP")
            mx = max(mx, c); atr_prev = a
        return day[max(k2 for k2 in day if k2 <= 24)][3], 24, "EOD"
    else:
        init_stop = entry + k * atr_e
        mn = entry; atr_prev = atr_e
        for b in range(ebar, 25):
            if b not in day: continue
            o, h, l, c, a = day[b]
            eff = min(init_stop, mn + TRAIL_MULT * atr_prev) if trailing else init_stop
            if o >= eff:  return o, b, "GAP"
            if h >= eff:  return eff, b, ("TRAIL" if (trailing and eff < init_stop - 1e-12) else "STOP")
            mn = min(mn, c); atr_prev = a
        return day[max(k2 for k2 in day if k2 <= 24)][3], 24, "EOD"


recs = {c[0]: [] for c in COMBOS}
n_days = n_sig = n_filled = 0
arr = bars[["symbol", "date", "bar_idx", "open", "high", "low", "close", "volume", "atr", "seq"]].to_numpy(object)
# group rows by (symbol,date) via itertuples over the sorted frame
from itertools import groupby as _gb
def keyfn(row): return (row[0], row[1])
for (sym, dt), grp in _gb(arr, key=keyfn):
    n_days += 1
    bybar = {}
    for row in grp:
        bi = int(row[2])
        bybar[bi] = (float(row[3]), float(row[4]), float(row[5]), float(row[6]),
                     float(row[7]), float(row[8]), int(row[9]))  # o,h,l,c,vol,atr,seq
    if 0 not in bybar:            # need OR bar
        continue
    orh, orl = bybar[0][1], bybar[0][2]
    sig = None
    for b in range(1, 24):
        if b not in bybar: continue
        o, h, l, c, vol, a, sq = bybar[b]
        if sq < 14 or not np.isfinite(a):  # ATR not warmed -> cannot size stop
            continue
        if c > orh:  sig = (b, "L", a); break
        if c < orl:  sig = (b, "S", a); break
    if sig is None: continue
    n_sig += 1
    sbar, side, atr_e = sig
    ebar = sbar + 1
    if ebar not in bybar or bybar[ebar][4] <= 0:   # fill guard: next bar exists w/ volume>0
        continue
    entry = bybar[ebar][0]
    if entry <= 0 or atr_e <= 0: continue
    gd = {b: (v[0], v[1], v[2], v[3], v[5]) for b, v in bybar.items()}  # o,h,l,c,atr
    n_filled += 1
    ym = pd.Timestamp(dt).strftime("%Y-%m")
    for name, k, trailing in COMBOS:
        ex, xbar, reason = simulate(side, entry, ebar, atr_e, k, trailing, gd)
        gross = (ex / entry - 1.0) if side == "L" else (entry - ex) / entry
        stop_exit = reason in ("STOP", "TRAIL", "GAP")
        exit_slip = SLIP * (2 if stop_exit else 1)
        cost1 = SLIP + exit_slip + FIXED
        cost2 = 2 * (SLIP + exit_slip) + FIXED
        recs[name].append((ym, pd.Timestamp(dt).date(), sym, side, sbar, ebar, xbar, reason,
                           round(entry, 3), round(ex, 3), round(atr_e, 4),
                           round(gross, 6), round(gross - cost1, 6), round(gross - cost2, 6),
                           rank_map.get((sym, ym), np.nan)))

cols = ["month", "date", "symbol", "side", "signal_bar", "entry_bar", "exit_bar", "exit_reason",
        "entry", "exit", "atr_entry", "gross_ret", "net_ret", "net_2x", "mom_rank"]
for name, _, _ in COMBOS:
    pd.DataFrame(recs[name], columns=cols).to_csv(os.path.join(OUT, f"trades_{name}.csv"), index=False)
print(f"symbol-days scanned {n_days} | signals {n_sig} | filled trades {n_filled}")
print("STAGE3 DONE")
