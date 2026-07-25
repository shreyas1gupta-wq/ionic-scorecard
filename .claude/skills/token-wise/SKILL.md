---
name: token-wise
description: TOKEN DISCIPLINE — deliver the best output with the fewest tokens. Apply AUTOMATICALLY (no command needed) whenever a task involves reading files or data (especially docx/xlsx/pdf/csv/parquet), multi-step or long-running work, spawning subagents, choosing a model, or when usage feels tight. Covers plan limits, cheapest-capable model selection, convert-to-Markdown-before-reading (markitdown), lean context, and step-by-step checkpointing so a token limit never loses work. Also invocable as /token-wise or for onboarding teammates.
---

# /token-wise — spend tokens like money

**Mindset: tokens are budget, not exhaust.** Every token spent should buy decision-value. The cheapest token is the one you never spend; the most expensive is the one you spend twice because work was lost or re-derived. This skill is fully portable — install by copying this folder into any repo's `.claude/skills/` (team-wide via git) or your personal `~/.claude/skills/` (all projects).

## 0. Cheat sheet (the commands this skill keeps referring to)

| Command | What it does | When |
|---|---|---|
| `/usage` | Shows plan-limit consumption | Start of day; before big tasks |
| `/context` | Shows what's eating your context window | When a session feels heavy |
| `/cost` | Session spend (API users) | Periodically |
| `/clear` | Wipe context completely | Between unrelated tasks |
| `/compact <focus>` | Summarize history, keep what matters | At milestones, with a focus instruction |
| `/rewind` | Roll back to an earlier checkpoint | Wrong turn — cheaper than redoing |
| `/model`, `/effort` | Pick model / thinking depth | Task start only (cache! see §8) |
| `claude --continue` / `/resume` | Reopen a previous session | After a limit-hit or break |
| Shift+Tab (plan mode) | Read-only exploration, no edits | Before any expensive build |

## 1. Know your limits (before they know you)

- Subscription plans (Pro/Max) meter usage in **rolling session windows plus weekly caps**; exact numbers vary by plan and change — don't memorize them, **check `/usage`**. API users: `/cost`.
- Usage is roughly **cost-weighted by model**: an Opus turn drains your limit ~5x faster than a Haiku turn. Model choice IS limit management. Same logic for the `[1m]` extended-context variants — a huge window filled with junk burns limits faster; a lean context beats a large window.
- **`/context`** shows exactly what's consuming space (files read, MCP servers, conversation). Fix the biggest line item, not the smallest.
- Symptoms you're near a limit: slower responses, auto-compact firing, `/usage` bar near full. **Act at 80%, not 100%** — checkpoint (§7), finish the current step, stop cleanly.

## 2. Right model for the job

Cheapest tier that does the job; escalate only for judgment.

| Tier | Model | Use for | API price in/out per MTok (for scale) |
|---|---|---|---|
| Mechanical | `haiku` | formatting, extraction, file inventory, renames, simple checks | $1 / $5 |
| Analysis | `sonnet` | standard research, code changes, summaries, data work | $3 / $15 |
| Judgment | `opus` | hard synthesis, audits, architecture, final reviews | $5 / $25 |
| Frontier | `fable` (if available) | hardest long-horizon autonomous work only | $10 / $50 |

- Switch with **`/model <alias>`** — but NOT mid-task casually: a model switch **invalidates the prompt cache** (full re-read of history at full price). Pick the model at task start.
- **`opusplan`** = Opus for plan mode, Sonnet for execution — strong thinking where it matters, cheap typing where it doesn't. Excellent default for big builds.
- **Effort levels** (`/effort` or `--effort`: low→max, model-dependent): drop to `low`/`medium` for routine work; changing mid-session also invalidates cache.
- **Subagents:** set `model: haiku` or `model: sonnet` in the agent's frontmatter (`.claude/agents/*.md`). Never let a mechanical subagent inherit Opus.
- Rule of thumb: escalate one tier when the output directly drives a real decision; de-escalate for drafts and mechanical passes.

## 3. Convert before you read (the Microsoft markitdown trick)

Reading binaries (docx/xlsx/pptx/pdf) raw wastes 10–50x the tokens of a Markdown digest. **Always convert first, read the .md.**

- **Generic (any machine):** Microsoft's [markitdown](https://github.com/microsoft/markitdown) — `pip install "markitdown[all]"`, then `markitdown report.docx > report.md`. Handles docx, xlsx, pptx, pdf, html, csv, json, zip.
- **Data files (parquet/csv):** never read raw. Digest with pandas — shape, head, dtypes, describe:
  ```python
  import pandas as pd; df = pd.read_parquet("f.parquet")
  print(df.shape, df.dtypes, df.head(20).to_markdown(), df.describe().to_markdown(), sep="\n\n")
  ```
- If your repo ships its own converter command (e.g. a `/to-md` skill), prefer that — same idea, already wired.
- **Digest once, reference many:** save the digest as `<name>.md` next to a reused source; later sessions read the digest, never the binary again.
- **Grep before Read:** locate the section with search, then Read only that range (`offset`/`limit`). Never read a 5,000-line file for one function.

## 4. Compute in code, reason in the model

- A script run in the shell costs **~0 tokens** regardless of how much it computes. Have Claude write the script and read its (small) output — never perform the computation in conversation. Loops over 500 files, statistics, data validation, log crunching: always a script.
- Long-running work: run scripts **in the background**; don't poll in a chat loop.
- Batch independent tool calls in one message instead of many round-trips.
- API pipeline users: the **Batch API is 50% off** and prompt-**cache reads are ~10%** of input price — structure repeated-context jobs around both.

## 5. Keep the context lean, and ask for less output

- **`/clear` between unrelated tasks.** Stale context is a tax on every subsequent turn.
- **`/compact` at natural breakpoints** (after a milestone, before a new phase), with a focus instruction: `/compact keep only the final schema decisions and open bugs`. Don't wait for auto-compact mid-task — it summarizes at the worst possible moment.
- **Subagents as context firewalls:** verbose operations (test runs, log parsing, doc reading, bulk search) go to a subagent; only its conclusion returns to your main context (full multi-agent rules in §6).
- **Hand off via files, not chat:** agents/steps exchange structured files (results.json, NOTES.md), never long verbal recaps — the telephone game burns tokens and loses precision.
- **Output tokens cost 5x input** — ask for the diff not the whole file, the table not the essay, the top-10 not the full list. Never have Claude print back a file it just wrote.
- **Keep CLAUDE.md under ~200 lines** — it loads every session. Move specialist instructions into skills (loaded on demand, like this one).
- **MCP servers cost context** — audit with `/context`; prefer a CLI tool (zero overhead) over an MCP server when both exist. Disconnect unused servers at session start, not mid-session (cache).
- Compact prompts to agents: pass file PATHS + a precise ask, never paste content the agent can read itself.

## 6. Multiple agents — powerful, and priced per head

Subagents (and multi-agent workflows) are the right tool for isolation and parallelism — and the fastest way to burn 5x tokens when used casually. Rules:

- **Spawn for:** genuinely independent workstreams that can run in parallel (research 3 topics, review 4 modules, sweep many files), or verbose work whose detail you don't need back. **Don't spawn for** short sequential work — an agent's boot context costs more than it saves under ~10 minutes.
- **Parallel = multiplied:** N agents cost roughly N× the tokens. Launch independent agents together (one message) so they run concurrently, but keep it to **2–3 at a time** — sequence waves rather than one big bang; harvest and prune between waves.
- **Brief like a work order:** file PATHS + a precise ask + required output format + where to write results. A vague brief makes the agent re-derive your context at your expense, and a wandering agent is pure burn.
- **Cheapest capable model per agent** (frontmatter `model:` — see §2): scouts and mechanical passes on haiku/sonnet, judgment on the strong model. A fleet of Opus agents drains a weekly limit in an afternoon.
- **Results to disk BEFORE synthesis:** every agent writes its output file first, then summarizes. A limit-hit or crashed agent then loses nothing — you re-read the file, not re-run the work.
- **Files are the bus between agents:** agent A's output file is agent B's input path. Never relay content through your own messages.
- **Continue, don't respawn:** if your setup supports messaging an existing agent, follow up with it (its context is intact) instead of booting a fresh one to re-learn everything.
- **A script beats an agent fleet for mechanical fan-out:** converting 50 files needs a loop (~0 tokens), not 50 agents.

## 7. Step-by-step + checkpoint — a token limit must never lose work

Plan in steps, persist after every step. A limit-hit then costs minutes, not the task.

1. **Size the task first:** one-prompt job → just do it. Session-sized → plan steps. Multi-session → checkpoint file is MANDATORY before starting.
2. **One well-specified first prompt beats ten clarifying turns.** State the goal, constraints, inputs, and what "done" looks like up front — drip-feeding requirements makes the model re-plan (and re-spend) every turn.
3. **Plan cheap, execute once:** plan mode (Shift+Tab) or `opusplan` for anything expensive — read-only exploration is far cheaper than building the wrong thing. Wrong turn mid-build? `/rewind` to a checkpoint instead of re-explaining from scratch.
4. **Write a checkpoint file** (`PROGRESS.md` in the repo) with: goal, step list, DONE so far, exact NEXT action, and where outputs live. Update it after **every** major step — not at the end.
5. **Outputs to disk, always.** Any result that exists only in the chat transcript is one limit-hit away from gone.
6. **On limit-hit / new session:** reopen with `claude --continue` (or `/resume`), read the checkpoint file FIRST, and never redo finished work or re-derive facts already written down.
7. **Long agent runs:** instruct every subagent to checkpoint partial output to disk BEFORE final synthesis, so a mid-flight failure keeps completed computation.

## 8. Cache awareness (free 90% discount — don't break it)

Claude Code caches your context automatically; cached tokens cost ~10%. Protect it:
- **Invalidates cache** (avoid mid-session): `/model` switch, `/effort` change, `/fast` toggle, connecting/disconnecting MCP servers, denying an entire tool.
- **Safe mid-session:** editing CLAUDE.md, changing permission mode, output style.
- Practical rule: choose model + effort + MCP set at task start, then leave them alone until the task ends.

## 9. Anti-waste red flags (catch yourself)

- Reading a binary/office file directly when a digest would do.
- Re-reading a large file already summarized in your notes — trust your own docs.
- Spawning an agent for <10 minutes of work (its boot context costs more than it saves).
- Full re-runs to change one parameter — parameterize the script instead.
- Asking the model to "look through" data a `grep`/pandas one-liner answers.
- Restating long context to an agent instead of giving it a file path.
- Having Claude echo whole files, logs, or datasets back into chat.
- Letting a failing loop retry blindly — diagnose the root cause after the second failure.

## 10. Shared code libraries — reuse, don't re-derive (and don't over-abstract)

Re-deriving the same non-trivial function across scripts costs tokens twice — once to write it, again when a fix lands in one copy and not the others. **Real incident:** the STOCK_SCORECARD_750 build independently re-typed `winsorize`/percentile-rank/ratio-derivation 3+ times across scripts; a financial-sector D/E exemption fix landed in one copy and was missed in another until caught by chance. Consolidated afterward into `STOCK_SCORECARD_750/lib/scorecard_common.py` — that file is the reference pattern.

- **Before writing a non-trivial function, grep the workstream's `lib/` folder first** — reuse beats a rewrite even if the rewrite feels faster.
- **Promote to shared lib only when it's genuinely reused (2+ real call sites) or non-trivial** (a formula that's been wrong before, a sector/schema exemption, anything with a subtle invariant). A 2-3 line one-off calc used once stays inline — extracting it adds an import + a file to navigate for zero amortization. Match the firm's own no-premature-abstraction rule (root CLAUDE.md): three similar lines beat a helper nobody else calls.
- **One import, not a re-type:** `from lib.scorecard_common import winsorize, percentile_rank, ...` — never copy-paste the body "just this once."
- Applies across desks/workstreams, not just this project — if MSQ_BASE, Xorlog, or a new backtest needs the same kind of derivation, check whether an existing `lib/` already has it before writing a fresh version.

## Installing & sharing this skill

Three ways, pick per team:
1. **Team repo (best):** commit `.claude/skills/token-wise/` into your shared project repos — everyone gets it (and future updates) automatically on pull.
2. **Personal, all projects:** copy the folder to `~/.claude/skills/token-wise/` (Windows: `C:\Users\<you>\.claude\skills\token-wise\`).
3. **No repo access:** circulate the folder as a zip; recipient extracts into either location above.

Verify install: type `/token-wise` in Claude Code — it should load. Everything here is tool-generic advice except the exact command names, which are Claude Code's.

**Make it fully automatic (recommended):** Claude auto-loads this skill when a task matches its description, but for guaranteed always-on behavior paste the 10-line kernel from `INSTALL.md` into your personal `~/.claude/CLAUDE.md` — that file loads in every session of every project, no command ever needed. The kernel carries the core rules; this skill carries the detail.
