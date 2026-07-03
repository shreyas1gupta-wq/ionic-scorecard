# MACRO & EVENTS CALENDAR — owner: Cyrus Daruwalla (E-021, Macro Strategist)
First issued 2026-07-04 (Tanvi catch #4 — the sheet referenced a calendar that didn't exist).
**Refresh cadence:** weekly (Monday), plus same-day on any surprise announcement.
**Honesty rule:** dates below are from the standing annual rhythm of each institution, NOT a live
feed (office proxy blocks most calendar APIs). Anything not exchange-confirmed is marked (est.).
Verify RBI/Fed dates against official sites on a home-network day before sizing around them.

## How the desks use this
- **Event-window vol rule:** no NEW short-vol entries T-1 → T+0 around RED events (RBI, Fed, budget-class fiscal events, index rebalance days for affected names). Existing positions: size unchanged, hedge review at T-2.
- **Earnings season:** single-stock short-vol (when any is live again) must check the name's own result date FIRST — that dominates every macro row here.
- Sheet integration: execution_scanner flags legs whose expiry window straddles a RED event.

## July 2026
| Date | Event | Sev | Desk note |
|---|---|---|---|
| Jul-06 (Mon) | Weekly refresh due (this file) | — | Cyrus |
| Jul-07..10 (est.) | TCS kicks off Q1-FY27 IT earnings week | AMBER | IT names IV bid; Karan covers |
| Jul-14 (est.) | India CPI (Jun) ~17:30 IST | AMBER | Prints after cash close; gap risk next open |
| Jul-15 (est.) | China Q2 GDP | AMBER | Metals/HINDALCO sensitivity |
| Jul-28..29 | US FOMC (est. — verify) | RED | No new short-vol T-1→T+0; USDINR watch |
| Jul-28 (Tue, est.) | NIFTY monthly expiry week begins | AMBER | Roll congestion; strangle exits per rule not expiry-day panic |
| Jul-31 | **Firm board meeting + investor letter #1** | — | CEO pack; Tanvi letter |
| All month | Q1-FY27 earnings season (peak mid-Jul → mid-Aug) | AMBER | Names on the sheet with results inside holding window get flagged |

## August 2026
| Date | Event | Sev | Desk note |
|---|---|---|---|
| Aug-04..06 (est.) | RBI MPC (bi-monthly rhythm) | RED | Banks/NBFC vol; no new short-vol T-1→T+0 |
| Aug-12 (est.) | India CPI (Jul) | AMBER | |
| Aug-15 (Sat) | Independence Day (market holiday falls on weekend — no session lost) | — | |
| Aug-25 (Tue) | 25AUG single-stock option expiry (our earnings back-legs) | AMBER | 8 backfilled PE legs expire |
| Aug-27 (est.) | US Jackson Hole window | AMBER | Fed-speak vol |

## Standing annual rhythm (for planning, all est. until confirmed)
- RBI MPC: bi-monthly — Aug, Oct, Dec, Feb, Apr, Jun.
- FOMC: 8 meetings/yr — next after Jul: Sep, Oct/Nov, Dec.
- Union Budget: Feb-01. Advance-tax outflow quarters: Jun/Sep/Dec/Mar 15th.
- NSE index rebalance: semi-annual review effective late Mar + late Sep (factor indices quarterly for some — matters for D-M4 replication).
- F&O expiry: monthly last-Tuesday regime (verify current exchange circular — expiry-day rules changed twice in 2025).

## Regime read (as of 2026-07-04) — Cyrus
- VIX series on disk (2016→): current level vs history to be computed by /macro-calendar refreshes (india_vix.parquet is live in `datasets/index_daily/`).
- Open risk: US tariff policy headlines remain the dominant un-calendarable gap source for IT/pharma exporters — treat every US trade announcement as an unscheduled AMBER.

## Changelog
- 2026-07-04: first issue (Cyrus). Sources: institutional annual rhythms; NOT yet exchange-verified (proxy). Home-net verification queued.
