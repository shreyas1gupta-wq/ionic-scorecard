"""
run_weekly_v1.py (2026-07-20) - the STOCK_SCORECARD V1 WEEKLY INCREMENTAL ROUTER.
The token-optimizer: instead of re-researching every covered stock each week, it reads the per-stock
state (pf_state/) + the earnings feed and classifies each stock into exactly one lane:
  FULL   - a results/earnings print landed since the last full research -> redo the full ~2min analyst pass.
  DELTA  - no earnings, but a news-scan flagged something material -> cheap ~30s look at just that news.
  CARRY  - nothing new -> keep the cached recommendation, ~0 tokens.
The FULL list is DETERMINISTIC (from the earnings dates) and computed here for free. The DELTA/CARRY
split needs a cheap batched news-scan agent over the non-FULL names (returns material:y/n + 1 line),
which is a fraction of a full research pass. Only FULL + DELTA names consume analyst tokens.

Weekly-session usage:
  1. python run_weekly_v1.py [as_of=YYYY-MM-DD]   -> writes pf_state/week_plan_<as_of>.json + prints the plan.
  2. Run one analyst agent per FULL stock (V1 rules: asymmetric Sell->Hold-only override).
  3. Run ONE batched news-scan agent over the NEWS-CHECK list; DELTA the material ones, CARRY the rest.
  4. Run the ~1min FM pass only on client-holding stocks whose rec changed.
  5. Call apply_full()/apply_delta()/apply_carry() to update state; rebuild the client/analyst Excels.
State updates are journaled in each stock's delta_log so the whole history is auditable.
"""
import os, json, glob, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
import pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SC = os.path.join(BASE, r"Shreyas_Ionic_AMC\04_RND_LAB\STOCK_SCORECARD_750")
STATE = os.path.join(SC, "pf_state")
ED = os.path.join(BASE, r"datasets\nse_earnings_dates")


def load_earnings_results():
    """sym -> sorted list of RESULTS dates (purpose mentions 'result')."""
    out = {}
    for fn in ["earnings_dates.csv", "forthcoming_results.csv"]:
        p = os.path.join(ED, fn)
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        if not {"symbol", "date"}.issubset(df.columns):
            continue
        df["d"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
        if "purpose" in df.columns:
            df = df[df["purpose"].astype(str).str.contains("result", case=False, na=False)]
        for _, r in df.iterrows():
            if pd.notna(r["d"]):
                out.setdefault(str(r["symbol"]).upper().strip(), set()).add(r["d"])
    return {s: sorted(v) for s, v in out.items()}


def load_state():
    return {os.path.basename(p)[:-5]: json.load(open(p, encoding="utf-8"))
            for p in glob.glob(os.path.join(STATE, "*.json")) if not os.path.basename(p).startswith("week_plan")}


def plan(as_of=None):
    as_of = pd.Timestamp(as_of) if as_of else pd.Timestamp("2026-07-20")
    earn = load_earnings_results()
    st = load_state()
    full, news_check = [], []
    for sym, s in st.items():
        lfr = pd.Timestamp(s["last_full_research_date"])
        dates = earn.get(sym, [])
        trig = [d for d in dates if lfr < d <= as_of]
        if trig:
            full.append({"symbol": sym, "reason": f"results on {trig[-1].date()} since last research {lfr.date()}",
                         "coverage": s["coverage"]})
        else:
            news_check.append({"symbol": sym, "coverage": s["coverage"]})
    p = {"as_of": str(as_of.date()), "n_total": len(st),
         "FULL": full, "NEWS_CHECK": news_check,
         "note": ("FULL = deterministic earnings trigger (re-research). NEWS_CHECK -> one cheap batched "
                  "news-scan agent splits into DELTA (material) vs CARRY (nothing). Only FULL+DELTA cost analyst tokens.")}
    out = os.path.join(STATE, f"week_plan_{as_of.date()}.json")
    json.dump(p, open(out, "w", encoding="utf-8"), indent=1)
    full_frac = len(full) / max(1, len(st))
    print(f"[{as_of.date()}] {len(st)} covered | FULL(earnings)={len(full)} | NEWS-CHECK={len(news_check)}")
    print(f"  token economics: {len(full)} full re-researches vs {len(st)} if naive => "
          f"~{(1-full_frac)*100:.0f}% of full-research tokens deferred to a cheap news-scan this week.")
    if full:
        print("  FULL:", ", ".join(x["symbol"] for x in full[:40]))
    print(f"  plan -> {out}")
    return p


def apply_full(sym, research: dict, quant: dict = None, fm: dict = None, as_of=None):
    """Overwrite state after a completed V1 full analyst pass. Enforces the ASYMMETRIC override:
    analyst may set Hold on a quant-Sell (rescue) but a quant-Hold cannot be turned into a Sell."""
    as_of = as_of or "2026-07-20"
    p = os.path.join(STATE, f"{sym}.json")
    s = json.load(open(p, encoding="utf-8"))
    qrec = (quant or {}).get("quant_rec") or s["quant"].get("quant_rec")
    arec = research.get("your_recommendation")
    if qrec == "Hold" and arec == "Sell":
        arec = "Hold"  # V1 rule: analyst cannot downgrade a score-Hold to Sell
        research["_override_blocked"] = "analyst Sell suppressed: V1 allows Sell->Hold only, not Hold->Sell"
    s["analyst"] = {"rec": arec, "growth_pct": research.get("expected_next_3y_growth_pct"),
                    "override_applied": bool(qrec == "Sell" and arec == "Hold"),
                    "summary": research.get("summary")}
    if quant:
        s["quant"].update(quant)
    if fm is not None:
        s["fm"] = fm
    s["last_full_research_date"] = as_of
    s["last_checked_date"] = as_of
    s["delta_log"].append({"date": as_of, "mode": "FULL", "note": research.get("_trigger", "earnings"),
                           "rec": arec, "override_blocked": research.get("_override_blocked")})
    json.dump(s, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return s


def apply_delta(sym, material, note, new_rec=None, as_of=None):
    """After a cheap news-scan/delta look. material=bool. Same asymmetric guard if a rec change is proposed."""
    as_of = as_of or "2026-07-20"
    p = os.path.join(STATE, f"{sym}.json")
    s = json.load(open(p, encoding="utf-8"))
    changed = False
    if material and new_rec:
        qrec = s["quant"].get("quant_rec")
        if qrec == "Hold" and new_rec == "Sell":
            new_rec = "Hold"; note += " [Sell suppressed: V1 Sell->Hold only]"
        if new_rec != s["analyst"]["rec"]:
            s["analyst"]["rec"] = new_rec; changed = True
    s["last_checked_date"] = as_of
    s["delta_log"].append({"date": as_of, "mode": "DELTA" if material else "CARRY",
                           "note": note, "changed": changed})
    json.dump(s, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return s


if __name__ == "__main__":
    asof = sys.argv[1] if len(sys.argv) > 1 else "2026-07-20"
    plan(asof)
    if asof == "2026-07-20":
        print("\n--- demo: what a run on 2026-08-31 would trigger (post Q1FY27 season) ---")
        plan("2026-08-31")
