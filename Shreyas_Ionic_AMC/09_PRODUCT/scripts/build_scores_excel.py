"""build_scores_excel.py — clean Excel of ALL 750 scorecard scores from full750_scored.csv.
TTM v7 run (2026-07-21). Internal research tool; not investment advice."""
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SRC = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results", "full750_scored.csv")
OUT = os.path.join(ROOT, "Shreyas_Ionic_AMC", "09_PRODUCT", "reports", "NIFTY750_SCORECARD_20260721.xlsx")

df = pd.read_csv(SRC)
df["roe"] = df["roe"] * 100
df["roce"] = df["roce"] * 100

COLS = [
    ("symbol", "Symbol", None), ("sector", "Sector", None),
    ("recommendation_overall", "Call", None),
    ("final_score_3y", "Score 3Y", 1), ("final_score_1y", "Score 1Y", 1),
    ("recommendation_3y", "Rec 3Y", None), ("recommendation_1y", "Rec 1Y", None),
    ("quality_score", "Quality", 1), ("growth_3y_score", "Growth 3Y", 1),
    ("growth_1y_score", "Growth 1Y", 1), ("value_score", "Value", 1),
    ("stage_3y_score", "Stage 3Y", 1), ("stage_1y_score", "Stage 1Y", 1),
    ("sector_macro_3y_score", "Sector/Macro", 1),
    ("coverage_flag_3y", "Cov 3Y", None), ("coverage_flag_1y", "Cov 1Y", None),
    ("revenue_growth_1y", "Rev Grw 1Y %", 1), ("roe", "ROE %", 1), ("roce", "ROCE %", 1),
    ("pe_current", "P/E", 1), ("debt_equity", "D/E", 2), ("bs_flag", "BS Gate", None),
    ("ttm_growth", "Grw Src", None), ("latest_qtr", "Latest Qtr", None),
    ("stale_flag", "Stale", None), ("zero_cov_flag", "ZeroCov", None),
    ("market_cap_approx", "MktCap(cr)", 0),
]
df = df.sort_values("final_score_3y", ascending=False).reset_index(drop=True)

NAVY = "1F3864"; GOLD = "C9A227"; RED = "F4CCCC"; GREEN = "D9EAD3"
MED = "FFF2CC"; HDR = "FFFFFF"
thin = Side(style="thin", color="D9D9D9")
border = Border(bottom=thin)

wb = Workbook(); ws = wb.active; ws.title = "All Scores (750)"
# title block
ws["A1"] = "IONIC — Nifty-750 Quant Scorecard (TTM v7)"
ws["A1"].font = Font(name="Georgia", size=15, bold=True, color=NAVY)
n = len(df); nsell = int((df["recommendation_overall"] == "Sell").sum()); nhold = n - nsell
ws["A2"] = (f"As of 2026-07-21  |  {n} names  |  {nhold} Hold / {nsell} Sell  |  "
            f"Score = 0.60x3Y + 0.40x1Y percentile-composite; Call=Sell if score<40.  "
            f"INTERNAL RESEARCH — not investment advice.")
ws["A2"].font = Font(name="Bahnschrift", size=9, italic=True, color="666666")
HDR_ROW = 4

hdr_fill = PatternFill("solid", fgColor=NAVY)
for j, (_, label, _) in enumerate(COLS, 1):
    c = ws.cell(HDR_ROW, j, label)
    c.font = Font(name="Bahnschrift", size=9, bold=True, color=HDR)
    c.fill = hdr_fill
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

for i, row in df.iterrows():
    r = HDR_ROW + 1 + i
    for j, (col, _, dec) in enumerate(COLS, 1):
        v = row[col]
        if pd.isna(v):
            v = ""
        elif dec is not None:
            try:
                v = round(float(v), dec)
            except (ValueError, TypeError):
                pass
        elif col in ("stale_flag", "zero_cov_flag"):
            v = "Y" if bool(v) else ""
        cell = ws.cell(r, j, v)
        cell.font = Font(name="Bahnschrift", size=9)
        cell.border = border
        if col in ("final_score_3y", "final_score_1y", "recommendation_overall"):
            cell.font = Font(name="Bahnschrift", size=9, bold=True)
    # colour the Call cell
    call = row["recommendation_overall"]
    cc = ws.cell(r, 3)
    cc.fill = PatternFill("solid", fgColor=RED if call == "Sell" else GREEN)
    cc.alignment = Alignment(horizontal="center")
    # coverage flags amber/red
    for ci, colname in ((15, "coverage_flag_3y"), (16, "coverage_flag_1y")):
        fv = row[colname]
        if fv == "Med":
            ws.cell(r, ci).fill = PatternFill("solid", fgColor=MED)
        elif fv == "Low":
            ws.cell(r, ci).fill = PatternFill("solid", fgColor=RED)

ws.freeze_panes = "C5"
ws.auto_filter.ref = f"A{HDR_ROW}:{get_column_letter(len(COLS))}{HDR_ROW + n}"
widths = {"Symbol": 12, "Sector": 24, "Call": 7, "Latest Qtr": 11, "Grw Src": 9}
for j, (_, label, _) in enumerate(COLS, 1):
    ws.column_dimensions[get_column_letter(j)].width = widths.get(label, 9.5)
ws.row_dimensions[HDR_ROW].height = 28

os.makedirs(os.path.dirname(OUT), exist_ok=True)
wb.save(OUT)
print("rows:", n, "cols:", len(COLS))
print("SAVED:", OUT)
