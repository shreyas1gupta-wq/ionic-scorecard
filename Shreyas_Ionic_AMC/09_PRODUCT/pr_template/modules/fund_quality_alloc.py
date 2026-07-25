# -*- coding: utf-8 -*-
"""fund_quality_alloc (F16), the overlay. Fund quality (QFRA) x allocation gap vs house view.
Two axes because a good fund can be oversized and a weak fund underweight, one axis mis-prescribes.
Quadrants: over+low = trim-then-exit (top priority); over+high = trim to target, keep;
under+high = retain/redeployment target; under+low = switch the vehicle."""
import charts as CH
from chart_lib import SELL as CC_SELL, HOLD as CC_HOLD, GOLD as CC_GOLD, NT2 as CC_NT2
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, SERIF, ML, UW, RX

LABELS = {
    "hni":    ("Fund quality × allocation", "Two questions at once: is it good, and do we own the right amount?"),
    "std":    ("Fund quality × allocation", "Where each fund sits on quality and on how much we hold"),
    "simple": ("Good fund, right size?", "A good fund can still be too big; a weak one too small"),
}


def _short(name, n=16):
    name = name.replace(" Fund", "").replace(" (Regular)", "").replace(" (Direct)", "")
    return name if len(name) <= n else name[:n - 1] + "…"


def _ccol(f):
    return {"EXIT": CC_SELL, "HOLD": CC_HOLD}.get(f["action"], CC_GOLD)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    funds = ctx["funds"]
    n = len(funds)
    avg = sum(f["weight_pct"] for f in funds) / n            # equal-weight reference
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(3, "Funds", eyebrow, title)
    deck.scope_tag(s, f"MF sleeve only · quality = QFRA score · allocation gap vs equal-weight reference · as of {ctx['client']['as_of']}")

    gap = [round(f["weight_pct"] - avg, 1) for f in funds]    # + = over-allocated
    quality = [f["qfra"] for f in funds]
    sizes = [f["value_inr"] for f in funds]
    colors = [_ccol(f) for f in funds]
    labels = [_short(f["name"], 15) for f in funds]
    png = CH.quality_alloc_quadrant(gap, quality, sizes, colors, labels, "fqa_quad")
    deck.pic(s, png, ML, 1.95, 6.7, 4.4, valign="top")

    # right-hand prescriptions
    tx = 7.85; tw = RX - tx
    over_low = [f for f, g in zip(funds, gap) if g > 0 and f["qfra"] < 50]
    over_hi = [f for f, g in zip(funds, gap) if g > 0 and f["qfra"] >= 50]
    under_low = [f for f, g in zip(funds, gap) if g <= 0 and f["qfra"] < 50]
    rows = [
        ("Over-sized · low quality", "Trim, then exit (first priority)", SELL, over_low),
        ("Over-sized · high quality", "Trim to target, keep the fund", AMBER, over_hi),
        ("Under-sized · low quality", "Switch the vehicle", AMBER, under_low),
    ]
    y = 2.05
    deck.txt(s, tx, y, tw, 0.3, [("WHAT EACH QUADRANT MEANS", "Bahnschrift", 9, SLATE, True, False, 80)]); y += 0.4
    for head, action, col, members in rows:
        names = ", ".join(_short(m["name"], 18) for m in members) if members else "none today"
        deck.rect(s, tx, y, tw, 0.86, fill=None, line=col, lw=1.0, round_=0.06)
        deck.rect(s, tx, y, 0.05, 0.86, fill=col)
        deck.txt(s, tx + 0.16, y + 0.10, tw - 0.3, 0.24, [(head, "Bahnschrift", 9.5, col, True)])
        deck.txt(s, tx + 0.16, y + 0.34, tw - 0.3, 0.24, [(action, SERIF, 10, INK, False, True)])
        deck.txt(s, tx + 0.16, y + 0.58, tw - 0.3, 0.24, [(names, SERIF, 8.5, SLATE, False)])
        y += 0.98

    deck.source(s, "Allocation gap = fund weight minus the equal-weight reference (illustrative; a live "
                   "review uses the house-view category bands). Quality = QFRA. Synthetic demo funds.")
    return 1
