"""
S6 NO-NEGATIVE-NEWS screen builder (ALPHA_RANKER, wave4).
Deterministic, rule-based (regex/keyword) severity tagging over the
`direct_news` field of datasets/india_fin_news/tier_segregated_news.csv
(55-symbol, 2020-01-01..2026-03-31 daily grid). No randomness, no LLM calls.
"""
import re
import pandas as pd
import numpy as np

SRC = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets\india_fin_news\tier_segregated_news.csv"
OUT_PARQUET = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\rnd\scorecard\no_negative_news_screen.parquet"

# ---------------------------------------------------------------------------
# Deterministic keyword lexicon. Severity 3 = most severe (fraud/auditor),
# 2 = regulatory/credit/promoter/guidance, 1 = litigation/generic adverse.
# All matching is case-insensitive substring/regex on the `direct_news` text
# blob for that (symbol, date) only -- sectoral_news / global_news are NOT
# used (they are not company-specific and would false-positive every stock
# in a sector/the whole market on the same day).
# ---------------------------------------------------------------------------
CATEGORIES = {
    "FRAUD_ACCOUNTING": (3, [
        r"\bfraud\b", r"forensic audit", r"accounting (discrepanc|irregularit|lapse)",
        r"financial irregularit", r"books? (were|was) cooked", r"whistleblow",
        r"sebi (probe|investigat|bars|debars|ban(s|ned)?)\b.*\b(company|firm|promoter)",
        r"restat(e|ement) of (accounts|financials|results)", r"misstatement of (accounts|financials)",
        r"hindenburg", r"short seller report", r"stock manipulation", r"round.tripping",
        r"siphon(ing|ed)? of funds", r"diversion of funds", r"shell compan",
        r"derivatives? (accounting )?(discrepanc|lapse|discovery)",
    ]),
    "AUDITOR_RESIGNATION": (3, [
        r"auditor (resign|steps? down|quit)", r"resignation of (the )?(statutory )?auditor",
        r"statutory auditor resign", r"auditor withdr(aw|ew|awal)",
    ]),
    "REGULATORY_ACTION": (2, [
        r"sebi (order|ban|bars|debars|penal(ty|ises|izes)|show.cause)",
        r"rbi (bans?|restricts?|cancels? licen[cs]e|penal(ty|ises|izes)|action against)",
        r"cci (probe|penal(ty|ises|izes)|order against)",
        r"\bed raids?\b", r"income tax raid", r"\braided\b", r"search and seizure",
        r"licen[cs]e (cancel(l)?ed|revoked|suspended)",
        r"market regulator (action|order|ban)", r"regulatory action against",
        r"cbi (probe|raids?|files? case|chargesheet)", r"enforcement directorate",
    ]),
    "CREDIT_DOWNGRADE": (2, [
        # Require an actual rating-agency name near "downgrade" -- deliberately
        # EXCLUDES generic brokerage stock-rating downgrades ("JPMorgan downgrades
        # to Neutral", "Nuvama downgrades to Hold"), which are analyst opinion,
        # not a credit/issuer-rating action. Confirmed false-positive in v1 (bare
        # "downgrad*" matched 674 rows, mostly brokerage stock-call downgrades).
        r"(crisil|icra|care ratings?|india ratings?|moody'?s|s&p( global)?|fitch)\b[^.]{0,80}downgrad",
        r"downgrad\w*[^.]{0,80}(crisil|icra|care ratings?|india ratings?|moody'?s|s&p( global)?|fitch)",
        r"credit rating (downgrad\w*|cut|lowered)", r"rating downgraded (to|from)",
        r"outlook (revised|changed) to negative", r"default(ed)? on (interest|repayment|loan|bond|debt)",
        r"npa surge", r"bond rating cut", r"downgraded to (junk|default status)",
    ]),
    "PROMOTER_ISSUE": (2, [
        # Directional only: pledge INCREASE / invocation / high absolute level.
        # Deliberately EXCLUDES bare "promoter pledge" mentions -- v1's bare
        # pattern false-positived on pledge REDUCTIONS ("reduces promoter pledge
        # from 8.9% to 3.09%", "Sun Pharma reduced promoter pledging... shares
        # rose 16%"), which are GOOD news, opposite sign.
        r"promoter pledg\w* (increase|rise|rising|surge|jump|steepest jump|higher)",
        r"pledged shares? (surge|rise|increase|higher)",
        r"(highest|elevated) promoter pledg", r"invocation of pledged shares",
        r"invok\w* (of )?pledged shares", r"promoter stake sale",
        r"promoter (resign|steps? down|arrested|investigat)",
        r"founder steps? down", r"founder resign", r"promoter group.{0,30}(default|invoke)",
    ]),
    "LITIGATION": (1, [
        r"class action (suit|lawsuit)", r"\blawsuit\b", r"\blitigation\b",
        r"court (order|ruling) against", r"penalty imposed on", r"\bfined\b.{0,30}(crore|lakh|million)",
    ]),
    "GUIDANCE_CUT": (2, [
        r"guidance cut", r"lower(ed|s) (its |the )?guidance", r"profit warning",
        r"warns? of (weak|lower|decline)", r"miss(es|ed) estimates", r"steep decline in (profit|net profit)",
        r"loss widens", r"downgrades? (its )?outlook", r"warns? investors",
    ]),
    "MGMT_EXIT": (1, [
        r"resignation of (the )?ceo\b", r"resignation of (the )?cfo\b", r"ceo (resigns?|steps? down|quits)",
        r"cfo (resigns?|steps? down|quits)", r"managing director resign",
    ]),
}

COMPILED = {
    cat: (sev, [re.compile(p, re.IGNORECASE) for p in pats])
    for cat, (sev, pats) in CATEGORIES.items()
}


def classify(text: str):
    """Return (max_severity, sorted_category_list, matched_snippet)."""
    if not isinstance(text, str) or not text:
        return 0, "", ""
    hits = []
    max_sev = 0
    snippet = ""
    for cat, (sev, regexes) in COMPILED.items():
        for rx in regexes:
            m = rx.search(text)
            if m:
                hits.append(cat)
                if sev > max_sev:
                    max_sev = sev
                    start = max(0, m.start() - 60)
                    end = min(len(text), m.end() + 60)
                    snippet = text[start:end].replace("\n", " ")
                break  # one hit per category is enough
    return max_sev, "|".join(sorted(set(hits))), snippet


def main():
    print("Loading tier_segregated_news.csv (date, symbol, direct_news only)...")
    df = pd.read_csv(SRC, usecols=["date", "symbol", "direct_news"])
    print("rows:", len(df))
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    print("Classifying (deterministic keyword scan)...")
    results = df["direct_news"].fillna("").map(classify)
    df["negative_severity_raw"] = [r[0] for r in results]
    df["negative_event_categories"] = [r[1] for r in results]
    df["matched_snippet"] = [r[2] for r in results]
    df["direct_news_available"] = df["direct_news"].fillna("").str.len() > 0

    # Trailing 20-trading-day max severity (rolling max INCLUDING current day).
    # PIT note: the raw same-day severity for date T uses only T's own news
    # text (EOD-conservative: treat as available only from T's close onward,
    # i.e. usable for T+1 decisions, never for a T-open decision). The
    # rolling window is a per-symbol trailing max over the row-ordered daily
    # grid (no future rows touched).
    def roll_max(g):
        return g["negative_severity_raw"].rolling(window=20, min_periods=1).max()

    df["negative_severity_trail20"] = df.groupby("symbol", group_keys=False).apply(roll_max)
    df["no_negative_news_flag"] = df["negative_severity_trail20"] == 0

    out_cols = [
        "date", "symbol", "direct_news_available",
        "negative_event_categories", "negative_severity_raw",
        "negative_severity_trail20", "no_negative_news_flag", "matched_snippet",
    ]
    out = df[out_cols].copy()
    out.to_parquet(OUT_PARQUET, index=False)
    print("Wrote:", OUT_PARQUET, "rows:", len(out))

    print("\n--- severity_raw value counts ---")
    print(out["negative_severity_raw"].value_counts().sort_index())
    print("\n--- severity_trail20 value counts ---")
    print(out["negative_severity_trail20"].value_counts().sort_index())
    print("\n--- category hit counts (raw, same-day) ---")
    cats = out.loc[out["negative_event_categories"] != "", "negative_event_categories"].str.split("|").explode()
    print(cats.value_counts())


if __name__ == "__main__":
    main()
