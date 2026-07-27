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
    dict(symbol="MOVALUE", name="Motilal Oswal S&P BSE Enhanced Value ETF", sector="Passive/Factor ETF",
         value_inr=5635, ionic_score=35, score_3y=35, score_1y=35, rec="Sell", pit_date="2026-07-27",
         summary="House decision (Principal 2026-07-27): consolidate away from passive/factor-ETF "
                 "exposure held directly in this account. (Fund-level note: a genuine, low-cost "
                 "multi-factor value screen, ~0.20-0.35% TER, ~Rs147cr AUM — the Sell is a "
                 "portfolio-construction call, not a quality concern with the ETF itself.)",
         client_case="A sound, low-cost factor ETF in its own right; the Sell reflects a house call "
                     "to consolidate this account out of direct passive/factor exposure, not a "
                     "concern with the fund itself."),
    dict(symbol="MOM30IETF", name="ICICI Prudential Nifty 200 Momentum 30 ETF", sector="Passive/Factor ETF",
         value_inr=3059, ionic_score=35, score_3y=35, score_1y=35, rec="Sell", pit_date="2026-07-27",
         summary="House decision (Principal 2026-07-27): consolidate away from passive/factor-ETF "
                 "exposure held directly in this account. (Fund-level note: tracks the Nifty 200 "
                 "Momentum 30 TRI, ~0.30% TER, ~Rs656cr AUM, reasonably liquid — the Sell is a "
                 "portfolio-construction call, not a quality concern with the ETF itself.)",
         client_case="A liquid, well-tracked momentum ETF; the Sell reflects a house call to "
                     "consolidate this account out of direct passive/factor exposure, not a concern "
                     "with the fund itself."),
]
for _e in _EQUITY:
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
    ("Aditya Birla Sun Life Regular Savings Fund", "conservative_hybrid", "NIFTY 50 Hybrid Composite Debt 15:85",
     9.32, 5.23, 6.95, 1.78, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV history, code 120705): ahead ~2.4pp/3y, ~3.5pp/1y."),
    ("Canara Robeco Flexi Cap Fund", "flexi", "NIFTY 500 TRI", 12.78, -1.55, 12.9, -1.71, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV history, code 118275): marginally ahead 1y, within "
     "noise of TRI on 3y."),
    ("SBI Equity Hybrid Fund", "hybrid", "NIFTY 50 Hybrid Composite Debt 65:35", 13.70, 2.35, 8.18, -2.38, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV history, code 119609; corroborated Advisorkhoj): "
     "ahead both windows, though the 65:35 benchmark's Nifty-50-only equity leg lagged the "
     "broad market this period — treat as earned on outcome, not proven on process."),
    ("HDFC Hybrid Debt Fund", "conservative_hybrid", "NIFTY 50 Hybrid Composite Debt 15:85", 8.70, 2.60, 6.95, 1.78, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV, code 119118): ahead ~1.75pp/3y vs its own stated benchmark."),
    ("SBI Gilt Fund", "gilt", "Gilt category median", 7.01, 4.19, 7.04, 4.19, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV, code 119707): sitting exactly on the category "
     "median (CRISIL Dynamic Gilt index return unpublished; category median of 22 direct-growth "
     "gilt schemes substituted, disclosed)."),
    ("ICICI Prudential Equity & Debt Fund", "hybrid", "NIFTY 50 Hybrid Composite Debt 65:35", 16.43, 2.89, 8.18, -2.38, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV, code 120251): strongest of the hybrid set on 3y, "
     "though the gap is mix-driven (can run equity above 65%), not purely stock-selection skill."),
    ("HDFC Gilt Fund", "gilt", "Gilt category median", 7.13, 4.30, 7.04, 4.19, "Hold",
     "Quant-head research 2026-07-27 (AMFI NAV, code 119116): a whisker above category median "
     "both windows. NOTE: held alongside SBI Gilt Fund — same category, same single risk factor "
     "(sovereign duration), no credit/maturity differentiation. Genuine duplication; consolidation "
     "candidate even though both are individually Hold on performance."),
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
     "A call to consolidate the debt sleeve of this account into fewer, more liquid holdings; "
     "not a concern with the scheme's mandate or management."),
    ("HDFC Overnight Fund", "overnight", "Overnight category avg.", 6.1, 5.3, 6.32, 5.95, "Hold",
     "Quant-head research 2026-07-27 (Groww): tracking the overnight category within the expected "
     "~0.1-0.6pp drag at 0.11% TER — cash parking doing its job, not a performance thesis. NOTE: "
     "the value of this holding is MISSING from the client's statement — see DATA_GAPS."),
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
    qfra = _qscore(f3 - b3, f1 - b1) if (f3 or f1) else 50
    _FUNDS.append(dict(name=f"{name} - Direct Plan", category=cat, plan="Direct", bench_label=bench,
                       verdict=verdict, action=("Exit" if verdict == "Sell" else "Hold"),
                       flags=[], qfra=qfra, merit=("A" if qfra >= 70 else "B" if qfra >= 55 else "C" if qfra >= 40 else "D"),
                       hit3y=None, alpha_t=round(f3 - b3, 1), exemplar="-", structural_reason=note,
                       ter=0.55, holding_years=2.0, up_capture=None, down_capture=None,
                       max_dd=None, worst_1y=None, sortino=None, calmar=None, cagr3y=f3,
                       alpha_ann=round(f3 - b3, 1), info_ratio=None, r2=None, bench_cagr3y=b3))
for name, (cat, verdict, note) in _QFRA2_MATCHED.items():
    _FUNDS.append(dict(name=f"{name} - Direct Plan", category=cat, plan="Direct", bench_label="",
                       verdict=verdict, action="Hold", flags=[], qfra=68, merit="B", hit3y=None,
                       alpha_t=None, exemplar="-", structural_reason=note, ter=0.55, holding_years=3.0,
                       up_capture=None, down_capture=None, max_dd=None, worst_1y=None, sortino=None,
                       calmar=None, cagr3y=None, alpha_ann=None, info_ratio=None, r2=None, bench_cagr3y=None))

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


def build_ctx():
    eq = [dict(e) for e in _EQUITY]
    funds = [dict(f) for f in _FUNDS]
    eq_val = sum(e["value_inr"] for e in eq)
    mf_val = sum(f["value_inr"] for f in funds)
    grand = eq_val + mf_val  # cash sleeve: none identified on this statement
    for e in eq:
        e["weight_pct"] = round(100 * e["value_inr"] / grand, 3) if grand else 0
    for f in funds:
        f["weight_pct"] = round(100 * f["value_inr"] / grand, 3) if grand else 0

    n_sell = sum(1 for e in eq if e["rec"] == "Sell")
    n_hold = sum(1 for e in eq if e["rec"] == "Hold")
    top10 = sum(sorted([e["weight_pct"] for e in eq], reverse=True)[:10])

    sell_val = sum(e["value_inr"] for e in eq if e["rec"] == "Sell")
    fund_action_val = sum(f["value_inr"] for f in funds if f["action"] != "Hold")
    proceeds = sell_val + fund_action_val
    # tax lots unknown (statement has no acquisition dates) — LTCG/STCG split cannot be
    # computed; show gross only and flag the gap rather than assume a split.
    ltcg = 0; stcg = 0; net = proceeds

    ctx = {
        "is_demo": False,  # real client — modules must not print "illustrative"/"synthetic" text
        "client": {"name": "Anand Reddy", "code": "ANANDREDDY-NDPMS-01", "account_type": "NDPMS (Non-Discretionary)",
                   "profile": "Not yet on file", "horizon": "Not yet on file", "construction": "Not yet on file",
                   "aum_inr": grand, "as_of": "2026-07-27", "meeting_history": []},
        "ips": {"on_file": False,
                "risk_tier": "Not yet on file", "objective": "Not yet on file — first review, no IPS on file.",
                "horizon_yrs": None, "single_name_cap_pct": 8.0, "foreign_target_pct": 0.0, "gold_target_pct": 0.0,
                "alloc_bands": {"Equity": (0, 100, 100), "Hybrid/Debt": (0, 0, 100), "Alternatives/Gold": (0, 0, 100), "Cash": (0, 0, 100)},
                "constraints": ["No IPS on file yet — bands shown are placeholders, not a house mandate"]},
        "house_view": {"alloc_gap": {"Foreign": 0.0}},
        "equity": eq, "funds": funds,
        "totals": {"grand_inr": grand, "eq_pct": round(100 * eq_val / grand, 1) if grand else 0,
                  "mf_pct": round(100 * mf_val / grand, 1) if grand else 0, "cash_pct": 0.0,
                  "top10_pct": round(top10, 1), "n_stocks": len(eq), "n_funds": len(funds),
                  "n_sell": n_sell, "n_trim": 0, "n_hold": n_hold},
        "cost": {"rows": [(f["name"], f["plan"], f["ter"], 0.0) for f in funds],
                 "pms_bps": 0, "total_bps": round(sum(f["ter"] * f["value_inr"] for f in funds) / mf_val * 100, 0) if mf_val else 0,
                 "total_inr": round(sum(f["ter"] / 100 * f["value_inr"] for f in funds)),
                 "reg_drag_inr": 0},  # every fund on this statement is already Direct plan
        "tax": {"fund_rows": [(f["action"].upper(), f["name"], f["value_inr"], f">{f['holding_years']:.0f}y",
                              "Unknown — no acquisition date on statement", f["structural_reason"][:60])
                             for f in funds if f["action"] != "Hold"],
                "gross": proceeds, "ltcg": ltcg, "stcg": stcg, "net": net,
                "de_gap_note": "Tax character (LTCG/STCG) unknown — no acquisition dates on this "
                               "statement. Confirm from demat/CAS records before any execution."},
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
            "no_view": [
                dict(name="JioBlackRock Flexi Cap Fund - Direct Plan", category="Flexi Cap",
                     reason="Brand-new fund (JioBlackRock JV) — under our house minimum of 7 months' "
                            "live track record before any fund gets a Sell/Hold view. No performance "
                            "view given yet; re-review once it crosses 7 months live."),
            ],
            "flags": [
                "Two unresolved data points on the client's statement, excluded rather than guessed: "
                "(1) the MF sheet's header row carries a stray value (Rs 8,61,415.04) that does not "
                "match any fund name on the statement — needs RM/client confirmation before it can "
                "be assigned; (2) HDFC Overnight Fund's current value is blank on the statement — "
                "shown here with a Hold view but zero value until confirmed.",
                "Two SBI/HDFC Gilt Fund holdings are genuine duplication — same category (dynamic "
                "gilt), same single risk factor (sovereign duration), no credit/maturity "
                "differentiation; consolidation candidate even though both are individually Hold.",
                "No tax-lot / acquisition-date data exists on this statement for any holding — LTCG/"
                "STCG character cannot be computed; the tax-impact figures show gross proceeds only.",
                "No IPS, goals/timeline, family structure, or meeting history exists yet for this "
                "client — this is a first review; all personalization fields are marked 'not yet on "
                "file' rather than assumed.",
            ],
        },
    }
    return ctx


# ----------------------------------------------------------------------------
# DATA_GAPS — do not resolve these by guessing; they need the Principal/RM.
# 1. MF sheet header row = ('Fund Name', 861415.04) — 861,415.04 does not match
#    any fund's value on the statement under any row-shift hypothesis tested.
#    Excluded from all totals. ASK: what does this number represent?
# 2. 'HDFC Overnight Fund - Direct Plan' has a blank current value on the
#    statement (last row, MF sheet). Real 3y/1y performance was still verified
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
