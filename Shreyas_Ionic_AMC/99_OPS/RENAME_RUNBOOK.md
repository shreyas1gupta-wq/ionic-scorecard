# ROOT RENAME RUNBOOK — "NIFTY 500" → "Shreyas_project_amc"

**STAGED, NOT EXECUTED.** Principal order 2026-07-05: "...also if possible rename nifty 500
folder as Shreyas_project_amc." This is the dangerous 10% of that order, deliberately not run in
the same session that staged it (live process + hardcoded paths + git + OneDrive + two Claude
accounts' session state all intersect here — see the order's own reasoning). The Principal, or a
dedicated future session with this checklist fully green, runs `migrate_root_rename.ps1 -Execute`.

Companion files: `HARDCODED_PATH_MANIFEST.csv` (34 rows, what the script rewrites and what it
deliberately leaves alone) and `migrate_root_rename.ps1` (the script itself — dry-run by default,
requires `-Execute` plus a typed confirmation phrase to do anything real).

## WHEN SAFE (every box must be true)

1. **No live process inside the tree.** At staging time (2026-07-05): two python.exe PIDs
   (35872, 26528) running `intraday_options_strategy/data/hf_stocks_opts.py` since 2026-06-30
   18:00. The script checks this automatically (aborts if any process `CommandLine` contains
   "NIFTY 500") — but confirm manually too:
   `Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like "*NIFTY 500*"}`.
2. **cwd is outside the tree.** Run from `...Desktop\Backup\`, never from inside `NIFTY 500\`.
   Windows cannot rename a directory that is a process's current directory; the script self-checks
   and aborts otherwise.
3. **No other session/editor has the folder open.** Close both Claude accounts' sessions
   (DESK-20 desktop app, DESK-100 VS Code), any Explorer windows, any editor windows pointing
   inside the tree.
4. **OneDrive sync is idle or paused.** Pause via the OneDrive tray icon before running. A rename
   mid-sync can produce conflict-duplicate files or a stuck sync state. Resume after and wait for
   a full green check before declaring the migration done.
5. **Not inside a cron firing window.** Avoid 15:45/20:00/23:00 IST (AngelDailyOptionCapture) and
   the Sun/Mon/Fri automated windows in `OPERATING_CALENDAR.md`. Best time: outside market hours,
   outside any scheduled job's trigger time, ideally right after a fresh weekly backup.
6. **A recent backup exists.** Check `C:\Users\Shreyas.1Gupta\ShreyasIonicAMC_BACKUP\` for a
   backup newer than today's session start. If not, run
   `python Shreyas_Ionic_AMC\99_OPS\backup_firm.py` manually first (backs up git history + firm
   tree + critical data, independent of this rename).

## WHAT BREAKS (and who fixes it)

| Break | Cause | Fixed by |
|---|---|---|
| `ShreyasIonicAMC_IndexClose` scheduled task fails silently at next trigger | Task Action Arguments hardcode the old absolute path to `nse_indices_close_pull.py` | `migrate_root_rename.ps1` step 4 (export → unregister → re-register with new path) |
| `ShreyasIonicAMC_WeeklyBackup` scheduled task fails silently at next trigger | Same — Action Arguments hardcode the old path to `backup_firm.py` | Same script step |
| `AngelDailyOptionCapture` starts throwing path errors | `daily_capture.py` (in `AppData\Local\angel_capture`, OUTSIDE the repo, untouched by this task) hardcodes `PROJ = Path(r"...NIFTY 500")` at line 23 | **NOT scripted.** This file lives outside git, outside the manifest's authorized scope. Hand-patch this ONE line right after the rename — it is the single easiest thing to forget, since nobody greps AppData by habit. |
| ~15 scripts under `Shreyas_Ionic_AMC/` (05_DATA_OFFICE, 04_RND_LAB) + root `build_final_docs.py` raise `FileNotFoundError` on next run | Hardcoded `ROOT`/`PROJ` literals | `migrate_root_rename.ps1` step 3, driven by `HARDCODED_PATH_MANIFEST.csv` |
| `HANDOFF.md` header/tree-diagram shows the wrong root | Doc references | Same manifest-driven rewrite (`DOC_REFERENCE` rows) |
| **73 files** under top-level `results/` (36), `intraday_options_strategy/` (34), `swing_momentum/` (3) still say "NIFTY 500" | Out of this manifest's authorized scope (Principal's scope was "Shreyas_Ionic_AMC + .claude + root scripts") | **NOT scripted, NOT swept.** See Appendix B — most of `results/**` are historical lineage records that SHOULD stay as-is (rewriting them would falsify provenance); the 37 under `intraday_options_strategy/`+`swing_momentum/` are real code that will break if ever re-run, but that's also the live/legacy tree nobody may touch right now anyway. |
| Claude session / project continuity breaks | The repo-local `.claude/` folder has zero hardcoded paths (verified clean), but the GLOBAL `~/.claude/projects/<path-derived-slug>/` folder — which holds `memory/MEMORY.md`, the shared cross-session brain for both desks — is keyed off the OLD path | **Not scriptable.** After rename: open a fresh session in the new folder, manually carry forward the `MEMORY.md` index content (it's short) into the new slug's memory, or at minimum leave a pointer note "history lives at the old slug path." Both DESK-20 and DESK-100 need to do this once each. |
| Desktop/Explorer shortcuts, Start-Menu pins, any other Task Scheduler jobs not enumerated here | Not inventoried by this task (scope was scripts + the 3 tasks discovered by name-pattern search) | Manual `Get-ScheduledTask` full sweep + shortcut check before declaring done (Appendix C) |
| OneDrive re-index/re-upload of the whole tree under the new name | Rename is a local metadata op, but OneDrive still reconciles cloud-side | Just wait for the green check; don't run this right before needing same-day confirmation |

## HOW TO VERIFY AFTER

1. `Test-Path "...\Desktop\Backup\Shreyas_project_amc"` = True; old path = False.
2. `git -C "...\Shreyas_project_amc" status` — clean except the expected path-rewrite diffs;
   `git diff` review before committing.
3. Spot-check 2-3 rewritten scripts (e.g. run `nse_indices_close_pull.py` once manually, or
   `python -c "import ast; ast.parse(open('Shreyas_Ionic_AMC/99_OPS/backup_firm.py').read())"`)
   to confirm they parse/resolve paths correctly.
4. `Get-ScheduledTask ShreyasIonicAMC_IndexClose, ShreyasIonicAMC_WeeklyBackup | Select -Expand
   Actions` — confirm Arguments show the NEW path. `Start-ScheduledTask` each once and check for
   a clean run.
5. Confirm `AngelDailyOptionCapture` runs clean at its next 15:45/20:00/23:00 IST window — this is
   the real test of the hand-patch to `daily_capture.py`.
6. OneDrive tray icon shows a full green check for the new folder.
7. New Claude session opens cleanly in the new path; `CURRENT_STATE.md`/`SESSION_JOURNAL.md` read
   fine; the memory-continuity caveat above has been actioned.
8. `git commit` the rewrite diffs as their own commit
   (`Root rename NIFTY 500 -> Shreyas_project_amc: path rewrites`).

## ROLLBACK

- If the rename step itself fails: the script auto-restores the 2 scheduled tasks from its XML
  export before exiting; the folder never moved, so there's nothing else to undo.
- If the rename succeeded but something downstream breaks: `Rename-Item` the folder back to
  `NIFTY 500`, restore the 2 scheduled tasks from the timestamped `scheduled_task_backup_*` folder
  (`schtasks /Create /TN <name> /XML <backup>.xml /F`), and `git revert` the path-rewrite commit if
  it was already made.
- The weekly backup (`ShreyasIonicAMC_BACKUP\<timestamp>\git_full.bundle` + `firm_tree.zip`) is the
  nuclear-option restore path if anything else goes wrong.

## Appendix A — where things live

- Path manifest (drives script step 3): `Shreyas_Ionic_AMC/99_OPS/HARDCODED_PATH_MANIFEST.csv`
- The script: `Shreyas_Ionic_AMC/99_OPS/migrate_root_rename.ps1`
- This runbook: `Shreyas_Ionic_AMC/99_OPS/RENAME_RUNBOOK.md`

## Appendix B — out-of-scope exposure (sized, not fixed)

Grepped read-only (nothing modified) for the literal "NIFTY 500" beyond the authorized manifest
scope:

- `results/**` (top-level — NOT `Shreyas_Ionic_AMC/04_RND_LAB/results/`, which IS in the
  manifest): 36 files, overwhelmingly `config.json`/build-script pairs from the 2026-07-04
  research sprint. Same rule as the in-scope lineage rows: mostly leave as historical record;
  rewrite only the handful of actively-reusable build scripts (`build_*.py`, `replicate_*.py`) if
  they'll actually be re-run post-rename.
- `intraday_options_strategy/**`: 34 files. This is the LIVE-process-owned tree — cannot be
  touched at all right now, and per the original order's Hard Constraint #1 should be reassessed
  ("move AFTER process completes") as its own, separate exercise. Do not sweep until
  `hf_stocks_opts.py` has been confirmed complete for a while.
- `swing_momentum/**`: 3 files (`combo_and_report.py`, `earnings_strategies.py`,
  `multi_backtest.py`).

Recommendation: after the live process exits, and before anyone next runs a script from these
three trees, repeat the same grep scoped to them and triage file-by-file. Do not blind
find-replace `results/**` — lineage accuracy matters more than freshness there.

## Appendix C — scheduled tasks inventory (as found 2026-07-05)

| Task | Action target | In-repo? | Handled by script? |
|---|---|---|---|
| AngelDailyOptionCapture | `C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\daily_capture.py` | No (outside repo) | No — task registration needs no change, but the SCRIPT hardcodes the old root internally (hand-patch, see "what breaks") |
| ShreyasIonicAMC_IndexClose | `Shreyas_Ionic_AMC\05_DATA_OFFICE\scripts\nse_indices_close_pull.py` | Yes | Yes |
| ShreyasIonicAMC_WeeklyBackup | `Shreyas_Ionic_AMC\99_OPS\backup_firm.py` | Yes | Yes |

This is the full `Get-ScheduledTask` result set matching `*Angel*`/`*ShreyasIonic*`/`*Nifty*` at
staging time. Run a broader, unfiltered `Get-ScheduledTask` sweep before declaring the rename
complete, in case something else was registered without those keywords in its name.

---
Staged by: Manoj Pillai (Ops), DESK-100, 2026-07-05. Not executed. Executing this script is a
Principal-level or deliberate-next-session decision, not something either desk does automatically
— per CLAUDE.md's approval gates and the order's own explicit instruction not to run it now.
