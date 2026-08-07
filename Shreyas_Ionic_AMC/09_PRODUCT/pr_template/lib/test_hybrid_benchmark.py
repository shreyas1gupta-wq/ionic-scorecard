# -*- coding: utf-8 -*-
"""Unit tests for hybrid_benchmark.py (FM #20 blended benchmark). Plain assert-based, matching
the house convention (see scripts/test_fund_matching.py).

Run: python test_hybrid_benchmark.py    (from this directory; exit 0 = all pass)
"""
import os
import sys
import tempfile
import datetime as _dt

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
_PRT = os.path.abspath(os.path.join(_LIB_DIR, ".."))
if _PRT not in sys.path:
    sys.path.insert(0, _PRT)

import hybrid_benchmark as H

FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL: {name}")
    else:
        print(f"ok:   {name}")


# use the OS temp dir, never the real store, so this test never touches production data and never
# depends on any one machine's directory layout
STORE = os.path.join(tempfile.gettempdir(), "test_mf_mix_history.csv")
if os.path.exists(STORE):
    os.remove(STORE)

fund = {"isin": "INF000TEST01", "name": "Test Balanced Advantage", "equity_gross_pct": 68.0,
        "debt_pct": 29.0, "others_pct": 3.0}

# ---------------------------------------------------------------------------------- degradation
mix0 = H.trailing_mix(fund, store_path=STORE)
check("trailing_mix: day one, zero history -> current-mix basis, labelled honestly",
      mix0["basis"] == "current-mix" and mix0["n_months"] == 0)
check("trailing_mix: current-mix uses the fund's own disclosed figures exactly",
      mix0["equity_pct"] == 68.0 and mix0["debt_pct"] == 29.0 and mix0["others_pct"] == 3.0)

n_written = H.record_snapshot([fund], "2026-01", store_path=STORE)
check("record_snapshot: writes one row for one fund with a disclosed mix", n_written == 1)
n_dupe = H.record_snapshot([fund], "2026-01", store_path=STORE)
check("record_snapshot: idempotent -- re-running the same month writes nothing new", n_dupe == 0)

months = ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
equity_by_month = {"2026-01": 68.0}   # the Jan row already written above, for the expected-value check
for i, m in enumerate(months):
    drifted = dict(fund, equity_gross_pct=68.0 + i, debt_pct=29.0 - i, others_pct=3.0)
    H.record_snapshot([drifted], m, store_path=STORE)
    equity_by_month[m] = 68.0 + i

mix_partial = H.trailing_mix(fund, store_path=STORE)
check("trailing_mix: 6 months on file (>= MIN_MONTHS_FOR_TRAILING_AVG's own threshold) "
      "flips the basis to a real average, not current-mix",
      mix_partial["n_months"] == 6)
check("trailing_mix: once >=MIN_MONTHS_FOR_TRAILING_AVG months exist, basis flips to a real average",
      mix_partial["basis"] == "trailing-6mo-average")
expected_eq = sum(equity_by_month.values()) / len(equity_by_month)
check("trailing_mix: the average is arithmetically correct, not a placeholder",
      abs(mix_partial["equity_pct"] - expected_eq) < 1e-6)

# ------------------------------------------------------------------------- pending interface gaps
start, end = _dt.date(2023, 1, 1), _dt.date(2026, 1, 1)
r, mix, gap = H.blended_return(fund, start, end, store_path=STORE)
check("blended_return: no lib.benchmark_returns yet -> None with an explicit gap reason, never a guess",
      r is None and mix is not None and "benchmark_returns" in gap)

dc, gap_dc = H.down_capture_vs_blended(dict(fund, nav=[100, 101, 99, 102]), start, end, store_path=STORE)
check("down_capture_vs_blended: same pending-interface gap, not a fabricated capture ratio",
      dc is None and bool(gap_dc))

cap6, gap6 = H.total_capture_6m(dict(fund, ret_6m_pct=4.2), store_path=STORE)
check("total_capture_6m: same pending-interface gap", cap6 is None and bool(gap6))

dc_nodata, gap_nodata = H.down_capture_vs_blended(dict(fund), start, end, store_path=STORE)
check("down_capture_vs_blended: no NAV on file -> gap before even reaching the interface",
      dc_nodata is None and "NAV" in gap_nodata)

# ------------------------------------------------------------------------------------ suitability
ctx_with_ips = {"ips": {"on_file": True, "alloc_bands": {"Equity": (50, 65, 75)}}}
ctx_no_ips = {"ips": {"on_file": False}}
ok, why = H.suitability_vs_ips(dict(fund, equity_gross_pct=68.0), ctx_with_ips)
check("suitability_vs_ips: 68% sits inside a 50-75 band -> suitable", ok is True)
bad, why_bad = H.suitability_vs_ips(dict(fund, equity_gross_pct=90.0), ctx_with_ips)
check("suitability_vs_ips: 90% sits outside a 50-75 band -> flagged, with a plain-English reason",
      bad is False and "90" in why_bad)
none_ok, none_why = H.suitability_vs_ips(fund, ctx_no_ips)
check("suitability_vs_ips: no IPS on file -> None, assumed no restriction (#18/#23 pattern)",
      none_ok is None and "#18/#23" in none_why)

os.remove(STORE)
print()
if FAILS:
    print(f"{len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("ALL PASS")
sys.exit(0)
