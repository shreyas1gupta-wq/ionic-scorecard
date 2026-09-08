# -*- coding: utf-8 -*-
"""Publish the direct-equity calls for the deck kit, the same shape the fund score file has.

WHY THIS EXISTS. The kit has always joined SCHEMES to a central score file on ISIN, and had nothing
at all for a direct share, so every share in a client book rendered as No View. On a family holding
139 direct positions that meant the deck told the client the desk had no opinion on 27 stocks it has
actually called Sell. The Stock Scorecard 750 already holds those calls; they were simply never
published in a shape the kit could read.

THE CALL, and the order of precedence is the frozen method's, not this file's:
  the analyst's own `your_recommendation` in pf_qual_<SYMBOL>.json wins wherever research exists,
  the quant `recommendation_v3` stands where it does not,
  and a name in neither is No View, which is the correct answer rather than a gap to fill.

The join key out of a client statement is the ISIN, so the symbol is resolved through the exchange's
own ISIN master. Nothing here is matched by name.

Like the fund score file this is PRODUCTION output: it is gitignored, and it is not for the public
repository.
"""
import glob
import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SC = os.path.join(ROOT, "04_RND_LAB", "STOCK_SCORECARD_750", "results")
MASTER = os.path.join(ROOT, "05_DATA_OFFICE", "data", "isin_master.csv")
OUT_DIR = os.path.join(os.path.dirname(ROOT), "ionic-deck-kit", "scores")

# The client-facing verdict vocabulary. The scorecard speaks Sell/Hold only, by construction: this
# review never issues a Buy on a holding the client already owns.
VOCAB = {"sell": "Sell", "hold": "Hold", "trim": "Trim",
         "no recommendation": "No View", "": "No View"}


def _analyst(sym):
    p = os.path.join(SC, "pf_qual_%s.json" % sym)
    if not os.path.exists(p):
        return {}
    try:
        return json.load(open(p, encoding="utf-8")) or {}
    except Exception:
        return {}


def main(as_of="2026-07-26"):
    q = pd.read_csv(os.path.join(SC, "full750_scored_v3.csv")).drop_duplicates("symbol")
    m = pd.read_csv(MASTER)
    s2i = dict(zip(m["symbol"].astype(str).str.strip(), m["isin"].astype(str).str.strip()))
    s2n = dict(zip(m["symbol"].astype(str).str.strip(), m["company_name"].astype(str).str.strip()))

    rows, no_isin = [], 0
    for _, r in q.iterrows():
        sym = str(r["symbol"]).strip()
        isin = s2i.get(sym)
        if not isin:
            no_isin += 1
            continue
        a = _analyst(sym)
        call = str(a.get("your_recommendation") or r.get("recommendation_v3") or "").strip()
        call = VOCAB.get(call.lower(), call.title() if call else "No View")
        rows.append({
            "isin": isin,
            "symbol": sym,
            "company": s2n.get(sym, sym),
            "sector": r.get("sector"),
            "ionic_score": r.get("ionic_score_v3"),
            "score_3y": r.get("final_score_3y_v3"),
            "score_1y": r.get("final_score_1y_v3"),
            "call": call,
            "call_source": ("Analyst" if a.get("your_recommendation") else
                            ("Quant" if r.get("recommendation_v3") else "None")),
            "growth_pct": a.get("expected_next_3y_growth_pct"),
            "rationale": (a.get("recommendation_rationale") or a.get("summary") or "").strip(),
            "negative_para": (a.get("negative_para") or "").strip(),
            "positive_para": (a.get("positive_para") or "").strip(),
            "reverse_dcf": (a.get("reverse_dcf_judgment") or "").strip(),
            "summary": (a.get("summary") or "").strip(),
        })

    D = pd.DataFrame(rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "ionic_stock_scores_%s.csv" % as_of)
    D.to_csv(path, index=False)

    print("  wrote %s" % path)
    print("  %d stocks published, %d skipped for having no ISIN in the master" % (len(D), no_isin))
    print("  calls: " + "  ".join("%s %d" % (k, v) for k, v in D["call"].value_counts().items()))
    print("  call source: " + "  ".join("%s %d" % (k, v)
                                        for k, v in D["call_source"].value_counts().items()))
    print("  analyst rationale present on %d, negative_para on %d"
          % ((D["rationale"].str.len() > 0).sum(), (D["negative_para"].str.len() > 0).sum()))
    return path


if __name__ == "__main__":
    main()
