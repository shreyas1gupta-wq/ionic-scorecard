"""Re-grade grid open-ended with a NEUTRAL judge (Opus) to test whether Sonnet<Haiku is real or
haiku-judge self-preference. Fresh random IDs + sealed mapping v2; per-task, 4 anonymized answers."""
import json, random
from pathlib import Path
SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
RES = SSP / "MODEL_GRID" / "results"
MODELS = ["fable", "haiku", "opus", "sonnetweb"]
OPEN = ["MG01", "MG02", "MG03", "MG04", "MG07", "MG08"]
RUB = {
 "MG01": ["PIT membership as-of (not today's list backward)","no lookahead: available_date/adjusted-price","survivorship-complete panel incl delisted","execution=next bar not formation close","realistic costs STT/impact/ADV cap","trade delta not full rebuild","same-exit/random-basket placebo","lag-sensitivity test","cost-stress 2-3x / regime split","explicit pre-registered kill criteria"],
 "MG02": ["exactly 5, materially distinct","mechanism: why edge exists","who is on the losing side","cheapest kill-test per idea","data obtainable by small team","explicit kill result","genuinely falsifiable","avoids survivorship-blind/impossible-data","considers factor overlap","non-overlap across the five"],
 "MG03": ["resume-safe (ledger/done-marker)","idempotent no double-ingest","atomic writes (.part rename)","corrupt-download rejection","checksum/schema validation gate","alerts only on actionable failure","new-machine takeover (state on disk)","rate-limit/backoff","concrete mechanisms not principles","gap/partial-history detection"],
 "MG04": ["quantified tail (numeric)","names real killer (gap/vol spike)","concrete pre-committed de-risk triggers","honest on what can't be hedged cheaply","liquidity/fill honesty in stress","book-wide correlation in spike","margin-call/sizing path","event-gate awareness","one-page actionable","specific not platitudes"],
 "MG07": ["known-value spot-checks vs independent source","PIT test: announcement-date genuineness","coverage-by-year/completeness","survivorship detection (delisted present?)","schema/dtype/null/dupe checks","date monotonicity/no future dates","sampling plan (n, stratified)","quarantine/acceptance gates","catalog/provenance","cross-check values not just structure"],
 "MG08": ["overfitting/multiple-testing (DSR/PBO)","costs & slippage under-modeled","lookahead/PIT violation","survivorship bias","regime dependence/crowding decay","capacity/market impact","ranked by probability","mechanism: HOW each inflates","specific check per mode","mechanisms not buzzwords"],
}
rng = random.Random(99)
mapping = {}; cases = []
for t in OPEN:
    items = [(m, (RES/f"{t}_{m}.md").read_text(encoding="utf-8").strip()) for m in MODELS if (RES/f"{t}_{m}.md").exists()]
    ids = [f"H{t[2:]}{chr(97+j)}" for j in range(len(items))]
    rng.shuffle(ids)
    blob = []
    for (m, body), hid in zip(items, ids):
        mapping[hid] = {"task": t, "model": m}
        blob.append(f"----- ANSWER {hid} -----\n{body}")
    cases.append({"tid": t, "anchors": RUB[t], "answers": "\n\n".join(blob), "ids": [h for h in ids]})
(RES.parent/"grid_regrade_mapping.json").write_text(json.dumps(mapping, indent=1), encoding="utf-8")
J = json.dumps
P = ["export const meta = { name: 'grid-regrade-opus', description: 'Neutral Opus re-grade of grid open-ended', phases:[{title:'Regrade'}] }"]
P.append("const CASES = " + J(cases))
P.append(r"""
const G = { type:'object', properties:{ grades:{ type:'array', items:{ type:'object', properties:{
  answer_id:{type:'string'}, score:{type:'number'}, hits:{type:'integer'} }, required:['answer_id','score'] } } }, required:['grades'] }
phase('Regrade')
const all=[]
for (let i=0;i<CASES.length;i+=3){
  const ch=CASES.slice(i,i+3)
  const r=await parallel(ch.map(c=>()=>agent(
    "You are a strict, fair, BLIND grader. Score each answer 0-10 on how many of the task's rubric anchors it genuinely meets (each ~1 pt; partial credit; do NOT reward length/verbosity or fluff - a concise answer that hits an anchor gets full credit). You do not know which model wrote which answer.\n\nRUBRIC ANCHORS for "+c.tid+":\n"+c.anchors.map((a,i)=>(i+1)+'. '+a).join('\n')+"\n\nANSWERS ("+c.ids.join(', ')+"):\n"+c.answers+"\n\nReturn {grades:[{answer_id,score,hits}]} for all "+c.ids.length+". No tools.",
    { label:'regrade:'+c.tid, phase:'Regrade', schema:G, model:'opus' })))
  all.push(...r); log('regraded '+Math.min(i+3,CASES.length)+'/'+CASES.length)
}
const rows=[]; for(let i=0;i<all.length;i++){ if(!all[i])continue; for(const g of all[i].grades) rows.push({...g, task:CASES[i].tid}) }
return { n: rows.length, rows }
""")
OUT = RES.parent / "grid_regrade"; OUT.mkdir(exist_ok=True)
(OUT/"regrade.js").write_bytes(("\n".join(P)).encode("utf-8").replace(b"\r\n",b"\n"))
print(f"regrade.js built: {len(OPEN)} tasks, {len(mapping)} answers, neutral judge=opus, sealed mapping v2")
