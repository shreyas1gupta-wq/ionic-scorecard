# T20 verification: placebo WITHOUT the same exit engine. The strategy exits on
# +2%/-4%/20d (asymmetric target/stop, avg hold ~6d); the placebos exit at a
# fixed 5-session close. Two mechanical consequences on an UPWARD-DRIFTING
# market, with ZERO entry skill in either arm:
#   1) win rate: the near target is hit far more often than the far stop, so the
#      target/stop engine converts noise+drift into ~60%+ "wins" vs ~52% for a
#      fixed 5-day exit;
#   2) mean/trade: the target/stop engine holds longer on average (E[hold]>5d)
#      and therefore harvests more drift per trade (optional stopping:
#      E[pnl] = drift x E[hold]).
# So the memo's separation (61% vs 52% wins, higher mean/trade) is reproducible
# with RANDOM entries in both arms -- the "99th percentile" certifies the exit
# rule, not the entry signal.
import numpy as np

rng = np.random.default_rng(29)
n_trades, drift, vol = 40000, 0.0006, 0.015     # bull-sample large-cap dailies

def strategy_exit(cum):
    """+2% target / -4% stop / 20-session timeout; filled at the crossing day."""
    for i, r in enumerate(cum):
        if r >= 0.02 or r <= -0.04:
            return r, i + 1
    return cum[-1], 20

s_pnl, s_hold, p_pnl = [], [], []
for _ in range(n_trades):
    path = rng.normal(drift, vol, 20)           # RANDOM entry: no signal at all
    cum = np.cumprod(1 + path) - 1
    r, h = strategy_exit(cum)
    s_pnl.append(r); s_hold.append(h)
    p_pnl.append(cum[4])                        # placebo: close of 5th session

s_pnl, p_pnl = np.array(s_pnl), np.array(p_pnl)
print("RANDOM entries, strategy exit engine : %+.3f%%/trade  win %4.1f%%  hold %.1fd"
      % (100 * s_pnl.mean(), 100 * (s_pnl > 0).mean(), np.mean(s_hold)))
print("RANDOM entries, placebo exit engine  : %+.3f%%/trade  win %4.1f%%"
      % (100 * p_pnl.mean(), 100 * (p_pnl > 0).mean()))
gap_win = (s_pnl > 0).mean() - (p_pnl > 0).mean()
gap_mean = s_pnl.mean() - p_pnl.mean()
print("separation from the exit engine alone: win rate %+.1fpp, mean %+.3f%%/trade"
      % (100 * gap_win, 100 * gap_mean))
assert gap_win > 0.05 and gap_mean > 0.0003, "defect demo failed"
print("DEFECT CONFIRMED: with zero entry skill in BOTH arms, the exit-engine")
print("mismatch alone manufactures a win-rate and mean/trade separation in the")
print("memo's direction, so the placebo percentile does not measure the entry.")
print("Fix: run the placebos through the IDENTICAL +2%/-4%/20d exit engine;")
print("only entry selection may differ between strategy and null.")
