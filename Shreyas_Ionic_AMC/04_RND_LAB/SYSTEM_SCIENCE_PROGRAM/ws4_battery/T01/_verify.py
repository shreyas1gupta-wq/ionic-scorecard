# T01 verification: HF daily bars stamped 18:30 UTC = next-day 00:00 IST.
# Naive .dt.date (UTC) labels each bar ONE DAY EARLY. Joined against a correctly
# dated execution panel, the signal at label d contains the TRUE close of d+1 --
# so "enter next session's close" actually enters at the very close the signal
# was computed from (one day earlier than implementable).
# Demo: mean-reverting daily returns. Mislabeled pipeline conditions on ret[t]
# and earns ret[t+1] (1 lag apart -> full reversal edge). Correct pipeline
# conditions on ret[t] and earns ret[t+2] (2 lags -> edge ~rho^2 ~ 0).
import numpy as np

rng = np.random.default_rng(7)
n_days, n_sym, rho = 3000, 60, -0.25

eps = rng.normal(0, 0.015, (n_days, n_sym))
ret = np.zeros((n_days, n_sym))
for t in range(1, n_days):
    ret[t] = rho * ret[t - 1] + eps[t]

def backtest(lag):
    """Condition on cross-sectional most-oversold at t, earn ret[t+lag]."""
    pnl = []
    for t in range(1, n_days - lag):
        picks = np.argsort(ret[t])[:15]          # 15 most oversold on day t
        pnl.append(ret[t + lag, picks].mean())
    return np.array(pnl)

# mislabeled panel: signal label d holds TRUE day d+1 data; "next close" entry
# means holding true day d+1 -> d+2, i.e. earn ret ONE step after the signal day
fake = backtest(lag=1)
# correct labels: signal at true d, enter close d+1, exit close d+2 -> two steps
true = backtest(lag=2)

ann = 252 ** 0.5
print("MISLABELED (tz bug) : mean/day %+.4f%%  Sharpe %5.2f"
      % (100 * fake.mean(), fake.mean() / fake.std() * ann))
print("CORRECT labelling   : mean/day %+.4f%%  Sharpe %5.2f"
      % (100 * true.mean(), true.mean() / true.std() * ann))
assert fake.mean() > 4 * abs(true.mean()), "defect demo failed"
print("DEFECT CONFIRMED: naive UTC .dt.date labelling fabricates the reversal edge.")
