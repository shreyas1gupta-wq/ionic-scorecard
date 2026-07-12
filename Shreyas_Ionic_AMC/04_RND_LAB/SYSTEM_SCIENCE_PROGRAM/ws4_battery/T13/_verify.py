# T13 verification: universe/membership lookahead (T5). The price panel itself is
# survivorship-complete, but the UNIVERSE is TODAY'S constituent list applied to
# 2013-2025. Membership in today's NIFTY-500 is an outcome: names that grew/rose
# into the index are in; names that shrank, delisted or fell out are excluded.
# Screening 2013's cross-section through that filter pre-selects winners.
# Demo: names have heterogeneous drift; "today's index" = the names with the best
# terminal size. Even a RANDOM basket inside that filtered universe beats the
# honest point-in-time universe.
import numpy as np

rng = np.random.default_rng(31)
n_sym, n_days = 800, 2520                       # ~10 years
mu = rng.normal(0.0002, 0.00040, n_sym)         # heterogeneous drift per name
rets = rng.normal(0, 0.02, (n_days, n_sym)) + mu

cum = (1 + rets).cumprod(axis=0)
today_members = np.argsort(cum[-1])[-500:]      # today's list = terminal top-500
pit_members = np.arange(n_sym)                  # honest PIT universe (all listable names)

def random_basket_cagr(universe, n_draws=300, k=50):
    out = []
    for _ in range(n_draws):
        picks = rng.choice(universe, size=k, replace=False)
        path = (1 + rets[:, picks].mean(axis=1)).prod()
        out.append(path ** (252 / n_days) - 1)
    return np.mean(out)

cagr_today = random_basket_cagr(today_members)
cagr_pit = random_basket_cagr(pit_members)
print("random basket inside TODAY'S constituents : %.1f%% CAGR" % (100 * cagr_today))
print("random basket inside PIT universe         : %.1f%% CAGR" % (100 * cagr_pit))
assert cagr_today > cagr_pit + 0.01, "defect demo failed"
print("DEFECT CONFIRMED: conditioning the historical universe on today's membership")
print("adds several CAGR points before any signal is applied; the momentum result")
print("is contaminated regardless of the panel being survivorship-complete.")
print("Fix: membership from the point-in-time snapshot file, as-of each rebalance.")
