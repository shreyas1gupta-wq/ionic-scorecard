# SKILLS INDEX — 48 firm skills (Voyager-style: reuse & COMPOSE before re-deriving)
Convention: each skill names its OWNER agent + what it composes with. Promote any repeated ad-hoc procedure into a new skill (D-022 authority).

## Daily ops (8)
/desk-open · /signals (composes: /events, /pre-trade-check) · /events · /eod · /war-room · /macro-calendar (feeds /events) · /pipeline-health · /risk-report

## Research pipeline (13)
/idea-log (staple /prior-art) · /prior-art · /cheap-test · /backtest (then /oos-audit, /fill-audit) · /deep-dive · /tech-scan · /data-check · /decay-check · /orthogonality · /capacity-check · /crowding-check · /replicate-paper · /reading-group

## Committee & risk (13)
/ic-memo (pre-req: incremental shuffle; composes /red-team, /structure-trade) · /red-team · /news-sweep · /post-mortem · /oos-audit · /pre-trade-check · /var-sanity · /stress-replay · /kill-switch-drill · /structure-trade · /compliance-audit · /attribution · /resurrect

## Execution & paper (5)
/paper · /order-plan · /tca-report · /fill-audit · /edge-decay

## Client deliverables (1)
/Shreyas_Review_Skill - the whole portfolio-review product, statement in and checked deck out.
Two commands from `ionic-deck-kit/`: `qa/check_sync.py`, then
`build/run_review.py <statement> --client "..."`. Supersedes ionic-wealth-complete and ndpms-deck;
composes with Ionic_Portfolio_Review, which stays the deep reference for the scoring chain only.
**Read `references/08_do_not_regress.md` before changing any deck module** - every defect listed
there passed all three QA gates.

## Team & governance (8)
/board-meet · /review-team (anchored rubric, no self-scoring) · /retro (failure taxonomy) · /hire · /approve · /spend-report · /probe-honesty · /prompt-improve
