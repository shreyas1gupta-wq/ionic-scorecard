# MG03 — Resume-Safe Daily EOD Ingestion Pipeline (Sonnet answer)

## 0. Shape of the answer
A ledger-driven state machine where every unit of work is `(trade_date, file)`, every filesystem
mutation is write-temp-then-atomic-rename, every state transition is a committed database row, and
the ledger itself is portable (survives to a new machine) and durable (survives OneDrive-style sync
of a shared folder). Nothing is inferred from "what files exist in a directory" — the ledger is the
only source of truth for what has and hasn't happened.

## 1. On-disk layout
```
05_DATA_OFFICE/pipelines/eod_ingest/
  ledger_events.jsonl        <- TRUE source of truth, append-only, git/OneDrive-safe
  ledger.db                  <- SQLite (WAL mode), a REBUILDABLE cache/index over the events log
  raw/incoming/<date>.part   <- in-progress downloads (never trusted, never read by ingestion)
  raw/verified/<date>/<file> <- passed every check, checksummed, kept forever (re-ingestion source)
  quarantine/<date>/<file>+reason.txt  <- failed a check; kept for forensics, never deleted
  locks/<date>.lock          <- {pid, hostname, heartbeat_ts}
  config/holiday_calendar.csv
  config/schema_v{n}.json    <- versioned expected columns/dtypes, for drift detection
  logs/ingest_YYYYMMDD.log
  ALERTS.md                  <- ONLY actionable items land here
  scripts/rebuild_ledger_db.py   <- replays ledger_events.jsonl -> ledger.db (new-machine bootstrap)
  scripts/run_ingest.py          <- the driver, safe to run any number of times, any machine
```

Why two ledgers: SQLite gives atomic, indexed, concurrent-safe status queries during a run, but a
binary DB file syncs badly under OneDrive/shared-folder concurrent writers (partial-write corruption
risk). The JSONL is append-only, line-per-event, diffable, mergeable, and is what actually gets
trusted; `ledger.db` is disposable and always reconstructable from it.

## 2. Ledger event schema (one JSON object per line in ledger_events.jsonl)
```json
{"ts":"2026-07-12T20:00:03+05:30","trade_date":"2026-07-11","event":"DOWNLOAD_START",
 "host":"DESK100-VSCODE","pid":12345,"attempt":1}
{"ts":"...","trade_date":"2026-07-11","event":"DOWNLOAD_OK","bytes":842113,"sha256":"..."}
{"ts":"...","trade_date":"2026-07-11","event":"VERIFY_OK","checks_passed":["size","parse","schema","rowcount","anchor_values"]}
{"ts":"...","trade_date":"2026-07-11","event":"INGEST_OK","rows":1847,"partition":"date=2026-07-11"}
```
Every event is idempotent to replay (keyed by trade_date+event+ts); `rebuild_ledger_db.py` simply
folds these into a `(trade_date -> latest terminal status + full history)` table. `ledger.db` table
`ingest_state`: `trade_date PK, status, attempts, last_attempt_ts, last_error, sha256, byte_size,
verified_ts, ingested_ts, row_count, host, lock_owner`.

## 3. State machine (states are the only vocabulary the pipeline reasons in)
```
PENDING -> DOWNLOADING -> DOWNLOADED -> VERIFIED -> INGESTING -> INGESTED   (happy path)
DOWNLOADING -> PENDING          (transient failure, attempts < max, backoff scheduled)
DOWNLOADING -> BLOCKED          (repeated 403 pattern -> proxy/IP block, not a data problem)
DOWNLOADED  -> QUARANTINED      (any verification check fails)
any -> stale-lock reclaim       (heartbeat > 30 min AND pid/host not alive -> force-release, roll back to last safe state)
```
Rule: a transition is only committed to the ledger **after** the corresponding filesystem action is
durably complete (bytes on disk, rename done). This means a crash mid-download leaves a `.part` file
and a ledger still at `DOWNLOADING`/`PENDING` — on restart the `.part` is discarded and the date is
simply retried. A crash mid-ingest leaves the ledger at `VERIFIED` (not `INGESTED`) and a temp parquet
partition that was never atomically renamed in — also just retried. There is no state in which a
half-done action is mistaken for a done one.

## 4. Download mechanics (surviving the 0.7 MB/s flaky proxy)
- Acquire `locks/<date>.lock` (pid+hostname+heartbeat) before touching the date — prevents two
  machines/two scheduled runs from downloading or ingesting the same date concurrently.
- Stream to `raw/incoming/<date>.part` using HTTP Range requests so a stall **resumes from the last
  byte**, not from zero.
- Per-chunk timeout (e.g. 30s of zero-progress) triggers abort+retry-with-range, not a full restart.
- Throughput watchdog: if sustained rate < ~50 KB/s for >120s, abort the attempt (proxy stall pattern),
  requeue with backoff — don't let one hung connection eat the whole run.
- Retry/backoff: exponential with jitter, base 30s, cap 20min, **max 5 attempts per date per run**.
  Distinguish error classes:
  - Transient (timeout, connection reset, 5xx, partial content) -> normal retry counter.
  - `403`/blocked pattern (3 consecutive across attempts) -> mark `BLOCKED`, stop hammering, defer to
    a longer-interval catch-up sweep (blocks usually self-clear in hours) — no alert yet.
  - `404`/file not published yet (exchange hasn't posted EOD file) -> check holiday calendar first;
    if trading day and file plausibly just late, requeue for the next sweep; do not count as a
    "failure" against the alert threshold until it's been missing past the exchange's normal
    publish-time SLA (e.g. 21:00 IST for NSE bhavcopy).
- On byte-count/Content-Length mismatch, treat as a failed attempt (not a success) — never let a
  truncated `.part` get renamed into `raw/incoming/` as if complete.

## 5. Corruption gate — nothing enters the dataset without ALL of these passing
Run in this order, on the completed `.part`, before it is ever renamed to `raw/verified/`:
1. **Size check** — actual bytes == `Content-Length` header (if given) and within [0.3x, 3x] of the
   trailing-20-trading-day median size for that file type (catches truncation and garbage responses,
   e.g. an ISP/proxy captive-portal HTML page saved as if it were the zip).
2. **Structural parse** — unzip cleanly (if zipped); load into pandas without parser errors.
3. **Schema check** against `config/schema_v{n}.json` — required columns present, dtypes coercible.
   Mismatch -> flag `SCHEMA_DRIFT`, quarantine (this is a "the exchange changed the format" case,
   deliberately routed to a human, not auto-patched).
4. **Row-count sanity** — within [0.5x, 1.5x] of trailing-20-day median row count. Outside that band
   -> quarantine as suspect rather than silently ingest a half-empty file (legitimately-thin days like
   a holiday-adjacent session are handled via the holiday calendar, not by loosening this check).
5. **Anchor-value spot check (D-009)** — a handful of known/derivable values (e.g. index close vs a
   second free source, or previous close continuity vs yesterday's ingested close) must match within
   tolerance. This is the one check that catches "parses fine, schema fine, but numbers are wrong."
6. **Hash record** — SHA-256 computed and stored regardless of outcome, so a later re-fetch of the
   same date can be compared byte-for-byte to detect silent re-publication/correction by the exchange.

Any single failure -> file + a `reason.txt` (which check failed, expected vs actual) moved to
`quarantine/<date>/`, ledger -> `QUARANTINED`, file is **never deleted** (forensics) and **never
read by the ingestion step**. All 6 pass -> atomic rename into `raw/verified/<date>/`.

## 6. Ingestion — idempotent by construction (no double-ingestion, ever)
- Ingestion only ever reads from `raw/verified/`, never from `incoming/` or `quarantine/`.
- Before starting, check ledger status for the date: if already `INGESTED`, skip (no-op) unless the
  operator explicitly passes `--force-reingest <date>` (a logged, deliberate human action).
- Writes to a **partitioned, overwrite-semantic** target: `dataset/date=YYYY-MM-DD/data.parquet`,
  built via write-to-temp-file + atomic rename over the partition. Re-running ingestion for a date
  (forced or otherwise) *replaces* that partition wholesale — it can never append duplicate rows,
  because the unit of ingestion is "the whole partition for one date," not row-by-row appends.
- Only after the atomic rename succeeds does the ledger commit `INGESTED` with the row count —
  matching §3's rule that ledger state always trails, never leads, the durable filesystem action.

## 7. Scheduling / self-healing sweep (this is what avoids most alerts)
- Primary run: scheduled daily (fits the firm's existing 20:00/23:00 IST capture-task cadence) —
  attempts today's date.
- Catch-up sweep: runs every ~2h until 09:00 next day, and additionally scans the **trailing 10
  trading days** on every invocation for any date not in a terminal state (`INGESTED` or
  `QUARANTINED`-and-acknowledged). This is what makes a multi-day proxy outage or IP block self-heal
  silently once the network recovers — no per-day alert fatigue, because each sweep just re-drives
  whatever's still incomplete through the same idempotent state machine.
- Holiday-calendar aware: a trading holiday with no file is expected and produces no alert at all.

## 8. Alerting — fires only when the pipeline itself cannot resolve it
Escalate to `ALERTS.md` (+ push notification) only when:
- A date has failed **all 5 download attempts in the primary run AND is still incomplete after the
  next full catch-up sweep** (i.e., two independent failure windows, not one blip).
- A file reaches `QUARANTINED` for a **content/schema reason** (checks 2–5 in §5) — this is
  definitionally something auto-retry cannot fix; a corrupt/garbled file will corrupt again on
  re-download of the same source glitch. (A blocked/`403` state is *not* alerted the same way —
  that's handled by backoff, see below.)
- `BLOCKED` (proxy/IP block) persists beyond **24h** with zero successful pulls in that window —
  blocks under an hour or two are normal proxy behavior and resolved by the sweep, not a human problem.
- A stale lock (heartbeat >30min, process confirmed dead) is force-reclaimed — logged as an
  informational note in the daily digest, not a page, since the pipeline self-recovered.
- Anchor-value spot check disagrees beyond tolerance repeatedly (2+ dates) — possible source-side data
  quality regression, needs a human to decide whether to update the anchor or reject the source.

Each alert entry carries: trade_date(s) affected, exact error signature/last_error, checks
passed/failed, attempts made, and a concrete suggested action (e.g. "schema drift: exchange added
column X — bump config/schema_v{n}.json and re-run ingest for these dates"). Alerts require explicit
acknowledgment (`status: OPEN -> RESOLVED` edit) before the same underlying issue can re-alert; while
open, recurring sweeps append "still open, Xh" to a daily digest rather than re-paging — no alert
spam for a single unresolved root cause.

## 9. New-machine mid-history takeover
1. Copy/sync the whole `eod_ingest/` folder (the JSONL ledger + `raw/verified/` + `quarantine/` are
   the only things that must travel; `ledger.db` and `.part` files do not need to and should not be
   copied — they're local/derived/transient).
2. Run `scripts/rebuild_ledger_db.py` — replays `ledger_events.jsonl` end-to-end into a fresh local
   `ledger.db`. This is what makes the JSONL, not the SQLite file, the actual portable ledger: SQLite
   binaries don't merge safely across machines/OneDrive sync, an append-only event log does.
3. Run `scripts/run_ingest.py` normally. Every already-`INGESTED` date is skipped (per §6); the sweep
   (§7) picks up exactly where the previous machine left off — oldest non-terminal date first. No
   manual bookkeeping, no "which day did we get to" conversation needed; the ledger answers it.
4. Locks (`locks/*.lock`) are host-qualified and heartbeat-timestamped, so if the old machine's process
   is actually dead, the new machine's stale-lock reclaim (§3) takes over cleanly rather than
   deadlocking on a lock file left behind by a machine that's now offline.

## 10. Why each failure mode is covered
| Failure | Mechanism that prevents it |
|---|---|
| Crash mid-download | `.part` file discarded, ledger still `PENDING`/`DOWNLOADING`, retried from scratch (or Range-resumed) |
| Crash mid-verify | File sits in `raw/incoming/`, not yet renamed to `verified/`; ledger not `VERIFIED`; re-verified next run |
| Crash mid-ingest | Temp partition never atomically renamed in; ledger not `INGESTED`; re-ingested from `raw/verified/` (idempotent overwrite) |
| Double-ingestion (re-run, two machines, retried sweep) | Ledger status check skips `INGESTED`; partition write is overwrite-semantic, not append |
| Corrupt/truncated file entering dataset | 6-point verification gate (§5) is mandatory between download and ingest; only `raw/verified/` is ever read by ingestion |
| Proxy stall | Range-resume + throughput watchdog + bounded per-chunk timeout |
| IP block | Detected via 403 pattern, backed off long, not alerted until >24h with zero successes |
| Alert fatigue | Escalation only after two independent failure windows or a definitionally-unfixable content failure; ack/cooldown prevents re-paging on the same open issue |
| New machine, lost history | JSONL event log is the portable source of truth; `rebuild_ledger_db.py` reconstructs state; raw/verified files travel with it |
| Schema drift at source | Explicit `QUARANTINED` + `SCHEMA_DRIFT` reason, routed to human — never silently coerced |
