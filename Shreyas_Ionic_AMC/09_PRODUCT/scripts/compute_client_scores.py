"""
Mechanical layer of the agentic-fund-manager pipeline (FROZEN v6.2, 2026-07-18).
Computes Ionic Scores + concentration/action flags for a client book ->
results/pf_mech_flags.json (input to the FM judgment pass and build_client_excel.py).

Ionic Score (FROZEN_METHODOLOGY.md v6.2):
  base = 0.60*final_3y_adj + 0.40*final_1y_adj
  growth leg (forward 3-5y analyst estimate, NOT trailing):
      <5% -> -15 | 5-10% -> -5 | 10-15% -> 0 | 15-20% -> +5 | 20-25% -> +10 | >=25% -> +15
      +20 EXCEPTIONAL tier: >=25% growth AND ROE>=20% AND minimal share dilution
      (share-count CAGR <2%; dilution needs analyst/FM confirmation until the share-count
      field lands in the quant CSV -- mechanical layer only marks candidates)
  conviction leg: analyst Sell -> -6 | analyst-rescue (analyst Hold, quant Sell) -> +6 | else 0
  total adj clamped to [-20, +20]
  CAPS (both frozen): growth <10% -> net adj <= 0 (penalized, never boosted);
                      analyst Sell -> net adj <= 0 (an exit name is never score-boosted)
Usage: python compute_client_scores.py [quant_csv] [qual_dir] [out_json]
"""
import os, sys, json, glob
os.environ["PYTHONIOENCODING"] = "utf-8"
import pandas as pd


def growth_leg(g: float) -> int:
    if g < 5: return -15
    if g < 10: return -5
    if g < 15: return 0
    if g < 20: return 5
    if g < 25: return 10
    return 15


def compute(quant_csv: str, qual_dir: str, out_json: str):
    q = pd.read_csv(quant_csv)
    qual = {}
    for p in glob.glob(os.path.join(qual_dir, "pf_qual_*.json")):
        d = json.load(open(p, encoding="utf-8"))
        qual[d["symbol"]] = d

    total = q["value_inr"].sum()
    rows = []
    for _, r in q.iterrows():
        s = r["symbol"]; d = qual[s]
        base = 0.6 * r["final_3y_adj"] + 0.4 * r["final_1y_adj"]
        g = float(d["expected_next_3y_growth_pct"])
        gl = growth_leg(g)
        ar, qr = d["your_recommendation"], r["recommendation"]
        cl = -6 if ar == "Sell" else (6 if (ar == "Hold" and qr == "Sell") else 0)
        # exceptional-tier candidate (final grant = analyst/FM confirmed, incl. dilution check)
        roe = (r.get("roe") or 0) * 100
        exceptional_candidate = bool(g >= 25 and roe >= 20)
        adj = max(-20, min(20, gl + cl))
        if g < 10: adj = min(adj, 0)          # low-growth cap (v6.1)
        if ar == "Sell": adj = min(adj, 0)    # analyst-Sell cap (v6.2)
        ionic = round(max(0, min(100, base + adj)), 1)
        w = r["value_inr"] / total * 100

        flags = []
        if exceptional_candidate:
            flags.append("EXCEPTIONAL-GROWTH CANDIDATE (+20 tier if FM confirms low dilution)")
        if ar == "Sell":
            action = "Sell"
        elif ionic < 40:
            action = "Sell-candidate(score)"; flags.append("score<40 but analyst Hold")
        else:
            action = "Hold"
        if action == "Hold" and 40 <= ionic < 50 and w > 2.5:
            flags.append("TRIM-BAND: score 40-50 & weight>2.5%")
        if w > 20: flags.append("EXTREME >20%")
        elif w > 10: flags.append("CONC >10% (little bad)")
        elif w > 5 and g < 12: flags.append(f"5-10% weight & modest growth {g}%")
        if w < 0.25: flags.append("clutter <0.25%")

        rows.append(dict(symbol=s, weight=round(w, 2), ionic_score=ionic, base=round(base, 1),
                         fwd_adj=adj, growth=g, analyst_rec=ar, quant_rec=qr,
                         sector=r["sector"], mcap=r["mcap_tercile"],
                         escalated=bool(d["escalation_flag"]),
                         exceptional_candidate=exceptional_candidate,
                         mech_action=action, flags=flags))

    df = pd.DataFrame(rows).sort_values("weight", ascending=False)
    sec = df.groupby(df["sector"].str.lower())["weight"].sum().sort_values(ascending=False)
    mc = df.groupby("mcap")["weight"].sum()
    json.dump({"holdings": df.to_dict("records"),
               "sector_weights": sec.round(2).to_dict(),
               "mcap_weights": mc.round(2).to_dict()},
              open(out_json, "w"), indent=1)
    wbook = (df["ionic_score"] * df["weight"]).sum() / df["weight"].sum()
    print(f"{len(df)} holdings -> {out_json} | book weighted Ionic {wbook:.1f}")
    return df


if __name__ == "__main__":
    base = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\STOCK_SCORECARD_750\results"
    quant_csv = sys.argv[1] if len(sys.argv) > 1 else base + r"\portfolio_quant.csv"
    qual_dir = sys.argv[2] if len(sys.argv) > 2 else base
    out_json = sys.argv[3] if len(sys.argv) > 3 else base + r"\pf_mech_flags.json"
    df = compute(quant_csv, qual_dir, out_json)
    chg = df[df["fwd_adj"] != 0]
    print("\nNon-zero forward adjustments:")
    for _, r in chg.sort_values("fwd_adj").iterrows():
        print(f'  {r["symbol"]:<11} growth={r["growth"]:>5.1f}% adj={r["fwd_adj"]:>+3} ionic={r["ionic_score"]:>5.1f} {r["analyst_rec"]}')
