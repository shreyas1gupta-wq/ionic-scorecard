Design doc below. Since no tools are allowed, my sanity check is a requirements re-read at the end mapping each of the four guarantees to the specific mechanism that enforces it.

# Resume-safe EOD ingestion pipeline

Example flavor: NSE-style bhavcopy zips posted ~18:00 IST; everything generalizes.

## 1. Disk layout (one filesystem, so renames are atomic)

```
data/
  incoming/                      # *.part downloads + *.meta.json (etag, expected size, url)
  raw/YYYY/MM/DD/file.zip        # immutable, verified originals (chmod 444 after landing)
  raw/YYYY/MM/DD/file.zip.sha256 # sidecar written at verification time
  quarantine/YYYY-MM-DD/         # failed verification + .reason.json, kept 30 days
  dataset/trade_date=YYYY-MM-DD/ # parquet partition + _SUCCESS marker containing the source sha256
  ledger/ingest.db               # SQLite (WAL) — rebuildable index, NOT the source of truth
  logs/YYYY-MM-DD.jsonl
```

Hard rule: `incoming/` and `raw/` are on the same mount so `rename()` is atomic. Nothing ever writes directly into `raw/` or `dataset/`; both are reached only by rename-after-verify.

## 2. Ledger

```sql
CREATE TABLE files (
  source TEXT, file_kind TEXT, trade_date TEXT,
  state TEXT CHECK(state IN ('PENDING','VERIFIED','INGESTED','HOLIDAY',
                             'QUARANTINED','WAITING_RETRY','NEEDS_HUMAN')),
  url TEXT, size INTEGER, etag TEXT, sha256 TEXT,
  attempts INT DEFAULT 0, last_error TEXT, next_retry_at TEXT,
  verified_at TEXT, ingested_at TEXT, operator_note TEXT,
  PRIMARY KEY (source, file_kind, trade_date));
CREATE TABLE alerts (key TEXT PRIMARY KEY, first_at TEXT, last_at TEXT,
                     count INT, resolved_at TEXT);
CREATE TABLE lease  (name TEXT PRIMARY KEY, owner TEXT, expires_at TEXT);
```

Two invariants that make this crash-safe:

- **The ledger records only durable facts, never in-flight status.** There is no `DOWNLOADING` state; a crash mid-download simply leaves a `.part` file, which the next run resumes. Attempt counts and `next_retry_at` are durable facts, so backoff survives restarts.
- **Filesystem first, ledger second.** File lands in `raw/` before the row says `VERIFIED`; the `_SUCCESS` marker lands before the row says `INGESTED`. Every crash window between the two is closed by `rebuild-ledger` (below), which re-derives state from disk — never by trusting a flag.

## 3. Work planning — absence is a first-class state

A versioned trading-calendar file (holidays, timezone `Asia/Kolkata`) expands into the expected set of `(source, file_kind, trade_date)` rows. Each expected file gets a `PENDING` row; holidays get `HOLIDAY`. This is what makes "nothing is ever lost" enforceable: a missing day is a visible non-`INGESTED` row, not silence. `pipeline gaps --since 2020-01-01` lists every unfilled trading day in seconds. An ad-hoc exchange holiday is resolved by a human with `pipeline mark-holiday 2026-07-14 --reason "..."` (recorded with operator note).

## 4. Download step (the unreliable-proxy defenses)

Per file, worker does:

1. `HEAD` (or `GET Range: bytes=0-0`) → capture `Content-Length`, `ETag`/`Last-Modified` into `incoming/name.meta.json`.
2. If `name.part` exists and stored ETag matches, resume with `Range: bytes=<part_size>-`. ETag mismatch or no `Accept-Ranges` → delete `.part`, restart from zero.
3. Stream in 1 MiB chunks. Timeouts: connect 15 s, read 60 s. **Stall watchdog:** if throughput < 20 KB/s averaged over 60 s, abort the attempt (equivalent to curl `--speed-limit 20480 --speed-time 60`) and retry immediately with a Range resume — a stall costs 60 s, not a hang.
4. **Retry schedule** on failure: 1 m, 5 m, 15 m, 60 m, then hourly, ±20% jitter, persisted in `next_retry_at` so restarts don't reset backoff. Honor `Retry-After` on 429/503.
5. **Block detection:** HTTP 403/429, connect-reset, or a 200 whose Content-Type/magic bytes are HTML instead of the expected zip (corporate proxies inject 200 block pages — never trust a 200). On block signature: back off 90 ± 30 min, force concurrency to 1, and keep a 3–8 s jittered politeness gap between requests on one keep-alive session. Default concurrency is 1 anyway — at 0.7 MB/s the link, not the loop, is the bottleneck, and parallelism only raises block risk.

## 5. Verification gate (corrupt bytes can't pass)

Runs on the completed `.part`, still in `incoming/`:

1. Byte size == Content-Length and == sidecar expectation.
2. Publisher checksum if the archive provides one.
3. Structural: zip CRC test of every member (`zipfile.testzip`), full gzip decode, strict-schema CSV parse.
4. Semantic hard-fails: zero rows; embedded trade date != requested date (catches "server served yesterday's file / an error page"). Soft warning (log only): row count outside 50–200% of the trailing 20-day median.
5. Compute SHA-256 → write sidecar → `fsync` file → atomic rename into `raw/YYYY/MM/DD/` → fsync directory → `chmod 444` → ledger row `VERIFIED`.

Failure → move to `quarantine/` with `.reason.json`, re-download from scratch (proxy mangling is the usual cause). Three failures with *identical* bad bytes → `NEEDS_HUMAN` (source-side problem). If a re-download of an already-`VERIFIED` date returns different bytes, never overwrite: store as `name.<sha8>.v2` and raise a RESTATEMENT alert for a human decision.

## 6. Ingestion — exactly-once by construction

Idempotency key: `(trade_date, file_sha256)`. Reads only from `raw/`.

- Parquet target: write to `dataset/_tmp/<uuid>/`, atomic-rename to `dataset/trade_date=YYYY-MM-DD/` containing `part-<sha8>.parquet`, write `_SUCCESS` (embedding the source sha256) last, then ledger `INSERT OR IGNORE` → `INGESTED`. The partition path is a pure function of the key, so re-running after any crash overwrites the same partition with the same bytes — replay converges, never duplicates. No appends anywhere (appends are how double-ingest happens).
- SQL target: `DELETE FROM eod WHERE trade_date=?; INSERT ...; INSERT INTO ingested(sha256, trade_date)...` in **one transaction**, with the idempotency table in the target DB itself.

Orphan `_tmp/` dirs and `.part` files older than 7 days are removed by a janitor step.

## 7. Scheduling and single-writer safety

systemd timer (or cron) runs the same idempotent command `pipeline run` at 18:30 IST, hourly until 23:00, and once at 07:00 next day for stragglers. Every run: acquire lease → plan → download → verify → ingest → alert-evaluate → heartbeat. The **lease** is a ledger row (`owner`, `expires_at`, heartbeat-refreshed every 60 s, stealable after 5 min stale) so an overlapping cron fire or a second machine can never double-run — critical during migration.

## 8. Alerting — silent unless a human must act

- **Never alerts:** retries, stalls, resumed downloads, a verification failure fixed by re-download, holiday skips. These go to JSONL logs and an optional daily digest line.
- **Alerts (Slack webhook + email fallback):** (a) any trading day not `INGESTED` by the SLA of T+1 09:00 IST — the only "data missing" signal a human ever needs; (b) 3× identical-bytes verification failure; (c) block signature persisting > 4 h despite backoff (means: call IT about the proxy); (d) RESTATEMENT detected; (e) disk < 10 GB, unwritable ledger, or lease conflict.
- **Dedup:** the `alerts` table keys each condition; re-fire only every 24 h while unresolved, and send an auto-resolve note when the condition clears. No repeats, no pager fatigue.
- **Dead-man switch:** the box that is down cannot alert about itself, so each successful cycle pings an external healthchecks.io-style URL with a 26 h grace period. Silence → external alert. This closes the "whole machine died quietly" hole.

## 9. New-machine takeover

`raw/` (plus its sidecars) is the only irreplaceable artifact — the ledger and dataset are both derivable from it — and it is rsync/rclone'd nightly to a second location along with a WAL-safe `sqlite3 .backup` snapshot.

Takeover: (1) install pinned code + config on the new box; (2) copy or mount the data dir (worst case: just `raw/`); (3) `pipeline rebuild-ledger` — every `raw/` file whose bytes match its sidecar hash → `VERIFIED`, every dataset partition with a `_SUCCESS` marker matching that hash → `INGESTED`, everything expected-but-absent → `PENDING`; add `--verify-all` to re-hash the whole copy after an untrusted transfer; (4) enable the timer. The first `pipeline run` resumes any `.part`, backfills the gap since the last file, and the lease guarantees safety even if the old machine wasn't stopped yet.

## Sanity check — requirement → enforcing mechanism

| Requirement | Mechanism |
|---|---|
| Nothing lost | Calendar-derived expected set makes absence visible; SLA alert + `gaps`; immutable append-only `raw/`; nightly offsite copy |
| Nothing double-ingested | `(trade_date, sha256)` idempotency key; rename-into-place partitions or single-transaction SQL; `INSERT OR IGNORE` ledger; no appends; lease against concurrent runners |
| Corrupt data never enters | Verify-then-rename gate (size, CRC, strict parse, embedded-date match, sha256) before anything touches `raw/`; quarantine; 200-with-HTML proxy-page detection |
| Alert only when actionable | Retries/stalls are silent; alerts only on SLA breach, persistent block, repeated identical corruption, restatement, ops faults; deduped with auto-resolve; dead-man switch for total silence |
| New machine mid-history | Self-describing `raw/` + sidecars + `_SUCCESS` markers; `rebuild-ledger`; lease steal; resumable `.part` files |

Crash-safety spine, restated in one line: durable facts only in the ledger, filesystem-before-ledger ordering, atomic renames on one mount, and idempotent re-checks to close every crash window.

result: Delivered a concrete resume-safe EOD ingestion design — staged-download/verify/rename flow with Range-resume and stall watchdog, sha256-keyed idempotent ingest, rebuildable SQLite ledger with lease, SLA-and-deadman-only alerting, and a rebuild-ledger takeover path for new machines.