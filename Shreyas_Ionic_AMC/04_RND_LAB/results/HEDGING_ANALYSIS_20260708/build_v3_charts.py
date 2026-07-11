# -*- coding: utf-8 -*-
import os, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT=os.path.dirname(os.path.abspath(__file__)); RES=os.path.join(OUT,"results"); CH=os.path.join(OUT,"charts")
cur=json.load(open(os.path.join(RES,"current_subregime.json")))
BLUE="#1f3b6f"; RED="#b3202c"; GRN="#1a7a3c"; ORA="#d98a00"
plt.rcParams.update({"font.size":10,"figure.dpi":130})

# 1) sub-regime quadrant map with current segment positions
fig,ax=plt.subplots(figsize=(8,4.2))
cols=["CHEAP_FALL","CHEAP_RECOV","FAIR","RICH_CALM","RICH_EXT"]
xpos={c:i for i,c in enumerate(cols)}
bg=[ "#fde0e0","#e6f2e6","#f2f2f2","#fff2d9","#f7d6d6"]
for i,c in enumerate(cols):
    ax.axvspan(i-0.5,i+0.5,color=bg[i],alpha=0.7)
label={"US":"US S&P500 (CAPE)","INDIA_LARGE":"India NIFTY50 (PB)","INDIA_BROAD":"India broad (median-PE)","INDIA_SMALLCAP":"India smallcap"}
yy={"US":3.3,"INDIA_LARGE":2.4,"INDIA_BROAD":1.5,"INDIA_SMALLCAP":0.6}
for seg,sr in cur.items():
    x=xpos[sr]; y=yy[seg]
    ax.scatter([x],[y],s=140,color=BLUE,zorder=5)
    ax.annotate(label[seg]+f"\n[{sr}]",(x,y),xytext=(0,10),textcoords="offset points",ha="center",fontsize=8,fontweight="bold")
ax.set_xticks(range(len(cols))); ax.set_xticklabels(["CHEAP\nfalling","CHEAP\nrecovering","FAIR","RICH\ncalm","RICH\nextended"])
ax.set_yticks([]); ax.set_ylim(0,4); ax.set_xlim(-0.5,4.5)
ax.set_title("Where each market sits TODAY — valuation × momentum sub-regime (2026-07)")
recs=["cheap put-spread-collar","LONG ATM put (keep rebound)","annual collar","annual collar 95/105","collar 95/105 + backspread kicker"]
for i,r in enumerate(recs):
    ax.annotate(r,(i,0.12),ha="center",fontsize=6.8,style="italic",color="#444")
fig.tight_layout(); fig.savefig(os.path.join(CH,"subregime_map.png")); plt.close()

# 2) US sub-regime hedge efficacy: unhedged vs hedged maxdd
h=pd.read_csv(os.path.join(RES,"subregime_hedge_recs_US.csv"))
h=h.set_index("subregime").reindex(cols).dropna(how="all")
fig,ax=plt.subplots(figsize=(8,3.6)); x=np.arange(len(h)); w=0.38
ax.bar(x-w/2,h["unhedged_maxdd"]*100,w,color="#bbb",label="Unhedged maxDD")
ax.bar(x+w/2,h["maxdd"]*100,w,color=BLUE,label="Best net-hedge-positive overlay")
for i,(idx,r) in enumerate(h.iterrows()):
    ax.annotate(f"{r['best_hedge'].replace('H_','')}\n{r['tenor']}",(i+w/2,r['maxdd']*100),xytext=(0,4),textcoords="offset points",ha="center",fontsize=6.5)
ax.set_xticks(x); ax.set_xticklabels(h.index,fontsize=8); ax.set_ylabel("Max drawdown %")
ax.set_title("U.S.: max-drawdown, unhedged vs best net-hedge-positive overlay, by sub-regime"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(CH,"us_subregime_hedge.png")); plt.close()
print("v3 charts done")
