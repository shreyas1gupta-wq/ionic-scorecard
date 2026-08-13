# -*- coding: utf-8 -*-
"""scheme_correlation (The Fund Book, core) -- Principal ruling 2026-08-06 (#24): correlation
REPLACES overlap as the main Fund Book page. His words: "yes replace add overlap ni annexure if
needed." scheme_overlap_full.py (now in the Annexure, engine.py) fabricated a holdings-overlap
score from category/AMC/hash -- ACE carries sector PERCENTAGES per fund, not a security list, so
holdings-level overlap is NOT COMPUTABLE from data on file, and the old page said so itself
("Illustrative, not final"). Scheme-LEVEL correlation is a different, honest thing: it needs only
each fund's own NAV history, which we already have -- real for a real client's ACE/NAV-store
match, and for this demo book the same synthetic daily series that already drives every capture-
ratio and alpha number elsewhere in the fund book (see `nav_history` in data/azby_family.py). "Is
available today" is therefore literal: this page computes a genuine correlation, not an
illustrative one, even on synthetic inputs.

A fund with no usable NAV history (a real client's fund not yet matched to a NAV source) is
EXCLUDED from the matrix and counted into a disclosed gap -- never smeared in as an assumption."""
import numpy as np

import chart_ext_a as CA
from slidekit import ML, RX

TOP_N = 10  # matches scheme_overlap_full.py's cap -- funds get 10, stocks get 15 (annex_correlation.py)


def _short(f):
    """Same short-nickname scheme as scheme_overlap_full.py, so a fund reads identically
    wherever it appears in the deck."""
    amc = f["amc"].split()[0]
    name_up = f["name"].upper()
    key = ""
    for k, tag in [("LARGE", "Large"), ("FLEXI", "Flexi"), ("MULTI-ASSET", "MA"),
                   ("MULTI", "Multi"), ("SMALL", "Small"), ("MIDCAP", "Mid"),
                   ("MID CAP", "Mid"), ("BALANCED", "BAF"), ("HYBRID", "Hybrid"),
                   ("ELSS", "ELSS"), ("VALUE", "Value"), ("FOCUSED", "Focus"),
                   ("DIVIDEND", "DivY"), ("NIFTY", "N50"), ("INDEX", "Idx"),
                   ("OVERNIGHT", "O/N"), ("LIQUID", "Liq"), ("GILT", "Gilt"),
                   ("SHORT", "Short"), ("ULTRA SHORT", "UST"), ("ARBITRAGE", "Arb"),
                   ("EQUITY SAVINGS", "EqSav"), ("BOND", "Bond"), ("DEBT", "Debt")]:
        if k in name_up:
            key = tag
            break
    return f"{amc[:6]} {key}".strip()


def _returns(nav_hist):
    if not nav_hist:
        return None
    a = np.asarray(nav_hist, float)
    if len(a) < 4:
        return None
    r = a[1:] / a[:-1] - 1.0
    if not np.isfinite(r).all() or r.std() == 0:
        return None
    return r


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    all_funds = ctx["funds"]
    funds = sorted(all_funds, key=lambda f: -f["weight_pct"])[:TOP_N]
    capped = len(all_funds) > TOP_N

    rets = {}
    for f in funds:
        r = _returns(f.get("nav_history"))
        if r is not None:
            rets[f["name"]] = r
    usable = [f for f in funds if f["name"] in rets]
    gap = [f for f in funds if f["name"] not in rets]

    if len(usable) < 2:
        return 0  # a correlation grid needs >=2 funds with real NAV history to be meaningful

    minlen = min(len(rets[f["name"]]) for f in usable)
    labels = [_short(f) for f in usable]
    n = len(usable)
    series = [rets[f["name"]][-minlen:] for f in usable]
    M = np.eye(n)
    for i in range(n):
        for j in range(i):
            c = float(np.corrcoef(series[i], series[j])[0, 1])
            M[i][j] = M[j][i] = c if np.isfinite(c) else 0.0

    title = ("Which funds actually move together" if reg != "simple"
             else "Do your funds move together?")
    s = deck.content(2, "The Fund Book", "Scheme correlation", title)
    scope = f"{n} of {len(all_funds)} funds" if (capped or gap) else f"All {n} funds"
    deck.scope_tag(s, f"{scope} with usable NAV history · MF sleeve only")

    png = CA.corr_heat(labels, M.tolist(), "scheme_corr")
    deck.pic(s, png, ML, 1.9, 7.4, 4.5, valign="top", halign="left")

    pairs = [(M[i][j], labels[i], labels[j]) for i in range(n) for j in range(i)]
    rx = ML + 7.65
    rw = RX - rx
    cy = 2.0
    if pairs:
        avg = sum(p[0] for p in pairs) / len(pairs)
        mx = max(pairs); mn = min(pairs)
        if reg == "simple":
            b1 = (f"Darker squares mean two funds move together. Average correlation is "
                  f"{avg:.2f}. {mx[1]}/{mx[2]} move most alike; {mn[1]}/{mn[2]} balance best.")
        else:
            b1 = (f"From each fund's own NAV history, not holdings. Average pairwise "
                  f"correlation across the {n} schemes is {avg:.2f}. {mx[1]}/{mx[2]} move most "
                  f"alike at {mx[0]:.2f}; {mn[1]}/{mn[2]} are most independent at {mn[0]:.2f}.")
        h1 = deck.callout_h(rw, b1, min_h=1.2, max_h=2.3)
        deck.callout(s, rx, cy, rw, h1, "What the funds actually share", b1, "note")
        cy += h1 + 0.15

    body2 = ("A real overlap map needs each fund's security-level holdings. We only have each "
             "fund's sector percentages, not a security list, so it cannot be honestly measured "
             "today. Correlation needs only price history, which every fund already has -- see "
             "the Annexure for the retired overlap page.")
    h2 = deck.callout_h(rw, body2, min_h=1.2, max_h=max(1.2, 6.45 - cy))
    deck.callout(s, rx, cy, rw, h2, "Why not fund overlap", body2, "human")

    demo_tag = (" Illustrative synthetic book; NAV history is a synthetic series, not a real "
                "fund's." if ctx.get("is_demo", False) else "")
    gap_txt = ""
    if gap:
        gap_txt = (f" {len(gap)} fund(s) lack usable NAV history and are excluded, not assumed: "
                   + ", ".join(g["name"] for g in gap) + ".")
    deck.source(s, "Correlation of monthly NAV returns, each fund's own history, common trailing "
                   f"window ({minlen} periods). Top {TOP_N} funds by weight."
                   f"{gap_txt}{demo_tag}")
    return 1
