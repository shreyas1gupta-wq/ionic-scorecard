# T1 Reconciliation — Is the "idle" delta-hedged 0DTE/DTE0+DTE1 short straddle new, or already tracked?

**Author:** Vikram Shah (FM, Derivatives book). **Date:** 2026-07-18.
**Task:** BROAD_RESEARCH_ROADMAP.md T1 (highest-priority item).

**REVISION NOTE:** this doc was first drafted before `INTRADAY_OPTIONS_SELLSIDE_ASSESSMENT.md`
existed on disk (it did not exist at my first check). A sibling agent (Aakash Jain, Structurer,
"BROAD-R3") subsequently wrote a deeper-dive version of it at that path, dated 2026-07-18, which I
have now read in full and independently spot-checked (`SESSION_JOURNAL.md:334`,
`03_RESEARCH_DESK/forward_tests/S-05_forward.md`). Aakash's finding materially changes §5 of this
doc (below) and is folded in. Everything in §1-4 that does NOT touch the delta-hedged real-fill
number stands as originally verified.

## VERDICT (revised): TWO DIFFERENT ANSWERS FOR TWO DIFFERENT STRATEGIES BURIED UNDER ONE "T1" LABEL.
1. **The naked (non-hedged) ATM straddle = SAME STRATEGY, already tracked, already live.** This is
   S1-F (frozen D-030, `06_TRADING_DESK/specs/S1F_SPEC.md`), real-fill validated, forward-testing
   since 2026-07-14 with an actual executed and closed trade (S1F-001, realized −₹5,767). Nothing
   new to add here — closing this out is correct.
2. **The delta-hedged / DTE0+DTE1 variant (register row S-05) is NOT a validated idle asset — its
   headline number is UNVERIFIED and, on the one real-fill reconstruction that exists, appears
   FALSE.** The "Sharpe 2.6 single / 3.6 combined" figure the roadmap quoted traces to
   **synthetic Black-Scholes pricing**, not real fills. The one real-fill delta-hedge backtest on
   disk (`run_realfill_deltahedged.py`, unconditional/unfiltered) gives **Sharpe −0.83, CAGR
   +1.3%** — essentially the opposite of the exciting number. The register's own claim for S-05
   ("+5.9% CAGR, MaxDD 5%, 6/6 years positive") traces only to a session-journal narrative
   sentence (`SESSION_JOURNAL.md:334`), not to any script or CSV — verified directly, see §5.
   S-05 is labeled "paper-APPROVED... live NOW" in `03_RESEARCH_DESK/forward_tests/S-05_forward.md`
   but its signal log is completely empty (zero rows) — so no capital-equivalent paper risk has
   actually accrued yet, but the firm is one automation-build away from carrying forward-clock
   weeks against a number nobody can currently trace to a file.

---

## 1. What the sibling agent found (legacy, `intraday_options_strategy/`, read-only)

**[DATA]** `intraday_options_strategy/results/AUDIT.md` (title: "AUDIT — Nifty 0DTE/DTE1
Delta-Hedged Short Straddle") is a 5-dimension adversarial audit (leakage, cost model, option
pricing, delta-hedge accounting, metrics/sizing, data integrity) that reconciles against six
independent code-level verification passes. It is NOT an idle/forgotten result — it has a real
audit trail with findings and fixes:
- One CRITICAL finding: the raw headline used an extrapolated IV multiplier (m≈0.96); at the
  **validated intraday multiplier m=0.80**, the deployable edge is **Sharpe ~1.65–2.0, not 3.6**
  (AUDIT.md line 52). This is the audit's own re-headlining, not my inference.
- `results/STRATEGIES_COMPARISON.md` lines 70-92: "Headline reported at m=0.80: naked 0DTE ~1.8,
  **delta-hedged 0DTE ~2.6**, **combined DTE0+DTE1 ~3.6** (diversification, corr −0.02)." A later
  bugfix (residual futures-hedge cost) revised combined OOS Sharpe 3.78→3.61. Individually: DTE0
  OOS 2.61, DTE1 OOS 2.51, corr(DTE0,DTE1) = −0.02 (near-uncorrelated — that's the diversification
  claim).
- Mechanism is explicit and distinct from a plain short straddle: **continuously delta-hedging the
  short-straddle's gamma using NIFTY futures** (`run_delta_hedge.py`, `engine_v2.simulate_delta_hedged`)
  is what lifts OOS Sharpe from ~2.0 (naked) to ~2.6-2.7 (hedged) at DTE0; the DTE0+DTE1 combined
  book stacks a second, independent near-non-expiry sleeve on top (`run_dte01.py`).
- Qualified-pass status confirmed: audit's own action items (re-headline at m=0.80, segment
  2015-2020 extrapolated vs 2021-2026 calibrated eras, stress drift/slippage) are the conditions
  attached to "passing" — this is a real, gated, honestly-qualified result, not a magnitude claim
  taken at face value.

## 2. What the firm already has on the books (current, live)

**[DATA]** `Shreyas_Ionic_AMC/06_TRADING_DESK/STRATEGY_REGISTER.md` row S-05 (line 10):
> S-05 | **Track-1: delta-hedged 0DTE/DTE1 NIFTY short straddle, morning-straddle ≥0.45% spot filter**
> | Paper-ready (pre-firm validated) | FM (Vikram) | CAGR +5.9%, MaxDD 5%, 6/6 yrs positive [books]
> | Index-only; real-fill validated | 2 consecutive negative quarters | monthly

**[DATA]** Same file, lines 20-26, a fully fleshed-out section titled **"S1-F — 0DTE NIFTY ATM
Short Straddle (REGISTERED 2026-07-10, paper forward test)"**:
- Frozen spec (D-030): `06_TRADING_DESK/specs/S1F_SPEC.md`, pinned commit `b8d2f3d`, v1.0.
- Edge quoted: "+10.7 pts/day net (t=3.92, PF 1.79, 259 expiry days 2021-26, 1% slip + TC)."
- Evidence base explicitly cited as `04_RND_LAB/results/SELLSIDE_20260710/` — **[DATA]** this
  folder exists on disk (verified via `ls`) with subfolders `final_three/`, `s1_sensitivity/`,
  `covid_backcast/`, `s1_final_filters/`, `s1f_final_graph/`, `hedged/`, `defense_strangle/`,
  `s1s2_core/` — i.e., this evidence base descends from the SAME legacy `intraday_options_strategy/`
  research lineage the sibling agent flagged (a `hedged/` subfolder exists here too — not yet
  inspected in depth, flagged as an open thread below).
- **Already in live paper forward test, not idle:** cron-armed Tue 09:12
  (`Shreyas_Ionic_AMC/06_TRADING_DESK/paper/s1f_daily_runner.py` →
  `06_TRADING_DESK/paper/s1f_paper_log.csv`); first real paper ticket fired 2026-07-14
  (trade ID **S1F-001**); exit legs logged 2026-07-16: CE stopped 09:24 (−₹2,025), PE stopped
  09:46 (−₹3,742), **realized −₹5,767** (SESSION_JOURNAL.md 2026-07-16 entry, `PAPER_LEDGER.md`
  updated). A SENSEX cross-index shadow clone, **S1-SX**, also runs Thursdays 09:14 zero-size
  (`06_TRADING_DESK/paper/s1sx_shadow_runner.py`, frozen @ `26e1684`) — confirmed by reading the
  runner source: "exact S1-F rules on SENSEX" (same 30% SL, same F1/F2 vetoes, same 09:20/15:25
  clock). S1-SX is a venue replica, **not** a DTE1 sleeve.
- **[DATA]** `04_RND_LAB/IDEA_PIPELINE.md` line 16 carries the matching pipeline row: "Track-1
  delta-hedged 0DTE/DTE1 short straddle (≥0.45% filter) | Index short-vol | 7-PAPER-ready | FM".
- **[DATA]** `01_COMMAND_CENTER/CURRENT_STATE.md` line 180 (Strategy truth): "S-05 Track-1
  straddle — paper-ready (P1 clear); openalgo pilot vehicle." Line 5: "Forward engines: S1-F Tue
  09:12, S1-SX Thu 09:14."

## 3. The actual construction that is frozen and running is SIMPLER than its own label

**[DATA]** Reading `06_TRADING_DESK/specs/S1F_SPEC.md` in full (the FROZEN, D-030, actually-running
spec — not a description of it) shows:
- Entry: sell 1× ATM CE + 1× ATM PE at 09:20, same-day (DTE0) expiry only. **No DTE1 sleeve exists
  anywhere in the frozen spec, the runner code, or the shadow (S1-SX is DTE0-SENSEX, not DTE1-NIFTY).**
- Risk control: **per-leg 30% premium stop-loss**, market order on breach. **No delta-hedging leg
  (no futures trade) appears anywhere in S1F_SPEC.md or `s1f_daily_runner.py`.**
- Entry vetoes: F1 (RSI(5) D-1 ≥80/≤20), F2 (|D-1 return|>1.5%). **No "≥0.45% spot filter" appears
  in the frozen spec** — that phrase only survives in the STRATEGY_REGISTER row-10 label and the
  IDEA_PIPELINE row, both of which read as **stale pointers to the ORIGINAL Track-1 concept that
  predates the actual freeze**, not descriptions of what S1F_SPEC.md v1.0 actually implements.
- Sizing/edge quoted in the spec itself: "+0.5%/expiry" return-on-margin invariant, "~13-17% CAGR,
  maxDD ~-5%" — this does **not** match the STRATEGY_REGISTER row-10 figure ("CAGR +5.9%, MaxDD
  5%") either. Two different numbers for the same row, from two documents in the same file.

**[INFERENCE]** The most coherent read of all four documents together: the firm took the broad
"Track-1" research family (which legitimately includes delta-hedging and a DTE0+DTE1 combined
book, per the legacy AUDIT/STRATEGIES_COMPARISON docs) and, when it came time to actually freeze
and paper-trade something, **shipped a deliberately simplified descendant** — naked legs +
stop-loss + entry vetoes instead of continuous delta-hedging, DTE0-only instead of DTE0+DTE1 —
without going back to update the S-05 register row or the IDEA_PIPELINE row to match what was
actually frozen. That is a **labeling/bookkeeping gap in the firm's own tracking**, not evidence
that the delta-hedged/combined variant was independently tested and duplicates T1's find.

## 4. Same vs. different — explicit diff

| Attribute | Legacy delta-hedged system (`intraday_options_strategy/`) | Firm's live paper strategy (S1-F / S-05) |
|---|---|---|
| Core structure | Short ATM straddle, 0DTE | Short ATM straddle, 0DTE — **same** |
| Risk mechanism | Continuous delta-hedge via NIFTY futures | Per-leg 30% stop-loss, no hedge leg — **different** |
| Scope | DTE0 alone (~2.6 Sharpe) AND combined DTE0+DTE1 book (~3.6 Sharpe, corr −0.02) | DTE0 only; no DTE1 sleeve exists — **DTE1 leg missing entirely** |
| Entry filter | Not centrally a filter-based system (relies on hedge to survive bad days) | F1 (RSI5 D-1) + F2 (\|D-1 ret\|>1.5%) vetoes — **different mechanism, same intent (skip bad days)** |
| Audited edge (post-correction) | Sharpe ~1.65–2.6 (naked-vs-hedged, m=0.80 calibrated) | +10.7 pts/day net, t=3.92, PF 1.79 (different metric, not Sharpe-comparable without conversion) |
| Status | Audited, qualified pass, sitting in `intraday_options_strategy/` — no paper/live wrapper | **Registered, D-030 frozen, live in paper since 2026-07-14, first trade realized a loss (−₹5,767)** |
| Owner | none currently (legacy) | Vikram Shah (FM), per STRATEGY_REGISTER |

## 5. Verdict, spelled out (revised after Aakash's real-fill reconstruction)

- It is **not accurate** to call the naked-straddle side of T1 "new, undiscovered work sitting
  idle." The firm already (a) owns S1-F, descended from the same research lineage, real-fill
  validated (n=259 expiry days, +10.73 pts/day net, t=3.92, PF 1.79, both eras positive, 72/84
  sensitivity cells positive), (b) has it D-030-frozen and running in live paper with a real
  executed trade and a real loss on the books (S1F-001, −₹5,767), and (c) has an IDEA_PIPELINE row
  and CURRENT_STATE line already pointing at this strategy by name. Treating this as a fresh
  discovery would be exactly the double-counting mistake this task was designed to catch. **CLOSED.**

- It is **also not accurate** to describe the delta-hedged/DTE0+DTE1 side as "a strong result
  sitting idle" that the firm should now consider adding. **[DATA, verified directly against
  Aakash's assessment]:**
  - The Sharpe 2.6 (single)/3.6 (combined) figures come from **synthetic Black-Scholes pricing**
    inside the legacy engine, not real option quotes.
  - The one script that tests the delta-hedged construction on **real fills**
    (`intraday_options_strategy/run_realfill_deltahedged.py`, unconditional, no IV filter) produces
    **Sharpe −0.83, CAGR +1.3%, MaxDD 17.7%** over the same n=259 expiries — i.e., on real data and
    without the filter, this variant shows **no edge**, not a 2.6-3.6 Sharpe.
  - The register's S-05 claim ("+5.9% CAGR, MaxDD 5%, 6/6 years positive") does **not** trace to
    any script or CSV anywhere in the repo. I traced it myself to
    `01_COMMAND_CENTER/SESSION_JOURNAL.md:334`, a **compressed pre-firm-history narrative
    sentence** ("Real-fill validated delta-hedged 0DTE/DTE1 short straddle; DEPLOY RULE: trade only
    when morning straddle ≥0.45% of spot (IV filter) → CAGR +5.9%..."), not a results file. No
    supporting backtest artifact for that exact number (with the 0.45% filter applied) exists on
    disk as far as either Aakash's search or mine could find.
  - `03_RESEARCH_DESK/forward_tests/S-05_forward.md` — read directly — confirms status
    "paper-APPROVED (Q3 plan P5, live NOW)" but the signal log table (§Signal log) has **zero
    rows** logged. The automated morning signal check does not exist yet (its own "Ops note" says
    so). So today there is no actual paper capital at risk on this claim — but the strategy is
    formally "approved/live," one cron job away from accruing forward-clock time against a number
    that cannot currently be traced to evidence.
  - **This is a live risk, not a closed research question.** The firm's own register/pipeline
    labels (STRATEGY_REGISTER row S-05, IDEA_PIPELINE row 16 — both say "delta-hedged 0DTE/DTE1... 
    CAGR +5.9%, MaxDD 5%, 6/6 years positive") assert a validated result that, on the one real-data
    test that exists, does not reproduce. Whoever wired S-05 into "paper-approved/live NOW" status
    did so on the pre-firm narrative claim, not on a re-verified number.

## 6. Recommended next steps (revised — verification-first, not a build-out)

1. **Urgent, cheap, before anything else:** flag S-05's "paper-APPROVED/live NOW" status to CIO —
   its headline evidence does not currently trace to a file, and the one real-fill test that
   exists contradicts it (Sharpe −0.83 vs claimed 6/6-years-positive). Recommend: **freeze S-05 at
   its current (non-executing) state — do not stand up the automated morning signal task for it —
   until the reconciliation in step 2 is done.** No capital-equivalent risk is currently accruing
   (signal log is empty), so this is a paperwork freeze, not an unwind.
2. **Single next research step (per Aakash's assessment, concur):** re-run
   `run_realfill_deltahedged.py` WITH (a) the `IV_GATE_PCT=0.0045` filter already coded in
   `run_today_live.py:33` and (b) the F1/F2 vetoes already adopted for S1-F — on real fills. This
   is a half-day script modification (data, engine, and filter logic all already exist on disk),
   not a new research program. Two outcomes:
   - **Reproduces something close to +5.9%/6-6-positive:** S-05's claim is finally evidenced —
     file the script + CSV where the register can cite it, THEN re-apply this doc's original gates
     (landmine #9 expiry-day-settle check, 2× cost stress including the futures-hedge leg's own
     round-trip cost, D-031 fill realism on the futures leg, correlation flag as a 5th short-vol
     sleeve per STRATEGY_REGISTER line 15) before letting it actually start accruing paper time.
   - **Does not reproduce:** kill S-05 as currently specified (with resurrection condition = a
     different filter/construction that does reproduce on real fills), correct the
     STRATEGY_REGISTER row and IDEA_PIPELINE row 16 to remove the unverified "CAGR +5.9%.../6-6
     positive" language, and log it in `KILLED_IDEAS.md` with the −0.83 Sharpe as the honest number.
3. **Either way, fix the bookkeeping:** STRATEGY_REGISTER S-05 row and IDEA_PIPELINE row 16
   currently assert a number that is either unverified or false — that gap should not persist past
   this reconciliation regardless of which way step 2 resolves.
4. **Do not touch** the live S1-F paper run itself (D-030 — frozen, forward clock already ticking
   since 2026-07-14, real trade already executed) — that side of T1 is closed and validated;
   nothing here bears on it.
