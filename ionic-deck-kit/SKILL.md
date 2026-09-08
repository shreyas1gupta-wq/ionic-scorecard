---
name: ionic-portfolio-review
description: Build an Ionic Wealth portfolio-review deck from a client's holding statement. Use whenever an advisor supplies a CAS, CAMS, Kfintech or platform holdings export and wants the standard review deck and holdings workbook. The recommendations come from a centrally published score file and are never derived, inferred or overridden here.
---

> **SUPERSEDED by `Shreyas_Review_Skill` (v1.0, 2026-09-08).**
>
> That skill is the single operating manual for producing a review deck end to end: the deck kit,
> the two score files and their order of precedence, client-directive overlays, the lot-aware tax
> engine, risk and liquidity mapping, the grafted firm pages and the QA gates. Start there.
>
> This file is kept because it is still referenced and because parts of it are not repeated
> elsewhere. **Where the two disagree, `Shreyas_Review_Skill` is right** - it was written after the
> defect sweep of 2026-09-08 and this one was not.


# Building a portfolio review

## The one rule

**You do not decide the calls.** Sell, Trim, Hold and No View come from files published centrally
and keyed on ISIN. Read them and render them.

There are two, because a share and a scheme are scored by different desks:

| what | file | keyed on |
|---|---|---|
| mutual-fund schemes | `scores/ionic_scores_*.csv` | ISIN (an `INF` prefix) |
| direct equity | `scores/ionic_stock_scores_*.csv` | ISIN (an `INE` prefix) |

The ISIN prefix is what tells a share from a scheme, exactly and with no lookup: India issues fund
units under INF and company securities under INE.

**The stock file has its own order of precedence, and the HOUSE VIEW is the top of it.** Wherever
`STOCK REVIEW FINAL.xlsx` carries a name, that call is the client-facing call, including where it
says No View. Only where it is silent does the analyst's own recommendation stand, and only where
that is silent too does the quant call. It matters: on the current pair of files the house view
disagrees with the scorecard on **97 of 384 names**, and in both directions. Shipping the
scorecard's answer put a Sell on Hindustan Aeronautics, Reliance, Bharat Dynamics, Thermax, Bajaj
Auto and Vedanta in a client deck while the house view held every one of them.

And where the house view overrides the analyst, **drop the analyst's rationale**. It was written to
argue the other case, so printing it under a house-view call contradicts the call it sits beneath.
`export_stock_score_file.py` already does this; do not undo it.

**A discretionary mandate is Hold, not No View.** A PMS or an AIF has a manager the client has
already appointed and a book the desk has not been given. That is a reason to withhold a SCORE, not
a position: "No View" against a rupee-crore mandate reads as *we have nothing to say about the
largest line in your portfolio*. It is Hold, the rationale says why, and it counts as EQUITY in
every band and every concentration test.

Never infer a call from returns you can see. Never fill a gap with judgement. Never override a call
because it looks wrong for a client. A scheme missing from the score file is **No View**, and that is
the correct answer rather than a problem to solve.

If the advisor asks why a fund is a Sell, the rationale column is the answer. If they want more than
that, it is a conversation with the desk.

The vocabulary is Sell, Trim, Hold (watch), Hold, No View. **Hold (watch)** is a held position the
desk has flagged, not a clean hold, and it is not an invitation for you to soften or harden it.

**Trim never comes from the score file.** It is derived from the single-scheme cap the desk publishes
in `VERSION.json`: a held scheme above the cap becomes a Trim sized to bring it back to the cap. A
Sell is a judgement on a fund, the same in every portfolio; a Trim is a judgement on a weight, and
the same fund is a trim in a concentrated book and nothing in a diversified one. Do not hand-set a
trim, and do not adjust the cap for a client.

## Steps

1. Read the statement with `parse/read_statement.py`. It finds the header row by VOCABULARY rather
   than by position, so the table can start anywhere on the sheet and the columns can be in any
   order. A sheet with no ISIN column at all is still read in full: the holdings are real whether or
   not the statement identifies them.
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

**Rows without an ISIN are still the client's money.** They are listed in the exceptions file because
the desk cannot put a CALL on them, and that is the only thing the exceptions file means. They stay
IN the portfolio: in the total, in every weight, in the concentration tests, on the risk-and-liquidity
grid and in the holdings annexure, carrying No View. On a real book this is not a rounding detail —
on the reference book it is 41 of 75 holdings and 39% of the money, REITs and AIFs and direct bonds
among them. A review that quietly reported the other 61% would be wrong on every page.
Never drop one, and never guess which scheme it was.

**Two caps, and they are not the same cap.** `single_scheme_cap_pct` in `VERSION.json` is the desk's
concentration cap: it applies to ANY holding as a share of the WHOLE book, and it is what fires a
Trim. The Investment Policy Statement separately carries a row called "A single listed security",
which is a limit on directly-held shares measured against the EQUITY SLEEVE. Two different
populations on two different denominators. Reading either as the other is the single most expensive
mistake available in this kit: it once reported a holding as comfortably inside a 15% cap while the
trim engine was already cutting it back to 10%.

**The demo score file is a trap.** It is dated later than the production file on purpose so nobody
mistakes it for real, and the kit prefers a production file whenever one is present. If the run
prints the invented-data warning, the deck is not sendable at any price. Say so and stop.

**Debt, arbitrage, gold and insurance-linked plans.** These are not taxed at equity-fund rates and
several carry no view at all. If the score file says No View, leave it at No View.

## What to say and what not to

State the call and the rationale line as published. Do not add a forecast, do not annualise anything,
and do not describe the score as a prediction. It describes a record.

House style: no long dashes, no filler adjectives, no three-item lists. Numbers in rupees with a
thousands separator. The `qa/` tell-scanner will flag most lapses.

## What is published centrally, and never written in a module

Five files in `scores/`, all refreshed on the desk's own cadence and none of them an advisor's to
edit for a meeting:

| file | what it fixes |
|---|---|
| `ionic_scores_*.csv` | the fund calls, scores and rationales |
| `ionic_stock_scores_*.csv` | the direct-equity calls, built by `export_stock_score_file.py` |
| `house_view.json` | the desk's stance, targets and what Ionic does for a client |
| `firm_profile.json` | the firm's own AUM, co-founders, edge and asset-class view |
| `VERSION.json` | the as-of date and `single_scheme_cap_pct`, the concentration cap |

`firm_profile.json` is what the introduction pages read. Without it those pages render **nothing**
rather than inventing a credential, and that is the correct behaviour: an AUM figure or a
co-founder's record is not something a deck should guess at.

## Two caps, and they are not the same cap

`single_scheme_cap_pct` in `VERSION.json` applies to ANY holding as a share of the WHOLE book and is
what fires a Trim. The IPS row "A single listed security" is a different limit: directly-held shares
only, measured against the EQUITY SLEEVE. Two populations, two denominators. Reading either as the
other once reported a holding as comfortably inside a 15% cap while the trim engine was cutting it
back to 10%.

## Tax

The tax page is computed from the exits the review actually recommends, and only where an invested
figure is on file. The rate that decides a debt bill is **when the units were bought**: anything
acquired on or after 1 April 2023 lost capital-gains treatment and is taxed at the holder's slab
whatever the holding period. A platform workbook usually carries that split already, under a column
named for "other income" units. Each family member's slab differs, so *whose* units are sold is as
much a lever as which. Nothing the kit prints is a tax opinion and the page says so.

## What this kit does not contain

No NAV history, no peer construction, no percentile maths, no backtest, no scoring engine. If a task
seems to need any of those, it is not a task for this kit.
