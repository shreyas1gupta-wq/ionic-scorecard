# FROZEN SPEC -- ALPHA_RANKER canonical 7-leg composite, forward-test protocol
Owner: Arjun Rao (Head of Quant, E-004). Frozen: 2026-07-17. Status: PRE-REGISTERED, evaluate ONCE, NOT YET GRADED.

## 0. Why this document exists
`rnd/FINAL_MODEL.md` S5-RISKOFFICE is explicit: after 456 logged trials across the ALPHA_RANKER
research program, in-sample validation CANNOT certify this composite. Deflated Sharpe (DSR) is
~0 and CSCV-PBO is ~0.92 on BOTH the biased and the survivorship-PIT-corrected universe. This is
a multiple-testing problem, not a construction defect -- more sensitivity batteries, more
perturbation tests, more re-runs make deflation WORSE, never better, because every additional
look adds a trial. The **only** remedy that escapes multiple-testing is a genuinely fresh,
calendar-time, held-out test: freeze the model, bank its predictions, wait, and grade exactly
once against returns that did not exist when the freeze happened. That is the entire purpose of
this tracker. It is not a workaround for the DSR/PBO failure -- it is the one gate compute cannot
close on its own.

## 1. What is frozen (tamper-evident)
- **Source file**: `rnd/lib/composite_final.py`
- **Content hash (sha256, NOT a git commit)**: `9fbfe8d4f62395f7a67efe307cc9025646524e837eaaa3665aa1576e758661cb`
  -- computed by `rnd/lib/forward_test_tracker.py::content_hash()`, recorded verbatim in
  `rnd/forward_test/freeze_manifest.json`. Any future edit to `composite_final.py` (including
  whitespace) changes this hash. Before trusting any grading pass against the banked scores below,
  re-run `content_hash()` on the file at that time and confirm it still matches -- a mismatch means
  the "frozen" spec was edited after freeze and the forward test is void.
- **No git commit was made for this freeze** (explicit task instruction) -- the hash is the
  tamper-evidence mechanism, not version control.

## 2. Exact leg list (7, unchanged from FINAL_MODEL.md S1-S2)
`value_EY`, `mom_resid_plain`, `trend_ma65_slope`, `quality_QMJ`, `bs_issuance`,
`bs_asset_growth`, `quality_cfo_pat`.

## 3. Exact construction (unchanged from `composite_final.py`, imported not re-implemented)
1. **Weighting**: equal-weight rank-average -- `rank_pct` per date per leg, then mean across
   whichever legs are present for that (date, symbol). Zero fitted parameters.
2. **min_legs = 5-of-7** required to emit a composite value for a (date, symbol). A name with
   fewer than 5 of the 7 legs present is NOT scored as "the 7-leg composite" (this is the
   min_legs=5-vs-2 distinction that previously caused two rebuilds to disagree -- see
   `composite_final.py` module docstring; 5-of-7 is canonical).
3. **Universe**: `panel_long.parquet` as-is (PIT survivorship-controlled fundamentals+price
   panel). No additional ADV/price screen.
4. **Corporate-action guard**: applied to the historical forward-return TARGET during backtesting
   (disc_event_in_window_1Y>0 rows NaN'd) -- not applicable to today's live scoring since no
   forward target exists yet for the current cross-section; recorded for completeness.
5. **Portfolio construction**: decile (10-bin), harness default, unchanged.
6. **Score map**: `score = 200*(rank_pct(composite) - 0.5)` in `[-100, +100]`. Zero fitted params.

Full detail: `rnd/forward_test/freeze_manifest.json`.

## 4. What was banked (today's predictions)
- **File**: `rnd/forward_test/scores_asof_20251205.parquet`
- **As-of date**: 2025-12-05 -- this is the LATEST date at which the underlying
  fundamentals+price panel (`panel_long.parquet`) actually has data, NOT the calendar date this
  freeze was executed (2026-07-17). **This ~7-month PIT lag is disclosed, not hidden** -- it is a
  property of the fundamentals data source (screener-derived, quarterly-lag publication), not a
  construction choice. Any grading pass must account for this: the true elapsed forward window
  from 2025-12-05 to the grading date is shorter than "time since freeze" by that lag.
- **Columns**: `date`, `symbol`, `subscore_<leg>` (7 columns, each `200*(rank_pct-0.5)` per leg),
  `composite_rank_avg` (raw rank-average, 0-1), `n_legs_present`, `scored_as_true7` (bool, whether
  min_legs>=5 was satisfied), `score` (`-100..+100`, only where `scored_as_true7`), `decile`
  (1=lowest..10=highest, only where `scored_as_true7`).
- **Coverage**: 976 names carry at least one leg value; **802 names clear the min_legs=5 bar and
  are scored as the true composite** (174 names present in the panel but data-thin, correctly
  left unscored rather than diluted).
- **Universe snapshot**: `rnd/forward_test/universe_snapshot_asof_20251205.csv` -- cross-references
  the 802 scored names against the current 750-name universe file
  (`data/universe/nifty_total_market_750.csv`); discloses any scored name absent from that file and
  any universe name that failed to clear min_legs=5.
- **Index of all freezes** (in case this tracker is re-run for a later refresh cycle):
  `rnd/forward_test/BANKED_SCORES_INDEX.json` (append-only).

## 5. PRE-REGISTERED evaluation protocol -- READ BEFORE GRADING
1. **Evaluate ONCE**, at the horizon the Principal chooses (the composite is built and validated
   as a 1Y-forward-return ranker, so a ~12-month elapsed window from the as-of date is the natural
   default, but the Principal owns this decision, not the quant desk).
2. **Do NOT grade early. Do NOT peek.** Checking partial results mid-window and then deciding
   whether to "let it run longer" or "call it now" is itself a form of multiple testing / p-hacking
   the stopping rule -- it would recreate exactly the problem this tracker exists to escape. If an
   interim curiosity-check is unavoidable, it must be logged as such and MUST NOT be substituted for
   the final, pre-registered evaluation.
3. **Success bar, pre-set BEFORE seeing any forward outcome**: expect a realized IC in the
   **~0.11-class** range -- the DECAYED, 2020-2025-era level already disclosed in
   `FINAL_MODEL.md` / `PREIC_AUDIT.md` (IC_mean fell from 0.190 in 2015-20 to 0.111 in 2020-25).
   **Do NOT benchmark forward success against the in-sample IC_IR figures (1.345 biased / 1.760
   PIT-corrected) or any of the historical IC_mean~0.18-0.19 figures from the earlier eras** --
   those are inflated by the very multiple-testing this forward test exists to escape, and by an
   already-observed decay trend. A realized forward IC anywhere near ~0.11, with the correct
   monotonic decile spread and no sign flip, is the honest "the edge is real, just modest and
   decaying" outcome and should be read as a PASS on realism, not a disappointment. A realized IC
   near zero or sign-flipped is the honest KILL signal.
4. **This tracker (and this script) never self-grades.** `forward_test_tracker.py` only freezes
   and banks; it contains no grading logic and must not be extended to include one. Grading is a
   SEPARATE script/session, run once, at the chosen horizon, comparing `scores_asof_20251205.parquet`
   against realized forward returns pulled independently at grading time.
5. Any grading pass must re-verify the freeze-manifest hash (Section 1) has not changed, and must
   itself go through the same disclosure discipline as every other result in this codebase
   (data lineage, row counts, dates, guards, degenerate-result checks) before any verdict is quoted.

## 6. What this forward test does and does not resolve
- It DOES give a genuine, un-gameable read on whether the 7-leg edge survives outside the
  456-trial search that built it -- the one thing DSR/PBO/sensitivity cannot provide.
- It does NOT retroactively fix the DSR~0 / PBO~0.92 in-sample verdict, which stands as recorded
  in `FINAL_MODEL.md` S5-RISKOFFICE regardless of the forward-test outcome. A good forward result
  upgrades the story from "unfalsifiable in-sample overfit risk" to "held-out evidence consistent
  with a modest, decaying, real edge" -- it does not erase the multiple-testing history.
- It does NOT address calibration (score -> p_up / E[return]), which remains explicitly deferred
  per Principal instruction.

## 7. Status
Tracker built. Composite frozen (hash on record). Today's 802-name scores banked
(as-of 2025-12-05, banked 2026-07-17). **Awaiting the Principal's horizon decision. No grading
has occurred. No grading should occur before the chosen horizon elapses.**
