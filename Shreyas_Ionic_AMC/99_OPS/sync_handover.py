# -*- coding: utf-8 -*-
"""SYNC HANDOVER — keep the skill and every artefact a recipient needs current on GitHub.

Principal, 2026-08-13: "update github in such a way that the skill we want automatically get updated
as we update from here each time and other details get saved in github".

WHAT THIS SYNCS. Only the HANDOVER MANIFEST below -- the skill, the explainer docs, the frozen spec,
and the finished score/fund/ISIN data. Deliberately NOT the whole working tree: an auto-sync that
commits every dirty file would push half-finished code the moment a turn ends. Source code is still a
deliberate commit. If a tracked file outside the manifest is dirty, this reports it rather than
committing it, so nothing silently diverges either way.

WHY IT IS NEEDED AT ALL. The skill is one file in this repo, so "sync" is really "commit and push".
The failure mode it prevents is the one that actually happened on 2026-08-13: SKILL.md was edited here
across a long session, the recipient was handed the skill, and the material she needed was on a branch
her clone never saw.

    python sync_handover.py            # sync + push, no-op if nothing changed
    python sync_handover.py --dry-run  # show what would sync, touch nothing
    python sync_handover.py --check    # exit 1 if out of sync (for a gate); no writes

BRANCH REALITY, read this before trusting a green run. This repo has three remote branches and the
GitHub DEFAULT is the emptiest of them:
    main    1 file, a README, and an UNRELATED history -- no merge-base with anything, so it can
            never fast-forward. A plain `git clone` lands here and gets nothing.
    master  the real trunk.
    claude/*  session work branches.
Pushing does not make a recipient able to read it. This script therefore always prints which branch it
pushed and whether that branch is the one a clone would land on, and says so loudly when it is not.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Paths a recipient cannot build a deck without. Directories are synced recursively.
# Keep this list SHORT and justified -- every entry is something that, if stale on GitHub, produces a
# deck that looks finished and is wrong.
MANIFEST = [
    # the operating manual itself
    ".claude/skills/SG_NDPMS_TEMP1/",
    # the entry point and the plain-language explainer
    "README.md",
    "Shreyas_Ionic_AMC/09_PRODUCT/HOW_WE_SCORE_STOCKS.md",
    "Shreyas_Ionic_AMC/09_PRODUCT/FIVE_SIGNAL_AND_V3_SCORING_SPEC.md",
    # the finished numbers: stock scores, fund grades, and the ISIN join key
    "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/full750_scored_v3.csv",
    "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/full750_scored.csv",
    "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/EARNINGS_QUALITY.csv",
    "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/portfolio_quant.csv",
    "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/isin_master.csv",
    "Shreyas_Ionic_AMC/03_RESEARCH_DESK/MF_RECOMMENDATIONS/",
    # the state files that tell the next session where things stand
    "Shreyas_Ionic_AMC/01_COMMAND_CENTER/CURRENT_STATE.md",
    "Shreyas_Ionic_AMC/01_COMMAND_CENTER/SESSION_JOURNAL.md",
]

# A clone with no -b lands on the remote's default branch. Ours is `main`, which is a 1-file stub.
CLONE_LANDS_ON = "main"


def _root(p):
    found = None
    while True:
        p, tail = os.path.split(p)
        if not tail:
            if found:
                return found
            raise RuntimeError("repo root not found")
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            found = cand


def git(*args, cwd, check=False):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    ap.add_argument("--check", action="store_true", help="exit 1 if out of sync; no writes")
    ap.add_argument("--no-push", action="store_true", help="commit locally, do not push")
    a = ap.parse_args()

    # The worktree this file sits in is the repo we sync -- NOT the outermost root. Using the outermost
    # root would commit from the live tree while the edits are in the worktree.
    wt = os.path.abspath(os.path.join(HERE, ".."))            # ...\Shreyas_Ionic_AMC
    wt = os.path.abspath(os.path.join(wt, ".."))              # the checkout containing it
    rc, inside, _ = git("rev-parse", "--is-inside-work-tree", cwd=wt)
    if rc != 0 or inside != "true":
        print(f"not a git checkout: {wt}")
        return 2

    _, branch, _ = git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt)

    # which manifest paths actually exist here, and which of those are dirty
    present = [p for p in MANIFEST if os.path.exists(os.path.join(wt, p.replace("/", os.sep)))]
    absent = [p for p in MANIFEST if p not in present]

    _, dirty_raw, _ = git("status", "--porcelain", "--", *present, cwd=wt)
    dirty = [l[3:].strip().strip('"') for l in dirty_raw.splitlines() if l.strip()]

    # anything tracked and dirty OUTSIDE the manifest -- reported, never committed here
    _, all_raw, _ = git("status", "--porcelain", cwd=wt)
    all_dirty = [l[3:].strip().strip('"') for l in all_raw.splitlines() if l.strip()]
    outside = [f for f in all_dirty if not any(
        f == p or f.startswith(p) for p in MANIFEST)]

    print(f"branch          : {branch}")
    print(f"manifest        : {len(present)} of {len(MANIFEST)} paths present")
    if absent:
        for p in absent:
            print(f"   MISSING       {p}")
    print(f"manifest changes: {len(dirty)}")
    for f in dirty[:20]:
        print(f"   ~ {f}")
    if len(dirty) > 20:
        print(f"   ... and {len(dirty) - 20} more")
    if outside:
        print(f"outside manifest: {len(outside)} dirty file(s) NOT synced by this script "
              f"(commit them deliberately)")
        for f in outside[:8]:
            print(f"   . {f}")

    if a.check:
        if dirty:
            print("\nOUT OF SYNC — run without --check to sync.")
            return 1
        print("\nin sync.")
        return 0

    if not dirty:
        print("\nnothing to sync.")
    elif a.dry_run:
        print("\n--dry-run: nothing written.")
        return 0
    else:
        git("add", "--", *present, cwd=wt)
        _, staged, _ = git("diff", "--cached", "--name-only", cwd=wt)
        if not staged.strip():
            print("\nnothing staged after add.")
        else:
            n = len(staged.splitlines())
            msg = (f"Sync handover material ({n} file{'s' if n != 1 else ''})\n\n"
                   f"Automated sync of the handover manifest: skill, explainer docs, frozen spec,\n"
                   f"stock scores, fund grades, ISIN master, and the command-centre state files.\n"
                   f"Source code is not synced here -- that stays a deliberate commit.\n")
            mp = os.path.join(wt, ".git_sync_msg.tmp")
            with open(mp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(msg)
            rc, out, err = git("commit", "-F", ".git_sync_msg.tmp", cwd=wt)
            try:
                os.remove(mp)
            except OSError:
                pass
            if rc != 0:
                print(f"\ncommit failed: {err or out}")
                return 3
            _, sha, _ = git("rev-parse", "--short", "HEAD", cwd=wt)
            print(f"\ncommitted {sha}: {n} file(s)")

            if not a.no_push:
                rc, out, err = git("push", "origin", branch, cwd=wt)
                if rc != 0:
                    print(f"push FAILED: {err or out}")
                    return 4
                print(f"pushed to origin/{branch}")

    # --- the part that decides whether any of this reaches a recipient --------------------------------
    git("fetch", "-q", "origin", cwd=wt)
    rc, _, _ = git("rev-parse", "--verify", f"origin/{CLONE_LANDS_ON}", cwd=wt)
    if rc == 0 and branch != CLONE_LANDS_ON:
        _, base, _ = git("merge-base", "HEAD", f"origin/{CLONE_LANDS_ON}", cwd=wt)
        _, cnt, _ = git("rev-list", "--count", f"origin/{CLONE_LANDS_ON}", cwd=wt)
        _, ntree, _ = git("ls-tree", "-r", "--name-only", f"origin/{CLONE_LANDS_ON}", cwd=wt)
        nfiles = len([x for x in ntree.splitlines() if x.strip()])
        print()
        print(f"DELIVERY WARNING")
        print(f"   A plain `git clone` lands on origin/{CLONE_LANDS_ON}, which holds {nfiles} file(s).")
        print(f"   You just pushed to origin/{branch}, a DIFFERENT branch.")
        if not base:
            print(f"   origin/{CLONE_LANDS_ON} shares NO history with this branch, so it cannot be")
            print(f"   fast-forwarded -- it is a separate lineage, not an older version.")
        print(f"   Until that is resolved, a recipient who clones normally gets none of this.")
        print(f"   Give them:  git clone -b {branch} <url>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
