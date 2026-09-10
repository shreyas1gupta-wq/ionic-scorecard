# The subskills, folded in

Six other skills touch this product. What each one carries that the rest of this manual does not is
below, so a recipient of `Shreyas_Review_Skill` alone is not missing a rule. Where a skill is the
runnable path to something (a NAV refresh, a framework rerun), it stays as its own skill and is
named here rather than duplicated.

| skill | what it is | fold in or point at |
|---|---|---|
| `qfra1-rerun` | the SHORT-TERM fund method (capture-ratio overlay) | rules folded in; the run stays there |
| `qfra2-rerun` | the LONG-TERM SIP fund method | the Sell rule folded in; the run stays there |
| `mf-nav-refresh` | pulls AMFI NAVs, feeds both frameworks | pointed at; nothing to fold |
| `mf-lookthrough` | true exposure through fund portfolios | flags and the tax-inertia rule folded in |
| `transfer-in-review` | the transfer-in acceptance checklist | the gate folded in; it is self-contained and stays |
| `agentic-fund-manager` | the mechanical client-portfolio layer | every ruling folded in below |

---

## 1. How a fund Sell originates: ORIGINATE-AND-VETO

**This section previously said "a fund Sell goes to the client only when both frameworks are
independently at Sell". That rule cannot fire.** The long-term framework has **no Sell verdict at
all** — its verdicts are Active / Index-core and it can only ever veto — so a test requiring both
to be at Sell is unsatisfiable, and a reader applying it loosely would fire on the wrong pair. The
rule as ruled (Principal, 2026-08-04, options A+B+C) and as implemented in `merge_calls()` is:

| framework | role |
|---|---|
| **short-term** (`qfra1-rerun`, capture-ratio) | **originates.** The only one with a Sell verdict, and the only one with a replayed backtest |
| **long-term** (`qfra2-rerun`, SIP) | **vetoes.** A CALIBRE **A or B** grade blocks the Sell → Hold, and raises a CONTRADICTION. C and D do not veto. It can never originate a Sell |
| neither has coverage | Hold, with a gap note |

**A contradiction must reach a human.** `merge_calls()` returns it as a string precisely so it is
never silently resolved. Structural actions — Redeem-to-Direct, a mandate switch — are exempt from
the whole mechanism: they are plan and category facts, not performance calls.

**Coverage gap, verified:** the long-term framework covers focused and value/contra categories the
short-term dashboard has no sheet for. There a Sell is necessarily single-framework, needs explicit
FM sign-off, and must be labelled as such.

### The honest reading of the Sell backtest

Measured 2026-08-04 over 906 formations, 2012-2024, all six category sheets. **Do not overstate
it:**

- **Buy** cohort, Apr/Oct pooled: median +2.59%, hit 66% — robust
- **Sell** cohort, Apr/Oct pooled: median −0.57%, hit **49.3%** — a coin flip

The replay is strong on the buy leg and weak on the sell leg. That is a reason to keep the veto and
the FM sign-off, and a reason never to present a fund Sell to a client as backtested.

### THE DECK KIT USES A THIRD RULE, and you should know which one you are looking at

`ionic-deck-kit` reads `ionic_scores_*.csv`, which `export_score_file.py` produces on the
**percentile rule**: Sell where the scheme sits in the bottom third of its own SEBI category on
**both** the three-year and five-year horizons, Hold otherwise, with a desk ruling in
`desk_calls.csv` overriding everything. That is neither originate-and-veto nor a two-framework
test — it is one method over two horizons.

So the firm currently has **two live fund-call paths**: the adapter path (originate-and-veto, used
by the legacy hand-written-context builds) and the exporter path (percentile, used by every deck
this kit produces). They can disagree on the same fund. Which is correct is a **method question for
the desk**, and calls are fixed centrally, so this manual does not resolve it. Before a fund Sell
goes out, know which path produced it, and get FM sign-off where the two would differ.

---

## 2. The short-term framework (qfra1-rerun), in the terms the deck needs

Ranking is on the **6-month total capture ratio** (upside capture ÷ downside capture), and the
downside-capture filter is applied **after** ranking, never before. Ranks 1-3 that survive the
filter are Buys, so a category can yield fewer than three — excluded funds "stealing" ranks is the
design, not a bug.

| ruling | what it says |
|---|---|
| six-month minimum (2026-07-26) | a fund without a full six-month NAV history is **not eligible** to be scored or ranked at all. **Not currently enforced in code**, so a fund with two of six months can still score, with an understated downside capture, and spuriously pass the filter |
| empty-set fallback (2026-08-17) | if the filter wipes all of ranks 1-3, promote the best **surviving** fund rather than returning an empty set. So a category yields one to three Buys, never zero |
| quadrant-3 asymmetry (2026-07-26) | a Sell fires on the catch-all quadrant only. Quadrant 3 (under-captures totals **and** over-captures downside) never fires a Sell, because the firm's own backtest shows those funds mean-revert with lower forward underperformance odds. **Do not "fix" this**; the asymmetry is intentional and evidence-backed |
| factor indices (2026-08-17) | scored as pseudo-funds inside their **parent-universe** category. Always publish both variants, with and without them: adding indices to the field changes every fund's rank |

**Known workbook bug, material:** each fund's capture ratio is gated on a value twelve rows earlier,
which needs NAV from about twenty-four months before evaluation. Funds aged roughly six to
twenty-four months are therefore silently forced to Hold even with a full six-month window. If a
young fund shows Hold and the arithmetic says otherwise, this is why.

---

## 3. Look-through: what the deck can say about exposure it cannot see

`mf-lookthrough` computes true exposure by looking through fund monthly portfolios. It feeds the
deck's sector scope-tags and its overlap page.

**The double-pay table** — stocks the client holds directly *and* inside a fund — is the output the
review actually needs. Without a look-through run, concentration on this deck is struck on the
holdings as listed, and the pages that do that **say so** rather than implying they looked through.

**Debt-risk flags** (flags only, not a fixed-income framework):

- any single debt **issuer above 10%** of the book on look-through
- the **debt sleeve above 10%** of the book **and** it contains below-AA paper (rating matched
  word-bounded, so AA+ and AAA never false-positive)
- an issuer that trips the scored universe's leverage or coverage gate (D/E above 2.5, or interest
  cover under 2, non-financials) with more than 3% look-through weight

**Tax inertia** applies wherever a fund switch is recommended: units held over five years, more so
over ten, carry embedded long-term gains large enough to offset switching alpha, so the bar rises to
**structural only** — plan cost, mandate rigidity, closet-indexing — never a performance gap.
**Shares are exempt.** Single-name risk dominates the tax cost, so equity Sell guidance is unchanged:
the tax is shown, the threshold is not raised.

---

## 4. The mechanical client-portfolio layer (agentic-fund-manager)

Every ruling here governs numbers this product prints.

**Asymmetric override bars (Principal, final 2026-07-26).** A Sell on a name scoring above 40 needs
a 90% exceptional case; an analyst Hold on a name scoring below 40 on either horizon needs a 60%
documented case — a hard dated catalyst, a verified one-off distorting the score, or forensic-grade
evidence the model is wrong. "Quality franchise, weak patch" clears neither. **Default below 40 is
Sell.** Sanity-check every book: the 750 universe runs about 33% quant Sells, so a client book whose
Sell share is far below that signals override leakage — re-check the sub-40 Holds.

**The balance-sheet gate is context-aware (2026-07-25).** The debt and interest-cover bar is judged
against industry norms — utilities, lenders and infrastructure run structurally levered — against
sovereign or PSU backing, and against membership of a promoter group with demonstrated capital
support. Never one fixed ratio across all names. A gate trip in a levered-by-design industry needs
the analyst to confirm it is abnormal **for that industry** before it caps the score.

**Commodity-cycle lens (2026-07-25).** Any Metals & Mining, Oil & Gas or commodity-power name gets
an explicit cycle-position read: where we are in the ten-to-fifteen-year cycle, whether the bull case
is structural demand or spot-price beta, and — for a Sell — why the call stands **despite** an
upcycle (valuation already prices it, earnings not following price, or company-specific execution).
The commodity-cycle suffix in `sell_cards` applies to sector "Metals & Mining" **only**;
conglomerates and utilities filed under Oil & Gas or Power must not get metal-price language.

**Single-group concentration (2026-07-25).** Map holdings to promoter groups — Tata, Reliance,
Adani, Bajaj, Aditya Birla, JSW, Vedanta, Mahindra, L&T and so on — and compute each group's share
of the equity sleeve on **every** run. No group above 20% → a check only, nothing in the deck. A
group above 20% → the group-concentration page renders, with the member table and a
cap-near-20% recommendation. `modules/group_concentration.py` implements this.

**Other bands the mechanical layer sets:**

| test | threshold | what it produces |
|---|---|---|
| single-name concentration | 5-10% with modest forward growth | a note |
| | above 10% | the Trim-advice zone |
| | above 20% | extreme |
| sector weight | above 20-25% of the book | check against the sector pillar and the regime call; overweight plus a weak forward view tightens the Trim band for that sector's weakest names |
| market cap | micro and small at the same weight as a large cap | judged on a lower comfort band; the book-level mix is noted |
| liquidity | a Trim that takes more than 10 trading days at ~20% ADV | **must say so on the page** |
| clutter | positions under 0.25% | a consolidation note, never a forced Sell |

**Client vocabulary (2026-07-25).** Internal codenames never reach a client artefact: no framework
codename, no engine version number, no agent name. Plain words only — "fund score /100", "grade",
"watch-outs", "the firm's fund-quality framework". `tellscan.py` enforces this on the deck and
`build/client_copy.py` on the workbook.

---

## 5. The transfer-in gate, which comes before any of this

`transfer-in-review` runs the moment a client hands over a statement ahead of a transfer-in. It is
self-contained — engine, bundled NIFTY 500 list and all — and stays its own skill. Two things from
it belong here:

**The portfolio-level gate, and it is a floor, not a guideline.** The transfer can proceed only if
**each family member's total is above ₹1 Cr AND the combined family total is above ₹2.5 Cr.** Both
are required. Below either, the answer is *cannot process*, whatever the individual holdings look
like. It needs a `family_member` column on the input; without one, the per-member half cannot be
evaluated and the verdict is UNKNOWN rather than a pass.

**The per-instrument checks**, each with its own named reviewer on failure:

| instrument | check | on failure |
|---|---|---|
| shares | in the current NIFTY 500? | to the equity reviewer |
| debt and InvIT | ISIN listed, and rating strictly better than A+ (AA- or above, or A1+)? | to the fixed-income reviewer |
| MF and SIF held in demat | on the Direct plan? | a manual confirm with the RM — no ISIN-to-plan master is bundled, so this is never an automated pass |
| shares and demat MF/SIF | has the RM confirmed purchase history? | always required, independent of the above, never automatically done |

NIFTY 500 membership changes twice a year. Check the bundled list's `as_of` and request a refresh if
it is more than about six months stale.

---

## 6. Where the fund scores come from

Neither the NAV refresh nor either framework rerun lives in this kit, and neither should. The chain:

```
mf-nav-refresh   AMFI NAVAll.txt -> datasets/mf_nav/{nav_latest,nav_monthend}.parquet
                 raw snapshots deleted after 180 days; month-end history kept forever
                 D-009 checks built in: row-count floor, NAV-range sanity, and an abort if
                 more than 2% of schemes move over 15% between refreshes
                 runs automatically on the 1st of each month
       |
       v
qfra1-rerun      the short-term capture-ratio method (§2)
qfra2-rerun      the long-term SIP method
       |
       v
export_score_file.py   -> scores/ionic_scores_*.csv   (desk-side, gitignored)
```

**This clone cannot run that chain.** `datasets/mf_nav/` is working data and is deliberately absent,
so `export_score_file.py` has nothing to read. With the score files but not the working data you can
**build decks and read scores**; you cannot re-run the scoring chain or a backtest. Ask the desk to
re-publish rather than trying to regenerate.

---

## 7. A family book is not one portfolio

`modules/family_implementation.py`, rendered from `ctx["family_book"]`, and it renders **nothing**
on a single-holder book.

Every other page in the review treats the book as one thing. That is right for allocation and wrong
for execution: an instruction to sell the fixed-income sleeve falls on whichever member holds it.
That member signs it, realises the gain on **their own return at their own slab**, and it is their
own defensive allocation that goes to zero — not the family's average. The Section 112A exemption is
per person per year, so *whose* units are sold is as much a lever as which.

On the reference book the sale fell on the member whose portfolio is 45% the size of the largest:
she held 24% of the family's money and carried 35% of the selling. No page could say so, because the
statement's holder column was thrown away at the parse.

The page reports, per holder: value, share of the family, what is moving, what share of the whole
plan that is, and **what defensive allocation is left afterwards** — where only the *defensive* money
being sold reduces it. Subtracting the whole programme, equity Sells included, showed every member
at 0.0% defensive on a book where two of them keep most of their fixed income: alarming, prominent
and wrong. A member who never held a defensive asset also reads 0.0% afterwards and is deliberately
**not** named among those the plan strips.

**A pooled holding is never allocated to a member.** Where the statement says "FAMILY" against a
deposit, the desk does not know whose it is, and guessing would credit a defensive buffer to someone
who may not own it. The pool gets its own row marked *not attributable* and its own note, because on
a book that is selling its fixed income the pool is what is left — which makes the split a
precondition for the plan rather than a housekeeping item.

---

## 8. What a stated target requires, and what this deck will not do

`modules/return_arithmetic.py`, from `ctx["return_target"]`, and it renders **nothing** without
`--target-return`. A target nobody stated is a target this desk invented, and every figure built on
it would then be presented to the client as their own number.

It runs the arithmetic the *other* way from the growth-projection page. That page asks what this book
might do, from this book's holdings. This one starts from the number the client named, sets aside the
part of the book that cannot carry the mandate — money in another member's name, plus anything the
client has been told cannot be redeemed on request — and says what the rest would have to compound
at. A constraint, not a forecast.

**It is not a Buy and names no product.** Where the required rate passes 20% it says the number is
not one this desk will present as achievable, and that the ambition is reachable on the part of the
book that can actually be invested for it. Restating a target as unreachable is the opposite of a
solicitation.

The defensive sleeve's yield is an **assumption**, passed in with `--defensive-yield` (6.5% by
default), printed on the page, and attributed to the desk rather than to any statement.

### The line this product does not cross

A **proposed model portfolio with named products** is a Buy recommendation, and two standing rules
forbid it: no client Buy is ever issued, and the `deployment` / `opportunity_set` /
`annex_mcap_migration` / `annex_liquidity_ladder` / `annex_returns_quilt` modules were cut
permanently (2026-07-28) as sell-biased or redeployment-implying. They remain in the library,
rendered nowhere.

So where an advisor's brief asks for a proposed allocation, this deck delivers the half that is not
a solicitation — the constraint arithmetic, the house-view fit, and what the plan frees — and the
proposal itself is a separate conversation with the desk. **Do not enable those modules to satisfy a
brief.** Reversing a permanent cut is the Principal's call, not a build decision.
