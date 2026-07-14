# BUILD_ADDENDUM_v1 — Principal's factor mandate + firm standards seed
2026-07-03 · filed by DESK-20 · **Status: DRAFT — prompts & costs become binding only after Principal approves each item (D-020)**
Companion: `01_COMMAND_CENTER/WORK_ORDER_DESK100_BUILD.md` (what to construct). This file = what goes inside.

---
## 1. FACTOR LIBRARY v1 (Principal directive — the research universe)

**Traditional factors (long-term, academically validated premia):**
| Factor | Definition | Primary metrics |
|---|---|---|
| Value | cheap vs fundamentals | earnings yield, P/B, P/CF, EV/EBITDA |
| Quality | durable profitability | ROE/ROCE, low leverage, earnings stability, F-score, accruals |
| Momentum | 6–12M price movement | 12-1 momentum, 3/6 month momentum, 52w-high proximity, residual momentum, sectoral momentum, VCP breakout, channel breakout, uptrend over long term but short term downtrend followed by a channel breakout, multi-year high, new trigger (Earning, sector, theme, product, revenue, government rule) movement or gapups/PEAD|
| Size | smaller-cap premium | mcap rank — trade only WITH quality(top 90%ile) + liquidity screens(ADV(20d) 5cr+) |
| Earnings Revision | analyst upgrades, surprise | SUE, beat/miss streaks, revision breadth | Higher the better, 25%+ is exceptional 
| Microstructure | flow/liquidity effects | volume spikes, Amihud illiquidity, VWAP deviation, auction behavior |
|Volume| Behaviour of price with volume | Sudden rising volume or decreasing volume | exceptionally high volume (10%ile) | gapup or 5%+ move with high volume
|Overbought | lowest point of last 20day % above from 200dma | ATR above from 50dma (>8x starting dangerous and 10ATR above 50dma is final, unless very low liquid stock or small-microcap stock or too strong fundamnetal backing (1Y forward PE still <30), good time for taking partial profits at minimum) | 30%+ move in a week or 60%+ move in a month |
|Oversold | RSI(28)<30, RSI(14)<20, RSI(5)<10, % Below 50 dma and 200dma and ATR(14) below 200dma and 50dma |


**Commodity sleeve:** Gold = crisis + inflation hedge · Silver = precious + industrial hybrid. ETF route (GOLDBEES/SILVERBEES etc. — tokens already in `datasets/angel_instrument_list.json`), no MCX needed.

**Proprietary edge (beyond traditional):**
| Sleeve | Content |
|---|---|
| Sentiment Alpha | NLP tone on news, social, earnings-call transcripts |
| Flow & Ownership | FII/DII buying pressure, ETF flows, promoter/institutional deltas, order-book & volume spikes, liquidity |
| Event & Seasonality | corporate actions, quarterly patterns, index reconstitution, expiry effects |
| ML Signals | non-linear, regime-specific models (no deep learning for now — D-011) |
|January-Feburary falls and profit booking, negative for momentum and small-microcaps and april recovery in smallcaps|

### Factor → on-disk data map (Data Officer keeps synced with DATA_CATALOG)
- **Value/Quality** → `datasets/screener_deep/` (BS 5,022 · CF 3,000 · PL 6,000 rows), `earnings_pit/ratios_pit`, `mc_fundamentals_parsed` — READY
- **Momentum/Size** → daily prices 2005–2026 + `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots, survivorship-free) — READY
- **Earnings Revision** → NO analyst-estimate feed yet. Proxy NOW: `derived/earnings_beat_miss.parquet` (31,891 rows, SUE-style) + PEAD off `unified_quarterly_pit` (86.2% exact dates). Candidate feed: Trendlyne/MarketsMojo scrape — D-009 gate (sample-verify + Principal approval) — PROXY READY
- **Microstructure** → 813M 1-min bars 2022–2026. LANDMINES: real open = first bar ≥09:15 (auction bug), IST timezone fix — READY
- **Sentiment** → `india_fin_news` (125K, tier-segregated), MoneyControl, TOI headlines, MiMIC 1,042 call transcripts. Model: ProsusAI/finbert (HF); lexicon baseline first — READY
- **Flow & Ownership** → `derived/shareholding_changes.parquet` (21,713 QoQ/YoY FII/DII/promoter). FII/DII daily + bulk/block + SLB fees = NSE-blocked → home-network list — PARTIAL
- **Event & Seasonality** → `derived/corporate_action_factors` (613), PIT earnings calendar, index add/delete from snapshots, OI-surface expiry patterns — READY
- **Options/positioning (firm extension)** → NIFTY+BANKNIFTY OI surface (633K rows): PCR, max-pain, dealer-gamma/GEX = Track-3 H1 — READY
- **ML** → LightGBM cross-sectional ranker (microsoft/qlib pattern); HMM/vol-state regime gates. Rule: linear/rank baseline must clear costs before any ML variant.

**Per-sleeve gate:** IC memo with economic WHY, expected decay horizon, capacity estimate, crowding check — before production.

---
## 2. STANDARD PROMPT CLAUSES v1 (Principal approves one by one → then move to approved/)
- **P-01** Never guess. Missing input/definition → ask, or proceed with the assumption stated LOUDLY at top.
- **P-02** Verify before claiming: every data claim carries file path + row count.
- **P-03** Point-in-time discipline: knowledge date = `available_date`; never quarter-end.
- **P-04** Costs only from `06_TRADING_DESK/COST_STANDARDS.md` once approved; never invent cost/slippage numbers.
- **P-05** Report failures verbatim (exact error text); never smooth over.
- **P-06** Checkpoint long work to files continuously; assume the session can die anytime.
- **P-07** Cheapest model that does the job (TOKEN_POLICY); escalate only for judgment work.
- **P-08** "I don't know" and "this idea is dead" are paid-for outputs. Kill fast; log kills with resurrection conditions (D-012).
- **P-09** Adversarial self-check before submitting: what would Red Team say?
- **P-10** New external data → Data Officer sample verification + Principal approval first (D-009).
- **P-11** Every backtest reports deflated Sharpe + PBO next to raw Sharpe; flag n<30 trades or >5 parameters.
- **P-12** Memos tag every claim **[DATA] / [INFERENCE] / [OPINION]**.

---
## 3. COST_STANDARDS skeleton (retail-conservative; Trading Desk formalizes; DRAFT until Principal approves)
- Brokerage: ₹20/executed order (discount broker)
- STT: delivery 0.1% both sides · intraday 0.025% sell · futures 0.02% sell · options 0.1% of premium (sell side)
- Exchange txn: NSE equity ~0.00297% · options ~0.035% of premium · GST 18% on (brokerage+txn) · SEBI ₹10/cr · Stamp: 0.015% delivery buy / 0.003% intraday & options buy / 0.002% futures buy
- Slippage floors (one-way): large-cap 10bps · mid-cap 20bps · small-cap 35bps · micro 50bps+ · options max(1 tick, 0.5% of premium), illiquid strikes 1–2%
- Liquidity: position ≤10% of 20d ADV (≤5% microcaps) · skip circuit-locked names
- Promotion rule: every strategy must survive **2× all of the above** before advancing to paper.

---
## 4. REFERENCE LIBRARY (seed for 04_RND_LAB/KNOWLEDGE_BASE)
**Books:** Lopez de Prado — *Advances in Financial ML* + *ML for Asset Managers* · Grinold & Kahn — *Active Portfolio Management* · Ilmanen — *Expected Returns* · Gray & Vogel — *Quantitative Momentum* · E. Chan — *Algorithmic Trading* · Minervini — *Trade Like a Stock Market Wizard* + *Think & Trade Like a Champion* · Weinstein — *Stage Analysis* · O'Neil — *How to Make Money in Stocks (CANSLIM)*
**Papers (search by title):** Jegadeesh & Titman 1993 (momentum) · Fama-French 2015 (5-factor) · Novy-Marx (gross profitability) · Piotroski (F-score) · Sloan (accruals) · Bernard & Thomas (PEAD) · Frazzini-Pedersen (Betting Against Beta) · Asness et al (Quality Minus Junk) · Harvey-Liu-Zhu (multiple testing; demand t>3) · Bailey & Lopez de Prado (Deflated Sharpe, PBO) · McLean & Pontiff (post-publication alpha decay) · Raju, SSRN (momentum/factor evidence in India)
**Repos:** microsoft/qlib · polakowo/vectorbt · stefan-jansen/machine-learning-for-trading · stefan-jansen/zipline-reloaded · alphalens-reloaded · pyfolio-reloaded · ranaroussi/quantstats · dcajasn/Riskfolio-Lib · skfolio/skfolio · twopirllc/pandas-ta · hudson-and-thames/mlfinlab · OpenBB-finance/OpenBB · jugaad-py/jugaad-data (NSE — proxy-blocked at office) · **wilsonfreitas/awesome-quant (master index)**
**HF models:** ProsusAI/finbert (news tone) · FinGPT (reference only)
**Agent/prompt craft:** docs.claude.com → sub-agents + prompt-engineering · anthropic.com/engineering/building-effective-agents · anthropic.com/engineering/claude-code-best-practices · github.com/anthropics/skills
**India method refs:** NSE index methodology PDFs · SEBI circulars · AMFI · screener.in · trendlyne.com (candidate estimates feed — D-009 gate)
**GPU escape hatch (D-011):** Kaggle 2×T4 ~30h/wk or Colab — export parquet → train → import model.

---
## 5. BACKTEST HONESTY CHECKLIST (Red Team gate — ALL must pass; wire into 07_RISK_OFFICE/ADVERSARIAL_REVIEWS)
PIT universe from 42 snapshots · `available_date` fundamentals · IST timezone fix · first bar ≥09:15 · option 17-month gap acknowledged · costs per §3 + 2× stress · ADV caps · walk-forward with ONE final untouched OOS · deflated Sharpe + PBO reported · ≥30 trades per parameter, ≤5 parameters · regime slices (2018 / 2020 / 2022 / 2024 / 2026) · capacity estimate · economic WHY written BEFORE testing · kill-criteria pre-registered · outcome logged (STRATEGY_REGISTER or KILLED_IDEAS).

---
## 6. GOVERNANCE EXTRAS (CIO/FM adopt or reject)
- `WAR_ROOM.md` — one live file both desks update during market hours.
- Monthly edge-decay review: every sleeve re-scored; 2 consecutive fails → auto-demote to paper.
- Resurrection conditions mandatory on every kill (D-012) — e.g., option BUYING stays dead UNLESS a sniper-entry variant shows <5 trades/mo AND net-positive after 2× costs.
- PAPER_LEDGER reconciled weekly against Angel quotes (fill realism).
- Quarterly red-team audit of the FIRM'S PROCESS itself, not just positions.

---
## 7. RESEARCH LOOP SOP (every idea walks these 8 steps; no skipping)
1. **INTAKE** — hypothesis one-pager (template below) → row in IDEA_PIPELINE. No one-pager, no work.
2. **TRIAGE** (FM + Quant, ≤30 min, cheap tier) — economic WHY plausible? data on disk? capacity ≥ target? → KILL or proceed.
3. **CHEAP TEST** — the single cheapest falsification (event study / decile spread / one-year slice). Kill threshold pre-registered BEFORE touching data.
4. **FULL BACKTEST** — per §9 code checks + §10 validation battery.
5. **RED TEAM** — one focused attack (D-008): "find the single most likely reason this is fake" + §5/§9 placebo battery. Verdict: REAL / FRAGILE / FAKE.
6. **IC MEMO** — verdict, sizing, kill criteria, review date → STRATEGY_REGISTER.
7. **PAPER** — ≥20 trades or 8 weeks (whichever is LATER); weekly reconcile vs Angel quotes; sim-vs-paper tracking error logged and explained.
8. **LIVE GATE** — Principal only (D-010).
Every kill at any step → KILLED_IDEAS with resurrection condition (D-012). Count and log EVERY variant tried (needed for §10 trials accounting).

**Hypothesis one-pager template:** name · one-line edge · economic WHY (who loses money to us and why do they keep doing it — forced / behavioral / structural?) · factor sleeve (§1) · universe · holding period · expected decay horizon · capacity estimate · data needed (on disk? Y/N) · cheap-test design · pre-registered kill criteria · trials run so far on this family.

---
## 8. STANDARD RESEARCH PROMPTS (RP-01…RP-10 — drafts; Principal approves one by one)
- **RP-01 Idea intake:** "Formalize this idea into the §7 one-pager. Any unknown field = write UNKNOWN, do not invent. End with the single cheapest test that could kill it."
- **RP-02 Cheap test:** "Design and run the minimal falsification for <H>. Pre-register the kill threshold before touching data. Output: PASS/KILL + evidence table + trials count."
- **RP-03 Backtest spec:** "Write the full spec (universe, PIT joins, signal, sizing, costs per COST_STANDARDS, walk-forward windows) BEFORE any code. List every free parameter and justify it. Max 5."
- **RP-04 Code review:** "Review this backtest code ONLY for: lookahead, merge row-blowups, silent NaN drops, same-bar signal+entry, costs actually applied, §9 landmine guards present. Cite line numbers. Ignore style."
- **RP-05 Red team:** "You are the Devil's Advocate. One focused attack: the single most likely reason this result is fake. Run the §9 placebo battery. Verdict REAL/FRAGILE/FAKE + evidence."
- **RP-06 IC memo:** "Synthesize into IC_MEMO_TEMPLATE. Tag every claim [DATA]/[INFERENCE]/[OPINION]. End with: size, kill criteria, next review date."
- **RP-07 Data intake (Data Officer):** "Sample 100 rows; check schema, dtypes, nulls, dupes, date monotonicity, PIT safety; cross-check 5 values against an independent source. Verdict + DATA_CATALOG entry draft. No new source goes live without this (D-009)."
- **RP-08 Post-mortem:** "Paper/live diverged from sim: decompose the gap into slippage / fill-rate / timing / signal-decay. Propose ONE fix. If costs were optimistic, draft the COST_STANDARDS amendment."
- **RP-09 Analyst deep-dive:** "Run the §13 forensic checklist on <name>. Output: verdict, 3 strongest bear points, and what evidence would change your mind."
- **RP-10 Technical scan:** "Apply the §13 Minervini trend template to <universe>. Return ONLY names passing ALL criteria, with stage, pivot, and risk level per position."

---
## 9. CODE CHECKS (mandatory before trusting ANY backtest output)
**Landmine guards — paste into every backtest entry point:**
```python
from datetime import time
# L1 HF timezone bug: daily 18:30 UTC == next-day 00:00 IST
assert df["timestamp"].dt.tz is not None, "tz-naive timestamps"
df["date"] = df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.date
# L2 pre-open auction bug: real open = first bar >= 09:15
intraday = intraday[intraday["timestamp"].dt.time >= time(9, 15)]
# L3 PIT: never act on data before it was public
assert (signals["available_date"] <= signals["action_date"]).all(), "LOOKAHEAD"
# L4 merge safety: joins must not create/destroy rows silently
n0 = len(a); m = a.merge(b, on=k, how="left"); assert len(m) == n0, "merge blew up rows"
# L5 same-bar sin: signal computed on bar t must trade at t+1 (or t close -> t+1 open)
# L6 option data gap: assert no trades generated Apr-2024..Aug-2025 in single-stock options
```
**Post-run degenerate detectors (any hit = assume bug until proven otherwise):**
- Daily-strategy Sharpe > 4, or CAGR > 60% with MaxDD < 10%
- Win rate > 75% with avg-win/avg-loss < 0.5 → tail-seller profile: check 2020/2022/2024 crash slices
- >30% of total P&L from one symbol/expiry, or top-5 trades removed → strategy goes negative
- Equity curve R² vs straight line > 0.98 (too smooth = accounting bug)
- Implied participation > 10% of 20d ADV anywhere (capacity fiction)
- Trade-level P&L sum ≠ equity-curve delta (leak in accounting)
**Placebo battery (Red Team runs; strategy must FAIL the placebos, pass the real):**
- Lag signal +1 day → performance must DEGRADE (if it improves: lookahead)
- Shuffle signal cross-sectionally within each date → Sharpe ≈ 0 expected
- Random-entry benchmark at same trade frequency → real must beat it decisively
- 2× costs rerun (promotion rule §3) · bootstrap 1,000 resamples → 5th-pctile CAGR > 0

---
## 10. STATISTICAL VALIDATION PROTOCOL
- **Walk-forward:** train 3y → validate 1y → roll 6m. Params frozen per window. Grid ≤ 3×3. The most recent 12m = FINAL untouched OOS, opened exactly ONCE per strategy family.
- **Plateau rule:** best cell must not beat its parameter-neighborhood median by >20% — else it's a spike, not an edge.
- **Deflated Sharpe (Bailey & López de Prado):** DSR > 0.95 to promote, computed with the HONEST trials count from §7 (every variant ever run on the family, including kills).
- **PBO (CSCV):** < 25% to promote.
- **Regime slices:** 2018 smallcap crash · 2020 COVID · 2022 rate shock · 2024 election vol · 2026 YTD — no catastrophic slice.
- Minimums: ≥30 trades per free parameter; ≤5 free parameters (P-11).

---
## 11. RUN & RESULTS ENGINEERING (no more lost/overwritten results)
- Every run: `results/<strategy>/<run_id>/` where run_id = `YYYYMMDD_HHMM_<confighash8>`. Contents: `config.json` (full param dump), `metrics.json`, `trades.csv`, `equity.png`. NEVER overwrite a run dir.
- Log the data snapshot: file paths + row counts + max(date) of every input parquet into `config.json` (a backtest that can't name its data is void).
- One shared guards module (work order adds `04_RND_LAB/lib/guards.py`) — landmine checks imported, not copy-pasted.
- Seeds fixed; any randomness logged. Re-run of same config must reproduce metrics to the rupee.

---
## 12. PAPER-TRADING SOP + STRATEGY DEFINITION-OF-DONE
**Paper SOP:** every signal logged BEFORE market action (timestamp, intended price, size); fills marked against actual Angel quotes at action time; weekly reconciliation → tracking-error decomposition (slippage / timing / missed fills); PAPER_LEDGER is append-only.
**Definition of DONE (live-candidate):** survived 2× costs · DSR > 0.95 & PBO < 25% · no catastrophic regime slice · capacity ≥ 3× intended size · paper ≥20 trades/8wk with tracking error explained · Red Team verdict REAL · kill criteria + review date in STRATEGY_REGISTER · Principal sign-off (D-010).

---
## 13. ANALYST DESK CHECKLISTS
**Fundamental forensic (India-specific red flags):** promoter pledge % + trend · related-party transactions · auditor resignation/change · CFO/Company-Secretary exits · receivables growing faster than revenue · CWIP-to-assets games · loans/guarantees to subsidiaries · contingent liabilities vs net worth · interest income implies less cash than reported · dividends vs FCF mismatch · abnormal tax rate · equity dilution history. PIT rule: judge only on what was knowable at `available_date`.
**Minervini trend template (ALL must hold):** close > 150d & 200d MA · 150d > 200d MA · 200d MA rising ≥22 sessions · 50d > 150d > 200d · close > 50d MA · close ≥30% above 52w low · close within 25% of 52w high · RS percentile ≥70 vs Nifty-500 universe (12m return rank) · VCP: volume contracting through base, expanding on breakout.
**Earnings-call NLP recipe (data on disk):** MiMIC transcripts → FinBERT tone, prepared-remarks vs Q&A separately → QoQ tone delta · evasion markers (question dodged) · guidance-language shift. Join to prices on `available_date` only.

---
## 14. OPERATING CADENCE
- **Daily (auto, DESK-100):** AngelDailyOptionCapture 15:45/20:00/23:00 IST · EOD_ROUTINE · data freshness ping.
- **Weekly:** paper-ledger reconcile · pipeline triage (FM) · WAR_ROOM cleanup.
- **Monthly:** edge-decay review (all sleeves re-scored; 2 consecutive fails → demote) · token-spend vs TOKEN_POLICY.
- **Quarterly:** red-team the firm's PROCESS · knowledge-base pruning · roster/AlphaPoints settlement · resurrection-conditions review of KILLED_IDEAS.
