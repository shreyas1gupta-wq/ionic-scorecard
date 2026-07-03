---
name: lookahead-audit
description: Mandatory D-028 lookahead-bias audit (T1-T10 taxonomy + programmatic battery + one-day-lag test) on a strategy/pipeline. Use for /lookahead-audit <strategy|script>, at Gate-4, and after any data-source change. Owner: Dr. Sameer Bhat.
---
# /lookahead-audit — owner: Dr. Sameer Bhat (overfit-analyst-sameer-bhat)
1. Read `Shreyas_Ionic_AMC/07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` (the T1-T10 taxonomy) and the target's code + run dir.
2. Run the programmatic battery: `Shreyas_Ionic_AMC/04_RND_LAB/lib/lookahead_audit.py` (audit_code on every source file; the frame-level checks on the panel/trades; audit_oos_log from the family trials ledger).
3. Walk T1-T10 MANUALLY against the code (the machine catches patterns; you catch intent). Run the one-day-lag test if a positive edge is claimed; terminal-date shuffle on >=20 decision dates for anything suspicious.
4. Verdict PASS / PASS-WITH-FLAGS / FAIL -> `results/<strategy>/<run>/LOOKAHEAD_AUDIT.md`, signed. FAIL = result quarantined (unquotable in register/memo/letter) + journal line + Ritika notified.
5. Gate-4 blocks without this report (RESEARCH_SOP). Loosening any of this = Principal only (RISK_LIMITS §Process risk).
