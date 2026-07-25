# NEW STRATEGY GENESIS — 2026-07-25 (Gate-1 intake, pre-registered)

**Origin:** Principal order "create new strategies from scratch" + open vehicle mandate ("option
selling, delta neutral, directional, credit/debit spread, straddle, strangle or anything else, just
high sharpe").
**Constraint applied:** the firm's own banked lesson (`results/STACKED_BOOK_20260711/RESULTS.md:11`)
— quarterly sleeve correlation reaches 0.53 and averages ~0.35 among equity-linked sleeves, capping
the Sharpe multiplier at ~sqrt(1/rho) ≈ 1.7x, so **"new sleeves must be different-FACTOR... not
additional equity variants."** Every candidate below is therefore screened for *what factor it
actually harvests*, not for what option structure it wears.
**Also applied:** OPT-SWEEP-50 already tested 49 structural variants on NIFTY VRP and found a ~1.0
Sharpe ceiling; KNOWLEDGE_BASE lesson 24 puts realistic net NIFTY VRP Sharpe at 0.9–1.2. So no
candidate here is "another structure on the same premium."

Pre-registered before any result. Editing a definition after its test = new version, new trials count.

---
## NS-1 — OVERNIGHT THETA HARVEST via LOW-GAMMA STRANGLE  ★ primary, testable now
**Factor:** the *overnight* segment of the variance risk premium — a distinct return stream from
intraday VRP, and measured (not assumed) this session.
**Evidence that motivates it (n=259, `results/DTE_1DTE_BACKTEST_20260725/gaps_1dte.csv`):** ATM
straddle premium from D−1 15:25 to D0 open: **mean 0.965x, median 0.920x, decays on 74.9% of
nights** — but p95 1.306x, max 3.481x, and **5.4% of nights gap through a 30% stop at the open.**
**Hypothesis:** the overnight decay is real and harvestable; what killed the 1DTE test was **ATM
gamma**, not the overnight itself. Moving strikes out reduces gap sensitivity faster than it reduces
premium (gamma decays faster than vega away from the money), so a wider strangle should keep most of
the decay with a bounded worst night.
**Why this is NOT the killed 1DTE:** 1DTE entered D−1 and held to D0 **15:25**, absorbing a whole
expiry day of intraday risk. NS-1 exits at the **open** — ~17.5 hours, zero intraday exposure, a
completely different risk profile.
**Spec (FROZEN):** sell 1× CE + 1× PE of the D0-expiring contract at D−1 15:25 at strike distance
d from spot; buy back at D0 first bar ≥09:15. No stop (there is no market open to run one in — this
is the honest treatment, and it is why bounded gap sensitivity must come from strike choice).
Declared surface: **d ∈ {0 (ATM), ±0.5%, ±1.0%, ±1.5%, ±2.0%} = 5 cells.** Costs = the frozen
`fee(px)=0.012·px+0.267` model, 4 fills.
**KNOWN RISK the test must expose:** the ₹20/order brokerage floor is **0.267 pts/lot regardless of
premium**, so on a cheap far strangle fixed costs can swamp an 8% decay. This is the most likely
kill mode and is why absolute pts/night, not %, is the headline metric.
**PRE-REGISTERED KILL:** net ≤ 0 pts/night after costs at every d → KILL. If positive but worst-night
loss exceeds ~3× mean nightly gain → KILL on tail shape (that is the 1DTE failure recurring).

### NS-1 GATE-3 RESULT — **KILLED, all 5 arms** (2026-07-25, same day as pre-registration)
Run `ns1_overnight.py`, n=258-259 nights per arm, 2021-05→2026-06.

| d | net pts/night | gross | cost | cost/gross | t | PF | win% | entry prem | worst night | worst/mean | ann pts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.0% (ATM) | +0.83 | 5.23 | 4.40 | **84%** | 0.30 | 1.08 | 64.0% | 141.5 | −455.8 | **550x** | 43 |
| 0.5% | +1.62 | 4.23 | 2.61 | 62% | 0.62 | 1.19 | 70.2% | 66.4 | −448.4 | 277x | 84 |
| 1.0% | +1.46 | 3.26 | 1.80 | 55% | 0.72 | 1.25 | 76.7% | 32.0 | −353.4 | **242x** | 76 |
| 1.5% | +1.11 | 2.55 | 1.45 | 57% | 0.68 | 1.28 | 74.5% | 17.1 | −306.3 | 276x | 58 |
| 2.0% | +0.68 | 1.97 | 1.29 | 65% | 0.54 | 1.25 | 66.4% | 10.4 | −234.1 | 346x | 35 |

**KILLED on the pre-registered tail criterion at every strike distance** (worst night 242–550x mean
nightly gain, bar was 3x). Also fails on significance independently: **t = 0.30–0.72 everywhere.**

**My hypothesis was directionally right and quantitatively useless.** I predicted wider strikes would
shed gap sensitivity faster than premium. They do — worst night improves monotonically from −455.8
(ATM) to −234.1 (2.0%), roughly halving. But edge falls too, so the worst/mean ratio bottoms at 242x
(d=1.0%) and never approaches survivable. Halving a catastrophic tail leaves a catastrophic tail.

**Costs are the executioner, exactly as pre-registered.** Costs consume **55–84% of gross** in every
arm. At d=2.0% the entire strangle collects 10.4 points and the ₹20/order floor alone is 1.07 points
(0.267 × 4 fills) — 10% of gross before slippage. Annualised edge is 35–84 pts/lot/yr ≈ **1–2.3% on
margin**: trivial even ignoring the tail. Liquidity is NOT the problem — zero-volume legs 0.0% in all
arms, so fills are clean and this is a genuine economic verdict, not a data artifact.

**MY OWN REPORTING ERROR, and it is the firm's oldest one.** I sold the overnight-decay finding to the
Principal as "mean 0.965x / banks ~9.5% of premium per night." True — and **premium-denominated**,
which is the exact denominator artifact that killed S-01, S-02 and S-03 and produced the firm's HARD
RULE that every per-trade edge be quoted in **denominator-free rupee points + %spot**. In points the
overnight decay is ~5.2 gross and **~0.8–1.6 net**. The percentage framing made a ~1-point edge sound
like a discovery. Quote points first, always.

**What this banks (the finding is worth keeping even though the strategy dies):** the overnight VRP in
NIFTY is REAL but ~5 points gross at ATM and ~2–4 points further out — structurally too small to
survive a 4-fill round trip. Any future overnight-premium design must either (a) collect
substantially more than ~5 points, or (b) use fewer than 4 fills. This retires the whole
"harvest the overnight" family unless one of those two changes. Trials ledger: +5 cells.

## NS-2 — NIFTY vs SENSEX VOL PREMIUM RELATIVE VALUE
**Factor:** cross-index vol *dispersion* — market-neutral-ish, so it adds little equity beta. This is
the one candidate that genuinely attacks the correlation ceiling above.
**Evidence:** `results/SX1_SENSEX_FEASIBILITY_20260711/` measured SENSEX 0DTE premium at **1.22x
NIFTY's** in the same window (0.697% vs 0.574% of spot), n=132, t=2.95.
**Hypothesis:** SENSEX is 30 stocks vs NIFTY's 50, so it is genuinely less diversified and *some* of
that 1.22x is fair compensation for higher realized vol. If the implied gap persistently exceeds the
realized gap, the excess is harvestable: sell the richer index's vol, buy the cheaper's.
**Cheap kill (do this BEFORE any structure):** compute (SENSEX implied − NIFTY implied) minus
(SENSEX realized − NIFTY realized) over the overlap. **If the premium gap is fully explained by the
realized-vol gap → KILL**, the 1.22x is fair value and there is nothing to harvest.
**BLOCKED ON:** D-009 verification + DATA_CATALOG entry for the 1-min SENSEX chains
(`hf_index_options_1m/options/SENSEX/`, 144 files 2023-08→2026-05, currently uncatalogued).
Overlap with NIFTY ≈ 2.8 yrs. Cross-checkable in-house against the catalogued BSE bhavcopy.
**Bonus property:** NIFTY expiry is Tuesday, SENSEX Thursday — the legs need not collide.

## NS-3 — NIFTY / BANKNIFTY IMPLIED-CORRELATION MEAN REVERSION
**Factor:** implied *correlation* — neither direction nor vol level. Genuinely orthogonal to
everything in the book.
**Hypothesis:** a proxy for implied correlation between NIFTY and BANKNIFTY (from their respective
ATM implied vols and the known bank weight in NIFTY) mean-reverts; trade the spread when it is at a
percentile extreme.
**Data:** BANKNIFTY 1-min + daily on disk; BANKNIFTY chains in the same HF source-family as NIFTY.
**Cheap kill:** if the proxy shows no mean reversion (Hurst ≥ 0.5 / no significant AR(1) pull) or its
amplitude is below round-trip cost on two option legs → KILL. Weakest of the four on tradability;
sequenced last.

## NS-4 — GOLD/EQUITY TILT over the banked 50/50 baseline
**Factor:** genuinely non-equity (gold), the firm's clearest different-factor asset.
**Baseline already banked (2026-07-13):** 50/50 NIFTY–gold monthly rebalance = 12.3% CAGR, 10.5%
vol, −21.5% maxDD on real ETFs 2013-26 — and it *dominated* the K-016 rotation that was rejected.
**Hypothesis:** a vol-scaled or trend-conditioned tilt between the two beats static 50/50 on Calmar.
**Data:** `etf_gold_silver/{niftybees,goldbees_ext}_daily.parquet` 2013-26, in hand (Kavya D-009
formalisation still pending).
**PRE-REGISTERED KILL — deliberately harsh, because this is the one most likely to produce a
flattering overfit:** must beat static 50/50 on Calmar **out of sample** (split 2013-19 / 2020-26)
with the tilt rule fixed on the first half only. In-sample-only improvement → KILL.

---
## Sequencing (cheapest-and-most-decisive first)
1. **NS-1 now** — data and engine both in hand from the 1DTE build; hours, not days.
2. **NS-2 after D-009** on the SENSEX chains (that check is owed anyway and unblocks S1-SX too).
3. **NS-4** — self-contained, small data, but honour the OOS split.
4. **NS-3 last** — most novel, least certain to be tradable.

## Standing honesty note
Three of these four are still *volatility* strategies, so NS-2's dispersion angle and NS-4's gold leg
are the only ones that truly diversify the book's factor exposure. Said plainly rather than
presenting four candidates as four independent bets.
