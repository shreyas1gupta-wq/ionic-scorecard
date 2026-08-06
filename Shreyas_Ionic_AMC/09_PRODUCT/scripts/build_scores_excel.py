# -*- coding: utf-8 -*-
"""build_scores_excel.py — the 750-universe scorecard Excel, now carrying the FIVE SIGNALS.
v8, 2026-08-07 (Principal): "in excel we had of 750 stock we have to add that while stock research
itself to avoid confusion and recommendation forward data".

What changed from the 2026-07-21 version:
  * The five client-deck signals (Quality / Growth / Value / Technical / Sector & Flows) appear as
    colour-banded word cells, computed by the SAME `pr_template/lib/five_signals.py` the deck uses --
    one source of truth, so research and client pages can never disagree about what green means.
  * Forward data: the analyst's expected 3-5y growth (N100 research run + portfolio pf_qual files)
    joins in; where present it blends into the Growth signal exactly as on the deck page.
  * v2 corrected scores sit BESIDE v1 (thin-history fix, results/THIN_COVERAGE_FIX_NOTE.md):
    neutral-fill for missing pillars, withdrawal at <=3 of 7 pillars, growth-artefact neutralisation.
  * New flags: Thin history / growth artefact / one-time-income risk / PAT-Sales divergence.

Reads results/full750_scored_v2.csv (falls back to v1 with the v2 columns simply absent).
Internal research tool; not investment advice.
"""
import glob
import json
import os
import sys

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "pr_template", "lib")))
import five_signals as F                                                   # noqa: E402


def _nifty_root(p):
    while True:
        p, tail = os.path.split(p)
        if not tail:
            raise RuntimeError("NIFTY 500 root not found")
        if tail == "NIFTY 500":
            return os.path.join(p, tail)


ROOT = _nifty_root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
SRC_V2 = os.path.join(RES, "full750_scored_v2.csv")
SRC_V1 = os.path.join(RES, "full750_scored.csv")
OUT = os.path.join(ROOT, "Shreyas_Ionic_AMC", "09_PRODUCT", "reports",
                   "NIFTY750_SCORECARD_20260807.xlsx")

AS_OF = "2026-08-07"

# ---- forward growth estimates: every research output that carries one ------------------------------
def load_forward():
    fwd = {}
    n100 = os.path.join(RES, "N100_RESEARCH_SUMMARY.csv")
    if os.path.exists(n100):
        t = pd.read_csv(n100)
        for _, r in t.iterrows():
            v = pd.to_numeric(r.get("expected_next_3y_growth_pct"), errors="coerce")
            if pd.notna(v):
                fwd[str(r["symbol"]).strip().upper()] = float(v)
    for p in glob.glob(os.path.join(RES, "pf_qual_*.json")):
        sym = os.path.basename(p)[len("pf_qual_"):-len(".json")].upper()
        try:
            with open(p, "r", encoding="utf-8") as fh:
                v = json.load(fh).get("expected_next_3y_growth_pct")
            if v is not None:
                fwd[sym] = float(v)          # per-name research beats the batch summary
        except (OSError, ValueError, TypeError):
            continue
    return fwd


src = SRC_V2 if os.path.exists(SRC_V2) else SRC_V1
df = pd.read_csv(src)
df["roe"] = df["roe"] * 100
df["roce"] = df["roce"] * 100
FWD = load_forward()
df["fwd_growth_pct"] = df["symbol"].astype(str).str.upper().map(FWD)
has_v2 = "final_score_3y_v2" in df.columns

# five signals per row, via the deck's own lib (forward-blended Growth where an estimate exists)
_sig_rows = []
for _, r in df.iterrows():
    rec = dict(r)
    if pd.notna(r.get("fwd_growth_pct")):
        rec["growth_pct"] = float(r["fwd_growth_pct"])
    _sig_rows.append({c: v for c, v in F.signals(rec)})
for cat in F.CATS:
    df[f"sig::{cat}"] = [F.word(sr[cat]) for sr in _sig_rows]

# rank by the corrected score where it exists; withdrawn names sink to the bottom
sort_col = "final_score_3y_v2" if has_v2 else "final_score_3y"
df = df.sort_values(sort_col, ascending=False, na_position="last").reset_index(drop=True)

COLS = [
    ("symbol", "Symbol", None), ("sector", "Sector", None),
    ("recommendation_overall", "Call v1", None),
]
if has_v2:
    COLS += [("recommendation_v2", "Call v2", None)]
COLS += [("final_score_3y", "Score 3Y", 1)]
if has_v2:
    COLS += [("final_score_3y_v2", "Score 3Y v2", 1)]
COLS += [("final_score_1y", "Score 1Y", 1)]
if has_v2:
    COLS += [("final_score_1y_v2", "Score 1Y v2", 1)]
COLS += [(f"sig::{c}", c, None) for c in F.CATS]
COLS += [
    ("fwd_growth_pct", "Fwd Grw % (analyst)", 0),
    ("coverage_3y", "Cov 3Y %", 0),
]
if has_v2:
    COLS += [("thin_history_flag", "Thin Hist", None), ("growth_artifact_flag", "Grw Artefact", None),
             ("one_time_income_risk", "1-time Inc", None), ("pat_sales_divergence", "PAT/Sales Div", None)]
COLS += [
    ("quality_score", "Quality raw", 1), ("growth_3y_score", "Growth 3Y raw", 1),
    ("value_score", "Value raw", 1), ("stage_3y_score", "Stage 3Y raw", 1),
    ("sector_macro_3y_score", "Sector/Macro raw", 1),
    ("revenue_growth_1y", "Rev Grw 1Y %", 1), ("roe", "ROE %", 1), ("roce", "ROCE %", 1),
    ("pe_current", "P/E", 1), ("debt_equity", "D/E", 2), ("bs_flag", "BS Gate", None),
    ("latest_qtr", "Latest Qtr", None), ("market_cap_approx", "MktCap(cr)", 0),
]

NAVY = "1F3864"; HDRC = "FFFFFF"; RED = "F4CCCC"; GREEN = "D9EAD3"; MED = "FFF2CC"; GREY = "EEEEEE"
# signal band styling: tint fill + band ink, index-aligned to the lib's DOT_COLOURS ramp
SIG_FILL = {0: ("D2EDE0", "1E9E6A"), 1: ("EAF6F0", "3E8E6E"),
            2: ("FCEBCB", "92400E"), 3: ("FBE3E0", "E0402F")}
_WORD_TO_BAND = {w: i for i, w in enumerate(F.WORDS[F.DEFAULT_WORDS])}
thin_side = Side(style="thin", color="D9D9D9")
border = Border(bottom=thin_side)

wb = Workbook(); ws = wb.active; ws.title = "All Scores (750)"
ws["A1"] = "IONIC — Nifty-750 Quant Scorecard (v8, five signals + v2 thin-history fix)"
ws["A1"].font = Font(name="Georgia", size=15, bold=True, color=NAVY)
n = len(df)
n_wd = int((df.get("thin_history_flag", pd.Series(dtype=str)) == "WITHDRAWN").sum()) if has_v2 else 0
ws["A2"] = (f"As of {AS_OF}  |  {n} names  |  Signals = the client-deck five (quartile bands vs this "
            f"universe; Growth blends the analyst's forward estimate where one exists)  |  v2 = "
            f"thin-history corrected score ({n_wd} withdrawn at <=3 of 7 pillars)  |  "
            f"INTERNAL RESEARCH — not investment advice.")
ws["A2"].font = Font(name="Bahnschrift", size=9, italic=True, color="666666")
HDR_ROW = 4

hdr_fill = PatternFill("solid", fgColor=NAVY)
for j, (_, label, _) in enumerate(COLS, 1):
    c = ws.cell(HDR_ROW, j, label)
    c.font = Font(name="Bahnschrift", size=9, bold=True, color=HDRC)
    c.fill = hdr_fill
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

for i, row in df.iterrows():
    r = HDR_ROW + 1 + i
    for j, (col, _, dec) in enumerate(COLS, 1):
        v = row.get(col, "")
        if pd.isna(v):
            v = ""
        elif dec is not None:
            try:
                v = round(float(v), dec)
            except (ValueError, TypeError):
                pass
        cell = ws.cell(r, j, v)
        cell.font = Font(name="Bahnschrift", size=9)
        cell.border = border
        if col.startswith("sig::"):
            band = _WORD_TO_BAND.get(v)
            cell.alignment = Alignment(horizontal="center")
            if band is not None:
                fill, ink = SIG_FILL[band]
                cell.fill = PatternFill("solid", fgColor=fill)
                cell.font = Font(name="Bahnschrift", size=9, bold=True, color=ink)
            else:
                cell.font = Font(name="Bahnschrift", size=9, color="999999")
        elif col in ("final_score_3y", "final_score_1y", "final_score_3y_v2",
                     "final_score_1y_v2", "recommendation_overall", "recommendation_v2"):
            cell.font = Font(name="Bahnschrift", size=9, bold=True)
    for col, ci in (("recommendation_overall", 3), ("recommendation_v2", 4)):
        if col in df.columns and ci <= len(COLS) and COLS[ci - 1][0] == col:
            call = str(row.get(col, ""))
            cc = ws.cell(r, ci)
            cc.alignment = Alignment(horizontal="center")
            if call == "Sell":
                cc.fill = PatternFill("solid", fgColor=RED)
            elif call == "Hold":
                cc.fill = PatternFill("solid", fgColor=GREEN)
            elif call.startswith("No Rec"):
                cc.fill = PatternFill("solid", fgColor=GREY)
    if has_v2:
        th = str(row.get("thin_history_flag", ""))
        if th:
            jj = next((k + 1 for k, (c0, _, _) in enumerate(COLS) if c0 == "thin_history_flag"), None)
            if jj:
                ws.cell(r, jj).fill = PatternFill("solid", fgColor=RED if th == "WITHDRAWN" else MED)

ws.freeze_panes = "C5"
ws.auto_filter.ref = f"A{HDR_ROW}:{get_column_letter(len(COLS))}{HDR_ROW + n}"
widths = {"Symbol": 12, "Sector": 22, "Call v1": 8, "Call v2": 13, "Sector & Flows": 12,
          "Fwd Grw % (analyst)": 9, "Latest Qtr": 11}
for j, (_, label, _) in enumerate(COLS, 1):
    ws.column_dimensions[get_column_letter(j)].width = widths.get(label, 9.5)
ws.row_dimensions[HDR_ROW].height = 28

os.makedirs(os.path.dirname(OUT), exist_ok=True)
wb.save(OUT)
print("source:", os.path.basename(src))
print("rows:", n, "cols:", len(COLS), "fwd estimates joined:",
      int(df["fwd_growth_pct"].notna().sum()))
print("SAVED:", OUT)
