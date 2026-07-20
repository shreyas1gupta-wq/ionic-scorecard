"""
v1_token_economics.py (2026-07-20) - effective token-cost reduction of the V1 weekly-incremental
router vs naive re-research, and vs the old quarterly full re-score.
Full = ~2min analyst + ~1min FM (Principal def). Delta = ~1min. Carry = 0. News-scan = batched.
Anchored to MEASURED costs from the Nifty-100 run where possible; every estimate is labelled.
"""
# ---- per-pass token costs -------------------------------------------------
# [DATA] N100 deep full-research agents measured 75k-113k tokens (mean ~93k), 66-agent run 2026-07-19/20.
DEEP_ANALYST = 93_000          # [DATA] measured mean, deep ~3min pass
ANALYST_2MIN = 60_000          # [EST] V1 ~2min pass, cached-thesis-anchored, ~0.65x the deep pass
FM_1MIN      = 30_000          # [EST] ~1min FM / portfolio-view pass
FULL_V1      = ANALYST_2MIN + FM_1MIN   # ~90k, a full re-research (2min + 1min)
DELTA_1MIN   = 30_000          # [EST] ~1min look at ONE news item vs the cached thesis
NEWSSCAN_PER = 1_200           # [EST] batched news-scan, ~25 stocks/agent -> per-stock share

# ---- routing model --------------------------------------------------------
EARN_PER_YR  = 4               # [DATA] a stock reports ~4x/year -> 4 forced FULLs
WEEKS        = 52
DELTA_RATE   = 0.08            # [EST] share of non-earnings stock-weeks with material news -> DELTA


def annual(N, delta_rate=DELTA_RATE, full=FULL_V1):
    full_yr   = N * EARN_PER_YR * full
    scan_yr   = N * (WEEKS - EARN_PER_YR) * NEWSSCAN_PER          # scan everyone not in a FULL that week
    delta_yr  = N * (WEEKS - EARN_PER_YR) * delta_rate * DELTA_1MIN
    v1        = full_yr + scan_yr + delta_yr
    naive_wk  = N * WEEKS * full                                  # re-research everyone every week
    quarterly = N * EARN_PER_YR * full                            # old cadence: full re-score 4x/yr, no weekly
    return dict(v1=v1, naive_weekly=naive_wk, quarterly=quarterly,
                full_yr=full_yr, scan_yr=scan_yr, delta_yr=delta_yr,
                red_vs_naive=1 - v1 / naive_wk, v1_vs_quarterly=v1 / quarterly)


def M(x):
    return f"{x/1e6:,.1f}M"


print("Per-pass (tokens):  FULL(2min analyst {a}k + 1min FM {f}k) = {t}k | DELTA {d}k | news-scan {n}k/stock | CARRY 0"
      .format(a=ANALYST_2MIN//1000, f=FM_1MIN//1000, t=FULL_V1//1000, d=DELTA_1MIN//1000, n=NEWSSCAN_PER/1000))
print("Routing: {e} earnings/stock/yr -> forced FULLs; the rest get a cheap weekly news-scan; ~{r:.0%} of those -> DELTA\n"
      .format(e=EARN_PER_YR, r=DELTA_RATE))
for N in (125, 750):
    a = annual(N)
    print(f"=== universe N={N} (annual) ===")
    print(f"  naive weekly full re-research : {M(a['naive_weekly'])} tokens/yr")
    print(f"  V1 incremental               : {M(a['v1'])} tokens/yr  "
          f"(FULL {M(a['full_yr'])} + scan {M(a['scan_yr'])} + delta {M(a['delta_yr'])})")
    print(f"  old quarterly full re-score  : {M(a['quarterly'])} tokens/yr")
    print(f"  -> reduction vs naive weekly : {a['red_vs_naive']*100:.1f}%")
    print(f"  -> V1 cost vs quarterly      : {a['v1_vs_quarterly']:.2f}x  (weekly freshness for ~this much more)\n")

print("Robust headline (routing-driven, cost-independent):")
print(f"  full-research passes/yr per stock: naive weekly {WEEKS}  ->  V1 {EARN_PER_YR}  = {(1-EARN_PER_YR/WEEKS)*100:.0f}% fewer FULL passes")
print("\nSensitivity of the vs-naive reduction to the DELTA rate (N=125):")
for dr in (0.03, 0.05, 0.08, 0.15, 0.30):
    print(f"  delta_rate {dr:>4.0%}: reduction {annual(125, delta_rate=dr)['red_vs_naive']*100:.1f}%")
print("\nIf V1 FULL is the heavier measured deep pass ({}k) instead of 90k: reduction vs naive still {:.1f}% (N=125)"
      .format(DEEP_ANALYST//1000, annual(125, full=DEEP_ANALYST)['red_vs_naive']*100))
