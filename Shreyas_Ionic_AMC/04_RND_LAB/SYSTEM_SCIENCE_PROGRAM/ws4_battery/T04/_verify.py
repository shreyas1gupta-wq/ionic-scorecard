# T04 verification: PIT/publication lookahead (T1). The screen sorts on the
# quarter's revenue growth and rebalances on the FIRST trading day AFTER the
# fiscal quarter ends -- but Indian results are published up to ~45 days later.
# Whatever part of the surprise gets priced on the announcement day is captured
# by the backtest and is uncapturable in reality.
# Demo: surprise s known only at announcement (qe+45d); price jumps 2%*s on the
# announcement day, zero drift afterwards. Portfolio formed at quarter end on s
# books the jump; portfolio formed at the available date books ~nothing.
import numpy as np

rng = np.random.default_rng(21)
n_sym, n_q, days_per_q = 200, 24, 63
ann_day = 45  # announcement day offset within the quarter

edge_qe, edge_avail = [], []
for q in range(n_q):
    s = rng.normal(0, 1, n_sym)                       # standardized surprise
    daily = rng.normal(0, 0.02, (days_per_q, n_sym))  # idiosyncratic noise
    daily[ann_day] += 0.02 * s                        # announcement-day jump
    top = np.argsort(s)[-30:]                         # top-30 by surprise

    # A) task's timing: enter day 0 of the new quarter, hold the quarter
    edge_qe.append(daily[:, top].sum(axis=0).mean())
    # B) honest timing: enter the day AFTER the announcement
    edge_avail.append(daily[ann_day + 1:, top].sum(axis=0).mean())

edge_qe, edge_avail = np.array(edge_qe), np.array(edge_avail)
print("formed at quarter-end (task) : %+.2f%% per quarter" % (100 * edge_qe.mean()))
print("formed at available date     : %+.2f%% per quarter" % (100 * edge_avail.mean()))
assert edge_qe.mean() > 0.02 and abs(edge_avail.mean()) < 0.01, "defect demo failed"
print("DEFECT CONFIRMED: the entire 'edge' is the announcement jump, tradeable")
print("only by acting on numbers ~45 days before they were published.")
