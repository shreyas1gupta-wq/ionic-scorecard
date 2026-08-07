# -*- coding: utf-8 -*-
"""concentration_risk, top-holdings treemap INCLUDING funds (FM #9), AMC concentration, and a
look-through sector-concentration pointer. Three levels per the FM's own wording: scheme (a large
fund is the same single-instrument risk as a large stock — the IPS single-name cap already
covers "single scheme / instrument"), AMC (funds only), and sector (look-through, pointing at
sector_exposure.py rather than duplicating its chart). Stock-level look-through inside a fund is
explicitly NOT claimed anywhere on this page — the fund data has no holdings list."""
from slidekit import (NAVY, GOLD, INK, SLATE, SELL, HOLD, AMBER, SANS, SERIF, ML, UW, RX,
                      short_name)
import charts as CH
from lib import lookthrough as LT

CNAVY, CNT1, CNT2, CNT3, CSELL = "#1B27A3", "#4A57C4", "#8C95DE", "#C9CEF0", "#E0402F"
_RAMP = [CNAVY, CNT1, CNT2, CNT3]

LABELS = {
    "hni":    {"eyebrow": "Concentration risk",
               "title": "Single-holding concentration, stocks and funds together"},
    "std":    {"eyebrow": "Concentration risk",
               "title": "Your largest positions, shares and funds, against the cap"},
    "simple": {"eyebrow": "Too much in too few holdings",
               "title": "Your ten biggest positions, shares and funds"},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    eq = ctx["equity"]; cap = ctx["ips"]["single_name_cap_pct"]; as_of = ctx["client"]["as_of"]

    # ---- scheme level: stocks AND funds together (FM #9) ----
    combined = LT.scheme_concentration(ctx, top_n=10)  # [(name, kind, weight_pct), ...]
    breaches = [(n, k, w) for n, k, w in combined if w > cap]
    top2 = sum(w for _, _, w in combined[:2])
    top10 = sum(w for _, _, w in combined)

    s = deck.content(1, "Portfolio X-ray", L["eyebrow"], L["title"])
    deck.anchor("mod:concentration", s, prio=5)
    deck.scope_tag(s, f"Direct equity + funds, scheme level · as of {as_of}")

    # ---- concentration KPIs, moved to the top so the two dense columns below have the
    # full remaining height (a bottom kpi_strip is a fixed ~0.9in footprint regardless of
    # its own h arg -- putting it under two already-tall columns is how this nearly clipped) ----
    deck.kpi_strip(s, [
        (f"{top2:.1f}%", "Top 2, incl. funds" if reg != "simple" else "Your 2 biggest"),
        (f"{top10:.1f}%", "Top 10, incl. funds" if reg != "simple" else "Your 10 biggest"),
        (f"{cap:.0f}%", "Our single-holding limit" if reg == "simple" else "IPS single-scheme cap"),
        (str(len(breaches)), "Over the cap", None, (SELL if breaches else INK)),
    ], y=1.80)
    deck.rule(s, ML, 2.76, UW, h=0.012)

    top_y = 2.90
    # ---- treemap (left) ----
    labels = [short_name(n, 16) for n, _, _ in combined]
    sizes = [w for _, _, w in combined]
    vlab = [f"{w:.1f}%" for _, _, w in combined]
    colors = [CSELL if w > cap else _RAMP[i % 4] for i, (_, _, w) in enumerate(combined)]
    tpath = CH.treemap(labels, sizes, "azby_conc_tree", colors=colors, value_labels=vlab)
    deck.pic(s, tpath, ML, top_y, 7.4, 3.05, valign="top", halign="left")
    deck.txt(s, ML, top_y + 3.10, 7.4, 0.32,
             [("Includes both direct stocks and fund schemes — a large single fund is the same "
               "concentration event as a large single stock against this cap.", SERIF, 8, SLATE,
               False, True)], ls=1.0)

    # ---- breach + AMC + sector-pointer column (right) -- each block is a callout sized to
    # its OWN text via callout_h, and every y-offset below is chained off the ACTUAL returned
    # height, never a guessed constant (guessed constants under this exact three-block layout
    # produced a real overlap on first build; see PROGRESS_FM_REVIEW_BUILD_2026-08-05.md) ----
    cx = ML + 7.65; cw = RX - cx
    y = top_y
    if breaches:
        names = ", ".join(f"{n} ({w:.1f}%)" for n, _, w in breaches[:2])
        extra = f" +{len(breaches)-2}" if len(breaches) > 2 else ""
        body = (f"{len(breaches)} over the {cap:.0f}% cap: {names}{extra}."
                if reg == "simple" else
                f"{len(breaches)} holding{'s' if len(breaches) != 1 else ''} above the {cap:.0f}% "
                f"IPS single-scheme guideline: {names}{extra}, {sum(w for _,_,w in breaches):.1f}% "
                "of the portfolio together.")
        bh = deck.callout_h(cw, body, min_h=0.65, max_h=1.75)
        deck.callout(s, cx, y, cw, bh, "SINGLE-SCHEME CAP", body, kind="warn")
    else:
        body = f"Nothing exceeds the {cap:.0f}% guideline at the scheme level; monitor on drift."
        bh = deck.callout_h(cw, body, min_h=0.55, max_h=0.85)
        deck.callout(s, cx, y, cw, bh, "SINGLE-SCHEME CAP", body, kind="good")
    y += bh + 0.14

    # ---- AMC concentration, ONE line, no table (funds only — equity has no AMC concept) ----
    amc_cap = ctx["ips"].get("single_amc_cap_pct")
    amc = list(LT.amc_concentration(ctx).items())
    if amc:
        top1a, p1a = amc[0]
        over1 = amc_cap is not None and p1a > amc_cap
        if len(amc) > 1:
            top2a, p2a = amc[1]
            # AMC names are already in their canonical short form (HDFC, LIC MF, ICICI PRU...)
            # via mf_mapping.canonical_amc() -- .title()-casing that ("Hdfc", "Lic Mf") reads
            # worse than the abbreviation itself, so it is shown as-is.
            amc_body = (f"{top1a} {p1a:.1f}%, {top2a} {p2a:.1f}%"
                        f"{', over the ' + format(amc_cap, '.0f') + '% AMC guideline' if over1 else ''}.")
        else:
            amc_body = f"{top1a} {p1a:.1f}% of the portfolio, across its funds."
    else:
        amc_body = "No fund holdings to concentrate by AMC."
    ah = deck.callout_h(cw, amc_body, min_h=0.5, max_h=1.05)
    deck.callout(s, cx, y, cw, ah, "AMC CONCENTRATION, FUNDS" if reg != "simple" else
                 "FUND HOUSES YOU USE MOST", amc_body, kind="note")

    # ---- sector, look-through: a one-line pointer in the source, not a third stacked
    # callout -- three colored boxes chained down this narrow a column (cw~3.8in) doesn't
    # fit even short copy above the churn/AMC blocks; the fact still gets a permanent line,
    # just not its own box (see PROGRESS_FM_REVIEW_BUILD_2026-08-05.md for the arithmetic) ----
    sect, sect_pct, sgap_pct, sgap_n = LT.max_sector_lookthrough(ctx)
    sect_line = (f"Largest sector incl. funds: {sect} {sect_pct:.0f}% (see Sector Exposure). "
                if sect else "")

    ips_note = ("IPS single-scheme guideline." if ctx["ips"].get("on_file", True) else
                "Guideline per house risk policy, no client IPS on file yet.")
    demo_tag = " Illustrative synthetic book." if ctx.get("is_demo", False) else ""
    deck.source(s, f"Source: holdings as of {as_of}. % of total portfolio; {ips_note} "
                   f"{sect_line}No fund holdings list exists, so concentration is not looked "
                   f"through to stocks inside a fund.{demo_tag}")
    return 1
