# BACKUP POLICY (Data Officer executes; D-015)

## Layers
1. **OneDrive** (continuous): the entire root folder is corporate-OneDrive synced — survives laptop loss. This is also the two-desk sync medium; do not move the folder.
2. **Git** (command layer): every session ends with a commit (code + firm docs; data excluded). History = point-in-time recovery of all decisions/prompts/agents. Local-only; any future remote requires secret-scrub first (HF token is hardcoded in some legacy `data/hf_*.py` — scrub before ANY push) (D-003).
3. **Data snapshots** (weekly, manual until scripted): zip the CRITICAL derived sets (earnings_pit, derived/, buying/*.parquet strategy outputs, angel_capture_2026) → `D:\` or external if available; else a dated `datasets/_snapshots/` folder. Raw HF dumps are re-downloadable (documented in DATA_CATALOG) — do not duplicate 28GB.
4. **Credentials**: creds.json + angel_cfg live OUTSIDE the repo (`AppData\Local\angel_capture\`) by design. They are NOT backed up to OneDrive-visible paths; Principal holds the originals.

## Restore drill (quarterly)
Pick one parquet from each critical family; verify it opens + row count matches catalog. Log the drill in the journal.
