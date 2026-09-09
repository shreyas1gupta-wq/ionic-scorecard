# -*- coding: utf-8 -*-
"""return_arithmetic: what the client's own target requires of the part of the book that can move.

WHY THIS IS NOT A PROJECTION. The growth-projection page shows what THIS book might do, from this
book's own holdings. This page runs the arithmetic the other way: the client has stated a number,
part of the book cannot carry that mandate, and the question is what the rest would have to
compound at for the stated number to arrive. It is a constraint, not a forecast, and it is the
single most useful thing a review can say to a client who has named a return.

WHY IT IS NOT A BUY. It recommends nothing and names no product. It says what a stated ambition
costs in required return, and where that required return is not a number this desk would put in
front of anybody, it says so. Restating a target as unreachable is the opposite of a solicitation.

IT DOES NOT RENDER WITHOUT A STATED TARGET. A target nobody stated is a target this desk invented,
and every figure on this page would then be arithmetic on a number the client never gave. Absent
--target-return the page is not built.

THE DEFENSIVE YIELD IS AN ASSUMPTION AND SAYS SO. It is passed in, printed on the page, and
attributed to the desk rather than to any file.
"""
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from slidekit import (NAVY, GOLD, INK, SLATE, NT2, NT3, SELL, AMBER, HOLD, PANEL, HAIR, WHITE,
                      SERIF, SANS, ML, UW, RX)

SECTION_NO, SECTION = 4, "Recommendations"

# Above this, a required compounding rate is not a number this desk will present as achievable.
# It is not a forecast either way; it is the line past which the page stops implying feasibility.
IMPLAUSIBLE = 20.0
STRETCHED = 16.0

LABELS = {
    "hni": ("What your target requires", "The return ambition, and what it asks of the money that can move"),
    "std": ("What your target requires", "The return ambition, and what it asks of the money that can move"),
    "simple": ("What your goal would need", "What the rest of the money would have to earn"),
}


def _money(v):
    return f"Rs {v / 1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v / 1e5:.1f} L"


def _required(target, defensive_share, defensive_yield):
    """The growth sleeve's required CAGR for the blend to reach `target`.

    A blend, not a compounding of a blend: the two sleeves are held side by side over the same
    horizon, so the arithmetic that matters to a client in the room is the weighted one.
    """
    g = 1.0 - defensive_share
    if g <= 0.0001:
        return None
    return (target - defensive_share * defensive_yield) / g


def render(deck, ctx, tier):
    T = ctx.get("return_target") or {}
    lo = T.get("low_pct")
    if not lo:
        return 0

    reg = tier.get("register", "std")
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(SECTION_NO, SECTION, eyebrow, title)
    hi = T.get("high_pct")
    dy = float(T.get("defensive_yield_pct") or 6.5)
    grand = (ctx.get("totals") or {}).get("grand_inr") or 1.0
    immovable = float(T.get("immovable_inr") or 0.0)
    imm_share = immovable / grand if grand else 0.0

    targets = [t for t in (lo, hi) if t]
    band = (f"{lo:.0f}%" if not hi else f"{lo:.0f} to {hi:.0f}%")

    deck.kpi_strip(s, [
        (band, "Your stated ambition", "a year, after costs", NAVY),
        (f"{T.get('defensive_pct_now', 0):.0f}%", "In fixed income and cash",
         "today, whole book", INK),
        (_money(immovable), "Cannot carry the mandate",
         f"{imm_share * 100:.0f}% of the book", AMBER if imm_share > 0.15 else NT2),
    ], y=1.8)

    # ---- the table: required growth return at a range of defensive shares ------------------
    shares = [0.10, 0.15, 0.20, 0.30, 0.40]
    # the book's own share, and the immovable share, both marked where they land
    _own = round(float(T.get("defensive_pct_now") or 0) / 100, 2)
    for extra in (_own, round(imm_share, 2)):
        if extra and 0.02 < extra < 0.75 and extra not in shares:
            shares.append(extra)
    shares = sorted(set(shares))

    cols = [("Held outside the growth sleeve", 0.34, "l")]
    for t in targets:
        cols.append((f"To blend to {t:.0f}%", 0.66 / len(targets), "r"))
    if reg == "simple":
        cols[0] = ("Kept safe", 0.34, "l")

    rows, worst = [], 0.0
    for sh in shares:
        tag = ""
        if abs(sh - _own) < 0.005:
            tag = "  the book today"
        elif abs(sh - imm_share) < 0.005:
            tag = "  cannot move"
        r = [("b", f"{sh * 100:.0f}%{tag}")]
        for t in targets:
            req = _required(t, sh, dy)
            if req is None:
                r.append("-")
                continue
            worst = max(worst, req)
            col = SELL if req >= IMPLAUSIBLE else AMBER if req >= STRETCHED else INK
            r.append(("c", f"{req:.1f}%", col))
        rows.append(r)

    deck.table(s, ML, 3.05, UW, cols, rows, rowh=0.36, fs=10, hfs=8)

    # ---- the read ---------------------------------------------------------------------------
    # THE SAME ROUNDED SHARE THE TABLE ROW USES. Struck on the unrounded share instead, the
    # sentence quoted 22.4% against a table cell reading 22.5% for the identical case, and a
    # reader who checks one number against the other stops trusting both.
    _req_at_imm = _required(max(targets), round(imm_share, 2), dy) if imm_share else None
    if _req_at_imm is not None and _req_at_imm >= IMPLAUSIBLE:
        body = (
            "%s, %.0f%% of the book, cannot carry an aggressive mandate: it is in another "
            "member's name or cannot be redeemed on request. Set it aside and the rest must "
            "compound at %.1f%% for the blend to reach %.0f%% - not a number this desk will "
            "present as achievable. The %s is reachable on the part of the book that can be "
            "invested for it; agree which of the two it is a target for."
            % (_money(immovable), imm_share * 100, _req_at_imm, max(targets), band))
        kind, ttl = "warn", "The target and the book do not yet agree"
    elif worst >= STRETCHED:
        body = ("The ambition is reachable, but not with a large defensive sleeve. At the book's "
                "current %.0f%% in fixed income and cash the growth sleeve would need %.1f%% a "
                "year; every point moved out of the defensive sleeve takes roughly a fifth of a "
                "point off what the rest has to earn."
                % (T.get("defensive_pct_now", 0), _required(max(targets), _own, dy) or 0.0))
        kind, ttl = "note", "What it asks of the growth sleeve"
    else:
        body = ("The ambition sits inside what an equity-led book has historically delivered, at "
                "the defensive shares in the table. The work is in the holdings, not in the "
                "allocation arithmetic.")
        kind, ttl = "note", "What it asks of the growth sleeve"

    if reg == "simple":
        body = ("The safer part of your money earns less, so the rest has to earn more to get to "
                "your goal. The table shows how much more. Where the number turns red, the goal "
                "is asking more of the investments than we would promise.")

    # THE SOURCE LINE SITS AT 6.66. A box starting at 5.55 has 1.05in before it runs into that,
    # and text past the box edge is invisible in PowerPoint's own view - so the bound is the
    # geometry, not the sentence, and the sentence is written to fit it.
    h = deck.callout_h(UW, body, min_h=0.9, max_h=1.05)
    deck.callout(s, ML, 5.55, UW, min(h, 1.05), ttl, body, kind=kind)

    deck.source(s, "A weighted blend of the two sleeves over one horizon, not a compounding "
                   "projection. The defensive sleeve is assumed to yield %.1f%% a year: that is "
                   "the desk's assumption, stated here, and not a figure from any statement. "
                   "Nothing on this page recommends a purchase." % dy)
    return 1
