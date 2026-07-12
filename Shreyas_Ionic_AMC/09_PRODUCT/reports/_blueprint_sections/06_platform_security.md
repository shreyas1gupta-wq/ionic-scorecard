# SECTION 6 — SKILLS, TOOLING, SECURITY & PLATFORM

*Blueprint section, researched 2026-07-12 from the live repo. Everything below was read from actual files; paths are absolute or repo-relative to `...\Desktop\Backup\NIFTY 500\`.*

---

## 6.1 The skill library (the firm's "standard operating procedures as code")

The firm runs on **79 project-level skills** in `.claude/skills/` (all 79 folders are versioned in git — 408 tracked files under `.claude/skills/` alone) plus **2 user-level skills** in `C:\Users\Shreyas.1Gupta\.claude\skills\` (`qfra2-rerun`, `token-wise`). A skill is a Markdown playbook (`SKILL.md`, sometimes with `scripts/` and `references/` subfolders) that any agent can invoke as a slash command (`/eod`, `/backtest`, ...). In practice the skill library IS the firm's procedures manual: every recurring meeting, research gate, risk report and ops routine has a named, versioned skill.

### Full inventory by function

| Category | Skills | Purpose |
|---|---|---|
| **Firm cadence / ops** | `desk-open`, `eod`, `weekly-meet`, `board-meet`, `war-room`, `pipeline-health`, `compliance-audit`, `spend-report` | Session open/close routines, the Monday leaders' meeting, monthly board, live market war-room, weekly pipeline health, monthly compliance spot-audit, token-spend rollup |
| **Research pipeline gates** | `idea-log`, `prior-art`, `cheap-test`, `backtest`, `sensitivity`, `lookahead-audit`, `oos-audit`, `fill-audit`, `red-team`, `resurrect`, `edge-decay`, `decay-check`, `crowding-check`, `orthogonality`, `capacity-check` | The stage-gated R&D pipeline: intake → prior-art check → cheapest falsification (Gate-3) → full backtest with guards (Gate-4) → overfit battery (DSR/PBO) → lookahead audit (T1–T10 taxonomy, D-028) → adversarial Red Team review → register or kill (with resurrection conditions) |
| **Risk office** | `risk-report`, `pre-trade-check`, `var-sanity`, `stress-replay`, `kill-switch-drill`, `post-mortem` | RP-29..36 risk pack, mandatory pre-trade gate, tri-method VaR reconciliation, historical crisis replays (Mar-2020 / 2022 hikes / Jun-2024), circuit-breaker drills |
| **Trading desk** | `signals`, `paper`, `order-plan`, `structure-trade`, `tca-report`, `events`, `macro-calendar`, `news-sweep` | Live signal scan on Angel data, paper-ledger log/mark/reconcile, order slicing plans, options vehicle design, implementation-shortfall TCA, event-window gates |
| **Analysis / IC** | `ic-memo`, `deep-dive`, `tech-scan`, `attribution`, `replicate-paper`, `reading-group` | Investment Committee memos, fundamental forensics, Minervini trend-template scans, P&L decomposition, paper replication queue |
| **Data office** | `data-check`, `factor-indices`, `to-md` | D-009 dataset verification gate; NIFTY factor-index benchmark refresh (home-network only — office proxy blocks it); binary→Markdown conversion (35x+ token reduction) |
| **Governance / HR / self-improvement** | `hire`, `retro`, `review-team`, `probe-honesty`, `prompt-improve`, `approve` | End-to-end agent onboarding (persona + roster + model assignment), post-task lesson capture into personas, quarterly gamified performance review with AlphaPoints, quarterly anti-sycophancy probe (seed a flawed claim, test dissent), evidence-based prompt evolution, the D-020 Principal-approval workflow |
| **Token discipline** | `token-wise` (project + user copy), `to-md` | The firm's token constitution: cheapest-capable model, markitdown-before-binaries, checkpoint-before-limits, /usage-at-80% |
| **Engineering practice** (superpowers suite) | `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `subagent-driven-development`, `using-git-worktrees`, `finishing-a-development-branch`, `using-superpowers`, `writing-skills`, `karpathy-guidelines`, `task-observer`, `find-skills` | Disciplined software workflow: plan-before-code, TDD, debug-before-fix, verify-before-claiming-done, plus meta-skills for discovering and writing new skills |
| **Design / product** | `design`, `design-system`, `banner-design`, `brand`, `slides`, `ui-styling`, `ui-ux-pro-max`, `impeccable`, `21st-cli-use` | Principal-facing deliverables, dashboards, the fno_game web product, investor-letter visuals |
| **Web acquisition** | `scrapling-official` | Anti-bot scraping framework (Cloudflare bypass, stealth browsing) for data acquisition under D-033 |

### The skills that matter most day-to-day

- **`token-wise`** — the economic constitution. Tokens are treated as risk capital: rolling plan-limit awareness (`/usage` at 80% → checkpoint and stop cleanly), model tiering (haiku=mechanical, sonnet=analysis, opus=judgment; "an Opus turn drains limits ~5x faster than Haiku"), never read a binary file raw (`markitdown` first), computation in scripts not conversation. Installed at both project and user level so it applies in every repo.
- **`eod`** — the daily close. Verifies the `AngelDailyOptionCapture` health line in `capture.log`, pings data freshness, retries the pending Angel OHLCV straggler queue, confirms expiry-week contract capture, journals.
- **`retro`** — the self-improvement loop: any mistake or Principal correction becomes a lesson written into the responsible agent's persona file (and propagated to the KNOWLEDGE_BASE / CODE_CHECKS firewalls if generalizable).
- **`lookahead-audit`** — mandatory before any Gate-4 pass or quoted result (D-028); owned by Dr. Sameer Bhat; backed by `04_RND_LAB/lib/lookahead_audit.py` plus a one-day-lag test. (Note: its `SKILL.md` description is a bare one-liner — thin relative to its criticality; see improvements.)
- **`to-md`** — the single biggest token lever: converts docx/xlsx/csv/parquet/pdf to lean Markdown before any read.
- **`hire`** — how the 28-agent team grows: persona file in `.claude/agents/`, TEAM_ROSTER row, MODEL_ASSIGNMENTS entry, CLAUDE.md table row, EVOLUTION_LOG entry — one skill guarantees no step is forgotten (most recent use: `hedge-expert-kabir-anand.md`, E-028).
- **`qfra2-rerun`** (user-level) — re-runs the frozen QFRA 2.0 mutual-fund ranking model ("Mr. X") for the Principal's personal fund picks.

All 31 agent personas live in `.claude/agents/` (also git-tracked), so the entire "team" — people, procedures, governance — is reproducible from the repo alone.

---

## 6.2 Environment & platform facts (hard-won, codified in root `CLAUDE.md` §ENVIRONMENT)

These are landmines discovered the expensive way and frozen into the constitution so no session re-learns them:

| Fact | Detail |
|---|---|
| Python interpreter | `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe` — the bare `python` alias is **broken** on this machine; every script/task must use the full path |
| Console encoding | Windows console is cp1252 → always `PYTHONIOENCODING=utf-8`, `PYTHONUNBUFFERED=1`, else Unicode output crashes scripts |
| Corporate TLS interception | `truststore.inject_into_ssl()` required before any HTTPS (corporate MITM proxy certificate) |
| Proxy throughput | ~0.7 MB/s; **sequential** `requests.Session()` only — threaded downloads stall |
| NSE access | Partial: `nsearchives.nseindia.com` bhavcopy zips + board-meetings/event-calendar APIs work after cookie warm-up (370+ downloads verified 2026-07-03); other `/api` endpoints (FII/DII, constituents) 403 from the office network → need home network/VPN |
| Angel SmartAPI | Rate limit AB1021 → ≥1.2 s/request with retry passes; `getCandleData ONE_DAY` bars stamped 00:00 IST (intraday `fromdate` silently drops day 1 — landmine #8); Angel purges expired option contracts from its scrip master |
| PowerShell 5.1 | No `&&` pipeline chaining; here-strings break Python raw strings → always write Python to `.py` files and execute, never inline |
| OS / hardware | Windows 11 Pro on a single corporate laptop (`24C-LTPAWM-0003`); repo root inside corporate OneDrive |
| Local web product | `.claude/launch.json` defines one launch config: `fno-game` — uvicorn serving `09_PRODUCT/fno_game/server/app:app` on `127.0.0.1:8787` |

---

## 6.3 Git posture — what is versioned, what is deliberately not

Local git repo at the project root: **1,288 tracked files, 187 commits, `.git` = 35 MB, NO remote configured** (`git remote -v` is empty). Local-only is deliberate (BACKUP_POLICY D-003): a hardcoded HF token in legacy `data/hf_*.py` scripts must be scrubbed before any push.

`.gitignore` design (comments in the file itself state the rationale):

| Excluded | Why |
|---|---|
| `datasets/`, `*.parquet`, `*.h5`, `*.feather`, `raw/`, `Strategy_Results/`, `05_DATA_OFFICE/data/` | 28+ GB of data — regenerable/re-downloadable, never in git |
| Master universe workbooks (`Nifty500_Master_Dataset_2005_2025.xlsx` etc.) | Already versioned by OneDrive |
| `.claude/settings.local.json`, `*creds*.json`, `*angel_cfg*` | **Secrets exclusion patterns** — account-specific settings and Angel credential files can never be committed even if copied in by mistake |
| `*.zip .png .pdf .docx .xlsx .csv .jsonl`, `scrip_master.json` | Binary outputs, regenerable by scripts |
| `__pycache__/`, `.venv/`, OS noise | Standard hygiene |

**What IS versioned:** all code, the entire `Shreyas_Ionic_AMC/` firm OS (governance, journals, decisions, memos, killed ideas), all 79 skills, all 31 agent personas, `CLAUDE.md`, `.claude/launch.json`. Git history is the point-in-time record of every decision and prompt — the firm's institutional memory is fully reconstructible from a clone.

---

## 6.4 Credential handling — where the secrets actually live

**Design intent (BACKUP_POLICY §4):** credentials live *outside* the repo in `C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\` and are not backed up to OneDrive-visible paths; the Principal holds the originals.

**Actual state, verified 2026-07-12:**

| Location | Contents | In git? | In OneDrive? |
|---|---|---|---|
| `AppData\Local\angel_capture\creds.json` | **Full Angel credential set in plaintext**: `api_key`, `client_id`, login **PIN**, and **TOTP secret seed** | No | No |
| `AppData\Local\angel_capture\angel_cfg.py` | Login helper — correctly reads from `creds.json`, no literals | No | No |
| Old session scratchpad (`AppData\Local\Temp\claude\...\d096bfac...\scratchpad\angel_cfg.py` + its `.pyc`) | **All four secrets hardcoded as string literals** (API key, client ID, PIN, TOTP seed) — an earlier-generation copy that was never cleaned up | No | No |
| Project `CLAUDE.md` (git-tracked, OneDrive-synced) | Angel **API key** (`8crMtPbu`) and **client code** (`S59047501`) in plaintext | **Yes** | **Yes** |
| `HANDOFF.md`, `other2\MANIFEST.md` (git-tracked) | Same API key + client code; HANDOFF.md also carries the **HuggingFace token** literal | **Yes** | **Yes** |
| 8 git-tracked Python files (`intraday_options_strategy/data/hf_*.py`, `05_DATA_OFFICE/scripts/hf_us_stocks_daily.py`) | Hardcoded **HF token** | **Yes** | **Yes** |
| Auto-memory dir (`~\.claude\projects\...\memory\reference_hf_token.md`) | HF token again | No (outside repo) | No |
| Repo research scripts (`results/S-03/.../live_ff_check.py` etc.) | Clean — read `creds.json` by path, **no literals** (correct pattern) | Yes (code only) | Yes |

Mitigating context: the Angel account is **fund-less and data-only** (hard rule: no real-money trades, ever), so credential compromise cannot move money today. But the PIN + TOTP seed together are a complete login — see the security audit below.

---

## 6.5 Two-account / two-desk sync mechanism

Two Claude accounts operate the same folder on the same laptop:
- **DESK-20** (desktop app, $20 plan) — CIO office: R&D, ideas, light analysis, ≤2 parallel subagents.
- **DESK-100** (VS Code, $100 plan) — execution floor: backtests, bulk data, EOD auto-runs, ≤3 parallel subagents (D-023).

Sync is achieved by three shared layers, in order of freshness:
1. **`01_COMMAND_CENTER/CURRENT_STATE.md`** — live state; every session MUST read it at start and update it at end (Session Protocol step 1/2 in CLAUDE.md).
2. **`01_COMMAND_CENTER/SESSION_JOURNAL.md`** — append-only log per session (date, account, what was done, files touched, next steps); each session reads the last ~2 entries.
3. **Git commits** — every session ends with a commit; history is the audit trail and recovery layer.

Plus the **shared auto-memory** (`~\.claude\projects\c--Users-Shreyas...\memory\MEMORY.md` + 11 topic files): both accounts read the same memory directory; the index file explicitly instructs "identify desk by harness (VS Code = DESK-100, desktop app = DESK-20)". Long tasks checkpoint continuously to files so either account (or a token-limit restart) can resume mid-task. The physical medium of sync between the two accounts is simply the shared filesystem (they are the same Windows user on the same laptop); OneDrive additionally replicates the folder to the cloud.

Concurrency control is minimal: `.claude/scheduled_tasks.lock` (a JSON `{sessionId, pid, acquiredAt}`) prevents two sessions from both arming the Claude cron jobs, but nothing prevents both desks editing the same firm doc simultaneously — the protocol relies on discipline (journal first, read state first) rather than locking.

---

## 6.6 Backup rotation (`99_OPS/BACKUP_POLICY.md`, D-015)

Four declared layers:

| Layer | Mechanism | Status observed |
|---|---|---|
| 1. OneDrive | Continuous corporate-OneDrive sync of the whole root — survives laptop loss; also the (implicit) cross-desk medium | ACTIVE (folder path is inside `OneDrive - Angel Broking Limited`) |
| 2. Git | Commit every session end; code + firm docs only; local-only, remote forbidden until HF-token scrub (D-003) | ACTIVE (187 commits) but **no off-machine copy except OneDrive's sync of `.git`** |
| 3. Data snapshots | Weekly manual zip of CRITICAL derived sets (earnings_pit, derived/, strategy outputs, angel_capture_2026) → `D:\` or `datasets/_snapshots/` | **NOT OBSERVED** — no `datasets\_snapshots\` folder exists and `D:\` shows no snapshot folder. This layer appears to be policy-on-paper only |
| 4. Credentials | `creds.json` + `angel_cfg.py` outside repo and outside OneDrive by design; Principal holds originals | ACTIVE as designed (but see plaintext finding) |

Restore drill: quarterly — open one parquet per critical family, verify row count vs DATA_CATALOG, log in journal. No evidence a drill has been logged yet (firm is ~2 weeks old in current form).

---

## 6.7 Scheduled-job inventory

**Windows Task Scheduler (survives Claude sessions):**

| Task | Schedule | What it does | Health |
|---|---|---|---|
| `AngelDailyOptionCapture` | Daily **15:45** primary (+20:00/23:00 backup triggers + StartWhenAvailable per EOD_ROUTINE) | Runs `AppData\Local\angel_capture\daily_capture.py` with the full Python path: captures 2 nearest expiries, ±10% strikes, 1-day full-life + 1-min front bars for all 210 F&O names → `datasets/angel_capture_2026/`. Idempotent via `last_success.txt` skip-marker. **This is the firm's only defense against Angel purging expired option contracts** — a missed expiry day is permanent data loss | Enabled; next run 12-Jul 15:45; **last run (11-Jul 23:41) returned error 0x8007052B** — and the task is `Logon Mode: Interactive only` + `No Start On Batteries`, i.e. it silently fails if the user isn't logged in or the laptop is on battery |

**Claude cron jobs (session-bound — die when the session ends):** re-armed by DESK-100 at every session start per CLAUDE.md Session Protocol §5, from the source of truth `01_COMMAND_CENTER/OPERATING_CALENDAR.md` §AUTOMATABLE-SLOT PROMPT SPEC. The seven standing jobs:

| Job | Cadence | Prompt runs |
|---|---|---|
| EOD daily | 17:00 daily | `/eod` — capture-log check, freshness ping, staleness → CURRENT_STATE |
| Paper-morning check | 09:00 market days (only if open positions) | `/paper reconcile --open-only` + `/events` over open legs |
| Paper reconcile | Fri 16:00 | `/paper reconcile` + `/tca-report` vs Angel quotes & COST_STANDARDS |
| Risk pack | Fri 17:00 | `/risk-report` (RP-29..36); breaches escalate to CIO |
| Macro refresh | Sun 18:00 | `/macro-calendar` → MACRO_CALENDAR.md |
| Pipeline health | Sun 19:00 | `/pipeline-health` → GREEN or repair list in `99_OPS/OPEN_ISSUES.md` |
| Skill discovery | Sun 19:30 | `/find-skills` weekly pass; top-3 proposals to Principal |
| Month-end pack + analytics | Last working day 08:00/09:00 | Board checkpoint assembly, then `/edge-decay`, `/attribution`, `/compliance-audit`, `/spend-report`, conditional `/stress-replay` |

Explicitly NOT automatable (human/decision required): the two meetings, Investor Letter, `/retro`, quarterly review/probe/resurrection, and anything paper→live (Principal only).

---

## 6.8 Memory system

Three tiers of persistent knowledge, from most to least durable:

1. **Git-tracked firm docs** — KNOWLEDGE_BASE, DECISIONS_LOG, KILLED_IDEAS, journals: the canonical record.
2. **Claude auto-memory** (`~\.claude\projects\<project-hash>\memory\`): `MEMORY.md` index + 11 topic files (firm structure, killed option-buying families, pre-open auction bug, FF decay, data-gap facts, Principal deliverable format, parallelism rules, HF token). Shared by both accounts; loaded automatically each conversation. Not in git, not in OneDrive — laptop-local only.
3. **CLAUDE.md constitution** (project + user-global) — the always-injected layer: session protocol, hard rules, 9 data landmines, environment facts, team roster, token discipline.

The design principle: anything an agent had to learn twice gets promoted upward (scratch → memory → persona/KB → CLAUDE.md) via the `/retro` skill.

---

## 6.9 SECURITY AUDIT — concrete risks, rated

Severity scale: CRITICAL (compromise now, high impact) / HIGH / MEDIUM / LOW. Ratings account for the mitigating fact that the Angel account is fund-less and data-only.

| # | Finding | Evidence | Severity | Why / recommended fix |
|---|---|---|---|---|
| 1 | **Complete Angel login secret set in plaintext** — API key + client ID + **PIN** + **TOTP seed** in `AppData\Local\angel_capture\creds.json`, and a second fully-hardcoded copy forgotten in an old session scratchpad (`...\d096bfac...\scratchpad\angel_cfg.py` + compiled `.pyc`) | Read directly 2026-07-12 | **HIGH** | The TOTP seed defeats 2FA entirely: anyone with filesystem access (malware, IT admin, laptop theft) gets full account login, not just API access. Fund-less account caps monetary damage, but the account exposes personal data and could place orders if ever funded. Fix: delete the stale scratchpad copy + `.pyc` NOW; move creds to Windows Credential Manager / DPAPI-encrypted blob; keep `creds.json` only as a break-glass copy held by the Principal offline. |
| 2 | **Angel API key + client code committed to git and synced to corporate OneDrive** — in `CLAUDE.md` (the constitution, read every session), `HANDOFF.md`, `other2\MANIFEST.md` | grep hits in 3 tracked files | **MEDIUM** | Key alone can't log in (needs PIN+TOTP) but it's a permanent secret in versioned history — un-removable without history rewrite, and visible to anyone with OneDrive/tenant access. Fix: rotate the API key at Angel, replace literals with "see creds.json" pointers, then treat old key as burned. |
| 3 | **HuggingFace token hardcoded in 8 git-tracked scripts + HANDOFF.md + a memory file** | `hf_zwgbMEO...` literals in `intraday_options_strategy/data/hf_*.py`, `05_DATA_OFFICE/scripts/hf_us_stocks_daily.py` | **MEDIUM** | Known issue (D-003 blocks any git push until scrubbed) — but the blocker approach means the token sits in history indefinitely and the firm can never get a remote backup until fixed. Fix: revoke + reissue the HF token, load from env var, THEN the remote-backup path opens. |
| 4 | **Everything lives on the employer's OneDrive tenant** — "OneDrive - Angel Broking Limited": all strategy IP, research, journals, and the CLAUDE.md-embedded API key sync to a cloud the employer (who is also the broker) administers | Folder path itself | **MEDIUM-HIGH** (confidentiality/IP, plus a personal-vs-employer compliance question) | Corporate admins/DLP can read the entire firm. This is simultaneously the only off-laptop backup, so it can't just be turned off. Fix: Principal decision needed — either accept explicitly (log in DECISIONS_LOG), or move the firm to a personal encrypted location with its own cloud backup. |
| 5 | **Single-laptop SPOF on the daily capture** — `AngelDailyOptionCapture` is `Interactive only` + `No Start On Batteries`; last run failed (0x8007052B); expiry-day data Angel purges is unrecoverable | schtasks query 2026-07-12 | **HIGH** (operational, not confidentiality) | Laptop asleep/logged-out/on-battery at 15:45 on an expiry day = permanent hole in the option dataset (this class of loss already forced the Apr-2024→Aug-2025 bhavcopy backfill). Fix: change task to "Run whether user is logged on or not" + allow on batteries; add the failed-run alarm to `/eod` (check Last Result, not just capture.log); longer-term, a ₹400/mo cloud VM or home box as second capture site. |
| 6 | **No remote git backup** — 187 commits of institutional memory exist only as a local `.git` (35 MB) whose sole replica is OneDrive's file-sync of the `.git` directory | `git remote -v` empty | **MEDIUM** | OneDrive syncing a live `.git` is a known corruption vector (partial syncs of packfiles/index during commits). If `.git` corrupts, decision history is gone even though working files survive. Fix: after finding #3's scrub, add a private remote (GitHub private repo); interim: weekly `git bundle create` to a path outside the repo/OneDrive. |
| 7 | **Backup layer 3 (weekly data snapshots) is not happening** — no `datasets\_snapshots\`, nothing on `D:\` | Filesystem check 2026-07-12 | **MEDIUM** | The critical *derived* datasets (earnings PIT, angel_capture_2026) have exactly one copy, on OneDrive with 28-GB-class exclusions — and `datasets/` is gitignored, so OneDrive is their ONLY copy. Fix: script the snapshot (zip + rotate 4 weekly) and wire it into the Sunday pipeline-health cron; log the quarterly restore drill. |
| 8 | **No credential rotation policy** — API key and TOTP seed are static since creation; no rotation cadence exists in any governance doc | Absence across 00_GOVERNANCE / 99_OPS | **LOW-MEDIUM** | Combined with findings 1–2 (key already in git history), rotation is the actual remediation, not just hygiene. Fix: add a quarterly rotation line to BACKUP_POLICY/OPERATING_CALENDAR; rotate immediately once (see #2). |
| 9 | **Permission system effectively disabled** — `.claude/settings.local.json` allows `Bash(*)`, `PowerShell(*)`, `WebFetch(*)`, `Agent(*)`, `Skill(*)` wildcards | Read 2026-07-12 | **MEDIUM** (agent-security) | Any prompt-injected instruction (e.g. hidden text in a scraped web page or downloaded PDF — the firm scrapes aggressively via `scrapling-official`) executes shell commands with zero human confirmation. On a machine holding plaintext broker creds, that is the realistic attack path. Fix: keep broad allows for the sandboxed scratchpad, but re-introduce prompts for writes outside the repo, `AppData` access, and network-touching commands; never `Bash(*)` on the desk that does bulk web scraping. |
| 10 | **Interactive-only task + `python` alias breakage = fragile automation surface** — every scheduled thing depends on one logged-in Windows session and one hardcoded interpreter path | CLAUDE.md §ENVIRONMENT + task config | **LOW** | A Python reinstall/update breaks every task silently (Last Result nonzero, nobody looks). Fix: `/pipeline-health` should assert the interpreter path exists and the task's Last Result == 0. |

**Top-3 actions if only three are done:** (1) delete the stale scratchpad `angel_cfg.py`/`.pyc` and DPAPI-protect `creds.json`; (2) rotate both the Angel API key and the HF token, scrub literals, then stand up a private git remote; (3) fix `AngelDailyOptionCapture` to run non-interactive/on-battery and alert on nonzero Last Result.

---

### Improvement opportunities

Prioritized for this section's scope (platform, tooling, security):

1. **P0 — Secrets remediation sprint (findings 1, 2, 3, 8).** One session of work: delete stale scratchpad creds, DPAPI-encrypt or Credential-Manager-store `creds.json`, rotate Angel API key + HF token, replace all literals in tracked files with pointers, add a `detect-secrets`-style pre-commit grep (the `.gitignore` patterns catch *files* named `*creds*` but not literals pasted into any .md/.py). Log a quarterly rotation cadence in OPERATING_CALENDAR.
2. **P0 — Harden the capture task (finding 5).** Switch to "run whether user is logged on or not", allow battery, and extend `/eod` + `/pipeline-health` to check `schtasks` Last Result — today a silently failing task looks healthy as long as an *older* capture.log line exists. The 11-Jul 23:41 failure (0x8007052B) proves this monitoring gap is live right now.
3. **P1 — Off-laptop git remote (finding 6).** Blocked only by the HF-token scrub (P0 above). Until then, add a weekly `git bundle` to a non-OneDrive path as a stopgap — one line in the Sunday pipeline-health cron.
4. **P1 — Implement backup layer 3 (finding 7).** Write `99_OPS/scripts/weekly_snapshot.py` (zip critical derived sets, rotate 4), schedule it, and actually run the quarterly restore drill the policy already mandates.
5. **P1 — Principal ruling on the OneDrive tenant question (finding 4).** This is a decision, not an engineering task: the employer-broker can read the whole firm. Either accept in DECISIONS_LOG or migrate.
6. **P2 — Tighten agent permissions (finding 9).** Replace `Bash(*)`/`PowerShell(*)` with a curated allowlist (the `fewer-permission-prompts` skill exists for exactly this); at minimum on whichever desk runs web scraping.
7. **P2 — Skill-library hygiene.** 79 skills but uneven depth: `lookahead-audit` (a mandatory gate) is a one-line stub while design skills ship full script suites; ~10 design/UI skills are near-duplicates (design, design-system, banner-design, brand, ui-styling, ui-ux-pro-max, impeccable, slides, 21st-cli-use) that bloat the skill index every session. A `/prompt-improve` pass on the thin critical skills + consolidation of the design cluster would cut per-session overhead and raise gate quality.
8. **P2 — Cross-desk write locking.** The `.claude/scheduled_tasks.lock` pattern works for crons; extend the idea with an advisory lock (or "journal-first" hard rule check in `/desk-open`) for CURRENT_STATE.md, the one file both desks rewrite — today simultaneous edits would silently last-writer-win through OneDrive.
9. **P3 — Back up the auto-memory tier.** The 12 memory files (`~\.claude\projects\...\memory\`) are laptop-local only — outside git AND OneDrive. A monthly copy into `00_GOVERNANCE/memory_mirror/` (secrets excluded — note `reference_hf_token.md` must NOT be mirrored) would make the third knowledge tier as durable as the other two.
10. **P3 — Task Scheduler inventory as code.** `AngelDailyOptionCapture` exists only in the Windows task store; export its XML definition into `99_OPS/` so a laptop rebuild can restore it exactly (schedule, triggers, idempotency contract).
