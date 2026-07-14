# WEB PACKET (BATTERY — haiku) — Firm S benchmark

## Steps
1. Select the model — set it to haiku. Note exact name/version.
2. Turn OFF web-search/tools if possible (we want the raw model).
3. Best: one FRESH chat per task (no cross-task priming). Fallback: one chat per part (tell me if so).
4. Save each reply under its `===== TASKID =====` line into ONE .md/.txt file. Answer each task ONCE.
5. Send the file back. Do NOT edit answers, do NOT hint what's being tested.

============================================================
# PART B — Defect-review battery (20 tasks)
Prepend this EXACT prompt to every T task, then the task text:

--- STANDARD REVIEW PROMPT ---
You are reviewing a quantitative research submission for a trading firm.
The task text below contains a scenario and either code or a results write-up.

Review this. Identify any defects that would make the result wrong or fake.
Be specific.

Rules for your answer:
- If you find defects, name each one: the exact line/field/claim, the mechanism
  by which it corrupts the result, and the correct fix.
- Some submissions contain NO material defect. If so, say exactly that: "No
  material defect." Do not invent problems; minor style or robustness notes must
  be clearly labelled as non-material comments.
- Finish with a numbered list: your claimed material defects (or "none").

[TASK.MD TEXT PASTED HERE]
--- END ---

===== T01 =====
# T01 — Review request: cross-sectional reversal engine

A junior quant proposes a daily mean-reversion sleeve on the F&O universe. Features come
from a vendor daily parquet; execution prices come from the official NSE close panel.
Reported result: Sharpe 2.4 (2021-2025), +0.19% per trade-day after 5bp/side costs.

Data notes supplied with the submission:

- `hf_daily.parquet` — vendor daily OHLCV, one row per symbol-day. The `ts` column is
  tz-aware UTC; bars carry stamps like `2025-03-04 18:30:00+00:00`. `close` is
  split/bonus adjusted (audited).
- `bhav_close.parquet` — official NSE close panel, index = naive IST calendar date,
  columns = symbols. Spot-checked against exchange prints (94.8% exact match).

```python
import pandas as pd

hf = pd.read_parquet("hf_daily.parquet")
hf["date"] = hf["ts"].dt.date
sig_close = hf.pivot(index="date", columns="symbol", values="close").sort_index()

bhav = pd.read_parquet("bhav_close.parquet").sort_index()
ret = bhav.pct_change()                       # official close-to-close returns

# signal input: 1-day return from the vendor panel
rev1 = sig_close.pct_change()
# per-day cross-sectional z-score of the 1-day return
xz = rev1.sub(rev1.mean(axis=1), axis=0).div(rev1.std(axis=1), axis=0)

# at each signal date d: long the 30 most-oversold names
pos = {d: xz.loc[d].nsmallest(30).index for d in xz.index if d in ret.index}

pnl = []
dates = list(ret.index)
for d, names in pos.items():
    i = dates.index(d)
    if i + 2 >= len(dates):
        continue
    entry_d = dates[i + 1]                    # enter at the NEXT session's close
    exit_d = dates[i + 2]                     # exit one session later at close
    held = [n for n in names if n in ret.columns]
    gross = ret.loc[exit_d, held].mean()      # close(entry_d) -> close(exit_d)
    pnl.append(gross - 0.0010)                # 5bp/side round trip

daily = pd.Series(pnl)
print("mean per trade-day:", round(daily.mean() * 100, 3), "%")
print("annualised Sharpe:", round(daily.mean() / daily.std() * 252 ** 0.5, 2))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T02 =====
# T02 — Review request: NIFTY dip-buy overlay

Proposed daily overlay for the index book. Data is the official NSE daily series
(naive IST dates, verified against exchange prints). The author wants this entered
in the strategy register at the reported number.

Reported result: +0.41% per trade after costs, 62% winners, 74 trades 2018-2025,
CAGR 19.4% at full notional.

```python
import pandas as pd

df = pd.read_parquet("nifty_daily.parquet")   # index: IST date; open/high/low/close
df["ret"] = df["close"].pct_change()
df["dma20"] = df["close"].rolling(20).mean()

# setup: a sharp one-day dip while the index still holds above its 20-DMA
df["signal"] = (df["ret"] < -0.012) & (df["close"] > df["dma20"])

trades = []
sig_days = df.index[df["signal"]]
for t in sig_days:
    i = df.index.get_loc(t)
    if i + 3 >= len(df):
        continue
    entry = df["close"].iloc[i]        # buy at the close of the signal day
    exit_ = df["close"].iloc[i + 3]    # sell at the close 3 sessions later
    trades.append(exit_ / entry - 1.0)

tr = pd.Series(trades) - 0.0006        # 3bp per side, index futures
print("trades:", len(tr))
print("mean per trade:", round(tr.mean() * 100, 2), "%")
print("win rate:", round((tr > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T03 =====
# T03 — Review request: post-earnings drift sleeve, results memo

A results memo submitted for gate review. The underlying code is not attached; review
the claims and methodology as written.

---

## Post-earnings positive-surprise long — validation summary (2021-2025)

**Universe.** NIFTY-200 members, membership taken as-of each date from the 42-snapshot
point-in-time constituent file (Mar/Sep snapshots). Window restricted to 2021-2025
because publication-date coverage in the earnings dataset is reliable only from 2021.

**Signal.** Positive earnings surprise: reported quarterly EPS above the trailing-4-quarter
trend extrapolation by more than one trend residual sigma. Signals are timestamped on the
`available_date` (publication date) of the filing, never the quarter-end.

**Execution.** Enter at the next session's OPEN after `available_date`. Entries skipped
when the open was locked at the upper circuit or the first-15-minute volume was zero
(9 entries dropped this way). Exit at the close of the 10th session after entry, no
exceptions. Costs: 25bp per side all-in (brokerage + impact at large/midcap slippage
standard).

**Result.** 412 trades. Mean net edge **+0.42% of spot per trade** (avg +Rs 3.1 per share
on an avg entry price of Rs 740); t-stat 3.4 (per-trade std 2.5%). Win rate 58%.
On a fixed Rs 50L notional with max 8 concurrent positions: CAGR 9.8%, Sharpe 1.1,
max DD -7.9%.

**Controls run.**
- *Placebo battery:* 200 random-entry baskets drawn from the same universe-dates, same
  trade count, and the SAME 10-session exit engine. Placebo mean +0.06%/trade; the
  strategy sits at the 92nd percentile of the placebo distribution. (Same trade count and
  identical holding period means the comparison is turnover-matched by construction.)
- *One-day-lag test:* lagging every input one extra day degrades the edge +0.42% -> +0.31%
  (graceful decay, no collapse).
- *Era splits:* 2021-22 +0.51%, 2023 +0.29%, 2024-25 +0.44% per trade.
- *Denominator check:* edge reported in % of spot and rupee points per share above;
  no per-premium or net-debit denominators anywhere.

**Verdict sought.** Entry edge appears real against matched nulls but the standalone
return is below the register bar. Recommend advancing to the sensitivity battery
(parameter surfaces, subsamples), NOT direct register entry.

---

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T04 =====
# T04 — Review request: quarterly revenue-growth rotation

Submission for the fundamental-momentum family. Universe membership is taken from the
42-snapshot point-in-time constituent file (as-of logic on Mar/Sep snapshot dates), so
the author states survivorship is handled. Prices are the adjusted union close panel.

Reported result: top-30 basket 21.7% CAGR vs universe equal-weight 12.9% (2016-2025),
quarterly rebalance, 40bp/side costs included.

```python
import pandas as pd

rev = pd.read_parquet("quarterly_revenue.parquet")
# columns: symbol, quarter_end (fiscal quarter end date), revenue (consolidated, Rs cr)
rev = rev.sort_values(["symbol", "quarter_end"])
rev["rev_yoy"] = rev.groupby("symbol")["revenue"].pct_change(4)

close = pd.read_parquet("close_panel.parquet")     # adjusted closes, IST dates
ret = close.pct_change()
members = load_pit_membership()                    # symbol lists as-of Mar/Sep snapshots

qe_dates = sorted(rev["quarter_end"].unique())
weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)

for qe in qe_dates:
    snap = rev[rev["quarter_end"] == qe].dropna(subset=["rev_yoy"])
    univ = members.asof(qe)                        # membership as of the quarter end
    snap = snap[snap["symbol"].isin(univ)]
    if len(snap) < 60:
        continue
    top = snap.nlargest(30, "rev_yoy")["symbol"]

    # rebalance on the first trading day AFTER the quarter ends, fill at open
    rebal_day = close.index[close.index.searchsorted(qe, side="right")]
    held = [s for s in top if s in close.columns]
    weights.loc[rebal_day:, :] = 0.0
    weights.loc[rebal_day:, held] = 1.0 / len(held)

# open-fill approximated as next session; positions earn from the session
# after the rebalance day
port = (weights.shift(1) * ret).sum(axis=1)
port -= turnover_costs(weights, bps_per_side=40)
print("CAGR:", ann_return(port))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T05 =====
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

===== T06 =====
# T06 — Review request: monthly NIFTY short strangle

Backtest of the flagship short-vol candidate. Option chain data is verified entry-day
prices (volume>0 enforced on both legs); spot is the official index close series.
The spot/chain dataset runs through 2026-06-30.

Reported result: 90 cycles 2019-01 to 2026-07, hit rate 84%, avg +41 pts/cycle,
worst cycle -412 pts.

```python
import pandas as pd

spot = load_spot_series()                  # official index closes, through 2026-06-30
chain = load_entry_chains()                # entry-day option prices, volume>0 verified

expiries = monthly_expiry_calendar("2019-01", "2026-07")   # exchange calendar

results = []
for exp in expiries:
    entry_day = last_trading_day_on_or_before(exp - pd.Timedelta(days=45))
    ref = spot.asof(entry_day - pd.Timedelta(days=1))      # prior close for strikes
    ce_k = round_to_strike(ref * 1.03)
    pe_k = round_to_strike(ref * 0.97)

    prem = chain.price(entry_day, exp, ce_k, "CE") + \
           chain.price(entry_day, exp, pe_k, "PE")         # entry-day close prints

    settle_spot = spot.asof(exp)                            # settlement level
    payoff = max(settle_spot - ce_k, 0) + max(pe_k - settle_spot, 0)

    pnl = prem - payoff - COSTS_PTS                         # 4.5 pts/cycle all-in
    results.append({"expiry": exp, "pnl": pnl, "win": pnl > 0})

r = pd.DataFrame(results)
print("cycles:", len(r), " hit rate:", round(r["win"].mean() * 100, 1), "%")
print("avg pnl:", round(r["pnl"].mean(), 1), "pts   worst:", round(r["pnl"].min(), 1))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T07 =====
# T07 — Review request: NIFTY weekly iron condor on F&O bhavcopy

Weekly defined-risk premium sleeve built on exchange bhavcopy (daily EOD rows:
OPEN/HIGH/LOW/CLOSE/SETTLE_PR/CONTRACTS/OI per contract). Underlying settlement uses
the official index close series.

Reported result: 2021-2025, 224 weeks traded, 31 skipped; avg +6.1 pts/week net,
hit rate 71%, worst week -312 pts (wings capped it).

```python
import pandas as pd

fo = load_fo_bhavcopy("NIFTY", "2021-01", "2025-12")   # option rows, daily EOD
idx_close = load_index_close()                          # official index closes

for tuesday in weekly_anchor_days:
    # --- decision, made after Tuesday's close on Tuesday data ---
    ref = idx_close.asof(tuesday)
    legs = {
        "sc": ("CE", round_to_strike(ref * 1.015)),
        "sp": ("PE", round_to_strike(ref * 0.985)),
        "lc": ("CE", round_to_strike(ref * 1.030)),
        "lp": ("PE", round_to_strike(ref * 0.970)),
    }
    # expiry: nearest weekly where ALL four legs traded on Tuesday (CONTRACTS > 0);
    # if none qualifies, fall back to the current monthly
    expiry = pick_expiry(fo, tuesday, legs, require_contracts=True)
    if expiry is None:
        skip("no liquid expiry"); continue

    # --- execution: Wednesday, fill at each leg's bhavcopy OPEN ---
    rows = fo.rows(date=tuesday + one_bday, expiry=expiry, legs=legs)
    if any(r.OPEN <= 0 or r.CONTRACTS == 0 for r in rows.values()):
        skip("leg not traded on entry day"); continue    # conservative no-fill
    credit = (rows["sc"].OPEN + rows["sp"].OPEN
              - rows["lc"].OPEN - rows["lp"].OPEN)
    credit -= slippage_ticks(4) + costs_pts()            # per-leg tick + charges

    # --- exit: hold to expiry, cash-settle at intrinsic from the INDEX close ---
    settle = idx_close.asof(expiry)
    payoff = (max(settle - legs["sc"][1], 0) - max(settle - legs["lc"][1], 0)
              + max(legs["sp"][1] - settle, 0) - max(legs["lp"][1] - settle, 0))
    book(week=tuesday, pnl=credit - payoff)

# guards: expiry <= idx_close.index.max() asserted inside pick_expiry;
# weeks with a scheduled major event (budget, RBI, election result) are skipped
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T08 =====
# T08 — Review request: NIFTY opening gap fade (1-minute data)

Intraday overlay using the vendor 1-minute NIFTY file (tz-aware IST timestamps; the
file includes every print the vendor ships for the session). Previous-day close is
taken from the same file's last bar at or before 15:30.

Reported result: 2022-2026, 388 trades, +0.09% per trade after 1bp/side futures costs,
win rate 58%.

```python
import pandas as pd
from datetime import time

m = pd.read_parquet("nifty_1min.parquet")     # ts (tz-aware IST), open, high, low, close
m["d"] = m["ts"].dt.date
m["t"] = m["ts"].dt.time

prev_close = (m[m["t"] <= time(15, 30)]
              .groupby("d")["close"].last().shift(1))

trades = []
for d, g in m.groupby("d"):
    if d not in prev_close.index or pd.isna(prev_close[d]):
        continue
    g = g.sort_values("ts")
    day_open = g.iloc[0]["open"]              # first print of the session
    gap = day_open / prev_close[d] - 1.0
    if abs(gap) < 0.004:                      # only fade gaps > 0.4%
        continue

    direction = -1 if gap > 0 else 1          # fade the gap
    entry_px = day_open
    exit_row = g[g["t"] >= time(10, 15)].iloc[0]
    exit_px = exit_row["close"]
    trades.append(direction * (exit_px / entry_px - 1.0) - 0.0002)

tr = pd.Series(trades)
print("trades:", len(tr), " mean:", round(tr.mean() * 100, 3), "%",
      " win:", round((tr > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T09 =====
# T09 — Review request: index trend filter with breadth confirmation

Daily long/flat timing model for the index sleeve. All series are official NSE daily
data with correct IST dates; `advances`/`declines` are the exchange's daily
market-breadth counts for each session.

Reported result: 2015-2025, long 38% of days, CAGR 17.1% vs buy-and-hold 12.4%,
max DD -11% vs -38%.

```python
import pandas as pd

df = pd.read_parquet("nifty_with_breadth.parquet")
# index: IST date; columns: open, close, advances, declines

df["ret1"] = df["close"].pct_change()

# features -- evaluated at day t's close, from data known by that close:
df["mom10"] = df["close"].pct_change(10)
df["vol20"] = df["ret1"].rolling(20).std()
df["adv_dec"] = (df["advances"] / df["declines"]).shift(-1)
df["above_dma"] = df["close"] > df["close"].rolling(50).mean()
df["vol_regime_ok"] = df["vol20"] < df["vol20"].rolling(100).mean()

df["signal"] = (
    (df["mom10"] > 0)
    & (df["adv_dec"] > 1.5)
    & df["above_dma"].fillna(False)
    & df["vol_regime_ok"].fillna(False)
)

# execution: signal at day t's close -> long from day t+1's open to day t+2's open
# (open-to-open return of the next session, aligned back to the signal day)
df["o2o_next"] = df["open"].shift(-2) / df["open"].shift(-1) - 1.0

pos = df["signal"].astype(int)
strat = pos * df["o2o_next"] - pos.diff().abs().fillna(0) * 0.0003

n = strat.notna().sum()
print("long share:", round(pos.mean() * 100, 1), "%")
print("CAGR:", round((1 + strat.dropna()).prod() ** (252 / n) - 1, 4))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T10 =====
# T10 — Review request: diversifier memo for a new event sleeve

Memo proposing to stack a new sleeve into the book. Review the claims and methodology
as written.

---

## Sleeve "EVT-1" — diversification case (2019-2025 backtest P&L)

**Profile.** Event-driven premium capture around scheduled announcements. 14 trades/yr
on average; the sleeve holds positions on ~19% of trading days and is flat otherwise
(flat days book 0). Standalone: 11.3% CAGR, Sharpe 0.94, worst month -6.2%.

**Correlation evidence (daily P&L, 2019-2025, 1,731 obs):**

| vs sleeve | daily corr |
|---|---|
| Momentum equity (MOM-EQ) | +0.02 |
| Quality-value equity (QV-EQ) | +0.01 |
| Short-vol index (SV-IDX) | +0.03 |
| Trend overlay (TR-OV) | +0.01 |

All pairwise daily correlations are indistinguishable from zero. **EVT-1 is an
uncorrelated return stream.**

**Stacking math.** Book Sharpe is currently 1.05. Adding an uncorrelated sleeve with
standalone Sharpe 0.94 at 20% risk weight lifts the projected book Sharpe to ~1.38
(standard root-N combination of independent streams). Proposed: fund EVT-1 at 20% of
book risk immediately; the diversification benefit does not depend on the sleeve's
standalone return staying at backtest levels.

**Monthly return excerpt (worst 5 book months in the window):**

| month | book (ex-EVT) | EVT-1 |
|---|---|---|
| Mar-2020 | -11.4% | -6.2% |
| Jun-2022 | -4.9% | -1.8% |
| Jan-2023 | -3.1% | -0.9% |
| Oct-2024 | -3.8% | -2.1% |
| Mar-2025 | -2.7% | -1.4% |

**Verdict sought.** Approve stacking at 20% risk weight on diversification grounds.

---

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T11 =====
# T11 — Review request: IV-richness straddle seller

Short-vol entry rule on the index. The raw IV series is noisy day-to-day, so the author
smooths it before testing richness. Data: daily ATM IV series (correct IST dates) plus
verified entry-day straddle prices.

Reported result: 2018-2025, 96 entries, avg +2.1% of premium per trade net, hit 76%.

```python
import pandas as pd

iv = pd.read_parquet("nifty_atm_iv.parquet")["iv"]     # daily ATM IV, %

# de-noise the series before comparing level vs local average
iv_ma = iv.rolling(11, center=True).mean()

rich = iv > 1.15 * iv_ma                # IV rich vs its local average
entry_days = rich & ~rich.shift(1).fillna(False)       # first day of a rich episode

trades = []
for d in iv.index[entry_days]:
    # sell the 1-month ATM straddle at the NEXT session's open,
    # exit at 50% of premium decay or 15 sessions, whichever first
    t = simulate_straddle(entry=next_open(d), exit_rule=("decay50", 15))
    if t is not None:                    # skipped if either leg untraded at entry
        trades.append(t.net_pnl_pct_premium)

tr = pd.Series(trades)
print("entries:", len(tr), " mean:", round(tr.mean(), 2),
      "% of premium  win:", round((tr > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T12 =====
# T12 — Review request: weekly short straddle on F&O bhavcopy

Hold-to-expiry weekly straddle engine on exchange bhavcopy data. Bhavcopy option rows
carry: INSTRUMENT, SYMBOL, EXPIRY_DT, STRIKE_PR, OPTION_TYP, OPEN, HIGH, LOW, CLOSE,
SETTLE_PR, CONTRACTS, OI, TIMESTAMP.

Reported result: 2020-2025, 261 weeks; hit rate 64%; several expiry weeks show
four-digit point losses even on weeks the index barely moved — the author attributes
these to expiry-day pin risk and asks whether to add a stop.

```python
import pandas as pd

fo = load_fo_bhavcopy("NIFTY", "2020-01", "2025-12")

for week in weekly_cycles:
    entry_day = week.first_session          # e.g. Friday after prior expiry
    ref = index_close.asof(entry_day - one_bday)
    k = round_to_strike(ref)                # ATM off prior close

    ce = fo.row(entry_day, week.expiry, k, "CE")
    pe = fo.row(entry_day, week.expiry, k, "PE")
    if ce.CONTRACTS == 0 or pe.CONTRACTS == 0:
        continue                            # only traded strikes at entry
    credit = ce.CLOSE + pe.CLOSE            # sell at entry-day close prints

    # exit at expiry: use the exchange's settlement field on the expiry-day row --
    # SETTLE_PR is the official settlement and avoids stale last-trade CLOSE prints
    ce_x = fo.row(week.expiry, week.expiry, k, "CE").SETTLE_PR
    pe_x = fo.row(week.expiry, week.expiry, k, "PE").SETTLE_PR
    debit = ce_x + pe_x

    book(week, pnl=credit - debit - costs_pts(4))

# summary output:
#   weeks: 261   hit: 64.0%   avg: -118.3 pts
#   worst 5 weeks all land ON expiry dates with |index move| < 0.4%:
#     2023-08-31: -23,912 pts   2021-04-08: -14,466 pts   2024-02-29: -21,880 pts ...
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T13 =====
# T13 — Review request: 12-1 momentum on the NIFTY-500

Classic cross-sectional momentum submission. Prices are the survivorship-complete
adjusted union panel (includes delisted names). Execution is next-open entry with
circuit/zero-volume no-fill checks and 45bp/side costs.

Reported result: 2013-2025, top-50 monthly-rebalanced basket 24.8% CAGR vs index 12.1%.

```python
import pandas as pd

close = pd.read_parquet("union_close_panel.parquet")   # adjusted, incl. delisted names

universe = pd.read_csv("nifty500_constituents.csv")["Symbol"].tolist()
# downloaded from the index provider's website, 2026-07 refresh, 500 symbols

close = close[[c for c in close.columns if c in universe]]
ret = close.pct_change()

# 12-1 momentum: return from t-252 to t-21 (skip the most recent month)
mom = close.shift(21).pct_change(231)

month_ends = close.groupby(close.index.to_period("M")).tail(1).index
weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)

for me in month_ends:
    row = mom.loc[me].dropna()
    if len(row) < 200:
        continue
    top = row.nlargest(50).index
    nxt = close.index[close.index.searchsorted(me, side="right")]
    weights.loc[nxt:, :] = 0.0
    weights.loc[nxt:, top] = 1.0 / 50

# next-open entries approximated at next session; no-fill on circuit-locked or
# zero-volume opens handled inside apply_fill_rules()
port = apply_fill_rules(weights.shift(1) * ret)
port -= turnover_costs(weights, bps_per_side=45)
print("CAGR:", ann_return(port), " maxDD:", max_drawdown(port))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T14 =====
# T14 — Review request: selected-nights overnight long, results memo

Memo for an overnight index sleeve. Review the claims and methodology as written.

---

## Overnight selected-nights long — validation summary (2019-2025)

**Signal.** Hold NIFTY futures long overnight only on "selected" nights: prior
20-session realized-vol percentile below 60 AND favourable weekday bucket. Both inputs
are computed at 15:00 from data through 14:59. Entry: futures bought 15:25-15:28
(marketable limit). Exit: next session 09:16-09:20 TWAP. Selected: ~55% of nights
(138/yr average).

**Result.** Gross edge on selected nights **+3.1bp/night**; costs 1.2bp/night round
trip (exchange + impact, futures); net **+1.9bp/night**, ~+2.6%/yr on notional.
Sharpe 1.21 on nightly P&L. t-stat 3.8 over 962 selected nights.

**Controls run.**
- *Unconditional-drift control:* ALL nights in the window earn +0.9bp/night on average
  (the index's ordinary overnight drift). An exposure-matched random-nights baseline
  (55% of nights, same count) earns +0.9bp/night net of the same costs. The selection
  adds **+2.2bp/night over matched exposure** — the claim is selection, not
  "overnight drift in costume".
- *Same-exit placebo:* 500 random night-subsets of identical size, run through the
  identical entry/exit engine and costs. Strategy at the 97th percentile.
- *One-day-lag test:* all inputs lagged one extra session: +3.1bp -> +2.2bp gross
  (graceful degradation, no collapse).
- *Era splits:* 2019-20 +2.4bp, 2021-22 +3.6bp, 2023-25 +3.2bp gross per night.
- *Costs:* taken from the approved futures cost standard; entry uses marketable limits
  and books no fill on the 3 nights the 15:25-15:28 window was limit-locked.

**Capacity/limits.** Futures-only, front month, ~Rs 40cr capacity at 5% participation.
Worst night -1.9%; worst month -1.7%.

**Verdict sought.** Diversifier-grade sleeve (net return modest but uncorrelated with
the day-session books). Recommend the orthogonality check vs existing sleeves next,
then paper.

---

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T15 =====
# T15 — Review request: IV-percentile strangle seller

Weekly short-vol rule on the index. The author standardizes the IV level before
thresholding, "so the rule generalizes across vol regimes". Entry-day option prices
are verified; entries are next-session-open after the signal evaluates true.

Reported result: 2015-2025, 214 entries, avg +1.7% of premium net, hit 79%,
worst trade -21% of premium (Mar-2020 skipped by the crash filter).

```python
import pandas as pd

hist = pd.read_parquet("nifty_iv_daily.parquet")       # 2015-2025 daily ATM IV

mu = hist["iv"].mean()
sd = hist["iv"].std()
hist["iv_z"] = (hist["iv"] - mu) / sd

# entry: IV meaningfully rich vs its normal level, but not crash regime
hist["entry"] = (hist["iv_z"] > 1.0) & (hist["iv_z"] < 2.5)

trades = []
for d in hist.index[hist["entry"]]:
    t = sell_weekly_strangle(
        signal_day=d,
        entry="next_open",                 # fills at next session's open prints
        wings=(0.97, 1.03),
        exit_rule=("hold_to_expiry",),
        liquidity=("both_legs_traded",),   # skip if either leg had no trades
    )
    if t is not None:
        trades.append(t.net_pnl_pct_premium)

tr = pd.Series(trades)
print("entries:", len(tr), " mean:", round(tr.mean(), 2), "% of premium",
      " hit:", round((tr > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T16 =====
# T16 — Review request: quality-tilt certification memo

Certification memo for a low-churn factor sleeve. Review the claims and methodology
as written.

---

## Quality-tilt mid/small portfolio vs random-basket hurdle (2016-2025)

**Strategy.** 40-name quality-tilt basket (profitability + leverage screen),
rebalanced **semiannually**. Measured one-way turnover: **38%/yr**.

**Hurdle (per firm SOP).** Distribution of 10,000 random equal-weight 40-name baskets
from the same mid/small segment, **refreshed monthly** (the standing random-basket
series). Measured one-way turnover of the hurdle baskets: **~330%/yr**.

**Costs.** Both arms charged the same honest mid/small cost model: 45bp per side
all-in (brokerage + impact + slippage).

| arm | gross CAGR | net CAGR |
|---|---|---|
| Quality-tilt (semiannual) | 15.0% | 14.6% |
| Random-basket hurdle, p50 (monthly refresh) | 14.7% | 11.5% |
| Random-basket hurdle, p95 (monthly refresh) | 16.9% | 13.7% |

**Reading.** Net of identical cost assumptions, the strategy beats the hurdle median by
**+3.1pp/yr** and clears even the 95th percentile of random baskets (14.6% vs 13.7%).
Statistical gates already passed: DSR 0.98, PBO 22%, parameter plateau confirmed,
lookahead audit 0-FAIL.

**Verdict sought.** Certify selection edge; register at +3.1pp/yr expected
outperformance over segment random.

---

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T17 =====
# T17 — Review request: calendar-spread timing engine

Monthly options calendar-spread family. The signal `ff` (front-back richness per unit
spot) is computed once per day from that day's settlement prints; higher `ff` = better
entry pricing for the spread. The question the engine answers: "which day inside the
T-30..T-10 window should we enter each cycle?"

Reported result: 2019-2026, 86 cycles, +7.2 pts avg per cycle net, hit 69%.

```python
import pandas as pd

cycles = build_monthly_cycles("2019-01", "2026-06")    # expiry calendar
ff = load_ff_series()          # daily: date, lead (days to expiry), ff value

results = []
for cyc in cycles:
    win = ff[(ff["expiry"] == cyc.expiry)
             & (ff["lead"] >= 10) & (ff["lead"] <= 30)]
    if len(win) < 8:
        continue

    # enter where the window's pricing is best
    best = win.loc[win["ff"].idxmax()]
    entry_day = next_session(best["date"])             # fill at next session's open

    spread = open_calendar_spread(entry_day, cyc.expiry,
                                  legs="near_short_far_long",
                                  liquidity="both_legs_traded_else_skip")
    if spread is None:
        continue
    pnl = close_at_lead(spread, lead=2)                # exit T-2, verified prints
    results.append(pnl - costs_pts(2))

r = pd.Series(results)
print("cycles:", len(r), " avg:", round(r.mean(), 1), "pts  hit:",
      round((r > 0).mean() * 100, 1), "%")
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T18 =====
# T18 — Review request: paper-book fill audit script

Script that audits whether last week's 501 paper entries (options legs, NFO) could
actually have been filled, by pulling daily candles from the broker API and checking
the entry day's traded volume. The broker's daily (ONE_DAY) candles are known to be
stamped at 00:00 IST.

Observed output: **all 501 legs flagged UNFILLABLE (no entry-day bar / zero volume)**,
including deep-liquid ATM NIFTY weeklies. The author concludes the paper book was
untradeable and recommends voiding the week's paper results.

```python
import time

def audit_leg(smart, leg):
    params = {
        "exchange": "NFO",
        "symboltoken": leg.token,
        "interval": "ONE_DAY",
        "fromdate": leg.entry_date.strftime("%Y-%m-%d") + " 09:15",
        "todate": (leg.entry_date + pd.Timedelta(days=5)).strftime("%Y-%m-%d") + " 15:30",
    }
    candles = smart.getCandleData(params)["data"]     # [[ts, o, h, l, c, vol], ...]
    time.sleep(1.3)                                   # rate-limit compliance

    entry_bar = None
    for c in candles or []:
        if c[0][:10] == leg.entry_date.strftime("%Y-%m-%d"):
            entry_bar = c
            break

    if entry_bar is None or entry_bar[5] == 0:
        return "UNFILLABLE"
    if entry_bar[5] * lot_value(leg) < 20 * leg.intended_notional:
        return "THIN"
    return "OK"

results = [audit_leg(smart, leg) for leg in paper_legs]
print(pd.Series(results).value_counts())
# UNFILLABLE    501
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T19 =====
# T19 — Review request: mid-cap momentum on the union panel

Cross-sectional momentum submission for the equity book. The author rebuilt an older
run after the data office published the survivorship-complete panel.

Reported result: 2014-2025, 16.2% CAGR net vs random-basket null p50 of 11.9%
(strategy at the 93rd percentile of 10,000 nulls); maxDD -34%.

```python
import pandas as pd

close = pd.read_parquet("close_panel_return_v11.parquet")   # union panel incl. delisted
stale = pd.read_parquet("stale_mask.parquet")               # frozen/stale price runs
close = close.mask(stale)                                    # stale rows excluded

members = load_pit_membership()      # 42 Mar/Sep point-in-time snapshots
ret = close.pct_change()

# 12-1 momentum, computed strictly from data through the signal date
mom = close.shift(21).pct_change(231)

for me in month_ends:
    univ = members.asof(me)                      # latest snapshot ON OR BEFORE me
    row = mom.loc[me, [s for s in univ if s in mom.columns]].dropna()
    row = row[eligible_midcap(row.index, asof=me)]
    if len(row) < 120:
        continue
    top = row.nlargest(40).index
    set_target_weights(date=first_session_after(me), names=top, w=1.0 / 40)

# execution: entries at the first session AFTER the rebalance date, filled at open;
# no-fill on circuit-locked or zero-volume opens (fill_check); 45bp/side costs.
#
# delistings: if a held name stops trading, the position is marked to its last
# traded price and the loss realized on the delisting date (no silent drop).
#
# null: 10,000 random 40-name baskets from the SAME panel, SAME PIT universe,
# SAME monthly rebalance dates and cost model (turnover-matched by construction).
port = run_engine(...)
print(report(port))
```

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

===== T20 =====
# T20 — Review request: RSI-dip entry validation memo

Memo claiming a validated entry signal. Review the claims and methodology as written.

---

## RSI-dip long on liquid large-caps — placebo validation (2018-2025)

**Signal.** RSI(3) < 20 on a liquid large-cap while the stock is above its 100-DMA.
Entries at the next session's open. 1,904 trades.

**Exit engine (strategy).** +2.0% profit target OR -4.0% stop OR 20-session time-out,
whichever hits first (intraday touch, next-tick fill). Average holding period 6.2
sessions.

**Placebo battery.** 500 baskets of random entries: same names, same period, same
number of trades per name. Placebo exit: **close of the 5th session after entry**
(fixed-time), chosen to approximate the strategy's typical holding period.

**Results.**

| arm | mean/trade (net) | win rate | avg hold |
|---|---|---|---|
| Strategy | +0.31% | 61% | 6.2 d |
| Placebo mean | +0.08% | 52% | 5.0 d |
| Placebo p99 | +0.24% | 55% | 5.0 d |

The strategy clears the **99th percentile** of the placebo distribution on mean/trade
and on win rate. Costs identical in both arms (30bp/side).

**Conclusion.** The entry signal carries real selection information; the probability
of the observed edge under the null is <1%. Recommend advancing to sizing and the
sensitivity battery with the entry certified.

---

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**

============================================================
# OUTPUT: first line `MODEL: <name>  TOOLS: off/on  MODE: fresh-per-task/one-chat`, then the ===== TASKID ===== blocks with answers.