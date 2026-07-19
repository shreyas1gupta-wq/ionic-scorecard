"""
S7 — FINAL ASSEMBLY of the two-scorecard reset (Arjun Rao, Head of Quant, E-004).
Per SCORECARD_BLUEPRINT.md §4 (determinism contract). No new research, no refit, no weight search.
This is a MECHANICAL merge of already-built, already-graded artifacts + honest verdict tagging.

Does NOT patch the S4 horizon-scaling bug or the placebo-underperformance — those are Principal/CIO calls.

Outputs:
  - weights_v1.json                 (merged frozen weights, all four fragments)
  - RELATIVE_SCORECARD_v1.parquet   (date,symbol,rel_score_1M/1Y/5Y + verdict tags)
  - ABSOLUTE_SCORECARD_v1.parquet   (carry-through of absolute_scorecard.parquet + verdict tags by horizon)
Determinism gate: build each parquet TWICE from source; confirm .equals() AND SHA-256 match. Logged, not asserted-blind.
"""
import json, hashlib, datetime, sys
import pandas as pd

HERE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\rnd\scorecard"
def p(name): return HERE + "\\" + name

# ---- verdict tags (from S1/S2/S3/S4 reports + S5 consolidation; NOT re-derived here) ----
REL_VERDICT = {
    "1M": ("REAL",
           "REAL: both hard gates pass (lag 0.199, placebo -0.002), DSR 0.997 honest-count. "
           "Caveats: earn_1M leg ~zero incremental IC despite 40% weight; IC decaying (2024 single-yr -0.014); "
           "no-neg-news screen covers only 55/~750 names (rest pass by absence, not verification)."),
    "1Y": ("FRAGILE",
           "FRAGILE: hard gates clean (lag 0.116, placebo -0.0014); DSR~0/PBO 0.926 fail at thin effective sample. "
           "quality_cfo_pat coverage cliff pre-2017 makes it a post-2017-only model (~7-8 independent annual windows)."),
    "5Y": ("FRAGILE",
           "FRAGILE: hard gates clean (lag 0.042, placebo +0.0014); only ~1.5 independent non-overlapping 5Y windows. "
           "Growth-longevity leg REDUCES IC on drop-one despite blueprint-mandated overweight (unresolved, escalated to Principal/CIO)."),
}
ABS_VERDICT = {
    "1M": ("FAKE / DO-NOT-USE",
           "FAKE (hard-gate KILL): lag-test 1.05 (g) / 0.51 (rerating) vs 0.25 bar. STRUCTURAL MATH DEFECT: rerating term "
           "not horizon-scaled -> annualized intensity median -50%/yr, tail to +4675%/yr. Magnitude unusable; do not display or size."),
    "1Y": ("FRAGILE",
           "FRAGILE: driver ICs pass hard gate, but portfolio loses to BOTH placebos on Calmar (0.482 vs random 0.483, cap-wt 0.495). "
           "CAGR premium over random is a DRAWDOWN premium, not risk-adjusted skill."),
    "5Y": ("FRAGILE",
           "FRAGILE (least-bad, not certifiable): beats cap-wt placebo but loses BADLY to random placebo on Calmar (0.395 vs 0.635); "
           "worse max-drawdown than random at every horizon; only ~2 independent 5Y windows post-2015 coverage-ramp."),
}

def dfhash(df):
    h = pd.util.hash_pandas_object(df, index=False).values
    return hashlib.sha256(h.tobytes()).hexdigest()

# ------------------------------------------------------------------ 1. weights_v1.json
def build_weights():
    frags = {}
    for key, fn in [("relative_1M","weights_1M_fragment.json"),
                    ("relative_1Y","weights_1Y_fragment.json"),
                    ("relative_5Y","weights_5Y_fragment.json"),
                    ("absolute","weights_absolute_fragment.json")]:
        with open(p(fn), "r", encoding="utf-8") as f:
            frags[key] = json.load(f)
    out = {
        "version": "v1",
        "assembled": "2026-07-18",  # frozen literal, not datetime.now() -> keeps json deterministic
        "owner": "Arjun Rao (quant-head-arjun-rao, E-004)",
        "governing_blueprint": "rnd/scorecard/SCORECARD_BLUEPRINT.md §4 determinism contract",
        "note": "Single frozen source of every number that governs scoring. Nothing hard-coded elsewhere. "
                "A version bump (_v1->_v2) is the ONLY way any number changes and it restarts any forward clock (D-030).",
        "shared_foundations": {
            "band_cutoffs": {"UNDERVALUED_lt": 65.0, "OVERVALUED_gte": 160.0},
            "richness_index_formula": "100*exp(-0.25*EY_hist_zscore_expanding)  (causal, market_state.parquet)",
            "richness_empirical_gap": "richness never crossed ~139 in 21yr India sample; >=160 branch precautionary/never-fired",
            "washout_breadth_pctrank_threshold": 0.20,
            "quality_score_formula": "rank_pct(0.5*rank_pct(quality_QMJ) + 0.5*rank_pct(quality_cfo_pat)), within-date",
            "quality_gate_1Y": 0.10,
            "quality_gate_5Y": 0.20,
        },
        "relative_1M": frags["relative_1M"],
        "relative_1Y": frags["relative_1Y"],
        "relative_5Y": frags["relative_5Y"],
        "absolute": frags["absolute"],
        "verdicts": {
            "relative": {h: REL_VERDICT[h][0] for h in REL_VERDICT},
            "absolute": {h: ABS_VERDICT[h][0] for h in ABS_VERDICT},
        },
    }
    return out

# ------------------------------------------------------------------ 2. RELATIVE scorecard
def build_relative():
    d1 = pd.read_parquet(p("rel_score_1M.parquet"))[["date","symbol","rel_score_1M"]].copy()
    d2 = pd.read_parquet(p("rel_score_1Y.parquet"))[["date","symbol","rel_score_1Y"]].copy()
    d5 = pd.read_parquet(p("rel_score_5Y.parquet"))[["date","symbol","rel_score_5Y"]].copy()
    for d in (d1, d2, d5):
        d["date"] = pd.to_datetime(d["date"]).astype("datetime64[ns]")  # normalize us vs ns
        d["symbol"] = d["symbol"].astype("string")
    m = d1.merge(d2, on=["date","symbol"], how="outer").merge(d5, on=["date","symbol"], how="outer")
    # per-horizon verdict tags carried in output so no downstream consumer can miss them
    m["verdict_1M"] = REL_VERDICT["1M"][0]
    m["verdict_1Y"] = REL_VERDICT["1Y"][0]
    m["verdict_5Y"] = REL_VERDICT["5Y"][0]
    m = m.sort_values(["date","symbol"], kind="mergesort").reset_index(drop=True)
    m = m[["date","symbol","rel_score_1M","rel_score_1Y","rel_score_5Y","verdict_1M","verdict_1Y","verdict_5Y"]]
    return m

# ------------------------------------------------------------------ 3. ABSOLUTE scorecard
def build_absolute():
    a = pd.read_parquet(p("absolute_scorecard.parquet")).copy()
    a["date"] = pd.to_datetime(a["date"]).astype("datetime64[ns]")
    a["symbol"] = a["symbol"].astype("string")
    a["verdict"] = a["horizon"].map(lambda h: ABS_VERDICT[h][0]).astype("string")
    a["verdict_note"] = a["horizon"].map(lambda h: ABS_VERDICT[h][1]).astype("string")
    a = a.sort_values(["horizon","date","symbol"], kind="mergesort").reset_index(drop=True)
    return a

# ------------------------------------------------------------------ determinism gate
def det_check(builder, label):
    r1 = builder(); r2 = builder()
    eq = r1.equals(r2)
    h1, h2 = dfhash(r1), dfhash(r2)
    match = (h1 == h2)
    print(f"[DETERMINISM] {label}: .equals()={eq}  sha256_match={match}  shape={r1.shape}")
    print(f"             sha256={h1}")
    if not (eq and match):
        print(f"             *** DETERMINISM FAILURE on {label} ***")
    return r1, (eq and match), h1

def main():
    print("=== S7 FINAL ASSEMBLY ===")
    # weights
    w = build_weights()
    with open(p("weights_v1.json"), "w", encoding="utf-8") as f:
        json.dump(w, f, indent=2, ensure_ascii=False, sort_keys=True)
    # determinism of json (rebuild + compare bytes)
    w2 = build_weights()
    b1 = json.dumps(w,  indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
    b2 = json.dumps(w2, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
    print(f"[DETERMINISM] weights_v1.json: bytes_match={b1==b2}  sha256={hashlib.sha256(b1).hexdigest()}")

    rel, rel_ok, rel_h = det_check(build_relative, "RELATIVE_SCORECARD_v1")
    ab,  ab_ok,  ab_h  = det_check(build_absolute,  "ABSOLUTE_SCORECARD_v1")

    rel.to_parquet(p("RELATIVE_SCORECARD_v1.parquet"), index=False)
    ab.to_parquet(p("ABSOLUTE_SCORECARD_v1.parquet"), index=False)

    # reload-and-rehash: confirm on-disk artifact reproduces the in-memory hash after a fresh read
    rel_r = pd.read_parquet(p("RELATIVE_SCORECARD_v1.parquet"))
    rel_r["date"] = pd.to_datetime(rel_r["date"]).astype("datetime64[ns]")
    rel_r["symbol"] = rel_r["symbol"].astype("string")
    rel_r = rel_r.sort_values(["date","symbol"], kind="mergesort").reset_index(drop=True)
    ab_r = pd.read_parquet(p("ABSOLUTE_SCORECARD_v1.parquet"))
    ab_r["date"] = pd.to_datetime(ab_r["date"]).astype("datetime64[ns]")
    ab_r["symbol"] = ab_r["symbol"].astype("string")
    ab_r = ab_r.sort_values(["horizon","date","symbol"], kind="mergesort").reset_index(drop=True)
    print(f"[RELOAD-CHECK] RELATIVE on-disk sha256_match={dfhash(rel_r)==rel_h}")
    print(f"[RELOAD-CHECK] ABSOLUTE on-disk sha256_match={dfhash(ab_r)==ab_h}")

    print("\n=== SHAPES / COVERAGE ===")
    print("RELATIVE:", rel.shape, "| non-null 1M/1Y/5Y:",
          int(rel.rel_score_1M.notna().sum()), int(rel.rel_score_1Y.notna().sum()), int(rel.rel_score_5Y.notna().sum()))
    print("ABSOLUTE:", ab.shape, "| by horizon:", ab.horizon.value_counts().to_dict())
    print("\nOVERALL DETERMINISM GATE:", "PASS" if (rel_ok and ab_ok and b1==b2) else "FAIL")

if __name__ == "__main__":
    main()
