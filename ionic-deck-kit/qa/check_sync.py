# -*- coding: utf-8 -*-
"""Is this installation actually in sync? One command, run it before any client build.

WHAT GOES OUT OF SYNC, and what each one costs:

  the score files      a stale fund file and a fresh stock file put two as-of dates on one deck
  the demo file        dated later than production on purpose; if it wins, the deck is invented
  the band files       missing, and every holding arrives with no risk or liquidity band and
                       silently drops out of the lock-in test and the liquidity page
  the house view       absent, and the direct-equity calls fall back to the scorecard, which
                       disagrees with the desk on about a quarter of the names it covers
  the firm profile     absent, and the introduction pages render nothing
  the skill            a copy in .claude/skills does not track the repository; a recipient can
                       work for months against a manual that has been superseded
  the git tree         a client name or a score file staged for a PUBLIC repository

It exits 1 on anything that would put a wrong number on a client page, 0 otherwise. Warnings that
degrade the deck honestly (no firm profile, so no firm pages) do not fail the run: shipping less is
not the same as shipping wrong.
"""
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
ROOT = os.path.dirname(KIT)
SCORES = os.path.join(KIT, "scores")

FAIL, WARN, OK = [], [], []


def fail(what, why):
    FAIL.append((what, why))


def warn(what, why):
    WARN.append((what, why))


def ok(what, why=""):
    OK.append((what, why))


def _asof(path):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    return m.group(1) if m else None


# ---- 1. the score files ------------------------------------------------------------------------
def check_scores():
    funds = sorted(glob.glob(os.path.join(SCORES, "ionic_scores_*.csv")))
    prod = [f for f in funds if "DEMO" not in os.path.basename(f).upper()]
    demo = [f for f in funds if "DEMO" in os.path.basename(f).upper()]
    stocks = sorted(glob.glob(os.path.join(SCORES, "ionic_stock_scores_*.csv")))

    if not prod:
        if demo:
            fail("fund scores", "only the DEMO file is present. Every call on the deck would be "
                                "invented. It is dated later than production on purpose so it "
                                "cannot be mistaken for real.")
        else:
            fail("fund scores", "no ionic_scores_*.csv in scores/. Every scheme becomes No View.")
        return
    fa = _asof(prod[-1])
    ok("fund scores", f"{os.path.basename(prod[-1])} as of {fa}")

    if not stocks:
        warn("stock scores", "no ionic_stock_scores_*.csv. Every direct share carries No View and "
                             "the equity-book pages are skipped.")
        return
    sa = _asof(stocks[-1])
    ok("stock scores", f"{os.path.basename(stocks[-1])} as of {sa}")

    # TWO AS-OF DATES ON ONE DECK. The client reads one date on the cover and gets calls struck on
    # two. A month apart is a refresh cadence; a quarter apart is a file somebody forgot to copy.
    if fa and sa and fa != sa:
        d = abs((int(fa[:4]) * 12 + int(fa[5:7])) - (int(sa[:4]) * 12 + int(sa[5:7])))
        (fail if d >= 3 else warn)(
            "score dates", f"the fund file is as of {fa} and the stock file as of {sa}. "
                           f"One deck, one date on its cover, two populations struck {d} month(s) "
                           f"apart.")
    else:
        ok("score dates", "the two files agree")


# ---- 2. the framework files --------------------------------------------------------------------
def check_framework():
    need = {
        "risk_liquidity_bands.csv": ("fail", "every holding arrives with no risk band, no "
                                             "liquidity band and no days-to-cash, and drops out "
                                             "of the lock-in test and the liquidity page"),
        "equity_mcap_bands.csv": ("warn", "direct shares cannot be placed in a market-cap band"),
        "VERSION.json": ("fail", "no as-of date and no single_scheme_cap_pct, so no Trim is sized"),
        "house_view.json": ("warn", "the house-view pages render nothing"),
        "firm_profile.json": ("warn", "the firm's introduction pages render nothing, which is "
                                      "correct behaviour rather than an invented credential"),
    }
    for name, (level, why) in need.items():
        p = os.path.join(SCORES, name)
        if os.path.exists(p):
            ok(name)
        else:
            (fail if level == "fail" else warn)(name, "missing: " + why)

    vp = os.path.join(SCORES, "VERSION.json")
    if os.path.exists(vp):
        try:
            # a BOM here has broken this file before, so it is tolerated rather than fatal
            v = json.loads(open(vp, encoding="utf-8-sig").read())
        except Exception as e:
            fail("VERSION.json", f"will not parse: {e}")
            return
        cap = v.get("single_scheme_cap_pct")
        if cap is None:
            fail("VERSION.json", "carries no single_scheme_cap_pct, so no Trim can be sized")
        elif not (1 <= float(cap) <= 50):
            fail("VERSION.json", f"single_scheme_cap_pct is {cap}, which is not a percentage a "
                                 f"concentration cap is ever set at")
        else:
            ok("concentration cap", f"{cap}% of the whole book, any holding")

        # THE BAND FILE MUST COVER THE SUB-CATEGORIES THE PARSER CAN PRODUCE. A sub-category the
        # parser names and the band file does not carry produces a holding with no band, which is
        # the failure mode that hides Rs 70 lakh of fifteen-year money from the liquidity page.
        bp = os.path.join(SCORES, "risk_liquidity_bands.csv")
        tp = os.path.join(KIT, "parse", "tag_risk_liquidity.py")
        if os.path.exists(bp) and os.path.exists(tp):
            bands = open(bp, encoding="utf-8").read()
            src = open(tp, encoding="utf-8").read()
            # ONLY THE RISK SUB-CATEGORIES. The same file also holds engine_category, a
            # different and much coarser vocabulary ("debt", "elss", "flexi") that the deck
            # uses to group pages and the band file has no business carrying. Scanning both
            # reported twelve phantom gaps and would have trained a reader to ignore this check.
            _body = "".join(re.findall(r"def sub_for_" + chr(92) + "w+.*?(?=" +
                                       chr(92) + "ndef |" + chr(92) + "Z)", src, re.S))
            named = set(re.findall(r'return "([^"]{4,})"', _body))
            # CATEGORY_TO_SUB's VALUES are sub-categories too, and they are the ones that
            # were missing when Rs 70 lakh of PPF and SCSS arrived unbanded. Its keys are
            # statement category strings, which are lower-case; the values are capitalised.
            named |= set(re.findall(r':\s*"([A-Z][^"]{4,})",', src))
            missing = sorted(n for n in named
                             if n not in bands and not n.startswith("Direct Equity - "))
            if missing:
                fail("risk_liquidity_bands.csv",
                     "the parser can produce %d sub-categor(y/ies) the band file does not carry, "
                     "so any holding mapped to one arrives unbanded: %s"
                     % (len(missing), ", ".join(missing[:6])))
            else:
                ok("band coverage", "every sub-category the parser names has a band")


# ---- 3. the skill ------------------------------------------------------------------------------
def check_skill():
    sk = os.path.join(ROOT, ".claude", "skills", "Shreyas_Review_Skill")
    if not os.path.isdir(sk):
        warn("Shreyas_Review_Skill", "not present in this clone's .claude/skills")
        return
    need = ["SKILL.md", "VERSION.json", "check_version.py"] + [
        os.path.join("references", f) for f in (
            "01_pipeline.md", "02_calls_and_scoring.md", "03_client_directives.md",
            "04_tax.md", "05_mapping.md", "06_firm_pages.md", "07_qa_gates.md",
            "08_do_not_regress.md")]
    gone = [f for f in need if not os.path.exists(os.path.join(sk, f))]
    if gone:
        fail("Shreyas_Review_Skill", "incomplete: missing " + ", ".join(gone))
    else:
        v = json.loads(open(os.path.join(sk, "VERSION.json"), encoding="utf-8-sig").read())
        ok("Shreyas_Review_Skill", f"{v.get('version')} (sequence {v.get('sequence')}), "
                                  f"{len(need)} files")


# ---- 4. the git tree ---------------------------------------------------------------------------
def check_git():
    """THE REPOSITORY IS PUBLIC. A score file or a client name staged for it cannot be unpublished."""
    try:
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT,
                                capture_output=True, text=True).stdout.split()
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.split()
    except Exception as e:
        warn("git", f"could not read the tree: {e}")
        return

    NEVER = ("ionic_scores_", "ionic_stock_scores_", "risk_liquidity_bands.csv",
             "equity_mcap_bands.csv", "desk_calls.csv")
    bad = [f for f in set(staged) | set(tracked)
           if any(n in f for n in NEVER) and "DEMO" not in f.upper()]
    if bad:
        fail("git", "these are tracked or staged in a PUBLIC repository and must not be: "
                    + ", ".join(sorted(bad)[:6]))
    else:
        ok("git", "no production score or band file is tracked")

    for d in ("out/", "_charts/", "_CENTRAL/"):
        leaked = [f for f in tracked if ("/" + d) in ("/" + f) or f.startswith(d)]
        if leaked:
            fail("git", f"{d} is tracked ({len(leaked)} file(s)); it holds client artefacts")


def main():
    print("\n  Ionic review kit . sync check\n")
    check_scores()
    check_framework()
    check_skill()
    check_git()

    for what, why in OK:
        print(f"    ok    {what}" + (f"  .  {why}" if why else ""))
    for what, why in WARN:
        print(f"    warn  {what}  .  {why}")
    for what, why in FAIL:
        print(f"    FAIL  {what}  .  {why}")

    print()
    if FAIL:
        print(f"  BLOCKED: {len(FAIL)} thing(s) would put a wrong number on a client page.")
        return 1
    if WARN:
        print(f"  OK with {len(WARN)} warning(s). Each of those makes the deck say LESS, not "
              f"anything untrue.")
        return 0
    print("  In sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
