# -*- coding: utf-8 -*-
"""Annexure, Scheme overlap & redundancy (F17): an illustrative fund-vs-fund overlap heatmap
(placeholder until the PIT look-through feed is wired), with the OVERLAP formula note (CH.heatmap).
Capped to the top 10 funds by weight (2026-07-29, permanent) -- an uncapped matrix stops being
readable well before a 30-fund book."""
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

    title = ("Where funds re-buy the same exposure"
             if reg != "simple" else "Funds that own many of the same shares")
    s = deck.content(3, "The Fund Book", "Scheme overlap & redundancy", title)
    if capped:
        deck.scope_tag(s, f"Top {TOP_N} of {len(all_funds)} funds by weight · MF sleeve only")
    else:
        deck.scope_tag(s, f"All {n} funds · MF sleeve only")
    deck.pic(s, png, ML, 1.9, 7.4, 4.5, valign="top", halign="left")

    rx = ML + 7.65
    rw = RX - rx
    if reg == "simple":
        b1 = ("Darker squares mean two funds own many of the same shares. A lot of overlap means you "
              "are paying two fees for one bet.")
    else:
        b1 = ("Each cell is the weighted common holding between two schemes: OVERLAP(A,B) = Σ min(w-A, "
              "w-B). Darker = more duplication · you pay two active fees for one underlying exposure.")
    deck.callout(s, rx, 2.0, rw, 2.0, "How to read it", b1, "note")
    deck.callout(s, rx, 4.1, rw, 1.95, "Illustrative, not final",
                 "These values are illustrative. The exact map needs each fund's point-in-time "
                 "look-through holdings, which we build from the funds' published portfolio "
                 "disclosures.", "warn")
    deck.source(s, "Illustrative overlap placeholder · full pairwise look-through pending the "
                   "funds' published portfolio disclosures. MF sleeve only.")
    return 1
