# How we score a stock — the workflow, explained

**For:** anyone joining the NDPMS desk. No prior knowledge of the codebase assumed.
**Companion to:** the `Ionic_Portfolio_Review` skill (the reference manual) and
`FIVE_SIGNAL_AND_V3_SCORING_SPEC.md` (the frozen spec). This file explains *why*; those explain *what*.
**As at:** 2026-08-07.

---

## 1. What the score is for, and what it is not

We score stocks a client **already owns**. The question is never "should we buy this" — it is
**"should this stay in the book?"** That is why the vocabulary is **Sell or Hold only, never Buy**, and
why the whole design leans conservative: the cost of holding a bad position is real and compounding,
while the cost of selling a decent one is an opportunity we can re-enter.

The score is **0-100** and it is an **input, not a verdict**. It shortlists; a person decides. Anything
in this document can be overridden by an analyst with a documented case — in one direction only (see §7).

---

## 2. The shape of the whole thing

```
        ┌─────────────── SEVEN PILLARS ───────────────┐
        │  what the business earns, how fast it grows, │
        │  what you pay, what the price is doing,      │
        │  and who else is buying                      │
        └──────────────────────┬───────────────────────┘
                               │  weighted average
                               ▼
                      COMPOSITE (two horizons)
                       3-year view  ·  1-year view
                               │
                               ▼  safety gates can CAP it
                      GATED COMPOSITE
                               │
                               ▼  red flags subtract, clean books add a little
                        FINAL 3Y  ·  FINAL 1Y
                               │
                               ▼  blend 60/40
                         BASE SCORE
                               │
                               ▼  + the analyst's forward view
                        IONIC SCORE (0-100, capped 5-95)
                               │
                               ▼
                     THE CALL:  Sell  /  Hold
                               (+ trim eligibility)
```

Read that top to bottom and you have the model. The rest of this file is each box explained.

---

## 3. The seven pillars — what each one actually measures

Every pillar is a **percentile rank against the other ~750 stocks**, not an absolute figure. A pillar
score of 80 means "better than 80% of the universe on this measure". It does **not** mean "good".
That distinction matters more than any other single idea in this document.

| Pillar | Measures | Built from | 3Y wt | 1Y wt |
|---|---|---|---|---|
| **Quality** | Does it earn well on the capital it uses? | ROE and ROCE, ranked **within sector** | 20% | 16% |
| **Growth** | Is the top line growing? | 3-year revenue CAGR (3Y) / 1-year revenue growth (1Y) | 20% | 16% |
| **Value** | What are we paying for that? | P/E vs universe, P/E vs sector-and-size peers, P/B, free-cash-flow yield | 18% | 16% |
| **Stage / Technical** | What is the price actually doing? | 12m and 24m returns, halved if below the 200-day average | 14% | 26% |
| **Sector & Macro** | Is the whole sector working? | sector-average return, adjusted for whether cyclicals suit the current regime | 11% | 13% |
| **Ownership Flow** | Are institutions buying or leaving? | quarter-on-quarter FII + DII shareholding change | 9% | 8% |
| **Accumulation** | Is there quiet buying under the surface? | on-balance-volume slope | 8% | 5% |

**Why two horizons.** The 3-year view is fundamentals-led (Quality + Growth + Value = 58%). The 1-year
view is behaviour-led (Stage jumps to 26%). A company can be a fine business having a bad year, or a
weak business in a hot sector — one number would hide both. We keep them separate all the way to the
final blend.

**Why sector-neutral for Quality.** A software company's 25% ROE and a utility's 12% are not comparable
in absolute terms; the utility may be the better operator in its own industry. Ranking within sector
asks "is this a good version of what it is".

**Why inputs are winsorised at 2%/98%.** One company with a 2,500% revenue jump off a tiny base would
otherwise compress everyone else into the bottom of the rank. We clip the extremes before ranking.

---

## 4. The safety gates — where the model refuses to be optimistic

These are **multiplicative caps**, applied after the weighted average. They cannot help a score, only
limit it. That asymmetry is deliberate: a strong balance sheet is already reflected in Quality, so the
gate exists purely to stop a leveraged or illiquid company scoring well on momentum alone.

| Gate | Trigger | Effect |
|---|---|---|
| Balance sheet | D/E > 2.5 **or** interest cover < 1.5 | **caps the score at 40** |
| Balance sheet | D/E > 1.5 **or** interest cover < 3 | **× 0.85** |
| Liquidity | 60-day median turnover below the size-tier bar | **caps at 50** |

**Two exemptions you must understand, because they look like bugs otherwise:**

**Financials are exempt from the entire balance-sheet gate.** Not just the D/E part — the whole thing.
For a bank or NBFC, borrowing *is* the business model, and interest expense is its **cost of funds**,
not debt service. Insurers barely have interest expense at all. When we briefly applied interest cover
to financials, it flagged **New India Assurance as RED at a coverage ratio of −399 with zero debt**, plus
four healthy capital-market firms. The ratio simply does not describe those businesses.

**Power, real estate, telecom and construction are exempt from the D/E trigger only.** Project debt and
regulated debt are how those businesses are normally financed, so a high ratio says little. **Interest
cover still applies to them** — leverage may be normal, but being unable to service it never is. That
is the honest form of the exemption.

A caution on classification: solar *generation* sits in Power (exempt); solar *equipment* manufacturers
sit in Capital Goods, where leverage is not structural, so the gate still bites them. Exempting on the
word "solar" would let the wrong half through.

---

## 5. Red flags and the small boost

**Red flags** (each one counted): interest cover < 1.5 · D/E > 2.5 (non-financials) · negative 1-year
revenue growth · growth decelerating by more than 15 percentage points.

Penalty = `−min(10, 2^flags − 1)`. So one flag costs 1 point, two cost 3, three cost 7, four cost 10.
**The escalation is deliberate** — one problem can be circumstance, three at once is a pattern.

**Boost** = +3, only if there are **zero** flags *and* both Quality and Value are above the 60th
percentile. Deliberately small. A clean, reasonably-priced, decent business earns a nudge, not a
promotion.

---

## 6. The forward view — the only place a human opinion enters the number

Everything above is mechanical and backward-looking. An analyst then researches each stock (business
model, earnings quality, sector cycle, a reverse-DCF sanity check) and produces two things:

**(a) An expected EPS growth rate for the next 3-5 years**, which is banded into points:

| expected EPS growth | <5% | 5-10% | 10-15% | 15-20% | 20-25% | ≥25% |
|---|---|---|---|---|---|---|
| points | **−15** | −5 | 0 | +5 | +10 | **+15** |

**(b) Their own Sell or Hold call**, which is worth:
- analyst says **Sell** → **−6**
- analyst says **Hold** on a stock the model would sell → **+6** (the "rescue")
- they agree → 0

Total adjustment is clamped to ±20, then two caps apply: **expected growth below 10% can never produce
a net uplift**, and **an analyst Sell can never produce a net uplift**.

**Three things about this leg that are easy to get wrong:**

1. **It is EPS growth, not revenue growth.** The Growth *pillar* is trailing revenue; this is expected
   earnings. They are genuinely different — across 550 stocks they rank only **0.41** correlated, and
   **23% of them disagree in sign** (revenue up, EPS down, or the reverse). A company can compound
   revenue 55% while EPS falls 95% — margin collapse, dilution, interest. Both facts are real and the
   model uses each where it belongs.
2. **We do not mix trailing revenue into it.** That was tried and it inverted the signal. BDL: the
   analyst expected **+15% EPS**, trailing revenue was **−27%** on delivery delays, and a blended figure
   produced the **maximum −15 penalty on a company the analyst liked**. Of 93 names then being
   penalised, 75 had negative trailing revenue and 20 had a healthy analyst estimate.
3. **The +20 "exceptional" tier is switched off.** It requires share dilution under 2%, which we do not
   currently capture. Granting it on the other two conditions alone over-awarded 27 names.

---

## 7. From score to call

```
Ionic Score = clamp( base + forward adjustment , 5 , 95 )
              where base = 0.60 × final 3Y  +  0.40 × final 1Y

below 40      →  SELL
40 and above  →  HOLD
     40 - 50  →  trim-ELIGIBLE if the position is over 2.5% of the book,
                 and/or if the analyst's own call is Sell
     above 50 →  HOLD, and an analyst Sell is OVERRULED
```

**The 40 bar is absolute. Nothing above 40 is ever a Sell.** Not a bad sector, not a stretched
valuation, not a dissenting analyst.

**Why the analyst cannot sell above 50.** The score already weighed valuation — Value is 18% of it. When
the ceiling was absent, the model was selling **BAJAJ-AUTO at 67** on a valuation argument, and of the
23 such cases **9 had a Value pillar reading Upper or Top-25%**: the analyst overriding a price the model
had looked at and considered reasonable. Above 50 the evidence is broadly good and one dissenting view
should not outrank seven pillars. Between 40 and 50 the evidence is genuinely mixed, so the analyst's
view moves it to Trim.

**Why 40-50 is not automatically "Trim".** It confers *eligibility*. Whether to trim depends on
**position weight**, which only exists inside a client's book — a universe-wide file has no portfolio in
it, so it can flag eligibility and nothing more. Concentration guidance: 5-10% is fine if growth is
strong; above 10% expect a trim; above 20% is extreme.

**Discretion runs one way only.** An analyst may **veto or soften** an action; they may not manufacture
one. Below 40, a Hold needs a documented case (~60% confidence). At 40-50, a Trim needs a documented
case and the `exceptional_override` field set, or the build fails its own QA gate. This asymmetry is
what stops judgment becoming a licence to invent.

**Sanity check you should run on every book.** The 750-stock universe produces roughly **33% Sells**. A
client book coming out far below that is a signal of **override leakage** — someone has been rescuing
too freely. The current universe runs 26%, which is already worth watching.

---

## 8. The v3 correction layer — why the scores you read are not the raw engine's

There is a real bug in the engine, and `fix_thin_coverage_v3.py` corrects it **without modifying the
engine**. It writes `full750_scored_v3.csv` alongside the original. **Use the v3 file.**

**The bug.** When a pillar is missing, the engine skips it and re-weights across the survivors. That
sounds harmless. It is not — the missing pillar's weight is **handed** to whatever remains. For a
company listed eight months ago, what remains is precisely the price pillars, and a post-listing rally
makes those strong; the fundamental pillars that would temper it are the missing ones. So the score
converges on "this went up", wearing the costume of a seven-pillar quantamental composite.

Measured: **67 names re-allocating an average 37% of their composite weight**, worst inflation
**+13.3 points**. One company scored a comfortable **58.8 Hold off a single pillar out of seven**.

**How v3 fixes it, in order:**

| Step | What it does | Why |
|---|---|---|
| Growth artefacts | revenue CAGR that is infinite or >200% → treated as missing | a first full year after listing produces a meaningless CAGR off a near-zero base |
| History class | full (≥2y) / 1-2y / <1y, from the price file | the fix differs by how much history genuinely exists |
| 1-year sibling | a missing 3-year pillar is filled from its 1-year twin | a 14-month-old listing has a real 12-month trend; discarding it throws away its only honest observation |
| Listing-price technical | for <1y names, rank the return **since listing** against everyone else measured over the **same window** | it is the only price evidence that exists |
| Neutral 50 | anything still unobservable scores mid-universe | "we don't know" should score average, not "whatever the price says" |
| March-to-March | growth from full fiscal years, never a rolling TTM window | see below |
| Caps | final scores clamped to 5-95 | a 0 or a 100 claims a certainty no model of this kind has |

**Every one of those rules was chosen by backtest**, not argument. On 515 stocks whose true score is
known, deleting the pillars thin names really lack:

| approach | error (MAE) | rank correlation |
|---|---|---|
| the engine's skip-and-reweight (the bug) | 10.08 | 0.601 |
| redistributing weight to value/growth/quality | **11.83** | **0.445** |
| neutral-fill at 50 | 6.95 | 0.601 |
| **1-year sibling** | **2.72** | **0.932** |
| **return since listing** | 6.17 | **0.701** (from just 3 months of history) |

Note the second row: an intuitive-sounding fix scored **worse than the bug**. Concentrating freed weight
on value amplifies value's own noise, and value tells you nothing about the pillars that went missing.
Under uncertainty, shrinking toward the middle beats betting on one surviving pillar.

**Why March-to-March matters.** The engine took growth from a rolling twelve-month window. 666 stocks
landed on a March-2026 window but **76 landed on June-2026**. Because the Growth pillar is a
**cross-sectional percentile**, those 76 were being ranked against everyone else **over a different
period** — not a staleness trade-off, an invalid comparison. One company read −13% on the engine's
window and **+89%** on clean fiscal years.

---

## 9. Earnings quality — reading profit growth properly

A separate check asks whether reported profit growth is **operating** or **accounting**. It decomposes
the year-on-year change in pre-tax profit:

```
volume effect  = (Sales₁ − Sales₀) × old margin      revenue genuinely grew
margin effect  =  Sales₁ × (margin₁ − margin₀)       operating leverage — LEGITIMATE
other income   =  other income₁ − other income₀      NON-OPERATING — the one to watch
finance/dep    = −(change in interest) − (change in depreciation)
```

The four parts sum to the total change, and across 662 stocks the residual is **0.6%** — proof the
decomposition is complete rather than approximate.

**What this replaced, and why it was wrong.** The old rule flagged "profit up more than 50% while sales
up less than 10%". That is the ordinary signature of **operating leverage** — lift margin from 12% to 15%
on flat revenue and profit grows 25% with nothing untoward happening. Of the 29 companies it flagged,
**17 (59%) were simply margin stories**. It was flagging good businesses.

Three narrow flags now: more than half the profit increase came from other income · other income above
25% of pre-tax profit · other income more than double its own 3-year median. Financials exempt —
treasury income *is* their operating business.

A note on limits: the bridge computed **₹1,196cr** of other income for Bajaj Auto; the analyst,
independently, wrote **₹1,195cr**. Same number, two methods. It did **not** raise a flag, because 19.1%
of pre-tax profit sits under the 25% threshold. That is threshold behaviour working as designed, and it
is exactly why the analyst layer exists on top.

---

## 10. Does it work? The honest answer

Point-in-time decile test, 2016-2025, no lookahead. At a **one-year** horizon the model's top decile
beat its bottom decile by **+5.5%**, with a 59% hit rate and a rank information coefficient of +0.026.

That is **weak but real**, and three caveats belong with it:

1. **It is not monotone in a single quarter (0 of 32).** It separates the extremes; it does not order
   the middle. Treat decile 4 and decile 6 as indistinguishable.
2. **The forward adjustment has never been validated and probably hurts ranking.** With the growth leg
   on, the 1-year decile spread collapsed from +5.5% to **+0.13%**. It is kept because it is what the
   frozen client model has always done and removing it would make new scores incomparable with every
   deck already delivered — but the evidence against it stands and is logged.
3. **Two parts cannot be tested at all.** The analyst's conviction leg has no point-in-time history
   (using today's opinion at a past date is lookahead; proxying it with the score is circular), and the
   listing-price rule cannot enter the backtest because the harness requires 260 days of price history —
   the very thing those names lack.

Anyone who tells you this model is strong has not read the numbers. It is a **disciplined shortlisting
tool** with a modest edge at the tails, wrapped in gates that stop it being stupid, with a human on top.
That is the honest description, and it is the one to give a client.

---

## 11. Running it

```bash
cd Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750
%PYTHON% earnings_quality_decomp.py     # → results/EARNINGS_QUALITY.csv
%PYTHON% fix_thin_coverage_v3.py        # → results/full750_scored_v3.csv
%PYTHON% audit_v3_freeze.py             # 21 invariants — must be 21 of 21
```

`fix_thin_coverage_v3.py` **aborts** if it cannot reproduce the engine's own composites exactly. That
assertion is the guard against the correction layer drifting from the engine it corrects. If it fires,
stop and find out why — do not edit the assertion.

**You will not be able to re-run this from a fresh clone.** The finished scores are in the repo; the
working data behind them (screener financial parquets, price panels) is not. That is deliberate — you
should be *consuming* these scores, not regenerating them. Ask the Principal if you genuinely need to.

**Refresh cadence:** April and October, clubbed with the MF frameworks.

---

## 12. The five things most worth remembering

1. **A pillar score is a rank, not a grade.** 80 means "better than 80% of the universe", never "good".
   In an expensive market the cheapest-looking stock is still expensive.
2. **The 40 bar is absolute.** Nothing above 40 is a Sell, whoever says otherwise.
3. **Use `full750_scored_v3.csv`, not the v1 file.** The raw engine over-scores thin-history names.
4. **Growth pillar = trailing revenue. Forward adjustment = expected EPS.** Different measures, used in
   different places, and they disagree for a quarter of the universe.
5. **The score shortlists; a person decides** — and that person may only soften an action, never invent
   one.
