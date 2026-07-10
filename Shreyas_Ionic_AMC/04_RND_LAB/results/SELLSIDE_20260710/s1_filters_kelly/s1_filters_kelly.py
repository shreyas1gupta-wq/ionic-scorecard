"""S1 (0DTE straddle 09:20/30%SL) — EXPLORATORY filter study (PCR + spot filters), 0.25-Kelly
sizing, and equity graph. HONESTY: S1 passed UNCONDITIONALLY; every filter here is in-sample
exploration on the same 259 days (multiple testing!) — a filter only becomes real after a
pre-registered re-test / Gate-4 holdout. Filters get reported, NOT adopted. Ledger +~14 cells.
PCR = 3-bar-lagged minute OI (PE/CE sum, strikes within +/-3% of spot) at <=09:17."""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1_filters_kelly"
OUT.mkdir(parents=True, exist_ok=True)

s1 = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1s2_core/s1_trades.csv")
p = s1[s1.cell == "09:20/30"].copy()
p["date"] = pd.to_datetime(p.day).dt.date

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
sd = pd.Series(spot.index.date, index=spot.index)
daily_close = spot["close"].groupby(sd).last()
mapping, _ = chain.build_expiry_index()

# ---- spot features per traded day ----
feat = {}
dc = daily_close.sort_index()
dlist = list(dc.index)
for d in p.date:
    i = dlist.index(d) if d in dlist else None
    if not i:
        continue
    prior = dc.iloc[i - 1]
    day_bars = spot[sd == d]
    o = day_bars["open"].iloc[0]
    r5 = day_bars.between_time("09:15", "09:20")
    px920 = day_bars.between_time("09:15", "09:20")["close"].iloc[-1]
    feat[d] = dict(prior_ret=(dc.iloc[i - 1] / dc.iloc[i - 2] - 1) * 100 if i >= 2 else np.nan,
                   gap=(o / prior - 1) * 100,
                   r5rng=(r5.high.max() - r5.low.min()) / prior * 100,
                   trend920=(px920 / prior - 1) * 100,
                   wd=pd.Timestamp(d).day_name())

# ---- PCR (lagged OI) per day ----
for d in p.date:
    exp = d
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type",
                                                  "open_interest", "trading_day"]).to_pandas()
    except Exception:
        continue
    df = df[df["trading_day"] == str(d)]
    ts = pd.to_datetime(df["timestamp"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(ts=ts)
    early = df[df.ts.dt.time <= dt.time(9, 17)]
    if not len(early):
        continue
    snap = early.sort_values("ts").groupby(["strike", "option_type"])["open_interest"].last()
    spx = spot[sd == d].between_time("09:15", "09:17")["close"]
    if not len(spx):
        continue
    spx = spx.iloc[-1]
    ks = [k for (k, cp) in snap.index if abs(k - spx) / spx <= 0.03]
    pe = sum(v for (k, cp), v in snap.items() if cp == "PE" and k in ks)
    ce = sum(v for (k, cp), v in snap.items() if cp == "CE" and k in ks)
    if ce > 0 and d in feat:
        feat[d]["pcr"] = pe / ce

F = pd.DataFrame(feat).T
m = p.set_index("date").join(F)
m.to_csv(OUT / "s1_primary_with_features.csv")

def bucket_report(col, q=3):
    g = m.dropna(subset=[col])
    if g[col].dtype == object:
        groups = [(v, gg) for v, gg in g.groupby(col)]
    else:
        try:
            g = g.assign(_b=pd.qcut(g[col], q, labels=[f"low", "mid", "high"][:q], duplicates="drop"))
        except Exception:
            return f"{col}: bucketing failed"
        groups = [(v, gg) for v, gg in g.groupby("_b", observed=True)]
    out = []
    for v, gg in groups:
        t = gg.net.mean() / (gg.net.std(ddof=1) / np.sqrt(len(gg))) if len(gg) > 2 else np.nan
        out.append(f"  {col}={v}: n={len(gg)} net={gg.net.mean():+.2f} t={t:.2f}")
    return "\n".join(out)

lines = ["# S1 filter study (EXPLORATORY — in-sample, multiple testing; adopt nothing without re-test)"]
for col in ["pcr", "prior_ret", "gap", "r5rng", "trend920", "wd"]:
    if col in m.columns:
        lines.append(bucket_report(col))

# ---- Kelly ----
MARGIN, LOT = 120000.0, 75
r = m.net * LOT / MARGIN
f_full = r.mean() / r.var(ddof=1)
f_q = 0.25 * f_full
lines.append(f"\n# Kelly (returns on ~1.2L margin/lot): mean/trade={r.mean()*100:+.3f}% sd={r.std()*100:.2f}%"
             f"\nfull Kelly f*={f_full:.2f}x margin-fraction | 0.25-Kelly={f_q:.2f}x"
             f"\nInterpretation: deploy ~{f_q*100:.0f}% of capital as margin -> on Rs 10L: "
             f"~{f_q*1000000/MARGIN:.1f} lots (round DOWN).")

# equity curves on Rs 10L
cap0 = 1_000_000
eq_fixed = cap0 + (m.net * LOT).cumsum()          # 1 lot fixed
eq_k, cap = [], cap0
for pnl in m.net:
    lots = max(int(cap * f_q / MARGIN), 0)
    cap += pnl * LOT * lots
    eq_k.append(cap)
eq_k = pd.Series(eq_k, index=m.index)
for name, s in [("fixed 1 lot", eq_fixed), ("0.25-Kelly", eq_k)]:
    ddpct = ((s - s.cummax()) / s.cummax()).min() * 100
    lines.append(f"{name}: final Rs {s.iloc[-1]:,.0f} on Rs 10L | maxDD {ddpct:.1f}% | "
                 f"CAGR~{((s.iloc[-1]/cap0)**(1/4.9)-1)*100:.1f}%")

txt = "\n\n".join(lines)
print(txt)
(OUT / "SUMMARY.md").write_text(txt + "\n", encoding="utf-8")

# ---- graph (validated palette) ----
INK, BLUE, AQUA, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#1baf7a", "#e1e0d9", "#898781", "#fcfcfb"
x = pd.to_datetime(pd.Series(m.index.astype(str)))
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), dpi=150)
fig.patch.set_facecolor(SURF)
ax = axes[0]; ax.set_facecolor(SURF)
ax.plot(x, eq_fixed / 1e5, color=BLUE, lw=2, label="Fixed 1 lot")
ax.plot(x, eq_k / 1e5, color=AQUA, lw=2, label="0.25-Kelly (compounded)")
ax.annotate(f"{eq_fixed.iloc[-1]/1e5:.1f}L", (x.iloc[-1], eq_fixed.iloc[-1] / 1e5), xytext=(5, 0),
            textcoords="offset points", fontsize=8, color=INK)
ax.annotate(f"{eq_k.iloc[-1]/1e5:.1f}L", (x.iloc[-1], eq_k.iloc[-1] / 1e5), xytext=(5, 0),
            textcoords="offset points", fontsize=8, color=INK)
ax.set_title("S1 equity on Rs 10L (Rs lakh) — 259 expiry days 2021-26, net of base costs",
             fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7); ax.legend(fontsize=8, frameon=False)
ax.tick_params(colors=MUTED, labelsize=8)
for sp in ax.spines.values(): sp.set_visible(False)
ax = axes[1]; ax.set_facecolor(SURF)
dd = (eq_k - eq_k.cummax()) / eq_k.cummax() * 100
ax.fill_between(x, dd, 0, color=BLUE, alpha=0.35, lw=0)
ax.plot(x, dd, color=BLUE, lw=1.5)
ax.set_title("0.25-Kelly drawdown (%)", fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7); ax.tick_params(colors=MUTED, labelsize=8)
for sp in ax.spines.values(): sp.set_visible(False)
plt.tight_layout()
plt.savefig(OUT / "S1_EQUITY_20260710.png", facecolor=SURF, bbox_inches="tight")
print("saved ->", OUT)
