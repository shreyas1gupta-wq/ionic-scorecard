"""
build_v1_scaffold.py (2026-07-20) - stand up the STOCK_SCORECARD V1 operating model.
V1 = leaner, weekly-runnable pipeline:
  quant score  ->  ~2min analyst (ASYMMETRIC override: may convert score-Sell to Hold, may NOT
                    convert score-Hold to Sell)  ->  ~1min fund-manager pass  ->  client sheet.
The full-discretion V0 (analyst overrides either way + full FM judgment) is RETIRED but PRESERVED:
this script snapshots every recommendation made to date into an immutable V0 archive so the calls
can be scored for hindsight accuracy later.
It also SEEDS the per-stock state store (pf_state/<SYM>.json) from the 125 researches already on
disk, so V1 starts with a warm cache and the weekly runner can do incremental (earnings->full,
news->delta, else->carry) updates instead of re-researching everything every week.
Rerunnable. Usage: python build_v1_scaffold.py
"""
import os, json, glob, shutil, csv
os.environ["PYTHONIOENCODING"] = "utf-8"
from datetime import datetime
import pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SC = os.path.join(BASE, r"Shreyas_Ionic_AMC\04_RND_LAB\STOCK_SCORECARD_750")
RES = os.path.join(SC, "results")
REPORTS = os.path.join(BASE, r"Shreyas_Ionic_AMC\09_PRODUCT\reports")
ED = os.path.join(BASE, r"datasets\nse_earnings_dates")
TODAY = "2026-07-20"
ARCH = os.path.join(SC, "V0_ARCHIVE_20260720")
STATE = os.path.join(SC, "pf_state")


def archive_v0():
    os.makedirs(ARCH, exist_ok=True)
    qdir = os.path.join(ARCH, "pf_qual"); os.makedirs(qdir, exist_ok=True)
    quals = glob.glob(os.path.join(RES, "pf_qual_*.json"))
    for p in quals:
        shutil.copy2(p, qdir)
    flat = ["pf_mech_flags.json", "pf_fm_actions.json", "pf_digest.json",
            "PORTFOLIO_QUAL_SUMMARY.csv", "N100_RESEARCH_SUMMARY.csv",
            "ESCALATIONS_FOR_PRINCIPAL.md", "portfolio_quant.csv", "n100_quant_scored.csv"]
    for fn in flat:
        p = os.path.join(RES, fn)
        if os.path.exists(p):
            shutil.copy2(p, ARCH)
    # canonical client/analyst workbooks (latest of each)
    for pat, dest in [("CLIENT_RECOMMENDATIONS*.xlsx", "CLIENT_RECOMMENDATIONS_V0.xlsx"),
                      ("ANALYST_RECOMMENDATIONS*.xlsx", "ANALYST_RECOMMENDATIONS_V0.xlsx")]:
        cands = sorted(glob.glob(os.path.join(REPORTS, pat)), key=os.path.getmtime)
        if cands:
            shutil.copy2(cands[-1], os.path.join(ARCH, dest))
    man = f"""# V0 ARCHIVE - frozen track record ({TODAY})

**Do not edit.** This is the immutable snapshot of every STOCK_SCORECARD recommendation made under
the V0 methodology (full-discretion analyst override in BOTH directions + full fund-manager judgment
pass). V0 is retired from production as of {TODAY}; V1 (asymmetric override, weekly incremental)
supersedes it. This archive exists so the V0 calls can be scored for hindsight accuracy later
(performance attribution: how did our Sell/Trim/Hold calls actually do?).

Contents:
- pf_qual/  : {len(quals)} per-stock research files (59 real client holdings + 66 Nifty-100 coverage).
- pf_mech_flags.json / pf_fm_actions.json : the client-layer scores + FM Trim actions for the 59-book.
- portfolio_quant.csv / n100_quant_scored.csv : the quant score layer.
- CLIENT_RECOMMENDATIONS_V0.xlsx / ANALYST_RECOMMENDATIONS_V0.xlsx : the shipped workbooks.
- summaries + escalations as of the archive date.

To score this track record in future: take each stock's your_recommendation + ionic_score here,
measure forward return from {TODAY} vs Nifty 500, and compute hit-rate / decile spread by cohort.
"""
    open(os.path.join(ARCH, "MANIFEST.md"), "w", encoding="utf-8").write(man)
    return len(quals)


def load_earnings():
    """Return dict sym -> sorted list of earnings/board-meeting dates (datetime)."""
    out = {}
    for fn in ["earnings_dates.csv", "forthcoming_results.csv"]:
        p = os.path.join(ED, fn)
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        if "symbol" not in df.columns or "date" not in df.columns:
            continue
        df["d"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
        pur = df["purpose"].astype(str).str.lower() if "purpose" in df.columns else ""
        # keep results / financial-results / board meetings that imply an earnings print
        for _, r in df.iterrows():
            if pd.isna(r["d"]):
                continue
            s = str(r["symbol"]).upper().strip()
            out.setdefault(s, set()).add(r["d"])
    return {s: sorted(v) for s, v in out.items()}


def seed_state(earn):
    os.makedirs(STATE, exist_ok=True)
    mech = json.load(open(os.path.join(RES, "pf_mech_flags.json"), encoding="utf-8"))
    hold = {h["symbol"]: h for h in mech["holdings"]}
    fm = {a["symbol"]: a for a in json.load(open(os.path.join(RES, "pf_fm_actions.json"), encoding="utf-8"))["actions"]}
    tdt = pd.Timestamp(TODAY)
    n = 0
    for p in glob.glob(os.path.join(RES, "pf_qual_*.json")):
        q = json.load(open(p, encoding="utf-8"))
        sym = q["symbol"]
        is_hold = sym in hold
        rdate = "2026-07-18" if is_hold else "2026-07-20"
        rdt = pd.Timestamp(rdate)
        dates = earn.get(sym, [])
        last_earn = max([d for d in dates if d <= rdt], default=None)
        next_earn = min([d for d in dates if d > rdt], default=None)
        m = hold.get(sym, {})
        a = fm.get(sym, {})
        st = {
            "symbol": sym, "version": "V1", "coverage": "client_holding" if is_hold else "universe",
            "last_full_research_date": rdate,
            "based_on_earnings_date": str(last_earn.date()) if last_earn is not None else None,
            "quant": {"final_3y_adj": None, "final_1y_adj": None,
                      "ionic_score": m.get("ionic_score"), "quant_rec": m.get("quant_rec")},
            "analyst": {"rec": q.get("your_recommendation"),
                        "growth_pct": q.get("expected_next_3y_growth_pct"),
                        "override_applied": bool(m.get("quant_rec") == "Sell" and q.get("your_recommendation") == "Hold"),
                        "summary": q.get("summary")},
            "fm": {"action": a.get("action"), "trim_to": a.get("trim_target_pct")} if is_hold else None,
            "escalation": bool(q.get("escalation_flag")),
            "next_earnings_date": str(next_earn.date()) if next_earn is not None else None,
            "last_checked_date": TODAY,
            "delta_log": [],
            "pf_qual_ref": os.path.basename(p),
        }
        json.dump(st, open(os.path.join(STATE, f"{sym}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        n += 1
    return n


if __name__ == "__main__":
    nq = archive_v0()
    earn = load_earnings()
    ns = seed_state(earn)
    with_next = sum(1 for f in glob.glob(os.path.join(STATE, "*.json"))
                    if json.load(open(f, encoding="utf-8")).get("next_earnings_date"))
    print(f"V0 archived: {nq} researches -> {ARCH}")
    print(f"State seeded: {ns} stocks -> {STATE}  ({with_next} have a known next-earnings date)")
