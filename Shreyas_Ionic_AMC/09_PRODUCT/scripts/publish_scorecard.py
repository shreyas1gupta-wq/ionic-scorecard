"""
publish_scorecard.py — publish the Nifty-750 scorecard to the PUBLIC distribution repo
(github.com/shreyas1gupta-wq/ionic-scorecard) so teammates' Claude skill auto-fetches the
latest week. Idempotent + rerunnable: first run bootstraps the repo (static files + remote);
every run rebuilds latest/* and pushes. Intended to run weekly (Sunday) via a scheduled task.

Publishes ONLY universe research (no client PII):
  latest/scores.csv, latest/commentary.json, latest/SCORECARD.xlsx, latest/manifest.json
Auth: pass the push token once via env GH_PUSH_TOKEN; it is stored in the dist repo's local
.git/config remote (never committed, never printed) so future scheduled runs need no env.

Run (first time):  set GH_PUSH_TOKEN=...  &&  python publish_scorecard.py
Run (weekly):      python publish_scorecard.py     (uses the stored remote credential)
"""
import json
import os
import shutil
import subprocess
import glob
from datetime import datetime, timezone, timedelta

FIRM = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
RESULTS = os.path.join(FIRM, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
XLSX_SRC = os.path.join(FIRM, "Shreyas_Ionic_AMC", "09_PRODUCT", "reports", "NIFTY750_SCORECARD_20260721.xlsx")
# MF recommendations (QFRA / "Mr. X"): published to latest/mf_recommendations.csv when the source exists;
# otherwise a schema-only placeholder is written so the repo + reader skill are ready for it. Set MF_SRC to override.
MF_SRC = os.environ.get("MF_SRC", r"C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\outputs\recommendations\QFRA2_current.csv")
DIST = r"C:\Users\Shreyas.1Gupta\ionic-scorecard"
USER = "shreyas1gupta-wq"
REPO = "ionic-scorecard"
IST = timezone(timedelta(hours=5, minutes=30))

import pandas as pd


def run(args, cwd=DIST, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        # never surface the remote URL (may embed token)
        msg = (r.stderr or r.stdout).replace(os.environ.get("GH_PUSH_TOKEN", "\0nope\0"), "***")
        raise RuntimeError(f"cmd {args[:2]} failed: {msg[:400]}")
    return r


STATIC = {}
STATIC[".gitignore"] = """# secrets — never publish
*.env
*token*
*.pem
*.key
.netrc
# client / PII — must never be committed to this public repo
*client*
*Client*
CLIENT_*
*holdings*
*CAS*
*PII*
# cruft
__pycache__/
*.pyc
.DS_Store
Thumbs.db
*.tmp
*.bak
"""
STATIC["DISCLAIMER.md"] = """# Disclaimer & Notice

(c) Shreyas / Ionic Wealth. **Proprietary research. All rights reserved.**

- **Internal research aid only.** For use by the Ionic Wealth team.
- **NOT investment advice**, not a recommendation to buy/sell any security, no solicitation.
- **Not for redistribution.** Do not forward this repository or its link outside the team.
- Scores are model output on point-in-time data and can be wrong or stale.
- No open-source licence is granted; absence of a LICENSE file means all rights reserved.
"""
STATIC["README.md"] = f"""# Ionic Scorecard — weekly distribution

Auto-updated weekly output of the Nifty-750 quant scorecard (TTM v7). **Internal team use only.**
See `DISCLAIMER.md` — proprietary, not investment advice, do not redistribute.

## What's here (always the latest week)
- `latest/scores.csv` — all ~750 names: score, Sell/Hold call, pillars, coverage.
- `latest/commentary.json` — per-stock analyst commentary (for names researched so far).
- `latest/SCORECARD.xlsx` — the formatted workbook.
- `latest/mf_recommendations.csv` — QFRA (Mr. X) mutual-fund picks: category, scheme, plan, score, MERIT grade, SENTINEL flags, conviction, recommendation.
- `latest/manifest.json` — as-of date, counts, source commit.
- `history/<YYYY-Www>/` — immutable weekly snapshots (track record).

## Use it in Claude (share once, always current)
Install `SKILL.md` (below) into your Claude skills, then ask e.g. *"show the latest Ionic
scorecard for TCS"* or *"give me the current Sell list"*. The skill fetches the newest files
from this repo each time — nothing to re-share.

Raw base: `https://raw.githubusercontent.com/{USER}/{REPO}/main/latest/`
"""
STATIC["SKILL.md"] = f"""---
name: ionic-scorecard-latest
description: Fetch the latest Ionic Wealth Nifty-750 quant scorecard (scores + Sell/Hold calls + per-stock commentary) from the team distribution repo. Use when asked for the current scorecard, a stock's score/commentary, the latest Sell list, or "refresh the scorecard". Internal research aid, not investment advice.
---

# Ionic Scorecard (latest) — reader skill

Data lives in the team repo `{USER}/{REPO}` and is refreshed weekly. Always fetch fresh; never
rely on cached/older numbers. Raw base:
`https://raw.githubusercontent.com/{USER}/{REPO}/main/latest/`

## How to answer
1. **Always first** WebFetch `…/latest/manifest.json` and state the as-of date + counts so the
   user knows the vintage.
2. Then fetch what the question needs:
   - Scores / calls / screening → `…/latest/scores.csv` (columns: symbol, sector,
     recommendation_overall, final_score_3y/1y, pillar scores, coverage flags, key ratios).
   - A stock's written view → `…/latest/commentary.json` (keyed by symbol: rec, growth%,
     summary, escalation). If a symbol isn't in commentary.json, only the quant row exists yet.
   - The formatted workbook → link `…/latest/SCORECARD.xlsx` (do not try to parse it; just share the URL).
   - Mutual-fund picks → `…/latest/mf_recommendations.csv` (QFRA / Mr. X: category, scheme, plan, score, MERIT grade, conviction, recommendation). If the file is empty, MF recs are not published yet.
3. Present concisely. **Never present this as investment advice**; it is an internal research
   aid. Reproduce numbers exactly as fetched; do not invent scores for names not in the files.

## Notes
- The score is 0.60x3Y + 0.40x1Y percentile-composite; a Call is "Sell" when the score < 40, else "Hold".
- TTM v7: 1-year growth + P/E reflect the latest reported quarter where available.
- Coverage flag Med/Low = read that row with lower confidence.
"""


def bootstrap():
    first = not os.path.isdir(os.path.join(DIST, ".git"))
    os.makedirs(os.path.join(DIST, "latest"), exist_ok=True)
    if first:
        run(["git", "init"], check=True)
        run(["git", "branch", "-M", "main"], check=False)
        run(["git", "config", "user.name", USER], check=False)
        run(["git", "config", "user.email", f"{USER}@users.noreply.github.com"], check=False)
    for name, body in STATIC.items():
        p = os.path.join(DIST, name)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
    # set remote (with token if provided) — stored locally, never committed
    tok = os.environ.get("GH_PUSH_TOKEN", "").strip()
    if tok:
        url = f"https://{USER}:{tok}@github.com/{USER}/{REPO}.git"
        run(["git", "remote", "remove", "origin"], check=False)
        run(["git", "remote", "add", "origin", url], check=True)
    return first


def build_artifacts():
    ld = os.path.join(DIST, "latest")
    # scores.csv (clean public subset)
    df = pd.read_csv(os.path.join(RESULTS, "full750_scored.csv"))
    df["roe"] = (df["roe"] * 100).round(1)
    df["roce"] = (df["roce"] * 100).round(1)
    cols = ["symbol", "sector", "recommendation_overall", "final_score_3y", "final_score_1y",
            "recommendation_3y", "recommendation_1y", "quality_score", "growth_3y_score",
            "growth_1y_score", "value_score", "stage_3y_score", "stage_1y_score",
            "sector_macro_3y_score", "coverage_flag_3y", "coverage_flag_1y", "revenue_growth_1y",
            "roe", "roce", "pe_current", "debt_equity", "bs_flag", "latest_qtr", "stale_flag"]
    cols = [c for c in cols if c in df.columns]
    out = df[cols].copy()
    for c in out.columns:
        if out[c].dtype == float:
            out[c] = out[c].round(2)
    out.sort_values("final_score_3y", ascending=False).to_csv(os.path.join(ld, "scores.csv"), index=False)
    n = len(out); nsell = int((out["recommendation_overall"] == "Sell").sum())

    # commentary.json from pf_qual files
    comm = {}
    for p in glob.glob(os.path.join(RESULTS, "pf_qual_*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        sym = d.get("symbol") or os.path.basename(p)[len("pf_qual_"):-5]
        comm[sym] = {"recommendation": d.get("your_recommendation"),
                     "growth_pct": d.get("expected_next_3y_growth_pct"),
                     "summary": d.get("summary"),
                     "escalation": bool(d.get("escalation_flag"))}
    json.dump(comm, open(os.path.join(ld, "commentary.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    # SCORECARD.xlsx
    if os.path.exists(XLSX_SRC):
        shutil.copyfile(XLSX_SRC, os.path.join(ld, "SCORECARD.xlsx"))

    # MF recommendations (QFRA / Mr. X) — published when available; schema placeholder otherwise
    mf_n = 0
    mf_out = os.path.join(ld, "mf_recommendations.csv")
    if os.path.exists(MF_SRC):
        try:
            mdf = pd.read_csv(MF_SRC); mdf.to_csv(mf_out, index=False); mf_n = len(mdf)
        except Exception:
            pass
    if mf_n == 0 and not os.path.exists(mf_out):
        pd.DataFrame(columns=["category", "scheme", "plan", "qfra_score", "merit_grade",
                              "sentinel_flags", "conviction", "recommendation", "as_of"]).to_csv(mf_out, index=False)

    # source sha
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=FIRM,
                         capture_output=True, text=True).stdout.strip()
    now = datetime.now(IST)
    week = now.strftime("%G-W%V")
    manifest = {"generated_at": now.strftime("%Y-%m-%d %H:%M IST"), "week": week,
                "universe_count": n, "hold": n - nsell, "sell": nsell,
                "commentary_count": len(comm), "mf_recommendations": mf_n,
                "methodology": "TTM v7 (2026-07-21)",
                "source_commit": sha, "note": "Internal research aid; not investment advice."}
    json.dump(manifest, open(os.path.join(ld, "manifest.json"), "w", encoding="utf-8"), indent=1)

    # weekly immutable snapshot
    snap = os.path.join(DIST, "history", week)
    os.makedirs(snap, exist_ok=True)
    for fn in ("scores.csv", "commentary.json", "manifest.json", "mf_recommendations.csv"):
        src = os.path.join(ld, fn)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(snap, fn))
    return week, n, nsell, len(comm), mf_n


def main():
    first = bootstrap()
    week, n, nsell, ncomm, nmf = build_artifacts()
    if os.environ.get("BUILD_ONLY"):
        print(f"BUILD-ONLY (no push): {DIST}\\latest built. week={week} names={n} sell={nsell} "
              f"commentary={ncomm} mf_recs={nmf}. Set a valid GH_PUSH_TOKEN (Contents:write) and run without BUILD_ONLY to publish.")
        return
    run(["git", "add", "-A"], check=True)
    status = run(["git", "status", "--porcelain"], check=False).stdout.strip()
    if not status:
        print("no changes to publish."); return
    run(["git", "commit", "-m", f"Weekly scorecard publish {week} ({n} names, {nsell} Sell, {ncomm} commentary)"], check=True)
    run(["git", "push", "-u", "origin", "main"], check=True)
    print(f"PUBLISHED week={week} names={n} sell={nsell} commentary={ncomm} first_run={first}")
    print(f"live: https://github.com/{USER}/{REPO}")
    print(f"raw : https://raw.githubusercontent.com/{USER}/{REPO}/main/latest/manifest.json")


if __name__ == "__main__":
    main()
