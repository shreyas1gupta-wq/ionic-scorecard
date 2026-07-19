"""Phase-3 demo: run the heuristic extractor on the LATEST available transcript for a couple
of pilot names that actually have transcript text, and write results/concall_demo_extract.json.

No scores are fabricated: only candidate sentences per rubric dimension (the evidence pool)
plus the llm_score_dimension() stub shape are emitted. Also writes an honest coverage report
across all 10 pilot names.
"""
import os, json, sys
sys.path.insert(0, os.path.dirname(__file__))
from concall_rubric import (TranscriptStore, extract_candidate_sentences, llm_score_dimension,
                             DIMENSIONS, PROJECT)

PILOT = ["HDFCBANK", "ASIANPAINT", "NESTLEIND", "TATASTEEL", "HINDALCO",
         "MARUTI", "TCS", "INFY", "GRAVITA", "SHAKTIPUMP"]

RES_DIR = os.path.join(PROJECT, "results")
os.makedirs(RES_DIR, exist_ok=True)

store = TranscriptStore()

# --- coverage across all 10 pilot names ---
coverage = {}
for tk in PILOT:
    qs = store.list_quarters(tk, kind="transcript")
    ppts = store.list_quarters(tk, kind="ppt")
    coverage[tk] = {"transcript_quarters": qs, "n_transcripts": len(qs),
                     "ppt_quarters": ppts, "n_ppts": len(ppts)}

demo_names = [tk for tk in PILOT if coverage[tk]["n_transcripts"] > 0][:2]  # e.g. HDFCBANK, TCS-ish order

out = {"coverage_all_pilot": coverage, "demo": {}}

for tk in demo_names:
    q = coverage[tk]["transcript_quarters"][-1]   # latest available quarter
    text = store.load_text(tk, q, kind="transcript")
    candidates = extract_candidate_sentences(text, max_per_dim=6)
    dim_block = {}
    for d in DIMENSIONS:
        dim_block[d.key] = {
            "name": d.name,
            "is_redflag": d.is_redflag,
            "n_candidates_found": len(candidates[d.key]),
            "candidate_sentences": candidates[d.key],
            "llm_score_hook": llm_score_dimension(d.key, candidates[d.key]),
        }
    out["demo"][tk] = {
        "quarter": q,
        "n_pages_chars": len(text),
        "dimensions": dim_block,
    }

out_path = os.path.join(RES_DIR, "concall_demo_extract.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print("wrote", out_path)
print("pilot coverage (n transcripts):", {k: v["n_transcripts"] for k, v in coverage.items()})
print("demo companies used:", demo_names)
