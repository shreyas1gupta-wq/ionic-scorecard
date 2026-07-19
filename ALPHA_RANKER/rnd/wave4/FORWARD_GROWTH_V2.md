# W6FG2 — Forward-Growth Composite, Multi-Year Earnings-Confirmation Gate (2nd and FINAL pass)
Devika Menon (Fund Manager, Equities & Momentum), with Quant Head coordination. 2026-07-17.

This is the redesign mandated after `FORWARD_GROWTH_DIVERGENCE.md` §3-4: the
single-year op-profit sign-flip gate BACKFIRED (made the composite worse, IC_IR
0.40→0.16 at 5Y, and within the GARP "story" quadrant confirmed names
UNDERPERFORMED unconfirmed ones — backwards from the intended "theme+earnings=
stays" discipline). Diagnosed cause: a same-year YoY>0 test is base-effect-
dominated and fires too LATE relative to the real inflection.

All numbers **[DATA]** (read from disk, verified by row/obs count) unless
tagged **[INFERENCE]** (derived here) or **[OPINION]** (judgment call). No
fabrication. Run synchronously, foreground, real data throughout
(`panel_source="real"` on every card). Deterministic — no randomization in the
gate construction or diagnostics; the harness's own placebo shuffle (seed=42)
does not affect any reported number.

## 1. The redesigned gate — persistence, not a single-period flip
Built in `w6fg2_build.py`, on `data/fundamentals/MASTER_fundamentals_pit.parquet`
(25,242 symbol-fiscal_year rows after PIT restatement-collapse, 2,356 symbols,
FY2002-2026 [DATA, verified]), same restatement/PIT discipline as V1 (first
disclosed `available_date` per symbol-FY, never the latest restatement).

`CONFIRM_V2 = 1` iff **ALL THREE** hold, using only same-symbol PRIOR rows
(chronological `.shift()`, no cross-symbol/future leakage), pre-registered
before looking at any 5Y result (no post-hoc threshold search):

1. **`op_growth_persistent`**: operating-profit YoY growth > 0 at BOTH the
   current fiscal year (t) AND the prior fiscal year (t-1) — replaces the
   single-year flag; a name that turned positive this year AND stayed
   positive last year cannot be the same-period base-effect blip diagnosed
   in §3 of the first pass.
2. **`margin_holds`**: margin_inflection (OPM% − trailing-3Y avg) > 0 at BOTH
   t and t-1 — the margin improvement must still be there a year later, not
   a one-year base-effect spike that mean-reverts.
3. **`cwip_converting`**: CWIP growth DECELERATING vs the prior year
   (`cwip_growth_t <= cwip_growth_t1`) — capex-in-progress is completing/
   converting into revenue-generating fixed assets, not still in an
   unconverted ramp (the "capex-to-revenue-ramp lag" the brief asked for).

`NaN` if any of the three inputs isn't computable (insufficient history —
excluded, not assumed good or bad). At the symbol-FY level: **confirmed(1) =
1,341, unconfirmed(0) = 9,393, NaN = 14,508** of 25,242 rows [DATA]. Strict
AND-of-3 is selective by design (~12.5% confirm rate of computable rows) — a
deliberate trade for genuine persistence, at the cost of sample size. Asof-
merged onto `panel_long.parquet` (full 2005-2025 grid): median staleness 184
days [DATA] — same PIT lag as V1, unchanged.

Sub-condition hit rates on computable rows [DATA]: op_persistent 42.3%
(n=16,527), margin_holds 33.8% (n=19,274), cwip_converting 55.6% (n=12,158).
None of the three is a rubber stamp — each is genuinely discriminating.

## 2. Headline re-test: does COMPOSITE_V2_CONFIRMED clear the bar at 5Y?
Same composite construction as V1 (`z(rev_accel) + z(margin_inflection) +
theme_dummy`), only the confirmation gate changed (forces unconfirmed names to
the bottom decile-equivalent). All four run through `H.evaluate()` (`rnd/lib/harness.py`),
`panel_long`, real, `return_basis=excess` unless noted. Full cards:
`rnd/wave4/cards_w6fg2/W6FG2_*.json`.

| factor | horizon | n_obs | IC_IR | NW-t | verdict |
|---|---|---|---|---|---|
| `W6FG2_COMPOSITE_V2_CONFIRMED` | 1M | 64,772 | 0.053 | 0.62 | KILL |
| `W6FG2_COMPOSITE_V2_CONFIRMED` | 1Y | 58,719 | 0.027 | 0.12 | KILL |
| `W6FG2_COMPOSITE_V2_CONFIRMED` | **5Y** | 33,918 | **0.139** | **0.53** | KILL |
| `W6FG2_COMPOSITE_V2_CONFIRMED_5Y_resid` | 5Y (resid) | 33,551 | 0.213 | 0.74 | KILL |
| `W6FG2_COMPOSITE_V1_CONFIRMED_5Y_REFCHECK` (V1 gate, same composite, re-run for reference) | 5Y | 45,826 | 0.163 | 0.50 | KILL |

**Reading this honestly: the multi-year gate did NOT clear the low-t bar,
and it did not even improve on V1.** At 5Y (excess basis) IC_IR went from
V1's 0.163 to V2's **0.139 — slightly worse**, and NW-t is statistically
unchanged (0.50 → 0.53, both far under the |t|>2 bar and both under the
ungated `COMPOSITE_RAW`'s original 0.398/0.83 from the first pass). The resid
basis is the best V2 result found (IC_IR 0.213, NW-t 0.74) but still nowhere
close to significance. **Making the gate stricter (persistence over 2 years,
3 conditions instead of 1) traded sample size for no power gain** — the
smaller, more selective "confirmed" bucket is not a materially better signal,
it is a differently-sized version of the same underpowered one.

## 3. Drop-one + era: is the (already-weak) 5Y result at least stable?
Computed directly (not a harness card) on `W6FG2_COMPOSITE_V2_CONFIRMED`'s 5Y
excess-basis merged sample (33,918 obs, Spearman IC per date, full-sample IC =
**0.0045** [DATA] — note this is the raw mean cross-sectional Spearman IC, not
the IC_IR/NW-t already reported above; near-zero, consistent with "weak
signal," not a contradiction).

- **Leave-one-year-out** (13 years): **1/13 sign flips** (2014 drops IC to
  -0.0003, essentially zero-crossing noise around an already-near-zero full
  IC, not a real reversal). 12/13 years hold sign.
- **Leave-one-sector-out** (23 macro sectors): **4/23 sign flips** (worst:
  dropping Capital Goods flips to -0.0039). 19/23 sectors hold sign.
- **Era split** (first half vs second half of dates chronologically): first
  half IC = 0.0328, second half IC = 0.0026 — **both same sign as full
  sample, era_holds = True**, but the magnitude decayed by ~12x
  first-half-to-second-half [DATA/INFERENCE: this reads as either genuine
  decay or simply noise around a signal whose true magnitude is close to
  zero either way — not distinguishable with this much power].

**Honest verdict on stability: technically holds (low sign-flip count, era
holds), but this is stability of a signal that is not statistically
distinguishable from zero to begin with.** A near-zero number staying
near-zero and same-signed across cuts is a weak form of "robustness" — it is
not evidence the underlying effect is real, only that there is no gross
overfitting-to-one-year/one-sector artifact inflating it. Full diagnostic:
`rnd/wave4/_w6fg2_dropone_era.json`.

## 4. The crux test: does the multi-year gate separate multibagger-from-trap
within the GARP "story" cell (Q2: expensive + growing)?
Same methodology as `FORWARD_GROWTH_DIVERGENCE.md` §4 (median split per date on
`value7leg_score` × `composite_raw`; Q2 = below-median 7-leg score (expensive)
AND above-median composite (growing)), now split by `CONFIRM_V2` instead of the
single-year V1 flag. Full output: `rnd/wave4/_w6fg2_story_cell_split.json`.

| horizon | confirmed mean | confirmed n | unconfirmed mean | unconfirmed n | t-stat | p-value | right direction? |
|---|---|---|---|---|---|---|---|
| 1Y | 0.188 | 1,975 | **0.255** | 10,861 | -4.09 | <0.0001 | **NO** |
| 5Y | 1.505 | 1,328 | **2.791** | 6,069 | -8.12 | <0.0001 | **NO** |

**This is the single most important result of the redesign, and it answers the
task's crux question unambiguously: NO, the multi-year gate does NOT separate
multibagger from trap in the hypothesized direction — it goes backwards, in
the SAME direction as V1's single-year gate, and MORE strongly so at 5Y**
(V1's confirmed/unconfirmed gap within Q2 at 5Y was 2.432 vs 3.196 [ratio
1.31x]; V2's gap is 1.505 vs 2.791 [ratio 1.85x] — a WIDER gap, both highly
significant, p<0.0001 both times). Making the earnings-confirmation test
stricter and multi-year did not fix the inversion — it sharpened it.

**[INFERENCE] Economic reading, now replicated twice independently (V1 same-
year gate, V2 strict multi-year gate):** within the expensive+growing quadrant,
names whose earnings/margin story has ALREADY fully confirmed and persisted —
and whose capex has ALREADY converted (CWIP decelerating) — are, on average,
names where the re-rating is largely BEHIND them, not ahead. The stocks with
the biggest forward returns in this quadrant are disproportionately the ones
still mid-story: revenue/theme momentum present, but earnings/margin/capex
proof not yet fully locked in. This is the opposite of "theme+earnings=stays"
as a forward-return discipline — on this data, "theme, earnings-not-yet-fully-
proven" outperforms "theme, earnings-fully-proven-and-persisted." This is not
a data quirk of one gate design; it now holds under two structurally different
gate constructions (single-year sign flip AND strict 3-condition 2-year
persistence), which is the strongest evidence yet that it is a real
population-level pattern on this data, not an artifact of how the gate was cut.

## 5. Verdict
1. **Multi-year 5Y IC_IR / NW-t**: IC_IR **0.139**, NW-t **0.53** (excess
   basis); IC_IR 0.213, NW-t 0.74 (resid basis, best V2 result). Neither
   clears |NW-t|>2. **Does NOT clear.**
2. **Drop-one + era hold?** Directionally yes (1/13 year sign flips, 4/23
   sector sign flips, era same-sign both halves) — but this is stability of a
   signal indistinguishable from zero, not confirmation the effect is real.
3. **Does it separate multibagger-vs-trap in the story cell?** **NO** — same
   wrong direction as V1, more strongly so at 5Y (1.85x gap vs V1's 1.31x),
   both t-stats highly significant (p<0.0001). This is now a twice-replicated,
   direction-consistent finding under two independent gate designs.
4. **Per the pre-registered honesty rule for this 2nd shot: the multi-year
   gate ALSO fails to clear the bar, and it does not reverse the story-cell
   inversion — it makes it worse. Per instruction, this is PARKED, not
   re-cut a third time.** Re-cutting the gate again would be overfitting the
   gate to the answer I want, not testing a hypothesis.
5. **[OPINION] What I'd actually resurrect on, if ever**: the story-cell
   inversion (replicated twice, large, significant, and economically legible —
   "not-yet-proven theme names outperform proven ones") is itself a candidate
   signal, but it is the OPPOSITE of what this task set out to build (a
   confirmation gate that REWARDS proof). Flipping the polarity — i.e., an
   "early-innings" filter that favors theme+growth names whose earnings proof
   is NOT yet locked in — is a genuinely different hypothesis from "forward-
   growth-confirmed," would need its own honest cheap-test and its own trials
   count, and is not something to fold into this already-twice-tested family
   without flagging it as a new idea to Quant Head first (resurrection
   condition, not a same-session pivot).
6. **Allocation-defense note unchanged**: even in the counterfactual where
   this had cleared, forward-growth is directional equity stock-selection —
   inside the existing equities book, not a new diversification source. This
   PARK does not change my diversifier argument for the momentum sleeve.

## Reproduction
- `rnd/wave4/w6fg2_build.py` — multi-year PIT fundamentals build (STEP 1),
  writes `_w6fg2_fund_derived.parquet`, `_w6fg2_fund_on_grid.parquet`.
- `rnd/wave4/w6fg2_evaluate.py` — composite scoring + harness runs (STEP 2) +
  drop-one/era diagnostic + story-cell split, writes `_w6fg2_scored.parquet`,
  `cards_w6fg2/W6FG2_*.json`, `_w6fg2_all_cards_summary.json`,
  `_w6fg2_dropone_era.json`, `_w6fg2_story_cell_split.json`.
- All run synchronously, foreground, real data (`panel_source="real"` on
  every card), deterministic (no tuning between build and evaluate; gate
  pre-registered in the build script's docstring before any 5Y number was
  seen).
