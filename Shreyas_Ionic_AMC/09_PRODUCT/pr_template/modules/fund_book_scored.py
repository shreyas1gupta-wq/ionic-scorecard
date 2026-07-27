# -*- coding: utf-8 -*-
"""fund_book_scored (F4/F12), the whole MF sleeve, QFRA 2.0-scored, with SENTINEL flag chips
and a SEBI-safe verdict (Hold/Trim/Switch/Redeem-to-Direct/Exit, never Buy).
Scope banner: MF sleeve only. Pairs the QFRA number with a desk human-read (rule d)."""
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, SERIF, ML, UW, short_name

MERIT_COL = {"A": HOLD, "B": NAVY, "C": AMBER, "D": SELL}
VDISP = {"Redeem-to-Direct": "To-Direct"}
# flag chips read as PLAIN WORDS (leak audit 2026-07-26), never engine codes; all <=9 chars
FLAB = {"CLOSET_INDEX": "INDEX HUG", "NEG_ALPHA": "TRAILS", "DOWN_CAP_HI": "DOWNSIDE",
        "WEAK_CONSIST": "WEAK 3-YR", "MANDATE_RIGIDITY": "RIGID", "REG_PLAN_DRAG": "COST DRAG",
        "DEEP_DD": "DEEP FALL", "CAPACITY": "TOO LARGE", "OVER_ALLOC": "OVERSIZED",
        "SUB_SCALE": "TINY FUND", "SHORT_RECORD": "NEW FUND"}

LABELS = {
    "hni":    ("The fund book, scored",
               "A 0-100 quality score on every scheme · the score is the input, the desk sets the verdict"),
    "std":    ("The fund book, scored",
               "Every scheme graded on quality, cost and structure · not just past returns"),
    "simple": ("Your funds, graded",
               "A simple quality grade for each fund, and what we suggest"),
}


def _short(name, n=27):
    return short_name(name, n)


_PER_PAGE = 9   # proven fit: 2.0 + 0.33 header + 9*0.40 rows = 5.93, clears the 6.02 read line


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    funds = ctx["funds"]
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    demo = ctx.get("is_demo", True)

    # pagination (added 2026-07-27, first real client: this module was built assuming a
    # ~9-fund demo book and silently overflowed past the read-line and footer on a 25-fund
    # real book) — one content() slide per _PER_PAGE funds, same layout proven to fit.
    n_pages = max(1, (len(funds) + _PER_PAGE - 1) // _PER_PAGE)
    n_act = sum(1 for f in funds if f["action"] not in ("HOLD", "Hold"))
    n_hold = len(funds) - n_act

    for page in range(n_pages):
        chunk = funds[page * _PER_PAGE:(page + 1) * _PER_PAGE]
        pg_title = title if n_pages == 1 else f"{title} ({page + 1} of {n_pages})"
        s = deck.content(3, "Funds", eyebrow, pg_title)
        deck.scope_tag(s, f"MF sleeve only, Direct-plan NAV, each scheme vs its own SEBI category "
                          f"benchmark (TRI) · as of {as_of}")

        if simple:
            cols = [("Scheme", 0.36, "l"), ("Category", 0.16, "l"), ("Share %", 0.12, "r"),
                    ("Quality /100", 0.18, "l"), ("Suggested", 0.24, "c")]
            rows = []
            for f in chunk:
                v = f["verdict"]
                rows.append([_short(f["name"], 30), f["category"].title(), f"{f['weight_pct']:.1f}",
                             ("bar", f["qfra"]), ("pill", VDISP.get(v, v), v)])
            deck.table(s, ML, 2.0, UW, cols, rows, rowh=0.40, fs=11, hfs=9)
        else:
            cols = [("Scheme", 0.24, "l"), ("Category", 0.10, "l"), ("Plan", 0.07, "c"),
                    ("Wt %", 0.06, "r"), ("Fund score /100", 0.13, "l"), ("Grade", 0.07, "c"),
                    ("Watch-outs", 0.23, "l"), ("Verdict", 0.13, "c")]
            rows = []
            for f in chunk:
                v = f["verdict"]
                fcell = ("flags", [FLAB.get(x, x[:9]) for x in f["flags"]]) if f["flags"] else ("c", "-", SLATE)
                rows.append([_short(f["name"]), f["category"].title(), f["plan"][:3],
                             f"{f['weight_pct']:.1f}", ("bar", f["qfra"]),
                             ("c", f["merit"], MERIT_COL.get(f["merit"], INK), True),
                             fcell, ("pill", VDISP.get(v, v), v)])
            deck.table(s, ML, 2.0, UW, cols, rows, rowh=0.40, fs=9.5, hfs=8)

        # the desk-read summary is book-level, not page-level — show it only once (last page)
        if page == n_pages - 1:
            if simple:
                read = (f"What this means: {n_act} of {len(funds)} funds could be improved, usually because "
                        f"of high fees or the wrong structure, not just weak returns. {n_hold} are worth keeping.")
            else:
                read = (f"The desk read: the fund score ranks the scheme; the Portfolio Review team sets the "
                        f"verdict. {n_act} of {len(funds)} schemes carry an action, mostly on cost and "
                        f"structure (plan, mandate rigidity, scale, consistency) rather than performance "
                        f"alone; {n_hold} are Holds on merit.")
            deck.txt(s, ML, 6.02, UW, 0.5, [(read, SERIF, 9.5, INK, False, True)], ls=1.05)
        demo_tag = " Illustrative synthetic funds." if demo else ""
        deck.source(s, "Ionic fund-quality framework · Direct-plan NAV vs each scheme's own SEBI category "
                       f"benchmark (TRI) · structural watch-outs flagged per scheme.{demo_tag}")
        deck.score_band(s)
    return n_pages
