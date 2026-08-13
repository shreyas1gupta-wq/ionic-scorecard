# -*- coding: utf-8 -*-
"""build_qfra2_pac_deck.py — QFRA 2.0 Product Approval Committee deck, rebuilt in the
firm's pr_template house style (2026-08-05).

Replaces the standalone repo's QFRA2_DECK_committee.pptx (28 slides, built by
Mf_qfra2/mr_x_framework/src/qfra2_deck_v4.py). Audience: PAC. INTERNAL, not client-facing,
so framework names and engine internals are used deliberately -- tellscan's client-copy
rules do not bind an internal committee paper.

EVERY NUMBER HERE SURVIVED THE RED-TEAM AUDIT in 03_RESEARCH_DESK/qfra2_pac_prep/
NUMBER_AUDIT.md. Five of the old deck's nine headline figures did not and are NOT carried
forward. The specific replacements, all sourced:
  * old "P(beat 3-5y) ~56%"        -> DROPPED. A hardcoded string on a page headed
                                      CLIENT-FACING, for a metric MODEL_SPEC.md Part D
                                      says is deferred and must not be promised.
  * old "~2.6/yr churn"            -> 3.9/yr (the same script's own chart data).
  * old "+0.9%/yr live"            -> +0.65%/yr, restricted to the 6 categories in scope
                                      (the +0.9% figure only holds if Focused is included,
                                      and Focused is out of scope in this very deck).
  * old "~40-60 funds eligible"    -> 99 Direct-plan funds, 5-9 per deployed category.
  * old Small "+2.2%/yr, +9pp"     -> shown as RAW-vs-HELD, because the deployed book did
                                      -1.34%/yr in Small.
  * old "AI/ML-assisted ranking"   -> DROPPED as false; see the parsimony page.

Principal's page-specific asks (2026-08-04), all applied:
  pg3  AI/ML claim              -> removed; replaced by an honest "no ML, and why" page.
  pg4  "client aligned"         -> reframed alpha-first. SEE THE ASSUMPTION NOTE BELOW.
  pg5  CALIBRE I and C pillars  -> rewritten (CALIBRE_PILLARS.md).
  pg8  QFRA-1 complementarity   -> new page + the 3Y-topper comparison he asked for.
  pg16 recommendation history    -> slot-stable, every H1/H2 shown (chart_qfra2_tenure.py).

*** ASSUMPTION, FLAGGED, NEEDS ONE WORD FROM THE PRINCIPAL ***
"pg 4 -> client aligned -> make it alpha focused". Physical slide 6 of the old deck is
"Four things rating houses don't do" and NO line on it says "client aligned", so the target
could not be identified from the deck text. Interpretation taken here: he wants that page's
framing to lead with ALPHA rather than with positioning-against-rating-houses. The page is
therefore rebuilt as "Where the alpha comes from" and leads with the measured edge. If he
meant a different line, only this one page changes.

UPDATE, 2026-08-06: added a "how we test our own engines" pair, a score-distribution page, and
one fund-side gap page. All sourced from the STOCK-scoring engine's 2026-08-05 stress-test run
(STOCK_SCORECARD_750/results/DECILE_ROLLING_20260805, REGIME_PSU_20260805;
chart_score_distribution.py) and labelled stock-score evidence throughout, never presented as
QFRA-2 findings: the two engines are different models on different asset classes. The added gap
page states, on the fund side, that QFRA-2 itself has not yet been regime-split tested the way
the stock score just was. No model, weight or threshold changed; page_limits, page_history and
every number that predates this update are unchanged.

UPDATE 2, 2026-08-06 (Principal: "the qfra deck is not correct remake changes improve recheck
previous main qfra deck i gave at start and what changes i told etc.") -- PRODUCT CONTENT
RESTORED. He is right. The rebuild above kept every honesty and correction page and lost most
of the product story: the committee was being asked to approve a model without being shown the
model's output. Eleven pages restored, each in the section where it belongs:

  page_exec_summary      front matter, after the side-by-side. KPI tiles, but on corrected
                         numbers: the raw edge and the held edge sit side by side in the tiles
                         rather than only the flattering one.
  page_evolution         01. QFRA 1.0 -> 2.0, WITHOUT the old table's "Method: Dynamic, AI/ML-
                         assisted ranking" and "ML rank" rows, which are false. The Method row
                         is restored corrected, not silently dropped, and a callout says so.
  page_vs_rating_houses  01. Competitive positioning, with a callout refusing to let it read
                         as a puff page.
  page_mid_sleeve        02. Why active mid is not used and what replaces it. Pipeline step 7
                         is the routing decision, so it belongs with how a rank is produced.
  page_recommendations   02. THE CURRENT FINAL-2 PER CATEGORY. The single worst omission of the
                         rebuild -- a product-approval deck with no product in it. Rendered
                         straight from QFRA2_current.csv, rank<=2, no editorialising.
  page_scorecard         02. One fund's output, as a client would see it, WITHOUT the old
                         "P(beat 3-5y) ~56%" chip: hardcoded in the old build script for a
                         metric MODEL_SPEC.md Part D defers and forbids client-facing.
  page_edge_chart        03. Edge by category, all six deployed categories.
  page_winrate_chart     03. Win-rate against a random pick, same six.
  page_live_proof        05. The Jan-2025 book, sixteen months on, at +0.65%/yr over the six in
                         scope -- not the old +0.9%, which only holds if Focused is counted and
                         Focused is out of scope in this very deck.
  page_churn            05. Low churn, at the realised 3.9/yr, not the old ~2.6/yr.
  page_rejected          05. What we tested and rejected. The integrity log.

Charts: the repo's six PNGs could not simply be reused. churn_by_category.png bakes "~2.6
changes/yr" into its pixels and live_alpha.png bakes "+0.9%/yr" -- both banned figures -- and
mid_momentum.png's win-rate labels collide with its tick labels. chart_qfra2_evidence.py
rebuilds four of them in house NAVY/GOLD from the same traced values, and the live-proof page
carries a per-category table instead of a chart. See that script's docstring.

NOTHING already correct was disturbed: the two-frameworks side-by-side still sits immediately
after the contents (his 2026-08-06 instruction), and the no-ML, AI-boundary, RAW-vs-HELD,
by-category, 3Y-topper, cadence, CALIBRE, SENTINEL, history, validation-pair, score-
distribution, limits, fund-regime-gap and ask pages are untouched.

Usage: python chart_qfra2_evidence.py && python build_qfra2_pac_deck.py
Output: 09_PRODUCT/reports/QFRA2_PRODUCT_APPROVAL_DECK.pptx
"""
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PRT = os.path.abspath(os.path.join(HERE, "..", "pr_template"))
sys.path.insert(0, PRT)

import slidekit as SK  # noqa: E402
from slidekit import (NAVY, INK, SLATE, GOLD, WHITE, HOLD, SELL, AMBER,
                      PANEL, HAIR, NT2, SERIF, SANS, ML, UW, RX)  # noqa: E402
from pptx.enum.text import PP_ALIGN  # noqa: E402

OUT = os.path.abspath(os.path.join(HERE, "..", "reports", "QFRA2_PRODUCT_APPROVAL_DECK.pptx"))
# Optional argv override. A PowerPoint COM process left over from a PDF conversion holds
# the canonical file open, and deck.save() then blocks indefinitely rather than erroring,
# so being able to write elsewhere keeps a rebuild verifiable while the lock persists.
if len(sys.argv) > 1:
    OUT = os.path.abspath(sys.argv[1])
CH_TENURE = os.path.join(PRT, "out", "qfra2_tenure.png")
CH_ANCHOR = os.path.join(PRT, "out", "anchor_pair_evidence.png")
# Stock-scorecard evidence (STOCK_SCORECARD_750), added 2026-08-06. Different model, different
# asset class; kept here only because it is the same pr_template/out/ chart directory.
CH_SCORE_DIST = os.path.join(PRT, "out", "score_distribution.png")
# Restored product-evidence charts, rebuilt in house style by chart_qfra2_evidence.py. The
# repo's originals are NOT used: two of them bake a banned number into their pixels.
CH_EDGE = os.path.join(PRT, "out", "qfra2_edge_by_category.png")
CH_WINRATE = os.path.join(PRT, "out", "qfra2_winrate.png")
CH_MIDMOM = os.path.join(PRT, "out", "qfra2_mid_momentum.png")
CH_CHURN = os.path.join(PRT, "out", "qfra2_churn.png")
AS_OF = "2026-05-27"          # QFRA2_current.csv asof
BUILT = "2026-08-06"


# The content area ends here; deck.source() is pinned at 6.66, so anything reaching past
# BOTTOM collides with it or runs off the slide. The first build of this deck produced 28
# geometry findings for exactly that reason, so the budget is now enforced at build time
# rather than discovered by a gate afterwards.
BOTTOM = 6.52
# 0.01in = 0.25mm, below any rendering significance; a hair over the floor is not a defect.
TOL = 0.01


def co(deck, s, x, y, w, title, body, kind="note", min_h=0.6, max_h=2.6):
    """Callout sized to its own text, and REFUSED if it would not fit above BOTTOM.

    Hardcoding a height is how every clip-risk finding on the NDPMS PAC deck's first build
    happened; silently letting a self-sized box run past the content area is how this deck's
    first build produced its own. Returns the y after the box.
    """
    h = deck.callout_h(w, body, min_h=min_h, max_h=max_h)
    if y + h > BOTTOM + TOL:
        raise AssertionError(
            f"callout '{title[:40]}' needs {h:.2f}in at y={y:.2f} and would end at "
            f"{y + h:.2f}, past the {BOTTOM} content floor by {y + h - BOTTOM:.2f}in. "
            f"Cut the body text or move it to its own page - do not shrink the box.")
    deck.callout(s, x, y, w, h, title, body, kind)
    return y + h


def fits(y, h, what=""):
    """Same budget check for tables, pictures and text blocks."""
    if y + h > BOTTOM + TOL:
        raise AssertionError(f"{what or 'block'} at y={y:.2f} height {h:.2f} ends at "
                             f"{y + h:.2f}, past the {BOTTOM} floor.")
    return y + h


# ===========================================================================
def cover(deck):
    s = deck.slide(bg=NAVY)
    deck.rect(s, 0, 0, 13.333, 7.5, fill=NAVY)
    deck.txt(s, ML, 2.05, 10.4, 0.5, [("QFRA 2.0", SANS, 13, GOLD, True)])
    deck.txt(s, ML, 2.55, 11.0, 1.5,
             [("Quantitative Fund Ranking Algorithm", SERIF, 40, WHITE, True)])
    deck.txt(s, ML, 4.15, 10.6, 0.40,
             [("Product Approval Committee", SANS, 15, WHITE, False)])
    deck.txt(s, ML, 4.62, 10.6, 0.40,
             [("Indian equity mutual funds  ·  HNI advisory  ·  Direct-plan basis  ·  "
               "price-return benchmarks", SANS, 11.5, NT2, False)])
    deck.rule(s, ML, 5.35, 4.2, color=GOLD, h=0.022)
    deck.txt(s, ML, 5.62, 10.6, 0.40,
             [(f"Recommendations as of {AS_OF}  ·  deck built {BUILT}  ·  "
               f"model frozen at v2.0", SANS, 10, NT2, False)])
    deck.txt(s, ML, 6.42, 10.6, 0.30,
             [("Internal committee paper. Not for client distribution.",
               SANS, 9, NT2, False)])
    return s


def contents(deck):
    s = deck.content(0, "", "CONTENTS", "What this deck covers")
    # Six rows is the ceiling: the loop steps 0.70 from 1.95 and the trailing note has to clear
    # deck.source() at 6.66. A seventh row does not fit, so the two front-matter pages -- the
    # side-by-side and the one-page summary -- share row 00 rather than each taking one.
    items = [
        ("00", "The two frameworks, and a one-page summary",
         "what each framework is  ·  how well each is evidenced  ·  the ask in brief"),
        ("01", "What it is, and what it is not",
         "the mandate  ·  v1 to v2  ·  no machine learning, and why  ·  where the alpha comes "
         "from  ·  versus the rating houses"),
        ("02", "How a rank is produced",
         "the pipeline  ·  CALIBRE  ·  SENTINEL  ·  the Mid sleeve  ·  the current final two  "
         "·  a sample scorecard"),
        ("03", "The evidence, honestly",
         "raw versus deployed  ·  by category  ·  the selection edge  ·  hit rates  ·  a "
         "3-year topper  ·  the cadence"),
        ("04", "The two frameworks",
         "why QFRA-1 is complementary  ·  where each one drives the call"),
        ("05", "Track record and the ask",
         "every review period since 2018  ·  live so far  ·  churn  ·  what we rejected  ·  "
         "how we validate our own models  ·  limits  ·  the decision sought"),
    ]
    y = 1.95
    for num, title, sub in items:
        deck.txt(s, ML, y, 0.8, 0.5, [(num, SERIF, 22, GOLD, True)])
        deck.txt(s, ML + 0.95, y + 0.02, 9.9, 0.34, [(title, SANS, 14, INK, True)])
        deck.txt(s, ML + 0.95, y + 0.40, 9.9, 0.34, [(sub, SANS, 10, SLATE, False)])
        y += 0.70
    # The "this deck corrects the last one" point deliberately does NOT live here. It is made
    # where it can be evidenced -- the raw-versus-held page and the ask -- rather than as a
    # claim on the contents page.
    deck.txt(s, ML, y + 0.10, UW, 0.30,
             [("Five of the nine headline figures in the previous committee pack did not "
               "survive an audit against the engine's own outputs. They are corrected "
               "here, not repeated.", SANS, 10.5, SLATE, False)])
    deck.source(s, "Audit trail: 03_RESEARCH_DESK/qfra2_pac_prep/NUMBER_AUDIT.md")
    return s


def page_two_frameworks(deck):
    """QFRA-1 versus QFRA-2, side by side, EARLY (Principal, 2026-08-06).

    Sits immediately after the contents because a committee otherwise reads seven slides about
    "the model" before discovering there are two of them. The complementarity discussion in
    section 4 answers WHY we run both; this answers WHAT they are, and it has to come first.
    Every row is a fact traceable to the two rerun skills or to a measured result in this deck.
    """
    s = deck.content(0, "", "THE TWO FRAMEWORKS", "What each one is, before anything else",
                     "The desk runs two fund frameworks on one calendar. They differ in horizon, "
                     "in what they may conclude, and in how well each is evidenced")
    cols = [("", 2.30, "l"), ("QFRA-1  short term", 4.30, "l"), ("QFRA-2  long term", 4.30, "l")]
    rows = [
        ("Question it answers", "Which funds are capturing the upside now",
         "Which two funds should beat the category index over 3 to 5 years"),
        ("Horizon", "6-month capture windows", "3 to 5 years, factor-adjusted"),
        ("Verdicts it can emit", "BUY / SELL / HOLD",
         "ACTIVE / INDEX CORE only. There is NO sell verdict"),
        ("Who may originate a sell", "This framework only", "Cannot. It may only VETO one"),
        ("Coverage", "6 categories, from the desk workbook",
         "8 categories, 99 Direct-plan funds after gates"),
        ("Universe depth", "All funds on the category sheet",
         "5 to 9 eligible funds in a deployed category"),
        ("Benchmark basis", "Price return", "Total return in its own docs"),
        ("Evidence", "906-formation replay: BUY leg strong, SELL leg near a coin flip",
         "Bootstrapped selection skill, but the held book realised far less"),
        ("Cadence", "April and October month end", "The same calendar, run together"),
    ]
    deck.table(s, ML, 1.96, UW, cols, rows, rowh=0.32, fs=9.5, hfs=8, zebra=True)
    co(deck, s, ML, 5.30, UW, "They are not independent, and that changes what agreement means",
       "QFRA-1 ranks on the 6-month capture ratio, which QFRA-2 already carries at a weight of "
       "0.30 plus a three-year down-capture term, so the capture family is 40% to 48% of the "
       "QFRA-2 score. When both agree, part of that is one signal agreeing with itself.", "warn")
    deck.source(s, "Sources: the qfra1-rerun and qfra2-rerun skills; overlap verified at "
                   "final_model.py:154. Benchmark basis: TRI is not obtainable on our network, so "
                   "every index we hold is price-return, measured 2026-08-06.")
    return s


def page_exec_summary(deck):
    """RESTORED. The old deck's slide 2, on numbers that survive the audit.

    The old tiles were +1.65% / "58% vs 40%" / ~2.6 a year / +0.9% a year: one safe, one
    right-number-wrong-basis, two contradicted. The fix is not to delete the page -- a
    committee is entitled to a one-page summary -- but to put the raw edge and the held edge
    in the tiles TOGETHER, so the gap the deck spends section 3 explaining is visible in the
    first thirty seconds rather than arriving as a reversal.
    """
    s = deck.content(0, "", "EXECUTIVE SUMMARY", "What is being asked, and on what evidence",
                     "One page. The two edge figures are both here on purpose: the second one "
                     "is what a client actually received")
    deck.kpi_strip(s, [
        ("+1.65%", "3Y edge, unconstrained rank", "over a random pick, pooled"),
        ("+0.09%", "3Y alpha, the book held", "after the churn rule"),
        ("3.9 / yr", "book changes, 8-year realised", "average hold near 3 years"),
        ("+0.65%/yr", "live since Jan-2025", "the 6 categories in scope"),
    ])
    rows = [
        ("What it is", "A ranking engine that publishes the top two funds in each category, "
                       "expected to beat the category index over three to five years. It has "
                       "no sell verdict, and it abstains where it cannot show an edge."),
        ("Where the edge is", "Largest in Large & Mid at +2.86%/yr and Flexi at +1.90%/yr over "
                              "a random pick of the same eligible field. In Small the level is "
                              "the market's, not ours. In Mid it is absent, which is why Mid "
                              "runs a momentum index."),
        ("The ask", "Approve deployment across the six categories in scope, on the corrected "
                    "numbers, with the model frozen at v2.0 and re-run every six months."),
    ]
    y = 2.92
    for k, v in rows:
        deck.txt(s, ML, y, 2.5, 0.4, [(k, SANS, 11, NAVY, True)])
        deck.txt(s, ML + 2.65, y, UW - 2.65, 0.66, [(v, SANS, 10.5, INK, False)])
        y += 0.70
    co(deck, s, ML, y + 0.04, UW, "Why both edge figures are on this page",
       "Selection skill is measured on the unconstrained ranking. Clients hold the churn-"
       "constrained one, and the churn discipline that makes the product attractive on tax "
       "absorbs most of the measured edge. Quoting only the first figure is how the previous "
       "pack read; section 3 does the arithmetic in full.", "warn")
    deck.source(s, "Edge and pooled figures: QFRA2_HANDOFF.md section 5. Held book: "
                   "QFRA2_recommendation_performance.md. Live: QFRA2_realized.csv, rank<=2, "
                   "six in-scope categories. Audit: qfra2_pac_prep/NUMBER_AUDIT.md.")
    return s


# --------------------------------------------------------------- section 1
def sec1(deck):
    deck.section_divider(1, "What it is, and what it is not",
                         "The mandate, the absence of machine learning, and where the "
                         "alpha actually comes from", pages=["5-10"])


def page_mandate(deck):
    s = deck.content(1, "What it is", "The mandate", "One job, stated narrowly")
    deck.kpi_strip(s, [
        ("8", "categories ranked"),
        ("99", "Direct-plan funds in the universe"),
        ("2", "funds recommended per category"),
        ("6", "categories deployed"),
    ])
    rows = [
        ("What it does", "Ranks the eligible funds in a category and publishes the top 2, "
                         "from a top-5 shortlist, expected to beat the category Total-Return "
                         "index over 3 to 5 years."),
        ("What it is not", "Not a market call, not a timing model, and not a sell engine. "
                           "It has no Sell verdict at all: its verdicts are Active and "
                           "Index core."),
        ("Who it is for", "HNI advisory on a Direct-plan basis, measured against Total-Return "
                          "benchmarks, reviewed twice a year."),
        ("Deployment scope", "Large as an index core, Large and Mid, Mid as a momentum "
                             "sleeve, Flexi, Multi, Small. Focused and Value are ranked but "
                             "not deployed."),
    ]
    y = 3.02
    for k, v in rows:
        deck.txt(s, ML, y, 2.5, 0.4, [(k, SANS, 11, NAVY, True)])
        deck.txt(s, ML + 2.65, y, UW - 2.65, 0.78, [(v, SANS, 10.5, INK, False)])
        y += 0.86
    deck.source(s, "Universe replicated from Mf_qfra2/data/verified_navs_*.csv, "
                   "2026-08-04. Verdicts from QFRA2_current.csv.")
    return s


def page_evolution(deck):
    """RESTORED. Why v2 exists at all -- the old deck's slide 5.

    Two of the old table's rows are deleted rather than reworded, because they were not
    imprecise, they were untrue: "Method: Dynamic, AI/ML-assisted ranking" and a Selection
    row reading "ML rank + discretionary overlay". There is no ML anywhere in the engine
    (AI_ML_AUDIT.md; the next page but one). The Method row is restored with what the method
    actually is, so a reader who remembers the old table can see what changed and why.
    """
    s = deck.content(1, "What it is", "QFRA 1.0 to QFRA 2.0",
                     "What changed, and why a second version was needed",
                     "v1 was a narrow, short-horizon, high-churn ranker. v2 is broad, "
                     "validated, low-churn and built for money that stays invested")
    cols = [("Dimension", 2.05, "l"), ("QFRA 1.0", 3.55, "l"), ("QFRA 2.0", 5.85, "l")]
    rows = [
        ("Signals", "Capture ratios only, a narrow base",
         "Factor alpha, appraisal ratio, information ratio, up and down capture, momentum, "
         "Calmar, quality beta"),
        ("Alpha horizon", "One year", "Three to five years, sized for money that compounds"),
        ("Method", "Rule-based, static scoring",
         "Still rule-based: percentile ranks within a category and date, weights fixed by "
         "hand, then validated out of sample"),
        ("Selection", "Direct rules",
         "A top-five shortlist, then a final two, with a discretionary gate that may only "
         "veto or trim"),
        ("Turnover", "Frequent changes, high churn",
         "Low churn: 3.9 book changes a year realised over eight years, tax-aware"),
        ("Investor fit", "Tactical, lump sum", "Long horizon, suitable for a staggered entry"),
        ("Risk control", "None",
         "SENTINEL loser screen, the CALIBRE scorecard, and out-of-sample validation"),
    ]
    deck.table(s, ML, 1.96, UW, cols, rows, rowh=0.42, fs=9, hfs=8, zebra=True)
    co(deck, s, ML, 5.31, UW, "Two rows this table used to carry, and no longer does",
       "The previous version called the method a dynamic, AI/ML-assisted ranking and the "
       "selection step an ML rank. Neither is true of the engine, so both were removed rather "
       "than softened. The very next page sets out what is actually there.", "warn")
    deck.source(s, "Signals and gates: final_model.py. Churn: the 8-year realised history. "
                   "Deleted claims: qfra2_pac_prep/AI_ML_AUDIT.md.")
    return s


def page_no_ml(deck):
    """Principal pg3: the old deck claimed AI/ML. It is false. This replaces it."""
    s = deck.content(1, "What it is", "No machine learning, and why that is the right answer",
                     "The previous pack claimed an AI/ML ranking. There is none, and adding "
                     "one would recreate a failure we already tested")
    y = 1.98
    y = co(deck, s, ML, y, UW, "What the earlier deck claimed, and what is actually there",
           "It called the method an \"AI/ML-assisted ranking\" and the selection an \"ML "
           "rank\". Neither is true: across all 137 engine files there is no scikit-learn, "
           "LightGBM, XGBoost, TensorFlow, PyTorch or Keras. The same build script also "
           "printed \"ML on the cross-section: too small, it memorises one era\", so the pack "
           "contradicted itself.", "warn")
    cols = [("Layer", 3.0, "l"), ("What it actually is", UW - 3.0, "l")]
    rows = [
        ("Signals", "Six to eight per-fund measures over a 756-day window: information "
                    "ratio, down-capture, Calmar, momentum, alpha stability, capture ratio."),
        ("Factor step", "One ordinary least-squares regression. The only estimated "
                        "coefficients anywhere in the engine, and they feed just 2 of the "
                        "ranked inputs."),
        ("Combination", "Cross-sectional percentile ranks blended with hand-set constants: "
                        "an equal-weight average, then 0.9 and 0.1, then 0.7 and 0.3."),
        ("Screens", "Fixed percentile and asset thresholds. Nothing is fitted."),
    ]
    deck.table(s, ML, y + 0.14, UW, cols, rows, rowh=0.46, fs=10, hfs=8, zebra=True)
    deck.source(s, "Audit: qfra2_pac_prep/AI_ML_AUDIT.md. Engine: final_model.py, "
                   "factors_live.py:223, features.py:38.")
    return s


def page_ai_boundary(deck):
    """The other half of the Principal's question: where AI IS used, and keep-or-add."""
    s = deck.content(1, "What it is", "Where we do use AI, and whether to add it here",
                     "The boundary matters: an analyst agent doing research is not the same "
                     "claim as a model that learns its weights")
    y = 1.98
    y = co(deck, s, ML, y, UW, "Where AI is actually used, and where it is not",
           "The stock scorecard runs one language-model research agent per stock, and that is "
           "real. It is judgment and research, not a fitted ranker. It is also entirely "
           "stock-side: checked in both directions, there is no path by which that research "
           "reaches this fund model, and no path by which this model reaches the stock "
           "agents. The fund engine consumes no AI output at all.", "ok")
    y = co(deck, s, ML, y + 0.14, UW, "Two things in the repository that look like AI and are not",
           "A legacy script does contain a real random-forest model. It sits outside the "
           "frozen engine, nothing imports it, and it hard-codes another machine's file "
           "paths. A second file named for an AI overlay detects manager changes from a "
           "hard-coded list, and its own comment says it is mocked to demonstrate the "
           "architecture. Neither is in the pipeline.", "warn")
    co(deck, s, ML, y + 0.14, UW, "Recommendation: keep the engine, drop the claim",
       "Fitting weights on 5 to 9 funds per category is how a model memorises one era, which "
       "is what the research already found and rejected. Parsimony is the defensible "
       "position: few orthogonal signals, no fitted weights, nothing to overfit. If the "
       "committee wants real machine learning later, the credible route is a pooled panel "
       "learner across fund-months to replace the hand-set blend constants. That is new "
       "validated work, not a relabelling of what already exists.", "ok")
    deck.source(s, "qfra2_pac_prep/AI_ML_AUDIT.md. Stock-side agent research: "
                   "STOCK_SCORECARD_750/FROZEN_METHODOLOGY.md.")
    return s


def page_alpha(deck):
    """Principal pg4: reframed to lead with alpha rather than with positioning."""
    s = deck.content(1, "What it is", "Where the alpha comes from",
                     "Four sources, each measured, and one of them is knowing when to stop")
    items = [
        ("1", "SELECTION, measured not described",
         "Factor-adjusted alpha and appraisal ratio, significance-gated. On the "
         "unconstrained ranking this is worth +0.48%/yr, with a 95% bootstrap interval of "
         "+0.06% to +1.05%."),
        ("2", "SCREENING OUT LOSERS",
         "SENTINEL flags closet indexing, a low-quality book and no measured skill. It "
         "lifts our own top-decile beat-the-index rate from 48.5% to 56.6%, the single "
         "largest validated lever in the model."),
        ("3", "ABSTAINING WHERE WE HAVE NO EDGE",
         "Large and Mid Cap are routed to an index core because active selection there is "
         "not distinguishable from a blind pick. Mid runs a momentum index instead, worth "
         "about +9%/yr over the plain mid-cap index."),
        ("4", "NOT TRADING IT AWAY",
         "The churn rule holds a fund unless a challenger clears a material margin, "
         "delivering 3.9 book changes a year and an average holding near three years. This "
         "protects long-term capital gains treatment."),
    ]
    y = 1.96
    for num, head, body in items:
        deck.txt(s, ML, y, 0.55, 0.42, [(num, SERIF, 19, GOLD, True)])
        deck.txt(s, ML + 0.62, y + 0.02, UW - 0.62, 0.3, [(head, SANS, 11.5, NAVY, True)])
        deck.txt(s, ML + 0.62, y + 0.34, UW - 0.62, 0.50, [(body, SANS, 10, INK, False)])
        y += 0.84
    co(deck, s, ML, y + 0.02, UW, "And the honest subtraction",
       "Source 4 pays for itself in tax and operations, but it also absorbs most of source 1. "
       "The deployed book's realized edge is far smaller than the ranking's, and that "
       "arithmetic is the next section.", "warn")
    deck.source(s, "Bootstrap and SENTINEL from QFRA2_evidence.csv. Churn from the 8-year "
                   "realised history. Momentum sleeve from qfra2_smartbeta.py.")
    return s


def page_vs_rating_houses(deck):
    """RESTORED. The old deck's slide 16 -- competitive positioning.

    Kept because it answers the first question a committee asks about any in-house model:
    why not just use a rating house. Given a callout that stops it reading as a puff page,
    because the honest margin is small and the deck says so four pages later.
    """
    s = deck.content(1, "What it is", "Why not simply use the rating houses",
                     "Seven differences, and the one that does not flatter us",
                     "The difference is method and disclosure. It is not a wide "
                     "performance margin, and this page does not claim one")
    cols = [("Dimension", 2.15, "l"), ("Rating houses, star-chasing", 3.95, "l"),
            ("QFRA 2.0", 5.35, "l")]
    rows = [
        ("Edge", "Qualitative, or last year's return",
         "Factor-adjusted alpha, gated on statistical significance"),
        ("Plan and basis", "Often Regular plan, price return",
         "Direct plan throughout, total-return benchmarks in the model's own documents"),
        ("Validation", "In sample, or none published",
         "Walk-forward out of sample, plus a year-block bootstrap"),
        ("Loser control", "None: every fund gets a rating",
         "SENTINEL lifts our own top-decile beat rate from 48.5% to 56.6%"),
        ("Abstention", "Rates every fund in every category",
         "Routes to an index core or a factor sleeve where we cannot show an edge"),
        ("Turnover and tax", "High, or simply not discussed",
         "3.9 book changes a year, and the rule that produces it is published"),
        ("Limits", "Rarely stated",
         "Stated: one era, a thin universe, and a held book well below the ranking"),
    ]
    deck.table(s, ML, 1.96, UW, cols, rows, rowh=0.42, fs=9, hfs=8, zebra=True)
    co(deck, s, ML, 5.31, UW, "The honest version of this comparison",
       "A rating house does not claim a factor-adjusted edge, so on that row there is nothing "
       "to beat. And our own held book earned +0.09%/yr at three years. What this page claims "
       "is a better method and fuller disclosure, not a wide margin.", "warn")
    deck.source(s, "SENTINEL lift: QFRA2_evidence.csv. Held book: "
                   "QFRA2_recommendation_performance.md. Rating-house column describes "
                   "published retail methodology in general, and names no competitor.")
    return s


# --------------------------------------------------------------- section 2
def sec2(deck):
    deck.section_divider(2, "How a rank is produced",
                         "The pipeline end to end, the quality scorecard, the negative "
                         "screen, and the churn rule", pages=["12-17"])


def page_pipeline(deck):
    s = deck.content(2, "How it works", "The pipeline, step by step",
                     "Point-in-time throughout. Every weight below is a fixed constant")
    cols = [("", 0.5, "c"), ("Step", 2.5, "l"), ("What happens", UW - 3.0, "l")]
    rows = [
        ("0", "Data", "Direct-Growth NAVs and a price-to-total-return benchmark, strictly "
                      "point-in-time."),
        ("1", "Eligibility", "At least 3 years of returns as a hard gate, plus an asset "
                             "floor, cost and true-to-label checks. Leaves 5 to 9 funds in a "
                             "deployed category."),
        ("2", "Factor model", "Regress on six factors for alpha, its t-statistic, "
                              "R-squared, quality beta and appraisal."),
        ("3", "Signals", "Information ratio, down-capture, Calmar, momentum, appraisal, "
                         "quality beta, alpha stability, 6-month capture."),
        ("4", "Rank", "Percentile-rank each signal within the category and date."),
        ("5", "Score", "Average the ranks, then 0.9 of that plus 0.1 of alpha stability."),
        ("6", "Capture blend", "0.7 of the score plus 0.3 of the 6-month capture ratio."),
        ("7", "Routing", "Active, or an index core for Large and Mid, or the Mid momentum "
                         "sleeve."),
        ("8", "SENTINEL", "Subtract one point per loser trait, then take the top 5."),
        ("9", "CALIBRE", "Quality scorecard and a discretionary gate that may only veto or "
                         "trim, never flatter."),
        ("10", "Final two", "Rank, take two, then apply the churn rule against the book "
                            "already held."),
    ]
    deck.table(s, ML, 1.92, UW, cols, rows, rowh=0.375, fs=9.5, hfs=8, zebra=True)
    deck.source(s, "Mf_qfra2/mr_x_framework/src/final_model.py. Model frozen at v2.0; no "
                   "weight on this page is fitted.")
    return s


def page_calibre(deck):
    """Principal pg5: Integrity did not mean integrity; Conviction was jargon."""
    s = deck.content(2, "How it works", "CALIBRE, the seven pillars of a rank",
                     "Rewritten this review so that every pillar says something we can "
                     "actually evidence")
    cols = [("", 0.42, "c"), ("Pillar", 2.05, "l"), ("What it means", UW - 5.1, "l"), ("Evidence", 2.63, "c")]
    rows = [
        ("C", "Conviction", "Top-of-category funds earn our biggest calls, while new ones "
                            "start smaller.", "Computed"),
        ("A", "Alpha", "Factor alpha and appraisal ratio, gated on genuine activeness.",
         "Computed"),
        ("L", "Leadership", "Manager tenure, key-person exit risk, AMC governance, true to "
                            "mandate.", "Analyst"),
        ("I", "Integrity", "Fair fees versus category, with nothing hidden from the "
                           "investor.", "Computed"),
        ("B", "Benchmark", "Win rate and up and down capture versus the total-return index.",
         "Computed"),
        ("R", "Resilience", "Down-capture, drawdown, alpha stability, concentration, "
                            "holdings quality.", "Mixed"),
        ("E", "Edge", "A validated edge, cost-efficient and clean of red flags.", "Computed"),
    ]
    # 7 pillar rows + a 0.33in header. At rowh 0.42 the table reached 5.19 and the callout
    # below it was starting at 5.02, i.e. on top of the last row.
    deck.table(s, ML, 1.92, UW, cols, rows, rowh=0.37, fs=10, hfs=8, zebra=True)
    y = 4.92
    y = co(deck, s, ML, y, UW, "Two pillars were wrong and are now fixed",
           "Integrity used to read as Active Share, concentration, price-earnings discipline "
           "and return-on-capital quality. That is portfolio construction, not integrity, and "
           "two of the four were never computed: there is no return-on-capital formula in the "
           "engine, and the price-earnings item is a NAV-trend proxy that disclaims itself. "
           "Conviction used to read \"within-category rank, clamped to track-record tier\", "
           "which is accurate and unreadable.", "warn")
    deck.source(s, "qfra2_pac_prep/CALIBRE_PILLARS.md. Analyst-judgment pillars are labelled "
                   "as such and applied one-directionally.")
    return s


def page_sentinel(deck):
    s = deck.content(2, "How it works", "SENTINEL and the churn rule",
                     "The negative screen, and the discipline that decides when not to act")
    y = 1.96
    y = co(deck, s, ML, y, UW, "SENTINEL: screen out losers rather than only rank winners",
           "Per fund, relative to its own category, raise one flag for each proven decay "
           "trait and subtract them from the blended score. R-squared in the top quartile "
           "means closet indexing. Quality beta in the bottom quartile means a junk book. "
           "Appraisal in the bottom quartile means no skill per unit of risk. It lifts our "
           "own top-decile beat-the-index rate from 48.5% to 56.6%. Only 3 of 12 candidate "
           "traits survived out of sample. It is deliberately switched off for Mid and "
           "Value, which mean-revert.", "ok")
    y = co(deck, s, ML, y + 0.16, UW, "The churn rule, and what it costs",
           "An incumbent is replaced only if a challenger beats it by a material margin in "
           "rank and the incumbent has fallen out of the category's top quartile, with at "
           "most one swap per category per review. Realised over eight years: 3.9 book "
           "changes a year, average holding near three years. The earlier pack said 2.6 a "
           "year; that figure is not supported by any output, including the chart data in "
           "the script that printed it.", "warn")
    co(deck, s, ML, y + 0.12, UW, "One consequence the committee should hold on to",
       "SENTINEL is a shortlist screen: it decides which candidates reach the top five. It is "
       "not a verdict on a fund a client owns, and our pipeline was briefly wired as though "
       "it were. Fixed, and covered in section 4.", "note")
    deck.source(s, "SENTINEL lift from QFRA2_evidence.csv. Churn from qfra2_charts_ceo.py "
                   "chart data and the realised history.")
    return s


def page_mid_sleeve(deck):
    """RESTORED. The old deck's slide 19 -- why active mid is not used, and what replaces it.

    Placed in section 2 rather than with the recommendations, because it IS the pipeline: step
    7 is the routing decision, and Mid is the one category where routing overrides the rank.
    """
    s = deck.content(2, "How it works", "The Mid Cap sleeve, and why it is not an active fund",
                     "The one category where the routing step overrides the ranking",
                     "The sleeve cleared the same out-of-sample bar that every model retune "
                     "failed, which is what separates an enhancement from a rescue")
    deck.pic(s, CH_MIDMOM, ML, 1.90, UW, 2.05)
    y = 4.03
    y = co(deck, s, ML, y, UW, "Why not an active mid-cap fund",
           "Mid-cap active selection is indistinguishable from chance over the eight-year "
           "replay: the model's picks returned -2.55%/yr against a random pick's -2.61%. The "
           "deployed mid book was the worst of the eight categories at -3.16%/yr. There is no "
           "stock-picking edge here to sell.", "warn")
    co(deck, s, ML, y + 0.08, UW, "The structure, and what can go wrong with it",
       "The momentum index carries 50 to 60% of the sleeve and one active fund the rest. "
       "Momentum can crash: worst drawdown about -72%, no better than the index it beats. "
       "Pre-2022 history is backfilled, and a real vehicle costs 0.3 to 0.5% a year plus "
       "tracking error.", "note")
    deck.source(s, "Premium and win rates: QFRA2_HANDOFF.md section 4; pre-2018 split from "
                   "qfra2_charts_ceo.py. Active mid edge: HANDOFF section 5. Held book: "
                   "QFRA2_recommendation_performance.md. Sleeve spec: QFRA2_MID_SLEEVE.md.")
    return s


def page_recommendations(deck):
    """RESTORED, and the most important restoration in this pass.

    The rebuild asked a committee to approve a ranking engine without ever showing it a rank.
    Every cell below is a verbatim rendering of QFRA2_current.csv, rank<=2, asof 2026-05-27:
    fund, qfra_score, merit_grade (labelled CALIBRE per the pending rename), sentinel,
    conviction. Nothing is re-scored, re-ordered or prettified here.

    Two things a reader will want to check, both deliberate:
      * Large Cap and Mid Cap carry grade C and "Low / index-lean" conviction because the CSV
        says so -- both are routed to an index core, and the grade follows the routing.
      * QFRA2_HANDOFF.md section 4 prints Quant Mid Cap as 100/A. The CSV says 100/C. The CSV
        is the engine's output and wins; the handoff table is wrong on that cell.
    """
    s = deck.content(2, "How it works", "The current final two, per category",
                     "What the engine actually publishes, as of the last run",
                     "The output the committee is being asked to approve, straight from the "
                     "engine's recommendation file")
    cols = [("Category", 1.75, "l"), ("Routing", 1.45, "l"), ("Final two", 3.85, "l"),
            ("QFRA", 0.85, "c"), ("CALIBRE", 0.90, "c"), ("SENTINEL", 1.35, "c"),
            ("Conviction", 1.25, "c")]
    rows = [
        ("Large Cap", "index core", "HSBC Large Cap  ·  Invesco India Largecap",
         "100 · 88", "C · C", "clear · clear", "Low, index-lean"),
        ("Large & Mid Cap", "active", "ICICI Pru Large & Mid  ·  Franklin India Equity Adv",
         "100 · 80", "A · A", "clear · flagged (1)", "High"),
        ("Mid Cap", "momentum sleeve", "Quant Mid Cap  ·  Aditya Birla SL Midcap",
         "100 · 88", "C · C", "clear · clear", "Low, index-lean"),
        ("Flexi Cap", "active", "Kotak Flexicap  ·  HDFC Flexi Cap",
         "100 · 83", "A · A", "clear · clear", "High"),
        ("Multi Cap", "active", "Invesco India Multicap  ·  ICICI Pru Multicap",
         "100 · 80", "A · A", "clear · clear", "High"),
        ("Small Cap", "active", "Aditya Birla SL Small Cap  ·  Sundaram Small Cap",
         "100 · 83", "A · A", "clear · clear", "High"),
    ]
    deck.table(s, ML, 1.96, UW, cols, rows, rowh=0.46, fs=9, hfs=7.5, zebra=True)
    co(deck, s, ML, 5.05, UW, "Three things to read off this table before approving it",
       "In deployment the Mid slot-1 fund is replaced by the BSE Midcap 150 Momentum 30 index, "
       "for the reason on the previous page; the ranked fund stays as the active half. A score "
       "is a rank within its own category, so Large Cap's 88 and Flexi's 83 are not comparable "
       "quantities. And Focused and Value are ranked by the engine but are not in the ask.",
       "note")
    deck.source(s, "Verbatim from mr_x_framework/outputs/recommendations/QFRA2_current.csv, "
                   f"rank<=2, asof {AS_OF}. Column merit_grade is shown as CALIBRE, the "
                   "pending rename. Out-of-scope ranks: Focused (360 ONE, HSBC), Value/Contra "
                   "(two closed Sundaram series with no continuous NAV).")
    return s


def page_scorecard(deck):
    """RESTORED, minus the one chip that should never have been on it.

    The old slide 20 was headed CLIENT-FACING and carried "P(beat 3-5y)  ~56%" -- a literal
    hardcoded string at qfra2_deck_v4.py:315 for a quantity the engine does not compute.
    MODEL_SPEC.md Part D defers the calibrated probability as in-sample-only and says in terms
    not to promise it client-facing. It is gone, not re-estimated, and the callout says why:
    a committee should see that the discipline bit on the one page where it was most tempting
    to fudge.
    """
    s = deck.content(2, "How it works", "What one fund's output looks like",
                     "Aditya Birla SL Small Cap Fund, Direct Growth  ·  Small Cap  ·  active",
                     "The client-facing scorecard the engine produces per fund. Four fields, "
                     "each computed, and no forecast")
    deck.kpi_strip(s, [
        ("100 / 100", "QFRA score, within category"),
        ("A", "CALIBRE grade"),
        ("clear", "SENTINEL, no loser flags"),
        ("0.84", "down-capture vs category"),
    ])
    rows = [
        ("Drivers", "Top-quartile factor alpha and appraisal ratio, a favourable six-month "
                    "capture ratio, no SENTINEL flag, and the highest absolute alpha of the "
                    "eight categories."),
        ("What would change our mind", "A SENTINEL flag; falling out of the category's top "
                                       "quartile while a challenger clears the churn margin; "
                                       "or a hard red flag such as a manager exit or a "
                                       "capacity breach."),
        ("Live", "Recommended January 2025. Realised +7.3%/yr alpha to 2026-05-27, the best of "
                 "the twelve in-scope picks."),
    ]
    y = 2.86
    for k, v in rows:
        deck.txt(s, ML, y, 2.9, 0.4, [(k, SANS, 11, NAVY, True)])
        deck.txt(s, ML + 3.05, y, UW - 3.05, 0.62, [(v, SANS, 10.5, INK, False)])
        y += 0.68
    co(deck, s, ML, y + 0.06, UW, "What this page used to claim, and does not",
       "The previous version carried a chip reading P(beat 3-5y) about 56%. The engine does not "
       "compute it: the figure was a hardcoded string, and the model's own specification defers "
       "the calibrated probability as in-sample only and says not to promise it client-facing. "
       "It is removed rather than re-estimated.", "warn")
    deck.source(s, "Fields verbatim from QFRA2_current.csv for this fund. Realised alpha from "
                   "QFRA2_realized.csv. Deferred probability: MODEL_SPEC.md Part D, steps 9 "
                   "and 11; finding 1 in qfra2_pac_prep/NUMBER_AUDIT.md.")
    return s


# --------------------------------------------------------------- section 3
def sec3(deck):
    deck.section_divider(3, "The evidence, honestly",
                         "What the ranking earns, what the deployed book earns, and how "
                         "both compare with the obvious alternative", pages=["19-24"])


def page_raw_vs_held(deck):
    s = deck.content(3, "The evidence", "The number we have been quoting is the wrong book",
                     "Selection skill is measured on the unconstrained ranking. Clients hold "
                     "the churn-constrained one")
    cols = [("Book", 3.5, "l"), ("1Y median alpha", 1.85, "r"), ("3Y median alpha", 1.85, "r"),
            ("3Y win rate", 1.6, "r"), ("5Y median alpha", 1.85, "r"), ("Changes / yr", 1.3, "r")]
    rows = [
        ("HELD: deployed, churn-constrained", "-0.09%", "+0.09%", "51.0%", "+0.20%", "3.9"),
        ("RAW: top 2, no churn rule", "+1.62%", "+0.56%", "56.7%", "+0.85%", "9.8"),
        ("Benchmark, total return", "0.00%", "0.00%", "n/a", "0.00%", "0"),
    ]
    deck.table(s, ML, 1.94, UW, cols, rows, rowh=0.46, fs=10, hfs=8, zebra=True)
    y = 3.62
    y = co(deck, s, ML, y, UW, "What this means, plainly",
           "The marketed +0.48%/yr is a selection-skill measure consistent with the raw row. "
           "The book a client actually holds returned +0.09%/yr at three years, with a win "
           "rate of 51%. The churn discipline that makes the product attractive on tax and "
           "operations absorbs almost the whole measured edge. The engine's own performance "
           "file says so: the low-churn book gives up roughly half a point a year at three "
           "to five years in exchange for about 60% less turnover.", "warn")
    deck.source(s, "QFRA2_recommendation_performance.md, 2018-H1 to 2024-H2, active "
                   "categories pooled.")
    return s


def page_by_category(deck):
    """Split out of page_raw_vs_held: a 6-row table stacked under a table plus a callout ran
    clean off the bottom of the slide."""
    s = deck.content(3, "The evidence", "The same book, category by category",
                     "Where the deployed book actually delivered, and where it did not")
    cols = [("Deployed category", 3.4, "l"), ("HELD 3Y median alpha", 2.4, "r"),
            ("Read", UW - 5.8, "l")]
    rows = [
        ("Flexi Cap", "+2.16%", "The only category where the realised book beat the theory."),
        ("Large Cap", "-0.25%", "Index core, as designed."),
        ("Large & Mid Cap", "-0.38%", "Best theoretical edge, worst delivery gap."),
        ("Small Cap", "-1.34%", "A rising tide, not our selection."),
        ("Multi Cap", "-2.35%", "Worst edge of the six; a blind pick wins."),
        ("Mid Cap", "-3.16%", "Why Mid is routed to a momentum index."),
    ]
    deck.table(s, ML, 1.94, UW, cols, rows, rowh=0.42, fs=10, hfs=8, zebra=True)
    # One callout only. A 6-row table plus two callouts does not fit, and the sampling caveat
    # already has a home on the limits page.
    co(deck, s, ML, 4.88, UW, "One of these rows should decide something",
       "Held-book alpha is negative in five of the eight ranked categories. It is positive in "
       "Flexi, and in Focused and Value, which this deck excludes from deployment. That "
       "exclusion was decided on edge over a blind pick rather than on realised alpha, and the "
       "two lenses disagree here.", "warn")
    deck.source(s, "QFRA2_recommendation_performance.md, per-category HELD book, 2018-H1 to "
                   "2024-H2.")
    return s


def page_edge_chart(deck):
    """RESTORED. The old deck's hero chart, slide 12, redrawn.

    Deliberately placed AFTER raw-versus-held and by-category, not before: this is the
    unconstrained ranking, and a committee that meets it first will read it as the product.
    Two changes from the original chart. All six deployed categories are drawn, including Mid,
    which the original omitted and which is the very category the momentum routing exists to
    fix; and the caption states the basis instead of leaving it to be inferred.
    """
    s = deck.content(3, "The evidence", "Where the selection edge is, by category",
                     "The unconstrained ranking, against a random pick of the same field")
    deck.pic(s, CH_EDGE, ML, 1.90, UW, 2.65)
    co(deck, s, ML, 4.63, UW, "Read the shape, not the pooled number",
       "The edge is concentrated: Large & Mid at +2.86%/yr and Flexi at +1.90%/yr do almost all "
       "the work, and in those two a random pick actually loses to the index. Small is +0.17%, "
       "Multi is -0.10% and Mid is +0.06% -- three of the six deployed categories where the "
       "ranking adds nothing measurable at three years. This is the unconstrained ranking; the "
       "book a client held earned a fraction of it, two pages back.", "note")
    deck.source(s, "QFRA2_HANDOFF.md section 5, the qfra2_vs_random.py panel. Total-return "
                   "benchmarks here use the model's documented dividend add-back, which is "
                   "modelled rather than vendor-official. Chart: chart_qfra2_evidence.py.")
    return s


def page_winrate_chart(deck):
    """RESTORED. The old deck's slide 13 -- the consistency story, on the honest footing.

    The old slide made Small the hero: "absolute alpha is highest here (+2.2%/yr)" with a
    "+9pp win-rate". Both figures are real on this panel and both are RAW. The deployed Small
    book returned -1.34%/yr, which the RAW-versus-HELD and by-category pages already state, so
    this page shows the win-rate panel and points at that contradiction rather than hiding
    behind it.
    """
    s = deck.content(3, "The evidence", "How often the pick beat the index",
                     "The same unconstrained panel, measured as a hit rate rather than a median")
    deck.pic(s, CH_WINRATE, ML, 1.90, UW, 2.65)
    co(deck, s, ML, 4.63, UW, "Where a hit rate says something a median does not",
       "In Large & Mid the ranking lifts the hit rate 36 points, from 26% to 62%. In Small it "
       "lifts it 9 points, but off a 64% base: the category beat its index most of the time "
       "whoever picked. In Mid the ranking is 2 points BEHIND a random pick. And a lifted hit "
       "rate on this panel did not carry into the deployed book: Small's held book returned "
       "-1.34%/yr at three years while winning half its windows.", "warn")
    deck.source(s, "QFRA2_HANDOFF.md section 5, win% model versus random at 3Y, same panel as "
                   "the previous page. Held-book figures: "
                   "QFRA2_recommendation_performance.md. Chart: chart_qfra2_evidence.py.")
    return s


def page_topper(deck):
    """Principal pg8, second half: versus buying the 3-year topper."""
    s = deck.content(3, "The evidence", "Against the obvious alternative",
                     "Why not simply buy the funds with the best three-year alpha")
    cols = [("Strategy", 3.3, "l"), ("3Y median alpha", 1.9, "r"), ("3Y win rate", 1.6, "r"),
            ("5Y median alpha", 1.9, "r"), ("Turnover / yr", 1.7, "r")]
    rows = [
        ("QFRA 2.0 final two", "+0.48%", "56.4%", "+0.58%", "3.9 deployed"),
        ("Best two by 3-year alpha", "+0.37%", "53.4%", "+0.90%", "7.8"),
        ("Best three by 3-year alpha", "+0.31%", "53.2%", "+0.27%", "10.8"),
        ("Blind pick", "-0.76%", "42.8%", "-0.69%", "n/a"),
    ]
    deck.table(s, ML, 1.94, UW, cols, rows, rowh=0.40, fs=10, hfs=8, zebra=True)
    y = 3.96
    y = co(deck, s, ML, y, UW, "The answer, with its exception stated",
           "The model wins 6 of the 8 pooled cells, and the topper still beats a blind pick, "
           "so it is a real signal rather than a straw man. Its only wins are the five-year "
           "cells, by a thin margin that reverses without factor adjustment. Small Cap is the "
           "genuine exception: there the topper beats us outright.", "ok")
    co(deck, s, ML, y + 0.12, UW, "And one belief this test corrected",
       "We expected the topper to churn far harder. It does not: at 7.8 changes a year it is "
       "no worse than our own unconstrained ranking at 11.1. Our low turnover comes from the "
       "churn rule, not from a steadier signal, and anyone could bolt that rule onto a topper "
       "strategy.", "warn")
    deck.source(s, "qfra2_pac_prep/3Y_TOPPER_BENCHMARK.md. Built on the same panel and the "
                   "same pooling convention as the published model-versus-random table.")
    return s


def page_cadence(deck):
    s = deck.content(3, "The evidence", "When the model runs, and why it matters",
                     "The review anchor is worth about 8 points of hit rate, so we tested "
                     "all six")
    deck.pic(s, CH_ANCHOR, ML, 1.86, UW, 2.55)
    co(deck, s, ML, 4.53, UW, "April and October, on the month end",
       "All six possible six-month pairs were replayed through the short-term framework's "
       "live decision logic at every month end from January 2012 to July 2024, across all six "
       "category sheets: 906 formations. April and October leads on the measure specified "
       "before the study ran, and ties with June and December on the 66% hit rate while the "
       "other four sit at 55% to 58%. Month end matters as much as the pair: a first-of-April "
       "anchor closes its window on about 31 March, so it is the March window renamed, and it "
       "scores a 53% hit rate against 66%. End-April reads prices that have digested the "
       "March-quarter and full-year results.", "ok")
    deck.source(s, "04_RND_LAB/STOCK_SCORECARD_750/results/anchor_pair_study/. Presented "
                   "measure is the 10% trimmed mean, specified in the original brief.")
    return s


# --------------------------------------------------------------- section 4
def sec4(deck):
    deck.section_divider(4, "The two frameworks",
                         "Why a second, shorter-horizon framework earns its place, and "
                         "where each one drives the call", pages=["26-28"])


def page_complementarity(deck):
    """Principal pg8, first half: QFRA-1 complementarity in mid, small, multi."""
    s = deck.content(4, "Two frameworks", "Why we run a second framework",
                     "Different horizons, one shared signal, and an honest statement of the "
                     "overlap")
    cols = [("Category", 2.3, "l"), ("Core", 2.5, "l"), ("Driven by", 1.85, "l"), ("Why", UW - 6.65, "l")]
    rows = [
        ("Large Cap", "Plain index", "QFRA-2", "Active selection is not distinguishable "
                                               "from a blind pick."),
        ("Large & Mid Cap", "Active", "QFRA-2", "Best theoretical edge of any category, "
                                                "worst delivery gap."),
        ("Mid Cap", "Factor momentum", "QFRA-2", "Active edge near zero and the worst "
                                                 "realised book of the eight."),
        ("Flexi Cap", "Active", "Both agree", "The one category where realised beat "
                                              "theoretical."),
        ("Multi Cap", "Plain index, provisional", "QFRA-2", "Worst edge of the six; no "
                                                            "evidenced factor substitute yet."),
        ("Small Cap", "Index core plus a tactical satellite", "Both, different jobs",
         "The level is the market's; the short signal is ours."),
    ]
    deck.table(s, ML, 1.92, UW, cols, rows, rowh=0.42, fs=9.5, hfs=8, zebra=True)
    co(deck, s, ML, 4.82, UW, "State the overlap before anyone finds it",
       "The short-term framework ranks funds on their six-month total capture ratio. QFRA-2 "
       "already carries that same quantity at a weight of 0.30, plus a three-year "
       "down-capture term, so the capture family is 40% to 48% of the QFRA-2 score. When the "
       "two agree, part of that is one signal agreeing with itself. What the short-term "
       "framework genuinely adds is recency and its own replayed backtest.", "warn")
    deck.source(s, "qfra2_pac_prep/FRAMEWORK_COMPLEMENTARITY.md; overlap verified at "
                   "final_model.py:154.")
    return s


def page_smallcap(deck):
    """The Principal's small-cap claim, examined. Half right, and the half matters."""
    s = deck.content(4, "Two frameworks", "Small Cap, stated precisely",
                     "The claim was that we have a lot of alpha in small caps. Half of that "
                     "is true, and the half that is not changes how we should run it")
    deck.kpi_strip(s, [
        ("92%", "of small-cap alpha a blind pick also gets"),
        ("-1.34%", "deployed book 3Y alpha in Small"),
        ("+3.49%", "short-term buy leg median excess"),
        ("72%", "short-term buy leg hit rate"),
    ])
    y = 2.88
    y = co(deck, s, ML, y, UW, "The level is the market's, not ours",
           "Small Cap has the highest absolute alpha of any category, +2.20% a year, but a "
           "blind pick captures +2.03% of it. The incremental edge is +0.17% and it did not "
           "survive into the deployed book, which returned -1.34%.", "warn")
    y = co(deck, s, ML, y + 0.10, UW, "But the short-horizon signal is real, and it is ours",
           "The short-term framework's small-cap buy leg is the strongest single signal in the "
           "firm: +3.49% median forward excess at a 72% hit rate, across 906 formations. That "
           "is six-month capture persistence, not five-year stock picking.", "ok")
    co(deck, s, ML, y + 0.10, UW, "So run it as what it is",
       "An index core for the beta, plus a separately sized and separately clocked tactical "
       "satellite. What we should not do is badge that satellite as our small-cap alpha.",
       "note")
    deck.source(s, "Random-baseline test from the model-versus-random panel; buy-leg figures "
                   "from the anchor-pair study extension.")
    return s


def page_sell_rule(deck):
    s = deck.content(4, "Two frameworks", "Who is allowed to say sell",
                     "A defect found this review, and the rule that replaced it")
    y = 1.96
    y = co(deck, s, ML, y, UW, "The defect",
           "QFRA 2.0 has no Sell verdict, yet our client pipeline derived one from it by "
           "treating a SENTINEL flag or a below-40 score as an exit signal. Both legs were "
           "wrong, and in one live case the rule called for selling a fund the same engine "
           "ranked second in its category with the top grade.", "warn")
    cols = [("Framework", 3.0, "l"), ("Role now", UW - 3.0, "l")]
    rows = [
        ("Short-term (QFRA-1)", "ORIGINATES the sell. It is the only framework with a sell "
                                "verdict and the only one with a replayed backtest."),
        ("QFRA 2.0", "VETOES only. A top-two grade blocks the sell. It can never originate "
                     "one."),
        ("Disagreement", "Surfaced as a contradiction for the fund manager's pack, never "
                         "resolved silently to hold."),
    ]
    deck.table(s, ML, y + 0.12, UW, cols, rows, rowh=0.46, fs=10, hfs=8, zebra=True)
    co(deck, s, ML, y + 1.93, UW, "And the limit on the leg that now originates",
       "On the same 906 formations the buy leg is strong, at +2.59% median excess and a 66% "
       "hit rate. The sell leg is not: 49% hit, below 50% in all six anchor pairs. A sell must "
       "stand on the analyst's reason, with capture as support, not on the backtest.", "warn")
    deck.source(s, "Implemented at 09_PRODUCT/scripts/fund_ctx_adapter.py. Sell-leg "
                   "measurement in the anchor-pair study extension.")
    return s


# --------------------------------------------------------------- section 5
def sec5(deck):
    deck.section_divider(5, "Track record and the ask",
                         "Every review period since 2018, the limits we accept, and the "
                         "decision sought", pages=["30-39"])


def page_history(deck):
    """Principal pg16: slot-stable, and every H1/H2 shown."""
    s = deck.content(5, "Track record", "Every review period since 2018",
                     "Rebuilt this review so a retained fund keeps its slot and no period "
                     "is hidden")
    deck.pic(s, CH_TENURE, ML, 1.82, UW, 3.16)
    y = 5.10
    co(deck, s, ML, y, UW, "What was wrong with the previous version",
       "It printed only the 43 periods in which something changed, hiding 93 of 136 rows, and "
       "it let a retained fund move between slots when the ranking reordered. JM Large Cap was "
       "held without interruption from 2020 to 2024 and appeared in both. Slot changes for "
       "retained funds are now zero, and all 17 periods are shown.", "ok")
    deck.source(s, "Rebuilt from QFRA2_recommendation_history.csv, which was complete all "
                   "along. Script: 09_PRODUCT/scripts/qfra2_history_rebuild.py.")
    return s


def page_live_proof(deck):
    """RESTORED. The old deck's slide 14, recomputed and given a table instead of a chart.

    The old KPI was "+0.9%/yr live realized alpha since Jan-2025". That number is the mean over
    all EIGHT tracked categories, including Focused -- a category this deck explicitly excludes
    from the ask. Over the six in scope the figure is +0.65%/yr mean, +0.70% median, n=12,
    reproduced from QFRA2_realized.csv (NUMBER_AUDIT.md finding 6). The repo's live_alpha.png
    bakes the +0.9% into its pixels, so it is not reused; the per-category table is better
    evidence anyway, because the dispersion is the story.
    """
    s = deck.content(5, "Track record", "The January-2025 book, sixteen months on",
                     "Live, not backtested -- and far too short to settle anything",
                     "Realised annualised alpha of the twelve in-scope picks, Direct-plan NAVs "
                     "against the category index")
    deck.kpi_strip(s, [
        ("+0.65%/yr", "mean realised alpha", "12 picks, 6 categories in scope"),
        ("+0.70%/yr", "median realised alpha", "the same twelve picks"),
        ("0", "slot changes since Jan-2025", "both re-runs held every slot"),
        ("16 months", "elapsed of a 3-to-5-year call", "to 2026-05-27"),
    ])
    cols = [("Category", 2.45, "l"), ("The two picks", 2.35, "c"), ("Category mean", 1.75, "r"),
            ("Read", UW - 6.55, "l")]
    rows = [
        ("Small Cap", "+7.3%  ·  +7.0%", "+7.15%", "The best pair of the twelve, both picks."),
        ("Flexi Cap", "+2.4%  ·  +1.7%", "+2.05%", "Consistent with its backtested edge."),
        ("Large Cap", "-1.2%  ·  +3.6%", "+1.20%", "Index core; the pair disagrees sharply."),
        ("Multi Cap", "-6.0%  ·  +5.2%", "-0.40%", "An 11-point spread inside one category."),
        ("Large & Mid Cap", "-0.3%  ·  -3.1%", "-1.70%", "Best backtested edge, negative live."),
        ("Mid Cap", "-7.7%  ·  -1.1%", "-4.40%", "The routing to momentum, vindicated early."),
    ]
    deck.table(s, ML, 2.86, UW, cols, rows, rowh=0.36, fs=9.5, hfs=8, zebra=True)
    co(deck, s, ML, 5.43, UW, "Sixteen months is a check, not evidence",
       "Twelve picks over sixteen months, with a 15-point spread between the best and worst "
       "single pick, cannot confirm a three-to-five-year thesis either way.", "warn")
    deck.source(s, "Recomputed from QFRA2_realized.csv, rank<=2 rows, alpha_ann_pct, "
                   f"Jan-2025 to {AS_OF}. Slot stability from QFRA2_history_rebuilt.csv "
                   "(2025-H2 and 2026-H1 both 'held' in all six). The previous pack's +0.9% is "
                   "the all-eight-category mean and includes Focused, which is out of scope.")
    return s


def page_churn(deck):
    """RESTORED. The old deck's slide 15, on the realised rate rather than the invented one.

    The old caption said "~2.6 changes/yr". The same script's own bar data eight lines earlier
    sums to 31 slot changes over eight years -- 3.9/yr -- and every reconciled firm document
    agrees on 3-4/yr. The chart is redrawn because the old PNG bakes 2.6 into its pixels; the
    bar counts are independently reproduced from the rebuilt slot-stable history, which is what
    makes 3.9 safe to print rather than merely conventional.
    """
    s = deck.content(5, "Track record", "How rarely the book actually changes",
                     "Eight years of realised turnover, and what the discipline costs")
    deck.pic(s, CH_CHURN, ML, 1.90, UW, 2.02)
    y = 4.00
    y = co(deck, s, ML, y, UW, "Why low churn is a product feature and not laziness",
           "Thirty-one slot changes across the six deployed categories in eight years is 3.9 a "
           "year, or an average holding near three years. That keeps gains in the long-term "
           "bracket and keeps the operational load on an advisory book small. Large & Mid "
           "changed most, at seven; Small Cap changed three times in eight years.", "note")
    co(deck, s, ML, y + 0.08, UW, "And the bill for it, stated once more",
       "The same discipline absorbs most of the measured selection edge: +0.09%/yr held against "
       "+0.48% unconstrained. Low churn is being bought, not received free.", "warn")
    deck.source(s, "Recomputed from qfra2_pac_prep/QFRA2_history_rebuilt.csv, 17 review "
                   "periods, first period excluded as the book's start; independently "
                   "reproduces qfra2_charts_ceo.py's own bar data (7/6/5/5/5/3). Chart: "
                   "chart_qfra2_evidence.py. The previous pack's 2.6/yr is unsupported.")
    return s


def page_rejected(deck):
    """RESTORED. The old deck's slide 25 -- the integrity log, from QFRA2_HANDOFF.md section 7.

    One change of substance. The old slide said rolling-consistency targeting was "the worst
    method (3Y median -1.44%, win 32.7%)". Neither figure reproduces from
    outputs/backtest/strategy_comparison.csv under any pooling I could construct (unweighted
    3Y mean is -1.32%/34.7%, n-weighted -1.31%). So the claim is restated as something the file
    does support exactly, and which is stronger: rolling consistency is the worst of the four
    alternatives at three years in all eight categories, verified category by category.
    """
    s = deck.content(5, "Track record", "What we tested and did not ship",
                     "Nine rejections and one adoption, kept as a standing record",
                     "We do not ship what we cannot validate. This log is the only evidence "
                     "that the rule actually binds")
    cols = [("What was tested", 3.30, "l"), ("Why it is not in the model", UW - 3.30, "l")]
    rows = [
        ("Downside information-ratio slot",
         "Looked good on pooled medians, then failed the paired block bootstrap. Not adopted."),
        ("Six-month tactical capture signals",
         "Strong at six months, but high turnover and short-term-gains heavy, which a three-to-"
         "five-year mandate cannot carry. Survives only as the frozen 0.30 capture weight."),
        ("Rolling-consistency targeting",
         "The worst of the four alternatives at three years in all eight categories."),
        # "no robust gain" is how HANDOFF section 7 words it; "robust" is a tellscan AI_TELL,
        # so the finding is stated rather than the adjective borrowed.
        ("Capture weight above 0.40",
         "Raising the weight bought no gain that survived validation. It ships at 0.30."),
        ("Bull and bear regime timing",
         "Mixed, unstable and era-dependent. Around 4% of dates are bear dates: too few to "
         "validate on."),
        ("A contrarian sleeve",
         "Helped only the mean-reverting categories, so SENTINEL is switched off for Mid and "
         "Value instead of adding a sleeve."),
        ("Machine learning on the cross-section",
         "Five to nine funds per category memorises one era. Rejected on our own evidence, "
         "well before the claim appeared on a slide."),
        ("Model retunes V1 to V5, IC-base, alpha persistence, cap split",
         "All rejected on out-of-sample significance."),
        # NOT an em dash: slidekit.txt() rewrites " — " to ", " for glyph hygiene (Bahnschrift
        # cannot render it), which rendered this row as "for Mid ,  ADOPTED" in the PDF.
        ("Momentum smart beta for Mid  ·  ADOPTED",
         "The one enhancement that cleared the same out-of-sample bar the retunes failed."),
    ]
    deck.table(s, ML, 1.96, UW, cols, rows, rowh=0.40, fs=9, hfs=8, zebra=True)
    deck.source(s, "QFRA2_HANDOFF.md section 7, the integrity log. Rolling-consistency claim "
                   "verified category by category against outputs/backtest/"
                   "strategy_comparison.csv; the previous pack's -1.44% / 32.7% for it does "
                   "not reproduce from that file and is not repeated.")
    return s


# --------------------------------------------------------------- validation aside (2026-08-06)
# The three pages below are STOCK-scorecard evidence (STOCK_SCORECARD_750), not QFRA-2. They
# exist to show how the firm tests a model before a committee sees it, using the larger, more
# recent stress-test run because it is the clearer demonstration. Every number is labelled
# stock-score on its own slide; none of it is carried into a QFRA-2 claim anywhere in this deck.
def page_validation_intro(deck):
    s = deck.content(5, "How we test", "How we test our own engines",
                     "Five stress-tests, run this cycle on the stock-scoring engine, shown for "
                     "the discipline alone")
    y = 1.92
    y = co(deck, s, ML, y, UW, "Scope, stated before the numbers",
           "Every figure on the next two pages is from the 750-stock scorecard, a different "
           "model on a different asset class, run 2026-08-04 to 2026-08-05. None of it is "
           "QFRA-2 evidence. It is shown because a committee approving one model should see "
           "how the firm tries to break its models in general.", "note")
    cols = [("Test", 3.0, "l"), ("What it checks", UW - 3.0, "l")]
    rows = [
        ("Rolling deciles, pre- vs post-gate", "Whether the balance-sheet gate, penalty and "
                                               "boost layer adds ranking power or costs it."),
        ("Regime and PSU split", "Whether the decile edge is a bull market or a PSU rally "
                                 "rather than stock selection."),
        ("PEG versus plain price-to-earnings", "Whether the Value pillar marks down fast "
                                                "growers for looking expensive on an earnings "
                                                "multiple alone."),
        ("Size decomposition by decile", "Whether a large, mid or small-cap tilt, not the "
                                         "score, is driving the decile spread."),
        ("Point-in-time literal rescore", "Whether a score built only from information "
                                          "available on the day still separates deciles."),
    ]
    deck.table(s, ML, y + 0.14, UW, cols, rows, rowh=0.44, fs=9.5, hfs=8, zebra=True)
    deck.source(s, "bt_decile_rolling.py, bt_regime_psu_test.py, bt_peg_test.py, "
                   "bt_size_by_decile.py, bt_decile_pit.py. Stock-score evidence, not QFRA-2.")
    return s


def page_validation_findings(deck):
    s = deck.content(5, "How we test", "What those tests found",
                     "Two results, both from the stock score, neither one QFRA-2 evidence")
    y = 1.92
    y = co(deck, s, ML, y, UW, "The gate layer gives up ranking power",
           "Across 35 rolling one-year formations on the stock score (pooled n=14,943), the "
           "composite score computed before the balance-sheet gate, penalty and boost layer "
           "separates deciles better than the deployed score computed after that layer: a "
           "top-minus-bottom spread of +9.4pp against +7.6pp, and a 94% per-formation hit "
           "rate against 86%. Windows overlap, so no t-statistic is quoted; the hit rate is "
           "the number built to survive that.", "warn")
    y = co(deck, s, ML, y + 0.12, UW, "A quarter of the top decile is government-owned",
           "PSU names are 8% of the bottom decile and 25% of the top one on the deployed, "
           "post-gate score. Remove them and the top-minus-bottom spread on that score falls "
           "from +7.6pp to +2.5pp: the edge "
           "does not disappear, but most of the concentration does. The PSU list used is "
           "hand-built and not exhaustive, which biases this toward understating the "
           "dependence, not overstating it.", "warn")
    co(deck, s, ML, y + 0.12, UW, "What neither test can say",
       "The panel behind both starts 2021-07-16; its worst 12-month forward window is about "
       "-6%. That is a flat market, not a full cycle, and the up-versus-down split is 29 "
       "formations against 7 that mostly overlap, closer to one down episode than seven. "
       "This is a stock-score limitation, and the fund-side version of it has its own page "
       "ahead.", "note")
    deck.source(s, "DECILE_ROLLING_20260805/summary.json; REGIME_PSU_20260805/psu_test.csv. "
                   "Stock-score evidence, not QFRA-2.")
    return s


def page_score_distribution(deck):
    s = deck.content(5, "How we test", "Where the calls actually sit",
                     "Stock-score evidence again, not QFRA-2: 751 names, scored 2026-08-05")
    deck.pic(s, CH_SCORE_DIST, ML, 1.86, UW, 2.55)
    co(deck, s, ML, 4.53, UW, "56% of the universe sits in the two middle buckets",
       "751 stocks, scored on the frozen stock methodology. 217 score 40 to 50 and 206 score "
       "50 to 60 on the 3-year horizon: 56% of the universe sits in the two buckets on either "
       "side of the Hold line. 85 names sit within 2 points of the 40 sell bar and 92 within "
       "2 points of the 50 Hold line, close enough that a small score revision flips the "
       "call. Stock-score evidence, not QFRA-2, and the clearest single case in the firm for "
       "why a model gets tested this hard before a committee sees it.", "warn")
    deck.source(s, "chart_score_distribution.py output (pr_template/out/score_distribution.png), "
                   "751-row scored universe, run 2026-08-05. Stock-score evidence, not QFRA-2.")
    return s


def page_limits(deck):
    s = deck.content(5, "Track record", "The limits we accept",
                     "Stated up front, because the committee will find them anyway")
    items = [
        ("The deployed edge is small",
         "+0.09% a year at three years on the held book, against +0.48% for the "
         "unconstrained ranking. This is the honest headline."),
        ("One era of validation",
         "Roughly 2014 to 2024, a single macro regime. The edge is regime-dependent and we "
         "cannot yet show it across a full cycle."),
        ("The universe is thin",
         "5 to 9 eligible funds per deployed category, not the 40 to 60 previously stated. "
         "A top-five shortlist is close to the whole field in four of six categories, and "
         "the binding constraint is NAV coverage, not the gates."),
        ("Scores do not compare across categories",
         "The score is a within-category rank. 80 out of 100 is second of five in Large and "
         "Mid; 88 is fourth of thirty-three in Focused."),
        ("The asset floor is unenforced where the feed is missing",
         "Twelve of the forty published rows carry no asset figure, so the capacity gate "
         "cannot bite there. This includes every Focused and Value row."),
        ("The scope decision and realised alpha disagree",
         "Focused and Value are excluded, yet they are two of only three categories whose "
         "held book was positive at three and five years. The exclusion rests on edge over "
         "a blind pick, not on realised alpha. The committee should know it is choosing "
         "between two defensible lenses."),
    ]
    y = 1.92
    for head, body in items:
        deck.txt(s, ML, y, UW, 0.28, [(head, SANS, 11, NAVY, True)])
        deck.txt(s, ML + 0.02, y + 0.29, UW - 0.04, 0.44, [(body, SANS, 9.8, INK, False)])
        y += 0.76
    deck.source(s, "Universe and scores verified 2026-08-04. Held-book alpha from the "
                   "engine's own performance file.")
    return s


def page_fund_regime_gap(deck):
    """The fund-side half of the validation aside: what QFRA-2 itself still has not been put
    through. Kept as its own page rather than a seventh bullet on page_limits, which already
    reaches the BOTTOM budget with six."""
    s = deck.content(5, "Track record", "The test we have not pointed at QFRA-2",
                     "Built this cycle, run on the stock score. Not yet run on the fund "
                     "engine itself")
    y = 1.92
    y = co(deck, s, ML, y, UW, "What we know, and what we have not checked",
           "QFRA-2's own validation runs one era, roughly 2014 to 2024 (previous page). "
           "Separately, this cycle a bull-versus-bear regime split was built and run on the "
           "stock score: on that panel the edge shrinks but survives a flat market. That "
           "method has not been run on QFRA-2's own fund-level returns. Until it is, \"one "
           "era\" should be read as \"untested across a downturn\", not simply \"a shorter "
           "sample than we would like.\"", "warn")
    y = co(deck, s, ML, y + 0.12, UW, "Why this is not a small gap",
           "QFRA-2's factor step and several of its signals, down-capture, Calmar, alpha "
           "stability, are exactly the kind of measure the stock-side quality challenge "
           "targets: that fundamentals stop discriminating in a rally. The same question "
           "applies to a fund ranked partly on down-capture and drawdown behaviour. The fix "
           "is mechanical, not conceptual: replay the eight years of category-level "
           "formations split by market regime, the design already used on the stock score.",
           "note")
    co(deck, s, ML, y + 0.12, UW, "Not asked to close today",
       "Point the regime-split method built for the stock score at QFRA-2's own "
       "category-level history. Flagged here as a gap, not answered here.", "note")
    deck.source(s, "Limits from the previous page. Regime method: bt_regime_psu_test.py, "
                   "REGIME_PSU_20260805/. Not yet applied to QFRA-2's own return history.")
    return s


def page_ask(deck):
    s = deck.content(5, "The ask", "The decision sought",
                     "Approval to deploy, on the corrected numbers")
    deck.kpi_strip(s, [
        ("6", "categories in scope"),
        ("6 months", "review cadence"),
        ("frozen v2.0", "no further tuning"),
        ("3.9 / yr", "expected book changes"),
    ])
    y = 2.82
    y = co(deck, s, ML, y, UW, "Approve",
           "Deployment across the six categories: Large as an index core, Large and Mid, Mid as a "
           "momentum sleeve, Flexi, Multi and Small. Governance as described: a Direct-plan and "
           "total-return basis, the SENTINEL screen, a veto-or-trim-only discretionary gate, "
           "the churn rule, and a published record of recommendations and rejected ideas.",
           "ok")
    y = co(deck, s, ML, y + 0.08, UW, "Note, on the record",
           "This deck corrects five of the nine headline figures in the previous pack, "
           "including a machine-learning claim the engine does not support and a client-facing "
           "probability that was never computed. The model is unchanged and remains frozen; "
           "what changed is what we say about it.", "warn")
    co(deck, s, ML, y + 0.08, UW, "Two items we are not asking to close today",
       "Whether Focused and Value should be re-scoped, given their held books were positive "
       "while two deployed categories were not; and the small-cap follow-up. Both need work "
       "first.", "note")
    deck.source(s, "Corrections logged in 07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md and "
                   "03_RESEARCH_DESK/qfra2_pac_prep/NUMBER_AUDIT.md.")
    return s


def closing(deck):
    s = deck.slide(bg=NAVY)
    deck.rect(s, 0, 0, 13.333, 7.5, fill=NAVY)
    deck.txt(s, ML, 2.55, 10.9, 1.9,
             [[("Measure it, validate it,", SERIF, 33, WHITE, True)],
              [("screen out the losers, and say", SERIF, 33, WHITE, True)],
              [("where we cannot win.", SERIF, 33, GOLD, True)]])
    deck.rule(s, ML, 5.05, 4.2, color=GOLD, h=0.022)
    deck.txt(s, ML, 5.34, 10.6, 0.8,
             [("QFRA 2.0  ·  Quantitative Fund Ranking Algorithm  ·  frozen v2.0",
               SANS, 11.5, NT2, False)])
    return s


def main():
    for p in (CH_TENURE, CH_ANCHOR, CH_SCORE_DIST):
        if not os.path.exists(p):
            raise SystemExit(f"missing chart: {p}\nRun chart_qfra2_tenure.py, "
                             f"chart_anchor_pair.py or chart_score_distribution.py first.")
    for p in (CH_EDGE, CH_WINRATE, CH_MIDMOM, CH_CHURN):
        if not os.path.exists(p):
            raise SystemExit(f"missing chart: {p}\nRun chart_qfra2_evidence.py first.")
    deck = SK.new_deck()
    deck.footer_label = "QFRA 2.0"   # not the NDPMS "Portfolio Review"
    cover(deck)
    contents(deck)
    page_two_frameworks(deck)     # Principal 2026-08-06: the side-by-side must come FIRST
    page_exec_summary(deck)       # ... so the summary sits after it, not ahead of it
    sec1(deck); page_mandate(deck); page_evolution(deck)
    page_no_ml(deck); page_ai_boundary(deck)
    page_alpha(deck); page_vs_rating_houses(deck)
    sec2(deck); page_pipeline(deck); page_calibre(deck); page_sentinel(deck)
    page_mid_sleeve(deck); page_recommendations(deck); page_scorecard(deck)
    sec3(deck); page_raw_vs_held(deck); page_by_category(deck)
    # The two unconstrained-basis charts come AFTER the held-book pages, deliberately.
    page_edge_chart(deck); page_winrate_chart(deck)
    page_topper(deck); page_cadence(deck)
    sec4(deck); page_complementarity(deck); page_smallcap(deck)
    page_sell_rule(deck)
    sec5(deck); page_history(deck); page_live_proof(deck); page_churn(deck)
    page_rejected(deck)
    page_validation_intro(deck); page_validation_findings(deck); page_score_distribution(deck)
    page_limits(deck); page_fund_regime_gap(deck); page_ask(deck)
    closing(deck)
    deck.resolve_links()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    deck.save(OUT)
    print(f"wrote {OUT}")
    print(f"slides: {len(deck.prs.slides.__iter__.__self__._sldIdLst)}"
          if hasattr(deck, "prs") else "")


if __name__ == "__main__":
    main()
