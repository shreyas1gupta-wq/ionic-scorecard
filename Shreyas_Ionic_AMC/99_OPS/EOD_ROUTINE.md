# EOD ROUTINE — DESK-100 owns (daily, mostly automated)

## Automated (Windows Task Scheduler — verify, don't re-run)
- **AngelDailyOptionCapture** — 15:45 primary + 20:00/23:00 backups + StartWhenAvailable; idempotent (`last_success.txt` skip-marker). Captures 2 nearest expiries, ±10% strikes, 1-day full-life + 1-min front, for all 210 F&O names → `datasets/angel_capture_2026/`. Health check: `C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\capture.log` (a post-close line dated today = healthy). Expiry-day data is captured BEFORE Angel purges the contract — this task is the firm's only defense against that purge.

## Manual/session checklist (any desk, ~5 min)
1. Capture log healthy? (above)
2. Freshness ping (Data Officer): max(trading_day) in angel_capture day/ = today? earnings forthcoming_results.csv < 7 days old? If stale → flag CURRENT_STATE.
3. Pending queue: 23 Angel OHLCV stragglers (list in RESUME_TOMORROW §Angel Daily Bulk) — retry after rate-limit cooldown, ≥1.2s/req.
4. If an expiry passed this week: confirm the expiring contracts' final day exists in capture (else bhavcopy re-pull via `05_DATA_OFFICE/scripts/bhavcopy_backfill.py` date-window edit).
5. Journal anything notable; update CURRENT_STATE if state changed.

## Weekly add-ons
- Paper-ledger reconcile (Tara) · pipeline triage (Vikram) · scrip-master snapshot check (210-name universe drift: new F&O entries/exits → Data Officer updates catalog + backfills newcomers).
