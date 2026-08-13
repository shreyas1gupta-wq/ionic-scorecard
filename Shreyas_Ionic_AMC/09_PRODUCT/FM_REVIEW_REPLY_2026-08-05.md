# NDPMS review deck — reply to the Fund Manager's 25 comments
**Date:** 2026-08-05 · **Re:** FM feedback on the NDPMS portfolio-review deck (pr_template engine)
**Status:** REPLY DRAFT for the Principal to send. Nothing has been changed in the deck yet.

All 25 comments are accepted in principle. Below: what we can answer now, what only you can decide,
what data we need, and what we will build without waiting. Comment numbers are yours throughout.

---

## A. Three of your points are questions. Answers now, with the honest gap in each.

**#2 — "I hope the equity being read is on a look-through basis."**
**Partly, and not where it matters most.** Today `ips_summary` computes a look-through mix, but it
classifies funds by CATEGORY, not by their actual holdings: an equity-category fund counts as 100%
equity and a **hybrid-category fund counts as 0% equity**, lumped into a hybrid-and-debt bucket. So a
balanced-advantage fund holding 65% equity contributes nothing to the equity number. You are right,
and it is worse than a rounding issue.
Also, look-through is applied **only** on the IPS page. Concentration and sector are direct-equity
only, which is why your #9 and #10 are real gaps rather than presentation preferences.
We have the machinery to fix this (`mf-lookthrough`, which computes true exposure from monthly fund
portfolios). **What it needs is a monthly fund-holdings feed — see #3 and item C1.**

**#3 — "What is the data source for MF data? Advisory has a defined source from ACE MF."**
Today, three sources, none of them ACE MF:
| Use | Source | Weakness |
|---|---|---|
| Short-term capture screen | `MF Dashboard.xlsx` (your workbook) | benchmark sheet is **PRI, not TRI** (fix already queued); data cut 2025-01-31 |
| Long-term fund ranking | Direct-Growth NAV files in the QFRA-2 repo | 99 funds only; equity categories only |
| NAV refresh | AMFI NAVAll, monthly on the 1st | NAVs only — no holdings, no YTM, no AUM |
**ACE MF would be a straight upgrade** and would unblock #2, #9, #10, #16 and #22 at once, because it
carries fund holdings, ratios and debt YTM that we currently do not have at all. **See C1 for exactly
what we need to use it.**

**#20 — "How is Hybrid getting ranked or scored?"**
**It is not.** Both frameworks cover equity categories only — six in the short-term screen, eight in
the long-term engine. Neither has a hybrid sheet. `funds_hybrid.py` renders a verdict but it does not
compute one: for hybrids the verdict is **set by hand in the client data file**. That is a genuine
methodology hole, not a display issue, and it is the single biggest gap your comments surface. **We
need your method — see B6.**

---

## B. Decisions only you can make. These block the build.

| # | Your comment | What we need from you |
|---|---|---|
| B1 | #1 core / satellite at portfolio level | Your definition is clear in spirit (core = stable, long-horizon, low-churn, strategic; satellite = experimental, high-churn, high risk and return). We need it **operational**: which categories or funds map to each, the **target core/satellite split**, and whether that split is house-wide or per-client IPS. |
| B2 | #17 scoring for sell decisions | You list five inputs: performance, risk-adjusted returns, IPS gaps, LTCG preference, concentration. We need the **weights** and the **cut-offs** (what score sells, what trims). Also: does this scoring **replace** the two existing fund frameworks for client work, or sit **on top** of them? That changes the build materially. |
| B3 | #16 tail analysis | Which measure? Options we can compute from NAV history: worst rolling 1M/3M, max drawdown and time to recover, VaR/CVaR at 95 or 99, or downside deviation. Naming one keeps this from becoming four charts. |
| B4 | #13-15 RAR ratios | Sortino, IR and Sharpe all need a **risk-free rate convention** (which series, what tenor) and a **common window**. Our house standard elsewhere is a common 3-year window; confirm or override. |
| B5 | #22 debt sells | Need the **house view on duration and credit** to measure "deviation vs house view" against, plus the YTM and expense-ratio **thresholds** per debt category. |
| B6 | #20 hybrid scoring | The method itself. Equity-sleeve look-through plus debt YTM? Or treat each hybrid category against its own benchmark? Until you set this, hybrids stay hand-set and we will label them as such on the page. |
| B7 | #25 churn cap | Confirm our reading: **20% is a prioritisation trigger, not a hard cap** — above 20% we still surface every sell but split it into high and low priority. Also: 20% of **portfolio value**, or of **number of holdings**? |
| B8 | #7 skip allocation vs house view | Confirm **delete**, not just hide. It is a shared module, so removing it affects every client deck built from this engine. |
| B9 | #24 correlation instead of overlap | We already have a correlation annexure (top 15 holdings). Do you want correlation to **replace** the scheme-overlap page, or both? And at which level: **scheme NAV correlation**, or **holdings-level overlap** (needs the ACE MF feed)? |
| B10 | #8 calculation base | Confirm the default: every percentage shows **as % of total portfolio**, with the sleeve percentage added in brackets where a reader would otherwise misread it. That is one convention applied everywhere rather than per-page judgment. |

**One clarification we would push back for, #21.** "Debt funds bought before 1 April 2023 should not be
sold" is right on tax — those units keep the pre-Finance-Act-2023 treatment and selling forfeits it. But
as an absolute rule it also blocks an exit on a credit event or mandate drift. Suggest: **no sell for
optimisation or rebalancing reasons, but a credit or governance event still overrides.** Confirm.

---

## C. Data and files we need.

| # | Need | For | Why it blocks |
|---|---|---|---|
| C1 | **ACE MF access** — licence or export, the fields available (holdings, YTM, expense ratio, AUM, ratios), the format, who owns the login, and the refresh cadence | #2, #9, #10, #16, #22, #24 | We cannot look through a hybrid, compute fund-level sector or concentration, or read debt YTM from anything we hold today |
| C2 | **Purchase dates and cost per lot** for every MF holding | #19, #21, #22 | STCG-versus-LTCG classification and the 1-April-2023 debt cut-off are both date-driven. Without dates we cannot mark low-priority sells at all |
| C3 | **The manual override list** (#18) and the **standing avoid-list** (#23, e.g. quant and Motilal on capital-gains grounds) | #18, #23 | Needs to be a file we read, not a conversation, so it survives into the next client's deck |
| C4 | **The client's seven IPS aspects** (#5): return, risk, liability, liquidity, timelines, tax, unique circumstances | #5 | We currently hold only allocation bands and caps. The other five aspects are not anywhere in our data. Is there an IPS document or questionnaire per client we can read? |
| C5 | **Staleness thresholds** (#4): how old is too old, per source | #4 | We will build the flag; you set the limits |

---

## D. What we will build without waiting for you.

These need no input and are already understood:
- **#11** three-part structure: portfolio statistics, then MF, then direct equity.
- **#6** asset allocation on the portfolio snapshot.
- **#8** calculation base printed on every figure, once B10 confirms the convention.
- **#12** an MF methodology page.
- **#13-15** the two-part MF analysis: returns versus benchmark with up and down capture, then the
  risk-adjusted ratios, once B4 fixes the risk-free convention.
- **#19** STCG holdings marked **low-priority sells**, once C2 arrives.
- **#4** a staleness flag in the QA gates, covering the monthly asset file and the MF data cut, once
  C5 sets the limits. **We would add one you did not ask for:** the same check on the fund NAV cut and
  the short-term screen's anchor date, because both have silently gone stale on us before.

## E. One thing you should know that is not in your list.

The deck's short-term fund screen currently reads a **price-return** benchmark sheet where it should
read **total-return**. That understates the benchmark by roughly 1.2 to 1.5 percentage points a year
and therefore **suppresses sell signals** — every fund looks better than it is. A fix is already
queued. It matters for your #14, because "returns vs benchmark" on the current sheet is measured
against the wrong benchmark.

---

## Sequencing we propose
1. You send C1 to C5 and decide B1, B2, B7, B8, B10 — that unblocks roughly 15 of the 25.
2. We build section D plus the three-part restructure and the calculation-base convention.
3. B3 to B6 (tail measure, RAR convention, debt thresholds, hybrid method) come second, since each is
   a method decision that should be written down before it is coded.
4. The look-through work (#2, #9, #10, #24) is last and largest, because it all depends on C1.
