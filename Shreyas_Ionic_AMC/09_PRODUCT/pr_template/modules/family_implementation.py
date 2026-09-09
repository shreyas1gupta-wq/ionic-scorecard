# -*- coding: utf-8 -*-
"""family_implementation: a family book is not one portfolio.

WHY THIS PAGE EXISTS. Every other page in this review treats the book as one thing, which is right
for allocation and wrong for execution. An instruction to sell the fixed-income sleeve falls on
whichever member happens to hold it. That member signs the instruction, realises the gain on their
own return at their own slab, and it is their own defensive allocation that goes to zero - not the
family's average.

On the book this was written for the sale fell 60% on the member whose portfolio is 45% the size of
the largest, and the review had no page on which it could say so. The holder column was in the
statement and was thrown away at the parse.

WHAT IT WILL NOT DO. It does not allocate a pooled holding to a member. Where the statement says
"FAMILY" against a deposit, the desk does not know whose it is, and guessing would put a defensive
buffer on a page against a person who may not own it. The pool is reported as a pool, with its size
and what leans on it, and the page says what document would resolve it.
"""
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from slidekit import (NAVY, GOLD, INK, SLATE, NT2, NT3, SELL, AMBER, HOLD, PANEL, HAIR, WHITE,
                      SERIF, SANS, ML, UW, RX, clip_clause)

SECTION_NO, SECTION = 4, "Recommendations"

LABELS = {
    "hni": ("Implementation across the family",
            "Who holds what, and who the plan actually lands on"),
    "std": ("Implementation across the family",
            "Who holds what, and who the plan actually lands on"),
    "simple": ("Who does what", "Which of you this affects, and by how much"),
}


def _money(v):
    if v is None:
        return "-"
    return f"Rs {v / 1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v / 1e5:.1f} L"


def _short(name, n=22):
    from slidekit import short_name
    return short_name(str(name or ""), n)


def render(deck, ctx, tier):
    F = ctx.get("family_book") or {}
    members = list(F.get("members") or [])
    pooled = list(F.get("pooled") or [])
    # ONE HOLDER IS NOT A FAMILY. A single-name book has no allocation question between people, so
    # the page renders nothing rather than a table with one row in it.
    if len(members) + len(pooled) < 2:
        return 0

    reg = tier.get("register", "std")
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(SECTION_NO, SECTION, eyebrow, title)
    deck.anchor("mod:family", s, prio=6)
    grand = F.get("grand_inr") or 1.0

    # ---- the table --------------------------------------------------------------------------
    if reg == "simple":
        cols = [("Held by", 0.22, "l"), ("Their portfolio", 0.16, "r"),
                ("Share of the family", 0.14, "r"), ("Being sold", 0.16, "r"),
                ("Share of the selling", 0.16, "r"), ("Safe assets left after", 0.16, "r")]
    else:
        cols = [("Holder", 0.20, "l"), ("Value", 0.14, "r"), ("% of family", 0.11, "r"),
                ("Moving", 0.14, "r"), ("% of own book", 0.13, "r"),
                ("% of the plan", 0.13, "r"), ("Defensive after", 0.15, "r")]

    rows = []
    for m in members:
        r = [("b", _short(m["name"], 24)),
             _money(m["value_inr"]),
             f"{m.get('share_pct', 0):.1f}%",
             _money(m.get("moving_inr")),
             f"{m.get('moving_pct_of_own', 0):.1f}%"]
        if reg != "simple":
            r.append(f"{m.get('share_of_plan_pct', 0):.1f}%")
        # THE NUMBER THIS PAGE EXISTS FOR. A member left with no defensive assets of their own is
        # not visible on any family-level allocation page, because the family average hides it.
        _after = m.get("defensive_after_pct", 0.0)
        r.append(("c", f"{_after:.1f}%", SELL if _after < 1.0 else
                  AMBER if _after < 5.0 else INK))
        rows.append(r if reg != "simple" else
                    [r[0], r[1], r[2], r[3], r[4], r[-1]])

    for p in pooled:
        lab = "Pooled, holder not stated"
        r = [("b", lab), _money(p["value_inr"]), f"{p.get('share_pct', 0):.1f}%",
             ("c", "not attributable", SLATE), "-"]
        if reg != "simple":
            r.append("-")
        r.append(("c", "-", SLATE))
        rows.append(r if reg != "simple" else [r[0], r[1], r[2], r[3], r[4], r[-1]])

    # tighter than the deck's usual pitch on purpose: the two notes underneath carry the
    # finding, and a table that takes their room drops one of them off the page unseen.
    rowh = max(0.30, min(0.40, 2.1 / max(1, len(rows))))
    y = deck.table(s, ML, 2.02, UW, cols, rows, rowh=rowh, fs=9.5, hfs=8) + 0.22

    # ---- who the plan lands on --------------------------------------------------------------
    _mv = [m for m in members if (m.get("moving_inr") or 0) > 0]
    lead = ""
    if _mv:
        # the member carrying the largest share of the plan against the size of their own book
        _worst = max(_mv, key=lambda m: (m.get("share_of_plan_pct") or 0)
                     - (m.get("share_pct") or 0))
        _gap = (_worst.get("share_of_plan_pct") or 0) - (_worst.get("share_pct") or 0)
        if _gap >= 5.0:
            lead = ("%s holds %.0f%% of the family's money and carries %.0f%% of what is being "
                    "sold. The instruction and the gain land on one person's return."
                    % (_short(_worst["name"], 26), _worst.get("share_pct") or 0,
                       _worst.get("share_of_plan_pct") or 0))
        else:
            lead = ("What is being sold is spread across the family in rough proportion to what "
                    "each member holds. No one person carries the plan.")
    # ONLY THE MEMBERS THE PLAN ACTUALLY STRIPS. A member who never held a defensive asset also
    # reads 0.0% after, and naming them here says the plan took something it never touched.
    _bare = [m for m in members
             if (m.get("defensive_inr") or 0) > 0
             and (m.get("defensive_after_pct") or 0) < 1.0]
    if _bare:
        lead += (" After it runs, %s %s no defensive assets of their own."
                 % (", ".join(_short(m["name"], 20) for m in _bare[:3]),
                    "has" if len(_bare) == 1 else "have"))

    # TWO CALLOUTS SHARE WHAT THE TABLE LEAVES. The pool note is a finding, not decoration, so it
    # is never the one that gets dropped: the space is divided before either is drawn, and each is
    # written to fit its half. Laid out one after the other, the second ran past the source line
    # and vanished without a trace on the finished page.
    _avail = 6.45 - y
    _two = bool(lead) and bool(pooled)
    _hw = (UW - 0.30) / 2 if _two else UW
    _cap = min(1.55, _avail - 0.05) if _two else min(1.30, _avail - 0.05)
    if lead:
        h = deck.callout_h(_hw, lead, min_h=0.72, max_h=_cap)
        deck.callout(s, ML, y, _hw, h,
                     ("Who this lands on" if reg != "simple" else "Who this affects most"),
                     lead, kind="human")

    # ---- the pool, which is a finding and not a footnote ------------------------------------
    if pooled:
        pv = F.get("pooled_inr") or 0.0
        body = ("%s, %.0f%% of the book, is recorded against the family and not a member. It is "
                "also the defensive money left after the plan runs, so the split is a "
                "precondition, not housekeeping. The account statements would settle it."
                % (_money(pv), pv / grand * 100))
        if reg == "simple":
            body = ("%s is recorded against the family, not any one of you. It is also the safe "
                    "money left after these changes, so please tell us who holds each account."
                    % _money(pv))
        body = clip_clause(body, 300 if _two else 520)
        h2 = deck.callout_h(_hw, body, min_h=0.72, max_h=_cap)
        _x = ML + (_hw + 0.30 if _two else 0.0)
        deck.callout(s, _x, y, _hw, h2, "What we cannot attribute", body, kind="warn")

    deck.source(s, "Holder as recorded on the statement. A gain shown against a member is realised "
                   "on that member's own return at that member's own slab; the exemption under "
                   "section 112A is per person per year. Nothing here is a tax opinion.")
    return 1
