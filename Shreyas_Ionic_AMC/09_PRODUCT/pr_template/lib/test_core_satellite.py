# -*- coding: utf-8 -*-
"""Unit tests for core_satellite.py (Principal ruling #1, 2026-08-06). Plain assert-based,
matching the house convention (see scripts/test_fund_matching.py).

Run: python test_core_satellite.py    (from this directory; exit 0 = all pass)
"""
import os
import sys

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
_PRT = os.path.abspath(os.path.join(_LIB_DIR, ".."))
if _PRT not in sys.path:
    sys.path.insert(0, _PRT)

import core_satellite as C

FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL: {name}")
    else:
        print(f"ok:   {name}")


# ---------------------------------------------------------------------------------- classify()
check("midcap is CORE (2026-08-06 correction, must not regress)",
      C.classify({"category": "mid", "name": "HDFC Mid-Cap Opportunities"})[0] == "core")
for cat in ("index", "large", "flexi", "multi", "hybrid", "debt", "gold", "largemid"):
    check(f"category {cat!r} classifies core per the literal ruling",
          C.classify({"category": cat, "name": "X Fund"})[0] == "core")
for cat, name in (("small", "X Small Cap Fund"), ("thematic_mnc", "X MNC Fund")):
    check(f"category {cat!r} classifies satellite per the literal ruling",
          C.classify({"category": cat, "name": name})[0] == "satellite")
check("name-based fallback catches a sectoral fund with an unrecognised category label",
      C.classify({"category": "misc", "name": "X Banking & Financial Services Sector Fund"})[0] == "satellite")
check("international by name -> satellite",
      C.classify({"category": "misc", "name": "X US International Opportunities Fund"})[0] == "satellite")
check("contra by name -> satellite",
      C.classify({"category": "misc", "name": "X Contra Fund"})[0] == "satellite")
check("an unrecognised, non-matching category defaults to core (documented default, not a guess)",
      C.classify({"category": "totally_unknown_xyz", "name": "Nothing Special Fund"})[0] == "core")

# --------------------------------------------------------------------------------- book_split()
funds = [
    {"name": "Index Fund", "category": "index", "weight_pct": 40.0},
    {"name": "Flexi Fund", "category": "flexi", "weight_pct": 30.0},
    {"name": "Small Cap Fund", "category": "small", "weight_pct": 20.0},
    {"name": "Sector Fund", "category": "sector", "weight_pct": 10.0},
]
res = C.book_split(funds)
check("book_split: core% arithmetic correct (70% core, 30% satellite by construction)",
      res["core_pct"] == 70.0 and res["satellite_pct"] == 30.0)
check("book_split: exactly-on-target reads gap_pp == 0 and within the guidance band",
      res["gap_pp"] == 0.0 and res["within_guidance_band"] is True)
check("book_split: detail lists every fund with its bucket and reason",
      len(res["detail"]) == 4 and all(len(row) == 4 for row in res["detail"]))

funds_off = [
    {"name": "Small Cap Fund", "category": "small", "weight_pct": 50.0},
    {"name": "Sector Fund", "category": "sector", "weight_pct": 50.0},
]
res_off = C.book_split(funds_off)
check("book_split: an all-satellite book reads a large negative gap and outside the band",
      res_off["core_pct"] == 0.0 and res_off["gap_pp"] == -70.0 and res_off["within_guidance_band"] is False)

# ------------------------------------------------------------------ sensitivity-style configurability
# proves the #1 midcap correction is genuinely load-bearing: flip it back and re-measure the same
# book. Removing "mid" from CORE_CATEGORIES alone is NOT enough to reclassify it -- classify()'s
# own safety net defaults an unrecognised, non-keyword-matching category back to core (see its
# docstring), so a full reversal also needs a matching satellite keyword, exactly as it would if
# the FM asked for this change for real.
cfg_midcap_satellite = dict(C.CONFIG)
cfg_midcap_satellite["CORE_CATEGORIES"] = frozenset(C.CONFIG["CORE_CATEGORIES"] - {"mid"})
cfg_midcap_satellite["SATELLITE_KEYWORDS"] = C.CONFIG["SATELLITE_KEYWORDS"] + ("mid",)
funds_mid = [
    {"name": "Large Fund", "category": "large", "weight_pct": 40.0},
    {"name": "Mid Fund", "category": "mid", "weight_pct": 30.0},
    {"name": "Small Fund", "category": "small", "weight_pct": 30.0},
]
res_ruling = C.book_split(funds_mid)
res_reversed = C.book_split(funds_mid, cfg=cfg_midcap_satellite)
check("configurability: reversing the midcap correction changes this book's core% by exactly the mid weight",
      abs((res_ruling["core_pct"] - res_reversed["core_pct"]) - 30.0) < 1e-6)
check("configurability: under the ruling, mid counts as core",
      any(r[0] == "Mid Fund" and r[1] == "core" for r in res_ruling["detail"]))
check("configurability: reversed cfg puts mid in satellite",
      any(r[0] == "Mid Fund" and r[1] == "satellite" for r in res_reversed["detail"]))

# --------------------------------------------------------- classify_equity() / whole-book scope
check("classify_equity: a stock named for gold is core regardless of wrapper",
      C.classify_equity({"name": "Gold ETF Units", "mcap_band": "Large"})[0] == "core")
check("classify_equity: small mcap_band is satellite",
      C.classify_equity({"name": "Random Small Co", "mcap_band": "Small"})[0] == "satellite")
check("classify_equity: large/mid mcap_band is core",
      C.classify_equity({"name": "Random Large Co", "mcap_band": "Large"})[0] == "core")

fund_only = C.book_split(funds)
check("book_split: default scope is fund-sleeve-only", fund_only["scope"] == "fund-sleeve-only")
equity_rows = [{"name": "Big Blue Chip", "mcap_band": "Large", "weight_pct": 60.0},
               {"name": "Tiny Small Cap Co", "mcap_band": "Small", "weight_pct": 40.0}]
whole = C.book_split(funds, equity=equity_rows)
check("book_split: passing equity switches scope to whole-book",
      whole["scope"] == "whole-book (funds + direct equity)")
check("book_split: whole-book total weight includes both equity and funds",
      len(whole["detail"]) == len(funds) + len(equity_rows))

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("ALL PASS")
sys.exit(0)
