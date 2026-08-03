# -*- coding: utf-8 -*-
"""build_pac_showcase.py — the PRODUCT APPROVAL COMMITTEE / CEO deck for the NDPMS
Portfolio Review engine (2026-08-03).

Audience: PAC + CEO. INTERNAL, not client-facing. It explains what the product is, the
scoring and fund frameworks behind it, the end-to-end workflow, the quality-control
stack, the compliance posture, the honest limitations, and the specific approval sought
— and shows real rendered pages of the deliverable as evidence rather than describing
them.

Page snapshots are rendered live from the ABXY showcase PDF (the house demo book on an
aggressive IPS, `pr_template/build_abxy_showcase.py`). Pages are located by SEARCHING
THE PDF TEXT for each page's title, never by hard-coded page number, so this script
keeps working as the deck's module order changes.

Because the audience is internal, this deck deliberately uses internal vocabulary the
client-facing tell-scan forbids (framework names, engine internals). That is correct
here; tellscan's client-copy rules do not bind an internal committee paper.

Usage: python build_pac_showcase.py
Output: 09_PRODUCT/reports/IONIC_NDPMS_PRODUCT_APPROVAL_DECK.pptx
"""
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PRT = os.path.abspath(os.path.join(HERE, "..", "pr_template"))
sys.path.insert(0, PRT)

import slidekit as SK  # noqa: E402
from slidekit import (NAVY, NAVYD, INK, SLATE, GOLD, WHITE, HOLD, SELL, AMBER,
                      PANEL, HAIR, NT2, NT3, SERIF, SANS, ML, UW, RX, CW)  # noqa: E402
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR  # noqa: E402

ABXY_PDF = os.path.join(PRT, "out", "ABXY_Showcase_HNI_DEEP.pdf")
SNAPS = os.path.join(PRT, "_pac_snaps")
OUT = os.path.abspath(os.path.join(HERE, "..", "reports",
                                   "IONIC_NDPMS_PRODUCT_APPROVAL_DECK.pptx"))

AS_OF = "2026-08-03"

# ---------------------------------------------------------------------------
# Page snapshots: (title text on the page, caption, [min font pt to accept])
#
# Needles must be TITLE text, not body or label text, and must avoid hyphens: the
# renderer emits a hyphenated title as separate spans ("Single", "-", "name"), so
# "single-name" never matches as one string. The optional third element raises the
# size floor where a shorter needle would otherwise match a smaller heading — the
# cover's 40pt "Portfolio" versus the 30pt divider and 26pt page titles.
# ---------------------------------------------------------------------------
SNAP_SPECS = [
    ("Portfolio", "Cover. Client, mandate and as-of date, with the synthetic-book label printed on the page.", 35),
    ("Investment Policy", "The mandate page. Every parameter's Current column is computed live from the holdings, never typed."),
    ("Where the book differs", "Executive summary. Five gaps, each with one action and a pointer to the page that proves it."),
    ("Portfolio snapshot", "Snapshot. Composition, and an explicit statement of what is in scope versus out."),
    ("Concentration risk", "Concentration, measured against this mandate's own cap rather than a generic rule."),
    ("Sector exposure", "Sector weights, with a standing note that the fund sleeve is not looked through here."),
    ("Two horizons", "The scoring method, explained to the client in plain language."),
    ("the book, scored", "Every holding with its score, its call, and the desk's one-line read."),
    ("names we would sell", "The sell list. Confirmed sells only, each linked to its full rationale page."),
    ("fund book, scored", "The fund book: a 0-100 quality score and a grade for every scheme."),
    ("Tax impact", "Tax. Fund actions on the left, the direct-equity plan on the right, each scope named."),
    ("priority actions", "The action plan, in order, with amounts and an authorisation line."),
    ("Sell rationale", "One card per sell: the case, the bull we rejected, the reverse-DCF, and the exit test."),
    ("Scheme scorecard", "One scorecard per fund action, showing the metric battery behind the call."),
]


def _find_title_page(doc, needle, used, min_pt=15.0):
    """Page whose needle appears as TITLE-SIZE type.

    A plain text search is not enough: the contents page and every section divider list
    the module names in small type, so searching for "Scheme scorecard" matched the
    contents page (page 2) rather than a real scorecard. Requiring the matching line to
    be rendered at >= min_pt separates a page's own title from a reference to it.
    """
    nl = needle.lower()
    for pno in range(len(doc)):
        if pno in used:
            continue
        for blk in doc[pno].get_text("dict").get("blocks", []):
            for line in blk.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(sp.get("text", "") for sp in spans).lower()
                if nl in text and max(sp.get("size", 0) for sp in spans) >= min_pt:
                    return pno
    return None


def render_snapshots(dpi=150):
    """Render each SNAP_SPECS page from the ABXY PDF to PNG. Returns [(png, caption, page)]."""
    import fitz
    if not os.path.exists(ABXY_PDF):
        raise SystemExit(f"ABXY showcase PDF not found: {ABXY_PDF}\n"
                         f"Build it first: pr_template/build_abxy_showcase.py HNI_DEEP, then pptx_to_pdf.py")
    os.makedirs(SNAPS, exist_ok=True)
    doc = fitz.open(ABXY_PDF)
    out, used = [], set()
    for i, spec in enumerate(SNAP_SPECS):
        needle, caption = spec[0], spec[1]
        min_pt = spec[2] if len(spec) > 2 else 15.0
        hit = _find_title_page(doc, needle, used, min_pt=min_pt)
        if hit is None:
            print(f"  [SKIP] no title-size match for {needle!r} — page not included")
            continue
        used.add(hit)
        png = os.path.join(SNAPS, f"snap_{i:02d}_p{hit + 1:03d}.png")
        doc[hit].get_pixmap(dpi=dpi).save(png)
        out.append((png, caption, hit + 1))
        print(f"  snap {i:02d}: page {hit + 1:>3} <- {needle!r}")
    doc.close()
    if not out:
        raise SystemExit("No snapshots resolved — check SNAP_SPECS against the built deck.")
    return out


# ---------------------------------------------------------------------------
# slide helpers
# ---------------------------------------------------------------------------
def cover(deck):
    deck.folio += 1
    s = deck.slide(NAVY)
    try:
        import art
        deck.pic(s, art.flow_art("pac_cover_art", seed=17), 8.03, 0.10, 5.31, 7.40,
                 valign="top", halign="right")
    except Exception:
        pass
    deck.rect(s, 0, 0, CW, 0.10, fill=GOLD)
    deck.txt(s, ML, 0.52, 5.0, 0.4, [("IONIC ", SANS, 17, WHITE, True, False, 100),
                                     ("WEALTH", SANS, 17, NT3, False, False, 100)])
    deck.txt(s, ML, 0.92, 5.0, 0.22, [("BY ANGEL ONE", SANS, 7.5, GOLD, True, False, 260)])
    deck.txt(s, ML, 2.10, 7.2, 0.85, [("Portfolio Review ", SANS, 36, WHITE, True),
                                      ("Engine", SANS, 36, GOLD, True)])
    deck.txt(s, ML, 3.10, 7.2, 0.5, [("An NDPMS client-reporting product, end to end",
                                      SERIF, 15, NT3, False, True)])
    deck.txt(s, ML, 3.95, 7.2, 0.3, [("FOR REVIEW BY", SANS, 10, NT2, True, False, 260)])
    deck.txt(s, ML, 4.27, 7.2, 0.45, [("Product Approval Committee  ·  CEO", SANS, 19, WHITE, True)])
    deck.rule(s, ML, 4.88, 3.4, GOLD, 0.03)
    deck.txt(s, ML, 5.08, 7.2, 0.4,
             [("Methodology, workflow, controls, and the deliverable itself", SERIF, 12, NT3, False, True)])
    deck.txt(s, ML, 6.62, 7.4, 0.5,
             [("INTERNAL   ·   ", SANS, 8.5, GOLD, True, False, 120),
              (f"Prepared by the Portfolio Review desk   ·   As of {AS_OF}   ·   "
               "Sample pages use a synthetic demo book, never a real client's holdings",
               SANS, 8.5, NT2, False)])
    return s


def bullets(deck, s, x, y, w, items, gap=0.42, fs=11, bullet_color=GOLD):
    """Gold square bullet + serif body; returns the y after the last item."""
    for it in items:
        deck.rect(s, x, y + 0.07, 0.075, 0.075, fill=bullet_color)
        h = 0.30 if len(it) < 105 else 0.52
        deck.txt(s, x + 0.24, y - 0.035, w - 0.24, h, [(it, SERIF, fs, INK, False)], ls=1.06)
        y += gap if len(it) < 105 else gap + 0.20
    return y


def co(deck, s, x, y, w, title, body, kind="note", min_h=0.6, max_h=2.6):
    """Callout sized to its own text via callout_h. Hardcoding a height is how every
    clip-risk finding on this deck's first build happened. Returns the y after the box."""
    h = deck.callout_h(w, body, min_h=min_h, max_h=max_h)
    deck.callout(s, x, y, w, h, title, body, kind)
    return y + h


def numbered_flow(deck, s, y, steps, rowh=0.66):
    """Numbered step rows: navy disc, bold title, serif detail."""
    for i, (title, detail) in enumerate(steps, 1):
        deck.oval(s, ML, y + 0.05, 0.40, NAVY)
        deck.txt(s, ML, y + 0.05, 0.40, 0.40, [(str(i), SANS, 13, WHITE, True)],
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        deck.txt(s, ML + 0.58, y, 3.5, 0.28, [(title, SANS, 12, INK, True)])
        deck.txt(s, ML + 4.20, y - 0.01, UW - 4.20, 0.56, [(detail, SERIF, 10.5, SLATE, False)], ls=1.05)
        deck.rule(s, ML, y + rowh - 0.10, UW, HAIR, 0.006)
        y += rowh
    return y


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build():
    print("Rendering page snapshots from the ABXY showcase PDF ...")
    snaps = render_snapshots()

    deck = SK.new_deck()
    cover(deck)

    # ---------- the ask ----------
    s = deck.content(0, "The proposal", "What is being approved",
                     "A scored, evidence-backed portfolio review, produced as a repeatable product")
    deck.kpi_strip(s, [
        ("751 / 751", "Stocks scored", "quant + analyst", NAVY),
        ("3", "Client tiers", "depth by audience", INK),
        ("60", "Page modules", "one library", INK),
        ("4", "QA gate layers", "all must pass", HOLD),
        ("0", "Buy calls", "holdings review only", SELL),
    ], y=1.78)
    y = bullets(deck, s, ML, 3.05, UW - 5.9, [
        "The product is a client portfolio review: every direct holding and every fund carries a score, a call and a written reason.",
        "The engine is frozen and rerunnable. The same holdings file produces the same deck, and every number traces to a source.",
        "It reviews existing holdings only. The vocabulary is Sell, Trim or Hold, and nothing executes without the client's signature.",
        "Three depth tiers serve a family office, a typical NDPMS client and an RM-led conversation from one module library.",
    ])
    co(deck, s, ML + UW - 5.6, 3.05, 5.6, "The approval sought",
                 "Sign-off to use this engine as the standard NDPMS review deliverable for onboarding and "
                 "periodic reviews, on the frozen methodology and the four-layer QA gate described here, with "
                 "the Principal or CEO countersigning every client deck before it ships. Two real client books "
                 "have already been produced end to end under this process.", "human")
    deck.source(s, "Coverage as of 2026-08-03. Sample pages in this deck are rendered from a synthetic demo book.")

    # ---------- what it is ----------
    s = deck.content(0, "The proposal", "Input and output",
                     "One holdings statement in, one reviewed and signed deck out")
    numbered_flow(deck, s, 1.95, [
        ("Holdings statement", "A client's CAS, demat or CAMS/Kfintech statement. Parsed to a validated holdings table, with corrupted or unmatched rows flagged to the RM rather than dropped."),
        ("Match to coverage", "Equity matched by ISIN to the scored universe; funds matched by verified scheme identity to the fund frameworks. Anything unmatched is disclosed, never guessed."),
        ("Score and read", "Frozen scoring engine produces the numbers; a sector analyst writes the case. The analyst can rescue a score-driven Sell to Hold, and cannot force the reverse."),
        ("Assemble the deck", "The module library renders the tier the client's audience needs, computing every narrative sentence from the data rather than from stored prose."),
        ("Prove it", "Four QA layers: two geometry checks, a client-copy scan, and a visual read of the rendered pages. All must pass."),
        ("Sign and ship", "Principal or CEO countersignature, then the client copy. Nothing reaches a client unsigned."),
    ])
    co(deck, s, ML, 6.02, UW, "The point",
       "The judgment stays human. What the engine removes is the variance.", "note", min_h=0.55, max_h=0.58)

    # ================= SECTION 1 — the model =================
    deck.section_divider(1, "The model", "What produces a score, and what produces a call",
                         pages=["Scoring architecture", "Gates, penalties, and the call",
                                "The one number a client sees", "The fund frameworks", "Coverage today"])

    s = deck.content(1, "The model", "Scoring architecture",
                     "Two horizons, seven pillars, never blended at the analyst's desk")
    cols = [("Pillar", 0.30, "l"), ("What it measures", 0.42, "l"),
            ("3-Year weight", 0.14, "r"), ("1-Year weight", 0.14, "r")]
    rows = [
        [("b", "Quality"), "Return on equity and capital, ranked within sector", "20%", "16%"],
        [("b", "Growth"), "Revenue compounding, three-year and trailing-twelve-month", "20%", "16%"],
        [("b", "Value"), "Earnings, book and cash-flow yield versus sector and size peers", "18%", "16%"],
        [("b", "Stage / technical"), "Price trend against its own history and its sector", "14%", "26%"],
        [("b", "Sector & macro"), "Sector strength, adjusted for cyclicality in the current regime", "11%", "13%"],
        [("b", "Ownership flow"), "Institutional buying and selling across recent quarters", "9%", "8%"],
        [("b", "Accumulation"), "Volume-flow trend behind the price", "8%", "5%"],
    ]
    deck.table(s, ML, 1.95, UW, cols, rows, rowh=0.40, fs=10, hfs=8, zebra=True)
    co(deck, s, ML, 5.02, (UW - 0.3) / 2, "Why two horizons",
                 "A three-year score leans on fundamentals; a one-year score leans on market behaviour. Keeping "
                 "them apart means a good business in a bad tape and a weak business in a strong tape read "
                 "differently, instead of averaging into the same middle.", "note")
    co(deck, s, ML + (UW - 0.3) / 2 + 0.3, 5.02, (UW - 0.3) / 2, "Discipline behind the ranks",
                 "Every input is winsorised before ranking, so one outlier cannot claim an extreme percentile. "
                 "Value ranks within sector and size tier, because a cement multiple and a software multiple are "
                 "not comparable numbers.", "note")
    deck.source(s, "Frozen scoring contract; discounted-cash-flow is deliberately excluded as a mechanical pillar and lives as the analyst's own reverse-DCF judgment.")

    s = deck.content(1, "The model", "Gates, penalties, and the call",
                     "A score can be capped by risk before it is ever compared")
    deck.txt(s, ML, 1.90, UW, 0.30,
             [("Overlay gates apply after the weighted composite and can cap a score outright.",
               SERIF, 11, INK, False, True)])
    gcols = [("Gate", 0.22, "l"), ("Trips when", 0.44, "l"), ("Effect", 0.34, "l")]
    grows = [
        [("b", "Balance-sheet safety"), "Debt/equity above 2.5x or interest cover below 1.5x", ("c", "Caps the score at 40", SELL)],
        [("b", "Balance-sheet caution"), "Debt/equity above 1.5x or interest cover below 3x", ("c", "Multiplies the score by 0.85", AMBER)],
        [("b", "Liquidity"), "Median traded value below the bar for the stock's size tier", ("c", "Caps the score at 40", SELL)],
    ]
    deck.table(s, ML, 2.28, UW, gcols, grows, rowh=0.42, fs=10, hfs=8)
    half = (UW - 0.3) / 2
    co(deck, s, ML, 3.94, half, "The lenders exemption",
       "Banks, NBFCs and insurers are exempt from the debt/equity trigger: leverage is their business model, "
       "not distress. They are judged on asset quality instead.", "good", min_h=1.02, max_h=1.06)
    co(deck, s, ML + half + 0.3, 3.94, half, "Red flags compound",
       "Penalties scale non-linearly, so several problems are punished far harder than one blemish. A clean "
       "bill of health earns a small capped boost.", "note", min_h=1.02, max_h=1.06)
    deck.txt(s, ML, 5.18, UW, 0.28, [("THE CALL", SANS, 9, SLATE, True, False, 200)])
    for i, (band, rec, kind) in enumerate([("Score below 40, on either horizon", "Sell", "Sell"),
                                           ("40 to 50, with a concentration or risk flag", "Trim", "Trim"),
                                           ("50 and above", "Hold", "Hold")]):
        bx = ML + i * ((UW - 0.6) / 3 + 0.3)
        bw = (UW - 0.6) / 3
        deck.rect(s, bx, 5.48, bw, 0.52, fill=PANEL, line=HAIR, round_=0.06)
        deck.txt(s, bx + 0.16, 5.48, bw - 1.5, 0.52, [(band, SERIF, 10, INK, False)], anchor=MSO_ANCHOR.MIDDLE)
        deck.pill(s, bx + bw - 1.25, 5.60, rec, w=1.05, kind=kind)
    co(deck, s, ML, 6.12, UW, "One-way override",
       "A Sell can be rescued to Hold with a written reason. A Hold cannot be forced to Sell; it escalates.",
       "human", min_h=0.48, max_h=0.50)

    s = deck.content(1, "The model", "The one number a client sees",
                     "A blended score, then a bounded forward adjustment")
    deck.rect(s, ML, 1.92, UW, 0.72, fill=PANEL, line=HAIR, round_=0.06)
    deck.txt(s, ML + 0.3, 1.92, UW - 0.6, 0.72,
             [("Ionic Score   =   0.60 x three-year score   +   0.40 x one-year score   +   forward adjustment",
               SANS, 14, NAVY, True)], anchor=MSO_ANCHOR.MIDDLE)
    deck.txt(s, ML, 2.86, UW, 0.28,
             [("The adjustment makes the number forward-looking. It is bounded, and it can never flatter a name we are telling the client to exit.",
               SERIF, 11, INK, False, True)])
    fcols = [("Analyst's forward growth view", 0.46, "l"), ("Adjustment", 0.22, "c"), ("Reading", 0.32, "l")]
    frows = [
        [("b", "Below 5%"), ("c", "-15", SELL), "Structurally stagnant or declining"],
        [("b", "5 to 10%"), ("c", "-5", SELL), "Below nominal growth in the economy"],
        [("b", "10 to 15%"), ("c", "0", SLATE), "Steady compounder, the neutral zone"],
        [("b", "15 to 20%"), ("c", "+5", HOLD), "Strong"],
        [("b", "20 to 25%"), ("c", "+10", HOLD), "Exceptional momentum"],
        [("b", "25% and above"), ("c", "+15", HOLD), "Hypergrowth, evidence required"],
    ]
    deck.table(s, ML, 3.24, UW - 5.5, fcols, frows, rowh=0.36, fs=9.5, hfs=8, zebra=True)
    co(deck, s, ML + UW - 5.2, 3.24, 5.2, "Two coherence caps",
                 "A name growing below 10% can be marked down but never up. And a name the analyst rates Sell "
                 "can never be lifted by the adjustment. Both caps exist because earlier versions could "
                 "perversely raise the score of a name we were recommending the client exit.", "warn")
    co(deck, s, ML + UW - 5.2, 4.76, 5.2, "Conviction, priced",
                 "Where the analyst and the engine disagree, the disagreement itself moves the score: a rescued "
                 "Sell earns a small credit, an analyst Sell a small debit. Agreement moves nothing.", "note")
    deck.source(s, "Growth is the analyst's forward three-to-five-year view, explicitly not trailing growth. Parroting trailing growth into this field is a named failure mode in the analyst brief.")

    s = deck.content(1, "The model", "The fund frameworks",
                     "Two independent engines, and a deliberately hard bar to sell a fund")
    deck.rect(s, ML, 1.92, (UW - 0.3) / 2, 1.62, fill=PANEL, line=HAIR, round_=0.06)
    deck.rect(s, ML, 1.92, 0.06, 1.62, fill=NAVY)
    deck.txt(s, ML + 0.24, 2.04, (UW - 0.3) / 2 - 0.5, 0.30, [("SHORT-TERM FRAMEWORK", SANS, 9, NAVY, True, False, 150)])
    deck.txt(s, ML + 0.24, 2.34, (UW - 0.3) / 2 - 0.5, 1.10,
             [("Ranks every fund in a category on how much of its benchmark's rise it captures versus how much "
               "of the fall, over a common six-month window, then applies a downside filter after ranking. "
               "Covers 181 funds across six categories.", SERIF, 10.5, INK, False)], ls=1.06)
    x2 = ML + (UW - 0.3) / 2 + 0.3
    deck.rect(s, x2, 1.92, (UW - 0.3) / 2, 1.62, fill=PANEL, line=HAIR, round_=0.06)
    deck.rect(s, x2, 1.92, 0.06, 1.62, fill=GOLD)
    deck.txt(s, x2 + 0.24, 2.04, (UW - 0.3) / 2 - 0.5, 0.30, [("LONG-TERM FRAMEWORK", SANS, 9, GOLD, True, False, 150)])
    deck.txt(s, x2 + 0.24, 2.34, (UW - 0.3) / 2 - 0.5, 1.10,
             [("A curated shortlist of 40 funds across eight categories, scored 0-100 with a letter grade and a "
               "conviction level, built for a multi-year holding rather than a six-month window. It carries no "
               "negative verdict by design.", SERIF, 10.5, INK, False)], ls=1.06)
    co(deck, s, ML, 3.74, UW, "The dual-framework rule",
                 "A fund is only recommended for sale when BOTH frameworks independently say sell. A buy signal "
                 "on either side vetoes the sale, and any disagreement defaults to Hold. The bar is intentionally "
                 "high: switching a fund costs the client tax and time, so the evidence has to be unambiguous.", "human")
    y = bullets(deck, s, ML, 4.90, UW, [
        "Category coverage is honest: hybrid, sectoral, index, liquid and debt funds sit outside both frameworks and are reported as No View, never given a manufactured score.",
        "Scheme identity is verified fund by fund, with the fund house and mandate confirmed. Name-similarity matching is prohibited after it produced real mis-matches.",
        "A fund with under seven months of record gets No View regardless of what the engines compute.",
    ], gap=0.40, fs=10.5)
    deck.source(s, "Fund models re-run at April-end and October-end; monthly net-asset-value history accrues in between so each run has a full window.")

    s = deck.content(1, "The model", "Coverage today", "What is actually scored, as of this review")
    deck.kpi_strip(s, [
        ("751", "Stocks in the universe", "quant layer complete", NAVY),
        ("751", "With analyst research", "100% coverage", HOLD),
        ("560 / 191", "Hold / Sell", "the current book of calls", INK),
        ("126", "Escalations", "open for desk ruling", AMBER),
        ("2", "Client books shipped", "end to end", NAVY),
    ], y=1.80)
    bullets(deck, s, ML, 3.10, UW - 6.0, [
        "Full analyst coverage was reached on 3 August 2026: all 751 names carry an engine score and a written human case.",
        "191 Sells against 560 Holds is about a quarter of the universe, in line with the engine's historical rate. Far below that would suggest override leakage.",
        "The 126 escalations are a feature, not a backlog: cases where an analyst thinks a passing score is wrong and is barred from forcing the change.",
        "Two real client books already run on this exact process.",
    ], gap=0.44, fs=10.5)
    y = co(deck, s, ML + UW - 5.7, 3.10, 5.7, "Refresh, not rebuild",
           "Coverage is maintained weekly by an incremental router, not a full re-run: names that reported get "
           "fresh research, news-only names get a cheap delta look, the rest carry forward.", "note",
           min_h=1.30, max_h=1.45)
    co(deck, s, ML + UW - 5.7, y + 0.18, 5.7, "What is not claimed",
       "Coverage is not a track record. These are point-in-time reviews, and the engine has not yet run through "
       "a full market cycle under this operating model.", "warn", min_h=1.05, max_h=1.20)

    # ================= SECTION 2 — workflow =================
    deck.section_divider(2, "The workflow", "How a review actually gets produced, and on what cadence",
                         pages=["The weekly refresh loop", "Cadence and ownership", "Decision rights"])

    s = deck.content(2, "The workflow", "The weekly refresh loop",
                     "Three lanes, so cost scales with what actually changed")
    lcols = [("Lane", 0.16, "l"), ("Triggered by", 0.30, "l"), ("What happens", 0.40, "l"), ("Cost", 0.14, "c")]
    lrows = [
        [("pill", "Full", "Sell"), "A results print landed since the last research", "Complete analyst pass, rewritten thesis", ("c", "Highest", SELL)],
        [("pill", "Delta", "Trim"), "News only: a rating action, deal, or management change", "The cached thesis is kept and only the new item is assessed", ("c", "Low", AMBER)],
        [("pill", "Carry", "Hold"), "Nothing material since the last look", "The existing call carries forward, journalled", ("c", "Near zero", HOLD)],
    ]
    deck.table(s, ML, 1.95, UW, lcols, lrows, rowh=0.52, fs=10, hfs=8)
    co(deck, s, ML, 3.74, UW, "Why this matters commercially",
       "The Full list comes deterministically from the earnings calendar, so the expensive work is bounded and "
       "predictable. Maintaining 751 names does not cost 751 research passes a week.", "good",
       min_h=0.78, max_h=0.82)
    y = bullets(deck, s, ML, 4.72, UW, [
        "Every state change is journalled per stock, so the history of a call is auditable rather than overwritten.",
        "Client workbooks and decks rebuild from that state, which is why a rerun reproduces the same deliverable.",
        "The router is scheduled, not manual: the cadence is a standing calendar entry, not something a person has to remember.",
    ], gap=0.40, fs=10.5)

    s = deck.content(2, "The workflow", "Cadence and ownership", "What runs when, and who owns it")
    ccols = [("Cadence", 0.16, "l"), ("What runs", 0.46, "l"), ("Owner", 0.20, "l"), ("Automated", 0.18, "c")]
    crows = [
        [("b", "Weekly"), "Stock re-score through the incremental router", "Portfolio Review desk", ("c", "Yes", HOLD)],
        [("b", "Weekly"), "Paper reconciliation and the risk pack", "Risk", ("c", "Yes", HOLD)],
        [("b", "Monthly"), "Fund net-asset-value history refresh", "Data", ("c", "Yes", HOLD)],
        [("b", "Monthly"), "Month-end checkpoint and analytics pack", "CEO office", ("c", "Yes", HOLD)],
        [("b", "Apr / Oct"), "Full fund-model re-run and reconciliation", "Fund desk", ("c", "Yes", HOLD)],
        [("b", "Apr / Oct"), "Client deck rebuild for every active mandate", "Portfolio Review desk", ("c", "Draft only", AMBER)],
        [("b", "Per client"), "Onboarding review on a new statement", "Relationship manager", ("c", "On demand", SLATE)],
    ]
    deck.table(s, ML, 1.95, UW, ccols, crows, rowh=0.42, fs=10, hfs=8, zebra=True)
    co(deck, s, ML, 5.08, UW, "The one deliberate manual gate",
                 "Deck rebuilds are automated only as far as a marked draft. A client copy requires a human "
                 "countersignature every single time. That gate is not an efficiency gap left to close later; it "
                 "is the control that keeps an automated pipeline from ever speaking to a client on its own.", "human")
    deck.source(s, "Scheduled jobs are re-armed each working session from the operating calendar, which is the source of truth if the two ever disagree.")

    s = deck.content(2, "The workflow", "Decision rights", "Who can change what, and where disagreement goes")
    dcols = [("Decision", 0.34, "l"), ("Who decides", 0.28, "l"), ("Control", 0.38, "l")]
    drows = [
        [("b", "A stock's score"), "The frozen engine", "No human edits a score. The methodology changes only by signed amendment."],
        [("b", "A Sell becoming a Hold"), "Sector analyst", "Permitted, with a written reason recorded against the name."],
        [("b", "A Hold becoming a Sell"), ("c", "Nobody, directly", SELL), "Barred. The analyst escalates and the desk rules."],
        [("b", "Trim levels and sizing"), "Fund manager", "Judgment, disclosed as such in the deck, not a formula output."],
        [("b", "Methodology change"), "Quant head plus red team", "Joint sign-off; comparability with the prior record is documented."],
        [("b", "A deck reaching a client"), ("c", "Principal or CEO", NAVY), "Countersignature on every deck, with no standing exemption."],
    ]
    deck.table(s, ML, 1.95, UW, dcols, drows, rowh=0.50, fs=10, hfs=8, zebra=True)
    half = (UW - 0.3) / 2
    co(deck, s, ML, 5.32, half, "The asymmetry is the point",
       "It is easy to talk yourself into holding something you like. Letting the engine originate only Sells "
       "puts the burden of proof on optimism.", "note", min_h=1.02, max_h=1.08)
    co(deck, s, ML + half + 0.3, 5.32, half, "Escalation is narrow on purpose",
       "Stale prices and ordinary uncertainty are not escalation-worthy, so the channel stays readable instead "
       "of becoming a queue nobody works.", "note", min_h=1.02, max_h=1.08)

    # ================= SECTION 3 — quality control =================
    deck.section_divider(3, "Quality control", "What stops a wrong page reaching a client",
                         pages=["The gate stack", "What went wrong, and what we changed"])

    s = deck.content(3, "Quality control", "The gate stack", "Four layers, each catching what the others cannot")
    qsteps = [
        ("Geometry", "Two independent checks for text overflowing its box, elements overlapping, and content spilling past the page frame. Machine-checkable, run on every build."),
        ("Client copy", "A scan for internal vocabulary, engine codenames, source citations, recommendation language we do not use, and unrenderable characters. Also run against the data file, because a scrub at render time cannot rescue a whole sentence of internal audit trail."),
        ("Visual read", "The deck is converted to PDF and pages are actually looked at. This layer exists because the geometry checks inspect declared shape positions, not rendered pixels, and a real clipped table survived both of them."),
        ("Reconciliation", "Any figure appearing on two pages must reconcile or be explicitly scoped. Counts on a summary page are computed from the same source as the detail pages, never retyped."),
    ]
    numbered_flow(deck, s, 1.95, qsteps, rowh=0.92)
    co(deck, s, ML, 5.82, UW, "Then, and only then, a person",
                 "Passing all four gates makes a deck eligible for review, not approved. The Principal or CEO "
                 "countersignature is the fifth layer, and it is the one that actually authorises a client copy.", "human")

    s = deck.content(3, "Quality control", "What went wrong, and what we changed",
                     "The controls above exist because these things actually happened")
    icols = [("What we found", 0.40, "l"), ("Why it was dangerous", 0.32, "l"), ("What changed", 0.28, "l")]
    irows = [
        [("b", "A fabricated breach"), "A page asserted a concentration limit breach that did not exist in the book, contradicting a correctly-computed page in the same deck",
         "Narrative sentences are now computed from the data; hard-coded client-specific claims are treated as defects"],
        [("b", "Name-similarity fund matching"), "Matched a mid-cap fund to a multi-cap fund, and a liquid fund to an equity fund",
         "Similarity matching prohibited. Identity is verified per fund, with alias and rename tables in code"],
        [("b", "A corrupted holdings row"), "One holding's name field silently absorbed another holding's data during statement parsing",
         "Every parsed row is validated on intake; suspect rows are flagged to the RM, never silently trusted"],
        [("b", "A missing score shown as zero"), "An unscored holding read as a score of zero, which is a real and very bad score",
         "Unscored is now visibly blank and labelled No View; zero is reserved for an actual zero"],
        [("b", "A clipped table"), "A total row was covered by the panel beneath it, and both geometry checks passed it",
         "The visual read became a required gate rather than a nice-to-have"],
    ]
    deck.table(s, ML, 1.95, UW, icols, irows, rowh=0.72, fs=9.5, hfs=8, zebra=True)
    co(deck, s, ML, 5.72, UW, "Why this page is in a committee deck",
                 "A product review that shows only what works is not evidence. Each of these was found by our own "
                 "checks before any client saw it, each is now closed in code rather than in a checklist, and the "
                 "same failure cannot recur silently.", "good")

    # ================= SECTION 4 — the deliverable =================
    deck.section_divider(4, "The deliverable", "Real rendered pages from the review deck",
                         pages=["Understanding the mandate", "The portfolio x-ray",
                                "The equity book", "The fund book", "Recommendations", "Annexure evidence"])

    # snapshot pages: two per slide with captions
    per = 2
    for i in range(0, len(snaps), per):
        chunk = snaps[i:i + per]
        n = i // per + 1
        total = (len(snaps) + per - 1) // per
        s = deck.content(4, "The deliverable", "Sample pages",
                         f"How it looks in the client's hands  ({n} of {total})")
        colw = (UW - 0.4) / 2
        for j, (png, caption, pno) in enumerate(chunk):
            x = ML + j * (colw + 0.4)
            deck.rect(s, x, 1.94, colw, colw * 0.5625 + 0.04, fill=PANEL, line=HAIR)
            deck.pic(s, png, x + 0.02, 1.96, colw - 0.04, colw * 0.5625,
                     valign="middle", halign="center")
            cy = 1.94 + colw * 0.5625 + 0.16
            deck.txt(s, x, cy, colw, 0.24, [(f"PAGE {pno}", SANS, 8, GOLD, True, False, 200)])
            deck.txt(s, x, cy + 0.24, colw, 0.85, [(caption, SERIF, 10, INK, False)], ls=1.06)
        deck.source(s, "Rendered from the house demo book on an aggressive mandate. Synthetic holdings, real engine, real template.")

    # ================= SECTION 5 — controls, risks, ask =================
    deck.section_divider(5, "Controls and the ask", "Compliance posture, honest limitations, and the decision",
                         pages=["Compliance posture", "What this product does not do yet", "The ask"])

    s = deck.content(5, "Controls and the ask", "Compliance posture",
                     "Built for a non-discretionary mandate, and constrained accordingly")
    pcols = [("Control", 0.30, "l"), ("How it is enforced", 0.70, "l")]
    prows = [
        [("b", "No buy recommendations"), "The vocabulary is Sell, Trim or Hold. This is a review of holdings the client already owns, not a solicitation. The word is blocked by the client-copy scan."],
        [("b", "No target prices"), "No page carries a price objective or an implied return promise. Valuation is expressed as a judgment on what the multiple already assumes."],
        [("b", "Nothing executes on its own"), "The mandate is non-discretionary. Every deck states that nothing is executed until the client authorises it, and carries a signature line."],
        [("b", "Tax is flagged as an estimate"), "Tax characterisations are labelled indicative, with the client's own adviser named as the authority before dealing."],
        [("b", "Gaps are disclosed, not filled"), "Where cost basis, coverage or fund data is missing, the deck says so on the page rather than substituting an assumption."],
        [("b", "Every client copy is signed"), "Principal or CEO countersignature, with no standing exemption for a repeat client or a routine refresh."],
    ]
    ty = deck.table(s, ML, 1.92, UW, pcols, prows, rowh=0.52, fs=10, hfs=8, zebra=True)
    co(deck, s, ML, ty + 0.16, UW, "The standing rule behind all of it",
       "We do not fabricate. An estimate is labelled an estimate, a gap is shown as a gap, and a number we "
       "cannot source does not go on a client page. Every control above follows from that one commitment.",
       "human", min_h=0.78, max_h=0.86)

    s = deck.content(5, "Controls and the ask", "What this product does not do yet",
                     "The open items, stated plainly")
    y = bullets(deck, s, ML, 1.92, UW, [
        "Fund expense ratios render from a single placeholder, not each scheme's real figure. Visible on the scorecard pages, and first to close.",
        "Hybrid, sectoral, index, liquid and debt funds have no quality framework and show as No View, leaving part of a typical fund book unscored.",
        "Equity cost basis is absent from a CAS statement, so share-sale tax is a disclosed estimate rather than a computed figure.",
        "The long-term fund framework covers a curated 40 funds; a holding outside it gets the short-term view only, or none.",
        "There is no live performance track record yet. Coverage and process are demonstrable today; outcomes will take cycles.",
        "Fund look-through into true sector and single-name exposure is built but not yet wired into every page.",
    ], gap=0.44, fs=10.5)
    co(deck, s, ML, y + 0.14, UW, "Why the committee is seeing this list",
       "None of these block shipping a review today, because each is disclosed on the page where it matters. "
       "They are here so approval is given with the gaps in view, and so the committee can rank them.",
       "warn", min_h=0.78, max_h=0.86)

    s = deck.content(5, "Controls and the ask", "The ask", "What we would like the committee to approve")
    deck.rect(s, ML, 1.92, UW, 1.30, fill=PANEL, line=NAVY, lw=1.1, round_=0.06)
    deck.rect(s, ML, 1.92, 0.07, 1.30, fill=GOLD)
    deck.txt(s, ML + 0.28, 2.06, UW - 0.6, 0.30, [("APPROVAL SOUGHT", SANS, 9.5, GOLD, True, False, 200)])
    deck.txt(s, ML + 0.28, 2.36, UW - 0.6, 0.80,
             [("Adopt this engine as the standard NDPMS portfolio-review deliverable for client onboarding and "
               "periodic reviews, on the frozen methodology, the four-layer quality gate, and the signature "
               "requirement described in this deck.", SERIF, 13, INK, False)], ls=1.08)
    y = bullets(deck, s, ML, 3.42, UW, [
        "Confirm the Sell, Trim and Hold vocabulary and the no-buy, no-target-price posture as permanent product constraints.",
        "Confirm the one-way override rule and the escalation channel as the standing way analyst disagreement is handled.",
        "Confirm that every client copy requires a Principal or CEO countersignature, with no standing exemption.",
        "Direct which of the open items on the previous page should be closed first, and by when.",
    ], gap=0.44, fs=11)
    deck.txt(s, ML, 5.42, UW, 0.28, [("SIGN-OFF", SANS, 9, SLATE, True, False, 200)])
    for i, role in enumerate(["Product Approval Committee", "Chief Executive Officer", "Chief Investment Officer"]):
        bx = ML + i * ((UW - 0.6) / 3 + 0.3)
        bw = (UW - 0.6) / 3
        deck.rule(s, bx, 6.16, bw - 0.3, HAIR, 0.01)
        deck.txt(s, bx, 6.22, bw, 0.26, [(role, SANS, 9, INK, True)])
        deck.txt(s, bx, 6.44, bw, 0.24, [("Name, signature, date", SERIF, 8.5, SLATE, False, True)])
    deck.source(s, "Internal committee paper. Sample pages use a synthetic demo book; no real client holdings appear in this deck.")

    deck.resolve_links()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    path = OUT
    for attempt in range(3):
        try:
            deck.save(path)
            break
        except PermissionError:
            path = OUT.replace(".pptx", f"_v{attempt + 2}.pptx")
    print(f"\nSaved {deck.folio} slides -> {path}")
    return path


if __name__ == "__main__":
    build()
