"""Random-entry placebo for the flagship intraday gate G2_VOV: same count (761), matched on the
hhmm (time-of-day) distribution of the real gated trades, drawn from buckets NOT selected by ANY
of the three gates (so the control is a genuine "ungated" baseline, not contaminated by the other
correlated vol signals), same one-trade-at-a-time non-overlap rule.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
RNG = np.random.default_rng(20260731)
S = pd.read_parquet(f"{OUT}/intraday_signal_buckets.parquet")
real = pd.read_parquet(f"{OUT}/intraday_trade_candidates.parquet")
real_g2 = real[real.gate == "G2_VOV"]
target_hhmm_counts = real_g2["t"].dt.hour * 100 + real_g2["t"].dt.minute
target_hhmm_counts = target_hhmm_counts.value_counts()
print("target hhmm distribution (n=761 real G2_VOV trades):")
print(target_hhmm_counts.sort_index())

pool = S[~(S["G1_ML"] | S["G2_VOV"] | S["G3_ATRCONS"])].copy()
pool["hhmm"] = pool.index.hour * 100 + pool.index.minute
print(f"\nungated pool: {len(pool)} buckets")

FWD_MIN = 120
picked = []
for hhmm, cnt in target_hhmm_counts.items():
    sub = pool[pool["hhmm"] == hhmm].sort_index()
    if len(sub) == 0:
        continue
    idxs = RNG.choice(len(sub), size=min(cnt, len(sub)), replace=False)
    picked.extend(sub.index[idxs].tolist())

picked = sorted(picked)
# one-at-a-time (same rule as the real gates)
kept = []
next_free = None
for t in picked:
    if next_free is not None and t < next_free:
        continue
    kept.append(t)
    next_free = t + pd.Timedelta(minutes=FWD_MIN)

print(f"\npicked {len(picked)} candidates -> {len(kept)} after one-at-a-time "
      f"(target was {len(real_g2)})")

T = pd.DataFrame({"t": kept})
T["gate"] = "PLACEBO_G2_VOV"
T["d"] = pd.to_datetime(T["t"]).dt.normalize()
T.to_parquet(f"{OUT}/placebo_trade_candidates.parquet")
print("wrote placebo_trade_candidates.parquet")
