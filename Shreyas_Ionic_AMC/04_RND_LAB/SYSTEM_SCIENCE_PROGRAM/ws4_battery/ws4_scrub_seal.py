"""Scrub + seal (PROTOCOL S5). Run AFTER all arms of a grid are in results/<RUN_ID>/raw/.
Strips arm-identifying furniture, assigns random IDs (seeded), writes SEALED _mapping.json
and scrubbed/ answers. NO session may open _mapping.json until grades.csv is filed.
Usage: python ws4_scrub_seal.py <RUN_ID>
"""
import json, re, sys, random
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
RUN = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/ws4_battery/results" / sys.argv[1]
RAW, SCR = RUN / "raw", RUN / "scrubbed"
SCR.mkdir(exist_ok=True)

FURNITURE = [
    r"(?im)^.*\b(arm\s*[abc]|reviewer|red team|red-team|cio|quant head|synthesis|consolidated verdict|persona|agent)\b.*(:|—)\s*$",
    r"(?im)^\s*(as the|i am the|speaking as).*(reviewer|red team|cio|quant head).*$",
    r"(?im)^\s*(tokens?|token usage|budget|spend)\s*[:=].*$",
]

files = sorted(RAW.glob("T*_arm*.md"))
assert files, f"no raw answers in {RAW}"
rng = random.Random(20260713)
ids = [f"R{n:03d}" for n in range(1, len(files) + 1)]
rng.shuffle(ids)
mapping = {}
for f, rid in zip(files, ids):
    m = re.match(r"(T\d\d)_arm([ABC])", f.stem)
    task, arm = m.group(1), m.group(2)
    txt = f.read_text(encoding="utf-8")
    for pat in FURNITURE:
        txt = re.sub(pat, "", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
    # hard check: no residual arm tells
    low = txt.lower()
    for tell in ("arm a", "arm b", "arm c", "red team", "red-team", "quant head", "as the reviewer", "consolidated verdict"):
        if tell in low:
            print(f"WARN {f.name}: residual tell '{tell}' - manual scrub needed")
    (SCR / f"{task}_{rid}.md").write_text(txt, encoding="utf-8")
    mapping[rid] = {"task": task, "arm": arm, "src": f.name}

(RUN / "_mapping.json").write_text(json.dumps(mapping, indent=1), encoding="utf-8")
print(f"scrubbed {len(files)} answers -> {SCR} | mapping SEALED at _mapping.json (do not open until grades.csv filed)")
