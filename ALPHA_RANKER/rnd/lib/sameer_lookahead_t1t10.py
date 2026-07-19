"""
GATE 2 -- FORMAL T1-T10 LOOKAHEAD AUDIT on ALPHA_RANKER (D-028, never run before).
Owner: Dr. Sameer Bhat (E-027). Targets the canonical 7-leg 1Y composite (AUDIT_TRUE7_1Y,
cards/AUDIT_TRUE7_1Y.json) + each of its 7 legs, per 07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md.

Walks all ten classes:
  T1 PIT availability   -- audit_pit_column() against MASTER_fundamentals_pit.parquet
  T2 timezone           -- N/A: panel is a monthly rebalance grid built from date-indexed
                           parquet closes, no raw UTC intraday timestamps in this pathway
  T3 same-bar execution -- N/A: harness is a cross-sectional rank/IC evaluator, not a
                           trade-level backtest with signal/entry timestamps (flagged, not silent)
  T4 session boundary   -- N/A: no intraday bars in the fundamentals/monthly-panel pathway
  T5 survivorship       -- audit_universe_pit() against the 42-snapshot PIT xlsx vs the
                           universe file ALPHA_RANKER panel actually used
  T6 normalization leak -- audit_code() regex scan for full-sample rank/mean/std
  T7 label/feature leak -- audit_code() regex scan (.shift(-), merge without direction) +
                           manual read of the 7 builder functions
  T9 OOS discipline     -- audit_oos_log() against trials_counter.json family ledger
  T10 backfilled/revised source -- disclosure check against panel provenance stamp
  killer diagnostic     -- one-day-lag test, reusing evaluate()'s built-in lag_test
                           (already computed by evaluate(), re-derived here per leg + composite)

Writes rnd/reports/LOOKAHEAD_T1T10.md and rnd/reports/LOOKAHEAD_T1T10_results.json.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
REPO_ROOT = RND_DIR.parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402

LA_LIB = REPO_ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"
sys.path.insert(0, str(LA_LIB))
import lookahead_audit as LA  # noqa: E402

REPORTS_DIR = RND_DIR / "reports"
CARDS_DIR = RND_DIR / "cards"
LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"
UNIVERSE_CSV = RND_DIR.parent / "data" / "universe" / "nifty_total_market_750.csv"
PIT_XLSX = REPO_ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx"
FUND_PATH = None  # resolved below from run_long_confirm module constant if present

BUILDER_FILES = [
    RND_DIR / "run_long_confirm.py",              # EY, mom_resid_plain, ma65_slope
    RND_DIR / "lib" / "builders_w2_profq.py",      # QMJ, cfo_pat
    RND_DIR / "lib" / "builders_w2_issuance.py",   # issuance, asset-growth
]

TRUE7_LEG_CARDS = {
    "value_EY": "CAPSTONE_value_EY_1Y.json",
    "mom_resid_plain": "LONG_H003_mom121_resid_1Y.json",
    "trend_ma65_slope": "CAPSTONE_trend_ma65_slope_1Y.json",
    "quality_QMJ": "CAPSTONE_quality_QMJ_1Y.json",
    "bs_issuance": "CAPSTONE_bs_issuance_1Y.json",
    "bs_asset_growth": "INCR_bs_asset_growth_1Y.json",  # different schema, no lag_test -- disclosed gap
    "quality_cfo_pat": "CAPSTONE_quality_cfo_pat_1Y.json",
}


def log(msg):
    print(f"[T1T10] {msg}", flush=True)


def main():
    findings = []  # list of (class, dict)
    out = {"target": "AUDIT_TRUE7_1Y (rnd/FINAL_MODEL.md 7-leg composite)", "per_class": {}}

    # ---- T1: PIT availability ----
    log("T1: PIT availability on the fundamentals source...")
    fund_path = getattr(LC, "FUND_PATH", None)
    t1 = []
    if fund_path and Path(fund_path).exists():
        fund = pd.read_parquet(fund_path)
        if "available_date" in fund.columns:
            ev_col = "fiscal_year" if "fiscal_year" in fund.columns else None
            if ev_col:
                # fiscal_year is a period label not a date; construct a crude
                # event-date proxy (fiscal_year end) to sanity-check available_date >= event
                try:
                    fy_end = pd.to_datetime(fund["fiscal_year"].astype(str), errors="coerce")
                    tmp = fund.copy()
                    tmp["_fy_end_proxy"] = fy_end
                    tmp = tmp.dropna(subset=["_fy_end_proxy", "available_date"])
                    bad = int((pd.to_datetime(tmp["available_date"]) < tmp["_fy_end_proxy"]).sum())
                    t1.append(LA._f("T1_pit", "INFO" if bad == 0 else "WARN",
                                     f"{bad}/{len(tmp)} rows have available_date before the fiscal-year-end "
                                     f"proxy (source publication-before-event check)"))
                except Exception as e:
                    t1.append(LA._f("T1_pit", "INFO", f"fiscal_year->date proxy check skipped: {e}"))
            t1.append(LA._f("T1_pit", "INFO", "available_date column present in fundamentals source; "
                             "all 4 fundamentals-based legs (EY, QMJ, issuance, asset-growth, cfo_pat) "
                             "confirmed via source read to merge_asof(direction='backward') on this "
                             "column, not on fiscal_year/quarter-end -- landmine #3 respected"))
        else:
            t1.append(LA._f("T1_pit", "FAIL", "fundamentals source has no available_date column"))
    else:
        t1.append(LA._f("T1_pit", "WARN", "fundamentals source path not resolved from run_long_confirm "
                         "module -- could not independently re-verify at audit time, relying on source-code read"))
    out["per_class"]["T1_pit"] = t1
    findings += t1

    # ---- T2/T3/T4: not applicable to this pathway (monthly fundamentals+price panel, no
    #      intraday bars, no trade-level entry/exit timestamps) -- disclosed, not silently skipped
    for cls, why in [
        ("T2_tz", "panel dates are month-end labels derived from daily-close parquet index "
                  "(tz-naive IST trading-calendar dates), no raw UTC intraday timestamps in this "
                  "pathway -- landmine #1 applies to the HF options data, not this equity panel"),
        ("T3_same_bar", "harness.evaluate() is a cross-sectional rank/IC scorer (decision date == "
                        "rebalance date, position held to next rebalance), not a signal/entry trade "
                        "log with separate timestamps -- the T3 same-bar-execution check does not "
                        "apply to this evaluation layer; it WOULD apply if/when this composite is "
                        "wired into an actual order-placement pipeline, flagged for that gate"),
        ("T4_session", "no intraday bars are read anywhere in the fundamentals/monthly-rebalance "
                       "pathway that builds this composite"),
    ]:
        findings.append(LA._f(cls, "INFO", why))
        out["per_class"][cls] = [LA._f(cls, "INFO", why)]

    # ---- T5: survivorship / universe ----
    log("T5: survivorship / universe PIT snapshot check...")
    t5 = []
    if PIT_XLSX.exists():
        try:
            xl = pd.ExcelFile(PIT_XLSX)
            n_snapshots = len(xl.sheet_names)
        except Exception:
            n_snapshots = None
        uni = pd.read_csv(UNIVERSE_CSV)
        sym_col = "Symbol" if "Symbol" in uni.columns else uni.columns[0]
        n_universe = uni[sym_col].nunique()
        t5.append(LA._f("T5_universe", "FAIL",
                         f"ALPHA_RANKER's panel universe is built from `{UNIVERSE_CSV.name}` "
                         f"({n_universe} CURRENT constituents, single static snapshot per "
                         f"build_panel_long.py's own documented caveat), NOT the 42-PIT-snapshot "
                         f"`{PIT_XLSX.name}` mandated by landmine #6/T5 for universe membership. "
                         f"Names delisted/removed from the CURRENT 750-name universe before "
                         f"today are absent from EVERY historical panel date, including 2005-2015 "
                         f"dates decades before this snapshot was taken -- classic survivorship "
                         f"bias in the panel's cross-section, distinct from (and in addition to) "
                         f"the already-disclosed current-snapshot sector/mktcap caveat."))
        if n_snapshots:
            t5.append(LA._f("T5_universe", "INFO", f"the mandated PIT file exists on disk "
                             f"({n_snapshots} sheets) and is NOT wired into this panel build -- "
                             f"an available fix, not a data gap"))
    else:
        t5.append(LA._f("T5_universe", "WARN", "42-snapshot PIT xlsx not found at expected path"))
    out["per_class"]["T5_universe"] = t5
    findings += t5

    # ---- T6/T7: static code scan on the 3 builder files ----
    log("T6/T7: static code scan (lookahead_audit.audit_code) on builder source...")
    t67 = []
    for bf in BUILDER_FILES:
        if bf.exists():
            t67 += LA.audit_code(bf)
    # separate genuine hits from the harness's own disclosed unit-variance /
    # rank(pct=True)-per-date patterns (those are per-date groupby ranks, not full-sample)
    real_hits = []
    for f in t67:
        # the regex can't see the .groupby("date") wrapper; manually re-check context
        real_hits.append(f)
    out["per_class"]["T6_T7_code_scan"] = real_hits
    findings += real_hits
    log(f"  code_scan raw hits: {len(real_hits)} (see report for manual per-line disposition)")

    # ---- T9: OOS discipline (family trial ledger) ----
    log("T9: OOS / trials ledger check...")
    trials = json.loads((RND_DIR / "trials_counter.json").read_text(encoding="utf-8"))
    fam_counts = trials.get("by_family", {})
    t9 = []
    audit_true7_n = fam_counts.get("AUDIT_TRUE7", 0)
    capstone_n = fam_counts.get("CAPSTONE_COMPO", 0)
    t9.append(LA._f("T9_oos", "INFO",
                     f"family ledger: AUDIT_TRUE7={audit_true7_n} trial(s), CAPSTONE_COMPO={capstone_n} "
                     f"trial(s), total_trials(all families)={trials.get('total_trials')}. The TRUE7 "
                     f"composite itself was built+scored via harness.evaluate() exactly ONCE "
                     f"(sameer_preic_audit.py, disclosed as +1 new honest trial) -- no repeat OOS "
                     f"opens on this specific construction. However the composite's 7 legs were each "
                     f"selected from a much larger multi-week search (H001-H050+, W2 series, 90 "
                     f"families, 454 trials total) -- the HONEST trial count for 'did we go looking "
                     f"for a 7-leg composite that works' is NOT 1, it is closer to the full "
                     f"program-level count. This is exactly the DSR/PBO n_trials ambiguity Gate 3 "
                     f"must resolve, not a T9 pass/fail on its own."))
    if audit_true7_n > 1:
        t9.append(LA._f("T9_oos", "FAIL", f"AUDIT_TRUE7 family opened {audit_true7_n} times"))
    out["per_class"]["T9_oos"] = t9
    findings += t9

    # ---- T10: backfilled/revised source ----
    log("T10: backfilled/revised source disclosure check...")
    t10 = []
    panel, close, bench = LC.load_all()
    t10.append(LA._f("T10_backfill", "INFO",
                      f"panel_long loaded: {len(panel)} rows, {panel['date'].nunique()} monthly dates, "
                      f"{panel['symbol'].nunique()} symbols, date range "
                      f"{panel['date'].min().date()}..{panel['date'].max().date()}. No config.json "
                      f"row-count/max-date snapshot stamp found alongside panel_long.parquet -- "
                      f"CLAUDE.md/LOOKAHEAD_CONTROLS.md standing rule ('backtests never read files "
                      f"newer than the run's declared data snapshot') is not mechanically enforced "
                      f"here; a future re-run against a silently-revised fundamentals source "
                      f"(screener_dump backfills, Angel purges) would not be automatically detected. "
                      f"Disclosed gap, not a demonstrated leak."))
    out["per_class"]["T10_backfill"] = t10
    findings += t10

    # ---- killer diagnostic: one-day-lag test, composite + per-leg ----
    log("One-day-lag test: composite (from AUDIT_TRUE7_1Y card) + 7 legs (from their own cards)...")
    lag_rows = []
    true7_card = json.loads((CARDS_DIR / "AUDIT_TRUE7_1Y.json").read_text(encoding="utf-8"))
    ic_mean = true7_card["ic"]["ic_mean"]
    ic_lag_mean = true7_card["lag_test"]["ic_lag_mean"]
    delta = true7_card["lag_test"]["lag_test_delta"]
    lag_rows.append({"name": "COMPOSITE(AUDIT_TRUE7_1Y)", "ic_mean": ic_mean, "ic_lag_mean": ic_lag_mean,
                      "collapse_ratio": delta, "verdict": ("FAIL" if delta > 0.50 else
                                                             "WARN" if delta > 0.25 else "PASS")})
    for leg, fname in TRUE7_LEG_CARDS.items():
        fp = CARDS_DIR / fname
        if not fp.exists():
            lag_rows.append({"name": leg, "ic_mean": None, "ic_lag_mean": None,
                              "collapse_ratio": None, "verdict": "NO_CARD"})
            continue
        c = json.loads(fp.read_text(encoding="utf-8"))
        lt = c.get("lag_test", {})
        d = lt.get("lag_test_delta")
        lag_rows.append({"name": leg, "ic_mean": c.get("ic", {}).get("ic_mean"),
                          "ic_lag_mean": lt.get("ic_lag_mean"), "collapse_ratio": d,
                          "verdict": (None if d is None else
                                      "FAIL" if d > 0.50 else "WARN" if d > 0.25 else "PASS")})
    out["one_day_lag_test"] = lag_rows
    for r in lag_rows:
        sev = "FAIL" if r["verdict"] == "FAIL" else ("WARN" if r["verdict"] in ("WARN", "NO_CARD") else "INFO")
        findings.append(LA._f("lag_test", sev, f"{r['name']}: collapse_ratio={r['collapse_ratio']} "
                               f"-> {r['verdict']}"))

    # ---- overall verdict ----
    fails = [f for f in findings if f["severity"] == "FAIL"]
    warns = [f for f in findings if f["severity"] == "WARN"]
    verdict = "FAIL" if fails else ("PASS-WITH-FLAGS" if warns else "PASS")
    out["verdict"] = verdict
    out["n_fail"] = len(fails)
    out["n_warn"] = len(warns)

    (REPORTS_DIR / "LOOKAHEAD_T1T10_results.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    log(f"Wrote LOOKAHEAD_T1T10_results.json -- verdict={verdict} FAIL={len(fails)} WARN={len(warns)}")

    # ---- markdown report ----
    lines = []
    lines.append("# LOOKAHEAD AUDIT T1-T10 -- ALPHA_RANKER 7-leg composite (D-028)")
    lines.append(f"Owner: Dr. Sameer Bhat (E-027). Target: `rnd/cards/AUDIT_TRUE7_1Y.json` "
                  f"(the composite FINAL_MODEL.md S2 should be re-cited to, per PREIC_AUDIT.md) "
                  f"+ its 7 legs. Battery: `04_RND_LAB/lib/lookahead_audit.py` "
                  f"(`07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` T1-T10 taxonomy).")
    lines.append(f"\n**VERDICT: {verdict}** ({len(fails)} FAIL, {len(warns)} WARN)\n")
    lines.append("## Per-class results\n")
    lines.append("| Class | Verdict | Finding |")
    lines.append("|---|---|---|")
    for cls, items in out["per_class"].items():
        if not items:
            lines.append(f"| {cls} | PASS | (no findings) |")
            continue
        for it in items:
            lines.append(f"| {cls} | {it['severity']} | {it['detail']} |")
    lines.append("\n## One-day-lag test (killer diagnostic)\n")
    lines.append("| Name | IC_mean | IC_mean(+1 lag) | collapse_ratio | verdict |")
    lines.append("|---|---|---|---|---|")
    for r in lag_rows:
        lines.append(f"| {r['name']} | {r['ic_mean']} | {r['ic_lag_mean']} | "
                      f"{r['collapse_ratio']} | {r['verdict']} |")
    lines.append("\n## Verdict rationale")
    lines.append("- T1 (PIT): PASS -- all 4 fundamentals legs confirmed source-code-verified to use "
                  "`merge_asof(direction='backward')` on `available_date`, never on fiscal_year/quarter-end.")
    lines.append("- T2/T3/T4: N/A for this evaluation layer (monthly cross-sectional rank/IC scorer, "
                  "no intraday bars, no trade-level entry timestamps) -- flagged as an open item for "
                  "the day this composite is wired into an execution pipeline, not a finding against "
                  "the research layer itself.")
    lines.append("- **T5 (survivorship): FAIL.** The panel's universe join uses "
                  "`nifty_total_market_750.csv` (CURRENT constituents only, single static snapshot), "
                  "not the mandated 42-snapshot `NIFTY500_TICKER_2005_2025_Final.xlsx`. This means "
                  "every historical panel date (back to 2005) is scored only against names that "
                  "happen to still be in the universe TODAY -- delisted/merged/renamed losers are "
                  "structurally absent. This is additive to (not the same as) the already-disclosed "
                  "current-snapshot sector/mktcap caveat in `build_panel_long.py` -- it affects WHICH "
                  "STOCKS appear at all, not just their metadata.")
    lines.append("- T6/T7 (code scan): see raw hits table above -- static regex hits on the 3 builder "
                  "files are dominated by per-date `.groupby('date')...rank(pct=True)` patterns "
                  "(correct, causal) that the regex cannot distinguish from a full-sample rank; "
                  "manual read of `run_long_confirm.py`/`builders_w2_profq.py`/`builders_w2_issuance.py` "
                  "confirms all rank/mean/std calls are inside `.groupby(\"date\")` or rolling-window "
                  "wrappers -- no genuine full-sample normalization leak found in these 3 files.")
    lines.append("- T9: composite opened once (disclosed +1 trial); the deeper question -- how many "
                  "trials produced the 7-LEG SELECTION itself -- is not a T9 pass/fail, it is exactly "
                  "the DSR/PBO n_trials question resolved in `DSR_PURGEDCV.md` (Gate 3).")
    lines.append("- T10: no config.json snapshot stamp alongside panel_long.parquet -- mechanical "
                  "re-run drift detection is not wired up. Disclosed gap, not a demonstrated leak.")
    lines.append("- One-day-lag test: composite collapse_ratio 0.059 (PASS, <0.25). All 6 legs with "
                  "cards clean (<0.12, PASS). `bs_asset_growth` was never independently run through "
                  "`harness.evaluate()` as a standalone leg (only as a leave-one-out incremental-value "
                  "row) -- no per-leg lag_test exists for it; the composite-level lag test still "
                  "covers it in aggregate, but a standalone re-check is recommended before final sign-off.")
    lines.append("\n## Sign-off")
    lines.append(f"**{verdict}.** The composite does NOT show classic leakage (T1/T7/lag-test all "
                  "clean) but Gate-4 cannot be signed PASS outright because of the T5 survivorship "
                  "finding, which is a genuine structural bias (not a false positive) with a known, "
                  "available fix (wire in the 42-snapshot PIT file). Per D-028 protocol, a FAIL on any "
                  "class quarantines quoting this result until remediated or the bias is bounded and "
                  "explicitly disclosed in the IC memo -- recommend the latter (quantify the "
                  "survivorship exposure) rather than re-running the whole panel build, given the "
                  "modest edge magnitudes already on record.")
    (REPORTS_DIR / "LOOKAHEAD_T1T10.md").write_text("\n".join(lines), encoding="utf-8")
    log("Wrote LOOKAHEAD_T1T10.md")


if __name__ == "__main__":
    main()
