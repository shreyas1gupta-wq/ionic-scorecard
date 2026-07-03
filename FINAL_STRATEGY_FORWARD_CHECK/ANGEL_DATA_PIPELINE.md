# Angel One — Recurring Data-Capture Pipeline

**Purpose:** never miss recent option data again. Angel *purges expired contracts from its
instrument master* right after expiry (confirmed: the current master only lists Jul/Aug/Sep
2026 — June 2026 is already gone and its candles are unfetchable). So we must snapshot the
live contracts **daily, before they expire.**

## What is running (unattended, no per-run permission)

| Item | Value |
|---|---|
| Windows Task | `AngelDailyOptionCapture` (State: Ready) |
| Schedule | **Daily 15:45 IST primary + 20:00 + 23:00 backups** + `StartWhenAvailable` (fires a missed slot when the PC is next on) |
| Script | `C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\daily_capture.py` |
| Credentials | `...\angel_capture\creds.json` (kept OUT of OneDrive; data-only disposable account) |
| Log | `...\angel_capture\capture.log` |
| Output | `intraday_options_strategy/datasets/angel_capture_2026/{day,minute}/{sym}/{expiry}.parquet` (OneDrive-synced, plugs into backtests) |
| Runtime | ~45–90 min/run (~8k API calls, rate-limited) |

## What it captures each run

- **Universe:** the 88 F&O stocks in the project dataset.
- **Contracts:** the **2 nearest future expiries**, strikes within **±10% of spot**, CE + PE.
- **1-DAY candles:** full contract life (re-fetched & overwritten each run → always complete).
- **1-MIN candles:** front expiry only, last 6 days, **merged & de-duped** into the running
  series → the full minute history accumulates day by day from now on.

## Why 15:45 daily solves the expiry-purge problem

Market closes 15:30; the run at 15:45 grabs that day's data. On an **expiry day**, the expiring
contract is still in the master at 15:45 (purge happens after), so its **final-day data is
captured before it disappears.** No separate expiry-day job needed — the daily run covers it.

### Laptop-off backup logic (why 3 times + self-healing)
- **3 daily triggers (15:45 / 20:00 / 23:00):** if the PC is off at 15:45 but on later that
  evening, a backup slot captures the same (post-close, unchanged) data.
- **`StartWhenAvailable`:** if the PC is off for all three, Windows fires the missed slot the
  moment the machine next comes on.
- **Idempotent skip marker (`last_success.txt`):** the script records the date of the last
  *post-close* successful run. So the backup slots are **instant no-ops** once the day is done —
  only the first successful post-close run each day does the ~1-hour work.
- **Self-healing gaps:** 1-day candles are re-fetched for the last 80 days every run and
  overwritten, so a missed day is automatically backfilled the next time the PC is on (as long
  as it's before that contract expires). A pre-close catch-up run does *not* mark the day done,
  so the post-close run still refreshes the final candle.
- **Residual risk:** if the laptop is off for the *entire* expiry day and evening, that one
  expiring contract's final bar can still be lost (Angel purges it before the PC returns). Only
  a HuggingFace backfill can recover that specific case.

## What this pipeline does NOT fix (needs HuggingFace backfill)

- **17-month historical gap: Apr-2024 → Aug-2025** (never downloaded).
- **June-2026 cycle** (already expired & purged from Angel — unfetchable here).

Both are historical → refill from HuggingFace (token on file, `hf_chunked.py`, sequential
through the corporate proxy). This pipeline only guarantees **forward** completeness from today.

## Manage the task

```powershell
# run it now (manual)
Start-ScheduledTask -TaskName "AngelDailyOptionCapture"
# check last run result / next run time
Get-ScheduledTaskInfo -TaskName "AngelDailyOptionCapture"
# change the time to e.g. 16:00
Set-ScheduledTask -TaskName "AngelDailyOptionCapture" -Trigger (New-ScheduledTaskTrigger -Daily -At "16:00")
# pause / resume / remove
Disable-ScheduledTask -TaskName "AngelDailyOptionCapture"
Enable-ScheduledTask  -TaskName "AngelDailyOptionCapture"
Unregister-ScheduledTask -TaskName "AngelDailyOptionCapture" -Confirm:$false
```

## Caveats

- Runs only when the PC is **on and the user is logged in**; `StartWhenAvailable` re-runs a
  missed slot when the machine next wakes (so a day off won't create a permanent hole, as long
  as it's before the contract expires).
- Single-stock options are **illiquid far from expiry** — expect sparse bars early in a cycle
  that fill in as expiry approaches (this is a market reality, not a capture bug).
- 1-min history only accumulates **from today forward** (Angel's intraday history depth is short);
  deep historical minute data still comes from HuggingFace.
- If TOTP/login ever fails, check the log; the disposable account's TOTP secret is in creds.json.
