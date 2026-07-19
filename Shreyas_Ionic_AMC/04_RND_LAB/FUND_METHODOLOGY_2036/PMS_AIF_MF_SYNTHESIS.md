# PMS/AIF/MF Industry Methodology — Consolidation + Extension
**Owner:** equity-head-ananya-iyer (E-003) · **Date:** 2026-07-18 · **Mandate:** Principal, 2026-07-18 — extend existing PMS_STUDY_20260712, cross-reference ALPHA_RANKER.
**Status:** process/methodology research. No stock picks. [DATA]/[INFERENCE]/[OPINION] tagged throughout.

---

## (a) Recap — existing 10-manager synthesis (PMS_STUDY_20260712/, not re-litigated here)

Full detail: `Shreyas_Ionic_AMC/04_RND_LAB/PMS_STUDY_20260712/SYNTHESIS.md` + 10 `notes_*.md` files (SageOne, Buoyant, Carnelian, Aequitas, Green Lantern, Bandhan Smallcap MF, Abakkus, ValueQuest, Solidarity, Marcellus). **[DATA]**

- **7 convergent rules** (3+ managers independently): ROE/ROCE floor ~15-20%, growth 10-25% CAGR, concentration (10-30 names, 3-15% position caps), low leverage, growth-adjusted valuation (PEG-style, not static low-PE), 3-5yr horizon, governance/forensic gate before the quant screen.
- **The one rule that actually separated outcomes**: a *mandatory deceleration/valuation exit trigger* — SageOne has one (25.1% CAGR/13.8yr, best-verified number in the study), Marcellus does not (11.58% since-inception CAGR vs 12.14% Nifty50 TRI = **negative alpha**, textbook quality-trap). This, not the entry screen, is flagged as the single highest-value codable rule (`SYNTHESIS.md` §3, strategy #1).
- **8 codable strategy candidates** ranked by evidence/codability/differentiation are already drafted in §4 of that file — none have been built into ALPHA_RANKER yet (checked below).
- **Honest non-codable list** (§5): primary qualitative research (plant visits, channel checks), forensic depth beyond ratios (annual_report col is corrupt in our own data), promoter/management judgment, FII/DII/buyback ownership signals (still 403 for us), CAP-duration judgment, discretionary cycle timing, top-down cash-timing calls.

**Nothing new to add here — this synthesis is thorough and self-critical. Extension work below builds on it, does not redo it.**

---

## (b) `raw/AIF_Final.xlsx` digest — IMPORTANT MISMATCH FLAG

**[DATA — verified by direct pandas read, `raw/AIF_Final.xlsx`, 8 sheets, shape/dtypes checked 2026-07-18]**

The file does **NOT** contain what the mandate description assumed (industry-level fund-count-by-strategy / AUM-growth / Category-2-vs-3 splits). I read all 8 sheets before concluding this — flagging clearly rather than force-fitting:

| Sheet | Shape | Actual content |
|---|---|---|
| Daily Data | 5152×32 | Daily NAV series, Apr-2005→2026, for: NIFTY 200 Momentum 30, Nifty Midcap Momentum 50, Nifty Smallcap Quality Momentum 100, NIFTY 200 Quality 30, NIFTY 200 Value 30, NIFTY 100 Low Vol 30, GOLDBEES, HDFC Liquid Fund(G) |
| Weightage | 5148×25 | Rotation-signal construction: 200-day MA columns (`200D, mom`, `200D, gold`), a mom-vs-gold ratio (`[MOM/G]`), 20-day averaging |
| Process | 250×70 | Monthly rebalance engine — "NAVIGATOR PRO" buy signals, next-month NAV projection, an explicit **0.5% transaction-cost assumption** ("showing good resonance with actual/mock") |
| Table 1Y / Table 3Y | 18×13 each | Rolling 1Y/3Y stats table: CAGR, Std Dev, RAR, Beta vs NIFTY 500, Correlation, **Calmar, Max Drawdown** — for "Navigator Passive" vs NIFTY 50/500/Midcap150/Smallcap100/GOLDBEES/each smart-beta index individually |
| CY Return | 14×13 | Calendar-year "Navigator Return" vs NIFTY 500 Return vs Alpha, 2013→Nov-2025 |
| 1Y/3Y Rolling(M) | 283×106 / 488×48 | Monthly-rolled rolling-window return/drawdown distributions per asset |

**What this actually is:** a private backtest/track-record workbook for a **tactical, trend-following rotation strategy** ("Navigator Passive") that switches between NIFTY smart-beta factor indices (momentum/quality/value/low-vol), Gold (GOLDBEES), and a liquid fund using ~200-day moving-average trend filters on momentum-vs-gold — i.e., a rules-based regime-switching product, not a fundamental-discretionary PMS and not industry aggregate data. **No manager/scheme name, AUM figure, or fund-count column exists anywhere in the file** — I could not identify who runs "Navigator Passive" from the file's own contents. Flagging as **unverified provenance** rather than guessing; the filename (`AIF_Final`) suggests it may be one specific AIF's own marketing/backtest deck rather than an industry census, but that is an inference, not confirmed.

**Headline numbers as computed in the file (their arithmetic, not independently re-derived by me — no lookahead/PIT audit run on this, it is someone else's spreadsheet):**
- CY Return 2013–Nov'25: Navigator CAGR-equivalent annual returns beat NIFTY 500 every single calendar year shown (13/13), average annual alpha ≈ +16pp (range +0.1pp in 2019 to +28pp in 2021).
- Table 1Y: Navigator Passive 1Y-rolling avg return 36.7%, **worst-ever 1Y return only −4.9%**, Calmar 3.55, max drawdown −10.5% — vs NIFTY 500's worst 1Y −57.1%, Calmar 0.25, max drawdown −57.1% (same number — implies the worst 1Y *is* the max drawdown window, almost certainly the 2008 GFC given the 2005 data start).
- Table 3Y: Navigator Passive never had a negative 3Y rolling window (lowest 3Y return +73.2%), Calmar 14.7, vs NIFTY 500 lowest 3Y −21.1%, Calmar 0.65.

**Read with real skepticism, not endorsement:** these are extraordinary numbers on someone's own spreadsheet with a hand-set 0.5% cost assumption and no visible slippage/circuit/liquidity treatment for the underlying smart-beta index constituents (our own landmine #7b territory) — this is exactly the profile of a backtest that has NOT been through a red-team/lookahead pass. I am reporting what the file says, not certifying it. **[INFERENCE: treat as a methodology example, not a validated result.]**

---

## (c) Quant / quantamental Indian PMS-AIF landscape — extension (light web pass, 2026-07-18)

None of the 10 existing manager notes cover a systematic/quant house — confirmed by grep (all 10 are discretionary-fundamental with forensic/governance gates, no rule-based signal engine described in any note). This is a genuine coverage gap the mandate asked me to close lightly. **[DATA, WebSearch 2026-07-18 — surface-level only, not manager-note-depth; treat as leads not verified track records]**

- **Alpha Alternatives (Elysium / "Beta++")** — explicitly markets itself as systematic/factor-based: "blending quantitative research, disciplined risk management, and a proven multi-factor model." AUM cited ~₹654 Cr for Alpha Alternatives Fund Advisors LLP. Closest India match to a genuine quant-factor PMS/AIF operator in the set searched. [pmsaifworld.com, businesstoday.in, altportfunds.com]
- **Windmill Capital** — SEBI-registered RA, "quantamental" smallcase-style thematic portfolios since 2016; explicitly data-driven portfolio construction (not a PMS/AIF wrapper — smallcase/model-portfolio distribution, different regulatory category and ticket size than PMS/AIF).
- **Renaissance Investment Managers (Pankaj Murarka)** — PMS/AIF/advisory, founded 2016 — search results did not surface an explicit "quant" or "systematic" self-description; likely fundamental/growth-style like the 10 already studied. **Not confirmed quant — do not add to the quant list without a primary-source check.**
- **Systematix** — broking/wealth group since 1985/1995 offering PMS ("Dynamic Investment" scheme etc.) — name suggests systematic but marketing material found is generic wealth-management language, no explicit quant/factor-model claim surfaced. **Not confirmed quant.**
- **ithought PMS** — factsheet exists (Dec-2025) but search did not return methodology detail; **not verified either way.**

**Net for this pass:** only **Alpha Alternatives** surfaced with an explicit, sourced "multi-factor quant model" self-description among the names checked. This is a *light* pass per the mandate (not a from-scratch manager deep-dive) — if the desk wants Alpha Alternatives added to the same rigor as the existing 10 (SEBI disclosure documents, verified track record, independent-review cross-check), that is a new, separate `notes_alpha_alternatives.md` task, not something to fabricate here.

The `raw/AIF_Final.xlsx` "Navigator Passive" workbook (§b) is, in substance, a closer real-world quant/quantamental comparable than anything found in the web pass — a rules-based, trend-filtered, smart-beta-index rotation strategy — even though its operator is unidentified.

---

## (d) Overlap vs. gap — cross-reference against `ALPHA_RANKER/rnd/scorecard/USABLE_ALPHA_INVENTORY.md`

**[DATA, both source files read in full 2026-07-18]**

| PMS/AIF-world methodology | ALPHA_RANKER equivalent | Verdict |
|---|---|---|
| ROE/ROCE floor + growth-adjusted valuation (PEG) — 6-8/10 managers | `quality_QMJ` leg + `value_EY` leg in the FROZEN 7-leg composite (A1) | **Overlap** — same economic bet (quality + value), different implementation (composite factor rank vs discrete manager funnel). |
| Concentration (10-30 names) + governance/forensic gate before scoring | Forensic red-flag layer (C2, 32-item CA taxonomy, hard-veto/penalty gate) + analyst contextualization layer (C1) | **Overlap, arguably ahead** — ALPHA_RANKER's forensic layer (751-name scored universe, 14,269 flag rows) is more systematic than any manager's disclosed process; the "governance gate before the quant screen" instinct is shared. |
| Mandatory deceleration/valuation exit trigger (the single highest-value rule SYNTHESIS.md identifies, §1/§3, codable strategy #1) | **No equivalent found in USABLE_ALPHA_INVENTORY.** The absolute scorecard's B1 (5Y earnings-inflection) is an *entry* timing signal, not an *exit*/deceleration trigger on existing holdings. | **GAP.** This is the single most concrete, evidence-backed methodology piece sitting in `PMS_STUDY_20260712` that has not been operationalized anywhere in the scorecard reset. Codable strategy #1 in the existing SYNTHESIS.md is a ready-made spec. |
| Position-size laddering on confirming conviction (Solidarity-style, 3%→5%→8%→10-15%) | No sizing-ladder concept in USABLE_ALPHA_INVENTORY (B3 is regime-level gross-exposure sizing, not name-level laddering) | **Gap**, lower priority — codability flagged as medium even in the original synthesis (proxy-only). |
| Trend-filtered smart-beta/gold rotation ("Navigator Passive", §b) — 200D MA regime switch between momentum/quality/value indices and gold/cash | **Direct conceptual overlap** with B3 (breadth-extreme regime sizing, "only act at extremes," VIX dropped) and B4 (gold/cash crisis state, "never fired, cannot be backtested" in ALPHA_RANKER's own data) | **Overlap, and a live counter-example to B4's "never fired" caveat** — the Navigator workbook claims its gold/liquid rotation *did* fire repeatably (worst 3Y never negative) rather than sitting dormant. Worth a closer look at *why* B4 shows "never triggered in 21yr" while an ostensibly similar external strategy shows frequent, profitable rotation — likely a *frequency/threshold* difference (Navigator rotates on 200D trend continuously; B4 only fires at richness≥160 or correlation-convergence tail events) rather than a contradiction, but this is exactly the kind of discrepancy a quant desk should reconcile, not wave through. |
| Sector-rotation Core/Satellite (Buoyant, codable strategy #3) | A5 sector-relative note exists (design input, not a leg) but no sector-rotation *sleeve* | **Gap**, flagged as "high differentiation" already in the original synthesis. |
| Discretionary/qualitative layers (§5 non-codable list: plant visits, promoter judgment, FII/DII ownership, real-time regulatory monitoring) | Not attempted, correctly | **Not a gap** — honestly excluded on both sides; no PIT proxy exists for either. |

**Bottom line for the FM desk:** ALPHA_RANKER's quality/value/forensic machinery is at least as systematic as anything in the 10-manager study and arguably ahead of it on the forensic-gate dimension. The **one clear, evidence-backed, ready-to-spec gap** is the **deceleration/valuation exit trigger** (codable strategy #1 in the existing synthesis) — it is fully designed, has the strongest causal evidence in the whole PMS study (SageOne vs Marcellus), uses only PIT fundamentals + OHLCV we already have, and is not present in USABLE_ALPHA_INVENTORY in any form. This is the highest-value next research item this consolidation surfaces.

---

## (e) Allocator-lens structural notes (context only — not investment advice)

**[DATA — standard, settled SEBI regulatory facts as of 2026; not independently re-verified against a primary SEBI circular this session, flagging as general market knowledge rather than freshly sourced]**

- **PMS minimum investment**: ₹50 lakh per client (SEBI-mandated since 2020, raised from ₹25 lakh). Direct ownership of underlying securities in the client's own demat — no pooling, no NAV-unit structure like a fund.
- **AIF minimum investment**: ₹1 crore per investor generally (₹25 lakh for AIF manager/sponsor employees/directors). Category III AIFs (the "hedge-fund-like" bucket — can use leverage, derivatives, complex/trading strategies) sit under this same ₹1cr floor; distinguished from Cat I/II (venture/private-credit/infra, generally closed-ended) by being open-ended and trading-oriented.
- **Fee structures**: PMS/AIF typically charge a fixed management fee (1-2.5%) plus a performance fee (typically 10-20% over a hurdle, sometimes with high-water-mark). The Abakkus note in the existing study is the sharpest evidenced example of *why this matters mechanically*: 5yr gross alpha ~5.3%/yr vs net alpha 2.83%/yr — the 2.5% fee consumed **nearly half** of the manager's real outperformance (`notes_abakkus.md`). This is a structural, quantified fee-drag finding worth carrying forward to any "should we ever wrap ALPHA_RANKER as a product" conversation.
- **Lock-ins**: PMS is generally open-ended/liquid (no SEBI-mandated lock-in, though individual schemes can set exit loads); Category III AIFs are typically structured with a defined tenure (often 3-5yr+ extension options) given the trading/leverage mandate, though this varies by scheme document and was not independently checked per-scheme in this pass.
- **What this means for "if we ever ran this as a product"**: the ₹50L/₹1cr ticket floors put both structures well above retail/MF distribution reach — the natural audience is HNI/UHNI, not the mass-market investor Xorlog is targeting (different venture, noted only to avoid conflating the two). Fee drag (Abakkus example) means any quant edge claimed on a gross backtest needs an explicit net-of-realistic-fee-and-cost translation before it means anything to an allocator — directly consistent with our own house rule of never quoting a strategy's edge pre-cost.

**Allocator-lens gaps in the existing study, flagged as data gaps (not filled here, per the "flag don't guess" instruction):**
- **AUM capacity constraints**: only Abakkus's note quantifies this explicitly (₹1,606cr smallcap sleeve creating "real execution constraints" per an independent reviewer). The other 9 notes do not appear to carry a capacity/crowding discussion — **gap**, worth a targeted follow-up read if capacity modeling matters to the desk.
- **Manager tenure/team stability**: Aequitas's founder passing (31-Dec-2025, noted in the original synthesis header) is the one team-stability event explicitly on record, and the study itself flags it as "not transferable to new management" — i.e., key-person risk is acknowledged for exactly one manager, not assessed systematically across all 10. **Gap.**
- **2018/2020/2022 stress-period drawdown behavior, name-by-name**: I did not find a structured drawdown-by-crisis-year table in the 10 notes during this pass (a keyword grep for 2018/2020/2022/drawdown matched all 10 files, but that reflects the terms appearing somewhere in each long note, not a systematic per-manager crisis-year table — I did not have budget in this pass to read all 10 notes end-to-end to confirm depth of coverage). **Flagging as a genuine open question rather than asserting the data does or doesn't exist** — a follow-up pass reading each note's stress-period section specifically would settle this cheaply.

---

## Files referenced
- `Shreyas_Ionic_AMC/04_RND_LAB/PMS_STUDY_20260712/SYNTHESIS.md` (existing, read in full)
- `Shreyas_Ionic_AMC/04_RND_LAB/PMS_STUDY_20260712/notes_*.md` (10 files, grepped/spot-read, not re-read end-to-end)
- `raw/AIF_Final.xlsx` (8 sheets, pandas digest, no raw dump)
- `ALPHA_RANKER/rnd/scorecard/USABLE_ALPHA_INVENTORY.md` (existing, read in full)
- WebSearch, 2026-07-18: Alpha Alternatives / Windmill Capital / Renaissance / Systematix / ithought — surface-level only, sources cited inline in §c.
