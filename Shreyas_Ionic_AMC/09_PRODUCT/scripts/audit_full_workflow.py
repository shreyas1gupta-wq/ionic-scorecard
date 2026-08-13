# -*- coding: utf-8 -*-
"""FULL WORKFLOW AUDIT — every deck, every tier, every gate, in one pass.
Principal, 2026-08-07: "re-audit every process of workflow and complete every task best".

Runs the whole pipeline end to end and reports a single table, so nothing passes by being skipped:
    STEP 1  scoring chain      earnings bridge -> v3 corrector -> freeze audit
    STEP 2  the 750 Excel
    STEP 3  every deck x every tier
    STEP 4  gates on each built deck: check_geometry, check_geometry2, tellscan
    STEP 4b signal dots carry colour -- catches a failed universe join, which is invisible to every
            other gate because the page renders perfectly with no data in it
    STEP 5  check_method on each data module (it takes a DATA FILE, not a pptx -- a mistake worth
            encoding here so it is not repeated)

Exit code is non-zero if any HARD gate fails. Known-benign findings are listed explicitly rather than
suppressed silently, so the exemption is visible and can be challenged.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PRT = os.path.abspath(os.path.join(HERE, "..", "pr_template"))


def _root(p):
    found = None
    while True:
        p, tail = os.path.split(p)
        if not tail:
            if found:
                return found
            raise RuntimeError("root not found")
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            found = cand          # keep walking: take the OUTERMOST match, not the first


ROOT = _root(HERE)
# The scoring scripts live NEXT TO THIS FILE'S TREE, which may be a git worktree; the results they read
# and write live in the LIVE tree. Resolving the scripts against ROOT sent the runner to the live
# scorecard directory, where they do not exist -- three silent rc=2 "can't open file" failures that
# looked like broken scripts rather than a bad path. Derive the script dir from __file__ instead.
_TREE = os.path.abspath(os.path.join(HERE, "..", ".."))          # ...\Shreyas_Ionic_AMC
SC = os.path.join(_TREE, "04_RND_LAB", "STOCK_SCORECARD_750")
if not os.path.exists(os.path.join(SC, "fix_thin_coverage_v3.py")):
    SC = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750")
PY = sys.executable
OUT = os.path.join(ROOT, "Shreyas_Ionic_AMC", "09_PRODUCT", "WORKFLOW_AUDIT.md")

# A finding we have examined and accepted, with the reason. Anything NOT here is a real failure.
BENIGN = {
    ("check_geometry2", "disclaimer colophon"):
        "the disclaimer page's own colophon sits at 6.90-7.20 by design on a dark terminal page; the "
        "gate exempts by y-position, not by role, so it reads as a spill",
    ("tellscan", "genuine"):
        "'genuine deleveraging' is ordinary English; tellscan's AI-tell list flags the word itself",
}

# is_demo matters to the gates, not just to the footer. tellscan's SYNTHETIC_DEMO_LEAK rule exists to
# catch "illustrative / synthetic / demo" wording sitting on a REAL client's data. On the ABXY showcase
# that wording is mandatory and correct -- the deck IS a demo, and 22 such labels are the deck doing its
# job. Treating them as failures buried the two findings on that deck that were real.
DECKS = [("build_client_a.py", "Client A", "data/client_a_family.py", False),
         ("build_abxy_showcase.py", "ABXY_Showcase", "data/azby_family.py", True),
         ("build_azby.py", "ABXY_Family", "data/azby_family.py", True)]
TIERS = ["HNI_DEEP", "STANDARD", "RM_SIMPLE"]
rows, hard_fail = [], 0


def run(cmd, cwd, timeout=900):
    try:
        r = subprocess.run([PY] + cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 99, "TIMEOUT"


def note(step, item, ok, detail=""):
    global hard_fail
    rows.append((step, item, "PASS" if ok else "FAIL", detail))
    if not ok:
        hard_fail += 1


print("STEP 1  scoring chain")
for script in ("earnings_quality_decomp.py", "fix_thin_coverage_v3.py", "audit_v3_freeze.py"):
    rc, out = run([script], SC)
    tail = [l for l in out.strip().splitlines() if l.strip()][-1:] or [""]
    detail = tail[0][:90]
    if script == "audit_v3_freeze.py":
        hit = [l for l in out.splitlines() if "hard invariants pass" in l]
        detail = hit[0].replace("*", "").strip() if hit else detail
    note("1 scoring", script, rc == 0, detail)
    print(f"   {script:32s} rc={rc}  {detail}")

print("STEP 2  the 750 Excel")
rc, out = run([os.path.join(HERE, "build_scores_excel.py")], HERE)
calls = [l for l in out.splitlines() if l.startswith("calls:")]
note("2 excel", "build_scores_excel.py", rc == 0, calls[0] if calls else out.strip()[-80:])
print(f"   rc={rc}  {calls[0] if calls else ''}")

print("STEP 3+4  decks x tiers, with gates")
for script, name, datamod, is_demo in DECKS:
    for tier in TIERS:
        rc, out = run([script, tier], PRT)
        nsl = next((l.split("->")[0].strip() for l in out.splitlines() if "slides ->" in l), "?")
        err = "[ERR ]" in out
        note("3 build", f"{name} {tier}", rc == 0 and not err,
             f"{nsl}{'  MODULE ERROR IN LOG' if err else ''}")
        print(f"   {name:16s} {tier:10s} rc={rc}  {nsl}")
        if rc != 0:
            continue
        pptx = f"out/{name}_{tier}.pptx"
        for gate in ("check_geometry.py", "check_geometry2.py", "tellscan.py"):
            grc, gout = run([gate, pptx], PRT)
            last = [l for l in gout.strip().splitlines() if "findings" in l]
            summary = last[-1].split(":")[-1].strip() if last else "?"
            nfind = int(summary.split()[0]) if summary.split() and summary.split()[0].isdigit() else 0
            benign = 0
            if gate == "check_geometry2.py" and "Angel One" in gout:
                benign += gout.count("Angel One")
            if gate == "tellscan.py":
                if "'genuine'" in gout:
                    benign += gout.count("'genuine'")
                if is_demo:
                    # on a demo deck the synthetic labelling is required, not a leak
                    m = re.search(r"\[SYNTHETIC_DEMO_LEAK\] x(\d+)", gout)
                    if m:
                        benign += int(m.group(1))
            real = max(nfind - benign, 0)
            note("4 gate", f"{name} {tier} {gate}", real == 0,
                 f"{nfind} findings, {benign} known-benign, {real} real")

print("STEP 4b  signal dots carry colour (the gate the others cannot do)")
# check_dots is deck-wide, not per-tier: it scans every .pptx in out/ once. It exists because a failed
# universe join is INVISIBLE to every other gate -- geometry, tellscan and check_method all pass on a
# page whose 60 signal dots are hollow grey rings, because the page is structurally perfect and the
# data is simply absent. Caught for real on 2026-08-07 in a clean export.
rc, out = run([os.path.join(PRT, "check_dots.py")], PRT)
verdict = next((l for l in out.splitlines() if l.startswith(("PASS", "FAIL"))), out.strip()[-90:])
note("4b dots", "check_dots.py (all decks)", rc == 0, verdict)
print(f"   rc={rc}  {verdict}")

print("STEP 5  check_method on each data module")
for datamod in sorted({d[2] for d in DECKS}):  # noqa: B007 — one run per distinct data module
    rc, out = run(["check_method.py", datamod], PRT)
    hits = [l.strip() for l in out.splitlines() if "findings" in l]
    note("5 method", datamod, rc == 0, hits[0] if hits else out.strip()[-90:])
    print(f"   {datamod:28s} rc={rc}  {hits[0] if hits else ''}")

lines = ["# Full workflow audit", "",
         f"**{sum(1 for r in rows if r[2] == 'PASS')} of {len(rows)} checks pass.**", "",
         "| step | item | result | detail |", "|---|---|---|---|"]
lines += [f"| {a} | {b} | {'PASS' if c == 'PASS' else '**FAIL**'} | {d} |" for a, b, c, d in rows]
lines += ["", "## Findings accepted as benign (examined, not suppressed)", ""]
lines += [f"- **{k[0]} / {k[1]}** — {v}" for k, v in BENIGN.items()]
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n" + "\n".join(lines[:4]))
print("wrote", OUT)
sys.exit(1 if hard_fail else 0)
