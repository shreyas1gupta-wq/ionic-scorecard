# FORENSIC / EARNINGS-QUALITY LANE (Wave-4 forensic) — methods, coverage, verdicts

Owner: Arjun Rao (Quant) for Sanjay Kulkarni (FM Fundamental Quality & Value).
Status: **R&D-lab hypotheses only** — NEXT-SLEEVE candidates, never touches the frozen 7-leg production model.
Data gate: every verdict below is gated on the `metric_norm` enumeration I ran myself (§B). If a needed
`metric_norm` is absent, the mechanism is **BLOCKED-BY-MISSING-METRIC**, not proposed.

Epistemic tags: [DATA] = I verified it by querying the parquet with row counts; [INFERENCE] = my reasoning;
[OPINION] = judgment call. No correlation numbers were computed (no tester run) — every orthogonality claim is [INFERENCE].

---

## A. Literature grounding (one line each)

- **Schilit — *Financial Shenanigans*:** the seven shenanigan families; the ones buildable here are #4/#5
  (shifting current expenses to later periods via aggressive capitalization / stretched depreciation) and #2
  (recording revenue too soon → receivables/asset bloat outrunning sales). [DATA: Schilit taxonomy]
- **Dechow–Ge–Schrand (2010), "Understanding Earnings Quality":** accruals are the core quality axis; the
  balance-sheet accrual and the *persistence* of accruals both predict; earnings that don't convert to cash or
  to book equity are low-quality. [INFERENCE grounding for W4F-02/04]
- **Sloan (1996):** the accruals anomaly — high accruals → low future returns (this firm's H022, level-based). [DATA: catalog]
- **Montier / Beneish:** manipulation checklists (C-score / M-score) — already in the catalog, not re-proposed.
- **Piotroski (2000) F-score:** DIRECTIONAL year-on-year improvement (ΔROA, Δmargin, Δleverage, Δturnover) beats
  variance-based stability — motivates streak/consistency framings over raw volatility. [DATA: catalog §3]
- **Revenue-recognition literature (Dechow-Sloan, channel-stuffing studies):** receivables growing faster than
  sales is the canonical too-soon-revenue tell — but requires a receivables line we do NOT have (see §D). [INFERENCE]
- **Penman (clean-surplus accounting):** ΔBook equity = comprehensive income − net distributions; violations of
  clean surplus flag write-offs/restatements/phantom earnings — the basis for W4F-02. [INFERENCE grounding]

---

## B. `metric_norm` coverage table (verified — the gate for every hypothesis)

Source: `ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet`, **1,092,785 rows**, 4,613 symbols,
fiscal_year 2002–2026, available_date 2002-06-29 → 2026-06-29. Statement split: PL 546,368 / BS 500,618 / CF 45,799. [DATA]
**34 distinct `metric_norm` values.** Columns rows / n_symbols / fy-range:

| metric_norm | stmt | rows | n_sym | fy range | coverage class |
|---|---|---|---|---|---|
| equity capital | BS | 49,355 | 4,613 | 2002–2026 | FULL |
| depreciation | PL | 49,352 | 4,613 | 2002–2026 | FULL |
| other income | PL | 49,352 | 4,613 | 2002–2026 | FULL |
| profit before tax | PL | 49,352 | 4,613 | 2002–2026 | FULL |
| expenses | PL | 49,352 | 4,613 | 2002–2026 | FULL |
| interest | PL | 49,352 | 4,613 | 2002–2026 | FULL |
| net profit | PL | 49,352 | 4,613 | 2002–2026 | FULL |
| total assets | BS | 49,281 | 4,599 | 2002–2026 | FULL |
| fixed assets | BS | 49,280 | 4,599 | 2002–2026 | FULL (NET block — no gross block) |
| other assets | BS | 49,280 | 4,600 | 2002–2026 | FULL (lumps CA+cash+recv+inv+misc) |
| total liabilities | BS | 49,279 | 4,599 | 2002–2026 | FULL |
| other liabilities | BS | 49,279 | 4,598 | 2002–2026 | FULL (lumps CL+provisions+misc) |
| investments | BS | 49,277 | 4,600 | 2002–2026 | FULL |
| reserves | BS | 49,277 | 4,599 | 2002–2026 | FULL |
| cwip | BS | 49,274 | 4,601 | 2002–2026 | FULL |
| borrowings | BS | 48,983 | 4,599 | 2004–2026 | FULL |
| tax % | PL | 48,624 | 4,613 | 2002–2026 | FULL |
| operating profit | PL | 48,271 | 4,530 | 2004–2026 | FULL |
| sales | PL | 48,271 | 4,530 | 2004–2026 | FULL |
| eps in rs | PL | 48,267 | 4,567 | 2005–2026 | FULL |
| opm % | PL | 45,655 | 4,493 | 2004–2026 | FULL |
| dividend payout % | PL | 7,695 | 749 | 2002–2026 | THIN (16%) |
| net cash flow | CF | 7,634 | 749 | 2005–2026 | THIN (16%) |
| cash from operating activity (CFO) | CF | 7,634 | 749 | 2005–2026 | THIN (16%) |
| free cash flow | CF | 7,634 | 749 | 2005–2026 | THIN (16%) |
| cash from investing activity | CF | 7,634 | 749 | 2005–2026 | THIN (16%) |
| cash from financing activity | CF | 7,633 | 749 | 2005–2026 | THIN (16%) |
| cfo/op | CF | 7,630 | 749 | 2005–2026 | THIN (16%) |
| preference capital | BS | 6,935 | 654 | 2005–2023 | THIN |
| financing profit | PL | 1,158 | 94 | 2002–2026 | FINANCIALS-only |
| revenue | PL | 1,158 | 94 | 2002–2026 | FINANCIALS-only |
| financing margin % | PL | 1,157 | 94 | 2002–2026 | FINANCIALS-only |
| borrowing | BS | 749 | 71 | 2002–2026 | tiny |
| deposits | BS | 369 | 34 | 2002–2026 | tiny |

**Three structural facts that decide the whole lane** [DATA, from the enumeration]:
1. **No receivables / debtors / inventory / trade-payables / unbilled / contract-asset / deferred-revenue line exists.**
   The entire DSO / receivables-vs-revenue / contract-asset revenue-recognition family is **BLOCKED** at the clean level.
2. **No current-asset / current-liability split and no cash line** (only `other assets` / `other liabilities`, which
   lump everything). Clean working-capital, CCC, and balance-sheet-accrual (needs cash) constructions are **BLOCKED**;
   only a very coarse `other assets`-vs-sales proxy survives.
3. **CFO exists for only 749 of 4,613 symbols (16%).** The incumbent forensic leg (CFO/PAT authenticity, IC_IR 1.14)
   and Sloan H022 both live on this thin subset — so a FULL-universe earnings-authenticity verifier that does NOT need
   CFO is itself alpha (the W4-03 "coverage is alpha" lesson). This is the design north-star of the lane.

---

## C. Buildability verdicts for EVERY candidate mechanism in the brief

| Mechanism (brief) | Verdict | Reason |
|---|---|---|
| DSO (receivables/revenue) LEVEL & TREND | **BLOCKED-BY-MISSING-METRIC** | no receivables/debtors line |
| Unbilled / contract-asset growth vs revenue | **BLOCKED-BY-MISSING-METRIC** | no unbilled/contract-asset line (would only exist for IT/EPC anyway) |
| Revenue-booked-ahead-of-cash (Δrecv-growth ≫ Δrev-growth) | **PARTIAL → W4F-03** | no receivables; only the coarse `other assets`-vs-sales proxy is buildable |
| Pro-rata vs bullet recognition proxy | **BLOCKED-BY-MISSING-METRIC** | needs deferred-revenue / order-book split — absent |
| Total-accrual SIGN/TREND persistence (vs Sloan level) | **BUILDABLE (thin) → W4F-04** | NI−CFO computable only on 749-firm CF subset; sign-persistence is a distinct dimension from H022's level |
| Full-universe accrual authenticity, CFO-free | **BUILDABLE → W4F-02** | clean-surplus / reserves-reconciliation is the equity-channel substitute; full 4,599-symbol coverage |
| Capitalization-of-expenses via rising INTANGIBLES + flat revenue | **BLOCKED-BY-MISSING-METRIC** | no intangibles line |
| Capitalization-of-expenses via rising CWIP + flat revenue | **BUILDABLE but SKIP** | overlaps W4-02 (CWIP-commissioning) materially — a CWIP-dynamics variant, not a distinct mechanism; folded into W4-02, not given a new ID |
| Depreciation-policy laxity (declining dep-rate w/o capex justification) | **BUILDABLE (proxy) → W4F-01** | dep + net fixed assets + cwip present; net-block proxy (no gross block) — caveat carried as the refinement |
| Interest-coverage DETERIORATION TREND | **BUILDABLE → W4F-05** | operating profit + interest full-universe; no static coverage leg exists in QUALITY §3 (only net-debt/EBITDA trend) so this is a distinct axis |
| Effective-tax-rate anomaly (LEVEL / linear TREND) | **ALREADY-COVERED — SKIP** | = W4-03 (3-FY median tax%, refinement Δtax trend). Do not re-propose. |
| Effective-tax-rate VOLATILITY (2nd moment) | **BUILDABLE → W4F-06** | W4-03 uses level+trend only (verified at HYPOTHESES_W4 L40-43); dispersion of ETR is a genuinely distinct moment |
| Other-income dependence | **ALREADY-COVERED — SKIP** | = W4-04 (OI/PBT level + ΔOI_share). Do not re-propose. |
| CCC-deterioration trend + WC-to-sales creep | **BLOCKED-BY-MISSING-METRIC** | no receivables/inventory/payables/current-split; the only proxy (`other assets`−`other liabilities` vs sales) is captured coarsely by W4F-03 already — a separate CCC leg would be a cosmetic variant, so skipped |

Net: **6 BUILDABLE new signals (W4F-01..06), 6 blocked families, 3 already-covered/overlap skips.**

---

## D. The 6 surviving candidates (exact construction)

Conventions for all: annual (FY) frequency; **PIT join = merge_asof backward on `available_date`** onto the rebalance
date (never fiscal_year / period_label / quarter-end); all cross-sectional scores are peer-set z-scores /rank-pcts within
sub-sector×size bucket (same peer convention as `MODEL_SPEC.md` §composite); ratios winsorized at the **1/99 pct**
cross-sectionally per date before z-scoring; financials (sector = Banks/NBFC/Insurance) **excluded** from every leg
(their BS format is the `revenue`/`financing profit` schema, 94 names). All signs framed so **higher score = worse =
expected NEGATIVE forward return** (penalty framing).

### W4F-01 — Depreciation-policy laxity (under-depreciation proxy) — priority **H**, sign **−**
- **Construction:** `dep_rate_t = depreciation_t / (0.5·(fixed_assets_t + fixed_assets_{t-1}) + 0.5·(cwip_t+cwip_{t-1}))`.
  Signal = **negative 3-FY slope of dep_rate** (declining dep-rate) **AND** gross fixed-asset base NOT shrinking
  (`fixed_assets_t + cwip_t ≥ fixed_assets_{t-3} + cwip_{t-3}`). Laxity score = z_cs(−slope) gated to fire only when
  the base is flat/growing. Higher = more aggressive under-depreciation.
- **metrics_used:** depreciation, fixed assets, cwip.
- **Why buildable / caveat:** `fixed assets` is NET block (no gross block, no accumulated depreciation on disk) — the
  denominator is imperfect, so the signal is the WITHIN-FIRM TREND (z-scored), not the cross-firm level. [DATA: no gross-block metric_norm]

### W4F-02 — Clean-surplus / reserves-reconciliation (phantom-earnings) — priority **H**, sign **−**
- **Construction:** over a rolling N=4 FY window, `gap = Σ net_profit − ΔReserves`, normalized:
  `gap_ratio = (Σ net_profit − (reserves_t − reserves_{t-4})) / Σ|net_profit|`, winsorized. A large POSITIVE gap =
  reported profits that never became book equity (write-offs, prior-period adjustments, restatements, off-P&L equity
  leakage). Extreme-leakage flag (full-universe, dividend-robust): fires hard when `ΔReserves < 0` while
  `Σ net_profit > 0`. Score = z_cs(gap_ratio).
- **metrics_used:** net profit, reserves (optional dividend payout % to de-confound on the 749-firm subset).
- **Why buildable:** net profit (49,352) + reserves (49,277) both FULL universe — the EQUITY-channel twin of the
  cash-channel CFO/PAT survivor, at 6× its coverage. [DATA]

### W4F-03 — Asset-buildup vs sales divergence (revenue-recognition proxy) — priority **M**, sign **−**
- **Construction:** `g_oa = other_assets_t/other_assets_{t-1} − 1`; `g_sales = sales_t/sales_{t-1} − 1`.
  Signal = z_cs(g_oa − g_sales) using 2-FY-smoothed growths (average of last 2 FY to damp lumpiness). High = balance
  sheet (which contains receivables+inventory) inflating faster than the P&L it supposedly generates — the classic
  too-soon-revenue / channel-stuffing tell. Operationalizes catalog §8 "receivables/inventory growth vs revenue" which
  is otherwise NOT buildable (no receivables line).
- **metrics_used:** other assets, sales.
- **Why buildable / caveat:** `other assets` lumps receivables+inventory+cash+loans&advances — COARSE proxy; this is the
  weakest-orthogonality candidate (shares an axis with the asset-growth leg) and MUST be gated vs asset-growth. [DATA]

### W4F-04 — Accrual sign-persistence (CF subset) — priority **M**, sign **−**
- **Construction:** `accrual_t = net_profit_t − CFO_t`. Signal = **count of last 4 FY with accrual_t > 0** (0–4);
  a firm posting positive accruals every year (earnings persistently above cash) is the persistence-of-accruals red flag.
  Distinct from Sloan H022 which scores the LEVEL of the latest accrual, not its multi-year sign consistency.
- **metrics_used:** net profit, cash from operating activity.
- **Why buildable / caveat:** CFO only on 749 symbols (16%) — this is a THIN-coverage gate item, and it must be gated
  vs both CFO/PAT (survivor) and H022 (kill if corr > 0.6) since it reuses the NI−CFO accrual definition. [DATA]

### W4F-05 — Interest-coverage deterioration trend — priority **M**, sign **−**
- **Construction:** `cover_t = operating_profit_t / max(interest_t, ε)`. Signal = z_cs(−3-FY slope of cover_t),
  with a hard escalation when cover crosses below 2.0× within the window. Deteriorating coverage = rising financing
  stress that hits reported PAT and solvency before the leverage LEVEL screens catch it.
- **metrics_used:** operating profit, interest.
- **Why buildable:** both FULL universe; QUALITY §3 has net-debt/EBITDA trend but NO interest-coverage axis, so distinct. [DATA]

### W4F-06 — Effective-tax-rate volatility — priority **L**, sign **−**
- **Construction:** `tax_vol = std(tax%_t over last 5 FY)` (or CV), winsorized to tax% ∈ [0,45]. Signal = z_cs(tax_vol).
  Erratic ETR unrelated to statutory changes = opportunistic tax positioning / deferred-tax games / earnings smoothed
  through the tax line. DISTINCT from W4-03 which uses the 3-FY median (level) + Δtax linear trend — this is the
  dispersion (2nd moment), verified against W4-03's construction text (HYPOTHESES_W4 L40-43). [DATA]
- **metrics_used:** tax %.
- **Caveat:** thinnest edge in the lane; gate vs W4-03 (kill if corr > 0.6).

---

## E. Orthogonality vs the frozen 7-leg composite (all [INFERENCE] — no corr computed)

7 legs (FINAL_MODEL.md §1): **EY, QMJ, PLAIN 12-1 momentum, MA-65 slope, net-share-issuance(−), asset-growth(−), CFO/PAT.**

| Signal | Least-correlated leg (my judgment) | Why |
|---|---|---|
| W4F-01 dep-laxity | momentum / EY | dep-policy is a non-price, non-valuation accounting-choice axis no leg touches; mild link to asset-growth via the FA base only |
| W4F-02 clean-surplus | CFO/PAT (the incumbent forensic leg) | CFO/PAT is the CASH channel; this is the EQUITY channel — different leakage path, and 6× coverage where CFO/PAT is silent |
| W4F-03 asset-buildup-vs-sales | EY / momentum | it's a ratio-of-growths, not a level or price; **weakest** claim — genuinely correlated with asset-growth(−), must gate |
| W4F-04 accrual-persistence | momentum / EY | persistence dimension; **overlaps CFO/PAT & H022 by construction** — gate hard |
| W4F-05 interest-coverage-deterioration | EY / momentum | no leg carries a coverage/solvency-trend axis; net-issuance & asset-growth are financing/investing levels, not coverage slope |
| W4F-06 tax-vol | CFO/PAT / QMJ | ETR dispersion is orthogonal to profitability level and cash conversion |

---

## F. Assembly (a) — improved FORENSIC PENALTY / GATE leg

Consistent with `02_SCORING_ENGINE.md` Step 6 / catalog §8: **nonlinear, non-additive**
`penalty = severity × size_mult(cap) × regime_mult(credit/valuation/trend)`.

- **Severity inputs (each a 0–1 flag from its z-score, higher=worse):** W4F-01, W4F-02, W4F-03, W4F-05
  (all FULL-universe); W4F-04 and W4F-06 enter only where covered, else omitted (no silent imputation — CATALOG lesson 16).
- **Non-additive rule:** `severity = max(flags) + 0.5·(second-highest flag)` — a single strong flag penalizes; TWO
  co-firing flags (e.g. clean-surplus gap AND asset-buildup, i.e. profits neither in cash-adjacent assets nor in equity)
  ESCALATE super-linearly (confirmation), but three weak flags do NOT sum into a false alarm. This mirrors the existing
  gate's "severity × mult" shape rather than a linear factor add.
- **size_mult:** heavier for micro/small (forensic base rates rise as cap falls — catalog §8 microcap weighting).
- **regime_mult:** heavier in tight-credit / high-valuation regimes (W4F-05 especially — coverage stress bites in credit crunches).
- **Relationship to incumbents:** this penalty leg SITS ALONGSIDE the CFO/PAT alpha leg as a GATE, not a replacement.
  CFO/PAT stays the additive forensic-quality alpha leg; W4F-01/02/03/05 form the nonlinear DOWNSIDE gate.

## Assembly (b) — standalone EARNINGS-QUALITY long-short sleeve?

**Honest verdict: NO candidate qualifies for a standalone L/S sleeve today.** [OPINION grounded in the firm's own bar]
Reason: the incumbent CFO/PAT leg (IC_IR 1.14, 1Y) already occupies the "forensic-quality alpha" slot and cleared the
INCREMENTAL bar vs accruals/cash-conversion. Firm rule (IC-1 lesson, CONSOLIDATION) is that a new signal must beat what's
there on the incremental-shuffle bar BEFORE it earns a sleeve — and none of W4F-01..06 has a tested sign yet. The ONE
signal worth a full tester specifically to see if it earns a sleeve is **W4F-02 (clean-surplus)**, purely because its
equity-channel mechanism + 6× coverage give it the only credible *orthogonal-alpha* (not just gate-item) argument vs the
incumbent. Everything else is gate material. Do not build a sleeve on any of these on in-sample shine.

## Tester needs — which need a full `panel_long` run vs gate-only

| Signal | Needs alpha tester (sign unknown / possible sleeve) | Gate-only (correctness test only, sign obvious) |
|---|---|---|
| W4F-01 dep-laxity | YES — sign & cross-sectional behaviour industry-varying | — |
| W4F-02 clean-surplus | YES — the one true sleeve candidate | — |
| W4F-03 asset-buildup-vs-sales | YES — coarse proxy, sign must be verified + gated vs asset-growth | — |
| W4F-04 accrual-persistence | YES (on the 749-firm CF subset) + corr gate vs CFO/PAT & H022 | — |
| W4F-05 interest-coverage-deterioration | — | GATE-ONLY: deterioration→bad is a priori; only needs correctness test |
| W4F-06 tax-vol | — | GATE-ONLY: dispersion→bad is a priori; corr gate vs W4-03 |

---

## G. DATA-ASSET R&D SCAN (untapped, no-overfit directions; checked vs IDEAS_GLOBAL / ROADMAP / SCOUT / W4 batch)

- **Triangulated earnings authenticity (cash × equity × tax):** we already verify earnings via CASH (CFO/PAT survivor,
  749 firms) and TAX (W4-03). The EQUITY channel (clean-surplus, W4F-02) is the missing third leg — a *program* that
  requires ALL THREE to agree could be a far stronger, coverage-broad authenticity composite than any single verifier.
  Not queued anywhere. [INFERENCE]
- **PBT-bridge decomposition ("quality of PBT"):** PBT = operating profit + other income − interest − depreciation is
  fully reconstructable on the full universe. W4-04 only takes the OI share; nobody has decomposed the full bridge to
  score how much of headline PBT growth is CORE-operating vs below-the-line, or the *persistence* of core-op-profit
  growth vs headline growth. Untapped, distinct from every leg. [INFERENCE]
- **Margin-structure stability (opm% 2nd moment) as a moat-durability factor:** opm% has 45,655 rows / 4,493 symbols
  back to 2004. QMJ uses margin LEVEL; the WITHIN-FIRM stability of gross/operating margin (low variance = pricing
  power) is untested. CAUTION: raw earnings-*variance* stability INVERTED in the junk-bull (CONSOLIDATION) — so test
  only as a rank-averaged quality sub-leg, never standalone. [DATA coverage + INFERENCE]
- **Long-history profitability mean-reversion (5Y):** 20+ years of net profit + total assets → ROA/ROCE for 4,599 firms.
  The Fama-French/Novy-Marx profitability LEVEL is in QMJ, but the 5–10-yr REVERSION dynamic (extreme-high ROA reverts,
  extreme-low recovers) is a distinct long-horizon axis untested here. Distinct from asset-growth. [INFERENCE]
- **Directional growth-streak count (Piotroski-style), NOT variance:** consecutive-FY count of positive sales AND
  net-profit growth, using the 21-yr series. Frames growth-consistency as an improvement STREAK (Piotroski) rather than
  low variance (which inverted) — a genuinely different construction from the killed earn-stability leg. [DATA + INFERENCE]

---
*All numbers in §B are [DATA] from my own enumeration script; §E orthogonality and §G directions are [INFERENCE]. No
tester has been run — no sign is trusted until a `panel_long` incremental-shuffle run clears it.*
