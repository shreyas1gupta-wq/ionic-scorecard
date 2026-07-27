# -*- coding: utf-8 -*-
"""ips_summary (F1, core), Investment Policy Statement, one page.
Risk-tier badge · objective · horizon · strategic allocation BANDS (min–target–max range
bars per asset from ctx['ips']['alloc_bands']) · single-name cap + target rails · constraints.
Tagged [ILLUSTRATIVE, demo IPS]: on a real client deck this content is advisory-owned and
would render 'IPS NOT ON FILE' if absent; AZBY is fictional so it carries an illustrative IPS."""
from slidekit import (NAVY, NT2, NT3, GOLD, INK, SLATE, PANEL, HAIR, TRACK, WHITE,
                      SERIF, SANS, ML, UW, RX)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    ips = ctx["ips"]
    title = "Your plan, in one page" if simple else "The mandate we manage to"
    s = deck.content(0, "Understanding", "Investment Policy Statement", title)

    # tag (top-right, under the header rule) — demo tag on the synthetic book, "NOT ON
    # FILE" on a real client with no IPS yet (2026-07-27), nothing when a real IPS exists
    if ctx.get("is_demo", True):
        tag = "[ILLUSTRATIVE, demo IPS]"
    elif not ips.get("on_file", True):
        tag = "IPS NOT ON FILE — bands shown are placeholders, not a house mandate"
    else:
        tag = ""
    if tag:
        deck.txt(s, RX - 4.6, 1.62, 4.6, 0.2,
                 [(tag, SANS, 8, GOLD, True, True)], align=PP_ALIGN.RIGHT)

    # ---- Row 1: risk-tier badge + objective ----
    deck.txt(s, ML, 1.80, 1.8, 0.2, [("RISK TIER", SANS, 8, SLATE, True, False, 120)])
    deck.rect(s, ML, 2.02, 1.9, 0.56, fill=NAVY, round_=0.12)
    deck.txt(s, ML, 2.02, 1.9, 0.56, [(ips["risk_tier"].upper(), SANS, 15, WHITE, True, False, 40)],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    ox = ML + 2.20
    deck.txt(s, ox, 1.80, RX - ox, 0.2, [("OBJECTIVE", SANS, 8, SLATE, True, False, 120)])
    deck.txt(s, ox, 2.04, RX - ox, 0.7, [(ips["objective"], SERIF, 11.5, INK, False, True)], ls=1.1)

    deck.rule(s, ML, 2.92, UW, HAIR, 0.008)

    # ---- Row 2 LEFT: targets & limits ----
    lx, lw = ML, 4.3
    deck.txt(s, lx, 3.06, lw, 0.2, [("TARGETS & LIMITS", SANS, 8.5, SLATE, True, False, 120)])
    rails = [
        ("Time horizon", f"{ips['horizon_yrs']} yr+"),
        ("Single-name cap", f"≤ {ips['single_name_cap_pct']:.0f}%  of the book"),
        ("Foreign / global equity", f"{ips['foreign_target_pct']:.0f}%  target of equity"),
        ("Gold & silver sleeve", f"{ips['gold_target_pct']:.0f}%  target"),
    ]
    for i, (lab, val) in enumerate(rails):
        yy = 3.42 + i * 0.44
        deck.txt(s, lx, yy, lw - 1.5, 0.3, [(lab, SERIF, 10.5, INK, False)], anchor=MSO_ANCHOR.MIDDLE)
        deck.txt(s, lx + lw - 1.6, yy, 1.6, 0.3, [(val, SANS, 10.5, NAVY, True)],
                 align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        deck.rule(s, lx, yy + 0.38, lw, HAIR, 0.006)

    # ---- Row 2 RIGHT: strategic allocation range bars ----
    rx = 5.55
    rw = RX - rx
    deck.txt(s, rx, 3.06, rw * 0.62, 0.2, [("STRATEGIC ALLOCATION BANDS", SANS, 8.5, SLATE, True, False, 120)])
    deck.txt(s, rx + rw * 0.62, 3.06, rw * 0.38, 0.2,
             [("min, target, max", SANS, 8, SLATE, False, True)], align=PP_ALIGN.RIGHT)
    LBLW, TRW = 1.55, 3.35            # label width, track width
    tx = rx + LBLW
    # 0/50/100 baseline ticks
    for f in (0.0, 0.5, 1.0):
        deck.txt(s, tx + TRW * f - 0.2, 3.30, 0.4, 0.16,
                 [(f"{int(f*100)}", SANS, 6.5, SLATE, False)], align=PP_ALIGN.CENTER)
    bands = list(ips["alloc_bands"].items())
    for i, (asset, (lo, tgt, hi)) in enumerate(bands):
        yy = 3.58 + i * 0.50
        deck.txt(s, rx, yy - 0.02, LBLW - 0.1, 0.3, [(asset, SANS, 9.5, INK, True)],
                 anchor=MSO_ANCHOR.MIDDLE)
        deck.rect(s, tx, yy + 0.10, TRW, 0.09, fill=TRACK)                 # 0-100 track
        bx = tx + TRW * lo / 100.0
        bw = TRW * (hi - lo) / 100.0
        deck.rect(s, bx, yy + 0.06, bw, 0.17, fill=NT3)                     # min-max band
        deck.rect(s, tx + TRW * tgt / 100.0 - 0.008, yy + 0.03, 0.016, 0.23, fill=GOLD)  # target tick
        deck.txt(s, tx + TRW + 0.10, yy - 0.02, rw - LBLW - TRW - 0.1, 0.3,
                 [(f"{lo:.0f}–{hi:.0f}%", SANS, 9.5, NAVY, True),
                  (f"   tgt {tgt:.0f}", SANS, 9, SLATE, False)], anchor=MSO_ANCHOR.MIDDLE)

    # ---- Row 3: constraints (full width, two columns) ----
    cy = 5.62
    deck.rule(s, ML, cy - 0.12, UW, HAIR, 0.008)
    deck.txt(s, ML, cy, UW, 0.2, [("CONSTRAINTS", SANS, 8.5, SLATE, True, False, 120)])
    cons = ips["constraints"]
    colw = UW / 2
    for i, c in enumerate(cons):
        col, rowi = i % 2, i // 2
        px = ML + col * colw
        yy = cy + 0.30 + rowi * 0.34
        deck.oval(s, px, yy + 0.06, 0.09, GOLD)
        deck.txt(s, px + 0.20, yy - 0.02, colw - 0.35, 0.32, [(c, SERIF, 10, INK, False)],
                 anchor=MSO_ANCHOR.MIDDLE)
    return 1
