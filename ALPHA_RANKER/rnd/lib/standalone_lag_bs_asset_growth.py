"""
Standalone one-day(-rebalance)-lag test for `bs_asset_growth` at 1Y horizon.
Closes the disclosed gap in LOOKAHEAD_T1T10.md ("bs_asset_growth never
independently lag-tested (only as a leave-one-out incremental-value row)").

Uses the SAME builder (`builders_w2_issuance.build_asset_growth_factor`),
SAME panel (panel_long.parquet via run_long_confirm.load_all()), SAME
resid return-basis and evaluation harness as the other 6 TRUE7 leg cards
(CAPSTONE_*_1Y.json / LONG_H003_..._1Y.json) -- no new construction, purely
closing a missing standalone card. A 5Y card already existed
(CAPSTONE_bs_asset_growth_5Y.json, lag_test_delta 0.0013, PASS) but the
canonical composite is 1Y, so that does not cover this gap.

Family tag "STANDALONE_LAGCHECK" is a NEW, disclosed +1 trial (not free --
recorded honestly in trials_counter.json like every other evaluate() call).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402
import builders_w2_issuance as bissu  # noqa: E402

RND_DIR = Path(__file__).resolve().parent.parent
CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "reports"


def log(msg):
    print(f"[standalone_lag_bs_asset_growth] {msg}", flush=True)


def main():
    log("Loading panel_long + long cubes (same as other TRUE7 leg cards)...")
    panel, close, bench = LC.load_all()

    log("Building bs_asset_growth factor via builders_w2_issuance.build_asset_growth_factor(panel)...")
    factor = bissu.build_asset_growth_factor(panel)
    log(f"Factor built: {len(factor)} (date,symbol) obs")

    log("Evaluating standalone via harness.evaluate() at 1Y/resid -- 1 new honest trial, disclosed...")
    card = harness.evaluate(
        factor, "1Y", return_basis="resid", factor_id="STANDALONE_bs_asset_growth_1Y",
        panel=panel, panel_source="real_panel_long_capstone",
        family="STANDALONE_LAGCHECK", write_card=True, cards_dir=CARDS_DIR,
    )

    ic_mean = card["ic"]["ic_mean"]
    ic_lag_mean = card["lag_test"]["ic_lag_mean"]
    delta = card["lag_test"]["lag_test_delta"]
    verdict = "FAIL" if (delta is not None and delta > 0.50) else ("WARN" if (delta is not None and delta > 0.25) else "PASS")

    result = {
        "name": "bs_asset_growth (STANDALONE, 1Y, independent of composite)",
        "card": "STANDALONE_bs_asset_growth_1Y.json",
        "ic_mean": ic_mean, "ic_lag_mean": ic_lag_mean,
        "lag_test_delta": delta, "verdict": verdict,
        "n_ic_dates": card["ic"]["n_ic_dates"], "n_trials_family": card["n_trials"],
    }
    log(json.dumps(result, indent=2))

    (REPORTS_DIR / "STANDALONE_LAG_bs_asset_growth_1Y_result.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8")
    log("Wrote reports/STANDALONE_LAG_bs_asset_growth_1Y_result.json")

    # ---- append to LOOKAHEAD_T1T10.md (task 2 instruction) ----
    la_md = REPORTS_DIR / "LOOKAHEAD_T1T10.md"
    addendum = (
        f"\n\n## ADDENDUM 2026-07-17 (Arjun Rao, quant desk) -- bs_asset_growth standalone 1Y lag test\n"
        f"Gap closed: `bs_asset_growth` was flagged in the original T1-T10 pass as never independently "
        f"lag-tested at 1Y (only present in the composite-level lag test and a leave-one-out incremental "
        f"row with no lag_test field). Ran it standalone through the identical harness/panel/basis used "
        f"for the other 6 TRUE7 legs -> `rnd/cards/STANDALONE_bs_asset_growth_1Y.json` "
        f"(+1 disclosed trial, family STANDALONE_LAGCHECK).\n\n"
        f"| Name | IC_mean | IC_mean(+1 lag) | lag_test_delta | verdict |\n"
        f"|---|---|---|---|---|\n"
        f"| bs_asset_growth (STANDALONE, 1Y) | {ic_mean} | {ic_lag_mean} | {delta} | {verdict} |\n\n"
        f"**Result: {verdict}** (lag_test_delta={delta:.4f} {'<' if delta is not None and delta < 0.25 else '>='} 0.25 threshold). "
        f"All 7 TRUE7 legs now have an independent 1Y lag_test on record; no leg is unverified. "
        f"This closes the residual T1-T10 gap; it does NOT change the binding Gate-3 verdict "
        f"(DSR~0 / PBO>0.5 multiple-testing kill stands per FINAL_MODEL.md S5-RISKOFFICE) -- this "
        f"addendum is a leak-check closure only, not a re-certification."
    )
    with la_md.open("a", encoding="utf-8") as f:
        f.write(addendum)
    log("Appended addendum to LOOKAHEAD_T1T10.md")


if __name__ == "__main__":
    main()
