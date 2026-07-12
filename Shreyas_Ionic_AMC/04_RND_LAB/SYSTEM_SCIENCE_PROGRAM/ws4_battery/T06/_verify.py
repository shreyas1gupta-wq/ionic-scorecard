# T06 verification: settlement beyond the end of data (T8 / guard-L7 class).
# Data ends 2026-06-30 but the expiry loop runs to Aug-2026. For those cycles,
# spot.asof(expiry) silently returns the LAST AVAILABLE close (~= the entry-day
# level), so both strangle legs "expire" worthless near where they were sold:
# guaranteed full-premium fake wins booked for cycles that are still open.
# Demo: random-walk spot; the walk truly continues past the data cut, but the
# backtest only sees data up to the cut.
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n, cut = 545, 500                       # true path 545 days, data ends at day 500
px = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, n)),
               index=pd.date_range("2024-01-01", periods=n, freq="B"))
data = px.iloc[:cut]                    # what the backtest can see

expiries = pd.date_range("2024-03-01", periods=18, freq="21B")
fake_wins, true_pnls = [], []
for exp in expiries:
    if exp <= data.index[cut - 1] - pd.Timedelta(days=30):
        continue                        # only inspect cycles near/past the cut
    entry = exp - pd.Timedelta(days=30)
    ref = data.asof(entry)
    ce_k, pe_k = ref * 1.03, ref * 0.97
    prem = ref * 0.015                  # 1.5% of spot premium, fixed for the demo

    settle_backtest = data.asof(exp)    # the task's line: stale last value
    pnl_backtest = prem - max(settle_backtest - ce_k, 0) - max(pe_k - settle_backtest, 0)

    settle_true = px.asof(exp)          # what actually happens
    pnl_true = prem - max(settle_true - ce_k, 0) - max(pe_k - settle_true, 0)

    if exp > data.index[-1]:            # cycles the data cannot settle
        fake_wins.append(pnl_backtest)
        true_pnls.append(pnl_true)
        print("expiry %s beyond data end: backtest books %+7.2f  | true outcome %+7.2f"
              % (exp.date(), pnl_backtest, pnl_true))

fake_wins, true_pnls = np.array(fake_wins), np.array(true_pnls)
assert len(fake_wins) >= 1 and (fake_wins > 0).all(), "demo failed: no fabricated cycles"
print("\nDEFECT CONFIRMED: %d cycles expire AFTER max(data); .asof marks them at the"
      % len(fake_wins))
print("stale last close, booking near-max-premium 'wins' for positions still open.")
print("Fix: assert expiry <= data.index.max(); drop or report those cycles as OPEN.")
