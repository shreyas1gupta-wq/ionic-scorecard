# -*- coding: utf-8 -*-
"""Statement in, deck out. The whole advisor-facing pipeline.

    python build/build_review.py <statement.xlsx> [--client "Name"] [--tier HNI_DEEP]

WHAT THIS KNOWS: how to read a statement, how to look a scheme up in the central score file, and how
to lay out a slide. That is all.

WHAT THIS DOES NOT KNOW, deliberately: how a score is produced. There is no NAV history here, no peer
construction, no percentile maths, no backtest and no scoring engine. The score, the call and the
rationale arrive as three columns in a CSV that is produced centrally. An advisor running this cannot
reconstruct the method from it, and does not need to.

A scheme missing from the score file renders as No View. Rows the parser could not resolve go to an
exceptions file. Neither is ever silently dropped.
"""
import argparse
import glob
import re
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "parse"))

# The slide engine, resolved RELATIVE to the repository root. An absolute path would tie the kit to
# one machine, which is the single most common reason a handover fails to run anywhere else.
ENGINE = os.path.join(os.path.dirname(KIT), "Shreyas_Ionic_AMC", "09_PRODUCT", "pr_template")
if not os.path.isdir(ENGINE):
    raise SystemExit(f"  slide engine not found at {ENGINE}\n"
                     f"  Run this from inside a clone of the repository, or set ENGINE by hand.")
sys.path.insert(0, os.path.join(os.path.dirname(KIT), "Shreyas_Ionic_AMC", "09_PRODUCT", "scripts"))
sys.path.insert(0, ENGINE)

from read_statement import read_statement                                  # noqa: E402
import tag_risk_liquidity as RL                                            # noqa: E402
import ips_profiles as IPSP                                                # noqa: E402
import build_ips as IPSB                                                   # noqa: E402
import tax_engine as TAXE                                                  # noqa: E402
import engine as ENG                                                       # noqa: E402
import tiers                                                               # noqa: E402

ORDER = {"Sell": 0, "Trim": 1, "Hold (watch)": 2, "Hold": 3, "No View": 4}
HELD = ("Hold", "Hold (watch)")
# every module that needs direct equity, plus the ones needing data a statement never carries
# Pages the kit cannot render honestly from a statement alone.
#   the Equity Book (score_method .. hold_rationale) needs a Stock Scorecard per name, which is a
#   separate engine and is not published to the kit. Direct shares still appear in the portfolio
#   pages; what they do not get is a per-stock verdict.
#   sector_exposure and mcap_positioning need a sector and a market-cap band per holding.
#   tax_impact needs a cost basis, which a holdings statement rarely carries.
#   scheme_correlation needs NAV history, which is deliberately not in the kit.
SKIP = {"sector_exposure", "funds_debt", "scheme_correlation"}
# tax_impact is skipped only when NO exit carries a cost basis, decided below.
# The Equity Book needs a call and a score per SHARE. Those now arrive in a published stock score
# file exactly as the fund calls do, so these pages are skipped only when that file is absent
# rather than always. sector_exposure still needs a sector on every holding including the funds,
# and tax_impact still needs a cost basis a statement rarely carries.
SKIP_WITHOUT_STOCK_SCORES = {"score_method", "book_scored", "equity_book", "sell_list",
                             "hold_rationale"}
# Pages that live in the library but sit in no tier by default, and which this review wants.
# The tier override INTERSECTS optional_on with KEEP_ANNEX, so a module that is not already in some
# tier's optional_on can only be switched on here. all_holdings is new and lives in no tier.
EXTRA_ON = {"allocation_house_view", "all_holdings"}
# holdings_detail is the direct-equity annexure and needs a Stock Scorecard per name; all_holdings
# replaces it here and covers funds, shares and everything else on the fields we do have.
KEEP_ANNEX = {"all_holdings", "appendix"}


def latest_score_file():
    """The newest PRODUCTION score file, and a demo one only if there is no production file.

    Never choose between them by filename order. The demo file is dated 2026-08-31 and a production
    file dated earlier sorts before it, so a plain sort hands a client deck the invented scores while
    the run still prints the production as-of date it read from a VERSION file next door. The demo is
    a fallback, and when it is used the output has to say so in words nobody can miss.
    """
    d = os.path.join(KIT, "scores")
    f = sorted(x for x in os.listdir(d) if x.startswith("ionic_scores_") and x.endswith(".csv"))
    real = [x for x in f if not x.upper().endswith("_DEMO.CSV")]
    if real:
        return os.path.join(d, real[-1]), False
    if f:
        return os.path.join(d, f[-1]), True
    raise SystemExit("  no score file in scores/. The kit cannot issue a call without one.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("statement")
    ap.add_argument("--client", default="Client")
    ap.add_argument("--tier", default="HNI_DEEP")
    ap.add_argument("--directives", default=None,
                    help="a JSON file of CLIENT instructions, applied on top of the desk's "
                         "published calls and labelled separately from them.")
    ap.add_argument("--lots", default=None,
                    help="a capital-gains LOT file (CSV) carrying LTCG / STCG / other-income "
                         "units per scheme. Without it the tax page can only price a gain where "
                         "the statement carries a cost, and cannot tell short-term from long.")
    ap.add_argument("--profile", default="Aggressive",
                    choices=["Aggressive", "Moderate", "Conservative"],
                    help="the client's mandate. It sets every band on the IPS.")
    a = ap.parse_args()

    # ---- 1. read the statement ------------------------------------------------------------------
    H, E, notes = read_statement(a.statement)
    print(f"  statement : {os.path.basename(a.statement)}")
    print(f"    {notes['rows']} holdings, {notes['schemes']} schemes, "
          f"Rs {notes['total_value']:,.0f}")
    r = notes.get("reconciliation")
    if r:
        print(f"    reconciles to the statement's own total: "
              f"{'OK' if r['ok'] else 'MISMATCH'} ({r['gap_pct']:+.2f}%)")
    else:
        print(f"    no total row in the statement to reconcile against")
    if notes["exceptions"]:
        # NOT "exceptions". These holdings are in the portfolio, in the totals and on the pages;
        # what they lack is a scheme-level match, which is a detail gap and not an exclusion.
        # Calling them exceptions is what made a reader think two listed REITs had been left out.
        print(f"    {notes['exceptions']} holding(s) carry no scheme-level match. They are IN the "
              f"portfolio and its totals; the list is written out for reference")

    # ---- 2. look up the central calls ------------------------------------------------------------
    # the house view travels with the calls
    HV = {"stance": {}, "alloc_gap": {}, "sector_bands": {}}
    _hvp = os.path.join(KIT, "scores", "house_view.json")
    if os.path.exists(_hvp):
        _hv = json.load(open(_hvp, encoding="utf-8"))
        HV = {"stance": _hv.get("stance", {}), "sector_bands": {}, "alloc_gap": {},
              "as_of": _hv.get("as_of"), "what_we_do": _hv.get("what_we_do", {}),
              "limits_we_state": _hv.get("limits_we_state", []),
              "review_cycle": _hv.get("review_cycle"), "targets": _hv.get("targets", {})}
    else:
        print("    no scores/house_view.json, so the house-view pages will render nothing")

    FIRM = {}
    _fp = os.path.join(KIT, "scores", "firm_profile.json")
    if os.path.exists(_fp):
        FIRM = json.load(open(_fp, encoding="utf-8"))
        print(f"  firm      : profile as of {FIRM.get('as_of', '?')}, "
              f"{len(FIRM.get('founders') or [])} co-founders, "
              f"{len(FIRM.get('asset_class_view') or [])} asset-class views")
    else:
        print("    no scores/firm_profile.json, so the firm introduction pages are skipped")

    sf, is_demo = latest_score_file()
    S = pd.read_csv(sf)
    # The production VERSION.json arrives with the real score file. VERSION_DEMO.json is the tracked
    # fallback so a fresh clone runs on the demo data without one.
    # Pair the VERSION with the score file actually chosen. Reading the production VERSION beside a
    # demo CSV is how a run announces an as-of date that belongs to neither.
    vp = os.path.join(KIT, "scores", "VERSION_DEMO.json" if is_demo else "VERSION.json")
    if not os.path.exists(vp):
        vp = os.path.join(KIT, "scores", "VERSION_DEMO.json")
    ver = json.load(open(vp, encoding="utf-8"))
    print(f"  scores    : {os.path.basename(sf)}  as of {ver['as_of']}  ({ver.get('kind','')})")
    if is_demo:
        print("  " + "!" * 74)
        print("  !! NO PRODUCTION SCORE FILE FOUND. These calls are INVENTED demo data.")
        print("  !! Do not send this deck to a client. Ask the desk for the current score file.")
        print("  " + "!" * 74)
    stamp = os.path.basename(sf).replace("ionic_scores_", "").replace("_DEMO", "")[:10]
    if stamp != str(ver.get("as_of")):
        raise SystemExit(f"  the score file is dated {stamp} but VERSION says {ver.get('as_of')}. "
                         f"They are not a matched pair; get a fresh set from the desk.")

    # A book with no scheme-level match anywhere is legitimate: a portfolio of direct shares,
    # bonds and REITs has no ISIN this kit can join on. Merging an empty frame raised a bare
    # KeyError on "isin" and took the whole run down.
    if H.empty:
        H = pd.DataFrame(columns=["isin", "sheet", "scheme", "holder", "folio", "units",
                                  "asset_class", "sub_category", "invested", "value"])
    M = H.merge(S, on="isin", how="left", suffixes=("_stmt", ""))
    M["call"] = M["call"].fillna("No View")
    M["rationale"] = M["rationale"].fillna("")
    M["category"] = M["category"].fillna("Not in the score file")
    M["scheme"] = M["scheme"].fillna(M["scheme_stmt"])
    unknown = M[M["score"].isna() & M["call"].eq("No View")]
    matched = M["isin"].isin(S["isin"]).sum()
    print(f"    matched {matched} of {len(M)} holdings to the score file")
    miss = sorted(set(M.loc[~M['isin'].isin(S['isin']), 'isin']))
    if miss:
        print(f"    {len(miss)} scheme(s) absent from the score file, rendered as No View: {miss}")

    # ---- 3. one call per SCHEME, never per plan --------------------------------------------------
    for _c in ("consistency", "hit_rate", "months"):
        if _c not in M.columns:
            M[_c] = None          # an older score file simply has no consistency; the page self-gates
    if "asset_class" not in M.columns:
        M["asset_class"] = ""
    M["asset_class"] = M["asset_class"].fillna("").astype(str)
    G = (M.groupby(["isin", "scheme", "category", "call", "rationale", "asset_class"],
                   dropna=False)
         .agg(value=("value", "sum"), invested=("invested", "sum"),
              folios=("folio", "nunique"), holders=("holder", "nunique"),
              score=("score", "first"),
              consistency=("consistency", "first"),
              hit_rate=("hit_rate", "first"),
              months=("months", "first")).reset_index())
    G["_o"] = G["call"].map(ORDER).fillna(9)
    G = G.sort_values(["_o", "value"], ascending=[True, False]).drop(columns="_o")
    # ---- 3a. the rest of the book -----------------------------------------------------------
    # Holdings the kit cannot issue a fund call on are still HOLDINGS. A REIT, an AIF, a direct
    # share or a bond belongs to the client, sits in an asset class, and counts toward every weight,
    # every concentration test and the risk profile. Filing them as exceptions took 39% of this book
    # out of the portfolio entirely, which is the opposite of what a review is for. Not reviewed is
    # not not held (Principal, 2026-09-07).
    OTH = []
    if len(E) and "value" in E.columns:
        for r in E.itertuples():
            v = pd.to_numeric(getattr(r, "value", None), errors="coerce")
            if pd.isna(v) or v <= 0:
                continue
            OTH.append(dict(name=(getattr(r, "name", "") or "").strip() or "Unidentified holding",
                            value=float(v),
                            asset_class=(getattr(r, "asset_class", "") or "").strip() or "Other",
                            sub_category=(getattr(r, "sub_category", "") or "").strip()))

    # THE DENOMINATOR IS THE WHOLE BOOK, not the part this kit can score. Holdings the parser could
    # not tie to a scheme still belong to the client, and a weight that ignores them is wrong in the
    # direction that matters: it inflates every fund's share and trips the single-scheme cap on
    # positions that are not actually concentrated.
    FUNDS_VAL = float(G["value"].sum())
    OTHER_VAL = float(sum(o["value"] for o in OTH))
    GRAND = FUNDS_VAL + OTHER_VAL
    if OTHER_VAL > 0:
        print(f"    Rs {FUNDS_VAL:,.0f} in schemes this kit scores, plus Rs {OTHER_VAL:,.0f} in "
              f"{len(OTH)} holdings it does not: they are carried into the book, not dropped")
        _cls = {}
        for o in OTH:
            _cls[o["asset_class"]] = _cls.get(o["asset_class"], 0.0) + o["value"]
        for k, v in sorted(_cls.items(), key=lambda kv: -kv[1]):
            print(f"      {k:<16} Rs {v:>15,.0f}  {v / GRAND * 100:5.1f}% of the book")
        print(f"    weights and the cap are computed on the full Rs {GRAND:,.0f}, "
              f"so the fund sleeve is {FUNDS_VAL / GRAND * 100:.1f}% of the book")
    G["weight_pct"] = G["value"] / GRAND * 100

    # ---- 3b. the central concentration cap ------------------------------------------------------
    # A Sell is a judgement on a fund and travels in the score file. A Trim is a judgement on a
    # WEIGHT, so it cannot: the same scheme at 13% of one book and 2% of another warrants a trim in
    # the first and nothing in the second. The desk publishes the cap in VERSION.json and it is
    # applied here, to a book the desk has not seen. Nothing about it is the advisor's to set.
    G["trim_to_pct"] = None
    G["trim_value"] = 0.0
    cap = ver.get("single_scheme_cap_pct")
    if cap:
        cap = float(cap)
        over = G["call"].isin(HELD) & (G["weight_pct"] > cap)
        for i in G.index[over]:
            w = G.at[i, "weight_pct"]
            G.at[i, "trim_to_pct"] = cap
            G.at[i, "trim_value"] = G.at[i, "value"] - GRAND * cap / 100.0
            G.at[i, "call"] = "Trim"
            G.at[i, "rationale"] = (
                (G.at[i, "rationale"].rstrip() + " ") if G.at[i, "rationale"] else "") + (
                "At %.1f%% of the portfolio it is above the firm's %.0f%% single-scheme cap, so the "
                "weight comes down to %.0f%% rather than the fund being sold." % (w, cap, cap))
        G["_o"] = G["call"].map(ORDER).fillna(9)
        G = G.sort_values(["_o", "value"], ascending=[True, False]).drop(columns="_o")
        if over.sum():
            print("    %d holding(s) above the %.0f%% cap, trimmed back to it" % (over.sum(), cap))
    else:
        print("    no single-scheme cap in VERSION.json, so no holding is trimmed on weight")

    print(f"  calls     : " + "  ".join(f"{k} {v}" for k, v in G["call"].value_counts().items())
          + "   (before direct shares are split out and scored separately)")

    # ---- 4. build the deck ------------------------------------------------------------------------
    _orig = tiers.get

    def _get(name):
        t = _orig(name)
        t["skip_core"] = set(t.get("skip_core", set())) | SKIP
        t["optional_on"] = (set(t["optional_on"]) & KEEP_ANNEX) | EXTRA_ON
        return t

    tiers.get = _get
    ENG.T = tiers

    # The AMC is read off the scheme name against a NAMED list, never by similarity. It is what
    # the single-manager cap is measured on, and several schemes from one house aggregate.
    AMCS = ("ICICI Prudential", "HDFC", "SBI", "Kotak", "Nippon India", "Mirae Asset",
            "Parag Parikh", "UTI", "Axis", "Canara Robeco", "HSBC", "Motilal Oswal", "quant",
            "Navi", "Sundaram", "Zerodha", "Tata", "Aditya Birla", "DSP", "Franklin", "Invesco",
            "Edelweiss", "Bandhan", "PPFAS", "360 ONE", "Baroda BNP", "JM ", "LIC ", "Mahindra",
            "Quantum", "Samco", "Shriram", "Sundaram", "Trust", "Union", "WhiteOak", "Bajaj",
            "Groww", "Helios", "ITI ", "NJ ", "Old Bridge", "Taurus", "Unifi", "Zerodha")

    def _amc(nm):
        u = str(nm or "").strip().lower()
        for a in sorted(AMCS, key=len, reverse=True):
            if u.startswith(a.strip().lower()):
                return a.strip()
        return None

    # THE DIRECT-EQUITY CALLS. The kit has always joined schemes to a central score file and had
    # nothing at all for a share, so every direct holding rendered No View: on a book of 139 shares
    # that told the client the desk had no opinion on 27 stocks it has called Sell. Same publisher,
    # same ISIN key, same rule that a name the file does not carry stays No View.
    _SS = {}
    _ssf = sorted(glob.glob(os.path.join(KIT, "scores", "ionic_stock_scores_*.csv")))
    if _ssf:
        _ssd = pd.read_csv(_ssf[-1]).drop_duplicates("isin")
        _SS = {str(r.isin).strip(): r for r in _ssd.itertuples()}
        print(f"  stocks    : {os.path.basename(_ssf[-1])}  {len(_SS)} names")
    else:
        print("    no stock score file in scores/, so direct shares carry No View")
    if not _SS:
        SKIP.update(SKIP_WITHOUT_STOCK_SCORES)

    _bands_all, _mcap_all = RL.load_bands()
    funds = [dict(name=r.scheme, isin=r.isin,
                  category=RL.engine_category(
                      RL.sub_for_fund(r.scheme, r.category),
                      str(getattr(r, "asset_class", "") or "")),
                  plan="",
                  amc=(_amc(r.scheme) or "-"),
                  asset_class=(str(getattr(r, "asset_class", "") or "").strip() or "Equity"),
                  sebi_category=r.category,
                  value_inr=float(r.value), cost_inr=float(r.invested or r.value),
                  unrealised_pnl=float((r.value or 0) - (r.invested or r.value or 0)),
                  weight_pct=round(r.weight_pct, 2),
                  verdict=r.call,
                  action=("Sell in full" if r.call == "Sell" else
                          ("Trim to %.0f%% of the portfolio" % r.trim_to_pct)
                          if (r.call == "Trim" and r.trim_to_pct is not None)
                          else "Trim" if r.call == "Trim" else "Hold"),
                  trim_to_pct=(None if r.trim_to_pct is None else float(r.trim_to_pct)),
                  trim_value_inr=float(r.trim_value or 0),
                  qfra=(None if pd.isna(r.score) else float(r.score)),
                  # The GRADE column rendered "-" on every row of every page because nothing set
                  # it. It is not a new judgement: the score is the share of the scheme's own peer
                  # group it beat, and the desk's published rule cuts that into thirds, which is
                  # exactly the legend the contents page prints. Restating the desk's own rule in
                  # words beside its own number is what the column was for.
                  merit=(None if pd.isna(r.score) else
                         ("Bottom" if float(r.score) < 100.0 / 3 else
                          "Top" if float(r.score) >= 200.0 / 3 else "Middle")),
                  # How STEADILY the fund got there, as against how far ahead it finished. Context
                  # for the reader, never a verdict: the desk's call always wins (Principal
                  # 2026-09-03), and a Sell sitting high here is a fund that is reliably behind.
                  consistency=(None if pd.isna(r.consistency) else float(r.consistency)),
                  hit_rate=(None if pd.isna(r.hit_rate) else float(r.hit_rate)),
                  cons_months=(None if pd.isna(r.months) else int(r.months)),
                  structural_reason=r.rationale, bench_label="", exemplar="-",
                  hit3y=None, alpha_t=None, ter=None, up_capture=None, down_capture=None,
                  max_dd=None, worst_1y=None, sortino=None, calmar=None, cagr3y=None,
                  bench_cagr3y=None, alpha_ann=None, info_ratio=None, r2=None, flags=[],
                  perf_flag=(r.call in ("Sell", "Trim", "Hold (watch)")))
             for r in G.itertuples()]

    # A SHARE IS NOT A SCHEME, EVEN THOUGH BOTH CARRY AN ISIN. Everything with an ISIN arrives in G
    # because that is the key the score file is published on, but a book held partly in direct
    # equity then walked its shares into the FUND BOOK: on this family's 138 direct holdings that
    # produced twenty-two pages headed "the fund book, scored" listing Bharat Dynamics and State
    # Bank of India as though they were mutual-fund schemes. The framework already knows which is
    # which, so the split is made on its answer rather than on a guess about the name.
    # The ISIN itself says which it is, and says so exactly. India issues mutual-fund units under
    # INF and company securities under INE, so no name, category or market-cap lookup is needed to
    # tell a scheme from a share. Relying on the market-cap file instead left 35 of this family's
    # 124 shares in the fund book, because that file carries the top 750 companies and the family
    # holds smaller names than that; the ISIN prefix has no such gap.
    _share_isin = set()
    for r in G.itertuples():
        isin = str(r.isin or "")
        if isin.startswith("INF"):
            continue                      # a mutual-fund unit, whatever its name reads like
        _sub = RL.sub_for_fund(r.scheme, r.category)
        if isin.startswith("INE") or str(_sub or "").startswith("Direct Equity"):
            _share_isin.add(r.isin)
    _shares = [f for f in funds if f["isin"] in _share_isin]
    funds = [f for f in funds if f["isin"] not in _share_isin]
    if _shares:
        print(f"    {len(_shares)} of these are DIRECT SHARES, not schemes; they go to the equity "
              f"pages rather than the fund book")

    # ---- 4a. the rest of the book, placed where the pages will find it -------------------------
    # Direct shares go into ctx["equity"] so concentration, holdings and sector pages count them as
    # the single-name risk they are. Everything else (AIF, private equity, PMS, REITs, a ULIP,
    # direct bonds) goes into ctx["other"], still carrying its asset class so the IPS equity band and
    # every weight on the deck are struck on the whole portfolio.
    def _isdirect(o):
        return o["sub_category"].strip().lower() in ("direct equity", "direct equities")

    equity_rows, other_rows = [], []
    for o in OTH:
        w = o["value"] / GRAND * 100 if GRAND else 0.0
        # A PMS, an AIF and a ULIP all have a manager, and the single-manager cap is measured on
        # the manager. Kotak Alternate Opportunities aggregates with Kotak's schemes, which is
        # exactly what that cap is for. A boutique with no match keeps its own leading words.
        _mgr = _amc(o["name"])
        if _mgr is None and o["sub_category"] in ("AIF", "Funds", "Private Equity"):
            _mgr = " ".join(str(o["name"]).split()[:2])
        # A DISCRETIONARY MANDATE IS HELD, NOT UNSEEN. A PMS or an AIF has a manager the client has
        # already appointed and a portfolio the desk has not been given, so the fund-quality
        # framework cannot score it. That is a reason to withhold a SCORE, not to withhold a
        # position: printing No View against a rupee-crore mandate reads to the client as "we have
        # nothing to say about the largest single line in your book". The call is Hold, the
        # rationale says exactly why it is a Hold and what would be needed to say more, and the
        # holding counts in every weight, band and concentration test like any other.
        _managed = str(o.get("sub_category") or "").strip().upper().startswith(("PMS", "AIF"))
        _why = ("Held under a discretionary mandate. The manager's own holdings are not part of "
                "this review, so the scheme-level framework does not score it; the position is "
                "carried at full value in every allocation and concentration test on these pages."
                if _managed else "")
        rec = dict(name=o["name"], value_inr=o["value"], weight_pct=round(w, 2),
                   asset_class=o["asset_class"], sub_category=o["sub_category"],
                   amc=(_mgr or "-"), structural_reason=_why,
                   rec=("Hold" if _managed else "No View"),
                   verdict=("Hold" if _managed else "No View"),
                   sector=None, ionic_score=None)
        (equity_rows if _isdirect(o) else other_rows).append(rec)
    # the ISIN-matched direct shares, in the shape the equity pages read
    _n_share_call = 0
    for f in _shares:
        _sc = _SS.get(str(f["isin"]).strip())
        _call = (str(getattr(_sc, "call", "") or "").strip() or "No View") if _sc is not None else "No View"
        if _sc is not None and _call != "No View":
            _n_share_call += 1

        def _t(field):
            v = getattr(_sc, field, None) if _sc is not None else None
            return "" if v is None or (isinstance(v, float) and v != v) else str(v).strip()

        def _f(field):
            v = getattr(_sc, field, None) if _sc is not None else None
            try:
                return None if v is None or (isinstance(v, float) and v != v) else float(v)
            except (TypeError, ValueError):
                return None

        equity_rows.append(dict(
            name=(_t("company") or f["name"]), isin=f["isin"],
            symbol=_t("symbol"), value_inr=f["value_inr"],
            weight_pct=f["weight_pct"], asset_class=f.get("asset_class") or "Equity",
            sub_category="Direct Equity", amc="-",
            sector=(_t("sector") or None),
            ionic_score=_f("ionic_score"), score_3y=_f("score_3y"), score_1y=_f("score_1y"),
            growth_pct=_f("growth_pct"),
            rationale=_t("rationale"), negative_para=_t("negative_para"),
            positive=_t("positive_para"), reverse_dcf=_t("reverse_dcf"),
            summary=_t("summary"), holding_years=None,
            structural_reason=_t("rationale") or f.get("structural_reason") or "",
            rec=_call, verdict=_call))
    if _shares:
        print(f"    {_n_share_call} of {len(_shares)} direct shares carry a published call; "
              f"the rest are No View")
    equity_rows.sort(key=lambda r: -r["value_inr"])
    other_rows.sort(key=lambda r: -r["value_inr"])

    def _clsval(cls):
        v = sum(o["value"] for o in OTH if o["asset_class"].strip().lower() == cls)
        if "asset_class" in H.columns:
            v += float(H.loc[H["asset_class"].astype(str).str.strip().str.lower() == cls,
                             "value"].sum())
        return v

    # A book worth nothing cannot be reviewed, and every weight on every page of this deck is a
    # share of GRAND. Sixteen divisions by it follow this line. Left unguarded the build died on
    # a ZeroDivisionError with a traceback and no deck; what the advisor needs is to be told
    # which statement produced no value, and that it is almost always a parsing problem rather
    # than an empty account.
    if not GRAND:
        raise SystemExit(
            "\n  STOP: this statement produced a book worth Rs 0, so there are no "
            "weights to compute and no review to write." + "\n" +
            "  Usually the value column was not read: check that the sheet has a column "
            "headed Value, Market Value, Current Value or Amount, that its numbers are "
            "stored as numbers rather than text, and that the holdings are not all closed."
            + "\n  Nothing has been written.")

    EQ_VAL = _clsval("equity")
    FI_VAL = _clsval("fixed income")
    ALT_VAL = _clsval("alternates")
    if EQ_VAL + FI_VAL + ALT_VAL == 0:      # a statement with no asset-class column at all
        EQ_VAL = FUNDS_VAL
    print(f"    asset classes on the whole book: equity {EQ_VAL / GRAND * 100:.1f}%, "
          f"fixed income {FI_VAL / GRAND * 100:.1f}%, alternates {ALT_VAL / GRAND * 100:.1f}%")

    # ---- 4b. the two risk axes ----------------------------------------------------------------
    # Every holding, fund or not, gets a risk band and a liquidity band. This is what lets the book
    # be read as a portfolio rather than as a list of schemes: an AIF nobody scores still occupies a
    # cell on the grid and still counts against the illiquidity budget.
    _bands, _mcap = _bands_all, _mcap_all
    if _bands:
        for f in funds:
            f["sebi_category"] = f.get("sebi_category") or ""
        pf, gf = RL.attach(funds, _bands, _mcap, "fund")
        pe, ge = RL.attach(equity_rows, _bands, _mcap, "other")
        for _e in equity_rows:
            _rs = (_e.get("risk_sub") or "")
            if _rs.startswith("Direct Equity - "):
                # mcap_positioning's buckets are "Large"/"Mid"/"Small"/"Micro". The framework's
                # sub-category says "Large Cap". Handing it the longer string put every holding in
                # a key the page does not read, so all four buckets summed to zero: the page either
                # showed nothing or, on a one-holding book, raised inside the chart on max() of an
                # empty sequence and vanished from the deck.
                _e["mcap_band"] = _rs.split(" - ", 1)[1].replace(" Cap", "")
        po, go = RL.attach(other_rows, _bands, _mcap, "other")
        placed, gap = pf + pe + po, gf + ge + go
        total_rows = len(funds) + len(equity_rows) + len(other_rows)
        print(f"    risk and liquidity bands on {placed} of {total_rows} holdings"
              + (f"; Rs {gap:,.0f} carries no band and is reported as such" if gap else ""))
    else:
        print("    no risk/liquidity band file in scores/, so those pages will not render")

    # ---- 4c. the Investment Policy Statement, generated ---------------------------------------
    # Three inputs only: the client, the profile, and the holdings. Every band comes from the
    # profile; every current figure is computed from the book. Nothing is typed in per client.
    _all = list(funds) + list(equity_rows) + list(other_rows)
    IPS = IPSB.compute(_all, profile=a.profile)
    _prof = IPSP.PROFILES[a.profile]
    _pb = _prof["portfolio"]
    print(f"    IPS        : {a.profile} profile"
          + ("" if IPS["approved"] else "  (bands are a DRAFT pending desk sign-off)"))
    for _sec in IPS["sections"]:
        _out = [r for r in _sec["rows"] if r["fit"] in ("Above", "Below")]
        _na = [r for r in _sec["rows"] if r["fit"] is None]
        print(f"      {_sec['title'][:44]:<46} {len(_out)} outside band, {len(_na)} not computable")

    _tg = HV.get("targets") or {}
    if _tg and GRAND:
        # GOLD IS NOT THE ALTERNATES SLEEVE. This bar used to plot the whole alternates class,
        # AIFs, PMS, REITs and gold together, against the house's 5% GOLD target, so a book with no
        # gold at all could show gold running well ahead of target on the strength of a private
        # equity fund. Gold is taken from the framework's own gold sub-categories, and whatever
        # else sits in alternates is reported as its own figure rather than folded into a bar that
        # names a different asset.
        _GOLD_SUBS = ("Gold / Silver ETF or FoF", "Sovereign Gold Bond")
        _gold_val = sum(float(h.get("value_inr") or 0.0)
                        for h in (list(funds) + list(equity_rows) + list(other_rows))
                        if str(h.get("risk_sub") or "").strip() in _GOLD_SUBS)
        HV["alloc_gap"] = {
            "Equity": round(EQ_VAL / GRAND * 100 - float(_tg.get("Equity", 0)), 1),
            "Debt/Hybrid": round(FI_VAL / GRAND * 100 - float(_tg.get("Debt/Hybrid", 0)), 1),
            "Gold": round(_gold_val / GRAND * 100 - float(_tg.get("Gold", 0)), 1)}
        HV["alloc_note"] = None
        _alt_ex_gold = ALT_VAL - _gold_val
        if _alt_ex_gold / GRAND * 100 >= 0.5:
            HV["alloc_note"] = ("A further %.1f%% of the book sits in alternates other than gold, "
                                "AIFs, PMS and listed property among them. The house view publishes "
                                "no single target for that sleeve, so it is not plotted here; the "
                                "mandate's own 0 to %.0f%% band for it is tested on the Investment "
                                "Policy Statement page."
                                % (_alt_ex_gold / GRAND * 100, _pb["Alternates"][1]))
    if HV.get("as_of"):
        print(f"    house view : published {HV['as_of']}, {len(HV.get('stance') or {})} stances")

    # The score file states the framework by its INTERNAL name. That name is on the desk's own
    # tell-scan list of words a client page must not carry, and it reached slide 26 of this deck
    # four times. Renamed at the point the rationale enters the deck, so an already-published
    # score file cannot leak it and a re-publish on the desk's own cadence cannot reintroduce it.
    # WHY a scheme carries an action, stated by the layer that decided it rather than inferred
    # downstream from an optional score field. A Sell in this pipeline is always originated by the
    # framework's own long-record test; a Trim is originated by the concentration cap and is not a
    # judgement on the fund at all. Left to infer, fund_actions counted the cap trim as a
    # performance call and opened the page "All 4 of these actions are performance calls ...
    # nothing here is being sold for structural or liquidity reasons", directly contradicted by
    # its own card for that trim three inches below.
    for _f in funds:
        _f["perf_flag"] = (_f["verdict"] == "Sell")
        _f["action_origin"] = ("performance" if _f["verdict"] == "Sell" else
                               "concentration" if _f["verdict"] == "Trim" else "")

    _HOUSE_NAME = "Fund-quality framework"
    for _f in funds:
        _r = _f.get("structural_reason")
        if _r:
            _f["structural_reason"] = str(_r).replace("QFRA Framework", _HOUSE_NAME).replace(
                "QFRA-2", _HOUSE_NAME).replace("QFRA-1", _HOUSE_NAME).replace("QFRA", _HOUSE_NAME)

    def _plan_of(name):
        n = " %s " % re.sub(r"[^a-z ]+", " ", str(name or "").lower())
        return ("Regular" if " regular " in n else
                "Direct" if " direct " in n else "Unstated")

    _N_REG = sum(1 for f in funds if _plan_of(f["name"]) == "Regular")
    _REG_VAL = sum(f["value_inr"] for f in funds if _plan_of(f["name"]) == "Regular")
    for _f in funds:
        _f["plan"] = _plan_of(_f["name"])

    def _n_call(c):
        return (int((G["call"] == c).sum() if len(G) else 0)
                - sum(1 for f in _shares if str(f.get("verdict") or "") == c)
                + sum(1 for r in equity_rows + other_rows
                      if str(r.get("rec") or r.get("verdict") or "") == c))

    # ---- 3d. what the CLIENT has asked for ------------------------------------------------------
    # A Sell on an Ionic page is the desk's verdict. A client asking to exit a sleeve is not that,
    # and rendering it as one would put the firm's name on twenty-two calls it never made. Client
    # instructions get their own call, their own colour and their own line in every total, so a
    # reader can always tell which of the two they are looking at.
    DIRECTIVES = {}
    if a.directives and os.path.exists(a.directives):
        DIRECTIVES = json.load(open(a.directives, encoding="utf-8"))

    def _bucket_of(row):
        """The asset class this row was read as, for matching a directive against a sleeve."""
        return str(row.get("asset_class") or "").strip().lower()

    _CLIENT_CALLS = {}
    if DIRECTIVES.get("directives"):
        _rows_all = list(funds) + list(equity_rows) + list(other_rows)
        for d in DIRECTIVES["directives"]:
            m = d.get("match") or {}
            want_bucket = [b.strip().lower() for b in (m.get("bucket") or [])]
            want_name = [w.strip().lower() for w in (m.get("name_contains") or [])]
            skip = [w.strip().lower() for w in (d.get("except_names") or [])]
            for r in _rows_all:
                nm = str(r.get("name") or "").lower()
                if any(w in nm for w in skip):
                    continue
                hit = (want_bucket and _bucket_of(r) in want_bucket) or                       (want_name and any(w in nm for w in want_name))
                if not hit:
                    continue
                # a later directive wins, which is how the retain rules override the sleeve rule
                _CLIENT_CALLS[id(r)] = (d["call"], d.get("reason", ""), d.get("id", ""))
        for r in _rows_all:
            got = _CLIENT_CALLS.get(id(r))
            if not got:
                continue
            call, why, _id = got
            r["desk_call"] = r.get("verdict") or r.get("rec") or "No View"
            r["rec"] = r["verdict"] = call
            r["call_source"] = "Client instruction"
            r["structural_reason"] = why
            # THE ACTION FIELD IS WHAT THE FUND PAGES COUNT. verdict/rec drive the tables; the
            # narrative lines on the fund book and the fund-action cards count `action`, which is
            # written once when the fund dict is built and knew nothing about a directive applied
            # afterwards. That single omission is why a deck showing nineteen EXIT (CLIENT) rows
            # in its own tables told the reader, four pages later, that five schemes carried an
            # action and fifty-three were Holds.
            r["action"] = call
        _n_exit = sum(1 for v in _CLIENT_CALLS.values() if v[0].startswith("Exit"))
        _n_ret = sum(1 for v in _CLIENT_CALLS.values() if v[0] == "Retain")
        _v_exit = sum(float(r.get("value_inr") or 0) for r in _rows_all
                      if str(r.get("verdict") or "").startswith("Exit"))
        print(f"  client    : {os.path.basename(a.directives)} -> "
              f"{_n_exit} holdings marked Exit (client), Rs {_v_exit:,.0f}; "
              f"{_n_ret} marked Retain")

    # ONE CENSUS, READ BY EVERY PAGE THAT COUNTS ANYTHING. Each module used to count the book for
    # itself, off whichever field it happened to use -- `action` here, `verdict` there, the scored
    # frame somewhere else -- and the four answers disagreed on the same deck. Every count of a
    # call in this review now comes from here.
    _ALL_ROWS = list(funds) + list(equity_rows) + list(other_rows)

    def _call_of(r):
        return str(r.get("verdict") or r.get("rec") or "No View")

    def _census(pred=None):
        rows = [r for r in _ALL_ROWS if (pred is None or pred(r))]
        out = {}
        for r in rows:
            c = _call_of(r)
            n, v = out.get(c, (0, 0.0))
            out[c] = (n + 1, v + float(r.get("value_inr") or 0.0))
        return out

    CENSUS = {"book": _census(),
              "funds": _census(lambda r: r in funds),
              "shares": _census(lambda r: r in equity_rows),
              "other": _census(lambda r: r in other_rows)}

    def _cn(scope, call):
        return CENSUS[scope].get(call, (0, 0.0))[0]

    def _cv(scope, call):
        return CENSUS[scope].get(call, (0, 0.0))[1]

    CLIENT_DIRECTIVE = {}
    if DIRECTIVES.get("directives"):
        _dir_rows = [r for r in _ALL_ROWS if r.get("call_source") == "Client instruction"]
        CLIENT_DIRECTIVE = {
            "on_file": True,
            "as_of": DIRECTIVES.get("as_of", ""),
            "instruction": DIRECTIVES.get("instruction", ""),
            "footnote": DIRECTIVES.get("footnote", ""),
            "exits": sorted([{"name": r.get("name"), "value_inr": float(r.get("value_inr") or 0),
                              "weight_pct": float(r.get("weight_pct") or 0),
                              "asset_class": r.get("asset_class") or "",
                              "category": r.get("sub_category") or r.get("category") or "",
                              "desk_call": r.get("desk_call") or "No View",
                              "reason": r.get("structural_reason") or ""}
                             for r in _dir_rows if _call_of(r).startswith("Exit")],
                            key=lambda d: -d["value_inr"]),
            "retains": sorted([{"name": r.get("name"), "value_inr": float(r.get("value_inr") or 0),
                                "weight_pct": float(r.get("weight_pct") or 0),
                                "asset_class": r.get("asset_class") or "",
                                "desk_call": r.get("desk_call") or "No View",
                                "reason": r.get("structural_reason") or ""}
                               for r in _dir_rows if _call_of(r) == "Retain"],
                              key=lambda d: -d["value_inr"]),
        }
        CLIENT_DIRECTIVE["exit_value_inr"] = sum(d["value_inr"] for d in CLIENT_DIRECTIVE["exits"])
        CLIENT_DIRECTIVE["retain_value_inr"] = sum(d["value_inr"]
                                                   for d in CLIENT_DIRECTIVE["retains"])

    # ---- 3c. what the recommended exits cost in tax ---------------------------------------------
    # PRICED SLICE BY SLICE, from the lot file where one was supplied. The old block charged a
    # flat 12.5% to every holding with a cost basis and printed a hard-coded "less STCG 0.0L",
    # which is not a gap in the estimate but a positive claim that no short-term gain arises. On
    # this family the supplied lot file carried Rs 89.5 lakh of short-term units, two of them in
    # schemes on the sell list. Nothing that cannot be computed is given a number: money taxed at
    # the holder's own slab is carried through in rupees and said so.
    _LOTS = TAXE.load_lots(a.lots) if a.lots else {}
    if _LOTS:
        _holders = set()
        for _v in _LOTS.values():
            _holders |= set(_v.get("members") or [])
        _N_HOLDERS = max(1, len(_holders))
        print(f"  lots      : {os.path.basename(a.lots)} -> {len(_LOTS)} schemes, "
              f"{_N_HOLDERS} holder(s); short-term units Rs "
              f"{sum(v['stcg_val'] for v in _LOTS.values()):,.0f}, post-Apr-2023 debt units Rs "
              f"{sum(v['other_val'] for v in _LOTS.values()):,.0f}")
    else:
        _N_HOLDERS = 1

    _TAX_ROWS, _GROSS, _LT, _ST, _SLAB = [], 0.0, 0.0, 0.0, 0.0
    _EQ_LT_GAIN, _n_priced, _no_basis, _UNDATED = 0.0, 0, 0, 0.0
    for _r in list(funds) + list(equity_rows) + list(other_rows):
        _call = str(_r.get("verdict") or _r.get("rec") or "")
        # a client-directed exit moves real money and carries real tax, so it is priced here
        # exactly like a desk Sell; the ACTION column is what tells the reader them apart.
        if _call not in ("Sell", "Trim", "Exit (client)"):
            continue
        _amt = (float(_r.get("trim_value_inr") or 0.0) if _call == "Trim"
                else float(_r.get("value_inr") or 0.0))
        if _amt <= 0:
            continue
        # a trim sells a slice, so it is priced on that slice and not on the position
        _row_for_tax = dict(_r)
        _row_for_tax["value_inr"] = _amt
        if _call == "Trim" and float(_r.get("value_inr") or 0) > 0:
            _f = _amt / float(_r["value_inr"])
            if _r.get("cost_inr"):
                _row_for_tax["cost_inr"] = float(_r["cost_inr"]) * _f
        _px = TAXE.price(_row_for_tax, _LOTS)
        _GROSS += _amt
        _LT += _px["ltcg_tax"]
        _ST += _px["stcg_tax"]
        _SLAB += _px["slab_value"]
        if TAXE.is_equity_oriented(_r.get("asset_class"),
                                   _r.get("risk_sub") or _r.get("sub_category"),
                                   _r.get("name")):
            _EQ_LT_GAIN += _px.get("ltcg_gain") or 0.0
        if _px["gain_known"]:
            _n_priced += 1
        else:
            _no_basis += 1
        if "no purchase date" in _px["character"]:
            _UNDATED += _amt
        _act = ("TRIM" if _call == "Trim"
                else "EXIT (CLIENT)" if _call.startswith("Exit") else "SELL")
        _TAX_ROWS.append((_act, _r.get("name") or "", _amt, None, _px["character"], _px["note"]))

    # SECTION 112A GIVES EACH HOLDER Rs 1.25 LAKH A YEAR, and this is a family book with more
    # than one holder in it. Applied once across the programme rather than per holding, which
    # would give the same exemption to a scheme twenty times over.
    _EXEMPT = TAXE.LTCG_EXEMPT_PER_HOLDER * _N_HOLDERS
    _LT_RELIEF = min(_LT, max(0.0, min(_EQ_LT_GAIN, _EXEMPT)) * TAXE.EQUITY_LTCG)
    _LT = max(0.0, _LT - _LT_RELIEF)

    _n_desk = sum(1 for r in _TAX_ROWS if r[0] in ("SELL", "TRIM"))
    _n_cl = sum(1 for r in _TAX_ROWS if r[0] == "EXIT (CLIENT)")
    _v_cl = sum(r[2] for r in _TAX_ROWS if r[0] == "EXIT (CLIENT)")
    _v_desk = sum(r[2] for r in _TAX_ROWS if r[0] in ("SELL", "TRIM"))
    _scope = ("The whole action programme" if _n_cl else "Mutual-fund actions")
    # THE TWO CALLOUTS HOLD ABOUT TWO LINES EACH. Text that overruns a PowerPoint box is
    # invisible in PowerPoint's own view, so a caveat written into the overflow is a caveat the
    # reader never sees while the deck looks finished. Each is written to fit; whatever does not
    # fit is not written smaller, it is left out of the box and put in the source line.
    _gap_a, _gap_b = [], []
    if _SLAB > 0:
        _gap_a.append("Rs %.1f L of these proceeds is taxed at each holder's own slab rather than "
                      "at a capital-gains rate, so no figure is put against it here."
                      % (_SLAB / 1e5))
    else:
        _gap_a.append("Every move here carries a capital-gains character; none of it falls to slab.")
    if _no_basis:
        _gap_b.append("%d of the %d moves carry no acquisition cost on file, so no gain is "
                      "computed for them." % (_no_basis, len(_TAX_ROWS)))
    if _UNDATED > 0:
        # A DEBT UNIT'S RATE TURNS ON ITS PURCHASE DATE and nothing else: bought before 1 April
        # 2023 it is 12.5%, on or after it is slab. Where the date is absent the lower of the two
        # is shown, so this is the direction in which the estimate can only be too small.
        _gap_b.append("Rs %.1f L is struck at 12.5%% with no purchase date on file; if those units "
                      "postdate April 2023 the rate is slab and this understates it."
                      % (_UNDATED / 1e5))
    if not _gap_b:
        _gap_b.append("Every move here is priced off the client's own capital-gains statement.")

    _TAX = {"fund_rows": _TAX_ROWS, "gross": round(_GROSS), "ltcg": round(_LT),
            "stcg": round(_ST), "slab_value": round(_SLAB),
            "net": round(_GROSS - _LT - _ST),
            "basis": ("lot file" if _LOTS else "statement cost only"),
            "table_scope_label": "%s . est. tax character per move" % _scope,
            "chart_scope_label": "%s . net of est. tax" % _scope,
            "table_total_label": ("Total, whole programme" if _n_cl else "Total fund actions"),
            "gap_note_title": ("What is not in this estimate" if (_SLAB or _no_basis)
                               else "How this estimate is struck"),
            "foot": (
                ("Both panels, one set: %d desk calls at Rs %.1f L and %d client-directed exits "
                 "at Rs %.2f Cr. " % (_n_desk, _v_desk / 1e5, _n_cl, _v_cl / 1e7))
                if _n_cl else "") +
                ("Long and short slices read from the client's own gains statement; the Rs 1.25 "
                 "lakh exemption applied once per holder. " if _LOTS else "") +
                "An estimate, not a tax opinion: confirm rates with the client's tax adviser."
                + (" " + " ".join(_gap_b[:-1]) if len(_gap_b) > 1 else ""),
            "de_gap_note": " ".join(_gap_a),
            "gap_note_2_title": "Also not in this estimate",
            # THE MATERIAL ONE GOES IN THE BOX. Where a rate could only be too low, that is the
            # caveat a reader has to see; the count of moves with no cost basis is visible on the
            # table itself, row by row, and goes to the source line.
            "gap_note_2": (_gap_b[-1] if len(_gap_b) > 1 else _gap_b[0]),
            "gap_note_2_extra": (" " + " ".join(_gap_b[:-1]) if len(_gap_b) > 1 else "")}

    # THE DESK'S OWN PROCEEDS, ACROSS THE WHOLE BOOK. Summed over `funds` alone this was the fund
    # sleeve's Rs 45.4 lakh, while the tax page priced the same programme at Rs 3.37 crore and the
    # priority page then printed a NET larger than its own GROSS -- Rs 3.28 crore net against
    # Rs 3.19 crore gross -- because the fourteen direct-equity Sells were in one figure and not
    # the other. Both figures are struck on the same population now.
    _SELL_VAL = sum(float(r.get("value_inr") or 0.0) for r in _ALL_ROWS
                    if str(r.get("verdict") or r.get("rec") or "") == "Sell")
    _TRIM_VAL = sum(float(r.get("trim_value_inr") or 0.0) for r in _ALL_ROWS
                    if str(r.get("verdict") or r.get("rec") or "") == "Trim")

    # Every ISIN that carries a real call after the overlay, whatever the score file said.
    _CALLED_ISIN = {str(r.get("isin")) for r in _ALL_ROWS
                    if _call_of(r) not in ("No View", "")}

    ctx = {
        "client": {"name": a.client, "code": "-", "account_type": "Portfolio review",
                   "profile": "-", "horizon": "-", "construction": "Mutual funds",
                   "aum_inr": GRAND, "as_of": ver["as_of"]},
        # THE MANDATE, from the firm's Risk and Liquidity framework rather than left blank. These
        # are the Aggressive profile's caps (Principal, 2026-09-07: equity band 80-100%). Every one
        # is tested on the WHOLE book, so an AIF or a direct share counts toward the equity band and
        # toward the single-name cap exactly as a fund does.
        "ips": {"on_file": True,
                "risk_tier": a.profile,
                "objective": "Long-term capital growth with an equity-led core",
                "horizon_yrs": None,
                "alloc_bands": {
                    "Equity": (_pb["Equity"][0],
                               (_pb["Equity"][0] + _pb["Equity"][1]) / 2, _pb["Equity"][1]),
                    "Fixed Income": (_pb["Fixed Income"][0],
                                     (_pb["Fixed Income"][0] + _pb["Fixed Income"][1]) / 2,
                                     _pb["Fixed Income"][1]),
                    "Alternatives": (_pb["Alternates"][0],
                                     (_pb["Alternates"][0] + _pb["Alternates"][1]) / 2,
                                     _pb["Alternates"][1]),
                    "Cash": (_pb["Cash and equivalents"][0],
                             sum(_pb["Cash and equivalents"]) / 2,
                             _pb["Cash and equivalents"][1])},
                # ONE cap, and it is the desk's own published single_scheme_cap_pct. The deck
                # tests this on EVERY holding as a share of the WHOLE book, which is exactly the
                # population and basis the trim engine above applies it on. It used to be sourced
                # from the IPS row "A single listed security", which is a different cap entirely:
                # direct listed shares only, measured against the EQUITY SLEEVE. Reading a 15%
                # sleeve limit as a 15% whole-book limit let a holding the trim engine was already
                # trimming at 10% be reported on the executive summary as inside the cap, and put
                # three different single-name caps in one deck. The IPS page keeps its own row and
                # tests it on the sleeve, in build_ips, where it belongs.
                "single_name_cap_pct": float(ver.get("single_scheme_cap_pct")
                                             or _prof["equity"]["A single listed security"][1]),
                "single_amc_cap_pct": float(_pb["Allocation to a single AMC"][1]),
                "locked_in_cap_pct": float(_pb["Locked-in products, over one year"][1]),
                "unlisted_equity_cap_pct": float(_prof["equity"]["Unlisted securities"][1]),
                # exec_summary indexes these directly rather than with .get, so an IPS that is
                # on_file must carry them or the executive summary raises and the engine, which
                # swallows module exceptions, drops the page with no error on the deck.
                "foreign_target_pct": None, "gold_target_pct": None,
                # EVERY band the profile already defines, under the key the IPS page reads. Nine of
                # the page's fifteen rows printed "TBD / Pending" because these were never set,
                # while ips_profiles.py held a number for each one; and "mcap_bands" was not even
                # the name the page looks up, which is "equity_mcap_bands", so the market-cap rows
                # could not have found a band under any circumstances. A TBD on a client page must
                # mean the desk has not set a band, never that the build forgot to pass it.
                # A BAND, NOT A CAP. Cash is 1 to 3% and international equity is 10 to 25% in this
                # profile; publishing only the upper bound threw the FLOOR away, so a book at 0.4%
                # cash against a 1% minimum and at 3% international against a 10% minimum were both
                # stamped ALIGNED. Two real breaches reported as compliant, in the direction that
                # never gets questioned. Rows whose mandate genuinely has no floor (thematic,
                # unlisted, locked-in, single AMC) keep their scalar cap.
                "cash_cap_pct": tuple(_pb["Cash and equivalents"]),
                # Whether the desk has SIGNED OFF these bands. The Aggressive profile is the
                # desk's own transcribed sheet; Moderate and Conservative are derived drafts. The
                # build printed that to the console and nowhere else, so a deck built on a draft
                # mandate said nothing about it to the person reading it.
                "bands_approved": bool(IPS["approved"]),
                # Figures the IPS workbook already computes and this deck used to print as "Not
                # tracked". Passed through rather than recomputed here, so the workbook and the
                # deck cannot drift apart, and left absent where the workbook itself could not
                # compute one.
                "computed": {r["name"]: r["current"]
                             for _s in IPS["sections"] for r in _s["rows"]
                             if r["current"] is not None},
                "equity_mcap_bands": {"Large": tuple(_prof["equity"]["Large cap"]),
                                      "Mid & Small": tuple(_prof["equity"]["Mid and small cap"])},
                "fi_credit_bands": {"AAA": tuple(_prof["fixed_income"]["AAA rated"]),
                                    "AA": tuple(_prof["fixed_income"]["AA rated"]),
                                    "Below AA": tuple(_prof["fixed_income"]["Below AA rated"])},
                "mod_duration_cap_yrs": _prof["fixed_income"]["Modified duration, years"][1],
                "thematic_sectoral_cap_pct": _prof["equity"]["Thematic and sectoral"][1],
                "international_equity_cap_pct": tuple(_prof["equity"]["International equity"]),
                "gold_band_pct": tuple(_prof["alternates"]["Gold"]),
                # The desk's profiles set a band for gold and silver together, under one heading.
                # Publishing a silver band the profile does not carry would be inventing one.
                "silver_band_pct": None,
                "mcap_bands": {}, "constraints": [
                    "Minimum liquid buffer, Priority 1 assets, 5% of the book at every review.",
                    "High Risk and Low Liquidity together may not exceed 30% of the book.",
                    "Uncalled commitments up to 25% of corpus, tracked outside NAV."]},
        "funds": funds, "equity": equity_rows, "other": other_rows, "fund_churn": {},
        "profile": a.profile, "ips_generated": IPS,
        "totals": {"grand_inr": GRAND,
                   "eq_pct": round(EQ_VAL / GRAND * 100, 1) if GRAND else 0.0,
                   "mf_pct": round(FUNDS_VAL / GRAND * 100, 1) if GRAND else 0.0,
                   "fi_pct": round(FI_VAL / GRAND * 100, 1) if GRAND else 0.0,
                   "alt_pct": round(ALT_VAL / GRAND * 100, 1) if GRAND else 0.0,
                   "cash_pct": 0.0,
                   "n_stocks": len(equity_rows), "n_other": len(other_rows),
                   "n_funds": len(funds),
                   # EVERY call in the book, not the fund sleeve's. The executive summary presents
                   # these as "Sell calls" without qualification, so counting only schemes told a
                   # client with twenty direct-equity Sells that the review had found five.
                   "n_sell": _n_call("Sell"), "n_trim": _n_call("Trim"),
                   "n_hold": _n_call("Hold") + _n_call("Hold (watch)"),
                   # THE CLIENT'S OWN INSTRUCTIONS, counted separately from the desk's calls and
                   # never folded into them. A page that says "19 sell calls" and stops has told
                   # the reader nothing about the largest single movement of money in the plan.
                   "n_exit_client": _cn("book", "Exit (client)"),
                   "n_retain": _cn("book", "Retain"),
                   "v_exit_client": _cv("book", "Exit (client)"),
                   "v_sell": _cv("book", "Sell"),
                   "n_no_view": _cn("book", "No View"),
                   "census": CENSUS,
                   "top10_pct": round(sorted(
                       [float(x) for x in G["weight_pct"]] +
                       [r["weight_pct"] for r in equity_rows + other_rows],
                       reverse=True)[:10] and sum(sorted(
                           [float(x) for x in G["weight_pct"]] +
                           [r["weight_pct"] for r in equity_rows + other_rows],
                           reverse=True)[:10]) or 0.0, 1),
                   "lookthrough": {}},
        # PUBLISHED, not invented here. The stance and the "what we do" text used to be written
        # inline in this file, which meant the house view was whatever the build script happened to
        # say that day and two advisors could send two different ones in the same week. It now comes
        # from scores/house_view.json alongside the calls, on the desk's own cadence.
        "house_view": HV,
        # WHAT THE CLIENT HAS ASKED FOR, in the client's own terms, carried to every page that
        # shows one of these rows. Without it the deck printed "Exit (client)" against a quarter
        # of the book and never once said whose instruction it was or why.
        "client_directive": CLIENT_DIRECTIVE,
        # The firm's own credentials, published centrally beside the calls. Absent, the
        # introduction pages render nothing at all rather than inventing an AUM.
        "firm": FIRM,
        # THE TAX ON THE EXITS THIS REVIEW ACTUALLY RECOMMENDS. The page used to be switched off
        # because "a holdings statement rarely carries a cost basis", which is true of a CAS and
        # not true of the workbooks a platform exports beside it. Where an invested figure is
        # present the gain is real arithmetic, and the character of that gain is the single fact
        # that decides the bill: a debt fund bought on or after 1 April 2023 lost capital-gains
        # treatment entirely and is taxed at the holder's slab, however long it has been held.
        # Every rate is stated on the page and nothing here is a tax opinion.
        "tax": _TAX,
        # REAL money, from the calls this run actually issued. Zeros here printed "Rs 0.0 L gross
        # freed" on the priority-actions page three lines above "Rs 96.29 Cr" of fund actions on
        # the same page. A Sell frees the whole position; a Trim frees only the slice above the
        # cap, which is trim_value_inr and never the position. Tax is NOT netted off: a holdings
        # statement carries no acquisition date and no lot history, so the rate cannot be known,
        # and the page says the figure is before tax rather than quietly showing a gross number
        # under a net label.
        # THE NET IS REAL NOW. It was None because a holdings statement carries no acquisition
        # date; where a lot file is supplied it carries exactly that, so the page can show a net
        # instead of a gross under a "net" heading. Where no lot file is supplied it stays None
        # and the page says the figure is before tax, which is what it was built to do.
        "deployment": {"proceeds_inr": _SELL_VAL + _TRIM_VAL,
                       "tax_leak_inr": (round(_LT + _ST) if _LOTS else None),
                       "net_inr": (round(_GROSS - _LT - _ST) if _LOTS else None),
                       "personalization": []},
        # The plan is READ OFF the scheme's own name, which is where SEBI requires it to be
        # stated; nothing here is matched by similarity. The rupee drag is a different question and
        # needs a TER per scheme in each plan, which a holdings statement does not carry, so it
        # stays 0 and the pages that quote it say the saving is not estimable rather than printing
        # one. Leaving this at "no Regular-plan drag" made the executive summary state that every
        # scheme was Direct on a book listing Regular-plan schemes by name a few pages later.
        "cost": {"reg_drag_inr": 0, "rows": [],
                 "n_regular": _N_REG, "regular_value_inr": _REG_VAL,
                 "n_direct": sum(1 for f in funds if _plan_of(f["name"]) == "Direct")},
        "actions": [], "meeting_history": [], "goals": [], "chart_top_n": 6,
        "data_notes": {
            "suspended": [],
            # value_inr so the page can rank them and count what it does not list: a book with a
            # direct-equity sleeve carries a No View on every share, and naming the largest is the
            # only version of this page a client will read.
            # G IS THE PRE-DIRECTIVE FRAME. It carries the call the score file published, and
            # knows nothing about the client's instruction applied to the fund objects afterwards,
            # so eight debt schemes the plan is exiting were listed on the coverage page as
            # holdings "with no performance view" -- the reader is told in one breath that the
            # money is moving and in the next that nobody has looked at it.
            "no_view": [{"name": r.scheme, "category": r.category, "value_inr": float(r.value),
                         "reason": ("A share, not a scheme: the fund-quality framework scores "
                                    "schemes against their own SEBI category, and a single company "
                                    "is not in that population."
                                    if str(r.isin).startswith("INE") else
                                    "Outside the coverage of the firm's fund-quality frameworks.")}
                        for r in G[G["call"] == "No View"].itertuples()
                        if str(r.isin) not in _CALLED_ISIN],
            "flags": ([f"Scores are as of {ver['as_of']}."] +
                      ([f"Rs {OTHER_VAL:,.0f}, {OTHER_VAL / GRAND * 100:.1f}% of the book, is held "
                        f"outside the schemes this review covers and carries no view here. It is "
                        f"counted in every weight on these pages."] if OTHER_VAL > 0 else []) +
                      ([f"{len(miss)} scheme(s) in this statement are absent from the score file and "
                        f"carry no view."] if miss else []) +
                      ([f"{notes['exceptions']} statement row(s) could not be resolved and are listed "
                        f"in the exceptions file."] if notes["exceptions"] else [])),
        },
    }

    # git does not track empty directories, so a fresh clone has no out/. Create it rather than
    # failing at the very last step with a FileNotFoundError from the pptx writer.
    out_dir = os.path.join(KIT, "out")
    os.makedirs(out_dir, exist_ok=True)
    deck, manifest = ENG.build(ctx, a.tier, verbose=True)
    safe = "".join(c for c in a.client if c.isalnum() or c in " _-").strip().replace(" ", "_")
    deck_path = os.path.join(out_dir, f"{safe}_Review_{a.tier}.pptx")
    deck.save(deck_path)

    # EVERY holding, not the scored sleeve. G is the fund frame: on the reference book that is 34 of
    # 75 rows and Rs 352.7 crore of a Rs 576.8 crore portfolio, while the file is called _Holdings
    # and the README documents it as "Every holding, the call, the rationale". The deck and the IPS
    # workbook were both moved onto the whole book; this file was not, so an advisor reconciling the
    # workbook against the deck would find Rs 224 crore missing and no explanation for it. The
    # unscored rows carry No View, which is the correct answer for them and not a reason to omit
    # them: they are still the client's money and they still count in every weight on every page.
    # G STILL CONTAINS THE DIRECT SHARES. They were removed from `funds` and re-added to
    # `equity_rows` with their own published call, so writing G alongside equity_rows listed every
    # share TWICE: once as the No View the FUND score file has for it, and once with its real call.
    # On this family that was 124 duplicated lines and Rs 2.43 crore of double-counted value in a
    # workbook whose whole purpose is to reconcile. The deck itself was never wrong, because it
    # reads the two lists the split produced; only this export read the pre-split frame.
    _G_FUNDS = G[~G["isin"].isin(_share_isin)].copy() if len(G) else G
    # THE CLIENT'S INSTRUCTION HAS TO REACH THE WORKBOOK TOO. G is the frame as the score file
    # left it and knows nothing about a directive applied to the fund objects afterwards, so the
    # workbook was showing No View against twenty holdings the deck three feet away showed as
    # Exit (client). The two must not disagree.
    if len(_G_FUNDS):
        _by_isin = {str(f.get("isin")): f for f in funds}
        _G_FUNDS["call"] = [
            (_by_isin.get(str(i), {}).get("verdict") or c)
            for i, c in zip(_G_FUNDS["isin"], _G_FUNDS["call"])]
        _G_FUNDS["rationale"] = [
            (_by_isin.get(str(i), {}).get("structural_reason") or r)
            for i, r in zip(_G_FUNDS["isin"], _G_FUNDS["rationale"])]
    _G_ALL = pd.concat(
        [_G_FUNDS.assign(source="Scored scheme")] +
        ([pd.DataFrame([{"isin": r.get("isin") or "", "scheme": r.get("name"),
                         "category": r.get("sub_category") or r.get("category") or "",
                         "call": r.get("rec") or "No View",
                         # THE REASON THE ROW CARRIES, not a coverage disclaimer. PPF, SCSS and
                         # the ULIP are Retains with a written reason apiece; the workbook printed
                         # "Outside the coverage of the firm's fund-quality frameworks" against
                         # all three, which is both the wrong sentence and, as an explanation of
                         # why a holding is being kept, untrue.
                         "rationale": (r.get("structural_reason")
                                       or "Outside the coverage of the firm's "
                                          "fund-quality frameworks."),
                         "asset_class": r.get("asset_class") or "", "value": r.get("value_inr") or 0.0,
                         "invested": r.get("cost_inr") or 0.0,
                         "weight_pct": r.get("weight_pct") or 0.0,
                         "risk_band": r.get("risk_band"), "liq_band": r.get("liq_band"),
                         "source": "Held, no scheme-level match"}
                        for r in (equity_rows + other_rows)])] if (equity_rows or other_rows) else []),
        ignore_index=True)
    # THIS FILE GOES TO THE CLIENT, so it obeys the same rules the slides do. It was shipping the
    # framework's internal name in 24 rationale cells and raw field names as column headings
    # (asset_class, hit_rate, trim_to_pct), both of which the deck's own tell-scanner exists to
    # catch and neither of which it can see, because it only reads PowerPoint.
    _G_ALL["rationale"] = (_G_ALL["rationale"].astype(str)
                           .str.replace("QFRA Framework", _HOUSE_NAME, regex=False)
                           .str.replace("QFRA-2", _HOUSE_NAME, regex=False)
                           .str.replace("QFRA-1", _HOUSE_NAME, regex=False)
                           .str.replace("QFRA", _HOUSE_NAME, regex=False))
    _COLS = {"isin": "ISIN", "scheme": "Holding", "category": "Category", "call": "Our call",
             "rationale": "Why", "asset_class": "Asset class", "value": "Value (Rs)",
             "invested": "Invested (Rs)", "folios": "Folios", "holders": "Holders",
             "score": "Fund score /100", "consistency": "Steadiness /100",
             "hit_rate": "Months ahead of peers (%)", "months": "Months of record",
             "weight_pct": "Weight (% of portfolio)", "trim_to_pct": "Trim to (% of portfolio)",
             "trim_value": "Trim amount (Rs)", "risk_band": "Risk band",
             "liq_band": "Liquidity band", "source": "Coverage"}
    _G_ALL.rename(columns=_COLS).to_excel(
        os.path.join(out_dir, f"{safe}_Holdings.xlsx"), index=False)
    ips_path = os.path.join(out_dir, f"{safe}_IPS_{a.profile}.xlsx")
    IPSB.write_workbook(IPS, ips_path, client=a.client, as_of=ver["as_of"])
    if len(E):
        E.to_csv(os.path.join(out_dir, f"{safe}_Holdings_Without_Scheme_Match.csv"), index=False)

    n = len(deck.prs.slides._sldIdLst)
    print(f"  deck      : {n} slides -> {deck_path}")
    print(f"  workbook  : {safe}_Holdings.xlsx")
    print(f"  IPS       : {os.path.basename(ips_path)}")
    if len(E):
        print(f"  reference : {safe}_Holdings_Without_Scheme_Match.csv  ({len(E)} rows, all of "
              f"them already counted in the portfolio)")


if __name__ == "__main__":
    main()
