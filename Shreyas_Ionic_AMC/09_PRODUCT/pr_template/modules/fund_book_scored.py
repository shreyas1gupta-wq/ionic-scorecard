# -*- coding: utf-8 -*-
"""fund_book_scored (F4/F12), the whole MF sleeve, quality-scored, with plain-word flag chips
and a SEBI-safe verdict (Hold/Trim/Switch/Redeem-to-Direct/Exit, never Buy).
Scope banner: MF sleeve only. Pairs the fund score with a desk human-read (rule d).

FM #25 churn/priority split: this IS "the existing table" the spec means for the fund sleeve —
below the FM's 20% churn trigger it renders exactly as before (one list, no Priority column). At
or above the trigger it adds a Priority column and groups rows under subhead rows (High/Low
priority actions, then Holds), using only existing table cell types — no new page, no layout
change, per the spec's explicit instruction."""
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, SERIF, ML, UW, short_name

MERIT_COL = {"A": HOLD, "B": NAVY, "C": AMBER, "D": SELL}
VDISP = {"Redeem-to-Direct": "Switch"}  # display label only (Principal 2026-07-27); internal verdict code unchanged
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


_SUBHEAD_BG = None  # subhead rows use the ("b", text) bold cell -- no new table primitive needed


def _subhead_row(ncols, text):
    return [("b", text.upper())] + [""] * (ncols - 1)


def _ordered_with_subheads(funds, split_required, simple):
    """Below the 20% churn trigger: original order, no subheads, no Priority column (FM #25 —
    'one list, unsegmented'). At or above it: High-priority actions, then Low-priority actions,
    then Holds, each under a subhead row built from existing cell types."""
    if not split_required:
        return [("row", f) for f in funds], False
    high = [f for f in funds if f.get("sell_priority") == "High"]
    low = [f for f in funds if f.get("sell_priority") == "Low"]
    holds = [f for f in funds if f not in high and f not in low]
    out = []
    if high:
        out.append(("sub", "High priority" if not simple else "Do this first"))
        out += [("row", f) for f in high]
    if low:
        out.append(("sub", "Low priority" if not simple else "Can wait"))
        out += [("row", f) for f in low]
    if holds:
        out.append(("sub", "Hold" if not simple else "Keep"))
        out += [("row", f) for f in holds]
    return out, True


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    funds = ctx["funds"]
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    demo = ctx.get("is_demo", False)
    churn = ctx.get("fund_churn", {})
    split = bool(churn.get("split_required"))

    entries, has_subheads = _ordered_with_subheads(funds, split, simple)
    n_act = sum(1 for f in funds if f["action"] not in ("HOLD", "Hold"))
    n_hold = len(funds) - n_act

    # pagination (added 2026-07-27, first real client: this module was built assuming a
    # ~9-fund demo book and silently overflowed past the read-line and footer on a 25-fund
    # real book) — one content() slide per _PER_PAGE entries, same layout proven to fit.
    # Subhead rows count as rows on purpose: they still take real vertical space in the table.
    n_pages = max(1, (len(entries) + _PER_PAGE - 1) // _PER_PAGE)

    for page in range(n_pages):
        chunk = entries[page * _PER_PAGE:(page + 1) * _PER_PAGE]
        pg_title = title if n_pages == 1 else f"{title} ({page + 1} of {n_pages})"
        s = deck.content(2, "The Fund Book", eyebrow, pg_title)
        scope = (f"MF sleeve only, Direct-plan NAV, each scheme vs its own SEBI category "
                f"benchmark (TRI) · as of {as_of}")
        if has_subheads:
            scope += (f" · churn {churn['pct']:.0f}% of the portfolio, above the 20% trigger, "
                      "so actions are split by priority")
        deck.scope_tag(s, scope)

        if simple:
            ncols = 5
            cols = [("Scheme", 0.32, "l"), ("Category", 0.14, "l"), ("Share %", 0.10, "r"),
                    ("Quality /100", 0.16, "l"), ("Suggested", 0.19, "c")]
            if has_subheads:
                cols = [("Scheme", 0.28, "l"), ("Category", 0.12, "l"), ("Share %", 0.09, "r"),
                        ("Quality /100", 0.15, "l"), ("Suggested", 0.17, "c"), ("Priority", 0.19, "c")]
                ncols = 6
            rows = []
            for kind, item in chunk:
                if kind == "sub":
                    rows.append(_subhead_row(ncols, item)); continue
                f = item; v = f["verdict"]
                row = [_short(f["name"], 30), f["category"].replace("_", " ").title(),
                       f"{f['weight_pct']:.1f}", ("bar", f["qfra"]), ("pill", VDISP.get(v, v), v)]
                if has_subheads:
                    prio = f.get("sell_priority")
                    row.append(("c", prio, (SELL if prio == "High" else (AMBER if prio == "Low" else SLATE)), True)
                               if prio else ("c", "-", SLATE))
                rows.append(row)
            deck.table(s, ML, 2.0, UW, cols, rows, rowh=0.40, fs=11, hfs=9)
        else:
            ncols = 8
            cols = [("Scheme", 0.22, "l"), ("Category", 0.09, "l"), ("Plan", 0.06, "c"),
                    ("Wt %", 0.06, "r"), ("Fund score /100", 0.12, "l"), ("Grade", 0.06, "c"),
                    ("Watch-outs", 0.20, "l"), ("Verdict", 0.10, "c")]
            if has_subheads:
                # Watch-outs kept WIDER than the no-priority layout, not narrower: a 3-flag row
                # (e.g. DEEP FALL/TRAILS/OVERSIZED) overlapped into Verdict the first time this
                # shrank to make room for Priority -- taken from Category/Plan/Grade instead,
                # which never carry more than one short token.
                cols = [("Scheme", 0.18, "l"), ("Cat.", 0.07, "l"), ("Plan", 0.05, "c"),
                        ("Wt %", 0.06, "r"), ("Fund score /100", 0.11, "l"), ("Grade", 0.05, "c"),
                        ("Watch-outs", 0.21, "l"), ("Verdict", 0.09, "c"), ("Priority", 0.08, "c")]
                ncols = 9
            rows = []
            for kind, item in chunk:
                if kind == "sub":
                    rows.append(_subhead_row(ncols, item)); continue
                f = item; v = f["verdict"]
                fcell = ("flags", [FLAB.get(x, x[:9]) for x in f["flags"]]) if f["flags"] else ("c", "-", SLATE)
                m = f["merit"]
                grade_cell = ("c", m, MERIT_COL.get(m, INK), True) if m else ("c", "-", SLATE)
                row = [_short(f["name"]), f["category"].replace("_", " ").title(), f["plan"][:3],
                       f"{f['weight_pct']:.1f}", ("bar", f["qfra"]), grade_cell, fcell,
                       ("pill", VDISP.get(v, v), v)]
                if has_subheads:
                    prio = f.get("sell_priority")
                    row.append(("c", prio, (SELL if prio == "High" else (AMBER if prio == "Low" else SLATE)), True)
                               if prio else ("c", "-", SLATE))
                rows.append(row)
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
                        f"alone; {n_hold} are Holds on their own standing.")
            if has_subheads:
                read += (f" Churn is {churn['pct']:.0f}% of the portfolio, above our 20% trigger, "
                        "so actions above are grouped by priority."
                        if not simple else
                        f" That's a lot of changes at once, so we've split them into do-first and "
                        "can-wait.")
            deck.txt(s, ML, 6.02, UW, 0.5, [(read, SERIF, 9.5, INK, False, True)], ls=1.05)
        demo_tag = " Illustrative synthetic funds." if demo else ""
        deck.source(s, "Ionic fund-quality framework · Direct-plan NAV vs each scheme's own SEBI category "
                       "benchmark (TRI) · watch-outs flagged per scheme; grade weighs more than the score "
                       f"alone.{demo_tag}")
        deck.score_band(s)
    return n_pages
