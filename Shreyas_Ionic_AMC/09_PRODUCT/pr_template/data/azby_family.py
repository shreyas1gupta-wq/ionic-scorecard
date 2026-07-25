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
import os, csv, json, glob
import numpy as np

RESULTS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
RESULTS = os.path.abspath(RESULTS)

# ---- reason taxonomy mapping from analyst text (fixed client-facing categories) ----
def _reason_category(q):
    esc = q.get("escalation_flag")
    txt = (q.get("negative_para", "") + " " + q.get("recommendation_rationale", "")).lower()
    if any(w in txt for w in ("forensic", "governance", "fraud", "pledge", "related-party")):
        return "Forensic / governance flag"
    if any(w in txt for w in ("leverage", "debt", "interest cover", "balance sheet", "distress")):
        return "Balance-sheet strain"
    if any(w in txt for w in ("valuation", "expensive", "priced", "multiple", "rich", "x trailing", "pe ")):
        return "Rich valuation, thin margin of safety"
    if any(w in txt for w in ("quality", "roce", "roe below", "margin")):
        return "Quality below peers"
    if any(w in txt for w in ("growth", "decelerat", "slowing", "soft")):
        return "Slowing growth"
    return "Weaker forward risk-reward"

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

def _equity(grand_inr):
    quant = _load_quant()
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
            "binding_trigger": (q.get("summary", "")[:130]) if rec == "Sell" else "",
            "analyst_read": (q.get("summary", "") or "").split(". ")[0][:150],
            "growth_pct": q.get("expected_next_3y_growth_pct"),
            "summary": q.get("summary", ""), "positive": q.get("positive_para", ""),
            "negative": q.get("negative_para", ""), "reverse_dcf": q.get("reverse_dcf_judgment", ""),
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

def _funds(grand_inr):
    D = 1000
    rb = _bench_rets(D, seed=99); bench = list(100 * np.cumprod(1 + rb))
    specs = [
        # name, amc, cat, plan, wt%, seed, up_beta, down_beta, alpha_ann, idio, hit3y, flags, verdict, action, exemplar, structural
        ("LIC MF Large Cap Fund", "LIC MF", "equity", "Regular", 6.0, 11, 0.99, 1.00, -1.8, 0.020, 34,
         ["CLOSET_INDEX", "NEG_ALPHA"], "Switch", "SWITCH",
         "a low-cost Large-Cap Index / Factor fund", "Closet-indexed (r2 ~0.97) and negative net-of-fee alpha — paying active fees for index beta."),
        ("LIC MF Flexi Cap Fund", "LIC MF", "equity", "Regular", 4.5, 12, 0.96, 1.18, -1.0, 0.060, 31,
         ["DOWN_CAP_HI", "WEAK_CONSIST"], "Switch", "SWITCH",
         "a top-quartile Flexi-Cap from the approved list", "Loses more than the market in down-months (down-capture >115%) and beats it <40% of rolling 3-yr windows."),
        ("LIC MF Multi Cap Fund", "LIC MF", "equity", "Regular", 3.5, 13, 1.02, 1.00, 0.6, 0.055, 52,
         ["MANDATE_RIGIDITY"], "Switch", "SWITCH",
         "a Flexi-Cap (manager-flexible cap mix)", "Multi-cap's SEBI 25/25/25 floor forces small/mid we prefer to size ourselves — structural, not performance."),
        ("ICICI Pru Multi-Asset (Regular)", "ICICI Pru", "hybrid", "Regular", 4.0, 14, 0.88, 0.72, 0.9, 0.045, 61,
         ["REG_PLAN_DRAG"], "Redeem-to-Direct", "REDEEM",
         "the same fund's Direct plan", "The identical fund is available Direct; the Regular-plan trail is pure avoidable cost."),
        ("Bandhan Small Cap Fund", "Bandhan", "equity", "Direct", 0.45, 15, 1.16, 1.34, -0.6, 0.120, 44,
         ["DEEP_DD", "CAPACITY", "OVER_ALLOC"], "Exit", "EXIT",
         "the primary small-cap sleeve already held", "Sub-scale ~3L beside a larger small-cap fund; deep drawdown and over-allocated — duplication and cost."),
        ("LIC MF Balanced Advantage", "LIC MF", "hybrid", "Regular", 3.0, 16, 0.86, 0.98, -0.8, 0.050, 38,
         ["DOWN_CAP_HI", "DEEP_DD"], "Trim", "TRIM",
         "a hybrid that actually cushions (down-capture <70%)", "Down-capture near equity levels — not doing its cushioning job; poor worst-year."),
        # --- genuine Holds so the book isn't all-Sell ---
        ("Parag Parikh Flexi Cap (Direct)", "PPFAS", "equity", "Direct", 7.5, 21, 1.03, 0.74, 2.6, 0.050, 74,
         [], "Hold", "HOLD", "-", ""),
        ("Nippon India Nifty 50 Index (Direct)", "Nippon", "passive", "Direct", 4.0, 22, 1.00, 1.00, -0.2, 0.004, 55,
         [], "Hold", "HOLD", "-", ""),
        ("HDFC Balanced Advantage (Direct)", "HDFC", "hybrid", "Direct", 3.5, 23, 0.80, 0.56, 1.3, 0.040, 66,
         [], "Hold", "HOLD", "-", ""),
    ]
    bench_cagr = round((np.asarray(bench)[-1] / bench[0]) ** (252 / len(bench)) - 1, 4) * 100
    # illustrative holding age (years) — drives the tax-inertia rule (Principal 2026-07-25):
    # units >5y (stronger >10y) switch only on structural grounds; stocks exempt (risk dominates tax)
    _HOLD_YRS = {"LIC MF Large Cap Fund": 9.2, "LIC MF Flexi Cap Fund": 3.1, "LIC MF Multi Cap Fund": 2.4,
                 "ICICI Pru Multi-Asset (Regular)": 6.5, "Bandhan Small Cap Fund": 1.8,
                 "LIC MF Balanced Advantage": 2.2, "Parag Parikh Flexi Cap (Direct)": 4.6,
                 "Nippon India Nifty 50 Index (Direct)": 5.8, "HDFC Balanced Advantage (Direct)": 3.9}
    out = []
    for (name, amc, cat, plan, wt, seed, ub, db, alpha, idio, hit3y, flags, verdict, action, exemplar, structural) in specs:
        nav = _make_fund_nav(rb, ub, db, alpha, idio, seed=seed)
        m = _metrics_from_nav(nav, bench)
        m["bench_cagr3y"] = round(bench_cagr, 1)
        # QFRA-style composite: reward alpha/consistency/cushion, penalize flags
        base = 55 + m["alpha_ann"] * 1.1 + (hit3y - 50) * 0.4 - max(0, m["down_capture"] - 100) * 0.5
        qfra = int(max(8, min(96, base - 10 * len([f for f in flags if f in ("CLOSET_INDEX", "NEG_ALPHA", "DEEP_DD")]))))
        merit = "A" if qfra >= 70 else ("B" if qfra >= 55 else ("C" if qfra >= 40 else "D"))
        out.append(dict(name=name, amc=amc, category=cat, plan=plan, weight_pct=wt,
                        value_inr=round(grand_inr * wt / 100), qfra=qfra, merit=merit, verdict=verdict,
                        action=action, flags=flags, hit3y=hit3y, alpha_t=round(m["info_ratio"] * 1.3, 2),
                        exemplar=exemplar, structural_reason=structural,
                        ter=(0.95 if plan == "Regular" else 0.55) if cat != "passive" else 0.20,
                        holding_years=_HOLD_YRS.get(name, 2.0), **m))
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
                   "aum_inr": grand, "as_of": "2026-07-25"},
        "ips": {"risk_tier": "Aggressive", "objective": "Long-term capital growth with a quality bias; tolerates interim drawdowns for higher compounding.",
                "horizon_yrs": 7, "single_name_cap_pct": 8.0, "foreign_target_pct": 15.0, "gold_target_pct": 5.0,
                "alloc_bands": {"Equity": (65, 78, 85), "Hybrid/Debt": (5, 12, 25), "Alternatives/Gold": (0, 5, 10), "Cash": (0, 5, 15)},
                "constraints": ["No single stock above 8% of the book", "Min 15% of equity in foreign/global by target",
                                "No unrated / F&O / leveraged positions", "ESG: no tobacco primary-producer adds"]},
        "house_view": {"stance": {"Domestic equity": "Incrementally positive", "Foreign equity": "~15% target, under-owned",
                                  "Gold & silver": "Positive, 75:25", "Momentum": "On hold", "Low-vol / value": "Favoured"},
                       "alloc_gap": {"Large": 8.5, "Mid": 3.0, "Small": -1.5, "Foreign": -12.0, "Gold": -4.0, "Debt/Hybrid": 6.0}},
        "equity": eq, "funds": funds,
        "totals": {"eq_pct": round(eq_val / grand * 100, 1), "mf_pct": round(mf_val / grand * 100, 1),
                   "cash_pct": round(cash_val / grand * 100, 1), "grand_inr": grand,
                   "top10_pct": round(top10, 1), "n_stocks": len(eq), "n_funds": len(funds),
                   "n_sell": n_sell, "n_trim": n_trim, "n_hold": n_hold},
        "cost": {"rows": [(f["name"], f["plan"], round(f["ter"] * 100),
                           round((0.95 - 0.55) * 100) if f["plan"] == "Regular" and f["category"] != "passive" else 0)
                          for f in funds],
                 "pms_bps": 120, "total_bps": 168, "total_inr": round(grand * 0.0168),
                 "reg_drag_inr": round(sum(f["value_inr"] for f in funds if f["plan"] == "Regular") * 0.004)},
        "tax": {"fund_rows": [(f["action"], f["name"], f["value_inr"], ">1y" if f["action"] != "Redeem-to-Direct" else "mixed",
                              "LTCG" if f["action"] in ("Switch", "Exit") else "STCG likely", f["structural_reason"][:60])
                             for f in funds if f["action"] not in ("HOLD", "Hold")],
                "gross": proceeds, "ltcg": ltcg, "stcg": stcg, "net": net,
                "de_gap_note": "Direct-equity Sell tax needs the demat trade file (acquisition date + cost per lot); not in the statement provided."},
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
