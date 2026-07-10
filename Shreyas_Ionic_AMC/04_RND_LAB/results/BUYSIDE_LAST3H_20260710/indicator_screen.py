"""TECHNICAL-INDICATOR SCREEN on the UNDERLYING (pre-option gate). 16 price-only signals,
5-min NIFTY bars 2018-2026 (kaggle). For each signal: directional forward spot return at 30/60min
minus time-of-day-matched baseline, day-clustered t. FROZEN SCREEN BAR: edge >= +6 pts AND |t| >= 3
(bar raised for 16 trials) -> earns an option-vehicle test. 4-6 pts with t>=3 = WATCH. Else DEAD.
Signals evaluated 09:30-14:45, onset-only (state change), 30-min dedupe per signal.
Ledger +16 (screen)."""
import numpy as np, pandas as pd, datetime as dt
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/BUYSIDE_LAST3H_20260710"
sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv", parse_dates=["date"]).set_index("date").sort_index()
sp = sp[(sp.index.time >= dt.time(9, 15)) & (sp.index >= "2018-01-01")]
b = sp.resample("5min", label="right", closed="right").agg(
    {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
b = b[(b.index.time > dt.time(9, 15)) & (b.index.time <= dt.time(15, 30))]
c, h, l, o = b["close"], b["high"], b["low"], b["open"]
day = pd.Series(b.index.date, index=b.index)

def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def rsi(s, n=14):
    d = s.diff(); u = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + u / dn)
tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
atr = tr.ewm(alpha=1/14, adjust=False).mean()

sig = {}
# 1-2 Donchian 20 / 55 breakout
for n in (20, 55):
    hi, lo = h.rolling(n).max().shift(1), l.rolling(n).min().shift(1)
    sig[f"donchian{n}"] = np.where(c > hi, 1, np.where(c < lo, -1, 0))
# 3 Supertrend(10,3)
hl2 = (h + l) / 2
ub, lb = hl2 + 3 * atr, hl2 - 3 * atr
st_dir = np.zeros(len(b)); fub = ub.copy(); flb = lb.copy()
for i in range(1, len(b)):
    fub.iloc[i] = min(ub.iloc[i], fub.iloc[i-1]) if c.iloc[i-1] <= fub.iloc[i-1] else ub.iloc[i]
    flb.iloc[i] = max(lb.iloc[i], flb.iloc[i-1]) if c.iloc[i-1] >= flb.iloc[i-1] else lb.iloc[i]
    st_dir[i] = 1 if c.iloc[i] > fub.iloc[i-1] else (-1 if c.iloc[i] < flb.iloc[i-1] else st_dir[i-1])
sig["supertrend"] = st_dir
# 4 MACD cross
macd = ema(c, 12) - ema(c, 26); sigl = ema(macd, 9)
sig["macd_cross"] = np.where((macd > sigl), 1, -1)
# 5 EMA20/50 cross
sig["ema20_50"] = np.where(ema(c, 20) > ema(c, 50), 1, -1)
# 6 ADX(14)>25 + DI direction
up_m = (h.diff()).clip(lower=0); dn_m = (-l.diff()).clip(lower=0)
pdm = np.where(up_m > dn_m, up_m, 0.0); ndm = np.where(dn_m > up_m, dn_m, 0.0)
pdi = 100 * pd.Series(pdm, index=b.index).ewm(alpha=1/14, adjust=False).mean() / atr
ndi = 100 * pd.Series(ndm, index=b.index).ewm(alpha=1/14, adjust=False).mean() / atr
dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
adx = dx.ewm(alpha=1/14, adjust=False).mean()
sig["adx25_di"] = np.where((adx > 25) & (pdi > ndi), 1, np.where((adx > 25) & (ndi > pdi), -1, 0))
# 7 BB breakout
mid = c.rolling(20).mean(); sd = c.rolling(20).std()
sig["bb_break"] = np.where(c > mid + 2 * sd, 1, np.where(c < mid - 2 * sd, -1, 0))
# 8 BB squeeze release
bw = (4 * sd) / mid
sq = bw < bw.rolling(200).quantile(0.10)
sig["squeeze_rel"] = np.where(sq.shift(1) & (c > mid), 1, np.where(sq.shift(1) & (c < mid), -1, 0))
# 9 PSAR flip (simplified: 2-ATR trailing flip)
sig["atr_flip"] = np.where(c > c.rolling(10).max().shift(1) - 2 * atr, 1,
                           np.where(c < c.rolling(10).min().shift(1) + 2 * atr, -1, 0))
# 10 Ichimoku cloud break
conv = (h.rolling(9).max() + l.rolling(9).min()) / 2
base = (h.rolling(26).max() + l.rolling(26).min()) / 2
spa = ((conv + base) / 2).shift(26); spb = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
sig["ichimoku"] = np.where((c > spa) & (c > spb), 1, np.where((c < spa) & (c < spb), -1, 0))
# 11 RSI50 trend cross
r = rsi(c)
sig["rsi50"] = np.where(r > 55, 1, np.where(r < 45, -1, 0))
# 12 Stoch reversal
lo14, hi14 = l.rolling(14).min(), h.rolling(14).max()
k = 100 * (c - lo14) / (hi14 - lo14)
sig["stoch_rev"] = np.where((k.shift(1) < 20) & (k > 20), 1, np.where((k.shift(1) > 80) & (k < 80), -1, 0))
# 13 CCI
tp = (h + l + c) / 3
cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True))
sig["cci100"] = np.where(cci > 100, 1, np.where(cci < -100, -1, 0))
# 14 Heikin-Ashi 3-in-a-row
ha_c = (o + h + l + c) / 4
ha_o = ((o + c) / 2).shift(1)
hag = (ha_c > ha_o).astype(int)
sig["ha3"] = np.where(hag.rolling(3).sum() == 3, 1, np.where(hag.rolling(3).sum() == 0, -1, 0))
# 15 Inside-bar breakout
inside = (h.shift(1) < h.shift(2)) & (l.shift(1) > l.shift(2))
sig["insidebar"] = np.where(inside & (c > h.shift(1)), 1, np.where(inside & (c < l.shift(1)), -1, 0))
# 16 ROC extreme continuation
roc = c.pct_change(12) * 100
q = roc.rolling(500).quantile
sig["roc_ext"] = np.where(roc > q(0.95), 1, np.where(roc < q(0.05), -1, 0))

fwd30 = c.shift(-6) - c
fwd60 = c.shift(-12) - c
bucket = pd.Series([t.hour * 2 + (t.minute >= 30) for t in b.index], index=b.index)
base30 = fwd30.groupby(bucket).transform("mean")
base60 = fwd60.groupby(bucket).transform("mean")
ok_time = (b.index.time >= dt.time(9, 30)) & (b.index.time <= dt.time(14, 45))

rows = []
for name, arr in sig.items():
    s = pd.Series(arr, index=b.index).fillna(0)
    onset = (s != 0) & (s != s.shift(1)) & ok_time
    ev = b.index[onset]
    # 30-min dedupe
    kept, last = [], None
    for t in ev:
        if last is None or (t - last) > pd.Timedelta(minutes=30):
            kept.append(t); last = t
    if len(kept) < 100: continue
    d30 = (fwd30[kept] - base30[kept]) * s[kept]
    d60 = (fwd60[kept] - base60[kept]) * s[kept]
    res = {}
    for tag, dd in (("30m", d30), ("60m", d60)):
        dd = dd.dropna()
        byday = dd.groupby(pd.Series(dd.index.date, index=dd.index)).mean()
        t_ = byday.mean() / (byday.std(ddof=1) / np.sqrt(len(byday)))
        res[tag] = (dd.mean(), t_, len(dd))
    e30, t30, n = res["30m"]; e60, t60, _ = res["60m"]
    best = max(e30, e60)
    verdict = "OPTION-TEST" if (best >= 6 and max(abs(t30), abs(t60)) >= 3) else ("WATCH" if (best >= 4 and max(t30, t60) >= 3) else "dead")
    rows.append(f"{name}: n={n} | 30m {e30:+.2f}(t={t30:+.1f}) 60m {e60:+.2f}(t={t60:+.1f}) | {verdict}")
txt = "# Indicator screen on UNDERLYING (2018-2026 5-min; bar: >=6pts & |t|>=3)\n" + "\n".join(rows)
print(txt)
(OUT / "INDICATOR_SCREEN.md").write_text(txt + "\n", encoding="utf-8")
