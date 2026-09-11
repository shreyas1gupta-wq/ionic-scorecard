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
    # HOLDINGS THE CLIENT ASKED TO EXIT THAT CANNOT BE EXITED. They belong on exactly this page:
    # it is the page for a holding that could not take a normal call. Three of them appeared
    # nowhere else in sixty-four pages as anything but the bare word "Retain" in an annexure
    # column, and the client is entitled to know why money they asked to move is staying put.
    retains = list(((ctx.get("client_directive") or {}).get("retains")) or [])
    if not (suspended or no_view or flags or retains):
        return 0
    reg = tier.get("register", "std")
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    n_slides = 0

    # PAGE 1: suspended holdings + no-view funds (tables) — split from the flags page
    # (2026-07-27: cramming both tables AND the flags callout onto one slide overflowed
    # past the footer the first time this module ran on a real, content-heavy book).
    # ITS OWN PAGE. Laid in above the no-view table it pushed six rows of that table below the
    # trim line, where nothing is visible and no gate but this one can see it.
    if retains:
        s = deck.content(SECTION_NO, SECTION, eyebrow,
                         "What you asked to exit, and what cannot be exited")
        deck.scope_tag(s, "Your instruction was to exit the fixed-income sleeve; these holdings "
                          "cannot be redeemed on request.")
        _c = [("Holding", 0.24, "l"), ("Value", 0.13, "r"),
              ("Why it stays, though you asked us to exit it", 0.63, "l")]
        _r = [[e.get("name") or "",
               ("Rs %.2f Cr" % ((e.get("value_inr") or 0) / 1e7)
                if (e.get("value_inr") or 0) >= 1e7
                else "Rs %.1f L" % ((e.get("value_inr") or 0) / 1e5)),
               clip_clause(e.get("reason") or "", 240)] for e in retains]
        deck.txt(s, ML, 2.0, UW, 0.22,
                 [("HELD BACK FROM YOUR EXIT INSTRUCTION, AND WHY", SANS, 9, AMBER,
                   True, False, 60)])
        _y = deck.table(s, ML, 2.30, UW, _c, _r,
                        rowh=_rowh_for([x[2] for x in _r], 0.63 * UW), fs=9.5, hfs=8) + 0.28
        _v = sum(e.get("value_inr") or 0 for e in retains)
        deck.txt(s, ML, _y, UW, 0.5,
                 [("Rs %s of the sleeve therefore stays where it is. None of it is counted in the "
                   "proceeds, the tax estimate or the redeployment on the preceding pages, and the "
                   "desk's own view on each of these holdings is unchanged: they are held because "
                   "their terms do not permit an exit on request, not because we would keep them."
                   % ("%.2f Cr" % (_v / 1e7) if _v >= 1e7 else "%.1f L" % (_v / 1e5)),
                   SERIF, 10, INK, False, True)], ls=1.08)
        deck.source(s, "Terms as stated in the scheme rules; confirm the exact surrender position "
                       "with the issuer before any instruction is given.")
        deck.score_band(s)
        n_slides += 1

    if suspended or no_view:
        s = deck.content(SECTION_NO, SECTION, eyebrow, title)
        deck.scope_tag(s, "These positions sit outside the normal scored tables — folding them "
                          "in would distort every comparison.")
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

        # PAGINATED 2026-08-19. The no-view table was unpaginated: a book with many uncovered
        # holdings ran it off the page (an MF-only book with 15 no-view funds reached 10.43in on a
        # 7.5in slide, 24 shapes below the trim and invisible). Exactly the failure the flags valve
        # below was fixed for on 2026-08-02 -- a holding we have no view on going missing is worse
        # than one more slide. Under _NV_PER_PAGE rows, behaviour is unchanged.
        _NV_PER_PAGE = 6      # row heights grow with the reason text; 8 collided with the source line
        # AND CAPPED. Pagination alone was the right fix for fifteen uncovered funds and the wrong
        # one for a hundred and forty-four: a family holding direct shares carries a No View on
        # every one of them, and the page became EIGHTEEN consecutive slides of "we have no view on
        # this" in the middle of a client deck. The largest are named, because those are the ones
        # worth a conversation, and the tail is counted and valued in a line rather than listed. The
        # annexure still lists every holding, so nothing is hidden by this.
        _NV_MAX_PAGES = 3
        no_view = sorted(no_view, key=lambda e: -(e.get("value_inr") or 0))
        _nv_cap = _NV_PER_PAGE * _NV_MAX_PAGES
        nv_rest = no_view[_nv_cap:]
        no_view = no_view[:_nv_cap]
        nv_pages = [no_view[i:i + _NV_PER_PAGE] for i in range(0, len(no_view), _NV_PER_PAGE)] \
            if no_view else []
        # NOT "verified against public listing/exchange records". Nothing in this pipeline
        # queries an exchange or a listing record; the status on these rows is whatever the
        # statement and the score file carry. A source line asserting a verification the code
        # cannot perform is the same defect as the reviewer sign-off and the total-return
        # benchmark: a claim with no field behind it.
        SRC = ("Status and category as the client's statement and the desk's score file record "
               "them. This review does not query exchange or listing records; confirm any "
               "suspension, delisting or launch date independently before it affects a decision.")
        cols = [("Holding", 0.30, "l"), ("Category", 0.20, "l"), ("Why no view", 0.50, "l")]
        for pg, chunk in enumerate(nv_pages or [None]):
            if pg > 0:
                s = deck.content(SECTION_NO, SECTION, eyebrow,
                                 f"{title}  ({pg + 1} of {len(nv_pages)})")
                deck.scope_tag(s, "These positions sit outside the normal scored tables, continued.")
                y = 2.0
            if chunk:
                rows = [[e["name"], e["category"], clip_clause(e["reason"], 200)] for e in chunk]
                rowh = _rowh_for([r[2] for r in rows], 0.50 * UW)
                label = ("HOLDINGS WITH NO PERFORMANCE VIEW" if pg else
                         "HOLDINGS WITH NO PERFORMANCE VIEW — \"NO VIEW\"")
                deck.txt(s, ML, y, UW, 0.22, [(label, SANS, 9, AMBER, True, False, 60)])
                y += 0.30
                y = deck.table(s, ML, y, UW, cols, rows, rowh=rowh, fs=9, hfs=8) + 0.22
                # the tail, counted rather than listed, on the last page of the table
                if nv_rest and pg == len(nv_pages) - 1:
                    _rest_v = sum(e.get("value_inr") or 0 for e in nv_rest)
                    _line = (f"A further {len(nv_rest)} holdings carry no performance view, "
                             + (f"Rs {_rest_v:,.0f} between them" if _rest_v else
                                "each smaller than those above")
                             + ". They are listed individually in the annexure, and every one of "
                               "them counts in full in the totals, weights and concentration tests "
                               "on these pages.")
                    deck.txt(s, ML, y, UW, 0.44, [(_line, SERIF, 9, SLATE, False, True)], ls=1.05)
                    y += 0.50
            deck.source(s, SRC)
            deck.score_band(s)
            n_slides += 1

    # PAGE 2+: data-quality flags, one callout each, paginated (2026-08-02 fix: a real
    # client's 13 authored flags silently dropped to 4 past a fixed footer valve —
    # a genuine data-quality note going missing is worse than one more slide).
    if flags:
        i = 0
        page = 0
        while i < len(flags):
            page += 1
            suffix = f" ({page} of {-(-len(flags) // 4)})" if len(flags) > 4 else ""
            s = deck.content(SECTION_NO, SECTION, eyebrow, f"Other data-quality flags from this statement{suffix}")
            deck.scope_tag(s, "Flagged rather than silently resolved — each needs RM or client confirmation.")
            y = 2.0
            while i < len(flags):
                body = clip_clause(flags[i], 300)
                h = deck.callout_h(UW, body, min_h=0.6, max_h=1.15)
                if y + h > 6.6 and y > 2.0:
                    break  # this page is full; start a new one (never silently drop a flag)
                deck.callout(s, ML, y, UW, h, f"Flag {i + 1}", body, "warn")
                y += h + 0.14
                i += 1
            deck.source(s, "Confirm each item with the RM/client before it affects any execution decision.")
            deck.score_band(s)
            n_slides += 1

    return n_slides
