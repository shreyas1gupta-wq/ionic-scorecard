# MG03 — Resume-Safe EOD Ingestion Pipeline — CIO Final Consolidated Spec

**Rajan Mehta, CIO** · integrating Arjun Rao (draft) + Nikhil Bose (red team) · 2026-07-14

**VERDICT: APPROVE — WITH FIVE MANDATED REVISIONS (a RESIZE, not a rebuild).**

Three-line rationale: Arjun's skeleton is the right one — idempotency-key + staging→verify→atomic-promote + calendar-as-arbiter + doctor-reconcile — and I am keeping it. Nikhil's central attack is **correct and load-bearing**: the exactly-once and concurrency proofs are proofs on POSIX local disk, and the deployment substrate (OneDrive/git) supplies none of the atomic create/rename/append they lean on. The fix is not to make OneDrive atomic (impossible) but to **remove the contended write-path from OneDrive entirely** and let the immutable dataset itself be the ultimate source of truth. With that plus four smaller mandated fixes, this is a certifiable pipeline.

---

## 1. The controlling ruling — single-writer by architecture, dataset-as-truth

Nikhil's category error is upheld. We do not defend it with a better lockfile. We remove the race:

- **Exactly ONE machine runs the ingester** (DESK-100 by standing assignment). Coordination state lives on that machine's **local disk**, where `rename`, `O_CREAT|O_EXCL`, `fsync`, and **SQLite in WAL mode** actually are atomic. No lease CAS, no `mkdir` lock, no append-race on OneDrive — those primitives are deleted from the design because the substrate can't honour them.
- **OneDrive/git carries only three things, none of them contended:** (a) the **immutable, content-addressed dataset outputs** (write-once — the writer is the only writer, so there is no concurrent-writer case to sync-conflict); (b) a periodically-snapshotted **read-only** copy of the ledger for the standby; (c) config + the version-pinned trading calendar.
- **The dataset directory is the true source of truth for "what is ingested."** The local SQLite is a *fast index*; the JSONL journal + OneDrive snapshot are for *audit + standby warm-start*. `doctor` can rebuild complete state by scanning `dataset/` and hashing files. This is the synthesis that makes even a botched two-writer episode self-heal: because every dataset file is content-addressed and write-once, two writers can only ever produce **identical bytes at identical paths** — idempotent by construction, never corruption, never divergence. Neither the draft (which relied on lockfile safety) nor the critique (which stopped at "single writer") stated this; it is the clean invariant.
- **Takeover = deliberate promotion, not a race.** A single small `writer_token` file on OneDrive (`{host, epoch, ttl}`) is claimed by an explicit `--promote` step when the primary is confirmed dead. Because handoff is deliberate and dataset writes are content-addressed write-once, the token does not need perfect atomicity — the residual "both alive, both claim" case degrades to duplicate harmless work, not corruption.

---

## 2. Adjudication of the red-team catches

| # | Catch | Ruling | Mechanism in final spec |
|---|---|---|---|
| Main | Safety proofs assume POSIX atomicity; substrate is OneDrive | **ACCEPT** | §1 single-writer, local SQLite-WAL, dataset-as-truth |
| S1 | Dead-man cron on the host it monitors can't fire when host dies | **ACCEPT** | **External** off-host heartbeat: writer pushes an "alive+complete" ping to a healthchecks.io-style dead-man / phone `PushNotification`; the *external* side pages on **absence** of ping by 22:45 IST |
| S2 | Calendar cross-check is circular — can't ask the exchange when blocked | **ACCEPT (refined)** | Cross-check is a *slow-loop opportunistic audit* that runs only on a successful fetch, **not** a real-time arbiter. Under a block we hold `PENDING`; the block path (S5/S6) owns it. Calendar is fetched from the NSE holiday/event API when reachable, git-version-pinned; missing/stale calendar = CRITICAL |
| S3 | Revised bhavcopy → silent stale data or destroyed audit trail | **ACCEPT** | **Content-versioned keys** `<date>|<product>|<sha256>`; a corrected file lands as a NEW version + a `supersedes` event; **never blind-overwrite**; catalog records which content-hash is *current*. This is a PIT/audit requirement — "which file did the backtest use" must be answerable forever |
| S4 | No ack-terminal → unbounded backlog, alert fatigue | **ACCEPT** | Human-ack terminal states `ACCEPTED_GAP` / `ABANDONED`; operator says "that day has no file, stop telling me"; bounds the re-attempt set |
| S5 | Deterministic proxy corruption misdiagnosed as "source corrupt"; NSE zips ship no checksum | **ACCEPT** | Discriminator is a **second network path** (home VPN / alternate endpoint), not a second same-path download. Quarantine alert reads "verify via alternate path before concluding source corruption." `Content-MD5` gate downgraded to *if-present*; **`zipfile.testzip()` CRC is the transport workhorse** |
| S6 | 403 conflates IP block vs expired cookie | **ACCEPT** | On 403: **re-warm cookies and retry once** before any block classification; escalate to IP-block cooldown only if the fresh-cookie retry also 403s |
| S7 | `business_date` timezone unspecified — firm landmine #1 | **ACCEPT** | `business_date` is computed **`Asia/Kolkata`-anchored**, explicitly, everywhere (keys and every publish-cutoff comparison) |
| S8 | Static 1k–6k row band contradicts 88→210 universe growth | **ACCEPT** | Rolling median of last N same-product files, ±X% band, per product |
| S9 | O(full-history) replay every run; unbounded logs | **ACCEPT** | Local SQLite-WAL *is* the materialized state (no full replay per run); JSONL is an audit journal, checkpoint-snapshotted; retention policy on `staging/`, `quarantine/`, `logs/` |
| S10 | Crash between rename and catalog append → file present, no catalog row | **ACCEPT** | `ingested` event + catalog row are one **local SQLite transaction**; the OneDrive `DATA_CATALOG.md` is a *projection generated from the DB*, not a separately-mutated file; `doctor` back-fills any gap |

**Rejected: none.** Every catch survives. Kept from the draft as genuinely correct and non-negotiable (Nikhil concurs): **zero-bytes-for-30s stall timeout vs total-transfer timeout** (the single most important download call), staging→verify→atomic-promote separation, calendar-as-arbiter for silent 404 suppression, the retry-taxonomy→action table.

---

## 3. Final persistent artifacts

```
# LOCAL DISK on the designated writer (real atomicity) — NOT on OneDrive
_ingest_local/
  state.sqlite (WAL)        # AUTHORITATIVE coordination state + catalog projection source
  staging/<date>/<product>/file.part   # in-flight, resumable
  staging/<date>/<product>/file        # completed raw bytes, pre-verify
  quarantine/<date>/<product>/...      # corrupt-suspect files, retained for forensics
  logs/ingest_YYYYMMDD.log             # verbatim per-run log

# OneDrive / git (immutable or read-only only — no contended writes)
dataset/<product>/<date>/<sha256>/<file>   # CANONICAL, content-addressed, WRITE-ONCE
config/ingest_config.yaml                  # sources, cutoffs, grace, retry budget, schema specs, thresholds
calendar/nse_trading_calendar.csv          # PIT, git-version-pinned, exchange-sourced
ledger/events.jsonl                        # append-only AUDIT journal (writer-only append, single writer → safe)
ledger/snapshot.sqlite                     # periodic READ-ONLY copy for standby warm-start
ledger/writer_token                        # {host, epoch, ttl} — deliberate handoff only
DATA_CATALOG.md                            # projection generated from state.sqlite (D-033)
```

## 4. State machine (content-versioned key `<date>|<product>|<sha256>`)

`PENDING → DOWNLOADING → DOWNLOADED_RAW → VERIFIED → INGESTED` (terminal success), with branches `FAILED_RETRYABLE` (backoff, `next_eligible_ts`), `MISSING_UPSTREAM` (past cutoff+grace, still 404), `QUARANTINED` (corrupt-suspect, alerts), `SKIPPED_HOLIDAY` (terminal no-op), and the two **human-ack terminals** `ACCEPTED_GAP` / `ABANDONED` (S4). A `supersedes` event links a corrected version to the one it replaces (S3).

## 5. Commit protocol (single-writer, local-transaction)

1. **Claim work unit** — a `SELECT ... WHERE state=PENDING` on the local DB (no lease CAS needed; single writer).
2. **Download** to `file.part` with HTTP `Range` resume; **abort only on 30s of zero bytes** (not total-transfer timeout — 0.7 MB/s legitimately takes minutes); sequential `requests.Session()` only, ≥1.2s/req, `truststore.inject_into_ssl()` first, cookie warm-up for `nsearchives`. `fsync`; atomic `rename .part→file` (same local volume). Record `bytes, sha256, http_status`.
3. **Verify** — the three gates in §6.
4. **Promote** — compute `dataset/<product>/<date>/<sha256>/`; if it already exists with matching hash → done (idempotent); else copy to `dataset/.tmp.<uuid>` (unique temp — the fixed `.tmp` name defect is fixed), `fsync`, atomic `rename` into the content-addressed path, `fsync` dir.
5. **Commit** — in ONE local SQLite transaction: write `ingested` event **and** upsert the catalog-projection row (S10). Append the same to `events.jsonl` (writer-only). Regenerate `DATA_CATALOG.md` from the DB. Snapshot to OneDrive on a timer.

**Recovery — `doctor` runs first on every start:** reconcile local DB against the actual `dataset/` files (dataset is truth); resume `DOWNLOADING` from `.part` via `Range`; re-verify `DOWNLOADED_RAW` (cheap, idempotent); for `VERIFIED`-not-`INGESTED`, if the content-addressed file exists+hashes → flip to `INGESTED` and back-fill the catalog row; spot-verify a sample of `INGESTED` hashes (skip files still syncing — check mtime-stable before hashing, so a mid-sync partial is not mistaken for canonical).

## 6. Corruption gates — nothing enters `dataset/` without passing all three

- **A — transport:** received bytes == `Content-Length`; **`zipfile.testzip()` CRC** (the real workhorse — NSE zips usually ship no checksum, so `Content-MD5`/sidecar is verified only *if present*, S5).
- **B — structure/schema:** unzip+parse; column set matches the product's expected schema via `lib/guards.py` (catches HF-1min vs bhavcopy-daily dual-schema mismatch); **row count within rolling-median ±band, per product** (not a static 1k–6k, S8); **date column == expected `business_date`** (Asia/Kolkata-anchored, S7 — catches a stale-cache/proxy serving yesterday's file).
- **C — content (firm landmines, D-009 sample check):** not mass-zero settles; **F&O `CONTRACTS>0` gating**; **never trust expiry-day option `SETTLE_PR`** (= underlying settlement, cost us −15,428 fake pts); spot-check 2–3 known values.

**Quarantine-vs-retry:** Layer-A fail → transport → retry. Layer-B/C fail → re-fetch **via the alternate network path** (home VPN/alt endpoint), not a second same-path download — two identical-wrong files from a deterministically-mangling proxy do NOT prove source corruption (S5). Only if the *alternate path* also fails → `QUARANTINED` + CRITICAL "inspect / update schema spec."

## 7. Download classification & alerts

| Signal | Class | Action |
|---|---|---|
| read/connect timeout, reset, 5xx, 429 | transient | `FAILED_RETRYABLE`, backoff `min(30m, 60s·2^(n-1))+jitter`; budget 8 attempts / ~6h |
| Content-Length mismatch / short read | transport | re-download |
| 404 **before** publish cutoff | not-yet-published | stay `PENDING`, poll silently, **no alert** |
| 404 **after** cutoff+grace | missing upstream | `MISSING_UPSTREAM`, alert once |
| **403** | cookie-expiry-first | **re-warm cookies + retry once**; only if that 403s → IP-block path (S6) |
| ≥3 consecutive 403 after cookie re-warm; 407/captcha/HTML-not-zip | IP block | pause ALL units 30–60 min cooldown; CRITICAL "switch to home network/VPN, run `--resume`" |

**Alert discipline:** healthy day = **zero pages** (or one WARN digest line). Per-unit `alert_state {none, open, acked, resolved}` dedups to one alert per incident; a later success emits one "resolved" note. WARN → batched into one end-of-run digest; CRITICAL → immediate push. Every alert is actionable: unit key, verbatim last error, attempt count, suspected cause, exact fix command. `ACCEPTED_GAP`/`ABANDONED` remove human-confirmed fileless days from the re-attempt set so the digest stops nagging (S4).

**Dead-man (external, S1):** the writer pushes an "alive+all-today-units-INGESTED" ping to an **off-host** dead-man service by 22:30 IST; the external side pages on **absence** of that ping by 22:45. A same-host watchdog cannot catch a dead host — this one can.

## 8. New-machine takeover mid-history

All durable state is portable: `dataset/` (content-addressed, self-describing), config, calendar, `events.jsonl`, `snapshot.sqlite` on OneDrive/git. A new box runs `doctor`, which **rebuilds full state by scanning `dataset/` file hashes** (dataset is truth) and warm-starts from the snapshot. Because the scheduler expands the calendar over *today + all still-open past units*, a multi-day outage self-heals on the next run. Handoff is **deliberate** (`--promote` claims the `writer_token`), never two live writers racing — and even a mistaken overlap is harmless because dataset writes are content-addressed write-once (identical bytes, identical path).

## 9. Scheduler

Cron on the single writer at **18:00 / 20:00 / 22:00 IST** (mirrors `AngelDailyOptionCapture`): `doctor` → expand calendar (today + open backlog) → process eligible units **sequentially, date-ordered** → digest + CRITICAL push. External dead-man checks completeness at 22:45. Extra runs are no-ops on completed work.

---

## Tail-risk assessment (CIO)

- **Worst single incident (silent hole):** a real missing day miscoded as trading, never fetched, nobody paged. Defended by external dead-man (S1) + git-pinned exchange-sourced calendar + opportunistic divergence audit (S2). Residual: a calendar error during a total-outage window — bounded, surfaces on next successful fetch.
- **Worst systemic (poisoned canonical):** a corrupt file reaching `dataset/` corrupts every downstream backtest — the highest-value failure. Defended in depth: three gates in staging + content-addressed write-once + mtime-stable hash checks + `doctor` rescan. A two-writer race cannot corrupt because bytes are identical by content-address.
- **Correlated blowup:** IP block across a multi-day critical fetch window (e.g. an expiry cluster). Defended by alternate-path remediation + backlog self-heal + explicit CRITICAL routing the human to the *right* fix (network, not exchange). This is exactly our documented NSE-proxy reality, now correctly diagnosed rather than misrouted.

## Requirement → mechanism traceability

| Requirement | Mechanism |
|---|---|
| Nothing lost across crashes | local SQLite-WAL state + append-only `events.jsonl` + calendar backlog re-expansion + `doctor` rebuild-from-dataset |
| Never double-ingested | content-addressed write-once dataset path + single-writer architecture; re-runs are no-ops |
| Corrupt never enters dataset | 3-layer gates in staging + alternate-path discriminator; only VERIFIED files atomically renamed (unique temp) into content-addressed canonical |
| Human alerted only when needed | per-unit dedup + auto-resolve, WARN-digest vs CRIT-push, calendar-aware 404 suppression, ack-terminals, **external** dead-man |
| New machine takes over mid-history | portable state, dataset-as-truth `doctor` rebuild, deliberate `writer_token` handoff, backlog self-heal |

## Kill criteria & review

- **Kill / halt-and-page** if: `doctor` finds a dataset file whose bytes ≠ its content-address path (integrity violation); calendar file missing or stale >2 trading days; external dead-man silent 2 consecutive days.
- **Review date:** re-audit after the first live month of running, and immediately after any incident where paper/backtest data is found stale or superseded (S3 path exercised).
- **Owner:** DESK-100 (ops-engineer Manoj Pillai) builds; data-officer Kavya Reddy owns catalog + D-009 gate; Red Team re-reviews before it feeds any Gate-4 backtest.

## Dissents recorded
None. Arjun (author) and Nikhil (red team) both concur with the single-writer / dataset-as-truth resolution; Nikhil's ten catches are adopted in full. This design is **APPROVED to build** as specified above.
