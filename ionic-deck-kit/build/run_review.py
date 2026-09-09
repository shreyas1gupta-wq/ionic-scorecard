# -*- coding: utf-8 -*-
"""ONE COMMAND for a whole review: statement in, checked deck out.

WHY THIS EXISTS. The pipeline was five commands run by hand from three different directories, each
with its own flags and its own way of failing quietly. Everybody who ran it ran a slightly different
version of it: someone forgot --lots and shipped a tax page that could not tell a short-term unit
from a long one; someone skipped the graft and shipped a deck with no firm pages; someone ran the
gates and read the count instead of the findings. A standard process that depends on remembering
five things is not a standard process.

    python build/run_review.py <statement.xlsx> --client "<Name>" [options]

It runs the build, the graft and all three QA gates, and it FAILS on a finding that lands on a page
this kit generated. Findings on the grafted firm pages are reported and do not fail the run: those
slides are lifted verbatim from the firm's own deck and are not this kit's to re-lay.

Everything it did is written to out/<Client>_RUN.json, so a deck can be traced back to the exact
inputs, the score-file dates and the gate results that produced it.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
ROOT = os.path.dirname(KIT)
GATES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "09_PRODUCT", "pr_template")
PY = sys.executable

# The gates cannot tell a page this kit drew from a page it grafted, so the caller says where the
# grafted block sits. Everything at or before this slide number is another firm's layout.
GRAFT_LAST_SLIDE = 6


def _run(cmd, label):
    """Run a step, stream nothing, keep everything. A step that fails stops the run."""
    t0 = time.time()
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    p = subprocess.run(cmd, capture_output=True, text=True, env=env,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    return {"label": label, "cmd": cmd, "rc": p.returncode,
            "seconds": round(time.time() - t0, 1), "output": out}


def _slides_in(text):
    """Every slide number a gate mentions, however it spelled it."""
    n = set()
    for m in re.finditer(r"'slide':\s*(\d+)", text):
        n.add(int(m.group(1)))
    for m in re.finditer(r"\bslide (\d+):", text):
        n.add(int(m.group(1)))
    return n


def main():
    ap = argparse.ArgumentParser(
        description="Build, graft and check a portfolio review in one command.")
    ap.add_argument("statement", help="the consolidated holdings workbook")
    ap.add_argument("--client", required=True)
    ap.add_argument("--tier", default="HNI_DEEP",
                    choices=["HNI_DEEP", "STANDARD", "RM_SIMPLE"])
    ap.add_argument("--profile", default="Aggressive",
                    choices=["Aggressive", "Moderate", "Conservative"])
    ap.add_argument("--directives", default=None,
                    help="a JSON file of the CLIENT's own instructions")
    ap.add_argument("--lots", default=None,
                    help="a capital-gains lot file (CSV). Without it the tax page cannot tell a "
                         "short-term unit from a long-term one and says so.")
    # PASSED STRAIGHT THROUGH. A flag the runner does not know about is a flag nobody can use
    # from the one command the skill tells them to run, so the runner has to carry every input
    # build_review takes.
    ap.add_argument("--target-return", default=None, type=float,
                    help="the client's stated return ambition, %% a year. Without it the "
                         "\"what your target requires\" page does not render.")
    ap.add_argument("--target-return-high", default=None, type=float)
    ap.add_argument("--defensive-yield", default=None, type=float,
                    help="assumed yield on the fixed-income and cash sleeve, %% a year "
                         "(default 6.5, printed on the page as the desk's assumption)")
    ap.add_argument("--firm-deck", default=None,
                    help="a reference deck to lift the firm's introduction pages from. Omitted, "
                         "the deck ships without them rather than with invented ones.")
    ap.add_argument("--firm-pages", default="2-6")
    ap.add_argument("--out", default=None, help="where to write the finished deck")
    ap.add_argument("--skip-gates", action="store_true",
                    help="build only. Use when iterating; never for anything that goes out.")
    a = ap.parse_args()

    safe = "".join(c for c in a.client if c.isalnum() or c in " _-").strip().replace(" ", "_")
    out_dir = os.path.join(KIT, "out")
    os.makedirs(out_dir, exist_ok=True)
    built = os.path.join(out_dir, f"{safe}_Review_{a.tier}.pptx")
    final = a.out or os.path.join(out_dir, f"{safe}_Review_FINAL.pptx")

    steps = []
    print(f"\n  {a.client}  .  {a.tier}  .  {a.profile}\n")

    # ---- 1. build -------------------------------------------------------------------------
    cmd = [PY, os.path.join(HERE, "build_review.py"), a.statement,
           "--client", a.client, "--tier", a.tier, "--profile", a.profile]
    if a.directives:
        cmd += ["--directives", a.directives]
    if a.lots:
        cmd += ["--lots", a.lots]
    if a.target_return:
        cmd += ["--target-return", str(a.target_return)]
    if a.target_return_high:
        cmd += ["--target-return-high", str(a.target_return_high)]
    if a.defensive_yield:
        cmd += ["--defensive-yield", str(a.defensive_yield)]
    st = _run(cmd, "build")
    steps.append(st)
    print(st["output"].rstrip())
    if st["rc"] != 0:
        print("\n  BUILD FAILED. Nothing further was run.")
        return 2

    # A MODULE THAT RAISES COSTS A WHOLE PAGE AND SAYS SO IN ONE LINE OF BUILD OUTPUT, which is
    # exactly the line a person running five commands by hand scrolls past. It is surfaced here.
    skipped = re.findall(r"\[skip\] (\S+): (.+)", st["output"])
    if skipped:
        print("\n  PAGES THAT DID NOT RENDER:")
        for m, why in skipped:
            print(f"    {m}: {why}")

    # ---- 2. graft -------------------------------------------------------------------------
    deck = built
    if a.firm_deck:
        st = _run([PY, os.path.join(HERE, "graft_firm_pages.py"),
                   "--src", a.firm_deck, "--tgt", built, "--out", final,
                   "--pages", a.firm_pages], "graft")
        steps.append(st)
        print("\n" + st["output"].rstrip())
        if st["rc"] != 0:
            print("\n  GRAFT FAILED. The ungrafted deck is at %s and is not sendable: it has no "
                  "firm pages and its cross-references were bound before the insert." % built)
            return 2
        deck = final
        if "WARNING" in st["output"]:
            print("\n  READ THE GRAFT WARNING ABOVE BEFORE THIS GOES OUT.")
    else:
        print("\n  no --firm-deck given, so the review ships without the firm's introduction "
              "pages. That is the honest outcome, not a failure: those pages are photographs and "
              "credentials and are never generated.")

    # ---- 2b. the client's workbook -------------------------------------------------------
    # THE CLIENT KEEPS THE SPREADSHEET. They read the deck once. build_review writes a raw frame
    # beside it for reconciliation; build_client_workbook turns that into the formatted seven-sheet
    # artefact that actually goes out, with the desk's internal vocabulary scrubbed by client_copy.
    # Left as a separate command it was a step somebody would forget, and forgetting it means the
    # client gets the raw dump -- raw field names as headings, and rationale text that names the
    # firm's own model. So it runs here, every time, from the same inputs as the deck.
    wb_raw = os.path.join(out_dir, f"{safe}_Holdings.xlsx")
    wb_client = None
    if os.path.exists(wb_raw):
        cmd = [PY, os.path.join(HERE, "build_client_workbook.py"), a.statement,
               "--client", a.client, "--holdings", wb_raw]
        if a.directives:
            cmd += ["--directives", a.directives]
        if a.lots:
            cmd += ["--lots", a.lots]
        st = _run(cmd, "workbook")
        steps.append(st)
        print("\n" + st["output"].rstrip())
        if st["rc"] != 0:
            print("\n  WORKBOOK FAILED. The deck is built, but the only file beside it is the raw "
                  "reconciliation frame, which is not a client artefact. Do not send it.")
            return 2
        wb_client = os.path.join(out_dir, f"{safe}_Portfolio_Workbook.xlsx")

    # ---- 3. gates -------------------------------------------------------------------------
    findings = {}
    if not a.skip_gates:
        print("\n  gates")
        for g in ("check_geometry.py", "check_geometry2.py", "tellscan.py"):
            st = _run([PY, os.path.join(GATES, g), deck], g)
            steps.append(st)
            slides = _slides_in(st["output"])
            ours = sorted(s for s in slides
                          if s > (GRAFT_LAST_SLIDE if a.firm_deck else 0))
            theirs = sorted(s for s in slides if s not in ours)
            findings[g] = {"generated_pages": ours, "grafted_pages": theirs}
            head = (st["output"].strip().splitlines() or [""])[0]
            print(f"    {g:<20} {head.split(': ')[-1]:<14} "
                  f"generated pages: {len(ours) or 'clean'}"
                  + (f"   (grafted: {len(theirs)}, out of scope)" if theirs else ""))
            if ours:
                for line in st["output"].splitlines():
                    if any(f"'slide': {s}," in line or f"slide {s}:" in line for s in ours):
                        print("      " + line.strip()[:150])

    # ---- 4. manifest ----------------------------------------------------------------------
    bad = sorted({s for f in findings.values() for s in f["generated_pages"]})
    manifest = {
        "client": a.client, "tier": a.tier, "profile": a.profile,
        "run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "inputs": {"statement": a.statement, "directives": a.directives, "lots": a.lots,
                   "firm_deck": a.firm_deck, "target_return": a.target_return,
                   "target_return_high": a.target_return_high,
                   "defensive_yield": a.defensive_yield},
        # NAMED FOR WHAT THEY ARE. Two workbooks land in out/: the formatted seven-sheet one that
        # goes to the client, and the raw frame it was built from, which exists to reconcile
        # against and is not a client artefact. A manifest calling both "workbook" is how the
        # wrong one gets attached to an email.
        "outputs": {"deck": deck,
                    "client_workbook": wb_client,
                    "reconciliation_frame": os.path.join(out_dir, f"{safe}_Holdings.xlsx"),
                    "ips": os.path.join(out_dir, f"{safe}_IPS_{a.profile}.xlsx")},
        "pages_that_did_not_render": [{"module": m, "why": w} for m, w in skipped],
        "gates": findings,
        "verdict": ("BLOCKED" if bad else "PASS" if not a.skip_gates else "UNCHECKED"),
        "steps": [{k: v for k, v in s.items() if k != "output"} for s in steps],
    }
    mpath = os.path.join(out_dir, f"{safe}_RUN.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    print(f"\n  deck      : {deck}")
    if wb_client:
        print(f"  workbook  : {wb_client}   (the raw {safe}_Holdings.xlsx beside it "
              f"reconciles; it is not the client's copy)")
    print(f"  manifest  : {os.path.basename(mpath)}")
    if a.skip_gates:
        print("\n  UNCHECKED: the gates were skipped. Do not send this.")
        return 0
    if bad:
        print(f"\n  BLOCKED: {len(bad)} generated page(s) carry a gate finding: "
              f"{', '.join(str(s) for s in bad)}.")
        print("  A geometry finding means text is off the page or on top of other text, and "
              "overflow is invisible in PowerPoint's own view.")
        return 1
    print("\n  PASS: every generated page is clean on all three gates.")
    print("  Now READ the pages you changed. No gate can see a page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
