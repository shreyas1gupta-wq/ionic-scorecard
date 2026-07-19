# Intraday Options Sell-Side — Current-State Assessment
**Author:** Aakash Jain (Derivatives Structurer) · **Date:** 2026-07-18 · **Scope:** `intraday_options_strategy/` (legacy, read-only) + what the firm has since built on top of it in `Shreyas_Ionic_AMC/`

**[DATA]** unless marked [INFERENCE]/[OPINION]. All numbers below are read from files on disk or computed directly from a results CSV on disk (shown inline); none are recalled from memory.

---

## 0. Bottom line

The firm memory note "edge is on the sell side" is correct but understates how far this has already gone. This is **not** an open research question sitting in a legacy folder — it is a **live, registered, paper-forward-testing strategy** (S1-F, frozen spec, D-030) with a second registered variant (S-05, delta-hedged). The legacy folder is Session 1-5 of a chain that the firm continued in `04_RND_LAB/results/SELLSIDE_20260710/` through real-fill validation, filter adoption, sensitivity, and a COVID stress backcast. Underlying instrument is **NIFTY index options** (0DTE/expiry-day), not single-stock — so the single-stock far-OTM liquidity trap this desk exists to catch does not apply here; index weeklies are the most liquid contracts on the exchange.

The one genuine gap I found: **the delta-hedged variant's headline "+5.9% CAGR / MaxDD 5% / 6-of-6 years positive" claim (S-05, now paper-live) has no traceable, reproducible backtest artifact on disk.** My own reconstruction of the nearest real-fill delta-hedge script gives materially worse numbers (Sharpe −0.83) without the filter that supposedly rescues it. That is the highest-value next step, detailed in §5.

---

## 1. What sell-side/writing work exists (legacy folder, beyond `buying/`)

`intraday_options_strategy/` root has ~15 non-buying strategy runners (`run_v2.py`, `run_vrp_test.py`, `run_vrp_realm.py`, `run_delta_hedge.py`, `run_dte01.py`, `run_drift_stress.py`, `run_capital_eff.py`, `run_realfill_0dte.py`, `run_realfill_deltahedged.py`, `run_23jun.py`, `run_today_live.py`, etc.) plus `backtest/engine_v2.py` (multi-leg/short/delta-hedge engine), `strategies/sleeves.py` (S2 weekly straddle, S3 0DTE, S4 trend rider, S5 iron fly, S6 iron condor), `portfolio/allocator.py`, and result docs `PLAN.md`, `RESEARCH.md`, `STRATEGY_V2.md`, `results/AUDIT.md`, `results/V3_FINDINGS.md`, `results/STRATEGIES_COMPARISON.md`.

**Chronology (self-documented in PLAN.md, Sessions 3–5g, 2026-06-11 to 06-16):**
1. Synthetic-BS pricing, VIX-as-IV proxy → S3 (0DTE short straddle) looked like the survivor, S2 (weekly held intraday) rejected.
2. Two modelling bugs found and fixed: (a) calendar-vs-trading-time clock understated 0DTE premium ~2x (**the single most consequential bug in the whole program** — flipped S3 from "rejected" to "real"); (b) Sharpe annualized per-trade-day instead of full calendar (~2.5x inflation).
3. Real NSE F&O EOD bhavcopy (2,673 ATM points, 2021–2026) used to calibrate ATM-IV/VIX multiplier `m(DTE)`; **expiry-day (DTE<1) rows are explicitly excluded** (`data/calibrate_iv.py:77`, comment "EOD: skip 0DTE (intrinsic)") — this is exactly the settlement-price landmine from `05_DATA_OFFICE/DATA_QUALITY_RULES.md` (expiry-day SETTLE_PR = underlying's final settlement, not option price) and **it has already been correctly avoided**, not silently eaten.
4. Live Angel SmartAPI 09:20 straddle candles (one weekly cycle) revalidated the extrapolated m=0.96 down to real m≈0.78–0.81 — a materially thinner but still real edge (Sharpe ~1.65–2.0, not ~3).
5. Extended to iron fly/condor (defined-risk wings) and delta-hedging. **Wings lose**: `results/STRATEGIES_COMPARISON.md` — iron fly Sharpe 0.93 vs naked-stopped 1.79, iron condor ~0.05. Structurer read: once you can monitor and stop out at 1-min granularity intraday, long OTM wings cost more premium than the tail protection is worth — defined-risk only pays for itself if held unmonitored/overnight, which this strategy never does (hard EOD flat). **Delta-hedging (futures overlay) wins in the synthetic-BS sim**: naked 1.79→hedged 2.98 (full)/2.74(OOS) Sharpe, PF 2.1→4.65, maxDD −28%. Declared "lead strategy," drift-stress-tested (mirror-path OOS 2.65→2.58, i.e. drift-independent — genuinely a theta/gamma effect not a directional one).
6. `results/AUDIT.md` — a proper adversarial audit: 3 "CRITICAL" cost-model alarms raised by dimension-audits were all **refuted at code level** (brokerage netting, GST scope, and a "2x TTE" claim were all misreads); the one real headline risk retained was reporting the optimistic extrapolated m=0.96 instead of the live-measured m=0.80 — which was then fixed.

**Real (non-synthetic) validation that followed, June 18–30 (after AUDIT.md, still in the legacy folder):** `run_realfill_0dte.py`, `run_realfill_deltahedged.py` — these replace synthetic BS pricing entirely with actual traded 1-min option prices (HuggingFace `india-index-options-1m` dataset, `datasets/raw/hf_index_options_1m/`). This is the acquisition of real intraday option quotes that V3_FINDINGS.md's own "REMAINING RISKS" section flagged as the #1 open validation item — **it was done**.

## 2. Real backtest numbers (verified, not recalled)

### 2a. Naked ATM straddle on REAL fills — the validated core, now live in paper (`06_TRADING_DESK/specs/S1F_SPEC.md`, evidence in `04_RND_LAB/results/SELLSIDE_20260710/`)
- `final_three/SUMMARY.md`: **S1 (frozen-spec naked ATM straddle, 30% SL, 1% slippage + statutory costs): n=259 expiry days (2021–2026), net +10.73 pts/day, t=3.92, PF=1.79, win 69%, maxDD −218 pts, both eras positive (2021-23: +8.46, 2024-26: +13.21).**
- `s1_sensitivity/SUMMARY.md`: 84-cell (strike offset × SL%) surface at 09:20 entry, 72/84 cells positive — a genuine plateau, not a single lucky cell. Same surface at 09:45 entry degrades hard (many negative) — mechanism-consistent (the edge is the very-early-session time-value crush, not a generic "sell premium" effect).
- `s1_final_filters/SUMMARY.md`: 12 candidate filters tested against a pre-declared adoption bar (uplift ≥1.0 AND vetoed-bucket <0 AND t improves). Only 2 survive: RSI(5) D-1 ∈{≤20,≥80} veto, and |D-1 return|>1.5% veto (~55 skip-days/yr). This is disciplined filter selection, not curve-fit-until-it-works.
- `covid_backcast/SUMMARY.md`: model (not real data — corr 0.64 validated against 2021-26 real-fill overlap) backcasts 2020. Under a stressed-IV assumption, the actual COVID crash window (20-Feb to 10-Apr 2020) is **net negative** for the strategy (S1: −285 pts over 8 expiries, worst single day −168). Full-sample survival sim at 75% deployment on ₹10L: final ₹9.9L, maxDD −16%. **This is the honest tail number** — a COVID-class event costs real money and ~16% drawdown at spec sizing, it does not "just work."
- `s1f_final_graph/SUMMARY.md`: with F1/F2 vetoes, ₹10L→₹35.3L, CAGR 28.8%, maxDD −9.9% at a **flat ₹1.1L/lot margin assumption**. **This was itself later corrected** — `S1F_SPEC.md` §Sizing states the flat margin was optimistic; real SPAN+exposure margin is ≈15% of notional (≈₹2.7L/lot at 2026 levels, not ₹1.1L), and the honest re-sized expectation is **~13–17% CAGR, maxDD ~−5%**, not 28.8%. The spec explicitly flags this correction before quoting a number — good discipline, and directly in my lane (margin-shape reality changes the deployable return, not the per-trade edge).

**Defined-risk alternatives, tested and killed** (`hedged/SUMMARY.md`, `defense_strangle/SUMMARY.md`): 0DTE iron fly (t=−0.80, PF 0.87, KILL), weekly-hold iron condor variants (all KILL, consistent with legacy folder's S5/S6 and `KILLED_IDEAS.md` K-005), 0DTE ±50 defense-strangle variants (some PASS at t~2.0-2.2/PF~1.4-1.5 but weaker than the plain ATM straddle on every metric). **Structurer verdict: naked short with a hard 1-min-monitored stop remains the best vehicle for this signal; every defined-risk or wing variant tested so far loses to it.** This is a genuine, repeatedly-confirmed finding, not an artifact — three independent test batteries (legacy S5/S6, firm-side `hedged/`, firm-side `defense_strangle/`) agree.

### 2b. Delta-hedged (futures overlay) variant — the discrepancy
The legacy folder's headline "lead strategy" was the delta-hedged 0DTE/DTE1 straddle, Sharpe 2.6–3.6 on **synthetic BS pricing**. I ran the one script that tests this on **real fills** (`run_realfill_deltahedged.py`, HF real 1-min option prices, no filter — same cost stack as the script, per-lot risk-based sizing at 0.6% of capital):

```
n=259 expiries, 2021-05-27..2026-05-19 (5.0 yrs)
Rs1Cr -> Rs1.06Cr   CAGR +1.3%   Sharpe -0.83   MaxDD 17.7%   WR 58%
2023: 52 exp, avg/lot -172 (losing year)   2024: 52 exp, avg/lot +164 (near-flat)
```
This is a materially worse result than the synthetic-BS claim (Sharpe 2.6-3.6 → real-fill unconditional Sharpe -0.83). It is **not necessarily wrong or a kill** — `run_today_live.py:33` carries a `IV_GATE_PCT=0.0045` comment ("skip if straddle < 0.45% of spot — real-fill validated: no edge below"), implying someone did validate that an IV-gate filter rescues this variant. **But I could not find that filtered backtest script or its output CSV anywhere in the repo** (checked `intraday_options_strategy/`, all of `04_RND_LAB/results/`, `06_TRADING_DESK/`). The registered claim — `STRATEGY_REGISTER.md` S-05 and `03_RESEARCH_DESK/forward_tests/S-05_forward.md`: "CAGR +5.9%, MaxDD 5%, 6/6 years positive" — traces only to a session-journal narrative line (`01_COMMAND_CENTER/SESSION_JOURNAL.md:334`), not to a script output. This strategy is currently **paper-approved and live** on that unreconciled claim.

## 3. Landmine-specific checks (per this desk's charter)

- **F&O bhavcopy expiry-day settlement bug:** checked and clean. `calibrate_iv.py` explicitly skips `dte<1` rows with the comment "EOD: skip 0DTE (intrinsic)" — the exact fix this firm's landmine list requires. No silent corruption found.
- **Circuit-lock fills:** not applicable in the stock sense (underlying is the NIFTY index, no per-name UC/LC). The index-analog — an NSE market-wide circuit halt on a >10/15/20% index move — is **not modeled anywhere** I found in either the legacy engine or the firm-side scripts. This is a real, if low-probability, gap: on a circuit-halt day the strategy's hard-coded exits (14:30/15:25 close, or SL-on-next-1-min-close) would not execute as modeled. Worth a one-line note in the risk register rather than a backtest re-run (near-zero historical frequency for NIFTY, but not zero — 13-Mar-2020 is the nearest real precedent, and it sits inside the COVID backcast window that already shows the strategy losing money that week).
- **Margin/SPAN realism for undefined-risk (naked) legs:** originally modeled as a flat ₹1.1L/lot — flagged as optimistic and corrected to ~15% of notional (≈₹2.7L/lot at 2026 spot) in `S1F_SPEC.md`, which is a reasonable SPAN+exposure proxy though still a flat percentage, not a real span file (real margin varies with IV level, skew, and would drop further if the book nets CE+PE portfolio margining benefits at the broker). Good enough for paper; not a substitute for pulling an actual Angel/Zerodha margin-calculator quote before scaling size, which the spec itself says to do.
- **Realistic slippage:** 1% and 2% slippage bands tested throughout (`final_three` at 1%, `V3_FINDINGS` at 0.5%/2%), SL exits modeled as gap-through fills at 3x stop-slippage rather than assumed clean fills — this is more conservative than most of this firm's other options work and is a modeling-discipline positive.

## 4. What's genuinely untested / open

1. **The delta-hedged variant's filtered real-fill number (§2b) — no reproducible artifact.** Biggest gap, see §5.
2. **COVID-class tail is a model backcast (corr 0.64), not real option data** — there is no real intraday NIFTY option quote history for Feb–Apr 2020 in this dataset; the −16% maxDD survival number is the best available estimate but carries model-uncertainty the spec itself flags.
3. **Multi-instrument/multi-expiry diversification** (BankNifty/FinNifty/Sensex 0DTE stacking) — proposed in both the legacy PLAN.md and `STRATEGIES_COMPARISON.md`, never built. Correctly flagged there that straddle P&L correlates on trend days, so this adds deployment frequency, not real tail diversification — a fair caveat, not an excuse to skip it.
4. **Market-wide circuit-halt scenario** — not modeled (§3).
5. **Live paper fills vs. this backtest** — this is precisely what the S1-F forward test (started 2026-07-14) and the S-05 forward log (signal log currently empty in `S-05_forward.md`) exist to answer; too early to have a verdict yet.

## 5. Single most valuable next step

**Reconcile or re-derive the delta-hedged (S-05) real-fill result under the ≥0.45% IV-gate filter, and file the script + output where the register claim can trace to it — before more paper-forward days accrue on an unreconciled number.**

Concretely: take `run_realfill_deltahedged.py` (already on disk, already reads real HF option-price data) and add (a) the `IV_GATE_PCT=0.0045` skip-if-straddle-too-cheap filter already coded in `run_today_live.py`, and (b) the F1/F2 vetoes from `S1F_SPEC.md` (already adopted for the naked variant, never applied to the hedged one). Re-run, and either the +5.9%/MaxDD-5%/6-of-6 claim reproduces — in which case S-05's paper-live status is finally evidenced, not just asserted — or it doesn't, in which case the desk should know that before Vikram's book carries more forward-clock weeks on it. This is a half-day script modification, not a new research program: the data, the engine, and the filter logic all already exist on disk; they have simply never been run together and saved.

This is higher priority than building the naked strategy's multi-instrument stack (item 4.3) or chasing a real COVID quote history (item 4.2, likely unobtainable) — those are refinements to an already-evidenced, already-live strategy (S1-F). The delta-hedged reconciliation is the one item where a **live paper-forward strategy's headline number cannot currently be traced to a file**, which is a process gap this desk's liquidity/vehicle-honesty gate exists to catch.

---

## Files referenced
- `intraday_options_strategy/PLAN.md`, `RESEARCH.md`, `STRATEGY_V2.md`
- `intraday_options_strategy/results/AUDIT.md`, `V3_FINDINGS.md`, `STRATEGIES_COMPARISON.md`
- `intraday_options_strategy/data/calibrate_iv.py` (settlement-bug avoidance, line 77)
- `intraday_options_strategy/run_realfill_deltahedged.py`, `run_today_live.py` (IV_GATE_PCT, line 33)
- `intraday_options_strategy/results/realfill_deltahedged_nifty.csv` (recomputed summary above)
- `Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/{final_three,s1_sensitivity,s1_final_filters,hedged,defense_strangle,covid_backcast,s1f_final_graph}/SUMMARY.md`
- `Shreyas_Ionic_AMC/06_TRADING_DESK/specs/S1F_SPEC.md`, `STRATEGY_REGISTER.md` (S-05, S1-F section)
- `Shreyas_Ionic_AMC/03_RESEARCH_DESK/forward_tests/S-05_forward.md`
- `Shreyas_Ionic_AMC/01_COMMAND_CENTER/SESSION_JOURNAL.md:334` (source of the unreconciled S-05 claim)
- `Shreyas_Ionic_AMC/04_RND_LAB/KILLED_IDEAS.md` (K-005, 0DTE iron condor)
