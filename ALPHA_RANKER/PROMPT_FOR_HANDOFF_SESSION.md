# KICKOFF PROMPT — paste this into the $100 execution session

---

You are joining an existing R&D build called **ALPHA_RANKER**. The full plan already exists on this laptop.

**First, do exactly this — do not start coding yet:**
1. Read `ALPHA_RANKER/00_START_HERE.md` (orientation), then `ALPHA_RANKER/PROGRESS.md` (current checkpoint + exact next step).
2. Read `ALPHA_RANKER/01_PHILOSOPHY_AND_ARCHITECTURE.md` and `ALPHA_RANKER/13_EXECUTION_PIPELINE.md` in full.
3. Skim `02`–`12` so you hold the whole design in your head.
4. Confirm back to me, in <15 lines: (a) the four frameworks and how their weights differ, (b) the scoring output contract, (c) what Phase 0 requires, (d) anything in the plan you'd challenge before we spend tokens on it.

**Then:** begin at `13_EXECUTION_PIPELINE.md` **Phase 0**. Work phase-by-phase. After every task, update `ALPHA_RANKER/PROGRESS.md` and write all outputs to disk so nothing is lost to a token limit. Respect the firm's rules in the root `CLAUDE.md`: max 3 parallel agents, no hard-coded thresholds, no lookahead (run the lookahead audit), no silent assumptions — ask me on edge cases.

**Guardrails specific to this build:**
- No fixed metric cutoffs anywhere. Everything is relative to peer/own-history/sector/cap/regime.
- Weights are learned/calibrated through the R&D loop (Phase 6–7), never hand-fixed and shipped.
- No real-money action. Everything is research/paper.
- When you need me to log in to screener.in / provide a Bloomberg dump / pick pilot stocks, ask.

This is a long build. Pace it, checkpoint constantly, and treat `PROGRESS.md` as the single source of truth for "where are we."

---

## Note to the PLANNING session (DESK-20) on transferring the chat itself
If the Principal wants the *conversation* (not just the folder) carried over, the mechanism is:
1. The folder IS the durable artifact — the execution session reads it directly; no chat paste needed.
2. For any nuance that lives only in chat and not in the docs, append it to `PROGRESS.md` §"Context from planning chat" before handoff.
3. If cross-machine: `Compress-Archive ALPHA_RANKER ALPHA_RANKER.zip` and move the zip.
