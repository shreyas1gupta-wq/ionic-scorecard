# Turnover / ADV-Capacity / Realistic-Fill Audit — Momentum Rescues
**Tara Singh (E-015, Execution & TCA) · 2026-07-17 · answers COMPLETENESS_CRITIC.md #4**
Targets: `H002_slope200_1M`, `H004_mom_sharpe12m_1M`, `H043_beta_adj_mom` (the Tier-A momentum/trend
rescues flagged as "the most likely place a rescue evaporates live").
Tags: **[DATA]** on-disk fact/computed by the scripts below · **[INFERENCE]** my construction/judgment ·
**[OPINION]** my call.
Scripts: `rnd/wave4/turnover_fill_audit.py`, `rnd/wave4/turnover_fullhistory_check.py` (both re-runnable).
Raw output: `rnd/wave4/_turnover_fill_audit_raw.json`, `rnd/wave4/cards_exec/W4TF_exec_*.json`,
`rnd/wave4/_turnover_fullhistory_check.log`.

---

## 0. DATA-INTEGRITY FINDING BEFORE ANYTHING ELSE [DATA]

`builders_ma.py` / `builders_mom.py` (the code that produced the H002/H004/H043 cards) load
`rnd/panel/cube_close.parquet` — which is **only 2021-07-16 → 2026-07-16** (751 symbols), NOT the
full-history `cube_close_long.parquet` (2005-04 → 2025-12, 976 symbols) that `panel_long.parquet`'s own
labels/beta/vol columns are built from. Confirmed: all three cards' `n_dates` (48 / 47 / 36) and this
audit's own decile-set count (43 / 42 / 42) fall entirely inside 2021-07→2025-12 — **~42-48 monthly
observations, not the ~237-239 the full 21-year panel would give.** This is the exact same root-cause
class already caught and killed for `H046_ey_only_1Y` (RECONCILED_RETURNS.md, PBO=1.000, "least
statistically supported of the four original numbers") and `H009` (SURVIVORS.md, "bull-only 2021-26
artifact"). **It had not previously been flagged for H002/H004/H043 specifically.**

Consequence for THIS audit: the volume data (`cube_volume.parquet`, 2021-07-16 start) happens to cover
the **entire** window these three cards were actually scored on — so the capacity/fill numbers below are
NOT a "recent-regime-only, can't say about the rest" caveat; they cover the full tested sample. But it
also means the IC/DSR/PBO "edge" being cost-tested here was itself only ever observed in one ~4-year,
largely post-COVID small/midcap-bull-tilted window — a finding for Quant Head / Overfit Analyst, not
something a costs memo can offset. **I ran a full-21yr cross-check of turnover only** (the one thing in my
lane that's directly comparable): turnover is **stable** between the narrow and full windows for these
three specific parameter choices (23-26% one-way/month both ways) — reassuring on churn, silent on
whether the IC itself would survive the other 17 years.

| Factor | Narrow-window turnover (book, one-way/mo) | Full-21yr turnover (book, one-way/mo) |
|---|---:|---:|
| H002_slope200_1M | 24.9% | 23.9% |
| H004_mom_sharpe12m_1M | 27.1% | 26.2% |
| H043_beta_adj_mom | 26.2% | 25.2% |

(For context: my own earlier `RECONCILED_RETURNS.md` found the H002-**family's** MA65-slope member at
**45.2%/month** — much higher. That's not a contradiction: MA65 is a faster, twitchier lookback than
MA200/252-day; turnover is parameter-sensitive within a sweep family, and the specific member ranked
CANDIDATE here (`slope200`, n=200) happens to be one of the slower-turning ones.)

---

## 1. TURNOVER

One-way monthly turnover, harness convention (`new_names_entering_decile / decile_size`, averaged over
consecutive monthly rebalances — same definition already in the cards, independently re-derived here):

| Factor | Long-leg turnover | Short-leg turnover | Book (avg) turnover | Implied avg holding (long / short) |
|---|---:|---:|---:|---|
| H002_slope200_1M | 23.9% | 25.9% | **24.9%** | 4.2 mo / 3.9 mo |
| H004_mom_sharpe12m_1M | 26.9% | 27.2% | **27.1%** | 3.7 mo / 3.7 mo |
| H043_beta_adj_mom | 24.8% | 27.5% | **26.2%** | 4.0 mo / 3.6 mo |

**Verdict on turnover itself:** moderate, not extreme — average holding ~4 months per name. This is
churn-y for a monthly-rebalanced equity long-short (roughly 3x a buy-and-hold quarterly strategy) but is
NOT the 45%/month "highest turnover in the book" profile the critic worried about in the abstract; that
description fits faster MA-lookback members of the H002 sweep (e.g. MA65-slope, 45.2%/month per prior
reconciliation), not the specific `slope200` member ranked CANDIDATE in `scoreboard_v2.csv`. Cost drag
scales with this number directly — see §3/§4.

---

## 2. ADV PARTICIPATION / CAPACITY (recent-regime, 2021-07→2025-12 — the only window `cube_volume.parquet`
covers, which per §0 is also the entire tested window)

Equal-weight-within-decile, dollar-neutral assumption: position per name = AUM / (names in that leg's
decile that month); decile size averages ~55-63 names/leg across the three factors. Participation% =
position ÷ (20-day median volume × price that day).

| Factor | Leg | Median % ADV @₹10cr | P90 % ADV @₹10cr | Max % ADV @₹10cr | Median % ADV @₹100cr | P90 % ADV @₹100cr | % of leg-days >10% ADV @₹100cr | % of MICRO-tier leg-days >5% ADV @₹10cr |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| H002_slope200_1M | long | 0.29% | 1.51% | 136% | 2.95% | 15.1% | 17.4% | 2.8% |
| H002_slope200_1M | short | 0.66% | 3.39% | 23% | 6.59% | 33.9% | 38.5% | 10.5% |
| H004_mom_sharpe12m_1M | long | 0.29% | 1.49% | 350% | 2.86% | 14.9% | 17.7% | 3.7% |
| H004_mom_sharpe12m_1M | short | 0.79% | 4.02% | 26% | 7.87% | 40.2% | 43.4% | 13.9% |
| H043_beta_adj_mom | long | 0.38% | 1.80% | 256% | 3.76% | 18.0% | 22.4% | 5.1% |
| H043_beta_adj_mom | short | 0.66% | 3.69% | 26% | 6.59% | 36.9% | 39.2% | 12.5% |

**Reading it:** at ₹10cr AUM the *typical* position is trivially small (median <1% ADV) — capacity is not
a binding constraint for a "normal" name in either leg. But:
- The **short leg is systematically less liquid than the long leg** in every one of the three factors
  (P90 ADV% 2.2-2.7x the long leg's) — consistent with the well-worn "momentum shorts beaten-down,
  neglected names" pattern, and consistent with my Lessons Learned re: mid/small-cap tails.
- The **tail is fat**: max participation at ₹10cr already hits triple digits (136-350%) for a handful of
  micro-cap names each month — these are exactly the COST_STANDARDS "≤5% micro" breaches the liquidity
  policy exists to catch, and they are ALREADY present at the smallest AUM tested, not just at scale.
- **Capacity ceiling (P90 basis, 10% ADV cap):** solving for the AUM where the 90th-percentile position
  first breaches 10% ADV: **long leg ≈ ₹56-67cr; short leg ≈ ₹25-30cr** across all three factors. Since a
  long-short book must size both legs together, **the short leg is the binding constraint: book-level
  capacity ≈ ₹25-30cr** before a materially-sized minority of monthly short positions need to be skipped
  or shrunk under the firm's own ≤10% ADV rule (tighter still under the ≤5% micro rule, which already
  bites 2.8-13.9% of micro-tier leg-days even at ₹10cr).
- At ₹100cr, 17-22% of ALL long-leg leg-days and 38-43% of ALL short-leg leg-days would breach the 10% ADV
  cap outright — i.e., at that scale you are not "trading around the edges of illiquidity," you are
  skipping/resizing more than a third of the short book every month, which mechanically changes what the
  decile-spread actually captures (survivorship of the tradeable subset, not the full decile IC).

**Caveat, stated per the brief:** this whole section uses `cube_volume.parquet` (2021-07 start only). As
established in §0, that happens to be the entire window these three cards were tested on, so there is no
"can't measure it" gap here — but it IS a single recent regime; ADV levels, and hence capacity, in a
different liquidity regime (e.g. a 2018-2019-style smallcap liquidity crunch) are not represented.

---

## 3. REALISTIC FILL (circuit/thin-volume no-fill + volume-conditional slippage, COST_STANDARDS "Dynamic
slippage & circuit rule", `Shreyas_Ionic_AMC/04_RND_LAB/lib/execution_realism.py`)

Applied to every ACTUAL entering name on its ACTUAL rebalance date (not a synthetic sample):

| Factor | Entry events tested | No-fill rate | Slippage-mult. distribution (1x/2x/3x) | Avg effective 1-way slip (bps) | Realistic RT bps | Flat-model RT bps (same tier mix) |
|---|---:|---:|---|---:|---:|---:|
| H002_slope200_1M | 1,322 | 0.08% | 89.4% / 10.1% / 0.5% | 28.7 | 80.4 | 74.5 |
| H004_mom_sharpe12m_1M | 1,223 | 0.0% | 94.9% / 4.9% / 0.2% | 27.1 | 77.3 | 74.5 |
| H043_beta_adj_mom | 1,185 | 0.0% | 93.8% / 5.9% / 0.3% | 29.3 | 81.7 | 78.0 |

**Reading it:** the vast majority (89-95%) of entries land on normal-volume days (1x floor applies); only
5-10% hit the "thin day" 2x multiplier and under 0.5% hit the "abrupt collapse" 3x. Realistic
volume-conditional round-trip cost is only **~3-6bps/roundtrip worse** than the flat COST_STANDARDS
estimate already baked into the cards — a small, not a devastating, gap for THIS specific slice.

**Important limitation, stated plainly:** `execution_realism.circuit_locked()` needs OHLC, and this panel
only carries adjusted CLOSE (no open/high/low). I could only apply the **zero/absent-volume** half of the
no-fill test, not the **circuit-lock** half. Given the firm's own documented lesson ("momentum entries
correlate with UPPER circuits — buying strength"), the near-zero no-fill rate above almost certainly
**understates** true no-fill risk on the exact days these signals want to enter. I do not have the
OHLC data in this panel to close that gap honestly; flagging it rather than guessing a number.

---

## 4. SHORT-LEG SHORTABILITY — the finding that matters most here [DATA/OPINION]

Cross-referenced every long/short decile name-month against the firm's own verified 210-name F&O-eligible
universe (`Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_CATALOG.md`, single-stock options universe; folder list
captured to `rnd/wave4/_fno_universe_list.txt`, 210 names):

| Factor | Long leg % F&O-eligible | Short leg % F&O-eligible |
|---|---:|---:|
| H002_slope200_1M | 33.1% | 22.4% |
| H004_mom_sharpe12m_1M | 42.1% | 24.1% |
| H043_beta_adj_mom | 32.4% | 22.9% |

**This is a structural, not a cost, problem.** Only ~22-24% of each factor's SHORT-decile names are even
F&O-eligible (i.e., could be shorted via single-stock futures). The remaining ~76-78% are cash-market-only
names — and continuous, monthly-rotating equity short positions in the Indian cash market require SLB
(Securities Lending & Borrowing), which:
1. Is **not priced anywhere in COST_STANDARDS.md** — there is no borrow-cost line item. **[DATA GAP]**:
   I cannot quote a borrow cost because the firm has never approved one; I am not fabricating one here.
2. Is, as a market-structure fact, illiquid-to-absent for the majority of non-F&O small/midcaps — many
   months, a chunk of the "short" decile is simply **unshortable at any price**, not merely expensive.

**Consequence:** the long-short construction graded in the cards is not the strategy that could actually
be run. A realistic implementation is closer to "short only the F&O-eligible ~quarter of the bottom
decile, cash-neutral against a smaller long book" — a materially different, thinner short leg than the
one the IC/turnover/decile-spread statistics above were computed on. This dominates the ADV-participation
finding in §2: it's not that the short leg is expensive to trade at scale, it's that ~3/4 of it likely
can't be traded as a continuous short at any scale, in any Indian retail/AMC-without-a-custodian-SLB-desk
setup. I flag this as the single highest-priority open question for Structurer Aakash Jain / CIO before
any of these three go anywhere near a forward clock: either (a) price and source real SLB access for the
non-F&O names, or (b) redesign the short leg around the F&O-eligible subset only and re-score the
resulting (probably much weaker) long-short spread.

---

## 5. NET-OF-COST vs GROSS, and VERDICT

Recomputed honestly with `harness.annualize_ls_return()` (horizon-aware — the 1Y-horizon H043 card's own
raw `ann_return_LS` field is the documented ×12-bug-inflated one; this uses the corrected figure) on the
**full tested sample** (2021-07→2025-12, per §0):

| Factor | Gross ann. (horizon-aware) | Net @1x (flat COST_STANDARDS) | Net @1x (realistic vol-cond. fill) | Net @2x (realistic, promotion-rule stress) | Verdict @2x |
|---|---:|---:|---:|---:|---|
| H002_slope200_1M | 17.4% | 15.2% | 15.0% | **12.6%** | **SURVIVES** |
| H004_mom_sharpe12m_1M | 15.7% | 13.3% | 13.2% | **10.7%** | **SURVIVES** |
| H043_beta_adj_mom | 28.6% | 26.2% | 26.1% | **23.5%** | **SURVIVES** |

(Note: H043's card literally reports `net_of_cost_ann_return: 2.54` (254%/yr) — that is the harness's
documented ×12-over-annualization bug for 1Y-horizon cards, not a real number; DECISION_PACKAGE.md's
already-corrected "19.0%/yr" is closer to my 26.1% but not identical, likely a different intermediate
correction method. Treat my 26-29% range, reusing harness's own `annualize_ls_return()`, as the more
directly reconciled figure for this specific card's raw series.)

**All three SURVIVE the 2x-cost promotion-rule stress on realistic (not flat-assumed) execution costs,**
on the sample they were actually tested on. Turnover-driven cost drag (~2.4-2.6%/yr at 1x, ~4.9-5.1%/yr at
2x) is real but modest relative to the gross edge — nothing like the near-annihilation my earlier
`RECONCILED_RETURNS.md` found for the faster-turning MA65-slope member of H002 (5.2%→1.4% at 2x). **For
these three specific parameterizations, turnover/ADV/fill realism is NOT where the edge dies** — subject
to two hard caveats that ARE where it plausibly dies, both flagged above and neither in a cost memo's
power to fix:
1. **§0**: the entire tested sample is one ~4-year post-2021 regime, not the 21-year history the panel
   nominally offers — same failure class that killed H046 and H009. Nobody has re-run these three against
   the full 21-year panel yet (Quant Head / Overfit Analyst's lane).
2. **§4**: ~76-78% of the short leg is not F&O-eligible and has no priced, and likely no practically
   available, borrow — the tested long-short spread is not the strategy that could actually be deployed.

**Bottom line for a forward clock:** turnover/capacity/fill-realism, narrowly, is a PASS for all three —
do not park these on execution grounds alone. But do not read that as "clear to forward-test" either:
resolve #1 (full-history re-score) and #2 (real short-leg design) first, or forward-test a LONG-ONLY
version of each (which sidesteps #2 entirely and halves the turnover-relevant capital, materially
improving the capacity picture in §2 as well, since only the more-liquid long leg would need sizing).

---

## Files
- Scripts: `rnd/wave4/turnover_fill_audit.py`, `rnd/wave4/turnover_fullhistory_check.py`
- Cards: `rnd/wave4/cards_exec/W4TF_exec_H002_slope200_1M.json`, `..._H004_mom_sharpe12m_1M.json`,
  `..._H043_beta_adj_mom.json`
- Raw: `rnd/wave4/_turnover_fill_audit_raw.json`, `rnd/wave4/_turnover_fullhistory_check.log`
- F&O universe list (210 names, from `Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_CATALOG.md`'s single-stock
  options coverage): `rnd/wave4/_fno_universe_list.txt`
- Inputs read: `rnd/panel/panel_long.parquet`, `rnd/panel/cube_close.parquet` (short, 2021-2026 — what the
  cards actually used), `rnd/panel/cube_close_long.parquet` + `cube_bench_long.parquet` (full 21yr,
  cross-check only), `rnd/panel/cube_volume.parquet`, `rnd/lib/harness.py`, `rnd/lib/builders_ma.py`,
  `rnd/lib/builders_mom.py`, `Shreyas_Ionic_AMC/04_RND_LAB/lib/execution_realism.py`,
  `Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md` (APPROVED, D-021).
