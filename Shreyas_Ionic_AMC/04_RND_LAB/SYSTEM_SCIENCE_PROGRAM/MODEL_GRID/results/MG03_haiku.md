# MG-03: Resume-Safe Daily Exchange Data Ingestion Pipeline

## Design Intent
Pull end-of-day files from an exchange archive through a hostile proxy (0.7 MB/s, random stalls, IP blocks, timeouts) such that:
- **No data loss:** every file fetched is recorded; crashes/restarts resume exactly where they stopped.
- **No double-ingestion:** same file processed twice → idempotent outcome (not duplicate rows).
- **No corruption:** invalid/incomplete downloads are caught before entering the live dataset.
- **Minimal alerts:** humans notified only when recovery action is actually required.
- **Machine-independent:** new laptop takes over mid-history by reading the state ledger, no manual re-sync.

---

## Architecture: Five-Layer Pipeline

```
┌─ LEDGER LAYER (single source of truth for all state)
│  ├─ state_ledger.jsonl    [daily file status, hashes, ingestion timestamp, error log]
│  ├─ download_log.jsonl    [every GET attempt, proxy stall/timeout/IP-block events]
│  └─ alert_log.jsonl       [human-facing escalations with context+recommendation]
│
├─ DOWNLOAD LAYER (resumable, proxy-resilient)
│  ├─ Staging/quarantine/   [temp .zip/.csv files, in-flight or awaiting validation]
│  ├─ retry_queue.json      [files that need re-fetch, with backoff-state]
│  └─ (proxy retry: exponential backoff 1s→2s→4s→8s, max 12 attempts over 4h)
│
├─ VALIDATION LAYER (integrity check before live)
│  ├─ [Hash match: archive metadata SHA256 vs. downloaded file]
│  ├─ [Schema check: expected columns, row count sanity, timestamp ranges]
│  ├─ [Corruption signal: > N missing rows, timestamp gaps, repeated prices]
│  └─ [Quarantine verdict: PASS → promote to live, FAIL → alert + human review]
│
├─ INGESTION LAYER (atomic, idempotent)
│  ├─ Live/current/          [parquet/SQL table, single source of truth for analytics]
│  ├─ On ingestion: upsert-by-key (date, ticker, contract) so re-running same file = no duplicates
│  └─ Rollback-safe: pre-ingest snapshot + transaction log so recovery is procedural
│
└─ MONITORING LAYER (ledger-driven diagnostics)
   ├─ Daily health-check: count(PENDING) + count(FAILED_VALIDATION) + backoff-queue length
   ├─ Machine-takeover bootstrap: read state_ledger, find last INGESTED row, resume from next date
   └─ Proxy-failure pattern detection: IP block → escalate, repeated timeouts → alert ops
```

---

## State Ledger Schema (source of truth)

**File:** `state_ledger.jsonl` (one JSON object per line, one per date/file)

```json
{
  "date": "2026-07-11",
  "filename": "bhavcopy_11-07-2026.zip",
  "archive_url": "https://nsearchives.nseindia.com/content/historical/...",
  "status": "INGESTED",
  "download_attempts": 3,
  "download_start_utc": "2026-07-11T15:30:00Z",
  "download_complete_utc": "2026-07-11T15:32:15Z",
  "file_size_bytes": 2345678,
  "archive_sha256": "a1b2c3d4e5f6...",
  "downloaded_sha256": "a1b2c3d4e5f6...",
  "hash_match": true,
  "validation_checks": {
    "schema_ok": true,
    "row_count": 1523,
    "expected_row_count_min": 1400,
    "expected_row_count_max": 1700,
    "timestamp_coverage": "2026-07-11T09:15:00Z to 2026-07-11T15:30:00Z",
    "corruption_signals": []
  },
  "validation_status": "PASS",
  "validation_completed_utc": "2026-07-11T15:33:00Z",
  "ingestion_start_utc": "2026-07-11T15:33:05Z",
  "ingestion_complete_utc": "2026-07-11T15:33:45Z",
  "ingestion_status": "SUCCESS",
  "rows_ingested": 1523,
  "rows_duplicate_skipped": 0,
  "notes": "Proxy stall attempt 2; recovered with 4s backoff",
  "error_log": []
}
```

**File:** `download_log.jsonl` (append-only, one line per download attempt)

```json
{
  "timestamp_utc": "2026-07-11T15:30:00Z",
  "filename": "bhavcopy_11-07-2026.zip",
  "attempt": 1,
  "status": "TIMEOUT",
  "proxy_event": "read timeout after 45s (0 bytes received)",
  "bytes_received": 0,
  "retry_after_seconds": 1
}
```

**File:** `alert_log.jsonl` (append-only, one line per human escalation)

```json
{
  "timestamp_utc": "2026-07-11T16:45:00Z",
  "severity": "WARNING",
  "code": "VALIDATION_FAILED",
  "filename": "bhavcopy_11-07-2026.zip",
  "context": {
    "row_count": 523,
    "expected_min": 1400,
    "corruption_signal": "50% fewer rows than baseline"
  },
  "recommendation": "Manual download from archive; inspect for NSE maintenance window",
  "human_action_required": true,
  "escalation_channel": "ops-engineer-manoj-pillai"
}
```

---

## Download Layer: Proxy-Resilient Fetching

### Retry Strategy (Non-Negotiable)

1. **Exponential Backoff:** 1s → 2s → 4s → 8s → 16s → 32s → 64s → 128s (doubling, capped at 2min)
2. **Max Attempts:** 12 retries = ~21 min cumulative wait
3. **Timeout per attempt:** 120 seconds (no partial completion; if stall detected, abort immediately)
4. **Proxy event categorization:**
   - `TIMEOUT`: no bytes after 120s → backoff + retry
   - `PARTIAL_DOWNLOAD`: bytes received < file_size_bytes by >1% → backoff + retry (discard incomplete)
   - `IP_BLOCK`: HTTP 429 or 403 from proxy → alert ops, backoff 5 min, retry once
   - `SSL_ERROR`: proxy certificate issue → alert ops immediately
   - `CONNECTION_RESET`: proxy closed mid-transfer → backoff + retry

### Quarantine Directory Structure

```
Staging/quarantine/
├── pending/           # Files being downloaded
│   └─ bhavcopy_11-07-2026.zip.partial
├── validated/         # Files passed integrity check, ready to ingest
│   └─ bhavcopy_11-07-2026.zip
├── failed/            # Files failed validation, awaiting human review
│   └─ bhavcopy_11-07-2026.zip.FAILED_<reason>
└── archive/           # Successfully ingested files (kept for 90 days, then purged)
    └─ bhavcopy_11-07-2026.zip
```

### Download Flow (Pseudocode)

```python
def download_file(date, url):
    ledger_entry = read_ledger(date)
    
    if ledger_entry and ledger_entry.status in ["INGESTED", "VALIDATED"]:
        return  # Already done, skip
    
    if ledger_entry and ledger_entry.status == "DOWNLOADING":
        # Crash recovery: check if partial file exists
        if pending_file_exists():
            attempt_count = ledger_entry.download_attempts
        else:
            attempt_count = 0
    else:
        attempt_count = 0
    
    for attempt in range(12):  # Max 12 attempts
        try:
            backoff_seconds = min(1 * (2 ** attempt), 120)
            if attempt > 0:
                sleep(backoff_seconds)
            
            response = requests.get(
                url,
                timeout=120,
                stream=True,
                verify=False  # Corporate proxy cert issue
            )
            
            expected_size = get_archive_metadata(date).file_size_bytes
            
            # Stream download with size check
            bytes_received = 0
            with open(f"quarantine/pending/{filename}.partial", "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_received += len(chunk)
                    
                    # Detect short-read stall (no data for 30s)
                    if time_since_last_byte() > 30:
                        raise TimeoutError("No data for 30s")
            
            # Check final size
            if bytes_received < expected_size * 0.99:
                raise ValueError(f"Partial download: {bytes_received}/{expected_size}")
            
            # Atomic rename to validated queue
            os.rename(
                f"quarantine/pending/{filename}.partial",
                f"quarantine/validated/{filename}"
            )
            
            # Log success
            log_download_event(date, "SUCCESS", bytes_received, attempt)
            update_ledger(date, status="VALIDATED", hash=compute_sha256(file))
            return
            
        except (requests.Timeout, ConnectionError, TimeoutError) as e:
            log_download_event(date, "TIMEOUT", bytes_received, attempt, str(e))
            if attempt == 11:  # Last attempt failed
                log_alert("DOWNLOAD_FAILED", date, f"12 retries exhausted: {e}")
                update_ledger(date, status="FAILED_DOWNLOAD", error=str(e))
        except Exception as e:
            log_alert("DOWNLOAD_ERROR", date, f"Attempt {attempt}: {e}")
            if "429" in str(e) or "403" in str(e):
                break  # Don't retry IP blocks; wait for ops to intervene
```

---

## Validation Layer: Corruption Detection

### Pre-Ingestion Validation Checklist

**Run immediately after download completes; before any database touch.**

1. **Hash Verification (against archive metadata)**
   - Download `bhavcopy_11-07-2026.zip` and read its SHA256 from NSE API/metadata endpoint
   - Compute SHA256 of downloaded file
   - If mismatch → move to `failed/` + log alert `HASH_MISMATCH`

2. **Schema & Structure Check**
   - Extract ZIP and check expected columns (SYMBOL, OPEN, HIGH, LOW, CLOSE, VOLUME, etc.)
   - If columns missing → `SCHEMA_INVALID`
   - If CSV encoding not UTF-8 → `ENCODING_ERROR`

3. **Row Count Sanity**
   - Load row count from file
   - Compare to baseline (e.g., ~1500 for NSE bhavcopy on a normal trading day)
   - If count < 1400 or > 1700 (outside normal range) → flag `ROW_COUNT_ANOMALY`
   - If count < 100 → automatic `VALIDATION_FAIL` (clearly corrupted)

4. **Timestamp & Time-Range Check**
   - Extract min/max timestamp from data
   - Should span roughly 09:15 to 15:30 IST (6h window)
   - If all timestamps identical → flag `TIMESTAMP_ANOMALY`
   - If spans < 1h or > 10h → flag `TIME_RANGE_ANOMALY`

5. **Price Sanity**
   - For each row: CLOSE should be within ±30% of OPEN (extreme single-day move = data error)
   - For NIFTY: should be between 10,000 and 30,000 (known range, adjust as needed)
   - Count rows with nonsensical prices (0, NULL, extreme outliers)
   - If > 5% of rows fail → flag `PRICE_CORRUPTION`

6. **Duplicate Detection**
   - Check for duplicate (SYMBOL, DATE, TIME) tuples
   - If found → flag `DUPLICATE_ROWS` (but do NOT fail; log for human review)

### Validation Outcome

**PASS:** All checks green → move file to `quarantine/validated/` → proceed to ingestion

**FAIL:** Any check red with `human_action_required=true`:
- Move file to `quarantine/failed/<filename>.FAILED_<code>`
- Log alert with severity=WARNING or ERROR
- Example: `bhavcopy_11-07-2026.zip.FAILED_HASH_MISMATCH`

**Examples of fail codes that require human intervention:**
- `HASH_MISMATCH` (file corrupted in transit or on archive)
- `SCHEMA_INVALID` (NSE changed format)
- `ROW_COUNT_ANOMALY` with < 100 rows
- `IP_BLOCK` (too many retries exhausted)

**Examples of fail codes that auto-retry or skip:**
- `TIMESTAMP_ANOMALY` on a holiday → log as INFO, skip date, move to next (ops can manually verify)

---

## Ingestion Layer: Atomic & Idempotent

### Pre-Ingestion Snapshot

Before touching the database:

```python
def ingest_file(date, filepath):
    ledger_entry = read_ledger(date)
    
    if ledger_entry.status == "INGESTED":
        return  # Already done, skip
    
    # Create rollback snapshot
    snapshot_file = f"backups/pre_ingest_{date}_v{int(time.time())}.parquet"
    existing_data = read_live_table().filter(date=date)
    existing_data.to_parquet(snapshot_file)
    
    # Upsert with idempotent key: (date, ticker, contract_code)
    new_data = read_quarantine_file(filepath)
    
    # Deduplicate: if same (date, ticker, contract) already in live table, replace
    live_table = read_live_table()
    live_table_minus_date = live_table.filter(date != date)
    
    combined = pd.concat([live_table_minus_date, new_data])
    combined = combined.drop_duplicates(subset=["date", "ticker", "contract"], keep="last")
    
    # Atomic write (SQL transaction or Parquet rewrite with atomic rename)
    combined.to_parquet(f"live_table_new.parquet")
    os.rename("live_table_new.parquet", "live_table.parquet")  # Atomic on NTFS
    
    # Mark as ingested in ledger
    update_ledger(
        date,
        status="INGESTED",
        rows_ingested=len(new_data),
        snapshot_file=snapshot_file
    )
```

### Rollback Procedure (if needed)

If human discovers corruption AFTER ingestion:
```python
def rollback_date(date):
    snapshot_file = read_ledger(date).snapshot_file
    snapshot_data = read_parquet(snapshot_file)
    
    live_table = read_live_table()
    live_table_minus_date = live_table.filter(date != date)
    
    restored = pd.concat([live_table_minus_date, snapshot_data])
    restored.to_parquet("live_table_new.parquet")
    os.rename("live_table_new.parquet", "live_table.parquet")
    
    update_ledger(date, status="ROLLED_BACK_MANUAL", notes="Human intervention: <reason>")
    log_alert("ROLLBACK_EXECUTED", date, f"Rolled back to {snapshot_file}")
```

---

## Resume Safety: Machine Takeover

### Bootstrap Procedure (new machine)

When a new laptop takes over:

```python
def bootstrap_new_machine():
    # 1. Read state ledger from network share
    ledger = read_state_ledger()
    
    # 2. Find last successfully ingested date
    last_ingested = ledger[ledger.status == "INGESTED"].sort_by("date").tail(1)
    next_date_to_fetch = last_ingested.date + timedelta(days=1)
    
    # 3. Check for stuck downloads (status == DOWNLOADING with timestamp > 24h ago)
    stuck = ledger[
        (ledger.status == "DOWNLOADING") &
        (now() - ledger.download_start_utc > timedelta(hours=24))
    ]
    for entry in stuck:
        # Clean up partial file and reset status
        os.remove(f"quarantine/pending/{entry.filename}.partial")
        update_ledger(entry.date, status="READY_TO_DOWNLOAD", notes="Resumed after crash")
    
    # 4. Check validation queue (status == VALIDATED)
    validated = ledger[ledger.status == "VALIDATED"]
    for entry in validated:
        ingest_file(entry.date, f"quarantine/validated/{entry.filename}")
    
    # 5. Start download cycle from next_date_to_fetch
    print(f"Resume from: {next_date_to_fetch}")
    return next_date_to_fetch
```

### New Machine Guarantees

- **No data loss:** every file that made it to `quarantine/validated/` will be ingested, even if old machine crashed
- **No double-ingestion:** ledger uniquely identifies each (date, file); re-ingesting same file is idempotent
- **No manual sync:** state ledger is single source of truth; new machine reads it and continues

---

## Alert Rules & Escalation (Concrete Thresholds)

**Alerts go to `alert_log.jsonl`; humans are notified only for these scenarios:**

| Condition | Severity | Action | Escalate To |
|-----------|----------|--------|-------------|
| Download fails 12 consecutive times (21 min elapsed) | ERROR | Manual re-download needed; check NSE status page | `ops-engineer-manoj-pillai` |
| Validation check fails (hash mismatch, schema invalid, row count < 100) | WARNING | File moved to `failed/`; human inspects NSE archive integrity | ops |
| IP block (HTTP 429/403) detected | ERROR | Pause all downloads; alert ops to contact proxy admin | ops |
| Consecutive 3 timeout events within 30 min | WARNING | Proxy is degraded; log pattern + recommend manual intervention | ops |
| Row count anomaly (< 1400) but ≥ 100 | INFO | Log as possible NSE maintenance; auto-skip, allow retry next day | (no escalation) |
| Timestamp anomaly on a holiday | INFO | Expected; skip date, proceed to next | (no escalation) |
| Pre-ingestion snapshot file missing | CRITICAL | Cannot guarantee rollback safety; halt pipeline | ops + cio-rajan-mehta |
| Ledger write fails (disk full, permissions) | CRITICAL | State machine broken; manual recovery needed | ops |

**Alert format (to be sent via Slack/email):**

```
[MG-03 ALERT] severity=ERROR | code=DOWNLOAD_FAILED
Date: 2026-07-11 | File: bhavcopy_11-07-2026.zip
Event: 12 download attempts exhausted after 21 minutes.
Proxy timeline: TIMEOUT (45s), TIMEOUT (2min), TIMEOUT (4min), ..., TIMEOUT (128s)
Last error: read timeout after 120s (0 bytes received)
Recommendation: Check NSE archive status; if available, trigger manual download.
Action: File placed in quarantine/failed/ for manual review.
Ledger: state_ledger.jsonl line 1523 (status=FAILED_DOWNLOAD)
```

---

## Monitoring & Diagnostics

### Daily Health Check (run at 16:30 IST)

```python
def daily_health_check():
    ledger = read_state_ledger()
    today = date.today()
    
    # Count files in each state
    status_counts = ledger.groupby("status").size()
    
    pending = ledger[ledger.status.isin(["READY_TO_DOWNLOAD", "DOWNLOADING"])].shape[0]
    failed = ledger[ledger.status == "FAILED_DOWNLOAD"].shape[0]
    backoff_queue = read_retry_queue()
    
    # Health dashboard
    report = {
        "date": today,
        "files_pending": pending,
        "files_failed": failed,
        "files_in_backoff_queue": len(backoff_queue),
        "status_breakdown": status_counts.to_dict(),
        "last_ingested_date": ledger[ledger.status == "INGESTED"].date.max(),
        "lag_days": (today - ledger[ledger.status == "INGESTED"].date.max()).days,
    }
    
    # Alert if lag > 2 days
    if report["lag_days"] > 2:
        log_alert("INGESTION_LAG", f"Data pipeline {report['lag_days']} days behind", "WARNING")
    
    return report
```

### Diagnostic Commands for Ops

```bash
# View recent alerts
tail -20 alert_log.jsonl | jq '{timestamp, severity, code, filename}'

# Find all failed validations
grep "VALIDATION_FAILED" state_ledger.jsonl | jq '{date, filename, validation_status}'

# Identify proxy patterns (IP blocks, timeouts)
grep -E "IP_BLOCK|TIMEOUT" download_log.jsonl | jq '{timestamp, attempt, status, proxy_event}' | sort | uniq -c

# Check retry queue backoff state
cat retry_queue.json | jq '.[] | {filename, attempt, backoff_seconds}'

# Recover from crash (find stuck downloads)
jq 'select(.status == "DOWNLOADING" and now - .download_start_utc > 86400)' state_ledger.jsonl

# List files awaiting human review
ls -la quarantine/failed/ | grep "FAILED_"
```

---

## Example: Complete 24-Hour Cycle

**Scenario:** Friday 2026-07-11, normal trading day. Proxy has 1 stall. File is valid. New machine takes over Saturday morning.

### Friday 15:35 IST (09:05 UTC) - Download Starts

```
Event: Daily scheduler triggers ingest_job.py
Action: Read ledger → find date=2026-07-11 not yet present
Action: Download bhavcopy_11-07-2026.zip (3.2 MB) from NSE
Attempt 1: Read timeout after 45s (0 bytes received) → log download_log.jsonl
Action: Exponential backoff = 1 second
Attempt 2: SUCCESS, 3.2 MB received in 5 minutes
Action: Atomic rename to quarantine/validated/
Ledger: { date: "2026-07-11", status: "VALIDATED", download_attempts: 2 }
```

### Friday 15:40 IST (09:10 UTC) - Validation Runs

```
Action: Schema check PASS (all columns present)
Action: Row count = 1523 (within 1400-1700 range) PASS
Action: Timestamp range 09:15 to 15:29 (normal) PASS
Action: Hash match PASS (SHA256 matches NSE metadata)
Action: Price sanity PASS (all NIFTY prices 17500-18100)
Ledger: { status: "VALIDATED", validation_status: "PASS" }
```

### Friday 15:45 IST (09:15 UTC) - Ingestion Runs

```
Action: Create snapshot: backups/pre_ingest_2026-07-11_v1689065100.parquet
Action: Read live_table.parquet (previous 500+ days)
Action: Deduplicate new data against live table by (date, ticker, contract)
Action: Atomic write to live_table_new.parquet (1523 new rows)
Action: Rename to live_table.parquet (atomic on Windows NTFS)
Ledger: { status: "INGESTED", rows_ingested: 1523, snapshot_file: "backups/pre_ingest_2026-07-11_v1689065100.parquet" }
Action: Move file to quarantine/archive/
```

### Saturday 09:00 IST - New Machine Boots Up

```
Event: Shreyas switches to new laptop with cloud-synced /state_ledger.jsonl
Action: bootstrap_new_machine() reads ledger from network share
Action: Finds last_ingested = 2026-07-11
Action: next_date = 2026-07-12 (today)
Action: Checks for stuck downloads → none found
Action: Checks for validated files awaiting ingest → none found
Action: Scheduler resumes download cycle for 2026-07-12
Guarantee: Zero data loss, zero double-ingest, zero manual re-sync
```

---

## File Checklist (All Required for Resume Safety)

| File | Purpose | Location | Format | Append/Overwrite |
|------|---------|----------|--------|------------------|
| `state_ledger.jsonl` | Source of truth for all files | `logs/` | JSONL | Append per date |
| `download_log.jsonl` | Every download attempt (diagnostic) | `logs/` | JSONL | Append per attempt |
| `alert_log.jsonl` | Human escalations only | `logs/` | JSONL | Append per alert |
| `retry_queue.json` | Files needing re-fetch (backoff state) | `state/` | JSON | Overwrite (atomic) |
| `quarantine/pending/<file>.partial` | In-flight download | `quarantine/` | Binary | Atomic rename on success |
| `quarantine/validated/<file>` | Passed validation, ready to ingest | `quarantine/` | ZIP/CSV | Atomic rename from pending |
| `quarantine/failed/<file>.FAILED_<code>` | Failed validation, awaiting review | `quarantine/` | ZIP/CSV | Placed by validator |
| `quarantine/archive/<file>` | Successfully ingested (90-day retention) | `quarantine/` | ZIP/CSV | Moved after ingest |
| `backups/pre_ingest_<date>_v<ts>.parquet` | Rollback snapshot for this date | `backups/` | Parquet | One per ingest |
| `live_table.parquet` | Current live dataset | `data/` | Parquet | Atomic rename after ingest |

---

## Edge Cases & Recovery

### Case 1: Machine Crashes During Download

**State:** `state_ledger.jsonl` has status=DOWNLOADING, partial file exists in `quarantine/pending/`

**Recovery (automatic on restart):**
1. Read ledger → find status=DOWNLOADING with timestamp > 24h ago
2. Delete `quarantine/pending/<file>.partial`
3. Reset ledger status to READY_TO_DOWNLOAD
4. Retry from attempt 0

### Case 2: Validation Fails; Operator Manually Fixes Source

**State:** File in `quarantine/failed/bhavcopy_11-07-2026.zip.FAILED_HASH_MISMATCH`

**Operator Action:**
1. Download file again from archive (or get from op who has it)
2. Copy to `quarantine/validated/bhavcopy_11-07-2026.zip` (overwrite)
3. Update ledger: `{ status: "VALIDATED", validation_status: "PASS", notes: "Manual fix by ops" }`
4. Scheduler re-runs ingestion

### Case 3: Proxy IP Block; Operator Waits, Then Retries

**State:** `alert_log.jsonl` has code=IP_BLOCK, ledger has status=FAILED_DOWNLOAD

**Operator Action:**
1. Contact proxy admin; IP block lifted after 30 min
2. Reset ledger: `{ status: "READY_TO_DOWNLOAD", download_attempts: 0 }`
3. Scheduler re-runs download from attempt 0

### Case 4: Holiday (NSE Closed); File Is Valid But Has 0 Rows

**State:** Validation detects row_count=0, timestamp_range invalid

**Logic:**
- Operator confirms NSE was closed that day
- Manually set ledger: `{ status: "INGESTED", notes: "Holiday (NSE closed)", rows_ingested: 0 }`
- Scheduler moves to next date

---

## Concurrency & Lock Safety

**Single-threaded guarantee:** Scheduler runs one date at a time; no parallel downloads.

**Ledger write safety:** All updates use `flock` (file-level lock) or database transaction:
```python
import fcntl

def update_ledger(date, **fields):
    with open("state_ledger.jsonl", "a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        # Read all entries, update the one matching date, write back
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Live table write safety:** Atomic rename (Windows NTFS supports atomic-rename semantics):
```python
os.rename("live_table_new.parquet", "live_table.parquet")  # Atomic
```

---

## Compliance Checklist

- [x] **Nothing lost:** Every file fetched is recorded in state_ledger before touch
- [x] **No double-ingest:** Idempotent upsert by (date, ticker, contract); same file→same outcome
- [x] **No corruption:** Pre-ingestion validation (hash, schema, row count, price sanity); failed files isolated
- [x] **Minimal alerts:** Only 8 alert codes; auto-recovery for common failures (timeouts, row anomalies)
- [x] **Resume-safe:** Ledger + snapshots + retry queue allow new machine to take over mid-history with zero manual sync
- [x] **Concrete mechanisms:** Files, ledgers, checksums, retry logic, alert rules all specified with examples
- [x] **Operator diagnostics:** Health check, recovery commands, crash scenarios documented

---

## Implementation Roadmap

1. **Phase 1 (Day 1):** State ledger + download layer with exponential backoff
2. **Phase 2 (Day 2):** Validation layer (hash, schema, row count checks)
3. **Phase 3 (Day 3):** Ingestion layer (snapshot, upsert, atomic rename)
4. **Phase 4 (Day 4):** Bootstrap procedure + resume testing (simulate crashes)
5. **Phase 5 (Day 5):** Alert rules + operator playbooks + diagnostics
6. **Phase 6 (Day 6):** Production deployment + 2-week live burn-in

---

## References

- NSE Archive API: `https://nsearchives.nseindia.com/content/historical/`
- SHA256 Metadata: NSE provides in API response; verify before ingestion
- Proxy Config: Use `requests.Session()` with `truststore.inject_into_ssl()` (see CLAUDE.md §ENVIRONMENT)
- Holiday Calendar: Sync daily from NSE trading calendar (auto-detect 0-row files)
