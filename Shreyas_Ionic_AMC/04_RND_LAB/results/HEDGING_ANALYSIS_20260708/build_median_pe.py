import os, glob
os.environ.setdefault("PYTHONIOENCODING","utf-8")
import numpy as np, pandas as pd
ROOT=r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUTDATA=os.path.join(ROOT,r"Shreyas_Ionic_AMC\04_RND_LAB\results\HEDGING_ANALYSIS_20260708\data")

# ---- Annual EPS per symbol, PIT (longer history than quarterly) ----
y=pd.read_parquet(os.path.join(ROOT,"datasets/earnings_pit/yearly_profit_loss_pit.parquet"))
y=y[["nse_symbol","year_end","available_date","EPS in Rs"]].rename(
    columns={"nse_symbol":"symbol","EPS in Rs":"ttm_eps"}).dropna(subset=["symbol","year_end","ttm_eps"]).copy()
y["year_end"]=pd.to_datetime(y["year_end"],errors="coerce")
y["available_date"]=pd.to_datetime(y["available_date"],errors="coerce")
y=y.dropna(subset=["year_end"]).sort_values(["symbol","year_end"])
y["available_date"]=y["available_date"].fillna(y["year_end"]+pd.Timedelta(days=90))
y["known"]=y.groupby("symbol")["available_date"].cummax()
ttm=y[["symbol","known","ttm_eps"]].rename(columns={"known":"date"}).sort_values(["symbol","date"])

# ---- price panel (broad, PRICE basis) ----
pp=None
for cand in ["datasets/derived/pit_union_panel_v1/close_panel_price.parquet",
             "datasets/derived/pit_union_panel_v1/close_panel_return.parquet"]:
    p=os.path.join(ROOT,cand)
    if os.path.exists(p): pp=pd.read_parquet(p); print("price panel:",cand,pp.shape); break
if pp is None: raise SystemExit("no price panel")
pp["date"]=pd.to_datetime(pp["date"])
wide=pp.pivot_table(index="date",columns="symbol",values="close",aggfunc="last")
mprice=wide.resample("ME").last()   # month-end close, wide (dates x symbols)

# month-end grid 2016-06 .. 2026-07
months=mprice.index[(mprice.index>="2016-06-30")]
syms_price=set(mprice.columns)
rows=[]
for dt in months:
    # latest TTM eps per symbol known as-of dt
    sub=ttm[ttm["date"]<=dt]
    if sub.empty: continue
    last=sub.groupby("symbol")["ttm_eps"].last()
    px=mprice.loc[dt]
    common=[s for s in last.index if s in syms_price and pd.notna(px.get(s))]
    if len(common)<50: continue
    e=last.reindex(common).values; pr=px.reindex(common).values
    pe=pr/e
    pe=pe[(e>0)&np.isfinite(pe)&(pe>2)&(pe<150)]   # sane positive-earnings names
    if len(pe)<50: continue
    rows.append(dict(date=dt,median_pe=np.median(pe),mean_pe=np.mean(pe),
                     p25_pe=np.percentile(pe,25),p75_pe=np.percentile(pe,75),n_stocks=len(pe)))
med=pd.DataFrame(rows).set_index("date")
med.to_parquet(os.path.join(OUTDATA,"india_market_median_pe.parquet"))
print("\nmedian PE series:",med.shape,med.index.min().date(),"->",med.index.max().date())
print(med.tail(4).round(1).to_string())
print("\nmedian_pe  min/med/max:",round(med.median_pe.min(),1),round(med.median_pe.median(),1),round(med.median_pe.max(),1))
print("avg n_stocks:",int(med.n_stocks.mean()))

# ---- compare vs cap-weighted index PE (large-cap bias) ----
a=pd.read_parquet(os.path.join(ROOT,"datasets/index_daily/nse_official_all_indices.parquet"))
def idxpe(nm):
    d=a[a.index_name==nm].copy(); d["date"]=pd.to_datetime(d["date"])
    return d.set_index("date")["pe"].resample("ME").last()
cmp=pd.DataFrame({"MEDIAN_stocklevel":med["median_pe"],
   "Nifty50_capwt":idxpe("Nifty 50"),"Nifty500_capwt":idxpe("Nifty 500"),
   "TotalMarket_capwt":idxpe("Nifty Total Market"),"Nifty50_EqWt":idxpe("NIFTY50 Equal Weight")}).dropna(how="all")
print("\n=== cap-weighted index PE vs true cross-sectional MEDIAN PE (latest 3) ===")
print(cmp.tail(3).round(1).to_string())
print("\nfull-sample means:\n",cmp.mean().round(1).to_string())
