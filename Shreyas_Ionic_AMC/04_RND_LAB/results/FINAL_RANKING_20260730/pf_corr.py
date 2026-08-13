"""PORTFOLIO-vs-STRATEGY correlation + WORST-MONTH behaviour (Principal correction, 2026-07-30).

Principal: "do not look strategy-strategy corrl, look portfolio-strategy corrl."
Correct: what matters for adding a sleeve is its relationship to the BOOK YOU ALREADY OWN.
Also resolves a tension I flagged: SWING is the MOST book-correlated (0.36/0.41) yet was credited with
cutting book maxDD -18.4%->-9.5%. Average correlation and worst-month behaviour are different things,
so both are reported here. Worst-month behaviour is what actually protects a book.
"""
from __future__ import annotations
import warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results")
LOT, CARRY_M = 75, 0.005

def d(df, dc, vc):
    x = df[[dc, vc]].copy(); x[dc] = pd.to_datetime(x[dc])
    return x.groupby(x[dc].dt.normalize())[vc].sum().sort_index()

S = {}
for tag, fn in (("SWEEP_E","trades_E_swing3_trail60_1lot.csv"),("SWEEP_D","trades_D_overnight1_trail40_1lot.csv")):
    t = pd.read_csv(R/"SWEEP_11YR_20260729"/fn); t["date"]=pd.to_datetime(t["date"])
    cy = t["entry"]*(CARRY_M/30.0)*np.maximum(t["hold_min"]/375.0,0.5)
    t["net"]=(t["gross_pts"]-np.sign(t["dir"])*cy)*LOT-t["cost"]; S[tag]=d(t,"date","net")
rc = pd.read_csv(R/"RATIO_CALENDAR_20260730"/"grid_a_trades_raw.csv")
c = rc[(rc.strike_struct=="ATM_ATM")&(rc.ratio=="1x1")&(rc.exit_variant=="3d_before")].drop_duplicates(subset=["day0","near_expiry"]).copy()
c["net"]=c["net_pts"]*LOT; S["CALENDAR_1x1"]=d(c,"exit_day","net")
sw = pd.read_csv(R/"SWING_DELTA1_20260729"/"all_trades.csv")
m=[x for x in sw["cell"].unique() if "priorweek" in x and "fixed_10" in x]
if m: S["SWING_pw10"]=d(sw[sw["cell"]==m[0]],"exit_date","net")
bk = pd.read_csv(R/"STACKED_BOOK_20260711"/"book_daily_pnl.csv",index_col=0); bk.index=pd.to_datetime(bk.index)
BOOK = bk["total"].sort_index()

bm = BOOK.resample("ME").sum(); bq = BOOK.resample("QE").sum()
print("="*118); print("PORTFOLIO-vs-STRATEGY  (BOOK_total is the portfolio you already own)"); print("="*118)
print(f"{'candidate':<15}{'ov.mo':>7}{'corr_mo':>10}{'corr_qtr':>10}{'beta_mo':>9}   {'verdict':<26}")
print("-"*118)
rows=[]
for k,s in S.items():
    sm=s.resample("ME").sum(); sq=s.resample("QE").sum()
    im=bm.index.intersection(sm.index); iq=bq.index.intersection(sq.index)
    cm=float(bm[im].corr(sm[im])) if len(im)>=6 else np.nan
    cq=float(bq[iq].corr(sq[iq])) if len(iq)>=6 else np.nan
    beta=float(np.polyfit(bm[im],sm[im],1)[0]) if len(im)>=6 else np.nan
    if np.isnan(cm) or np.isnan(cq): v="insufficient overlap"
    elif np.sign(cm)!=np.sign(cq): v="~ZERO (sign flips)"
    elif max(abs(cm),abs(cq))>0.35: v="CORRELATED - weak diversifier"
    elif cq<-0.15: v="NEGATIVE - true diversifier"
    else: v="LOW - good diversifier"
    print(f"{k:<15}{len(im):>7}{cm:>10.3f}{cq:>10.3f}{beta:>9.3f}   {v:<26}")
    rows.append({"cand":k,"corr_mo":round(cm,3),"corr_qtr":round(cq,3),"beta_mo":round(beta,3),"verdict":v})

print(); print("="*118)
print("WORST-MONTH BEHAVIOUR — what actually protects a book (book's 6 worst months)")
print("="*118)
worst = bm.nsmallest(6).sort_values()
hdr=f"{'month':<10}{'BOOK':>12}" + "".join(f"{k:>15}" for k in S)
print(hdr); print("-"*len(hdr))
helped={k:0 for k in S}
for mth,bv in worst.items():
    line=f"{mth:%Y-%m':<10}"[:10].ljust(10)+f"{bv:>12,.0f}"
    for k,s in S.items():
        sm=s.resample("ME").sum()
        v=sm.get(mth,np.nan)
        line+=("            n/a" if pd.isna(v) else f"{v:>15,.0f}")
        if not pd.isna(v) and v>0: helped[k]+=1
    print(line)
print("-"*len(hdr))
print(f"{'positive in':<10}{'':>12}"+"".join(f"{f'{helped[k]}/6':>15}" for k in S))
pd.DataFrame(rows).to_csv("portfolio_strategy_corr.csv",index=False)
print("\nwrote portfolio_strategy_corr.csv")
