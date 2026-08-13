# QFRA-1 / QFRA-2 Complementarity — Evidence for Product Approval Committee

Prepared by: Vikram Shah (Fund Manager) | 2026-08-04
Purpose: why we run TWO fund frameworks, and whether QFRA-1 is complementary to or redundant with QFRA-2 — Mid/Small/Multi cap specifically.
All figures below were independently re-verified against source by 3 parallel read-only agents this session (file:line citations throughout). Two corrections to the original brief are flagged explicitly in §5 — do not carry the uncorrected versions into the slide.

---

## 1. Per-category recommendation (the deployed six)

| Category | Recommended core | Driving framework | Why (all [DATA] unless tagged) |
|---|---|---|---|
| **Large** | Plain index-core | QFRA-2 | Model-vs-random 3Y edge only **+0.42**, and that row is explicitly labeled **"Large (index)"** in the handoff — i.e. even QFRA-2's own test used an index proxy here, not a deep active-fund panel (`QFRA2_HANDOFF.md:114`). Realized HELD-book alpha is **-0.25%** (n=18, `QFRA2_recommendation_performance.md:18`). QFRA-1 BUY hit-rate is a near coin-flip, **52%** (`ANCHOR_PAIR_STUDY.md:99-101`). Matches existing CEO deployment ruling (`ionic-wealth-complete` skill, "Index-core routing is Large Cap and Mid Cap"). |
| **Large & Mid** | Active (as-is) — but flag execution gap | QFRA-2 | **Best theoretical edge of any category, +2.86** (`QFRA2_HANDOFF.md:108`) — real skill exists here. Yet realized HELD alpha is **-0.38%** (`...performance.md:19`) and QFRA-1's own BUY magnitude is the **weakest of all six categories, +0.66%/68% hit** (`ANCHOR_PAIR_STUDY.md:99-101`, in-file flagged "weakest"). Keep ACTIVE per existing CEO ruling — this is a theory-vs-realization gap for the FM/execution desk to chase (turnover/hysteresis discipline, see §5), not a mandate redesign. |
| **Mid** | **Factor-momentum index** (BSE Midcap 150 Momentum 30) | QFRA-2 smartbeta study, corroborated by QFRA-2's own selection-skill tests (as negative evidence) | Directly confirms the Principal's thesis. Active-selection edge ~**+0.06**, again an **"(index)"**-labeled row (`QFRA2_HANDOFF.md:115`), and realized HELD alpha is the **worst of all 8 sub-books, -3.16%** (n=18, `...performance.md:20`). Meanwhile the factor sleeve, reproduced live from `qfra2_smartbeta.py`/`qfra2_smartbeta2.py`: **+9.52%/yr** excess CAGR over plain Nifty Midcap 150, wins **87% of rolling 3Y** (n=212) and **100% of rolling 5Y** (n=188) windows, **+15.11%/yr post-2018** (vs +7.29%/yr pre-2018 — strengthening, not decaying), max drawdown **-71.7% vs parent's -73.4%** (no extra tail risk — slightly less). [DATA] pre-2022 history is backfilled/hypothetical per both scripts' own output text. Matches existing CEO ruling exactly ("Mid = momentum sleeve"). |
| **Flexi** | Active | QFRA-2, corroborated by QFRA-1 | Second-best theoretical edge (**+1.90**) and the **only category where realized alpha (+2.16%) exceeds the theoretical edge** — skill that shows up in theory shows up in practice. QFRA-1's BUY hit-rate here is the **best of all six, 84%** (`ANCHOR_PAIR_STUDY.md:99-101`). Cleanest active case in the book. |
| **Multi** | Plain index-core, **provisional** — flagged research gap | QFRA-2 | **Worst theoretical edge of any category, -0.10** — a blind random pick beats the model (`QFRA2_HANDOFF.md:110`) — and second-worst realized alpha, **-2.35%** (`...performance.md:22`). This is a *stronger* index-core case than Mid on the numbers, but unlike Mid **we have no evidenced factor-tilt substitute on file** — no Multicap-mandate momentum/quality index has been backtested here. [OPINION] Recommend plain index-core now; flag to R&D (Devika Menon/quant desk) to test whether a Multicap-momentum analogue to the Mid fix exists before the next review — that is "a view," not a completed answer. |
| **Small** | Plain index-core, with QFRA-1's short-horizon signal as a **tactical satellite overlay, not core active selection** | Both, different jobs — see §3 | See full reconciliation in §3 below; this is the one the Principal's thesis needs stress-testing on. |

---

## 2. The overlap — corrected and it's LARGER than the brief assumed

**[DATA]** `final_model.py` (`mr_x_framework/src/final_model.py`), QFRA-2's frozen live engine:
- Line 154: `F['score'] = 0.7 * _rkp(F['score']) + 0.3 * _rkp(F['cap6_ratio'])` — the 6-month capture ratio's weight is **exactly 0.30**, confirmed.
- `down_capture` (a further capture term, computed over a 756-trading-day ≈ 3-year window, `config.py:77`) sits inside the four-term (or six-term, when a live factor-return cache is present) equal-weighted base that gets the remaining 0.7. Its own final weight is **not a fixed constant** — it's `0.7 × 0.9 × (1/len(terms))`:
  - **Richest case** (6 terms, live factor cache present): 0.7×0.9×(1/6) = **10.5%** → combined with the 0.30 = **40.5%**, matching the brief's "~40%" almost exactly.
  - **More common fallback case** (4 terms, no live factor cache — the engine's documented default behavior when the cache is absent): 0.7×0.9×0.25 = **15.75%** → combined = **45.75%**, rising to **47.5%** if `alpha_stab` is also absent.
- **Byte-identical** in the packaged `QFRA2_FINAL/03_CODE/final_model.py` snapshot — no drift between the frozen copy and the live engine on any of these weights.

**Verdict: the honest overlap is ~40-48%, not a flat "~40%."** ~40% is the floor (best case), not the typical case. This means the two frameworks are *even less independent* than the brief stated — say "both of our fund frameworks are at Sell," never "two independent frameworks agree" (this is already the standing Principal-ruling language in `ionic-wealth-complete` §Fund Sell rule — this session's verification confirms it's if anything understated).

**Where QFRA-1 genuinely adds information QFRA-2 doesn't have:**
1. **Recency.** QFRA-1 re-ranks fresh every 6 months on a rolling capture window with its own dedicated, directly-validated backtest (906 formations, explicit BUY/SELL hit-rates). QFRA-2's down-capture term uses a slower 3-year window and is one input blended into a score most of which (52-60%) is unrelated to capture at all — info_ratio, Calmar, 12-1 momentum, and (when live) appraisal ratio/quality-beta. QFRA-1 catches a capture shift faster than QFRA-2's blend will move.
2. **A different validation regime entirely.** QFRA-2 is validated by model-vs-random and HELD-book realized-alpha tests; QFRA-1 is validated by its own formation-level replay. These are genuinely different kinds of evidence about the same underlying signal family, which is useful — but it is evidence about the *same signal*, not a second independent signal.

**Where it's just re-reading the same thing:** whenever a fund's capture profile is simply stable (persistently good or persistently bad), both frameworks will move together because ~40-48% of QFRA-2's score is the same capture data QFRA-1 ranks on directly. Agreement in that regime should not be marketed as two independent checks.

---

## 3. Stress-testing "we have a lot of alpha in smallcap"

**[DATA]** Three facts side by side:
- QFRA-2 model-vs-random, Small, 3Y: model **+2.20%**, random baseline **+2.03%**, incremental edge **+0.17%** (`QFRA2_HANDOFF.md:111`) — one of the two weakest incremental edges of all six categories (only Multi's is worse).
- QFRA-2 realized HELD book, Small, 3Y median alpha: **-1.34%** (n=18, `...performance.md:23`) — negative in practice.
- QFRA-1 anchor-pair replay, Small BUY leg: median **+3.49%**, hit **72%** (`ANCHOR_PAIR_STUDY.md:87,100`) — the strongest or near-strongest BUY signal of any category the firm has measured.

**[INFERENCE] Reconciliation:** these are not contradictory — they are answering different questions. QFRA-2's random-baseline number says almost all (2.03 of 2.20 = ~92%) of what looks like "smallcap return" is available to a blind pick — a size/rising-tide effect, not stock-selection skill. QFRA-2's own selection layer adds next to nothing on top of that (+0.17%), and what little it claims in theory didn't survive to the realized book (-1.34%). That is a direct, data-grounded rebuttal of "active 3-5yr fundamental selection earns its place in smallcap" as literally stated.

QFRA-1's smallcap strength is real (906-formation replicated, not a fluke) but is a **different kind of alpha**: a short-horizon (6-month), seasonally-anchored, capture-persistence signal — funds that protected capital well in the last down-leg tend to keep doing so for ~6 more months. Given §2's overlap finding, this is close kin to (not independent of) the down-capture term already inside QFRA-2's score; it's the same underlying phenomenon read fresher and validated on its own short-horizon terms.

**[OPINION] Verdict on the Principal's claim:** "We have a lot of alpha in smallcap" is true as a *market* statement (smallcap risk premium is large and mostly capturable passively) and true as a *narrow tactical* statement (QFRA-1's 6-month capture-BUY signal is genuinely our strongest edge anywhere in the book) — but **false** as a claim that long-horizon fundamental active selection (the QFRA-2 sense of "active selection") earns its place in Small. Recommend: keep Small's *core* passive/index, run QFRA-1's capture-BUY list as a **named tactical satellite sleeve** with its own sizing and review clock (it is a trading signal, not a buy-and-hold conviction call) — don't badge it as "our smallcap stock-picking alpha," because whoever reads that phrase will assume the QFRA-2-style claim, which the data does not support.

---

## 4. Where the two frameworks can give OPPOSITE calls on the same fund

**[DATA] Already coded and firing — the "Originate and Veto" rule** (`09_PRODUCT/scripts/fund_ctx_adapter.py:merge_calls()`, Principal ruling 2026-08-04):
- QFRA-1 is the only leg with a Sell verdict and a replayed backtest — it **originates**.
- QFRA-2's CALIBRE grade **A or B vetoes** the Sell → **Hold**; C/D does not veto; QFRA-2 can never originate a Sell on its own.
- QFRA-1 Sell + QFRA-2 A/B = Hold, and the disagreement is raised as a **CONTRADICTION** that must appear in the FM review pack, never resolved silently — `build_fund_entries()` returns a 3-tuple `(entries, gaps, contradictions)` for exactly this case.
- **Real documented instance**, not hypothetical: Franklin India Equity Advantage — a QFRA-2 rank-2, A-grade, High-conviction pick — trips this exact gate against a QFRA-1 Sell (`fund_ctx_adapter.py:384-387`, self-test comment naming it explicitly).
- QFRA-1 Sell + no QFRA-2 coverage = Sell, but flagged `SINGLE-FRAMEWORK SELL` for FM sign-off.

**[INFERENCE] A gap the Committee should see:** the coded gate only catches Sell-side disagreement (QFRA-1 Sell vs. QFRA-2 A/B). There is no symmetric gate for the mirror case — QFRA-2 naming a fund a top-2, high-conviction ACTIVE pick while that same fund fails QFRA-1's own down-capture cutoff or ranks outside its category's BUY top-3. Given §2's finding that ~40-48% of QFRA-2's score is the same capture family QFRA-1 ranks on, this mirror case is mechanically possible (a high-CALIBRE fund whose recent 6-month capture just soured) and is not yet instrumented. Worth a ticket, not yet a documented real case.

---

## 5. Corrections to the original brief (verify-before-claiming-done)

1. **The "+0.09%/yr HELD vs +0.48%/yr RAW no-hysteresis" comparison mis-sources the second number.** `+0.09%` (HELD, tau-hysteresis, 3Y) is correct and lives in `QFRA2_recommendation_performance.md:9`. But the actual RAW-no-hysteresis 3Y figure, in the **same file, line 10**, is **+0.56%**, not +0.48%. The **+0.48%/yr** figure that does exist verbatim in `QFRA2_HANDOFF.md:125` is a different, separately-labeled quantity — "Significance-tested selection skill... **+0.48%/yr**, 95% bootstrap CI [+0.06, +1.05], P(>0)=98.8%" for the "ACTIVE pooled (all 8)" 3Y model alpha, not the RAW-no-hysteresis book. The qualitative point survives either way — HELD realizes roughly **16-19% of the theoretical selection edge** depending on which comparator you use — but the slide should cite `+0.09 vs +0.56 (RAW)` or `+0.09 vs +0.48 (significance-tested headline)` and not blend the two into one sentence.
2. **The capture-family overlap is ~40-48%, not a flat "~40%"** — see §2. 40% is the best case, not the typical case.
3. Two of QFRA-2's six model-vs-random category rows (**Large, Mid**) are explicitly labeled **"(index)"** in the handoff — i.e., tested via an index-fund proxy rather than a panel of active funds in that category. This wasn't in the original brief and is worth knowing: it means even QFRA-2's own methodology treats Large and Mid as index-like categories, independently reinforcing the index-core call for both.
4. No sample-size/trial-count is stated for the §5 model-vs-random table itself (only per-category win% pairs); the nearest explicit N found is a footnote for a separate 5Y smallcap recheck (13 dates, 2014-2020) — do not imply the headline 3Y edge table carries a stated N, it does not.

---

## Source index (for the slide-builder — everything above traces to one of these)
- `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/anchor_pair_study/ANCHOR_PAIR_STUDY.md` (QFRA-1 replay, 906 formations; EXTENSION section, lines 43-131)
- `Mf_qfra2-20260529T103217Z-3-001/QFRA2/QFRA2_HANDOFF.md` (§5, lines 103-125: model-vs-random by category)
- `Mf_qfra2-20260529T103217Z-3-001/Mf_qfra2/mr_x_framework/outputs/recommendations/QFRA2_recommendation_performance.md` (HELD-book realized alpha, lines 9-25; byte-identical in the two QFRA2_FINAL copies)
- `Mf_qfra2-20260529T103217Z-3-001/Mf_qfra2/mr_x_framework/src/final_model.py` (score weights, lines 90-159; byte-identical to `QFRA2_FINAL/03_CODE/final_model.py`) + `config.py:77` (ALPHA_WINDOW_D=756)
- `Mf_qfra2-20260529T103217Z-3-001/Mf_qfra2/mr_x_framework/src/qfra2_smartbeta.py` / `qfra2_smartbeta2.py` (Mid momentum sleeve, re-run live this session, not just read)
- `Shreyas_Ionic_AMC/09_PRODUCT/scripts/fund_ctx_adapter.py` (`merge_calls()`, lines ~340-390: the contradiction gate + Franklin India Equity Advantage self-test case)
- `.claude/skills/ionic-wealth-complete/SKILL.md` (Part 3: QFRA-1/QFRA-2 operating rules, CEO deployment-scope ruling, Principal's 2026-08-04 Originate-and-Veto ruling)
