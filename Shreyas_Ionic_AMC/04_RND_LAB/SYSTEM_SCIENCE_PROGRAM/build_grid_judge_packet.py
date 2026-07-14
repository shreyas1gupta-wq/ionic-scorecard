"""Build a BLIND grid-judging packet for the web account (saves our judge budget).
Anonymizes the 6 open-ended grid answers x 4 models (=24), random IDs, sealed mapping, embeds rubric
anchors. Web grader outputs 0-10 per ID; we unseal + average. Objective puzzles (MG05/06) already scored.
"""
import json, random
from pathlib import Path

SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
RES = SSP / "MODEL_GRID" / "results"
MODELS = ["fable", "haiku", "opus", "sonnetweb"]
OPEN = ["MG01", "MG02", "MG03", "MG04", "MG07", "MG08"]
RUBRIC = {
 "MG01": ["PIT index membership as-of (not today's list backward)", "no lookahead: available_date / adjusted-price awareness", "survivorship-complete panel incl delisted", "execution = next bar, NOT formation-day close (explicit)", "realistic costs: STT/impact/ADV cap (not flat bps)", "trade the delta / turnover, not full rebuild", "same-exit or random-basket placebo control", "lag-sensitivity test", "cost-stress 2-3x and/or regime split", "explicit pre-registered kill criteria"],
 "MG02": ["exactly 5, materially distinct (not variants)", "mechanism: why the edge exists", "who is on the losing side", "cheapest kill-test per idea", "data is obtainable by a small team", "explicit kill result stated", "genuinely falsifiable", "avoids survivorship-blind / impossible-data ideas", "considers factor overlap (just momentum/size?)", "non-overlap across the five"],
 "MG03": ["resume-safe (ledger/done-marker)", "idempotent, no double-ingest", "atomic writes (.part rename)", "corrupt-download rejection", "checksum/schema validation gate", "alerts only on actionable failure", "new-machine takeover (state on disk)", "rate-limit/backoff handling", "concrete mechanisms not principles", "gap/partial-history detection"],
 "MG04": ["quantified tail (numeric scenario)", "names the real killer (gap thru strikes/vol spike)", "concrete pre-committed de-risk triggers", "honest on what can't be hedged cheaply", "liquidity/fill honesty in stress", "book-wide correlation in a spike", "margin-call / sizing path", "event-gate awareness (CB/budget)", "one-page, actionable", "specific, no platitudes"],
 "MG07": ["known-value spot-checks vs independent source", "PIT test: announcement-date genuineness", "coverage-by-year/completeness check", "survivorship detection (delisted present?)", "schema/dtype/null/dupe checks", "date monotonicity / no future dates", "sampling plan (n, stratified)", "quarantine/acceptance pass-fail gates", "catalog/provenance entry", "cross-check values not just structure"],
 "MG08": ["overfitting / multiple-testing (DSR/PBO)", "costs & slippage under-modeled", "lookahead / PIT violation", "survivorship bias", "regime dependence / crowding decay", "capacity / market impact", "ranked by probability", "mechanism: HOW each inflates the number", "a specific check per failure mode", "mechanisms not buzzwords"],
}
rng = random.Random(4242)
items = []
for t in OPEN:
    for m in MODELS:
        f = RES / f"{t}_{m}.md"
        if f.exists():
            items.append((t, m, f.read_text(encoding="utf-8").strip()))
ids = [f"G{n:03d}" for n in range(1, len(items) + 1)]
rng.shuffle(ids)
mapping = {}
by_task = {t: [] for t in OPEN}
for (t, m, body), gid in zip(items, ids):
    mapping[gid] = {"task": t, "model": m}
    by_task[t].append((gid, body))
(SSP / "MODEL_GRID" / "grid_judge_mapping.json").write_text(json.dumps(mapping, indent=1), encoding="utf-8")

P = ["# WEB PACKET — BLIND GRID JUDGING (Firm S)", "",
     "You are a strict, fair grader. For EACH answer below, score 0-10 on how well it meets the task's",
     "rubric anchors (each anchor ~1 point; award partial credit; do not reward length or fluff).",
     "You do NOT know which model wrote which answer — do not guess. Score only against the anchors.",
     "OUTPUT (one line per answer, nothing else): `ID=<Gxxx> SCORE=<0-10> HITS=<n_anchors_met> NOTE=<=12 words`",
     "Do each task's answers together for consistency. One pass, no revisiting.", ""]
for t in OPEN:
    P += ["=" * 60, f"# TASK {t} — rubric anchors:"]
    for i, a in enumerate(RUBRIC[t], 1):
        P.append(f"  {i}. {a}")
    P.append("")
    for gid, body in by_task[t]:
        P += [f"----- ANSWER {gid} (task {t}) -----", body, ""]
P += ["=" * 60, "# REMINDER: output only `ID=Gxxx SCORE=n HITS=n NOTE=...` lines. All " + str(len(items)) + " answers."]
out = SSP / "WEB_PACKET_GRID_JUDGE.md"
out.write_bytes(("\n".join(P)).encode("utf-8").replace(b"\r\n", b"\n"))
print(f"{out.name}: {len(items)} answers across {len(OPEN)} tasks, sealed mapping written (grid_judge_mapping.json)")
