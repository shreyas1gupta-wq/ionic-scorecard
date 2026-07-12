# Section 5 — Trading Desk, Book, Ops & Product

*Sources: `06_TRADING_DESK/` (register, ledger, cost standards, specs, paper runners, marks), `04_RND_LAB/results/STACKED_BOOK_20260711/RESULTS.md`, `07_RISK_OFFICE/RISK_LIMITS.md`, `99_OPS/`, `01_COMMAND_CENTER/OPERATING_CALENDAR.md`, `09_PRODUCT/`. All facts read from the files as of 2026-07-13 state.*

This section describes the "downstream" half of the firm: what the desk actually holds (nothing yet — everything is paper), what is honestly certified vs merely labeled, what runs automatically every day and week, what cost and risk rules bind every number, how a strategy would ever reach real money, how the firm survives a laptop loss, and what the Principal actually receives as products.

---

## 5.1 The book — honest state (as of 2026-07-13)

The firm's own consolidated ruling (in `01_COMMAND_CENTER/CURRENT_STATE.md`, restated in `04_RND_LAB/STOCKS_PROGRAM_2026/MASTER_PLAN.md`) is deliberately blunt:

> **HONEST BOOK STATE: 2 certified alphas (S1-F, B1b) + 2 labeled betas (midsmall Var-B with binding conditions, breakout). Zero red-team debt. Shadows in flight: P6 snapback, B1c DII-flow, S1-SX Thursday.**

This is a *restatement* — earlier the book was described as "four alphas". After two red-team passes (2026-07-12 and 2026-07-13) two of the four were demoted to beta, and the 30/10-frontier sleeve-count math restarted from 2 certified + 3 shadows.

### 5.1.1 The two certified alphas

| Sleeve | What it is | Certified evidence | Forward status |
|---|---|---|---|
| **S1-F** | 0DTE NIFTY ATM short straddle: on every weekly expiry day, sell 1× ATM CE + 1× ATM PE at 09:20, 30% per-leg stop-loss, flat by 15:25. Two entry vetoes: F1 (D-1 daily RSI(5) ≥80 or ≤20) and F2 (\|D-1 return\| >1.5%). ~55 skip-days/yr. | +10.73 pts/day net (1% slip + transaction costs), t=3.92, PF 1.79 over 259 expiry days 2021-26; 84-cell sensitivity plateau (72/84 positive); COVID backcast survivable (modeled maxDD ~−16% in the 2020 stress); lookahead-audited. Evidence in `04_RND_LAB/results/SELLSIDE_20260710/`. | **Registered for paper forward test** 2026-07-10, spec FROZEN (D-030) at git commit `b8d2f3d`, v1.0. Forward clock: first expiry ≥ 2026-07-14. Spec: `06_TRADING_DESK/specs/S1F_SPEC.md`. Crucially, S1-F is **the only sleeve that was flat-to-positive in all 5 worst book months** — the one genuinely orthogonal sleeve. |
| **B1b** | FII-minus-Client index-futures flow signal: bottom-quartile (q4) flow days → next-day long. Rolling-252 percentile rank, T+1 close entry, q5−q1 spread construction (locked in `04_RND_LAB/ALPHA_FORGE/flow_lattice.py`). | Cheap-test pass 2026-07-11: **+21.8 bps/day, t=2.53, era-strengthening**, frozen @ commit `4d9c6f1`. Full pipeline pass same day (the "B1b template" is now the firm's reference red-team battery). | IC review scheduled at the Monday leaders' meeting (cron "IC-B1b Mon 09:33"). Register row pending IC (still in `04_RND_LAB/IDEA_PIPELINE.md` at stage 2-CHEAP-TEST-PASS with a Gate-4 spec assigned to Arjun/Sameer/Nikhil). |

S1-F sizing (from the frozen spec): margin = ~15% of one-side notional (spot × 75 × 0.15 ≈ ₹2.7L/lot at 2026 levels — the earlier flat ₹1.1L model was declared optimistic and superseded); `lots = floor(0.75 × equity / margin)` ≈ 3-4 lots per ₹10L; **halve lots** when trailing 3-day realized vol > 2× its 1-year median. Honest expectation ~13-17% CAGR, maxDD ~−5% at spec sizing. Pre-registered kill criteria (frozen): 26 traded expiries with expectancy ≤ 0 → KILL; paper maxDD > 15% → KILL; fills > 3 pts/day worse than model over 13 expiries → HALT and CIO review.

### 5.1.2 The two labeled betas (in the book, but not counted as alpha)

| Sleeve | Red-team verdict | Binding conditions |
|---|---|---|
| **Breakout pack** | Red-teamed 2026-07-12: **NOT CERTIFIED** — +1.23%/trade is *below* both shuffle-null 95th percentiles (~+2.45%), i.e. the return is market beta/drift, not stock selection (`04_RND_LAB/results/BREAKOUT_REDTEAM_20260712`). | Demoted to "disciplined beta": tradeable as such, benchmarked vs random-stage-2 entries (not vs cash), **no diversification credit as alpha**. |
| **Midsmall Var-B** | Red-teamed 2026-07-13 (Nikhil): **SURVIVES-AS-BETA** — invested-days alpha t=0.16 (statistically zero), realized beta 1.13× the midcap index; placebo Sharpe tie; drop-2021+2023 CAGR 10.4% < NIFTY500 buy-and-hold. Verdict memo: `07_RISK_OFFICE/ADVERSARIAL_REVIEWS/MIDSMALL_VARB_REDTEAM_20260713.md`. | Relabel "risk-managed midcap-momentum beta"; **NOT an independent alpha in the 30/10 frontier math**; size on QUARTERLY correlation (0.53 vs B1b); expect ~13-14% net, not the headline 22.8%; if breakout+B1b already fill the equity-momentum bucket it is largely redundant (CIO/FM portfolio-construction call). |

### 5.1.3 The three shadows (zero size, building forward evidence)

1. **S1-SX** — SENSEX 0DTE Thursday shadow of S1-F (exact same rules, strike round-100, BSE), frozen @ commit `26e1684`, zero size for 13 Thursday expiries. Runner: `06_TRADING_DESK/paper/s1sx_shadow_runner.py` → `s1sx_shadow_log.csv`.
2. **P6 snapback** — equity shadow in flight (Stocks Program).
3. **B1c DII-flow** — DII-flow variant graduated to shadow from the wave-B card sweep.

### 5.1.4 Legacy register rows (the four original sleeves, S-01..S-06)

The `06_TRADING_DESK/STRATEGY_REGISTER.md` table still carries the firm's first-generation short-vol book, with its scars recorded row by row. Nothing trades (even paper) without a row here — owner, edge, gates, kill criteria, review date.

| ID | Strategy | Status | Honest number |
|---|---|---|---|
| S-01 | IV/RV short straddle (IV/RV ≥ 1.4) | **SEND-BACK** (IC 2026-07-03), paper-tracking only, firewalled, NO capital | +11.4 pts *incremental* over unconditional short-vol; the +37.6% headline was 71% regime beta (Red Team). DSR 0.687 / PBO 55% FAIL. |
| S-02 | Earnings short-vol through the print | **FAILS-PRE-IC** (2026-07-04) | Registered +21.6% was a denominator artifact (per-leg premium → 0 on expiry-week rows; worst row +6,759%). Honest crush incremental vs calendar-matched short-vol: **−10.1%** (CI all-negative). |
| S-03 | FF calendar single-CE | **KILLED** (K-012; resurrection review CLOSED 2026-07-05, stays killed) | Third denominator artifact. In rupee points: build +5.85 → forward **−9.30** (loses 2024 AND 2025); 61% of back-leg markets un-exitable (CIO "exitability veto"). Signal itself is real (100th-percentile vs placebos) and graduated to a new liquidity-native intake. |
| S-04 | Short strangle 14-DTE managed | **FULLY CERTIFIED → PAPER-WATCH** (2×-cost 12/12, sensitivity plateau pass-with-flags, D-028 lookahead PASS) | +0.22%/spot managed; but 2025 subsample +0.081%/spot (near-breakeven), decay zero-cross 2025.4-2028.9, 5-7% of entry fills suspect under the circuit rule. Kill: fwd <+0.1%/spot over 3 cycles OR fill-optimism >30% of edge. |
| S-05 | Track-1 delta-hedged 0DTE/DTE1 straddle (≥0.45% morning-straddle filter) | Paper-ready (pre-firm validated) | CAGR +5.9%, maxDD 5%, 6/6 years positive. |
| S-06 | Equity Mom-12-1 + LowVol blend | Backtest (PIT-universe + approved-costs re-run pending) | +15%/yr — below bar, kept as diversifier candidate. |

**Book-level standing rules** (CIO, at the bottom of the register): (1) S-01..S-04 are all short-vol and drawdown TOGETHER in a vol spike — combined sizing must assume it; (2) no naked short-vol through a known binary event; (3) compounded CAGRs are reporting artifacts — size from per-trade edge × worst-case MTM; (4) paper first, Principal approves any LIVE step.

A firm-wide hard rule born from this table: **every per-trade edge is reported in denominator-free rupee points + %spot** — three sleeves died of "denominator disease" (P&L divided by a premium that goes to zero).

### 5.1.5 The stacked-book frontier — and the correlation-horizon correction

`04_RND_LAB/results/STACKED_BOOK_20260711/RESULTS.md` stacked the four sleeves (2022-2025, banked ledgers, ₹1cr, pledge-based capital reuse):

| Config | CAGR | maxDD | Sharpe | Note |
|---|---|---|---|---|
| v1 naive (equity-heavy) | +16.9% | −19.2% | 1.46 | diversification wasted |
| v2 risk-parity @ margin cap | +15.8% | **−8.1%** | **2.29** | the quality point |
| v3 full-deploy | **+35.9%** | −22.1% | 1.91 | the growth point |

The original frontier math: Principal's bar is **30% CAGR AND <10% maxDD**, which requires book Sharpe ~3.5 → 6-8 independent alphas at current sleeve quality (Sharpe scales ~√N at zero correlation). Peak F&O margin 44L vs 75L pledge = feasible with stress headroom.

**But the file carries two addenda that materially change the plan:**

- **Addendum 1 (2026-07-13, CA-BOOK card):** the celebrated "max pairwise correlation 0.08" is a **daily-horizon artifact**. Sleeves that trade asynchronously look uncorrelated by day.
- **Addendum 2 (2026-07-13, own-sleeve re-measurement):** daily max 0.08 → monthly max 0.27 → **quarterly: midsmall-B1b 0.53, midsmall-breakout 0.41, S1F-B1b 0.39** — ALL pairs positive. Worst months cluster directly (Feb-2022: midsmall −2.8L + breakout −3.7L + B1b −3.2L together; Mar-2024: midsmall −4.5L + breakout −4.2L). **Revised frontier math: with quarterly avg correlation ~0.35 among equity-linked sleeves, the Sharpe multiplier caps at √(1/ρ) ≈ 1.7× regardless of sleeve count.** The 6-8-sleeve path to 30/10 holds ONLY if new sleeves are *different-factor* (vol / gold / macro / flow class), not additional equity variants. Realized in-window numbers stand as history; all forward projections must use monthly+quarterly correlation.

Also flagged in the file's own caveats ("do not launder"): the stack is an in-sample assembly of separately-validated sleeves; the equity-pair stress correlation (a 2020-class event) is unmeasured because the window was mostly-bull; and **the paper-first law applies to the BOOK exactly as to sleeves**.

---

## 5.2 What runs each morning — the paper runners

Both runners live in `06_TRADING_DESK/paper/` and embody the paper-desk discipline: **intent is logged to CSV BEFORE any market action** (the append happens whether the decision is GO or SKIP; corrections are new rows, never edits).

### 5.2.1 `s1f_daily_runner.py` (run ~09:10 IST any day; safe daily; cron-armed Tue 09:12)

1. Loads the Angel scrip master (`AppData\Local\angel_capture\scrip_master.json`) and derives NIFTY weekly expiries **from live contract data, not an assumed weekday**. If today is not an expiry day → prints SKIP and exits.
2. Logs into Angel SmartAPI (data-only account), pulls 400 days of NIFTY daily candles **with `fromdate` at 00:00 — explicitly defending against data landmine #8** (an intraday fromdate silently drops the first bar), and truncates to D-1 and earlier only (no same-day peeking).
3. Computes the two frozen vetoes — F1: RSI(5) of daily closes ≥80/≤20; F2: \|prior-day return\| >1.5% — plus the crash-halving rule (3-day avg \|return\| > 2× the 1-year rolling median → halve lots).
4. Fetches spot LTP, rounds to the nearest 50 for the ATM strike, computes **dynamic margin = spot × 75 × 0.15** (per the registered spec; the code comment notes this replaced the superseded flat ₹1.1L) and `lots = int(0.75 × CAPITAL / margin)` with CAPITAL currently hardcoded ₹10,00,000.
5. Prints a human order ticket — "at 09:20 SELL n× lots: SELL NIFTY <expiry> <ATM> CE/PE (tokens), SL: exit leg at 1.30× fill, exit survivors 15:25" — and appends the intent row (date, decision, reason, rsi5, pret, lots, halved, atm, tokens, blank fill/exit columns) to `s1f_paper_log.csv`. Actual 09:20 fills are then marked by hand into the `fill_ce`/`fill_pe` columns.

Header comment: "DRAFT-OPS v1 (Manoj to harden)". Known open item (CURRENT_STATE 2026-07-11): the runner was still on the flat ₹1.1L margin at registration — the file read above already carries the dynamic 15% fix, but the Phase-0 #8 instruction ("sanity-check lots vs ~₹2.7L/lot until hardened") stands.

### 5.2.2 `s1sx_shadow_runner.py` (Thursdays ~09:10 IST; cron Thu 09:14)

The SENSEX mirror at **zero size** for 13 Thursday expiries (SX1-CARD stage 2, frozen @ `26e1684`): identical S1-F rules translated to BSE — BFO scrip filter, strike rounding to 100, lot size read from the scrip master (fallback 20), same F1/F2 vetoes and crash-halve computed on SENSEX dailies, same 00:00-fromdate landmine defense, `truststore.inject_into_ssl()` for the corporate proxy. Output: "SHADOW-GO (ZERO SIZE) — note quotes at 09:20" ticket + intent row to `s1sx_shadow_log.csv` with blank entry/exit quote columns to fill at 09:20/15:25.

### 5.2.3 Paper ledger and marks

- `06_TRADING_DESK/PAPER_LEDGER.md` — append-only; three tables (Open positions / Closed trades with sim-vs-paper tracking-error decomposition / Weekly reconciliation log), all still empty as of writing — the first eligible S1-F expiry is 2026-07-14. Tara Singh reconciles Fridays.
- `06_TRADING_DESK/marks/` — early live-mark artifacts already exist: `LIVE_MARKS_20260709.csv`, `FILL_AUDIT_20260710.csv`, `PNL_GRAPH_20260710.png`.

---

## 5.3 Cost standards (APPROVED, binding)

`06_TRADING_DESK/COST_STANDARDS.md` — **STATUS: APPROVED** (D-021, 2026-07-03, Principal). Binding on all backtests and paper trades; amendments only via `/post-mortem` evidence + Principal sign-off. Tara Singh owns.

**Per-order charges:** ₹20 brokerage/executed order; STT 0.1% both sides (equity delivery), 0.025% sell (intraday), 0.02% sell (futures), 0.1% of premium sell-side (options — avoid exercise, which costs 0.125% of intrinsic); NSE exchange txn ~0.00297% equity / ~0.035% of premium options; GST 18% on (brokerage + exchange + SEBI); SEBI ₹10/crore; stamp duty 0.015%/0.003%/0.002%.

**Slippage floors (one-way, of traded value; DOUBLED for panic exits):**

| Tier | Floor |
|---|---|
| Large-cap equity | 10 bps |
| Mid-cap | 20 bps |
| Small-cap | 35 bps |
| Micro | 50+ bps |
| Options — liquid ATM index | max(1 tick, 0.25% premium) |
| Options — single-stock near-ATM | max(1 tick, 0.5-1.5% premium) |
| Options — illiquid strikes | 1-2% premium; **far-OTM single-stock wings = UNTRADEABLE** (firm lesson: a −883% stale-print artifact) |

**Dynamic slippage & circuit rule (Principal order 2026-07-04, a tightening):** circuit-locked day = **NO FILL, ever** (detector `lib/execution_realism.circuit_locked`; signals defer to the next tradeable day). Volume-conditional slippage multiplier: day volume ≥50% of 20d median → 1× floor; 20-50% → 2×; <20% → 3×; zero volume → NO FILL. Rationale recorded in the file: momentum entries correlate with upper circuits and stops with lower circuits — fixed slippage overstates every momentum backtest exactly on signal days.

**Liquidity & capacity:** position ≤10% of 20-day ADV (≤5% micro-caps); options need standing OI/volume at the strike. Margin proxies: short strangle ~12% notional, short straddle-through-event ~14%; worst-case MTM modeled, never average.

**Promotion rule (the tollgate):** every strategy must remain net-positive at **2× ALL of the above** before advancing to paper. Paper reconciliation can only RAISE these numbers, never lower them without Principal sign-off.

---

## 5.4 Risk limits (APPROVED, obeyed by the paper book now)

`07_RISK_OFFICE/RISK_LIMITS.md` — **STATUS: APPROVED** (D-021, 2026-07-03). Written for the future small retail account; **the paper book obeys them NOW to build the habit**. CIO (Rajan Mehta) enforces; loosening needs Principal sign-off.

- **Position level:** max risk 1.0% of book equity per position (worst-case MTM for undefined-risk structures, NOT premium); short-vol per-name notional ≤5% of book; inverse-IV sizing mandatory but **capped at 1.0× reference until a regime gate exists** (no upsizing into calm regimes); no naked short-vol through known binaries; illiquid instruments prohibited.
- **Book level:** aggregate short-vol margin ≤40% of equity; **free cash ≥30% at all times** (gap-day survival); ≤20% per sector (Adani group counts as ONE name); all short-vol sleeves share ONE combined VaR budget (the equity sleeve does not offset it in stress); staggered entries — max 25% of a sleeve's monthly deployment on any single date (April-2026 cluster lesson).
- **Monthly stress tests:** COVID-open (−13% index gap, +25 vol points panic IV — book must survive with drawdown <20%); single-name −20% overnight gap on the largest short-vol position; all four short-vol sleeves at historical-worst-month simultaneously.
- **Process risk (D-028):** lookahead-bias controls are themselves a risk limit — no result enters the register, an IC memo, sizing math, or the investor letter without a LOOKAHEAD AUDIT PASS (T1-T10 taxonomy, `lib/lookahead_audit.py`, one-day-lag test). Dr. Bhat signs; Ritika monitors live/paper signal-reproducibility parity weekly.
- **Escalation ladder:** single-day book loss >3% → trading halted, CIO review before next entry; 2 consecutive monthly sleeve losses → auto-demote to paper; any realized trade >2× modeled worst-case → immediate post-mortem + COST/RISK amendment proposal.
- **Book equity:** paper BOOK_EQUITY = **₹1 crore** (D-026, resolving the earlier ₹10L problem where the 1% rule capped ~87% of NSE F&O single lots at 0-1 lots).

**D-034 (Principal, 2026-07-13)** adds a portfolio-level adjudication principle: a good sleeve may carry >25% standalone maxDD or lower standalone Sharpe if its *book* contribution/XIRR/regime value is real — but frozen-card bars still bind their own verdicts.

---

## 5.5 The paper → live gate

The path from research to real money is a chain of gates, every one already written down:

1. **Register row** — nothing paper-trades without a `STRATEGY_REGISTER.md` row (owner, edge, gates, kill criteria, review date).
2. **2×-cost promotion** — net-positive at double ALL cost standards (§5.3) before paper.
3. **Certification battery** — Gate-4 sensitivity (Sameer), red-team (Nikhil, mandatory), lookahead audit (D-028), fill audit (Tara).
4. **Forward-test freeze (D-030)** — at paper entry the spec+code+params are FROZEN with a pinned git hash (S1-F @ `b8d2f3d`); any change = a NEW version with a restarted forward clock; mid-test tuning voids the result.
5. **Paper discipline** — intent logged before action; fills marked vs actual Angel quotes; Tara reconciles weekly; pre-registered kill criteria apply automatically (e.g. S1-F's 26-expiry expectancy test).
6. **The final gate is human-only:** paper → live = **Principal ONLY**, always (CLAUDE.md hard rule; idea-pipeline gates auto-advance EXCEPT this one). The Angel account is fund-less/data-only — **no real-money trades, ever**, until the Principal explicitly approves a live step himself. D-031 additionally sanctions "limit-order-or-skip" execution for the personal trading line (backtest translation: no-fill = DROP).

---

## 5.6 What runs automatically — ops, calendar, cadence

`01_COMMAND_CENTER/OPERATING_CALENDAR.md` (owner: CEO Meher) is the single source of truth for firm rhythm; if procedure files disagree with it, the calendar wins on *timing*. Crons are session-bound, so DESK-100 re-arms them at every session start from this file (CLAUDE.md protocol #5).

### Daily

| Slot | Time (IST) | What | Auto? |
|---|---|---|---|
| Option capture | 15:45 (+20:00/23:00 backups) | Windows task `AngelDailyOptionCapture`: 2 nearest expiries, ±10% strikes, all 210 F&O names → `datasets/angel_capture_2026/`. **The firm's only defense against Angel purging expired contracts** — expiry-day data is captured before the purge. Idempotent via `last_success.txt`. Health = a post-close line dated today in `AppData\Local\angel_capture\capture.log`. | AUTO (live) |
| Index-close append | 19:30 | Task `ShreyasIonicAMC_IndexClose` → `nse_indices_close_pull.py`, resume-safe, keeps `datasets/index_daily/nse_official_all_indices.parquet` (174 NSE indices, verified 0.000% vs Principal's NAV file over 1,365 days) current. | AUTO (live) |
| EOD health + freshness | post-close ~5 min | `/eod`: capture-log check, max(trading_day) freshness, earnings file age; staleness → CURRENT_STATE flag. | AUTO |
| Desk-open sync | session start | `/desk-open`: CURRENT_STATE + journal top-2 + today's events. | SESSION |
| Paper-morning check | pre-open (if open positions) | `/paper reconcile --open-only` + `/events` (RP-29 event gate over open legs; breaches → Ritika). | AUTO |
| Paper-signal log | when a sleeve fires | `/signals` → intent logged BEFORE action into PAPER_LEDGER. | SESSION |

### Weekly (anchored on the Monday leaders' meeting, 09:30 IST)

| Slot | Day/time | Owner | Output |
|---|---|---|---|
| Paper reconcile + TCA | Fri 16:00 | Tara | implementation shortfall + fill-optimism flag → PAPER_LEDGER + forward_tests/ |
| Risk pack (RP-29..36) | Fri 17:00 | Ritika | exposures/greeks/VaR/limit utilization → `07_RISK_OFFICE/` weekly snapshot |
| Macro-calendar refresh | Sun 18:00 | Cyrus | forward RBI/Fed/budget/expiry/results calendar + cluster-risk warnings |
| Pipeline health | Sun 19:00 | Manoj | GREEN or numbered repair list → `99_OPS/OPEN_ISSUES.md` |
| Skill discovery | Sun 19:30 | Lakshmi | top-3 skill proposals vs the week's pain points |
| S1-SX shadow ticket | **Thu 09:14** | desk | `s1sx_shadow_runner.py` → shadow log |
| **LEADERS' MEETING** | **Mon 09:30** | CEO chairs | fixed 7-item agenda (WORK_LOG → pipeline moves → risk readout → paper/TCA → macro → token spend → week priorities); minutes to `08_BOARD_ROOM/minutes/weekly/` |
| /retro sweep + leaderboard | Mon post-meeting | CEO | persona lessons + AlphaPoints |
| Edge-decay quick-scan | folded into Fri risk pack | Ritika→Arjun | register note (only if trades exist) |

Open forward engines currently cron-armed: **S1-F Tue 09:12, S1-SX Thu 09:14, IC-B1b Mon 09:33** (CURRENT_STATE 2026-07-13).

### Monthly (last working day = board window)

Month-end pack (CEO, 08:00, mechanical) → **BOARD MEETING** (Principal chairs) → full edge-decay re-score (2 consecutive fails = auto-demote) → attribution (Neel) → compliance spot-audit (Farhan) → stress replay (Ritika, if positions) → **Investor Letter** (Tanvi) → spend report + AlphaPoints settlement.

### Quarterly

Binding QUARTERLY_PLAN refresh; `/review-team` settlement; process red-team (Nikhil attacks the FIRM's process, not a strategy); honesty probe (seeded flawed claim — does dissent flow?); KB pruning; killed-idea resurrection review; knowledge-propagation audit; **kill-switch drill** (simulate the circuit breaker firing today: de-risk sequence, time-to-flat).

The calendar closes with a change-control clause: timing edits are CEO actions; adding/removing a MANDATORY slot is a D-025 CEO+CIO joint decision.

### EOD routine detail (`99_OPS/EOD_ROUTINE.md`)

The manual ~5-minute checklist for whichever desk is open: capture-log health; data-freshness ping (angel_capture max trading day = today? earnings file <7 days old?); the 23 pending Angel OHLCV stragglers (retry ≥1.2s/req); expiry-week check that expiring contracts' final day exists in capture (else bhavcopy re-pull); journal anything notable. Weekly add-ons: Tara's ledger reconcile, Vikram's pipeline triage, scrip-master 210-universe drift check. Known open flag (2026-07-11): `forthcoming_results.csv` is missing from `datasets/earnings_pit` — assigned to Kavya.

---

## 5.7 Backup & disaster posture

Four layers (`99_OPS/BACKUP_POLICY.md`, D-015) plus an out-of-band vault (D-027):

1. **OneDrive (continuous):** the entire root is corporate-OneDrive synced — survives laptop loss and doubles as the two-desk sync medium. Do not move the folder.
2. **Git (command layer):** every session ends with a commit (code + firm docs; data excluded). History = point-in-time recovery of every decision/prompt/agent. **Local-only**; any future remote requires a secret scrub first — an HF token is hardcoded in some legacy `data/hf_*.py` (D-003).
3. **Data snapshots (weekly):** zip the critical derived sets (earnings_pit, derived/, strategy-output parquets, angel_capture_2026) to `D:\`/external or a dated `datasets/_snapshots/`. Raw HF dumps (28GB) are deliberately NOT duplicated — re-downloadable, documented in DATA_CATALOG.
4. **Credentials:** `creds.json` + `angel_cfg` live OUTSIDE the repo (`AppData\Local\angel_capture\`) by design and are NOT backed up to OneDrive-visible paths; the Principal holds originals.

**The vault — `99_OPS/backup_firm.py` (D-027, weekly task, live per CURRENT_STATE):** writes to `C:\Users\Shreyas.1Gupta\ShreyasIonicAMC_BACKUP\<YYYYMMDD_HHMM>\` — deliberately **outside OneDrive** so it survives OneDrive sync accidents/ransomware of the synced tree. Each backup contains: (1) `git_full.bundle` — the entire git history in one restorable file; (2) `firm_tree.zip` — raw copy of `Shreyas_Ionic_AMC/` + `.claude/` + root md files, git-independent; (3) `critical_data.zip` — the small high-value parquets (strategy outputs, derived/, ETF/index pulls, the PIT earnings parquet, the NIFTY500 PIT membership xlsx). Rotation keeps the newest 5. Restore: `git clone git_full.bundle restored/` + unzip.

**Restore drill:** quarterly — open one parquet from each critical family, verify row count vs catalog, log in the journal.

**Resilience beyond files:** the session protocol itself (CURRENT_STATE + SESSION_JOURNAL + continuous checkpointing) is designed so a token-limit cut or desk switch loses nothing; and a staged-but-NOT-run root-rename runbook (`99_OPS/RENAME_RUNBOOK.md` + `migrate_root_rename.ps1` + `HARDCODED_PATH_MANIFEST.csv`) sits ready with an explicit WHEN-SAFE checklist (fresh backup, OneDrive paused) before anyone passes `-Execute`.

---

## 5.8 Principal-facing products (09_PRODUCT)

Owner: Tanvi Desai (Head of Product). Governing order (Principal, 2026-07-05): **Principal deliverables are HUMAN-format** — Word docs with tables/charts, or clean in-chat tables — never bare .md pointers (.md files are internal agent books).

### 5.8.1 Reports pipeline

- `09_PRODUCT/scripts/` — python-docx builder scripts: `build_principal_report.py`, `build_alphagrep_maaf_report.py` (+ `verify_agmaaf_numbers.py`, a separate number-verification pass), `build_ff_verdict_addendum.py`, `build_s1f_docx.py`.
- `09_PRODUCT/reports/` — shipped docx: `PRINCIPAL_REPORT_2026-07-05.docx`, `ALPHAGREP_MAAF_ANALYSIS_2026-07-05.docx` (external-fund forensics: 78% of the claimed 13.9% CAGR was beta; their "NIFTY TRI" benchmark was actually the price index), `FF_CALENDAR_BRIEF/VERDICT_2026-07-05.docx` (an honest kill delivered as a product), and `S1F_STRATEGY_PACK_20260710.docx` (kept out of git per gitignore).

### 5.8.2 Product roadmap (`09_PRODUCT/ROADMAP.md`, Q3-2026 ranked)

| # | Product | Status / target |
|---|---|---|
| 1 | Monthly Investor Letter #1 — plain-language book account, honest edges and kills, bundled with the board pack | Jul-31 |
| 2 | Execution-sheet v2 — one decision-ready view: conviction + sizing + gates (516 legs → 258 trades, TRADE/DISCRETIONARY/BLOCKED blocks); builder `execution_sheet_v2.py` | **DONE 2026-07-04** (shipped early) |
| 3 | Firm dashboard v1 — single HTML page: books, pipeline, AP league, spend (Tanvi spec / Manoj build) | Aug |
| 4 | Strategy product-spec template — packaging a sleeve at paper/DoD: minimum capital, plain-language drawdowns, retail run-steps | Aug-Sep |
| 5 | Retail-account runbook | **Explicitly gated** — scoping does not start until the Principal authorizes moving a strategy toward his own capital |

### 5.8.3 FnO Replay Game (`09_PRODUCT/fno_game/` — v1 COMPLETE & DEPLOYED)

A training product for the Principal himself: an intraday NIFTY weekly-options paper-trading simulator that replays a **random hidden historical day** bar-by-bar from real 1-min data (2019+; eligible pool 1,198/1,242 days), 100% local/offline at `http://127.0.0.1:8787` (FastAPI/uvicorn, launch `run_game.ps1`). Key design points, all documented in its README/ROADMAP (locked Principal rulings L1-L11):

- **Blinding:** the date is hidden (timestamps rebased to a fake epoch, HH:MM only; VIX shown as a band, OI as within-day percentiles); an end-of-session honesty prompt excludes recognized days from career analytics; a leak-test suite (`test_leak.py`) asserts no ISO date or weekday name in any pre-reveal payload.
- **Realism:** spread-aware fills at next-bar open (zero-volume bars don't fill; gapped-through SL-limits MISS); approximate SPAN margin with a 1.3× expiry-day short-leg multiplier; today's exchange costs applied uniformly; force square-off at 15:25 through the stressed fill engine; thin-strike staleness blocks entries (exit-liquidity realism).
- **Honest stats:** Wilson 95% CI on win rate, n<30 buckets greyed out, R-multiples only from stated risk, MAE/MFE labeled as bounds — and the README states plainly that game stats are an *upper bound* on live skill.
- Persistent ₹10L bankroll, append-only history, seasons on reset; 45/45 tests passing; full trading stack (chain with IV/Greeks/OI-percentile, payoff canvas, MKT/LMT/SL-M orders, straddle/strangle presets, sizing calculator, journal tags, CSV export).

This is the clearest expression of the firm's product philosophy: even the *toy* enforces fill realism, blinding, and statistical honesty.

---

### Improvement opportunities

Prioritized, concrete, for THIS section's scope:

1. **[HIGH] Close the runner-vs-spec hardening gap before the first fill (2026-07-14).** `s1f_daily_runner.py` is self-labeled "DRAFT-OPS v1 (Manoj to harden)": CAPITAL is hardcoded ₹10L with a "update before each run" comment (a stale value silently mis-sizes every ticket), fills are marked by hand-editing a CSV, there is no 15:25 exit reminder job, and no automated check that an intent row exists for every expiry day (a forgotten run = a silent hole in the forward test). Minimum fix: read equity from a small config file, add a scheduled 15:20 "mark your fills/exits" prompt, and a nightly assert that every expiry date since 2026-07-14 has a log row.
2. **[HIGH] Automate the S1-F kill-criteria tracker.** The pre-registered kills (26-expiry expectancy, 15% maxDD, 3-pt implementation shortfall over 13 expiries) live only in prose. A ~30-line script reading `s1f_paper_log.csv` that prints expectancy-to-date, running maxDD, and shortfall-vs-model each week would make the kill un-fudgeable and remove any temptation to "interpret" the clock.
3. **[HIGH] Script the weekly data snapshot (Backup layer 3).** BACKUP_POLICY still says "weekly, manual until scripted" — the one layer that isn't automated is the one covering derived data that git excludes and the vault only partially covers. Fold it into `backup_firm.py` or a second scheduled task, and log the quarterly restore drill (no drill entry is visible in the journal yet).
4. **[MEDIUM] Add an off-machine backup leg.** Both the vault (`C:\...\ShreyasIonicAMC_BACKUP`) and OneDrive live on/through the same laptop+account. A periodic copy of `git_full.bundle` + `critical_data.zip` to a physically separate medium (external drive, or a scrubbed private remote per D-003) would close the "laptop stolen + OneDrive account compromised" corner. Prerequisite: the already-known HF-token secret scrub.
5. **[MEDIUM] Restate the stacked-book frontier table on quarterly correlations.** The v2/v3 table (Sharpe 2.29 / CAGR 35.9%) is what a reader sees first; the two addenda that materially demote it sit below. Publish a "v4 honest frontier" row set computed with the 0.35 quarterly correlation and beta-relabeled sleeves so no future session quotes the superseded numbers (the file itself warns "do not launder" — make the honest version the headline).
6. **[MEDIUM] Fix the D-026 inconsistency between book equity and runner capital.** RISK_LIMITS says paper BOOK_EQUITY = ₹1cr; the S1-F spec and runner size from ₹10L (Principal personal line, D-031/D-032). Both are legitimate, but no document states how the two books relate (does S1-F's paper P&L roll into the ₹1cr book's risk limits and VaR budget, or is it a separate mandate with its own limits?). One paragraph in RISK_LIMITS or the register would prevent a future double-count or gap in Ritika's Friday risk pack.
7. **[MEDIUM] Give the paper desk a fill engine instead of hand-marks.** The openalgo evaluation already concluded PILOT-ONE-STRATEGY (2026-07-04). Piloting it on S1-F/S-05 would replace hand-typed CSV fills with captured quotes and make Tara's Friday TCA mechanical rather than reconstructive.
8. **[LOW] Different-factor sleeve pipeline priority.** Addendum 2's own conclusion — the 30/10 path needs vol/gold/macro/flow-class sleeves, not more equity variants — should be reflected as an explicit intake filter in IDEA_PIPELINE triage (e.g. a "factor bucket" column with a soft cap on the equity bucket), so the factory's wave-3 doesn't keep producing correlated equity candidates.
9. **[LOW] Dashboard v1 (Roadmap #3) should include ops health.** The spec lists books/pipeline/AP/spend; adding the three cron heartbeats (capture task, index close, backup vault age) would give the Principal a one-glance "is the machine alive" view and surface a dead scheduled task within a day instead of at the Sunday pipeline-health slot.
10. **[LOW] Version the marks folder convention.** `06_TRADING_DESK/marks/` holds ad-hoc dated CSV/PNGs with no README; a two-line convention note (naming, what each column means, who writes it) prevents the same archaeology this blueprint had to do.
