# -*- coding: utf-8 -*-
"""Annexure, Scheme overlap & redundancy (F17): an illustrative fund-vs-fund overlap heatmap
(placeholder until a security-level look-through feed exists), with the OVERLAP formula note
(CH.heatmap). Capped to the top 10 funds by weight (2026-07-29, permanent) -- an uncapped matrix
stops being readable well before a 30-fund book.

MOVED to the Annexure 2026-08-06 (Principal ruling #24: "yes replace add overlap ni annexure if
needed") -- scheme_correlation.py, computed from real NAV history, is now the main Fund Book page;
this stays available on request. Disclosure strengthened the same day: our data source (ACE)
carries each fund's SECTOR PERCENTAGES, never a security list, so a real holdings-overlap number
is not computable from data on file today, not merely unbuilt yet -- the copy below says so
plainly rather than implying it is a matter of more engineering time."""
import charts as CH
from slidekit import ML, UW, RX


def _short(f):
    """Deliberate short nicknames for heatmap axes — never a mid-word chop
    ('ICICI M-Asse'); every label must be a whole word/abbreviation.
    Case-insensitive keyword scan with a wide keyword list so same-AMC funds
    (e.g. two Mirae or two HDFC schemes) get distinct labels."""
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
                   ("EQUITY SAVINGS", "EqSav")]:
        if k in name_up:
            key = tag
            break
    return f"{amc[:6]} {key}".strip()


def _ov(a, b, i, j):
    if i == j:
        return 100
    v = 10
    if a["category"] == b["category"]:
        v += 24
    if a["amc"] == b["amc"]:
        v += 16
    # equity + passive large-cap tend to overlap regardless of house
    cats = {a["category"], b["category"]}
    if "passive" in cats and ("equity" in cats or "passive" == a["category"] == b["category"]):
        v += 14
    h = abs(hash((min(a["name"], b["name"]), max(a["name"], b["name"])))) % 14
    return min(72, v + h)


TOP_N = 10  # 2026-07-29 (permanent): a fund-vs-fund matrix stops being readable well before a
            # 30-fund book -- cap to the top 10 by holding weight, same rule as annex_correlation.py


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    all_funds = ctx["funds"]
    funds = sorted(all_funds, key=lambda f: -f["weight_pct"])[:TOP_N]
    capped = len(all_funds) > TOP_N
    labels = [_short(f) for f in funds]
    n = len(funds)
    M = [[_ov(funds[i], funds[j], i, j) for j in range(n)] for i in range(n)]
    png = CH.heatmap(labels, labels, M, "annex_overlap", fmt="{:.0f}", vmax=100)

    title = ("Where funds might re-buy the same exposure, illustrated"
             if reg != "simple" else "Funds that may own similar shares")
    s = deck.content(5, "Annexure", "Scheme overlap & redundancy", title)
    if capped:
        deck.scope_tag(s, f"[ILLUSTRATIVE] Top {TOP_N} of {len(all_funds)} funds by weight · MF sleeve only")
    else:
        deck.scope_tag(s, f"[ILLUSTRATIVE] All {n} funds · MF sleeve only")
    deck.pic(s, png, ML, 1.9, 7.4, 4.5, valign="top", halign="left")

    rx = ML + 7.65
    rw = RX - rx
    if reg == "simple":
        b1 = ("Darker squares mean two funds may own many of the same shares. A lot of overlap "
              "would mean paying two fees for one bet -- but these numbers are illustrative, not "
              "measured. See the fund correlation page in the Fund Book for a real read.")
    else:
        b1 = ("Each cell is an ILLUSTRATIVE weighted common-holding proxy between two schemes: "
              "OVERLAP(A,B) = Σ min(w-A, w-B), estimated from category and AMC, not from actual "
              "positions. Darker = more estimated duplication. See scheme_correlation (Fund Book) "
              "for the real, NAV-based read.")
    cy = 2.0
    h1 = deck.callout_h(rw, b1, min_h=1.3, max_h=1.75) + 0.30  # +pad: check_geometry2's own
    deck.callout(s, rx, cy, rw, h1, "How to read it", b1, "note")               # text estimate
    cy += h1 + 0.15                                                             # runs hotter than
    b2 = ("The fund data available to us carries only each fund's SECTOR "      # callout_h's for
          "percentages, never a security list -- not a gap more time closes, "  # this narrow a
          "a structural limit of what is disclosed to us. Every value on this " # column; padded
          "page is illustrative, never a measured figure.")                     # rather than
    h2 = min(6.50 - cy, deck.callout_h(rw, b2, min_h=1.3, max_h=6.50 - cy) + 0.30)  # re-derive it
    deck.callout(s, rx, cy, rw, h2, "Why this page cannot be real", b2, "warn")
    deck.source(s, "[ILLUSTRATIVE] Estimated from fund category and AMC, not from actual holdings "
                   "-- a real pairwise look-through needs a security-level portfolio feed no "
                   "current source provides. MF sleeve only. Kept in the Annexure on request; "
                   "the Fund Book's main correlation page is the measured alternative.")
    return 1
