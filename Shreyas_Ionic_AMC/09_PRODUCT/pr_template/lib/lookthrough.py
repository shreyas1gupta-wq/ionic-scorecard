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


def is_equity_fund(f):
    """One definition of an equity-style fund, shared by every page that needs it.

    funds_equity filtered on the literal pair ("equity", "passive") while this library sorted on a
    richer set. While the kit handed every fund the single coarse string "equity" both happened to
    agree; once the real category was derived, a large-cap fund reads "large" and passed the library
    but failed the page, so the equity-funds pages went from four to one and twenty-four scored
    equity funds vanished from the fund book.
    """
    return (f.get("category") or "") in _EQUITY_FUND_CATS


def other_holdings(ctx):
    """Everything held that is neither a direct share nor a mutual-fund scheme: AIFs, private
    equity, a PMS, REITs, a ULIP, direct bonds and deposits.

    THIS LIBRARY USED TO IGNORE THEM ENTIRELY, and that was the single biggest error in the
    portfolio pages. Every function below summed ctx["equity"] and ctx["funds"] only, so on a book
    holding 30% of its value in AIFs, a PMS, REITs, a ULIP and direct bonds, the allocation strip,
    the core-satellite split, the AMC and scheme concentration tests and the IPS current column were
    all struck on 70% of the portfolio. full_lookthrough_mix even documents a Principal ruling that
    it must sum to the WHOLE book, and it did not.

    Each one is bucketed BY ITS OWN ASSET CLASS, which is what the statement already states: a
    long-only equity AIF and a discretionary equity PMS are equity, a credit AIF and a bond are
    fixed income, a REIT and a ULIP are alternates.
    """
    return list(ctx.get("other") or [])


def other_by_class(ctx):
    """(equity_w, debt_w, alt_w) from the non-fund, non-share holdings, as % of the book."""
    eq = debt = alt = 0.0
    for o in other_holdings(ctx):
        w = float(o.get("weight_pct") or 0.0)
        c = (o.get("asset_class") or "").strip().lower()
        if c == "equity":
            eq += w
        elif c == "fixed income":
            debt += w
        else:
            alt += w
    return eq, debt, alt


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
    oth_eq, _d, _a = other_by_class(ctx)
    return round(eq_w + fund_eq + oth_eq, 1), round(gap_w, 1), gap_n


def lookthrough_mix(ctx):
    """DEPRECATED. Kept only so an older client data file importing it does not break.

    Its own body summed ctx["equity"] and ctx["funds"] and nothing else, so on a book holding
    AIFs, a PMS, REITs, direct bonds and a ULIP it returned 70% of the money and called it the
    whole mix, while its docstring claimed every page read the identical number from it. Nothing
    in the kit calls it any more. It now delegates to full_lookthrough_mix, which covers the whole
    book, so the two can no longer disagree.
    """
    eq, debt, cash, _others = full_lookthrough_mix(ctx)
    return eq, debt, cash

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
            # THE FUND'S OWN ASSET CLASS OUTRANKS ITS COARSE CATEGORY. engine_category files a
            # gold ETF and a gold fund-of-fund as "passive", which is true of how they are run and
            # false about what they hold, and "passive" is in the equity set -- so Rs 41.9 lakh of
            # gold was counted as look-through EQUITY. Two pages of one deck then disagreed on the
            # headline allocation by 3.66 points, with no way for a reader to tell which was
            # right. Alternates is alternates however the sleeve is managed.
            _ac = str(f.get("asset_class") or "").strip().lower()
            if _ac == "alternates":
                fund_others_w += w
            elif _ac == "fixed income" and cat not in _DEBT_FUND_CATS:
                fund_debt_w += w
            elif cat in _EQUITY_FUND_CATS:
                fund_eq_w += w
            elif cat in _DEBT_FUND_CATS:
                fund_debt_w += w
            elif cat in _HYBRID_FUND_CATS:
                # No split on file for this hybrid. Calling it debt was described here as the
                # conservative choice, but it is not conservative, it is simply wrong in a
                # particular direction: a Balanced Advantage or Multi-Asset fund typically runs
                # most of its money in equity, and filing it as 100% debt understates the book's
                # equity and overstates its debt by the whole position. Neither number is knowable
                # without the fund's own allocation, so it goes to the disclosed Others bucket,
                # which is what that bucket is for. A reader can see there is something the review
                # could not split; a reader cannot see a hybrid hidden inside a debt figure.
                fund_others_w += w
            else:
                fund_others_w += w  # truly uncategorised: disclosed as Others, never smuggled in
    oth_eq, oth_debt, oth_alt = other_by_class(ctx)
    true_equity = eq_w + fund_eq_w + oth_eq
    true_cash = t.get("cash_pct", 0.0)
    return (round(true_equity, 1), round(fund_debt_w + oth_debt, 1), round(true_cash, 1),
            round(fund_others_w + oth_alt, 1))


def combined_sector_exposure(ctx):
    """Direct-equity sector weights + the fund sleeve's own sector weights (ACE's 44-column
    `Sector Wise Allocation` block, or the demo's illustrative equivalent), both as % of TOTAL
    portfolio. Replaces the old "fund sleeve not looked through" caveat (FM #10). A fund with no
    sector allocation on file contributes nothing and is counted into the gap — never smeared
    evenly across sectors as an assumption.
    Returns (sector_pct: {sector: pct_of_portfolio}, gap_pct, gap_n)."""
    out = {}
    # Include everything held. Without this the "largest sector" was computed on the direct-share
    # sleeve only, 8.9% of this book, and then presented as a whole-portfolio figure.
    for e in list(ctx["equity"]) + list(ctx.get("other") or []):
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
    # A PMS, an AIF or a ULIP has a manager too, and the cap is measured on the manager.
    for o in other_holdings(ctx):
        amc = (o.get("amc") or "").strip()
        if amc and amc != "-":
            k = mf_mapping.canonical_amc(amc)
            out[k] = out.get(k, 0.0) + float(o.get("weight_pct") or 0.0)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def scheme_concentration(ctx, top_n=10):
    """Top holdings by weight, stocks AND fund schemes together (FM #9, scheme level) — the IPS
    page's own single_name_cap_pct is already documented as covering "single scheme / instrument",
    so a large fund is the same concentration event as a large stock against that one cap.
    Returns [(name, kind, weight_pct), ...], kind in {"Stock","Fund"}, sorted descending."""
    rows = [(e["name"], "Stock", e["weight_pct"]) for e in ctx["equity"]]
    rows += [(f["name"], "Fund", f["weight_pct"]) for f in ctx["funds"]]
    # Without this, the largest single position in a book like this one, a Rs 31 crore
    # discretionary PMS, was absent from the top-ten concentration table altogether.
    rows += [(o["name"], (o.get("sub_category") or "Other").split(" - ")[0],
              float(o.get("weight_pct") or 0.0)) for o in other_holdings(ctx)]
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
