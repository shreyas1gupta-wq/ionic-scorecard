# Gold as a Static Diversifier vs the Firm's Actual Short-Vol Book P&L

**Author:** Kabir Anand, Head of Hedging & Tail Risk (E-028)
**Date:** 2026-07-18
**Trigger:** Cyrus Daruwalla's `CROSS_ASSET_MACRO_ASSESSMENT.md` (2026-07-18) found gold near-zero-to-
slightly-negative correlated to Nifty on down days, index-level, using `goldbees_daily_ext.parquet`
(2013–2026). That memo's own §7 flagged the one untested gap: does this hold at the level of the
firm's **actual short-vol book P&L**, not just the Nifty index. This memo runs that test.

**Scope decision [OPINION]:** Of the candidate P&L series on disk, the two that are (a) genuine
portfolio-level daily/weekly series (not per-symbol trade lists needing aggregation) and (b) already
Red-Team/audited are used as primary evidence:
- `intraday_options_strategy/results/v2_portfolio_daily.csv` — 0DTE/DTE1 NIFTY delta-hedged short
  straddle, **daily**, 2015-01-09 → 2026-05-14, n=2,794 days (audited: `intraday_options_strategy/results/AUDIT.md`).
- `intraday_options_strategy/results/realfill_deltahedged_nifty.csv` — same family, **per-expiry
  (weekly)**, 2021-05-27 → 2026-05-19, n=259 expiries, includes the `hedgpnl_lot` leg explicitly.

S-01..S-04 (STRATEGY_REGISTER) trade-level CSVs (`strangle_trades.csv`, `ivrv_trades.csv`) are
per-symbol entry/exit rows, not a clean daily book P&L, and would need an aggregation step outside
this cheap test's scope. `portfolio_monthly_returns.csv`'s combined sleeves are **excluded on
purpose** — several of its columns (`ivrv_short`, `earnings_shortvol`) are the same series the firm
already identified as **denominator-artifact-inflated** (S-01/S-02 register rows; e.g. July-2021
`ivrv_short` = +75.7%/month is not a real return). Using it here would launder a known-bad number
into a new memo.

Gold: `datasets/etf_gold_silver/goldbees_daily_ext.parquet` (GOLDBEES daily OHLCV, 2013-01-01 →
2026-07-03, n=3,341 — same file Cyrus used, extended past the original 2021+ sleeve memo's window).

Method is diagnostic (realized daily/weekly P&L vs realized gold return, same class as `/stress-replay`)
— not a PIT trading signal, no lookahead concern. Script: `04_RND_LAB/results/GOLD_SHORTVOL_DIVERSIFIER_20260718/gold_shortvol_test.py` (daily) and `gold_shortvol_weekly_crosscheck.py` (weekly), outputs saved alongside.

---

## 1. Headline honesty check before anything else: this book never actually had a crisis

Full-sample max drawdown on the 11-year daily book is **−1.06%**. On the 5-year weekly delta-hedged
book it is **−18.75%**, but that is an accumulation of small losing weeks (worst single week −4.2%),
not a crash spike. **[DATA] Neither series contains a genuine large-loss "short-vol blowup" event** —
which is the exact scenario a crisis-hedge diversifier is supposed to offset. This matters more than
any correlation number below: it means the two real crisis windows in the sample period (COVID,
2022 H1) did **not** actually hurt this specific book, so I cannot show you "gold saved the book from
a big loss" — because there was no big loss to save it from, in this book's own recorded history.
This is the honest sample-size flag the task asked for, stated plainly, not softened.

Why this book stayed tame through COVID/2022 while short-vol intuition says it should have bled:
0DTE/DTE1 tenor (minimal gap exposure vs. holding a strangle to expiry) + intraday delta-hedging
(per AUDIT.md, the hedge leg is real and drift-independent, MIRROR-PATH-stress-tested). This is a
genuinely different risk profile from the classic "sold a monthly strangle, held through the crash"
short-vol trap this firm's own charter warns about — a legitimate structural reason, not an artifact,
though the pre-2021 segment (covering COVID) runs on **extrapolated IV calibration**, an AUDIT.md
HIGH-severity flag — so that specific window's numbers are lower-confidence than 2021-05+.

## 2. (a) Correlation — conditional on the book's own bad days, not just full-sample

| Test | Daily book (2015–2026) | Weekly delta-hedged book (2021–2026) |
|---|---|---|
| Full-sample correlation | **−0.009** | **−0.071** |
| On the book's LOSS days/weeks only | **+0.25** (n=65 loss days) | n/a (see win-rate below) |
| Mean gold return on book's loss days/weeks | — | gold **+0.76%**/week vs book **−0.68%**/week (n=109 loss weeks) |
| Gold win-rate on book's loss days/weeks | 57–58% (varies by tail cut, see below) | **57.8%** |
| Worst 1% of daily book days (n=28): mean gold return | **+0.015%**/day (57.1% win-rate) | — |
| Worst 2% of daily book days (n=56): mean gold return | **+0.045%**/day (55.4% win-rate) | — |
| Worst 5% of daily book days (n=137): mean gold return | **+0.065%**/day (51.1% win-rate) | — |

**[DATA]** Full-sample correlation is near-zero-to-slightly-negative in both series — matches Cyrus's
index-level finding, now confirmed **at the book-specific level**, not just Nifty. More useful: on the
book's own bad days/weeks specifically, gold's mean return tilts positive and gold is in profit
slightly more often than not (~55-58%). This is real but modest — a coin-flip-plus-a-bit, not a
one-way crash payoff. **Worst 10 individual weeks for the delta-hedged book**: gold was positive in
7 of 10 (including +6.2% the week of the book's single worst loss, −4.2%), but negative in the other
3 (once falling −4.8% and −1.8% *simultaneously* with a book loss) — full table in
`weekly_worst10_deltahedged.csv`. **Gold is not a guaranteed offset on every bad day** — it is a
directionally favorable tilt, consistent with a genuine but partial hedge property, not an inverse.

## 3. Named crisis episodes — book P&L vs gold, SAME dates

| Episode | Short-vol book P&L | Gold P&L | Era reliability |
|---|---|---|---|
| COVID crash (2020-01-20 → 2020-03-24), daily book | **−0.24%** | **+4.12%** | pre-2021, **extrapolated-IV segment — lower confidence per AUDIT.md** |
| 2022 H1 (Jan–Jun 2022), daily book | **+0.00%** (flat) | **+5.50%** | calibrated-IV era (reliable) |
| 2022 H1 (Jan–Jun 2022), weekly delta-hedged book | **+0.64%** (positive) | **+6.16%** | calibrated-IV era (reliable) |

**[DATA] Honest reading:** in both real crisis windows available, the short-vol book itself was
flat-to-slightly-positive, not in drawdown, while gold gained 4–6%. This is the direct evidence for
§1's point — the "hedge" was never actually called upon in this book's own history. Gold's gain in
these windows is real and would have added standalone return to a blended book, but it is not
evidence of gold *offsetting a loss*, because there was no loss on these dates for this book. Cyrus's
index-level COVID/2022-H1 numbers (Nifty −35.2% and −10.9% respectively) are a much harder test than
this specific delta-hedged book ever faced.

## 4. (b) Blended-book simulation — daily-rebalanced weights, full sample

**Daily book (2015–2026, all of it):**

| Book | CAGR | AnnVol | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|
| Short-vol book alone | −0.06% | 0.27% | −0.20 | −1.06% | −0.05 |
| + 5% gold | +0.72% | 0.80% | 0.90 | −1.22% | 0.59 |
| + 10% gold | +1.50% | 1.54% | 0.97 | −2.43% | 0.62 |
| + 15% gold | +2.28% | 2.30% | 0.99 | −3.63% | 0.63 |

**Daily book, calibrated-IV era only (2021-05+, AUDIT.md's reliable segment):**

| Book | CAGR | AnnVol | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|
| Short-vol book alone | −0.07% | 0.39% | −0.18 | −0.96% | −0.07 |
| + 5% gold | +1.16% | 0.95% | 1.21 | −1.02% | 1.14 |
| + 10% gold | +2.39% | 1.79% | 1.33 | −2.32% | 1.03 |
| + 15% gold | +3.64% | 2.65% | 1.36 | −3.62% | 1.00 |

**Weekly delta-hedged book (2021–2026):**

| Book | CAGR | AnnVol | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|
| Book alone | +0.92% | 5.84% | 0.19 | −18.75% | 0.05 |
| + 5% gold | +2.10% | 5.55% | 0.40 | −15.72% | 0.13 |
| + 10% gold | +3.28% | 5.38% | 0.63 | −13.18% | 0.25 |
| + 15% gold | +4.47% | 5.34% | 0.85 | −11.67% | 0.38 |

**[DATA] Sharpe, Calmar improve and MaxDD falls at every tested weight (5/10/15%), in every book
variant.** This is a genuine improvement, not purely cosmetic — MaxDD (a crash-shaped statistic) falls
too, on the weekly book from −18.75% to −11.67% at 15% gold. **But flag plainly: a large share of this
lift is gold's own strong absolute return over the sample window (2013–2026 was a strong secular gold
bull run, e.g. +66.8% cumulative in the 2024-04→2025-11 stretch alone)** — not proof that gold
specifically fires when the book specifically loses. §1–3 already showed this book rarely loses hard
enough to test that mechanism directly. The Sharpe/Calmar improvement is better read as "a modest,
near-zero-correlated, positive-expected-return asset improves a risk-adjusted blend" — a standard and
real portfolio-construction benefit — rather than as "gold rescued the book from a crash," which the
book's own history does not contain an instance of.

**Denominator caveat on the daily-book magnitude [flagged per firm discipline]:** the daily book's own
computed Sharpe here (−0.18 to −0.20) is far below the AUDIT.md-quoted headline (delta-hedged 0DTE
~2.6, combined ~3.6). Correlation and the *direction* of the blend improvement are scale-invariant to
a constant capital denominator and therefore unaffected — but the absolute CAGR/Sharpe/Calmar levels
in the daily-book table above should be read as **this book's return on a stated ₹1cr AUM basis**,
not as a restatement of AUDIT.md's separately-computed (and higher) headline metric. The weekly
delta-hedged book, computed directly on `cap`/`lots`/`net_lot` from source, does not have this
ambiguity and is the more trustworthy magnitude of the two.

## 5. Verdict — is the sample sufficient?

**[OPINION, per firm's own low-t rule — do not kill for thin n, but say so plainly]:** No. This is
thinner evidence than even Cyrus's index-level test, which already had only 2 real crisis episodes.
Here, neither of those 2 episodes actually stressed the specific book being tested — so the number of
genuine "does gold cover an actual short-vol loss" observations in this dataset is effectively **zero
large-loss events**, not two. What IS supported, with reasonable (not high) confidence:
1. Gold's correlation to this book is consistently near-zero-to-negative, full sample and conditional
   on the book's bad days/weeks (both series agree, independently constructed).
2. On the book's own (mostly small) bad days, gold tilts positive ~55-58% of the time — a real,
   modest, non-perfect diversification property, not an artifact of one lucky window (it holds across
   1%/2%/5% tail cuts on the daily book AND independently on the weekly book's loss-week conditional).
3. A static 5-15% gold sleeve improves Sharpe/Calmar and lowers MaxDD in every variant tested — driven
   substantially by gold's own return premium in this sample, which will not repeat indefinitely and
   should not be extrapolated as "gold pays for itself every period."
4. What is NOT supported by this specific test: any claim that gold would have offset a genuine
   short-vol blowup, because this book's own history contains no such event to check against. That
   claim still rests only on Cyrus's index-level analysis (Nifty −35.2%/gold +4.1% COVID,
   Nifty −10.9%/gold +5.6% 2022H1) — a real but separate, index-level result, not yet confirmed at
   the book level because the book itself hasn't had a comparable drawdown in its recorded history.

## 6. Recommendation to CIO/FM

- Do not size a gold allocation on the strength of "it will save the short-vol book in a crash" — that
  specific claim is untested at the book level (§5.4) and the book's audited magnitude discrepancy
  (§4 denominator caveat) means precise Sharpe/Calmar uplift numbers here should be treated as
  directionally indicative, not final sizing inputs.
- Do treat the *correlation* finding (near-zero-to-negative, tilting favorable on bad days, consistent
  across two independently-built book series) as a genuine, modest diversification property worth
  carrying into portfolio construction discussions — consistent with, and reinforcing, Cyrus's
  index-level result.
- A static long gold sleeve is inherently net-hedge-positive by construction (long-only, no short
  leg) — it trivially satisfies this desk's non-negotiable discipline; the open question is sizing and
  whether the return premium embedded in the 2013-2026 sample should be assumed forward, not whether
  the structure itself is sound.
- Next cheap step, if this is pursued further: re-run this exact test once the book has lived through
  one more genuine equity drawdown in real (not backtested) time — that is the only way to actually
  observe whether gold offsets THIS book's losses, since none of the backtested history did.

---
**Files:** `04_RND_LAB/results/GOLD_SHORTVOL_DIVERSIFIER_20260718/gold_shortvol_test.py`,
`gold_shortvol_weekly_crosscheck.py`, `merged_daily_series.csv`, `shortvol_drawdown_episodes.csv`,
`blended_book_comparison.csv`, `blended_book_comparison_calibrated_era.csv`,
`weekly_worst10_deltahedged.csv`, `weekly_blended_comparison.csv` (all in that results folder).
Source books: `intraday_options_strategy/results/v2_portfolio_daily.csv`,
`intraday_options_strategy/results/realfill_deltahedged_nifty.csv`,
`intraday_options_strategy/results/AUDIT.md`. Gold: `datasets/etf_gold_silver/goldbees_daily_ext.parquet`.
Cross-reference: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/CROSS_ASSET_MACRO_ASSESSMENT.md` §4.
