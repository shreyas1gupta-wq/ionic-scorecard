# PUBLICATION PLAN — Principal decisions (2026-07-13, Q&A of 10)
Binding for the WS-4 publication. The frozen PROTOCOL/bars are untouched by this file.

1. **Framing/naming:** personal experiment, neither company-affiliated nor conspicuously distanced. CONSEQUENCE (flagged): the internal firm name contains the employer's name — public materials use a neutral alias ("a personal 28-agent AI research firm"; internal name and employer never appear). No employer/broker/data-account names anywhere public.
2. **Content scope:** architecture + process + efficacy metrics ONLY (cost, tokens, time-saved, structured-research quality, comparisons vs standalone LLM and vs published agent systems). NO strategy content, NO research findings, NO return figures, NO detailed internal reports.
3. **Negative-result policy:** publish honestly either way. If arm C fails the bar: improvement cycle THEN a NEW battery version (v2, fresh tasks) re-measures — the v1 battery is one-shot per arm (frozen protocol §8, memorization taint) and its v1 result stands unedited. The publication then tells the full journey: v1 result -> what we changed -> v2 result. No silent re-runs on the same instrument, ever.
4. **Paper:** YES, worth writing — target = arXiv-class preprint (methodology/system paper with in-house benchmark; honest fit) + optional later workshop submission (ICAIF / FinNLP class). The LinkedIn PDF is the readable version of the same content.
5. **LinkedIn deliverable:** post + attached PDF; outline-level, copyable-by-design (the reader should be able to reproduce the METHOD: pre-registration freeze commits, adversarial gates, placebo batteries, blind grading, skills list) — usefulness is the engagement engine.
6. **Disclosure width:** generous — several example tasks (defective ones only; never reveal the clean/defective split), the rubric design, the arm prompts, the protocol; withhold only the full answer key + _verify scripts while the battery version is live (v2 supersedes -> v1 can be opened fully later).
7. **Model naming:** explicit (Claude family, exact model ids per run) — transparency is the credibility.
8. **Repeats:** v1 = one run per arm per task (frozen). Paper states this limitation plainly; v2 protocol may pre-register k-repeats reported as mean±sd (all runs reported, never best-of).
9. **Human baseline:** Principal takes the battery himself BEFORE seeing results or key — packet at `ws4_battery/PRINCIPAL_EXAM/` (tasks only, instructions, answer sheet; ~60-90 min). Scored blind by the same rubric alongside the arms. Publishable line: human expert vs single LLM vs the firm.
10. **Reach vs rigor:** defensibility owns the PDF, punch owns the hook, the hook never claims what the PDF cannot back. Principal is willing to fund system improvements before/around publication (see #3 loop) — improvements happen between battery versions, never mid-version.

**#9 RESOLVED (Principal 2026-07-13): labeled-estimate option confirmed** - paper carries 'estimated expert reference point (author estimate, NOT measured): ~60-75% mechanism-level' with basis disclosed; exam packet stays available if he later wants a measured number.

## ROUND-2 DECISIONS (Principal, 2026-07-13 late)
- MEASUREMENT ADDITIONS 1-8 ALL APPROVED: latency/wall-clock, instruction-compliance rate, hallucinated-citation audit, consensus-difficulty map, cost-of-verification share, variance/repeats (v2 only - v1 stays one-shot), memory-recall test (WS-1c), skill-ablation. Plus mandate: find MORE unique publishable metrics.
- PUBLIC ALIAS = **"Firm S"** (all public materials; internal name never appears).
- CHARTS/ILLUSTRATIONS: maximal, best-of-best - BUT LAST, after all results complete (dataviz + docx_style_kit pass).
- ARXIV: decide after charts - REMINDER OWED to Principal at that point.
- TIMELINE: no rush - publish 1-2 weeks out; Fable-dependent runs today, everything else can slip to next week.
- AUTHOR AUDIT OF GRADES (integrity sequencing per D-035): the paper line "grades audited by the author" enters ONLY AFTER the Principal actually does the ~20-min spot-audit - which he committed to do when the report is complete (fits the 1-2 week timeline). Until then the draft carries [pending author audit]. No pre-crediting.

## PIVOT TO OPUS BASE (2026-07-13, Fable exhausted on BOTH accounts; Principal: complete + post this week, use a proxy)
- Fable unavailable -> the model-matched core comparison CANNOT stay Fable-based (arm A alone was Fable; matching B/C to a proxy against a Fable A would be a model-confound). CORRECT PIVOT: primary base model = **Opus 4.8**; run arms A/B/C(/C2) ALL on Opus, matched. New run id: **ws4run_opus_20260713**. Publishable claim becomes 'a multi-agent firm on Opus 4.8 vs a single Opus 4.8 call at catching quant-research defects' - clean, self-contained, honest.
- Fable arm A (ws4run_20260713, 20/20, blind-mix disclosed) is DEMOTED to a labeled SECONDARY cross-model row (single-call battery, Fable) - NOT part of the matched A/B/C.
- MG model-grid: measured haiku/sonnet(5)/opus; Fable OBJECTIVE puzzle cells imputed (labeled); Fable OPEN-ENDED cells = NOT AVAILABLE (Fable budget exhausted) - reported as such, never imputed. SYSTEM row runs on Opus.
- HANDOFF_FABLE_ACCOUNT2.md = DEPRECATED for the core (Fable gone); retained only as bonus if Fable budget ever returns.
- BUDGET FLAG: Opus/proxy draws the shared non-Fable pool (25%% colleague floor). Running A/B now (40 cheap cells), then C (60), C2 only if floor safe. Checkpoint per stage; STOP + tell Principal if approaching floor.
- RUNNING: arms A+B on Opus (wf_e1983d76-8b0). NEXT: arm C on Opus when A/B land.
