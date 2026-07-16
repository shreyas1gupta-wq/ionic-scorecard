# System vs. Single LLM: Results Filled 2026-07-15

**Status:** Numbers filled from the frozen protocol's grading output, 2026-07-15. `[pending author audit]` markers remain until the Principal completes the ~20-minute grade spot-audit (see §6). Base model for the pre-registered A/B/C/C2 study is **Opus 4.8** (the original Fable-5 arm A is retained as a labeled secondary cross-model data point, §5.5/Table 6, following the mid-study pivot recorded in `SYSTEM_SCIENCE_PROGRAM/PUBLICATION_PLAN.md`). Editorial note (not to be removed before Principal review): the Principal's 2026-07-15 publication-angle ruling directs the *public* LinkedIn version to lead with §5.5-5.6 (cost/accuracy, judge self-preference) rather than the negative system result; this paper, per its own §7 commitment to publish unfavourable outcomes, reports the full pre-registered study. Principal to confirm this split before either goes out.
**Owners:** Quant Head (experiment validity), CEO (program), Librarian (literature). Style target: `00_GOVERNANCE/STYLE_GUIDE.md` (DRAFT).
**Pre-registration:** the bar, the rubric, the 20 tasks, and the arm definitions were frozen 2026-07-12 before any arm ran. This draft cannot change any of them.

---

## Title options

1. **Does Process Beat the Model? A Pre-Registered, Blind Test of Governed Multi-Agent Review Against a Single Frontier LLM on Backtest Defect Detection.**
2. **Guilty Until Proven Innocent: Whether an Adversarial Multi-Agent Firm Catches Backtest Landmines a Single LLM Misses.**
3. **The Firm vs. the Model: A Cost-Metered Benchmark of Multi-Agent Research Discipline on 20 Planted Backtest Defects.**

(Working preference: option 1 for the paper, option 2 for the LinkedIn version.)

---

## Abstract (template)

We test whether a governed multi-agent research process adds measurable value over a single frontier language model on a task where correctness is objective and money is at stake: reviewing quantitative trading backtests for defects that would fabricate or inflate the reported result. We built a 20-task adversarial battery from a documented corpus of nine data landmines and a ten-class lookahead taxonomy accumulated during live quantitative research. Sixteen tasks carry exactly one planted, script-verified defect; four are clean controls that punish false alarms. Three arms review the same tasks under a single identical prompt: (A) one model call with no tools, (B) the same model with code execution, and (C) the firm's review pipeline (a reviewer pass, an adversarial red-team attack, and an overfit/sensitivity check consolidated into one verdict) run at a token budget matched to arm B. A grader blind to arm identity scores each answer 0 to 3 against a rubric fixed in advance, with a penalty for invented defects. The bar was pre-registered before any arm ran: arm C is credited with adding value only if it finds at least 20% more defects in relative terms than the better of A and B, and is non-inferior elsewhere at matched cost.

**Defects found (score ≥ 2 on the 16 defective tasks): A = 15/16, B = 16/16, C = 14/16, C2 (ablation, no personas) = 14/16.** Mean score across all 20 tasks, raw 0-3 scale (see §6 on the grader's inconsistent penalty-field sign, which is why we report raw score rather than a penalty-adjusted composite): A = 2.20, B = 2.25, C = 1.80, C2 = 1.95. **False-positive rate on the 4 clean controls: 4/4 for every arm** — on this model family, every arm claimed a material defect on every clean submission at least once; arms differ in how many spurious defects they invent per clean task (§5.4), not in whether they invent one. **Cost: arm C runs ≈4.5× the tokens of a single reviewer call per task, for equal-or-fewer defects** (§5.3); score-per-dollar and score-per-100k-tokens both favour A and B. **Paired permutation p: C vs. A p = 1.00, C vs. B p = 0.50** (n = 16 paired tasks; §5.2) — the observed 1-2 task gap is well within the range produced by chance alone at this sample size, so we do not claim the gap is statistically distinguishable from noise, even though the *point estimate* itself is unambiguous (C is not ahead). **Verdict against the pre-registered bar: FAIL.** The bar (C ≥ 1.2× the larger of A and B = 1.2×16 = 19.2) was mathematically unreachable against a 16-task ceiling — but this is moot: C (14) sits below *both* A (15) and B (16) outright, so "the multi-agent process did not beat a single model call on this instrument" holds regardless of where the threshold was set. The weakest assumption in this verdict is sample size: n = 16 paired defect-tasks is not enough to rule out that a larger battery would show a different point estimate, and single-run grading (§6) adds measured noise on top of that.

We also report two findings outside the pre-registered bar, from the same infrastructure: a **cross-model cost/accuracy comparison** (§5.5) and a **directly measured LLM-judge self-preference effect** (§5.6), because both bear on how any reader should weigh automated benchmarks generally, including this one.

We release the benchmark design, the controls, and two example tasks. We withhold the full answer key so the instrument survives for future runs.

---

## 1. Introduction

The claim under test is narrow and falsifiable. A team runs a research firm as a set of specialised agents with hard governance: pre-registered hypotheses frozen by git hash, an adversarial reviewer whose only job is to kill a result, a mandatory data-landmine audit gate, and a multiple-testing deflation on every reported metric. A frontier model can be prompted, in one shot, to do the same review. Does the process win, and by how much, and at what cost? If a single model call catches the same defects for a fraction of the tokens, the machinery is overhead dressed as rigour, and we should say so.

Most agent-system papers cannot answer this cleanly because their success metric is soft. "The agents produced a better report" invites a soft judge and a soft conclusion. We chose finance backtest review as the testbed for three reasons, each about measurability rather than domain glamour.

First, the defects are objective. A backtest that books option premium spread across holding days rather than at exit fabricates a low variance and an inflated Sharpe. That is not a matter of taste; it is a wrong number with a known mechanism and a known fix. A reviewer either identifies the mechanism or does not.

Second, ground truth exists and is verifiable. Each planted defect in our battery ships with a Python check (`_verify.py` per task) that demonstrates the corruption numerically, so the answer key rests on executed evidence rather than on an author's opinion.

Third, the consequences are real. This firm has itself shipped fake-looking results and caught them late: a return-on-net-debit metric that exploded as the debit approached zero, a spread Sharpe near 7 to 10 that was a booking artifact, a post-earnings-drift edge that was illiquidity contamination. The landmine corpus that seeds the battery is not hypothetical. It is the list of ways we, and by extension any careful quant, have been fooled by a good-looking equity curve. A review process that cannot catch these on demand is not protecting capital.

The question, then, is whether governance is a real capability or a comforting story. We designed the study so that a negative answer is publishable and, by our own pre-registration, mandatory to report.

## 2. System under test

We describe only the machinery that bears on the claim. The firm operates as roughly 28 role-specialised agents on a shared file tree under version control, coordinated by a written constitution (`CLAUDE.md`) and a research standard of procedure (`04_RND_LAB/RESEARCH_SOP.md`). Four mechanisms are load-bearing for this study.

**Pre-registration by freeze commit.** Once a strategy enters forward test, its spec, code, and parameters are frozen and a git hash is pinned in the register (decision D-030, `01_COMMAND_CENTER/DECISIONS_LOG.md`; example pin `b8d2f3d` in `06_TRADING_DESK/STRATEGY_REGISTER.md`). Mid-test tuning voids the result and restarts the clock. The same discipline governs this experiment: the protocol, rubric, tasks, and bar were committed before the first arm ran, and this draft is downstream of that freeze.

**Adversarial red-team.** A dedicated agent (`.claude/agents/red-team-nikhil-bose.md`) exists to attack a result before capital, distinct from any directional debate about whether a trade is a good idea. Its remit is the evidence, not the position. No strategy passes the audit gate without a red-team pass on record (`07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md`).

**Placebo and control batteries.** The firm runs deliberate null and shuffled arms to catch a pipeline that rubber-stamps everything (the `/red-team` placebo battery and the quarterly `/probe-honesty` anti-sycophancy probe). The four clean tasks in this benchmark are the same idea applied to the reviewer itself: an arm that "finds" a defect where none was planted is penalised, not rewarded.

**Landmine corpus and lookahead taxonomy.** The firm maintains an enumerated list of nine data landmines (`CLAUDE.md`, "DATA LANDMINES") and a ten-class lookahead taxonomy T1 to T10 with a mandatory audit tool (`07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md`, `04_RND_LAB/lib/guards.py`, `lib/lookahead_audit.py`). This corpus is the source material for the battery. Every planted defect is an instance a real desk has hit, documented with date and mechanism.

**Trials ledger and metric deflation.** Reported edges carry a Deflated Sharpe Ratio computed against an honest count of trials and a Probability of Backtest Overfitting, so that a strategy selected out of many candidates is deflated for the selection (RESEARCH_SOP validation battery; DSR and PBO grounding in §4). The ledger is what makes the trials count honest rather than convenient.

These five are the treatment. The benchmark asks whether they, embodied as an agent pipeline, out-detect a single model given the identical task text.

## 3. Related work

**Agent orchestration frameworks.** Current frameworks give durable execution and structured hand-offs but do not gate a hypothesis before a run. LangGraph provides step-level checkpointing and human-in-the-loop interruption (github.com/langchain-ai/langgraph). CrewAI Flows persist and fork run state (docs.crewai.com/concepts/flows). The OpenAI Agents SDK makes delegation a first-class filtered-state hand-off (openai.github.io/openai-agents-python/handoffs). Microsoft's Agent Framework, the successor merging AutoGen and Semantic Kernel, unifies checkpointing, group-chat, and declarative agent definitions (devblogs.microsoft.com/agent-framework). MetaGPT encodes role SOPs as code, "Code = SOP(Team)" (github.com/geekan/MetaGPT). All checkpoint state; none freeze a hypothesis plus its success criteria under a prior sign-off, which is the pre-registration property we test here. (Absence verified by reading each cited document, 2026-07-12; absence in the doc is not proof of absence in the code.)

**Finance agent systems.** TradingAgents runs an N-round bull/bear debate with a facilitator judge and reports return, Sharpe, and max drawdown (arXiv:2412.20138). It is the closest published analogue to a multi-agent finance firm, and it is instructive for what it lacks: no Deflated Sharpe or Probability of Backtest Overfitting, no pre-registration, and only an ad-hoc "no future data per day" rule rather than an enumerated lookahead audit. We note in fairness that the paper's own authors flag their reported Sharpe as suspiciously high, which is exactly the honesty a trials-ledger and DSR are built to enforce ex ante rather than confess ex post. FinRobot draws a hard line where all numbers come from deterministic Python and the model only narrates, with provenance on each output (github.com/AI4Finance-Foundation/FinRobot). FinMem adds importance-weighted memory promotion (arXiv:2311.13743). The debate structure and the numbers-from-Python discipline are good; the missing piece across all of them is an adversarial reviewer of the evidence and a multiple-testing correction.

**Evaluation methodology.** Our design borrows scaffolding rather than dependencies. Inspect-AI (UK AISI) separates a task into Dataset, Solver, and Scorer so the scoring cannot drift between arms, and supports multi-grader majority vote (inspect.aisi.org.uk/scorers.html, /model-graded.html). Promptfoo's `llm-rubric` emits a strict `{reason, score, pass}` JSON contract and runs deterministic checks before the model judge, and its `select-best` and `battle` templates handle paired and arena grading (promptfoo.dev/docs). OpenAI's evals registry separates eval logic from data (github.com/openai/evals). On the risk of using a model as grader, Zheng et al. document position, verbosity, and self-enhancement biases in LLM judges while also showing above-80% agreement with human preference, comparable to human-human agreement (arXiv:2306.05685, "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"). We take both halves seriously: a rubric plus blind labels plus a human spot-audit to bound the bias, and majority vote as the check on grader noise. The deflation statistics we rely on for the "system" claim are Bailey and López de Prado's Deflated Sharpe Ratio (Journal of Portfolio Management, 2014; SSRN 2460551) and Bailey, Borwein, López de Prado, and Zhu's Probability of Backtest Overfitting via combinatorially symmetric cross-validation (Journal of Computational Finance, 2015; SSRN 2326253).

**What is new here.** Against every framework and finance system cited above, four properties are absent in the cited documentation and present in ours: a pre-registration freeze that voids mid-test tuning, an adversarial red-team of the evidence, a deliberate placebo/clean-control arm, and an enumerated data-landmine audit gate (verified-absence table, `04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/WS1D_ECOSYSTEM_SCAN.md`). This paper measures whether those properties earn their cost.

## 4. Methods

### 4.1 The instrument: a 20-task adversarial battery

The battery lives at `04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/ws4_battery/T01..T20/task.md`. Each task is a self-contained review request: a short scenario, a reported result, and either the code that produced it or a results write-up. The reviewer is asked to find any defect that would make the result wrong or fake. Sixteen tasks contain exactly one planted, script-verified defect; four are clean controls with no material defect (T03, T07, T14, T19). Every defective task ships a `_verify.py` that reproduces the corruption numerically; all sixteen ran green on 2026-07-12.

The defects span three classes drawn from live firm incidents.

- **Lookahead and timing.** Signal and execution dates that leak the future into the present. Example (T01, cross-sectional reversal): the signal panel carries UTC timestamps stamped `18:30:00+00:00` (which map to the next IST calendar day), while execution uses an IST-dated close panel; the join silently shifts the effective entry, a timing leak the firm has catalogued as landmine 1.
- **Data landmines.** Schema and settlement traps specific to Indian options and bhavcopy data. Example (T06, monthly short strangle): the payoff reads a settlement level off a spot series at expiry, a construction adjacent to landmine 9, where an expiry-day option settle is the underlying's settlement level rather than the option price.
- **Statistics.** Sharpe inflation, P&L booking, denominator instability, and multiple-testing. Example (T02, dip-buy overlay): a reported per-trade edge and win rate on a small trade count, the kind of result that needs a DSR-and-trials check before it earns a register row.

The three example task texts above are reproduced as exhibits at the end of this section without their answers.

**Why the clean controls matter.** A reviewer that flags a defect on every submission scores perfectly on a battery of defects and is worthless in production, because it cries wolf on the four submissions in five that are fine. The four clean tasks convert that failure mode into a measured penalty: an arm that claims a material defect where none exists is scored 0 on that task and carries a false-positive count. An arm cannot win this benchmark by being maximally suspicious. It has to be right.

### 4.2 The three arms

All three arms review the identical `task.md` text under the identical prompt (§4.3). They differ only in machinery (`ws4_battery/PROTOCOL.md` §2).

| Arm | Definition |
|---|---|
| **A** | One model call, no tools. The arm prompt plus the task text in, one response out, no follow-ups. |
| **B** | One model call with code tools. The model may write and run scratch code in an isolated directory before giving one final answer. |
| **C** | The firm's review pipeline: the standing multi-agent gate (reviewer pass, red-team attack, overfit/sensitivity pass) applied to the same task, consolidated into one verdict, run at a total token budget matched to arm B (§4.4). |

The same base model family and settings apply across arms, with the exact model id recorded per run. Arm C's agents may use their standing persona knowledge but may not open repository files during a run, because the repository contains the answer key and the source landmine documents; reading them would contaminate the arm. Tasks run in fixed order T01 to T20, one fresh context per task, one run per arm per task, no best-of-N anywhere.

### 4.3 Matched-prompt discipline

Every arm receives one prompt, verbatim, and nothing else about the battery. It states the task, asks for each defect by exact line or field with its mechanism and fix, instructs the reviewer to say "No material defect" when that is the truth and not to invent problems, and asks for a closing numbered list of claimed defects. No arm is told the defect classes, the defect count, or that clean tasks exist beyond that shared wording (`PROTOCOL.md` §3). This is the fairness spine of the study: a difference in outcome cannot be attributed to a difference in instruction, because there is none.

### 4.4 Cost metering and the all-tokens rule

Every arm is metered per task: input and output tokens, USD cost at published per-token pricing, and wall-clock. The accounting rule for arm C is frozen and deliberately unflattering: arm C counts all tokens, orchestration overhead, failed agents, and every red-team pass, not merely the tokens in the final consolidated answer. Counting only the final answer would credit the system for work it actually spent. Arm C's per-task budget cap is 1.5x arm B's measured per-task average, with the extra headroom for orchestration; if C exceeds the cap on a task, its answer is whatever the pipeline has consolidated at cutoff (`PROTOCOL.md` §4). We report score-per-dollar and score-per-100k-tokens alongside raw score, because a small accuracy gain bought at ten times the cost is a different finding from the same gain at parity.

An optional extension runs the same battery across a Claude model grid (Fable 5 effort tiers, Opus 4.8, Sonnet 5, Haiku 4.5) to locate the cheapest tier that still catches the landmines, which feeds `00_GOVERNANCE/MODEL_ASSIGNMENTS.md` directly. External models (Gemini, GPT, Grok classes) are not runnable from this harness; per the Principal's ruling of 2026-07-13, their published scores may appear only under a strict borrowing gate (primary source, identical public benchmark and split, stated methodology) and never in the same table as our measured numbers without a `[borrowed]` tag. On this in-house battery, which no external leaderboard reports, that gate excludes external models entirely, and the comparison proceeds Claude-only.

### 4.5 Blind grading

Grading is separated from running so the grader cannot see which arm produced an answer (`PROTOCOL.md` §5). The final answer text of every (arm, task) pair is collected, a scrub pass removes arm-identifying furniture (agent names, persona headers, tool logs, token counts), each answer gets a random id, and the arm-to-id mapping is sealed in a file not opened until all grades are filed. A grader in a fresh session, holding only the answer key and the rubric and the scrubbed answers in shuffled order, scores each answer.

The rubric (`ws4_battery/GRADING_RUBRIC.md`) is fixed in advance. On defective tasks: 0 for missing the planted defect or naming only unrelated problems, 1 for the right area without the mechanism, 2 for the specific mechanism (the exact line or field and why it corrupts the result), 3 for the mechanism plus a correct fix. On clean tasks: 3 for a sound "no material defect", 2 for a thin one, 0 for claiming a material defect. Across all 20 tasks a false-positive penalty of minus 1 applies per invented material defect, floored at 0. The primary metric is the mean per-task score across all 20 tasks after penalties. The false-positive rate on the four clean tasks is reported separately and never blended into the primary metric. Where a score is uncertain between two values, the grader records the lower.

### 4.6 Pre-registered bar

Copied verbatim from `MASTER_PLAN.md` WS-4 and operationalised in `PROTOCOL.md` §6: the firm claims "the system adds value over a single LLM" only if arm C beats both A and B on defects-found by at least 20% relative and is non-inferior elsewhere at matched budget. "Defects-found" is the count of the 16 defective tasks scored 2 or higher (mechanism identified). "At least 20% relative" means C's count is at least 1.2x the larger of A's and B's counts. If C beats on defects-found but posts a worse clean-task false-positive rate than B, the write-up must say so prominently, because a red team that hallucinates defects is not added value.

The direction of a null or negative result is settled in advance. If arm C does not clear the bar, or matches arm B at higher cost, we report that the multi-agent overhead did not pay on this instrument and we explain why. Publishing the theatre outcome when it happens is the credibility of the whole program; a benchmark that can only conclude in our favour is marketing, not science.

### Exhibit A: example task T01 (cross-sectional reversal), answer withheld

```
A junior quant proposes a daily mean-reversion sleeve on the F&O universe. Features come
from a vendor daily parquet; execution prices come from the official NSE close panel.
Reported result: Sharpe 2.4 (2021-2025), +0.19% per trade-day after 5bp/side costs.
[vendor daily OHLCV with tz-aware UTC 18:30 stamps; official NSE close panel on naive IST
dates; join-on-date and next-session entry/exit code follow]
Review this. Identify any defects that would make the result wrong or fake. Be specific.
```

### Exhibit B: example task T06 (monthly short strangle), answer withheld

```
Backtest of the flagship short-vol candidate. Verified entry-day option prices (volume>0
on both legs); spot is the official index close series through 2026-06-30.
Reported result: 90 cycles 2019-01 to 2026-07, hit rate 84%, avg +41 pts/cycle, worst -412.
[45-day entry, 3%-OTM strikes, expiry payoff read off the spot series, costs 4.5 pts/cycle]
Review this. Identify any defects that would make the result wrong or fake. Be specific.
```

## 5. Results

All figures below come from `ws4_battery/results/opus_arms_grade/` (pre-registered A/B/C/C2 study, blind Haiku-4.5 judge — deliberately *not* Opus, given §5.6) and `ws4_battery/results/xmodel_grade/` + `MODEL_GRID/` (cross-model extension). Raw grade files, the sealed answer-to-arm mapping, and the grading workflow scripts are committed alongside this draft.

### 5.1 Primary result: the pre-registered A/B/C/C2 study

### Table 1: Primary results per arm

| Arm | Mean score (0-3, all 20, raw) | Defects found (of 16) | FP rate (of 4 clean) | Total tokens (in+out, 20-task, extrapolated from n=2 measured) | Cost (USD, extrapolated) | Score per USD | Score per 100k tokens |
|---|---|---|---|---|---|---|---|
| A (single, no tools) | 2.20 | 15/16 | 4/4 | ~1.84M (proxied by C's stage-1 call) | ~$32 | ~0.98 | ~0.12 |
| B (single, + code) | 2.25 | 16/16 | 4/4 | ~1.84M (proxied; A/B share one reviewer-call structure) | ~$32 | ~1.00 | ~0.12 |
| C (firm pipeline) | 1.80 | 14/16 | 4/4 | ~8.34M (measured n=2, extrapolated ×10) | ~$137 | ~0.26 | ~0.04 |
| C2 (pipeline, no personas) | 1.95 | 14/16 | 4/4 | ~8.34M (assumed = C; identical 3-call structure, not separately metered) | ~$137 (assumed) | ~0.28 | ~0.05 |

Token/cost columns are extrapolated from a clean 2-task sample metered this session (`OPUS_ARMS_COST.txt`), not a full 20-task measurement — the harness's journal does not persist the agent label needed for full-sample per-arm attribution (§6, tooling limitation). The **token ratio is the number to trust**: arm C spends **≈4.5×** the tokens of a single reviewer call per task (measured directly, pricing-independent); absolute dollar figures assume list pricing on 100% fresh input and are an upper bound (most of the pipeline's later-stage input is cache-read, materially cheaper in practice). Score-per-dollar and score-per-100k-tokens both favour A and B by a wide margin under either the measured ratio or the extrapolated dollars.

### 5.2 Pre-registered bar and statistical tests

### Table 4: Pre-registered bar and statistical tests

| Comparison | Metric | Observed (arm 1 / arm 2) | Difference | Paired permutation p (n=16, 20k draws) | Pre-registered bar | Pass? |
|---|---|---|---|---|---|---|
| C vs. A | defects found (of 16) | 14 / 15 | −1 | 1.00 | C ≥ 1.2 × A (≥18.0) | **FAIL** |
| C vs. B | defects found (of 16) | 14 / 16 | −2 | 0.50 | C ≥ 1.2 × B (≥19.2) | **FAIL** |
| C vs. B | mean score (all 20) | 1.80 / 2.25 | −0.45 | — | non-inferior | **FAIL** |
| C vs. A | mean score (all 20) | 1.80 / 2.20 | −0.40 | — | report only | (worse) |
| C vs. B | clean-task FP rate | 4/4 / 4/4 | 0 | — | C not worse than B | tie (both bad) |
| C vs. C2 | defects found (of 16) | 14 / 14 | 0 | 1.00 | — (ablation, no bar) | tied |

**Overall verdict: FAIL against the pre-registered bar.** The 1.2× threshold was arithmetically unreachable given a 16-task ceiling (1.2×16 = 19.2 > 16), but the qualitative conclusion does not depend on that: arm C found strictly fewer defects than either single-model arm, at several times the cost. The single weakest assumption behind this verdict is sample size — n = 16 paired tasks yields permutation p-values (1.00, 0.50) that cannot rule out sampling noise as the source of the 1-2 task gap; what the data does support unambiguously is that the multi-agent pipeline shows **no positive signal** on this instrument, not that it is definitively worse by a precise margin.

### 5.3 Cost detail

### Table 5: Cost-efficiency (Pareto inputs)

| Arm | Mean score | Tokens/task (measured, n=2 clean sample) | System cost multiple vs. single-LLM proxy | Note |
|---|---|---|---|---|
| A / B (single-LLM proxy) | 2.20 / 2.25 | ~92,110 | 1.0× (baseline) | no-tool / +tools floor |
| C (full pipeline) | 1.80 | ~417,229 | **4.5×** tokens (4.3× $, upper-bound) | reviewer + red-team + synthesis, all tokens counted incl. every stage |
| C2 (pipeline, no personas) | 1.95 | assumed ≈ C | assumed ≈ 4.5× | same 3-call structure; ablation changes only the system prompt, not call count |

The per-stage breakdown (`OPUS_ARMS_COST.txt`) shows the cost is structural, not incidental: stage 1 (reviewer) ≈ 92k tokens/task, stage 2 (red-team) ≈ 98k, stage 3 (synthesis, which re-reads both prior stages) ≈ 227k — synthesis alone costs more than the entire single-LLM baseline. Adding review stages adds tokens faster than it adds defects found.

### 5.4 Where the arms actually diverge

### Table 2: Defects found by class (of tasks in class)

| Class | # tasks | Arm A | Arm B | Arm C | Arm C2 |
|---|---|---|---|---|---|
| Data landmine (schema / settlement) | 4 | 3/4 | 4/4 | 3/4 | 3/4 |
| Lookahead / timing | 8 | 8/8 | 8/8 | 7/8 | 8/8 |
| Statistics (Sharpe / booking / denominator / trials) | 4 | 4/4 | 4/4 | 4/4 | 3/4 |
| Clean controls (correct = score 3, "no defect") | 4 | 0/4 | 0/4 | 0/4 | 0/4 |

No class shows the pipeline (C) ahead of both single-LLM arms. C's two misses are T08 (data landmine) and T11 (lookahead), both caught by at least one single-LLM arm; C2 additionally misses T05 (statistics), which both A and the C pipeline caught. We looked specifically for a landmine class only the pipeline catches — the motivating hope for a red-team stage — and found none in this battery.

**Clean-control behaviour (Table 3, §5.1 note):** every arm scored 0 (the "claimed a material defect" outcome) on all four clean tasks. This is a finding about this model family and this battery's clean-task difficulty, not only about the firm's process: a capable single call also over-flags plausible-looking clean submissions here. Arms differ in *how many* spurious defects they invent per clean task (grader `penalties` field, `combined_grade_journal.jsonl`) — C invents the most on T03 and T19, C2 the fewest across the board — but none avoids the false alarm entirely. We treat this as an open item for the Principal's grade spot-audit (§6) rather than a settled number, because the grader's penalty field was not applied with a consistent sign convention across cells (see Limitations).

### Table 3: Per-task score matrix (0-3, raw, before any penalty adjustment)

| Task | Class | A | B | C | C2 |
|---|---|---|---|---|---|
| T01 | data landmine | 3 | 2 | 2 | 3 |
| T02 | lookahead | 2 | 2 | 2 | 2 |
| T03 | **clean** | 0 | 0 | 0 | 0 |
| T04 | lookahead | 3 | 3 | 3 | 3 |
| T05 | statistics | 3 | 3 | 3 | 0 |
| T06 | lookahead | 3 | 3 | 2 | 3 |
| T07 | **clean** | 0 | 0 | 0 | 0 |
| T08 | data landmine | 2 | 2 | 0 | 0 |
| T09 | lookahead | 3 | 3 | 2 | 3 |
| T10 | statistics | 3 | 3 | 3 | 3 |
| T11 | lookahead | 3 | 3 | 0 | 2 |
| T12 | data landmine | 3 | 3 | 3 | 3 |
| T13 | lookahead | 3 | 3 | 3 | 3 |
| T14 | **clean** | 0 | 0 | 0 | 0 |
| T15 | lookahead | 3 | 3 | 3 | 3 |
| T16 | statistics | 3 | 3 | 3 | 3 |
| T17 | lookahead | 3 | 3 | 2 | 2 |
| T18 | data landmine | 1 | 3 | 3 | 3 |
| T19 | **clean** | 0 | 0 | 0 | 0 |
| T20 | statistics | 3 | 3 | 2 | 3 |

### 5.5 Cross-model extension: cost/accuracy across the Claude family

This extension is outside the pre-registered A/B/C/C2 bar (§4.6) — it reuses the same battery and rubric as a single-call comparison (arm-A-equivalent) across four Claude tiers, blind-graded the same way.

### Table 6: Cross-model single-call comparison (defect-finding battery)

| Model | Defects found (of 16) | FP (of 4 clean) | Battery cost (20 tasks, USD est.) | Cost per defect found |
|---|---|---|---|---|
| **Sonnet 5** | **15/16** | 3/4 | **$0.148** | **$0.0099** |
| Fable 5 | 15/16 | 2/4 | $1.492 | $0.0995 |
| Opus 4.8 | 14/16 | 4/4 | $2.110 | $0.1507 |
| Haiku 4.5 | 9/16 | 1/4 | $0.025 | $0.0028 |

The result is not a price ladder. **Sonnet 5 matches the top defect-finding score (15/16, tied with Fable 5) at roughly one-tenth Fable's cost and one-fifteenth Opus's** — and Opus, the most expensive single-call tier, is *not* the most accurate. Haiku 4.5 is far cheaper again but recall drops to 9/16; verbosity and false-positive rate move together across the grid (mean answer length: Haiku 81 words, Sonnet 296, Fable 667, Opus 972 — the two most verbose tiers also carry the highest clean-task false-positive counts), consistent with a precision/recall trade-off rather than a pure capability ordering. For the firm's own purposes, this cross-model result is the more actionable one: it identifies Sonnet 5 as the cost-efficient default for this class of review task, independent of the negative §5.1-5.2 system finding.

*(Costs are word-length-based estimates at published per-token pricing, not exact API token counts, for the three web-sourced columns; Opus's column is exact-harness where separately available. See `MODEL_GRID/COST_ESTIMATE.txt`.)*

### 5.6 An incidental finding: measured LLM-judge self-preference

While grading a secondary open-ended capability grid (8 tasks, same four models, judged first by Haiku then re-graded blind by Opus as a check), we observed a swing large enough to flip a ranking. The first grading (Haiku judge) placed Sonnet 5 (8.25/10) *below* Haiku 4.5 (9.08/10) on open-ended answer quality. A neutral re-grade by Opus reversed this (Sonnet 8.30 vs. Haiku 8.08). Comparing both judges' scores for every model:

| Model | Haiku-judged | Opus-judged | Δ |
|---|---|---|---|
| Fable 5 | 9.50 | 9.55 | +0.05 |
| Sonnet 5 | 8.25 | 8.30 | +0.05 |
| Haiku 4.5 | 9.08 | 8.08 | **−1.00** |
| Opus 4.8 | 9.25 | 9.75 | **+0.50** |

Each judge inflated its own model family (Haiku-judge → Haiku +1.0, Opus-judge → Opus +0.5) while leaving the two models neither judge shared a family with essentially unmoved (±0.05). This is a direct, measured instance of the self-enhancement bias Zheng et al. (2023) describe qualitatively; we did not design this comparison to find it; it surfaced during a **routine sanity check** the Principal requested after noticing the counter-intuitive Sonnet-below-Haiku ranking. Leave-one-out correction (excluding each model's own family as judge) restores the ranking Fable (9.53) > Opus (9.25) > Sonnet (8.28) > Haiku (8.08), and we treat this dimension as *rough parity within noise and bias*, not a clean ranking — the defect battery (§5.5, objective ground truth) is the more reliable discriminator between models. We report this because a benchmark that only checks its headline claim and not its own grading infrastructure would miss exactly this kind of artifact, and because it is directly relevant to how any reader should weight single-judge LLM evaluations generally.

## 6. Limitations

We state these now, before the numbers, so they cannot be read as post-hoc excuses.

**Sample size.** Twenty tasks, sixteen of them defective, is a small battery. A single task swinging one point moves the mean by 0.05, and the defects-found bar turns on integer counts. We report the paired permutation p-value precisely because the n is small, and we treat a narrow win as a narrow win, not a headline. The battery is a first instrument, not the last word; T21 onward or a v2 extends it.

**In-house benchmark, same organisation.** We built the test we are grading ourselves on. That is a real conflict, and the honest mitigations are structural, not verbal: the bar and rubric were pre-registered before any arm ran, grading is blind to arm identity, four clean controls penalise the reviewer's own over-eagerness, every defect ships an executable verification, and we release example tasks so the instrument is inspectable. The battery was built by a session with access to the firm's landmine documents, and arm C's personas draw on the same documents; that overlap is the treatment, not a leak, and arm A/B fairness rests on the defects being real, self-contained, and detectable from the task text alone, which each `_verify.py` confirms.

**Single model family.** Arms A, B, and C share one base model family (Claude), so this study isolates the effect of process at a fixed model, not the effect of model choice. External models enter only through the strict borrowing gate of §4.4, which this in-house battery excludes, so cross-vendor claims are out of scope by design. The optional model grid varies the tier within the family, not the vendor.

**One run per arm.** The protocol fixes one run per arm per task with no best-of-N, so run-to-run variance is unestimated unless budget allows repeats. If it does, a small number of repeats on a subset would bound the noise; absent that, we read close results conservatively.

**Grading is model-assisted, and we now have a direct measurement of how noisy that is.** A rubric-guided grader can still carry the biases Zheng et al. document, and §5.6 shows this is not merely theoretical: a neutral re-grade of the same open-ended answers moved individual model scores by up to 1.0 point on a 10-point scale purely from judge self-preference. A second, independent observation compounds this: the identical arm-A answer set was blind-graded twice in two separate grading sessions (once as part of the cross-model comparison, §5.5, once as part of the primary A/B/C/C2 study, §5.1) and returned 14/16 and 15/16 defects found respectively — a one-task swing on exactly the same text, same rubric, same model family, from single-pass grading variance alone. We did not average or reconcile these two runs; each section reports the grading it actually used, and we flag the discrepancy here rather than picking the number that reads better. Our mitigations are the fixed rubric, blind labels, the option of majority vote across graders (not yet run at full scale), and a human spot-audit by the Principal on a sample of grades `[pending author audit]`. We additionally found that the grader's `penalties` field (intended as a signed count, negative per invented defect) was populated with an inconsistent sign convention across cells in the primary study — mostly positive integers (a plain count) rather than the intended negative value, in a small number of cells negative as specified. We therefore report raw 0-3 score as the primary per-task metric throughout (Tables 1, 3) rather than a penalty-adjusted composite we could not compute reliably from this field, and treat false-positive counts as a separate, explicitly-labeled quantity rather than folding them into the headline score. This is disclosed rather than silently patched.

**Containment is procedural.** The blind depends on the scrub pass actually removing every arm tell and on the mapping staying sealed until grades are filed. We log the scrub and the seal; a failure there would bias the study, and we would disclose it.

## 7. Ethics and disclosure

The benchmark's value depends on staying unseen by the systems it tests. We therefore publish the design, the protocol, the rubric, the aggregate results, and two or three example tasks, and we withhold the full answer key and the per-task `_verify.py` scripts. Publishing the key would let any future model, ours or a competitor's, memorise the answers and would burn the instrument for the repeat runs that make it useful. The example tasks we do release are spent deliberately, as illustration; the remaining tasks stay closed. When the battery is retired or superseded by a v2, the full key may be released for reproducibility, with that decision recorded in the trials ledger. Borrowed external numbers, if any survive the gate, carry a `[borrowed]` tag and their primary source, and never share a table with our measured numbers. This disclosure section, and the pre-registration it rests on, are the reason a reader should believe a favourable result, and the reason we are bound to publish an unfavourable one.

---

## Reference list (all verified; provenance noted)

Agent frameworks and finance systems (verified in `WS1D_ECOSYSTEM_SCAN.md`, 2026-07-12):
1. LangGraph: https://github.com/langchain-ai/langgraph
2. CrewAI Flows: https://docs.crewai.com/concepts/flows
3. OpenAI Agents SDK (hand-offs): https://openai.github.io/openai-agents-python/handoffs/
4. Microsoft Agent Framework (AutoGen + Semantic Kernel successor): https://devblogs.microsoft.com/agent-framework/migrate-your-semantic-kernel-and-autogen-projects-to-microsoft-agent-framework-release-candidate/
5. MetaGPT: https://github.com/geekan/MetaGPT
6. TradingAgents (Sharpe reported without DSR / pre-registration / lookahead controls; authors flag it as high): https://arxiv.org/abs/2412.20138
7. FinRobot (numbers-from-Python, narration-only LLM): https://github.com/AI4Finance-Foundation/FinRobot
8. FinMem (importance-weighted memory): https://arxiv.org/abs/2311.13743

Evaluation scaffolding (verified in `WS1D_ECOSYSTEM_SCAN.md`, 2026-07-12):
9. Inspect-AI (Dataset/Solver/Scorer; multi-grader majority vote): https://inspect.aisi.org.uk/scorers.html and https://inspect.aisi.org.uk/model-graded.html
10. Promptfoo (`llm-rubric` JSON contract; `select-best`; `battle`): https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/
11. OpenAI Evals (registry, eval templates): https://github.com/openai/evals/blob/main/docs/eval-templates.md

Methodology (verified via WebFetch/WebSearch, 2026-07-12 for this draft):
12. Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena," 2023: https://arxiv.org/abs/2306.05685 (position/verbosity/self-enhancement bias; >80% judge-human agreement).
13. Bailey & López de Prado, "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality," Journal of Portfolio Management 40(5), 2014: https://ssrn.com/abstract=2460551
14. Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting," Journal of Computational Finance, 2015: https://ssrn.com/abstract=2326253

Firm-internal sources (this repository):
15. `04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/MASTER_PLAN.md` (WS-4 design, bars, cost dimension, borrowing gate).
16. `04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/ws4_battery/PROTOCOL.md`, `GRADING_RUBRIC.md`, `T01..T20/task.md`, `_verify.py`.
17. `04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/WS1D_ECOSYSTEM_SCAN.md` (verified-absence table).
18. `CLAUDE.md` (constitution, nine data landmines); `04_RND_LAB/RESEARCH_SOP.md`; `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` (T1-T10); `04_RND_LAB/lib/guards.py`, `lib/lookahead_audit.py`.
19. `06_TRADING_DESK/STRATEGY_REGISTER.md` (freeze-hash pins, e.g. `b8d2f3d`); `01_COMMAND_CENTER/DECISIONS_LOG.md` (D-030 freeze rule).
20. `.claude/agents/red-team-nikhil-bose.md`; `07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md`.

---

*All `[RESULT: ...]` markers and Table 1-6 cells are filled as of 2026-07-15. Remaining open items before publication: (1) the Principal's grade spot-audit `[pending author audit]` on a sample of the blind grading (§6) — the FP-on-clean-controls result (§5.4) and the two grading-noise/self-preference findings (§5.6, Limitations) are exactly what that audit should stress-test first; (2) the arXiv-vs-internal-only publication decision, Principal's call, deferred to after the charts pass per `PUBLICATION_PLAN.md`; (3) the Principal's confirmation of the paper-vs-LinkedIn emphasis split noted in the header; (4) a `/style-lint` pass and CEO+CIO style/approval review per `00_GOVERNANCE/STYLE_GUIDE.md`.*
