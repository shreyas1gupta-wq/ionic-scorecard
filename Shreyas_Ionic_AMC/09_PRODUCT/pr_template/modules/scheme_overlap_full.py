# -*- coding: utf-8 -*-
"""Annexure, Scheme overlap & redundancy (F17): an illustrative fund-vs-fund overlap heatmap
(placeholder until the PIT look-through feed is wired), with the OVERLAP formula note (CH.heatmap)."""
import charts as CH
from slidekit import ML, UW, RX


def _short(f):
    amc = f["amc"].split()[0]
    key = ""
    for k in ("Large", "Flexi", "Multi-Asset", "Multi", "Small", "Balanced", "Nifty"):
        if k in f["name"]:
            key = k
            break
    key = {"Multi-Asset": "M-Asset", "Balanced": "BAF", "Nifty": "N50"}.get(key, key)
    return (f"{amc[:6]} {key}").strip()[:12]


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


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    funds = ctx["funds"]
    labels = [_short(f) for f in funds]
    n = len(funds)
    M = [[_ov(funds[i], funds[j], i, j) for j in range(n)] for i in range(n)]
    png = CH.heatmap(labels, labels, M, "annex_overlap", fmt="{:.0f}", vmax=100)

    title = ("Where funds re-buy the same exposure"
             if reg != "simple" else "Funds that own many of the same shares")
    s = deck.content(5, "Annexure", "Scheme overlap & redundancy", title)
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
                 "look-through holdings, which the Data Office feed will supply.", "warn")
    deck.source(s, "Illustrative overlap placeholder · full pairwise look-through pending the PIT "
                   "holdings feed (Data Office). MF sleeve only.")
    return 1
