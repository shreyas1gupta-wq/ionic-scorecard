"""Build intraday 15-min-bucket entry-signal candidates for THREE gates, restricted to the
option-data-covered period (>=2021-05-24). Reuses regime_ml.py's exact feature formulas (rv_back15,
rv_back60, atr_consumed) so gates are computed identically to the validated ML head, then joins the
already-validated p_H3_vol3_HIGH OOS probability from REGIME_ML_20260730/oos_predictions.parquet.

Gates (all thresholds pre-registered on the PRE-2024-10-01 build era only, then applied unchanged
to the rest, including the 2026 held-out slice):
  G1_ML       p_H3_vol3_HIGH >= q90 (build era)          -- the flagship ML vol-expansion gate
  G2_VOV      spike_ratio = rv_back15 / trailing20d-same-time-of-day-mean(rv_back15) >= q90 (build era)
  G3_ATRCONS  atr_consumed >= 1.0 (economic threshold, not fitted: day's range already >= its own ATR20)

No lookahead: trailing means use only PRIOR days (shift by day). Entry decision known at bucket
close; actual trade fill will be NEXT 1-min bar's open (handled in the option-extraction stage).
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
IDX = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
       r"\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet")
OPT_START = pd.Timestamp("2021-05-24")
BUCKET = 15
ENTRY_LO, ENTRY_HI = "09:30", "13:15"   # need 120min of session left (matches ML label window)
FWD_MIN = 120
BUILD_END = pd.Timestamp("2024-10-01")   # gate thresholds pre-registered on data BEFORE this date only

print("[load] index 1-min", flush=True)
px = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
px = px[(px.index.time >= pd.Timestamp("09:15").time()) & (px.index.time <= pd.Timestamp("15:30").time())]
px["d"] = px.index.normalize()
print(f"       {len(px):,} bars {px.index.min()} .. {px.index.max()}", flush=True)

dly = px.groupby("d").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
tr = pd.concat([dly.h - dly.l, (dly.h - dly.c.shift()).abs(), (dly.l - dly.c.shift()).abs()], axis=1).max(axis=1)
dly["atr20"] = tr.rolling(20, min_periods=10).mean()

rows = []
lo_t, hi_t = pd.Timestamp(ENTRY_LO).time(), pd.Timestamp(ENTRY_HI).time()
for d, g in px.groupby("d"):
    if d < OPT_START - pd.Timedelta(days=30):   # small buffer, filtered precisely later
        continue
    if d not in dly.index or not np.isfinite(dly.at[d, "atr20"]):
        continue
    atr = float(dly.at[d, "atr20"])
    if atr <= 0:
        continue
    c = g["close"].to_numpy(float)
    h = g["high"].to_numpy(float)
    lw = g["low"].to_numpy(float)
    ts = g.index
    n = len(c)
    if n < 200:
        continue
    for i in range(n):
        if not (lo_t <= ts[i].time() <= hi_t):
            continue
        if ts[i].minute % BUCKET != 0:
            continue
        j = i + FWD_MIN
        if j >= n:
            continue
        b = max(0, i - 60)
        bc = c[b:i + 1]
        rows.append(dict(
            t=ts[i], d=d, hhmm=ts[i].hour * 100 + ts[i].minute, spot=c[i],
            atr_consumed=(h[:i + 1].max() - lw[:i + 1].min()) / atr,
            rv_back60=np.diff(bc).std() * np.sqrt(375) if len(bc) > 5 else np.nan,
            rv_back15=np.diff(c[max(0, i - 15):i + 1]).std() * np.sqrt(375) if i > 16 else np.nan,
        ))

S = pd.DataFrame(rows).set_index("t").sort_index()
S = S[S["d"] >= OPT_START]
print(f"[build] {len(S):,} candidate buckets {S.index.min()} .. {S.index.max()}", flush=True)

# spike_ratio: rv_back15 vs trailing 20-trading-day mean of rv_back15 AT THE SAME TIME-OF-DAY,
# using only prior days (shift(1) on the per-hhmm series so today's value never leaks into its own mean)
S = S.sort_values(["hhmm", "d"])
grp = S.groupby("hhmm")["rv_back15"]
S["rv_back15_trail_mean"] = grp.transform(lambda s: s.shift(1).rolling(20, min_periods=10).mean())
S["spike_ratio"] = S["rv_back15"] / S["rv_back15_trail_mean"]
S = S.sort_index()

# join the already-validated ML probability
oos = pd.read_parquet(r"Shreyas_Ionic_AMC/04_RND_LAB/results/REGIME_ML_20260730/oos_predictions.parquet",
                       columns=["p_H3_vol3_HIGH"])
S = S.join(oos, how="left")
print(f"[join] p_H3 non-null: {S['p_H3_vol3_HIGH'].notna().mean():.1%}", flush=True)

build = S[S["d"] < BUILD_END]
q_ml = build["p_H3_vol3_HIGH"].quantile(0.90)
q_vov = build["spike_ratio"].quantile(0.90)
print(f"[thresholds, pre-registered on build era < {BUILD_END.date()}]")
print(f"  G1_ML      p_H3_vol3_HIGH >= {q_ml:.4f}")
print(f"  G2_VOV     spike_ratio    >= {q_vov:.4f}")
print(f"  G3_ATRCONS atr_consumed   >= 1.00 (fixed economic threshold, not fitted)")

S["G1_ML"] = S["p_H3_vol3_HIGH"] >= q_ml
S["G2_VOV"] = S["spike_ratio"] >= q_vov
S["G3_ATRCONS"] = S["atr_consumed"] >= 1.00

for g in ["G1_ML", "G2_VOV", "G3_ATRCONS"]:
    print(f"  {g}: {S[g].sum():,} raw bucket-hits ({S[g].mean():.2%} of {len(S):,})")

S.to_parquet(f"{OUT}/intraday_signal_buckets.parquet")
with open(f"{OUT}/intraday_gate_thresholds.txt", "w") as f:
    f.write(f"build_end={BUILD_END.date()}\nq_ml_p90={q_ml}\nq_vov_p90={q_vov}\natr_consumed_fixed=1.00\n")
print("wrote intraday_signal_buckets.parquet")
