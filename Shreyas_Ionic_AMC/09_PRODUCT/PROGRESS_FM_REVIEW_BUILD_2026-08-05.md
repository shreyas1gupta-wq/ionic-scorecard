# FM review build — checkpoint (Tanvi Desai, Product)
**Goal:** implement the unblocked FM comments (#2,6,7,8,9,10,11,12,19,21,22,25) from
`09_PRODUCT/FM_REVIEW_REPLY_2026-08-05.md`, per the sell-method spec and ACE verification docs.
Rebuild `build_pac_showcase.py` + `build_abxy_showcase.py`, pass all 5 QA gates on both.
Do NOT touch the scoring model (STOCK_SCORECARD_750 / QFRA engines).

## Key findings before editing (read carefully before resuming)
- `check_method.py` (QA gate 5) and `lib/acemf.py` are ALREADY COMMITTED (a032743, 9e387c0) —
  built in a prior session, ahead of this one. check_method.py already defines the EXACT field
  contract: `sell_priority`, `sell_reason_type`, `exceptional_override` (equity); `bought_pre_apr_2023`,
  `structural_reason`, `action`/`verdict` (funds); `holding_years` (both). Baseline run on
  UNMODIFIED azby_family.py: **2 findings** — (a) HINDCOPPER quality SELL at score 47.6, no
  `exceptional_override` set (pre-existing gap, equity ctx layer, NOT one of my 12 items — fixing
  it only adds the missing evidence flag that sell_list.py already visually implies via its
  EXCEPTIONAL chip at the same >=40 threshold; equity SCORE/REC untouched); (b) churn 22.03% (11
  equity Sells) > 20%, no `sell_priority` anywhere — this IS #25, mine to fix.
- ABXY funds are 100% fictional (no real ISIN) — cannot join to the real ACE Excel row-for-row.
  Decision: extend the synthetic generator in `data/azby_family.py` with ACE-SHAPED fields
  (equity_gross_pct, sector_alloc, ytm/duration/expense/rating for debt-bearing categories,
  purchase_date), using real medians from `05_DATA_OFFICE/ACEMF_VERIFICATION_2026-08-05.md` where
  a real number exists (e.g. Balanced Advantage equity% median 70.1), clearly still `is_demo`.
  Mirrors real ACE field names/semantics 1:1 so a future real-client wire-up is a drop-in.
- Section-restructure (#11) requires renumbering: content pages hardcode `deck.content(sec_no, ...)`
  as a literal int per module (not derived) -> renumbering Fund Book 3->2 / Equity Book 2->3 means
  editing the literal in ~10 module files, plus engine.py's MODULES/DIVIDER_TOC/titles and
  contents_legend.py's _SECTIONS list. Full file list below.

## Plan / file list
- [ ] `lib/lookthrough.py` (NEW): lookthrough_mix (moved from ips_summary, re-exported), equity_gross_lookthrough,
      combined_sector_exposure, amc_concentration, scheme_concentration (stocks+funds together).
- [ ] `lib/mf_sell_gates.py` (NEW): purchase-date derivation (graceful None), debt-grandfather gate
      (force Hold unless structural_reason override), sell_priority assignment (STCG->low, else high
      pending FM's Layer-2 cutoffs — documented as the honest placeholder), churn_pct.
- [ ] `data/azby_family.py`: add ACE-shaped fund fields + 2 new debt funds (YTM present / absent,
      one pre-2023 gated, one recent-STCG) + call the new gates at ctx build; equity: add
      `exceptional_override` (evidenced, mirrors sell_list.py's existing >=40 EXCEPTIONAL chip).
- [ ] `modules/snapshot.py`: #6 add allocation (look-through equity/hybrid-debt/cash) panel.
- [ ] `engine.py`: #7 retire allocation_house_view (core False, drop DIVIDER_TOC[1] entry);
      #11 reorder MODULES (Fund Book block before Equity Book block) + renumber sec_no 2<->3,
      DIVIDER_TOC keys, titles dict in build(); register new modules mf_methodology, funds_debt.
- [ ] `tiers.py`: RM_SIMPLE skip_core cleanup + new module skip entries.
- [ ] `modules/contents_legend.py`: swap _SECTIONS 02/03.
- [ ] Sec_no literal swap (2->3): book_scored.py, sell_list.py, hold_rationale.py, score_method.py,
      equity_book.py. Sec_no literal swap (3->2): fund_book_scored.py, funds_equity.py,
      funds_hybrid.py, fund_actions.py, scheme_overlap_full.py.
- [ ] `modules/mf_methodology.py` (NEW): #12.
- [ ] `modules/funds_debt.py` (NEW): #22, graceful YTM-gap display.
- [ ] `modules/concentration_risk.py`: #9 scheme(incl funds)/AMC/look-through-sector + #8 calc-base.
- [ ] `modules/sector_exposure.py`: #10 combined sector exposure, replace "not looked through" caveat.
- [ ] `modules/fund_book_scored.py`: #25 Priority column + subhead segregation when churn>20%.
- [ ] `modules/allocation_house_view.py`: leave file as-is (unwired only, per "no orphan" instruction).
- [ ] Rebuild both decks, run check_geometry/check_geometry2/tellscan/check_method/check_freshness,
      grep build log for `[ERR ]`, convert to PDF, visually read.

## Status: DONE (2026-08-06)
All checklist items built and verified. Both decks pass check_geometry/check_geometry2/check_method
at 0 findings; tellscan and check_freshness findings are pre-existing/expected (see
CURRENT_STATE.md + SESSION_JOURNAL.md 2026-08-06 entries for the full breakdown). Visual PDF read
caught and fixed 3 real bugs the automated gates missed (snapshot.py label collision,
fund_book_scored.py flag-chip overlap, funds_debt.py expense-ratio x100 error). Nothing committed
to git (not requested). This file kept as the permanent build record; no further action pending
from this task.
