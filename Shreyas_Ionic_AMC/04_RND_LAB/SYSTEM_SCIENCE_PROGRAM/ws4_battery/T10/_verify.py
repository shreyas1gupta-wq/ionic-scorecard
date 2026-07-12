# T10 verification: daily correlation on an EPISODIC sleeve is an artifact.
# A sleeve that is flat ~80% of days books zeros against the other sleeve's
# nonzero daily P&L, crushing the daily correlation toward 0 even when both
# sleeves load on the SAME monthly factor. Measured at the horizon where
# drawdowns live (monthly), the correlation reappears.
# (Firm precedent: 0.00-0.02 daily vs +0.36..+0.54 monthly, KB 25a.)
import numpy as np
import pandas as pd

rng = np.random.default_rng(9)
n_months, dpm = 84, 21
factor = rng.normal(0, 0.02, n_months)             # one shared monthly factor

daily_eq, daily_evt = [], []
for m in range(n_months):
    # equity sleeve: factor spread across the month + daily noise
    eq = factor[m] / dpm + rng.normal(0, 0.004, dpm)
    # event sleeve: flat except ~4 event days; event-day P&L loads on the SAME factor
    evt = np.zeros(dpm)
    days = rng.choice(dpm, size=4, replace=False)
    evt[days] = factor[m] / 4 + rng.normal(0, 0.004, 4)
    daily_eq.append(eq); daily_evt.append(evt)

eq = pd.Series(np.concatenate(daily_eq))
evt = pd.Series(np.concatenate(daily_evt))
month_id = np.repeat(np.arange(n_months), dpm)

daily_corr = eq.corr(evt)
meq = eq.groupby(month_id).sum()
mevt = evt.groupby(month_id).sum()
monthly_corr = meq.corr(mevt)

print("daily correlation  : %+.2f   (memo's evidence)" % daily_corr)
print("monthly correlation: %+.2f   (the horizon where drawdowns live)" % monthly_corr)
assert abs(daily_corr) < 0.25 and monthly_corr > 0.5, "demo failed"
print("DEFECT CONFIRMED: the same data shows ~zero daily corr and strong monthly")
print("corr; the 'uncorrelated diversifier' claim and the root-N Sharpe projection")
print("are artifacts of measuring an episodic sleeve at daily frequency.")
print("Fix: quote monthly / drawdown-window correlation; note the memo's own worst-")
print("month table already shows EVT-1 negative in all five worst book months.")
