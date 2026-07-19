# ANALYST-AGENT CONTEXTUALIZATION LAYER — CONTEXT_VERDICT_FRAMEWORK

**Owner:** equity-head-ananya-iyer (E-003). **Status:** v1.0, built 2026-07-17. **Principal principle this
operationalizes:** raw relative/absolute/forensic scores from ALPHA_RANKER are SIGNALS / flags-to-investigate,
**not verdicts**. Interpretation is sector- and business-model-conditional. This layer sits between the scoring
engine (`02_SCORING_ENGINE.md`, `rnd/panel/canonical_7leg_scores.parquet`, `results/universe_forensic_score.parquet`)
and any human- or agent-facing verdict, so the system never emits a bogus "-90, sell" out of a mechanical score
that was never sector-conditioned.

**Inputs wired together:**
- `rnd/panel/canonical_7leg_scores.parquet` (98,465 rows) + `rnd/panel/capstone_legs.parquet` (1,310,958 rows,
  12 legs) — the composite + component scores.
- `results/universe_forensic_score.parquet` (751 names, 0-100 badness scale) + `results/universe_forensic_flags.parquet`
  (14,269 flag-level rows) — the live forensic scorer.
- `rnd/forensic/FORENSIC_FRAMEWORK_CA.md` (32-item CA-grade red-flag taxonomy, tiered HARD-VETO/HEAVY-PENALTY/
  WATCH-FLAG) + `rnd/forensic/FRAUD_CASE_LIBRARY.md` (15 named Indian cases, cross-case synthesis).
- `rnd/wave4/batch_A.json` / `batch_B.json` / `batch_C.json` — 24-name business-model KB (how_it_makes_money,
  unit_economics, value_chain_position per name). **[DATA GAP, logged below]** this KB does not currently cover
  KPIGREEN or most capex-heavy small-caps; it is a KB-BUILD-OUT candidate, not yet a universe-wide input.
- `data/universe/sector_map.parquet` (2,825 symbols, macro_sector/sub_sector) + `data/fundamentals/MASTER_fundamentals_pit.parquet`
  (1,092,785 rows, PIT `available_date`) — sector-norm benchmarks computed fresh for this build (§1, `sector_norms.json`).
- `rnd/wave4/SECTOR_BIAS_AUDIT.md` — **[DATA GAP] file does not exist in the repo as of this build** (referenced
  as "running" but not found under `rnd/wave4/`; nothing in that directory matches). Treat sector-relative
  scoring conclusions in this document as a FRESH, INDEPENDENT computation (§1), not a continuation of that
  audit. Flagging to rnd-head-aditya-verma / quant-head-arjun-rao to confirm whether it was ever created or is
  still pending.

---

## §1. SECTOR-NORM BENCHMARKS [DATA]

Full detail: `sector_norms.json` (21 macro-sectors with n≥5 symbols each, two families of norms). Methodology
summary — everything below is computed from real firm data, not assumed:

**Family A — leg-based (`rnd/panel/capstone_legs.parquet`, latest obs per symbol, cross-sectional z-scores
already baked into `bs_asset_growth`/`bs_issuance`):** These two legs are **already sign-inverted** — confirmed
by cross-checking KPIGREEN's leg values (`bs_asset_growth = -3.84`, near the universe minimum of -6.15) against
its raw fundamentals (`fixed_asset_growth_yoy = +91%`, `total_asset_growth_yoy = +106%` YoY, the highest-growth
tail of the whole universe). **A very negative leg value = very high raw growth/dilution**, not low. Read sector
medians accordingly: a sector median far below the universe's ~0 mean means high raw asset-growth/dilution is
the SECTOR NORM there, and a name scoring "badly" on that leg merely for being unremarkable-for-its-sector is a
false flag.

**Family B — raw ratio-based (`data/fundamentals/MASTER_fundamentals_pit.parquet`, latest FY vs prior FY,
sector-winsorized at 2nd/98th pct):** capex intensity (CWIP/fixed-assets, fixed/total-asset YoY growth),
dilution (equity-capital face-value YoY growth — **caveat: this misses share-premium-only raises, see below**),
and CFO/PAT.

### Which sectors normalize what (medians, n≥5 symbols; full percentiles in `sector_norms.json`)

| Sector (n) | fixed-asset growth YoY (median) | CFO/PAT (median) | asset-growth leg (median, less-negative=lower raw growth) | Reads as NORMAL |
|---|---|---|---|---|
| **Power** (21) | +1.4% | **2.51x** (very high) | +0.10 | Sector median is a mature-utility/genco book (NTPC, POWERGRID, CESC, TATAPOWER etc. dominate the 21-name count) — HIGH CFO/PAT and LOW asset growth is the norm for the median member. **A fast-scaling small-cap EPC/IPP inside this sector (KPIGREEN, sub_sector "Power Infrastructure", only 3 names) will look like an outlier vs its own macro-sector median** — macro_sector is too blunt here; see §4. |
| **Construction** (n≥5) | -1.8% (median flat/negative — lumpy by project) | 0.72x (below-1, normal) | +0.27 | Low/volatile CFO/PAT is structurally normal — project billing/retention-money timing, not a red flag on its own. |
| **Capital Goods** | +7.3% | 0.84x | +0.03 | Moderate capex growth normal (order-book-driven capacity adds); CFO/PAT <1 normal given execution-cycle timing. |
| **Realty** | 0% (flat) | **0.28x (lowest of all sectors checked)** | +0.01 | Low CFO/PAT is THE sector norm (inventory-led revenue recognition, project completion method) — do not read a Realty name's low CFO/PAT as an accrual/earnings-quality flag by the same yardstick as an industrial. |
| **Financial Services** | +3.1% | 0.42x (2nd-lowest) | +0.01 | Low CFO/PAT is a CF-statement-structure artifact (financing flows dominate), not comparable cross-sector at all — see edge-case playbook §5, this whole leg family should be down-weighted for BFSI, not merely reinterpreted. Low value_EY (~24x implied PE) is ALSO the sector norm — P/B and RoE are the right lens, not P/E. |
| **Information Technology** | +9.1% | 1.13x | +0.12 | Asset-light peer group — CFO/PAT ~1 and modest capex growth is normal; **HIGH asset growth here (unlike Power/Construction) IS atypical for the sector and should NOT get the capex-heavy-sector pass.** |
| **FMCG** | +5.5% | 1.06x | +0.08 | Same logic as IT — asset-light; elevated asset growth is a genuine flag-worth-investigating, not a norm. |
| **Metals & Mining** | (winsorized, capex-cyclical) | 1.66x | +0.25 | Higher CFO/PAT reflects commodity-cycle cash generation phases; capex lumps with the cycle — check WHERE in the cycle before reading capex growth as either normal or alarming. |
| **Consumer Services** | | 1.44x | +0.04 | Asset-light platform/retail names — treat like IT/FMCG for the asset-growth read. |

**`bs_issuance` leg caveat:** its cross-sectional distribution is heavily right-clustered (most non-issuing
firm-quarters sit near +0.21-0.27) with a long negative tail for actual issuers — sector MEDIANS are therefore
nearly identical across sectors (~0.21 everywhere) and NOT discriminating. Use `bs_issuance_flagged_incidence_pct`
in `sector_norms.json` (% of names per sector with leg <-1, i.e. in the heavy-issuance tail) instead of the
median for this leg.

**Known measurement gap [DATA]:** the dilution proxy computed here (`equity_capital_growth_yoy_dilution`, from
`MASTER_fundamentals_pit`'s `equity capital` face-value line) under-measures true dilution for any raise done at
a premium (QIP/rights issue with premium — the face-value line barely moves while share count and share-premium
reserve do). KPIGREEN's own raw dilution proxy reads only +1.0% YoY despite a documented FY24-25 capital raise
program — **do not trust this specific raw metric at face value; cross-check actual share-count change from the
price/corporate-actions data or a filing read before concluding "dilution is low."**

---

## §2. EDGE-CASE PLAYBOOK

Full detail with per-leg tables: `edge_case_playbook.md`. Six business-model contexts covered, one row per
misleading score:

1. **Capex-heavy infra build-out** (solar/power EPC-IPP, roads-EPC, capacity adds in cement/steel/chemicals) —
   asset-growth, issuance, CFO/PAT-divergence, and Beneish SGI legs all mechanically fire and are ALL normal in
   the build phase; the flags that still matter are CWIP-ageing/never-capitalizing (PT-03) and related-party
   EPC-vendor identity.
2. **Turnaround (loss→profit)** — trailing-quality legs and trailing-EY are backward-looking by construction and
   are the worst-suited leg family for a name past its trough; check absolute PAT level and normalized earnings,
   not the trailing growth-rate/multiple.
3. **Cyclical trough** — trailing-E-based value legs misread the trough as "expensive" exactly when normalized
   earnings say it's cheapest; momentum-weak legs are a legitimate timing signal, not a fundamentals verdict.
4. **High-growth, dilutive** (new-age/internet, CDMO capacity, consumer-brand scale-up) — distinguish ESOP/growth-
   capital dilution (normal) from cash raises plugging a structurally negative unit economics (real flag); this
   is the ONE context where the rich-valuation leg should be taken closer to face value, not softened.
5. **Financials** (banks/NBFC/insurance/AMC) — value_EY/PE and CFO/PAT legs are close to meaningless for BFSI
   (balance-sheet-is-the-business); down-weight/exclude rather than reinterpret; use P/B-vs-RoE, NIM, credit-cost
   instead.
6. **Holding company** — standalone-financials-based fundamental legs are a CATEGORY ERROR (not a contextualizable
   flag) for a pure holdco; route to manual SOTP valuation, and raise (not lower) the RPT-scrutiny bar given the
   naturally higher base-rate of intra-group transactions.

---

## §3. PRODUCTIVE-CAPEX vs SIPHONING distinguisher

The single most common false-positive in the whole system: **high asset-growth + high dilution + low CFO** fires
identically whether a company is (a) building a legitimate, revenue-generating asset base or (b) using "capex" as
a cash-extraction mechanism. `FORENSIC_FRAMEWORK_CA.md`'s own PT-03 item is written for exactly this — "capex
gold-plating / CWIP that never capitalizes" — and its own severity note is explicit: *PARTIAL DATA-SCREENABLE...
treat every 'PARTIAL' tag as a lead for the analyst-agent's filing read, never as a stand-alone verdict.*

| Check | Legit infra / productive capex | Siphoning (PT-03 / RP-01 pattern) |
|---|---|---|
| **Revenue ramp** | Revenue/order-book grows in the 1-3 years FOLLOWING the capex spend, roughly tracking capacity added | Capex balloons with no matching revenue/order-book growth over multiple years |
| **CWIP → gross block commissioning** | CWIP converts to fixed/gross block on a disclosed schedule (Schedule III 2021 CWIP-ageing table shows most CWIP <2yr old, "completion overdue" bucket near zero) | CWIP ages past its own stated commissioning date (2yr/3yr+/overdue buckets grow), or converts at a fraction of the amount invoiced |
| **ROIC/ROCE trajectory** | Post-commissioning ROIC/ROCE on the new asset base rises toward or above cost of capital within a normal gestation window for the sub-sector | ROIC stays structurally depressed indefinitely even as "commissioned" capacity is reported |
| **Order book / PPA / contracted pipeline** | A specific, disclosed, bankable pipeline (signed PPAs for a solar IPP, an executable order book for an EPC/road contractor) sized consistently with the capex run-rate | Capex without a matching disclosed pipeline, or a pipeline that keeps slipping/getting re-announced without conversion |
| **Vendor identity on the capex spend** | Capex placed with third-party, arm's-length EPC/equipment vendors (or transparently disclosed captive-manufacturing vendors at market pricing) | Capex routed through related-party/promoter-linked EPC or equipment-supply entities (RP-01/PT-01 co-firing — the framework's own "non-additive escalation to HARD-VETO" rule) |
| **Funding-to-use trace** | Raise proceeds traceable to specific, named capex/project use in the following 1-2 quarters' cash-flow/AR disclosures | Raise proceeds parked in "other investments"/ICDs to group entities instead of the stated capex use (PT-01/PT-02) |
| **Promoter pledge** | Promoter pledge flat/declining through the build-out (skin in the game rising, not being levered against) | Promoter pledge rising alongside the capex/dilution story (AG-09) |

This is the operational core of §4's KPI Green worked example below, and it is what the analyst-agent's
INVESTIGATE-flag output (§5) routes an analyst to check — none of these seven checks are computable purely from
`MASTER_fundamentals_pit`; they require the filing/AR read the forensic framework itself flags as "FILING-READ-ONLY."

---

## §4. WORKED EXAMPLE — KPI GREEN (KPIGREEN)

### Raw, context-blind picture [DATA]
- `results/universe_forensic_score.parquet`: **forensic_risk_score_0_100 = 36.0** (universe mean 24.7, universe
  p75 34.6 — KPIGREEN sits at roughly the universe's 75th-80th percentile of forensic risk, i.e. "elevated," not
  extreme, and **not** anywhere close to a -90/worst-decile verdict on the live scorer as it actually runs today).
- Within its OWN macro-sector (Power, n=21), KPIGREEN's 36.0 sits exactly at that sector's own 75th percentile
  (Power sector p75 = 36.0, sector mean 26.5) — so it is elevated even sector-relative, not merely universe-relative.
- Flag-level detail (`results/universe_forensic_flags.parquet`, all 19 tracked flags, 14 computed / 5
  insufficient-data): the flags actually firing are `cfo_pat_divergence_multiyear` (badness 0.76/1.0),
  `cash_conversion_cfo_op` (badness 1.0/1.0, maxed), `debt_to_ebitda_trend` (2.62x→5.42x YoY, badness 1.0/1.0,
  maxed), `SGI_sales_growth_index` (badness 0.92/1.0, Beneish high-growth flag). Mitigants already visible in
  the SAME flag table: `interest_cover_trend` is actually IMPROVING (+1.35x over 3yr, badness only 0.24),
  promoter holding is stable-to-rising (49.49%, +0.71pp YoY, badness 0.0), and pledge data is simply missing
  (insufficient-data, not a confirmed flag).
- Raw fundamentals (`MASTER_fundamentals_pit`, latest FY): `fixed_asset_growth_yoy = +91%`, `total_asset_growth_yoy
  = +106%`, `cwip_to_fixed_assets = 20.4%`, `cfo_to_pat_raw = 0.83` (CFO running at 83% of PAT — a REAL but not
  extreme gap), `equity_capital_growth_yoy (face value) = +1.0%` (likely understates true dilution, see §1 caveat).
- Leg-based: `bs_asset_growth = -3.84` (near-universe-minimum, i.e. among the highest raw asset-growth names in
  the whole panel), `bs_issuance = -1.60` (in the heavy-issuance tail), `quality_cfo_pat = 0.58` (below-average
  cash conversion), `value_EY = 0.038` (≈26x implied PE — not cheap, not extreme for a growth name).

### Does a hypothetical "-90 forensic verdict" hold?

**No — and importantly, the live scorer does not actually produce -90 for this name; it produces 36/100 (moderate
elevated), so the premise itself is a useful stress-test of what a context-blind system COULD wrongly emit if a
different scoring convention or an unconditioned composite (e.g. one that stacked the asset-growth, issuance, and
CFO/PAT legs at full raw weight with no sector floor) were applied.** Walking the productive-capex-vs-siphoning
test from §3 against what's actually knowable from this data:

| §3 check | KPIGREEN read | Verdict |
|---|---|---|
| Revenue ramp | `sales_cagr_3y = 61%`, `sales_cagr_5y = 92%` (`results/universe_fundamental_factors_raw.csv`) tracking the asset build — revenue IS ramping alongside the asset base, not lagging it | **PASSES** — matches legit-infra pattern |
| ROIC trajectory | `roe_last = 17.4%`, `roce_last = 13.8%` — positive and reasonable for a scaling IPP/EPC, not depressed-indefinitely | **PASSES**, though these are CONSOLIDATED current-period figures, not a post-commissioning cohort ROIC — a true test needs asset-vintage-level IRR, which is filing-read-only |
| CWIP ageing / commissioning schedule | **NOT COMPUTABLE from `MASTER_fundamentals_pit`** (only a level ratio exists: cwip/fixed-assets = 20.4%, not an ageing bucket) — this is exactly PT-03's own documented gap: "AGEING BREAKDOWN... FILING-READ-ONLY" | **[INVESTIGATE]** — genuinely unknown from current data |
| Order book / PPA pipeline | **NOT in this data catalog at all** | **[INVESTIGATE]** — filing/company-disclosure read required |
| Related-party vendor identity on capex | **NOT in this data catalog** | **[INVESTIGATE]** — the single highest-value check left to do; this is what would flip the verdict from "contextualize" to "real fraud lead" if it came back positive |
| Promoter pledge trajectory | Data insufficient in the current run (`flags_insufficient_data` includes pledge) | **[INVESTIGATE]** — promoter holding itself is stable/rising, a mild positive, but pledge specifically is unknown |
| Funding-to-use trace | Not screenable from this dataset | **[INVESTIGATE]** |

**Contextualized verdict:** the pattern presented — high asset growth, elevated dilution incidence, CFO running
below PAT, rising gross leverage — is the SAME shape §1's sector-norm table says is structurally normal for a
scaling Power/renewables name (sector median CFO/PAT = 2.51x is actually generous for MATURE Power names; the
gap here is that KPI Green, in sub_sector "Power Infrastructure," is a young scaler, not a mature genco, so it
sits below even its own sector's typically-strong CFO/PAT — that is the one place the macro-sector norm should
make you MORE cautious, not less, since the norm-setters in "Power" are mature cash cows and KPI Green doesn't
resemble them yet). Combined with a genuine revenue ramp (61-92% CAGR) that is NOT disconnected from the asset
build, and improving (not worsening) interest cover and promoter holding, the evidence available in this data
catalog **does not support a -90/fraud verdict.** It supports: **"legitimate capital-intensive growth story,
consistent with the sector's build-out pattern — investigate capex QUALITY specifically (CWIP ageing, EPC-vendor
related-party status, order-book/PPA disclosure), do not treat the composite forensic/asset-growth/dilution
score as a sell signal on its own."** This is an **[INVESTIGATE]** verdict, not a clean pass and not a kill — see
§5 for how the agent should format that distinction.

**What PIT evidence would flip this** (in order of diagnostic power): (1) a related-party/promoter-linked entity
appearing as the EPC or module/equipment vendor in the AR related-party schedule — would immediately escalate
per the framework's own PT-03+RP-01 co-firing rule to HARD-VETO-equivalent; (2) the Schedule III CWIP-ageing
table showing a growing >2yr/"completion overdue" bucket without a commissioning trail; (3) a stalling or
declining order-book/contracted-capacity disclosure alongside continued capex and dilution (capex without a
funded destination); (4) promoter pledge appearing and rising (currently unknown, not zero — a genuine data gap,
not a clean bill of health); (5) CFO/PAT divergence WORSENING rather than following the normal 1-2yr post-
commissioning catch-up pattern.

---

## §5. PER-STOCK ANALYST-AGENT SETUP SPEC

### Inputs (per stock, per run)
1. **Scores:** latest row from `canonical_7leg_scores.parquet` (composite) + all 12 legs from `capstone_legs.parquet`
   + `universe_forensic_score.parquet` (0-100) + full flag detail from `universe_forensic_flags.parquet`.
2. **Sector norms:** this stock's `macro_sector`/`sub_sector` (from `sector_map.parquet`) looked up against
   `sector_norms.json` (§1) — both leg-based and raw-fundamental-based norm tables, plus sample-size (n) so the
   agent knows when a norm is statistically thin (n<5 → fall back to macro_sector; both thin → flag "no reliable
   norm, apply generic framework only").
3. **Business-model KB:** lookup in `rnd/wave4/batch_A/B/C.json` if the symbol is covered (24/2825 names today —
   log a KB-coverage gap for any miss, do not silently skip context) — `how_it_makes_money`, `unit_economics`,
   `value_chain_position` inform which edge-case bucket (§2) applies.
4. **Forensic framework:** the 32-item tiered checklist (`FORENSIC_FRAMEWORK_CA.md`) mapped against which flags
   actually fired for this name, each flag's data-screenability (Y/PARTIAL/N) and tier (HARD-VETO/HEAVY-PENALTY/
   WATCH-FLAG).
5. **Edge-case playbook:** `edge_case_playbook.md` — matched by detected business-model bucket (capex-heavy /
   turnaround / cyclical-trough / high-growth-dilutive / financials / holdco), else "no special context, apply
   scores at face value with the standard forensic-checklist caveats."

### Contextualize/override logic
```
1. Classify business-model bucket for the stock (KB lookup first; else macro_sector/sub_sector heuristic;
   else analyst manual tag — never leave unclassified silently).
2. For each fired score/flag:
   a. Look up sector norm (Family A leg-based + Family B raw) for this metric at this stock's macro_sector.
   b. If stock's raw value sits WITHIN the sector's normal range (~p25-p75, or below the
      flagged-incidence-pct threshold for sparse legs like bs_issuance) -> the flag is DOWNGRADED from
      "forensic/quality red flag" to "sector-normal, not diagnostic on its own."
   c. If stock's raw value is an OUTLIER even vs its own sector norm (like KPIGREEN's asset-growth/CFO-PAT vs
      the Power-sector's mature-incumbent-dominated norm) -> flag is RETAINED, tagged [INVESTIGATE], and routed
      to the edge-case playbook's specific check (CWIP ageing / RPT vendor / order-book / pledge / cohort ROIC).
   d. HARD-VETO tier items (per FORENSIC_FRAMEWORK_CA.md) are NEVER auto-downgraded by sector norms alone --
      auditor resignation, going-concern, fictitious-cash pattern etc. require the underlying fact to be
      genuinely confirmed or refuted from a filing read, full stop, regardless of sector.
3. Aggregate: if ANY item remains [INVESTIGATE] after (2), the stock's OUTPUT is an INVESTIGATE-flag, not a
   contextualized clean verdict, EVEN IF the composite numeric score looks fine -- the composite score is never
   self-executing (mirrors FORENSIC_FRAMEWORK_CA.md's own closing rule).
4. Only when ALL fired items are resolved to (b) sector-normal, or independently confirmed clean via a filing
   read, does the agent emit a CONTEXTUALIZED VERDICT with a conviction level (HIGH/MED/LOW), and even then the
   verdict must name which specific mechanism was checked and cleared -- never a bare "score contextualized, OK."
```

### Output format
- **INVESTIGATE-flag** (default state for any capex-heavy/turnaround/cyclical/holdco name with fired flags that
  the current data catalog cannot resolve, e.g. no CWIP-ageing, no RPT-vendor-identity, no order-book field):
  names the specific unresolved check(s), tags [DATA]/[INFERENCE]/[OPINION] per firm protocol, and is EXPLICITLY
  not a buy/sell/hold call — it is a "go read the filing for X" instruction to the sector analyst.
- **Contextualized verdict + conviction:** only once the specific mechanism checks in §3/edge-case tables are
  actually confirmed (via a filing read, not inferred), following the standard analyst memo format (Verdict →
  3 FOR / 3 AGAINST → forensic flags found → PIT data used → catalysts → what would change my mind).

Scores are never applied blindly under this spec: every fired flag either (i) resolves to "sector-normal, stand
down" with the sector-norm evidence cited, or (ii) stays open as a named, checkable [INVESTIGATE] item until a
human or filing-read closes it — there is no path from "score fired" directly to "verdict" without passing
through one of those two gates.

---

## Filed / distribution
This document + `sector_norms.json` + `edge_case_playbook.md` live in `ALPHA_RANKER/rnd/analyst_layer/`. Consumed
by: the per-stock analyst-agent runtime, all five sector analysts (Meera/Karan/Sneha/Rohan/Priya) on deep-dives,
fm-fundamental-sanjay-kulkarni for forensic-gated entries. Logged gaps for follow-up: `rnd/wave4/SECTOR_BIAS_AUDIT.md`
not found (confirm with rnd-head/quant-head whether it exists elsewhere or is still pending); business-model KB
covers 24/2825 symbols (KB-build-out backlog item); CWIP-ageing, RPT-vendor-identity, order-book/PPA, and
promoter-pledge fields are not in the current data catalog and remain FILING-READ-ONLY per `FORENSIC_FRAMEWORK_CA.md`'s
own data-screenability table — flagging to data-officer-kavya-reddy as candidate new-source ingestion items
(D-009 gate applies to any new source before use).
