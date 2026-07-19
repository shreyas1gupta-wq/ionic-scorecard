# S4 — ABSOLUTE (STANDALONE) SCORECARD — build + evaluation report

**Owner:** Arjun Rao (Head of Quant, E-004). **Date:** 2026-07-18. **Status:** IMPLEMENTATION
of `SCORECARD_BLUEPRINT.md` §1 + §3 + §3.4, exactly as specified — no weight search, no new
legs, no fitted P(up). **Hard non-goal honored (§0.1): this build never reads, imports, or is
seeded by `rel_score_1M/1Y/5Y.parquet` or any relative-score artifact** (grep-verified: zero
references to `rel_score` in `S4_build_absolute.py` / `S4_eval_absolute.py`).

Code: `ALPHA_RANKER/rnd/scorecard/S4_build_absolute.py` (score construction + P(up) lookup +
determinism check) and `S4_eval_absolute.py` (portfolio backtest + placebos + hard gates).
Both run synchronously, foreground, to completion; console logs banked at
`C:\tmp\s4_build.log` and `C:\tmp\s4_eval.log`.

---

## 0. Bottom line

**None of the three horizons clears the mandatory dual-placebo bar on both CAGR and
Calmar simultaneously.** 1M additionally fails the hard lag/placebo gate outright on both
drivers. 5Y is directionally the most economically coherent of the three (sane intensity
magnitudes, cleanest driver ICs, only horizon to beat the cap-weighted placebo on both
metrics) but still loses to the *random*-selection placebo on Calmar, and its 12.7-year
usable sample is really only **~2.5 independent non-overlapping 5-year windows**, not the
"~3-4" the blueprint anticipated — coverage does not start until March 2013, later than
the full panel history would suggest. **Verdict: 1M = FAKE (hard gate KILL). 1Y = FRAGILE.
5Y = FRAGILE (least bad, not certifiable).** Nothing here should be read as "the model
works" — it should be read as "here is exactly where a standalone absolute-return model's
honest signal sits today, and why none of it clears this firm's own bar."

---

## 1. Data lineage [DATA]

| Input | Path | Rows used | Date range (scored subset) |
|---|---|---|---|
| Panel grain / forward labels | `rnd/panel/panel_pit.parquet` | 99,415 (date,symbol) rows, 249 monthly dates | 2005-04-29 → 2025-12-05 (survivorship-free, 42-snapshot PIT) |
| Valuation | `rnd/panel/stock_valuation_pit.parquet` | PE notna 89,613/148,297 (60.4%) | same |
| Growth/earnings-confirm | `rnd/wave4/_w6fg2_scored.parquet` | 143,907 rows; `op_growth_t` notna 59.1%, `rev_growth_t` 62.8%; PIT assert `available_date<=date` passed (0 violations / 106,245 checked) | same |
| Market regime | `rnd/panel/market_state.parquet` | 249 monthly dates | richness_index range 47.4–122.4; **0/226 dates ≥160 (OVERVALUED never fires — confirms §1.2's own disclosed empirical gap)**; 7/226 dates <65 (UNDERVALUED) |
| Benchmark | `rnd/panel/cube_bench_long.parquet` (NIFTY500 level) | 5,131 daily rows, 2005-04-01 → | used for buy-hold context row only |

**Joint coverage after gating (g AND rerating both present):** 52,210 / 99,415 rows (52.5%),
identical across all three horizons (the presence rule only depends on g/PE inputs, not the
horizon-specific forward label). **After the additional `MIN_NAMES_PER_DATE≥20` +
`fwd_ret_1M_raw` requirement for the portfolio backtest, only 152/249 monthly dates are
usable, and the first usable date is 2013-03-28 (27 names), jumping to ~283-296 names by
2013-05-31.** This is a real, disclosed coverage-ramp artifact (`op_growth_t`/PE coverage
is much thinner before ~2013) — **NOT the ~20 years of history the full panel_pit date range
suggests.** This is the same class of landmine as the firm's own "17-month gap"/"partial-year
data reads as positive every year" lesson: always check the *actual* usable-date coverage
before trusting a long-sample claim.

---

## 2. Guards / determinism — PASSED

- PIT assert on `_w6fg2_scored.parquet` (`available_date <= date`): **0 violations**.
- `S4_build_absolute.py` run TWICE from disk: `absolute_scorecard.parquet` SHA-256 match =
  **True**, `pd.DataFrame.equals` = **True**. `pup_lookup_v1.parquet` SHA-256 match = **True**,
  `equals` = **True**. Zero `.fit()` calls in the scoring path (P(up) lookup is a one-time
  frozen historical tabulation, not a live fit).
- No `rel_score_*` reference anywhere in either script (hard non-goal §0.1 verified by
  inspection, not just by intent).

---

## 3. Score construction — what got built (see script docstrings for full formula detail)

- **g** = 0.5·mean(op_growth_t, rev_growth_t) + 0.5·rev_accel **only when** `earnings_confirm_v2==1`;
  else = mean(op_growth_t, rev_growth_t) alone (fallback-to-trailing, not blended with zero).
  5Y gets a frozen +2pp/yr durability boost when `sub_op_persistent==1`. Clipped to [-20%,+40%]/yr.
- **rerating** = clip(PE_anchor·regime_multiplier(band) / PE_current, 0.5, 2.0), where
  PE_anchor = mean(own-trailing-expanding-median PE, cross-sectional sector-median PE — the
  latter computed directly from `stock_valuation_pit.parquet`, since neither
  `sector_context.parquet` nor `market_state.PE_by_tier` actually carries a per-sector PE
  level on disk — [MY CALL, J4], disclosed).
- Five judgment calls (J1–J5) are logged verbatim in `weights_absolute_fragment.json` and in
  the build script's module docstring — none require a rebuild if the Principal rules
  differently (one-line changes).

**Distributional check (52,210 scored rows/horizon):**

| Horizon | g median (IQR) | rerating median (IQR) | E[total_return_h] median | **intensity (annualized) median** | intensity 95th pct |
|---|---|---|---|---|---|
| 1M | 11.3% (−20%…40%, clipped both tails ~equally) | 0.936 (0.5–2.0 clipped) | −5.7% | **−50.5%/yr** | **+4675%/yr** |
| 1Y | 11.3% | 0.936 | +3.7% | +3.7%/yr (identical to E_return, H=1) | +140%/yr |
| 5Y | 12.5% | 0.936 | +73.1% | **+11.6%/yr** | +50.1%/yr |

**DEGENERATE-DETECTOR FLAG, 1M (found, not silently patched):** the blueprint's own §3.2
formula does not horizon-scale the `rerating` ratio inside `E[total_return_h]`; it is the
same clipped multiple gap fed into `(1+g)^H·rerating` at every horizon. At 1M, `H=1/12`
makes `(1+g)^H≈1`, so a modest rerating gap (e.g. 1.3×) reads as "the market re-rated this
name 30% *this month*" and then gets ANNUALIZED via `(1+E)^(1/H)−1 = (1+E)^12−1`, which
explodes: **median annualized 1M intensity is actually −50%/yr, with a right tail to
+4,675%/yr (max +5,733%/yr)** — not the "reads near-neutral" the blueprint's prose
anticipated. This is exactly the Sharpe/P&L-degenerate pattern this desk is built to catch
(cf. Lessons Learned: spreading option-trade returns across holding days → fake-low-variance
Sharpe artifact — same genus of "annualizing a short-window number produces nonsense").
**Portfolio construction is NOT corrupted by this** — for a fixed date and horizon,
`intensity` is a strictly monotone transform of `E[total_return_h]`, so quintile RANKING
(which is all the backtest below uses) is identical whether sorted on `E_return` or
`intensity`. But the raw 1M *intensity number itself* must never be quoted or displayed as
an expected annual return — it is currently unusable as a magnitude. Flagged as the **single
weakest assumption at 1M**, not fixed here (redesigning the formula's H-scaling of rerating
is out of scope for an implementation task — recorded as a recommended blueprint revision).

**P(up) lookup — degenerate-band flag (found):** the frozen lookup (`pup_lookup_v1.parquet`,
24 rows) shows base "up" rates of ~54% (1M), ~62-67% (1Y), ~75-83% (5Y) — consistent with
India's secular equity drift (matches `ABSOLUTE_MODEL_STANDALONE.md`'s independently-derived
0.60/0.74 base rates almost exactly, a mild corroboration). Because the P(up) BAND cutoffs
(J5) are FIXED ABSOLUTE probability levels rather than base-rate-relative, **the coarse band
is degenerate at 1Y (100% of scored rows land in "pos" or "strong-pos", zero "neutral"/"neg")
and completely degenerate at 5Y (100% of scored rows = "strong-pos", zero differentiation
whatsoever)**. Only 1M retains some spread (`neutral` 71.0%, `pos` 29.0%, `neg`/`strong-neg`
combined 0.03% — driven by the tiny 7-row UNDERVALUED-band cells). **This band, as shipped,
carries almost no information at 1Y/5Y beyond "the market usually goes up over that
horizon"** — a base-rate-relative recalibration (P(up) minus the horizon's own average) is
the obvious fix but is a NEW judgment call beyond this implementation pass; flagged for the
Principal / a future version bump, not silently redesigned here.

**Also disclosed:** the OVERVALUED band never populates a lookup cell in this historical
sample (0 rows, matches §1.2's own documented empirical gap) — if it ever fires OOS/forward,
`apply_pup_lookup` correctly returns `pup_band="unscored"` (verified in code: no silent
default), not a fabricated probability.

---

## 4. Portfolio backtest (§3.4) — 152 usable months, 2013-03-28 → 2025-10-31, gross costs only

Construction: long top-quintile by `E_return_h`, equal-weight, monthly rebalance, realized
`fwd_ret_1M_raw` (identical mechanics at all three horizons — only the *selection* signal's
horizon varies). Average 336.6 names/month in the scored universe, ~67.7 selected (top
quintile). Placebo 1 = random quintile-sized draw (seed=42) from the same monthly universe.
Placebo 2 = the SAME names the real model selected, cap-weighted instead of equal-weighted.

| Horizon | Portfolio | CAGR | Calmar | Sharpe | MDD | ann-vol |
|---|---|---|---|---|---|---|
| **1M** | REAL | 27.96% | 0.517 | 1.140 | −54.1% | 24.5% |
| | Random placebo | 22.45% | **0.544** | 1.086 | −41.3% | 20.8% |
| | Cap-wt placebo | 22.70% | 0.496 | 1.050 | −45.8% | 21.9% |
| | NIFTY500 buy-hold | 14.24% | 0.475 | 0.901 | −30.0% | 16.4% |
| **1Y** | REAL | 27.82% | 0.482 | 1.134 | −57.7% | 24.6% |
| | Random placebo | 22.28% | **0.483** | 1.088 | −46.1% | 20.6% |
| | Cap-wt placebo | 25.18% | **0.495** | 1.119 | −50.9% | 22.5% |
| | NIFTY500 buy-hold | 14.24% | 0.475 | 0.901 | −30.0% | 16.4% |
| **5Y** | REAL | 23.42% | 0.395 | 1.024 | −59.3% | 23.5% |
| | Random placebo | 22.24% | **0.635** | 1.081 | −35.0% | 20.8% |
| | Cap-wt placebo | 18.94% | 0.343 | 0.974 | −55.2% | 20.1% |
| | NIFTY500 buy-hold | 14.24% | 0.475 | 0.901 | −30.0% | 16.4% |

**Beats-both-placebos check (mandatory, §3.4):**

| Horizon | Beats random (CAGR & Calmar) | Beats cap-weighted (CAGR & Calmar) | Verdict driver |
|---|---|---|---|
| 1M | **NO** (loses Calmar: 0.517 < 0.544) | yes | fails mandatory bar |
| 1Y | **NO** (ties/loses Calmar: 0.482 < 0.483) | **NO** (loses Calmar: 0.482 < 0.495) | fails mandatory bar |
| 5Y | **NO** (loses Calmar badly: 0.395 vs 0.635) | yes | fails mandatory bar |

**At every horizon the REAL portfolio's max-drawdown is materially worse than the random
placebo's** (1M: −54.1% vs −41.3%; 1Y: −57.7% vs −46.1%; 5Y: −59.3% vs −35.0%). All three
CAGR "wins" over random are compensation for taking on more drawdown risk, not a clean
Calmar edge — **this is precisely the FM-lens suspicion the Principal asked me to apply
explicitly (see §7): the equal-weight top-quintile selection is riding a higher-volatility/
higher-drawdown tilt, not demonstrating risk-adjusted stock-picking skill.** By the
blueprint's own stated rule ("if the scorecard doesn't beat BOTH placebos, the CAGR/Calmar
edge is a tilt, not the model"), **all three horizons fail this test.**

---

## 5. Hard gates — lag-test + placebo-shuffle on the g/rerating drivers (vs `fwd_ret_h_raw`)

| Horizon | Driver | IC (current) | IC (driver lagged 1 period) | lag_test_delta | placebo IC (5×, seed 42) | Gate (delta<0.25 AND \|placebo\|≤0.02) |
|---|---|---|---|---|---|---|
| 1M | g | 0.0058 | −0.0003 | **1.048** | 0.0022 | **FAIL** |
| 1M | rerating | 0.0202 | 0.0099 | **0.511** | 0.0024 | **FAIL** |
| 1Y | g | −0.0287 | −0.0332 | 0.153 | −0.0006 | PASS |
| 1Y | rerating | 0.0366 | 0.0407 | 0.112 | 0.0005 | PASS |
| 5Y | g | −0.0104 | −0.0100 | 0.039 | −0.0003 | PASS |
| 5Y | rerating | 0.0609 | 0.0592 | 0.029 | −0.0013 | PASS |

**1M is hard-gate KILLED on both drivers** — the driver's cross-sectional IC against
next-1-month realized return collapses (or flips sign) when the driver is staled by one
month, a signature of a fast-decaying/noisy signal at this resolution (PE-based `rerating`
updates every time price moves, so a 1-month-stale valuation snapshot loses most of its
information content at 1M sampling — consistent with, not contradicting, the blueprint's own
"valuation doesn't predict 1M" disclosure). 1Y and 5Y both pass cleanly, with 5Y showing the
smallest lag-deltas (3-4%) of the three — the strongest, most stable driver relationship in
the whole build. Notably **g's IC is slightly NEGATIVE at both 1Y and 5Y** (−0.029, −0.010) —
higher blended growth is weakly associated with *lower* forward returns at these horizons,
while `rerating` (the valuation-reversion driver) carries essentially all of the real signal
(IC +0.037 to +0.061). This is a genuinely surprising, disclosed finding: as constructed here,
**the "growth" half of the g×rerating story is not pulling its weight** — the model's honest
IC comes almost entirely from the valuation-reversion leg.

---

## 6. Robustness — era split (leave-one-non-overlapping-period-out proxy, §3.4)

Non-overlapping ~5-year blocks over the REAL 5Y portfolio's return series:

| Era | n months | CAGR | Calmar | MDD |
|---|---|---|---|---|
| 2005–2010 | 0 (no coverage) | — | — | — |
| 2010–2015 | 22 | **82.0%** | **12.3** | −6.7% |
| 2015–2020 | 60 | 6.3% | 0.17 | −37.2% |
| 2020–2026 | 70 | 24.1% | 0.70 | −34.3% |

**DEGENERATE-DETECTOR FLAG (found):** the "2010-2015" bucket is really only 22 months
(2013-03 → 2014-12, per §1's coverage-ramp finding — there is essentially zero usable history
before March 2013), during which universe coverage itself ramps from 27 to ~292 names
mid-stream. An 82% CAGR / 12.3 Calmar / −6.7% MDD reading over 22 months on a
still-stabilizing universe is a textbook small-sample / partial-coverage artifact (same genus
as the firm's own "partial-year data reads as positive every year" lesson) and **must not be
read as a real regime**. Excluding that transitional block, the two genuinely independent
post-2015 windows (2015-2020, 2020-2026) show CAGR 6.3% and 24.1% — a wide, inconsistent
range consistent with **~2 real independent 5-year draws**, materially fewer than the
blueprint's anticipated "~3-4," which itself weakens confidence in the 5Y aggregate CAGR
(23.4%) reported in §4 above.

---

## 7. FM lens (mandatory paragraph)

Does `g × PE-rerating` match how a real fundamental PM underwrites a position? Directionally,
yes — "pay a fair multiple for durable growth, expect a re-rating if you bought cheap
relative to the name's own history and its sector" is exactly the mental model a fundamental
PM uses, and the honest driver-level result here (rerating carrying real signal, g carrying
essentially none once confirmed-forward growth is blended in) is itself a useful, humbling
finding for that mental model: **it says the "growth" half of the thesis is not adding
value in this construction, and a PM should be more skeptical of paying up for growth alone
than of buying cheap-relative-to-history.** But the placebo comparison is where a real PM
should get *most* suspicious, and the honest answer is exactly what the Principal asked me to
call out: **at every single horizon, the real portfolio's drawdown is meaningfully worse than
a same-sized RANDOM draw from the identical universe** (−54% to −59% MDD vs −35% to −46% for
random), and the CAGR premium over random essentially reflects that extra risk, not
risk-adjusted skill — the Calmar ratio, which a PM should trust more than raw CAGR in a
long-only book, FAVORS THE RANDOM PLACEBO at every horizon except 5Y-vs-cap-weighted. A PM
looking at this backtest should ask: is the model's equal-weight top-quintile simply
concentrating in smaller, more volatile, more circumstantially "cheap-for-a-reason" names
that a dumb random draw from the same universe would partly avoid by chance? The data here
says: probably, at least in part — this is precisely the small/mid-cap-tilt-riding-a-bull-
market confound the blueprint itself named as the exact failure mode of the prior
`ABSOLUTE_MODEL_V2` +11pp CAGR result, and it has not been avoided here either.

---

## 8. Verdict per horizon + weakest assumption

| Horizon | Verdict | Single weakest assumption |
|---|---|---|
| **1M** | **FAKE** (hard-gate KILL) | Un-annualized `rerating` term produces a mathematically degenerate intensity magnitude (median −50%/yr, tail to +4,675%/yr) AND the drivers fail their own lag-test outright (delta 0.51–1.05 vs the 0.25 bar) — both the magnitude and the underlying signal are unusable at this resolution. |
| **1Y** | **FRAGILE** | Driver ICs are real and pass the hard gate, but the portfolio-level edge does not survive the mandatory placebo comparison — real Calmar (0.482) is statistically indistinguishable from / worse than BOTH the random (0.483) and cap-weighted (0.495) placebos; the CAGR premium is a drawdown premium. |
| **5Y** | **FRAGILE** (least bad, not certifiable) | Cleanest driver signal and only horizon beating the cap-weighted placebo, but (a) still loses to the random placebo on Calmar by a wide margin (0.395 vs 0.635), and (b) the usable sample is really only ~2 independent non-overlapping 5-year windows post-2015 (the pre-2015 data is a coverage-ramp artifact), materially thinner than the ~3-4 the blueprint anticipated. |

**No horizon is promotable today.** This matches, and independently corroborates, the
`ABSOLUTE_MODEL_STANDALONE.md` (fitted-model) prototype's own finding that this firm's
absolute-return signal is real-but-uncertifiable and strongest (if still not clean) at 5Y —
two independently-constructed absolute models (one hand-set/frozen, one fitted) landing on
the same qualitative conclusion is a mild corroboration of the *finding*, not a certification
of either model.

---

## 9. Determinism-check confirmation

`S4_build_absolute.py` executed its full build pipeline twice in the same run
(`build_everything()` called twice, no caching between calls): `absolute_scorecard.parquet`
(298,245 rows) SHA-256-matched byte-for-byte across both runs, `pup_lookup_v1.parquet`
(24 rows) likewise. `pandas.DataFrame.equals()` returned `True` for both artifacts on both
comparisons. Zero `.fit()` calls anywhere in the scoring path. Console confirmation:
```
DETERMINISM CHECK: PASS (byte-identical scores AND pup_lookup across two independent rebuilds)
```

---

## Output files

- `ALPHA_RANKER/rnd/scorecard/absolute_scorecard.parquet` (298,245 rows: date, symbol,
  sector, horizon, E_return, intensity, pup_band, g, rerating, band, p_up, PE_current,
  PE_fair, fwd_ret_h_raw, fwd_ret_1M_raw, mktcap_log)
- `ALPHA_RANKER/rnd/scorecard/pup_lookup_v1.parquet` (24 rows: horizon, g_tercile,
  rerating_sign, band, p_up, n_obs)
- `ALPHA_RANKER/rnd/scorecard/weights_absolute_fragment.json` (all frozen constants +
  judgment calls J1-J5 + per-horizon build diagnostics)
- `ALPHA_RANKER/rnd/scorecard/S4_eval_results.json` (full portfolio-backtest + gate numbers)
- `ALPHA_RANKER/rnd/scorecard/S4_build_absolute.py`, `S4_eval_absolute.py` (source)
- This report: `ALPHA_RANKER/rnd/scorecard/S4_ABSOLUTE_REPORT.md`
