# -*- coding: utf-8 -*-
"""data_notes (Section 04, Recommendations, NEW 2026-07-27 — first real client build).
Surfaces anything that couldn't go through the normal scored equity/fund tables without
distorting them: suspended/insolvent legacy holdings (shown as a status, never a Sell/Hold
score), funds below the firm's minimum track record (No View), and any statement-level data
quality flags. Renders 0 if ctx has no notes (keeps the demo book unaffected)."""
import math
from slidekit import (NAVY, INK, SLATE, SELL, AMBER, HOLD, SERIF, SANS, ML, UW, RX, clip_clause)


def _rowh_for(texts, col_w_in, fs=9, chars_per_in=19):
    """Row height that actually fits the longest cell at this column width — the module's
    first cut used a fixed 0.4in guess and truncated real multi-sentence findings."""
    per_line = max(20, int(col_w_in * chars_per_in))
    lines = max(1, max(math.ceil(len(t) / per_line) for t in texts))
    return max(0.42, lines * 0.19 + 0.14)

SECTION_NO, SECTION = 4, "Recommendations"

LABELS = {
    "hni": ("Data & coverage notes", "What this review could not score as a normal Sell/Hold call"),
    "std": ("Data & coverage notes", "What this review could not score as a normal Sell/Hold call"),
    "simple": ("A few things to flag", "Some holdings needed a different kind of note, not a score"),
}


def render(deck, ctx, tier):
    notes = ctx.get("data_notes") or {}
    suspended = notes.get("suspended") or []
    no_view = notes.get("no_view") or []
    flags = notes.get("flags") or []
    if not (suspended or no_view or flags):
        return 0
    reg = tier.get("register", "std")
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    n_slides = 0

    # PAGE 1: suspended holdings + no-view funds (tables) — split from the flags page
    # (2026-07-27: cramming both tables AND the flags callout onto one slide overflowed
    # past the footer the first time this module ran on a real, content-heavy book).
    if suspended or no_view:
        s = deck.content(SECTION_NO, SECTION, eyebrow, title)
        deck.scope_tag(s, "These positions sit outside the normal scored tables on purpose "
                          "— folding them in would distort the comparison for every other holding.")
        y = 2.0
        if suspended:
            cols = [("Holding", 0.24, "l"), ("Status", 0.20, "l"), ("Statement value", 0.16, "r"), ("What we'd do", 0.40, "l")]
            rows = [[e["name"], e["status"], f"Rs {e['stated_value']:,.0f} (not realisable)",
                     clip_clause(e["action"], 200)]
                    for e in suspended]
            rowh = _rowh_for([r[3] for r in rows], 0.40 * UW)
            deck.txt(s, ML, y, UW, 0.22, [("LEGACY HOLDINGS — SUSPENDED OR UNDER INSOLVENCY", SANS, 9, SELL, True, False, 60)])
            y += 0.30
            y = deck.table(s, ML, y, UW, cols, rows, rowh=rowh, fs=9, hfs=8) + 0.22

        if no_view:
            cols = [("Holding", 0.30, "l"), ("Category", 0.20, "l"), ("Why no view", 0.50, "l")]
            rows = [[e["name"], e["category"], clip_clause(e["reason"], 200)] for e in no_view]
            rowh = _rowh_for([r[2] for r in rows], 0.50 * UW)
            deck.txt(s, ML, y, UW, 0.22, [("FUNDS BELOW OUR MINIMUM TRACK RECORD — \"NO VIEW\"", SANS, 9, AMBER, True, False, 60)])
            y += 0.30
            y = deck.table(s, ML, y, UW, cols, rows, rowh=rowh, fs=9, hfs=8) + 0.22

        deck.source(s, "Suspended/insolvent status and fund launch dates verified against public "
                       "listing/exchange records at the time of this review; re-confirm before any "
                       "client communication that depends on them.")
        deck.score_band(s)
        n_slides += 1

    # PAGE 2: data-quality flags, one callout each — own slide, own room to breathe
    if flags:
        s = deck.content(SECTION_NO, SECTION, eyebrow, "Other data-quality flags from this statement")
        deck.scope_tag(s, "Flagged rather than silently resolved — each needs RM or client confirmation.")
        y = 2.0
        for i, f in enumerate(flags):
            body = clip_clause(f, 300)
            h = deck.callout_h(UW, body, min_h=0.6, max_h=1.15)
            if y + h > 6.9:
                break  # safety valve: never spill past the footer, even if flags grows later
            deck.callout(s, ML, y, UW, h, f"Flag {i + 1}", body, "warn")
            y += h + 0.14
        deck.source(s, "Confirm each item with the RM/client before it affects any execution decision.")
        deck.score_band(s)
        n_slides += 1

    return n_slides
