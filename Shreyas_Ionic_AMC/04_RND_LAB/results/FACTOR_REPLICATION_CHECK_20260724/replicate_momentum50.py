"""
FACTOR REPLICATION CHECK — NIFTY 500 Momentum 50 (approximation).
Owner: Arjun Rao (Head of Quant). Date: 2026-07-24.

PURPOSE: replicate the OFFICIAL NSE "NIFTY 500 Momentum 50" NAV using OUR OWN data
(canonical price panel + real historical Nifty-500 membership + current mcaps) and
measure how closely our replication tracks the official series. This is a DATA/METHOD
QUALITY test, not a new strategy. Verdict = do we trust our pipeline?

APPROXIMATION (we do NOT have NSE's exact proprietary methodology doc):
  score_i = mean( z(r6/vol6), z(r12/vol12) )   [risk-adjusted 6M & 12M momentum, x-sectional z]
  norm_i  = (1+z) if z>=0 else 1/(1-z)          [NSE-style positive momentum multiplier]
  select  = top 50 by score
  weight  ~ norm_i * mcap_backprojected_i, capped 5%, iterated
  rebal   = semi-annual (Jun / Dec end), membership = most-recent Mar/Sep snapshot at-or-before

PIT / LANDMINE handling (documented, not silent):
  - price panel capped at 2026-01-22 (only 13/2566 syms have data past Jan-2026; verified).
  - membership snapshot is most-recent-AT-OR-BEFORE each rebalance (no forward membership).
  - mcap back-projected via constant implied shares (= current_mcap/current_price) so historical
    weights use REAL historical prices, NOT current absolute mcap (that would be a lookahead leak).
  - exclusion rate (members we cannot match to price+mcap) measured & reported per year.
  - costs applied on REALIZED TURNOVER ONLY, tier-based (COST_STANDARDS.md), 1x headline + 2x stress.
  - official index is ~TRI; our panel is corp-action-spliced but likely EX-dividend -> expect a
    small systematic CAGR shortfall (~1-1.5%/yr). Flagged, not hidden.
"""
import os, sys, json
os.environ["PYTHONIOENCODING"] = "utf-8"; os.environ["PYTHONUNBUFFERED"] = "1"
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT  = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "results", "FACTOR_REPLICATION_CHECK_20260724")
NAV_F   = os.path.join(ROOT, "datasets", "index_daily", "factor_navs_principal.parquet")
PANEL_F = os.path.join(ROOT, "datasets", "derived", "pit_union_panel_v1", "close_panel_return_v11.parquet")
TICK_F  = os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx")
MCAP_F  = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results", "full750_scored.csv")

SERIES     = "NIFTY 500 Momentum 50"
PANEL_CAP  = pd.Timestamp("2026-01-22")   # verified real end for mass of symbols
TOPN       = 50
WCAP       = 0.05
LB6, LB12  = 126, 252
MIN_HIST   = 252

# ---- cost model (COST_STANDARDS.md): one-way, of traded value ----
SLIP = {"Large": 0.0010, "Mid": 0.0020, "Small": 0.0035}   # bps floors by mcap tercile
def oneway_cost(tier):
    slip = SLIP.get(tier, 0.0035)
    stt  = 0.0010                 # delivery STT 0.1% (both sides -> applies each leg)
    exch = 0.0000297              # NSE equity txn
    stamp= 0.000075               # ~avg of 0.015% buy / 0 sell
    sebi = 0.000001               # Rs10/cr
    gst  = 0.18 * (exch + sebi)   # GST on (brokerage+exch+SEBI); brokerage ~0 on % basis
    return slip + stt + exch + stamp + sebi + gst

# --------------------------------------------------------------------------- #
def snap_key(ts):
    """rebalance ts -> most-recent Mar/Sep snapshot label at-or-before it."""
    y = ts.year
    if ts >= pd.Timestamp(y, 9, 1):   return f"Sep{y}"
    if ts >= pd.Timestamp(y, 3, 1):   return f"Mar{y}"
    return f"Sep{y-1}"

def zscore(x):
    x = np.asarray(x, float); m = np.nanmean(x); s = np.nanstd(x)
    return (x - m) / s if s > 0 else np.zeros_like(x)

def norm_mom(z):
    return np.where(z >= 0, 1 + z, 1 / (1 - z))

def cap_weights(w, cap):
    w = w / w.sum()
    for _ in range(100):
        over = w > cap
        if not over.any(): break
        excess = (w[over] - cap).sum()
        w[over] = cap
        room = ~over
        if not room.any(): break
        w[room] += excess * (w[room] / w[room].sum())
    return w / w.sum()

# --------------------------------------------------------------------------- #
print("Loading official NAV ...", flush=True)
nav = pd.read_parquet(NAV_F)
off = nav[nav["series"] == SERIES][["date", "nav"]].copy()
off["date"] = pd.to_datetime(off["date"]); off = off.sort_values("date").reset_index(drop=True)
print(f"  official {SERIES}: {len(off)} rows, {off['date'].min().date()} -> {off['date'].max().date()}", flush=True)

print("Loading membership snapshots ...", flush=True)
tick = pd.read_excel(TICK_F)
MEMB = {k: set(g["Ticker"].astype(str).str.strip()) for k, g in tick.groupby("Month-Year")}
print(f"  {len(MEMB)} snapshots; union tickers = {len(set().union(*MEMB.values()))}", flush=True)
uni_tickers = set().union(*MEMB.values())

print("Loading current mcaps ...", flush=True)
sc = pd.read_csv(MCAP_F)
MCAP = {r.symbol: float(r.market_cap_approx) for r in sc.itertuples()
        if pd.notna(r.market_cap_approx) and float(r.market_cap_approx) > 0}
TIER = {r.symbol: str(r.mcap_tercile) for r in sc.itertuples()}
print(f"  {len(MCAP)} symbols with positive mcap", flush=True)

print("Loading price panel (filtered to membership union) ...", flush=True)
pan = pd.read_parquet(PANEL_F, columns=["date", "symbol", "close"])
pan["date"] = pd.to_datetime(pan["date"])
pan = pan[(pan["symbol"].isin(uni_tickers)) & (pan["date"] <= PANEL_CAP)]
px = pan.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").sort_index()
px = px[px.index >= pd.Timestamp("2003-01-01")]
print(f"  wide px: {px.shape[0]} dates x {px.shape[1]} symbols; {px.index.min().date()} -> {px.index.max().date()}", flush=True)
rets = px.pct_change()

# implied constant shares from current mcap / current price (last available close per symbol)
last_px = px.ffill().iloc[-1]
SHARES = {s: MCAP[s] / last_px[s] for s in px.columns if s in MCAP and pd.notna(last_px.get(s)) and last_px.get(s) > 0}

# --------------------------------------------------------------------------- #
# rebalance dates: end-Jun & end-Dec, from 2005-06 while <= panel end
rebals = []
for y in range(2005, 2027):
    for m in (6, 12):
        d = pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)
        if off["date"].min() <= d <= px.index.max():
            # snap to nearest available trading day <= d
            avail = px.index[px.index <= d]
            if len(avail): rebals.append(avail[-1])
rebals = sorted(set(rebals))
print(f"\n{len(rebals)} rebalances: {rebals[0].date()} -> {rebals[-1].date()}", flush=True)

excl_rows = []
weight_hist = {}   # rebal_date -> Series(weights)
for rb in rebals:
    key = snap_key(rb)
    members = MEMB.get(key, set())
    hist = px.loc[:rb]
    elig = []
    for s in members:
        if s not in px.columns: continue
        col = hist[s].dropna()
        if len(col) < MIN_HIST: continue
        if s not in MCAP: continue
        if pd.isna(px.loc[rb, s]) if rb in px.index else True: continue
        elig.append(s)
    n_price = sum(1 for s in members if s in px.columns and len(hist[s].dropna()) >= MIN_HIST)
    excl_rows.append(dict(rebal=rb, snapshot=key, n_members=len(members),
                          n_with_price=n_price, n_eligible=len(elig)))
    if len(elig) < TOPN:
        weight_hist[rb] = pd.Series(dtype=float); continue
    # momentum score
    rows = []
    for s in elig:
        col = hist[s].dropna()
        p_now = col.iloc[-1]
        r6  = p_now / col.iloc[-LB6] - 1
        r12 = p_now / col.iloc[-LB12] - 1
        dr = col.pct_change().dropna()
        v6  = dr.iloc[-LB6:].std()  * np.sqrt(252)
        v12 = dr.iloc[-LB12:].std() * np.sqrt(252)
        if v6 <= 0 or v12 <= 0 or not np.isfinite(v6) or not np.isfinite(v12): continue
        rows.append((s, r6 / v6, r12 / v12))
    dfm = pd.DataFrame(rows, columns=["symbol", "ra6", "ra12"]).dropna()
    dfm["score"] = (zscore(dfm["ra6"]) + zscore(dfm["ra12"])) / 2
    dfm = dfm.sort_values("score", ascending=False).head(TOPN).copy()
    dfm["norm"] = norm_mom(zscore(dfm["score"]))    # re-z within the 50, NSE-style positive multiplier
    dfm["mcap_t"] = [SHARES.get(s, np.nan) * px.loc[rb, s] for s in dfm["symbol"]]
    dfm = dfm.dropna(subset=["mcap_t"])
    w = (dfm["norm"] * dfm["mcap_t"]).values
    w = cap_weights(w, WCAP)
    weight_hist[rb] = pd.Series(w, index=dfm["symbol"].values)

excl = pd.DataFrame(excl_rows)
excl["excl_rate"] = 1 - excl["n_eligible"] / excl["n_members"]
print("\nExclusion by rebalance (members -> eligible):", flush=True)
print(excl[["rebal","snapshot","n_members","n_with_price","n_eligible","excl_rate"]].to_string(index=False), flush=True)

# --------------------------------------------------------------------------- #
# simulate daily replication NAV with drift + turnover costs at rebalance
print("\nSimulating replication NAV ...", flush=True)
def simulate(cost_mult):
    dates = px.index[px.index >= rebals[0]]
    nav_v = 100.0
    out = [(rebals[0], nav_v)]
    cur_w = weight_hist[rebals[0]].copy()
    # apply entry cost at first rebalance (full deploy)
    entry_cost = sum(abs(cur_w[s]) * oneway_cost(TIER.get(s, "Small")) for s in cur_w.index) * cost_mult
    nav_v *= (1 - entry_cost)
    rb_idx = 0
    prev_date = rebals[0]
    for d in dates[1:]:
        r = rets.loc[d, cur_w.index].fillna(0.0)
        port_r = float((cur_w * r).sum())
        nav_v *= (1 + port_r)
        # drift weights
        cur_w = cur_w * (1 + r); cur_w = cur_w / cur_w.sum()
        # rebalance?
        if rb_idx + 1 < len(rebals) and d >= rebals[rb_idx + 1]:
            rb_idx += 1
            new_w = weight_hist[rebals[rb_idx]]
            if len(new_w) >= TOPN:
                allsym = cur_w.index.union(new_w.index)
                a = cur_w.reindex(allsym).fillna(0.0)
                b = new_w.reindex(allsym).fillna(0.0)
                dturn = (b - a).abs()
                cost = sum(dturn[s] * oneway_cost(TIER.get(s, "Small")) for s in allsym) * cost_mult
                nav_v *= (1 - cost)
                cur_w = new_w.copy()
        out.append((d, nav_v))
    s = pd.Series(dict(out)); s.index = pd.to_datetime(s.index)
    return s.sort_index()

rep1 = simulate(1.0)
rep2 = simulate(2.0)

# --------------------------------------------------------------------------- #
def metrics(rep, off_df, label):
    m = pd.merge(rep.rename("rep").reset_index().rename(columns={"index":"date"}),
                 off_df.rename(columns={"nav":"off"}), on="date", how="inner").sort_values("date")
    if len(m) < 30: return None
    base_r, base_o = m["rep"].iloc[0], m["off"].iloc[0]
    m["rep_i"] = m["rep"] / base_r * 100
    m["off_i"] = m["off"] / base_o * 100
    mm = m.set_index("date").resample("ME").last().dropna()
    mm["rr"] = mm["rep_i"].pct_change(); mm["ro"] = mm["off_i"].pct_change()
    mm = mm.dropna()
    corr = mm["rr"].corr(mm["ro"])
    te = (mm["rr"] - mm["ro"]).std() * np.sqrt(12)
    yrs = (m["date"].iloc[-1] - m["date"].iloc[0]).days / 365.25
    cagr_r = (m["rep_i"].iloc[-1] / 100) ** (1/yrs) - 1
    cagr_o = (m["off_i"].iloc[-1] / 100) ** (1/yrs) - 1
    tr_r = m["rep_i"].iloc[-1] / 100 - 1
    tr_o = m["off_i"].iloc[-1] / 100 - 1
    return dict(label=label, start=str(m["date"].iloc[0].date()), end=str(m["date"].iloc[-1].date()),
                n_months=len(mm), monthly_corr=round(float(corr),4),
                ann_tracking_error=round(float(te),4), cagr_rep=round(float(cagr_r),4),
                cagr_off=round(float(cagr_o),4), cagr_delta=round(float(cagr_r-cagr_o),4),
                total_ret_rep=round(float(tr_r),4), total_ret_off=round(float(tr_o),4),
                total_ret_delta=round(float(tr_r-tr_o),4)), m

res = {}
full1, mfull = metrics(rep1, off, "full_1x")
res["full_1x"] = full1
res["full_2x"] = metrics(rep2, off, "full_2x")[0]
# recent sub-window (2015+) where mcap coverage is better
off15 = off[off["date"] >= "2015-01-01"]
rep1_15 = rep1[rep1.index >= "2015-01-01"]
res["recent_2015_1x"] = metrics(rep1_15, off15, "recent_2015_1x")[0]

# exclusion by year
excl["year"] = excl["rebal"].dt.year
excl_yr = excl.groupby("year").agg(n_members=("n_members","mean"), n_eligible=("n_eligible","mean"),
                                    excl_rate=("excl_rate","mean")).round(3).reset_index()

print("\n===== METRICS =====", flush=True)
for k,v in res.items():
    if v: print(k, "->", {kk:v[kk] for kk in ("start","end","monthly_corr","ann_tracking_error","cagr_rep","cagr_off","cagr_delta","total_ret_delta")}, flush=True)

# --------------------------------------------------------------------------- #
# plot (log scale)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), height_ratios=[3, 1])
ax1.plot(mfull["date"], mfull["off_i"], label="Official NIFTY 500 Momentum 50", lw=1.6, color="#1a1a2e")
ax1.plot(mfull["date"], mfull["rep_i"], label="Our replication (approx)", lw=1.4, color="#c8102e", alpha=0.85)
ax1.set_yscale("log"); ax1.legend(loc="upper left"); ax1.grid(alpha=0.3, which="both")
ax1.set_title(f"NIFTY 500 Momentum 50 — replication vs official (rebased 100 @ {res['full_1x']['start']}, log scale)\n"
              f"monthly corr={res['full_1x']['monthly_corr']}  ann.TE={res['full_1x']['ann_tracking_error']:.1%}  "
              f"CAGR {res['full_1x']['cagr_rep']:.1%} vs {res['full_1x']['cagr_off']:.1%} (Δ{res['full_1x']['cagr_delta']:+.1%})")
ax1.set_ylabel("Rebased NAV (log)")
# exclusion rate bars
ax2.bar(excl_yr["year"], excl_yr["excl_rate"]*100, color="#888", width=0.7)
ax2.set_ylabel("member exclusion %"); ax2.set_xlabel("year"); ax2.grid(alpha=0.3, axis="y")
ax2.set_title("Membership names we could NOT match to price+mcap (higher = less reliable era)", fontsize=9)
plt.tight_layout()
png = os.path.join(OUT, "momentum50_replication.png")
plt.savefig(png, dpi=110); plt.close()
print(f"\nsaved {png}", flush=True)

out_json = dict(series=SERIES, generated="2026-07-24", owner="Arjun Rao",
                panel_cap=str(PANEL_CAP.date()), official_range=[str(off['date'].min().date()), str(off['date'].max().date())],
                methodology="approx: mean(z(r6/vol6),z(r12/vol12)); top50; w~norm_mom*backproj_mcap cap5%; semiannual Jun/Dec",
                metrics=res, exclusion_by_year=excl_yr.to_dict(orient="records"),
                n_rebalances=len(rebals))
with open(os.path.join(OUT, "momentum50_summary.json"), "w") as f:
    json.dump(out_json, f, indent=2, default=str)
excl.to_csv(os.path.join(OUT, "momentum50_exclusion_detail.csv"), index=False)
print("saved momentum50_summary.json + exclusion_detail.csv", flush=True)
print("\nEXCLUSION BY YEAR:\n", excl_yr.to_string(index=False), flush=True)
