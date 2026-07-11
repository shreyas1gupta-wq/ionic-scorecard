"""
LOSER FORENSICS — what marks the -10%..-30% trades BEFORE entry, that doesn't mark winners?
Champion ledger (SWING/NONE, Oct-2022, 679 trades). All features PIT (<= decision moment).
Includes decision-time entry-day open info (we buy AT that open, so it's usable).

Steps:
 1. Build forensic features per trade (fake-setup / manipulation signatures from OHLCV)
 2. Loser (ret<=-10) vs Winner (ret>=+10) vs Mid profile
 3. Grid-search single filters for asymmetry: %losers killed vs %winners killed
 4. Re-run champion portfolio with the best filter stack -> CAGR/DD impact
 5. Case table: worst 15 trades with their forensic fingerprint
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets"
SIG_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_3 (2).csv"

led = pd.read_csv(os.path.join(OUT, "champ_ledger_SWING_NONE.csv"),
                  parse_dates=["entry_date", "exit_date"])
panel = pd.read_parquet(os.path.join(OUT, "chartlink_prices_full5yr.parquet"))
panel["date"] = pd.to_datetime(panel["date"])
psym = {s: g.sort_values("date").reset_index(drop=True) for s, g in panel.groupby("symbol")}

sig = pd.read_csv(SIG_CSV)
sig["Date"] = pd.to_datetime(sig["Date"], format="%d-%m-%Y")
sig_dates = sig.groupby("Symbol")["Date"].apply(list).to_dict()

feat_pit = pd.read_csv(os.path.join(OUT, "signal_features_pit.csv"), parse_dates=["signal_date"])

# smallcap index context
idx = pd.read_parquet(os.path.join(BASE, "index_daily", "nse_official_all_indices.parquet"),
                      columns=["index_name", "date", "close"])
idx["date"] = pd.to_datetime(idx["date"])
sc = idx[idx["index_name"] == "NIFTY Smallcap 100"].sort_values("date").set_index("date")["close"]
sc21 = sc.pct_change(21)

print("Building forensic features for", len(led), "trades...")
rows = []
for _, t in led.iterrows():
    s = t["symbol"]; ed = t["entry_date"]
    g = psym[s]
    eix = g.index[g["date"] == ed]
    if len(eix) == 0: continue
    ei = eix[0]
    six = ei - 1                     # signal day = bar before entry
    if six < 61: continue
    srow = g.loc[six]
    sd = srow["date"]
    hist = g.iloc[six-60:six+1]      # 60 bars up to & incl signal day
    cl, hi, lo, op, vol = hist["close"], hist["high"], hist["low"], hist["open"], hist["volume"]

    f = {"symbol": s, "entry_date": ed, "signal_date": sd,
         "ret_pct": t["ret_pct"], "pnl": t["pnl"], "reason": t["reason"],
         "hold_days": t["hold_days"]}

    # --- decision-time entry-day info (we buy AT the open, so open is knowable) ---
    e_open = g.loc[ei, "open"]
    f["entry_gap_pct"] = (e_open/srow["close"]-1)*100

    # --- fake-setup signatures on/before signal day ---
    sc_, so_, sh_, sl_, sv_ = srow["close"], srow["open"], srow["high"], srow["low"], srow["volume"]
    rng = sh_ - sl_
    f["give_up"] = (sh_-sc_)/rng if rng > 0 else 0            # finished off highs?
    f["price_level"] = sc_
    atr = (hi-lo).iloc[-15:-1].mean()
    f["chg_vs_atr"] = ((sc_/g.loc[six-1, "close"]-1)*100) / (atr/sc_*100) if atr > 0 else np.nan
    f["sl_dist_pct"] = (t["entry_px"]-t["sl_px"])/t["entry_px"]*100

    # failed breakouts in last 60d: close made 20d-high then closed 3% lower within 5 bars
    c60 = cl.values
    fails = 0
    roll_hi = pd.Series(c60).rolling(20).max().values
    for k in range(20, len(c60)-5):
        if c60[k] >= roll_hi[k] * 0.999:                      # at 20d high
            if min(c60[k+1:k+6]) < c60[k]*0.97:
                fails += 1
    f["failed_bo_60d"] = fails

    # distribution days: down days on >1.5x avg vol in last 20
    v20 = vol.iloc[-21:-1]; c20 = cl.iloc[-21:]
    dn = (c20.diff().iloc[1:] < 0).values
    hv = (v20.values > v20.mean()*1.5)
    f["dist_days_20"] = int((dn & hv).sum())

    # erratic volume: cv of volume over 60d
    f["vol_cv_60"] = vol.std()/vol.mean() if vol.mean() > 0 else np.nan
    # gap frequency: |open/prev close -1| > 3% in last 60d
    gaps = (op.values[1:]/cl.values[:-1]-1)
    f["gap_freq_60"] = float((np.abs(gaps) > 0.03).mean())
    # up-day fraction last 20
    f["up_frac_20"] = float((cl.iloc[-20:].diff().dropna() > 0).mean())
    # closes near high frac (last 10 days): close in top 25% of daily range
    last10 = hist.iloc[-11:-1]
    cir = (last10["close"]-last10["low"])/(last10["high"]-last10["low"]).replace(0, np.nan)
    f["close_hi_frac_10"] = float((cir > 0.75).mean())
    # run-up before signal: 10d return
    f["ret_10d_pre"] = (g.loc[six-1, "close"]/g.loc[six-11, "close"]-1)*100
    # prior signal within 30d (chasing repeated signals)
    prior_sigs = [d for d in sig_dates.get(s, []) if 0 < (sd-d).days <= 30]
    f["resignal_30d"] = len(prior_sigs)
    # smallcap tape frothiness at signal
    scv = sc21[sc21.index <= sd]
    f["sc100_r21"] = scv.iloc[-1]*100 if len(scv) else np.nan
    rows.append(f)

df = pd.DataFrame(rows)
# join the earlier PIT features
fj = feat_pit[["symbol", "signal_date", "vol_ratio", "dist_52wh_pct", "ret_252d", "days_since_earn",
               "atr_pct", "rsi14", "turnover_cr", "mcap", "sector", "gap_pct", "chg_pct",
               "upper_wick_pct", "pos_52w", "nifty_above20"]]
df = df.merge(fj, on=["symbol", "signal_date"], how="left")
df["bucket"] = np.where(df["ret_pct"] <= -10, "LOSER", np.where(df["ret_pct"] >= 10, "WINNER", "MID"))
print(df["bucket"].value_counts().to_string())
df.to_csv(os.path.join(OUT, "loser_forensics.csv"), index=False)

# ---------------- 2. Profile ----------------
FEATS = ["entry_gap_pct", "give_up", "price_level", "chg_vs_atr", "sl_dist_pct", "failed_bo_60d",
         "dist_days_20", "vol_cv_60", "gap_freq_60", "up_frac_20", "close_hi_frac_10",
         "ret_10d_pre", "resignal_30d", "sc100_r21", "vol_ratio", "dist_52wh_pct", "ret_252d",
         "days_since_earn", "atr_pct", "rsi14", "turnover_cr", "gap_pct", "chg_pct",
         "upper_wick_pct", "pos_52w"]
print("\nLOSER vs WINNER medians (and MID):")
print(f"{'feature':<18} {'LOSER':>9} {'MID':>9} {'WINNER':>9}  note")
prof = df.groupby("bucket")[FEATS].median().T
for ft in FEATS:
    lz, md, wn = prof.loc[ft, "LOSER"], prof.loc[ft, "MID"], prof.loc[ft, "WINNER"]
    print(f"{ft:<18} {lz:>9.2f} {md:>9.2f} {wn:>9.2f}")

# mcap breakdown
print("\nBucket by mcap:")
print(pd.crosstab(df["mcap"], df["bucket"], normalize="index").round(3).to_string())

# ---------------- 3. Filter asymmetry search ----------------
print("\n" + "="*88)
print("FILTER SEARCH: kill-rate on LOSERS vs WINNERS (want high loser-kill, low winner-kill)")
print("="*88)
L = df[df["bucket"]=="LOSER"]; W = df[df["bucket"]=="WINNER"]
cands = []
def test(name, mask_fn):
    dm = mask_fn(df)
    lk = mask_fn(L).mean()*100; wk = mask_fn(W).mean()*100
    net = df.loc[mask_fn(df), "pnl"].sum()/1e5
    cands.append({"filter": name, "hits_pct": dm.mean()*100, "loser_kill": lk,
                  "winner_kill": wk, "asym": lk-wk, "pnl_removed_L": round(net,1)})

test("entry gap-down < -1%", lambda d: d["entry_gap_pct"] < -1)
test("entry gap-down < -2%", lambda d: d["entry_gap_pct"] < -2)
test("entry gap-up > +5% (chase)", lambda d: d["entry_gap_pct"] > 5)
test("give_up > 0.5 (weak close)", lambda d: d["give_up"] > 0.5)
test("failed_bo_60d >= 3", lambda d: d["failed_bo_60d"] >= 3)
test("dist_days_20 >= 3", lambda d: d["dist_days_20"] >= 3)
test("vol_cv_60 > 2 (erratic vol)", lambda d: d["vol_cv_60"] > 2)
test("gap_freq_60 > 15%", lambda d: d["gap_freq_60"] > 0.15)
test("price < Rs.50", lambda d: d["price_level"] < 50)
test("price < Rs.100", lambda d: d["price_level"] < 100)
test("sl_dist > 12% (wide stop)", lambda d: d["sl_dist_pct"] > 12)
test("chg_vs_atr > 4 (blowoff move)", lambda d: d["chg_vs_atr"] > 4)
test("ret_10d_pre > 15% (late entry)", lambda d: d["ret_10d_pre"] > 15)
test("resignal within 30d", lambda d: d["resignal_30d"] >= 1)
test("vol_ratio > 8x", lambda d: d["vol_ratio"] > 8)
test("far from 52wh (<-15%)", lambda d: d["dist_52wh_pct"] < -15)
test("stale earnings >120d", lambda d: d["days_since_earn"] > 120)
test("sc100 hot (r21 > 8%)", lambda d: d["sc100_r21"] > 8)
test("sc100 cold (r21 < -5%)", lambda d: d["sc100_r21"] < -5)
test("upper_wick > 3%", lambda d: d["upper_wick_pct"] > 3)
test("rsi > 85", lambda d: d["rsi14"] > 85)
test("smallcap + price<100", lambda d: (d["mcap"]=="Smallcap") & (d["price_level"]<100))

cdf = pd.DataFrame(cands).sort_values("asym", ascending=False)
print(cdf.to_string(index=False))
cdf.to_csv(os.path.join(OUT, "loser_filters.csv"), index=False)

# ---------------- 4. Worst-15 case table ----------------
print("\nWORST 15 TRADES — forensic fingerprint:")
worst = df.nsmallest(15, "ret_pct")
cols = ["symbol","signal_date","ret_pct","entry_gap_pct","give_up","failed_bo_60d","dist_days_20",
        "vol_ratio","dist_52wh_pct","days_since_earn","price_level","mcap","sector"]
print(worst[cols].to_string(index=False))
