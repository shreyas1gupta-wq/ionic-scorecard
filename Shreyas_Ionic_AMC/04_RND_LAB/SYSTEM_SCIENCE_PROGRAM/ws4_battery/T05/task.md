# T05 — Review request: "fastest growers" earnings-growth screen

Quarterly screen feeding the growth sleeve. The fundamentals table is publication-lagged
(`asof_date` = the date the filing became public), so the author states there is no
timing leak. Prices are the adjusted union panel; entries at next session's open after
each `asof_date` refresh; 40bp/side costs.

Reported result: top-20 "fastest growers" basket +34% CAGR 2019-2025 vs universe 13%.

```python
import pandas as pd

f = pd.read_parquet("ttm_eps_pit.parquet")
# columns: symbol, asof_date (publication-lagged), ttm_eps (trailing-12m EPS, Rs)
f = f.sort_values(["symbol", "asof_date"])

# growth: TTM EPS now vs TTM EPS four quarterly refreshes ago
f["ttm_eps_prev"] = f.groupby("symbol")["ttm_eps"].shift(4)
f["growth"] = (f["ttm_eps"] - f["ttm_eps_prev"]) / f["ttm_eps_prev"]

def rebalance(asof, universe):
    snap = f[(f["asof_date"] <= asof)]
    snap = snap.sort_values("asof_date").groupby("symbol").tail(1)
    snap = snap[snap["symbol"].isin(universe)].dropna(subset=["growth"])
    top20 = snap.nlargest(20, "growth")["symbol"].tolist()
    return top20

# quarterly loop: PIT membership, equal weight, next-open entry, hold to next rebalance
# (loop body omitted -- standard, shared with the value sleeve which passed audit)

# sample of what the screen actually selects (top of the Jun-2025 ranking):
#   symbol        ttm_eps_prev   ttm_eps    growth
#   ZENVITECH         0.04          1.62     39.50
#   ORBIPHARM         0.11          2.05     17.64
#   SUNWINDPWR       -1.20         -2.55      1.13     <- ranked 8th
#   JPINFRAVENT      -0.35         -0.68      0.94     <- ranked 9th
#   BLUECHIPCO       98.40        122.10      0.24     <- ranked 61st, not selected
#   TURNCORP         -5.00          1.00     -1.20     <- ranked 496th (near bottom)
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
