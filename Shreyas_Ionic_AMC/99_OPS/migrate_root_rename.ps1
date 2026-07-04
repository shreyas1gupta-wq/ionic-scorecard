<#
.SYNOPSIS
  STAGED, NOT-YET-RUN root rename: "NIFTY 500" -> "Shreyas_project_amc".
  Principal order 2026-07-05 (see other2/MANIFEST.md + 99_OPS/RENAME_RUNBOOK.md).

.DESCRIPTION
  Full sequence: verify no live process holds the old tree -> export+unregister the 2 in-repo
  scheduled tasks -> Rename-Item the root -> targeted absolute-path rewrites driven by
  HARDCODED_PATH_MANIFEST.csv -> re-register the 2 scheduled tasks with the new path -> verify
  -> print the manual next-steps (there are things this script cannot do: patch a file outside
  the repo, or migrate Claude's own session/project state).

  THIS SCRIPT DOES NOT RUN ITSELF. Default invocation (no -Execute) is a 100% read-only dry run
  that only prints what it WOULD do. Even with -Execute, it stops and requires a typed
  confirmation phrase before touching anything. This is deliberate: per CLAUDE.md's approval
  gates, a root rename affecting live scheduled tasks and two Claude accounts' session state is
  a Principal-level, deliberate-session decision, never something either desk fires accidentally.

.NOTES
  Owner: Manoj Pillai (Ops), staged 2026-07-05, DESK-100. Run from OUTSIDE the target tree
  (e.g. cwd = "...Desktop\Backup"), in a brand-new PowerShell window with NO Claude session,
  NO Explorer window, NO editor open inside the old tree. Read RENAME_RUNBOOK.md's "WHEN SAFE"
  checklist in full before ever passing -Execute.

.PARAMETER OldRoot
  Current repo root. Defaults to the path this script was staged against.

.PARAMETER NewName
  New leaf folder name. Defaults to "Shreyas_project_amc" per the Principal's order. Change here
  if the Principal picks a different final name before executing.

.PARAMETER ManifestCsv
  Path (relative to OldRoot/NewRoot) to the hardcoded-path manifest this script rewrites from.

.PARAMETER Execute
  Without this switch: dry-run only, changes nothing. With it: after a typed confirmation,
  performs the real rename + rewrites + task re-registration.

.EXAMPLE
  # Safe to run any time -- read-only, reports what would happen:
  .\migrate_root_rename.ps1

.EXAMPLE
  # The real thing -- only after RENAME_RUNBOOK.md's WHEN SAFE checklist is fully green:
  .\migrate_root_rename.ps1 -Execute
#>
[CmdletBinding()]
param(
    [string]$OldRoot     = "c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500",
    [string]$NewName     = "Shreyas_project_amc",
    [string]$ManifestCsv = "Shreyas_Ionic_AMC\99_OPS\HARDCODED_PATH_MANIFEST.csv",
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$ParentDir  = Split-Path -Parent $OldRoot
$NewRoot    = Join-Path $ParentDir $NewName
$StampedLog = Join-Path $ParentDir ("migrate_root_rename_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")

function Write-Log {
    param([string]$Msg)
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Msg
    Write-Output $line
    Add-Content -Path $StampedLog -Value $line
}

Write-Log "=== migrate_root_rename.ps1 starting (Execute=$($Execute.IsPresent)) ==="
Write-Log "OldRoot = $OldRoot"
Write-Log "NewRoot = $NewRoot"
Write-Log "Log file: $StampedLog"

# ---------- PRE-FLIGHT 1: refuse to run from inside the target tree ----------
if ($PWD.Path.ToLower().StartsWith($OldRoot.ToLower())) {
    Write-Log "ABORT: current directory is inside $OldRoot. cd to $ParentDir (or anywhere outside the tree) and re-run."
    exit 1
}

# ---------- PRE-FLIGHT 2: sanity on source/destination ----------
if (-not (Test-Path -LiteralPath $OldRoot)) {
    Write-Log "ABORT: OldRoot not found. Already renamed? Nothing to do."
    exit 1
}
if (Test-Path -LiteralPath $NewRoot) {
    Write-Log "ABORT: NewRoot already exists ($NewRoot). Refusing to overwrite/merge. Resolve manually first."
    exit 1
}

# ---------- PRE-FLIGHT 3: any live process still referencing the old tree? ----------
Write-Log "Checking for live processes referencing the old root..."
$suspects = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine -like "*NIFTY 500*")
}
if ($suspects) {
    Write-Log "ABORT: $($suspects.Count) process(es) still reference the old tree:"
    foreach ($p in $suspects) { Write-Log ("  PID {0}: {1}" -f $p.ProcessId, $p.CommandLine) }
    Write-Log "Known offender at staging time: intraday_options_strategy/data/hf_stocks_opts.py (running since 2026-06-30)."
    Write-Log "Wait for it to finish, then re-run this script."
    exit 1
}
Write-Log "No live process references the old tree by command line. OK."
Write-Log "NOTE: this check is CommandLine-based only. It cannot see open file handles held by"
Write-Log "      OneDrive, an editor, or a process that opened files without the path in argv."

# ---------- PRE-FLIGHT 4: reminders this script cannot verify programmatically ----------
Write-Log "MANUAL CHECKS -- confirm all of these before passing -Execute (see RENAME_RUNBOOK.md):"
Write-Log "  1. OneDrive sync is PAUSED or fully idle/green (not mid-upload)."
Write-Log "  2. No other Claude Code / VS Code / Explorer window has this tree open as cwd."
Write-Log "  3. Not inside a cron firing window (15:45/20:00/23:00 IST Angel capture; OPERATING_CALENDAR.md Sun/Mon/Fri jobs)."
Write-Log "  4. A fresh ShreyasIonicAMC_WeeklyBackup backup exists under C:\Users\Shreyas.1Gupta\ShreyasIonicAMC_BACKUP."

if (-not $Execute) {
    Write-Log "DRY RUN complete -- no -Execute passed, nothing was changed."
    Write-Log "Re-run with -Execute once the WHEN SAFE checklist in RENAME_RUNBOOK.md is fully green."
    exit 0
}

Write-Log "Execute mode requested. Final human confirmation gate."
$phrase = Read-Host "Type EXACTLY 'RENAME THE FIRM ROOT' to proceed"
if ($phrase -ne "RENAME THE FIRM ROOT") {
    Write-Log "ABORT: confirmation phrase did not match. No changes made."
    exit 1
}

# ---------- STEP 1: export + unregister the 2 in-repo scheduled tasks ----------
$tasksToMigrate = @("ShreyasIonicAMC_IndexClose", "ShreyasIonicAMC_WeeklyBackup")
$taskBackupDir  = Join-Path $ParentDir ("scheduled_task_backup_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $taskBackupDir -Force | Out-Null
Write-Log "Scheduled-task XML backups going to: $taskBackupDir"

foreach ($t in $tasksToMigrate) {
    try {
        Get-ScheduledTask -TaskName $t -ErrorAction Stop | Out-Null
        Export-ScheduledTask -TaskName $t | Out-File (Join-Path $taskBackupDir "$t.xml") -Encoding utf8
        Write-Log "Exported task $t"
        Unregister-ScheduledTask -TaskName $t -Confirm:$false
        Write-Log "Unregistered task $t"
    } catch {
        Write-Log "WARN: could not export/unregister $t : $($_.Exception.Message)"
    }
}
# AngelDailyOptionCapture is deliberately untouched here: its Action target
# (AppData\Local\angel_capture\daily_capture.py) lives OUTSIDE the repo, so the task
# registration needs no change. That script's INTERNAL hardcoded root (line ~23) is a
# separate landmine -- see the printed reminder at the end of this script and manifest
# row "[OUTSIDE REPO] ...daily_capture.py".

# ---------- STEP 2: the rename itself ----------
try {
    Rename-Item -LiteralPath $OldRoot -NewName $NewName -ErrorAction Stop
    Write-Log "RENAMED: $OldRoot -> $NewRoot"
} catch {
    Write-Log "FATAL: rename failed: $($_.Exception.Message)"
    Write-Log "Attempting best-effort restore of the 2 scheduled tasks from backup before exiting."
    foreach ($t in $tasksToMigrate) {
        $xml = Join-Path $taskBackupDir "$t.xml"
        if (Test-Path $xml) { schtasks /Create /TN $t /XML $xml /F | Out-Null }
    }
    exit 1
}

# ---------- STEP 3: targeted absolute-path rewrites from the manifest ----------
$manifestPath = Join-Path $NewRoot $ManifestCsv
if (-not (Test-Path $manifestPath)) {
    Write-Log "WARN: manifest CSV not found at $manifestPath -- skipping automated rewrites."
    Write-Log "      Do them by hand from RENAME_RUNBOOK.md / HARDCODED_PATH_MANIFEST.csv."
} else {
    $rows = Import-Csv -LiteralPath $manifestPath
    $skipCategories = @("FALSE_POSITIVE", "ALREADY_SAFE", "LINEAGE_DO_NOT_TOUCH", "LEGEND",
                         "SCHEDULED_TASK", "OUTSIDE_REPO_LANDMINE", "OUT_OF_SCOPE_SUMMARY")
    $rewritten = 0
    foreach ($row in $rows) {
        if ($skipCategories -contains $row.category) { continue }
        $relPath = $row.relative_path
        if ($relPath -like "[[]*") { continue }   # any bracketed pseudo-path marker, skip defensively
        $target = Join-Path $NewRoot $relPath
        if (-not (Test-Path -LiteralPath $target)) {
            Write-Log "WARN: manifest row references a missing file: $target (skipped)"
            continue
        }
        $content = Get-Content -LiteralPath $target -Raw
        if ($content -match [regex]::Escape($OldRoot)) {
            $count = ([regex]::Matches($content, [regex]::Escape($OldRoot))).Count
            $newContent = $content -replace [regex]::Escape($OldRoot), $NewRoot
            Set-Content -LiteralPath $target -Value $newContent -NoNewline
            Write-Log "Rewrote $relPath ($count occurrence(s))"
            $rewritten++
        } else {
            Write-Log "INFO: $relPath had no literal OLD_ROOT match at rewrite time (already clean?)"
        }
    }
    Write-Log "Manifest-driven rewrite pass done: $rewritten file(s) touched."
}

Write-Log "REMINDER: results/**, intraday_options_strategy/**, swing_momentum/** were NOT swept"
Write-Log "          (out of manifest scope -- 73 files at staging time). See RENAME_RUNBOOK.md Appendix B."
Write-Log "REMINDER: C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\daily_capture.py hardcodes"
Write-Log "          the OLD root at ~line 23 and lives OUTSIDE this repo -- hand-patch it NOW."

# ---------- STEP 4: re-register the 2 scheduled tasks with the new path ----------
foreach ($t in $tasksToMigrate) {
    $xmlPath = Join-Path $taskBackupDir "$t.xml"
    if (-not (Test-Path $xmlPath)) {
        Write-Log "WARN: no exported XML for $t -- re-register manually."
        continue
    }
    $xmlContent    = Get-Content -LiteralPath $xmlPath -Raw
    $xmlContentNew = $xmlContent -replace [regex]::Escape($OldRoot), $NewRoot
    $xmlPathNew    = Join-Path $taskBackupDir "$t.new.xml"
    Set-Content -LiteralPath $xmlPathNew -Value $xmlContentNew -Encoding Unicode
    try {
        schtasks /Create /TN $t /XML $xmlPathNew /F | Out-Null
        Write-Log "Re-registered task $t with the new path"
    } catch {
        Write-Log "WARN: re-registration of $t failed: $($_.Exception.Message). Restore manually from $xmlPathNew"
    }
}

# ---------- STEP 5: verification ----------
Write-Log "=== VERIFICATION ==="
Write-Log ("NewRoot exists: {0}" -f (Test-Path -LiteralPath $NewRoot))
Write-Log ("OldRoot gone:   {0}" -f (-not (Test-Path -LiteralPath $OldRoot)))
foreach ($t in $tasksToMigrate) {
    try {
        $chk = Get-ScheduledTask -TaskName $t -ErrorAction Stop
        $act = $chk.Actions | Select-Object -First 1
        Write-Log ("Task {0}: {1} {2}" -f $t, $act.Execute, $act.Arguments)
    } catch {
        Write-Log ("WARN: task {0} not found after re-registration attempt" -f $t)
    }
}

Write-Log "=== NEXT STEPS (manual -- cannot be scripted) ==="
Write-Log "1. Hand-patch C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\daily_capture.py (the PROJ= line) to the new root."
Write-Log "2. Restart ALL Claude Code sessions (DESK-20 desktop app AND DESK-100 VS Code). The old"
Write-Log "   .claude project slug (path-derived) will NOT auto-follow -- a session opened at the new"
Write-Log "   path starts a brand-new, empty project slug. Manually carry forward memory/MEMORY.md"
Write-Log "   content, or at minimum note the discontinuity in the new session's first message."
Write-Log "3. Re-open any editor/workspace pointing at the new folder name."
Write-Log "4. Re-arm the firm cadence crons per CLAUDE.md's DESK-100 session-start protocol (#4)."
Write-Log "5. Run the pipeline-health / desk-open skill once to confirm everything resolves cleanly."
Write-Log "6. Once intraday_options_strategy's live process has been finished for a while, run a"
Write-Log "   supplementary sweep of results/**, intraday_options_strategy/**, swing_momentum/**"
Write-Log "   (RENAME_RUNBOOK.md Appendix B) -- triage file-by-file, do not blind find-replace results/**."
Write-Log "7. git add -A; git commit the path-rewrite diffs as their own commit (easy to review/revert)."
Write-Log "=== migrate_root_rename.ps1 finished. Full log: $StampedLog ==="
