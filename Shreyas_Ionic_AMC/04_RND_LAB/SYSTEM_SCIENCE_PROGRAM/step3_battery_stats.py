"""Step 3: unseal cross-model battery grades -> per-model defects-found + false-positive rate + cost/defect.
Reads the grading workflow journal (robust to penalty-sign inconsistency by using score>=2 as the hit rule)."""
import json, re, csv
from pathlib import Path

SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
OUT = SSP / "ws4_battery" / "results" / "xmodel_grade"
journal = Path(r"C:\Users\Shreyas.1Gupta\.claude\projects\c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500\d5dd8360-a9cd-46c8-aeaa-21285e71a9a4\subagents\workflows\wf_3ac64dcf-137\journal.jsonl")
mapping = json.loads((OUT / "battery_xmodel_mapping.json").read_text(encoding="utf-8"))
CLEAN = {"T03", "T07", "T14", "T19"}
COST = {"fable": 1.492, "opus": 2.110, "sonnet": 0.148, "haiku": 0.025}  # from step1

# collect grades from journal (each agent result has {grades:[...]})
grades = {}
for ln in journal.read_text(encoding="utf-8", errors="replace").splitlines():
    try:
        obj = json.loads(ln)
    except Exception:
        continue
    def find(o):
        if isinstance(o, dict):
            if "grades" in o and isinstance(o["grades"], list):
                return o["grades"]
            for v in o.values():
                r = find(v)
                if r:
                    return r
        return None
    g = find(obj)
    if g:
        for e in g:
            if "answer_id" in e and "score" in e:
                grades[e["answer_id"]] = int(e["score"])
print(f"grades parsed: {len(grades)}/80")

# unseal + tally
from collections import defaultdict
stat = defaultdict(lambda: {"def_n": 0, "hit": 0, "clean_n": 0, "fp": 0})
rows = []
for bid, sc in grades.items():
    mp = mapping.get(bid)
    if not mp:
        continue
    m, t = mp["model"], mp["task"]
    rows.append((bid, m, t, sc))
    s = stat[m]
    if t in CLEAN:
        s["clean_n"] += 1
        if sc < 2:
            s["fp"] += 1
    else:
        s["def_n"] += 1
        if sc >= 2:
            s["hit"] += 1

with (OUT / "grades.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["answer_id", "model", "task", "score"]); w.writerows(rows)

print(f"\n{'model':<9}{'defects_found':>15}{'FP_rate':>10}{'$batt(est)':>12}{'$/defect':>10}")
out = ["BATTERY CROSS-MODEL RESULT (blind haiku judge; hit=score>=2 on 16 defective; FP=score<2 on 4 clean; cost=est from step1)"]
for m in ["fable", "opus", "sonnet", "haiku"]:
    s = stat[m]
    df, dn, fp, cn = s["hit"], s["def_n"], s["fp"], s["clean_n"]
    cpd = COST[m] / df if df else float("nan")
    line = f"{m:<9}{f'{df}/{dn}':>15}{f'{fp}/{cn}':>10}{COST[m]:>12.3f}{cpd:>10.4f}"
    print(line)
    out.append(f"{m}: defects_found {df}/{dn}, FP {fp}/{cn}, battery-cost ~${COST[m]:.3f}, $/defect ~${cpd:.4f}")
(OUT / "BATTERY_RESULT.txt").write_text("\n".join(out), encoding="utf-8")
print("\n-> BATTERY_RESULT.txt + grades.csv written")
