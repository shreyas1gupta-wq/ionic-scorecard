"""Robust cost meter for the opus arm-C pipeline (this session's clean 2-task run).
Handoff's ws4_spend_extract.py relies on journal 'label' which THIS harness does not write
(journal stores only a hashed 'key'), so it emits nothing. This reads agent-*.jsonl usage
directly and maps each agent to a pipeline stage via agent-*.meta.json 'agentType'.
Opus pricing $15/$75 per MTok in/out (per ws4_spend_extract PRICE table)."""
import json, glob, os, sys
from collections import defaultdict

WF = sys.argv[1]  # arm-C workflow transcript dir (clean, known = 2 tasks x 3 stages)
NTASKS = int(sys.argv[2])
STAGE = {"quant-head-arjun-rao": "1_review(single-LLM proxy)",
         "red-team-nikhil-bose": "2_redteam",
         "cio-rajan-mehta": "3_synthesis"}
PIN, POUT = 15, 75  # opus $/MTok

agg = defaultdict(lambda: [0, 0, 0])  # stage -> [in, out, n]
for f in glob.glob(os.path.join(WF, "agent-*.jsonl")):
    meta = f.replace(".jsonl", ".meta.json")
    at = None
    if os.path.exists(meta):
        at = json.load(open(meta, encoding="utf-8")).get("agentType")
    tin = tout = 0; model = ""
    for ln in open(f, encoding="utf-8", errors="replace"):
        if '"usage"' not in ln:
            continue
        try: r = json.loads(ln)
        except Exception: continue
        def fu(o):
            if isinstance(o, dict):
                if "input_tokens" in o and "output_tokens" in o: return o
                for v in o.values():
                    u = fu(v)
                    if u: return u
            return None
        u = fu(r)
        if u:
            tin += int(u.get("input_tokens", 0) or 0) + int(u.get("cache_creation_input_tokens", 0) or 0) + int(u.get("cache_read_input_tokens", 0) or 0)
            tout += int(u.get("output_tokens", 0) or 0)
        if not model and '"model"' in ln:
            import re
            m = re.search(r'"model"\s*:\s*"([^"]+)"', ln)
            if m: model = m.group(1)
    st = STAGE.get(at, at or "unknown")
    a = agg[st]; a[0] += tin; a[1] += tout; a[2] += 1
    if "opus" not in model.lower() and tin + tout > 0:
        print(f"  [warn] non-opus model on {st}: {model}")

print(f"arm C metering from {os.path.basename(WF)} | tasks={NTASKS}")
print(f"{'stage':<32}{'agents':>7}{'tok_in':>12}{'tok_out':>10}{'usd':>9}")
tot_in = tot_out = 0.0
s1_in = s1_out = 0.0
for st in sorted(agg):
    tin, tout, n = agg[st]
    usd = tin/1e6*PIN + tout/1e6*POUT
    print(f"{st:<32}{n:>7}{tin:>12,}{tout:>10,}{usd:>9.2f}")
    tot_in += tin; tot_out += tout
    if st.startswith("1_"): s1_in, s1_out = tin, tout
tot_usd = tot_in/1e6*PIN + tot_out/1e6*POUT
s1_usd = s1_in/1e6*PIN + s1_out/1e6*POUT
print("-"*70)
print(f"ARM C total: {tot_in:,.0f} in + {tot_out:,.0f} out = {tot_in+tot_out:,.0f} tok, ${tot_usd:.2f}")
print(f"ARM C per-task: {(tot_in+tot_out)/NTASKS:,.0f} tok, ${tot_usd/NTASKS:.3f}/task")
print(f"SINGLE-LLM proxy (stage-1 only) per-task: {(s1_in+s1_out)/NTASKS:,.0f} tok, ${s1_usd/NTASKS:.3f}/task")
mult = tot_usd/s1_usd if s1_usd else float('nan')
print(f"SYSTEM cost multiple (armC / single-LLM proxy): {mult:.2f}x")
print()
# cost-per-defect using Step-2 blind-graded defect counts over the FULL 16 defect-tasks
armC_defects, single_defects = 14, 16
armC_full_usd = tot_usd/NTASKS*20   # 20 total tasks in battery
single_full_usd = s1_usd/NTASKS*20
print(f"[extrapolated to 20-task battery @ this per-task rate]")
print(f"  arm C (system):    ${armC_full_usd:.2f} for {armC_defects} defects = ${armC_full_usd/armC_defects:.3f}/defect")
print(f"  single-LLM (proxy):${single_full_usd:.2f} for {single_defects} defects = ${single_full_usd/single_defects:.3f}/defect")
print(f"  => system costs {armC_full_usd/single_full_usd:.2f}x more AND finds fewer defects ({armC_defects} vs {single_defects}).")
