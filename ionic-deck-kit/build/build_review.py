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
SKIP = {"score_method", "book_scored", "equity_book", "sell_list", "hold_rationale",
        "sector_exposure", "funds_debt",
        "scheme_correlation", "tax_impact"}
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

    print(f"  calls     : " + "  ".join(f"{k} {v}" for k, v in G["call"].value_counts().items()))

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
        rec = dict(name=o["name"], value_inr=o["value"], weight_pct=round(w, 2),
                   asset_class=o["asset_class"], sub_category=o["sub_category"],
                   amc=(_mgr or "-"),
                   rec="No View", verdict="No View", sector=None, ionic_score=None)
        (equity_rows if _isdirect(o) else other_rows).append(rec)
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
    _bands, _mcap = RL.load_bands()
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

    _SELL_VAL = sum(f["value_inr"] for f in funds if f["verdict"] == "Sell")
    _TRIM_VAL = sum(f.get("trim_value_inr") or 0.0 for f in funds if f["verdict"] == "Trim")

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
                "cash_cap_pct": float(_pb["Cash and equivalents"][1]),
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
                "international_equity_cap_pct": _prof["equity"]["International equity"][1],
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
                   "n_sell": int((G["call"] == "Sell").sum()),
                   "n_trim": int((G["call"] == "Trim").sum()),
                   "n_hold": int(G["call"].isin(HELD).sum()),
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
        "tax": {"fund_rows": [], "gross": 0, "ltcg": 0, "stcg": 0, "net": 0},
        # REAL money, from the calls this run actually issued. Zeros here printed "Rs 0.0 L gross
        # freed" on the priority-actions page three lines above "Rs 96.29 Cr" of fund actions on
        # the same page. A Sell frees the whole position; a Trim frees only the slice above the
        # cap, which is trim_value_inr and never the position. Tax is NOT netted off: a holdings
        # statement carries no acquisition date and no lot history, so the rate cannot be known,
        # and the page says the figure is before tax rather than quietly showing a gross number
        # under a net label.
        "deployment": {"proceeds_inr": _SELL_VAL + _TRIM_VAL, "tax_leak_inr": None,
                       "net_inr": None, "personalization": []},
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
            "no_view": [{"name": r.scheme, "category": r.category,
                         "reason": "Outside the coverage of the firm's fund-quality frameworks."}
                        for r in G[G["call"] == "No View"].itertuples()],
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

    G.to_excel(os.path.join(out_dir, f"{safe}_Holdings.xlsx"), index=False)
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
