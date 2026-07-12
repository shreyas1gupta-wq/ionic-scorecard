"""Extract per-(arm,task) token usage from workflow transcript dirs (PROTOCOL S4 metering).
Scans agent-*.jsonl for API usage records; labels from journal.jsonl (agent label e.g. 'A:T01', 'C2red:T05').
Usage: python ws4_spend_extract.py <RUN_ID> <transcript_dir> [<transcript_dir2> ...]
Appends/updates results/<RUN_ID>/spend.csv (arm,task,stage,tokens_in,tokens_out,usd) and prints arm summaries.
Pricing: Fable/Opus-class $15/$75 per MTok in/out, Sonnet $3/$15, Haiku $1/$5 (edit PRICE if model differs;
model id recorded per row from transcript when present).
"""
import json, sys, re, csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
RUN = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/ws4_battery/results" / sys.argv[1]
PRICE = {"fable": (15, 75), "opus": (15, 75), "sonnet": (3, 15), "haiku": (1, 5)}

def price_for(model):
    m = (model or "").lower()
    for k, v in PRICE.items():
        if k in m:
            return v
    return PRICE["fable"]

rows = []
for tdir in sys.argv[2:]:
    tdir = Path(tdir)
    # label map from journal
    labels = {}
    j = tdir / "journal.jsonl"
    if j.exists():
        for line in j.open(encoding="utf-8", errors="replace"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            aid = r.get("agentId") or r.get("agent_id") or r.get("id")
            lab = r.get("label")
            if aid and lab:
                labels[str(aid)] = lab
    for f in tdir.glob("agent-*.jsonl"):
        aid = f.stem.replace("agent-", "")
        tin = tout = 0
        model = None
        for line in f.open(encoding="utf-8", errors="replace"):
            if '"usage"' not in line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            def find_usage(obj):
                if isinstance(obj, dict):
                    if "input_tokens" in obj and "output_tokens" in obj:
                        return obj
                    for v in obj.values():
                        u = find_usage(v)
                        if u:
                            return u
                return None
            u = find_usage(r)
            if u:
                tin += int(u.get("input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0) or 0) + int(u.get("cache_read_input_tokens", 0) or 0)
                tout += int(u.get("output_tokens", 0))
            m = re.search(r'"model"\s*:\s*"([^"]+)"', line)
            if m:
                model = m.group(1)
        lab = labels.get(aid, aid)
        m = re.match(r"(A|B|C1rev|C2red|C3syn):(T\d\d)", lab)
        if not m or tin + tout == 0:
            continue
        stage, task = m.group(1), m.group(2)
        arm = stage[0]
        pin, pout = price_for(model)
        usd = tin / 1e6 * pin + tout / 1e6 * pout
        rows.append(dict(arm=arm, task=task, stage=stage, tokens_in=tin, tokens_out=tout,
                         usd=round(usd, 4), model=model or "unknown"))

out = RUN / "spend.csv"
existing = []
if out.exists():
    existing = list(csv.DictReader(out.open(encoding="utf-8")))
    seen_new = {(r["arm"], r["task"], r["stage"]) for r in rows}
    existing = [r for r in existing if (r["arm"], r["task"], r["stage"]) not in seen_new]
allrows = existing + rows
with out.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["arm", "task", "stage", "tokens_in", "tokens_out", "usd", "model"])
    w.writeheader()
    for r in allrows:
        w.writerow(r)

agg = defaultdict(lambda: [0, 0, 0.0, 0])
for r in allrows:
    a = agg[r["arm"]]
    a[0] += int(r["tokens_in"]); a[1] += int(r["tokens_out"]); a[2] += float(r["usd"]); a[3] += 1
print(f"spend.csv: {len(allrows)} rows")
for arm in sorted(agg):
    tin, tout, usd, n = agg[arm]
    ntasks = len({r['task'] for r in allrows if r['arm'] == arm})
    per = (tin + tout) / max(ntasks, 1)
    print(f"arm {arm}: {ntasks} tasks, {tin:,} in + {tout:,} out = {tin+tout:,} tok, ${usd:.2f}, avg {per:,.0f} tok/task")
    if arm == "B":
        print(f"  -> ARM C CAP (1.5x B avg): {1.5*per:,.0f} tokens/task")
