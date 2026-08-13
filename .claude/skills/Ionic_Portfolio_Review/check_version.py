# -*- coding: utf-8 -*-
"""SELF-UPDATE CHECK for the Ionic_Portfolio_Review skill.

Principal, 2026-08-13: the skill must be able to update itself in future, and carry a stamp so a
recipient can tell which version they hold.

WHY THIS EXISTS. A skill file dropped into `.claude/skills/` is a COPY. It does not track the
repository, so a recipient can work for months against a stale manual with no signal that anything
moved. That is not hypothetical: an earlier handover shipped a copy asserting the stock scores were
not in the repo, which was the opposite of the truth, and nothing told the reader it was out of date.

WHAT IT DOES. Compares the local VERSION.json against the copy on the repo's delivery branch and says
plainly whether you are current. Three lookup paths, tried in order, so it works whether the skill sits
inside a clone or was copied out on its own:

    1. `git show <branch>:<path>` from inside a clone      -- offline-ish, no auth prompt
    2. `git archive` / `git cat-file` via the remote        -- clone present but file moved
    3. GitHub raw over HTTPS                                -- standalone copy, no clone at all

    python check_version.py            # report only
    python check_version.py --update   # fetch and overwrite the local skill if newer
    python check_version.py --quiet    # exit code only: 0 current, 1 stale, 2 unknown

`--update` rewrites SKILL.md and VERSION.json in place. It refuses if the local copy has uncommitted
edits it would destroy, because a recipient who has customised the manual should be told, not silently
overwritten.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_NAME = "Ionic_Portfolio_Review"
REL_SKILL = f".claude/skills/{SKILL_NAME}/SKILL.md"
REL_VERSION = f".claude/skills/{SKILL_NAME}/VERSION.json"
DELIVERY_BRANCH = "master"
REPO_RAW = ("https://raw.githubusercontent.com/shreyas1gupta-wq/ionic-scorecard/"
            f"{DELIVERY_BRANCH}/")
TIMEOUT = 20


def local_version():
    """Read the local VERSION.json.

    Opened as utf-8-SIG, not utf-8. A BOM is easy to acquire on Windows -- PowerShell's
    `Out-File -Encoding utf8` writes one, and this repo had 11 tracked files carrying one -- and plain
    utf-8 makes `json.load` raise on the BOM. That surfaced as the far more alarming "this copy has no
    VERSION.json, treat it as stale and re-clone", i.e. a false alarm telling the recipient to throw
    away a perfectly current skill. utf-8-sig reads both forms.
    """
    p = os.path.join(HERE, "VERSION.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, ValueError) as e:
        print(f"[warn] VERSION.json exists but could not be parsed ({type(e).__name__}: {e}). "
              f"Treating as unversioned.")
        return None


def _git(*args, cwd=None):
    try:
        r = subprocess.run(["git", *args], cwd=cwd or HERE, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return 1, "", "git unavailable"


def remote_via_git():
    """Path 1 & 2: read the file out of the clone's remote-tracking branch."""
    rc, _, _ = _git("rev-parse", "--is-inside-work-tree")
    if rc != 0:
        return None, "not inside a git checkout"
    _git("fetch", "--quiet", "origin", DELIVERY_BRANCH)
    for ref in (f"origin/{DELIVERY_BRANCH}", DELIVERY_BRANCH):
        rc, out, _ = _git("show", f"{ref}:{REL_VERSION}")
        if rc == 0 and out.strip():
            try:
                return json.loads(out), f"git {ref}"
            except ValueError:
                continue
    return None, "VERSION.json not found on the delivery branch"


def remote_via_http():
    """Path 3: standalone copy with no clone. Public raw URL; private repos will 404."""
    url = REPO_RAW + REL_VERSION
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:      # noqa: S310
            return json.loads(r.read().decode("utf-8-sig")), "https raw"
    except (urllib.error.URLError, ValueError, OSError) as e:
        return None, f"raw fetch failed ({type(e).__name__}) — expected on a private repo"


def fetch_remote():
    v, how = remote_via_git()
    if v:
        return v, how
    note = how
    v, how = remote_via_http()
    if v:
        return v, how
    return None, f"{note}; {how}"


def dirty_locally():
    rc, out, _ = _git("status", "--porcelain", "--", REL_SKILL)
    return rc == 0 and bool(out.strip())


def do_update():
    """Overwrite the local SKILL.md + VERSION.json from the delivery branch."""
    if dirty_locally():
        print("REFUSING to update: your local SKILL.md has uncommitted edits.")
        print("  Commit or stash them first — an update would overwrite your changes.")
        return 3
    ok = False
    for rel, dest in ((REL_SKILL, os.path.join(HERE, "SKILL.md")),
                      (REL_VERSION, os.path.join(HERE, "VERSION.json"))):
        rc, out, _ = _git("show", f"origin/{DELIVERY_BRANCH}:{rel}")
        if rc != 0 or not out:
            try:
                with urllib.request.urlopen(REPO_RAW + rel, timeout=TIMEOUT) as r:  # noqa: S310
                    out = r.read().decode("utf-8")
            except (urllib.error.URLError, OSError) as e:
                print(f"could not fetch {rel}: {type(e).__name__}")
                return 4
        if os.path.exists(dest):
            shutil.copy2(dest, dest + ".bak")
        with open(dest, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
        ok = True
    if ok:
        print("Updated SKILL.md and VERSION.json (previous copies kept as .bak).")
        print("RE-READ the skill now — you are still holding the old text in context.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="overwrite the local copy if newer")
    ap.add_argument("--quiet", action="store_true", help="exit code only")
    a = ap.parse_args()

    lv = local_version()
    rv, how = fetch_remote()

    if not a.quiet:
        print(f"skill      : {SKILL_NAME}")
        print(f"local      : {lv.get('version') if lv else '(no VERSION.json)'}"
              f"{'  ' + lv['released'] if lv and lv.get('released') else ''}")
        print(f"remote     : {rv.get('version') if rv else '(unavailable)'}  [{how}]")

    if not lv:
        if not a.quiet:
            print("\nVERDICT: cannot tell — this copy has no VERSION.json, so it predates version "
                  "stamping. Treat it as stale and re-clone.")
        return 2
    if not rv:
        if not a.quiet:
            print(f"\nVERDICT: unknown — could not reach the delivery branch. Your copy is "
                  f"{lv.get('version')}. If the repo is private, run this from inside a clone.")
        return 2

    lseq, rseq = int(lv.get("sequence", 0)), int(rv.get("sequence", 0))
    if lseq >= rseq:
        if not a.quiet:
            print(f"\nVERDICT: CURRENT. You are on {lv.get('version')}.")
        return 0

    if not a.quiet:
        print(f"\nVERDICT: STALE — remote is {rv.get('version')} ({rv.get('released')}), "
              f"you have {lv.get('version')}.")
        for line in (rv.get("changes") or [])[:6]:
            print(f"   • {line}")
        if not a.update:
            print("\nRun with --update to replace this copy, then re-read the skill.")
    if a.update:
        return do_update()
    return 1


if __name__ == "__main__":
    sys.exit(main())
