# QA Sweep — STOCK_SCORECARD_750 Universe Build, Batches 1-3 (Nifty-100)

Auditor: Ananya Iyer (Head of Equity Research). Date: 2026-07-20. Method: full-text read of all 30 `pf_qual_<SYM>.json` files against the 8-point checklist (verdict-rationale consistency, growth-band calibration, banned language, pending-vs-completed, summary quality, bear-case substance, escalation discipline, source hygiene), fanned out across 3 parallel sonnet subagents (10 files each) then spot-verified directly by me on the HIGH finding and two of the MED findings (DRREDDY escalation text, ADANIGREEN reverse-DCF vs growth number, ADANIENSOL/ADANIGREEN/ADANIPOWER escalation-flag cross-check). No file was edited; no re-research performed beyond targeted sanity web-searches on strong 2026 completion claims (Adani DOJ/SEC status, CG Semi Sanand OSAT start, BOB CEO tenure extension, Allianz-Bajaj stake buyback, HAL AMCA exclusion, DRREDDY Health Canada NOC) — all checked out accurate as stated.

**Summary: 30 files audited. 23 clean. 7 flagged (1 HIGH / 3 MED / 3 LOW), each in a different file — no file carried more than one issue.**

No Buy/Accumulate/target-price language and no chart/RSI/support-resistance talk found in any file's own voice (third-party analyst targets are quoted transparently as attributed external figures, not adopted house calls — CGPOWER borderline, see below). No fabricated sources or impossible dates found anywhere.

## Flagged rows

| Symbol | Check# | Severity | Issue |
|---|---|---|---|
| DRREDDY | 7 (Escalation discipline) | HIGH | recommendation_rationale itself says "Hold would be the defensible call" and "this is not a high-conviction structural Sell," flags Q1 FY27 (due in 3 days) as a swing factor with "essentially no visibility" — a self-described near coin-flip on the Sell/Hold axis — yet escalation_flag is false and escalation_reason is null. |
| ADANIENSOL | 7 (Escalation discipline) | MED | Escalated as a "genuine Hold-vs-Sell coin-flip" using the same "good execution, priced for perfection" logic that sister files ADANIGREEN and ADANIPOWER use — but those two reach a clean Sell with escalation_flag false, no coin-flip framing. Internally each file may be self-consistent, but the desk is not applying the escalation trigger uniformly across near-identical Adani-group setups. |
| ADANIGREEN | 2 (Growth-band calibration) | MED | expected_next_3y_growth_pct = 20 (exceptional band) sits inside the exact "high-teens-to-20s%" compounding rate that the file's own reverse_dcf_judgment argues the balance sheet (interest coverage ~1x, debt funding ~2.5x FY26 EBITDA of capex) "cannot comfortably clear" — no lower, analyst-derived achievable number is offered to reconcile the input against the bear thesis it feeds. |
| BANKBARODA | 5 (Summary quality) | MED | Summary paragraph leans on unexplained acronyms (PAT, GNPA/NNPA, QIP) that a lay client would not parse, where peer files in the same batch (CANBK, CHOLAFIN, COALINDIA) translate equivalent concepts into plain English. |
| DMART | 8 (Source hygiene) | LOW | The "first-ever NCD programme, Rs 1,000cr, approved 11-Jul-2026" claim — load-bearing for the bear point that DMart's debt-free narrative is stretched — has no matching citation in research_sources (independently web-verified as accurate, but undocumented). |
| CGPOWER | 3 (Banned language) | LOW | Third-party price targets (Nomura Rs 1,100, Ambit Rs 650) are quoted directly in negative_para rather than confined to reverse_dcf_judgment/sources; defensible as attributed external-analyst figures used for reverse-DCF triangulation rather than a house target, but borderline against house style. |
| CUMMINSIND | 5 (Summary quality) | LOW | Summary uses the unexplained regulatory acronym "CPCB IV+" without translating what the emission-norm change means for a lay client. |

## Clean files (23)
ADANIENT, ADANIPORTS, ADANIPOWER, AMBUJACEM, APOLLOHOSP, AXISBANK, BAJAJ-AUTO, BAJAJFINSV, BAJAJHLDNG, BPCL, BRITANNIA, CANBK, CHOLAFIN, COALINDIA, DLF, DIVISLAB, EICHERMOT, GODREJCP, GRASIM (escalation_flag=true correctly used for a genuine holdco-quant-methodology gap, not a disguised Sell/Hold coin-flip), HCLTECH, HDFCAMC, HDFCLIFE, HAL.
