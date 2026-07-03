"""FINAL news-adjusted execution sheet + Word plan. Base conviction (edge+signal+earnings risk)
adjusted by a NEWS/sectoral overlay (IT pack detailed from research; other sectors flagged by
earnings-in-window + sector cluster). Produces execution_scored.csv, conviction_summary.csv,
and EXECUTION_PLAN.docx with conviction, sector, earnings flag, news note + a sectoral note.
"""
import datetime as dt, re
from pathlib import Path
import numpy as np, pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor

PROJ = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
EXD = PROJ / "FINAL_STRATEGY_FORWARD_CHECK" / "08_Execution"
FWD = pd.read_csv(PROJ / "datasets/nse_earnings_dates/forthcoming_results.csv")
FWD["d"] = pd.to_datetime(FWD["date"], format="%d-%b-%Y", errors="coerce")
earn_dates = {}
for _, r in FWD.dropna(subset=["d"]).iterrows():
    earn_dates.setdefault(r["symbol"], []).append(r["d"].date())
FRONT_EXP = dt.date(2026, 7, 28)

import importlib.util
spec = importlib.util.spec_from_file_location("cs", str(Path("conviction_scorer.py")))
cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)   # reuse SECTOR + score_trade

# --- NEWS overlay (from 6-sector research sweep). (flag, note, conviction_adj) ---
NEWS = {
    # IT (results week 9-27 Jul + US H-1B $100k visa overhang)
    "TCS": ("HIGH", "Q1 9-Jul: IT season-opener; margin guidance sets sector tone", -11),
    "INFY": ("HIGH", "Q1 23-Jul: FY27 guidance reset = biggest single-stock IT gap catalyst", -12),
    "COFORGE": ("HIGH", "Q1 27-Jul: mid-cap, FIRST post-Encora consolidation quarter", -14),
    "HCLTECH": ("ELEVATED", "Q1 13-Jul + full-year guidance", -5),
    "TECHM": ("ELEVATED", "Q1 16-Jul; turnaround stock, higher realized vol", -6),
    # Banks / financials (private banks all 18-Jul)
    "HDFCBANK": ("HIGH", "Q1 18-Jul + CEO-reappoint/RBI-approval/governance-probe all cluster 15-18 Jul", -14),
    "ICICIBANK": ("ELEVATED", "Q1 18-Jul (clean bank, no binary overhang)", -5),
    "AXISBANK": ("ELEVATED", "Q1 18-Jul; history of asset-quality gap surprises", -7),
    "HDFCLIFE": ("ELEVATED", "Q1 15-Jul; VNB/APE print + HDFC-group sentiment", -5),
    "ANGELONE": ("HIGH", "Q1 15-16 Jul + LIVE SEBI weekly-expiry/F&O-tenure consultation-paper risk", -13),
    "BANKINDIA": ("NORMAL", "PSU bank; Q1 likely ~late-Jul (after 28-Jul expiry); healthy business update", 0),
    # Adani group (report 21-22 Jul, group-headline correlated)
    "ADANIGREEN": ("ELEVATED", "Q1 22-Jul; Adani-group headline-correlated", -6),
    "ADANIENSOL": ("ELEVATED", "Q1 21-Jul; Adani-group", -6),
    "ADANIPOWER": ("ELEVATED", "Q1 22-Jul; Adani-group", -6),
    # Pharma (US Sec-232 tariff overhang; generics exempt for now)
    "DRREDDY": ("HIGH", "Q1 22-Jul + fresh 7-obs USFDA 483 (biologics site) + GLP-1 headlines", -12),
    "CIPLA": ("ELEVATED", "Q1 23-Jul + unresolved Lanreotide supplier OAI", -6),
    "APOLLOHOSP": ("ELEVATED", "active demerger (HealthCo spin-off); Q1 likely mid-Aug -> verify date", -5),
    # FMCG / cement (all report late-Jul)
    "ASIANPAINT": ("ELEVATED", "Q1 ~28-29 Jul; Birla-Opus paint-war / market-share pressure", -6),
    "NESTLEIND": ("ELEVATED", "Q1 22-Jul; special-dividend decision 3-Jul", -5),
    "COLPAL": ("ELEVATED", "Q1 late-Jul; soft-volume + competition backdrop", -6),
    "ULTRACEMCO": ("ELEVATED", "Q1 20-Jul; weak July cement pricing + premium valuation", -6),
    # Auto / defence / metals
    "BAJAJ-AUTO": ("ELEVATED", "Q1 21-Jul; strong June sales already priced", -5),
    "BHARATFORG": ("ELEVATED", "lumpy defence order-flow headlines; Q1 mid-Jul (verify)", -6),
    "BDL": ("HIGH", "imminent Q1 + hot defence sector + India-Pak geopolitics + stretched valuation", -13),
    "JSWSTEEL": ("HIGH", "Q1 17-Jul + EU safeguard/CBAM step-change (1-Jul) + open duty decisions", -12),
    "COALINDIA": ("NORMAL", "PSU energy; no notable near-term binary found", 0),
}
IT_SET = {s for s, v in cs.SECTOR.items() if v == "IT"}
IT_NOTE = "IT sector: results week 9-27 Jul + H-1B $100k fee / visa overhang -> elevated sector IV"


def news_for(sym, strat, entry, expiry):
    if sym in NEWS:
        return NEWS[sym]
    # earnings-in-window (from announced calendar) -> ELEVATED
    for d in earn_dates.get(sym, []):
        if entry <= d <= expiry:
            return ("ELEVATED", f"Q1 earnings {d} in window", -5)
    if sym in IT_SET:
        return ("ELEVATED", "IT sector visa/earnings-week overhang", -4)
    return ("NORMAL", "no notable idiosyncratic news (earnings/sector only)", 0)


d = pd.read_csv(EXD / "execution_ALL.csv")
d["entry_date"] = pd.to_datetime(d["entry_date"]).dt.date
rows = []
cache = {}
for _, r in d.iterrows():
    exp = FRONT_EXP if "JUL" in str(r["expiry"]) else dt.date(2026, 8, 25)
    key = (r["strategy"], r["symbol"])
    if key not in cache:
        base, flags = cs.score_trade(r["strategy"], r["symbol"], r["signal"], r["entry_date"], exp)
        nflag, nnote, nadj = news_for(r["symbol"], r["strategy"], r["entry_date"], exp)
        conv = int(np.clip(base + nadj, 0, 100))
        cache[key] = (conv, flags, nflag, nnote)
    conv, flags, nflag, nnote = cache[key]
    rr = r.to_dict()
    rr["sector"] = cs.sector(r["symbol"]); rr["conviction"] = conv
    rr["news_risk"] = nflag; rr["news_note"] = nnote
    rr["risk_flags"] = "; ".join(flags) if flags else "-"
    rows.append(rr)

out = pd.DataFrame(rows).sort_values(["entry_date", "conviction", "strategy", "symbol", "opt"],
                                     ascending=[True, False, True, True, True])
cols = ["entry_date", "strategy", "action", "symbol", "sector", "expiry", "strike", "opt",
        "live_price", "lots", "lot_size", "conviction", "news_risk", "signal", "risk_flags", "news_note", "exit_rule"]
out[cols].to_csv(EXD / "execution_scored.csv", index=False)
trades = out.drop_duplicates(["strategy", "symbol", "entry_date"])
trades[["entry_date", "strategy", "symbol", "sector", "signal", "conviction", "news_risk", "risk_flags", "news_note"]].to_csv(
    EXD / "execution_conviction_summary.csv", index=False)

# --- Word doc ---
doc = Document()
doc.add_heading("EXECUTION PLAN + CONVICTION", 0)
p = doc.add_paragraph(f"Live prices {dt.date(2026,7,3)} (Fri close); next session Mon 6-Jul. Front expiry {FRONT_EXP}. "
                      "Conviction /100 = statistical edge + signal strength - earnings/event risk +/- news. "
                      "Account = disposable/data-only."); p.runs[0].italic = True

doc.add_heading("Conviction scoring method", 1)
for b in ["Base by strategy: strangle 70 (89% fwd-hit), IV/RV 72, earnings 62 (+39% but 60% hit), FF 60 (71% hit).",
          "Signal: FF magnitude (0.5-1.5 best; >1.5 usually earnings-driven -> discount); strangle credit%; ",
          "Risk deductions: earnings inside the front expiry (calendars/strangles = gap risk) -15 to -18.",
          "News overlay: HIGH RISK -12/-14, ELEVATED -4/-6, NORMAL 0 (IT pack researched; others by earnings/sector)."]:
    doc.add_paragraph(b, style="List Bullet")

def tbl(df, title):
    doc.add_heading(title, 1)
    t = doc.add_table(rows=1, cols=9); t.style = "Light Grid Accent 1"
    hs = ["Entry", "Action", "Symbol", "Sector", "Expiry", "Strike", "CE/PE", "Px", "Conv"]
    for i, h in enumerate(hs):
        rr = t.rows[0].cells[i].paragraphs[0].add_run(h); rr.bold = True; rr.font.size = Pt(8)
    for _, x in df.iterrows():
        c = t.add_row().cells
        for i, v in enumerate([str(x["entry_date"]), x["action"], x["symbol"], x["sector"], x["expiry"],
                               f"{x['strike']:g}", x["opt"], f"{x['live_price']}" if pd.notna(x['live_price']) else "-",
                               f"{x['conviction']}"]):
            rr = c[i].paragraphs[0].add_run(v); rr.font.size = Pt(8)

for strat, title in [("FF_Calendar", "FF Calendars (enter Mon 6-Jul) - by conviction"),
                     ("Earnings_ShortVol", "Earnings short-vol (enter 1 session before each result)"),
                     ("Short_Strangle", "Short strangles (enter ~14-Jul) - top 25 by conviction")]:
    sub = out[out["strategy"] == strat].sort_values("conviction", ascending=False)
    if strat == "Short_Strangle":
        top = sub.drop_duplicates(["symbol"]).head(50)   # 25 trades = 50 legs
        sub = sub[sub["symbol"].isin(top["symbol"])]
    tbl(sub, title)

doc.add_heading("Per-stock news & risk flags", 1)
tr = trades.sort_values("conviction")
t = doc.add_table(rows=1, cols=5); t.style = "Light Grid Accent 1"
for i, h in enumerate(["Symbol", "Sector", "Conv", "News", "Note / risk"]):
    rr = t.rows[0].cells[i].paragraphs[0].add_run(h); rr.bold = True; rr.font.size = Pt(8)
for _, x in tr.drop_duplicates("symbol").iterrows():
    note = x["news_note"] if x["news_note"] != "no notable idiosyncratic news (earnings/sector only)" else (x["risk_flags"] if x["risk_flags"] != "-" else "-")
    c = t.add_row().cells
    for i, v in enumerate([x["symbol"], x["sector"], f"{x['conviction']}", x["news_risk"], note[:90]]):
        rr = c[i].paragraphs[0].add_run(str(v)); rr.font.size = Pt(8)

doc.add_heading("Sectoral / macro note (3 Jul - 10 Aug 2026)", 1)
for b in [IT_NOTE + ".",
          "Bank results week ~17-18 Jul (HDFCBANK/ICICIBANK/AXISBANK) - private-bank IV elevated mid-July.",
          "Adani-group (ADANIGREEN/ENSOL/POWER) report 21-22 Jul - group-correlated, headline-prone.",
          "Pharma (CIPLA/DRREDDY) 22-23 Jul; FMCG (NESTLEIND/COLPAL/DABUR) 22-29 Jul; Auto (BAJAJ-AUTO/M&M) 21-30 Jul.",
          "EARNINGS-FLAG CAVEAT: only 27 stocks have ANNOUNCED board dates so far. By the 14-Jul strangle entry many more late-July earnings will be confirmed - RE-RUN the earnings refresh right before entry and skip/downsize strangles on any name reporting 14-28 Jul.",
          "Macro to watch for broad vol spikes: RBI MPC (early Aug), US Fed (late Jul), monthly F&O expiry 28-Jul."]:
    doc.add_paragraph(b, style="List Bullet")
doc.save(EXD / "EXECUTION_PLAN.docx")

print(f"scored {len(out)} legs / {len(trades)} trades -> execution_scored.csv + EXECUTION_PLAN.docx")
print("\n=== TOP 10 by conviction ===")
print(trades.sort_values("conviction", ascending=False).head(10)[
    ["entry_date", "strategy", "symbol", "sector", "conviction", "news_risk"]].to_string(index=False))
print("\n=== LOWEST 10 (avoid / downsize) ===")
print(trades.sort_values("conviction").head(10)[
    ["entry_date", "strategy", "symbol", "sector", "conviction", "news_risk", "news_note"]].to_string(index=False))
