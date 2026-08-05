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

Usage: python build_qfra2_pac_deck.py
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
AS_OF = "2026-05-27"          # QFRA2_current.csv asof
BUILT = "2026-08-05"


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
               "Total-Return benchmarks", SANS, 11.5, NT2, False)])
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
    items = [
        ("01", "What it is, and what it is not",
         "the mandate  ·  no machine learning, and why  ·  where the alpha comes from"),
        ("02", "How a rank is produced",
         "the pipeline  ·  CALIBRE  ·  SENTINEL  ·  the churn rule"),
        ("03", "The evidence, honestly",
         "raw versus deployed  ·  by category  ·  against a 3-year topper  ·  the cadence"),
        ("04", "The two frameworks",
         "why QFRA-1 is complementary  ·  where each one drives the call"),
        ("05", "Track record and the ask",
         "every review period since 2018  ·  limits  ·  the decision sought"),
    ]
    y = 1.95
    for num, title, sub in items:
        deck.txt(s, ML, y, 0.8, 0.5, [(num, SERIF, 22, GOLD, True)])
        deck.txt(s, ML + 0.95, y + 0.02, 9.9, 0.34, [(title, SANS, 14, INK, True)])
        deck.txt(s, ML + 0.95, y + 0.40, 9.9, 0.34, [(sub, SANS, 10, SLATE, False)])
        y += 0.80
    # The "this deck corrects the last one" point deliberately does NOT live here. It is made
    # where it can be evidenced -- the raw-versus-held page and the ask -- rather than as a
    # claim on the contents page.
    deck.txt(s, ML, y + 0.10, UW, 0.30,
             [("Five of the nine headline figures in the previous committee pack did not "
               "survive an audit against the engine's own outputs. They are corrected "
               "here, not repeated.", SANS, 10.5, SLATE, False)])
    deck.source(s, "Audit trail: 03_RESEARCH_DESK/qfra2_pac_prep/NUMBER_AUDIT.md")
    return s


# --------------------------------------------------------------- section 1
def sec1(deck):
    deck.section_divider(1, "What it is, and what it is not",
                         "The mandate, the absence of machine learning, and where the "
                         "alpha actually comes from", pages="4-7")


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


# --------------------------------------------------------------- section 2
def sec2(deck):
    deck.section_divider(2, "How a rank is produced",
                         "The pipeline end to end, the quality scorecard, the negative "
                         "screen, and the churn rule", pages="8-10")


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


# --------------------------------------------------------------- section 3
def sec3(deck):
    deck.section_divider(3, "The evidence, honestly",
                         "What the ranking earns, what the deployed book earns, and how "
                         "both compare with the obvious alternative", pages="13-16")


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
                         "where each one drives the call", pages="18-20")


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
                         "decision sought", pages="20-22")


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
             [("Measure it, validate it,", SERIF, 33, WHITE, True),
              ("screen out the losers, and say", SERIF, 33, WHITE, True),
              ("where we cannot win.", SERIF, 33, GOLD, True)])
    deck.rule(s, ML, 5.05, 4.2, color=GOLD, h=0.022)
    deck.txt(s, ML, 5.34, 10.6, 0.8,
             [("QFRA 2.0  ·  Quantitative Fund Ranking Algorithm  ·  frozen v2.0",
               SANS, 11.5, NT2, False)])
    return s


def main():
    for p in (CH_TENURE, CH_ANCHOR):
        if not os.path.exists(p):
            raise SystemExit(f"missing chart: {p}\nRun chart_qfra2_tenure.py and "
                             f"chart_anchor_pair.py first.")
    deck = SK.new_deck()
    deck.footer_label = "QFRA 2.0"   # not the NDPMS "Portfolio Review"
    cover(deck)
    contents(deck)
    sec1(deck); page_mandate(deck); page_no_ml(deck); page_ai_boundary(deck)
    page_alpha(deck)
    sec2(deck); page_pipeline(deck); page_calibre(deck); page_sentinel(deck)
    sec3(deck); page_raw_vs_held(deck); page_by_category(deck)
    page_topper(deck); page_cadence(deck)
    sec4(deck); page_complementarity(deck); page_smallcap(deck)
    page_sell_rule(deck)
    sec5(deck); page_history(deck); page_limits(deck); page_ask(deck)
    closing(deck)
    deck.resolve_links()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    deck.save(OUT)
    print(f"wrote {OUT}")
    print(f"slides: {len(deck.prs.slides.__iter__.__self__._sldIdLst)}"
          if hasattr(deck, "prs") else "")


if __name__ == "__main__":
    main()
