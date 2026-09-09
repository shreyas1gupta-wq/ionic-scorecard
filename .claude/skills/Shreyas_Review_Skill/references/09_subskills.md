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

## 1. A fund Sell needs BOTH frameworks to agree

**The desk's rule (Principal, wording corrected 2026-07-26):** a fund Sell or Exit goes to the
client **only when both frameworks are independently at Sell.** A Buy or a high score on *either*
side **vetoes** the Sell.

- one says Sell, the other Hold → **Hold**
- both Hold → Hold
- structural actions (Redeem-to-Direct, a mandate switch) are **exempt** — they are plan and
  category facts, not performance calls

The older wording, "both non-Hold", is wrong and must not be used: it is satisfied by one side Buy
and the other Sell, which is exactly the silent contradiction the rule exists to prevent.

**Coverage gap, verified:** the long-term framework covers focused and value/contra categories that
the short-term dashboard has no sheet for. In those two categories a Sell is *necessarily*
single-framework, needs explicit FM sign-off, and must be labelled as such.

> **A live discrepancy, flagged rather than fixed.** `export_score_file.py` issues a Sell on the
> percentile rule — bottom third of the scheme's own category on **both horizons** of one method.
> That is two horizons of one framework, not two frameworks. Whether a published Sell therefore
> satisfies the dual-framework rule is a **method question for the desk**, and calls are fixed
> centrally, so this manual does not resolve it. If you are about to send a fund Sell, check it
> against both frameworks or get FM sign-off. Do not quietly reinterpret either rule.

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
