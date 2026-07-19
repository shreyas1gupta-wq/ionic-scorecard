# EDGE-CASE PLAYBOOK — sector/business-model conditional reinterpretation of ALPHA_RANKER scores

**Owner:** equity-head-ananya-iyer. **Status:** v1.0, 2026-07-17. **Consumed by:** the per-stock analyst-agent
(`CONTEXT_VERDICT_FRAMEWORK.md`), sector analysts on deep-dives, fm-fundamental-sanjay-kulkarni (forensic-gated
entries).

Every row below follows the same discipline as `rnd/forensic/FORENSIC_FRAMEWORK_CA.md`'s own closing line: **"no
hard cutoffs are self-executing."** A score is a lead. This playbook says which leads mislead by default, in
which business-model context, and what to check before believing them.

---

## 1. Capex-heavy infra build-out (solar/power EPC-IPP, roads/EPC, data-centre/warehousing REIT-adjacent, new
capacity in cement/steel/chemicals)

| Score that fires | Why it fires | Default read (context-blind) | Reinterpretation |
|---|---|---|---|
| `bs_asset_growth` very negative (high raw asset growth) | Balance sheet growing faster than the universe median every fiscal year during build-out | "Over-investing / value-destroying growth" (academic asset-growth anomaly prior) | **NORMAL AND NECESSARY** if the growth funds identified, committed capacity (order book / PPA / roof-top pipeline) with a visible commissioning trail. [OPINION: sector convention] |
| `bs_issuance` negative / high incidence | QIP, rights issue, warrants, debt raise to fund capex | "Dilution destroying per-share value" | **EXPECTED FUNDING MIX** for a capital-intensive scale-up that cannot self-fund from CFO in year 1-5. Judge PRICE and DILUTION RATE (was it done near cyclical lows to a promoter/related party at a discount = PT-04 flag) vs market-price QIP to diversified institutions (normal). |
| `quality_cfo_pat` < 1 / CFO-PAT divergence flag | Revenue booked (Ind AS 115 percentage-of-completion for EPC) ahead of cash collection; commissioned-but-not-yet-billed capacity | "Earnings quality problem / possible channel stuffing" | **STRUCTURALLY NORMAL for EPC/project business** in the ramp years; CFO catches up 1-2 years after commissioning as receivables convert. Check trend, not level — persistent (5yr+) divergence with NO improving trend is the real flag (this is exactly forensic RP-flag "cfo_pat_divergence_multiyear" in the live scorer). |
| Beneish `SGI` (sales growth index) flag | High revenue growth vs peers | "Manipulation-prone growth" (Beneish M-score was built on a US mature-company prior) | Beneish's SGI is **mechanically miscalibrated for any high-growth small-cap**, not just capex names — flag the METHOD limitation, don't apply the raw penalty at full weight. |
| Low current-period free cash flow / negative FCF | Capex > CFO | "Cash-burning business" | Normal for years 1-N of a build-out; the real test is **project-level ROIC/IRR once assets season (2-3yr post-commissioning)**, not consolidated FCF during the build phase. |

**What does NOT get a pass here:** CWIP that never converts to gross block on schedule (PT-03), CWIP invoiced
through a related-party EPC/equipment vendor, revenue growth with NO matching order-book/capacity disclosure,
promoter pledge rising alongside the raise. These distinguish legitimate build-out from siphoning — see §3 below.

## 2. Turnaround (loss → profit)

| Score that fires | Why it fires | Default read | Reinterpretation |
|---|---|---|---|
| Extreme YoY EPS/PAT growth (division by a small/negative base) | Mechanical — going from -1 to +1 crore PAT is "+200%" | Momentum/quality legs may score it as a strong quality inflection when it is really base-effect noise | Check **absolute PAT/margin level**, not just the growth rate; require 2-3 consecutive profitable quarters before trusting the growth-rate leg. |
| `quality_QMJ` / profitability composites unstable or negative history | Multi-year losses drag trailing quality averages | "Poor quality business, avoid" | May be exactly WRONG for a name past its trough if the loss-making years were driven by a ONE-TIME/identifiable cause (deleveraging post-restructuring, one plant idled, commodity-cost trough) now resolved. Trailing-average legs are backward-looking by construction and are the single worst-suited leg family for turnarounds. |
| Low `value_EY` improving fast | Price re-rating ahead of full earnings normalization | Value leg may look "expensive already" | Check **normalized/mid-cycle earnings power**, not trailing EY — turnarounds are value traps for a naive trailing-multiple read precisely because the E hasn't normalized yet. |
| High debt/interest-cover flags | Legacy balance sheet from the loss period | "Distress" | Verify the debt-reduction TRAJECTORY (is leverage falling post-turnaround?) rather than the static level, which is a lagging artifact of the pre-turnaround period. |

## 3. Cyclical trough (commodity, capital goods, real estate at bottom of cycle)

| Score that fires | Why it fires | Default read | Reinterpretation |
|---|---|---|---|
| Low/negative earnings, `value_EY` near zero or negative | Trough-year earnings depress the E | "Not cheap / value trap" | Cyclicals are structurally MISPRICED by trailing-E value legs at BOTH extremes — cheapest-looking (low PE) at the cycle TOP (peak E, about to fall) and most-expensive-looking (high/negative PE) at the cycle BOTTOM (trough E, about to recover). A trailing-PE/EY leg reads the trough as "expensive" exactly when it is cheapest on normalized earnings. |
| Momentum legs weak/negative | Price has been falling with the cycle | "Avoid — negative trend" | Correct signal to respect for TIMING (don't fight the trend), but should not be read as a fundamental quality verdict — cyclical troughs are a genuine "wait for trend confirmation" case, not a "fundamentals are broken" case. |
| High leverage/interest-cover flags | Cyclical revenue trough vs fixed debt | "Distress risk" | Legitimate risk to size for (this is real, not an artifact) — but check whether debt is against LONG-LIFE assets with a multi-cycle track record of surviving prior troughs (steel/cement/capital-goods incumbents) vs a first-cycle balance sheet with no survival precedent. |

## 4. High-growth, dilutive (new-age/internet, high-growth pharma-CDMO capacity adds, consumer-brand scale-up)

| Score that fires | Why it fires | Default read | Reinterpretation |
|---|---|---|---|
| `bs_issuance` negative (ESOP-heavy + primary raises) | New-age listings routinely issue ESOPs and primary capital | "Heavy dilution flag" | Distinguish ESOP-driven (non-cash, but real per-share dilution — still count it) from CASH primary raises for growth capital (funds a real ramp) vs raises to plug OPERATING losses (the latter is the genuine red flag — growth capital funding capacity is different from growth capital funding a structurally negative unit economics business). |
| Negative CFO / negative `quality_cfo_pat` | Path-to-profitability businesses burn cash pre-scale | "Poor earnings quality" | Check **contribution-margin trend and cohort/unit economics**, not consolidated CFO — the right question is "does unit economics improve with scale" (data usually filing-read-only, not in MASTER_fundamentals_pit), not "is CFO positive today." |
| High `value_dcf_revgap` / rich multiples | Priced for a long growth runway | "Expensive, low margin of safety" | Correct as far as it goes — this is the ONE leg family where the raw signal should be taken closer to face value; high-growth-dilutive names are exactly where valuation-context matters most and margin-of-safety should not be waived. |

## 5. Financials (banks/NBFC/insurance/AMC/capital markets)

| Score that fires | Why it fires | Default read | Reinterpretation |
|---|---|---|---|
| Low `value_EY` implied PE looks HIGH is actually the wrong read here — flip: **low PE/EY is systematically NORMAL** | Banks/NBFCs trade on P/B and RoE, not P/E, and carry structurally low absolute earnings yields for high-quality franchises (data confirms: Financial Services sector `value_EY` median 0.041 -> ~24x implied, but this ratio is not the right lens at all) | Applying a generic "cheap = good" value screen | **The whole value_EY/PE leg is close to meaningless for BFSI** — the balance sheet IS the product (leverage is the business, not a risk flag), CFO/PAT is structurally not comparable (deposit-taking/lending flows dominate operating cash flow), and asset growth = loan-book growth = the entire investment thesis, not a red flag. Use P/B vs RoE, NIM trend, credit-cost trend, provisioning coverage instead — legs built for non-financials should be DOWN-WEIGHTED OR EXCLUDED entirely, not reinterpreted. |
| `quality_cfo_pat` flag (Financial Services sector median 0.57, well below industrial norms ~1.0-1.6) | CF-statement structure for lenders nets financing/operating flows differently | "Poor cash conversion" | Not a comparable metric across a bank/NBFC vs an industrial; ignore this leg for BFSI names, do not down-rate. |
| `bs_asset_growth` fires | Loan book growth | "Overinvestment risk" | **Loan growth = revenue growth** for a lender; only reinterpret as risk if growth is OUTPACING deposit/liability growth (funding-mismatch) or asset QUALITY metrics (GNPA/NNPA, restructured book) are deteriorating alongside it — those are the real financials-specific forensic checks, not the generic asset-growth leg. |

## 6. Holding company (promoter holdcos, conglomerate parents, investment-company structures)

| Score that fires | Why it fires | Default read | Reinterpretation |
|---|---|---|---|
| Every fundamental leg on STANDALONE financials (revenue, margin, growth legs near-zero/meaningless) | Holdco standalone P&L is mostly dividend/other income from subsidiaries, not an operating business | "No revenue growth / no margin / doesn't screen" | **Wrong statement to score entirely.** The investable economics are in NAV of the underlying stakes minus holdco discount, not standalone P&L legs. Fundamental legs computed off standalone financials for a pure holdco are a CATEGORY ERROR, not a contextualizable flag — flag for **manual SOTP (sum-of-the-parts) valuation**, do not trust the automated composite score at all for these names. |
| `other_income_dependence` (EQ-03) flags heavily | Dividend/interest from subsidiaries IS the P&L | "Low-quality earnings, over-reliant on other income" | For a genuine holdco this is BY DESIGN, not a red flag — the EQ-03 flag was built for an OPERATING company hiding a weak core business behind other income; misapplied to a holdco it fires on the entire business model. Check the CO-04 (consolidation-scope) angle instead: is the holdco used to keep debt/related-party exposure OFF the listed operating entity's books (legitimate concern) vs simply being a clean pass-through holding structure (no concern)? |
| Related-party transaction flags (RP-01/RP-04) elevated | Intra-group service/royalty/loan agreements are structurally more frequent in a group holdco | "RPT red flag" | Still a REAL flag to check (this is where RP-flags matter MOST, not least) — but the base rate of RPT volume is naturally higher for a holdco/group-parent, so the SECTOR-CONDITIONAL bar for "how much RPT is normal" must be set higher before treating volume alone as anomalous; price/terms non-arm's-length is still the same hard-veto test as anywhere else. |

---

## Cross-cutting rule

For every row above, the reinterpretation is a **downgrade of the SCORE'S authority, never an upgrade of the
UNDERLYING FACT'S benefit of the doubt**. "Normal for the sector" converts a HARD-VETO-shaped automated flag into
an **INVESTIGATE flag** (go verify against the actual mechanism — order book, CWIP ageing, RPT vendor identity,
consolidation notes) — it never converts it into a clean pass on the composite score alone. See
`CONTEXT_VERDICT_FRAMEWORK.md` §4 for the productive-capex-vs-siphoning test that operationalizes this for the
single most common edge case (capex-heavy build-out) and §5 for the analyst-agent decision logic that applies
this uniformly.
