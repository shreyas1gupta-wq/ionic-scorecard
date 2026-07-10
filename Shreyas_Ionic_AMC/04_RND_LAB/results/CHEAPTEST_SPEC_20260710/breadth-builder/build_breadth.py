"""
BREADTH-BUILDER (CHEAPTEST_SPEC_20260710) — daily NIFTY500 breadth series 2020-2025.
Inputs (all existing, catalog-verified):
  - datasets/nse_bhavcopy_daily/close_all.parquet  (official NSE closes, 2013->2026-07)
  - NIFTY500_TICKER_2005_2025_Final.xlsx           (PIT membership snapshots, landmine #6)
  - datasets/index_daily/nse_official_all_indices.parquet (Nifty 50 OHLC, for conditioning check)
Outputs: breadth_daily.parquet, conditioning_check.csv, validation printout.
BUILD task: no kill threshold. Conditioning check is INFORMATIONAL only.
Lookahead: breadth on day D uses closes up to D only; conditioning uses breadth(D-1) -> NIFTY open->close(D).
"""
import pandas as pd, numpy as np, sys

BASE = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
OUT = BASE + "/Shreyas_Ionic_AMC/04_RND_LAB/results/CHEAPTEST_SPEC_20260710/breadth-builder"
sys.path.insert(0, BASE + "/Shreyas_Ionic_AMC/04_RND_LAB/lib")

# ---------- 1. membership snapshots (PIT) ----------
mem = pd.read_excel(BASE + "/NIFTY500_TICKER_2005_2025_Final.xlsx")
mem.columns = ["snap", "ticker"]
mem["snap_date"] = pd.to_datetime(mem["snap"], format="%b%Y")  # month start of snapshot
snaps = sorted(mem["snap_date"].unique())
print(f"snapshots: {len(snaps)}, first {snaps[0].date()}, last {snaps[-1].date()}")
snap_map = {d: set(mem.loc[mem.snap_date == d, "ticker"].astype(str).str.strip()) for d in snaps}

# ---------- 2. closes wide ----------
px = pd.read_parquet(BASE + "/datasets/nse_bhavcopy_daily/close_all.parquet")
px = px[px["series"].isin(["EQ", "BE"])]
px = px[(px["date"] >= "2019-10-01") & (px["date"] <= "2025-12-31")]  # warmup tail for 20DMA
wide = px.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").sort_index()
print("wide:", wide.shape)

# symbol match rate for 2020+ snapshots
tick_2020p = set().union(*[snap_map[d] for d in snaps if d >= pd.Timestamp("2020-01-01")])
matched = tick_2020p & set(wide.columns)
print(f"union tickers 2020+ snapshots: {len(tick_2020p)}, matched in bhavcopy: {len(matched)} ({len(matched)/len(tick_2020p):.1%})")

prev = wide.shift(1)
adv = (wide > prev) & prev.notna() & wide.notna()
dec = (wide < prev) & prev.notna() & wide.notna()
both = prev.notna() & wide.notna()
dma20 = wide.rolling(20, min_periods=20).mean()
above = (wide > dma20) & dma20.notna()
has_dma = dma20.notna() & wide.notna()

# ---------- 3. per-day breadth over PIT membership ----------
dates = wide.index[wide.index >= "2020-01-01"]
snap_arr = np.array(snaps)
rows = []
for d in dates:
    # latest snapshot <= d (PIT; snapshot labeled by month applies from that month)
    k = snap_arr[snap_arr <= d]
    members = snap_map[k[-1]] if len(k) else set()
    cols = [c for c in members if c in wide.columns]
    if not cols:
        continue
    a = adv.loc[d, cols].sum(); de = dec.loc[d, cols].sum(); n_ad = both.loc[d, cols].sum()
    ab = above.loc[d, cols].sum(); n_dma = has_dma.loc[d, cols].sum()
    if n_ad < 100:  # not a proper trading day / holiday artifact
        continue
    rows.append(dict(date=d, n_members=len(members), n_matched=len(cols), n_priced=int(n_ad),
                     adv_pct=a / n_ad * 100, dec_pct=de / n_ad * 100,
                     ad_net_pct=(a - de) / n_ad * 100,
                     pct_above_20dma=ab / n_dma * 100 if n_dma else np.nan,
                     n_dma=int(n_dma)))
br = pd.DataFrame(rows).set_index("date")
br["ad_line"] = (br["ad_net_pct"] / 100 * br["n_priced"]).cumsum()
br.to_parquet(OUT + "/breadth_daily.parquet")
print("\nbreadth_daily:", br.shape, br.index.min().date(), "->", br.index.max().date())
print(br[["n_matched", "n_priced", "adv_pct", "pct_above_20dma"]].describe().round(2))

# ---------- 4. validation vs known dates ----------
checks = {"2020-03-23": "COVID low", "2020-03-24": "COVID rebound d1", "2021-10-18": "2021 top zone",
          "2022-06-17": "2022 hike low", "2024-06-04": "election shock", "2024-06-05": "election rebound",
          "2025-02-28": "Feb-2025 selloff"}
print("\nvalidation:")
for dt, label in checks.items():
    if pd.Timestamp(dt) in br.index:
        r = br.loc[pd.Timestamp(dt)]
        print(f"  {dt} {label:20s} adv%={r.adv_pct:5.1f} %>20DMA={r.pct_above_20dma:5.1f} n={int(r.n_priced)}")
    else:
        print(f"  {dt} {label:20s} NOT A TRADING DAY in series")

# ---------- 5. informational conditioning check ----------
idx = pd.read_parquet(BASE + "/datasets/index_daily/nse_official_all_indices.parquet")
idx["date"] = pd.to_datetime(idx["date"]).astype("datetime64[ns]")
n50 = idx[idx["index_name"] == "Nifty 50"].set_index("date").sort_index()[["open", "close"]]
n50 = n50[(n50.index >= "2020-01-01") & (n50.index <= "2025-12-31")]
oc = (n50["close"] - n50["open"])  # intraday open->close move in NIFTY points (T1-style proxy)
ocp = (n50["close"] / n50["open"] - 1) * 100

brj = br[["adv_pct", "pct_above_20dma"]].shift(1)
brj.index = brj.index.astype("datetime64[ns]")
df = pd.DataFrame({"oc_pts": oc, "oc_pct": ocp}).join(brj).dropna()
print("conditioning join n days:", len(df))
assert len(df) > 500, "join failed - abort rather than report empty stats"
# lookahead-safe: breadth from D-1 close conditions D's open->close. One obs per day => plain t is day-clustered.
res = []
for sig in ["adv_pct", "pct_above_20dma"]:
    df["q"] = pd.qcut(df[sig], 5, labels=False, duplicates="drop")
    for q, g in df.groupby("q"):
        t = g["oc_pts"].mean() / (g["oc_pts"].std() / np.sqrt(len(g)))
        res.append(dict(signal=sig, quintile=int(q) + 1, n=len(g),
                        mean_oc_pts=g["oc_pts"].mean(), mean_oc_pct=g["oc_pct"].mean(), t=t))
    lo, hi = df[df.q == df.q.min()]["oc_pts"], df[df.q == df.q.max()]["oc_pts"]
    spread = hi.mean() - lo.mean()
    se = np.sqrt(hi.var() / len(hi) + lo.var() / len(lo))
    res.append(dict(signal=sig, quintile="Q5-Q1", n=len(lo) + len(hi), mean_oc_pts=spread,
                    mean_oc_pct=np.nan, t=spread / se))
cond = pd.DataFrame(res)
cond.to_csv(OUT + "/conditioning_check.csv", index=False)
print("\nconditioning (prior-day breadth -> next-day NIFTY open->close, pts):")
print(cond.round(2).to_string(index=False))

# per-era table (per spec convention)
print("\nper-era means of breadth series:")
for era, g in br.groupby(br.index.year):
    print(f"  {era}: n={len(g):3d} adv%={g.adv_pct.mean():5.1f} %>20DMA={g.pct_above_20dma.mean():5.1f}")
