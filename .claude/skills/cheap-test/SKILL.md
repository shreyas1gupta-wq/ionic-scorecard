---
name: cheap-test
description: Gate-3 of the research pipeline — design and run the single cheapest falsification of a hypothesis, kill threshold pre-registered. Use for /cheap-test <idea-file|hypothesis>.
---
# /cheap-test — minimal falsification (RESEARCH_SOP gate 3)
1. Read the idea's one-pager (`04_RND_LAB/ideas/`); confirm the pre-registered kill threshold EXISTS before touching data (else send back to /idea-log).
2. Spawn `quant-head-arjun-rao`: design the minimal test (event study / decile spread / one-year slice), import `04_RND_LAB/lib/guards.py`, run on cataloged data only.
3. Verdict PASS → advance pipeline stage (auto, D-010) and spec the full backtest next. KILL → KILLED_IDEAS row with resurrection condition + trials count increment. Either way: update IDEA_PIPELINE board + journal one line.
