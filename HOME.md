# 🏠 Shreyas_Ionic_AMC — Firm Cockpit

> Open this note first. Everything below is a live link into the vault. (`Ctrl+O` quick-switch · `Ctrl+Shift+F` search · `Ctrl+P` command palette)

## 🗂️ Command Center

| Book | What it is |
|---|---|
| [[Shreyas_Ionic_AMC/01_COMMAND_CENTER/CURRENT_STATE\|CURRENT_STATE]] | Read-me-first state of the firm (updated every session end) |
| [[Shreyas_Ionic_AMC/01_COMMAND_CENTER/SESSION_JOURNAL\|SESSION_JOURNAL]] | Append-only sync log, both desks, newest on top |
| [[Shreyas_Ionic_AMC/01_COMMAND_CENTER/DECISIONS_LOG\|DECISIONS_LOG]] | Principal rulings (D-xx) |
| [[Shreyas_Ionic_AMC/01_COMMAND_CENTER/OPERATING_CALENDAR\|OPERATING_CALENDAR]] | Firm cadences (weekly meet, EOD, month-end) |
| [[Shreyas_Ionic_AMC/99_OPS/OPEN_ISSUES\|OPEN_ISSUES]] | Known breakages / follow-ups |
| [[Shreyas_Ionic_AMC/ORG_STRUCTURE\|ORG_STRUCTURE]] | Master map + file-placement rules |

## 🗃️ Databases (live views — click a tab inside each)

- **[[PORTFOLIO_BOOK|Portfolio book]]** — all 230 researched stocks as a filterable table (tabs: *Holdings by value · All Sells · Escalations · Full universe*). Every row opens the full analyst note (bull/bear case, reverse-DCF, sources).
- **[[Shreyas_Ionic_AMC/01_COMMAND_CENTER/decisions/D-023|Decision notes (D-001…D-039)]]** — every Principal ruling is now its own note in `01_COMMAND_CENTER/decisions/`. Open any D-xxx note → **backlinks pane → Unlinked mentions** shows every file where that ruling is invoked. The [[Shreyas_Ionic_AMC/01_COMMAND_CENTER/DECISIONS_LOG|DECISIONS_LOG]] ledger remains the record.
- **[[Shreyas_Ionic_AMC/01_COMMAND_CENTER/daily/2026-07-22|Daily notes]]** — the EOD routine appends a desk digest to each day's note (`01_COMMAND_CENTER/daily/`). Use the calendar/daily-note hotkey to flip through firm history.
- **Templates** (`templates/` — insert via `Ctrl+P` → "Insert template"): escalation-ruling · idea-one-pager · post-mortem.

## ⚖️ Escalations awaiting Principal — 36 open

**Work them on the board:** [[Shreyas_Ionic_AMC/01_COMMAND_CENTER/ESCALATIONS_BOARD|ESCALATIONS_BOARD]] (drag a card to *Ruled — Hold stands* or *Ruled — Sell / execute* as you decide; methodology cards go to Kavya/Arjun).
Full analyst texts: [[Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/ESCALATIONS_FOR_PRINCIPAL|ESCALATIONS_FOR_PRINCIPAL]] · summary CSV: `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/PORTFOLIO_QUAL_SUMMARY.csv`

## 📅 This week — Q1 FY27 prints sitting on knife-edge calls

- [ ] BANDHANBNK — printed 21-Jul → re-check the Hold (rally already priced the ROE recovery)
- [ ] DRREDDY — ~22-Jul → the Revlimid-cliff coin-flip swings on this print
- [ ] IDFCFIRSTB — 25-Jul → tests mgmt's mid-teens-ROE promise vs Street 9-12%
- [ ] SUMICHEM — 27-Jul → 55x into a weak-kharif quarter
- [ ] BEL — 27-Jul → margin trend vs ~50x
- [ ] BAJAJHFL — 29/30-Jul → coin-flip vs LICHF value gap
- [ ] MARUTI — 31-Jul → PBT-margin compression check
- [ ] ITC / VBL / TMPV (JLR) — next prints could flip their Holds

## 📚 Research shelf

- **Stock scorecard (750)**: [[Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/PROGRESS_PORTFOLIO_HOLDINGS|holdings progress/checkpoint]] · [[Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/MASTER_PLAN|MASTER_PLAN]] · full-750 quant: `results/full750_scored.csv`
- **ALPHA_RANKER**: [[ALPHA_RANKER/rnd/wave4/WAVE4_FINDINGS|WAVE4_FINDINGS]] · [[ALPHA_RANKER/rnd/wave4/RESEARCH_QUEUE|RESEARCH_QUEUE]]
- **Fund methodology 2036**: [[Shreyas_Ionic_AMC/04_RND_LAB/FUND_METHODOLOGY_2036/MASTER_ROADMAP_2036|MASTER_ROADMAP_2036]] (the "round-trip gap" = priority 1)
- **Trading desk**: [[Shreyas_Ionic_AMC/06_TRADING_DESK/STRATEGY_REGISTER|STRATEGY_REGISTER]] · [[Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS|COST_STANDARDS]] · [[Shreyas_Ionic_AMC/07_RISK_OFFICE/ADVERSARIAL_REVIEWS|ADVERSARIAL_REVIEWS]]
- **R&D pipeline**: [[Shreyas_Ionic_AMC/04_RND_LAB/IDEA_PIPELINE|IDEA_PIPELINE]] · [[Shreyas_Ionic_AMC/04_RND_LAB/KILLED_IDEAS|KILLED_IDEAS]]
- **Xorlog (venture)**: [[Xorlog/00_VISION_AND_PLAN|00_VISION_AND_PLAN]] · [[Xorlog/HANDOFF_DESK100|HANDOFF_DESK100]]
- **Legacy indexes**: [[RESUME_TOMORROW]] · [[HANDOFF]]

## 🔎 Recently touched firm files

![[FIRM_RECENT.base]]

## ⚡ Obsidian tips for this vault

- **Omnisearch** (`Ctrl+P` → Omnisearch) beats core search for fuzzy queries across the books.
- **Local graph** on any note (`Ctrl+P` → "local graph") shows what links here — useful on CURRENT_STATE.
- The escalations board is a **Kanban** — drag cards between columns; each card's `→ detail` link jumps to the full analyst text.
- ⚠️ Standing rules still apply inside Obsidian: legacy research folders are read-only; never trade off `EXECUTION_SHEET_V2.md` (see CURRENT_STATE urgent flags).

---
*Built 2026-07-22 by the desk. If folder structure changes, ask the desk to regenerate this cockpit.*
