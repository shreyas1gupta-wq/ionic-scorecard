
# FORWARD-CHECK vs REGISTER CROSS-CHECK — provenance audit piece 1 of N
**Owner:** Farhan Qureshi (Compliance) — part of the D-037 firm-wide provenance audit (due 2026-07-20)
**Scope:** `FINAL_STRATEGY_FORWARD_CHECK/` (legacy, read-only) vs `06_TRADING_DESK/STRATEGY_REGISTER.md` S-01..S-04
**Date of this check:** 2026-07-18

## URGENT — read this first

**S-03 (FF calendar) is a KILLED, money-losing strategy whose pre-correction rosy numbers are STILL sitting in the firm's live 258-trade execution sheet's auto-recommended "TRADE" block, alongside S-04 (Short strangle) — a PAPER-WATCH-ONLY strategy — dressed with real margin/lot sizing as if cleared for capital.** This is materially the same class of risk as tonight's S-05 finding (D-037): an unverified/superseded headline number "traveling further than its evidence" into something that looks decision-ready. **This needs to reach CIO/Principal before this sheet is acted on.** Detail in Verdict table + §3 below. [INFERENCE, from file-timestamp reconstruction — see evidence]

---

## 1. Identity check — are S-01..S-04 the same strategies as the FINAL_STRATEGY_FORWARD_CHECK four?

`FINAL_STRATEGY_FORWARD_CHECK/00_INDEX.docx` (converted via raw-XML text extraction, markitdown module unavailable in this environment — content verified directly from `word/document.xml`) states, verbatim:

> "Indian short-volatility option strategies | build 2021-2024, forward 2025-2026 | generated 2026-07-03"
> 01_FF_Calendar — Forward-Factor calendar (sell rich front CE / buy back CE)
> 02_Earnings_ShortVol — short ATM straddle through earnings (IV crush)
> 03_IVRV_ShortStraddle — short straddle when IV/RV >= 1.4
> 04_Short_Strangle — 5% OTM strangle, 14 DTE, managed at 50%

Matched against `STRATEGY_REGISTER.md` construction descriptions:
- **IVRV_ShortStraddle** ("short straddle when IV/RV>=1.4") = **S-01** ("IV/RV short straddle (IV/RV>=1.4, IV<100% cap)") — **[DATA] identical trigger condition, identical instrument.**
- **Earnings_ShortVol** ("short ATM straddle through earnings") = **S-02** ("Earnings short-vol (ATM straddle through print)") — **[DATA] identical.**
- **FF_Calendar** ("sell rich front CE / buy back CE") = **S-03** ("FF calendar single-CE") — **[DATA] identical (calendar CE spread).**
- **Short_Strangle** ("5% OTM strangle, 14 DTE, managed at 50%") = **S-04** ("Short strangle 14-DTE managed") — **[DATA] identical (14-DTE, managed exit).**

**Conclusion: all four are the SAME underlying strategies as S-01–S-04, not distinct constructions.** This is not a case of parallel/independent research — it is one build lineage that the register later re-audited and, in three of four cases, corrected downward or killed.

## 2. Timeline reconstruction (file mtimes, NTFS timestamps, `stat -c %y`)

This is the load-bearing evidence — it establishes whether FINAL_STRATEGY_FORWARD_CHECK predates or postdates each register correction.

| Artifact | Timestamp | What it is |
|---|---|---|
| `results/S-02/.../config.json`+`metrics.json` (Shreyas_Ionic_AMC/04_RND_LAB path) | **2026-07-03 21:12** | S-02 denominator-artifact discovery (register correction basis) |
| `FINAL_STRATEGY_FORWARD_CHECK/02_Earnings_ShortVol/*.docx` | 2026-07-04 02:54:39 | Forward-check doc (59% win, +21.6%/trade, "robust") |
| `results/S-01/20260703_validation/metrics.json` | 2026-07-03 20:45 | S-01 initial validation (pre the later correction) |
| `FINAL_STRATEGY_FORWARD_CHECK/03_IVRV_ShortStraddle/*.docx` | 2026-07-04 02:54:40 | Forward-check doc (90% win, +37.4%/trade) |
| `results/S-01/20260704_purgedcv_acceptance/verdict.md` | **2026-07-04 03:29:20** | S-01 SEND-BACK verdict (regime-beta inflation found) — **AFTER** the docx above |
| `FINAL_STRATEGY_FORWARD_CHECK/01_FF_Calendar/*.docx` | 2026-07-04 02:54:39 | Forward-check doc (69% win, +7.2%/trade, "fragile") |
| `results/S-03/20260704_shuffle/verdict.md` | **2026-07-04 03:24:05** | S-03 KILLED-PRE-IC verdict (3rd denominator artifact) — **AFTER** the docx above |
| `FINAL_STRATEGY_FORWARD_CHECK/04_Short_Strangle/*.docx` | 2026-07-04 02:54:40 | Forward-check doc (85% win, +0.17%/trade, "most robust") |
| `results/S-04/20260704_cost_cert/verdict.md` | 2026-07-04 03:15:26 | S-04 preliminary cost-cert (positive) — after the docx |
| `results/S-04/20260704_sensitivity/SENSITIVITY_REPORT.md` | 2026-07-04 22:24:37 | S-04 full Gate-4 sensitivity, completed same day, ~19.5h later |
| `FINAL_STRATEGY_FORWARD_CHECK/08_Execution/EXECUTION_SHEET_V2.md` (+`execution_scored.csv`,`execution_ALL.csv`) | **2026-07-04 03:46–03:55** | The 258-trade decision-ready sheet — built **AFTER** the S-01 SEND-BACK (03:29) and S-03 KILL (03:24) verdicts existed on disk |

**Reading:** the forward-check docs for all four strategies were generated in a single automated ~2-hour batch (02:54–04:40 on 2026-07-04), using the strategies' pre-correction/naive numbers. The corrections (S-02's denominator artifact, found the night before at 21:12; S-01's regime-beta inflation, found at 03:29; S-03's own denominator artifact, found at 03:24) landed on disk either before or during that same window — meaning the correction evidence already existed when the forward-check pack, and then the execution sheet 20-50 minutes later, were assembled. The rosy numbers were not "not yet known to be wrong" at build time for S-01/S-03 — the corrections were already sitting in `results/`.

## 3. Verdict per strategy

| Strategy | Verdict | Basis |
|---|---|---|
| **IVRV_ShortStraddle ↔ S-01** | **SAME-BUT-STALE, folder-only (contained)** | Forward-check doc (+37.4%/trade, 90% win) is the pre-correction number; register now carries +11.4pts incremental (SEND-BACK/FIREWALLED, no capital). **However**: checked `EXECUTION_SHEET_V2.md` for any "IVRV_ShortStraddle" row — **0 occurrences** across all three blocks (TRADE/DISCRETIONARY/BLOCKED). The stale number did NOT leak into the live execution artifact. Action: mark `03_IVRV_ShortStraddle/IVRV_ShortStraddle_Strategy.docx` and the portfolio combiner as SUPERSEDED-BY-REGISTER; no execution-sheet fix needed for this leg. |
| **Earnings_ShortVol ↔ S-02** | **SAME-BUT-STALE, execution sheet affected (moderate)** | Forward-check (+21.6%/trade, 59% win, "robust") vs register FAILS-PRE-IC (honest ~+9.7%/event, crush-incremental CI [+0.08,+9.6], **−10.1% vs calendar-matched unconditional short-vol**). Found **54 Earnings_ShortVol rows in `EXECUTION_SHEET_V2.md`, ALL in the ⚠️DISCRETIONARY tier (conviction 45-59)** — none in the auto-recommended ✅TRADE block, none BLOCKED either (checked TRADE-block rows 1-227 and BLOCKED-block head: zero Earnings_ShortVol matches in either). Lower severity than S-03/S-04 because discretionary framing already signals "human judgment required," but a strategy that FAILS-PRE-IC (not yet cleared by the Investment Committee at all) should not be feeding ANY tier of a decision-ready sheet. |
| **FF_Calendar ↔ S-03** | **SAME-BUT-STALE, execution sheet affected — URGENT** | Forward-check (+7.2%/trade, 69% win, tagged "fragile" even in its own rosy telling) vs register **KILLED PRE-IC 2026-07-04, forward −9.30 pts (loses money 2024 AND 2025), CIO resurrection review CLOSED 2026-07-05 STAYS-KILLED**. Found **37 FF_Calendar rows in `EXECUTION_SHEET_V2.md`, with entries in the ✅TRADE block itself** (e.g. rows #160 LTF, #168 PHOENIXLTD, #171 PRESTIGE, plus ~19 more further down the TRADE list), not merely discretionary/blocked. A strategy the CIO closed as **STAYS-KILLED** with a **negative** honest edge is sitting in the "go execute this" bucket of a sheet carrying real margin/lot-sizing math. |
| **Short_Strangle ↔ S-04** | **SAME, direction not contradicted, but STAGE-GATE bypassed — flag separately** | Forward-check (+0.17%/trade, 85% win, "most robust") is directionally consistent with the register's own certified read (+0.22%/spot managed, FULLY CERTIFIED 2026-07-04 → **PAPER-WATCH**, "PAPER MEASURES FIRST" before any capital, ₹1cr book cap under D-026, known fill-optimism/circuit-rule caveats). This is the one case where the *number* isn't obviously wrong — but the *stage* is: S-04 is explicitly paper-only pending fill verification, yet it supplies the bulk of the TRADE block (roughly 190 of the 209 rows) with real order tickets and a summed margin estimate (Rs.3,05,08,317) as if cleared for live sizing. This is a D-009/D-010 gate-integrity issue (my charter, not a numbers-provenance issue): the document format itself skips the paper-first gate regardless of whether S-04's edge holds up. |

## 4. Is the execution sheet itself live or stale?

`FINAL_STRATEGY_FORWARD_CHECK/08_Execution/EXECUTION_SHEET_V2.md` — built 2026-07-04 03:47, by its own header "Generated by Tanvi Desai (Product)... Product packages; Quant/Risk decided the numbers." It is dated internally to trade windows 2026-07-06 through 2026-08-07 (a ~5-week forward calendar). As of today (2026-07-18) most of its near-dated legs (FF_Calendar entries dated 07-06, first Short_Strangle wave dated 07-14) have already rolled past their stated entry dates without any corresponding register update, paper-ledger entry, or kill-note reconciling the sheet against the S-01/S-02/S-03 corrections that predate it. No evidence was found (checked `06_TRADING_DESK/` — no matching execution/fills file) that any of these 258 legs were actually sent to a broker; **Angel remains a data-only/fund-less account per firm hard rules, so this reads as a planning artifact, not a proof of live fills** — but it is formatted and titled as "Decision-Ready," which is exactly the "traveled further than its evidence" pattern D-037 called out.

## 5. Recommendation

1. **Immediate:** flag this file's §URGENT section to CIO (Rajan Mehta) and, per protocol, to the Principal — same class of finding as S-05 (D-037), i.e., a killed/firewalled strategy's stale numbers reachable from something that looks executable.
2. Mark all five `FINAL_STRATEGY_FORWARD_CHECK/*.docx` (four strategies + Portfolio_Overview) as **SUPERSEDED BY STRATEGY_REGISTER.md 2026-07-04 corrections** — do not edit the legacy folder itself (read-only), but the register/pipeline docs referencing it should carry a pointer note.
3. `EXECUTION_SHEET_V2.md` / `execution_scored.csv` / `execution_ALL.csv` should not be used for any real sizing decision until regenerated off S-01–S-04's CURRENT register verdicts (which would drop S-03 entirely, demote S-02 to no-go, and gate S-04 behind paper-first).
4. This is task 1 of the D-037 provenance audit; remaining scope (IDEA_PIPELINE, CURRENT_STATE, SESSION_JOURNAL headline sweep) still due 2026-07-20 per Kavya Reddy joint ownership.

**Tags:** [DATA] = verified against file contents/timestamps directly. [INFERENCE] = reasoned conclusion from DATA, not itself a stored fact (used once, in the URGENT banner, for the overall risk characterization).
