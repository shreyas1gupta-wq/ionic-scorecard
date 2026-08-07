# -*- coding: utf-8 -*-
"""AZBY Family — synthetic NDPMS demo dataset for the v9 template.
[ILLUSTRATIVE — fully fictional demo client; equity SCORES + rationale are real (from our scored
universe) but the HOLDINGS/WEIGHTS are synthetic; the mutual funds are entirely synthetic, with
NAV series engineered to trigger the SENTINEL flags. Nothing here is a real client or a fund call.]

build_ctx() -> dict  is THE data contract every module renderer reads. Schema (top-level keys):
  client   : {name, account_type, profile, horizon, construction, aum_inr, as_of, code}
  ips      : {risk_tier, objective, horizon_yrs, alloc_bands{asset:(min,tgt,max)}, single_name_cap_pct,
              constraints[list], foreign_target_pct, gold_target_pct}   # illustrative
  house_view : {sector_bands{sector:(lo,hi)}, alloc_gap{bucket:signed_pct}, stance{dim:text}}
  equity   : [ {symbol,name,sector,weight_pct,value_inr,ionic_score,score_3y,score_1y,pe,roe,mcap_band,
                rec('Sell'/'Trim'/'Hold'),reason_category,binding_trigger,analyst_read,growth_pct,
                summary,positive,negative,reverse_dcf,detailed,escalation,pit_date,conviction} ]
  funds    : [ {name,amc,category('equity'/'hybrid'/'passive'),plan('Regular'/'Direct'),weight_pct,
                value_inr,qfra,merit,verdict,action,flags[list],up_capture,down_capture,hit3y,alpha_ann,
                alpha_t,info_ratio,r2,sortino,calmar,max_dd,worst_1y,cagr3y,nav(list[float]),
                exemplar,structural_reason,ter} ]
  totals   : {eq_pct,mf_pct,cash_pct,grand_inr,top10_pct,n_stocks,n_funds,n_sell,n_trim,n_hold}
  cost     : {rows[(scheme,plan,ter_dir_bps,drag_bps)],pms_bps,total_bps,total_inr,reg_drag_inr}
  tax      : {fund_rows[(action,scheme,amt_inr,holding,character,note)],gross,ltcg,stcg,net,de_gap_note}
  deployment : {proceeds_inr,tax_leak_inr,net_inr,sleeves[(name,amt_inr,rationale)],sequence[list]}
  overlap  : {fund_direct[(stock,direct_pct,via_funds_pct,n_funds)], headline_pct, headline_bps}
"""
import os, re, csv, json, glob, sys
import numpy as np

_PRT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PRT not in sys.path:
    sys.path.insert(0, _PRT)
from lib import mf_sell_gates  # Layer-1 debt-grandfather gate + churn/priority (FM #19/#21/#25)


def _tax_character(f):
    """Tax character from actual holding age (case bug fixed 2026-07-26: uppercase action
    codes never matched ('Switch','Exit'), so every row printed 'STCG likely')."""
    if f["action"].upper() == "REDEEM":
        return "Mixed, lot-by-lot"
    return "LTCG" if f.get("holding_years", 0) >= 1 else "STCG likely"

RESULTS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
RESULTS = os.path.abspath(RESULTS)

# ---- reason taxonomy mapping from analyst text (fixed client-facing categories) ----
# negated mentions ('no governance red flags') must not trip a bucket — RELIANCE was
# tagged forensic off its own PRO-Hold sentence (CEO sweep 2026-07-26)
_NEG_RE = re.compile(r"\bno [^.;]{0,70}?(?:red flags?|concerns?|breaks?|flags?)")

# buckets scored by keyword-hit COUNT, not first match — first-match let one incidental
# 'net debt' line outrank five quality mentions (RELIANCE/HINDUNILVR misfiled 2026-07-26).
# 'growth' alone is excluded: it counts stat mentions ('PAT growth +156%'), not the thesis.
_BUCKETS = [
    ("Balance-sheet strain", ("leverage", "debt", "interest cover", "balance sheet", "distress")),
    ("Rich valuation, thin margin of safety",
     ("valuation", "expensive", "priced", "multiple", "rich", "x trailing", "pe ")),
    ("Quality below peers", ("quality", "roce", "roe below", "margin")),
    ("Slowing growth", ("decelerat", "slowing", "slowdown", "guidance cut", "fell short")),
]

def _reason_category(q):
    def scan(txt):
        txt = _NEG_RE.sub(" ", (txt or "").lower())
        if not txt.strip():
            return None
        # a real (non-negated) forensic mention always wins, whatever else the text says
        if any(w in txt for w in ("forensic", "governance", "fraud", "pledge", "related-party")):
            return "Forensic / governance flag"
        counts = [(sum(txt.count(w) for w in ws), i, label) for i, (label, ws) in enumerate(_BUCKETS)]
        best = max(counts, key=lambda c: (c[0], -c[1]))   # most hits; severity order breaks ties
        return best[2] if best[0] > 0 else None
    # the sell case (negative_para) decides first; the mixed pro/con rationale is fallback only
    return (scan(q.get("negative_para", "")) or scan(q.get("recommendation_rationale", ""))
            or "Weaker forward risk-reward")

def _mcap_band(mc):
    try:
        mc = float(mc)
    except Exception:
        return "Large"
    if mc >= 100000: return "Large"
    if mc >= 30000: return "Large"
    if mc >= 10000: return "Mid"
    if mc >= 3000: return "Small"
    return "Micro"

# ---- AZBY equity book: (symbol, weight%) — synthetic weights; 2 concentrated, a few clutter ----
_EQUITY_WEIGHTS = [
    ("RELIANCE", 12.4), ("TITAN", 11.3), ("BAJFINANCE", 5.2), ("HDFCBANK", 4.6), ("ICICIBANK", 4.1),
    ("TATAPOWER", 3.4), ("SBIN", 3.1), ("SUNPHARMA", 2.8), ("BHARTIARTL", 2.7), ("M&M", 2.5),
    ("ITC", 2.4), ("LT", 2.2), ("TATASTEEL", 2.0), ("HINDALCO", 1.8), ("MARUTI", 1.7),
    ("JIOFIN", 1.6), ("DEEPAKNTR", 1.5), ("PIDILITIND", 1.4), ("ABB", 1.3), ("SIEMENS", 1.2),
    ("BHEL", 1.1), ("POWERINDIA", 1.0), ("GAIL", 0.9), ("CIPLA", 0.9), ("APLAPOLLO", 0.8),
    ("PERSISTENT", 0.8), ("COCHINSHIP", 0.7), ("HINDCOPPER", 0.6), ("TATATECH", 0.6), ("BOSCHLTD", 0.5),
    ("NATIONALUM", 0.5), ("MOTHERSON", 0.4), ("VBL", 0.4), ("ULTRACEMCO", 0.3), ("BANDHANBNK", 0.22),
    ("IRCTC", 0.18), ("ITCHOTELS", 0.12), ("CMSINFO", 0.10),
    # CEO case-study expansion (2026-07-25): +9 scored names for a fuller, real-feeling book
    ("TCS", 2.1), ("INFY", 1.6), ("HINDUNILVR", 1.4), ("BEL", 1.0), ("SCHAEFFLER", 0.7),
    ("SUZLON", 0.6), ("DIXON", 0.35), ("ETERNAL", 0.28), ("ANANDRATHI", 0.15),
]

def _load_quant():
    d = {}
    with open(os.path.join(RESULTS, "portfolio_quant.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["symbol"]] = r
    return d

def _fnum(v, dflt=None):
    try: return float(v)
    except Exception: return dflt

def _load_client_cases():
    """Optional analyst-authored two-line sell cases (client_cases.json beside this file):
    {SYMBOL: two_liner}. Written by the 90%-recheck pass; overrides the auto-clip."""
    p = os.path.join(os.path.dirname(__file__), "client_cases.json")
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def _equity(grand_inr):
    quant = _load_quant()
    cases = _load_client_cases()
    out = []
    for sym, wt in _EQUITY_WEIGHTS:
        qp = os.path.join(RESULTS, f"pf_qual_{sym}.json")
        q = json.load(open(qp, encoding="utf-8")) if os.path.exists(qp) else {}
        row = quant.get(sym, {})
        f3 = _fnum(row.get("final_3y_adj"), 50.0); f1 = _fnum(row.get("final_1y_adj"), 50.0)
        ionic = round(0.6 * f3 + 0.4 * f1, 1)
        rec = q.get("your_recommendation", "Hold")
        out.append({
            "symbol": sym, "name": (q.get("symbol") and row.get("Company Name")) or row.get("Company Name") or sym,
            "sector": (row.get("sector") or "").title() or "Diversified",
            "weight_pct": wt, "value_inr": round(grand_inr * wt / 100),
            "ionic_score": ionic, "score_3y": round(f3, 1), "score_1y": round(f1, 1),
            "pe": _fnum(row.get("pe_current")), "roe": (_fnum(row.get("roe")) or 0) * 100,
            "mcap_band": _mcap_band(row.get("market_cap_approx")),
            "rec": rec, "reason_category": _reason_category(q) if rec == "Sell" else "",
            # check_method.py's sell-bar gate (commit a032743): a quality Sell scoring >=40 needs
            # an explicit, evidenced exceptional override. sell_list.py already renders this exact
            # condition (ionic_score>=40) as its "EXCEPTIONAL" chip -- this carries the same fact,
            # plus the analyst's own evidence, into ctx so the gate sees what the page already
            # shows. Never a blanket True: empty/None whenever the condition doesn't hold.
            "exceptional_override": (q.get("negative_para") or q.get("summary") or "")[:160].strip()
                                     if (rec == "Sell" and ionic >= 40) else None,
            "binding_trigger": (q.get("summary", "")[:130]) if rec == "Sell" else "",
            "analyst_read": (q.get("summary", "") or "").split(". ")[0][:150],
            "growth_pct": q.get("expected_next_3y_growth_pct"),
            "summary": q.get("summary", ""), "positive": q.get("positive_para", ""),
            "negative": q.get("negative_para", ""), "reverse_dcf": q.get("reverse_dcf_judgment", ""),
            "client_case": cases.get(sym),
            "detailed": q.get("detailed_rationale", ""), "escalation": bool(q.get("escalation_flag")),
            "pit_date": "2026-07-21",
            "conviction": "Core" if (ionic >= 58 and wt >= 2) else ("Watch" if rec == "Hold" else "Exit"),
        })
    return out

# ---- benchmark-relative NAV generator (capture ratios come out realistic) ----
def _bench_rets(days, mu_ann=0.13, vol_ann=0.15, seed=99):
    rng = np.random.default_rng(seed)
    return rng.normal(mu_ann / 252.0, vol_ann / np.sqrt(252.0), days)

def _make_fund_nav(rb, up_beta, down_beta, alpha_ann, idio_vol, seed=1):
    """Fund daily return = alpha + up_beta*max(bench,0) + down_beta*min(bench,0) + idiosyncratic noise.
    up_beta/down_beta directly set the up/down capture; alpha_ann in %/yr; idio_vol annualised."""
    rng = np.random.default_rng(seed)
    a = alpha_ann / 100.0 / 252.0
    noise = rng.normal(0, idio_vol / np.sqrt(252.0), len(rb))
    rf = a + np.where(rb >= 0, up_beta * rb, down_beta * rb) + noise
    return list(100 * np.cumprod(1 + rf))

def _metrics_from_nav(nav, bench):
    nav = np.asarray(nav); bench = np.asarray(bench)
    rf = nav[1:] / nav[:-1] - 1; rb = bench[1:] / bench[:-1] - 1
    up = rb > 0; dn = rb < 0
    up_cap = (rf[up].mean() / rb[up].mean() * 100) if up.any() and rb[up].mean() else 100
    dn_cap = (rf[dn].mean() / rb[dn].mean() * 100) if dn.any() and rb[dn].mean() else 100
    peak = np.maximum.accumulate(nav); max_dd = float((nav / peak - 1).min() * 100)
    w = 252
    roll = (nav[w:] / nav[:-w] - 1) * 100 if len(nav) > w else np.array([0.0])
    worst = float(roll.min())
    downside = rf[rf < 0]
    sortino = float(rf.mean() / (downside.std() + 1e-9) * np.sqrt(252)) if downside.size else 0.0
    cagr = float((nav[-1] / nav[0]) ** (252 / len(nav)) - 1) * 100
    calmar = cagr / (abs(max_dd) + 1e-9)
    excess = rf - rb
    ir = float(excess.mean() / (excess.std() + 1e-9) * np.sqrt(252))
    alpha_ann = float(excess.mean() * 252 * 100)
    r2 = float(np.corrcoef(rf, rb)[0, 1] ** 2)
    return dict(up_capture=round(up_cap, 1), down_capture=round(dn_cap, 1), max_dd=round(max_dd, 1),
                worst_1y=round(worst, 1), sortino=round(sortino, 2), calmar=round(calmar, 2),
                cagr3y=round(cagr, 1), info_ratio=round(ir, 2), alpha_ann=round(alpha_ann, 1), r2=round(r2, 3))

# ---- ACE-MF-shaped synthetic fields (2026-08-06, FM comments #2/#9/#10/#22) ----
# ABXY's funds are entirely fictional (no real ISIN), so they cannot be joined to the real ACE
# extract row for row. These fields use the SAME names/semantics `lib/acemf.py` produces for a
# real client (equity_gross_pct, sector_alloc, ytm_pct, mod_duration_yrs, rating_alloc) so wiring
# a real client through the ACE loader later is a drop-in, not a rename. Where a real published
# figure exists it is used (hybrid equity-gross medians below, cited); everything else is a
# seeded, deterministic illustrative value -- never a hand-typed magic number repeated flat
# across funds (the "never default a categorical field to one hardcoded value" lesson).
_SECTOR_POOL = ["Financial Services", "Information Technology", "Energy", "Healthcare",
                "Consumer Goods", "Automobile", "Industrials", "Materials"]

# Hybrid sub-category equity-gross medians, ACE MF Advisory V2 (30-Jun-2026 block), Direct-plan
# hybrid rows -- 05_DATA_OFFICE/ACEMF_VERIFICATION_2026-08-05.md. Matched by keyword since this
# book's own `category` field ("hybrid") is coarser than ACE's sub-category label.
_ACE_HYBRID_EQUITY_MEDIAN = [("Balanced Advantage", 70.1), ("Multi-Asset", 66.5), ("Multi Asset", 66.5)]

# Debt-sell inputs (FM #22): YTM / modified duration / rating buckets for the two DEBT-category
# funds added below. LIC MF Short Term Debt's YTM is deliberately None -- ACE's real Direct-debt
# coverage is only 2,529 of 4,486 rows (56%); this demo carries one fund WITH and one WITHOUT so
# the "show the gap, never a blank that reads as zero" rule has something real to render.
_ACE_DEBT_INPUTS = {
    "HDFC Corporate Bond Fund (Direct)": {"ytm_pct": 7.42, "mod_duration_yrs": 4.1,
                                          "rating_alloc": {"AAA": 82.0, "AA+": 10.0, "SOV": 8.0}},
    "LIC MF Short Term Debt Fund": {"ytm_pct": None, "mod_duration_yrs": 1.6,
                                    "rating_alloc": {"AAA": 64.0, "AA": 24.0, "Unrated": 12.0}},
}

# Purchase dates (FM #19/#21): case-by-case from the holding statement, per the Principal --
# present here for the two new debt funds only, to exercise both the pre-Apr-2023 grandfather
# gate and the STCG-low-priority rule; every OTHER fund in this book has no purchase_date on
# file, which is the graceful-degradation path (proceed on holding_years alone, no date claim).
_PURCHASE_DATE = {
    "HDFC Corporate Bond Fund (Direct)": "2021-03-15",   # pre-1-Apr-2023: grandfathered
    "LIC MF Short Term Debt Fund": "2026-02-01",          # <1y before as_of: STCG
}


def _ace_equity_gross_pct(name, cat, seed):
    """Per-fund GROSS equity % in the ACE sense (Principal ruling: gross, no netting). None only
    when there is truly no equity-sleeve figure on file; a real 0.0 for a debt fund is data,
    not a gap, and must be told apart from None downstream (lib/lookthrough.py does)."""
    rng = np.random.default_rng(seed + 500)
    if cat in ("equity", "passive"):
        return round(float(rng.uniform(95.0, 99.0)), 1)
    if cat == "hybrid":
        med = 70.1  # Balanced Advantage median -- the modal hybrid sub-category if unmatched
        for kw, m in _ACE_HYBRID_EQUITY_MEDIAN:
            if kw.lower() in name.lower():
                med = m; break
        return round(med + float(rng.uniform(-2.0, 2.0)), 1)
    if cat == "debt":
        return 0.0
    return None


def _ace_sector_alloc(equity_pct, seed):
    """Illustrative per-fund sector split (ACE's real block carries 44 named sectors/fund) that
    sums to the fund's own equity_gross_pct. None when there is no equity sleeve to allocate,
    so combined_sector_exposure() correctly reads that as zero-contribution, not a coverage gap."""
    if not equity_pct or equity_pct <= 0.5:
        return None
    rng = np.random.default_rng(seed + 700)
    w = rng.dirichlet(np.ones(len(_SECTOR_POOL)))
    return {sec: round(equity_pct * float(x), 1) for sec, x in zip(_SECTOR_POOL, w) if x > 0.03}


def _ace_fields(name, cat, seed):
    eqp = _ace_equity_gross_pct(name, cat, seed)
    rng = np.random.default_rng(seed + 900)
    if eqp is None:
        debt = others = None
    elif cat == "debt":
        others = round(float(rng.uniform(2.0, 5.0)), 1)
        debt = round(100.0 - others, 1)
    else:
        others = round(float(rng.uniform(1.0, 3.0)), 1)
        debt = round(max(0.0, 100.0 - eqp - others), 1)
    debt_inputs = _ACE_DEBT_INPUTS.get(name, {"ytm_pct": None, "mod_duration_yrs": None, "rating_alloc": None})
    return {
        "equity_gross_pct": eqp, "debt_pct": debt, "others_pct": others,
        "sector_alloc": _ace_sector_alloc(eqp, seed),
        "purchase_date": _PURCHASE_DATE.get(name),
        **debt_inputs,
    }


def _funds(grand_inr):
    D = 1000
    rmkt = _bench_rets(D, seed=99)                 # broad-market factor (NIFTY 500 class)
    rng_b = np.random.default_rng(7)
    rbond = rng_b.normal(0.07 / 252.0, 0.015 / np.sqrt(252.0), D)
    # per-category SEBI benchmarks (Principal 2026-07-26): every scheme is measured against
    # ITS OWN category benchmark, never one common index — mirrors the desk engine, which
    # reads each category sheet's declared benchmark (see qfra1-rerun skill)
    BENCH = {
        "NIFTY 100 TRI":                   rmkt * 0.95,
        "NIFTY 500 TRI":                   rmkt,
        "NIFTY Multicap 50:25:25 TRI":     rmkt * 1.03,
        "NIFTY Midcap 150 TRI":            rmkt * 1.10,
        "NIFTY Smallcap 250 TRI":          rmkt * 1.18,
        "NIFTY 50 TRI":                    rmkt * 0.97,
        "NIFTY 50 Hybrid Composite 65:35": rmkt * 0.65 + rbond,
        "NIFTY Composite Debt Index":      rbond,
    }
    BENCH_NAV = {k: list(100 * np.cumprod(1 + v)) for k, v in BENCH.items()}
    EQNAV = BENCH_NAV["NIFTY 500 TRI"]
    specs = [
        # name, amc, cat, bench, plan, wt%, seed, up_beta, down_beta, alpha_ann, idio, hit3y, flags, verdict, action, exemplar, structural
        # hybrids/passive are GENERATED against their own benchmark (betas mean 'vs own BM');
        # equity funds are generated against the market factor, measured vs their category BM
        # verified vs MF Dashboard 'large' sheet (as of 2025-01-31): 3y -5.0pp / 5y -4.3pp vs
        # NIFTY 100, 6M dcap 1.04 vs ucap 0.97 — but r2(3y)=0.77, NOT a closet indexer.
        # CLOSET_INDEX claim removed (recheck-all-funds pass, 2026-07-25).
        ("LIC MF Large Cap Fund", "LIC MF", "equity", "NIFTY 100 TRI", "Regular", 6.0, 11, 0.97, 1.04, -1.6, 0.100, 34,
         ["NEG_ALPHA", "DOWN_CAP_HI"], "Switch", "SWITCH",
         "a low-cost Large-Cap Index / Factor fund",
         "Trails the large-cap index by 4-5pp a year over 3 and 5 years; active fees for below-index outcomes."),
        # Principal 2026-07-26: LIC Flexi (Regular, Switch) REPLACED by HDFC Flexi Cap held
        # DIRECT and rated Hold — the real fund's record supports the Hold (top-quartile
        # flexi over 3y/5y, ahead of NIFTY 500); betas tuned so the synthetic lands near
        # +4-5pp vs index, not a fake bar.
        ("HDFC Flexi Cap (Direct)", "HDFC", "equity", "NIFTY 500 TRI", "Direct", 4.5, 24, 1.00, 0.98, 3.0, 0.045, 71,
         [], "Hold", "HOLD", "-", ""),
        # verified vs 'multi' sheet: launched Nov-2022, 1y +9.8pp vs benchmark — performance is
        # FINE; the Switch is purely structural (SEBI 25/25/25 floor), which is what the card says.
        ("LIC MF Multi Cap Fund", "LIC MF", "equity", "NIFTY Multicap 50:25:25 TRI", "Regular", 3.5, 13, 1.02, 1.00, 0.6, 0.055, 52,
         ["MANDATE_RIGIDITY"], "Switch", "SWITCH",
         "a Flexi-Cap (manager-flexible cap mix)", "Multi-cap's SEBI 25/25/25 floor forces small/mid we prefer to size ourselves — structural, not performance."),
        # Principal 2026-07-26: now held in the DIRECT plan and rated Hold — the real fund's
        # record is strong (category leader among multi-asset), and in Direct there is no
        # structural issue left; no performance claim beyond what the record supports.
        # betas vs the hybrid composite (own BM): ahead of benchmark with a real cushion
        ("ICICI Pru Multi-Asset (Direct)", "ICICI Pru", "hybrid", "NIFTY 50 Hybrid Composite 65:35", "Direct", 4.0, 14, 1.02, 0.95, 1.2, 0.035, 64,
         [], "Hold", "HOLD", "-", ""),
        # underperformer example verified against real data (MF Dashboard 'small' sheet,
        # as of 2025-01-31): PGIM 3y CAGR 9.1% vs index 17.3% (worst in category).
        # NEVER use a strong real fund (e.g. Bandhan Small Cap: 3y rank 1/23, 5y 2/21,
        # +7-9pp over index) as a demo Sell — Principal flagged this twice.
        ("PGIM India Small Cap Fund", "PGIM India", "equity", "NIFTY Smallcap 250 TRI", "Direct", 0.45, 15, 1.12, 1.26, -0.5, 0.120, 44,
         ["DEEP_DD", "NEG_ALPHA", "OVER_ALLOC"], "Exit", "EXIT",
         "the primary small-cap sleeve already held", "Sub-scale ~3L beside a larger small-cap fund; persistent underperformance and duplication — structural exit."),
        # web-checked 2026-07-25 (mstock / INDmoney / PaytmMoney): since-launch (Nov-2021)
        # ~9.4-9.8% CAGR and AHEAD of its hybrid benchmark over 1y/3y — the old DOWN_CAP_HI +
        # DEEP_DD framing was NOT supported and is removed. Verifiable weaknesses used instead:
        # AUM ~Rs 761 cr (May-2025, sub-scale) and a track record under 4 years.
        # vs own hybrid BM: modestly ahead (real record: ahead since launch) — Trim stays structural
        ("LIC MF Balanced Advantage", "LIC MF", "hybrid", "NIFTY 50 Hybrid Composite 65:35", "Regular", 3.0, 16, 1.02, 0.96, 0.6, 0.035, 48,
         ["SUB_SCALE", "SHORT_RECORD", "REG_PLAN_DRAG"], "Trim", "TRIM",
         "the hybrid core already held (HDFC BAF, Direct)",
         "Under four years of record, sub-scale, Regular plan; we fold the sleeve into the proven hybrid held."),
        # --- genuine Holds so the book isn't all-Sell ---
        # betas tuned so the synthetic 3y CAGR lands near the real fund's +4-5pp vs index
        # (a 56% CAGR bar reads as fake and poisons the page's credibility)
        ("Parag Parikh Flexi Cap (Direct)", "PPFAS", "equity", "NIFTY 500 TRI", "Direct", 7.5, 21, 0.98, 0.98, 1.6, 0.040, 74,
         [], "Hold", "HOLD", "-", ""),
        ("Nippon India Nifty 50 Index (Direct)", "Nippon", "passive", "NIFTY 50 TRI", "Direct", 4.0, 22, 1.00, 1.00, -0.2, 0.004, 55,
         [], "Hold", "HOLD", "-", ""),
        # vs own hybrid BM: the proven cushion core — clearly ahead with a strong down-capture
        ("HDFC Balanced Advantage (Direct)", "HDFC", "hybrid", "NIFTY 50 Hybrid Composite 65:35", "Direct", 3.5, 23, 0.98, 0.88, 1.0, 0.035, 66,
         [], "Hold", "HOLD", "-", ""),
        # --- debt sleeve added 2026-08-06 (FM #22 debt-sell-inputs, #21 grandfather gate) ---
        # bought 2021-03-15 (see _PURCHASE_DATE): pre-1-Apr-2023, so lib/mf_sell_gates.apply()
        # forces this fund's pre-gate Trim back to Hold with a gate_note -- the concrete case
        # that exercises the debt-grandfather rule rather than leaving it untested code.
        ("HDFC Corporate Bond Fund (Direct)", "HDFC", "debt", "NIFTY Composite Debt Index", "Direct", 1.2, 31, 1.0, 1.0, 0.3, 0.015, 60,
         [], "Trim", "TRIM",
         "-", "Sub-scale allocation inside a larger corporate-bond sleeve; considered for consolidation."),
        # bought 2026-02-01 (see _PURCHASE_DATE): under a year before as_of, so this is an STCG
        # sell -- the gate does NOT apply (post-1-Apr-2023) but mf_sell_gates still marks it a
        # LOW-priority Switch, never suppressed. Also this book's YTM-coverage-gap case (#22).
        ("LIC MF Short Term Debt Fund", "LIC MF", "debt", "NIFTY Composite Debt Index", "Regular", 1.0, 32, 1.0, 1.05, -0.4, 0.018, 48,
         ["REG_PLAN_DRAG"], "Switch", "SWITCH",
         "a Direct-plan short-duration debt fund", "Regular-plan cost drag versus an equivalent Direct-plan short-duration fund; a plan switch, not a credit call."),
    ]
    # illustrative holding age (years) — drives the tax-inertia rule (Principal 2026-07-25):
    # units >5y (stronger >10y) switch only on structural grounds; stocks exempt (risk dominates tax)
    _HOLD_YRS = {"LIC MF Large Cap Fund": 9.2, "HDFC Flexi Cap (Direct)": 4.2, "LIC MF Multi Cap Fund": 2.4,
                 "ICICI Pru Multi-Asset (Direct)": 6.5, "PGIM India Small Cap Fund": 1.8,
                 "LIC MF Balanced Advantage": 2.2, "Parag Parikh Flexi Cap (Direct)": 4.6,
                 "Nippon India Nifty 50 Index (Direct)": 5.8, "HDFC Balanced Advantage (Direct)": 3.9}
    out = []
    for (name, amc, cat, bench_label, plan, wt, seed, ub, db, alpha, idio, hit3y, flags, verdict, action, exemplar, structural) in specs:
        # hybrids/passive are generated against their own benchmark; equity funds against
        # the market factor. Metrics are ALWAYS vs the scheme's own category benchmark
        # (Principal 2026-07-26: never one common index), on the same 3y window for all
        # funds (an MDD/worst-year comparison is only fair on a common window — a fund
        # launched before a crash otherwise 'loses' on inception luck).
        gen = BENCH[bench_label] if cat in ("hybrid", "passive", "debt") else rmkt
        nav = _make_fund_nav(gen, ub, db, alpha, idio, seed=seed)
        bnav = BENCH_NAV[bench_label]
        m = _metrics_from_nav(nav, bnav)
        m["bench_cagr3y"] = round(((bnav[-1] / bnav[0]) ** (252 / len(bnav)) - 1) * 100, 1)
        if cat == "hybrid":
            # the cushion story is a separate, explicitly-labeled stat vs PURE EQUITY —
            # vs its own 65:35 benchmark a hybrid's down-capture is ~100 by construction
            m["down_capture_vs_equity"] = _metrics_from_nav(nav, EQNAV)["down_capture"]
        # QFRA-style composite: reward alpha/consistency/cushion, penalize flags
        base = 55 + m["alpha_ann"] * 1.1 + (hit3y - 50) * 0.4 - max(0, m["down_capture"] - 100) * 0.5
        qfra = int(max(8, min(96, base - 10 * len([f for f in flags if f in ("CLOSET_INDEX", "NEG_ALPHA", "DEEP_DD")]))))
        merit = "A" if qfra >= 70 else ("B" if qfra >= 55 else ("C" if qfra >= 40 else "D"))
        out.append(dict(name=name, amc=amc, category=cat, bench_label=bench_label, plan=plan, weight_pct=wt,
                        value_inr=round(grand_inr * wt / 100), qfra=qfra, merit=merit, verdict=verdict,
                        action=action, flags=flags, hit3y=hit3y, alpha_t=round(m["info_ratio"] * 1.3, 2),
                        exemplar=exemplar, structural_reason=structural,
                        ter=(0.95 if plan == "Regular" else 0.55) if cat != "passive" else 0.20,
                        holding_years=_HOLD_YRS.get(name, 2.0),
                        # ACE-MF-shaped fields (#2/#9/#10/#22) + purchase-date input (#19/#21) --
                        # credit_or_governance_event is never set True here: this book has no
                        # such event on file, so the debt-grandfather gate is left free to fire.
                        credit_or_governance_event=False,
                        # monthly-resampled NAV (FM #24, 2026-08-06): the same daily series that
                        # already drives every up/down-capture and alpha number above, resampled
                        # ~21 trading days apart. A real client's equivalent is month-end NAV from
                        # the fund NAV store / ACE, keyed by ISIN -- this is that field's synthetic
                        # stand-in, not a separate invented number, so scheme_correlation.py
                        # computes a genuinely derived correlation even on this demo book rather
                        # than a hand-tuned illustrative one.
                        nav_history=[round(float(x), 4) for x in nav[::21]],
                        **_ace_fields(name, cat, seed), **m))
    return out

def build_ctx():
    grand = 68_000_000  # ~Rs 6.8 Cr
    eq = _equity(grand); funds = _funds(grand)
    # --- normalise weights to eq 60 / funds 34 / cash 6, keeping the >11% concentrated names fixed ---
    FUND_TGT, CASH_TGT = 34.0, 6.0
    fscale = FUND_TGT / sum(f["weight_pct"] for f in funds)
    for f in funds:
        f["weight_pct"] = round(f["weight_pct"] * fscale, 2); f["value_inr"] = round(grand * f["weight_pct"] / 100)
    eq_tgt = 100 - FUND_TGT - CASH_TGT
    fixed_sum = sum(e["weight_pct"] for e in eq if e["weight_pct"] >= 11)
    rest = [e for e in eq if e["weight_pct"] < 11]
    escale = (eq_tgt - fixed_sum) / sum(e["weight_pct"] for e in rest)
    for e in rest:
        e["weight_pct"] = round(e["weight_pct"] * escale, 2)
    for e in eq:
        e["value_inr"] = round(grand * e["weight_pct"] / 100)
    AS_OF = "2026-07-25"
    # Layer-1 MF sell-method gates (FM #19/#21/#25) MUST run before tax/cost/deployment below are
    # built from `funds` -- a gate-forced Hold has to be excluded from proceeds/tax the same way
    # any other Hold is, never sold in one dict and held in another.
    fund_churn = mf_sell_gates.apply_to(eq, funds, AS_OF)
    eq_val = sum(e["value_inr"] for e in eq); mf_val = sum(f["value_inr"] for f in funds)
    cash_val = grand - eq_val - mf_val
    n_sell = sum(1 for e in eq if e["rec"] == "Sell"); n_trim = sum(1 for e in eq if e["rec"] == "Trim")
    n_hold = sum(1 for e in eq if e["rec"] == "Hold")
    top10 = sum(sorted([e["weight_pct"] for e in eq], reverse=True)[:10])
    proceeds = sum(e["value_inr"] for e in eq if e["rec"] == "Sell") + \
               round(grand * 0.02)  # + a trim
    ltcg = round(proceeds * 0.11); stcg = round(proceeds * 0.015); net = proceeds - ltcg - stcg
    ctx = {
        "client": {"name": "ABXY Family", "code": "ABXY-NDPMS-DEMO", "account_type": "NDPMS (Non-Discretionary)",
                   "profile": "Aggressive", "horizon": "Long term (7yr+)", "construction": "Core–satellite",
                   "aum_inr": grand, "as_of": AS_OF},
        # IPS schema v2 (2026-07-28, "best of both worlds" — Principal reference deck +
        # our existing rail-bar visual style): richer parameter coverage (portfolio/equity/
        # fixed-income/commodities level, each with a real min-target-max or max-only band),
        # on_file=True here since this is the house-standard DEMO template; a real client
        # with on_file=False gets the same shape with "Not yet on file"/None where a bespoke
        # target hasn't been agreed yet -- ips_summary.py computes "Current" live from ctx,
        # never from a client-authored guess.
        "ips": {"on_file": True, "risk_tier": "Aggressive",
                "objective": "Long-term capital growth with a quality bias; tolerates interim drawdowns for higher compounding.",
                "horizon_yrs": 7,
                "alloc_bands": {"Equity": (65, 78, 85), "Hybrid/Debt": (5, 12, 25), "Alternatives/Gold": (0, 5, 10), "Cash": (0, 5, 15)},
                # portfolio-level caps (single_name_cap_pct kept as the canonical field name --
                # used by 7 other modules already; it covers "single scheme/instrument" exactly)
                "single_name_cap_pct": 8.0, "single_amc_cap_pct": 25.0,
                "locked_in_cap_pct": 10.0, "cash_cap_pct": 5.0,
                # equity-level parameters
                "equity_mcap_bands": {"Large": (50, 70), "Mid & Small": (30, 50)},
                "thematic_sectoral_cap_pct": 20.0, "unlisted_equity_cap_pct": None,
                "foreign_target_pct": 15.0, "international_equity_cap_pct": 25.0,
                # fixed-income parameters (not derivable from equity/fund ctx yet -- house
                # policy bands only, "Current" stays "Not tracked" until credit-quality/
                # duration data is sourced per debt holding)
                "fi_credit_bands": {"AAA": (75, 85), "AA+ / AA / AA-": (5, 15), "Below AA-": (5, 15)},
                "mod_duration_cap_yrs": 5.0,
                # commodities
                "gold_band_pct": (0, 5, 10), "silver_band_pct": (0, 2, 5),
                "constraints": ["No single stock above the single-scheme cap of the book", "Min 15% of equity in foreign/global by target",
                                "No unrated / F&O / leveraged positions", "ESG: no tobacco primary-producer adds"],
                # Seven IPS aspects (FM #5, Principal ruling 2026-08-06): "for abxy family assume
                # something best we can show" -- ABXY is the DEMO book (is_demo=True elsewhere in
                # this ctx), so an assumed value here is legitimate PROVIDED the page discloses it
                # as illustrative, never as fact on file. modules/ips_seven_aspects.py is what
                # applies that disclosure; a real client ctx simply has no "seven_aspects" key
                # until an advisor actually records one, and the module renders "on file with the
                # advisor" for every row in that case rather than inheriting these assumptions.
                "seven_aspects": {
                    "return": "Long-term capital growth ahead of inflation, pursued through the "
                              "equity-heavy mandate rather than a stated numeric return target.",
                    "risk": "Aggressive tolerance -- the mandate explicitly rides through interim "
                            "drawdowns rather than de-risking on a fall (no drawdown-triggered "
                            "de-risking is already a standing constraint on this account).",
                    "liability": "No near-term liability is funded from this account. Assumed to "
                                 "be discretionary long-term capital, not earmarked against a "
                                 "specific debt or payment.",
                    "liquidity": "Low liquidity need assumed. Cash is held at 2-8% of the book by "
                                 "band, sized for rebalancing and opportunistic deployment, not "
                                 "for near-term withdrawals.",
                    "timelines": "Ten-year investment horizon under this mandate; no interim "
                                 "milestone or drawdown date is assumed.",
                    "tax": "Assumed taxed at the top individual slab with standard equity LTCG/"
                          "STCG treatment; no exemption, loss carry-forward or NRI/trust status "
                          "is assumed.",
                    "unique": "One constraint is actually on file: no tobacco primary-producer "
                             "additions (ESG). No other family, governance or values-based "
                             "restriction is assumed.",
                }},
        "house_view": {"stance": {"Domestic equity": "Incrementally positive", "Foreign equity": "~15% target, under-owned",
                                  "Gold & silver": "Positive, 75:25", "Momentum": "On hold", "Low-vol / value": "Favoured"},
                       "alloc_gap": {"Large": 8.5, "Mid": 3.0, "Small": -1.5, "Foreign": -12.0, "Gold": -4.0, "Debt/Hybrid": 6.0}},
        "equity": eq, "funds": funds, "fund_churn": fund_churn,
        "totals": {"eq_pct": round(eq_val / grand * 100, 1), "mf_pct": round(mf_val / grand * 100, 1),
                   "cash_pct": round(cash_val / grand * 100, 1), "grand_inr": grand,
                   "top10_pct": round(top10, 1), "n_stocks": len(eq), "n_funds": len(funds),
                   "n_sell": n_sell, "n_trim": n_trim, "n_hold": n_hold},
        "cost": {"rows": [(f["name"], f["plan"], round(f["ter"] * 100),
                           round((0.95 - 0.55) * 100) if f["plan"] == "Regular" and f["category"] != "passive" else 0)
                          for f in funds],
                 "pms_bps": 120, "total_bps": 168, "total_inr": round(grand * 0.0168),
                 "reg_drag_inr": round(sum(f["value_inr"] for f in funds if f["plan"] == "Regular") * 0.004)},
        "tax": {"fund_rows": [(f["action"], f["name"], f["value_inr"],
                              "mixed" if f["action"].upper() == "REDEEM" else f">{min(f.get('holding_years', 1), 9):.0f}y",
                              _tax_character(f), f["structural_reason"][:60])
                             for f in funds if f["action"] not in ("HOLD", "Hold")],
                "gross": proceeds, "ltcg": ltcg, "stcg": stcg, "net": net,
                "de_gap_note": "The equity tax opposite is an estimate; the exact bill needs the demat trade file (buy dates + cost per lot), not in the statement provided."},
        "deployment": {"proceeds_inr": proceeds, "tax_leak_inr": ltcg + stcg, "net_inr": net,
                       "personalization": [
                           ("Education 2031", "foreign sleeve doubles as the USD hedge"),
                           ("Liquidity", "Rs 25L 12-month call met by staged cash"),
                           ("Tax posture", "5y+ fund units: structural switches only"),
                       ],
                       "sleeves": [("Low-vol / value core add", round(net * 0.45), "Closest-substitute risk profile to what's being sold; absorbs the largest share."),
                                   ("Foreign / global equity", round(net * 0.28), "Closes the ~12pt gap to the 15% foreign target — a real diversifier, not a return chase."),
                                   ("Gold & silver sleeve", round(net * 0.12), "Adds the missing 4pt vs the 5% target; 75:25 gold:silver per house view."),
                                   ("Cash (staged)", round(net * 0.15), "Held as cash until settlement; deployed on liquidity, never assumed fully invested.")],
                       "sequence": ["Execute clear-Sell names first — conviction-driven, not market-timing.",
                                    "Stage by liquidity: largest / least-liquid names sliced across days at <=10% ADV.",
                                    "Fund switches settle T+2/T+3; redeploy only settled cash.",
                                    "Trim the two >11% positions toward the 8% single-name guideline last, into strength."]},
        "overlap": {"fund_direct": [("Reliance Industries", 12.4, 2.1, 3), ("HDFC Bank", 4.6, 1.8, 4),
                                    ("ICICI Bank", 4.1, 1.6, 4), ("Infosys", 0.0, 1.9, 5), ("Titan", 11.3, 0.7, 2)],
                    "headline_pct": 8.4, "headline_bps": 78},
    }
    return ctx


if __name__ == "__main__":
    c = build_ctx()
    t = c["totals"]
    print(f"AZBY: Rs {t['grand_inr']/1e7:.2f} Cr | {t['n_stocks']} stocks ({t['n_sell']} Sell/{t['n_hold']} Hold) | "
          f"{t['n_funds']} funds | eq {t['eq_pct']}% mf {t['mf_pct']}% cash {t['cash_pct']}% | top10 {t['top10_pct']}%")
    print("fund verdicts:", [(f["name"][:22], f["verdict"], f["qfra"], f["up_capture"], f["down_capture"], f["max_dd"]) for f in c["funds"]])
    print("proceeds Rs %.2fL  net %.2fL" % (c["tax"]["gross"]/1e5, c["tax"]["net"]/1e5))
