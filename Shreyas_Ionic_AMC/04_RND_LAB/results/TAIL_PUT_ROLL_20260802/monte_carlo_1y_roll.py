"""TAIL_PUT_ROLL_20260802 -- Monte Carlo: 1Y backspread, roll-before-expiry timing.
Same 3 forward scenarios as the naked-put MC. Paired paths: each simulated path is evaluated
under all 4 exit rules simultaneously (hold-to-expiry, roll 3/2/1 months before expiry), pricing
the early-exit value via Black-Scholes at that timepoint using the SAME scenario sigma (no
separate vol-risk-premium modeled here, same self-consistency assumption as the naked-put MC).
"""
import numpy as np
from vollib.black_scholes import black_scholes

S0 = 25000.0
SHORT_K = round(S0 * 0.95 / 50) * 50
LONG_K = round(S0 * 0.90 / 50) * 50
R = 0.065
COST = 3 * 1.77
N_PATHS = 60_000
N_STEPS = 252  # daily steps over 1 year

SCENARIOS = [
    ("A: bull/low-vol   (12% mean, 12% vol)", 0.12, 0.12),
    ("B: sluggish/mod-vol (4% mean, 16% vol)", 0.04, 0.16),
    ("C: bear/high-vol  (-5% mean, 20% vol)", -0.05, 0.20),
]
ROLL_POINTS = [("hold_to_expiry", 0.0), ("roll_3mo_before", 3 / 12), ("roll_2mo_before", 2 / 12),
               ("roll_1mo_before", 1 / 12)]

print(f"S0={S0} shortK={SHORT_K} longK={LONG_K} paths={N_PATHS:,} steps={N_STEPS}\n")
rng = np.random.default_rng(20260803)

for label, mu, sigma in SCENARIOS:
    dt = 1.0 / N_STEPS
    Z = rng.standard_normal((N_PATHS, N_STEPS))
    logret = (mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * Z
    path = S0 * np.exp(np.cumsum(logret, axis=1))
    path = np.hstack([np.full((N_PATHS, 1), S0), path])  # prepend t=0

    entry_short = black_scholes('p', S0, SHORT_K, 1.0, R, sigma)
    entry_long = black_scholes('p', S0, LONG_K, 1.0, R, sigma)
    net_debit0 = entry_short - 2 * entry_long

    print(f"--- {label} --- entry short_prem={entry_short:.1f} long_prem={entry_long:.1f} "
          f"net_debit0={net_debit0:.1f}")
    for name, t_remaining_at_roll in ROLL_POINTS:
        if t_remaining_at_roll == 0.0:
            S_at = path[:, -1]
            short_val = np.maximum(SHORT_K - S_at, 0.0)
            long_val = np.maximum(LONG_K - S_at, 0.0)
        else:
            step_idx = int(round((1.0 - t_remaining_at_roll) * N_STEPS))
            S_at = path[:, step_idx]
            short_val = np.array([black_scholes('p', s, SHORT_K, t_remaining_at_roll, R, sigma) for s in S_at])
            long_val = np.array([black_scholes('p', s, LONG_K, t_remaining_at_roll, R, sigma) for s in S_at])
        exit_value = 2 * long_val - short_val
        net = exit_value - net_debit0 - COST
        print(f"  {name:18s}: mean_net={net.mean():7.1f} median={np.median(net):7.1f} "
              f"win%={(net>0).mean():5.1%} p5={np.percentile(net,5):8.1f} p95={np.percentile(net,95):8.1f}")
    print()
