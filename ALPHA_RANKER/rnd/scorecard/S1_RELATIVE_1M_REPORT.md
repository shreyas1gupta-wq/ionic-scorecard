# S1 — RELATIVE 1M scorecard: quant review

**Owner:** Arjun Rao (Head of Quant, E-004). **Date:** 2026-07-18. **Task:** implementation only, per
`SCORECARD_BLUEPRINT.md` §1 (shared foundations) + §2.1 (RELATIVE 1M spec). No weight search, no new
legs, no data-source swaps performed — every number below is either read off disk or a frozen prior
already specified in the blueprint.

Tags: **[DATA]** = read from disk, verified below. **[INFERENCE]** = derived by this build.
**[MY CALL]** = a disclosed judgment call (all logged in the script's own docstring, §J1–J5).

---

## 1. Result (headline)

| Metric | Value | Gate | Outcome |
|---|---|---|---|
| Rank-IC (mean, `fwd_ret_1M_excess`) | **0.0716** | PRIMARY | solid for a 1M cross-sectional factor |
| IC_IR | **0.420** | PRIMARY | > harness default floor (0.20) |
| Decile monotonicity (Spearman) | **0.879** | PRIMARY | near-monotone |
| Decile LS Sharpe (annualized) | **0.950** | PRIMARY | sane magnitude (not the 7–10 fabrication pattern) |
| LS ann return, gross | 28.4% | context | hit-rate 68.5%, n=235 monthly periods |
| Net-of-cost, 1× (80bps RT) | 24.7% ann | deployability | survives |
| Net-of-cost, 2× stress (160bps RT) | **20.9% ann** | mandatory 2× stress | **survives comfortably** |
| Lag-test delta | **0.199** | **HARD GATE (<0.25)** | **PASS** |
| Placebo IC (5 shuffles, seed=42) | **−0.0020** | **HARD GATE (±0.02)** | **PASS** |
| DSR, honest per-family trials (n=1) | **0.997** | ADVISORY (>0.95 charter bar) | **PASS** on honest count |
| DSR, global cross-program trials (n=703) | ≈0 | ADVISORY, disclosed artifact | crushed by shared counter — not this factor's honest count |
| PBO (single-factor CSCV, 12 blocks) | **0.996** | ADVISORY (blueprint: not gating) | high — flagged, see §4 |

**Verdict: REAL**, with one disclosed fragility (§5) that should shape how a PM sizes it, not whether it ships.

---

## 2. Data lineage [DATA]

| Input | Path | Rows / grain used |
|---|---|---|
| Universe grid | `rnd/panel/panel_pit.parquet` | 99,415 rows, 249 monthly dates (2005-04-29 → 2025-12-05), survivorship-free — used per instruction, NOT `panel_long` |
| Prices (mom_1M, rev5d) | `rnd/panel/cube_close_long.parquet` | 5,131 daily rows × 976 tickers, 2005-04-01 → 2025-12-05 |
| Regime classifier (reused verbatim) | `rnd/wave4/w5_regime_momentum_horizon.py::build_regime_panel` | imports `cube_bench_long.parquet` + `market_state.parquet` internally |
| Earnings surprise | `rnd/wave4/_w6fg2_scored.parquet` | 143,907 rows, 249 dates; `earnings_confirm_v2=1` fires on 8,509/143,907 rows (~5.9%) |
| Quality legs | `rnd/panel/capstone_legs.parquet` | `quality_QMJ` 144,870 rows/249 dates; `quality_cfo_pat` 47,260 rows/**208**/249 dates (coverage gap, handled §J3) |
| No-neg-news gate | `rnd/scorecard/no_negative_news_screen.parquet` | 125,510 rows, **55 symbols only**, daily 2020-01-01→2026-03-31 |

**PIT check [DATA]:** `_w6fg2_scored.available_date <= date` holds for all 106,245 non-null rows (min gap = 0
days) — asserted in the build script; run did not raise. No lookahead in the earnings-confirm gate by
construction.

**Coverage after all gates:** 93,423 of 99,415 universe rows scored (94.0%). 5,646 rows unscored for missing
`mom_1M`/`qual_floor_1M` presence (early-history price-lookback and quality-leg gaps). 346 rows excluded by
the `no_neg_news` hard gate.

---

## 3. Guards passed?

- **PIT / available_date discipline:** PASS (asserted programmatically, §2).
- **Lag-test (HARD GATE):** PASS — delta 0.199 < 0.25.
- **Placebo (HARD GATE, 5 shuffles, seed=42):** PASS — IC −0.002, inside ±0.02 noise band.
- **Determinism contract (blueprint §4):** PASS — the build script (`S1_build_relative_1M.py`) reruns its
  entire pipeline a second time from disk inside the same foreground run and SHA-256-hashes the sorted
  output: `hash1==hash2` and `scores1.equals(scores2)` both True. Zero `.fit()` calls anywhere in the
  scoring path; the only RNG in the whole exercise is the harness's placebo shuffle (seed=42), which is
  evaluation, not scoring.
- **One bug caught and fixed during this build, logged for the record:** the first no-neg-news implementation
  produced `neg_news_flag` values of −2/−1 instead of 0/1. Root cause: `pd.concat`-ing a scalar-assigned
  bool column with a `merge_asof`'d column silently upcast the Series to `object` dtype; `~` on an `object`
  Series of Python `bool`s performs **bitwise NOT** (`~True == -2`), not logical negation. The diagnostic
  tell was `n_excluded_neg_news == 0` across 21 years, which is implausible on its face — caught before this
  went anywhere near a report. Fixed by forcing `.astype(bool)` before negating (script, `build_no_neg_news`).
  This is exactly the class of silent-corruption bug the firm's guards discipline exists to catch; there was
  no `guards.py` in this ALPHA_RANKER tree to import, so the check was manual — **flagging this as a gap**:
  ALPHA_RANKER should get its own `lib/guards.py` schema/sanity-assertion module before S2–S4 build further on
  this pattern.

---

## 4. Validation battery (full table, blueprint §2.4)

| Metric | Value | Role | Note |
|---|---|---|---|
| Rank-IC / IC_IR | 0.0716 / 0.420 | PRIMARY | via `rnd/lib/harness.py::evaluate()`, one code path |
| Decile monotonicity | 0.879 | PRIMARY | |
| Decile LS Sharpe (ann.) | 0.950 | PRIMARY | computed via harness's own `_decile_stats` internals for consistency |
| Quintile LS | not separately run | secondary | decile result already ≥30 trades/decile most months (n≈477–500 names/month ÷10) |
| Net-of-cost LS, 1×/2× | 24.7% / 20.9% ann | deployability | COST_STANDARDS APPROVED source; both positive |
| Lag-test | 0.199 | **HARD GATE** | PASS |
| Placebo | −0.002 | **HARD GATE** | PASS |
| DSR (honest per-family, n=1) | 0.997 | ADVISORY | PASS (>0.95 charter bar) |
| DSR (global counter, n=703) | ≈0 | ADVISORY, disclosed | shared cross-program counter, not this factor's own honest trial count — do not read as a kill signal |
| PBO (single-factor CSCV) | 0.996 | ADVISORY | high — see below |
| Era split | see table | robustness | **decaying** — flagged as weakest assumption |
| Drop-one-leg | see table | robustness | **earn_1M ≈ zero incremental** — flagged as weakest assumption |
| Regime breakdown (panel_pit's own bull/bear/vol tags) | see below | robustness | weaker in high-vol regime |

**Era split (Spearman IC per date, grouped):**

| Era | IC mean | n dates |
|---|---|---|
| 2005–2011 | 0.071 | 69 |
| 2012–2015 | 0.091 | 48 |
| 2015–2018 | 0.090 | 48 |
| 2018–2021 | 0.086 | 48 |
| 2021–2024 | **0.048** | 48 |
| 2024–2026 | **0.015** | 22 |

Single-year slices: 2018 = 0.136, 2020 = 0.023 (COVID momentum-crash year, consistent with known literature),
2022 = 0.054, 2024 = **−0.014** (negative). Coverage check: the 2024–2026 bucket's 22 dates run through
Nov-2025 with essentially full name coverage (477–500 names/month have valid `fwd_ret_1M_raw` through
Oct-2025; only the last 2 panel dates, Nov-28 and Dec-05 2025, correctly have zero valid forward-return
observations and are excluded — no lookahead, no artificial thinning). **The recent-era IC decay is real
data, not a small-n artifact of the tail.**

**Drop-one-leg (weights renormalized to sum 1 among the remaining two legs):**

| Variant | Kept legs | IC mean | IC_IR | LS Sharpe (ann.) |
|---|---|---|---|---|
| Full model | mom + earn + qual | 0.0716 | 0.420 | 0.950 |
| Drop mom | earn + qual | **0.035** | 0.178 | **0.260** |
| Drop earn | mom + qual | 0.073 | 0.424 | **0.994** |
| Drop qual | mom + earn | 0.065 | 0.397 | 0.902 |

Dropping momentum roughly **halves** IC and cuts LS Sharpe to a quarter of the full model — momentum is
carrying the leg. Dropping earn_1M **does not hurt** IC or Sharpe at all (both are marginally *higher*
without it). Mechanism: `earnings_confirm_v2=1` fires on only ~5.9% of rows monthly, so ~94% of names carry
earn_1M's neutral-0.5 filler value every month — the leg is mostly inert dilution, not signal, despite
carrying 40% of the composite's weight by design.

**Regime breakdown (panel_pit `regime_trend`/`regime_vol` tags):** IC fairly stable across trend states
(bear 0.080, bull 0.073, sideways 0.066) but visibly weaker in the high-vol state (0.029) vs low/normal
(0.084/0.084) — consistent with the known momentum-crash-in-high-vol pattern in the literature, not a new
finding, but worth carrying forward.

---

## 5. Degenerate detectors

- Sharpe 0.95 — **not** in the >4 fabrication band from the 2026-07 spread-Sharpe lesson.
- Hit-rate 68.5% — elevated but below the 75% threshold, and not paired with a W/L<0.5 pattern (LS mean
  2.37%/mo vs std 8.63%/mo — a normal, if slightly fat-tailed, monthly spread, not a suspiciously smooth one).
- Return-distribution shape: skew **−2.40**, kurtosis **32.6** (LS monthly series) — a real, disclosed fat
  left tail (occasional bad months), not a red flag on its own, but it is why the CSCV-adapted PBO reads so
  high (§below) and something a PM should size for.
- No net-debit-style denominator anywhere in this construction (all `rank_pct`-based) — the 2026-07
  debit-denominator landmine does not apply here.
- P&L-concentration / R²-equity-line / ADV-violation checks are not directly meaningful at this
  decile-IC/rank stage (no position sizing or execution is modeled beyond the blended cost-bps drag); these
  become relevant once S1's output feeds an actual portfolio construction step, not at this scorecard layer.

**On PBO=0.996:** `harness.py`'s own docstring for `compute_pbo_cscv` discloses this is a **single-factor
adaptation** of the classic multi-strategy CSCV/PBO procedure (Bailey/Borwein/Lopez de Prado/Zhu 2014), not
the literal paper method — it is testing whether 12 chronological blocks of ONE already-blended composite
are internally consistent, which is a much harsher and less standard bar than the paper's original intent
(choosing among *competing* strategies). Combined with the fat left tail above, a high adapted-PBO here is
expected and, per blueprint §2.4, **explicitly advisory, not gating**. I am not letting it override the
clean hard gates (lag, placebo) or the honest-count DSR — but it's disclosed in full, not buried.

---

## 6. Verdict: **REAL**

Both HARD GATES (lag-test, placebo) pass cleanly, DSR on the honest per-family trial count (n=1, this is a
genuinely first-and-only evaluation of this exact composite, not a search) clears the firm's own 0.95 bar
at 0.997, monotonicity and IC_IR are solid, and the 2× cost stress survives with room (20.9% net ann.). This
is not a fabricated result by any of the landmine patterns this desk has been burned by before.

### Single weakest assumption

**The blueprint's own economic-prior assumption that `earn_1M` "carries the weight" alongside momentum (its
stated 40% weight, per §2.1's own FM logic: "momentum + earnings-surprise carry the weight") is not borne
out by the drop-one-leg test.** `earnings_confirm_v2=1` fires on only ~5.9% of the panel monthly, so the leg
is overwhelmingly neutral-0.5 filler; removing it entirely does not reduce (and marginally improves) IC and
LS Sharpe. The composite's actual edge is concentrated almost entirely in the skip-15 momentum leg, with
`qual_floor_1M` doing its intended job as a floor (small, positive, non-dominant contribution) and `earn_1M`
contributing close to zero net signal at its current 40% weight. This is not grounds to kill or reweight
under this task's mandate (no weight search permitted here), but it is the single fact a PM or the next
builder most needs to know before trusting the "momentum + earnings-surprise" framing literally.

Secondary, disclosed concern (not the primary pick, but related): IC is **decaying** in the most recent eras
(2021–2024: 0.048, 2024–2026: 0.015, 2024 single-year: −0.014), on real (not artificially thinned) data. If
this decay continues, the momentum leg itself — not just earn_1M — may be weakening, which would matter more
than the earn_1M finding above. Both should be watched at the next scheduled edge-decay re-score.

---

## 7. FM lens (Principal's 2026-07-18 mandatory instruction)

> FM LENS (Arjun Rao): a 1M momentum + earnings-surprise + news-screen combo is exactly the kind of tilt a
> real short-horizon PM already runs informally — "is this name still working, did it just beat and guide
> up, and is there a skeleton in the news I don't know about" is a Monday-morning checklist, not a fitted
> model. The skip-15 momentum leg avoids the classic 1-month reversal trap; gating earnings on a CONFIRMED
> (reported, PIT) reading rather than a forecast keeps it honest; the quality floor doing nothing but
> excluding junk (not selecting on it) matches how a PM actually uses ROE/CFO-PAT at this horizon — as a
> screen, never a driver.
>
> Where this is economically hollow, not statistically clean: the no-neg-news gate, as built, is a 55-name
> island in a ~750-name sea — it reads like a real risk control but for ~93% of the universe it is a no-op
> passed by construction, not by verification. A PM using this scorecard needs to know that the "no adverse
> news" badge is only meaningful for the large-cap 55 and is silent (not clean) everywhere else — shipping it
> unlabeled would be the statistically-clean-but-economically-hollow failure mode this review exists to
> catch.
>
> Conversely, the WASHOUT/rev5d substitution is the piece most likely to look fragile on paper (n=25
> BEAR_OVERSOLD-tagged dates; DSR/PBO fail at that n per the firm's own low-t rule) but is economically the
> most sound leg here — it fires only in the specific ~17% oversold-extreme regime where the certified rev5d
> has already survived per-episode drop-one, era-split, and 2×-cost tests in `REGIME_SPEC_V2 §0`. That is a
> case where thin-sample statistics should NOT override sound logic + prior certification, per the firm's own
> low-t re-screen rule.
>
> And the drop-one-leg finding above (§6) is the mirror-image failure mode: earn_1M *looks* like it should
> matter economically (earnings surprises genuinely move 1M prices) but the way it's gated here (~6% monthly
> incidence, neutral fallback elsewhere) makes it statistically almost inert. A real PM would either widen the
> confirm gate or accept that, at 1M, momentum alone is doing the work and earnings-surprise is a rare bonus
> tiebreaker, not a co-equal driver.

---

## 8. No-negative-news coverage caveat (repeated explicitly, per instruction)

**S6's `no_negative_news_screen.parquet` covers 55 large-cap symbols out of the ~750-name universe.** For the
remaining ~695 names (93% of the panel-pit universe by symbol count; 99,069 of 99,415 rows before any other
gate), `no_negative_news_flag` defaults to `True` (pass) purely because there is no row to match against —
**this is a coverage gap, not a verified clean read.** Only 346 of 99,415 universe rows were actually excluded
by this gate in the full 2005–2025 sample, all of them among the 55 covered names. Anyone consuming
`rel_score_1M` downstream must not read "passed no_neg_news" as "verified no adverse news" for the ~93%
uncovered tail — it means "not checked."

---

## 9. Low-conviction flag (ships as instructed)

**RELATIVE 1M ships LOW-CONVICTION**, per `FINAL_MODEL §5.2`: there is no 21-year intra-month confirmation of
this exact composite (only the individual certified pieces — rev5d, the regime classifier — have that
history; the 1M composite itself is new). A PM should treat `rel_score_1M` as a **tilt/timing nudge layered
on top of other theses**, not a standalone buy/sell signal.

---

## 10. Determinism-check confirmation

Confirmed twice within the same foreground run of `S1_build_relative_1M.py`: the full pipeline (universe
load → mom/rev5d → regime classify → earn_1M → qual_floor_1M → no_neg_news → combine → final rank) was
executed from disk **twice**, independently, and the resulting `(date, symbol, ..., rel_score_1M)` frames
were confirmed **byte-identical** via SHA-256 hash of `pd.util.hash_pandas_object` plus a full
`DataFrame.equals()` check — both passed (`sha256_match=True`, `dataframe.equals=True`). Zero `.fit()` calls
in the scoring path; the only RNG anywhere is the harness's evaluation-time placebo shuffle (seed=42), which
never touches the scoring script.

---

## Output files

- `rnd/scorecard/rel_score_1M.parquet` — 99,415 rows × [date, symbol, sector, regime, washout, mom_1M_raw,
  rev5d, mom_1M_component, earn_1M, qual_floor_1M, neg_news_flag, composite_1M, rel_score_1M]
- `rnd/scorecard/weights_1M_fragment.json` — frozen weights/thresholds for S7's final merge (own fragment
  file only; `weights_v1.json` and other horizons' fragments untouched)
- `rnd/scorecard/S1_REL_1M_harness_card.json` — full harness card + era-split + drop-one-leg + LS-Sharpe extras
- `rnd/scorecard/S1_fm_lens.txt` — FM-lens paragraph (also inlined above)
- `rnd/scorecard/S1_build_relative_1M.py`, `rnd/scorecard/S1_evaluate_relative_1M.py` — the build and eval
  scripts, run synchronously in the foreground, determinism-checked
