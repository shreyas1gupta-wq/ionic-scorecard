# -*- coding: utf-8 -*-
"""core_satellite.py — core/satellite classification for the FUND sleeve (Principal ruling #1,
2026-08-06). Target 70/30, flexible band; his words: "broad direction/idea" — so the book-level
check below is guidance, not a breach test (no red/green pass-fail; a plain distance-from-target
readout).

SCOPE NOTE: the ruling's own wording names only fund categories (core: index, large, mid, flexi,
multi, hybrid, debt, gold; satellite: sectoral/thematic, small cap, international, factor/
smart-beta, contra). This module's primary classifier (classify/book_split) is fund-sleeve-only
for that reason. FOUND WHILE BUILDING THIS (2026-08-06): a concurrent build the same day,
`modules/core_satellite.py` (Product/Tanvi — a slide renderer, not this lib layer), resolved the
direct-equity question independently and the other way — it classifies stocks too (gold by name
-> core, mcap_band=='Small' -> satellite, else core) — so this file's `classify_equity()` mirrors
that exact rule and `book_split()` takes an optional `equity=` argument, rather than leaving two
independent, silently-diverging answers to the same question on the same day. The two modules'
FUND-category maps also differ in one place: `modules/core_satellite.py`'s own `_CORE_FUND_CATS`
set has no "mid" entry (relies on its catch-all default to land "mid" at Core, same *outcome* as
this file's explicit membership, different and more fragile *mechanism*) — flagged for a
reconciliation pass, not silently fixed here since that file is owned by a different, possibly
still-in-flight, build.

MIDCAP CORRECTION (2026-08-06): an earlier proposal this session put midcap funds in satellite;
the Principal corrected this directly — MIDCAP IS CORE. CORE_CATEGORIES below reflects the
correction; the mistake is kept in this comment, not hidden, per the firm's Lessons-Learned
convention.
"""

CONFIG = {
    "TARGET_CORE_PCT": 70.0,
    "TARGET_SATELLITE_PCT": 30.0,
    # Flexible band width: his own word is "broad direction/idea", not a hard test, so this
    # number only decides how the book_split() readout is WORDED (within-guidance vs a wide
    # miss), never a pass/fail flag. Chosen wide enough that swapping one satellite fund for
    # another doesn't flip the cue, narrow enough to still mean something.
    # DOCUMENTED DEFAULT — open to the FM's revision, same as every other undecided number here.
    "BAND_PP": 10.0,

    # Exact category strings this codebase already uses (lookthrough.py's category sets,
    # acemf.py's Category column, azby_family.py's category field) mapped onto the Principal's
    # two buckets. Categories the ruling did NOT explicitly name (ELSS, dividend_yield, focused,
    # value, largemid, conservative_hybrid, debt_short, overnight, gilt) are placed by the STATED
    # default rule in classify() (core unless it matches a satellite keyword) and listed here so
    # the mapping is auditable rather than silently invented. Kept inside CONFIG (not a bare
    # module constant) specifically so mf_sell_score_sensitivity.py can flip one entry — e.g. put
    # "mid" back in the satellite set — and show what today's #1 midcap correction is actually
    # worth in book-split terms.
    "CORE_CATEGORIES": frozenset({
        "index", "passive",                  # ruling: "index"
        "large", "largemid",                 # ruling: "large" (largemid is the same broad-cap family)
        "mid",                                # ruling: "mid" (2026-08-06 correction — was wrongly satellite)
        "flexi",                              # ruling: "flexi"
        "multi",                              # ruling: "multi"
        "hybrid", "conservative_hybrid",      # ruling: "hybrid" (both hybrid sub-types)
        "debt", "debt_short", "overnight", "gilt",  # ruling: "debt" (all debt-category sub-labels)
        "gold",                               # ruling: "gold"
        # not explicitly named by the ruling; defaulted to core (see module docstring) because
        # none is a concentrated sector/geography/factor bet -- they are style tilts on a broad
        # mandate:
        "elss", "dividend_yield", "focused", "value",
    }),

    # Keyword match against category label OR fund name -- the ruling's satellite bucket is a
    # set of concentrated/tactical MANDATES, most reliably identified by keyword rather than by
    # trying to enumerate every category string a real ACE file might use.
    "SATELLITE_KEYWORDS": (
        "sector", "thematic", "small", "international", "global", "overseas", "foreign",
        "factor", "smart beta", "smart-beta", "momentum", "quality30", "alpha", "contra",
        "mnc",  # this codebase's own "thematic_mnc" category label
    ),
}


def classify(fund, cfg=None):
    """Returns ("core"|"satellite", reason). Category is checked first (cheap, deterministic);
    name is checked only as a fallback for a category string this map doesn't recognise, so an
    unusual/new category never silently defaults through without at least a keyword look."""
    cfg = cfg or CONFIG
    cat = str(fund.get("category") or "").strip().lower()
    name = str(fund.get("name") or "").lower()
    if cat in cfg["CORE_CATEGORIES"]:
        return "core", f"category {cat!r} is in the Principal's core list (#1, 2026-08-06)"
    for kw in cfg["SATELLITE_KEYWORDS"]:
        if kw in cat or kw in name:
            return "satellite", f"matches satellite keyword {kw!r} (category={cat!r})"
    # unrecognised category, no satellite keyword: default to core (see module docstring) —
    # the ruling defines satellite by naming concentrated/tactical mandates explicitly; anything
    # matching none of them is treated as core by default, mirroring the #18/#23 nil-restriction
    # default pattern used elsewhere in this build.
    return "core", f"category {cat!r} not recognised and matches no satellite keyword; defaulted to core"


def classify_equity(e):
    """Direct-equity classification — NOT part of the Principal's literal ruling (see module
    docstring's SCOPE NOTE), mirrored here from `modules/core_satellite.py`'s own rule (built the
    same day, independently) purely so this lib and that renderer agree rather than silently
    diverging: gold named explicitly regardless of wrapper -> core; small-cap by mcap_band ->
    satellite; everything else (large/mid) -> core. Returns (bucket, reason)."""
    name = str(e.get("name") or "").lower()
    if "gold" in name:
        return "core", "named gold, treated as core regardless of wrapper (matches modules/core_satellite.py)"
    if e.get("mcap_band") == "Small":
        return "satellite", "mcap_band == 'Small' (matches modules/core_satellite.py)"
    return "core", f"mcap_band {e.get('mcap_band')!r} treated as core (large/mid)"


def book_split(funds, equity=None, cfg=None):
    """Core/satellite split vs the 70/30 guidance (informational band, not a breach test — see
    module docstring). `equity` is optional: omit it (default) for the fund-sleeve-only split the
    Principal's literal ruling covers; pass ctx['equity'] to get the whole-book split that mirrors
    `modules/core_satellite.py`'s own scope. Returns {"core_pct", "satellite_pct", "gap_pp",
    "within_guidance_band", "core_holdings", "satellite_holdings", "detail", "scope"} where
    `detail` is a per-holding [(name, bucket, weight_pct, reason)] list for an analyst to audit,
    and `scope` records which of the two questions this particular call answered."""
    cfg = cfg or CONFIG
    holdings = [(f, classify(f, cfg)) for f in funds]
    holdings += [(e, classify_equity(e)) for e in (equity or [])]
    total_w = sum(h.get("weight_pct") or 0.0 for h, _ in holdings)
    core_w = sat_w = 0.0
    core_holdings, sat_holdings, detail = [], [], []
    for h, (bucket, reason) in holdings:
        w = h.get("weight_pct") or 0.0
        detail.append((h.get("name"), bucket, w, reason))
        if bucket == "core":
            core_w += w
            core_holdings.append(h.get("name"))
        else:
            sat_w += w
            sat_holdings.append(h.get("name"))
    core_pct = round(100.0 * core_w / total_w, 1) if total_w else None
    sat_pct = round(100.0 * sat_w / total_w, 1) if total_w else None
    gap_pp = round(core_pct - cfg["TARGET_CORE_PCT"], 1) if core_pct is not None else None
    within = (abs(gap_pp) <= cfg["BAND_PP"]) if gap_pp is not None else None
    return {"core_pct": core_pct, "satellite_pct": sat_pct, "gap_pp": gap_pp,
            "within_guidance_band": within, "core_holdings": core_holdings,
            "satellite_holdings": sat_holdings, "detail": detail,
            "target_core_pct": cfg["TARGET_CORE_PCT"], "band_pp": cfg["BAND_PP"],
            "scope": "fund-sleeve-only" if equity is None else "whole-book (funds + direct equity)"}
