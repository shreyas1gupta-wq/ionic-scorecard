# FRAMEWORK CATALOG — factor/signal ideas mined from firm knowledge, for ALPHA_RANKER 1M/1Y/5Y research
Compiled by Lakshmi Narayanan (Librarian), 2026-07-16. Every row is what our own files actually say — [DATA] = verbatim/near-verbatim from source; [INFERENCE] = a construction detail I filled in because the source named the factor but not the exact formula. Nothing here is fabricated; where the source gave no formula, the Construction column says so.

Sources scanned: `Shreyas_Ionic_AMC/04_RND_LAB/FACTOR_LIBRARY.md`, `KNOWLEDGE_BASE.md`, `KILLED_IDEAS.md`, `CODE_CHECKS.md`; `ALPHA_RANKER/02_SCORING_ENGINE.md`, `04_FRAMEWORK_1M.md`, `05_FRAMEWORK_1Y.md`, `06_FRAMEWORK_5Y.md`, `07_FRAMEWORK_MICROCAP.md`, `08_FORENSICS_REDFLAGS.md`, `12_RND_READING_LIST.md`; `03_RESEARCH_DESK/ANALYST_CHECKLISTS.md`, `EVALUATION_FRAMEWORK.md`; `04_RND_LAB/imported_research/MULTIBAGGER_STUDY.md`, `MULTIBAGGER_DNA.md`; `04_RND_LAB/PMS_STUDY_20260712/SYNTHESIS.md`; `04_RND_LAB/ideas/20260704_n500_lowvol50_sleeve.md`, `20260704_factor_index_replication.md`; already-coded factor modules in `ALPHA_RANKER/src/factors/*.py` (cross-referenced, not re-derived).

---

## 1. MOMENTUM

| Name | Horizon | Construction | Expected sign | Evidence / caveat | Source |
|---|---|---|---|---|---|
| 12-1 cross-sectional momentum | 1M/1Y | 12-month return excluding most recent month (skip-month, avoids short-term reversal contamination) | + | Academic cross-sectional winner (Jegadeesh-Titman 1993); firm's core momentum factor, coded in `universe_technical.py` | `04_FRAMEWORK_1M.md` L10-11, `05_FRAMEWORK_1Y.md` L20, `12_RND_READING_LIST.md` L8 [DATA] |
| Multi-lookback price momentum | 1M | 1M/3M/6M returns, most-recent-month skipped | + | — | `04_FRAMEWORK_1M.md` L11 [DATA] |
| Relative strength vs sector & Nifty (12-1, 3-1) | 1M/1Y | RS rank of stock return vs sector index and vs Nifty | + | — | `04_FRAMEWORK_1M.md` L12, `05_FRAMEWORK_1Y.md` L21 [DATA] |
| Residual / idiosyncratic momentum | 1Y | Momentum beta/sector-neutralized (regression residual) | + | Blitz et al: cleaner signal than raw momentum at 1Y | `05_FRAMEWORK_1Y.md` L21, `12_RND_READING_LIST.md` L10 [DATA]; exact regression spec not on file [INFERENCE] |
| 52-week-high proximity | 1M/microcap | Distance from 52w high (anchoring/breakout tendency) | + | Also used as a "still in favor" re-entry gate for concentrated quality books | `04_FRAMEWORK_1M.md` L14; PMS #6 ValueQuest funnel, `SYNTHESIS.md` L108 [DATA] |
| DMA alignment/slope | 1M | Distance from 20/50 DMA; MA alignment/slope | + | — | `04_FRAMEWORK_1M.md` L13 [DATA] |
| Minervini trend template (8 gates, all must hold) | 1M (entry timing) | Close>150dMA>200dMA; 150dMA>200dMA; 200dMA rising ≥22 sessions; 50dMA>150dMA>200dMA; Close>50dMA; Close≥30% above 52w low; Close within 25% of 52w high; RS percentile ≥70 vs N500 (12m return rank); VCP (volume contracting through base, expanding on breakout) | + | 100% of 549 multibagger-years (2007-25) passed trend-template in-year — "the signal CAN catch them all" — but 42% only emerge mid-year (turnarounds), so it's a confirming not a discovery filter | `ANALYST_CHECKLISTS.md` L7-17; `MULTIBAGGER_STUDY.md` L8 [DATA] |
| Time-series (absolute) momentum | 1M/1Y trend | Own-asset trailing-return sign as position filter (not cross-sectional) | + | Moskowitz-Ooi-Pedersen | `12_RND_READING_LIST.md` L9 [DATA]; not yet built for equities per catalog scan [INFERENCE] |
| Short-term reversal (mean-reversion, opposite sign) | 1M | Last-week return, sign-flipped; RSI(14) extremes; Bollinger %B; distance from anchored VWAP | − (fades momentum in chop) | Weight flips with regime: momentum↑/mean-rev↓ in trend; reverse in chop | `04_FRAMEWORK_1M.md` L28-31 [DATA] |
| Sector-momentum tilt | 1Y/5Y/microcap | Overweight the year's hot structural/policy-theme sector (defence, power, EMS/semis, capital-markets infra named as 2026-2040 candidates) | + | HIGH-PRIORITY GAP: every era's giant winners cluster in ONE hot theme; sector_industry_map.parquet now exists but the tilt itself is NOT YET BUILT (pre-registered TODO for SIG-12) | `KNOWLEDGE_BASE.md` #11; `MULTIBAGGER_DNA.md` L54, L71-72 [DATA] |

## 2. VALUE

| Name | Horizon | Construction | Expected sign | Evidence / caveat | Source |
|---|---|---|---|---|---|
| Earnings yield / P/B / P/CF / EV-EBITDA | 1Y/5Y | Standard multiples, cheap vs fundamentals | + (cheap wins) | READY data status (screener_deep, ratios_pit, mc_fundamentals) | `FACTOR_LIBRARY.md` L7 [DATA] |
| Valuation vs own 5-10y history percentile + vs sector peers | 1Y | PE/PB/EV-EBITDA/PEG percentile-ranked against the stock's own trailing history AND sector | + (cheap-but-improving = sweet spot) | Re-rating is named THE 1Y alpha driver | `05_FRAMEWORK_1Y.md` L15-17 [DATA] |
| Earnings-yield vs bond-yield gap; FCF yield | 1Y | — | + | — | `05_FRAMEWORK_1Y.md` L16 [DATA] |
| Reverse-DCF implied-growth sanity check | 5Y | What growth is the current price implying vs is that beatable (not a point DCF) | penalty if implied growth is unrealistic | Damodaran *Narrative and Numbers* | `06_FRAMEWORK_5Y.md` L29; `12_RND_READING_LIST.md` L33 [DATA] |
| PEG-style growth-adjusted valuation | 1Y/5Y | PE / trailing-growth-CAGR < ~1.5 (Carnelian Shift precise threshold: PEG~1.1 vs bmk 1.5); NOT a static low-PE screen | + (below threshold) | 6/10 studied PMS managers converge on growth-adjusted valuation over static PE; explicit rejection of fixed-PE/PEG in favor of Competitive-Advantage-Period duration (SageOne) | `SYNTHESIS.md` §1 row 5, §4 candidate #4 [DATA] |
| PE-percentile-vs-own-history + decelerating-growth JOINT condition (exit trigger, not entry) | 1Y/5Y | Trailing PE in top decile of stock's own 5-10y distribution AND trailing-4Q revenue growth decelerated <8% for 2 consecutive quarters | sell/− | Highest-confidence codable rule in the whole PMS study: SageOne (has this trigger) 25.1% CAGR SI vs Marcellus (lacks it) −ve alpha since inception on an otherwise near-identical quality entry screen — the "Anti-Marcellus-Trap" candidate #1 | `SYNTHESIS.md` §3, §4 candidate #1 [DATA] |
| Value-cannot-grow-faster-than-earnings discipline | 1Y | Qualitative overlay — flag when a "value" name's implied growth exceeds fundamentals | penalty | Carnelian house rule | `SYNTHESIS.md` §1 row 5 [DATA] |

## 3. QUALITY

| Name | Horizon | Construction | Expected sign | Evidence / caveat | Source |
|---|---|---|---|---|---|
| ROE/ROCE floor ~15-20%+ | 1Y/5Y/microcap | ROE or ROCE above a threshold (varies 14-20% across managers; Marcellus requires ROCE>cost-of-capital for 10 consecutive years) | + | Single most convergent screen across 10 studied PMS/AIF managers (7/10 use it) | `SYNTHESIS.md` §1 row 1 [DATA] |
| ROE/ROCE level vs cost of capital, trend not cutoff | 1Y | — | + | Firm's own framework explicitly prefers level-vs-COC and trend over a hard cutoff | `05_FRAMEWORK_1Y.md` L25 [DATA] |
| ROCE sustained 8+ trailing quarters | 1Y/5Y | Quarterly ROCE>15% held for ≥8 consecutive quarters (PIT `available_date`) | + (entry gate) | Marcellus's own twin filter, reused in Anti-Marcellus-Trap candidate | `SYNTHESIS.md` §4 candidate #1 [DATA] |
| Piotroski F-score | 1Y/5Y/microcap | 9-point fundamental-strength checklist within value | + (support, not cutoff) | — | `FACTOR_LIBRARY.md` L8; `12_RND_READING_LIST.md` L12 [DATA] |
| Novy-Marx gross profitability | 5Y | (Revenue − COGS)/Assets | + | Academic quality factor | `12_RND_READING_LIST.md` L13 [DATA]; not yet coded per scan [INFERENCE] |
| Asness-Frazzini-Pedersen QMJ (quality-minus-junk) | 5Y | Composite of profitability+growth+safety+payout | + | — | `12_RND_READING_LIST.md` L14 [DATA] |
| Frazzini-Pedersen BAB (betting-against-beta / low-vol) | regime-defense | Long low-beta, short high-beta (or long-only low-beta tilt) | + (low-beta outperforms risk-adjusted) | — | `12_RND_READING_LIST.md` L15 [DATA] |
| Low leverage / net-debt-to-EBITDA trend | 1Y/5Y/microcap | D/E or net-debt/EBITDA below threshold and improving | + | 5/10 PMS managers converge on this; universal aversion to financing-driven ROE | `SYNTHESIS.md` §1 row 4; `06_FRAMEWORK_5Y.md` L25 [DATA] |
| FCF conversion / accruals (Sloan) | 1Y/5Y | (Net income − CFO)/Assets; low accruals = higher-quality earnings | + (low accruals better) | Sloan 1996 accruals anomaly | `05_FRAMEWORK_1Y.md` L25; `08_FORENSICS_REDFLAGS.md` L7; `12_RND_READING_LIST.md` L16 [DATA] |
| Earnings stability & predictability | 1Y/5Y | Low variance of quarterly/annual earnings growth | + | — | `05_FRAMEWORK_1Y.md` L26 [DATA] |
| Reinvestment runway: ROIC × reinvestment rate, ROIC-WACC spread × redeployment opportunity size | 5Y | Sustainable growth = ROIC × reinvestment rate; wide spread with no reinvestment opportunity ≈ dividend stock, not compounder | + (spread AND runway both needed) | Firm's own 5Y-lens dominant growth factor | `06_FRAMEWORK_5Y.md` L9-10 [DATA] |
| Moat type & direction (widening/stable/eroding) | 5Y | Brand/network/switching-cost/cost-advantage/regulatory/distribution, scored for DIRECTION not just level | + (widening only) | Dorsey moat taxonomy | `06_FRAMEWORK_5Y.md` L14-16; `12_RND_READING_LIST.md` L28 [DATA] |
| Growth threshold ~10-25% CAGR (revenue/PAT) | 1Y/5Y | Trailing revenue or PAT CAGR above manager-specific threshold (10% Marcellus floor up to 20-25% SageOne) | + | 6/10 PMS managers converge; threshold scales with valuation tolerance paid | `SYNTHESIS.md` §1 row 2 [DATA] |
| Estimate-revision breadth & momentum (SUE) | 1M/1Y | Net upgrades, magnitude, dispersion tightening of analyst estimates | + | Named "the single most reliable 1Y signal" (Chan-Jegadeesh-Lakonishok); at 1M "the fastest fundamental signal that works" | `05_FRAMEWORK_1Y.md` L10-11; `04_FRAMEWORK_1M.md` L24; `12_RND_READING_LIST.md` L18 [DATA] |
| Post-earnings-announcement drift (PEAD) | 1M | Price drift following an earnings surprise, joined on PIT `available_date` | + (in drift direction) | Bernard-Thomas; firm has a PEAD_EARNINGS_TRAIL research line already | `12_RND_READING_LIST.md` L17; `SYNTHESIS.md` §4 candidate #5 [DATA] |

## 4. GROWTH

| Name | Horizon | Construction | Expected sign | Evidence / caveat | Source |
|---|---|---|---|---|---|
| Forward earnings growth trajectory + acceleration/deceleration | 1Y | Growth over next 4-8 quarters, sign of 2nd derivative | + (accelerating) | — | `05_FRAMEWORK_1Y.md` L9 [DATA] |
| Revenue growth durability (volume vs price-led) | 1Y | — | + | — | `05_FRAMEWORK_1Y.md` L11 [DATA] |
| Margin trajectory / operating leverage inflection | 1Y/5Y/microcap | Margin turn from a capex/capacity-expansion lag | + | THE microcap-multibagger upside engine per firm's own model | `05_FRAMEWORK_1Y.md` L12; `07_FRAMEWORK_MICROCAP.md` L33-34 [DATA] |
| Earnings-inflection + multi-year-base-breakout coincidence | 1Y/microcap | Fundamental inflection (loss-to-profit/margin turn/order book) timed at a chart base breakout | + strongly | Universal winning setup across ALL eras studied (2007-2025); "theme + earnings = stays; theme alone = trade" | `MULTIBAGGER_DNA.md` L22-28 [DATA] |
| TAM growth / penetration runway / optionality | 5Y | Qualitative-quant hybrid, judgment-scored | + | — | `06_FRAMEWORK_5Y.md` L11 [DATA] |
| Asset-growth anomaly (overinvestment) | 5Y/forensic | High asset growth predicts LOWER future returns | − | Cooper-Gulen-Schill | `12_RND_READING_LIST.md` L20 [DATA]; not yet coded [INFERENCE] |
| Government-policy-lever / structural-theme catalyst | 1Y/5Y/microcap | Flag names in the year's policy-driven sector (PLI, China+1, defence indigenisation, capex cycle) | + | Every durable multibagger theme mapped to a policy lever across 2007-2025 | `MULTIBAGGER_DNA.md` L36-37 [DATA] |

## 5. TECHNICAL

| Name | Horizon | Construction | Expected sign | Evidence / caveat | Source |
|---|---|---|---|---|---|
| Stage analysis (Weinstein) | 1Y (trend confirmation overlay) | 4-stage classification (basing/advancing/topping/declining) | + in stage 2 | — | `05_FRAMEWORK_1Y.md` L22 [DATA] |
| VCP (volatility contraction pattern) | 1M/microcap | Volume contracting through the base, expanding on breakout | + | Component #9 of trend template | `ANALYST_CHECKLISTS.md` L16 [DATA] |
| Volatility state / ATR percentile | 1M | High vol → widen return distribution, reduce conviction magnitude (NOT a directional signal) | neutral (dampener) | — | `04_FRAMEWORK_1M.md` L31 [DATA] |
| ATR-based trailing exit | risk overlay | Chandelier-style ATR trail | n/a (exit, not entry) | K-adx-atr-family: ATR trails are GOOD EXITS ("credit belongs to the exit") even though ADX-entry-gating on the same family failed | `KILLED_IDEAS.md` K-adx-atr-family [DATA] |
| Two-stage stop (tight initial, wide trailing 25-35% once profitable) | position management, all horizons | Tight 5-8%-below-pivot initial stop; then trail 25-35%/below 50DMA once in profit | n/a (risk mgmt, not scoring) | Median multibagger draws down 23% intra-year on the way up; a 15% trailing stop ejects the median winner — verified on 549 multibagger-years 2007-25 | `MULTIBAGGER_STUDY.md` L13-24 [DATA] |
| Base length / accumulation (low-float, multi-year base) | microcap | Long base formation + breakout from multi-year base on volume/delivery | + | — | `07_FRAMEWORK_MICROCAP.md` L27-29 [DATA] |

## 6. VOLATILITY / RISK-DEFENSIVE

| Name | Horizon | Construction | Expected sign | Evidence / caveat | Source |
|---|---|---|---|---|---|
| N500 LowVol50, inverse-vol weighted, quarterly rebalance | 1Y | Rank full N500 by trailing realized vol, inverse-vol-weight the top-50 lowest-vol names, rebalance quarterly | + | RESURRECTED (K-013): 17.46% frictionless CAGR clears the corrected p75 hurdle (17.13%) by +0.33pp; monthly cadence was marginal (turnover 173%), quarterly halves turnover and clears comfortably. Standing diversifier candidate for IC (orthogonality to short-vol book), independent of the p75 debate | `FACTOR_LIBRARY.md` L10; `KILLED_IDEAS.md` K-013; `ideas/20260704_n500_lowvol50_sleeve.md` [DATA] |
| Do NOT apply a low-vol or low-price filter to a multibagger/growth screen | 1Y/microcap | — (negative construction rule) | n/a | Multibaggers are VOLATILE (median 42% annualized 60-day vol at year-start) and mid-priced (median Rs.94) — a low-vol screen actively EXCLUDES the winners you want; low-vol and momentum-growth are separate, sometimes conflicting sleeves | `MULTIBAGGER_STUDY.md` L11-12, L47 [DATA] |
| VIX percentile / trend / breadth as a REGIME gate (not a stock factor) | overlay, all horizons | India-VIX percentile, price-vs-50/200DMA slope, breadth | gates weight, not stock score | Regime classifier drives which weight-vector is used firm-wide (`02_SCORING_ENGINE.md` Step 4); mean-reversion signals on derivatives MUST regime-gate or risk existential tail loss | `02_SCORING_ENGINE.md` L40-48; `KNOWLEDGE_BASE.md` #23 [DATA] |

## 7. FLOW / SENTIMENT / POSITIONING

| Name | Horizon | Construction | Expected sign | Evidence / caveat | Source |
|---|---|---|---|---|---|
| Volume & delivery-% trend, OBV, volume-price divergence | 1M | — | + (rising delivery% + volume on up-moves) | — | `04_FRAMEWORK_1M.md` L17 [DATA] |
| F&O positioning: OI build-up classification, futures basis, PCR, rollover% | 1M | Long-buildup/short-covering classification from ΔOI vs Δprice | + / − by classification | — | `04_FRAMEWORK_1M.md` L18 [DATA] |
| Bulk/block deal flow, FII/DII proxy at stock level | 1M | — | + (net buying) | Daily FII/DII + bulk/block partially NSE-blocked (home-network list) | `04_FRAMEWORK_1M.md` L19; `FACTOR_LIBRARY.md` L21 [DATA] |
| DII 5-day flow rank | short-horizon | Daily DII net-flow, 5-day rolling rank, q≥0.8 → 3-day hold | + | K-B1c-DII-flow: near-miss on a certify-or-kill card (t=2.43 vs 2.5 bar; 4/5 sub-tests passed, beat shuffle95, eras strengthening +11.7→+44.4). NOT usable yet — forward-data-only shadow-ledger resurrection path, no in-sample re-tests permitted | `KILLED_IDEAS.md` K-B1c-DII-flow [DATA] |
| NLP tone on news/social/call-transcripts | 1M/1Y (as an overlay) | FinBERT tone score on prepared-remarks vs Q&A separately; QoQ tone delta; evasion markers (dodged questions); guidance-language shift; lexicon baseline BEFORE any model | + (improving tone) | Data ready: india_fin_news 125K + MiMIC 1,042 calls | `FACTOR_LIBRARY.md` L20; `ANALYST_CHECKLISTS.md` L19-20 [DATA] |
| Promoter/institutional shareholding deltas | 1Y/5Y/microcap | Δ promoter holding, Δ FII/DII holding, insider PIT/SAST direction | + (accumulation) | shareholding_changes (21,713 rows) READY | `FACTOR_LIBRARY.md` L21 [DATA] |
| Buyback / creeping-acquisition in trailing 12M | 5Y/microcap | Flag names where promoter/company did a buyback or creeping acquisition recently | + | Aequitas pre-purchase screen — flagged in our study as NON-CODABLE at present (needs SAST/shareholding filings still 403 for us) | `SYNTHESIS.md` §5 [DATA — but marked non-codable] |

## 8. FORENSIC / RED-FLAG (penalty / gate factors, not additive alpha)

All items below feed a nonlinear, context-scaled penalty (`penalty = severity × size_mult(cap) × regime_mult(credit/valuation/trend)`), NOT a linear factor — see `02_SCORING_ENGINE.md` Step 6 and `08_FORENSICS_REDFLAGS.md`. [DATA]

| Name | Horizon weight | Construction | Source |
|---|---|---|---|
| Beneish M-score (8 ratios: DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) | all, heaviest at 5Y/microcap | Manipulation-probability composite | `08_FORENSICS_REDFLAGS.md` L8; `12_RND_READING_LIST.md` L19 |
| Montier C-score | cross-check to Beneish | Earnings-manipulation checklist | `08_FORENSICS_REDFLAGS.md` L9 |
| CFO vs PAT divergence, 3-5y | all | Profits without cash = red flag, severity↑ if persistent | `08_FORENSICS_REDFLAGS.md` L7 |
| Receivables/inventory growth vs revenue growth | all | Classic microcap fraud tell | `08_FORENSICS_REDFLAGS.md` L11; `07_FRAMEWORK_MICROCAP.md` L25 |
| CWIP-to-assets that never capitalizes | all | Perennial under-construction = cash siphon | `08_FORENSICS_REDFLAGS.md` L16 |
| Promoter pledge level & trend | all, near-veto microcap | — | `08_FORENSICS_REDFLAGS.md` L22; `ANALYST_CHECKLISTS.md` L4 |
| Auditor resignation / adverse opinion / frequent changes | all — HARD VETO | Caps score ≤ −60 regardless of other strengths | `08_FORENSICS_REDFLAGS.md` L23, L51-55 |
| Related-party transaction %-of-revenue/PAT and trend | all | — | `08_FORENSICS_REDFLAGS.md` L21 |
| Debt-covenant breach with going-concern doubt | all — HARD VETO | — | `08_FORENSICS_REDFLAGS.md` L54 |
| Key-management churn (CFO exits) | all | "Classic tell" | `08_FORENSICS_REDFLAGS.md` L24; `ANALYST_CHECKLISTS.md` L4 |
| Governance-elimination as a PRE-STEP before any quant screen | all | Applied as a gate BEFORE the ROE/growth funnel, not blended additively | 6/10 PMS managers do this (SageOne 300→150 names purely on governance) | `SYNTHESIS.md` §1 row 6 [DATA] |

## 9. COMPOSITE / MULTI-FACTOR SCREENS (whole rule-sets, PMS-derived)

These are pre-assembled, ranked, codable composite screens — not single factors — carried over from the PMS study for direct testing.

| Name | Horizon | Rule | Evidence rank | Source |
|---|---|---|---|---|
| #1 Anti-Marcellus-Trap (quality-floor + mandatory deceleration exit) | 1Y/5Y | Entry: ROCE>15% for 8+ trailing quarters + revenue CAGR≥10%. Exit: trailing-4Q growth decelerates <8% for 2 consecutive quarters AND/OR PE in top decile of own 5-10y history while growth decelerated 2 consecutive quarters | HIGHEST — direct verified causal contrast (SageOne 25.1% CAGR SI with trigger vs Marcellus −ve alpha SI without it) | `SYNTHESIS.md` §4 #1 [DATA] |
| #2 SageOne GARP funnel + mcap-rank band | 1Y | Sector ROE/margin/growth screen → stock trailing 8-12Q sales/PAT growth>20% + ROE/ROCE>20% + low D/E + mcap rank 101st-600th + low-stdev growth persistence proxy; exit on growth <15% for 2 consecutive quarters (valuation alone NOT a sell trigger) | Strongest single track record (25.1% CAGR/13.8yrs) | `SYNTHESIS.md` §4 #2 [DATA] |
| #3 Core-Satellite sector rotation (static substitute) | 1Y/5Y | Core: top-quartile ROE + low earnings-vol + dividend payer + sector-leadership. Satellite: named cyclical sectors, PE/PB percentile bottom decile. Static 50/50 blend (cannot replicate the real regime-timing call) | Good (20.64% SI, +6.6pp alpha) but process only partially replicable; firm has NO sector-rotation sleeve today (high differentiation) | `SYNTHESIS.md` §4 #3 [DATA] |
| #4 PEG-style growth-adjusted valuation | 1Y | PE/growth-CAGR<1.5, ROE>15%, D/E<1; exit when PEG>2.5 AND growth simultaneously decelerating | Medium-strong, young track record | `SYNTHESIS.md` §4 #4 [DATA] |
| #5 Forensic-lite quality + position ladder | 5Y | ROE>15% (18%+ ex-financials) + moat proxy (5y stable/rising gross margin) + PE<40x unless PAT growth≥20%; ladder 3%→5%→8%→10-15% on confirming quarters; PEAD-quality-of-reaction as ladder-step-up trigger | Solid, modest alpha | `SYNTHESIS.md` §4 #5 [DATA] |
| #6 ValueQuest concentrated ROE funnel | 5Y | 400-500 universe → 150-200 → 30-50 → 8-12 names, ROE≥20%, cross-checked vs P/B; exit when ROE drops out of top quartile 2 consecutive quarters or growth<universe median | Strong, consistent across every window, but likely overlaps existing quality-momentum composites (low differentiation) | `SYNTHESIS.md` §4 #6 [DATA] |
| #7 CAUTION — Smallcap GARP rank-band (400th-1200th mcap) | 1Y | Same mechanics as #2 applied to smaller names | Mixed-to-bad: SageOne's own Small&Micro product is independently reviewed as −3.7% 5yr alpha, "do not recommend" | `SYNTHESIS.md` §4 #7 [DATA] |
| Quality-momentum composite (quality gate on momentum picks) | 1Y/5Y | Gate/boost momentum candidates by ROE + low-debt + earnings-acceleration | HIGH PRIORITY per firm's own multibagger research — NOT YET BUILT (needs fundamentals data fetch, flagged as done/cataloged) | `KNOWLEDGE_BASE.md` #11; `MULTIBAGGER_DNA.md` L50-53 [DATA] |

---

## ANTI-OVERFIT / VALIDATION LESSONS (apply to every stock-scoring backtest before trusting it)

1. **Denominator disease (three-strikes hard rule):** any per-trade/per-period return must ALSO be reported in denominator-free rupee terms and % of a stable base (spot/notional, never a decaying or near-zero base) before it may be believed. `KNOWLEDGE_BASE.md` #8, #2. [DATA]
2. **Lookahead taxonomy T1-T10, mandatory audit pass:** `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` + `lib/lookahead_audit.py` + one-day-lag test on every backtest before a Gate-4 pass or quoted result. `KNOWLEDGE_BASE.md` #7 (D-028). [DATA]
3. **PIT discipline is non-negotiable for stock-scoring:** join fundamentals on `available_date`, never quarter-end date (86.2% exact-dated PIT dataset exists). Any filter built from realized outcomes is untradeable (the "16 landmines" lesson). `KNOWLEDGE_BASE.md` #3; `CODE_CHECKS.md` L12-13. [DATA]
4. **Survivorship inflates BOTH the strategy AND its null:** fixing a panel for delisted names cut one strategy's CAGR ~4pp/yr AND raised the random-draw null from 3.5% to 4.7-7.1% — a shuffle/permutation gate is only as honest as the universe it draws from. `KNOWLEDGE_BASE.md` #13. [DATA]
5. **Random-basket benchmark (D-029), not the index:** the honest null for stock-selection is the DISTRIBUTION of cost-loaded random baskets from the same cap-segment at the same position count — percentile bands are the real information, not the mean. Standing series in `datasets/derived/benchmarks_random/`. `KNOWLEDGE_BASE.md` #15. [DATA]
6. **Turnover-matched comparator is mandatory:** a strategy can pass DSR/PBO/plateau/lookahead gates and still have zero selection edge if its hurdle churns more and pays more costs — every hurdle comparison requires a turnover-matched placebo. `KNOWLEDGE_BASE.md` #20. [DATA]
7. **Percentile bar must be built from TERMINAL path outcomes, not a chained percentile-of-percentiles path** (a "p75 NAV" built by chaining the 75th-best quarterly return every quarter is a path no random basket ever walked — an always-lucky fiction). `KNOWLEDGE_BASE.md` #18. [DATA]
8. **Rebalance cadence is part of the edge, not a detail:** monthly rebalancing of momentum/quality portfolios can run 330-450% one-way turnover → 3.5-10.7pp/yr cost drag; NSE's own factor indices rebalance semiannually for a reason. Test multiple cadences explicitly (N500 LowVol50 killed at monthly turnover, resurrected at quarterly). `KNOWLEDGE_BASE.md` #16; `KILLED_IDEAS.md` K-013/K-014. [DATA]
9. **Costs invert the size premium:** gross smallcap ≈ gross largecap (~13.4-13.8% CAGR) but net-of-honest-costs large (11.9%) beats small (9.2-10.0%) — a smallcap factor must clear 2.4-4.2pp/yr extra drag before it exists. Also: smallcap "quality" scores from free data have <40% coverage in all years — a free-data smallcap MQ index is momentum in a quality costume. `KNOWLEDGE_BASE.md` #17. [DATA]
10. **Circuit/volume-conditional fills mandatory for any equity backtest** (`lib/execution_realism.fill_check()`): no-fill on locked/zero-volume bars, 2-3x slippage on thin bars — momentum entries cluster on upper-circuit days. `KNOWLEDGE_BASE.md` #14. [DATA]
11. **Regime/timing overlays must beat BOTH static parents, pre-registered:** a vol-timing layer that "feels" sophisticated lost to pure momentum by 4.8pp/yr net (K-015) — judge such overlays as RISK overlays (Sharpe/DD budget), never on raw CAGR. `KNOWLEDGE_BASE.md` #19; `KILLED_IDEAS.md` K-015. [DATA]
12. **Same-exit placebo is the only reliable arbiter for any "entry timing" claim:** AF-07's turn signal showed +24.1%/Sharpe 1.26 from queue-mechanics artifacts alone (favorable-trade-subset selection + active-days-only Sharpe) but was WORSE than random entries with identical exits at episode-level measurement. K-adx-atr-family and K-stock-meanrev-standalone both show the same pattern: signal may be real, but must beat the same-exit placebo, not just an unconditional backtest. `KILLED_IDEAS.md` K-AF07-stage-turn, K-adx-atr-family, K-stock-meanrev-standalone. [DATA]
13. **Multiple-testing/DSR discipline — read Harvey-Liu-Zhu and López de Prado FIRST**, before a 1000-test factor program fools itself; family trials ledger feeds DSR honesty. `12_RND_READING_LIST.md` L49; `FACTOR_LIBRARY.md` L27. [DATA]
14. **Post-publication decay is real but ~50% is a measurement artifact:** literature shows 26-58% decay on published factors; separate real crowding from denominator/risk-exposure mis-measurement via forward-test at 1.5-2x tighter costs and tracking capacity/win-rate trend. `KNOWLEDGE_BASE.md` #22, #24. [DATA]
15. **Sleeve correlation must be measured at the horizon where drawdowns live** (monthly/DD-window, not daily) — daily correlation systematically overstates diversification for episodic/asynchronous strategies; a new stock-scoring sleeve's diversification claim vs the existing short-vol book must use monthly-horizon correlation. `KNOWLEDGE_BASE.md` #25a. [DATA]
16. **No silent imputation on missing factor data** — flag, reduce confidence, and escalate to a human if the missing factor is load-bearing for the call (brief Q17, no ruinous fallback). `02_SCORING_ENGINE.md` Step 1, Step 10. [DATA]
17. **Explainability is mandatory** — every score ships with SHAP-style top-driver decomposition; a score that can't be explained doesn't ship. `02_SCORING_ENGINE.md` "Explainability". [DATA]

---

## PRIOR-ART: KILLED IDEAS RELEVANT TO STOCK-SCORING (do not retest without meeting the resurrection condition)

| ID | Family | Why it's relevant to ALPHA_RANKER scoring | Resurrection condition |
|---|---|---|---|
| K-stock-meanrev-standalone | RSI(3)/z-score pullback buying in stage-2 uptrends | Direct test of a mean-reversion ENTRY-TIMING factor on stocks — net −0.15%/−0.19% per trade, t=−4.8/−7.2, n=21k/30k, both eras negative 2015-2026. Timing info is real (+0.28% vs placebo) but standalone vehicle is dead | Only as an entry-timing OVERLAY on trades already being made for other reasons — NO standalone re-tests at different RSI/z thresholds |
| K-postbreakout-orb | Intraday ORB during post-breakout weeks (tests whether breakout stocks "trend harder" intraday) | Relevant if ALPHA_RANKER ever extends to intraday entry-timing on its 1M-flagged names — hypothesis is BACKWARDS (fade, not follow) | Only a construction with positive GROSS edge ≥40bps on NEW data |
| K-adx-atr-family | ADX-confirmation trend-entry (8 constructions) | Tests whether "trend confirmation" (a technical factor family adjacent to momentum) adds anything beyond the exit — it never has; ADX-entry-gated stocks earned HALF of random stage-2 entries with identical exits | None for ADX-entry; ATR-exit components remain usable (they're exits, not scoring factors) |
| K-015 dynamic-regime momentum/low-vol basket | Regime-switching overlay on a momentum+low-vol composite | Directly relevant: a VIX-median regime SWITCH diluted a static pure-momentum parent (21.54% vs 26.38%) despite cutting vol/DD — regime overlays are a RISK tool, not a return-enhancer, for stock-scoring composites too | Only as a risk-targeting overlay judged on Sharpe/DD, or with a demonstrably predictive (non-trailing-VIX) regime signal |
| K-014 N500 MQ50 semiannual | Momentum+Quality composite at semiannual rebalance | CLEAN structural kill: semiannual cadence lets momentum winners round-trip (frictionless 18.94%→12.34% collapse); quality-leg coverage only 23% (momentum-fallback majority) — a warning for any 1Y quality-momentum blend the ranker builds | Only a QUARTERLY MQ50 variant beating hurdle+0.5pp at 2x costs, maxDD>−50% |
| K-013 N500 LowVol50 | Low-vol composite | RESURRECTED — see catalog §6; the p75-hurdle methodology fight (chained-percentile-path vs terminal-path-percentile) is itself a reusable validation lesson (#7 above) | Already resurrected; Gate-4 pending |
| PMS #7 (smallcap GARP rank-band) | Extending the ROE/growth screen to smallcap | Explicitly flagged CAUTION, not killed but evidence mixed-to-bad (SageOne's own Small&Micro product independently reviewed as −3.7% 5yr alpha, "do not recommend") | Must carry the circuit/thin-volume execution-realism overlay before any conclusion is drawn — the factor screen is likely not the actual determinant of outcome at smallcap |

---

## SUMMARY COUNT (by category)
Momentum 9 · Value 7 · Quality 12 · Growth 6 · Technical 6 · Volatility/risk-defensive 3 · Flow/sentiment 6 · Forensic/red-flag 10 (gate-only) · Composite multi-factor screens 8 = **67 distinct factor/signal entries** + 17 anti-overfit/validation lessons + 7 killed-idea prior-art entries.

## GAPS FLAGGED (named in our own docs as needed but not yet built)
- Sector-momentum tilt (data now exists — sector_industry_map.parquet — build pending, HIGH PRIORITY per `KNOWLEDGE_BASE.md` #11).
- Quality-momentum gate/boost overlay on momentum picks (HIGH PRIORITY, `MULTIBAGGER_DNA.md`).
- Real analyst-estimate revision feed (currently PROXY via beat_miss + PEAD; Trendlyne flagged as a D-009 candidate, not yet approved). `FACTOR_LIBRARY.md` L11.
- Time-series (absolute) momentum for single-stock trend confirmation — named in reading list, not found coded in `src/factors/*`.
- Novy-Marx gross profitability, Cooper-Gulen-Schill asset-growth anomaly — named in reading list, not found coded.
