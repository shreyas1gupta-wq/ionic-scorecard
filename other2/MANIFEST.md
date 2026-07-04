# other2/ — Root Declutter Manifest

Created 2026-07-05, DESK-100 (Manoj Pillai / Ops). Principal order: "everything in nifty 500
folder has got too messy, take what is necessary in ionic_amc folder and other arrange and
modify and save them as other2 folder and also if possible rename nifty 500 folder as
Shreyas_project_amc."

Scope executed here: the SAFE 90% (plain root declutter into `other2/`). The dangerous 10%
(root folder rename) is STAGED, NOT executed — see `Shreyas_Ionic_AMC/99_OPS/RENAME_RUNBOOK.md`
and `Shreyas_Ionic_AMC/99_OPS/migrate_root_rename.ps1`.

## Moved (6 items)

| Item | From | To | Git status | Why safe |
|---|---|---|---|---|
| `.venv/` | root | `other2/.venv/` | untracked (gitignored) | Full Python venv built against pythoncore-3.14-64. CLAUDE.md's canonical interpreter is the system install used directly — nothing activates this venv. Grepped every `.py`/`.json`/`.md`/`.ps1` in the repo for `.venv` — zero references anywhere. |
| `working/` | root | `other2/working/` | untracked (gitignored) | Contained one one-off diagnostic script (`check_public_sources.py` — tests yfinance/FRED/HF connectivity) plus a near-empty output file (`check`). No inbound references anywhere. Scratch dir. |
| `working101/` | root | `other2/working101/` | untracked (gitignored, empty) | Zero files inside. Nothing to lose. |
| `factor_navs (1).xlsx` | root | `other2/factor_navs (1).xlsx` | untracked (gitignored — matches the generic `*.xlsx` rule) | "(1)" duplicate-download artifact. Confirmed via `SESSION_JOURNAL.md` (2026-07-04 entry: "Principal unblocked D-M4... factor_navs.xlsx (22 official NAV series)...") and `results/factor_replication/20260704_factor_family/build_factor_family.py` (`NAV_PATH = ROOT/"datasets/index_daily/factor_navs_principal.parquet"`): the Principal's contributed data was already ingested into that parquet, which is what every factor-replication script actually reads. Zero code references the root xlsx by name. This is exactly the Principal's own example category: "superseded xlsx already converted to parquet." |
| `OPERATING_STANDARD_2026.md` | root | `other2/OPERATING_STANDARD_2026.md` | tracked (`git mv`, recorded as a rename) | Pre-firm-structure strategic planning doc (built 2026-06-16, same session as the `alpha_research` legacy track). Not on the Principal's explicit root keep-list. Content (Risk OS, vol-targeting, DD circuit-breakers, stress replays) is now the working domain of `07_RISK_OFFICE` + risk-manager-ritika-sharma; archived as source material, not deleted. |
| `PORTFOLIO_OF_EDGES.md` | root | `other2/PORTFOLIO_OF_EDGES.md` | tracked (`git mv`, recorded as a rename) | Same category (built 2026-06-16). The cross-asset / √N-diversification thesis now lives operationally in fm-equities-devika-menon's "defending the diversifier" mandate and FM allocation calls. Archived as source material. |

## Reference fix-ups made (nothing left silently dangling)

- `RESUME_TOMORROW.md` lines 8, 18, 170 — pointers to `OPERATING_STANDARD_2026.md` /
  `PORTFOLIO_OF_EDGES.md` updated to `other2/...` with a one-line "moved in 2026-07-05 reorg" note.
- `HANDOFF.md` lines 33-34 (top-level structure tree) and line 619 (a build-order action item) —
  same two filenames updated to `other2/...`.
- `HANDOFF.md` lines 2 and 30 (the literal root-path header, and the tree diagram's root label)
  were deliberately **not** touched here — they correctly describe the current, not-yet-renamed
  root path. They're carried as `DOC_REFERENCE` rows in
  `Shreyas_Ionic_AMC/99_OPS/HARDCODED_PATH_MANIFEST.csv` for the staged rename to fix later.

## Flagged for follow-up (not an ops-engineer judgment call)

`OPERATING_STANDARD_2026.md` and `PORTFOLIO_OF_EDGES.md` look superseded by the current firm
structure on inspection (dates, topic overlap with `07_RISK_OFFICE` / FM mandates), but this was
not a line-by-line content diff against `RISK_LIMITS.md` / `KNOWLEDGE_BASE` to certify nothing
unique was lost — that's a research-content judgment call, not a plumbing one. Recommend
rnd-head-aditya-verma or risk-manager-ritika-sharma skim `other2/` once and confirm, or pull
specific sections back into `07_RISK_OFFICE` if something load-bearing is missing.

## Refused to move (verified live/necessary — kept at root despite not being on the explicit list)

| Item | Why it stays |
|---|---|
| `logs/` | **Live** operational log sink, not clutter. `logs/2026-07-03/app.log` (4,654 bytes) contains real Angel SmartAPI `smartConnect` errors (`AB1021 Too many requests`, exact API key `8crMtPbu` from CLAUDE.md) dated through yesterday. Gitignored as "regenerable" but evidently still being appended to by live capture activity — moving it mid-session risks an open file handle or breaking tonight's write. |
| `stocks_data_cache.pkl` | **Cataloged source** — `DATA_CATALOG.md` row 71 ("stocks_data_cache", Principal-contributed 2026-07-04, feeds TRUE mcap weights + SIG-12 quality overlay). The order explicitly forbids moving anything DATA_CATALOG lists as a source. |
| `build_final_docs.py` | Active utility, not clutter — regenerates `FINAL_STRATEGY_FORWARD_CHECK/` (a kept root folder) from `intraday_options_strategy/buying`. It hardcodes the NIFTY 500 root path internally (line 19), so it's carried in the path-manifest CSV for the staged rename, but it stays at root today, co-located with its output. |
| `intraday_options_strategy/` | **LIVE PROCESS** — two python.exe PIDs (35872, 26528) confirmed via `Get-CimInstance` running `intraday_options_strategy/data/hf_stocks_opts.py` since 2026-06-30 18:00:2x. Hard constraint: do not move/rename anything under this tree while it runs. |
| 5 catalog xlsx (Master, Delisted, N200, N50N100 "Historical stock composition...", `NIFTY500_TICKER_2005_2025_Final.xlsx`) | Catalog-listed sources per `DATA_CATALOG.md` rows 31, 65-68 — never move. |
| `.claude/`, `.git/`, memory dir, `ShreyasIonicAMC_BACKUP` (outside repo), `angel_capture` (outside repo) | Explicit do-not-touch per the order. |
| `alpha_research/`, `swing_momentum/`, `datasets/`, `raw/`, `results/`, `FINAL_STRATEGY_FORWARD_CHECK/`, `Strategy_Results/`, `Shreyas_Ionic_AMC/`, `.gitignore`, `CLAUDE.md`, `RESUME_TOMORROW.md`, `HANDOFF.md` | On the Principal's explicit root keep-list; not evaluated for moving. |

Nothing else was found at root — no stray `__pycache__`, no `.tmp`/`.bak`/`Thumbs.db` junk. Checked
explicitly, not just assumed.

## Part B — "necessary strays not yet in Shreyas_Ionic_AMC" check

Searched for anything at root that looked necessary but wasn't yet represented in
`Shreyas_Ionic_AMC/`. Found none: everything at root that isn't a legacy folder or a catalog
source is either (a) one of the two superseded docs above, or (b) already fully mirrored by the
firm tree (`DATA_CATALOG.md` already documents every root xlsx/pkl by exact filename with a
`(root)` location tag). No copy-into-firm-tree action was needed.

## Part C — DATA_CATALOG / DATA_QUALITY_RULES updates

None required. No cataloged source's location changed — `stocks_data_cache.pkl` and all 5 xlsx
sources stayed exactly where `DATA_CATALOG.md` says they live.

## Root item count

Before: 29 items. After: 24 items (-6 moved out, +1 `other2/` created).

## Rollback (per item)

- Untracked items (`.venv`, `working`, `working101`, `factor_navs (1).xlsx`): plain reverse move,
  e.g. `Move-Item "other2\working" "..\working"`.
- Tracked items (`OPERATING_STANDARD_2026.md`, `PORTFOLIO_OF_EDGES.md`): `git mv
  other2/<name> <name>` (git recorded these as clean renames), then revert the 5 pointer edits in
  `RESUME_TOMORROW.md`/`HANDOFF.md` via `git checkout -- RESUME_TOMORROW.md HANDOFF.md` if not yet
  committed elsewhere.
