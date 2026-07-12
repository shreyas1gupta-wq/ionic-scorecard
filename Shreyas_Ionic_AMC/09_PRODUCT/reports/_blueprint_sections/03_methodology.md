# SECTION 3 — RESEARCH METHODOLOGY, AUDIT & ANTI-FRAUD MACHINERY (the firm's moat)

> **The thesis in one line:** most retail curve-fits; this firm kills. The firm's own master plan states it plainly — "our real edge over other retail: the falsification machine (pre-registration, frozen bars, trials ledger, era splits, adversarial verifiers)." The proprietary asset is not any single strategy; it is a research pipeline that makes it *structurally hard to lie to yourself*, and a graveyard of 30+ documented kills whose lessons are codified into reusable law.

This section documents that machinery in full: the experiment lifecycle, the frozen-card pre-registration system with real examples, the code-level enforcement library, the T1–T10 lookahead taxonomy, the placebo battery, the trials ledger and DSR discipline, red-team certification, the killed-ideas graveyard, the ~25 firm-earned lessons, and the alpha thesis that all of this evidence converged on.

---

## 3.1 The full experiment lifecycle

Every experiment in the firm now travels the same rail. The lifecycle hardened progressively across July 2026 (each step below was added in response to a specific self-caught fraud vector, cited inline):

```
IDEA (any source; Principal ideas jump the queue)
  │  prior-art check (KILLED_IDEAS + KNOWLEDGE_BASE + results dirs — nothing killed is re-tested
  │  without a structurally new construction; curator blocks duplicates at intake)
  ▼
FROZEN CARD — pre-registration
  │  construction, data, costs, windows, controls and PASS/KILL/PARK bars all written down
  │  and COMMITTED ALONE to git BEFORE the experiment script runs (the freeze hash goes into
  │  the results file). Rule created 2026-07-11 after the firm's own LEAK_AUDIT found that
  │  card+results in the same commit makes "frozen before run" unprovable.
  ▼
AST SCAN (pre-flight, static)
  │  lib/ast_lookahead_scan.py runs on the backtest script BEFORE execution — mechanically
  │  flags shift(-n), rolling(center=True), bfill, full-sample normalization, shuffled
  │  train_test_split, forward index arithmetic. Exit 1 = findings must be justified in the card.
  ▼
ENGINE RUN (scripts, not conversation)
  │  guards.py imported into every entry point (L1–L7b landmine guards);
  │  execution_realism.fill_check() on every equity fill; RUN_CARD.json emitted per run
  │  (card name, freeze hash, trials_increment, verdict) — this feeds the trials ledger.
  ▼
PLACEBO / CONTROL BATTERY (see §3.5)
  │  same-exit placebo × 200 · stock-shuffle · date-shuffle · label-permutation ·
  │  lag-decay (timing-information test) · plateau (≥2 cells must pass) ·
  │  calendar-specificity · turnover-matched comparator · era split · 2x-cost stress
  ▼
VERDICT — exactly the pre-registered one
  │  PASS / KILL / PARK per the frozen bars. Single-shot cards get NO tuning pass after
  │  seeing results ("a fished overlay grid could show 40/-8 and would be a lie" — EQ-MAX card).
  │  PARK may sanction exactly ONE new-card iteration (TF-1 → TF-2), never in-place re-tuning.
  ▼
BANKING
  │  results dir under 04_RND_LAB/results/<NAME_yyyymmdd>/ with scripts + CSVs + RESULTS.txt;
  │  outcome appended to the card in MASTER_PLAN; trials ledger incremented; KB lesson filed
  │  if transferable; KILLED_IDEAS entry if killed — WITH resurrection conditions.
  ▼
(survivors only) GATE-4 → RED-TEAM → IC → PAPER
     lookahead audit (D-028, mandatory) + sensitivity (Sameer) + DSR + Nikhil red-team
     certification → IC memo → paper trading under D-030 freeze (spec+code+params frozen,
     git hash pinned; any change = new version, restarted forward clock).
```

Two structural facts make this more than process theater:

1. **Kills are conditional, never dogma.** Every kill carries a specific, pre-written resurrection condition (D-012), and resurrection attempts are themselves adjudicated adversarially (see the GT-2 "DENIED-WITH-RESURRECTION-CONDITION" ruling, §3.4, and the K-012 CIO ruling, §3.8) — the firm calls disguised re-tests "resurrection laundering" and routes them to the red team.
2. **The machinery catches its own authors.** AF-07 — a discovery made by the red-team function itself — was killed by its own certification battery (episode-level re-measurement: −0.28%/trade vs a date-shuffle placebo at +4.05%). The KILLED_IDEAS entry notes: "the verification machinery catches its own author — that is the point of it."

---

## 3.2 The frozen-card system (STOCKS_PROGRAM_2026) — representative cards with outcomes

`04_RND_LAB/STOCKS_PROGRAM_2026/MASTER_PLAN.md` is the live card book: ~25 cards frozen and adjudicated across 2026-07-11..13, every one carrying a pre-run git freeze hash, pre-declared bars, a trials increment, and a banked evidence directory. Five representative cards:

### Card 1 — T-C POST-BREAKOUT ORB (frozen @ 4692e17) — a clean, decisive KILL of the Principal's own priority idea
- **Hypothesis:** stocks that just broke out have elevated intraday trendiness, so a 5/15-min opening-range-breakout in the post-breakout window clears the friction floor that killed basket-ORB.
- **Pre-registered discipline:** two variants only (V1 same-day exit, V2 overnight hold — the sanctioned "cost-regime change"), 15 bps/side costs (30 on stop fills), era split, placebo = same ORB engine on 200× frequency-matched random non-breakout stage-2 stock-days, n<150 = INSUFFICIENT.
- **Outcome: KILL both.** V1 gross −11.1 bps/trade *before* costs (t=−16.3, n=6,646) — the hypothesis is backwards in the data: post-breakout stocks FADE opening-range triggers. V2 = noise (t=0.54, era-flip). Combined with the 07-07 basket kills and the puts-vehicle kill, this **terminally closed the intraday-ORB family** across universes, windows, stops, vehicles and event-conditioning. Resurrection bar: positive GROSS edge ≥40 bps demonstrated on NEW data first, never parameter reshuffles.
- **Why it matters:** the Principal's specific ask was honored with a full-rigor test and an honest negative — no sycophantic survivor was manufactured.

### Card 2 — TF-1 TECHNOFUNDA COMPOSITE (frozen @ 47e8a00) — PARK with a diagnostic, and the one-iteration rule
- **Hypothesis:** Minervini VCP + O'Neil CANSLIM + Weinstein stage-2 + PIT fundamentals, six ANDed layers, 15-slot portfolio.
- **Outcome: PARK — "selection alpha REAL, vehicle starves it."** Per-trade +2.10% net beats placebo95 (+1.25%): the composite genuinely picks better breakouts than random stage-2 entries. But portfolio CAGR only +5.1%/Sharpe 0.51 because the six-layer gate fires ~33×/yr and 15 slots sit mostly empty — *deployment*, not philosophy, failed.
- **The governance point:** PARK sanctioned exactly ONE new card (TF-2: 8 slots, two entry tiers, "no other changes", PARK-FINAL after that — "no third iteration; family goes to data-intake dependency"). Iteration is rationed by rule, not by enthusiasm. This also produced recurring lesson #2: **episode alpha does not imply portfolio alpha; slot dynamics are a first-class design variable** (re-confirmed by POS-2).

### Card 3 — EQ-MAX (frozen @ 94786d2) — the single-shot card honored against the Principal's stated target
- **Ask:** stocks-only max-MAR book at the Principal's bar of 30% CAGR / −10% maxDD, using pre-declared vol-targeting + regime-gate overlays, "one canonical parameterization, NO grid".
- **Outcome: NOT DELIVERED, single-shot honored.** EQ-MAX 22.8%/−12.7%/Sharpe 1.67; the raw equal-weight mix actually beat the overlay. The banked conclusion: stocks-only tops out ~Sharpe 1.8 with current sleeves; 30/10 (MAR 3) requires the cross-asset book at ~6–8 independent sleeves. And explicitly: "No tuning pass taken — a fished overlay grid could 'show' 40/−8 and would be a lie."
- **Why it matters:** the card returned a frontier fact instead of a flattering number, and named the exact fraud (overlay-grid fishing) it declined to commit.

### Card 4 — P6 FAILED-BREAKOUT SNAPBACK — the honest 3/4 and the shadow-track disposition
- **Path:** survived the 19-cell TECHNOFUNDA battery (validate +5.16 vs placebo95 +3.95, n=2,328), then the placebo-relative confirmation card, then the full red-team battery.
- **Red-team outcome (2026-07-12): NOT CERTIFIED — 3/4 bars, "strongest stock lead in the firm."** Beats stock-shuffle 95th (+3.59% vs +2.24%), median liquidity ₹127cr, survives 2× costs (+3.09%) — but FAILS year-consistency (6/9 years; profits concentrated in the 2020-21 high-vol recovery).
- **The discipline on failure:** "NO post-hoc regime gate (that would fit the year pattern)." Disposition = **SHADOW-TRACK at zero size** — the regime hypothesis gets tested on FORWARD data only. A Principal idea, an honest 3/4 verdict, kept alive "in the only legitimate way."

### Card 5 — GOLD-TREND / GT-2 (results/GOLD_TREND_20260713) — a bar-design error, and the anti-laundering ruling
- **Outcome: NOT ADOPTED, 1/4 cells** (only golden-cross G4 passed; plateau bar ≥2 failed). The run also surfaced a **bar-design error**: the diversifier correlation bar was written `|corr| < 0.25`, which mechanically fails a NEGATIVE-corr diversifier (G4 monthly book corr −0.30, which is *better* than zero for stacking).
- Rather than quietly re-freezing a "fixed" card, the question — is a GT-2 re-card legitimate or resurrection-laundering? — was **routed to the red team**, with the ledger entry itself declared "the anti-laundering trail."
- **NIKHIL RULING (2026-07-13): GT-2 DENIED-WITH-RESURRECTION-CONDITION.** G4 died on the *plateau* bar (binding), not the corr bar (non-binding) — "fixing a gate that never bound cannot revive the result"; re-classing sleeve→overlay to escape plateau = "bar-shopping." The process fix (all future corr bars SIGNED, `corr < +0.25`) was adopted; the result stayed dead. Resurrection requires ALL of: fresh holdout evidence + 6-month forward shadow, D-034 overlay adjudication with explicit DSR trial penalty, and a DD-parity marginal-book-contribution pass.

**Other notable card outcomes (same book):** BREAKOUT-PACK red-team (frozen @ faed362) found the Principal's audited +182% pack sits **below the stock-shuffle placebo mean** — demoted to "disciplined beta," and the doctrine banked that "prior internal audit verified *accounting*, not *alpha*." CA family: selection REAL (+4–6% over placebo across three versions) but drawdown never armored — the CA-COLLAR card **proved** static index collars make DD worse (−50.1%→−52.4%, 2020 collar −12.2% *despite* the March put paying +17.4%). DECEL-TRAP F&O put spec was **struck from the queue with no trial spent** because its existence card had not confirmed — "building an options vehicle on a failed existence test = laundering." P1-R returned **NOT-ADJUDICABLE** and surfaced a brand-new data landmine (PIT `available_date` coverage ≈ zero pre-2020, so every "validate 2016-2024" fundamentals window was really 2022-2024).

---

## 3.3 Code-level enforcement — `04_RND_LAB/lib/`

Four modules turn the doctrine into machine checks. They are cheap, importable, and mandatory.

| Module | Stage | What it enforces |
|---|---|---|
| **`ast_lookahead_scan.py`** | Pre-flight (static, before the script runs) | Parses the backtest script's AST and flags: `shift(-n)` (future value into present row), `rolling/ewm(center=True)`, `bfill`/`fillna(method='bfill')`, whole-object `.mean()/.std()/.quantile()` etc. on a bare name (full-sample normalization leak), `train_test_split` without `shuffle=False` (temporal leakage), and `[x+y]` forward index arithmetic. Exit 0 = clean; findings must be justified in the run card. Adopted from the Vibe-Trading "purity gate" concept, 2026-07-11. |
| **`lookahead_audit.py`** | Gate-4 (runtime, D-028) | Programmatic battery over the T1–T10 taxonomy on the *data and trade log*: `audit_pit_column()` (decision before `available_date` = hard FAIL), `audit_tz()` (detects the 18:30-UTC daily-bar signature), `audit_same_bar()`, `audit_session()`, `audit_code()` regex greps, plus the **one-day-lag test** harness (`one_day_lag_test(callable)`) — a real edge degrades gracefully when features are lagged one extra day; a leak collapses (>50% collapse = investigate). Owner: Dr. Sameer Bhat. |
| **`guards.py`** | Every backtest entry point (import mandatory) | The landmine guards, each born from a real incident: **L1** `fix_ist_dates()` (HF tz bug; refuses tz-naive stamps), **L2** `drop_preopen()` (≥09:15; auction prints corrupted ~94% of 2026 gap calcs), **L3** `assert_pit()` (no action before `available_date`), **L4** `safe_merge()` (row-explosion detector), **L5** `assert_next_bar()` (the "same-bar sin"), **L6** dual-schema option helpers (`option_schema()`, `clean_daily_options()` dropping 0.00-price untraded strikes, `assert_intraday_capable()`), **L7** `assert_no_future_settlement()` (S-04's 84 fabricated wins from `spot.asof(future_date)`), **L7b** `assert_physical_bounds()` (a short strangle cannot earn more than its premium — 380 rows once violated physics yet passed a generic 60% threshold). Plus **`degenerate_flags()`** post-run: Sharpe>4, CAGR>60% with DD>−10%, equity-curve R²>0.98 (too smooth), tail-seller profile (win>75%, W/L<0.5 → check crash slices), one symbol >30% of |P&L|, negative-without-top-5-trades. |
| **`execution_realism.py`** | Every equity fill (Principal order 2026-07-04, landmine #7b) | `circuit_locked()` heuristic (zero-range single-print days; band-pinned closes at ±5/10/20%), `slippage_multiplier()` (volume ratio ≥0.5 → 1×; 0.2–0.5 → 2×; <0.2 → 3×; zero/NaN volume → **infinite = NO FILL**), composed in `fill_check()` → (fillable, effective_bps, reason). Rationale documented in the module: momentum entries cluster with upper circuits and stops with lower circuits — fixed-bps slippage fabricates impossible fills exactly on signal days. |

---

## 3.4 The lookahead taxonomy — `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` (D-028, BINDING)

Issued 2026-07-04 by Principal order ("ensure no lookahead bias"). Owner: Sameer Bhat; live/paper parity monitor: Ritika Sharma; attack surface: Nikhil Bose. **Gate-4 cannot pass without a LOOKAHEAD AUDIT PASS.** The framing: "unlike overfitting, ONE leaked column can create an arbitrarily large fake return."

| # | Class | The trap | Firm precedent / programmatic check |
|---|---|---|---|
| T1 | Data-availability (PIT) | Using data on its event date, not publication date | Landmine #3; `available_date` mandatory; `audit_pit_column()` |
| T2 | Timestamp/timezone | 18:30 UTC bar = next-day 00:00 IST | Landmine #1; guards L1; `audit_tz()` |
| T3 | Same-bar execution | Signal on bar t's close, fill at bar t | guards L5; next-day-open rule; `audit_same_bar()` |
| T4 | Intraday session boundary | 09:00 pre-open auction print as "open" | Landmine #2; guards L2; `audit_session()` |
| T5 | Survivorship / universe | Screening today's members historically | 42 PIT snapshots mandatory; `audit_universe_pit()` |
| T6 | Normalization leakage | Z-scores/scalers fit on the full sample | Trailing/train-window fit only; `audit_full_sample_stats()` |
| T7 | Label/target leakage | Feature window overlaps label; wrong-date joins | `audit_feature_label_overlap()`; merges reviewed line-by-line |
| T8 | Settlement / lifecycle | Marking open options with FUTURE settles; corp actions pre-ex-date | S-04's 84 fake wins; guards L7/L7b |
| T9 | Walk-forward contamination | OOS opened more than once; thresholds picked after seeing forward | OOS opened exactly ONCE; trials ledger; Sameer verifies run log |
| T10 | Backfilled/revised source | Vendor silently restates history (HF re-uploads, Angel purges) | DATA_CATALOG snapshot dates; results dirs record row-counts+max-dates |

**The audit gate:** (1) run the programmatic battery; (2) walk T1–T10 manually against the CODE ("the machine catches patterns; the human catches intent"); (3) two killer diagnostics — **terminal-date shuffle** (true PIT replay, delete all data after each decision date, ≥20 dates) and the **one-day-lag test**; (4) verdict PASS / PASS-WITH-FLAGS / FAIL filed as `results/<strategy>/<run>/LOOKAHEAD_AUDIT.md`, signed. FAIL = the result is **quarantined** — not quotable in any register, memo, or letter. (5) Weekly live/paper parity check: the paper signal stream must be reproducible from data that existed at signal time.

**Standing code rules:** every feature column carries an as-of comment; `.shift(-n)` forbidden without a `# LABEL:` tag; no full-axis `mean()/std()/rank()` in feature code; date merges via `merge_asof(direction='backward')` or explicit lag; backtests never read files newer than the declared data snapshot.

**The T-log** (the firm's own incidents, kept as institutional shame/memory): the FF-calendar v2 argmax-FF entry (a v1→v2 *rewrite injected* a T9 leak that survived the original kill AND the recheck, caught by Nikhil during the K-012 resurrection review — lesson: diff successive engine versions); S-04 future-expiry settlements (+1.75% fake edge); the HF timezone bug; the pre-open auction bug; earnings joined on quarter-end dates; Angel's contract purges.

---

## 3.5 The placebo & control battery — how a number earns belief

The firm's controls evolved from "beat an index" to a layered battery, each layer added after a specific fraud mode was caught in-house:

| Control | What it kills | Origin incident |
|---|---|---|
| **Same-exit placebo ×200** (random entries, SAME exit engine) | Trail/cap exits harvest drift and flatter ANY entry signal | T-E PEAD: raw +3.48% failed placebo95 +4.70% — the DMA50 trail alone earns +2.14% on random events. Institutionalized in every card since. "The placebo-with-same-exits test is the ONLY reliable arbiter in drifting markets" (AF-07 kill). |
| **Stock-shuffle** (same entry dates, random same-universe stock, same exits) | "Selection" that is really calendar/regime timing | Breakout-pack red-team: the pack's picks sit BELOW the shuffle mean — negative selection. |
| **Date-shuffle** (same spacing, random dates) | Calendar/regime luck in the entry timing | AF-07 kill (date-shuffle placebo +4.05% vs real −0.28%). |
| **Label-permutation** (shuffle event labels within strata ×500) | Spurious event-class spreads | FT-1 filing-time card (night/Friday/late-filer spreads all inside perm95 → family terminally closed). |
| **Lag-decay** (enter +1/+2/+5 days late) | Two frauds at once: a *leak* collapses >50%; *drift-in-costume* shows NO decay (being late loses nothing = zero timing information) | INV-1: entering 5 days late earned MORE → "the signal is index drift." Promoted to the standard battery 2026-07-12. Beta signature confirmed in MidSmall red-team (83–102% retained). |
| **Plateau rule** (≥2 pre-registered cells must pass; neighbors must agree) | Single-cell luck | GOLD-TREND 1/4, VBT 1/4 — both NOT ADOPTED despite one passing cell; S1's 84-cell surface (72/84 positive) is the positive example. |
| **Calendar-specificity** (pseudo-anchor test) | Generic drift dressed as a calendar effect | TOM-VIX: mid-month pseudo-ToM must show <0.5× the real effect — it did (clean), but the effect itself was dead post-2024 (post-publication decay, KB 22/24). |
| **Turnover-matched comparator** | "Beating" a full-churn hurdle by cost savings alone | KB lesson 20 (I-016): a strategy passed DSR 0.9995, PBO 19.8%, plateau, 0-FAIL lookahead — and still had no selection edge; the hurdle paid 3× the costs. SOP amended. |
| **Random-basket null (D-029)** | Index benchmarks flattering cost-loaded stock selection | The honest null = the DISTRIBUTION of 10,000 cost-loaded random baskets, same segment, same position count; percentile bands are the information (60th pct = luck, 95th+ = selection). Standing series in `datasets/derived/benchmarks_random/`. |
| **Era split + embargoed holdout** | Regime-loaded results | Validate/screen windows pre-declared per card; INDEX program constitution: "2026-H2+ = embargoed holdout — no in-sample touch, ever." |
| **2×-cost stress + dual cost models** | Under-costed edges (the most common error per KB 24) | Verdict must survive both flat-point and %-of-premium cost models; K-012's exploratory +0.99 "dies at 2x" and was fenced out of the verdict. |
| **Denominator-free restatement** | Denominator disease (three strikes: FF net-debit, S-02, S-03) | HARD RULE (KB 8): any per-trade return must ALSO be reported in rupee points and % of spot; an edge that changes sign between denominators is an artifact. |
| **Fill-rate / exitability audit** | Placebo-real but untradeable signals | K-012: 61% of forward signals fired into zero-volume back-leg markets; sequence law: fillability → sizing → sensitivity ("a sizing cap of any width cannot fix a zero"). CIO added an exitability tail-veto: 61% dead markets = un-exitable inventory. |
| **Degenerate detectors** | Too-good-to-be-true shapes | `guards.degenerate_flags()` — Sharpe>4, smooth equity R²>0.98, tail-seller profile, single-symbol concentration. |

---

## 3.6 Trials ledger & DSR discipline — `04_RND_LAB/INDEX_PROGRAM_2026/`

**The problem:** after hundreds of tests on the same 2021-26 sample, in-sample statistics stop meaning anything. The firm's answer has three parts.

1. **TRIALS_LEDGER.csv** (`build_trials_ledger.py`): one consolidated denominator of every test ever aimed at the data. Auto-rows harvested from every `results/**/RUN_CARD.json` (card, trials_increment, verdict) + a curated historical block for pre-run-card campaigns (e.g., "S1 sensitivity surface, 84 trials"; "sell-side battery, 45"; "misc 07-07 campaigns, 30"). Every card since 2026-07-11 declares its trials increment in the frozen spec ("Trials +2", "+19"...), and the STOCKS book shows a live countdown (Trials 255 → 252 → 249 → 246 → 242 → 238 → 235 as of 07-13). The trials registry was upgraded to a **PREREQUISITE** — "DSR at graduation gates is uncomputable without N/variance/T/skew/kurt of ALL trials" — blocking for any Gate-4 pass.

2. **DSR_BASELINE.md** (Bailey & López de Prado deflated Sharpe): for S1-F (T=259 daily, SR≈0.243/expiry ≈1.75 annualized), DSR is computed under a *declared grid* of assumptions rather than one flattering number: N ∈ {50, 157, 229} × V[SR] ∈ {tight, wide} → DSR from 0.30 down to 0.00. The interpretation is unusually honest: strict independence overstates deflation (the 84-cell surface is ~5–10 effective trials, not 84; effective-N plausibly 20–40; Bonferroni cross-check p≈0.016), so the verdict is **AMBER, not red** — and the binding conclusion: "In-sample statistics CANNOT settle this after this much search... The forward test is the only exit from this ambiguity."

3. **The sample-is-spent doctrine:** every additional sell-side variant tested on the same 2021-26 sample deflates S1-F further → new research must target NEW data (forward paper, the 2011-21 bhavcopy backfill era, different data families). This is why B1c-DII-flow was killed at t=2.43 vs a 2.5 bar with a resurrection condition of **FORWARD DATA ONLY** (zero-size shadow ledger, re-decide after 60 forward signals, "NO in-sample re-tests, NO threshold changes").

**The IDEA_FACTORY funnel** (`04_RND_LAB/IDEA_FACTORY/PROTOCOL.md`) is the multiple-testing control for high throughput: intake 100+/wave → Stage-1 screen on a fixed recent window (2024-07..2026-06; gate: net expectancy >2× cost, t≥1.5, n≥30) → Stage-2 validation on the **untouched** full history (2013/15..2024-06) with placebo-shares-exit + era split → Stage-3 = the deep-card machinery. Every screened idea is logged so the denominator is complete; killed families are blocked at intake. Results: Wave-1 116 ideas → 6 validated → **0 promoted** ("the untouched-window design caught what would have been 6 fake discoveries"); Wave-2 315 → 2 → 0; running total **442 ideas, 0 certified from price primitives** — which is itself the input to the alpha thesis (§3.9). The INDEX program's Validation Constitution (§5 of its MASTER_PLAN) binds all of this per stream: pre-registration with frozen kill bars, trials ledger + DSR at every IC, era splits, embargoed 2026-H2+ holdout, dual cost models, next-bar fills invariant, one-day-lag test, paper forward test as final arbiter (D-030), red-team before Gate-5.

---

## 3.7 Red-team certification — `07_RISK_OFFICE/ADVERSARIAL_REVIEWS/`

Nikhil Bose (Devil's Advocate) must review before any strategy passes the audit gate. Two filed reviews illustrate the two modes:

### MIDSMALL_VARB_REDTEAM_20260713.md — the anatomy of a modern red-team
Target: the MidSmall momentum rotation sleeve already in the 50L stacked paper book (banked CAGR 22.8%, Sharpe 1.14). Nikhil's method is instructive:
- **Harness integrity first:** his rig feeds randomized scores into the FROZEN engine and reproduces the banked result *exactly* (CAGR 0.2277, Sharpe 1.142) before any perturbation — so every attack runs through the real cost/fill/regime machinery, and D-030 is respected.
- **One focused attack:** the author had self-labelled the sleeve "regime-timing, not selection" — *asserted, never proven with a statistic*. Nikhil proved it: invested-days regression vs MSS400 → beta 1.13, **alpha +0.9%, t=0.16** (the headline +12.4% full-sample alpha is a mechanical artifact of sitting in cash ~31% of the time).
- **Placebo with a self-check:** the D-029 random-selection placebo (N=200) showed gross selection IS real (100th pctile, +12.5pp — the momentum factor premium) but the enormous NET gap is a **turnover artifact** (random churns 42–44×/yr vs momentum's 22×) — Nikhil explicitly "did not let my own kill-test overstate."
- **Correlation-horizon attack:** daily max pairwise corr 0.08 → quarterly **0.53 vs b1b** — the book's "uncorrelated sleeves" claim is a daily-sampling illusion at exactly the horizon where drawdowns live (now KB lesson 25a).
- **Verdict: SURVIVES-AS-BETA** with hard conditions: relabel in the register as risk-managed midcap-momentum *beta*; no independent-alpha credit in the 30/10 frontier math; size on quarterly correlation; expect ~13-14% net, not 22.8%. Plus explicit both-direction triggers: → genuine alpha if invested-days alpha vs a passive midcap-momentum index shows t>2; → KILL if the book keeps presenting it as uncorrelated alpha.

### LEAK_AUDIT_20260711.md — self-red-team of the firm's own process
Triggered by the Principal's challenge ("there will definitely be some loopholes and leaks"). Material findings: (1) **pre-registration was not cryptographically provable** (card + results in one commit) → the standing freeze-commit-alone rule was born here; (2) A4's missing 2011-15 spot data and the SETTLE_PR-not-CLOSE rule flagged into the card before it ran. Also six empirically-checked cleans (stale prints 0/4,245 obs; settlement STT sub-noise; C1 timezone alignment), six documented-not-fixed caveats (USDT≠USD, adj_close vs close for price-level rules, participant-OI T+1 rule), and the honest admission that ~155+ trials on one sample "cannot be closed in-sample — the forward test is the live guard."

**Related certification outcomes:** B1b (FII-minus-Client spread flow) SURVIVED its red-team (shuffle-null 100th pctile, extra-lag flips negative = timely-information signature, 18/18 sensitivity cells positive) — one of only two certified alpha sleeves. AF-07 was killed by its own certification. The BOOK RESTATEMENT of 2026-07-12 is the honest ledger: **certified alpha sleeves = 2 (S1-F, B1b)**; Var-B = regime-timing beta; breakout pack = disciplined beta; "the 30/10 sleeve-count math RESTARTS from 2 certified + 3 shadows (P6, B1c, S1-SX)."

---

## 3.8 The graveyard — `04_RND_LAB/KILLED_IDEAS.md` (D-012, append-only)

Every kill records what/when/WHY (evidence) and the SPECIFIC condition that would reopen it. Current census: **K-001..K-015 plus six named family kills**, ~22 families, spanning intraday option buying (~14 variants), reverse/double calendars, far-OTM longs, 0DTE condors, gap-fades, FF-calendar stops/wings/blacklists, gold-as-crash-hedge, the FF calendar itself, LowVol50 (killed AND resurrected same day when the inflated bar was corrected), semiannual MQ50, regime-switch baskets, air-pocket overlays, standalone stock mean-reversion, post-breakout ORB, AF-07, DII flow, and the 8-construction ADX/ATR family.

Doctrinal features visible in the file:

- **Kills are surgical, not tribal.** K-013 shows the process running in reverse: the kill bar itself was found defective (a chained "p75 path" no random basket ever walked — an always-lucky fiction), Devika honored the pre-registered kill anyway, the BAR was fixed, and the idea was resurrected the same day under the corrected bar. "The process stays trustworthy."
- **Signal-vs-vehicle separation.** Repeatedly a kill states the signal is real but the vehicle dead: K-012 (FF signal at the 100th placebo percentile; calendar vehicle un-fillable), K-stock-meanrev (+0.28% relative timing edge, standalone dead on friction), the ORB family (real +8–13 bps gross, dead vs 35–50 bps friction).
- **The K-012 resurrection review** is the flagship anti-sycophancy artifact: a Principal-triggered "were we too hard on them?" review ran four independent evidence legs (Sameer sensitivity plateau; Nikhil placebo battery — which caught a NEW T9 leak in the firm's own supporting evidence mid-rescue; Tara fill audit — 61% dead markets; Arjun's pre-registered final gate — fwd −0.03/₹100) and returned **STAYS-KILLED-WITH-NEW-INTAKE**. Paper signal-tracking was rejected as scope creep; the FF signal graduated to a genuinely new Structurer intake with 5 pre-registered kills — explicitly "NOT a resurrection of K-012." Honesty-probe conclusion (KB 18): "a review triggered by the boss is not a mandate to manufacture a survivor... Kill credibility is the firm's most valuable asset."
- **Resurrection conditions are constrained to prevent fishing:** typically NEW data only (forward shadows, backfilled eras, different assets), never threshold re-tuning on the same sample ("t=−5 to −7 is not a tuning problem"; "NO re-tuning of trigger thresholds/OI deciles on this dataset").

---

## 3.9 The knowledge base — all firm-earned lessons (`04_RND_LAB/KNOWLEDGE_BASE.md` §A)

"Paid for with real mistakes — never re-learn." The file's numbering has duplicates (two 9s, two 14/15/16/17s from parallel appends); the table below lists every lesson in file order.

| # | Lesson (compressed) | Origin |
|---|---|---|
| 1 | VRP is the meta-edge in Indian options: selling wins, buying loses; every buying family died | K-001, K-004 |
| 2 | The measurement-artifact trophy wall: net-debit denominators, P&L spread across holding days (Sharpe 7–10, Kelly 300), monthly-compounded "+246%/+681%" CAGRs, near-expiry return-on-premium explosions, partial-year "positive every year". Antidotes: exit-period booking, stable denominators, per-trade edge headline, coverage checks | Red Team |
| 3 | Lookahead in stock selection: filters built from realized outcomes are untradeable; live filters must be ex-ante | 16-landmines incident |
| 4 | Tails are unforecastable at trade level, survivable at portfolio level: small size × many idiosyncratic positions, inverse-IV sizing, staggered entries, event gates — stops and bought wings all FAILED | FF tail work |
| 5 | Cap-tier gating is strategy-specific: premium harvesting improves on mid-caps; calendars/binary-event strategies are large-cap only | sleeve studies |
| 6 | Event gates are the cheapest tail insurance (IT earnings −31..−47% through a short straddle) | earnings sleeve |
| 7 | Data coverage is alpha: 88→210 F&O names doubled every sample | bhavcopy backfill |
| 8 | DENOMINATOR DISEASE — hard rule after three strikes: every per-trade return also in rupee points and % of spot; sign-flip between denominators = artifact | FF v1, S-02, S-03 |
| 9a | Pre-IC incremental-shuffle kills fictions cheaply (re-priced S-01 +37.6→+11.4; killed S-02 pre-IC); `c4_short_thru` column contaminated | Gate-5 SOP |
| 9b | Never settle beyond max(available data): `spot.asof(future_expiry)` fabricates wins; physical bounds beat generic thresholds | S-04 → guards L7/L7b |
| 10a | Angel purges expired contracts — capture before expiry or lose data forever | ops incident |
| 10b | Multibagger heat rule: median winner endures 23% intra-year DD; exits must be two-stage (tight initial, then 25–35% trail) | MULTIBAGGER_STUDY, 549 winner-years |
| 11 | Track-2 missing overlays: sector-momentum tilt + quality gate separate compounders from junk rallies | MULTIBAGGER_DNA |
| 12 | Depth beats adjustment as the silent backtest killer: pre-2018 error was missing history (survivorship hole), not bad prices; coverage % now in every data snapshot | 2026-07-04 forensics |
| 13 | Survivorship inflates the NULL too: shuffle gates only honest on the survivorship-complete panel (bias ≈1/3 of measured CAGR, concentrated in one year) | BT-11 union re-run |
| 14a | Fill-rate audit BEFORE sizing/sensitivity: a placebo-real signal can be untradeable (61% dead markets); "a sizing cap of any width cannot fix a zero" | S-03/K-012 |
| 14b | Circuit/volume-conditional fills mandatory: fixed-bps slippage lies exactly where momentum trades | Principal rule → execution_realism |
| 15a | Ex-ante liquidity gates can ADMIT weaker trades — always pre-register gate-vs-drop (dropping +3.88 beat gating +0.99) | K-012 |
| 15b | Random-basket benchmark law (D-029): the honest null is cost-loaded random baskets, percentile bands are the information | benchmark suite |
| 16a | v1→v2 rewrites can INJECT lookahead — diff legacy engines as an audit surface | FF v2 argmax leak |
| 16b | Rebalance cadence IS part of the edge: monthly factor rebalancing = 330–450% turnover = 3.5–10.7pp/yr drag; smallcap "quality" from free data is fiction | D-029 factor family |
| 17a | Entry-fill convention (same-day-close vs D+1) swings ~1pp/₹100 — freeze it in the spec; same-day is the optimistic bound, never the verdict bound | K-012 |
| 17b | Costs invert the size premium: net-of-cost LARGE beats SMALL; MID was the 2005-25 sweet spot; "if p95 looks absurd, check prices first" | D-029 suite |
| 18 | Honesty-probe #1: the kill→challenge→validation loop self-corrected in both directions under soft boss pressure; anti-sycophancy law codified | K-012 review |
| 18b | Percentile-path construction decides kills: skill bars must be percentiles of TERMINAL path outcomes, not chained always-lucky paths | I-016/K-013 |
| 19 | Overlay vs parent controls (K-015): any regime/timing overlay must beat BOTH static parents; corollary discoveries from controls are post-hoc | K-015, I-017 |
| 20 | Turnover-matched comparator: a strategy can pass every statistical gate and still have no selection edge; "gates test the NUMBER; the red team tests the INTERPRETATION" | Nikhil, I-016 |
| 21 | Evaluation is a standing capability: EVALUATION_FRAMEWORK.md (6 modules, 0-100 rubric, hard-fail overrides); route through QFRA 2.0, don't rebuild | Librarian |
| 22 | Post-publication decay = ~50% denominator mis-measurement + ~50% real crowding; separate via tighter forward costs + forward-vs-backtest Sharpe ratio + capacity tracking | LITSCAN 2026-07-07 |
| 23 | Regime filtering on derivatives mean-reversion is survival insurance, not tuning — existential for short-option positions | LITSCAN |
| 24 | Pre-register short-vol forward expectation at 50% of backtest gross; Sharpe>2 claims usually mean under-costed slippage; realistic index VRP = 15–25% XIRR | McLean-Pontiff prior |
| 25a | Sleeve correlation must be measured at the horizon where drawdowns live: daily corr on asynchronous sleeves is an artifact (0.00 daily → +0.36..0.54 monthly); sub-book-Sharpe sleeves cannot improve the frontier at DD parity | CA-BOOK 2026-07-13 |
| 25b | Static index collars cannot armor a stock-selection book: V-recovery whipsaw refunds the crash payout with interest; hedge-basis mismatch (idiosyncratic DD while NIFTY flat). Armor with position-level exits/regime gates or factor hedges | CA-COLLAR 2026-07-13 |

---

## 3.10 The alpha thesis — `04_RND_LAB/ALPHA_FORGE/THESIS.md` (2026-07-12 synthesis)

The distillation of 442 kills and 5 survivors into a positive theory of where the firm's edge can exist:

**The evidence, compressed.** DEAD: *every* price-pattern construction from public knowledge — breakouts (20/55/100/252d), reversion (RSI/z/N-down across stocks/gold/index), seasonality, gap plays, vol-expansion, exhaustion, intraday ORB in every costume — 442 samples, 3 asset classes, two-window tested, not one certified. ALIVE: S1-F (+10.7 pts/day, t=3.9), B1b (+18.5 bps/trade, survived a 3-placebo red-team), and (at the time) AF-07, TF-1's selection layer, the breakout pack — the last three since demoted/killed by the same machinery, which sharpens rather than weakens the thesis.

**Three survival mechanisms — "no exceptions found":**
1. **Structural premium + convexity modifier.** S1-F earns a risk premium that *must* exist (sellers insure buyers) and manufactures its own tail-safety (the 30% SL turned −1.5 into +10.7 pts/day). The edge is not prediction; it is being PAID for a service while capping the service's worst case.
2. **Information asymmetry from proprietary data.** B1b reads participant-positioning flows most retail cannot compute; PIT earnings dates enable event tests others cannot run honestly. The edge is cleaner information, not smarter patterns.
3. **Phase-transition timing.** Buying the *birth* of a trend (stage-1→2 turns, confirmed regime changes with quality gates). Steady-state patterns are arbitraged flat; transitions are structurally hard to arbitrage — rare, heterogeneous, and requiring holding through ambiguity.

**The friction theorem (corollary):** at retail cost an edge must be ≥2× friction per round trip. Patterns visible in any charting app cannot sustain that ("they are sold to retail as courses precisely because they no longer work"); mechanisms 1–3 can, because their scarcity is structural, informational, or psychological — not visual.

**The directed campaign this implies** replaced undirected idea waves with posterior-weighted veins: V1 flow lattice (144 pre-registered cells over participant-OI, BH-FDR(10%) within family + untouched-window confirmation — "the grid IS the hypothesis"), V2 AF-07 certification (which killed it), V3 earnings interaction lattice, V4 option-structure overlays. The V1 execution result is a model of honest lattice work: 4 BH-FDR discovery passes, 0 formally confirmed, but one cell (DII futures-net 5d-flow) replicated sign-and-magnitude across both windows and missed the BH cut by one rank → queued as a single pre-registered confirmation card (B1c) rather than quietly promoted — and then killed at t=2.43 vs the 2.5 bar, with a forward-data-only resurrection condition. Family lesson locked: flow-transforms of FUTURES positioning are the only cell-type with cross-window stability; option-positioning LEVELS are a dead vein (regime artifacts).

---

## 3.11 What makes this a moat

1. **Pre-commitment is cryptographic, not rhetorical** — frozen cards committed alone before runs, hashes in results files, single-shot bars honored even against the Principal's stated targets (EQ-MAX) and his own pet ideas (T-C, P6, DECEL-TRAP).
2. **The controls were each paid for** — every battery element maps to a named in-house incident, and the incidents are preserved (T-log, trophy wall, graveyard) so the tuition is never re-paid.
3. **Anti-sycophancy is tested, not assumed** — honesty probes, boss-triggered reviews returning pre-registered FAILs, a red team that kills its own discoveries and denies bar-shopping resurrections with written rulings.
4. **The denominator of search is public inside the firm** — trials ledger, DSR grids, and the standing admission that the in-sample well is nearly dry, forcing research toward new data.
5. **Negative knowledge compounds** — 442 screened ideas and ~22 killed families constitute a map of where alpha *is not*, which is precisely what funds the alpha thesis of where it *is*.

---

### Improvement opportunities

Prioritized, concrete, from reading the actual machinery:

1. **[HIGH] Consolidate the trials ledger across programs.** `TRIALS_LEDGER.csv` lives in INDEX_PROGRAM_2026 and its curated block predates the STOCKS program; the STOCKS book keeps its own in-prose countdown (255→235) inside MASTER_PLAN.md. One firm-wide ledger (auto-rebuilt nightly from all `results/**/RUN_CARD.json` + curated blocks) with a per-family effective-N clustering column is the prerequisite Sameer's Gate-4 DSR refinement already calls for. Automation candidate: an EOD cron step that rebuilds and diff-alerts.
2. **[HIGH] Make the freeze-commit rule machine-verifiable.** The standing rule (card committed alone before the run) is enforced by habit. A tiny pre-run checker — `verify_freeze.py <card-name>` that confirms the freeze hash exists, contains ONLY the card text, and predates the results dir mtime — would convert the LEAK_AUDIT's fix from discipline into a gate. Could be wired into the RUN_CARD emitter.
3. **[HIGH] KNOWLEDGE_BASE numbering is corrupt.** Duplicate lesson numbers (two 9s, 14s, 15s, 16s, 17s) from parallel appends make citations ambiguous ("KB 14" means two different laws). One librarian pass to renumber with stable IDs (KB-A01..A32) and a cross-reference fixup; then an append-only discipline with next-ID stated at the top.
4. **[MEDIUM] Promote the battery to a single importable harness.** The standard battery (same-exit placebo, shuffles, lag-decay, plateau, era, 2×-cost, degenerate flags) is re-implemented per card script. A `lib/battery.py` with a declarative config (as the IDEA_FACTORY harness already does for screens) would eliminate per-card implementation drift — the CB zero-pick bug and the T-E nan-era KILL-print artifact were both one-off engine defects a shared harness would have caught once.
5. **[MEDIUM] AST scanner gaps.** `ast_lookahead_scan.py` misses: `merge`/`join` on raw date columns (the T7 line-by-line review is fully manual), `.asof()` calls (the S-04 fabrication vector), `resample().last()` boundary leaks, and `numpy` indexing (`arr[i+1]` outside pandas). Adding these four detectors covers the firm's actual T-log incident classes.
6. **[MEDIUM] Institutionalize engine-version diffing.** KB 16a/T-log make v1→v2 rewrite diffs an audit surface, but nothing enforces it. A rule: any script named `*_v{n}.py` whose v{n−1} exists must attach a diff summary to its RUN_CARD; a 5-line git hook can flag it.
7. **[MEDIUM] Shadow-ledger infrastructure.** Three shadows exist (P6, B1c, S1-SX) with per-card wording of the tracking rule but no common ledger/format or automated accrual. A `06_TRADING_DESK/SHADOW_LEDGER.md` + daily EOD append job would prevent the forward evidence from being reconstructed later (a T10 risk: reconstructed shadows are not PIT).
8. **[LOW] Kill-record schema.** KILLED_IDEAS.md drifted from a table (K-001..K-015) to free-form named sections. A uniform schema (id, family, killed-by card+hash, evidence numbers, resurrection condition, resurrection-attempt log) would make the `/resurrect` and prior-art checks greppable and prevent duplicate intake misses as the graveyard grows.
9. **[LOW] Monthly-horizon correlation as a standing gate.** KB 25a / the MidSmall review both establish that daily correlation lies at DD horizon, and the signed-corr template fix exists — but the stacked-book claims still originate from daily numbers with addenda. Bake "monthly-horizon (or DD-window) corr" into the adopt-candidate bar template and the risk-report so the artifact cannot recur.
10. **[LOW] Placebo-engine parity checks.** The breakout-pack red-team carried the caveat "placebo exit engine approximates the pack engine." Adopt Nikhil's MidSmall gold standard as doctrine: every placebo rig must first reproduce the banked real result byte-exactly through the frozen engine before any perturbation is quotable.
