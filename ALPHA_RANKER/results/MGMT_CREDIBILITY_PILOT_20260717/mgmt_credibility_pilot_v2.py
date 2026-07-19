"""
Management-Credibility Pilot v2 — P0 FIX: speaker-attributed guidance extraction.

Fixes the bug documented in ALPHA_RANKER/rnd/wave4/MGMT_COMMENTARY.md section 3:
the v1 regex had NO speaker attribution, so analyst QUESTIONS ("So just wanted to
know what is in the pipeline for the growth?") were counted as management
COMMITMENTS. This script:
  1. Parses each transcript's speaker turns and builds a per-call MANAGEMENT name
     roster (from the moderator intro + inline title mentions) and an ANALYST name
     roster (from "the line of <Name> from <Firm>" moderator cues) — both regex,
     no LLM, no invented labels.
  2. Segments the transcript into speaker turns and keeps ONLY management-labelled
     turns for commitment extraction (analyst questions AND moderator lines excluded).
  3. Re-extracts quantified guidance (revenue/margin/capex/debt) from management
     speech only, using the same 5 commit-type cue patterns as v1 (topic word AND
     a type-specific forward-looking cue word, co-occurring in one sentence).
  4. Delivery check: quarterly PIT actuals (datasets/earnings_pit/unified_quarterly_pit.parquet,
     real available_date) for revenue/margin; annual PIT actuals
     (ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet) for capex/debt
     (no quarterly cwip/borrowings series exists) — documented granularity gap, not
     silently glossed over. NEVER uses quarter-end date as the availability date
     (CLAUDE.md landmine #3).
  5. Base-rate + sector-demeaning for revenue/margin verdicts: company QoQ growth is
     compared against the SAME-QUARTER cross-sectional median growth (sector median
     if >=5 peers, else whole-sample median) before calling DELIVERED/MISSED/PARTIAL.
  6. Company-level credibility score (min 3 verifiable commitments) + a pilot
     forward-return test (sector-demeaned), with drop-one stability check.

No fabrication: every classification is a deterministic regex/lexicon rule; every
"don't know" case is left NO_MATCHING_ACTUAL_IN_WINDOW / NOT_VERIFIABLE, never imputed.
"""
from __future__ import annotations
import os, re, sys, json
import pandas as pd
import numpy as np

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, os.path.join(BASE, "ALPHA_RANKER", "src"))
from themes.concall_rubric import TranscriptStore, split_sentences  # noqa: E402

OUT_DIR = os.path.join(BASE, "ALPHA_RANKER", "results", "MGMT_CREDIBILITY_PILOT_20260717")
PRICES_DIR = os.path.join(BASE, "ALPHA_RANKER", "data", "prices")
SECTOR_MAP_PATH = os.path.join(BASE, "ALPHA_RANKER", "data", "universe", "sector_map.parquet")
QUARTERLY_PIT_PATH = os.path.join(BASE, "datasets", "earnings_pit", "unified_quarterly_pit.parquet")
ANNUAL_PIT_PATH = os.path.join(BASE, "ALPHA_RANKER", "data", "fundamentals", "MASTER_fundamentals_pit.parquet")

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def quarter_label_to_date(label: str) -> pd.Timestamp:
    """'Mon-YYYY' -> day-20 proxy (same convention v1 used; real RESULT DATE switch
    is a documented P1, out of scope for this P0-fix pass)."""
    m = re.match(r"([A-Za-z]{3})-(\d{4})", label)
    if not m:
        return pd.NaT
    mo = _MONTHS.get(m.group(1))
    if not mo:
        return pd.NaT
    return pd.Timestamp(year=int(m.group(2)), month=mo, day=20)


# ============================================================================
# 1. SPEAKER ROSTER EXTRACTION (P0 fix)
# ============================================================================

TITLE_WORDS = (r"(?:Chief\s+\w+\s+Officer|Chief\s+\w+|Managing\s+Director|CEO|CFO|COO|CTO|CIO|"
               r"President|Chairman|Chairperson|Whole[- ]?time\s+Director|Director|Founder|"
               r"Executive\s+Director|Vice\s+President|VP|Promoter|Head\s*[-–—]?\s*\w*)")
_NAME = r"[A-Z][a-zA-Z\.]+(?:\s+[A-Z][a-zA-Z\.]+){0,3}"
MGMT_INTRO_RE = re.compile(rf"(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s*({_NAME})\s*[-,–]?\s*(?:the\s+)?({TITLE_WORDS})")
ANALYST_RE = re.compile(rf"line of\s+({_NAME})\s*(?:from|\.|,|Please)")


def _clean_name(n: str) -> str:
    n = re.sub(r"\s+", " ", n.strip())
    return n.rstrip(".").rstrip(",").strip()


def build_rosters(full_text: str) -> tuple[set, set]:
    mgmt, analysts = set(), set()
    for m in MGMT_INTRO_RE.finditer(full_text):
        nm = _clean_name(m.group(1))
        words = nm.split()
        if 2 <= len(words) <= 4 and len(nm) < 45 and not nm.isupper():
            mgmt.add(nm)
    for m in ANALYST_RE.finditer(full_text):
        nm = _clean_name(m.group(1))
        words = nm.split()
        if 1 <= len(words) <= 3 and len(nm) < 40 and not nm.isupper():
            analysts.add(nm)
    analysts -= mgmt
    return mgmt, analysts


# ============================================================================
# 2. TURN SEGMENTATION — keep MANAGEMENT turns only
# ============================================================================

def segment_turns(text: str, mgmt_names: set, analyst_names: set) -> list[tuple[str, str]]:
    if not mgmt_names and not analyst_names:
        return [("UNKNOWN", text)]
    all_names = sorted(mgmt_names | analyst_names, key=len, reverse=True)
    name_alt = "|".join(re.escape(n) for n in all_names)
    line_start_re = re.compile(rf"^\s*[-–•]?\s*(?:Mr\.|Ms\.|Mrs\.|Dr\.)?\s*({name_alt})\b")
    mod_re = re.compile(r"^\s*[-–•]?\s*Moderator\b", re.IGNORECASE)

    turns, current_label, buf = [], "UNKNOWN", []
    for raw_line in text.split("\n"):
        line = raw_line.replace("​", "")
        if re.match(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", line, re.IGNORECASE):
            continue  # PDF page-number artifact, not transcript content
        m = line_start_re.match(line)
        if m:
            if buf:
                turns.append((current_label, " ".join(buf)))
            nm = m.group(1)
            current_label = "MANAGEMENT" if nm in mgmt_names else "ANALYST"
            buf = [line[m.end():]]  # drop the speaker-name prefix itself from the text
        elif mod_re.match(line):
            if buf:
                turns.append((current_label, " ".join(buf)))
            current_label = "MODERATOR"
            buf = [line]
        else:
            buf.append(line)
    if buf:
        turns.append((current_label, " ".join(buf)))
    return turns


def management_only_text(text: str, mgmt_names: set, analyst_names: set) -> str:
    """Concatenate MANAGEMENT-labelled turns only. A '.' is force-inserted between turns
    that don't already end in sentence punctuation, so split_sentences() (which collapses
    all whitespace before splitting) doesn't fuse the tail of one turn to the head of the
    next — otherwise page-break artifacts ('Page 7 of 14') and adjacent-turn text bleed
    into a single fake 'sentence'."""
    parts = []
    for lbl, t in segment_turns(text, mgmt_names, analyst_names):
        if lbl != "MANAGEMENT":
            continue
        t = t.strip()
        if not t:
            continue
        if not t.endswith((".", "!", "?")):
            t += "."
        parts.append(t)
    return " ".join(parts)


# ============================================================================
# 3. COMMITMENT EXTRACTION (5 types, topic-word AND forward-cue co-occurrence)
# ============================================================================

COMMIT_RULES = {
    "revenue": dict(
        topic=re.compile(r"\brevenue\b|\bsales\b|\btop[- ]line\b", re.I),
        cue=re.compile(r"\bgrowth\b|\bgrow\w*\b|\bguidance\b|\bguide\w*\b|\bexpect\w*\b|\btarget\w*\b|\boutlook\b", re.I),
    ),
    "margin": dict(
        topic=re.compile(r"\bmargin(s)?\b|\bOPM\b", re.I),
        cue=re.compile(r"\bexpect\w*\b|\btarget\w*\b|\bmaintain\w*\b|\bguidance\b|\bimprove\w*\b|\bsustain\w*\b", re.I),
    ),
    "capex": dict(
        topic=re.compile(r"\bcapex\b|\bcapital expenditure\b|\bcapacity expansion\b|\bnew (?:plant|facility|unit|line)\b|\bgreenfield\b|\bbrownfield\b", re.I),
        cue=re.compile(r"\bFY\s?2?\d{1,2}\b|\bQ[1-4]\b|\bnext year\b|\bplan\w*\b|\bexpect\w*\b|\bcommission\w*\b", re.I),
    ),
    "debt": dict(
        topic=re.compile(r"\bdebt\b|\bborrowing\w*\b|\bleverage\b", re.I),
        cue=re.compile(r"\breduc\w*\b|\bdeleverag\w*\b|\brepay\w*\b|\bpay(?:ing)? down\b|\bdebt[- ]free\b", re.I),
    ),
    "orderbook": dict(
        topic=re.compile(r"\border book\b|\bbacklog\b|\bpipeline\b|\border[- ]?intake\b|\bbook[- ]to[- ]bill\b", re.I),
        cue=re.compile(r"\bgrowth\b|\bgrow\w*\b|\bexpect\w*\b|\btarget\w*\b|\bexecut\w*\b", re.I),
    ),
}
UP_WORDS = re.compile(r"\bgrow(?:th)?\b|\bincreas\w*\b|\bimprov\w*\b|\bexpand\w*\b|\bhigher\b|\bexceed\w*\b|\bstrong(?:er)?\b|\baccelerat\w*\b", re.I)
DOWN_WORDS = re.compile(r"\bdeclin\w*\b|\bfall\w*\b|\blower\b|\breduc\w*\b|\bcut\w*\b|\bcontract\w*\b|\bmoderat\w*\b|\bslow\w*\b", re.I)
DEBT_DOWN_CUE = re.compile(r"debt reduction|deleverag|repay|debt[- ]free|pay(?:ing)? down", re.I)


def classify_sentence(sentence: str):
    """Returns (commit_type, direction) or None. First matching type wins (order matters
    for rare multi-topic sentences); direction 'up'/'down' per lexicon, debt type forced
    'down' unless an explicit up-word appears without a reduction cue (raising debt case)."""
    for ctype, rules in COMMIT_RULES.items():
        if rules["topic"].search(sentence) and rules["cue"].search(sentence):
            if ctype == "debt":
                direction = "down" if DEBT_DOWN_CUE.search(sentence) else (
                    "up" if UP_WORDS.search(sentence) else "down")
            else:
                up, down = bool(UP_WORDS.search(sentence)), bool(DOWN_WORDS.search(sentence))
                if up and not down:
                    direction = "up"
                elif down and not up:
                    direction = "down"
                else:
                    direction = "up"
            return ctype, direction
    return None


def extract_commitments(sentences: list[str]) -> list[dict]:
    out = []
    for s in sentences:
        r = classify_sentence(s)
        if r:
            ctype, direction = r
            out.append({"commit_type": ctype, "direction": direction, "sentence": s})
    return out


METRIC_PROXY = {
    "revenue": {"source": "quarterly", "metric": "sales"},
    "margin": {"source": "quarterly", "metric": "opm_pct"},
    "capex": {"source": "annual", "metric": ["cwip", "fixed assets"]},
    "debt": {"source": "annual", "metric": ["borrowings", "borrowing"]},
    "orderbook": {"source": None, "metric": None},
}


# ============================================================================
# 4. FULL-COVERAGE EXTRACTION RUN (139 tickers) — mgmt-only vs naive (before/after)
# ============================================================================

def list_zip_tickers(store: TranscriptStore) -> list[str]:
    tickers = set()
    for folder in store._folders:
        m = re.match(r"^(.*)_([A-Za-z]{3}-\d{4})_transcript$", folder)
        if m:
            tickers.add(m.group(1))
    return sorted(tickers)


def run_extraction(store: TranscriptStore, tickers: list[str]) -> tuple[pd.DataFrame, dict]:
    """Returns (commitments_df, before_after_counts). commitments_df has one row per
    MANAGEMENT-attributed commitment sentence (the corrected, v2 extraction).
    before_after_counts totals naive vs mgmt-only commitment counts across all calls,
    plus how many naive "commitments" actually came from an ANALYST-labelled turn
    (the direct measurement of the P0 bug's impact)."""
    rows = []
    tot_naive = tot_mgmt = tot_from_analyst_turn = tot_calls = 0
    for tk in tickers:
        for q in store.list_quarters(tk, "transcript"):
            try:
                text = store.load_text(tk, q)
            except Exception:
                continue
            call_date = quarter_label_to_date(q)
            if pd.isna(call_date):
                continue
            tot_calls += 1
            mgmt_names, analyst_names = build_rosters(text)

            naive_sents = split_sentences(text)
            naive_commits = extract_commitments(naive_sents)
            tot_naive += len(naive_commits)

            turns = segment_turns(text, mgmt_names, analyst_names)
            analyst_text = " ".join(t for lbl, t in turns if lbl == "ANALYST")
            analyst_sents = split_sentences(analyst_text) if analyst_text.strip() else []
            analyst_commit_sentences = {c["sentence"] for c in extract_commitments(analyst_sents)}
            # how many of the NAIVE commitment sentences match something that (in v2) is
            # attributable to an analyst turn -- approximate overlap by substring match
            # against the analyst-only commitment sentence set (exact same classifier).
            tot_from_analyst_turn += sum(1 for c in naive_commits if c["sentence"] in analyst_commit_sentences)

            mgmt_text = management_only_text(text, mgmt_names, analyst_names)
            mgmt_sents = split_sentences(mgmt_text)
            mgmt_commits = extract_commitments(mgmt_sents)
            tot_mgmt += len(mgmt_commits)

            for c in mgmt_commits:
                rows.append({
                    "ticker": tk, "quarter": q, "call_date": call_date,
                    "commit_type": c["commit_type"], "direction": c["direction"],
                    "sentence": c["sentence"][:300],
                })
    df = pd.DataFrame(rows)
    stats = {
        "n_calls": tot_calls,
        "naive_commitment_sentences": tot_naive,
        "mgmt_only_commitment_sentences": tot_mgmt,
        "naive_sentences_from_analyst_turns": tot_from_analyst_turn,
        "reduction_pct": round(100 * (1 - tot_mgmt / tot_naive), 1) if tot_naive else None,
    }
    return df, stats


# ============================================================================
# 5. DELIVERY CHECK — quarterly PIT (revenue/margin), annual PIT (capex/debt)
#    + base-rate / sector-demeaning for revenue & margin
# ============================================================================

def load_pit_sources():
    q = pd.read_parquet(QUARTERLY_PIT_PATH)
    q["available_date"] = pd.to_datetime(q["available_date"], errors="coerce")
    q["quarter_end"] = pd.to_datetime(q["quarter_end"], errors="coerce")
    a = pd.read_parquet(ANNUAL_PIT_PATH)
    a = a.rename(columns={"key_symbol": "symbol"})
    sec = pd.read_parquet(SECTOR_MAP_PATH)
    return q, a, sec


def _next_prior_quarterly(qdf_sym: pd.DataFrame, metric_col: str, call_date, lag_min=30, lag_max=200):
    d = qdf_sym[["available_date", "quarter_end", metric_col]].dropna(subset=[metric_col, "available_date"])
    d = d.sort_values("available_date")
    cand = d[(d.available_date - call_date).dt.days.between(lag_min, lag_max)]
    if cand.empty:
        return None
    nxt = cand.iloc[0]
    prior = d[d.available_date < nxt.available_date]
    if prior.empty:
        return None
    return nxt, prior.iloc[-1]


def _next_prior_annual(adf_sym: pd.DataFrame, metrics: list[str], call_date, lag_min=30, lag_max=400):
    d = adf_sym[adf_sym.metric_norm.isin(metrics)][["available_date", "value"]].dropna()
    d = d.sort_values("available_date")
    cand = d[(d.available_date - call_date).dt.days.between(lag_min, lag_max)]
    if cand.empty:
        return None
    nxt = cand.iloc[0]
    prior = d[d.available_date < nxt.available_date]
    if prior.empty:
        return None
    return nxt, prior.iloc[-1]


def sector_quarter_benchmark(qdf: pd.DataFrame, metric_col: str, quarter_end, sector_syms: set) -> float | None:
    """Cross-sectional median QoQ %growth for `metric_col` at this quarter_end, restricted
    to `sector_syms` if that gives >=5 observations, else falls back to the whole quarterly
    universe at that quarter_end (base-rate / sector-demeaning per memo gap item)."""
    snap = qdf[qdf.quarter_end == quarter_end][["symbol", metric_col]].dropna()
    if snap.empty:
        return None
    prior_snap = qdf[qdf.quarter_end == (quarter_end - pd.DateOffset(months=3))][["symbol", metric_col]].dropna()
    merged = snap.merge(prior_snap, on="symbol", suffixes=("_now", "_prior"))
    merged = merged[merged[f"{metric_col}_prior"].abs() > 1e-9]
    if merged.empty:
        return None
    merged["pct_growth"] = (merged[f"{metric_col}_now"] - merged[f"{metric_col}_prior"]) / merged[f"{metric_col}_prior"].abs()
    sector_rows = merged[merged.symbol.isin(sector_syms)]
    if len(sector_rows) >= 5:
        return float(sector_rows.pct_growth.median())
    if len(merged) >= 3:
        return float(merged.pct_growth.median())
    return None


def delivery_check_row(row, qdf: pd.DataFrame, adf: pd.DataFrame, sector_of: dict, sector_syms_map: dict) -> dict:
    tk, ctype, direction, call_date = row.ticker, row.commit_type, row.direction, row.call_date
    out = {"delivery_available_date": None, "delivery_value": None, "delivery_prior_value": None,
           "relative_growth_vs_peers": None, "verdict": None}

    if ctype == "orderbook":
        out["verdict"] = "NO_FUNDAMENTAL_PROXY (order-book not in metric set)"
        return out

    if ctype in ("revenue", "margin"):
        metric_col = METRIC_PROXY[ctype]["metric"]
        qdf_sym = qdf[qdf.symbol == tk]
        if qdf_sym.empty:
            out["verdict"] = "NO_MATCHING_ACTUAL_IN_WINDOW"
            return out
        res = _next_prior_quarterly(qdf_sym, metric_col, call_date)
        if res is None:
            out["verdict"] = "NO_MATCHING_ACTUAL_IN_WINDOW"
            return out
        nxt, prior = res
        out["delivery_available_date"] = nxt.available_date
        out["delivery_value"] = nxt[metric_col]
        out["delivery_prior_value"] = prior[metric_col]
        if abs(prior[metric_col]) < 1e-9:
            out["verdict"] = "NOT_VERIFIABLE_FROM_FUNDAMENTALS"
            return out
        pct_growth = (nxt[metric_col] - prior[metric_col]) / abs(prior[metric_col])
        sector = sector_of.get(tk)
        peer_syms = sector_syms_map.get(sector, set())
        bench = sector_quarter_benchmark(qdf, metric_col, nxt.quarter_end, peer_syms)
        if bench is None:
            # fall back to raw-direction verdict, no base-rate available for this cell
            if direction == "up":
                out["verdict"] = "DELIVERED" if pct_growth > 0.005 else ("PARTIAL" if abs(pct_growth) <= 0.005 else "MISSED")
            else:
                out["verdict"] = "DELIVERED" if pct_growth < -0.005 else ("PARTIAL" if abs(pct_growth) <= 0.005 else "MISSED")
            return out
        rel = pct_growth - bench
        out["relative_growth_vs_peers"] = round(rel, 4)
        if direction == "up":
            out["verdict"] = "DELIVERED" if rel > 0.02 else ("MISSED" if rel < -0.02 else "PARTIAL")
        else:
            out["verdict"] = "DELIVERED" if rel < -0.02 else ("MISSED" if rel > 0.02 else "PARTIAL")
        return out

    if ctype in ("capex", "debt"):
        metrics = METRIC_PROXY[ctype]["metric"]
        adf_sym = adf[adf.symbol == tk]
        if adf_sym.empty:
            out["verdict"] = "NO_MATCHING_ACTUAL_IN_WINDOW"
            return out
        res = _next_prior_annual(adf_sym, metrics, call_date)
        if res is None:
            out["verdict"] = "NO_MATCHING_ACTUAL_IN_WINDOW"
            return out
        nxt, prior = res
        out["delivery_available_date"] = nxt.available_date
        out["delivery_value"] = nxt.value
        out["delivery_prior_value"] = prior.value
        if abs(prior.value) < 1e-9:
            out["verdict"] = "NOT_VERIFIABLE_FROM_FUNDAMENTALS"
            return out
        pct_growth = (nxt.value - prior.value) / abs(prior.value)
        # capex/debt: annual-only, no base-rate correction yet (documented gap — see memo)
        if direction == "up":
            out["verdict"] = "DELIVERED" if pct_growth > 0.02 else ("MISSED" if pct_growth < -0.02 else "PARTIAL")
        else:
            out["verdict"] = "DELIVERED" if pct_growth < -0.02 else ("MISSED" if pct_growth > 0.02 else "PARTIAL")
        return out

    out["verdict"] = "NO_MATCHING_ACTUAL_IN_WINDOW"
    return out


def run_delivery_check(commit_df: pd.DataFrame) -> pd.DataFrame:
    qdf, adf, sec = load_pit_sources()
    sector_of = dict(zip(sec.symbol, sec.macro_sector))
    sector_syms_map: dict = {}
    for s, grp in sec.groupby("macro_sector"):
        sector_syms_map[s] = set(grp.symbol)

    results = []
    for row in commit_df.itertuples(index=False):
        d = delivery_check_row(row, qdf, adf, sector_of, sector_syms_map)
        results.append(d)
    res_df = pd.DataFrame(results)
    out = pd.concat([commit_df.reset_index(drop=True), res_df], axis=1)
    return out


# ============================================================================
# 6. COMPANY CREDIBILITY SCORE (min 3 verifiable commitments, else excluded)
# ============================================================================

VERIFIABLE_VERDICTS = {"DELIVERED", "MISSED", "PARTIAL"}


def company_credibility(delivered_df: pd.DataFrame, min_n: int = 3) -> pd.DataFrame:
    v = delivered_df[delivered_df.verdict.isin(VERIFIABLE_VERDICTS)].copy()
    rows = []
    for tk, grp in v.groupby("ticker"):
        n = len(grp)
        if n < min_n:
            continue
        n_del = (grp.verdict == "DELIVERED").sum()
        n_miss = (grp.verdict == "MISSED").sum()
        n_part = (grp.verdict == "PARTIAL").sum()
        score = (n_del - n_miss) / n
        last_call = grp.call_date.max()
        rows.append({"ticker": tk, "n_verifiable": n, "n_delivered": n_del, "n_missed": n_miss,
                     "n_partial": n_part, "credibility_score": round(score, 3), "last_call_date": last_call})
    return pd.DataFrame(rows).sort_values("credibility_score", ascending=False)


# ============================================================================
# 7. PILOT FORWARD-RETURN TEST (sector-neutral, honest pilot-scale, drop-one)
# ============================================================================

def load_price(ticker: str) -> pd.DataFrame | None:
    path = os.path.join(PRICES_DIR, f"{ticker}.parquet")
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    return df


def fwd_return(px: pd.DataFrame, asof, horizon_days: int) -> float | None:
    idx = px.index
    start_pos = idx.searchsorted(asof)
    if start_pos >= len(idx):
        return None
    start_date = idx[start_pos]
    end_target = start_date + pd.Timedelta(days=horizon_days)
    end_pos = idx.searchsorted(end_target)
    if end_pos >= len(idx):
        return None
    p0 = px["Close"].iloc[start_pos]
    p1 = px["Close"].iloc[end_pos]
    if p0 <= 0:
        return None
    return p1 / p0 - 1.0


def pilot_return_test(cred_df: pd.DataFrame, sector_of: dict, horizon_days: int = 252) -> dict:
    rows = []
    for r in cred_df.itertuples(index=False):
        px = load_price(r.ticker)
        if px is None:
            continue
        ret = fwd_return(px, r.last_call_date, horizon_days)
        if ret is None:
            continue
        rows.append({"ticker": r.ticker, "credibility_score": r.credibility_score,
                      "n_verifiable": r.n_verifiable, "last_call_date": r.last_call_date,
                      "fwd_return": ret, "sector": sector_of.get(r.ticker, "UNKNOWN")})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"n": 0, "note": "no tickers had both a credibility score and sufficient price history"}

    # sector-neutral: demean fwd_return by sector-median (fallback: whole-sample median
    # if sector has <3 names in this small pilot cross-section)
    sector_med = df.groupby("sector").fwd_return.transform(
        lambda s: s.median() if len(s) >= 3 else np.nan)
    overall_med = df.fwd_return.median()
    df["fwd_return_xs"] = df.fwd_return - sector_med.fillna(overall_med)

    def _corr(d):
        if len(d) < 4:
            return None
        return float(d["credibility_score"].corr(d["fwd_return_xs"], method="spearman"))

    full_corr = _corr(df)
    drop_one = []
    for tk in df.ticker:
        sub = df[df.ticker != tk]
        c = _corr(sub)
        if c is not None:
            drop_one.append(c)

    hi = df[df.credibility_score > 0]
    lo = df[df.credibility_score < 0]
    return {
        "n": len(df),
        "n_hi_credibility": len(hi), "n_lo_credibility": len(lo),
        "mean_fwd_return_xs_hi_credibility": round(hi.fwd_return_xs.mean(), 4) if len(hi) else None,
        "mean_fwd_return_xs_lo_credibility": round(lo.fwd_return_xs.mean(), 4) if len(lo) else None,
        "spearman_ic_full_sample": round(full_corr, 3) if full_corr is not None else None,
        "spearman_ic_drop_one_min": round(min(drop_one), 3) if drop_one else None,
        "spearman_ic_drop_one_max": round(max(drop_one), 3) if drop_one else None,
        "spearman_ic_drop_one_mean": round(float(np.mean(drop_one)), 3) if drop_one else None,
        "horizon_days": horizon_days,
        "detail": df[["ticker", "sector", "credibility_score", "n_verifiable", "fwd_return", "fwd_return_xs"]]
            .sort_values("credibility_score", ascending=False),
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    store = TranscriptStore()
    tickers = list_zip_tickers(store)
    print(f"[1/5] {len(tickers)} tickers with text-ready transcripts")

    commit_df, extraction_stats = run_extraction(store, tickers)
    print("[2/5] extraction stats:", json.dumps(extraction_stats, indent=2))
    commit_df.to_csv(os.path.join(OUT_DIR, "commitment_extraction_v2.csv"), index=False)

    delivered_df = run_delivery_check(commit_df)
    delivered_df.to_csv(os.path.join(OUT_DIR, "commitment_delivery_pilot_v2.csv"), index=False)
    print("[3/5] verdict distribution:\n", delivered_df.verdict.value_counts())

    cred_df = company_credibility(delivered_df, min_n=3)
    cred_df.to_csv(os.path.join(OUT_DIR, "company_credibility_pilot_v2.csv"), index=False)
    print(f"[4/5] {len(cred_df)} companies scored (min 3 verifiable commitments)")

    _, _, sec = load_pit_sources()
    sector_of = dict(zip(sec.symbol, sec.macro_sector))
    result_1y = pilot_return_test(cred_df, sector_of, horizon_days=252)
    result_1m = pilot_return_test(cred_df, sector_of, horizon_days=21)
    print("[5/5] 1Y pilot return test:", {k: v for k, v in result_1y.items() if k != "detail"})
    print("[5/5] 1M pilot return test:", {k: v for k, v in result_1m.items() if k != "detail"})

    if "detail" in result_1y:
        result_1y["detail"].to_csv(os.path.join(OUT_DIR, "pilot_return_test_1Y_detail_v2.csv"), index=False)
    if "detail" in result_1m:
        result_1m["detail"].to_csv(os.path.join(OUT_DIR, "pilot_return_test_1M_detail_v2.csv"), index=False)

    summary = {
        "extraction_stats": extraction_stats,
        "verdict_distribution": delivered_df.verdict.value_counts().to_dict(),
        "n_companies_scored": len(cred_df),
        "return_test_1Y": {k: v for k, v in result_1y.items() if k != "detail"},
        "return_test_1M": {k: v for k, v in result_1m.items() if k != "detail"},
    }
    with open(os.path.join(OUT_DIR, "SUMMARY_v2.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print("\nDONE. Summary written to SUMMARY_v2.json")
