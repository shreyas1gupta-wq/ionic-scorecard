---
name: ionic-portfolio-review
description: Build an Ionic Wealth portfolio-review deck from a client's holding statement. Use whenever an advisor supplies a CAS, CAMS, Kfintech or platform holdings export and wants the standard review deck and holdings workbook. The recommendations come from a centrally published score file and are never derived, inferred or overridden here.
---

# Building a portfolio review

## The one rule

**You do not decide the calls.** Sell, Trim, Hold and No View come from `scores/ionic_scores_*.csv`,
published centrally and keyed on ISIN. Read them and render them.

Never infer a call from returns you can see. Never fill a gap with judgement. Never override a call
because it looks wrong for a client. A scheme missing from the score file is **No View**, and that is
the correct answer rather than a problem to solve.

If the advisor asks why a fund is a Sell, the rationale column is the answer. If they want more than
that, it is a conversation with the desk.

## Steps

1. Read the statement with `parse/read_statement.py`. It finds holdings by ISIN rather than by column
   position, so it survives unfamiliar layouts.
2. **Check the reconciliation.** It compares the parsed total against the total the statement prints
   for itself. If it says MISMATCH, stop and tell the advisor. A deck built on a partial read carries
   wrong numbers on every page.
3. Join to the score file on ISIN. Report how many holdings matched and name any that did not.
4. Build with `build/build_review.py`.
5. Run the QA gates in `qa/`. Geometry findings mean content is off the page or overlapping.
6. Hand over the deck, the workbook, and the exceptions file if one was written.

## Things that will bite you

**Two plans, one scheme.** Direct and Regular are share classes of the same portfolio. They carry the
same score and the same call, always. If they ever differ, something is wrong upstream.

**Renames and acquisitions.** A scheme's name changes; its ISIN does not. HSBC Value Fund is the old
L&T India Value Fund. Today's Kotak Midcap Fund is the old Kotak Emerging Equity, while the *old*
Kotak Midcap became Kotak Small Cap in 2018. This is exactly why the join is on ISIN and never on
name. Do not match schemes by string similarity under any circumstances.

**Rows without an ISIN.** They go to the exceptions file. Never drop one quietly, and never guess
which scheme it was.

**Debt, arbitrage, gold and insurance-linked plans.** These are not taxed at equity-fund rates and
several carry no view at all. If the score file says No View, leave it at No View.

## What to say and what not to

State the call and the rationale line as published. Do not add a forecast, do not annualise anything,
and do not describe the score as a prediction. It describes a record.

House style: no long dashes, no filler adjectives, no three-item lists. Numbers in rupees with a
thousands separator. The `qa/` tell-scanner will flag most lapses.

## What this kit does not contain

No NAV history, no peer construction, no percentile maths, no backtest, no scoring engine. If a task
seems to need any of those, it is not a task for this kit.
