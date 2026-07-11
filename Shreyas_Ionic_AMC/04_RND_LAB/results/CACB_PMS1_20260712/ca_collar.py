"""CA-COLLAR (frozen @ 83b78c8): CA book + monthly NIFTY 95/104 collar at 1x notional.
Collar legs from fo_idx monthly settles (landmine #9: exits at intrinsic from near-fut settle).
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(157)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/CACB_PMS1_20260712"
CS = 0.0025
W0, W1 = pd.Timestamp("2016-01-01"), pd.Timestamp("2026-06-30")

# ---------- CA daily returns (verbatim reconstruction, nan-aware) ----------
d = pd.read_parquet(ROOT / "swing_momentum/data/hf_stock_minute/day/train-00000.parquet")
ts = pd.to_datetime(d.timestamp)
d["date"] = ts.dt.tz_convert("Asia/Kolkata").dt.date
uni = pd.read_excel(ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx")
uni["snap"] = pd.to_datetime(uni["Month-Year"], format="%b%Y").dt.date
snaps = {dd: set(g["Ticker"].astype(str).str.strip()) for dd, g in uni.groupby("snap")}
snap_dates = sorted(snaps)
ever = set().union(*snaps.values())
d = d[d.symbol.isin(ever)]
C = d.pivot_table(index="date", columns="symbol", values="close"); C.index = pd.to_datetime(C.index); C = C.sort_index()
V = d.pivot_table(index="date", columns="symbol", values="volume"); V.index = C.index
RET = C.pct_change()
memb = pd.DataFrame(False, index=C.index, columns=C.columns)
for i, sd in enumerate(snap_dates):
    end = snap_dates[i + 1] if i + 1 < len(snap_dates) else dt.date(2027, 1, 1)
    memb.loc[(C.index.date >= sd) & (C.index.date < end), [c for c in C.columns if c in snaps[sd]]] = True
ma50 = C.rolling(50).mean()
def rsi_f(cf, n):
    dd_ = cf.diff()
    up = dd_.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-dd_.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)
rsi14 = rsi_f(C, 14)
mom3 = C / C.shift(63) - 1
upvol = (V.where(RET > 0, 0)).rolling(126).sum() / V.rolling(126).sum()
vwret = (RET * V).rolling(126).sum() / V.rolling(126).sum()
ev = pd.read_parquet(ROOT / "datasets/earnings_pit/unified_quarterly_pit.parquet")
ev.columns = [c.lower() for c in ev.columns]
ev["available_date"] = pd.to_datetime(ev["available_date"])
ev = ev.dropna(subset=["available_date"]).sort_values(["symbol", "quarter_end"])
ev["ttm_np"] = ev.groupby("symbol")["net_profit"].rolling(4).sum().values
ev["ttm_sales"] = ev.groupby("symbol")["sales"].rolling(4).sum().values
ev["ttm_np_ly"] = ev.groupby("symbol")["ttm_np"].shift(4)
ev["ttm_sales_ly"] = ev.groupby("symbol")["ttm_sales"].shift(4)
def step(frame, symcol, val):
    p = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for sym, g in frame.dropna(subset=[val]).groupby(symcol):
        s = str(sym).strip()
        if s not in C.columns:
            continue
        ser = pd.Series(g[val].values, index=g["available_date"]).sort_index()
        p[s] = ser[~ser.index.duplicated(keep="last")].reindex(C.index, method="ffill")
    return p
NPG = (step(ev, "symbol", "ttm_np") / step(ev, "symbol", "ttm_np_ly") - 1) * 100
SG = (step(ev, "symbol", "ttm_sales") / step(ev, "symbol", "ttm_sales_ly") - 1) * 100
rat = pd.read_parquet(ROOT / "datasets/earnings_pit/ratios_pit.parquet")
rat["available_date"] = pd.to_datetime(rat["available_date"])
ROCE = step(rat.rename(columns={"ROCE %": "roce"}), "nse_symbol", "roce")
ROE = step(rat.rename(columns={"ROE %": "roe"}), "nse_symbol", "roe")
def wz(row, cap=3.0):
    m, s = np.nanmean(row), np.nanstd(row)
    if not np.isfinite(s) or s == 0:
        return row * 0
    return np.clip((row - m) / s, -cap, cap)
dates = C.index[(C.index >= W0) & (C.index <= W1)]
month_start = set(dd for i, dd in enumerate(dates) if i == 0 or dates[i - 1].month != dd.month)
hold, daily, turn = {}, [], 0
for i, dd in enumerate(dates[:-1]):
    gi = C.index.get_loc(dd)
    if dd in month_start:
        m100 = mom3.iloc[gi].where(memb.iloc[gi]).dropna().sort_values(ascending=False).index[:100]
        qa = wz(ROCE.iloc[gi][m100].values); qb = wz(ROE.iloc[gi][m100].values)
        with np.errstate(all="ignore"):
            q = pd.Series(np.nanmean(np.vstack([qa, qb]), axis=0), index=m100)
        q50 = q.dropna().sort_values(ascending=False).index[:50]
        if len(q50) >= 10:
            gg = pd.Series(wz(NPG.iloc[gi][q50].values) + wz(SG.iloc[gi][q50].values), index=q50)
            pva = pd.Series(wz(vwret.iloc[gi][q50].values) + wz(upvol.iloc[gi][q50].values), index=q50)
            pick_g = list(gg.dropna().sort_values(ascending=False).index[:10])
            pick_p = [s for s in pva.dropna().sort_values(ascending=False).index if s not in pick_g][:10]
            target = pick_g + pick_p
            for s in list(hold):
                j = C.columns.get_loc(s)
                px = C.iat[gi, j]
                appreciated = np.isfinite(px) and px > hold[s]
                ob = (rsi14.iat[gi, j] >= 78) or (px >= 1.25 * ma50.iat[gi, j]) or \
                     (gi >= 10 and px >= 1.35 * C.iat[gi - 10, j])
                if (s not in target and not appreciated) or ob:
                    del hold[s]; turn += 1
            for s in target:
                if s not in hold and len(hold) < 20:
                    e_ = C.iat[gi, C.columns.get_loc(s)]
                    if np.isfinite(e_):
                        hold[s] = e_; turn += 1
    r = 0.0
    if hold and gi + 1 < len(C.index):
        vals = [RET.iat[gi + 1, C.columns.get_loc(s)] for s in hold]
        vals = [v for v in vals if np.isfinite(v)]
        r = np.mean(vals) * len(hold) / 20 if vals else 0.0
    daily.append(r)
ca = pd.Series(daily, index=dates[:len(daily)])
ca = ca - (turn / len(daily)) * 2 * CS / 20
print("CA reconstructed", flush=True)

# ---------- collar legs from fo_idx monthly ----------
D = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist"
fo = pd.concat([pd.read_parquet(p) for p in sorted(D.glob("fo_idx_*.parquet"))], ignore_index=True)
fo = fo[fo.SYMBOL == "NIFTY"]
fo["d"] = pd.to_datetime(fo.TIMESTAMP, format="%d-%b-%Y", errors="coerce")
fo["exp"] = pd.to_datetime(fo.EXPIRY_DT, format="%d-%b-%Y", errors="coerce")
fo = fo.dropna(subset=["d", "exp"])
for c in ["STRIKE_PR", "SETTLE_PR", "CONTRACTS"]:
    fo[c] = pd.to_numeric(fo[c], errors="coerce")
fut = fo[fo.INSTRUMENT == "FUTIDX"].sort_values(["d", "exp"]).drop_duplicates("d")
fut_settle = fut.set_index("d")["SETTLE_PR"]
opt = fo[fo.INSTRUMENT == "OPTIDX"]
# monthly expiries = last expiry in each month with wide strike coverage
opt_month = opt.groupby([opt.exp.dt.year, opt.exp.dt.month]).exp.max()
monthly_exps = sorted(opt_month.unique())
collar = pd.Series(0.0, index=ca.index)
prev_exp = None
for exp in monthly_exps:
    exp = pd.Timestamp(exp)
    entry_day = prev_exp if prev_exp is not None and prev_exp >= ca.index[0] - pd.Timedelta(days=40) else None
    prev_exp2 = prev_exp
    prev_exp = exp
    if entry_day is None or exp < ca.index[0] or entry_day > ca.index[-1]:
        continue
    e_i = fut_settle.index.searchsorted(entry_day, side="right")
    e_days = fut_settle.index[fut_settle.index > entry_day]
    if not len(e_days):
        continue
    ed = e_days[0]
    spot = fut_settle.get(ed, np.nan)
    if not np.isfinite(spot):
        continue
    ch = opt[(opt.d == ed) & (opt.exp == exp)]
    if not len(ch):
        continue
    def pick(strike_tgt, typ):
        cc = ch[(ch.OPTION_TYP == typ) & (ch.SETTLE_PR > 0.05) & (ch.CONTRACTS > 0)]
        if not len(cc):
            return None
        k = cc.iloc[(cc.STRIKE_PR - strike_tgt).abs().argsort()].iloc[0]
        return float(k.STRIKE_PR), float(k.SETTLE_PR)
    put = pick(0.95 * spot, "PE"); call = pick(1.04 * spot, "CE")
    if put is None or call is None:
        continue
    s_exp = fut_settle.get(exp, np.nan)
    if not np.isnan(s_exp):
        put_pay = max(put[0] - s_exp, 0.0) - put[1]
        call_pay = call[1] - max(s_exp - call[0], 0.0)
        pnl_pts = put_pay + call_pay - 4.0  # costs 1pt/leg entry x2 + settle buffer
        # distribute at expiry date as book % (notional match: pnl_pts / spot)
        dloc = collar.index.searchsorted(exp)
        if dloc < len(collar):
            collar.iloc[dloc] += pnl_pts / spot
print("collar legs built", flush=True)

def perf(r):
    eqc = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return (eqc.iloc[-1] ** (1 / yrs) - 1, (eqc / eqc.cummax() - 1).min(), eqc)

cg0, dd0, _ = perf(ca)
combo = ca + collar
cg1, dd1, eqc = perf(combo)
drag = cg0 - cg1
bars = {"DD<=25": dd1 >= -0.25, "CAGR>=12": cg1 >= 0.12, "drag<=6%": drag <= 0.06}
stretch = (dd1 >= -0.20) and (cg1 >= 0.15)
verdict = ("ARMORED+STRETCH" if stretch else "ARMORED") if all(bars.values()) else ("KILL" if cg1 < 0.08 else "NOT ARMORED")
yr = combo.groupby(combo.index.year).apply(lambda x: (1 + x).prod() - 1)
lines = [f"CA alone: CAGR {cg0*100:+.1f}% maxDD {dd0*100:.1f}%",
         f"CA+COLLAR: CAGR {cg1*100:+.1f}% maxDD {dd1*100:.1f}% | collar drag {drag*100:+.1f}%/yr",
         " | ".join(f"{y}: {v*100:+.1f}%" for y, v in yr.items()),
         "bars: " + ", ".join(f"{k}={'P' if v else 'F'}" for k, v in bars.items()),
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "CA_COLLAR_RESULTS.txt").write_text(txt, encoding="utf-8")
eqc.to_frame("equity").to_csv(OUT / "ca_collar_equity.csv")
