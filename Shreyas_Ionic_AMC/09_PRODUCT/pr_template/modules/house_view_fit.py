# -*- coding: utf-8 -*-
"""house_view_fit (Section 04, Recommendations, v8 #25).
Table: Dimension | Ionic house view | What the plan does | Fit (Aligned / Gap),
driven by ctx['house_view']['stance']. No score / no direct-equity scope on this slide."""
from slidekit import NAVY, GOLD, INK, SLATE, SERIF, SANS, ML, UW
from pptx.enum.text import PP_ALIGN

SECTION_NO, SECTION = 4, "Recommendations"

# Authored "what the plan does" + fit verdict per house-view dimension (content, not numbers).
PLAN = {
    "Domestic equity": ("Core book kept; only sub-gate names sold and the two >11% positions trimmed toward guideline.", "Aligned"),
    "Foreign equity": ("~28% of net proceeds seeds a global sleeve, a first step; the full ~15% target is phased over cycles.", "Gap"),
    "Gold & silver": ("New gold–silver sleeve (75:25) added from proceeds; still building toward the ~5% target.", "Gap"),
    "Momentum": ("No momentum chase, every sell is fundamentals-driven, not a price-trend call.", "Aligned"),
    "Low-vol / value": ("Largest redeployment sleeve is a low-vol / value core, the closest-substitute risk profile.", "Aligned"),
}

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
        plan_txt, fit = PLAN.get(dim, (None, None))
        if plan_txt is None:
            # generic fallback if the stance dimensions change: flag a gap on any large signed band
            plan_txt = "Reviewed against the house view; see recommendations."
            fit = "Gap" if any(abs(v) >= 8 for k, v in gaps.items() if k.lower() in dim.lower()) else "Aligned"
        rows.append([("b", dim), view, plan_txt, ("pill", fit, fit)])

    cols = [("Dimension", 0.19, "l"), ("Ionic house view", 0.22, "l"),
            ("What the plan does", 0.45, "l"), ("Fit", 0.14, "c")]
    deck.table(s, ML, 2.12, UW, cols, rows, rowh=0.62, fs=9.5, hfs=8)

    deck.callout(s, ML, 5.68, UW, 0.82, L["ct"], L["cb"], kind=L["ck"])
    deck.source(s, f"Ionic house view is advisory-owned · illustrative for the AZBY demo · as of {ctx['client']['as_of']}.")
    return 1
