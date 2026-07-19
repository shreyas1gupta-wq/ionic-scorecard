# XORLOG — VISION & MASTER PLAN
**v1.0 — 2026-07-16. Synthesized from 01_RESEARCH/ (india_competitors.md, global_comparables.md, regulatory_map.md, ux_growth_resources.md). Research is [DATA]-labeled in those files; this plan is the decision layer.**

---

## 1. One-line thesis
Xorlog is the trading co-pilot for Indian retail: journal → screen → research with your own AI → build & honestly backtest → execute via your own broker — one login for a workflow users today stitch across 4-5 subscriptions (confirmed: no India incumbent spans all five pillars).

## 2. The three validated wedges (from research)
1. **F&O-native trade journal** — the single most under-built category in India. Zerodha Console = tag-filter on P&L; the only real options journal (TradesViz) is USD-priced with derivatives excluded from its free tier, in a market where F&O dominates retail volume. White space: INR-priced, GST-invoiced, multi-leg auto-tagging, Greeks at entry/exit, expiry-day handling.
2. **Honest backtesting on a real data moat** — Streak's most-cited failure is backtest-vs-live mismatch (close-price engine, no slippage; threads literally titled "Pathetic Streak"). We own survivorship-bias-free daily data (PIT NIFTY500 membership), 1-min index options, daily stock options, 4-5yr of 1-min stock data — plus the internal lookahead/fill-realism discipline (T1-T10 taxonomy) incumbents visibly lack. "How backtests lie — and how ours don't" is both the product and the marketing.
3. **BYOK AI research** — Indian traders already run ad-hoc ~$60/mo ChatGPT+Gemini+Claude stacks for stock research; ZERO incumbents wire this in natively. BYOK is now the industry-default AI pricing pattern (JetBrains/Warp/Copilot, 2025). We charge for the data+orchestration layer; the user pays their own token bill ($5-15/mo typical).

## 3. Regulatory architecture (the spine — from regulatory_map.md)
**Template = the proven split structure every incumbent uses** (Trendlyne→Windmill Capital INH200007645, Sensibull→Riskilla INH200006895, Univest→Uniresearch INH000013776, smallcase→licensed managers):
- **Layer 1: Xorlog (tech company, unregistered)** — journal, neutral screener, backtester, BYOK AI, education. Never emits a first-party buy/sell/hold on a named security.
- **Layer 2: research entity (RA-registered)** — added in Phase 2 for the paid recommendations plan and any published model portfolio/track record.

**Hard lines that shape the product (all sourced in regulatory_map.md):**
- Screener stays neutral-metric / sector-index level. A user-adjustable framework builder (USER sets the weights, tool computes the score) = calculator, stays legal. A first-party "Xorlog Score/BUY on INFY" = RA territory (that's exactly why Trendlyne is registered) → post-RA only.
- **Dec-2024 amendment closed the track-record loophole**: published model portfolios / paper track records of named securities = RA-regulated "research services," even without a "buy now." So pre-RA we publish strategy METHODOLOGY research (aggregate stats, factor-level results), never a named-stock model portfolio.
- BYOK AI ships scoped to analysis/explanation grounded in data with citations — NOT templated per-stock buy/sell verdicts. This is the single most unsettled question (SEBI's substance-over-disclaimer posture + Jun-2025 AI/ML consultation paper) → **lawyer sign-off before the paid tier and BYOK tier converge on verdict-style output.**
- Execution helper v1 = pure order terminal: user specifies order, one click, their own broker key, zero Xorlog-side logic. Anything that auto-populates orders from strategies = algo framework (exchange Algo-ID, broker empanelment; black-box also needs RA) → Phase 3 gate.
- No "assured/consistent returns" language anywhere, ever (Tradetron-broker fines, Mar-2026). No broker partnership/referral revenue on rec-features until registered (Jan-2025 finfluencer circular makes the BROKER liable).
- Enforcement is real and fast: Asmita Patel ₹53.67cr impounded, Avadhut Sathe ₹546cr impounded, Yash Garg (a small operator) caught via digital surveillance and banned. "Education" wrappers and disclaimers do not survive contact with SEBI.

**RA path (start the clock NOW, in parallel with the build):** NISM-Series-XV is the bottleneck (slots take up to ~3 months; cert prep 1-2 months) → register for the exam in month 1. Individual RA ≈ ₹15,000+GST + ₹1L security deposit (≤150 clients) + BASL enlistment; corporate ≈ ₹5.5L+GST. Realistic end-to-end: 4-8 months — which is exactly why it runs parallel to Phase 1, not after it. Interim option for faster revenue: host an already-registered third-party RA's content (smallcase/AlgoTest "RA Algos" model). **Open issue: Principal's employment (Ionic Wealth APM) — part-time RA needs employer NOC and caps at 75 clients; outside-business-activity clauses in a SEBI-intermediary employment contract must be cleared first. This may force the corporate-RA or third-party-RA route. Decide in Phase 1.**

## 4. Phased roadmap (each phase has a gate + kill condition)
### Phase 0 — Distribution before product (Weeks 1-6, cost ≈ ₹0)
- Landing page + waitlist. Ship the content engine: 2-3 genuinely useful public artifacts from our data ("every NIFTY500 backtest you've seen is survivorship-biased — here's the honest number", "what Streak's close-price backtests get wrong — measured"). Factor/aggregate level only — no stock calls.
- Founder LinkedIn (~23k followers) + X + Reddit value-posts. Register NISM-XV exam slot. Trademark/domain check for "Xorlog".
- **Gate to Phase 1: ≥500 waitlist emails or clear qualitative pull. Kill/pivot: <100 emails after 6 weeks of real distribution → reposition before building.**
### Phase 1 — MVP (Months 2-4)
- **Journal** (the wedge): broker import (start Angel SmartAPI — free + we have working code; add Zerodha/Dhan/Fyers next), F&O multi-leg auto-tagging, Greeks at entry/exit, mistake/psychology tagging with ONE headline discipline score (Edgewonk "Tiltmeter" pattern), MFE/MAE analytics, pre-trade risk-rule checks (Stonk Journal pattern).
- **AI Trading Coach v1** (the journal's killer feature — "why you fail, what to fix", stocks AND F&O): computed diagnostics FIRST, AI narration second. Cross the user's trade log with our market data lake to compute honest, personal failure diagnostics no incumbent can: loss clustering by time-of-day/day-type (e.g. "your losses concentrate in the first 30 min on gap days"), revenge-trade and oversizing-after-wins detection, expectancy by setup/instrument, premium-selling vs buying edge split, MFE/MAE "profit left on the table", cost drag (brokerage/STT/slippage share of P&L), discipline-score trend. AI (BYOK or hosted) narrates these computed stats with citations to the user's own numbers — grounded, not generic chat. **Regulatory note [INTERPRETATION]: coaching on the user's OWN past behavior/process = behavioral analytics/education, not a security recommendation — stays pre-RA-safe as long as output never says "trade X now"; include in the feature's compliance one-pager.**
- **Screener v1**: neutral metrics, fast (Finviz lesson: speed > AI), user-defined framework builder (user weights → transparent score decomposition, Simply-Wall-St-radar UX).
- **BYOK AI v1**: chat grounded in our structured data with inline citations on every claim (Perplexity Finance pattern — its 92% vs 87% accuracy edge comes from grounding), token-cost meter visible.
- Pricing: free-forever tier (genuinely usable — free-trial-only products lose in India) + ONE paid tier ~₹499-699/mo (₹4,999/yr anchor) sitting in the validated gap between ₹300-400/mo entry tools and ₹1,300-3,000/mo pro tools. Quantity-gated, not feature-gated (TradingView lesson).
- **Gate to Phase 2: 100 paying users OR 2,000 WAU free users; MRR covers infra + RA costs. Kill: <25 paying after 2 months of live selling → narrow to journal-only and re-attack.**
### Phase 2 — Licensed research (Months 4-8; RA process already running)
- RA entity live (own or third-party-hosted) → paid research plan: framework picks WITH the full Danelfin-style explainable decomposition + published methodology + third-party-benchmarked performance (now a compliance requirement anyway). Fee cap ₹1,51,000/family/yr honored.
- Strategy Lab beta: no-code builder benchmarked at "English → backtested strategy in under 60 seconds" (Composer/moomoo bar), honesty report on every backtest (costs, slippage, DSR/overfit warnings, no assured-returns language). **Two run modes, both credit-priced: "I backtest" (user configures, cheaper) and "AI-agent backtest" (agent builds → tests → diagnoses → proposes variants, dearer per iteration; BYOK discount applies).**
- AI Trading Coach v2: monthly deep-dive report (credit-priced beyond the bundled one), style classification (scalper/swing/positional × momentum/mean-reversion × buyer/seller), peer-percentile benchmarks on anonymized aggregates, "what to improve next month" process plan.
- **Gate: research plan ≥₹50k MRR or strategy lab ≥30% of WAU. Kill: research plan <100 subs after 3 months → fold picks into main subscription as a feature, not a product.**
### Phase 3 — Execution & scale (Months 8-14)
- Broker empanelment as algo provider (framework now stable post Apr-2026); auto-populate order tickets, basket execution, strategy deployment with Algo-ID registration; mobile app (offline-first PWA first — India connectivity); community with verified-holdings badges (Toss pattern) + anonymized portfolio sharing (Getquin pattern), leaderboards ONLY with risk guardrails.
- Optional second monetization: Xorlog data/scores as an MCP feed into users' own Claude/ChatGPT (Fiscal.ai/Zacks distribution-as-data pattern) — fits BYOK thesis perfectly.
### Explicitly deferred/rejected
- Copy-trading of human traders (eToro pattern) — regulatory + concentration risk. Autonomous AI execution (Robinhood Cortex pattern) — collides with SEBI. IA/robo-advisory — different, heavier licence; only on a deliberate pivot. Fantasy-trading gamification (StockGro) — scrutiny magnet.

## 5. Pricing — subscription + credit hybrid (Principal direction 2026-07-16)
**Model: flat subscription for the habit layer (journal/screener — near-zero marginal cost, never credit-gated) + CREDITS for every compute/AI-heavy action (backtest, optimize, AI-agent strategy run, deep AI review). Not unlimited-monthly.**
Why credits win here (all research-backed):
- AlgoTest already trained the Indian F&O market on credit-priced backtests (100 backtests = 100 credits, non-expiring) — the mental model exists.
- Solves the bimodal price-sensitivity finding: casual traders stay cheap, power users pay linearly instead of being subsidized by an "unlimited" plan.
- Kills the AI cost-blowout risk (the TradeZella flat-AI-inclusion trap) — every LLM/compute-heavy action is margin-safe by construction.
- Monetizes the data moat directly: a 1-min options backtest costs more credits than a daily-equity one because it IS worth more.

| Tier | Price | Flat inclusions | Credits/mo included |
|---|---|---|---|
| Free forever | ₹0 | Journal (capped executions), basic screener, BYOK chat (capped/day) | small starter pack (taste the backtester) |
| Pro | ~₹499-699/mo (₹4,999/yr) | Uncapped journal + AI coach reports + framework builder + full BYOK | ~2,000-3,000 |
| Research plan (Phase 2, RA) | ~₹999-1,499/mo | Framework picks + model portfolios + hosted AI | bundled allowance |
| Quant (high-ticket annual) | ₹30-60k/yr [ESTIMATE] | API access, 1-min options/equity data backtests in-platform, prop-compliance tracking, priority compute | large bulk allowance |
| Top-ups | ₹199 / ₹999 / ₹2,999 packs [ESTIMATE] | — | non-expiring (AlgoTest pattern); bulk discounts |

**Credit costing (illustrative, price properly in Phase 1 — [ESTIMATE]):** daily-equity backtest 25-50 · intraday 1-min equity 100 · daily options 100 · **1-min index-options backtest 300-500 (the moat premium)** · optimizer sweep = per-variant · AI-agent "build → backtest → diagnose → improve" loop 500-1,000 per iteration (BYOK users pay only the compute portion, ~half — BYOK stays the discount lever) · AI coach deep-dive report bundled monthly in Pro, extra runs cost credits.
**Design rules:** show the credit estimate BEFORE every run; auto-refund failed runs; journal never costs credits (it's the retention organ); in-product name them "credits" not "tokens" (avoids collision with the visible BYOK LLM-token meter).
**Data-selling caveat (IMPORTANT — [INTERPRETATION], verify with counsel + NSE data policy):** we sell BACKTESTS ON the 1-min options data (compute-on-data, results out), NOT raw data downloads/export. Raw redistribution of NSE-derived market data generally requires an NSE data-vendor licence; in-platform compute is the standard workaround (QuantConnect model: data usable in platform, not exportable). Raw-data export = separate licensing decision, not in scope until cleared.

## 6. Distribution plan (runs from week 1)
Founder-led content on the "honest data" angle: LinkedIn (23k) + X + YouTube long-form teardowns; Reddit/TradingQnA genuine value-posts; morning "global context before NSE open" digest (Kakao/Siebert pattern) as a free daily habit hook; community later. Keep Xorlog content firewalled from Ionic/Brand-Desk rules (no stock calls pre-RA — which our regulatory line already enforces anyway).
**Channel priorities (from ux_growth_resources.md):**
1. **Programmatic SEO** — per-stock/per-screen pages on the Screener.in `/company/<ticker>/` template pattern, but differentiated with our PIT/survivorship-honest data (a page Google hasn't seen 50 clones of).
2. **Founder LinkedIn (~23k) + fintwit** — teaching-content-first, never launch-hype; weekly build-log.
3. **Referral/queue-position waitlist** for the first 100-200 beta users (Jupiter Money playbook).
4. Telegram/WhatsApp for community only — SEBI is actively enforcing against stock-tip language there in 2026; our no-calls rule keeps us clean.

## 7. Tech stack (FINAL from ux_growth_resources.md — ₹0 licence cost)
- **Hosting: Cloudflare Pages + Workers + R2 — NOT Vercel Hobby (its ToS bars commercial use).** Supabase free tier (auth+Postgres), Railway ~$5-10/mo for DuckDB/pandas batch compute over our parquet lake, cron-job.org (scheduling), Resend (email), PostHog (analytics).
- **Cost: ~₹500-1,400/mo at 0-1k users; ~₹5-7k/mo at 10k users.** Well under the <₹5k/mo pre-revenue burn target at launch scale.
- **UI: shadcn/ui + Tremor (MIT) app shell/dashboards; TradingView lightweight-charts for price charts (Apache 2.0 — mandatory attribution link); Recharts for business charts; AG Grid Community (MIT) for the screener table.**
- **Broker APIs: Angel One, Dhan, Fyers, Upstox, 5paisa, Shoonya — all FREE including order placement + tradebook import. Zerodha Kite Connect = ₹500/mo per app + compliance sign-off for multi-user products → add later.** Start with Angel SmartAPI (working code in-house), Dhan/Fyers second.
- Data-residency-in-India as a stated trust feature (Parqet pattern). **Broker-sync reliability gets MORE engineering budget than AI features — 37% of TradeZella's negative reviews are sync bugs; Trendlyne lost Angel API access entirely. Multi-source data architecture (exchange archives + multiple broker APIs) is itself a moat vs single-pipe incumbents.**

### 7b. ONE-TIME BUDGET — ≤₹10,000 own-pocket cap (Principal constraint, 2026-07-16)
Hard ceiling until the product earns its own revenue — credits/subscription income funds everything after (see "what revenue unlocks next" below). Infra itself is ~₹0 on free tiers (§7 above); the ₹10k mostly covers the few things that AREN'T free:

| Item | Cost | Timing | Notes |
|---|---|---|---|
| Domain (.in or .com) | ₹500-1,200/yr [ESTIMATE] | After name-availability check (§10) | Buy only once "Xorlog" is confirmed clear |
| NISM-Series-XV exam fee | ₹1,500 [DATA, regulatory_map.md] | Week 1 | Book regardless of final RA route — cert valid 3yr, exam-slot wait is the real bottleneck, not the fee |
| Trademark public search | ₹0 | Immediately | ipindiaonline.gov.in public search — free, do this first |
| Trademark FILING (if done now) | ₹4,500 (individual/startup e-filing rate, 1 class) [UNVERIFIED — reconfirm current fee on ipindia.gov.in before paying] | Optional now vs later | **Directly competes with the lawyer-consult line below — see trade-off** |
| Hosting/infra buffer | ₹500-1,500 | Rolling, 2-4 months | Covers any paid nudge beyond free tiers during the T1-T4 build window |
| Lawyer consult (BYOK-AI line + RA route + execution-helper classification) | ₹3,000-5,000 [ESTIMATE — get quotes; some firms offer a free/cheap first call] | Before Phase-1 gate | The single highest-ROI spend in the whole plan — resolves what the PRODUCT is allowed to do, not just the brand |
| Misc (business email, tools beyond free tiers) | ₹500-1,000 | Buffer | Default to free tiers first (Zoho Mail free, Canva free, Figma free) |

**Trade-off Principal must choose — do not silently split the difference:** filing the trademark now (₹4,500) leaves too little room for a real lawyer consult inside a ₹10k budget. Deferring filing (free search only now, file later once there's revenue) leaves room for both the domain and a proper lawyer session on the BYOK/RA-route question. **Recommendation: defer trademark filing, do the free search now, spend on the lawyer consult** — the legal ambiguity shapes what code gets written; the trademark protects a name that isn't earning anything yet. Flag if the Principal wants it the other way.

**What ₹10k buys:** Phase 0 (landing page, first content artifacts) + the start of Phase 1 build, entirely on free-tier infra + founder time, with the one real legal ambiguity resolved before code assumes a shape that turns out non-compliant.
**What revenue unlocks next (NOT funded by the ₹10k):** Zerodha Kite Connect (₹500/mo, once multi-broker demand justifies it) · paid compute at real scale (Railway/Supabase paid tiers) · trademark filing if deferred · RA registration proper (₹15k+GST individual / ₹5.5L+GST corporate, per regulatory_map.md) · any paid data vendor · any paid distribution (a last resort per `04_DISTRIBUTION_ZERO_COST.md` §6, never assumed by this plan).

## 8. Step-by-step procedure — first 90 days
1. **Week 1**: Name/trademark/domain check. Register NISM-XV slot. Incorporate decision (Pvt Ltd needed before charging). Employer/outside-business clearance question resolved.
2. **Week 1-2**: Landing page + waitlist live. First honest-data artifact published (survivorship-bias piece) on LinkedIn/X.
3. **Week 2-4**: Journal spec + Angel SmartAPI import prototype (reuse existing code). Screener data pipeline from existing parquet lake. Artifact #2 (backtest-honesty teardown).
4. **Week 4-6**: Phase-0 gate review vs waitlist numbers. Lawyer consult booked: BYOK-AI line, execution-helper classification, RA route (individual+NOC vs corporate vs third-party).
5. **Week 6-12**: MVP build (journal → screener → BYOK chat, in that order). Weekly public build-log (distribution). NISM-XV exam taken.
6. **Week 12**: Closed beta to waitlist. Instrument everything. Iterate to Phase-1 gate.

## 9. Compliance standing rules (every phase)
1. Every feature ships with a compliance one-pager (which regulation, why we're clean, what would change the answer).
2. No named-security buy/sell/hold output from anything Xorlog-authored, pre-RA. 3. No performance promises anywhere. 4. Substance test, not disclaimer test. 5. Re-verify the four [UNVERIFIED] regulatory items (BYOK line, exact RA fees, algo-framework dates/OPS threshold, order-terminal classification) with counsel before the corresponding feature ships — list at bottom of regulatory_map.md.

## 10. Open decisions for Principal
1. RA route: individual (+employer NOC, 75-client cap) vs corporate (₹5.5L) vs third-party-RA content first. 2. Incorporation timing + who holds equity. 3. Monthly burn ceiling pre-revenue (target <₹5k/mo infra). 4. "Xorlog" name final? 5. Lawyer budget for the one-time regulatory sign-off (~the highest-ROI spend in the whole plan).

## 11. Claude-side skills/agents for this project
Existing: brainstorming, impeccable/ui-ux-pro-max/design (UI), 21st-cli-use, dataviz, scrapling-official (review mining), deep-research, mcp-builder (broker-API + Xorlog-data MCP), slides/banner-design/brand (marketing), writing-plans, token-wise.
To create: /xorlog-competitor-watch (monthly sweep), /voc-miner (Play-Store/Reddit review refresh), /xorlog-ship (feature → compliance one-pager → landing copy), /honest-backtest-post (data artifact → LinkedIn/X post pipeline).
