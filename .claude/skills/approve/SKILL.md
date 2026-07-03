---
name: approve
description: Principal-approval workflow (D-020) — promote a prompt/standard from draft to approved and log the decision. Use when the Principal says "approve P-xx / RP-xx / COST_STANDARDS / RISK_LIMITS" or similar explicit sign-off language.
---

# /approve — Principal sign-off workflow (D-020)

1. **D-025 flow (2026-07-04):** route the item to ceo-meher-kapadia AND cio-rajan-mehta for JOINT review — both must approve (each: APPROVE/REJECT + one-line reason, logged). Split verdict → Principal tie-break. LIVE-capital + RISK_LIMITS-loosening still need the Principal directly. Legacy path (explicit Principal message naming the item) still valid (e.g. "approve RP-08", "approve COST_STANDARDS"). Never move/strip anything speculatively or because it "seems ready" — no message, no action.
2. For a prompt (P-xx/RP-xx): move (not copy) the file from `Shreyas_Ionic_AMC/02_PROMPT_LIBRARY/drafts/` to `02_PROMPT_LIBRARY/approved/`, creating `approved/` if it doesn't exist yet.
3. For a standards file (`06_TRADING_DESK/COST_STANDARDS.md`, `07_RISK_OFFICE/RISK_LIMITS.md`): edit in place — remove the `> **STATUS: DRAFT...**` banner line, replace with an `> **STATUS: APPROVED** (D-###, YYYY-MM-DD)` line.
4. Record a new row in `01_COMMAND_CENTER/DECISIONS_LOG.md` (next sequential D-###, today's date, decision text quoting the Principal's exact approval words).
5. Append one journal line (what was approved, files touched). Cheap tier — this is mechanical filing, not judgment.
