# LOT SCALING RE-COST — the sizing recommendation survives, thinner and with CPPI's case weaker
**2026-08-03 · rebuild of `LOT_SCALING_20260801/lot_scaling.py`, cost model only. Fidelity check:
the OLD-cost historical (non-bootstrap) path reproduces the original run's end-equity/return/maxDD
bit-for-bit to the reported decimal (verified programmatically) before trusting the NEW numbers.**

## What changed, what didn't
Signal (THREE_SOLDIERS), hold windows (1-session=26 bars, 3-session=78 bars), the RANDOM-LONG beta
control, the 5 policies, MAX_LOTS=40, RUIN_FRAC=50%, MARGIN_PCT=10% of contemporaneous notional,
N_BOOT=2,000 stationary block bootstrap at block=3 months, one position at a time, pathsafe
pessimistic bound — all unchanged. Only the cost function changed:
- **OLD** (unchanged, kept for comparison): flat era-stepped `4.47` pre-Oct-2024 / `5.97` after +0.5 slip.
- **NEW** (STT_RECOST_20260803 basis): `0.0005 × entry_spot + 1.97 + 0.5`, STT on **contemporaneous**
  spot at the Budget-2026 0.05% futures rate, applied throughout history (the FORWARD convention used
  in PORTFOLIOS_RECOST_20260803 — "as if every trade had paid the new rate," the number for a forward
  capital call). At spot 24,000 this is 14.47 pts, matching STT_RECOST_20260803 exactly.

Trades were built ONCE (identical entries/exits/gross P&L); both cost columns were computed on the
same trades, and the SAME block-bootstrap month-ordering draws were replayed against the OLD and NEW
monthly series per arm/policy (paired, not independently resampled) — this is what "confirm from the
actual replay" means operationally, and it is why a flat per-trade subtraction would have missed the
spot-path effect below. Minor method note: because draws are now shared across policies too (not just
across cost bases, an improvement on the original's per-policy-fresh-draw design), the OLD-basis
bootstrap numbers here differ from the original FINDINGS.md by <1-3pp (noise at n=2,000) — e.g. beta
P(ruin) naive-monthly 17.8% (original) vs 18.7% (here); no qualitative conclusion changes.

## Q1 — Do the per-trade edges survive? YES, but the realistic forward number is thinner than the
11-year average, and thinner than the flat -7.2pt estimate implied

| arm | mean OLD | mean NEW (11yr avg) | delta | mean spot (11yr) |
|---|---|---|---|---|
| SOLDIERS 1-session | +18.52 | **+13.77** | -4.75 | 14,918 |
| SOLDIERS 3-session | +45.52 | **+40.80** | -4.72 | 14,854 |
| RANDOM-LONG (beta) | +10.63 | +5.91 | -4.71 | 14,857 |

The realized delta (-4.7 pts) is smaller than the -7.2 pts implied by pricing at today's spot (24,000),
because the new cost scales with spot and the 11-year sample's average entry spot (~14,900) is well
below today's ~25,000 — early cheap trades pull the average delta down. **This is the opposite of what
a flat subtraction would show, and it is exactly the kind of thing "replay, don't subtract" catches.**

But it cuts both ways — the number that actually matters for a trade taken **today** is worse, not
better, than the 11-year blended average:

| arm | mean OLD, last 12mo | mean NEW, last 12mo (spot ~25,065) | mean NEW, 11yr avg |
|---|---|---|---|
| SOLDIERS 1-session | +16.09 | **+7.55** | +13.77 |
| SOLDIERS 3-session | +31.89 | **+23.36** | +40.80 |
| RANDOM-LONG (beta) | -0.12 | -8.64 | +5.91 |

At current spot, the forward-relevant net edge is **+7.55 pts for 1-session and +23.36 for 3-session** —
roughly 45% below what the full-history "NEW" average implies. Both remain positive. The edge survives.
It is materially thinner than the historical average suggests, at the spot the Principal will actually
trade at.

## Q2 — Does the CPPI verdict reverse the way it did at portfolio level? Partially — Calmar degrades
everywhere, but it never had a clean Calmar edge over naive-monthly to reverse; ruin-protection is intact

Bootstrap medians, both cost bases, all 5 policies × 3 arms (full table in `bootstrap_paths_recost.csv`):

| arm | policy | ret OLD | ret NEW | P(ruin) OLD | P(ruin) NEW | P(>25%DD) OLD | P(>25%DD) NEW | maxDD OLD | maxDD NEW | Calmar OLD | Calmar NEW |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1-session | FIXED_1 | 214% | 159% | 0.0% | 0.0% | 0.0% | 0.0% | -4.4% | -6.3% | 2.348 | 1.359 |
| 1-session | NAIVE_MONTHLY | 6659% | 4727% | 0.0% | 1.7% | 35.6% | 66.5% | -20.2% | -31.1% | 2.210 | 1.296 |
| 1-session | MARGIN_ONLY | 8012% | 5697% | 2.6% | 8.8% | 63.4% | 82.3% | -32.6% | -43.0% | 1.461 | 0.984 |
| 1-session | MDD_BUFFER | 7785% | 5323% | 0.5% | 1.7% | 52.5% | 74.2% | -26.1% | -34.5% | 1.774 | 1.200 |
| 1-session | **CPPI_FLOOR** | 198% | 57% | **0.0%** | **0.0%** | 23.2% | 24.1% | -19.9% | -20.3% | 0.427 | 0.177 |
| 3-session | FIXED_1 | 224% | 201% | 0.0% | 0.0% | 0.0% | 0.0% | -3.0% | -3.4% | 3.632 | 2.944 |
| 3-session | NAIVE_MONTHLY | 7289% | 6461% | 0.0% | 0.1% | 10.0% | 16.6% | -12.4% | -15.0% | 3.648 | 2.947 |
| 3-session | MARGIN_ONLY | 8541% | 7600% | 0.0% | 0.1% | 28.4% | 35.5% | -16.7% | -19.1% | 2.873 | 2.383 |
| 3-session | MDD_BUFFER | 8432% | 7430% | 0.0% | 0.0% | 23.6% | 30.5% | -15.2% | -16.3% | 3.138 | 2.822 |
| 3-session | **CPPI_FLOOR** | 7884% | 6647% | **0.0%** | **0.0%** | 12.7% | 15.7% | -14.3% | -15.5% | 3.266 | 2.921 |
| BETA | FIXED_1 | 137% | 75% | 0.0% | 0.4% | 1.8% | 18.1% | -10.5% | -15.9% | 0.744 | 0.319 |
| BETA | NAIVE_MONTHLY | 3797% | **-50%** | **18.7%** | **50.1%** | 91.6% | 99.2% | -52.9% | -68.6% | 0.711 | -0.065 |
| BETA | MARGIN_ONLY | 4268% | **-53%** | **33.8%** | **59.8%** | 92.5% | 98.5% | -57.9% | -71.4% | 0.656 | -0.088 |
| BETA | MDD_BUFFER | 3127% | 309% | 3.6% | 7.6% | 93.1% | 98.6% | -44.5% | -48.1% | 0.802 | 0.277 |
| BETA | **CPPI_FLOOR** | 21% | 2% | **0.0%** | **0.0%** | 24.6% | 6.7% | -21.6% | -18.2% | 0.080 | 0.010 |

**What actually happens to CPPI:**
- Its Calmar collapses under the new cost on every arm (1-session -59%, 3-session -11%, beta -88%),
  the same mechanism as the portfolio-level finding: CPPI buys drawdown protection by capping lots,
  and a thinner underlying edge means the same-sized "premium" (foregone lots) buys less return.
- **But it never had a clean Calmar edge over naive-monthly to begin with.** On 1-session CPPI was
  already the worst policy by Calmar at OLD cost (0.427 vs naive's 2.210) — unchanged conclusion, if
  anything the gap narrows in relative terms but 1-session-CPPI was never the recommendation anyway
  (original FINDINGS called it "a genuine flaw," median lots ≈0). On 3-session — the arm the original
  recommendation actually rested on — CPPI's Calmar (3.266) was already fractionally *below*
  naive-monthly's (3.648) at OLD cost, a ~10% shortfall; at NEW cost the two are essentially tied
  (2.921 vs 2.947, a ~1% shortfall). So this is **not a portfolio-style flip from helps-to-hurts** —
  CPPI was a near-tie-or-slightly-worse Calmar choice on 3-session before the hike, and remains a
  near-tie-or-slightly-worse Calmar choice after it. What genuinely worsens for both is P(>25%DD) in
  absolute terms (naive 10.0%→16.6%, CPPI 12.7%→15.7%) — the whole 3-session sizing exercise gets
  riskier, CPPI included, not specifically CPPI-vs-naive.
- **What is unchanged, and is the actual reason to still prefer CPPI:** P(ruin) stays pinned at
  **0.0% at both cost bases, on all three arms**, while every other lot-adding policy's ruin
  probability *rises* under the new cost — most dramatically on the beta control (next section). CPPI
  remains the only policy in this set whose ruin protection is cost-regime-invariant.

## Q3 — Beta control ruin probability: gets materially WORSE, as hypothesized, and it is the
single most decision-relevant number here

| policy | P(ruin) OLD | P(ruin) NEW | change |
|---|---|---|---|
| NAIVE_MONTHLY | 18.7% | **50.1%** | **+31.4pp, 2.7x** |
| MARGIN_ONLY | 33.8% | **59.8%** | **+26.1pp, 1.8x** |
| MDD_BUFFER | 3.6% | 7.6% | +4.0pp, 2.1x |
| CPPI_FLOOR | 0.0% | 0.0% | unchanged |

Under naive monthly lot-adding — the policy that most literally matches the Principal's stated plan
("add 1-2 lots after a good month") — **one bootstrap path in two now ends in ruin if the compounding
were pure beta rather than genuine signal.** Since the real THREE_SOLDIERS arm is measured to be
roughly 40-60% beta (per the original session's placebo work), this is the risk that actually sits
underneath the recommendation, not a hypothetical. This number alone is sufficient reason not to run
naive monthly lot-adding regardless of what the signal-arm numbers show in isolation.

## Q4 — Does 3-session-beats-1-session hold, and is it reinforced? YES, clearly reinforced

Under NAIVE_MONTHLY (matches the original comparison):

| | 1-session | 3-session | spread | ratio |
|---|---|---|---|---|
| P(>25%DD), OLD cost | 35.6% | 10.0% | 25.6pp | 3.6x |
| P(>25%DD), NEW cost | 66.5% | 16.6% | **49.9pp** | **4.0x** |

Under CPPI_FLOOR (the recommended policy), the reinforcement is starker on Calmar specifically:

| | 1-session | 3-session | ratio |
|---|---|---|---|
| Calmar, OLD cost | 0.427 | 3.266 | 7.6x |
| Calmar, NEW cost | 0.177 | 2.921 | **16.5x** |

The higher cost taxes frequency exactly as expected — 1-session's 13 trades/month absorb the fixed
per-trade cost bite far more often than 3-session's 5.5/month. "Edge-to-drawdown ratio, not frequency,
is what makes a strategy scalable" is **more true after the STT hike, by a factor of roughly 2x on the
ceiling-breach spread and roughly 2.2x on the CPPI Calmar gap.**

## Supplementary — MAX_LOTS relaxed 40→100,000 (capacity desk confirmed 40 lots = 0.047% of NIFTY
futures ADV; the cap is not a liquidity constraint). NEW cost basis, same paired draws.

| arm | policy | med ret (cap 40) | med ret (cap off) | P(>25%DD) cap40 | P(>25%DD) cap off | med maxLots (cap off) |
|---|---|---|---|---|---|---|
| 1-session | NAIVE_MONTHLY | 4727% | 6526% | 66.5% | 66.5% | 86 |
| 1-session | CPPI_FLOOR | 57% | 64% | 24.1% | 35.2% | 13 |
| 3-session | NAIVE_MONTHLY | 6461% | 10290% | 16.6% | 16.2% | 104 |
| 3-session | CPPI_FLOOR | 6647% | **6204%** | 15.7% | **39.9%** | 654 |

**Two different stories, not one.** For NAIVE_MONTHLY, margin — not the 40-lot cap — becomes the real
constraint once the cap is lifted (median lots settle at 86-104, not 40, and not "unlimited"); median
return rises 38-59% with essentially no change to tail risk, confirming the 40-cap was arbitrary and
mildly binding for this policy. **For CPPI_FLOOR on the 3-session arm, relaxing the cap makes things
WORSE, not better**: P(>25%DD) balloons from 15.7% to 39.9% (median lots run up to 654 in some paths)
while median return actually *falls slightly* (6647%→6204%) — the CPPI cushion math, once freed from
the accidental brake the 40-lot cap provided, levers into bigger drawdowns without a corresponding
median-return benefit. **The arbitrary cap was, by accident, doing real risk-management work for
CPPI specifically.** If MAX_LOTS is ever revisited on capacity grounds, CPPI needs its own explicit
cap derived from risk (not simply inherited from whatever the liquidity study allows), or its formula
needs a hard ceiling independent of margin.

## Q5 — Corrected recommendation
1. **"Run 1 lot until forward evidence exists" still stands, more strongly.** P0_FIXED_1 remains the
   only row with ~0% ruin and ~0% ceiling breach at both cost bases (1-session 214%→159% total return,
   3-session 224%→201%, maxDD -3% to -6% throughout) — and the forward-relevant per-trade edge at
   TODAY's spot (+7.55 pts 1-session, +23.36 pts 3-session) is thinner than the 11-year backtest
   average, which is one more reason not to lever an edge that has not yet been proven live.
2. **If scaling: 3-session hold with the CPPI drawdown floor remains the best available policy**, but
   its case is now thinner — its Calmar edge over naive-monthly on 3-session was never large (a ~10%
   shortfall pre-hike, an even smaller ~1% shortfall post-hike: essentially a tie) — the reason to
   still prefer it is that **its P(ruin) is the only one immune to the cost regime** (0.0% at both
   bases, all arms, vs naive-monthly's beta-control ruin rocketing to 50.1%).
3. **Do not relax MAX_LOTS=40 casually.** It is confirmed not a liquidity constraint (0.047% ADV), but
   for the CPPI policy specifically it is accidentally doing risk-management work — removing it nearly
   triples the 3-session ceiling-breach probability for no median-return gain. Any capacity-driven
   relaxation needs a policy-specific risk cap, not a blanket lift to the ADV-implied number.
4. **The historical 5,000-10,000% figures remain arithmetic, not forecast — MORE so than before.**
   They still hit MAX_LOTS=40 almost immediately (median lots = 40 in most policies at both cost
   bases) and are still >50% leveraged index beta on an 11-year, +186% bull sample. Nothing here should
   be read as what the strategy will return; it is what maximum-permitted leverage compounds to when it
   happens to be right, on the one historical path we have.

## Files
`lot_scaling_recost.py` (full rebuild + Calmar addendum) · `historical_paths_recost.csv` ·
`bootstrap_paths_recost.csv` · `maxlots_relaxed_recost.csv` · `trades_1session.csv` ·
`trades_3session.csv` · `trades_beta.csv` · `meta.json` · `run_log.txt`
