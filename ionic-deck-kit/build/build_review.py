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
import engine as ENG                                                       # noqa: E402
import tiers                                                               # noqa: E402

ORDER = {"Sell": 0, "Trim": 1, "Hold (watch)": 2, "Hold": 3, "No View": 4}
HELD = ("Hold", "Hold (watch)")
# every module that needs direct equity, plus the ones needing data a statement never carries
SKIP = {"score_method", "book_scored", "equity_book", "sell_list", "hold_rationale",
        "mcap_positioning", "sector_exposure", "funds_debt", "mf_methodology",
        "scheme_correlation", "tax_impact"}
KEEP_ANNEX = {"holdings_detail", "appendix"}


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
    G = (M.groupby(["isin", "scheme", "category", "call", "rationale"], dropna=False)
         .agg(value=("value", "sum"), invested=("invested", "sum"),
              folios=("folio", "nunique"), holders=("holder", "nunique"),
              score=("score", "first")).reset_index())
    G["_o"] = G["call"].map(ORDER).fillna(9)
    G = G.sort_values(["_o", "value"], ascending=[True, False]).drop(columns="_o")
    GRAND = float(G["value"].sum())
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
        t["optional_on"] = set(t["optional_on"]) & KEEP_ANNEX
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
                  structural_reason=r.rationale, bench_label="", exemplar="-",
                  hit3y=None, alpha_t=None, ter=None, up_capture=None, down_capture=None,
                  max_dd=None, worst_1y=None, sortino=None, calmar=None, cagr3y=None,
                  bench_cagr3y=None, alpha_ann=None, info_ratio=None, r2=None, flags=[],
                  perf_flag=(r.call in ("Sell", "Trim", "Hold (watch)")))
             for r in G.itertuples()]

    ctx = {
        "client": {"name": a.client, "code": "-", "account_type": "Portfolio review",
                   "profile": "-", "horizon": "-", "construction": "Mutual funds",
                   "aum_inr": GRAND, "as_of": ver["as_of"]},
        "ips": {"on_file": False, "single_name_cap_pct": 8.0, "single_amc_cap_pct": None,
                "locked_in_cap_pct": None, "cash_cap_pct": None, "alloc_bands": {},
                "mcap_bands": {}, "risk_tier": None, "objective": None, "horizon_yrs": None},
        "funds": funds, "equity": [], "fund_churn": {},
        "totals": {"grand_inr": GRAND, "eq_pct": 0.0, "mf_pct": 100.0, "cash_pct": 0.0,
                   "n_stocks": 0, "n_funds": len(funds),
                   "n_sell": int((G["call"] == "Sell").sum()),
                   "n_trim": int((G["call"] == "Trim").sum()),
                   "n_hold": int(G["call"].isin(HELD).sum()),
                   "top10_pct": round(G["weight_pct"].nlargest(10).sum(), 1),
                   "lookthrough": {}},
        "house_view": {"stance": {"Domestic equity": "Constructive, quality-biased",
                                  "Foreign equity": "none held", "Gold & silver": "held",
                                  "Momentum": "Neutral", "Low-vol / value": "Favoured"},
                       "alloc_gap": {}, "sector_bands": {}},
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
    deck, manifest = ENG.build(ctx, a.tier, verbose=False)
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
