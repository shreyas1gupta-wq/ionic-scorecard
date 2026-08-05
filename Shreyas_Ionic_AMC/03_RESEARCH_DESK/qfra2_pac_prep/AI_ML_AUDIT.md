# QFRA 2.0 — AI/ML Claim Audit (PAC Deck Slide 5)
**Auditor:** Ishaan Gupta (ML/Data Science) · **Date:** 2026-08-04 · **Scope:** Mf_qfra2 repo read-only, NOT modified.
Tags: [DATA] verified against file/line · [INFERENCE] derived · [OPINION] judgment.

---

## 1. What the ranking engine ACTUALLY is (mechanical, one paragraph)
[DATA] `mr_x_framework/src/final_model.py` computes ~6-8 per-fund quant metrics over a 756-day (3y)
trailing window — info_ratio, down_capture, calmar, mom_12_1, alpha_stab, cap6_ratio, and (when a cache
exists) appraisal/quality_beta (lines 93-131). Every metric is converted to a **cross-sectional percentile
rank**: `def rk(s, asc=False): return s.rank(pct=True, ascending=asc)` (:135). Scores are **hand-set
constant-weight blends of these ranks**: `base = sum(terms) / len(terms)` (:143, equal-weight);
`F['score'] = 0.9 * base + 0.1 * rk(F.alpha_stab, asc=True)` (:146); then
`F['score'] = 0.7 * _rkp(F['score']) + 0.3 * _rkp(F['cap6_ratio'])` (:154). Funds are sorted
(`elig = F[F['eligible']].sort_values(['loser_score','score'] ...)`, :174), top-5 shortlisted (:179), and a
human picks the final-2 (discretionary overlay, outside this file). Screens/gates use hard-coded percentile
thresholds (0.75/0.25, :168-170) and AUM floors (`config.py` GATE_MIN_AUM_CR_BY_CAT, :102-103) — all
constants, none fitted. **The one place with a statistically *estimated* (not hand-set) coefficient**:
`ols_appraisal()` (`factors_live.py:223-247`) calls `features.py:ols_alpha_t` — plain `np.linalg.lstsq`
OLS (:38) regressing fund excess return on 6 factor returns — a Carhart/CAPM-style linear factor
regression, not a cross-sectional learned ranker; its output (appraisal, quality_beta) is just 2 of the
~6 ranked inputs above. **No `.fit()`/train-test split/hyperparameter search exists anywhere in the
ranking path.** Grep of all 137 `.py` files in `mr_x_framework/src` for
sklearn/lightgbm/xgboost/tensorflow/torch/keras/RandomForest/GradientBoost/neural: **zero hits** —
independently confirms your preliminary finding.

## 2. Are the 8 legacy sklearn scripts part of the frozen pipeline?
[DATA] **No.** Zero import statements anywhere in `mr_x_framework/src/*.py` reference any of the 8 files
(02/11/21/22/23/25/26/28_*.py) — confirmed by grep, empty result. All 8 do contain `sklearn` (confirmed).
**Two more legacy files are directly relevant and were not in your list:** `34_ml_alpha_predictor.py`
("Phase 10: Non-Linear ML Alpha Predictor" — real `RandomForestRegressor`/`GradientBoostingRegressor`/
`LinearRegression`) and `32_ai_agent_overlay.py` ("Phase 7: AI Agent Overlay"). Neither is imported anywhere
in the repo (grep empty) and both hard-code output paths to `c:\Users\shrey\OneDrive\Desktop\Mf_qfra2\...`
— a different user profile than this machine (`Shreyas.1Gupta`) — i.e. artifacts of an earlier
build/machine, dead before `mr_x_framework` existed. `32_ai_agent_overlay.py`'s "AI Agent" is fully mocked:
`apply_manager_change_nlp()` checks membership in a hardcoded list `known_exits = ['Axis Midcap
Fund-Reg(G)', 'Quant Small Cap Fund(G)']`, with its own comment admitting "we mock it ... to demonstrate
the architecture" (:48-75) — zero NLP, zero model. [INFERENCE] `34_ml_alpha_predictor.py` is almost
certainly the artifact of the rejected ML experiment logged in `QFRA2_HANDOFF.md:144`.

## 3. Verdict on the deck claim
[DATA] Verified slide 5 directly via python-pptx against the live file: `Method: "Rule-based, static
scoring" -> "Dynamic, AI/ML-assisted ranking"`; `Selection: "Direct rules" -> "Shortlist top-5 -> final-2
(ML rank + discretionary overlay)"` (matches your quote exactly).

**FALSE. Remove it.** [INFERENCE] There is no AI/ML anywhere in the deployed ranking path — it is
percentile ranks + hand-set linear blend weights + one optional OLS factor regression (a 60-year-old
statistics technique, not ML) + hard-coded threshold gates. "Dynamic" is defensible (scores recompute as
NAVs update); "AI/ML-assisted"/"ML rank" is not. **Worse: this is a self-contradiction inside the firm's
own materials, not just an audit finding** — `qfra2_deck_v3.py:332` and `qfra2_deck_v4.py:359` (the same
deck-generation lineage that renders the slide-5 claim, at :111-112/:166-167 of those same files) also
render the bullet *"ML on the cross-section -> ~40-60 funds x ~20 dates is too small; it memorises one
era."* `QFRA2_HANDOFF.md:144` confirms: *"...capture w>0.40, ML on the cross-section, metric-bloat (9 of 12
loser-traits): all rejected."* The deck asserts ML-assisted ranking on one slide and documents ML being
tried-and-killed on this exact cross-section elsewhere in the same codebase.

## 4. Where the firm legitimately uses AI/ML — and the boundary
[DATA] `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/FROZEN_METHODOLOGY.md:55` — "**One Sonnet agent
per stock**" doing qualitative research (business model, earnings-quality flags, reverse-DCF judgment,
forward growth estimate) + a separate Technical agent (:59) + an agentic FM pass for trim targets (:91,
113). This is real, and it is LLM-agent-assisted *research/judgment*, not a fitted ranking model — no
`.fit()`, no cross-sectional learned score there either. **Boundary is clean**: grepped both repos in both
directions for cross-references (stock_scorecard/ionic_amc terms in Mf_qfra2; mr_x_framework/final_model
in the firm repo) — Mf_qfra2 has **zero** references to the firm repo or LLM-agent research; the firm
repo's only touches are one-directional consumers of QFRA's *output CSVs* (`fund_ctx_adapter.py`,
`save_mf_recommendations.py`) — they read recommendation rows, they do not run or feed research into the
ranking. STOCK_SCORECARD_750's LLM agents never touch the MF/QFRA model, and QFRA never touches them.
"LLM agents doing research" and "ML ranking" are not the same claim, and neither product currently makes
the latter true.

## 5. The forward question — weakness or feature?
**Honest case for parsimony [OPINION, grounded in DATA above]:** the eligible universe is genuinely tiny —
5-9 funds per deployed category, ~99 funds across all 8 categories (independently cross-checked today
in `03_RESEARCH_DESK/QFRA2_SKILL_RECONCILIATION_2026-08-04.md` §1a via the identical eligibility filter,
same figures), validated over on the order of ~40-150 monthly rolling formations per category
(`ALPHA_WINDOW_D`=756/`ROLL_STEP_D`=21 in `config.py`). A fitted model — even a shallow tree ensemble — has
more effective degrees of freedom than 5-9 cross-sectional points; it will memorize, not learn. This isn't
a judgment call, it's the arithmetic the firm's own rejected experiment already ran into (§2-3 above).
Every weight that *is* in the model was proposed, bootstrap/OOS-tested, and mostly rejected (9 of 12 tried
enhancements killed per `QFRA2_HANDOFF.md:143-144`) — parsimony here is hard-won, not laziness.

**Strongest counter-argument:** small-N kills cross-sectional ML *for this specific ranking step*, but
doesn't rule out ML everywhere in the MF workflow. Pooling across categories and ~10 years of monthly
windows gives thousands of fund-month observations — enough for a regularized *panel* learner (with
strict purged/walk-forward CV) to replace the hand-set 0.9/0.1 and 0.7/0.3 blend constants on the *same*
existing features, which is a materially different (larger-N, still-defensible) claim than "ML ranks the
9 funds." Separately, a real (non-mocked) small NLP classifier could replace `32_ai_agent_overlay.py`'s
fabricated `known_exits` hardcode for manager-change detection — "AI" was already promised there, just
faked; that's the lowest-risk place to make it real. Also: shipping "no ML" while claiming ML is a
standalone credibility risk with PAC regardless of whether ML would help.

**Recommendation:** Keep the ranking engine as-is — do not fit a cross-sectional ranker at N=5-9, that
recreates the exact failure mode already tested and killed. **Drop "AI/ML-assisted ranking" and "ML rank"
from the deck now**; replace with accurate language ("multi-factor quantitative ranking," "OLS
factor-attribution enrichment"). If the firm wants a genuinely defensible AI/ML claim on this product
later, the two lowest-risk real candidates are (a) a purged-CV panel learner over pooled fund-months to
replace the hand-set blend constants, and (b) a real NLP manager-change/red-flag classifier replacing the
mocked one — both are net-new validated work, not a rebrand of what exists today.
