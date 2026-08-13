"""TAIL_PUT_ROLL_20260802 -- Monte Carlo: 10%-OTM NIFTY put under 3 forward-looking (mean,vol)
scenarios. Pure simulation, no historical data -- answers "what would this hedge cost/pay under
an ASSUMED future regime" rather than "what did it do historically."
Self-consistency assumption [DISCLOSED]: entry premium priced via Black-Scholes using the SAME
sigma as the simulation's realized vol (no separate vol-risk-premium modeled -- i.e. IV=RV for
this exercise). r=6.5% (matches other arms this session). T=0.5yr (6M, matching the base case).
"""
import numpy as np
from vollib.black_scholes import black_scholes
from vollib.black_scholes.greeks.analytical import delta

S0 = 25000.0
K = round(S0 * 0.90 / 50) * 50   # 10% OTM strike
T = 0.5
R = 0.065
COST = 1.77
N_PATHS = 100_000

SCENARIOS = [
    ("A: bull/low-vol   (12% mean, 12% vol)", 0.12, 0.12),
    ("B: sluggish/mod-vol (4% mean, 16% vol)", 0.04, 0.16),
    ("C: bear/high-vol  (-5% mean, 20% vol)", -0.05, 0.20),
]

print(f"S0={S0} K={K} (10% OTM) T={T}yr r={R} paths={N_PATHS:,}\n")
rng = np.random.default_rng(20260802)

for label, mu, sigma in SCENARIOS:
    premium = black_scholes('p', S0, K, T, R, sigma)
    Z = rng.standard_normal(N_PATHS)
    ST = S0 * np.exp((mu - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * Z)
    payoff = np.maximum(K - ST, 0.0)
    net = payoff - premium - COST

    print(f"--- {label} ---")
    print(f"  entry premium (BS, sigma={sigma:.0%} as IV): {premium:.1f} pts")
    print(f"  mean payoff: {payoff.mean():.1f} | mean net: {net.mean():.1f} pts/cycle "
          f"({net.mean()*2:.1f} pts/yr annualized)")
    print(f"  win rate (net>0): {(net > 0).mean():.1%} | prob expires worthless: {(payoff == 0).mean():.1%}")
    pcts = np.percentile(net, [5, 25, 50, 75, 95])
    print(f"  net P&L percentiles [5/25/50/75/95]: {np.round(pcts, 1).tolist()}")
    print(f"  max simulated payoff: {payoff.max():.1f} (ST_min={ST.min():.0f}, "
          f"{(ST.min()/S0-1):.1%} move)")
    print()
