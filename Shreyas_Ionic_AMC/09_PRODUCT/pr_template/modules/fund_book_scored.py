# -*- coding: utf-8 -*-
"""fund_book_scored (F4/F12), the whole MF sleeve, QFRA 2.0-scored, with SENTINEL flag chips
and a SEBI-safe verdict (Hold/Trim/Switch/Redeem-to-Direct/Exit, never Buy).
Scope banner: MF sleeve only. Pairs the QFRA number with a desk human-read (rule d)."""
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, SERIF, ML, UW

MERIT_COL = {"A": HOLD, "B": NAVY, "C": AMBER, "D": SELL}
VDISP = {"Redeem-to-Direct": "To-Direct"}

LABELS = {
    "hni":    ("The fund book, scored",
               "QFRA 2.0 quality read on every scheme · the score is the input, the desk sets the verdict"),
    "std":    ("The fund book, scored",
               "Every scheme graded on quality, cost and structure · not just past returns"),
    "simple": ("Your funds, graded",
               "A simple quality grade for each fund, and what we suggest"),
}


def _short(name, n=27):
    name = name.replace(" Fund", "").replace(" (Regular)", " (Reg)").replace(" (Direct)", " (Dir)")
    return name if len(name) <= n else name[:n - 1] + "…"


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    funds = ctx["funds"]
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])

    s = deck.content(3, "Funds", eyebrow, title)
    deck.scope_tag(s, f"MF sleeve only, Direct-plan NAV vs total-return benchmark · as of {as_of}")

    if simple:
        cols = [("Scheme", 0.36, "l"), ("Category", 0.16, "l"), ("Wt %", 0.12, "r"),
                ("Quality /100", 0.18, "l"), ("Suggested", 0.24, "c")]
        rows = []
        for f in funds:
            v = f["verdict"]
            rows.append([_short(f["name"], 24), f["category"].title(), f"{f['weight_pct']:.1f}",
                         ("bar", f["qfra"]), ("pill", VDISP.get(v, v), v)])
        deck.table(s, ML, 2.0, UW, cols, rows, rowh=0.40, fs=11, hfs=9)   # 2.0+0.33+9x0.40=5.93, clears the 6.02 read line
    else:
        cols = [("Scheme", 0.24, "l"), ("Category", 0.10, "l"), ("Plan", 0.07, "c"),
                ("Wt %", 0.06, "r"), ("QFRA /100", 0.13, "l"), ("Merit", 0.07, "c"),
                ("SENTINEL flags", 0.23, "l"), ("Verdict", 0.13, "c")]
        rows = []
        for f in funds:
            v = f["verdict"]
            fcell = ("flags", f["flags"]) if f["flags"] else ("c", ", ", SLATE)
            rows.append([_short(f["name"]), f["category"].title(), f["plan"][:3],
                         f"{f['weight_pct']:.1f}", ("bar", f["qfra"]),
                         ("c", f["merit"], MERIT_COL.get(f["merit"], INK), True),
                         fcell, ("pill", VDISP.get(v, v), v)])
        deck.table(s, ML, 2.0, UW, cols, rows, rowh=0.40, fs=9.5, hfs=8)

    n_act = sum(1 for f in funds if f["action"] not in ("HOLD", "Hold"))
    n_hold = len(funds) - n_act
    if simple:
        read = (f"What this means: {n_act} of {len(funds)} funds could be improved, usually because of "
                f"high fees or the wrong structure, not just weak returns. {n_hold} are worth keeping.")
    else:
        read = (f"The desk read: QFRA scores the scheme; the Portfolio Review team sets the verdict. "
                f"{n_act} of {len(funds)} schemes carry an action, mostly on cost and structure "
                f"(plan, mandate rigidity, scale, consistency) rather than performance alone; "
                f"{n_hold} are Holds on merit.")
    deck.txt(s, ML, 6.02, UW, 0.5, [(read, SERIF, 9.5, INK, False, True)], ls=1.05)
    deck.source(s, "QFRA 2.0 (frozen engine) · Direct-plan NAV vs total-return benchmark · "
                   "SENTINEL flag ledger. Illustrative synthetic funds.")
    deck.score_band(s)
    return 1
