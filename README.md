# Ionic Wealth — NDPMS deck toolkit

Everything needed to turn a client's holdings into a branded NDPMS portfolio-review deck, **with our
scores already computed**. You do not need to re-run any scoring or fund research: the finished stock
scores and fund grades are committed to this repo.

> If you build a deck and the five-signal page shows **hollow grey rings** instead of coloured dots,
> stop — the score files were not found. Jump to [Troubleshooting](#troubleshooting). Nothing errors in
> that case; the deck builds perfectly with no data in it.

---

## 1. Setup, once

```bash
python -m pip install python-pptx matplotlib Pillow numpy openpyxl pandas pyarrow
```

On the Principal's machine the `python` alias is broken — use the full path:
`C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe`

Always set these two (the Windows console is cp1252 and will crash on the ₹ sign):

```bash
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
```

## 2. Build the demo deck — confirm your setup works before touching real data

```bash
cd Shreyas_Ionic_AMC/09_PRODUCT/pr_template
python build_abxy_showcase.py RM_SIMPLE
```

You should get `out/ABXY_Showcase_RM_SIMPLE.pptx`, 20 slides. Now prove the data joined:

```bash
python check_dots.py
```

It must print `PASS`. If it prints `FAIL`, the deck is a shell — see
[Troubleshooting](#troubleshooting).

## 3. Build a deck for a real client

```
holdings CSV/XLSX  ->  client_intake.py  ->  data/<client>.py  ->  build_<client>.py  ->  QA gates
```

1. **Holdings file.** Columns (case-insensitive): `type` (EQ/MF), `name`, `isin`, `units`,
   `value_inr`. **Always supply the ISIN** — it is the only exact join key. Without it, matching falls
   back to name-prefix guessing, which is banned as a silent default and will be flagged loudly.
2. **Intake:** `python 09_PRODUCT/scripts/client_intake.py <holdings> <profile.json> <out_dir>`
   Matched names get scores; unmatched rows go to `exceptions.csv` and are never dropped.
3. **Data module:** copy `pr_template/data/azby_family.py` to `data/<client>.py` and fill in the real
   numbers. That file is the schema reference.
4. **Build:** `python build_<client>.py HNI_DEEP` (or `STANDARD` / `RM_SIMPLE`).
5. **Gates — all of them, in order:**
   ```bash
   python check_geometry.py out/<deck>.pptx
   python check_geometry2.py out/<deck>.pptx
   python tellscan.py out/<deck>.pptx
   python check_dots.py
   python check_method.py data/<client>.py      # a DATA MODULE, not the .pptx
   ```
   Or run everything at once: `python 09_PRODUCT/scripts/audit_full_workflow.py`

## 4. Tiers

| Tier | Audience | Slides |
|---|---|---|
| `HNI_DEEP` | Family office / sophisticated HNI | ~67–103 |
| `STANDARD` | Typical NDPMS client | ~38–48 |
| `RM_SIMPLE` | RM-led / newer investor | ~20–30 |

---

## Where things are

| What | Path |
|---|---|
| **Deck engine + all slide modules** | `Shreyas_Ionic_AMC/09_PRODUCT/pr_template/` |
| **Five-signal logic — the single source of truth for bands and colours** | `pr_template/lib/five_signals.py` |
| **Stock scores, 751 names, final** | `04_RND_LAB/STOCK_SCORECARD_750/results/full750_scored_v3.csv` |
| **Fund grades, 181 funds (QFRA-1 + QFRA-2)** | `03_RESEARCH_DESK/MF_RECOMMENDATIONS/saved_2026-07-26/QFRA1_all_categories.csv` |
| **Symbol ↔ ISIN master, 2,404 NSE equities** | `05_DATA_OFFICE/data/isin_master.csv` |
| **How the scoring works, in plain language** | `09_PRODUCT/HOW_WE_SCORE_STOCKS.md` ← **start here** |
| **The frozen scoring spec + logged challenges** | `09_PRODUCT/FIVE_SIGNAL_AND_V3_SCORING_SPEC.md` |
| **Scoring correction layer (v3)** | `04_RND_LAB/STOCK_SCORECARD_750/fix_thin_coverage_v3.py` |
| **Full operating manual** | `.claude/skills/SG_NDPMS_TEMP1/SKILL.md` |

`results/full750_scored.csv` (no `_v3`) is **not** an obsolete duplicate — it is the engine output and
the input the v3 corrector reads. Both files must stay.

## The rules that are not negotiable

- **Sell or Hold only, never Buy.** This product reviews holdings the client already owns.
- **The call ladder is frozen:** below 40 → Sell. 40–50 → Hold, *eligible* for a trim if the position
  is over-concentrated or the analyst says so. Above 50 → Hold only. **There is no Sell above 50.**
- **Never fabricate a score.** An unscored name carries "No Recommendation" and a hollow ring. That is
  correct behaviour, not a defect — but check it is not *every* name (see below).
- **Never restate a threshold** in your own code or copy. Bands live in `five_signals.py`, scoring
  rules in `fix_thin_coverage_v3.py`. A duplicated number drifts within the hour.
- **No client PII in commits.** `pr_template/data/talaulikar_family.py` holds a real client's book.

---

## Troubleshooting

**The five-signal page is all hollow grey rings / every score reads "pending".**
The universe join found nothing. Nothing raises an error in this case — the page is structurally
perfect and only the data is absent. Diagnose from `pr_template/`:

```bash
python -c "import sys; sys.path.insert(0,'lib'); import five_signals as F; print(len(F.load_universe()))"
```

- Prints a number in the **hundreds** → the join works; hollow rings are genuinely unscored names.
- Prints **0** → the score files were not found. Confirm
  `04_RND_LAB/STOCK_SCORECARD_750/results/full750_scored_v3.csv` exists in your checkout. If you only
  received `SKILL.md` and not this repository, that is the cause — the skill file describes the
  pipeline but carries no data.

**Every client holding comes back unmatched.**
Supply ISINs in the holdings file, and check `05_DATA_OFFICE/data/isin_master.csv` exists. Rebuild it
with `python 05_DATA_OFFICE/scripts/build_isin_master.py` (fetches the NSE equity list).

**`check_method.py` throws `'NoneType' object has no attribute 'loader'`.**
You passed it a `.pptx`. It takes a **data module** (`data/<client>.py`).

**`tellscan.py` flags the word "genuine", or `SYNTHETIC_DEMO_LEAK` on the ABXY deck.**
Both are known-benign. ABXY *is* a demo, so the synthetic labelling is required there.
