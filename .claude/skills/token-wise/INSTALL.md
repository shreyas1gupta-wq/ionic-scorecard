# token-wise — Install (2 minutes, Windows shown; Mac/Linux same idea)

## Step 1 — Put the skill folder in place

Extract the zip. You get a folder named `token-wise` (containing `SKILL.md` and this file).
Copy the whole folder to **one** of these:

| Where | Path | Effect |
|---|---|---|
| Personal (recommended) | `C:\Users\<your-name>\.claude\skills\token-wise\` | Works in ALL your projects |
| One team repo | `<repo>\.claude\skills\token-wise\` (commit it) | Everyone on the repo gets it via git |

If the `.claude\skills` folder doesn't exist yet, just create it.

## Step 2 — Make it automatic (no /command ever)

Claude Code auto-loads the skill when a task matches its description. To make the core rules
**always on in every session**, open (or create) the file:

```
C:\Users\<your-name>\.claude\CLAUDE.md
```

…and paste this kernel at the end (Mac/Linux: `~/.claude/CLAUDE.md`):

```markdown
# Token discipline (always on — full playbook in the token-wise skill)
- Before reading any .docx/.xlsx/.pptx/.pdf: convert to Markdown first (`markitdown file.docx > file.md`) and read the .md. For parquet/csv: pandas digest (shape/head/dtypes/describe), never the raw file.
- Search/grep first, then read only the relevant line range. Never read a whole large file for one fact.
- Computation belongs in scripts (~0 tokens), not in conversation; long jobs run in background.
- Use the cheapest model tier that does the job (haiku=mechanical, sonnet=analysis, opus=judgment). Pick model + effort at task start and don't switch mid-task (it invalidates the prompt cache).
- Verbose operations (test runs, logs, bulk search) go to subagents that return conclusions only; hand context between steps via files, never long chat recaps.
- Output lean: diffs not whole files, tables not essays; never echo a file back into chat.
- Any task beyond ~30 min: keep a PROGRESS.md checkpoint (goal, DONE, exact NEXT step, output paths) updated after every step, and write all results to disk — a token limit must never lose work.
- For the full playbook (limits, /compact, cache rules, red flags), load the token-wise skill.
```

That file loads automatically in every Claude Code session — nothing to type, ever.

## Step 3 — Verify

Start a new Claude Code session and type `/token-wise` once — it should load and summarize itself.
From then on it applies by itself: the kernel is always on, and the full skill auto-loads whenever
you work with files, data, subagents, or long tasks.

## One-time extra (for the file-conversion trick)

```
pip install "markitdown[all]"
```

Gives you `markitdown report.docx > report.md` — reading the .md instead of the binary is a
10–50x token saving, the single biggest lever in the whole skill.
