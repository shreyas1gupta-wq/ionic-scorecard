---
name: transfer-in-review
description: Run the NDPMS transfer-in portfolio review whenever a client's CAS, Demat, CAMS, or Kfintech statement is provided — checks stocks against NIFTY 500, debt/InvIT against listed+rating>A+, MF/SIF against Direct-plan, and produces a Transfer Report (pre-approved list + exceptions routed to Yajash/Girdhar/RM). Use automatically the moment such a statement is uploaded/pasted/referenced — do not wait to be asked. Also invocable as /transfer-in-review <statement>.
---

# Transfer-In Review (NDPMS, Ionic Wealth)

Checks an incoming client's existing holdings statement against the transfer-in
acceptance checklist and produces the **Transfer Report**: an immediate
pre-approved list (Stocks / MF & SIF / Bonds & InvIT) plus an exceptions list
with named routing, so the desk can act without re-deriving the rules each time.

**Owner of the underlying rules:** RM (checklist given 2026-07-27). **Engine:**
`Shreyas_Ionic_AMC/09_PRODUCT/scripts/transfer_in_review.py`.

## The checklist (exactly as specified — do not add or drop conditions)

| Instrument | Check | If it fails |
|---|---|---|
| Stocks | Is it in the current NIFTY 500? | Alert → **Yajash** to review and confirm |
| Debt & InvIT | Is the ISIN listed, and is the credit rating strictly better than A+ (i.e. AA- or above / A1+)? | Route to **Girdhar** to check |
| MF & SIF | Is the demat-mode (ISIN-based) holding on the Direct plan? | Note for **RM** — no ISIN→plan master exists in this repo yet, so this is always a manual confirm, not an automated pass |
| Stocks + MF/SIF (demat) | Has the RM confirmed purchase history? | Always required before transfer, independent of the checks above — never treated as done automatically |

There is **no family-AUM threshold gate** in this workflow (Principal/RM instruction
2026-07-27: drop that rule — do not resurrect a >1Cr/>2.5Cr check unless explicitly
asked again).

## Steps

1. **Get the statement into a row-level holdings table.**
   - If the RM/ops already has a clean CSV/XLSX extract (columns: `type`, `isin`,
     `name`, `units`, `value_inr`, optionally `rating`, `plan`, `family_member`) —
     use it directly. This is the reliable path.
   - If only a raw CAS/CAMS/Kfintech PDF is available, the engine will
     heuristically extract rows via ISIN/line scanning (PyMuPDF). **This has never
     been validated against a real sample statement.** Every row it produces is
     tagged `extraction_confidence=low` and MUST be spot-checked against the
     source PDF pages before anyone acts on the report — say so explicitly when
     presenting results from a PDF input. Do not silently upgrade a guess to a fact.

2. **Run the engine:**
   ```
   python Shreyas_Ionic_AMC/09_PRODUCT/scripts/transfer_in_review.py \
     --statement <file.pdf|csv|xlsx> --client "<Client Name>" --out <dir>
   ```
   Default `--out` is `Shreyas_Ionic_AMC/09_PRODUCT/reports/transfer_reviews/<client>_<date>/`.
   Produces: `transfer_report.csv` (full row-level detail), `summary.json` (counts +
   routing tally), and `Transfer_Report_<client>.docx` (house-styled, via
   `docx_style_kit.py` — pre-approved tables by instrument type, an exceptions
   table with routed-to + reason, and an action-items section addressed to
   Yajash/Girdhar/RM by name).

3. **Present the summary in chat** (counts pre-approved vs exceptions, routing
   tally) and point to the docx/csv paths. Never claim a row is "cleared" if its
   `rm_purchase_history_confirmed` column is blank — that confirmation is RM's
   call, not this skill's.

4. **If the input was a raw PDF**, flag the low-confidence rows prominently and
   recommend the RM re-run with a clean CSV/XLSX extract once one exists — that
   path is exact, the PDF path is a best-effort first pass.

## Epistemic conduct (D-035 class — non-negotiable here)

This touches real client transfers. Never:
- invent a credit rating, "listed" status, or plan type that isn't actually on
  the statement — an unresolved check must fall to the human reviewer (Girdhar/
  RM), never default to "assume it passes".
- claim a PDF-derived number is exact — tag it `[low confidence]`.
- silently drop a row that doesn't parse cleanly — it goes to Exceptions with a
  reason, same convention as `client_intake.py`'s exceptions.csv.

## Related

- `client_intake.py` (NDPMS deck intake) is a sibling script with the same
  "never silently drop a row" convention — read its docstring if you need the
  deck-building side of holdings intake instead of the transfer-in checklist.
- `mf_lookthrough.py` (`05_DATA_OFFICE/scripts/`) has the closest existing
  rating-parsing precedent in this repo (fund-disclosure ISIN→rating), though it
  works off a different data source (AMC monthly disclosures, not a statement).
- Agent: `.claude/agents/transfer-review-officer.md` runs this skill end to end
  and drafts the routing note.
- To circulate the process itself (not a specific client's report) by email, see
  `Shreyas_Ionic_AMC/09_PRODUCT/reports/Transfer_In_Review_SOP.docx`, built by
  `Shreyas_Ionic_AMC/09_PRODUCT/scripts/build_transfer_review_sop.py`.
