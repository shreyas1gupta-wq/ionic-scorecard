"""CA-BOOK (frozen @ 8c45a08): CA marginal contribution to the stacked book, D-034 first application.
All inputs banked; collar lumps removed deterministically to recover pure CA daily returns.
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/CACB_PMS1_20260712"
SB = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711"

# ---- pure CA returns = banked combined curve minus deterministic collar lumps ----
eq = pd.read_csv(OUT / "ca_collar_equity.csv", index_col=0, parse_dates=True)["equity"]
combo = eq.pct_change()
combo.iloc[0] = eq.iloc[0] - 1.0

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
opt_month = opt.groupby([opt.exp.dt.year, opt.exp.dt.month]).exp.max()
collar = pd.Series(0.0, index=combo.index)
prev_exp = None
for exp in sorted(opt_month.unique()):
    exp = pd.Timestamp(exp)
    entry_day = prev_exp if prev_exp is not None and prev_exp >= combo.index[0] - pd.Timedelta(days=40) else None
    prev_exp = exp
    if entry_day is None or exp < combo.index[0] or entry_day > combo.index[-1]:
        continue
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
    def pick(tgt, typ):
        cc = ch[(ch.OPTION_TYP == typ) & (ch.SETTLE_PR > 0.05) & (ch.CONTRACTS > 0)]
        if not len(cc):
            return None
        k = cc.iloc[(cc.STRIKE_PR - tgt).abs().argsort()].iloc[0]
        return float(k.STRIKE_PR), float(k.SETTLE_PR)
    put = pick(0.95 * spot, "PE"); call = pick(1.04 * spot, "CE")
    if put is None or call is None:
        continue
    s_exp = fut_settle.get(exp, np.nan)
    if not np.isnan(s_exp):
        pnl_pts = (max(put[0] - s_exp, 0.0) - put[1]) + (call[1] - max(s_exp - call[0], 0.0)) - 4.0
        dloc = collar.index.searchsorted(exp)
        if dloc < len(collar):
            collar.iloc[dloc] += pnl_pts / spot
ca = combo - collar
ca.to_frame("ret").to_csv(OUT / "ca_daily_returns.csv")

# sanity: pure-CA curve must reproduce the banked CA-alone stats
def perf(r):
    e = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    sh = r.mean() / r.std(ddof=1) * np.sqrt(252)
    return e.iloc[-1] ** (1 / yrs) - 1, (e / e.cummax() - 1).min(), sh
cg, dd_, sh = perf(ca)
print(f"sanity pure CA: CAGR {cg*100:+.1f}% (banked +14.1%) maxDD {dd_*100:.1f}% (banked -50.1%)", flush=True)

# ---- incumbent books + sleeves ----
def book_ret(fn):
    e = pd.read_csv(SB / fn, index_col=0, parse_dates=True)["equity"]
    r = e.pct_change()
    r.iloc[0] = e.iloc[0] / 1e7 - 1.0
    return r
v2, v3 = book_ret("book_equity_v2.csv"), book_ret("book_equity_v3.csv")
slv = pd.read_csv(SB / "book_daily_pnl.csv", index_col=0, parse_dates=True)

common = ca.index.intersection(v2.index)
ca_c = ca.reindex(common).fillna(0.0)
lines = [f"common window: {common[0].date()} .. {common[-1].date()} ({len(common)} td)"]
corr_book = {}
for nm, b in [("v2", v2), ("v3", v3)]:
    corr_book[nm] = float(np.corrcoef(ca_c, b.reindex(common).fillna(0.0))[0, 1])
corr_slv = {c: float(pd.concat([ca_c, slv[c].reindex(common)], axis=1).corr().iloc[0, 1]) for c in ["midsmall", "breakout", "s1f", "b1b"]}
lines.append("CA corr: " + " | ".join(f"{k}={v:+.2f}" for k, v in {**corr_book, **corr_slv}.items()))

rows = []
for nm, b in [("v2", v2), ("v3", v3)]:
    b_c = b.reindex(common).fillna(0.0)
    icg, idd, ish = perf(b_c)
    rows.append(dict(cell=f"{nm}_incumbent", cagr=icg, dd=idd, sharpe=ish, verdict="-"))
    for w in (0.20, 0.33):
        blend = w * ca_c + (1 - w) * b_c
        cgb, ddb, shb = perf(blend)
        ok = (shb >= ish - 0.05) and (ddb >= idd - 0.02) and (cgb >= icg + 0.01)
        rows.append(dict(cell=f"{nm}_w{int(w*100)}", cagr=cgb, dd=ddb, sharpe=shb, verdict="PASS" if ok else "fail"))
df = pd.DataFrame(rows)
df[["cagr", "dd"]] = (df[["cagr", "dd"]] * 100).round(1)
df["sharpe"] = df.sharpe.round(2)
lines.append(df.to_string(index=False))
any_pass = (df.verdict == "PASS").any()
regime_park = max(corr_book.values()) > 0.35
verdict = "ADD-TO-BOOK" if (any_pass and not regime_park) else "REGIME-PARK"
lines.append(f"max book corr {max(corr_book.values()):+.2f} (bar 0.35) | VERDICT: {verdict}")
txt = "\n".join(lines)
print(txt, flush=True)
(OUT / "CA_BOOK_RESULTS.txt").write_text(txt, encoding="utf-8")
