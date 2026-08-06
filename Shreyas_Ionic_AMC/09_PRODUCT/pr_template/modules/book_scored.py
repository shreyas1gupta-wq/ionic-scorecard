# -*- coding: utf-8 -*-
"""book_scored (F13), The whole book, scored, with five colour-coded signals per name.
Distribution KPI (Sell / Trim / Hold counts from ctx totals; no book-level weighted score, frozen rule)
+ a table of the largest positions (Name | Wt | Score-bar | Rec-pill | Quality | Growth | Value |
Technical | Flows), maxrows-capped with 'and N more in annexure'. score_band + scope_tag both attach.

CHANGED 2026-08-06 (Principal): the single prose "Analyst read" column is replaced by five
colour-banded signals -- the seven scorecard pillars clubbed into five dimensions. His words: "if we
have a high growth company we will show green below growth". The prose read is not lost; it is what
the per-name rationale card in the annexure already carries at full length, and each row still links
there. What this page loses is a 58-character clipped fragment of that paragraph; what it gains is a
reason the score is what it is, on every row, comparable down the column.

Bands and clubbing come from `lib/five_signals.py` -- never restated here. Three copies of a
threshold is three chances to disagree about what green means.
"""
from slidekit import (NAVY, INK, SLATE, HAIR, PANEL, WHITE, SELL, HOLD, AMBER,
                      SELLBG, HOLDBG, AMBERBG, NT2, SERIF, SANS, ML, RX, UW, clip_clause)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import importlib.util
import os

MAXROWS = 11
# Row budget with the signal legend below the table. The table starts at 2.98, the header eats 0.33 and
# each row 0.28; the legend then needs 0.36 and must clear the footer band at 7.14.
#   11 rows -> legend 6.45-6.81, clear.      12 rows -> legend 6.73-7.09, only 0.05 off the footer.
# This was 10 while source() still sat at 6.66; with both bottom footnotes removed the 11th row fits,
# so the freed space goes back to showing one more holding rather than to blank paper.
MAXROWS_SIG = 11

_F = None


def _sig():
    """`lib/five_signals.py`, loaded by absolute path. The engine puts both lib/ and modules/ on
    sys.path, so a bare name-import is at the mercy of path order (the core_satellite duplicate-
    basename bug, 2026-08-06). Returns None if absent and the page falls back to the prose read."""
    global _F
    if _F is None:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "lib", "five_signals.py")
        if not os.path.exists(p):
            return None
        spec = importlib.util.spec_from_file_location("_lib_five_signals", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _F = mod
    return _F


# The count in the title is DERIVED from F.CATS, never typed. Adding the Cash signal left a hardcoded
# "five dimensions" over a six-dot table -- the class of stale-text defect that survives every automated
# gate, because nothing in the XML knows the sentence is now wrong.
_COUNT_WORD = {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}

LABELS = {
    "hni":    {"title": "The largest positions, scored across {n} dimensions"},
    "std":    {"title": "The largest positions, scored across {n} dimensions"},
    "simple": {"title": "Your biggest holdings, and what is working in each"},
}


def _dist_band(deck, s, tot, y):
    """Compact distribution 'KPI' band. Zero-count calls are dropped — a '0 TRIM'
    tile is dead ink (declutter pass, 2026-07-25)."""
    cells = [(str(tot["n_sell"]), "SELL", SELL),
             (str(tot["n_trim"]), "TRIM", AMBER),
             (str(tot["n_hold"]), "HOLD", HOLD),
             (str(tot["n_stocks"]), "HOLDINGS", INK)]
    cells = [c for c in cells if c[0] != "0" or c[1] in ("SELL", "HOLDINGS")]
    # content-sized tiles (v7 stat-strip rule) — 3 numbers spread across the full
    # width read as gaps, not as a band
    cw = min(UW / len(cells), 2.35)
    for i, (val, lab, col) in enumerate(cells):
        cx = ML + i * cw
        deck.txt(s, cx, y, cw - 0.2, 0.42, [(val, SANS, 27, col, False)], anchor=MSO_ANCHOR.MIDDLE)
        deck.txt(s, cx, y + 0.44, cw - 0.2, 0.2,
                 [(lab, SANS, 8.5, SLATE, True, False, 150)])
        if i:
            deck.vrule(s, cx - 0.02, y + 0.04, 0.56, HAIR, 0.008)


def render(deck, ctx, tier):
    reg = tier["register"]
    L = LABELS.get(reg, LABELS["std"])
    eq = ctx["equity"]; tot = ctx["totals"]
    as_of = ctx["client"].get("as_of", "")
    _F0 = _sig()
    n_dims = len(_F0.CATS) if _F0 is not None else 5
    s = deck.content(3, "The Equity Book", "The book, scored",
                     L["title"].format(n=_COUNT_WORD.get(n_dims, str(n_dims))))

    # Both bottom footnotes are gone (Principal, 2026-08-07). Two facts they carried are not decoration
    # and cannot simply vanish: how many holdings this page actually SHOWS out of the book, and how many
    # carry a score at all. Without the first, a reader sees 10 rows against a "98 HOLDINGS" tile above
    # and concludes 88 are missing. Both now ride in the scope tag at the TOP of the page, which is one
    # line, already exists, and is not a footnote.
    n_scored_all = sum(1 for e in eq if e.get("ionic_score") is not None)
    shown = min(MAXROWS_SIG if _sig() is not None else MAXROWS, len(eq))
    # Keep these SHORT. scope_tag's budget is ~118 characters and it handles overflow by dropping MIDDLE
    # ' · ' segments, keeping the first and the tail -- so the verbose first version silently deleted the
    # "10 of 98 shown" segment, the single most important thing here, while looking perfectly fine.
    bits = [f"Direct equity only · as of {as_of}",
            f"largest {shown} of {len(eq)} shown, rest in annexure"]
    if n_scored_all < len(eq):
        bits.append(f"{len(eq) - n_scored_all} unscored")
    deck.scope_tag(s, " · ".join(bits))

    _dist_band(deck, s, tot, 1.95)

    # override honesty line: Holds sitting below the Sell line, kept on analyst conviction
    overrides = sum(1 for e in eq if e["rec"] == "Hold" and (e.get("ionic_score") or 100) < 40)
    if overrides:
        note = (f"{overrides} name(s) score below 40 yet are held on analyst conviction, "
                "the score flags, the desk decides.")
        deck.txt(s, ML, 2.66, UW, 0.24,
                 [("ANALYST OVERRIDE   ", SANS, 8, AMBER, True, False, 40),
                  (note, SERIF, 9.5, INK, False, True)], anchor=MSO_ANCHOR.MIDDLE)

    # table — largest positions first, then five colour-banded signals per name
    rows_src = sorted(eq, key=lambda e: -(e.get("weight_pct") or 0))
    F = _sig()
    ROWH = 0.28
    n_sig = 0
    nrows = MAXROWS
    if F is not None:
        # Join the pillar scores in by symbol. If nothing matches -- a demo book of invented names, or
        # a scoring run that has not happened -- fall back to the prose read rather than printing five
        # grey "No data" chips per row, which would read as a broken page instead of a missing input.
        n_sig, _n_tot = F.enrich(rows_src[:MAXROWS_SIG])
        if n_sig == 0:
            F = None
        else:
            nrows = MAXROWS_SIG
    if F is not None:
        # A dot needs a fraction of the width a word did, so the signal columns shrink and the freed
        # space goes back to the Holding name. What sets the floor now is the HEADER, not the dot:
        # "TECHNICAL" at 8pt with the header's 200-unit letter-spacing needs ~0.75in plus padding, so
        # that column stays wider than its four neighbours. "Flows" is abbreviated for the same reason
        # -- "Flows & Sector" would need ~1.35in of header for a 0.15in dot.
        # One dot column per signal, driven by F.CATS so the two never drift out of step. Header text is
        # what sets each width, not the 0.15in dot: "SECTOR & FLOWS" at 8pt with the header's 200-unit
        # letter-spacing needs ~1.2in with padding -- affordable at five signal columns (it was not at
        # six, which is why the six-column build abbreviated it to "Flows").
        WID = {"Technical": 0.095, "Sector & Flows": 0.130}
        cols = [("Holding", 0.260, "l"), ("Wt %", 0.058, "r"), ("Ionic Score", 0.135, "l"),
                ("Call", 0.082, "c")]
        cols += [(c, WID.get(c, 0.080), "c") for c in F.CATS]
    else:
        cols = [("Holding", 0.22, "l"), ("Wt %", 0.07, "r"), ("Ionic Score", 0.15, "l"),
                ("Call", 0.10, "c"), ("Analyst read", 0.46, "l")]
    rows = []
    for e in rows_src[:nrows]:
        row = [("b", e["name"]),
               ("c", f"{e['weight_pct']:.1f}", INK),
               ("bar", e.get("ionic_score")),
               ("pill", e["rec"], e["rec"])]
        if F is not None:
            for _cat, v in F.signals(e):
                fill = F.dot(v)
                row.append(("dot", None if fill is None else F.to_rgb(fill)))
        else:
            row.append(clip_clause(e.get("analyst_read", ""), 58))
        rows.append(row)
    ty = deck.table(s, ML, 2.98, UW, cols, rows, rowh=ROWH, fs=9, hfs=8, maxrows=nrows)

    # legend — a colour grid with no key is decoration. ONE line, directly under the table: the first
    # draft stacked a "% of the universe" sub-label under each chip, which pushed the block into
    # source() at 6.66 and printed three layers of type on top of each other. The share now rides
    # inside the chip label, which keeps the honesty and costs no vertical space.
    # Legend: four colours, four words, and the not-scored ring. Nothing else. Principal, 2026-08-07 --
    # the band percentages and the explanatory sentence are both out. The words carry the meaning now,
    # which is exactly why the RELATIVE set is the default: "Top 25% / Upper / Lower / Bottom 25%" says
    # in the label what the removed sentence used to say in prose, so nothing is lost with it gone.
    if F is not None:
        DIA, PITCH, lx = 0.15, 1.42, ML
        for lab, fill in F.legend():
            deck.oval(s, lx, ty + 0.10, DIA, F.to_rgb(fill))
            deck.txt(s, lx + DIA + 0.08, ty + 0.04, PITCH - DIA - 0.16, 0.26,
                     [(lab, SANS, 8, INK, False)], anchor=MSO_ANCHOR.MIDDLE, wrap=False)
            lx += PITCH
        deck.oval(s, lx, ty + 0.10, DIA, None, line=SLATE, lw=0.9)
        deck.txt(s, lx + DIA + 0.08, ty + 0.04, 1.0, 0.26,
                 [(F.NO_DATA_WORD, SANS, 8, SLATE, False)], anchor=MSO_ANCHOR.MIDDLE, wrap=False)
        ty += 0.36

    # each row clicks through to the name's rationale page in the annexure (resolved at save)
    deck.anchor("tbl:book", s, prio=5)
    linked = ("sell_cards" in tier.get("optional_on", set())
              or "holdings_detail" in tier.get("optional_on", set()))
    ry = 2.98 + 0.33
    for e in rows_src[:nrows]:      # nrows, not MAXROWS: an extra hotspot would sit over the legend
        deck.hotspot(s, ML, ry - 0.02, UW, ROWH, f"stock:{e['symbol']}")
        ry += ROWH

    # NO source() and NO score_band() on this page any more -- Principal, 2026-08-07: "we have to modify
    # the last footnote aswell remove it all". Both were the standard chrome for a score-bearing slide,
    # so this page is deliberately the exception. Everything material they carried moved to the scope tag
    # at the top; the methodology they pointed at is score_method.py's page, which every tier includes.
    if ctx.get("is_demo", False):
        # The one line that cannot be dropped by preference: a synthetic book must never be mistakable
        # for a real one. Kept where the footnote used to sit, on demo builds only.
        deck.source(s, "Illustrative synthetic book.")
    return 1
