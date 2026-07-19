# W6FG — Forward-Growth/Theme Dimension + Value-vs-Growth (GARP) Divergence Classifier
Devika Menon (Fund Manager, Equities & Momentum), with Quant Head coordination. 2026-07-17.
Principal's brief: the validated 7-leg is backward value/quality and structurally penalizes
capex/dilution that funds future growth — it would short early multibaggers. Forward-looking
matters MORE for 5Y/multibaggers. Build the dimension honestly; kill it if it's story-chasing.

All numbers in this note are **[DATA]** (read from disk, verified by row count) unless
tagged **[INFERENCE]** (derived here) or **[OPINION]** (my judgment call). No fabrication;
everything reproducible from the scripts listed at the bottom.

## 0. A harness-calibration fact that changes how to read every verdict below
Before trusting any single-factor "KILL" verdict from `rnd/lib/harness.py`, I checked the
harness's own track record: across **558** previously-evaluated factors in `rnd/cards/` with a
PBO number, **median PBO = 0.98** and **0% pass PBO ≤ 0.50** [DATA, verified this session].
The harness's single-factor CSCV/PBO adaptation is documented in its own docstring as "not the
literal multi-strategy paper procedure," and empirically it kills almost everything the firm has
ever tested, including (presumably) components of the validated 7-leg itself. So a "KILL"
verdict from this harness is **not, on its own, evidence a factor is worse than the production
book** — I read IC_IR + Newey-West t-stat + monotonicity + hit-rate + sign-stability instead,
and flag PBO/DSR separately as "this gate fires on almost everything, calibration issue for
Sameer Bhat / overfit-analyst to fix, not a fresh finding about this factor."

## 1. Data used (PIT construction)
- `data/fundamentals/MASTER_fundamentals_pit.parquet` — 1,092,785 rows, 2,356 symbols. Filtered
  to `sales`, `operating profit`, `opm %`, `cwip`, `fixed assets` (annual, `available_date` ≈
  FYE+3 months). Restatements (11.5% of symbol-fiscal_year groups have >1 `available_date`)
  collapsed to the **first disclosed** date — never the latest restatement — to avoid using
  information not knowable at the time.
- Derived, per (symbol, fiscal_year), using only same-symbol prior rows (no cross-symbol/future
  leakage): `rev_accel` = YoY revenue growth minus PRIOR YoY growth (the 2nd derivative /
  acceleration), `margin_inflection` = current OPM% minus trailing-3Y average OPM%,
  `cwip_growth` / `cwip_intensity` = capex-in-progress dynamics, `earnings_confirm` = operating
  profit YoY growth > 0 (the "theme+earnings=stays" gate).
- Theme tag: `data/universe/sector_map.parquet` (2,825 symbols), keyword match on
  macro/sub-sector text (renewable/solar/defence/EMS/capital goods/power/infra/battery/
  semiconductor) → 349 symbols (12.4%) tagged.
- Joined onto `rnd/panel/panel_long.parquet` (148,297 rows, 969 symbols, 2005-2025, the FULL
  history — not the truncated `panel.parquet`) via `merge_asof(..., direction="backward")` per
  symbol: median staleness between panel date and the fundamentals `available_date` actually
  used = **184 days** [DATA] — i.e., a typical rebalance is looking at data ~6 months old, which
  is what PIT annual-filing lag should look like, not fresher (no lookahead) and not absurdly
  stale either.
- Value/quality axis: `rnd/panel/canonical_7leg_scores.parquet` (`value7leg_score`, the
  validated 7-leg composite, ~+100 cheap+quality to ~-100 expensive/poor-quality-by-backward-
  metrics).

## 2. Four factors built, all run through the ONE harness (`H.evaluate`, panel_long, excess basis)
| factor | construction | 1M IC_IR / NW-t | 1Y IC_IR / NW-t | 5Y IC_IR / NW-t |
|---|---|---|---|---|
| `THEME_ALONE` | sector tag only, static | 0.002 / 0.0 | 0.038 / — | **-0.201 / -0.48** |
| `ACCEL_ALONE` | raw revenue-growth acceleration only, no gate | -0.028 / — | -0.275 / — | **-0.721 / -3.18** |
| `COMPOSITE_RAW` | z(accel)+z(margin_infl)+theme, no gate | 0.228 / — | 0.407 / 1.53 | 0.398 / 0.83 |
| `COMPOSITE_CONFIRMED` | same, unconfirmed names forced to bottom | 0.201 / — | 0.101 / 0.42 | 0.163 / 0.50 |

Full cards: `rnd/wave4/cards_w6fg/W6FG_*.json`.

**Reading this honestly:**
- **Raw growth acceleration alone is not just useless, it's actively harmful at 5Y**
  (NW-t = **-3.18**, monotonicity **-0.19**, i.e. the top-growth-acceleration decile
  UNDERPERFORMS the bottom decile). This is a real, statistically significant negative signal —
  the exact "growth trap" the firm already killed as families H024-H027
  (`rnd/cards/_growth_run_summary.json`, all KILL, e.g. H024_1Y IC_IR -0.59, PBO 0.78). Raw
  growth chasing is confirmed dead twice now, independently.
- **The static theme tag alone is noise-to-mildly-negative** (NW-t -0.48 at 5Y, not
  distinguishable from zero, but hit-rate only 22% and horizon-aware annualized L/S return
  **-17%/yr**). Buying a sector label with no earnings check behind it is a bad idea on this
  data — story-chasing confirmed.
- **The combined composite (accel + margin-inflection + theme, undirected/no gate) is the only
  one that looks interesting**: IC_IR ~0.40 at both 1Y and 5Y, decent hit rate (~63%), but the
  Newey-West t-stat is 1.53 (1Y) and only **0.83 (5Y)** — well under the conventional |t|>2 bar.
  **Low-t rule: this does not clear the bar for a real, tradeable signal on its own.** It is a
  "maybe," not a "yes."
- **My crude binary earnings-confirmation gate (force unconfirmed names to the worst decile)
  made the composite WORSE, not better** (IC_IR drops from 0.40 to 0.16 at 5Y, monotonicity
  collapses to ~0). See §3 for why — this falsifies the naive form of "theme+earnings=stays"
  as I first implemented it, and is an important, non-obvious finding in its own right.

## 3. Why the earnings-confirmation gate backfired (informal diagnostic, not a harness card)
Splitting the composite's IC by earnings_confirm status directly (not gating, just
conditioning) instead of injecting a penalty:

| horizon | subset | IC_mean | IC_IR | NW-t | n_obs |
|---|---|---|---|---|---|
| 1Y | confirmed (op-profit growing) | 0.0226 | 0.181 | 0.68 | 50,733 |
| 1Y | **unconfirmed** (op-profit NOT growing) | 0.0727 | **0.818** | **3.57** | 25,508 |
| 5Y | confirmed | 0.0242 | 0.197 | 0.41 | 31,163 |
| 5Y | **unconfirmed** | 0.0936 | **0.771** | **3.54** | 14,663 |

**The composite works BETTER — and is statistically significant (NW-t ≈ 3.5) — precisely among
names where operating profit growth has NOT yet turned positive.** [INFERENCE] The most likely
economic reading: a simple "op-profit YoY > 0" test is a poor proxy for "is this a real
inflection" because it's base-effect-dominated — a company coming off a small or negative prior-
year profit base can show revenue acceleration and margin improvement for 1-2 years BEFORE its
YoY op-profit growth crosses zero on this crude test. In other words: **my binary gate fires too
LATE relative to the inflection it's trying to confirm** — by the time op-profit growth is
positive on a simple YoY basis, much of the re-rating may already be behind the stock. This is
a genuine, counter-intuitive result and a specific, falsifiable critique of the "theme+earnings=
stays" discipline **as a same-period binary gate** — it needs a lagged or multi-year
confirmation window (e.g., op-profit growing in 2 of the last 3 years, or op-profit margin
trend, not a single-year sign flip) to work as intended. I did not have runway in this pass to
rebuild and re-test that refined gate; flagging it as the next concrete step rather than papering
over it.

Fama-MacBeth (`fwd_ret ~ value7leg_score + composite_raw`, per date, avg coefficient + NW-t):

| horizon | value coef (NW-t) | growth coef (NW-t) | n_dates |
|---|---|---|---|
| 1Y | 0.072 (**4.61**) | 0.009 (0.72) | 141 |
| 5Y | 0.036 (0.18) | 0.224 (0.97) | 92 |

Value/quality's incremental power is clearly real and significant at 1Y (NW-t 4.61) but fades at
5Y (NW-t 0.18, n_dates=92 with heavy 5Y-overlap autocorrelation eating power). Growth's
coefficient is **directionally consistent with the brief's prior — much bigger at 5Y (0.224) than
1Y (0.009), i.e. forward-growth's incremental power over value/quality does look like it should
matter more at long horizons** — but at NW-t 0.97 it is NOT statistically distinguishable from
zero at either horizon. **Directionally plausible, not proven.**

## 4. GARP 2×2 quadrant (median split per date: value7leg_score × composite_raw)
| quadrant (1Y) | mean fwd ret | std | n | 
|---|---|---|---|
| Q1 cheap+growing (GARP) | **0.441** | 1.08 | highest |
| Q3 cheap+not-growing (value-trap risk) | 0.366 | 0.85 | |
| Q2 expensive+growing (STORY) | 0.330 | 0.95 | |
| Q4 expensive+not-growing (avoid) | **0.244** | 0.74 | lowest |

| quadrant (5Y) | mean fwd ret | std | CV (std/mean) |
|---|---|---|---|
| Q2 expensive+growing (STORY) | **2.675** (highest mean) | **8.78** (highest, by far) | 3.28 |
| Q1 cheap+growing (GARP) | 2.533 | 5.26 | 2.08 |
| Q3 cheap+not-growing | 2.240 | 4.70 | 2.10 |
| Q4 expensive+not-growing (avoid) | 2.191 (lowest) | 5.00 | 2.28 |

**Yes, the quadrant carries real, sensible information**, and it reproduces the task's own
language almost exactly: at 1Y, GARP (Q1) wins outright and the "story" cell (Q2) is
mediocre — a middling short-term result. At 5Y, Q2 (the "story" cell) has the HIGHEST mean but
also by far the highest dispersion (std 8.78 vs Q1's 5.26, CV 3.28 vs 2.08) — **the quadrant
literally reproduces "multibagger-OR-trap"**: on average it looks best, but you are taking on
far more variance to get there, and GARP (Q1) gets nearly the same mean with much tighter
dispersion. That is a genuine, useful, non-obvious result for portfolio construction, independent
of whether any single component factor clears its own significance bar.

**Does the earnings-confirm conditional separate multibagger from trap within Q2 (the "story"
cell)?** No — and in the SAME (surprising) direction as §3:

| Q2 split (1Y) | mean | std | n |
|---|---|---|---|
| unconfirmed | 0.410 | 0.97 | 3,972 |
| confirmed | 0.291 | 0.87 | 13,379 |
(t=-6.92, p<0.0001, confirmed underperforms unconfirmed)

| Q2 split (5Y) | mean | std | n |
|---|---|---|---|
| unconfirmed | 3.196 | 8.13 | 2,361 |
| confirmed | 2.432 | 9.09 | 8,199 |
(t=-3.92, p=0.0001, same direction)

Within the "story" cell, earnings-confirmed names (as I defined confirmation) do **WORSE**, not
better, than unconfirmed ones, both at 1Y and 5Y, both highly significant. Combined with §3, this
is a consistent pattern, not a fluke of one test — but it inverts the naive discipline. **Honest
verdict: my simple same-year op-profit-growth gate does NOT separate multibagger from trap in
the direction hypothesized; if anything it points the other way**, most plausibly for the
base-effect timing reason in §3.

## 5. INFY vs KPIGREEN — ex-ante adjudication (no lookahead: their own 5Y forward returns are
still unrealized/NaN in the panel, correctly not used; adjudication is via population base rates
+ their own PIT fundamental trajectory only)

**INFY** (7-leg score +39.65 "cheap+quality" / production score_5Y -9, score_1Y -25 "negative")
[DATA, verified]: PIT trajectory (FY2025 data as of 2025-12-05) shows `rev_growth_t`=6.1%,
`rev_accel`=+0.014 (essentially flat — barely accelerating), `margin_inflection`=-0.67
(margins slightly BELOW trailing 3Y average), `theme_dummy`=0 (not a policy-lever sector),
`composite_raw`=**+0.041** (near-ZERO on my forward-growth axis, neither a growth story nor a
growth trap). **[INFERENCE] I cannot explain the production engine's negative INFY call using
this forward-growth/theme dimension at all** — the growth composite is flat, not negative, so
whatever drives production's bearish 1Y/5Y view on INFY is coming from a different mechanism
(most likely valuation-multiple mean-reversion, estimate-revision momentum, or something else in
its own scoring — none of which I rebuilt here). This is an honest gap, not a resolved
adjudication: **on the forward-growth axis specifically, INFY is a non-event, not a case for or
against either engine.**

**KPIGREEN** (7-leg score -90.5 "very expensive/poor-quality-by-backward-metrics" / production
score_5Y +22 "mild BUY-ish") [DATA, verified]: PIT trajectory shows `rev_growth_t`=69.4%,
`rev_accel`=+0.104 (accelerating — this year's growth rate is 10.4pp above last year's),
`op_growth_t`=67.4% (**earnings_confirm=1**, operating profit IS growing, not just revenue),
`margin_inflection`=-5.33 (margins BELOW trailing 3Y average — plausible cost-of-new-capacity
drag), `cwip_intensity`≈0.07-0.10 (real, moderate capex-in-progress), `theme_dummy`=1 (renewable/
solar sector). This is EXACTLY the profile the 7-leg is structurally built to penalize (heavy
capex + margin compression + high growth funded by investment, not FCF) and exactly the profile
the brief describes as an "early multibagger" candidate. `composite_raw`=**+1.06**, placing it
squarely in the Q2 "expensive+growing/STORY" quadrant.

**But** — and this is the honest, hedged part — §4's own base-rate finding is that WITHIN Q2,
names with KPIGREEN's exact profile (earnings_confirm=1) have historically underperformed
Q2 peers where earnings are NOT yet confirmed, both at 1Y and 5Y, both highly significant. So
**the population base rate for KPIGREEN's specific profile is mediocre-to-average relative to
its own quadrant, not exceptional** — I cannot say ex-ante that KPIGREEN is a standout
multibagger-in-waiting versus an average Q2 name using this tool. What I CAN say confidently:
production's forward engine and the 7-leg are looking at genuinely different, both-real signals
here (a real revenue/earnings acceleration the 7-leg's backward metrics structurally miss, vs a
real margin-compression/capex-funding risk the forward engine may be underweighting) — this is
a legitimate divergence to hold in the portfolio construction as TWO camera angles, not a "one
engine is simply wrong" situation. Given the mild sizing on both sides (7-leg -90 is extreme,
but production's +22 is only a HOLD/mild-BUY band, not an extreme conviction call either),
neither engine is making an aggressive bet here — the practical read is: **small-to-no net
position from this signal alone, more diligence (concall/theme KB — not currently covering
KPIGREEN, see below) needed before sizing.**

Neither INFY nor KPIGREEN appear in the concall business-model KB (`rnd/wave4/batch_A/B/C.json`,
25 names total) — qualitative order-book/capacity corroboration was not available for this pass;
this adjudication rests on quant PIT fundamentals + population base rates only.

## 6. Verdict
1. **Does forward-growth (earnings-confirmed) add real 5Y predictive value beyond value/quality?
   MAYBE.** The combined composite (accel+margin-inflection+theme) shows a directionally
   consistent, economically sensible pattern (bigger incremental coefficient at 5Y than 1Y,
   matching the brief's prior that forward-looking matters more for multibaggers) but does NOT
   clear the low-t bar standalone (NW-t 0.83 at 5Y) or in the Fama-MacBeth race against value/
   quality (NW-t 0.97). My literal implementation of "earnings-confirmed" (same-year op-profit
   growth flag) actively hurts the composite and inverts the hypothesized multibagger/trap
   split — needs a lagged/multi-year confirmation redesign before this crosses from "maybe" to
   "yes." Raw growth-chasing (no gate at all) remains dead (NW-t -3.18 at 5Y, consistent with
   the already-killed H024-H027 family) and the static theme tag alone is noise-to-negative.
2. **Does the GARP-divergence quadrant predict returns and separate multibagger-vs-trap? Y/N-
   split: the QUADRANT itself Y** — GARP (cheap+growing) wins on a risk-adjusted basis and the
   "story" cell (expensive+growing) genuinely displays the hypothesized multibagger-or-trap
   character (highest mean AND highest dispersion at 5Y, CV 3.28 vs GARP's 2.08). **The
   earnings-confirm conditional does NOT separate multibagger from trap within that cell — N**,
   and in fact points the opposite direction from the hypothesis, for the base-effect reason
   in §3.
3. **INFY / KPIGREEN adjudication**: INFY's divergence is NOT explained by the forward-growth
   dimension (its growth composite is flat/near-zero) — a genuine gap, not a call either way.
   KPIGREEN's profile (real revenue+earnings acceleration, real margin compression from real
   capex, real theme) is exactly the structural 7-leg-blind-spot the brief describes, but its
   EXACT sub-profile (earnings-confirmed within the story quadrant) has a mediocre historical
   base rate versus its own quadrant peers — so this is a genuine two-engines-see-different-real-
   things divergence, not a case where one engine is straightforwardly right.
4. **Should the firm build a forward-growth sleeve on this? NOT YET.** The signal is real enough
   to keep researching (kill raw growth-chasing again confirmed; the combined composite is the
   most promising thing in this test and matches the brief's economic prior directionally) but
   it is underpowered on the low-t rule and the earnings-confirmation gate needs a redesign
   (multi-year, not single-year, confirmation window) before it earns a capital allocation. My
   allocation-defense hat: even if it eventually passes, this dimension would sit INSIDE the
   existing equities book (it's directional equity selection, not a new source of book-level
   diversification) — it doesn't change my diversifier argument for the momentum sleeve, it's a
   candidate improvement to stock selection within names already in the book's universe.

## Reproduction
- `rnd/wave4/w6fg_build.py` — PIT fundamentals build (STEP 1), writes
  `_w6fg_fund_derived.parquet`, `_w6fg_theme_tag.parquet`, `_w6fg_fund_on_grid.parquet`.
- `rnd/wave4/w6fg_evaluate.py` — factor construction + harness runs (STEP 2), writes
  `_w6fg_scored.parquet`, `cards_w6fg/W6FG_*.json`, `_w6fg_all_cards_summary.json`.
- `rnd/wave4/w6fg_diagnostics.py` (+ inline reruns for §3-5) — conditional IC, Fama-MacBeth,
  GARP quadrant, INFY/KPIGREEN pull, writes `_w6fg_diagnostics_DE.json`.
- All run synchronously, foreground, real data (`panel_source="real"` on every card).
