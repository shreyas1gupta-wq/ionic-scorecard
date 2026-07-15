"""Unseal opus-arms grades -> A/B/C/C2 defects-found + FP + frozen-bar verdict.
Usage: python opus_arms_stats.py <path_to_grade_workflow_journal.jsonl>"""
import json, sys
from pathlib import Path
from collections import defaultdict
SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
OUT = SSP / "ws4_battery" / "results" / "opus_arms_grade"
CLEAN = {"T03", "T07", "T14", "T19"}
mp = json.loads((OUT / "opus_arms_mapping.json").read_text(encoding="utf-8"))
sc = {}
for ln in Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines():
    try: o = json.loads(ln)
    except Exception: continue
    def f(x):
        if isinstance(x, dict):
            if "grades" in x and isinstance(x["grades"], list): return x["grades"]
            for v in x.values():
                r = f(v)
                if r: return r
        return None
    g = f(o)
    if g:
        for e in g:
            if "answer_id" in e and "score" in e: sc[e["answer_id"]] = int(e["score"])
st = defaultdict(lambda: {"dn": 0, "hit": 0, "cn": 0, "fp": 0})
for oid, s in sc.items():
    mm = mp.get(oid)
    if not mm: continue
    a, t = mm["arm"], mm["task"]; S = st[a]
    if t in CLEAN:
        S["cn"] += 1; S["fp"] += (s < 2)
    else:
        S["dn"] += 1; S["hit"] += (s >= 2)
print(f"{'arm':<5}{'defects_found':>15}{'FP':>8}")
res = {}
for a in ["A", "B", "C", "C2"]:
    S = st[a]; res[a] = S["hit"]
    print(f"{a:<5}{f'{S[chr(104)+chr(105)+chr(116)]}/{S[chr(100)+chr(110)]}':>15}{f'{S[chr(102)+chr(112)]}/{S[chr(99)+chr(110)]}':>8}")
if all(k in res for k in ("A", "B", "C")):
    need = 1.2 * max(res["A"], res["B"])
    verdict = "SYSTEM ADDS VALUE (bar met)" if res["C"] >= need else "BAR NOT MET (system does not beat single-LLM at matched task)"
    print(f"\nFROZEN BAR: C defects {res['C']} vs required >= {need:.1f} (1.2x max(A={res['A']},B={res['B']})) -> {verdict}")
    if "C2" in res: print(f"ABLATION C vs C2 (personas/naming): C {res['C']} vs C2 {res['C2']} -> personas {'help' if res['C']>res['C2'] else 'do not help'} on defects")
(OUT / "OPUS_ARMS_RESULT.txt").write_text("\n".join(f"{a}: defects {st[a]['hit']}/{st[a]['dn']}, FP {st[a]['fp']}/{st[a]['cn']}" for a in ["A","B","C","C2"]), encoding="utf-8")
print("\n-> OPUS_ARMS_RESULT.txt written")
