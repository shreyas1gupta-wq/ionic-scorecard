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

AS_OF = "2026-08-04"

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
    deck.txt(s, ML, 4.27, 7.2, 0.45, [("Product Approval Committee", SANS, 19, WHITE, True)])
    deck.rule(s, ML, 4.88, 3.4, GOLD, 0.03)
    deck.txt(s, ML, 5.08, 7.2, 0.4,
             [("Methodology, workflow, controls, and the deliverable itself", SERIF, 12, NT3, False, True)])
    # 6.62 + 0.5 put the effective bottom at 7.12, two hundredths into the footer band. It was
    # invisible until check_geometry2's exemption stopped keying on the words "portfolio review",
    # which this very line happens to contain.
    deck.txt(s, ML, 6.54, 7.4, 0.5,
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
    ], y=1.78)
    y = bullets(deck, s, ML, 3.05, UW - 5.9, [
        "The product is a client portfolio review: every direct holding and every fund carries a score, a call and a written reason.",
        "The engine is frozen and rerunnable. The same holdings file produces the same deck, and every number traces to a source.",
        "It reviews existing holdings only, and the vocabulary is Sell, Trim or Hold.",
        "Three depth tiers serve a family office, a typical NDPMS client and an RM-led conversation from one module library.",
    ])
    co(deck, s, ML + UW - 5.6, 3.05, 5.6, "The approval sought",
       "Sign-off to use this engine as the standard NDPMS review deliverable for onboarding and "
       "periodic reviews, on the frozen methodology and the four-layer quality gate described here. "
       "Two real client books have already been produced end to end under this process.", "human",
       min_h=1.55, max_h=1.85)
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
        ("Analyst sign-off", "The reviewing analyst confirms the pack, name by name, before it goes to the client."),
    ])
    co(deck, s, ML, 6.02, UW, "The point",
       "The judgment stays human. What the engine removes is the variance.", "note", min_h=0.55, max_h=0.58)

    # ---------- why do it this way at all ----------
    s = deck.content(0, "The proposal", "Engine-led review against a manual one",
                     "The same judgment, reached faster and applied to everything the client owns")
    ccols = [("", 0.26, "l"), ("A manual review", 0.37, "l"), ("This engine", 0.37, "l")]
    crows = [
        [("b", "Turnaround per client"), "About a week", ("c", "A few hours", HOLD, True)],
        [("b", "Holdings covered"), "The larger names, sampled", ("c", "Every holding, no sampling", HOLD, True)],
        [("b", "Scored universe behind it"), "None maintained", ("c", "751 names, refreshed weekly", HOLD, True)],
        [("b", "Consistency between reviewers"), "Varies with who does it", "One weight set, applied identically"],
        [("b", "Audit trail"), "Notes, if they were kept", "Dated research and journalled state, per name"],
        [("b", "Cost of the next client"), "Another full cycle", "Assembly is scripted; research is incremental"],
        [("b", "What stays human"), "Everything", ("c", "The call, the override, the sign-off", NAVY, True)],
    ]
    deck.table(s, ML, 1.95, UW, ccols, crows, rowh=0.44, fs=10, hfs=8, zebra=True)
    co(deck, s, ML, 5.46, UW, "What this comparison is not saying",
       "Not that the engine reviews better than an analyst. That the analyst should spend their time on "
       "judgment rather than assembling arithmetic, and a client with 98 holdings should get all 98 looked "
       "at. The week-versus-hours figure is our own estimate, not a measured benchmark.", "human",
       min_h=0.80, max_h=0.88)
    deck.source(s, "Turnaround and coverage for the engine are observed from the two client books produced to date; the manual baseline is an internal estimate and is labelled as such.")

    # ================= SECTION 1 — the model =================
    deck.section_divider(1, "The model", "What produces a score, what produces a call, and what the evidence shows",
                         pages=["Scoring architecture", "Where the weights come from",
                                "Gates and the call", "The one number a client sees",
                                "Coverage, and does it work"])

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

    # ---------- weight provenance: the single most likely question ----------
    s = deck.content(1, "The model", "Where the weights come from",
                     "Set by judgment, not fitted to returns, and we would rather say so")
    deck.kpi_strip(s, [
        ("58 / 42", "3-year split", "fundamentals / market", NAVY),
        ("48 / 52", "1-year split", "fundamentals / market", NAVY),
        ("0", "weights fitted to returns", "none optimised", SELL),
        ("8", "quarterly rebalances", "of clean point-in-time data", AMBER),
    ], y=1.78)
    bullets(deck, s, ML, 3.05, UW - 5.9, [
        "The weights encode a stated view: over three years fundamentals should dominate, over one year market behaviour should. The shipped weights deliver exactly that, at 58/42 and 48/52.",
        "No weight was fitted to maximise a backtested return. With eight quarterly rebalances of clean history, optimising would be curve-fitting dressed as rigour.",
        "What we do claim is narrower and checkable: one set of weights applied identically to every name, frozen, versioned, and changeable only by signed amendment.",
        "The weights are a hypothesis the forward record will judge, not a proven finding.",
    ], gap=0.46, fs=10.5)
    y = co(deck, s, ML + UW - 5.6, 3.05, 5.6, "The live question on this page",
           "Value sits at 18% of the three-year score, the smallest of the three fundamental pillars, "
           "which is arguably wrong for a discipline whose job is deciding what to exit. Raising it is "
           "under consideration.", "human", min_h=1.30, max_h=1.45)
    co(deck, s, ML + UW - 5.6, y + 0.16, 5.6, "Why we have not simply raised it",
       "Sixty per cent of the Value pillar is price-to-earnings by construction, so moving Value from "
       "18% to 25% would take that one ratio from 10.8% to 15.0% of the whole score, and a low-multiple "
       "tilt in India loads onto public-sector and cyclical names. Valuation also already enters twice "
       "more, through the analyst's own reverse-DCF and the forward adjustment. We would rather test it "
       "on the point-in-time harness than assert it.", "warn", min_h=1.60, max_h=1.90)
    deck.source(s, "Splits are the fundamentals block (quality, growth, value) against the market block (stage, sector and macro, ownership, accumulation), computed from the shipped weights on the previous page.")

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
    deck.txt(s, ML + 0.24, 2.04, (UW - 0.3) / 2 - 0.5, 0.30,
             [("QFRA-1", SANS, 9, NAVY, True, False, 150),
              ("   ·   SHORT-TERM FRAMEWORK", SANS, 9, SLATE, True, False, 150)])
    deck.txt(s, ML + 0.24, 2.34, (UW - 0.3) / 2 - 0.5, 1.10,
             [("Ranks every fund in a category on how much of its benchmark's rise it captures versus how much "
               "of the fall, over a common six-month window, then applies a downside filter after ranking. "
               "Covers 181 funds across six categories.", SERIF, 10.5, INK, False)], ls=1.06)
    x2 = ML + (UW - 0.3) / 2 + 0.3
    deck.rect(s, x2, 1.92, (UW - 0.3) / 2, 1.62, fill=PANEL, line=HAIR, round_=0.06)
    deck.rect(s, x2, 1.92, 0.06, 1.62, fill=GOLD)
    deck.txt(s, x2 + 0.24, 2.04, (UW - 0.3) / 2 - 0.5, 0.30,
             [("QFRA-2", SANS, 9, GOLD, True, False, 150),
              ("   ·   LONG-TERM FRAMEWORK", SANS, 9, SLATE, True, False, 150)])
    deck.txt(s, x2 + 0.24, 2.34, (UW - 0.3) / 2 - 0.5, 1.10,
             [("A curated shortlist of 40 funds across eight categories, scored 0-100 with a letter grade and a "
               "conviction level, built for a multi-year holding rather than a six-month window. Its only two "
               "verdicts are Active and Index-core: it has NO sell verdict, by design.", SERIF, 10.5, INK, False)], ls=1.06)
    co(deck, s, ML, 3.72, UW, "How a fund actually gets sold, stated precisely",
       "QFRA-1 is the only engine that can originate a sell, because it is the only one with a sell verdict. "
       "QFRA-2 cannot vote to sell; it can only veto one, since an Active rating is evidence against exiting. "
       "Absence from its curated forty is not a negative signal. Disagreement defaults to Hold.",
       "human", min_h=0.94, max_h=1.02)
    y = bullets(deck, s, ML, 4.92, UW, [
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

    # ---------- evidence: the "does it work" question, answered honestly ----------
    s = deck.content(1, "The model", "Does it work",
                     "What the point-in-time test shows, and what it does not")
    ecols = [("Basket, equal-weight, quarterly rebalance", 0.44, "l"), ("CAGR", 0.18, "r"),
             ("Sharpe", 0.18, "r"), ("Max drawdown", 0.20, "r")]
    erows = [
        [("b", "Top 10 by score"), ("c", "41.3%", HOLD, True), "1.28", ("c", "-2.3%", HOLD, True)],
        [("b", "Bottom 10 by score"), "32.4%", "0.89", ("c", "-12.6%", SELL)],
        [("b", "Nifty 500, cap-weighted total return"), "30.3%", "1.75", "-5.6%"],
        [("b", "Eligible universe, equal-weighted"), ("c", "44.3%", AMBER), "2.00", "-6.2%"],
    ]
    # vertical budget is tight on this page: table ends ~3.85, note to 4.16, the paired
    # callouts to ~5.58, and the closing line must still clear the source rule at 6.66.
    deck.table(s, ML, 1.92, UW, ecols, erows, rowh=0.40, fs=10, hfs=8, zebra=True)
    deck.txt(s, ML, 3.92, UW, 0.24,
             [("December 2021 to September 2024, 8 quarterly rebalances. Survivorship-safe universe, "
               "fundamentals lagged 90 days, entry lagged one session, regime tilt switched off.",
               SERIF, 9.5, SLATE, False, True)])
    half = (UW - 0.3) / 2
    yy = co(deck, s, ML, 4.24, half, "What the test does support",
            "The top decile beat the bottom by 9 points of CAGR and the index by 11, at a fraction of "
            "the drawdown: 2.3% against 12.6% and 5.6%. That gap is what we defend, because it follows "
            "from what the gates screen out.", "good", min_h=1.24, max_h=1.34)
    co(deck, s, ML + half + 0.3, 4.24, half, "What it does not support",
       "It is not a return edge. Against 2,000 random ten-name baskets the top decile sat at the 44th "
       "percentile, long-short Sharpe was about zero, and it trailed an equal-weighted universe by 2.8 "
       "points a year. Eight quarters is underpowered.", "warn", min_h=1.24, max_h=1.34)
    co(deck, s, ML, yy + 0.14, UW, "The line we will actually say",
       "A downside-protection tilt, but no statistically significant return selection. The analyst "
       "overlay is the real product, and it is only testable forward.", "human",
       min_h=0.58, max_h=0.64)
    deck.source(s, "Quant core only: the analyst layer is present-day judgment and cannot be rebuilt point-in-time, so it is excluded from every figure above. Red-teamed; an earlier version of this test was invalid and was corrected.")

    # ---------- what the score actually picks, named ----------
    s = deck.content(1, "The model", "The top and bottom of the book, named",
                     "What the score is actually saying about real holdings today")
    half = (UW - 0.3) / 2
    tcols = [("Stock", 0.28, "l"), ("Sector", 0.30, "l"), ("3Y", 0.12, "r"),
             ("1Y", 0.12, "r"), ("Call", 0.18, "c")]
    deck.txt(s, ML, 1.90, half, 0.24, [("TOP 5 BY BLENDED SCORE", SANS, 9, HOLD, True, False, 120)])
    deck.table(s, ML, 2.18, half, tcols, [
        [("b", "EMMVEE  78.8"), "Capital Goods", "77.9", "80.2", ("pill", "Hold", "Hold")],
        [("b", "SKFINDUS  76.8"), "Capital Goods", "79.8", "72.3", ("pill", "Hold", "Hold")],
        [("b", "SAATVIKGL  76.6"), "Capital Goods", "79.4", "72.4", ("pill", "Hold", "Hold")],
        [("b", "WELCORP  74.5"), "Capital Goods", "73.2", "76.5", ("pill", "Hold", "Hold")],
        [("b", "SUZLON  73.6"), "Capital Goods", "75.8", "70.3", ("pill", "Hold", "Hold")],
    ], rowh=0.34, fs=9, hfs=7.5, zebra=True)
    x2 = ML + half + 0.3
    deck.txt(s, x2, 1.90, half, 0.24, [("BOTTOM 5 BY BLENDED SCORE", SANS, 9, SELL, True, False, 120)])
    deck.table(s, x2, 2.18, half, tcols, [
        [("b", "RVNL  15.1"), "Construction", "14.2", "16.4", ("pill", "Sell", "Sell")],
        [("b", "VIPIND  17.9"), "Consumer Durables", "17.4", "18.7", ("pill", "Sell", "Sell")],
        [("b", "DBL  19.3"), "Construction", "19.6", "18.8", ("pill", "Sell", "Sell")],
        [("b", "NETWORK18  21.5"), "Media", "22.0", "20.7", ("pill", "Sell", "Sell")],
        [("b", "ICICIPRULI  22.0"), "Financial Services", "25.9", "16.1", ("pill", "Hold", "Hold")],
    ], rowh=0.34, fs=9, hfs=7.5, zebra=True)
    yb = co(deck, s, ML, 4.40, half, "The last row is the override, working",
            "ICICIPRULI scores 22 and the analyst still says Hold, on sector-aware reasoning about an "
            "insurer that the score cannot see. That rescue is written down against the name, and it is "
            "the only direction an analyst is allowed to move a call.", "good", min_h=1.20, max_h=1.40)
    co(deck, s, x2, 4.40, half, "And a concentration we should own",
       "All five top names are Capital Goods. That is the regime tilt and the trend pillars pulling in the "
       "same direction, and it is exactly why the score flags candidates for review rather than being used "
       "to build a portfolio.", "warn", min_h=1.20, max_h=1.40)
    deck.source(s, "Blended = 0.60 x three-year plus 0.40 x one-year, before the analyst forward adjustment. Scored universe of 751 names, full range 15.1 to 78.8. Internal page: these are live calls on real names.")

    # ================= SECTION 2 — workflow =================
    deck.section_divider(2, "The workflow", "What runs when, and who owns each step",
                         pages=["Cadence and ownership"])

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

    # ================= SECTION 3 — quality control =================
    deck.section_divider(3, "Quality control", "What stops a wrong page reaching a client",
                         pages=["The gate stack"])

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
    deck.section_divider(5, "Controls", "The compliance posture this product is built to",
                         pages=["Compliance posture"])

    s = deck.content(5, "Controls and the ask", "Compliance posture",
                     "Built for a non-discretionary mandate, and constrained accordingly")
    pcols = [("Control", 0.30, "l"), ("How it is enforced", 0.70, "l")]
    prows = [
        [("b", "No buy recommendations"), "The vocabulary is Sell, Trim or Hold. This is a review of holdings the client already owns, not a solicitation. The word is blocked by the client-copy scan."],
        [("b", "No target prices"), "No page carries a price objective or an implied return promise. Valuation is expressed as a judgment on what the multiple already assumes."],
        [("b", "Tax is flagged as an estimate"), "Tax characterisations are labelled indicative, with the client's own adviser named as the authority before dealing."],
        [("b", "Gaps are disclosed, not filled"), "Where cost basis, coverage or fund data is missing, the deck says so on the page rather than substituting an assumption."],
        [("b", "Every client copy is signed"), "Principal or CEO countersignature, with no standing exemption for a repeat client or a routine refresh."],
    ]
    ty = deck.table(s, ML, 1.92, UW, pcols, prows, rowh=0.52, fs=10, hfs=8, zebra=True)
    co(deck, s, ML, ty + 0.16, UW, "The standing rule behind all of it",
       "We do not fabricate. An estimate is labelled an estimate, a gap is shown as a gap, and a number we "
       "cannot source does not go on a client page. Every control above follows from that one commitment.",
       "human", min_h=0.78, max_h=0.86)

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
