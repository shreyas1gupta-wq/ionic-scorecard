# SCORECARD FINAL SUMMARY — two-scorecard reset (RELATIVE + ABSOLUTE), v1 frozen

**Owner:** Arjun Rao (Head of Quant, E-004). **Date:** 2026-07-18. **Step:** S7 final assembly.
**Status:** frozen `_v1` candidates, NOT certified books. Assembled mechanically per `SCORECARD_BLUEPRINT.md §4`
from S1–S4 builder outputs + S5 consolidation. No new research, no refit, no weight search. Verdicts below are
carried VERBATIM from the builder reports — this assembly does not upgrade, launder, or paper over any of them.

**Frozen artifacts (single source of every number that governs scoring):**
- `weights_v1.json` — merged from the four `weights_*_fragment.json`; determinism: bytes-identical on rebuild.
- `RELATIVE_SCORECARD_v1.parquet` — 123,889 rows; `date, symbol, rel_score_1M/1Y/5Y, verdict_1M/1Y/5Y`.
- `ABSOLUTE_SCORECARD_v1.parquet` — 298,245 rows (99,415 × 3 horizons long); adds `verdict` + `verdict_note` per horizon.

**Determinism gate (blueprint §4, HARD TESTABLE) — PASS.** Each parquet built twice from source in one foreground
run: `.equals()=True` AND SHA-256 match on both; on-disk reload re-hashes identical; `weights_v1.json` bytes-identical.
- RELATIVE sha256 `7b692bf4…4c65dd` · ABSOLUTE sha256 `b1d24e97…97b809` · weights `a085fdb6…90faf6`.

---

## Per-horizon table — BOTH scorecards

### RELATIVE scorecard (cross-sectional ranker; lens = LS Sharpe / monotonicity / rank-IC)

| Horizon | Verdict | Headline metric | Beat hard gates (lag/placebo)? | Beat placebo? | Weakest assumption |
|---|---|---|---|---|---|
| **1M** | **REAL** | Rank-IC 0.072, IC_IR 0.42, decile LS Sharpe 0.95, mono 0.88; net-2x 20.9%/yr | **YES** (lag 0.199, placebo −0.002) | n/a (LS design) | `earn_1M` contributes ~zero incremental IC despite 40% weight (fires ~5.9% of rows); edge is almost all skip-15 momentum. Secondary: IC decaying (2021–24 = 0.048, 2024 = −0.014). |
| **1Y** | **FRAGILE** | Rank-IC 0.084, IC_IR 0.63, mono 0.988, decile LS Sharpe 0.137/yr net | **YES** (lag 0.116, placebo −0.0014) | n/a (LS design) | DSR≈0 / PBO 0.926 at thin effective-n: `quality_cfo_pat` coverage cliff pre-2017 → this is a **post-2017-only model** (~7–8 independent annual windows); never tested through 2008/2011. |
| **5Y** | **FRAGILE** | Rank-IC 0.079 (blend), IC_IR 1.59, +12.6%/yr net; mono 0.71 blend | **YES** (lag 0.042, placebo +0.0014) | n/a (LS design) | Only ~1.5 independent non-overlapping 5Y windows. Growth-longevity leg **reduces** IC on drop-one despite the blueprint mandating its overweight — unresolved, escalated. |

### ABSOLUTE scorecard (standalone long-only E[return]; lens = CAGR + Calmar vs TWO placebos)

| Horizon | Verdict | Headline metric | Beat hard gates (lag/placebo)? | Beat BOTH placebos (CAGR & Calmar)? | Weakest assumption |
|---|---|---|---|---|---|
| **1M** | **FAKE / DO-NOT-USE** | CAGR 27.96%, Calmar 0.517 — but magnitude structurally broken | **NO** — hard-gate KILL (lag 1.05 g / 0.51 rerating vs 0.25 bar) | NO (loses random on Calmar) | **Structural math defect:** rerating term not horizon-scaled → annualized intensity median −50%/yr, tail +4675%/yr. Both signal and magnitude unusable at 1M. |
| **1Y** | **FRAGILE** | CAGR 27.82%, Calmar 0.482 | YES (lag 0.11–0.15, placebo ~0) | **NO** — loses Calmar to random (0.483) AND cap-wt (0.495) | CAGR premium over random is a **drawdown premium, not skill**. Growth half of g×rerating carries ~zero IC; valuation-reversion carries all of it. |
| **5Y** | **FRAGILE (least-bad)** | CAGR 23.42%, Calmar 0.395 | YES (lag 0.03–0.04, cleanest drivers) | **NO** — beats cap-wt but loses Calmar BADLY to random (0.395 vs **0.635**) | Loses to a coin-flip on risk-adjusted return; worse max-DD than random at every horizon (−59% vs −35%). Only ~2 independent 5Y windows post the 2013 coverage ramp. |

---

## What IS and ISN'T usable right now (plain language)

**Usable now (as disclosed forward-test candidates — NOT certified, NOT sized by anyone but the Principal):**
- **1M RELATIVE — usable.** The only REAL verdict in the set. Both hard gates clean, sane Sharpe (0.95, not a
  fabrication-band number), survives 2× cost. Ship it LOW-CONVICTION (no 21-yr intra-month confirmation) and know
  three things: the earnings leg is inert filler at its 40% weight, the edge is essentially skip-15 momentum, and
  IC is decaying in the last two eras. A PM treats it as a tilt/timing nudge, not a standalone thesis.
- **1Y and 5Y RELATIVE — usable with disclosed caveats.** Hard gates clean, economic logic sound, no leg redundant
  on drop-one (except the 5Y growth-longevity tension). FRAGILE strictly because the *independent* sample is thin
  (1Y effectively post-2017; 5Y ~1.5 windows) — that is a power problem, not evidence of no effect, so per the
  firm's low-t re-screen rule they are forward-test candidates, not rejects. Do not claim 2008/2011-bear behavior.

**Explicitly NOT usable:**
- **1M ABSOLUTE — DO NOT USE. Structurally broken.** Hard-gate KILL, and the intensity number is mathematically
  degenerate (rerating not horizon-scaled). The magnitude must never be displayed or sized. This needs a formula
  fix (a blueprint revision), not an assembly patch — left for the Principal/CIO.
- **1Y and 5Y ABSOLUTE — NOT YET a demonstrated edge.** Not fake, but they do not clear the blueprint's own
  mandatory bar: they lose to a naive placebo on the metric a long-only PM should trust most (Calmar). As of today
  there is no evidence these beat a coin-flip on a risk-adjusted basis. They need rework before any real use.

---

## Consolidated escalations (carried forward, NOT resolved here)

1. **[Data Officer — Kavya Reddy] S2 pre-2017 `quality_cfo_pat` coverage cliff.** Verified source-coverage fact
   (`quality_cfo_pat` covers 187/249 dates, median 1–4 names/date 2010–16 → 226+ from 2017-06-30), not a join bug.
   Confirm whether a wider pre-2017 CFO/PAT panel exists that fell out of `capstone_legs.parquet`'s cache, or the
   source itself starts there. Until answered, 1Y relative is honestly a **post-2017 model**.
2. **[Principal / CIO] S3 growth-longevity drop-one anomaly.** Blueprint §2.3 mandates a 2.0× overweight on
   growth-longevity at 5Y; as built, dropping the leg *increases* IC in both limbs (sr_5Y 0.083→0.120; abs_merit
   0.052→0.084). Two live hypotheses (noisy proxy vs earns-keep-on-tail-risk-not-avg-IC). Builder correctly did
   NOT unilaterally remove a blueprint-locked leg. Needs a ruling: keep, re-spec via cheap-test, or drop.
3. **[Quant desk] `earnings_confirm_v2` naming correction (2026-07-18, techno-funda research).** Documented in
   `SCORECARD_BLUEPRINT.md` header — it's a multi-year fundamental confirmation flag, not a single-quarter
   earnings-surprise/price-reaction signal. Doesn't change any construction, but likely explains why `earn_1M`
   contributed ~zero incremental IC in S1 despite 40% weight (a slow fundamental filter on a fast-horizon leg).
   Candidate fix: pair with a genuine price-reaction confirmation, or re-weight down at 1M.
3. **[Principal / CIO — SERIOUS, flag prominently] S4 absolute model loses to a random placebo on drawdown.** At
   **every** horizon the real long-only portfolio's max-drawdown is materially worse than a same-sized random draw
   from the identical universe (−54% to −59% vs −35% to −46%), and Calmar favors the random placebo everywhere
   except 5Y-vs-cap-weighted. The CAGR "wins" are compensation for extra risk, not risk-adjusted skill — the exact
   small/mid-cap-tilt-riding-a-bull-market confound the blueprint named as `ABSOLUTE_MODEL_V2`'s failure mode. A PM
   must know: **the current absolute model loses to a coin-flip on risk-adjusted return.** Rework-or-shelve decision
   belongs to the Principal/CIO.
4. **[Principal / CIO] S4 1M horizon-scaling math defect** (rerating not H-scaled → nonsense annualized intensity).
   Real formula bug, out of scope for an implementation/assembly pass. Blueprint revision + version bump required
   before 1M absolute intensity is ever quotable.

---

## Closing brief to the CIO (FM lens — blunt, Principal's 2026-07-18 instruction)

Rajan — here is what I would actually let a PM touch today and what I would take off the table.

**Let a PM use, sized small and clearly flagged: the 1M RELATIVE ranker,** as a momentum/quality tilt on names
they already have a thesis on — not as a standalone signal, and knowing its edge is really skip-15 momentum with a
decaying recent IC and an earnings leg that does nothing. **Let a PM use, forward-test only, the 1Y and 5Y RELATIVE
rankers** — the logic is PM-sane and the leakage gates are clean; the only knock is thin independent sample, which
is a "we can't prove it yet through a bear market," not a "it's fake." I'd put all three relative horizons on a
forward clock and adjudicate on live behavior.

**What I would explicitly tell a PM NOT to touch: the entire ABSOLUTE scorecard.** The 1M horizon is structurally
broken — its expected-return magnitude is mathematically nonsense and it fails the leakage gate outright; it must
not appear on any screen. The 1Y and 5Y absolute horizons are the more dangerous ones, because they *look*
respectable (23–28% CAGR) and a PM could be tempted — but they lose to a random draw from the same universe on
risk-adjusted return. The extra return is just extra drawdown; a coin-flip beats it on Calmar. That is not a
stock-picking model yet, it is a volatility tilt wearing a fundamental costume. I would shelve the absolute book
until the horizon-scaling bug is fixed and it can demonstrably beat both placebos — anything less and we'd be
selling a bull-market beta tilt as alpha, which is exactly the fabrication this reset existed to prevent.

Net: **one usable ranker (1M relative), two watchlist rankers (1Y/5Y relative), and an absolute model that is not
ready for capital in any form.** No false comfort in the packaging — the honest verdicts are stamped into the
parquet outputs themselves so no downstream consumer can miss them.
