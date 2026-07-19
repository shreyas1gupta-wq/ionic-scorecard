# 12 — R&D Reading List & Know-How Extraction (mine for alpha)

Brief Q20: extract know-hows from research papers, books, and AMC methodologies. For each, the execution session should produce a one-pager (claim → method → our-data replication path → verdict) via the firm's `reading-group` / `replicate-paper` skills, and route survivors into the factor library. **Extraction only — replicate on OUR PIT data before believing anything.**

## Academic factors (with the horizon they serve)
| Work | Edge | Serves |
|---|---|---|
| Jegadeesh–Titman (1993) | cross-sectional momentum (12-1) | 1M/1Y |
| Moskowitz–Ooi–Pedersen | time-series (absolute) momentum | 1M/1Y trend |
| Blitz et al. | **residual/idiosyncratic momentum** (beta/sector-neutral) | 1Y (cleaner) |
| Fama–French 3/5-factor | value, size, profitability, investment | 1Y/5Y |
| Piotroski (2000) | F-score fundamental strength within value | 1Y/5Y/microcap |
| Novy-Marx | gross profitability | 5Y quality |
| Asness–Frazzini–Pedersen — QMJ | **quality minus junk** | 5Y quality |
| Frazzini–Pedersen — BAB | betting against beta / low-vol | regime defense |
| Sloan (1996) | **accruals anomaly** (earnings quality) | forensic/quality |
| Bernard–Thomas | **post-earnings-announcement drift** | 1M catalyst |
| Chan–Jegadeesh–Lakonishok | **estimate-revision** momentum | 1Y (core) |
| Beneish | **M-score** manipulation detection | forensic |
| Cooper–Gulen–Schill | asset-growth anomaly (overinvestment) | 5Y/forensic |
| Baker–Wurgler | investor sentiment | regime/sentiment |
| Daniel–Hirshleifer–Sun | behavioral over/underreaction | cross-horizon theory |
| Harvey–Liu–Zhu — "…and the Cross-Section of Expected Returns" | **multiple-testing / DSR discipline** | validation (read FIRST) |
| López de Prado — *Advances in Financial ML* | purged CV, PBO, backtest hygiene | validation |

## Books (frameworks & forensics)
- Howard Schilit — *Financial Shenanigans* (the forensic bible → `08`).
- Pat Dorsey — *The Little Book That Builds Wealth* (moat taxonomy → 5Y).
- Joel Greenblatt — *Magic Formula* (ROC + earnings yield → 1Y/5Y baseline).
- Peter Lynch — *One Up on Wall Street* (categories, tenbaggers → microcap).
- William O'Neil — *CANSLIM* (momentum+earnings → 1M/1Y); Minervini — *Trade Like a Stock Market Wizard* (firm already uses → 1M base/VCP).
- Terry Smith — *Investing for Growth* (quality-compounder discipline → 5Y).
- Aswath Damodaran — *Narrative and Numbers* / valuation (reverse-DCF sanity → 5Y).
- Kahneman — *Thinking, Fast and Slow* (bias defense → red-team).

## AMC / practitioner methodologies (India-relevant)
- **Marcellus** (Saurabh Mukherjea) — Consistent Compounders, forensic screens ("Little Champs" = microcap), capital-allocation focus → 5Y & microcap.
- **Motilal Oswal — QGLP** (Quality-Growth-Longevity-Price) → clean 5Y template.
- **Nalanda / Pabrai** — low-risk quality at reasonable price, few bets → 5Y.
- **Fundsmith (Terry Smith)** — buy good companies, don't overpay, do nothing → 5Y.
- **AQR** — factor construction & combination, quality/momentum/value blending → weight book.
- **Buffett/Munger letters** — moats, management, capital allocation → qualitative rubric.
- India microcap forensic practitioners (Veritas-style short reports) — governance red-flag patterns → `08`/microcap.

## Extraction protocol
1. `reading-group` one-pager per item (claim/method/replication path).
2. Queue replications; run `replicate-paper` on our PIT data with pre-registered success criteria.
3. Survivors → factor library with an economic story; failures → `KILLED_IDEAS` with resurrection conditions.
4. Read the **multiple-testing / de Prado** material FIRST so the 1000-test program doesn't fool itself.
