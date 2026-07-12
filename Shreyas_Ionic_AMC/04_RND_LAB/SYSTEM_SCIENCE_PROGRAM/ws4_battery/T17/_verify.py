# T17 verification: argmax-over-window entry (T9). win['ff'].idxmax() picks the
# best-priced day of the WHOLE T-30..T-10 window -- knowing day d was the window
# maximum requires having seen every day after d. No causal trader can enter
# "at the peak"; any causal rule (threshold crossing, fixed lead) enters at a
# systematically worse level. Selecting the extreme of an observed series inside
# a window is perfect hindsight timing.
# Demo: driftless random walk; "enter at the window's best price, exit at window
# end" mints money from nothing; the causal threshold version earns ~0.
# (Firm precedent: forward_factor v2 argmax entry, caught in K-012 review.)
import numpy as np

rng = np.random.default_rng(13)
n_windows, w = 4000, 21

argmax_pnl, causal_pnl = [], []
for _ in range(n_windows):
    px = 100 * np.cumprod(1 + rng.normal(0, 0.01, w))
    # "ff" = entry cheapness = -price (higher ff == better entry pricing)
    best_day = np.argmin(px)                     # idxmax of ff == idxmin of price
    if best_day < w - 1:
        argmax_pnl.append(px[-1] / px[best_day] - 1)     # buy the hindsight low
    # causal rule: buy the FIRST day price is 1% below the window's first print
    hit = np.where(px < px[0] * 0.99)[0]
    if len(hit) and hit[0] < w - 1:
        causal_pnl.append(px[-1] / px[hit[0]] - 1)

a, c = np.array(argmax_pnl), np.array(causal_pnl)
print("argmax-of-window entry (task): %+.2f%% per cycle on a DRIFTLESS walk (%d)"
      % (100 * a.mean(), len(a)))
print("causal threshold entry       : %+.2f%% per cycle (%d)"
      % (100 * c.mean(), len(c)))
assert a.mean() > 0.01 and abs(c.mean()) < 0.005, "defect demo failed"
print("DEFECT CONFIRMED: entering at the window extreme fabricates edge from pure")
print("noise. Next-session fill does NOT repair it -- identifying the peak still")
print("requires the unseen remainder of the window. Fix: pre-registered causal")
print("trigger (first ff crossing of a fixed threshold) or a fixed entry lead.")
