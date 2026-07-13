# Resume-Safe Daily EOD Ingestion Pipeline

**Scope:** pull end-of-day exchange archive files (e.g. NSE bhavcopy zips) through an unreliable corporate proxy (~0.7 MB/s, random stalls, occasional IP blocks). Guarantees: no loss, no double-ingest across crashes/restarts, no corrupt file ever enters the dataset, human alerted only on genuine action, a fresh machine can resume mid-history.

The whole design rests on one idea: **the pipeline holds no state in memory.** Every fact about "what has happened" lives in files that survive `kill -9`. A crash is indistinguishable from a fresh start — both just read the ledger and continue.

---

## 1. On-disk layout (the state IS the filesystem)

```
data_office/eod/
├── manifest/
│   ├── expected.jsonl          # what SHOULD exist per trading day (the plan)
│   └── ledger.jsonl            # append-only event log (the truth)
├── work/                       # partial downloads, never read by consumers
│   └── <date>__<source>.part
├── raw/                        # verified, immutable exchange files
│   └── <yyyy>/<mm>/<date>__<source>.zip
├── raw/.sha256/
│   └── <date>__<source>.zip.sha256   # sidecar checksum, written with the file
├── curated/                    # parsed parquet, the dataset consumers read
│   └── <yyyy>/<mm>/<date>.parquet
├── locks/
│   └── ingest.lock             # single-writer lock (PID + hostname + mtime)
└── alerts/
    └── outbox.jsonl            # dedup'd alert queue
```

Rules that make this safe:
- **`raw/` and `curated/` are append-only and immutable.** A file appears there only after it is fully verified. Nothing is ever edited in place.
- **`work/` is disposable.** Anything in `work/` on startup is a half-download from a crash and is deleted (or resumed via HTTP Range — see §4).
- **Consumers only ever read `curated/`.** They never see `work/` and never see a `raw/` file mid-write.

---

## 2. The two manifests

### `expected.jsonl` — the plan (idempotent to regenerate)
One line per (trading_day, source), generated from the exchange trading calendar. Regenerating it is a pure function of the calendar, so it is safe to rebuild on any machine.

```json
{"date":"2026-07-13","source":"nse_bhav_sec","url":"https://nsearchives.nseindia.com/.../sec_bhavdata_full_130726.csv","required":true}
{"date":"2026-07-13","source":"nse_bhav_fo","url":"https://nsearchives.nseindia.com/.../fo130726.zip","required":true}
```
Trading-holiday days simply have no rows → nothing is "missing" on a holiday, so no false alerts.

### `ledger.jsonl` — the truth (append-only event log)
Every state transition is one appended line. **We never rewrite lines**; the current state of a file = the last event for its `(date,source)` key. Append-only + fsync makes it crash-atomic (a torn final line is detected by JSON-parse failure and dropped on read).

```json
{"ts":"2026-07-13T20:01:03Z","date":"2026-07-13","source":"nse_bhav_fo","event":"DOWNLOAD_OK","bytes":184322,"sha256":"9f...","attempt":2}
{"ts":"2026-07-13T20:01:05Z","date":"2026-07-13","source":"nse_bhav_fo","event":"VERIFY_OK","rows":184,"schema":"fo_v3"}
{"ts":"2026-07-13T20:01:06Z","date":"2026-07-13","source":"nse_bhav_fo","event":"INGEST_OK","curated":"curated/2026/07/2026-07-13.parquet"}
```

Event vocabulary (a file marches monotonically forward):
`QUEUED → DOWNLOAD_OK → VERIFY_OK → INGEST_OK` (terminal-success)
Failure branches: `DOWNLOAD_FAIL`, `VERIFY_FAIL`, `IP_BLOCKED`, `PERMANENTLY_MISSING`, `ALERTED`.

**Why this gives no-double-ingest for free:** before doing any work on `(date,source)`, the runner folds the ledger to that key's last event. If it's `INGEST_OK`, skip. This is the *"skip-completed rerun rule"* — a re-run, a cross-session resume, or a second machine simply re-reads the ledger and does nothing already done. (Firm history: cross-session resume that ignored this once re-ran and overwrote a subset — hence the append-only ledger fold is mandatory, never a "did the file exist?" check.)

---

## 3. Single-writer lock (no two runners collide)

`locks/ingest.lock` written atomically (`open O_CREAT|O_EXCL`) containing `{"pid":…,"host":…,"started":…,"heartbeat":…}`. The runner refreshes `heartbeat` every 30 s.
- On startup, if the lock exists **and** heartbeat is < 5 min old → another runner is alive → exit quietly (no alert).
- If heartbeat is stale (> 5 min) → previous runner died → **steal the lock** (log `LOCK_STOLEN`) and proceed. Because all real state is in the ledger, stealing is safe: the dead runner left at most a `work/*.part` file, which we discard.

This is what lets a **new machine take over mid-history**: point it at the same `data_office/eod/` (shared drive / synced folder / object store), it acquires or steals the lock, folds the ledger, and continues from the first non-`INGEST_OK` expected row.

---

## 4. Download stage — beating the flaky proxy

Per the environment: sequential `requests.Session()` only (threads stall behind the proxy), `truststore.inject_into_ssl()`, ~1.2 s spacing, cookie warm-up for NSE.

For each expected row whose ledger state is below `DOWNLOAD_OK`:

1. **Download to `work/<key>.part`, never to `raw/`.** Consumers can never see it.
2. **Streamed, resumable, stall-detected:**
   - `stream=True`, write in 64 KB chunks.
   - **Stall watchdog:** if no chunk arrives for `read_timeout = 45 s`, abort this attempt (this is the "random stall" case — a socket that hangs forever otherwise).
   - **HTTP Range resume:** on retry, if `<key>.part` exists and server sent `Accept-Ranges: bytes`, send `Range: bytes=<partsize>-` and append. Saves re-pulling MBs already through the 0.7 MB/s pipe. If the server ignores Range (200 not 206), truncate `.part` and restart clean.
3. **Retry policy (bounded, jittered exponential backoff):** delays `5s, 20s, 60s, 180s`, max 4 attempts. Each attempt logs `DOWNLOAD_FAIL` with the reason. Distinct handling:
   - Timeout / connection reset / `ChunkedEncodingError` → normal retry.
   - **HTTP 403 / 429 / connection-refused burst → treat as IP block:** log `IP_BLOCKED`, stop the whole run for that source, and back off long (see §7). Do **not** burn all attempts hammering a block — that deepens it.
4. On a complete download: compute SHA-256 of the `.part`, log `DOWNLOAD_OK` with bytes + sha.

Nothing is promoted out of `work/` yet — a byte-complete download is still not trusted.

---

## 5. Verify stage — corrupt files can never enter the dataset

This is the gate that makes "corrupt downloads never enter the dataset" true. A file passes **all** checks or it is deleted from `work/` and marked `VERIFY_FAIL`.

1. **Size sanity:** bytes > a per-source floor (e.g. bhavcopy zip > 20 KB). Catches proxy error-pages / truncation (a 4 KB "Access Denied" HTML page fails here).
2. **Content-type / magic bytes:** first bytes match the expected container (`PK\x03\x04` for zip; not `<!DOCTYPE html` / `<html`). Catches the proxy returning an HTML block page with HTTP 200.
3. **Container integrity:** `zipfile.testzip()` (or gzip CRC) returns clean — every entry's CRC matches. A partial/corrupt zip fails here even if byte-count looked plausible.
4. **Schema + row sanity (parse to staging):** open the inner CSV, assert expected columns present (per `05_DATA_OFFICE/DATA_QUALITY_RULES.md` schema helpers / `04_RND_LAB/lib/guards.py`), row count > per-source floor, date column == the expected date (no wrong-day file), no all-zero/empty frame.
5. **Domain spot-check (D-009):** a couple of known-value assertions — e.g. NIFTY/ RELIANCE row present, `CONTRACTS>0` gate for F&O legs, close within a sane band vs the prior curated day (a 10x jump = fat-finger/bad file → fail). This is the sample verification the firm requires before any new data is used.

Only on all-pass:
- Write sidecar `raw/.sha256/<key>.zip.sha256`.
- **Atomically publish:** `os.replace(work/<key>.part → raw/yyyy/mm/<key>.zip)` — `os.replace` is atomic on the same filesystem, so `raw/` never contains a half file even if power dies mid-move.
- Log `VERIFY_OK` with rows + schema version.

A crash between `DOWNLOAD_OK` and `VERIFY_OK` is harmless: on restart the ledger shows `DOWNLOAD_OK`, the `.part` is re-verified (checksum matches the logged sha → skip re-download), and it proceeds.

## 6. Ingest stage — atomic, idempotent parquet write

1. Parse verified `raw/` file → dataframe (with the firm's landmine guards: HF tz fix, pre-open filter, expiry-day settle handling, etc. as applicable to the source).
2. Write to `curated/yyyy/mm/<date>.parquet.tmp`, then `os.replace` to the final name — atomic publish again. Consumers reading `curated/` either see the old file or the complete new one, never a partial.
3. Log `INGEST_OK` with the curated path. This is the terminal state; the `(date,source)` key is now permanently "done" and will be skipped by every future run.

Idempotency guarantee: because the final ledger event, not the presence of a file, decides "done", re-running after `INGEST_OK` is a no-op; re-running after `VERIFY_OK` but before `INGEST_OK` re-parses the *already-verified* raw file (no re-download, no re-verify network cost) and republishes atomically — safe to repeat.

---

## 7. Alerts — only when a human must act

An alert fires **only** for states that automation cannot resolve on its own. Everything transient is retried silently. Alerts go to `alerts/outbox.jsonl` first (dedup key = `date|source|reason`), then a single delivery step drains the outbox (email/push). Writing to the outbox before sending means a crash during send doesn't lose the alert, and dedup means a 3-day proxy outage produces **one** alert, not 300.

Alert **only** on:
- **`IP_BLOCKED` persists** past the long backoff and the next scheduled window (i.e. the block is not clearing itself) → *"proxy blocking archive host; needs home-network/VPN run."* This maps to the known landmine: office proxy blocks some NSE endpoints → human switches network.
- **`PERMANENTLY_MISSING`:** a `required` file still absent N hours after the exchange's normal publish time and after all retries → *"NSE has not published fo-bhav for 2026-07-13, or URL pattern changed."*
- **`VERIFY_FAIL` that is not transient:** same file fails integrity/schema on 2 independent fresh downloads → the source file itself is bad or the schema changed → human inspection. (One-off verify fail just retries; it does not alert.)
- **`SCHEMA_DRIFT`:** columns present but changed vs the registered schema → dataset guard would break downstream → human must update the parser.

Explicitly **no alert** for: another runner already holds the lock, a holiday with no expected rows, a single timed-out download that then succeeds, a stale lock that was cleanly stolen. These are normal operation.

Each alert line logs `ALERTED` to the ledger so it is never re-sent; a matching later success logs `RESOLVED` and (optionally) sends an all-clear.

---

## 8. The run loop (what actually executes each day)

Scheduled via the firm's cron cadence (e.g. `AngelDailyOptionCapture`-style, 15:45 / 20:00 / 23:00 IST — multiple windows so a missed/blocked earlier window is picked up later, each idempotent).

```
1. acquire-or-steal lock (else exit quietly)
2. sweep work/ : for each .part, if its logged DOWNLOAD_OK sha still matches keep for resume, else delete
3. regenerate expected.jsonl from trading calendar (idempotent)
4. fold ledger.jsonl -> current state per (date,source)     # single pass, tail is enough with periodic snapshot
5. build worklist = expected rows whose state != INGEST_OK, oldest-first   # <-- backfill & mid-history resume fall out here
6. for each item, sequentially:
       download (§4) -> verify (§5) -> ingest (§6), appending ledger events, honoring IP_BLOCKED backoff
7. drain alerts/outbox.jsonl (§7)
8. release lock
```

Because step 5 walks **all** not-yet-done expected days oldest-first, the same loop does daily ingest **and** history backfill **and** post-outage catch-up — no separate code path. A new machine on day 400 of history runs the identical loop and simply finds days 1–399 already `INGEST_OK` in the shared ledger.

---

## 9. Ledger compaction & portability (so it scales and travels)

- **Snapshot:** nightly, fold the full `ledger.jsonl` into `ledger.snapshot.json` (current state per key) and truncate the appended log to events since the snapshot. Fold cost stays O(recent), not O(all-history). The snapshot + tail reconstruct full state; both are plain files.
- **Portability / new-machine takeover:** the entire `data_office/eod/` tree is self-describing — ledger + snapshot + raw + sidecar checksums. Copy/sync it (rsync, shared drive, S3) to a new box; it acquires the lock and resumes. To *audit* an inherited dataset, re-hash each `raw/*.zip` against its `.sha256` sidecar and confirm a matching `INGEST_OK` in the ledger; any mismatch is re-verified/re-ingested.
- **Backup:** `raw/` + `manifest/` are the irreplaceable state (curated is regenerable from raw). Back those up per `99_OPS/BACKUP_POLICY.md`.

---

## 10. Failure-mode matrix (the guarantees, made concrete)

| Failure | What survives it | Mechanism |
|---|---|---|
| `kill -9` mid-download | no partial in dataset | download goes to `work/`, atomic `os.replace` only after verify |
| `kill -9` mid-ingest | no partial parquet | `.parquet.tmp` + atomic `os.replace`; ledger fold re-drives |
| crash mid-ledger-write | torn line ignored | append-only + JSON-parse-drop of torn tail; prior events intact |
| re-run / double schedule | no double-ingest | ledger fold → skip `INGEST_OK`; single-writer lock |
| proxy stall (hung socket) | run continues | 45 s read-timeout watchdog aborts the attempt |
| proxy IP block | no wasted hammering, human told once | `IP_BLOCKED` state, long backoff, dedup'd single alert |
| proxy HTML block-page (HTTP 200) | corrupt file rejected | magic-byte + size + zip-CRC checks in verify |
| truncated download | rejected, resumed | size floor + zip `testzip`; HTTP Range resume next attempt |
| wrong-day / stale file | rejected | date-column assertion in schema check |
| schema change at source | human told, dataset unbroken | `SCHEMA_DRIFT` alert; parser never runs on unknown schema |
| exchange didn't publish | one alert after grace window | `PERMANENTLY_MISSING`, not treated as a bug |
| new machine takes over | seamless resume | shared `data_office/eod/`, lock steal, ledger fold, oldest-first worklist |

**Net:** the dataset (`curated/`) is a pure, monotonic function of verified `raw/` files, which are a pure function of the append-only ledger. Nothing enters `curated/` unverified, nothing is done twice, nothing transient wakes a human, and any machine with the folder can continue.
