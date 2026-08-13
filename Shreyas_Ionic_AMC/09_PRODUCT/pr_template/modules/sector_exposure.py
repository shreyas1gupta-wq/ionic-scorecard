# -*- coding: utf-8 -*-
"""sector_exposure (F12), COMBINED sector weights: direct equity + the fund sleeve, looked
through via each fund's own disclosed sector allocation (FM #10). Replaces the old
"fund sleeve not looked through" caveat outright — this page now IS the looked-through view,
not a direct-only one with a warning attached. A fund with no sector disclosure on file
contributes nothing and is disclosed as a coverage gap, never smeared evenly across sectors."""
from slidekit import (NAVY, GOLD, INK, SLATE, AMBER, SANS, SERIF, ML, UW, RX)
import charts as CH
from lib import lookthrough as LT

LABELS = {
    "hni":    {"eyebrow": "Sector exposure",
               "title": "Combined sector weights, direct equity and funds looked through"},
    "std":    {"eyebrow": "Sector exposure",
               "title": "Which sectors you lean on, shares and funds combined"},
    "simple": {"eyebrow": "Which industries you own",
               "title": "Where your money is invested, shares and funds together"},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    eq = ctx["equity"]; as_of = ctx["client"]["as_of"]

    sectors, gap_pct, gap_n = LT.combined_sector_exposure(ctx)
    ranked = sorted(sectors.items(), key=lambda kv: -kv[1])
    ranked = [(k, round(v, 1)) for k, v in ranked]
    if len(ranked) > 8:
        head = ranked[:8]; other = round(sum(v for _, v in ranked[8:]), 1)
        ranked = head + [("Other", other)]

    # direct-only figure for the same top sector, kept ONLY to show the size of the look-through
    # effect — never shown as the headline number itself (FM #10's whole point).
    direct_agg = {}
    for e in eq:
        sec = (e.get("sector") or "Diversified").strip() or "Diversified"
        direct_agg[sec] = direct_agg.get(sec, 0.0) + e["weight_pct"]

    s = deck.content(1, "Portfolio X-ray", L["eyebrow"], L["title"])
    if gap_n:
        deck.scope_tag(s, f"Direct equity + {len(ctx['funds']) - gap_n} of {len(ctx['funds'])} "
                          f"funds looked through · as of {as_of}")
    else:
        deck.scope_tag(s, f"Direct equity + all funds looked through · as of {as_of}")

    # ---- hbar (left): combined, % of total portfolio ----
    labels = [k for k, _ in ranked]; values = [v for _, v in ranked]
    hpath = CH.hbar(labels, values, "azby_sector_combined", highlight=0, fmt="{:.1f}%")
    deck.pic(s, hpath, ML, 2.0, 6.75, 4.35, valign="top", halign="left")

    single_sector = len(ranked) == 1
    top1, v1 = ranked[0]
    top2, v2 = ranked[1] if len(ranked) > 1 else (None, None)
    t3 = round(sum(v for _, v in ranked[:3]), 1)
    v1_direct_only = round(direct_agg.get(top1, 0.0), 1)
    lookthrough_lift = round(v1 - v1_direct_only, 1)

    # ---- coverage callout (right, top) — replaces the old "not looked through" warning ----
    cx = ML + 7.05; cw = RX - cx
    cov_y = 2.0
    if gap_n:
        cov_body = (f"{gap_n} fund{'s' if gap_n != 1 else ''} ({gap_pct:.1f}% of the portfolio) "
                    "carries no fund-level sector disclosure yet and is not yet included below "
                    "— shown as a gap, not spread evenly across sectors as a guess."
                    if reg != "simple" else
                    f"{gap_n} fund{'s' if gap_n != 1 else ''} hasn't told us its sector mix yet, "
                    "so it isn't in this picture yet — we say so rather than guess.")
        cov_h = deck.callout_h(cw, cov_body, min_h=1.2, max_h=1.95)
        deck.callout(s, cx, cov_y, cw, cov_h, "COVERAGE, LOOK-THROUGH", cov_body, kind="warn")
    else:
        cov_body = ("Every fund you hold discloses its own sector mix, so the chart below is "
                    "fully looked through — direct shares plus each fund's own holdings, nothing "
                    "estimated." if reg != "simple" else
                    "Every fund you hold has told us its sector mix, so this picture includes "
                    "your funds too, not just your direct shares.")
        cov_h = deck.callout_h(cw, cov_body, min_h=1.0, max_h=1.6)
        deck.callout(s, cx, cov_y, cw, cov_h, "COVERAGE, LOOK-THROUGH", cov_body, kind="good")

    # ---- read (right, bottom) — chained off the coverage callout's ACTUAL height, and its
    # own height is callout_h-driven too (a fixed 2.0in box is what clipped here once the
    # lookthrough-lift sentence was added) ----
    read_y = max(cov_y + cov_h + 0.15, 4.15)
    if single_sector:
        read = (f"Your whole book, shares and funds together, sits in one sector: {top1}."
                if reg == "simple" else
                f"Combined across direct equity and the fund sleeve, the book sits entirely in "
                f"one sector, {top1} ({v1:.0f}% of the portfolio). Sector risk here is total, not "
                "partial, and it compounds with any single-name concentration flagged earlier.")
    elif reg == "simple":
        read = (f"Most of your money, shares and funds together, sits in {top1} and {top2}. "
                f"Your funds add about {lookthrough_lift:+.0f} points to {top1} alone versus "
                "your direct shares by themselves.")
    elif reg == "hni":
        read = (f"Combined, the book leans on {top1} ({v1:.0f}% of the portfolio) and {top2} "
                f"({v2:.0f}%); the top three sectors are {t3:.0f}%. The fund sleeve alone adds "
                f"{lookthrough_lift:+.1f} points to {top1} versus a direct-equity-only read "
                f"({v1_direct_only:.1f}%) — the gap FM comment #10 asked us to close. Sector risk "
                "compounds with the single-name concentration flagged earlier.")
    else:
        read = (f"Combined across direct equity and funds, the book leans toward {top1} "
                f"({v1:.0f}% of the portfolio) and {top2} ({v2:.0f}%); the top three sectors are "
                f"{t3:.0f}%. Looking through the funds adds {lookthrough_lift:+.1f} points to "
                f"{top1} alone versus counting direct equity only ({v1_direct_only:.1f}%). "
                "Sector risk compounds with the single-name concentration flagged earlier.")
    read_h = deck.callout_h(cw, read, min_h=1.3, max_h=max(1.3, 6.55 - read_y))
    deck.callout(s, cx, read_y, cw, read_h,
                 "THE READ" if reg != "simple" else "IN SHORT", read, kind="human")

    demo_tag = " Illustrative synthetic book." if ctx.get("is_demo", False) else ""
    deck.source(s, f"Source: client holdings as of {as_of}. Weights as % of TOTAL portfolio "
                   "(calculation base: FM #8) — direct-equity sector plus each fund's own "
                   f"disclosed sector allocation, weighted by that fund's own weight.{demo_tag}")
    return 1
