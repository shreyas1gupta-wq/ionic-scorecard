# -*- coding: utf-8 -*-
"""Publish the direct-equity calls for the deck kit, the same shape the fund score file has.

WHY THIS EXISTS. The kit has always joined SCHEMES to a central score file on ISIN, and had nothing
at all for a direct share, so every share in a client book rendered as No View. On a family holding
139 direct positions that meant the deck told the client the desk had no opinion on 27 stocks it has
actually called Sell. The Stock Scorecard 750 already holds those calls; they were simply never
published in a shape the kit could read.

THE CALL, in strict order of precedence:

  1. THE HOUSE VIEW wins wherever it carries the name, including where it says No View. It is the
     firm's published position on a stock and the client-facing deck cannot contradict it. Against
     the scorecard it disagrees on 97 of the 384 names both cover, and not in one direction: 59
     the scorecard would sell it holds, 38 it would hold it sells. Shipping the scorecard's answer
     put a Sell on Hindustan Aeronautics, Reliance, Bharat Dynamics, Thermax, Bajaj Auto and Vedanta
     in a client deck while the house view held every one of them.
  2. The analyst's own `your_recommendation` in pf_qual_<SYMBOL>.json, for a name the house view
     does not cover.
  3. The quant `recommendation_v3`, where there is no analyst research either.
  4. No View, which is the correct answer for a name in none of them rather than a gap to fill.

AND THE REASONING HAS TO FOLLOW THE CALL. Where the house view overrides the analyst, the analyst's
rationale is arguing the OTHER case, so printing it under a house-view call would contradict the
call it sits beneath. In that situation the rationale is dropped and the house view's own four
attributes, operating margin, ROE, valuation and growth, carry the reasoning instead.

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


HOUSE_VIEW_XLSX = os.path.join(os.path.expanduser("~"), "Downloads", "STOCK REVIEW FINAL.xlsx")


def _house_view():
    """The firm's published stock view, keyed on ISIN. Absent, this file falls back to the
    scorecard and says so; the deck is then the scorecard's answer, not the house's."""
    if not os.path.exists(HOUSE_VIEW_XLSX):
        print("  NO HOUSE VIEW FILE at %s" % HOUSE_VIEW_XLSX)
        print("  Calls will come from the scorecard alone. That is NOT the firm's published view.")
        return {}
    h = pd.read_excel(HOUSE_VIEW_XLSX)
    h.columns = [str(c).strip() for c in h.columns]
    out = {}
    for _, r in h.iterrows():
        isin = str(r.get("ISIN") or "").strip()
        if len(isin) != 12:
            continue
        call = str(r.get("Views") or "").strip()
        # the sheet mixes "Hold" and "HOLD"; they are the same call
        call = VOCAB.get(call.lower(), call.title() if call else "No View")
        out[isin] = {"call": call,
                     "margin": str(r.get("Op. Margin %") or "").strip(),
                     "roe": str(r.get("ROE") or "").strip(),
                     "valuation": str(r.get("Valuations") or "").strip(),
                     "growth": str(r.get("Growth") or "").strip(),
                     "cap": str(r.get("Categorization as per SEBI Circular dated Oct 6, 2017")
                                or "").strip()}
    print("  house view : %d names read from %s" % (len(out), os.path.basename(HOUSE_VIEW_XLSX)))
    return out


# WORDS THAT LEAN. An attribute reads as an argument for holding or against it, and which side a
# word falls on decides whether the sentence built from it supports the call above it.
_FAVOURABLE = ("strong", "excellent", "high", "good", "reasonable", "attractive", "cheap",
               "undervalued", "growth", "improving", "expanding")
_ADVERSE = ("weak", "poor", "low", "declining", "falling", "expensive", "rich", "stretched",
            "overvalued", "lacks growth", "no growth", "deteriorating", "compressing")


def _leans(text):
    """+1 favourable, -1 adverse, 0 neutral. Longest match wins, so "lacks growth" beats "growth"."""
    low = " " + str(text or "").lower() + " "
    hits = [(len(w), -1) for w in _ADVERSE if w in low] +            [(len(w), +1) for w in _FAVOURABLE if w in low]
    return max(hits)[1] if hits else 0


def _hv_reason(hv, call=""):
    """The house view's own four attributes, as a sentence that LEANS WITH THE CALL.

    This carries the reasoning wherever the house view overrides an analyst who argued the other
    way, and it was building the sentence out of all four attributes regardless of what they said.
    On the current file that put "operating margin strong, ROE strong, valuation reasonable,
    growth" underneath a red SELL pill on four of fourteen Sell rows in a client deck. A client
    either disbelieves the call or disbelieves the page, and either way the deck has argued against
    itself in the one place it had to be persuasive.

    So on a Sell the sentence carries the adverse attributes only. Where the house view records
    none, the honest sentence is that the call is a published view and the attributes do not
    explain it -- not a recital of the favourable ones.
    """
    pairs = [("operating margin " + hv["margin"].lower()) if hv["margin"] else "",
             ("ROE " + hv["roe"].lower()) if hv["roe"] else "",
             ("valuation " + hv["valuation"].lower()) if hv["valuation"] else "",
             (hv["growth"].lower()) if hv["growth"] else ""]
    bits = [b for b in pairs if b]
    if not bits:
        return "The firm's published view on this holding."
    _sell = str(call or "").strip().lower() in ("sell", "trim")
    if _sell:
        adverse = [b for b in bits if _leans(b) < 0]
        if adverse:
            return ("The firm's published view, on which this call rests: "
                    + ", ".join(adverse) + ".")
        return ("A published call of the firm's, held despite the fundamentals reading "
                "adequately: " + ", ".join(bits) + ". The desk's reasoning is on file.")
    return "The firm's published view: " + ", ".join(bits) + "."


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

    HV = _house_view()

    rows, no_isin = [], 0
    for _, r in q.iterrows():
        sym = str(r["symbol"]).strip()
        isin = s2i.get(sym)
        if not isin:
            no_isin += 1
            continue
        a = _analyst(sym)
        hv = HV.get(isin)
        _analyst_call = VOCAB.get(str(a.get("your_recommendation") or "").strip().lower(),
                                  str(a.get("your_recommendation") or "").strip().title())
        if hv is not None:
            call, src = hv["call"], "House view"
        elif a.get("your_recommendation"):
            call, src = _analyst_call, "Analyst"
        else:
            call = str(r.get("recommendation_v3") or "").strip()
            call = VOCAB.get(call.lower(), call.title() if call else "No View")
            src = "Quant" if call != "No View" else "None"
        # the reasoning must not argue against the call printed above it
        _overridden = hv is not None and _analyst_call and _analyst_call != hv["call"]
        rows.append({
            "isin": isin,
            "symbol": sym,
            "company": s2n.get(sym, sym),
            "sector": r.get("sector"),
            "ionic_score": r.get("ionic_score_v3"),
            "score_3y": r.get("final_score_3y_v3"),
            "score_1y": r.get("final_score_1y_v3"),
            "call": call,
            "call_source": src,
            "house_cap": (hv or {}).get("cap", ""),
            "growth_pct": (None if _overridden else a.get("expected_next_3y_growth_pct")),
            "rationale": (_hv_reason(hv, call) if _overridden else
                          (a.get("recommendation_rationale") or a.get("summary") or "").strip()
                          or (_hv_reason(hv, call) if hv else "")),
            "negative_para": ("" if _overridden else (a.get("negative_para") or "").strip()),
            "positive_para": ("" if _overridden else (a.get("positive_para") or "").strip()),
            "reverse_dcf": ("" if _overridden else (a.get("reverse_dcf_judgment") or "").strip()),
            "summary": ("" if _overridden else (a.get("summary") or "").strip()),
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
