"""MARGINAL-ADD TEST (Principal correction 2026-07-30).

Principal: "if corr is there but lesser than certain threshold and we can create extra cagr and sharpe
it is better to add, 0.2-0.4 corrl is not a bad thing."  CORRECT — and it is the textbook condition:

    ADD improves portfolio Sharpe  <=>  S_candidate > rho * S_portfolio

A raw correlation threshold is NOT the decision rule. High correlation matters as a warning that two
sleeves are the SAME BET (e.g. SWEEP_E vs SWEEP_D at 0.82 share one entry signal) — not as a veto on a
0.2-0.4 sleeve that carries real standalone performance.
Reported: the analytic condition, plus the EMPIRICAL book Sharpe/CAGR/maxDD at 5/10/15/20% weight,
because the analytic test speaks only to Sharpe and says nothing about drawdown or tail.
"""
from __future__ import annotations
import warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results")
LOT, CARRY_M = 75, 0.005
BOOK_CAP = 1_00_00_000.0

def dser(df, dc, vc):
    x = df[[dc, vc]].copy(); x[dc] = pd.to_datetime(x[dc])
    return x.groupby(x[dc].dt.normalize())[vc].sum().sort_index()

S = {}
for tag, fn in (("SWEEP_E","trades_E_swing3_trail60_1lot.csv"),("SWEEP_D","trades_D_overnight1_trail40_1lot.csv")):
    t = pd.read_csv(R/"SWEEP_11YR_20260729"/fn); t["date"]=pd.to_datetime(t["date"])
    cy=t["entry"]*(CARRY_M/30.0)*np.maximum(t["hold_min"]/375.0,0.5)
    t["net"]=(t["gross_pts"]-np.sign(t["dir"])*cy)*LOT-t["cost"]; S[tag]=dser(t,"date","net")
rc=pd.read_csv(R/"RATIO_CALENDAR_20260730"/"grid_a_trades_raw.csv")
c=rc[(rc.strike_struct=="ATM_ATM")&(rc.ratio=="1x1")&(rc.exit_variant=="3d_before")].drop_duplicates(subset=["day0","near_expiry"]).copy()
c["net"]=c["net_pts"]*LOT; S["CALENDAR_1x1"]=dser(c,"exit_day","net")
sw=pd.read_csv(R/"SWING_DELTA1_20260729"/"all_trades.csv")
m=[x for x in sw["cell"].unique() if "priorweek" in x and "fixed_10" in x]
if m: S["SWING_pw10"]=dser(sw[sw["cell"]==m[0]],"exit_date","net")
bk=pd.read_csv(R/"STACKED_BOOK_20260711"/"book_daily_pnl.csv",index_col=0); bk.index=pd.to_datetime(bk.index)
BOOK=bk["total"].sort_index()

def met(s, cap):
    eq=cap+s.cumsum(); pk=eq.cummax(); mdd=float(((eq-pk)/pk).min())
    yrs=max((s.index.max()-s.index.min()).days/365.25,.01)
    cagr=(float(eq.iloc[-1])/cap)**(1/yrs)-1 if eq.iloc[-1]>0 else np.nan
    r=s/cap; sh=float(r.mean()/r.std()*np.sqrt(252)) if r.std()>0 else np.nan
    mo=s.resample("ME").sum()
    return dict(CAGR=100*cagr, Sharpe=sh, maxDD=100*mdd,
                Calmar=cagr/abs(mdd) if mdd else np.nan,
                worst_mo=100*float(mo.min()/cap))
b=met(BOOK,BOOK_CAP)
print("="*122); print(f"BASELINE BOOK: CAGR {b['CAGR']:.2f}%  Sharpe {b['Sharpe']:.2f}  maxDD {b['maxDD']:.2f}%  Calmar {b['Calmar']:.2f}  worst-mo {b['worst_mo']:.2f}%")
print("="*122)
print("ANALYTIC TEST:  add helps Sharpe  <=>  S_cand > rho * S_book")
print(f"{'candidate':<15}{'S_cand':>8}{'rho_mo':>8}{'bar=rho*S_bk':>14}{'passes?':>9}   {'note':<40}")
print("-"*122)
bm=BOOK.resample("ME").sum()
for k,s in S.items():
    ms=met(s,10_00_000.0)
    sm=s.resample("ME").sum(); i=bm.index.intersection(sm.index)
    rho=float(bm[i].corr(sm[i]))
    bar=rho*b["Sharpe"]
    ok = ms["Sharpe"]>bar
    note = "PASS with huge margin" if ms["Sharpe"]>3*max(bar,0.05) else ("PASS" if ok else "FAIL")
    print(f"{k:<15}{ms['Sharpe']:>8.2f}{rho:>8.3f}{bar:>14.3f}{str(ok):>9}   {note:<40}")

print(); print("="*122); print("EMPIRICAL: book metrics after blending each sleeve at w% of the Rs1cr book"); print("="*122)
print(f"{'candidate':<15}{'w':>5}{'CAGR':>9}{'dCAGR':>8}{'Sharpe':>8}{'dSharpe':>9}{'maxDD':>9}{'dMDD':>8}{'Calmar':>8}{'worst_mo':>10}")
print("-"*122)
rows=[]
for k,s in S.items():
    for w in (0.05,0.10,0.15,0.20):
        idx=BOOK.index
        comb=BOOK.add((s*(w/0.10)).reindex(idx).fillna(0.0),fill_value=0.0)  # sleeve sized at 10%->w scaling
        mm=met(comb,BOOK_CAP)
        print(f"{k:<15}{int(w*100):>4}%{mm['CAGR']:>9.2f}{mm['CAGR']-b['CAGR']:>+8.2f}{mm['Sharpe']:>8.2f}"
              f"{mm['Sharpe']-b['Sharpe']:>+9.2f}{mm['maxDD']:>9.2f}{mm['maxDD']-b['maxDD']:>+8.2f}"
              f"{mm['Calmar']:>8.2f}{mm['worst_mo']:>10.2f}")
        rows.append(dict(cand=k,w=w,**{kk:round(vv,3) for kk,vv in mm.items()}))
    print("-"*122)
pd.DataFrame(rows).to_csv("marginal_add.csv",index=False)
print("wrote marginal_add.csv")
