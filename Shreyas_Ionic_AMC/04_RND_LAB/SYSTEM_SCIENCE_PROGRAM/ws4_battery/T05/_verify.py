# T05 verification: base-effect / denominator disease in a percent-growth rank.
# (eps - eps_prev)/eps_prev is meaningless when eps_prev is near zero or negative:
#   - tiny positive base -> explosive fake "growth" dominates the top ranks
#   - negative base + DEEPENING loss -> POSITIVE "growth" (sign flip, ranked top)
#   - negative base + swing to profit -> NEGATIVE "growth" (real turnaround ranked bottom)
import pandas as pd

rows = [
    ("ZENVITECH",    0.04,   1.62),   # penny-EPS base
    ("ORBIPHARM",    0.11,   2.05),   # penny-EPS base
    ("SUNWINDPWR",  -1.20,  -2.55),   # loss DEEPENED
    ("JPINFRAVENT", -0.35,  -0.68),   # loss DEEPENED
    ("BLUECHIPCO",  98.40, 122.10),   # genuine high-quality grower
    ("TURNCORP",    -5.00,   1.00),   # genuine turnaround to profit
]
df = pd.DataFrame(rows, columns=["symbol", "prev", "now"])
df["growth_pct"] = (df["now"] - df["prev"]) / df["prev"]
df = df.sort_values("growth_pct", ascending=False).reset_index(drop=True)
print(df.to_string(index=False))
print()

rank = {s: i for i, s in enumerate(df["symbol"])}
# the pathologies the task's nlargest(20, 'growth') selects on:
assert rank["ZENVITECH"] == 0                          # near-zero base dominates
assert rank["SUNWINDPWR"] < rank["BLUECHIPCO"]         # deepening loss beats real grower
assert rank["JPINFRAVENT"] < rank["BLUECHIPCO"]
assert rank["TURNCORP"] == len(df) - 1                 # real turnaround ranked LAST
assert df.loc[df.symbol == "SUNWINDPWR", "growth_pct"].iloc[0] > 0   # sign flip
print("DEFECT CONFIRMED: percent growth on near-zero/negative bases sign-flips and")
print("explodes; the 'fastest growers' basket is penny-base noise plus deteriorating")
print("loss-makers, while true growers/turnarounds are excluded.")
print("Fix: require positive material base (e.g. eps_prev > threshold), or rank on")
print("delta-EPS scaled by price/assets, not percent-of-base.")
