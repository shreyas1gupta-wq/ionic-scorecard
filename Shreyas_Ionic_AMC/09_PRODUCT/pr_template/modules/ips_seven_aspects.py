# -*- coding: utf-8 -*-
"""ips_seven_aspects (Understanding, core) -- FM comment #5 / Principal ruling 2026-08-06.

The client's seven IPS aspects (return, risk, liability, liquidity, timelines, tax, unique
circumstances) were flagged in FM_REVIEW_REPLY_2026-08-05.md (C4) as data we hold nowhere. His
ruling: "add that for now for abxy family assume something best we can show" -- ABXY is the DEMO
book (ctx["is_demo"] is True), so an assumed value is legitimate there, PROVIDED the page says so.

THE DEGRADATION THIS MODULE EXISTS TO GET RIGHT: a real client's ctx has no `ips.seven_aspects`
key at all today (no advisor has recorded one yet). That must render "on file with the advisor" --
never ABXY's assumptions, and never a blank. The gate is deliberately on the DATA (whether the key
exists), not on the is_demo flag alone, so the day an advisor genuinely records a real client's
seven aspects, this page picks them up with no code change and no demo framing."""
from slidekit import NAVY, GOLD, INK, SLATE, HAIR, WHITE, SERIF, SANS, ML, UW
from pptx.enum.text import PP_ALIGN

ASPECTS = [
    ("return", "Return objective"),
    ("risk", "Risk tolerance"),
    ("liability", "Liability / goals"),
    ("liquidity", "Liquidity needs"),
    ("timelines", "Time horizon"),
    ("tax", "Tax situation"),
    ("unique", "Unique circumstances"),
]

_ON_FILE_PLACEHOLDER = "On file with the advisor — not yet recorded in this system."

LABELS = {
    "hni":    ("Client circumstances", "The seven things this plan is built around"),
    "std":    ("Client circumstances", "The seven things this plan is built around"),
    "simple": ("About you", "What we know, in seven parts"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    ips = ctx.get("ips", {})
    is_demo = ctx.get("is_demo", False)
    seven = ips.get("seven_aspects")

    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(0, "Understanding", eyebrow, title)

    if seven and is_demo:
        tag = "[ASSUMED — illustrative for the ABXY demo; not a real client's circumstances]"
        tag_color = GOLD
    elif seven:
        tag = "As recorded with the client's advisor."
        tag_color = SLATE
    else:
        tag = "None of the seven are yet on file for this client in our system of record."
        tag_color = SLATE
    deck.txt(s, ML, 1.80, UW, 0.24, [(tag, SANS, 8.5, tag_color, True, seven is not None)])

    y = 2.16
    rowh = 0.615
    labelw = 1.85
    for key, label in ASPECTS:
        text = (seven or {}).get(key) if seven else None
        placeholder = not text
        if placeholder:
            text = _ON_FILE_PLACEHOLDER
        deck.txt(s, ML, y, labelw - 0.15, rowh, [(label.upper(), SANS, 9, NAVY, True, False, 20)])
        deck.txt(s, ML + labelw, y, UW - labelw, rowh,
                 [(text, SERIF, 10, (SLATE if placeholder else INK), False, placeholder)], ls=1.10)
        deck.rule(s, ML, y + rowh - 0.06, UW, HAIR, 0.006)
        y += rowh

    demo_tag = " Illustrative synthetic book." if is_demo else ""
    deck.source(s, "The seven IPS aspects are the standard investment-policy framework: return, "
                   "risk, liability, liquidity, time horizon, tax and unique circumstances. Shown "
                   f"here for completeness against that framework, not as a scored input.{demo_tag}")
    return 1
