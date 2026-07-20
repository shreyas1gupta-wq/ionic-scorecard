# V0 ARCHIVE - frozen track record (2026-07-20)

**Do not edit.** This is the immutable snapshot of every STOCK_SCORECARD recommendation made under
the V0 methodology (full-discretion analyst override in BOTH directions + full fund-manager judgment
pass). V0 is retired from production as of 2026-07-20; V1 (asymmetric override, weekly incremental)
supersedes it. This archive exists so the V0 calls can be scored for hindsight accuracy later
(performance attribution: how did our Sell/Trim/Hold calls actually do?).

Contents:
- pf_qual/  : 125 per-stock research files (59 real client holdings + 66 Nifty-100 coverage).
- pf_mech_flags.json / pf_fm_actions.json : the client-layer scores + FM Trim actions for the 59-book.
- portfolio_quant.csv / n100_quant_scored.csv : the quant score layer.
- CLIENT_RECOMMENDATIONS_V0.xlsx / ANALYST_RECOMMENDATIONS_V0.xlsx : the shipped workbooks.
- summaries + escalations as of the archive date.

To score this track record in future: take each stock's your_recommendation + ionic_score here,
measure forward return from 2026-07-20 vs Nifty 500, and compute hit-rate / decile spread by cohort.
