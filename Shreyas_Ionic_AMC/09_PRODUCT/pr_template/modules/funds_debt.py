# -*- coding: utf-8 -*-
"""funds_debt (NEW, FM #22), debt-fund sell inputs: YTM, modified duration, expense ratio and
rating buckets. Renders nothing (returns 0) when the book holds no debt-category fund — a common,
not an error, mirroring funds_hybrid.py's own graceful-empty pattern.

YTM coverage is a genuine, partial gap even in the real feed (56% of Direct debt rows carry it per
05_DATA_OFFICE/ACEMF_VERIFICATION_2026-08-05.md) — a missing YTM is rendered as an explicit
"Not disclosed" cell, NEVER a blank that could read as zero (FM #22's own wording)."""
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, SERIF, SANS, ML, UW, fmt_dual_pct

LABELS = {
    "hni":    ("Debt funds, the sell inputs", "Yield, duration, cost and credit quality — the inputs a debt sell needs"),
    "std":    ("Debt funds, the sell inputs", "What we look at before touching a debt holding"),
    "simple": ("Your debt funds", "The numbers we check before we would ever suggest a change"),
}


def _short(name, n=28):
    from slidekit import short_name
    return short_name(name, n)


def _rating_read(alloc):
    if not alloc:
        return "-"
    top = sorted(alloc.items(), key=lambda kv: -kv[1])
    return "  ·  ".join(f"{k} {v:.0f}%" for k, v in top[:3])


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    debt = [f for f in ctx["funds"] if f.get("category") == "debt"]
    if not debt:
        return 0  # a book with no pure-debt fund holding is common, not an error
    as_of = ctx["client"]["as_of"]
    grand = ctx["totals"]["grand_inr"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(2, "The Fund Book", eyebrow, title)
    deck.scope_tag(s, f"MF sleeve · debt schemes only · Direct-plan NAV where held · as of {as_of}")

    n_gap = sum(1 for f in debt if f.get("ytm_pct") is None)

    if simple:
        cols = [("Scheme", 0.28, "l"), ("Share", 0.12, "r"), ("Yield", 0.16, "l"),
                ("How long it locks in", 0.20, "l"), ("Quality", 0.12, "l"), ("Suggested", 0.12, "c")]
    else:
        cols = [("Scheme", 0.22, "l"), ("Plan", 0.07, "c"), ("% of portfolio", 0.11, "r"),
                ("YTM", 0.10, "l"), ("Mod. duration", 0.11, "r"), ("Direct-plan expense", 0.12, "r"),
                ("Rating mix", 0.17, "l"), ("Verdict", 0.10, "c")]
    rows = []
    for f in debt:
        ytm = f.get("ytm_pct")
        ytm_cell = (f"{ytm:.2f}%" if ytm is not None else
                    ("Not disclosed" if not simple else "Not shown yet"))
        ytm_color = INK if ytm is not None else AMBER
        dur = f.get("mod_duration_yrs")
        dur_cell = f"{dur:.1f}y" if dur is not None else "n/a"
        # f["ter"] is ALREADY a percentage (azby_family.py: 0.55 means 0.55%, matching cost.py's
        # own *100-to-bps convention elsewhere) -- multiplying by 100 here printed "55.00%" for
        # a 0.55% fund, caught on the mandatory visual PDF read (2026-08-06).
        ter_pct = round(f["ter"], 2)
        v = f["verdict"]
        wt_disp = fmt_dual_pct(f["weight_pct"])
        if simple:
            rows.append([_short(f["name"], 30), ("c", wt_disp, INK),
                         ("c", ytm_cell, ytm_color, True), dur_cell,
                         _rating_read(f.get("rating_alloc")).split("  ·  ")[0],
                         ("pill", v, v)])
        else:
            rows.append([_short(f["name"]), f["plan"][:3], ("c", wt_disp, INK),
                         ("c", ytm_cell, ytm_color, True), ("c", dur_cell, INK),
                         ("c", f"{ter_pct:.2f}%", INK), _rating_read(f.get("rating_alloc")),
                         ("pill", v, v)])
    ty = deck.table(s, ML, 2.0, UW, cols, rows, rowh=0.46, fs=9.5, hfs=8)

    if n_gap:
        gap_note = (f"{n_gap} of {len(debt)} debt fund{'s' if len(debt) != 1 else ''} in this "
                    "book has no disclosed yield yet — shown as \"Not disclosed\", never a blank "
                    "or a zero. Coverage of this figure is partial fund-wide, not specific to "
                    "this holding."
                    if not simple else
                    f"{n_gap} of {len(debt)} fund{'s' if len(debt) != 1 else ''} hasn't disclosed "
                    "a yield yet — we show that honestly rather than guess.")
        gh = deck.callout_h(UW, gap_note, min_h=0.5, max_h=0.85)
        deck.callout(s, ML, ty + 0.14, UW, gh, "COVERAGE", gap_note, kind="warn")
        ty = ty + 0.14 + gh

    demo_tag = " Illustrative synthetic funds." if ctx.get("is_demo", False) else ""
    deck.source(s, "YTM / modified duration / rating mix from each scheme's own fund-level "
                   "disclosure; expense ratio is the Direct-plan figure regardless of which plan "
                   f"is held. Weights shown as % of total portfolio (see calculation-base note)."
                   f"{demo_tag}")
    return 1
