

## ================ WINDUP CHECKPOINT 2026-07-15 (resume here next session) ================
### RESULTS BANKED & COMMITTED (reliable):
- GRID PUZZLES (objective /2): all 4 models 2.0 -> MODEL_GRID/MG_PUZZLE_SCORES.txt (floor; no discrimination).
- GRID OPEN-ENDED QUALITY, bias-corrected leave-one-out (exclude self-family judge): fable 9.53 > opus 9.25 > sonnet 8.28 > haiku 8.08 -> MODEL_GRID/GRID_QUALITY_CORRECTED.txt. MEASURED judge self-preference: haiku-judge +1.0 to haiku, opus-judge +0.5 to opus (Sonnet<Haiku was self-pref artifact, FLIPPED under neutral judge). Treat grid quality as ROUGH PARITY ~8-9.5, not a clean ranking. Mappings: grid_judge_mapping.json (haiku judge), grid_regrade_mapping.json (opus judge).
- BATTERY single-call arm A cross-model (blind haiku judge, hit=score>=2/16 defective, FP=score<2/4 clean) -> ws4_battery/results/xmodel_grade/BATTERY_RESULT.txt: defects fable 15, sonnet 15, opus 14, haiku 9; FP opus 4/4, sonnet 3/4, fable 2/4, haiku 1/4; cost/defect haiku $0.003, sonnet $0.010, fable $0.099, opus $0.151. HEADLINE: Sonnet = Fable on defects at ~10x lower cost; precision/recall tradeoff inversely tied to verbosity. **battery IS the reliable discriminator (objective ground truth).**
- COST est: MODEL_GRID/COST_ESTIMATE.txt (Haiku $0.025 .. Opus $2.11 for 20-task battery).

### DATA COLLECTED, NOT YET GRADED (opus-base core comparison, run ws4run_opus_20260713/raw):
- arm A (single, no tools): 20/20 | arm B (single+tools): 20/20 | arm C (multi-agent firm): 11/20 | arm C2 (ablation): 12/20
- MG SYSTEM grid (firm pipeline on 8 grid tasks): 8/8 (MODEL_GRID/results/MG0x_SYSTEM.md)

### RUNNING AT WINDUP (session-bound; CANNOT cross-session resume by runId -> use skip-regenerate):
- arm C  wf_4591b6b7 (ws4_arm_c.js) ; arm C2 wf_61f33b05 (ws4_arm_c2.js). If <20 each next session: rerun  (and C2) -> auto-skips completed -> Workflow the .js.

### NEXT-SESSION EXACT STEPS:
1. Complete arm C & C2 to 20/20 (skip-regenerate as above).
2. GRADE opus core arms A/B/C/C2 blind vs sealed key. **JUDGE MUST BE NON-OPUS (use haiku or sonnet) to avoid the measured opus self-preference** on opus-authored arms. Adapt build_battery_xmodel_grade.py (point COLS at the 4 opus arms, model='haiku' judge). One judge/task.
3. HEADLINE: A vs B vs C defects-found; frozen bar = C >= 1.2 x max(A,B) (PROTOCOL S6). Report PASS/FAIL honestly (publish either way). C vs C2 = do personas/naming help.
4. Judge MG SYSTEM grid vs 4 models (add SYSTEM as 5th col, leave-one-out non-self judge).
5. COST/TOKEN metering: ws4_spend_extract.py on the opus workflow transcript dirs -> per-arm tokens/$; arm C cost = sum of 3-stage tokens -> system cost-per-defect vs single-LLM.
6. Assemble full table -> fill SYSTEM_VS_LLM_PAPER_DRAFT.md [RESULT] slots + LINKEDIN_POST_DRAFT.md -> /style-lint -> CHARTS LAST (dataviz + docx_style_kit) -> then REMIND Principal: arXiv decision + his grade spot-audit (FP-on-clean anomaly: opus 4/4, sonnet 3/4 - needs his eyes).

### OPEN INTEGRITY FLAGS (carry into paper limitations):
- Interface confound: fable/sonnet=web, opus/haiku=harness -> verbosity differs; disclose.
- Haiku battery = 18 web + 2 harness (same model, diff interface).
- Arm A blind-mix (ws4run_20260713 Fable) demoted to secondary; opus-base ws4run_opus is primary.
- FP-on-clean high across models -> Principal spot-audit pending before "grades audited by author" line.
### NON-PUBLICATION loose end: S1F-001 paper straddle (14-Jul) exit fills never logged; expiry passed.

### CORRECTED COMMAND REFS (bash ate the backticks above):
- Complete arm C / C2:  python SSP/ws4_battery/build_arm_c_workflow.py ws4run_opus_20260713 C   (and ...C2) -> auto-skips completed -> launch the printed .js via Workflow.
- Grade opus arms: adapt SSP/build_battery_xmodel_grade.py (COLS -> the 4 opus arms A/B/C/C2 in ws4run_opus_20260713/raw; judge model = haiku, NON-opus) -> per-task blind grade -> step3-style unseal.
- Cost/token: python SSP/ws4_spend_extract.py <RUN_ID> <workflow_transcript_dirs...> -> spend.csv.
(SSP = Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM)
