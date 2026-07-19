"""
Value probe (DATA-PREP task, librarian-directed): does transcript TEXT carry any
directional signal for forward returns?

HONESTY NOTE: concall_rubric.llm_score_dimension() is an explicit STUB (not fabricated,
not implemented -- see file header, hard rule against fabrication). There is no real
LLM-graded rubric score to correlate. This script instead builds a crude MECHANICAL proxy
(keyword-hit density from concall_rubric.DIMENSIONS: positive/constructive dimensions minus
the one red_flag_language dimension, per 1000 words) purely as a directional smoke test.
This is NOT the rubric score and must not be reported as such. [INFERENCE]
"""
import sys, os, re, json
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\src\themes")
import pandas as pd
import numpy as np
from concall_rubric import TranscriptStore, DIMENSIONS, split_sentences, _month_year_key, _MONTHS

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
ALPHA = os.path.join(BASE, "ALPHA_RANKER")
OUT = os.path.join(ALPHA, "results", "CONCALL_VALUE_PROBE_20260717")

store = TranscriptStore()
tickers = sorted(set(f.split("_")[0] for f in store._folders if f.endswith("_transcript")))
print(f"tickers with transcript text in zip: {len(tickers)}")

cube = pd.read_parquet(os.path.join(ALPHA, "rnd", "panel", "cube_close.parquet"))
cube.index = pd.to_datetime(cube.index)
cube = cube.sort_index()

pos_dims = [d for d in DIMENSIONS if not d.is_redflag]
neg_dims = [d for d in DIMENSIONS if d.is_redflag]

def quarter_label_to_date(label):
    m = re.match(r"([A-Za-z]{3})-(\d{4})", label)
    if not m:
        return None
    mon, yr = m.group(1), int(m.group(2))
    monnum = _MONTHS.get(mon)
    if not monnum:
        return None
    # earnings-call date proxy: mid-month of the label month (calls cluster ~15th-30th)
    return pd.Timestamp(year=yr, month=monnum, day=20)

def fwd_return(ticker, asof, horizon_days):
    if ticker not in cube.columns:
        return None
    ser = cube[ticker].dropna()
    if ser.empty:
        return None
    pos = ser.index.searchsorted(asof)
    if pos >= len(ser):
        return None
    t0 = ser.index[pos]
    p0 = ser.iloc[pos]
    t1_pos = pos + horizon_days
    if t1_pos >= len(ser):
        return None
    p1 = ser.iloc[t1_pos]
    if p0 in (0, None) or pd.isna(p0) or pd.isna(p1):
        return None
    return (p1 / p0) - 1.0

rows = []
n_done = 0
for t in tickers:
    quarters = store.list_quarters(t, "transcript")
    for q in quarters:
        try:
            text = store.load_text(t, q, "transcript")
        except Exception:
            continue
        sentences = split_sentences(text)
        nwords = max(len(text.split()), 1)
        pos_hits = 0
        for d in pos_dims:
            pats = [re.compile(p, re.IGNORECASE) for p in d.keywords]
            pos_hits += sum(1 for s in sentences if any(p.search(s) for p in pats))
        neg_hits = 0
        for d in neg_dims:
            pats = [re.compile(p, re.IGNORECASE) for p in d.keywords]
            neg_hits += sum(1 for s in sentences if any(p.search(s) for p in pats))
        proxy_score = (pos_hits - neg_hits) / (nwords / 1000.0)
        asof = quarter_label_to_date(q)
        if asof is None:
            continue
        r1q = fwd_return(t, asof, 63)
        r1y = fwd_return(t, asof, 252)
        rows.append(dict(ticker=t, quarter=q, asof=str(asof.date()), nwords=nwords,
                          pos_hits=pos_hits, neg_hits=neg_hits, proxy_score=proxy_score,
                          fwd_1q=r1q, fwd_1y=r1y))
    n_done += 1
    if n_done % 25 == 0:
        print(f"...{n_done}/{len(tickers)} tickers processed")

df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, "transcript_proxy_scores.csv"), index=False)
print(f"total transcript-quarter rows: {len(df)}")

def report_corr(sub, col, label):
    s = sub.dropna(subset=["proxy_score", col])
    if len(s) < 20:
        print(f"{label}: n={len(s)} too small, skip")
        return
    pear = s["proxy_score"].corr(s[col])
    spear = s["proxy_score"].corr(s[col], method="spearman")
    print(f"{label}: n={len(s)}  pearson={pear:.4f}  spearman={spear:.4f}")

print("\n--- POOLED (all ticker-quarters) ---")
report_corr(df, "fwd_1q", "proxy_score vs fwd_1q")
report_corr(df, "fwd_1y", "proxy_score vs fwd_1y")

# cross-sectional-only version: rank-demean proxy_score and fwd ret within each quarter label
df["q_key"] = df["quarter"].apply(_month_year_key)
xs = df.copy()
for col in ["proxy_score", "fwd_1q", "fwd_1y"]:
    xs[col + "_xs"] = xs.groupby("quarter")[col].transform(lambda s: s - s.mean())

print("\n--- CROSS-SECTIONAL (demeaned within same call-quarter, isolates stock-picking signal from market beta) ---")
xs_q = xs[["proxy_score_xs", "fwd_1q_xs"]].rename(columns={"proxy_score_xs": "proxy_score", "fwd_1q_xs": "fwd_1q"})
xs_y = xs[["proxy_score_xs", "fwd_1y_xs"]].rename(columns={"proxy_score_xs": "proxy_score", "fwd_1y_xs": "fwd_1y"})
report_corr(xs_q, "fwd_1q", "xs proxy_score vs xs fwd_1q")
report_corr(xs_y, "fwd_1y", "xs proxy_score vs xs fwd_1y")

with open(os.path.join(OUT, "SUMMARY.txt"), "w") as f:
    f.write(f"rows={len(df)} tickers={df['ticker'].nunique()}\n")
    for col in ["fwd_1q", "fwd_1y"]:
        s = df.dropna(subset=["proxy_score", col])
        if len(s) >= 20:
            f.write(f"pooled {col}: pearson={s['proxy_score'].corr(s[col]):.4f} spearman={s['proxy_score'].corr(s[col],method='spearman'):.4f} n={len(s)}\n")
    for col in ["fwd_1q_xs", "fwd_1y_xs"]:
        s = xs.dropna(subset=["proxy_score_xs", col])
        if len(s) >= 20:
            f.write(f"cross-sectional {col}: pearson={s['proxy_score_xs'].corr(s[col]):.4f} spearman={s['proxy_score_xs'].corr(s[col],method='spearman'):.4f} n={len(s)}\n")
print("\nsaved:", OUT)
