# XORLOG — FEATURE BACKLOG & GAP ANALYSIS
v1.0 — 2026-07-16. Companion to 00_VISION_AND_PLAN.md. Every item cites the research pattern it came from (01_RESEARCH/) or is tagged [NEW IDEA]. Phases: P0 launch-prep, P1 MVP, P2 licensed, P3 scale, PX explicitly parked.

## A. Features to add (validated, phase-mapped)

### Journal+ (the wedge, deepen it)
| # | Feature | Phase | Why / source |
|---|---|---|---|
| A1 | **Multi-broker tax engine** — STCG/LTCG, intraday speculative income, F&O turnover for ITR, charges breakdown, across ALL brokers | P1-P2 | BIGGEST miss in plan v1.1. Zerodha Console does this Zerodha-only; nobody does it multi-broker. Zero regulatory risk, every trader needs it yearly, natural journal adjacency, seasonal viral spike (Jun-Jul ITR) |
| A2 | Contract-note PDF parser (AI) — import trades from ANY broker via contract-note upload, even brokers with no API | P1 | Solves import breadth cheaply; India-specific; kills the "my broker isn't supported" objection; reduces broker-API single-point-of-failure (Trendlyne/Angel precedent) |
| A3 | Verified P&L share-cards — shareable image cards of journal stats (win rate, discipline score), "Verified by Xorlog" | P1 | Growth loop. India's verified-P&L culture on X/Twitter is huge; every share = an ad. Guardrail: show risk metrics alongside returns, no "assured returns" framing |
| A4 | Discipline streaks & weekly review ritual (email/PWA push: "your week in 5 numbers") | P1 | Retention organ. Streaks on PROCESS (journaling, rule-adherence) not profit — avoids the overtrading dark pattern flagged in global_comparables |
| A5 | Cost-drag audit — brokerage/STT/stamp/slippage as % of gross P&L, per strategy | P1 | Pairs with firm TCA expertise; nobody shows this honestly; feeds the coach |
| A6 | Prop-firm/funded-account compliance tracker (drawdown/daily-loss rules auto-checked) | P2 | TradesViz niche pattern; India funded-account scene growing |

### Screener+ / analytics
| # | Feature | Phase | Why / source |
|---|---|---|---|
| A7 | **Alerts engine** — screener-result alerts, price/OI/IV alerts via email/Telegram/PWA push | P1 | Table stakes — Chartink's whole draw is scan-alerts; missing from plan v1.1 |
| A8 | Portfolio/MF X-ray — look-through overlap across user's MFs/ETFs/stocks ("your 5 funds are 62% the same stocks") | P2 | Parqet pattern; India retail is MF-heavy; Tickertape does portfolio sync but not deep look-through |
| A9 | Regime dashboard — market breadth, vol regime, factor leadership now (educational, index-level, no calls) | P2 | Uses our data; index/sector-level = RA-exempt zone; daily-habit surface |
| A10 | FII/DII flows + bulk/block deals + insider (SAST) tracker | P2 | StockEdge/Trendlyne draws; NSE data (note: some NSE APIs 403 on office network) |
| A11 | Corporate-announcement AI summarizer with hard SLA ("filing → summary in N sec") | P2 | Toss 10-second pattern + moomoo; NSE announcement flood is high-noise; we already have working NSE announcements API code |
| A12 | Earnings calendar + event-window flags on positions ("results in 3 days on 2 holdings") | P1-P2 | PIT earnings data in hand; mirrors firm /events discipline |
| A13 | Shariah-compliant screen lens | P3 | Sarwa pattern; underserved niche, cheap to add |

### Options/F&O depth
| # | Feature | Phase | Why / source |
|---|---|---|---|
| A14 | Options chain analytics: IV rank/percentile, OI build-up, PCR (incl. volume PCR — an explicit Sensibull user request) | P2 | Sensibull TradingQnA feature-gap mining |
| A15 | Historical chain replay + options backtests on OUR 1-min index data (credit-premium priced) | P2 | Opstra pattern but with better data; monetizes moat |
| A16 | Payoff/strategy builder with margin estimate | P2 | Table stakes for F&O audience; feeds Strategy Lab |
| A17 | Paper-trading/forward-test sandbox with honest fills + one-tap virtual→real conversion (top Sensibull user request) | P2-P3 | Firm forward-test discipline productized; conversion feature needs execution-helper compliance check first |
| A18 | Expiry-day dashboard (0DTE flows, straddle prices, pin risk) | P3 | Growing 0DTE cohort; our 1-min data shines |

### AI-native
| # | Feature | Phase | Why / source |
|---|---|---|---|
| A19 | "Why did MY portfolio move" daily brief (holdings-aware AI narration, citations) | P2 | Robinhood Cortex pattern minus execution; retention |
| A20 | AI concall/annual-report Q&A grounded in our doc store | P2 | Screener.in "Screener AI" precedent; BYOK-friendly |
| A21 | **Xorlog MCP server** — user's own Claude/ChatGPT can call our screener/data/backtest as tools | P2-P3 | Fiscal.ai/Zacks distribution-as-data; perfect BYOK fit; also a dev-community wedge |
| A22 | AI strategy-improvement loop with honesty guardrails (agent proposes variants, ALWAYS shows overfit/DSR warning as variants multiply) | P2 | Our overfit discipline as UX — nobody else will do this honestly |

### Community/growth (P3, compliance-gated)
A23 Verified-holdings badges (Toss) · A24 anonymized portfolio sharing (Getquin) · A25 strategy gallery with mandatory honesty reports (Composer, minus return-claims — Tradetron enforcement precedent) · A26 morning pre-open global digest (Kakao/Siebert) · A27 vernacular/Hindi UI (PX→P3, first-time-investor cohort).

### B2B (parked, PX)
A28 White-label analytics for RAs/RIAs/PMS (Koyfin advisor pattern) · A29 data/score licensing into enterprise AI copilots (Zacks pattern) — both only after retail traction + track record.

## B. What's MISSING from the plan (structural, not features)
| # | Gap | Severity | Action |
|---|---|---|---|
| B1 | **Security & key custody** — we will hold users' BROKER API keys (order-placement power!) + LLM keys. Encryption at rest/in transit, scoped permissions, key-vault design, breach plan, India data residency, "we never train on your data" policy | CRITICAL | Design doc before ANY user data; it's also a marketing asset (Parqet privacy pattern). Add to Phase-1 gate |
| B2 | Tax engine absent from v1.1 plan | High | Added as A1; consider it MVP-adjacent |
| B3 | Alerts engine absent | High | Added as A7 |
| B4 | Support ops for broker-sync failures — the #1 trust-breaker (TradeZella 37% lesson) needs a support SLA + status page, even solo | High | Status page + in-app sync-health indicator from day 1 |
| B5 | Instrumentation/north-star undefined | High | Proposal: north star = weekly-active journaled traders (WAJT); activation = first broker import <10 min from signup; PostHog events spec'd before MVP code |
| B6 | ToS/privacy policy/entity — needed before first user, not first revenue | Medium | Bundle into the lawyer consult |
| B7 | **Zerodha fast-follow defense** — they bundled Sensibull+Streak free; they could bundle a journal | Medium | Moats: multi-broker neutrality (Zerodha won't sync Angel/Dhan), honesty-grade backtests (data+discipline they lack), AI-native BYOK, tax multi-broker. Write positioning one-pager |
| B8 | Backup/DR for user data | Medium | Supabase PITR + R2 backups; document RPO/RTO |

## C. Think about (strategic questions, no answer forced yet)
1. Mobile timing: PWA-first (offline-capable, Stonk Journal pattern) vs native — PWA until 10k users, then decide.
2. Bootstrapped vs raise: credits model = revenue from month 2-4; decide only if MRR gate misses.
3. Solo-founder bandwidth: MVP order journal→screener→AI is also a build-effort order; cut scope, not sync-reliability.
4. Pricing psychology: annual anchor (₹4,999) vs monthly; free credits on referral (waitlist mechanics reuse).
5. Community moderation cost + SEBI exposure (user-posted stock calls on OUR platform) — needs rules + moderation before any social feature; Telegram enforcement climate noted in research.
6. Data pipeline ops: our lake updates need daily automation on a machine we control (currently laptop-bound; Railway cron later).
7. Name check "Xorlog" still pending (trademark/domain/app-store collisions).

## D. Explicitly rejected (with reasons — don't re-add without new evidence)
Copy-trading humans (eToro — regulatory+concentration) · autonomous AI execution (Cortex — SEBI collision) · fantasy-trading contests (StockGro — scrutiny magnet) · unregistered paid calls in ANY wrapper (enforcement cases) · raw data resale without NSE licence (see plan §5 caveat).

## E. Zero-cost features (buildable now — ₹0 incremental, from existing data/free tools/founder time)
| # | Feature | Phase | Why / source |
|---|---|---|---|
| E1 | Circuit/thin-volume risk flag on any stock/screen result | P1 | Turns an internal landmine we already know cold (circuit-lock + thin-volume fill risk, `lib/execution_realism.py`, COST_STANDARDS §Dynamic slippage) into a user-facing informational safety flag — mechanics-only, no buy/sell opinion, reuses an existing pipeline, zero new data cost. Nobody in 01_RESEARCH turns this into a customer feature. |
| E2 | "Second opinion" tip base-rate checker | P1-P2 | User pastes a stock + a tip they received; tool shows the historical base-rate behavior of similar technical/fundamental setups WITHOUT a call on that specific stock — pure repurposing of the backtest engine, anti-tip-channel positioning, genuinely shareable ("check before you buy"). Needs the same compliance one-pager as every feature (statistical/pattern level, never personalized). |
| E3 | Free cost-of-trade calculator, no login | P0-P1 | Static brokerage+STT+slippage math as an embeddable public widget — zero incremental cost, strong SEO/lead-magnet, top-of-funnel traffic before anyone signs up. |
| E4 | Public "Data Honesty Scorecard" | P0-P1 | Educational page grading COMMON DATA PRACTICES (survivorship bias, PIT-correctness) in the abstract — not naming competitor products by name (defamation exposure) — using lessons the firm already paid for internally. Zero cost, high authority-building value, feeds SEO. |
| E5 | Broker-cost/fit comparator using the user's OWN journal | P1-P2 | "Which broker is actually cheapest for how YOU trade" — compares BROKERS, not securities, likely outside RA scope. **[INTERPRETATION — re-verify the Jan-2025 finfluencer-referral circular doesn't reach neutral broker-comparison content before ever monetizing this via referral.]** |
| E6 | Founder-curated free screener template packs | P1 | 5-10 hand-picked, well-explained screens published free (human-curated, not algorithmic at first) — zero build cost beyond the screener itself, seeds the framework-builder pillar, demonstrates expertise pre-launch. |
| E7 | Free public "explain this filing" AI micro-tool, no login | P1 | Paste any NSE announcement/filing text → plain-English summary via a FREE-TIER model (Gemini/Sonnet free plan — see free_ai_models_benchmarks.md — NOT our paid tokens) — zero-cost demo of the AI pillar, drives signups. |
| E8 | "How backtests lie" weekly public teardown series | P0-P1 | Repeatable version of the T1 survivorship-bias artifact (HANDOFF_DESK100.md) — zero cost beyond founder time, compounds SEO + trust, and is exactly the methodology-level content the regulatory line allows pre-RA. |
| E9 | Founder-moderated Discord/Telegram (education/discussion only, no calls) | P1 | Free tools, zero build cost; strict no-stock-call moderation matches the compliance line anyway — turns a compliance constraint into the community's actual identity ("the place with no tip-mongers"). |
| E10 | Referral-based waitlist queue-jump | P0 | ₹0 to build on the Supabase waitlist table already planned (HANDOFF_DESK100.md T3); Jupiter Money pattern (ux_growth_resources.md). |

## F. Manual / "do-things-that-don't-scale" concierge features (human-powered, zero build cost)
| # | Feature | Why |
|---|---|---|
| F1 | Founder-run white-glove onboarding for the first 20-50 users (manual trade import + a call/DM) | Maximum insight for MVP prioritization at zero engineering cost — classic early-stage pattern; also doubles as F5's interview channel. |
| F2 | Founder personally writes the weekly digest before any automation exists | Builds the content habit-loop and proves the format before ever paying to automate it. |
| F3 | Personal reply to every waitlist signup while the list is still small | Zero cost, outsized perceived care — differentiates from every incumbent's support experience (see B4 broker-sync-support gap). |
| F4 | Founder's own paper-trading journal, run publicly THROUGH Xorlog itself once it exists (dogfooding) | Proof-of-product + content in one motion; same RA-safe framing as everything else — process/methodology commentary, never a call. |
| F5 | Trade 15-min user interviews for early-access/lifetime-discount perks | Currency = founder time + product perks, not cash — feeds T2-T4 build priorities directly. |
| F6 | Founder hand-moderates community flags early | Defers building a moderation system until scale actually justifies the engineering cost. |

## G. China-comparables mined items (from `01_RESEARCH/china_comparables.md`, DONE 2026-07-16)
Every durable Chinese winner (East Money, Tonghuashun, Xueqiu) ran neutral free tools/community for years, then acquired a licence onto that audience — the exact Phase 0→2 sequencing Xorlog already plans, now externally validated at 100M-user scale. Features below are what that cohort proves are worth building; each tagged with its regulatory guardrail because the China market already litigated the "is this advice?" line.
| # | Feature | Phase | Why / source (China comparable) | Regulatory guardrail |
|---|---|---|---|---|
| G1 | **Natural-language screener** — plain-English query ("ROE>15% 3yrs, FII buying, near 52w high") → screened list on top of the neutral-metric engine | P1 | HIGHEST-conviction import. Tonghuashun's **Wencai** proved NL screening is mass-retail behavior at 100M+-user scale a *decade* before LLMs; no India incumbent does it well; LLMs make it near-free to build now | Output = a filtered list from user-stated criteria (neutral tool). Must NOT auto-rank into a "top pick" verdict pre-RA |
| G2 | **Platform-verified STRATEGY track record** — rule-based strategies (not stock lists) with every signal/rebalance timestamped and logged by Xorlog, tamper-proof, publicly followable | P2-P3 | Xueqiu's timestamped portfolio "cubes" (broadcast rebalances) are its stickiest mechanic (46 min/day engagement). Verified-by-platform beats self-reported | Dec-2024 SEBI amendment sweeps named-stock model-portfolios-with-track-record into RA scope → attach the mechanic to STRATEGIES/frameworks pre-RA, named-stock portfolios only post-RA |
| G3 | **Per-stock / per-strategy community pages** — permanent discussion page per ticker/strategy (doubles as the programmatic-SEO surface in dist plan §3) | P2 | East Money's **Guba** (per-stock boards, ran 7 yrs before any licence) = community + SEO in one structure; same insight as Screener.in per-company pages | Guba is where pump-and-dump lives; SEBI hostile to unmoderated tip-flows → moderation + no-calls norms + no-named-recommendation rule baked in from day 1 |
| G4 | **Aggregated con-call / filing Q&A per stock** — structured "what management actually said" channel per company | P2-P3 | East Money's "Ask the Board Secretary" (companies answer retail) has NO India equivalent (SCORES is complaints-only); even an unofficial con-call-Q&A aggregation is differentiated | Factual aggregation of public disclosures — neutral, no interpretation-as-advice |
| G5 | **Grounded BYOK AI (no verdicts)** — LLM answers strictly grounded in Xorlog's curated NSE/BSE data, ships analysis/summaries/NL-screening, never a templated per-stock buy/sell | P1 | ALL FOUR Chinese platforms (HithinkGPT, Miaoxiang, TigerGPT, Moomoo AI) ground their LLM in proprietary data, ship as free retention, monetize data/orchestration NOT "the AI", and STOP at analysis — none emit portfolio verdicts even in China | Confirms Xorlog's existing thesis. CSRC Jun-2026 + SEBI Jun-2025 both converging on "AI output that looks like a recommendation IS a recommendation regardless of authorship" — the no-verdict line is load-bearing, keep it |
| G6 | **B2B data/honest-backtest engine** — sell the parquet lake + survivorship-honest backtester to brokers/institutions once the retail brand exists | P3+ | Tonghuashun's **iFinD** B2B terminal is a second revenue engine on the same data; validated pattern (retail brand first, institutional product second) | Selling data/tools to licensed institutions is outside the RA/advice perimeter — cleaner than any retail-advice line |
| G7 | **Journal-verified position badge** — community posts carry a Xorlog-verified "this trade is real" badge sourced from the user's imported journal | P3 | Futu's broker-verified position badges are the single best community-trust mechanic found; our verifier is the journal, not broker custody | Verifies a trade HAPPENED, not that it's a recommendation; keep beta/testimonial screenshots free of named-stock P&L brags (reads as a performance claim) |

**Two meta-lessons from the China regulatory arc (not features, but binding on all of the above):** (1) enforcement is **retroactive and personal** — Futu/Tiger were fined ~₹1,900cr / ~₹420cr equivalent in May-2026 for years-earlier conduct, CEOs personally fined; "everyone does it and the regulator is quiet" ≠ safe. Build compliance-by-design now. (2) **India's open RA regime is a genuine advantage** — China's advice-licence pool has been frozen since ~2016 (you must buy a grandfathered holder); India's ₹15k + NISM-XV + open application is dramatically more accessible, making Xorlog's Phase-2 licence step far easier than the Chinese comparables ever had.

## H. Budget note
The ≤₹10,000 one-time bootstrap budget (domain, NISM-XV exam, trademark search, hosting buffer, lawyer consult) is itemized in `00_VISION_AND_PLAN.md` §7b, not repeated here — every feature above was chosen specifically because it needs ₹0 of that budget.
