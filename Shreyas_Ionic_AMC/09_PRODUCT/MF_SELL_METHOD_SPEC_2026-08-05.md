# MF sell method — spec v1 (non-linear, gated, escalating)
**Principal rulings 2026-08-05.** Written before coding, so the method is agreed rather than
discovered in a diff. Covers FM comments #3, #6, #7, #9, #17, #19, #21, #25.

Design rulings taken:
- **Non-linear**, not a linear weighted sum (#6). Rules flexible, with AI-analyst and FM discretion,
  escalating to a human analyst when it cannot resolve.
- **Discretion is one-directional** — it may veto or soften an action, never manufacture one. Same
  asymmetry as QFRA-2's Stage-2 gate, and the reason judgment does not become invention.
- **Equity counted gross**, footnote not flag (#1).
- **Risk-free 6.5%** unless supplied per run (#8).

---

## Why not a linear weighted sum

A weighted average lets a good score on one axis pay for a disqualifying score on another. A fund
with a broken risk profile but a large unrealised gain averages out to "hold", which is the wrong
answer arrived at arithmetically. Both QFRA-1 and QFRA-2 already avoid this — each uses **gates plus
ranks**, not a single linear blend — and this method follows the same shape.

## Layer 1 — HARD GATES. Binary, no compensation, checked first.

| Gate | Action | Source |
|---|---|---|
| Debt bought before 1-Apr-2023 | **Never sell for optimisation or rebalancing.** A credit or governance event still overrides | FM #21 + Finance Act 2023 grandfathering |
| Track record under 7 months | **No View.** No score is emitted at all | existing firm floor |
| Block as-of staler than threshold for a material holding | **No View + escalate.** Do not print a number we cannot date | `check_freshness.py`; 40.5% of ACE rows are behind the file's own month-end |
| Manual override / avoid-list hit | Forced action, override reason recorded | FM #18, #23 |

Gates run before scoring. A gated holding never receives a score, because a score would imply an
assessment we did not make.

## Layer 2 — CONTINUOUS SCORE with saturating, non-linear responses

Five inputs (FM #17), each mapped through a response curve chosen for how the quantity actually
behaves, not through a flat weight:

| Input | Curve | Why that shape |
|---|---|---|
| **Performance** vs its own blended benchmark | Sigmoid | Small under- or out-performance should not move a decision; large gaps should saturate. A fund 20% behind is not "twice as sell-worthy" as one 10% behind — both are already decisive |
| **Risk-adjusted return** (Sortino / IR / Sharpe, rf 6.5%) | Sigmoid **with a floor that becomes a gate** | Below a hard bar this stops being a score and becomes a disqualification |
| **IPS gap** | Piecewise: flat inside the band, steeply rising outside | Genuinely non-linear. Inside the band there is no problem at all; 1pp outside is minor; 10pp outside is a breach. A linear term would penalise a compliant fund |
| **Tax position** | **Asymmetric**, not symmetric | LTCG mildly reduces sell urgency. **STCG reduces it strongly — an STCG holding is a low-priority sell, never suppressed entirely** (FM #19) |
| **Concentration** | Convex, rising faster than linearly | Matches the house guidance already in the stock scorecard: 5-10% acceptable, above 10% a concern, above 20% extreme |

**Underperformance is scored explicitly**, not just as the negative tail of performance (FM #9):
persistent shortfall against a fund's *own* blended benchmark across consecutive windows is its own
term, because a fund that is reliably 2% behind is a different problem from one that is violently
behind once.

## Layer 3 — DISCRETION BAND

Scores in the middle band do **not** auto-decide. They route to the AI analyst for a reasoned call,
which the FM may override. One-directional: this layer can veto or soften a sell, never create one.
Every discretionary call records its reason, so the next review can see why.

## Layer 4 — ESCALATION (the standing rule)

Where discretion cannot resolve it, escalate to the human analyst **at the end**, once everything
resolvable is resolved, in this shape: the situation and how much of the book it affects; our view
with its evidence; the counter-view argued honestly; and the specific datum or ruling that would
settle it. Recorded in `.claude/skills/ionic-wealth-complete/SKILL.md` as a firm-wide standing rule.

---

## Churn rule (FM #3, #25) — Principal: implement

- Compute total churn as **% of portfolio value** recommended for sale.
- **Churn ≤ 20%** → present every sell as a single list, unsegmented.
- **Churn > 20%** → segregate into **high priority** and **low priority**, without degrading the
  existing slide format. Implementation: the priority split becomes a **grouping within the existing
  sell table** (a subhead row and a priority column), not a new page and not a different layout — the
  deck's row-pagination and column widths are unchanged.
- Priority is assigned from the Layer-2 score, with two overrides: **STCG holdings are always low
  priority** (FM #19), and any gate-forced action is always high priority.
- The 20% figure is the FM's own (comment 25) and is recorded as his, not derived.

## Tail measure (FM #7, approved with latitude to improve)

1. **Common 3-year window** for every fund, so comparison is valid by construction rather than by
   coincidence of launch dates.
2. **Expected shortfall at 90%** — mean of the worst decile of rolling 1-month returns. This is the
   Principal's "extreme 10th percentile", averaged over roughly 70 observations rather than resting
   on a single worst-drawdown reading, which is one noisy point.
3. **Regime-coverage test.** Does the fund's history actually span a stress episode — Mar-2020,
   Jan-2018 small-cap, Sep-2018 IL&FS, Oct-2021 to Jun-2022? If not, the estimate is extrapolation
   and is labelled as such. This is the Principal's pre-COVID versus post-COVID point made explicit
   instead of buried in a number.
4. **Safety factor.** The Principal proposed ~2.5x. **To be validated, not assumed:** compute ES90
   over a calm 3-year window for the benchmark and compare with the realised COVID drawdown to see
   what multiple the ratio actually is. If it lands near 2.5 the factor is evidence-backed. Until
   that check runs, no 2.5x number is quoted as validated.
5. **Category-relative**, so a small-cap fund is not penalised for being a small-cap fund.

## Hybrid scoring (FM #9, #20) — flexible benchmark

The reason hybrids cannot be scored against one category benchmark: Balanced Advantage funds range
from **52.8% to 90.4% equity**, so a single benchmark punishes whichever manager was correctly
defensive.

- Build **each fund its own blended benchmark** from its **trailing 3-year average disclosed mix**:
  (avg equity% x equity TRI) + (avg debt% x debt index) + (avg others% x proxy).
- **Degradation path, stated honestly.** ACE supplies a month-end snapshot, so a 3-year average needs
  36 monthly extracts. Until they accumulate, the benchmark is built from the **latest snapshot** and
  labelled "current-mix" rather than "3-year-average mix". The method gets more accurate every month
  instead of pretending to be right on the first file.
- Judge on: outperformance versus that blended benchmark; **down-capture** against it (from QFRA-2);
  **6-month total capture** (from QFRA-1); persistent underperformance; and **suitability** — does the
  fund's actual disclosed mix fit this client's IPS bands?
- Then the same five inputs and the same four layers as above.

---

## Open, and deliberately not invented
- **Layer-2 curve parameters and the discretion band's edges.** Shapes are set above; the numbers need
  either the FM's thresholds or a backtest. Nothing ships with invented cut-offs.
- **Whether this scoring replaces the fund frameworks for client work or sits on top of them.** My
  recommendation remains **on top**: the originating leg keeps its 906-formation evidence and this
  score decides priority among sells rather than manufacturing them.
- **House view on duration and credit** (FM #10) and the **client's seven IPS aspects** (FM #12) —
  both awaiting documents.
