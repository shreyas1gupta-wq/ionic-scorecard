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
        "mcap_positioning", "sector_exposure", "funds_debt",
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
        print(f"    {notes['exceptions']} row(s) could not be resolved, written to the exceptions file")

    # ---- 2. look up the central calls ------------------------------------------------------------
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
    G = (M.groupby(["isin", "scheme", "category", "call", "rationale"], dropna=False)
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

    funds = [dict(name=r.scheme, isin=r.isin, category="equity", plan="",
                  amc="-", sebi_category=r.category,
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
                  qfra=(None if pd.isna(r.score) else float(r.score)), merit=None,
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
        rec = dict(name=o["name"], value_inr=o["value"], weight_pct=round(w, 2),
                   asset_class=o["asset_class"], sub_category=o["sub_category"],
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
        po, go = RL.attach(other_rows, _bands, _mcap, "other")
        placed, gap = pf + pe + po, gf + ge + go
        total_rows = len(funds) + len(equity_rows) + len(other_rows)
        print(f"    risk and liquidity bands on {placed} of {total_rows} holdings"
              + (f"; Rs {gap:,.0f} carries no band and is reported as such" if gap else ""))
    else:
        print("    no risk/liquidity band file in scores/, so those pages will not render")

    ctx = {
        "client": {"name": a.client, "code": "-", "account_type": "Portfolio review",
                   "profile": "-", "horizon": "-", "construction": "Mutual funds",
                   "aum_inr": GRAND, "as_of": ver["as_of"]},
        # THE MANDATE, from the firm's Risk and Liquidity framework rather than left blank. These
        # are the Aggressive profile's caps (Principal, 2026-09-07: equity band 80-100%). Every one
        # is tested on the WHOLE book, so an AIF or a direct share counts toward the equity band and
        # toward the single-name cap exactly as a fund does.
        "ips": {"on_file": True,
                "risk_tier": "Aggressive",
                "objective": "Long-term capital growth with an equity-led core",
                "horizon_yrs": None,
                "alloc_bands": {"Equity": (80, 90, 100),
                                "Fixed Income": (0, 10, 20),
                                "Alternatives": (0, 5, 15),
                                "Cash": (0, 2, 10)},
                "single_name_cap_pct": 5.0,          # per ISIN, direct equity and single-issuer debt
                "single_amc_cap_pct": 20.0,          # measured on the manager, schemes aggregate
                "locked_in_cap_pct": 40.0,           # the illiquidity budget
                "unlisted_equity_cap_pct": 35.0,
                # exec_summary indexes these directly rather than with .get, so an IPS that is
                # on_file must carry them or the executive summary raises and the engine, which
                # swallows module exceptions, drops the page with no error on the deck.
                "foreign_target_pct": None, "gold_target_pct": None,
                "cash_cap_pct": None,
                "mcap_bands": {}, "constraints": [
                    "Minimum liquid buffer, Priority 1 assets, 5% of the book at every review.",
                    "High Risk and Low Liquidity together may not exceed 30% of the book.",
                    "Uncalled commitments up to 25% of corpus, tracked outside NAV."]},
        "funds": funds, "equity": equity_rows, "other": other_rows, "fund_churn": {},
        "profile": "Aggressive",
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
        # The gap is struck against the MANDATE bands above, not an invented house target, so the
        # page and the IPS page cannot disagree with each other.
        "house_view": {"stance": {"Domestic equity": "Constructive, quality-biased",
                                  "Foreign equity": "held via feeders",
                                  "Gold & silver": "held" if ALT_VAL else "none held",
                                  "Momentum": "Neutral", "Low-vol / value": "Favoured"},
                       "alloc_gap": {
                           "Equity": round(EQ_VAL / GRAND * 100 - 90, 1) if GRAND else 0.0,
                           "Debt/Hybrid": round(FI_VAL / GRAND * 100 - 10, 1) if GRAND else 0.0,
                           "Gold": round(ALT_VAL / GRAND * 100 - 5, 1) if GRAND else 0.0},
                       "sector_bands": {}},
        "tax": {"fund_rows": [], "gross": 0, "ltcg": 0, "stcg": 0, "net": 0},
        "deployment": {"proceeds_inr": 0, "tax_leak_inr": 0, "net_inr": 0, "personalization": []},
        "cost": {"reg_drag_inr": 0, "rows": []},
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
    if len(E):
        E.to_csv(os.path.join(out_dir, f"{safe}_EXCEPTIONS.csv"), index=False)

    n = len(deck.prs.slides._sldIdLst)
    print(f"  deck      : {n} slides -> {deck_path}")
    print(f"  workbook  : {safe}_Holdings.xlsx")
    if len(E):
        print(f"  exceptions: {safe}_EXCEPTIONS.csv  ({len(E)} rows)")


if __name__ == "__main__":
    main()
