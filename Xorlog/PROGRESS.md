# XORLOG — PROGRESS CHECKPOINT
Goal: Build the plan + market research for Xorlog — an India-focused invest/trade platform (journaling, API trading, BYO-LLM research, framework-based recommendations, strategy builder, screener). Bootstrap-funded, phased, license-light MVP first.

## Status: HANDED TO DESK-100 (2026-07-16) — research+plan+backlog done on DESK-20; execution queue T1-T5 lives in HANDOFF_DESK100.md (T1 survivorship artifact → T2 Angel journal-import prototype → T3 landing page build → T4 screener data layer → T5 backlog triage). Outputs land in 03_BUILD/.

## OPEN (Principal decisions pending)
- RA route (individual+NOC vs corporate ₹5.5L vs third-party-RA content) · incorporation · "Xorlog" trademark/domain check · lawyer consult budget (BYOK line, execution-helper classification, NSE data licensing for raw export) · B1 security/key-custody design sign-off before any user data.

## DONE
- [x] Project folder created
- [x] PROGRESS.md checkpoint file

## IN FLIGHT
- [x] global_comparables.md DONE (166 lines; BYOK pricing default $5-15/mo, explainable scores, citation-backed AI, broker-sync = retention lever, Toss simplification)
- [x] india_competitors.md DONE (176 lines; no incumbent spans all 5 pillars, F&O journaling weakest category, Streak/AlgoTest backtest-fidelity complaints, SEBI algo framework mandatory 1-Apr-2026 bans direct 3rd-party API execution, BYOK AI gap confirmed)
- [x] regulatory_map.md DONE (Dec-2024 amendment: model-portfolio/track-record showcase IS RA scope — resequence P5; individual RA ~₹15k + deposit + NISM-XV, 4-8mo; BYOK AI unsettled → lawyer sign-off + no verdict-style output; brokers fined for integrating with dirty platforms)
- [x] ux_growth_resources.md DONE (UI/UX sites: Refero+Dribbble+land-book best free fintech refs; component stack shadcn+Tremor+lightweight-charts[Apache2.0+attribution req'd]+Recharts+AGGrid Community = ₹0 licence cost; stack rec = Cloudflare Pages+Workers+R2 (NOT Vercel Hobby — its ToS bars commercial use) + Supabase free + Railway for compute, ~₹500-1.4k/mo at 0-1k users, ~₹5-7k/mo at 10k; broker API table — Angel/Dhan/Fyers/Upstox/5paisa/Shoonya all free incl. order placement, Zerodha needs ₹500/mo+compliance approval for multi-user; SEBI algo framework live 1-Apr-2026 (Algo-ID, static IP, empanelment) applies to ALL brokers → auto-execution is Phase-2+, manual order ticket is the MVP-safe path; distribution: programmatic per-stock SEO pages (Screener.in pattern) + founder's 23k LinkedIn + fintwit as cheapest channels, Telegram/WhatsApp fine for community but SEBI is actively enforcing against stock-tip language there in 2026)
- [x] Synthesis DONE → 00_VISION_AND_PLAN.md v1.0 (thesis, 3 validated wedges, regulatory split-structure architecture, phased roadmap P0-P3 with gates+kill conditions, pricing bands, final stack, 90-day procedure, open Principal decisions)
- [x] v1.1 (Principal direction 2026-07-16): pricing switched to SUBSCRIPTION+CREDITS hybrid (credits for backtests/optimize/AI-agent runs, journal never credit-gated, non-expiring top-ups, 1-min options backtests priced premium); AI Trading Coach added (v1 Phase-1 computed diagnostics + AI narration, v2 Phase-2 deep reports/style classification); data-selling = compute-on-data only, raw export needs NSE licence check [flagged to counsel list]
- [x] free_ai_models_benchmarks.md DONE (AA Index /100 as of 2026-07-16: Fable 5 = 60 #1, Opus 4.8 = 56, Sonnet 5 = 53 free-on-claude.ai; best free: GLM-5.2 51, Gemini 3.5 Flash 50, Grok 4.5 54 rate-limited, Qwen3.7 46, DeepSeek V4/Kimi K2.6 44; gotchas: Copilot Free trains on code by default, GitHub Models retiring 2026-07-30, Qwen Code free OAuth dead, financial-hallucination bench shows free/open models weakest)

## NEXT STEP (if resuming after token cut)
1. Check which files exist in Xorlog/01_RESEARCH/ — each agent writes incrementally, so partial files are still usable.
2. If wave 1 files exist but wave 2 missing → launch wave 2 (regulatory + UX/growth agents, prompts described below).
3. If all 4 research files exist → write 00_VISION_AND_PLAN.md synthesizing them (structure: vision, regulatory sequencing, phased roadmap P0→P3, MVP spec, data moat, distribution plan, pricing, skills to build).

## Wave definitions (for resume)
- Agent A (india_competitors.md): map Screener.in/Tickertape/Trendlyne/StockEdge/Sensibull/Streak/Tradetron/AlgoTest/smallcase/Univest/Chartink etc — features, pricing, user complaints from Reddit/PlayStore/TradingQnA, feature demands, gaps.
- Agent B (global_comparables.md): US/EU/UAE/Japan/Korea comparables — TradingView, TrendSpider, Composer, QuantConnect, Danelfin, Edgewonk/Tradervue/TradesViz (journaling), Toss (UX), baraka/Sarwa (UAE), moomoo JP — features worth importing, AI-research UX, monetization.
- Agent C (regulatory_map.md): SEBI RA/IA regs — what needs license vs not, RA registration cost/steps/timeline, Feb-2025 algo framework, how Sensibull/Streak/smallcase structured legally, enforcement examples vs unregistered advisory.
- Agent D (ux_growth_resources.md): UI/UX inspiration sites (Mobbin, Godly, shadcn, 21st.dev, Tremor, lightweight-charts), free/cheap infra stack, India broker APIs (free: Angel/Dhan/Fyers), distribution playbooks (SEO programmatic, YouTube, fintwit, Varsity content moat).

## Key constraints (from Principal, 2026-07-16)
- Max 2 parallel agents; bank every step to disk.
- Low funds → phased deployment; build distribution channel alongside product.
- No SEBI license at start → plan MUST sequence: Phase 1 = only genuinely license-free features (tools/screener/journal/BYO-API AI); paid recommendations ONLY after RA registration. No "under the radar" advisory — enforcement risk kills the startup.
- Data assets in hand: survivorship-bias-free daily equities, stock options daily + index options 1-min, 4-5yr of 1-min stock data.

## v1.2 IN FLIGHT (2026-07-16, Principal direction: zero-cost features + China/cross-region + ≤₹10k budget + post-MVP zero-cost distribution)
- [x] china_comparables.md DONE (Xueqiu/East Money/Tonghuashun/Futu/Tiger + AI-cohort subsection + CSRC-vs-SEBI + synthesis + sources log). Survived 2 mid-write session restarts; landed on the 3rd resume via incremental-write orders. KEY: East Money sequencing (free content/community/tools → audience → acquire licence → monetize) = Xorlog's Phase 0→2 validated at 100M-user scale; India's open RA regime is EASIER than China's frozen advice-licence pool; NL screening (Wencai) is the highest-conviction feature import; both CSRC + SEBI converging on "AI verdict = advice regardless of authorship".
- [x] zero_cost_growth_tactics.md DONE (China/Korea/Japan/UAE/EU/US+India per-region case studies, each with →Xorlog line + [DATA]/[ANECDOTE]/[INFERENCE] tags; LinkedIn-23k conversion §7; 12-tactic 90-day table §8). KEY: 2026 LinkedIn reach is 8-12% of followers AND comment-link workaround now suppressed → funnel must route around the feed (Newsletter + profile-as-landing + carousels + human DMs); realistic sequence yield 300-800 waitlist emails (clears ≥500 gate) vs 30-80 for a lone post.
- [x] SYNTHESIS DONE (this session, 2026-07-16 DESK-20/Opus): `04_DISTRIBUTION_ZERO_COST.md` → v1.0 (§3 launch playbook filled, §4 China+cross-region engines, §5 12-week calendar table); `02_FEATURE_BACKLOG.md §G` → 7 China-mined features (G1 NL screener … G7 journal-verified badge) each phase-mapped + regulatory-guardrailed, plus 2 meta-lessons (retroactive/personal enforcement; India's open-RA advantage).
- **v1.2 COMPLETE.** All research + plan + backlog + distribution now content-complete on DESK-20. Nothing further buildable here without Principal input — next is DESK-100's T1-T5 build queue (HANDOFF_DESK100.md) + the OPEN Principal decisions above.
- [x] 02_FEATURE_BACKLOG.md §E (zero-cost features) + §F (manual/concierge features) — written directly, no agent needed (synthesis from existing research + product judgment)
- [x] 00_VISION_AND_PLAN.md §7b — itemized ≤₹10,000 one-time budget table with an explicit trademark-filing-now vs lawyer-consult-now trade-off FLAGGED for Principal, not decided silently
- [x] 04_DISTRIBUTION_ZERO_COST.md — skeleton + known generic tactics written; full fill pending the two agents above; explicitly sequenced to ACTIVATE post-MVP per Principal's latest instruction (Phase-0 seeding unchanged)

## NEXT STEP (if resuming after token cut, v1.2)
1. Check Xorlog/01_RESEARCH/ for china_comparables.md and zero_cost_growth_tactics.md — if both present, synthesize into 02_FEATURE_BACKLOG.md §G and fill 04_DISTRIBUTION_ZERO_COST.md §3-5.
2. If only one present, the other agent may still be running — check for a running-agent notification before relaunching (avoid duplicate spend).
3. Update this file + firm SESSION_JOURNAL/CURRENT_STATE once this pass is fully banked.
