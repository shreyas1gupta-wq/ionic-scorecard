---
name: transfer-in-review
description: Run the NDPMS transfer-in portfolio review whenever a client's CAS, Demat, CAMS, or Kfintech statement is provided — checks stocks against NIFTY 500, debt/InvIT against listed+rating>A+, MF/SIF against Direct-plan, and produces a Transfer Report (pre-approved list + exceptions routed to Yajash/Girdhar/RM). Use automatically the moment such a statement is uploaded/pasted/referenced — do not wait to be asked. Also invocable as /transfer-in-review <statement>.
---

# Transfer-In Review (NDPMS)

Checks an incoming client's existing holdings statement against the transfer-in
acceptance checklist and produces the **Transfer Report**: an immediate
pre-approved list (Stocks / MF & SIF / Bonds & InvIT) plus an exceptions list
with named routing.

This skill is **self-contained** — everything it needs ships in this folder.
It does not assume any particular repo layout, so it's safe to copy this whole
`transfer-in-review/` folder into anyone else's `.claude/skills/`.

**Engine:** `transfer_in_review.py` (same folder as this file).
**Reference data:** `reference/nifty500_current.json` (bundled NIFTY 500 list —
see its `as_of` field; NIFTY 500 membership changes twice a year, so re-request
a refreshed copy if it's more than ~6 months stale).

## Setup (one-time, per machine)

```
pip install python-docx openpyxl
pip install pymupdf     # only needed if you'll feed it raw PDF statements
```

## The checklist (exactly as specified — do not add or drop conditions)

| Instrument | Check | If it fails |
|---|---|---|
| Stocks | Is it in the current NIFTY 500? | Alert → **Yajash** to review and confirm |
| Debt & InvIT | Is the ISIN listed, and is the credit rating strictly better than A+ (i.e. AA- or above / A1+)? | Route to **Girdhar** to check |
| MF & SIF | Is the demat-mode (ISIN-based) holding on the Direct plan? | Note for **RM** — there is no ISIN→plan master bundled here, so this is always a manual confirm, not an automated pass |
| Stocks + MF/SIF (demat) | Has the RM confirmed purchase history? | Always required before transfer, independent of the checks above — never treated as done automatically |

**Plus a portfolio-level gate, separate from the per-instrument checks above:**
the transfer can proceed only if EACH family member's total value is
**> Rs 1 Cr** AND the combined family total is **> Rs 2.5 Cr** (floor, both
required). Below either threshold → the engine reports `CANNOT PROCESS
(below minimum)` regardless of how the individual holdings check out. This
needs a `family_member` column on the input — without it, the per-member half
of the gate can't be evaluated and the verdict comes back `UNKNOWN`.

## Steps

1. **Get the statement into a row-level holdings table.**
   - Preferred: a clean CSV/XLSX extract with columns `type`, `isin`, `name`,
     `units`, `value_inr`, and optionally `rating`, `plan`, `family_member`.
     This is the reliable path — use it whenever you can.
   - If only a raw CAS/CAMS/Kfintech PDF is available, the engine will
     heuristically extract rows via ISIN/line scanning (needs `pymupdf`).
     **This has not been validated against every statement format.** Every row
     it produces is tagged `extraction_confidence=low` and MUST be
     spot-checked against the source PDF pages before anyone acts on the
     report — say so explicitly when presenting results from a PDF input. Do
     not silently upgrade a guess to a fact.

2. **Run the engine:**
   ```
   python transfer_in_review.py --statement <file.pdf|csv|xlsx> --client "<Client Name>" --out <dir>
   ```
   Produces: `transfer_report.csv` (full row-level detail), `summary.json`
   (counts + routing tally), and `Transfer_Report_<client>.docx` (pre-approved
   tables by instrument type, an exceptions table with routed-to + reason, and
   an action-items section addressed to Yajash/Girdhar/RM by name).

3. **Present the summary in chat** (counts pre-approved vs exceptions, routing
   tally, and the family AUM gate verdict) and point to the docx/csv paths.
   Never claim a row is "cleared" if its `rm_purchase_history_confirmed`
   column is blank — that confirmation is RM's call, not this skill's. Lead
   with the family gate verdict — it decides whether the transfer proceeds at
   all, independent of the per-instrument exceptions.

4. **If the input was a raw PDF**, flag the low-confidence rows prominently
   and recommend re-running with a clean CSV/XLSX extract once one exists —
   that path is exact, the PDF path is a best-effort first pass.

## Epistemic conduct (non-negotiable — this touches real client transfers)

Never:
- invent a credit rating, "listed" status, or plan type that isn't actually on
  the statement — an unresolved check must fall to the human reviewer
  (Girdhar/RM), never default to "assume it passes".
- claim a PDF-derived number is exact — tag it low-confidence.
- silently drop a row that doesn't parse cleanly — it goes to Exceptions with
  a reason.

## Known limitations (flagged, not silently resolved)

- **Family-AUM gate scope** [ASSUMPTION]: the family total currently sums EVERY
  row in the statement (stocks + MF/SIF + debt/InvIT). If "family level" is
  meant to apply only to the sleeve actually moving into the PMS mandate
  rather than the client's whole existing portfolio, this reads too high —
  confirm the intended scope before relying on a borderline verdict.
- **One statement per run**: there's no multi-file input. If "family level"
  needs to combine several people's separate CAS/demat statements (realistic,
  since CAS is per-PAN), pre-merge them into one CSV with `family_member`
  filled in before running this — the engine does not do that merge for you.
- **`family_member` grouping is an exact string match**, not identity
  resolution — "Rakesh", "rakesh", and "Rakesh Gupta" would be treated as
  three different people. Keep the spelling consistent across rows.
- **No ISIN/name cross-check**: if a row has both and they disagree (e.g. a
  copy-paste error put the wrong name next to a real ISIN), the ISIN silently
  wins with no warning.
- **PDF path specifics** (beyond the general "low confidence" caveat): the
  name-guess heuristic assumes the name comes BEFORE the ISIN on the line —
  statement layouts that print ISIN first will produce garbage names. The
  units/value guess takes the LAST TWO numbers on the line, which breaks if a
  row prints more than two trailing numbers (e.g. avg cost + price + value).
  Duplicate ISINs (e.g. a CAS summary section repeating the detail section)
  are flagged, not deduplicated — a human still has to decide which to keep.

## Related

- Agent: `transfer-review-officer` (in `.claude/agents/`) runs this skill end
  to end and drafts the routing note — use it when you want a dedicated
  persona for this rather than running the script directly.
- `reference/nifty500_current.json` is the only external data dependency. To
  refresh it yourself: download the current NIFTY 500 constituent list (NSE
  publishes `ind_nifty500list.csv`) and rebuild the JSON with the same three
  fields (`isin`, `symbol`, `company`) plus an `as_of` date.
