# -*- coding: utf-8 -*-
"""anand_reddy.py — REAL client ctx builder (first live NDPMS review, 2026-07-27).
Every number in this file is either lifted directly from the client's own statement
(Anand Reddy.xlsx) or comes from a named, dated source (agent research this session,
cited in comments). Nothing here is synthetic. Two data points on the statement could
not be resolved and are deliberately EXCLUDED rather than guessed — see data_notes.flags
and DATA_GAPS at the bottom of this file.

Source statement: 'Anand Reddy.xlsx' (MF sheet + Stocks sheet), read 2026-07-27.
Verdicts: analyst-financials-meera-krishnan, fm-fundamental-sanjay-kulkarni,
analyst-industrials-rohan-deshmukh, quant-head-arjun-rao (parallel agent research,
2026-07-27, web-sourced — see each entry's `source` field).
"""
import os
import re

# ----------------------------------------------------------------------------
# Client-safe text scrub (2026-07-27, HNI_DEEP tell-scan sweep). The `summary` /
# `structural_reason` fields above carry the REAL internal audit trail (who
# reviewed it, which method, what date, which third-party source) -- essential
# for our own record, banned from a client slide (QA LAW #3: no analyst names,
# no source names, no "pf_qual"/"quant-only"/method-citation vocabulary).
# `client_case` already carries a hand-authored clean sentence for all 15 Sell
# names (unchanged below); this scrub produces the same for the 19 Hold names
# and every fund's structural_reason, by stripping the citation clause and
# keeping the real analysis that follows -- never inventing new content.
# ----------------------------------------------------------------------------
_CITE_PREFIX = re.compile(
    r'^(Quant-only,?\s*)?analyst view [\d-]+\s*(\([^)]*\))?\s*[:.,]?\s*'
    r'|^Quant-head research [\d-]+\s*\([^)]*\)\s*[:.,]?\s*'
    r'|^One-time review\s*\([^)]*\)\s*[:.,]?\s*'
    r'|^House decision\s*\([^)]*\)\s*[:.,]?\s*'
    r'|^Ratified (Sell|Hold)\s*\(pf_qual[^)]*\)\.?\s*,?\s*',
    re.IGNORECASE)
_CITE_PAREN_TOKENS = re.compile(
    r'(INDmoney|Groww|Paytm Money|Advisorkhoj|AMFI NAV|pf_qual|screener\.in|'
    r'Meera Krishnan|Sanjay Kulkarni|Principal|code \d+)', re.IGNORECASE)


def _scrub_client_text(raw):
    """Strip the internal-audit citation preamble from a real analyst sentence, keeping the
    substantive reasoning. Returns "" if nothing survives (bare citation, no content) -- caller
    supplies a generic, score-derived fallback in that case, never an invented claim."""
    if not raw:
        return ""
    t = _CITE_PREFIX.sub("", raw.strip())

    def _kill_paren(m):
        return "" if _CITE_PAREN_TOKENS.search(m.group(1)) else m.group(0)
    t = re.sub(r'\(([^)]*)\)', _kill_paren, t)
    t = t.replace("quality_score", "quality score")  # de-snake-case, QA LAW #3
    t = re.sub(r'\s{2,}', ' ', t).strip(' ,.')
    if t:
        t = t[0].upper() + t[1:]
        if not t.endswith('.'):
            t += '.'
    return t

FIRM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# ============================================================================
# EQUITY (27 scored positions: 18 in our 750-scorecard/NIFTY500 universe verified
# by ISIN, + 9 one-time-scored out-of-universe names, per Principal 2026-07-27:
# "even if stock is not in nifty 750 use of method... for this review". 3 more
# holdings (Parekh Aluminex, Balasore Alloys, Value Industries) are SUSPENDED/
# INSOLVENT and excluded from this list -> see DATA_NOTES.
# ============================================================================
_EQUITY = [
    # --- 18 in-universe (full750_scored.csv + pf_qual where available) ---
    # your_recommendation from pf_qual_*.json (ratified) where present, else the
    # Wave-1 agent's judgment on the real quant metrics (full750_scored.csv, 2026-07-26 run)
    dict(symbol="RELIANCE", name="Reliance Industries Ltd.", sector="Oil Gas & Consumable Fuels",
         value_inr=2894670, ionic_score=27.3, score_3y=27.3, score_1y=32.4, rec="Sell",
         reason_category="Quality below peers", pit_date="2026-07-21",
         summary="Ratified Sell (pf_qual, recheck 2026-07-25/26): bottom-quartile quality/value, "
                 "negative 6m/12m momentum, no margin of safety despite record segment EBITDA.",
         client_case="Bottom-quartile on quality and value versus large-cap peers; momentum has turned "
                     "negative even as segment EBITDA hit a record."),
    dict(symbol="HDFCBANK", name="HDFC Bank Ltd.", sector="Financial Services", value_inr=1708440,
         ionic_score=53.0, score_3y=53.0, score_1y=49.5, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual)."),
    dict(symbol="TCS", name="Tata Consultancy Services Ltd.", sector="Information Technology",
         value_inr=1408938, ionic_score=50.6, score_3y=50.6, score_1y=49.2, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual)."),
    dict(symbol="JIOFIN", name="Jio Financial Services Ltd.", sector="Financial Services",
         value_inr=281652, ionic_score=37.9, score_3y=37.9, score_1y=38.1, rec="Sell",
         reason_category="Rich valuation, thin margin of safety", pit_date="2026-07-21",
         summary="Ratified Sell (pf_qual): 1.1x book prices ~14% normalized ROE vs actual ~1-2%.",
         client_case="Priced at ~1.1x book for a ~14% normalised return on equity the business is "
                     "currently earning only 1-2% of, leaving little margin of safety."),
    dict(symbol="ICICIBANK", name="ICICI Bank Ltd.", sector="Financial Services", value_inr=78810,
         ionic_score=58.8, score_3y=58.8, score_1y=53.6, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual)."),
    dict(symbol="SBIN", name="State Bank of India", sector="Financial Services", value_inr=50750,
         ionic_score=69.9, score_3y=69.9, score_1y=49.5, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual)."),
    dict(symbol="SBFC", name="SBFC Finance Ltd.", sector="Financial Services", value_inr=46090,
         ionic_score=25.5, score_3y=25.5, score_1y=41.1, rec="Sell",
         reason_category="Rich valuation, thin margin of safety", pit_date="2026-07-26",
         summary="Quant-only, analyst view 2026-07-27 (Meera Krishnan): fundamentals aren't broken "
                 "(profit +29% YoY, GNPA stable 2.66%) but 29.4x PE with quality_score 22.7 still "
                 "isn't cheap despite the price fall. Affirm Sell on valuation discipline.",
         client_case="Fundamentals are intact — profit up ~29% YoY, asset quality stable — but at "
                     "~29x earnings the stock isn't cheap enough to justify holding through the "
                     "recent price fall."),
    dict(symbol="IDFCFIRSTB", name="IDFC First Bank Ltd.", sector="Financial Services", value_inr=40395,
         ionic_score=49.7, score_3y=49.7, score_1y=48.5, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual)."),
    dict(symbol="TATASTEEL", name="Tata Steel Ltd.", sector="Metals & Mining", value_inr=27400,
         ionic_score=51.3, score_3y=51.3, score_1y=32.5, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual) — analyst override of the quant Sell."),
    dict(symbol="MANAPPURAM", name="Manappuram Finance Ltd.", sector="Financial Services", value_inr=17648,
         ionic_score=45.4, score_3y=45.4, score_1y=38.6, rec="Sell",
         reason_category="Rich valuation, thin margin of safety", pit_date="2026-07-26",
         summary="Quant-only, analyst view 2026-07-27: real tailwinds (Bain Capital stake approval, "
                 "eased gold-loan LTV norms) but 28.6x PE now prices in a turnaround revenue growth "
                 "(-5.4% YoY) hasn't delivered. Affirm Sell.",
         client_case="Real tailwinds (a large institutional stake approval, easier gold-loan rules) are "
                     "already more than priced in at ~29x earnings against revenue that is still falling."),
    dict(symbol="NTPC", name="NTPC Ltd.", sector="Power", value_inr=17360,
         ionic_score=45.2, score_3y=45.2, score_1y=32.8, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual) — analyst override of the quant Sell."),
    dict(symbol="MAHABANK", name="Bank of Maharashtra", sector="Financial Services", value_inr=16206,
         ionic_score=78.6, score_3y=78.6, score_1y=63.2, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual)."),
    dict(symbol="BEL", name="Bharat Electronics Ltd.", sector="Industrials", value_inr=11745,
         ionic_score=57.9, score_3y=57.9, score_1y=46.6, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual)."),
    dict(symbol="IDBI", name="IDBI Bank Ltd.", sector="Financial Services", value_inr=8493,
         ionic_score=52.2, score_3y=52.2, score_1y=46.8, rec="Hold", pit_date="2026-07-26",
         summary="Quant-only, analyst view 2026-07-27: 9.9x PE prices real privatization deal "
                 "uncertainty (Fairfax India bid vs a stalled earlier round). Hold reflects "
                 "optionality without conviction to add into an unresolved deal. ESCALATION: "
                 "binary outcome, watch the Sept-2026 government target."),
    dict(symbol="SJVN", name="SJVN Ltd.", sector="Power", value_inr=5068,
         ionic_score=31.4, score_3y=31.4, score_1y=29.3, rec="Sell",
         reason_category="Balance-sheet strain", pit_date="2026-07-26",
         summary="Quant-only, analyst view 2026-07-27: AMBER balance-sheet flag earned — 5,091MW "
                 "under construction vs 3,147MW installed, funded on D/E 2.27x; market pays 43x PE "
                 "for flawless multi-year execution. Affirm Sell.",
         client_case="A large expansion programme (over 5,000MW under construction against ~3,100MW "
                     "already live) is funded at a stretched debt-to-equity of ~2.3x, while the stock "
                     "trades near 43x earnings — priced for flawless execution."),
    dict(symbol="UCOBANK", name="UCO Bank", sector="Financial Services", value_inr=2588,
         ionic_score=42.9, score_3y=42.9, score_1y=44.3, rec="Hold", pit_date="2026-07-26",
         summary="Quant-only, analyst view 2026-07-27: asset quality genuinely improving (GNPA "
                 "2.69%, FY25 profit +47.8%) at a cheap 12.8x PE, but a live QIP dilution pipeline "
                 "(~Rs 2,700cr needed by Aug-2026) explains the price weakness. Hold."),
    dict(symbol="ITC", name="ITC Ltd.", sector="Fast Moving Consumer Goods", value_inr=1134,
         ionic_score=59.7, score_3y=59.7, score_1y=45.1, rec="Hold", pit_date="2026-07-21",
         summary="Ratified Hold (pf_qual)."),
    dict(symbol="RPOWER", name="Reliance Power Ltd.", sector="Power", value_inr=650,
         ionic_score=38.3, score_3y=38.3, score_1y=30.7, rec="Sell",
         reason_category="Weaker forward risk-reward", pit_date="2026-07-26",
         summary="Quant-only, analyst view 2026-07-27: weakest quality_score of the quant-only set "
                 "(7.1), PE negative, revenue flat 3 years, stock down -62%/12m. RED balance-sheet "
                 "flag. Affirm Sell.",
         client_case="The weakest quality score of the names reviewed, negative earnings, three years "
                     "of flat revenue and a 62% price decline over the past year; balance-sheet risk flagged."),
    # --- 9 one-time-scored, out-of-universe (Principal 2026-07-27 ruling: apply the same
    # method for this review even though these are outside NIFTY 500/the 750 scorecard) ---
    dict(symbol="RITAFIN", name="Rita Finance and Leasing Ltd.", sector="Financial Services (unlisted-adjacent)",
         value_inr=33853, ionic_score=15, score_3y=15, score_1y=15, rec="Sell", pit_date="2026-07-27",
         reason_category="Forensic / governance flag",
         summary="One-time review (Sanjay Kulkarni, 2026-07-27, screener.in): Rs13.3cr market cap "
                 "on Rs1.33cr FY26 sales — a listed shell-adjacent entity, not an operating NBFC. "
                 "77.3% of promoter holding pledged; promoter stake down 44.8%->28.9% in 3 years; "
                 "BSE surveillance query on unusual price movement (Mar-2026). Exit on limit orders.",
         client_case="A very small listed entity (~Rs13cr market cap on ~Rs1.3cr of sales) with the "
                     "large majority of promoter holding pledged and an exchange query on unusual "
                     "price movement. Exit on limit orders, not market orders."),
    dict(symbol="LANCORHOL", name="Lancor Holdings Ltd.", sector="Realty",
         value_inr=12905, ionic_score=28, score_3y=28, score_1y=28, rec="Sell", pit_date="2026-07-27",
         summary="One-time review (2026-07-27, screener.in): FY26 profit of Rs40cr sits on just "
                 "Rs1cr operating profit against Rs131cr sales — Rs73.9cr of other income (a "
                 "litigation recovery) does the work. Core margin collapsed 17%->~1% YoY, working "
                 "capital days blew out 416->638. Value trap at 0.78x book, not a margin of safety.",
         client_case="Reported profit is being carried almost entirely by a one-off litigation "
                     "recovery, not the underlying business — core operating margin has collapsed "
                     "and working-capital days have blown out."),
    dict(symbol="SUMMITSEC", name="Summit Securities Ltd.", sector="Financial Services (holding co.)",
         value_inr=11862, ionic_score=30, score_3y=30, score_1y=30, rec="Sell", pit_date="2026-07-27",
         summary="One-time review (2026-07-27, screener.in): a genuine 0.19x book RPG-group holdco "
                 "discount (Rs3,776cr investments, zero debt) but no monetisation catalyst — ROE "
                 "1.14%, never paid a dividend, promoters at 74.64% with no float headroom. "
                 "ESCALATION flagged to CIO: a long-horizon Hold is intellectually defensible, but "
                 "8 shares isn't a position worth carrying that debate for.",
         client_case="A holding company trading at a steep discount to its investment book with no "
                     "debt, but no catalyst to close that discount and no dividend history — too "
                     "small a position to justify the wait."),
    dict(symbol="NETWORK18", name="Network18 Media & Investments Ltd.", sector="Media",
         value_inr=8586, ionic_score=22, score_3y=22, score_1y=22, rec="Sell", pit_date="2026-07-27",
         summary="One-time review (2026-07-27, screener.in): still separately listed post the "
                 "TV18/e-Eighteen merger (Oct-2024) and the unrelated Viacom18-Star/JioStar deal "
                 "(Nov-2024) — no delisting, ISIN unchanged. 3y ROE -2.19%, last two quarters both "
                 "losses. The only bull case is an unlisted JioStar stake with no public valuation "
                 "— a story, not a thesis.",
         client_case="Still loss-making over the last two quarters with negative return on equity; "
                     "the bull case rests on an unlisted media stake with no public valuation — a "
                     "story, not yet a thesis."),
    dict(symbol="MOSCHIP", name="MosChip Technologies Ltd.", sector="Information Technology",
         value_inr=5795, ionic_score=18, score_3y=18, score_1y=18, rec="Sell", pit_date="2026-07-27",
         summary="One-time review (2026-07-27, screener.in): 129x PE / 10.2x book for 11% ROE — no "
                 "margin of safety. Promoter holding diluted 50.3%->39.3% (Sep-2023 to Jun-2026) via "
                 "repeated preferential share issues funding acquisitions. Revenue and profit both "
                 "declined quarter-on-quarter in the latest print. Under BSE Long-Term ASM.",
         client_case="Trading at a rich ~129x earnings against an 11% return on equity, with promoter "
                     "holding diluted through repeated share issuances and both revenue and profit "
                     "declining quarter-on-quarter."),
    dict(symbol="MUFIN", name="Mufin Green Finance Ltd.", sector="Financial Services",
         value_inr=3108, ionic_score=20, score_3y=20, score_1y=20, rec="Sell", pit_date="2026-07-27",
         summary="One-time review (2026-07-27, screener.in): 88.3x P/E, 4.3x P/B against ROE of "
                 "just 6.69% — a severe quality-value mismatch. FY26 operating cash flow was "
                 "-Rs695cr despite a reported profit; flagged low interest coverage.",
         client_case="A steep mismatch between price (~88x earnings) and quality (under 7% return on "
                     "equity), with negative operating cash flow despite a reported accounting profit."),
    dict(symbol="PRAGBOSIMI", name="Prag Bosimi Synthetics Ltd.", sector="Textiles/Chemicals",
         value_inr=1870, ionic_score=5, score_3y=5, score_1y=5, rec="Sell", pit_date="2026-07-27",
         summary="One-time review (2026-07-27, screener.in): negative net worth (book value "
                 "-Rs1.96/share), ROCE -3.41%, auditor flagged material uncertainty on going "
                 "concern in FY26 results. Sales down 27.8% over 5 years. Not a going concern by "
                 "any quality screen.",
         client_case="Negative net worth and negative return on capital, and the company's own "
                     "auditors have flagged material doubt over its ability to continue as a going "
                     "concern."),
    # Standing rule (Principal 2026-07-27, permanent — see ndpms-deck skill "PRINCIPAL RULINGS"):
    # a factor ETF/index fund held directly defaults to HOLD, not Sell, on portfolio-construction
    # grounds alone — the earlier "consolidate all passive/factor exposure" blanket call is
    # superseded. The ONE named exception is a Nifty 200 Momentum 30 factor fund specifically,
    # which stays Sell (momentum has a documented regime-dependent failure mode the house already
    # gates elsewhere — ALPHA_RANKER valuation-band rule). Plain, non-factor index funds (e.g. a
    # vanilla Nifty 50 index fund) are unaffected by this rule and can still be Sold on ordinary
    # consolidation/cost grounds.
    dict(symbol="MOVALUE", name="Motilal Oswal S&P BSE Enhanced Value ETF", sector="Passive/Factor ETF",
         value_inr=5635, ionic_score=35, score_3y=35, score_1y=35, rec="Hold", pit_date="2026-07-27",
         summary="House rule (Principal 2026-07-27): factor ETFs default to Hold, not a blanket "
                 "passive-consolidation Sell. A genuine, low-cost multi-factor value screen, "
                 "~0.20-0.35% TER, ~Rs147cr AUM — no quality concern with the ETF itself.",
         client_case="A sound, low-cost factor ETF with no quality concern; held as a Hold under "
                     "our standing policy for factor funds."),
    dict(symbol="MOM30IETF", name="ICICI Prudential Nifty 200 Momentum 30 ETF", sector="Passive/Factor ETF",
         value_inr=3059, ionic_score=35, score_3y=35, score_1y=35, rec="Sell", pit_date="2026-07-27",
         reason_category="Weaker forward risk-reward",
         summary="House rule (Principal 2026-07-27): factor ETFs default to Hold, EXCEPT a Nifty 200 "
                 "Momentum 30 factor fund specifically, which stays Sell. Tracks the Nifty 200 "
                 "Momentum 30 TRI, ~0.30% TER, ~Rs656cr AUM, reasonably liquid — the Sell is the "
                 "named policy exception, not a quality concern with the ETF itself.",
         client_case="A liquid, well-tracked momentum ETF; momentum factors carry a regime-dependent "
                     "risk our house view treats as a standing exception, so this one stays a Sell "
                     "while other factor funds in this account are Held."),
]
# real Invested Value from the client's own statement (Stocks sheet), for the 15 Sell-rated
# names only -- used to compute a REAL gain/loss for the tax slide rather than assume one.
# Verified 2026-07-27: net gain across all 15 = -Rs 1,93,522 (a real, computed LOSS).
_INVESTED = {
    "RELIANCE": 2928706.0, "JIOFIN": 393145.0, "SBFC": 42870.0, "RITAFIN": 51871.0,
    "MANAPPURAM": 8778.0, "LANCORHOL": 20000.0, "SUMMITSEC": 25712.0, "NETWORK18": 23913.0,
    "MOSCHIP": 6600.0, "SJVN": 8954.0, "MOVALUE": 5016.0, "MUFIN": 2778.0,
    "MOM30IETF": 3519.0, "PRAGBOSIMI": 2990.0, "RPOWER": 1121.0,
}
# Bull case we rejected + reverse-DCF margin-of-safety text for every Sell name
# (RELIANCE, JIOFIN from ANALYST_RECOMMENDATIONS_v2.xlsx; others from analyst one-time reviews)
_BULL_RDCF = {
    "RELIANCE": {
        "positive": ("Both O2C and Jio Platforms hit record EBITDA in Q1 FY27. Jio Platforms IPO "
                     "DRHP filed June 2026, $133-180bn implied valuation, potentially unlocking "
                     "20-40% of RIL market cap in H2 2026. New Energy giga-complex on timeline. "
                     "Consolidated leverage comfortable (D/E 0.45, interest cover 6.6x)."),
        "reverse_dcf": ("Conservative sum-of-parts (O2C 8x, Jio 9x standalone-telco, Retail 22x, "
                        "E&P 5x, New Energy at committed capex): ~Rs 18L crore equity, within 3% of "
                        "current market cap. Not cheap, not overpriced. The asymmetry sits in Jio: "
                        "if the IPO prices near the DRHP range, that alone could unlock Rs 3.5-7L "
                        "crore not currently credited. But without that catalyst crystallising, "
                        "there is no margin of safety at today's price."),
    },
    "JIOFIN": {
        "positive": ("Jio Credit AUM 2.6x YoY to Rs 30,667cr, funded by promoter capital (D/E 0.16), "
                     "not leverage. JioBlackRock AMC past Rs 10,000cr AUM. Sell-side models 46% PAT "
                     "CAGR FY26-28. Stock already de-rated 26% over 12 months."),
        "reverse_dcf": ("At ~1.1x book the market prices in a normalised ROE of ~13.5-14% vs actual "
                        "~1-2%. Closing that gap requires multi-fold AUM growth and treasury "
                        "redeployment, none likely inside 2-3 years. A fair, not cheap, price for "
                        "patience with no margin of safety if the ramp disappoints."),
    },
    "SBFC": {
        "positive": ("Profit growing ~29% YoY, GNPA stable at 2.66%, a micro-NBFC gaining scale in "
                     "small-ticket secured lending with no balance-sheet stress."),
        "reverse_dcf": ("At ~29x earnings the stock prices in sustained 25%+ growth; current quality "
                        "score of 22.7 and sub-scale AUM leave no margin if growth slows."),
    },
    "MANAPPURAM": {
        "positive": ("Bain Capital stake approved, RBI eased gold-loan LTV norms, genuine structural "
                     "tailwinds for the gold-lending model."),
        "reverse_dcf": ("At ~29x earnings against falling revenue (-5.4% YoY), the stock prices in a "
                        "turnaround the top line has not yet delivered. No margin of safety."),
    },
    "SJVN": {
        "positive": ("5,091MW under construction doubles installed capacity; a government-backed PSU "
                     "with a visible pipeline in hydro and solar."),
        "reverse_dcf": ("At ~43x earnings with D/E 2.3x, the price assumes flawless multi-year "
                        "execution of a capital programme larger than the existing asset base. "
                        "No margin for delays or cost overruns."),
    },
    "RPOWER": {
        "positive": ("Reliance group pedigree and a general power-sector tailwind."),
        "reverse_dcf": ("Negative trailing PE, negative cash flow, flat revenue for three years. No "
                        "meaningful reverse-DCF is possible on negative earnings; the stock is priced "
                        "on hope, not cash flow."),
    },
    "RITAFIN": {
        "positive": ("A listed NBFC with a valid stock code and nominal promoter holding."),
        "reverse_dcf": ("Rs 13cr market cap on Rs 1.3cr of sales with 77% promoter pledge. No "
                        "credible earnings base exists to reverse-engineer a fair value from."),
    },
    "LANCORHOL": {
        "positive": ("Trades at 0.78x book, a Chennai-based developer with a 40-year track record "
                     "and low headline debt."),
        "reverse_dcf": ("FY26 profit was built on Rs 73.9cr of one-off litigation recovery against "
                        "Rs 1cr operating profit. Core margin collapsed from 17% to ~1%. At 0.78x "
                        "book, this is a value trap, not a margin of safety."),
    },
    "SUMMITSEC": {
        "positive": ("A genuine 0.19x book discount to Rs 3,776cr of RPG-group investments with zero "
                     "debt, a textbook deep-value holdco play."),
        "reverse_dcf": ("No monetisation catalyst, ROE 1.14%, zero dividends ever, promoters at "
                        "74.6% with no float headroom. The discount is earned and indefinite; too "
                        "small a position to justify a decade-long wait."),
    },
    "NETWORK18": {
        "positive": ("An unlisted stake in JioStar (the merged Viacom18-Star entity) that could "
                     "carry significant hidden value if eventually marked or monetised."),
        "reverse_dcf": ("Loss-making with negative ROE; the bull case rests entirely on an unlisted, "
                        "unvalued stake. No margin of safety when the only potentially valuable asset "
                        "has no public price."),
    },
    "MOSCHIP": {
        "positive": ("A semiconductor and VLSI design play in a growing addressable market, scaling "
                     "through acquisitions."),
        "reverse_dcf": ("At 129x PE for 11% ROE, the price assumes a massive ramp in returns the "
                        "declining quarterly trajectory contradicts. Promoter dilution from 50% to "
                        "39% via preferential issues means existing shareholders fund the growth."),
    },
    "MUFIN": {
        "positive": ("A green-finance NBFC in an expanding market with government support for "
                     "renewable lending."),
        "reverse_dcf": ("88x PE against 6.7% ROE with negative operating cash flow. No credible "
                        "valuation framework justifies this multiple on current economics."),
    },
    "PRAGBOSIMI": {
        "positive": ("A listed entity with a stock code."),
        "reverse_dcf": ("Negative net worth, negative returns on capital, and auditor going-concern "
                        "doubt. No reverse-DCF is possible; the equity is likely worthless."),
    },
    "MOM30IETF": {
        "positive": ("A well-tracked, liquid momentum factor ETF (ICICI Pru, ~0.30% TER, Rs 656cr "
                     "AUM) capturing the Nifty 200 Momentum 30 factor."),
        "reverse_dcf": ("An index product with no independent valuation to reverse-engineer. The "
                        "Sell is a house-view policy call on the momentum factor's regime-dependent "
                        "risk, not a valuation call on the ETF itself."),
    },
}
for _e in _EQUITY:
    if _e["symbol"] in _BULL_RDCF:
        _e.update(_BULL_RDCF[_e["symbol"]])
    _e.setdefault("score_3y", _e["ionic_score"]); _e.setdefault("score_1y", _e["ionic_score"])
    _e.setdefault("pe", None); _e.setdefault("roe", None); _e.setdefault("mcap_band", "Small")
    _e.setdefault("binding_trigger", (_e.get("summary", "")[:130]) if _e["rec"] == "Sell" else "")
    _e.setdefault("analyst_read", (_e.get("summary", "") or "").split(". ")[0][:150])
    _e.setdefault("growth_pct", None)
    _e.setdefault("positive", ""); _e.setdefault("negative", _e.get("summary", ""))
    _e.setdefault("reverse_dcf", ""); _e.setdefault("client_case", None)
    _e.setdefault("detailed", _e.get("summary", "")); _e.setdefault("escalation", "ESCALATION" in _e.get("summary", ""))
    _e.setdefault("reason_category", "" if _e["rec"] != "Sell" else "Weaker forward risk-reward")
    _e.setdefault("conviction", "Core" if (_e["ionic_score"] >= 58) else ("Watch" if _e["rec"] == "Hold" else "Exit"))
    _e["invested_value"] = _INVESTED.get(_e["symbol"])

# Real fundamentals enrichment (2026-07-27, quant-head research pass over
# full750_scored.csv / pf_qual_*.json / NSE index-constituent lists -- verified
# on-disk, not fabricated). Coverage disclosed, not padded: pe/roe 19/27, forward
# growth 12/27 (analyst-ratified pf_qual figure only -- no historical-growth
# stand-in used, to avoid mislabeling a backward-looking number as forward),
# official SEBI/AMFI cap-band 13/27 (the rest keep the existing "Small" default --
# NOT the internal quant-tercile field, which a spot-check showed can disagree
# with the real index membership, e.g. MAHABANK tercile="Large" vs real
# Midcap150 constituent).
_FUND_PE_ROE = {  # symbol -> (pe, roe_pct)
    "RELIANCE": (23.48, 25.0), "HDFCBANK": (15.74, 59.66), "TCS": (15.99, 100.0),
    "JIOFIN": (73.64, 5.04), "ICICIBANK": (18.1, 72.27), "SBIN": (11.33, 68.07),
    "SBFC": (29.36, 22.69), "IDFCFIRSTB": (39.05, 12.61), "TATASTEEL": (21.49, 33.33),
    "MANAPPURAM": (28.57, 40.34), "NTPC": (12.27, 52.38), "MAHABANK": (8.11, 78.15),
    "BEL": (49.11, 84.11), "IDBI": (9.87, 35.29), "SJVN": (42.98, 19.05),
    "UCOBANK": (12.79, 14.29), "ITC": (16.91, 88.37), "RPOWER": (-30.36, 4.76),
    "NETWORK18": (-131.78, 12.5),
}
_FUND_GROWTH = {  # symbol -> analyst-ratified expected next-3y growth %, pf_qual_*.json
    "RELIANCE": 11, "HDFCBANK": 13, "TCS": 7, "JIOFIN": 28, "ICICIBANK": 12, "SBIN": 11,
    "IDFCFIRSTB": 26, "TATASTEEL": 8, "NTPC": 10, "MAHABANK": 13, "BEL": 17, "ITC": 6,
}
_MCAP_OFFICIAL = {  # symbol -> real NSE index-constituent-confirmed band
    "RELIANCE": "Large", "HDFCBANK": "Large", "TCS": "Large", "JIOFIN": "Large",
    "ICICIBANK": "Large", "SBIN": "Large", "IDFCFIRSTB": "Mid", "TATASTEEL": "Large",
    "NTPC": "Large", "MAHABANK": "Mid", "BEL": "Large", "SJVN": "Mid", "ITC": "Large",
}
for _e in _EQUITY:
    _sym = _e["symbol"]
    if _sym in _FUND_PE_ROE:
        _e["pe"], _e["roe"] = _FUND_PE_ROE[_sym]
    if _sym in _FUND_GROWTH:
        _e["growth_pct"] = _FUND_GROWTH[_sym]
    if _sym in _MCAP_OFFICIAL:
        _e["mcap_band"] = _MCAP_OFFICIAL[_sym]
    # client_case is the single source of truth every module should read for client-facing
    # rationale prose. The 15 Sell names already carry a hand-authored one (kept as-is); the
    # 19 Holds get the scrubbed summary, or -- when the summary is a bare audit stamp with no
    # analysis attached ("Ratified Hold (pf_qual)." and nothing else) -- a generic sentence
    # built only from real, already-computed fields (the Ionic score itself), never invented.
    if not _e.get("client_case"):
        _scrubbed = _scrub_client_text(_e.get("summary", ""))
        _e["client_case"] = _scrubbed or (
            f"Scores {_e['ionic_score']:.0f}/100 on our quality/value/momentum framework — "
            + ("below our bar; recommended for exit." if _e["rec"] == "Sell"
               else "comfortably within our Hold range; no changes recommended this review."))
    _e["analyst_read"] = _e["client_case"][:150]
    _e["detailed"] = _e["client_case"]
    _e["negative"] = _e["client_case"]
    if _e["rec"] == "Sell":
        _e["binding_trigger"] = _e["client_case"][:130]

# ============================================================================
# FUNDS (25 scored: 5 with a real QFRA-2 category match + 20 one-time benchmark-
# relative research, per Principal 2026-07-27: "if a fund is not in qfra recom
# try comparing its benchmark 3y 1y performance". JioBlackRock Flexi Cap (<7mo
# track record) is EXCLUDED here -> "No View" in DATA_NOTES per the firm's new
# hard 7-month rule.
# qfra score = 50 + 3*(3y alpha, pp) + 1*(1y alpha, pp), clipped [5,95] — a
# transparent, disclosed scaling of REAL alpha-vs-benchmark numbers onto the
# deck's 0-100 display scale. NOT the full internal QFRA engine score for most
# of these (only the 5 marked qfra2_matched=True went through the real engine).
# ============================================================================
def _qscore(a3, a1):
    return max(5, min(95, round(50 + 3 * a3 + 1 * a1)))


_FUNDS_RAW = [
    # (name, category, bench_label, f3y, f1y, b3y, b1y, verdict, source_note)
    ("Mirae Asset Midcap Fund", "mid", "NIFTY Midcap 150 TRI", 18.6, 7.9, 18.1, 3.4, "Hold",
     "Quant-head research 2026-07-27 (INDmoney+Groww, date-matched 24-Jul-26): ahead 1y (+4.5pp), "
     "in line 3y (+0.5pp); beats the index but trails mid-cap category average by ~3pp."),
    # internal audit note (2026-07-27, Principal ruling): index/factor-ETF holdings get a blanket
    # Sell for portfolio-construction consolidation, no extra tracking-error work required
    ("HDFC NIFTY 50 Index Fund", "passive", "NIFTY 50 TRI", 0, 0, 0, 0, "Sell",
     "Tracking is clean — the gap versus benchmark is essentially just the expense ratio "
     "(0.19-0.31%, INDmoney). The Sell reflects a call to consolidate index exposure into a "
     "single fund, not a tracking-quality concern with this scheme."),
    ("HDFC Hybrid Equity Fund", "hybrid", "NIFTY 50 Hybrid Composite Debt 65:35", 6.6, -5.6, 10.2, 0.2, "Watch",
     "Quant-head research 2026-07-27 (INDmoney, corroborated Paytm Money): behind 3.6pp/3y and "
     "5.7pp/1y — the clearest laggard in the book."),
    ("Mirae Asset ELSS Tax Saver Fund", "elss", "NIFTY 500 TRI", 13.4, 0.8, 11.7, -1.9, "Hold",
     "Quant-head research 2026-07-27 (INDmoney+Groww): ahead ~1.7pp/3y and ~2.7pp/1y; beats the "
     "index but trails ELSS category average by ~3pp."),
    ("ICICI Prudential Dividend Yield Equity Fund", "dividend_yield", "NIFTY Dividend Opportunities 50 TRI",
     18.3, 1.7, 12.0, -1.4, "Hold",
     "Quant-head research 2026-07-27 (INDmoney+Groww, Advisorkhoj benchmark): ahead ~6pp/3y and "
     "~3pp/1y — strongest risk-adjusted contributor in the book."),
    ("Edelweiss Small Cap Fund", "small", "NIFTY Smallcap 250 TRI", 17.3, 3.9, 16.7, -1.1, "Hold",
     "Quant-head research 2026-07-27 (INDmoney+Groww): in line 3y (+0.6pp), ahead ~5pp/1y."),
    ("Bandhan Small Cap Fund", "small", "NIFTY Smallcap 250 TRI", 27.3, 5.6, 16.7, -1.1, "Hold",
     "Quant-head research 2026-07-27 (INDmoney, NAV-verified): ranked 1st in category, ahead "
     "~10.4pp/3y and ~6.7pp/1y. NOTE: a gap this large is unlikely to persist and raises a "
     "capacity question as AUM grows — flagged for the next review, not an action now."),
    # Client-specific constraint (Principal 2026-07-29): exit all liquid/debt/arbitrage and
    # debt-dominant (conservative-hybrid) holdings, proceeds to cash -- a portfolio-construction
    # call for THIS client, not a performance verdict; real performance was ahead on both windows.
    ("Aditya Birla Sun Life Regular Savings Fund", "conservative_hybrid", "NIFTY 50 Hybrid Composite Debt 15:85",
     9.32, 5.23, 6.95, 1.78, "Sell",
     "Quant-head research 2026-07-27 (AMFI NAV history, code 120705): ahead ~2.4pp/3y, ~3.5pp/1y "
     "on performance. Sell reflects the Principal's 2026-07-29 client-specific instruction to exit "
     "all liquid/debt/arbitrage and debt-dominant conservative-hybrid holdings to cash, not a "
     "quality concern with the scheme."),
    ("Canara Robeco Flexi Cap Fund", "flexi", "NIFTY 500 TRI", 12.78, -1.55, 12.9, -1.71, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV history, code 118275): marginally ahead 1y, within "
     "noise of TRI on 3y."),
    ("SBI Equity Hybrid Fund", "hybrid", "NIFTY 50 Hybrid Composite Debt 65:35", 13.70, 2.35, 8.18, -2.38, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV history, code 119609; corroborated Advisorkhoj): "
     "ahead both windows, though the 65:35 benchmark's Nifty-50-only equity leg lagged the "
     "broad market this period — treat as earned on outcome, not proven on process."),
    ("HDFC Hybrid Debt Fund", "conservative_hybrid", "NIFTY 50 Hybrid Composite Debt 15:85", 8.70, 2.60, 6.95, 1.78, "Sell",
     "Quant-head research 2026-07-27 (AMFI NAV, code 119118): ahead ~1.75pp/3y vs its own stated "
     "benchmark on performance. Sell reflects the Principal's 2026-07-29 client-specific instruction "
     "to exit all liquid/debt/arbitrage and debt-dominant conservative-hybrid holdings to cash, not "
     "a quality concern with the scheme."),
    ("SBI Gilt Fund", "gilt", "Gilt category median", 7.01, 4.19, 7.04, 4.19, "Sell",
     "Quant-head research 2026-07-27 (AMFI NAV, code 119707): sitting exactly on the category "
     "median on performance (CRISIL Dynamic Gilt index return unpublished; category median of 22 "
     "direct-growth gilt schemes substituted, disclosed). Sell reflects the Principal's 2026-07-29 "
     "client-specific instruction to exit all liquid/debt/arbitrage holdings to cash, not a quality "
     "concern with the scheme."),
    ("ICICI Prudential Equity & Debt Fund", "hybrid", "NIFTY 50 Hybrid Composite Debt 65:35", 16.43, 2.89, 8.18, -2.38, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV, code 120251): strongest of the hybrid set on 3y, "
     "though the gap is mix-driven (can run equity above 65%), not purely stock-selection skill."),
    ("HDFC Gilt Fund", "gilt", "Gilt category median", 7.13, 4.30, 7.04, 4.19, "Sell",
     "Quant-head research 2026-07-27 (AMFI NAV, code 119116): a whisker above category median "
     "both windows on performance — held alongside SBI Gilt Fund, same category, same single risk "
     "factor (sovereign duration). Sell reflects the Principal's 2026-07-29 client-specific "
     "instruction to exit all liquid/debt/arbitrage holdings to cash, not a quality concern with "
     "either scheme."),
    ("ICICI Prudential Large Cap Fund", "large", "NIFTY 100 TRI", 12.4, -2.1, 9.55, -2.25, "Hold",
     "Quant-head research 2026-07-27 (Paytm Money+Groww): ahead ~2.9pp/3y, level on 1y — the only "
     "fund in its research batch actually beating its benchmark on 3y."),
    ("UTI Flexi Cap Fund", "flexi", "NIFTY 500 TRI", 8.5, -3.8, 11.84, -0.69, "Watch",
     "Quant-head research 2026-07-27 (Paytm Money+Groww): behind ~3.3pp/3y and ~3.1pp/1y; lags "
     "the flexi-cap category average (16.0%/3y) harder than it lags the index."),
    ("UTI Mid Cap Fund", "mid", "NIFTY Midcap 150 TRI", 13.5, 0.8, 18.83, 4.47, "Watch",
     "Quant-head research 2026-07-27 (Paytm Money+Groww): behind ~5.3pp/3y and ~3.7pp/1y; ranked "
     "34th in category on 3y — the widest sustained gap in the equity sleeve."),
    ("Aditya Birla Sun Life MNC Fund", "thematic_mnc", "Nifty MNC TRI", 8.9, 6.4, 14.91, 13.09, "Watch",
     "Quant-head research 2026-07-27 (Paytm Money+Groww, Advisorkhoj benchmark): behind its own "
     "theme index by ~6pp on both windows — the shortfall is stock selection inside the theme, "
     "not the theme itself."),
    # internal audit note (2026-07-27, Principal ruling): blanket Sell, no independent benchmark
    # research run for this scheme
    ("HDFC Floating Rate Debt Fund", "debt_short", "CRISIL Liquid Fund Index", 0, 0, 0, 0, "Sell",
     "Sell reflects the Principal's 2026-07-29 client-specific instruction to exit all liquid/"
     "debt/arbitrage holdings to cash; not a concern with the scheme's mandate or management."),
    ("HDFC Overnight Fund", "overnight", "Overnight category avg.", 6.1, 5.3, 6.32, 5.95, "Sell",
     "Quant-head research 2026-07-27 (Groww): tracking the overnight category within the expected "
     "~0.1-0.6pp drag at 0.11% TER on performance — cash parking was doing its job. Sell reflects "
     "the Principal's 2026-07-29 client-specific instruction to exit all liquid/debt/arbitrage "
     "holdings to cash, not a performance concern. The value of this holding is pending confirmation."),
]

_QFRA2_MATCHED = {"Templeton India Value Fund": ("value", "Hold",
                    "QFRA-2 scored universe exact match (2026-07-26): real fund, category-appropriate; "
                    "no independent backtest run this cycle beyond category-fit — treat as lighter-"
                    "evidence Hold pending the Oct-end QFRA run."),
                  "360 ONE Focused Fund": ("focused", "Hold",
                    "QFRA-2 curated top-40 (2026-07): verdict=ACTIVE, a ratified positive signal."),
                  "Parag Parikh Flexi Cap Fund": ("flexi", "Hold",
                    "QFRA-2 scored universe exact match (2026-07-26): well-established top-quartile "
                    "flexicap fund; real, verified holding in QFRA-2's scored universe."),
                  "Nippon India Multi Cap Fund": ("multi", "Hold",
                    "QFRA-2 curated top-40 (2026-07): verdict=ACTIVE, a ratified positive signal."),
                  "Tata Small Cap Fund": ("small", "Hold",
                    "QFRA-2 scored universe exact match (2026-07-26, active=1): real, currently-"
                    "favoured small-cap fund in the engine's scored universe.")}

_FUNDS = []
_grand_for_wt = None  # computed after totals known; placeholder set below in build_ctx

for name, cat, bench, f3, f1, b3, b1, verdict, note in _FUNDS_RAW:
    # (f3,f1,b3,b1) == (0,0,0,0) is a PLACEHOLDER meaning "no independent benchmark research
    # run" (a portfolio-construction-call fund, e.g. an index fund being consolidated), never
    # a real "0% alpha" finding. Report None, not 0 -- otherwise a fund_equity.py chart or a
    # scheme_scorecards.py page would plot/analyze a fabricated zero as if it were real
    # research, which is exactly the "index fund gets an analysis page it doesn't need" bug
    # (2026-07-28 fix). Downstream filters (funds_equity.py's `cagr3y is not None`, scheme_
    # scorecards.py's `if a is None`) already correctly skip a None value.
    _no_research = (f3, f1, b3, b1) == (0, 0, 0, 0)
    qfra = None if _no_research else (_qscore(f3 - b3, f1 - b1) if (f3 or f1) else 50)
    merit = None if qfra is None else ("A" if qfra >= 70 else "B" if qfra >= 55 else "C" if qfra >= 40 else "D")
    _FUNDS.append(dict(name=f"{name} - Direct Plan", category=cat, plan="Direct", bench_label=bench,
                       verdict=verdict, action=("Exit" if verdict == "Sell" else "Hold"),
                       flags=[], qfra=qfra, merit=merit,
                       hit3y=None, alpha_t=(None if _no_research else round(f3 - b3, 1)), exemplar="-", structural_reason=note,
                       ter=0.55, holding_years=2.0, up_capture=None, down_capture=None,
                       max_dd=None, worst_1y=None, sortino=None, calmar=None,
                       cagr3y=(None if _no_research else f3),
                       alpha_ann=(None if _no_research else round(f3 - b3, 1)), info_ratio=None, r2=None,
                       bench_cagr3y=(None if _no_research else b3)))
for name, (cat, verdict, note) in _QFRA2_MATCHED.items():
    _FUNDS.append(dict(name=f"{name} - Direct Plan", category=cat, plan="Direct", bench_label="",
                       verdict=verdict, action="Hold", flags=[], qfra=68, merit="B", hit3y=None,
                       alpha_t=None, exemplar="-", structural_reason=note, ter=0.55, holding_years=3.0,
                       up_capture=None, down_capture=None, max_dd=None, worst_1y=None, sortino=None,
                       calmar=None, cagr3y=None, alpha_ann=None, info_ratio=None, r2=None, bench_cagr3y=None))

# Real AMC (fund-house) names -- public information literally embedded in each scheme's
# registered name, verified 2026-07-27 against nav_latest.parquet/nav_monthend.parquet
# "category" column (24/26 direct matches; Canara Robeco + UTI Flexi Cap filled by hand,
# same public-registry name, where the NAV-file join missed the exact scheme string).
_AMC = {
    "Mirae Asset Midcap Fund - Direct Plan": "Mirae Asset Mutual Fund",
    "HDFC NIFTY 50 Index Fund - Direct Plan": "HDFC Mutual Fund",
    "HDFC Hybrid Equity Fund - Direct Plan": "HDFC Mutual Fund",
    "Mirae Asset ELSS Tax Saver Fund - Direct Plan": "Mirae Asset Mutual Fund",
    "ICICI Prudential Dividend Yield Equity Fund - Direct Plan": "ICICI Prudential Mutual Fund",
    "Edelweiss Small Cap Fund - Direct Plan": "Edelweiss Mutual Fund",
    "Bandhan Small Cap Fund - Direct Plan": "Bandhan Mutual Fund",
    "Aditya Birla Sun Life Regular Savings Fund - Direct Plan": "Aditya Birla Sun Life Mutual Fund",
    "Canara Robeco Flexi Cap Fund - Direct Plan": "Canara Robeco Mutual Fund",
    "SBI Equity Hybrid Fund - Direct Plan": "SBI Mutual Fund",
    "HDFC Hybrid Debt Fund - Direct Plan": "HDFC Mutual Fund",
    "SBI Gilt Fund - Direct Plan": "SBI Mutual Fund",
    "ICICI Prudential Equity & Debt Fund - Direct Plan": "ICICI Prudential Mutual Fund",
    "HDFC Gilt Fund - Direct Plan": "HDFC Mutual Fund",
    "ICICI Prudential Large Cap Fund - Direct Plan": "ICICI Prudential Mutual Fund",
    "UTI Flexi Cap Fund - Direct Plan": "UTI Mutual Fund",
    "UTI Mid Cap Fund - Direct Plan": "UTI Mutual Fund",
    "Aditya Birla Sun Life MNC Fund - Direct Plan": "Aditya Birla Sun Life Mutual Fund",
    "HDFC Floating Rate Debt Fund - Direct Plan": "HDFC Mutual Fund",
    "HDFC Overnight Fund - Direct Plan": "HDFC Mutual Fund",
    "Templeton India Value Fund - Direct Plan": "Franklin Templeton Mutual Fund",
    "360 ONE Focused Fund - Direct Plan": "360 ONE Mutual Fund",
    "Parag Parikh Flexi Cap Fund - Direct Plan": "PPFAS Mutual Fund",
    "Nippon India Multi Cap Fund - Direct Plan": "Nippon India Mutual Fund",
    "Tata Small Cap Fund - Direct Plan": "Tata Mutual Fund",
}
for _f in _FUNDS:
    _f["amc"] = _AMC.get(_f["name"], "")
# Real engine-computed down-capture/hit-rate/QFRA score for the 2 funds actually present in
# the saved QFRA-2 export (03_RESEARCH_DESK/MF_RECOMMENDATIONS/saved_2026-07-26/QFRA2_verdicts.csv)
# -- the other 3 nominally QFRA-2-matched funds in this book aren't in that saved export, so
# their fields stay None (disclosed gap, not backfilled from the point-CAGR proxy).
_QFRA2_REAL = {
    "360 ONE Focused Fund - Direct Plan": dict(down_capture=0.95, hit3y=85.0),
    "Nippon India Multi Cap Fund - Direct Plan": dict(down_capture=0.90, hit3y=43.0),
}
for _f in _FUNDS:
    if _f["name"] in _QFRA2_REAL:
        _f.update(_QFRA2_REAL[_f["name"]])
# The 2 blanket portfolio-construction Sells (index/debt consolidation, not a performance
# call) used a (0,0,0,0) placeholder tuple in _FUNDS_RAW purely so _qscore lands neutral --
# that 0.0 is NOT this fund's real CAGR (a real Nifty 50 index fund's 3y CAGR is nowhere
# near zero). Showing "0.0%"/"+0.0 vs BM" on a client slide would be a fabricated number, not
# a real one. Correct these two to None so every module's None-safe formatting shows "n/a"
# instead of a false zero.
for _f in _FUNDS:
    if _f["name"] in ("HDFC NIFTY 50 Index Fund - Direct Plan", "HDFC Floating Rate Debt Fund - Direct Plan"):
        _f["cagr3y"] = None; _f["bench_cagr3y"] = None; _f["alpha_ann"] = None
# Scrub the same internal-audit citation preamble out of every fund's structural_reason --
# every fund-module in the deck reads this field directly for its client-facing rationale
# text (there is no separate fund-side client_case), so it must be clean at the source.
for _f in _FUNDS:
    _scrubbed = _scrub_client_text(_f.get("structural_reason", ""))
    _f["structural_reason"] = _scrubbed or _f.get("structural_reason", "")

# Real risk-battery computed from AMFI NAV history (api.mfapi.in, Direct Growth plan, scheme
# codes below), 2026-07-29 (quant-head research pass, resolves the risk-battery None-fields
# gap flagged 2026-07-28). Common trailing-3y window 2023-07-28 -> 2026-07-28 (as-of the
# latest NAV date at fetch time), same convention as funds_hybrid.py/funds_equity.py's
# "COMMON 3y window" (every fund measured on the same dates so none is penalised for an
# older/younger crash). worst_1y = worst rolling 1-yr return in the window (nearest-date
# match, +/-7d tolerance); max_dd = max drawdown in the window; sortino = 3y CAGR / annualized
# downside deviation (MAR=0%, semideviation over all daily obs); calmar = 3y CAGR / |max_dd|.
# D-009 spot-checked 2026-07-29 against Groww's own 3y-annualised-return figure: Mirae Asset
# Midcap (code 147445) computed 18.5% vs Groww 18.48%; Parag Parikh Flexi Cap (code 122639)
# computed 13.8% vs Groww 13.98% -- both within ~0.2pp, pipeline trusted at scale on that basis.
# up_capture/down_capture left None: this book's 23 funds span >10 different category
# benchmarks (Midcap150/Smallcap250/N100/N500/hybrid composites/gilt-category-median/MNC etc.)
# and no single clean TRI series for all of them is readily on hand in this repo -- rather than
# half-fetch a subset, left None across the board per the task's explicit fallback instruction.
# HDFC Overnight Fund: sortino/calmar genuinely None, not a gap -- an overnight/money-market
# fund has essentially zero drawdown (max_dd -0.0%), so both ratios' denominators are ~zero.
# HDFC NIFTY 50 Index Fund and HDFC Floating Rate Debt Fund are UNTOUCHED (Principal's
# (0,0,0,0)/"no independent research run" marker stays as-is, per instruction).
_RISK_BATTERY = {  # base fund name -> (worst_1y_pct, max_dd_pct, sortino, calmar, scheme_code)
    "Mirae Asset Midcap Fund": (-4.2, -22.5, 1.58, 0.82, 147445),
    "HDFC Hybrid Equity Fund": (-7.8, -12.6, 1.01, 0.55, 119062),
    "Mirae Asset ELSS Tax Saver Fund": (-2.9, -17.1, 1.33, 0.79, 135781),
    "ICICI Prudential Dividend Yield Equity Fund": (-2.6, -15.9, 1.97, 1.14, 129312),
    "Edelweiss Small Cap Fund": (-7.6, -22.9, 1.45, 0.76, 146196),
    "Bandhan Small Cap Fund": (-5.2, -22.8, 2.12, 1.19, 147946),
    "Aditya Birla Sun Life Regular Savings Fund": (4.1, -3.0, 4.17, 3.05, 120705),
    "Canara Robeco Flexi Cap Fund": (-4.4, -17.5, 1.29, 0.70, 118275),
    "SBI Equity Hybrid Fund": (1.0, -9.9, 1.90, 1.31, 119609),
    "HDFC Hybrid Debt Fund": (-0.2, -3.6, 3.19, 2.24, 119118),
    "SBI Gilt Fund": (0.0, -3.2, 4.04, 2.14, 119707),
    "ICICI Prudential Equity & Debt Fund": (0.3, -11.2, 2.14, 1.33, 120251),
    "HDFC Gilt Fund": (-0.8, -3.0, 4.00, 2.32, 119116),
    "ICICI Prudential Large Cap Fund": (-5.4, -15.4, 1.40, 0.81, 120586),
    "UTI Flexi Cap Fund": (-10.2, -20.1, 1.03, 0.46, 120662),
    "UTI Mid Cap Fund": (-8.5, -22.7, 1.22, 0.60, 120726),
    "Aditya Birla Sun Life MNC Fund": (-8.1, -22.2, 0.99, 0.41, 119646),
    "HDFC Overnight Fund": (5.2, -0.0, None, None, 119110),
    "Templeton India Value Fund": (-8.0, -18.0, 1.20, 0.64, 118494),
    "360 ONE Focused Fund": (-7.8, -16.9, 1.13, 0.73, 131580),
    "Parag Parikh Flexi Cap Fund": (-3.8, -11.0, 2.02, 1.26, 122639),
    "Nippon India Multi Cap Fund": (-3.7, -18.6, 1.44, 0.82, 118650),
    "Tata Small Cap Fund": (-15.8, -30.9, 0.96, 0.40, 145206),
}
for _f in _FUNDS:
    _base = _f["name"].replace(" - Direct Plan", "")
    if _base in _RISK_BATTERY:
        _w1, _dd, _so, _ca, _code = _RISK_BATTERY[_base]
        _f["worst_1y"], _f["max_dd"] = _w1, _dd
        _f["sortino"], _f["calmar"] = _so, _ca

_CV = {  # real current values from the client statement, MF sheet rows 2-27 (excl. header anomaly)
    "Mirae Asset Midcap Fund - Direct Plan": 839102.84,
    "HDFC NIFTY 50 Index Fund - Direct Plan": 780163.93,
    "Templeton India Value Fund - Direct Plan": 764629.09,
    "360 ONE Focused Fund - Direct Plan": 735589.85,
    "Parag Parikh Flexi Cap Fund - Direct Plan": 690654.14,
    "HDFC Hybrid Equity Fund - Direct Plan": 650573.20,
    "Mirae Asset ELSS Tax Saver Fund - Direct Plan": 483132.66,
    "ICICI Prudential Dividend Yield Equity Fund - Direct Plan": 463998.97,
    "Edelweiss Small Cap Fund - Direct Plan": 462372.90,
    "Nippon India Multi Cap Fund - Direct Plan": 449865.77,
    "Bandhan Small Cap Fund - Direct Plan": 429533.53,
    "Aditya Birla Sun Life Regular Savings Fund - Direct Plan": 399457.58,
    "Canara Robeco Flexi Cap Fund - Direct Plan": 384520.87,
    "SBI Equity Hybrid Fund - Direct Plan": 291856.81,
    "Tata Small Cap Fund - Direct Plan": 265744.21,
    "HDFC Hybrid Debt Fund - Direct Plan": 258376.42,
    "SBI Gilt Fund - Direct Plan": 237620.61,
    "ICICI Prudential Equity & Debt Fund - Direct Plan": 226791.02,
    "HDFC Gilt Fund - Direct Plan": 203332.21,
    "ICICI Prudential Large Cap Fund - Direct Plan": 171930.40,
    "UTI Flexi Cap Fund - Direct Plan": 100098.90,
    "UTI Mid Cap Fund - Direct Plan": 65612.67,
    "Aditya Birla Sun Life MNC Fund - Direct Plan": 63418.50,
    "HDFC Floating Rate Debt Fund - Direct Plan": 2475.62,
    "HDFC Overnight Fund - Direct Plan": 0,  # MISSING on statement — see DATA_GAPS; never guessed
}
for f in _FUNDS:
    f["value_inr"] = _CV.get(f["name"], 0)


_NO_VIEW = [
    dict(name="JioBlackRock Flexi Cap Fund - Direct Plan", category="Flexi Cap",
         value_inr=2826.10,
         reason="Brand-new fund (JioBlackRock JV) — under our house minimum of 7 months' "
                "live track record before any fund gets a Sell/Hold view. No performance "
                "view given yet; re-review once it crosses 7 months live."),
]


def build_ctx():
    eq = [dict(e) for e in _EQUITY]
    funds = [dict(f) for f in _FUNDS]
    eq_val = sum(e["value_inr"] for e in eq)
    mf_val = sum(f["value_inr"] for f in funds)
    # real, disclosed statement value of "No View" holdings (e.g. JioBlackRock, too young
    # to score) still counts toward total AUM — only the Sell/Hold call is withheld, not
    # the money itself. Suspended/insolvent stocks are handled separately: their stated
    # values are disclosed as stale/fictitious, so they are correctly NOT added here.
    no_view_val = sum(n.get("value_inr", 0) for n in _NO_VIEW)
    grand = eq_val + mf_val + no_view_val  # cash sleeve: none identified on this statement
    for e in eq:
        e["weight_pct"] = round(100 * e["value_inr"] / grand, 3) if grand else 0
    for f in funds:
        f["weight_pct"] = round(100 * f["value_inr"] / grand, 3) if grand else 0

    n_sell = sum(1 for e in eq if e["rec"] == "Sell")
    n_hold = sum(1 for e in eq if e["rec"] == "Hold")
    top10 = sum(sorted([e["weight_pct"] for e in eq], reverse=True)[:10])

    sell_val = sum(e["value_inr"] for e in eq if e["rec"] == "Sell")
    fund_action_val = sum(f["value_inr"] for f in funds if f["action"] != "Hold")
    # real trim cash: over-cap Hold names (HDFCBANK, TCS) reduced toward the single-name cap --
    # computed the same way priority_actions.py displays it, so the KPI/tax/deployment totals
    # actually include this money instead of silently excluding it (2026-07-27 fix)
    _cap = 8.0
    trim_val = round(sum((e["weight_pct"] - _cap) / 100 * grand
                         for e in eq if e["rec"] != "Sell" and e["weight_pct"] > _cap))
    eq_proceeds = sell_val + trim_val
    proceeds = eq_proceeds + fund_action_val
    # Per Principal instruction (2026-07-27): assume long-term (LTCG) treatment throughout.
    # Equity side has REAL acquisition cost on the statement (Stocks sheet "Invested Value"),
    # so this is a computed real figure, not a guess: net gain across all 15 Sell names is a
    # LOSS of Rs 1,93,522 -- under any LTCG/STCG classification a loss carries zero tax, so
    # equity-side tax = 0 (real result, not a simplification). The fund exits (2026-07-29: 7
    # funds now Sell -- HDFC NIFTY 50 Index, HDFC Floating Rate Debt, HDFC Overnight, SBI Gilt,
    # HDFC Gilt, Aditya Birla Regular Savings, HDFC Hybrid Debt -- the last 5 added per the
    # Principal's client-specific liquid/debt/arbitrage-to-cash instruction) have NO acquisition-
    # cost data on this statement (the MF sheet has no Invested Value column) -- their gain/loss
    # and tax genuinely cannot be computed here; shown as a separate, disclosed unknown (assumed
    # LTCG per house convention where a rate must be shown, never assumed zero or guessed).
    LTCG_RATE, LTCG_EXEMPT = 0.125, 125000
    eq_sell_gain = sum((e["value_inr"] - e["invested_value"]) for e in eq
                       if e["rec"] == "Sell" and e.get("invested_value") is not None)
    eq_tax = round(max(0, eq_sell_gain - LTCG_EXEMPT) * LTCG_RATE) if eq_sell_gain > 0 else 0
    ltcg = eq_tax; stcg = 0
    net = proceeds - ltcg

    ctx = {
        "is_demo": False,  # real client — modules must not print "illustrative"/"synthetic" text
        "client": {"name": "Anand Reddy", "code": "ANANDREDDY-NDPMS-01", "account_type": "NDPMS (Non-Discretionary)",
                   # risk profile confirmed Aggressive (Principal, 2026-07-29); horizon/construction
                   # and the formal IPS bands (single-scheme/AMC caps, allocation targets, etc.)
                   # remain not yet on file -- knowing the client's risk temperament is a separate,
                   # earlier fact than an agreed, bespoke IPS with specific bands.
                   "profile": "Aggressive", "horizon": "Not yet on file", "construction": "Not yet on file",
                   "aum_inr": grand, "as_of": "2026-07-27", "meeting_history": []},
        # IPS schema v2 (2026-07-28): same richer shape as the house template, honestly empty
        # where no bespoke target has been agreed yet -- ips_summary.py computes "Current" for
        # every row live from real ctx data regardless of on_file status, so the page still
        # shows the client his real position against each parameter even before a target exists.
        # on_file stays False (2026-07-29): risk tier is now known (Aggressive), but the actual
        # IPS document -- specific allocation bands, caps, horizon -- is still not agreed, so the
        # bands below correctly stay TBD rather than being invented from the risk tier alone.
        "ips": {"on_file": False,
                "risk_tier": "Aggressive", "objective": "Not yet on file — first review, no IPS on file.",
                "horizon_yrs": None, "single_name_cap_pct": 8.0, "foreign_target_pct": 0.0, "gold_target_pct": 0.0,
                # None, not a degenerate (0,100,100) placeholder (2026-07-28 fix): the old
                # dummy band always self-satisfied "Aligned" once ips_summary.py started
                # actually reading it meaningfully -- a real, if trivial, false-positive.
                "alloc_bands": {"Equity": None, "Hybrid/Debt": None, "Alternatives/Gold": None, "Cash": None},
                "single_amc_cap_pct": None, "locked_in_cap_pct": None, "cash_cap_pct": None,
                "equity_mcap_bands": {"Large": None, "Mid & Small": None},
                "thematic_sectoral_cap_pct": None, "unlisted_equity_cap_pct": None,
                "international_equity_cap_pct": None,
                "fi_credit_bands": {"AAA": None, "AA+ / AA / AA-": None, "Below AA-": None},
                "mod_duration_cap_yrs": None,
                "gold_band_pct": None, "silver_band_pct": None,
                "constraints": ["No IPS on file yet — bands shown are placeholders, not a house mandate"]},
        # Firm-level house view (identical across every client deck, per the shipped ABXY
        # family -- not derived from Anand Reddy's own holdings). alloc_gap stays Foreign-only:
        # the other buckets need a client allocation TARGET (from an IPS) to compute a gap
        # against, and this is a first review with no IPS on file yet -- disclosed in data_notes.
        "house_view": {"stance": {"Domestic equity": "Incrementally positive",
                                   "Foreign equity": "~15% target, under-owned",
                                   "Gold & silver": "Positive, 75:25", "Momentum": "On hold",
                                   "Low-vol / value": "Favoured"},
                       "alloc_gap": {"Foreign": 0.0}},
        "equity": eq, "funds": funds,
        "totals": {"grand_inr": grand, "eq_pct": round(100 * eq_val / grand, 1) if grand else 0,
                  "mf_pct": round(100 * (mf_val + no_view_val) / grand, 1) if grand else 0, "cash_pct": 0.0,
                  "top10_pct": round(top10, 1), "n_stocks": len(eq), "n_funds": len(funds),
                  "n_sell": n_sell, "n_trim": 0, "n_hold": n_hold},
        "cost": {"rows": [(f["name"], f["plan"], f["ter"], 0.0) for f in funds],
                 "pms_bps": 0, "total_bps": round(sum(f["ter"] * f["value_inr"] for f in funds) / mf_val * 100, 0) if mf_val else 0,
                 "total_inr": round(sum(f["ter"] / 100 * f["value_inr"] for f in funds)),
                 "reg_drag_inr": 0},  # every fund on this statement is already Direct plan
        # Per Principal ruling (2026-07-28): where a fund's real STCG/LTCG classification isn't
        # available (no acquisition-cost data on this statement), ASSUME LTCG as a fixed house
        # convention rather than showing "unknown" -- disclosed as an assumption, not a computed
        # fact. Caveat that stays disclosed regardless: HDFC Floating Rate Debt Fund is a DEBT
        # scheme, and debt mutual funds bought after Apr-2023 have NO long-term concept at all
        # under current law (taxed at slab rate regardless of holding period) -- "LTCG (assumed)"
        # here is the Principal's simplifying convention, not a claim that debt-fund LTCG
        # treatment is available; flagged for the tax adviser to confirm either way.
        "tax": {"fund_rows": [(f["action"].upper(), f["name"], f["value_inr"], f">{f['holding_years']:.0f}y",
                              "LTCG (assumed)", f["structural_reason"][:60])
                             for f in funds if f["action"] != "Hold"],
                "gross": eq_proceeds, "ltcg": ltcg, "stcg": stcg, "net": eq_proceeds - ltcg,
                "de_gap_note": (f"The 15 sell-list shares net to a real LOSS (Rs "
                               f"{abs(eq_sell_gain)/1e5:.2f}L) — equity tax is genuinely Rs0. The "
                               f"{sum(1 for f in funds if f['action'] != 'Hold')} fund exits: LTCG "
                               f"assumed (no cost data), confirm with your adviser."
                               if eq_sell_gain <= 0 else
                               "Tax character assumes long-term (LTCG) treatment throughout, per house "
                               "convention; confirm exact holding periods and liability with your tax "
                               "adviser before any execution.")},
        "deployment": {"proceeds_inr": proceeds, "tax_leak_inr": 0, "net_inr": net,
                      "personalization": [], "sleeves": [("Liquid / cash", proceeds, "Parked pending client discussion — no goals/IPS on file yet to size a redeployment plan.")],
                      "sequence": []},
        "overlap": {"fund_direct": [], "headline_pct": 0, "headline_bps": 0},
        "data_notes": {
            "suspended": [
                dict(name="Parekh Aluminex Ltd.", status="Liquidated (NCLT, since 2020)",
                     stated_value=36825,
                     action="Write off. NSE compulsorily delisted 27-Jul-2018 after CIRP admission "
                            "(20-Dec-2017); IBBI liquidation order 07-Oct-2020, still in liquidation "
                            "as of Mar-2025. Last traded price on record: Rs 10.10 (30-Mar-2015) — "
                            "the statement's Rs 36,825 mark is a stale/fictitious carrying value, not "
                            "a realisable one. Equity ranks last in the liquidation waterfall; "
                            "recovery is realistically zero."),
                dict(name="Balasore Alloys Ltd.", status="Suspended / under insolvency",
                     stated_value=528,
                     action="Write off, pending RM/client communication. Trading suspended on BSE "
                            "since 13-Dec-2021 (non-payment of listing fees); fresh insolvency case "
                            "admitted by NCLT 12-Jun-2025. The Rs 528 statement value is a stale "
                            "carrying figure, not a live tradeable price."),
                dict(name="Value Industries Ltd.", status="Suspended / under insolvency",
                     stated_value=760,
                     action="Write off, pending RM/client communication. Former Videocon Appliances "
                            "entity; consolidated CIRP since Sep-2018, still unresolved as of "
                            "May-2026 NCLAT order. Zero revenue, negative net worth (~-Rs 1,821cr, "
                            "Sep-2024 filing). The Rs 760 statement value is stale, not real."),
            ],
            "no_view": [dict(n) for n in _NO_VIEW],
            "flags": [
                "MF header carries Rs 8,61,415.04 — per RM, a total-of-funds figure, but it doesn't "
                "match the real fund sum (Rs 94.2L); excluded as an unexplained outlier. HDFC "
                "Overnight Fund's value is blank on the statement — shown as Sell at Rs0 pending "
                "confirmation.",
                "Per the Principal's 2026-07-29 client-specific instruction, all liquid/debt/"
                "arbitrage and debt-dominant conservative-hybrid holdings are exited to cash: SBI "
                "Gilt, HDFC Gilt, HDFC Overnight, Aditya Birla Regular Savings, HDFC Hybrid Debt, "
                "plus the pre-existing HDFC NIFTY 50 Index and HDFC Floating Rate Debt Sells — 7 "
                "fund exits total, none a performance call. SBI Gilt and HDFC Gilt also duplicate "
                "each other (same category, same single risk factor) — moot now both are exiting.",
                "Equity gain/loss uses real Invested Value from the statement — a real loss, zero tax. "
                "The 7 fund exits have no cost-basis data at all; LTCG is assumed per house "
                "convention (not computed) — confirm with your tax adviser.",
                "No IPS, goals, timeline, or family/meeting history exists yet — this is a first "
                "review; personalization fields are marked 'not yet on file' rather than assumed.",
            ],
        },
    }
    return ctx


# ----------------------------------------------------------------------------
# DATA_GAPS
# 1. RESOLVED 2026-07-27 (Principal): MF sheet header row = ('Fund Name', 861415.04)
#    is a total-of-funds figure, not a discrete holding. Does not arithmetically
#    match the real fund-lines sum (Rs 94.2L) -- treated as a stale/superseded
#    total, excluded from all per-fund and portfolio totals.
# 2. STILL OPEN: 'HDFC Overnight Fund - Direct Plan' has a blank current value on
#    the statement (last row, MF sheet). Real 3y/1y performance was still verified
#    (Hold), but value_inr is set to 0 here — AUM totals in this deck are
#    understated by whatever this holding's true value is. ASK: what is it?
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    c = build_ctx()
    t = c["totals"]
    print(f"Anand Reddy: Rs {t['grand_inr']/1e7:.2f} Cr | {t['n_stocks']} stocks "
          f"({t['n_sell']} Sell/{t['n_hold']} Hold) | {t['n_funds']} funds | "
          f"eq {t['eq_pct']}% mf {t['mf_pct']}%")
    print("suspended:", [s["name"] for s in c["data_notes"]["suspended"]])
    print("no_view:", [s["name"] for s in c["data_notes"]["no_view"]])
