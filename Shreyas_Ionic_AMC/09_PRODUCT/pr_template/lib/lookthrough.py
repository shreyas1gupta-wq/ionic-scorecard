# -*- coding: utf-8 -*-
"""lookthrough.py — shared direct-equity + fund-sleeve combination helpers.

Implements FM comments #2 (look-through equity), #9 (concentration including funds, at scheme/
AMC/sector level) and #10 (combined sector exposure). This is product/reporting ARITHMETIC —
weighted combination of numbers that are already known (a fund's own portfolio weight, and its
own ACE-disclosed mix) — never a scoring decision, so it is explicitly outside the "do not touch
the scoring model" boundary.

Every function here prefers a fund's own ACE-derived figure (`equity_gross_pct`, `sector_alloc`,
etc. — real for a matched client fund, illustrative-but-ACE-shaped for the ABXY demo) and treats
a fund with none of that on file as a COVERAGE GAP, never a silent zero or a category guess
smuggled in as data. Every combining function therefore returns the gap alongside the number.

2026-08-06 bug found while building this: `modules/ips_summary.py`'s original `_lookthrough_mix`
bucketed funds by a QFRA-style category set (`{"mid","small","large","flexi",...}`) that never
included the literal string `"equity"` — the category label azby_family.py's demo funds actually
use. Effect: 5 of the demo book's 9 funds (LIC MF Large Cap, HDFC Flexi Cap, LIC MF Multi Cap,
PGIM India Small Cap, Parag Parikh Flexi Cap — all `category="equity"`) fell through to the
"hybrid/debt" bucket on the IPS page, understating true equity there too. Fixed here by (a) adding
"equity" to the fallback category set, matching this file's mirror of the original sets, and
(b) preferring the per-fund `equity_gross_pct` figure when present, which does not depend on
category bucketing at all. `ips_summary.py` now imports `lookthrough_mix` from here instead of
carrying its own copy, so every page that needs this number reads the same one.
"""
from lib import mf_mapping

# Fallback ONLY for a fund with no ACE-derived equity_gross_pct on file yet (real client, not yet
# matched). "equity" and "passive" are azby_family.py's/most intake files' coarse category labels;
# the rest are the finer QFRA-style labels ips_summary.py originally carried alone.
_EQUITY_FUND_CATS = {"mid", "small", "large", "flexi", "multi", "elss", "dividend_yield",
                      "focused", "value", "passive", "thematic_mnc", "largemid", "equity"}
_HYBRID_FUND_CATS = {"hybrid", "conservative_hybrid"}
_DEBT_FUND_CATS = {"gilt", "debt_short", "overnight", "debt"}


# Same categories as lib/acemf.py's GROSS_EQUITY_CAVEAT, matched by NAME keyword because a ctx
# fund dict (real client, post-intake, or the ABXY demo) carries a coarse `category` string, not
# ACE's own literal Category label. Kept as a short keyword list, not the full acemf.py set,
# because the two shorter categories (Arbitrage, Equity Savings) do not exist anywhere in this
# book yet; extend if a fund of that type is ever held.
_GROSS_EQUITY_NAME_KEYWORDS = ("balanced advantage", "multi-asset", "multi asset",
                               "dynamic asset allocation", "arbitrage", "equity savings")


def gross_equity_footnote(ctx):
    """Footnote text for a page carrying look-through equity (Principal ruling 2026-08-05: gross,
    footnote not a per-row flag), or None if no held category needs it. Names the CATEGORIES
    actually matched in this book (mirrors lib/acemf.py's original design), not every individual
    fund name -- a fund-by-fund version ran long enough to overflow a one-line source caption the
    first time this was tried (2026-08-06), and the category name carries the same information."""
    hit_kw = sorted({kw for f in ctx["funds"] for kw in _GROSS_EQUITY_NAME_KEYWORDS
                      if kw in f["name"].lower()})
    if not hit_kw:
        return None
    label = ", ".join(k.title() for k in hit_kw)
    return (f"Equity is counted gross; {label} categories hold part of that exposure hedged, so "
            "real equity risk is lower than shown.")


def fund_equity_gross_pct(f):
    """Best-available GROSS equity % for one fund (Principal ruling 2026-08-05: gross, as ACE
    reports it, no netting for hedged categories — see gross_equity_footnote in lib/acemf.py).
    None means the fund has no ACE match yet — never guessed from its category."""
    v = f.get("equity_gross_pct")
    return float(v) if v is not None else None


def equity_lookthrough_pct(ctx):
    """Direct equity + fund-sleeve equity (gross), as % of TOTAL portfolio (FM #8 basis).
    Returns (equity_pct, gap_pct, gap_n) — gap_pct/gap_n are the weight and count of funds with
    no ACE-derived equity% on file, so a page can disclose the gap instead of hiding it inside
    a blended number."""
    eq = ctx["equity"]; funds = ctx["funds"]
    eq_w = sum(e["weight_pct"] for e in eq)
    fund_eq = 0.0; gap_w = 0.0; gap_n = 0
    for f in funds:
        g = fund_equity_gross_pct(f)
        if g is None:
            gap_w += f["weight_pct"]; gap_n += 1
            continue
        fund_eq += f["weight_pct"] * g / 100.0
    return round(eq_w + fund_eq, 1), round(gap_w, 1), gap_n


def lookthrough_mix(ctx):
    """Equity / Hybrid-debt / Cash split, direct equity + fund look-through — moved from
    ips_summary.py 2026-08-06 so every page that needs this figure (IPS, snapshot allocation,
    concentration, sector) reads the identical number rather than re-deriving its own."""
    eq = ctx["equity"]; funds = ctx["funds"]; t = ctx["totals"]
    eq_w = sum(e["weight_pct"] for e in eq)
    fund_eq_w = fund_hybrid_w = fund_debt_w = 0.0
    for f in funds:
        w = f["weight_pct"]
        g = fund_equity_gross_pct(f)
        if g is not None:
            d = f.get("debt_pct")
            if d is None:
                d = max(0.0, 100.0 - g - (f.get("others_pct") or 0.0))
            fund_eq_w += w * g / 100.0
            fund_hybrid_w += w * d / 100.0
        else:
            cat = f.get("category")
            if cat in _EQUITY_FUND_CATS:
                fund_eq_w += w
            elif cat in _HYBRID_FUND_CATS:
                fund_hybrid_w += w
            elif cat in _DEBT_FUND_CATS:
                fund_debt_w += w
            else:
                fund_hybrid_w += w  # unknown category: conservative default (unchanged behaviour)
    true_equity = eq_w + fund_eq_w
    true_hybrid_debt = fund_hybrid_w + fund_debt_w
    true_cash = t.get("cash_pct", 0.0)
    return true_equity, true_hybrid_debt, true_cash


# NEXT STEP, NOT BUILT (FM #9 extension, Principal 2026-08-06): "we can look for last factsheet
# other data etc." for fund HOLDINGS. Everything above is fund-level (a scheme's own disclosed
# equity/debt/sector split). STOCK-level look-through -- which named companies a client is really
# exposed to once every fund's underlying portfolio is added to their direct holdings -- needs each
# fund's monthly factsheet/portfolio disclosure, which is not sourced yet (ACE gives sector percentages,
# not a security list, per the scheme_correlation.py / scheme_overlap_full.py finding the same day).
# Documented here as the natural next data-sourcing step; deliberately NOT scraped in this task.


def full_lookthrough_mix(ctx):
    """Principal ruling 2026-08-06 (FM #6): 'asset allocations should incl ... all mf stocks
    other' -- the full-portfolio look-through has to be direct equity + fund look-through equity +
    debt + cash + others, SUMMING TO THE WHOLE BOOK. `lookthrough_mix()` above pre-dates this
    ruling and has exactly the gap it names: for any ACE-matched fund with a nonzero `others_pct`
    (every fund in this book carries a small one -- REITs/InvITs/derivatives-margin/unclassified,
    per ACE's own 'Others' column), that slice was silently dropped -- added to neither the equity
    nor the debt bucket -- so the three-segment strip understated the book by however much
    `others_pct` weighted. Real, not hypothetical: with azby's synthetic ACE-shaped funds all
    carrying 1-5% Others, the old strip leaked roughly 0.3-0.5pp of the total book.

    Equity is counted GROSS, per the 2026-08-05 ruling (no netting for the hedged categories --
    that is a footnote, not a per-row adjustment here). Returns (equity_pct, debt_pct, cash_pct,
    others_pct); the four always sum to ~100% of the book (direct equity carries no debt/others of
    its own in this deck's holdings, so its full weight lands in the equity bucket)."""
    eq = ctx["equity"]; funds = ctx["funds"]; t = ctx["totals"]
    eq_w = sum(e["weight_pct"] for e in eq)
    fund_eq_w = fund_debt_w = fund_others_w = 0.0
    for f in funds:
        w = f["weight_pct"]
        g = fund_equity_gross_pct(f)
        if g is not None:
            others = f.get("others_pct")
            debt = f.get("debt_pct")
            if debt is None:
                debt = max(0.0, 100.0 - g - (others or 0.0))
            if others is None:
                others = max(0.0, 100.0 - g - debt)
            fund_eq_w += w * g / 100.0
            fund_debt_w += w * debt / 100.0
            fund_others_w += w * others / 100.0
        else:
            cat = f.get("category")
            if cat in _EQUITY_FUND_CATS:
                fund_eq_w += w
            elif cat in _DEBT_FUND_CATS:
                fund_debt_w += w
            elif cat in _HYBRID_FUND_CATS:
                # no ACE split on file for this hybrid -- conservative: treat as debt-like rather
                # than invent an equity/debt split we do not have (unchanged conservative default
                # from lookthrough_mix, just now landing in the finer debt bucket, not "others").
                fund_debt_w += w
            else:
                fund_others_w += w  # truly uncategorised: disclosed as Others, never smuggled in
    true_equity = eq_w + fund_eq_w
    true_cash = t.get("cash_pct", 0.0)
    return (round(true_equity, 1), round(fund_debt_w, 1), round(true_cash, 1), round(fund_others_w, 1))


def combined_sector_exposure(ctx):
    """Direct-equity sector weights + the fund sleeve's own sector weights (ACE's 44-column
    `Sector Wise Allocation` block, or the demo's illustrative equivalent), both as % of TOTAL
    portfolio. Replaces the old "fund sleeve not looked through" caveat (FM #10). A fund with no
    sector allocation on file contributes nothing and is counted into the gap — never smeared
    evenly across sectors as an assumption.
    Returns (sector_pct: {sector: pct_of_portfolio}, gap_pct, gap_n)."""
    out = {}
    for e in ctx["equity"]:
        sec = (e.get("sector") or "Diversified").strip() or "Diversified"
        out[sec] = out.get(sec, 0.0) + e["weight_pct"]
    gap_w = 0.0; gap_n = 0
    for f in ctx["funds"]:
        alloc = f.get("sector_alloc")
        if not alloc:
            gap_w += f["weight_pct"]; gap_n += 1
            continue
        for sec, pct in alloc.items():
            out[sec] = out.get(sec, 0.0) + f["weight_pct"] * pct / 100.0
    return out, round(gap_w, 1), gap_n


def amc_concentration(ctx):
    """Fund weight grouped by canonical AMC (FM #9, AMC level) — equity holdings have no AMC.
    Returns {amc: pct_of_portfolio}, sorted descending."""
    out = {}
    for f in ctx["funds"]:
        amc = mf_mapping.canonical_amc(f.get("amc") or "Unknown")
        out[amc] = out.get(amc, 0.0) + f["weight_pct"]
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def scheme_concentration(ctx, top_n=10):
    """Top holdings by weight, stocks AND fund schemes together (FM #9, scheme level) — the IPS
    page's own single_name_cap_pct is already documented as covering "single scheme / instrument",
    so a large fund is the same concentration event as a large stock against that one cap.
    Returns [(name, kind, weight_pct), ...], kind in {"Stock","Fund"}, sorted descending."""
    rows = [(e["name"], "Stock", e["weight_pct"]) for e in ctx["equity"]]
    rows += [(f["name"], "Fund", f["weight_pct"]) for f in ctx["funds"]]
    rows.sort(key=lambda r: -r[2])
    return rows[:top_n]


def max_sector_lookthrough(ctx):
    """Convenience for a concentration-page callout: (sector, pct_of_portfolio, gap_pct, gap_n)
    for the single largest sector once the fund sleeve is looked through."""
    sectors, gap_w, gap_n = combined_sector_exposure(ctx)
    if not sectors:
        return None, 0.0, gap_w, gap_n
    top = max(sectors.items(), key=lambda kv: kv[1])
    return top[0], round(top[1], 1), gap_w, gap_n
