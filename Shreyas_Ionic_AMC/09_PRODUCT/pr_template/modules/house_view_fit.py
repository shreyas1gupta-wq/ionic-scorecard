# -*- coding: utf-8 -*-
"""house_view_fit (Section 04, Recommendations, v8 #25).
Table: Dimension | Ionic house view | What the plan does | Fit (Aligned / Gap),
driven by ctx['house_view']['stance']. No score / no direct-equity scope on this slide."""
from slidekit import NAVY, GOLD, INK, SLATE, SERIF, SANS, ML, UW
from pptx.enum.text import PP_ALIGN

SECTION_NO, SECTION = 4, "Recommendations"


def _sleeve_amount(sleeves, prefixes):
    for name, amt, _note in sleeves:
        if any(name.lower().startswith(p) for p in prefixes):
            return amt
    return 0


def _plan_for(dim, ctx):
    """What the plan does per house-view dimension, derived from THIS client's real ctx --
    never authored/static prose (2026-07-28 fix: the old static PLAN dict claimed a global
    sleeve, a gold-silver sleeve and 2 trims that did not exist on the real Client B deck --
    confirmed shipped-false content, same bug class as the cut annex_stress_scenarios.py)."""
    t = ctx["totals"]
    sleeves = ctx.get("deployment", {}).get("sleeves", [])
    if dim == "Domestic equity":
        n_sell, n_trim = t.get("n_sell", 0), t.get("n_trim", 0)
        txt = f"{n_sell} equity name(s) sold on quality/value grounds"
        txt += (f"; {n_trim} position(s) trimmed toward the single-name guideline."
                if n_trim else "; no position currently sits far enough over guideline to "
                "warrant a trim.")
        return txt, "Aligned"
    if dim == "Foreign equity":
        amt = _sleeve_amount(sleeves, ("foreign", "global"))
        if amt > 0:
            return (f"Rs {amt/1e5:.1f}L of net proceeds seeded into a foreign/global sleeve, "
                    "a first step toward the house target.", "Gap")
        return ("No foreign sleeve funded yet — proceeds are held in cash pending your goals "
                "and IPS discussion.", "Gap")
    if dim == "Gold & silver":
        amt = _sleeve_amount(sleeves, ("gold",))
        if amt > 0:
            return (f"Rs {amt/1e5:.1f}L of net proceeds seeded into a gold & silver sleeve, "
                    "building toward the house target.", "Gap")
        return ("No gold/silver sleeve funded yet — proceeds are held in cash pending your "
                "goals and IPS discussion.", "Gap")
    if dim == "Momentum":
        # firm methodology statement, not a client-specific portfolio claim -- always true
        return ("No momentum chase — every sell/hold call here is fundamentals-driven, not a "
                "price-trend call.", "Aligned")
    if dim == "Low-vol / value":
        amt = _sleeve_amount(sleeves, ("low-vol", "value"))
        if amt > 0:
            return ("Largest redeployment sleeve is a low-vol / value core, the closest-"
                    "substitute risk profile.", "Aligned")
        return ("No redeployment sleeve funded yet — proceeds are held in cash pending your "
                "goals and IPS discussion.", "Gap")
    return None, None

LABELS = {
    "hni": {"eyebrow": "House-view fit", "title": "Where the plan aligns with Ionic's positioning · and where a gap stays open",
            "intro": "Each recommendation, checked against how Ionic is currently positioned.",
            "ck": "note", "ct": "Read",
            "cb": "The plan pulls the book toward the house view where it is off. Two gaps stay open by design, foreign and gold are built in steps, not funded in a single cycle."},
    "std": {"eyebrow": "House-view fit", "title": "Where the plan aligns with Ionic's positioning · and where a gap stays open",
            "intro": "Each recommendation, checked against how Ionic is currently positioned.",
            "ck": "note", "ct": "Read",
            "cb": "The plan pulls the book toward the house view where it is off. Two gaps stay open by design, foreign and gold are built in steps, not funded in a single cycle."},
    "simple": {"eyebrow": "Does the plan match our view?", "title": "How your plan lines up with the way Ionic is positioned",
               "intro": "A simple check: does each change move with Ionic's view, or is there still a gap?",
               "ck": "human", "ct": "What this means",
               "cb": "Most of your portfolio already matches how Ionic is positioned. The parts still to build, your overseas slice and gold, we add to gradually, not all at once."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    deck.txt(s, ML, 1.72, UW, 0.3, [(L["intro"], SERIF, 11, SLATE, False, True)])

    stance = ctx["house_view"]["stance"]
    gaps = ctx["house_view"].get("alloc_gap", {})
    rows = []
    for dim, view in stance.items():
        plan_txt, fit = _plan_for(dim, ctx)
        if plan_txt is None:
            # generic fallback if the stance dimensions change: flag a gap on any large signed band
            plan_txt = "Reviewed against the house view; see recommendations."
            fit = "Gap" if any(abs(v) >= 8 for k, v in gaps.items() if k.lower() in dim.lower()) else "Aligned"
        rows.append([("b", dim), view, plan_txt, ("pill", fit, fit)])

    cols = [("Dimension", 0.19, "l"), ("Ionic house view", 0.22, "l"),
            ("What the plan does", 0.45, "l"), ("Fit", 0.14, "c")]
    deck.table(s, ML, 2.12, UW, cols, rows, rowh=0.62, fs=9.5, hfs=8)

    deck.callout(s, ML, 5.68, UW, 0.82, L["ct"], L["cb"], kind=L["ck"])
    demo_tag = " · illustrative for this demo" if ctx.get("is_demo", False) else ""
    deck.source(s, f"Ionic house view{demo_tag} · as of {ctx['client']['as_of']}.")
    return 1
