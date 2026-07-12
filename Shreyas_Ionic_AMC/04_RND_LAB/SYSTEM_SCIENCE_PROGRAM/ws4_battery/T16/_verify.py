# T16 verification: turnover-cost confound. The hurdle churns ~330%/yr one-way,
# the strategy 38%/yr; both are charged 45bp/side. The memo's own table proves
# the "+3.1pp net edge" is almost entirely the cost differential, not selection.
# (Firm precedent: KB lesson 20 / I-016 -- turnover-matched comparator law.)

BPS = 0.0045                       # 45bp per side
t_strat, t_hurdle = 0.38, 3.30     # one-way annual turnover
gross_strat, gross_hurdle = 0.150, 0.147
net_strat, net_hurdle = 0.146, 0.115

drag_strat = 2 * t_strat * BPS     # buys + sells
drag_hurdle = 2 * t_hurdle * BPS
print("cost drag, strategy : %.2fpp/yr" % (100 * drag_strat))
print("cost drag, hurdle   : %.2fpp/yr" % (100 * drag_hurdle))

cost_differential = drag_hurdle - drag_strat
gross_edge = gross_strat - gross_hurdle
net_edge = net_strat - net_hurdle
print("gross edge (memo table)      : %+.2fpp/yr" % (100 * gross_edge))
print("cost differential            : %+.2fpp/yr" % (100 * cost_differential))
print("net 'edge' claimed           : %+.2fpp/yr" % (100 * net_edge))
print("gross edge + cost diff       : %+.2fpp/yr" % (100 * (gross_edge + cost_differential)))

# memo numbers are internally consistent with drag arithmetic (rounding ~0.2pp)
assert abs((gross_edge + cost_differential) - net_edge) < 0.003
# and the selection component (gross vs gross) is a tenth of the claim:
assert gross_edge < 0.005 and cost_differential > 0.025
print("\nDEFECT CONFIRMED: ~2.6pp of the 3.1pp comes from charging the hurdle 8.7x")
print("the strategy's turnover; gross-vs-gross the edge is +0.3pp (noise). Gates")
print("passed because they test the number, not the comparator. Fix: turnover-")
print("matched placebo (semiannually-refreshed random baskets) before certifying.")
