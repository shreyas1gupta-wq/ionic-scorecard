"""Diagnostic (not a trial): collar leg coverage + per-year collar PnL for the CA-COLLAR run."""
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
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
monthly_exps = sorted(opt_month.unique())
W0, W1 = pd.Timestamp("2016-01-01"), pd.Timestamp("2026-06-30")
rows, missing = [], []
prev_exp = None
for exp in monthly_exps:
    exp = pd.Timestamp(exp)
    entry_day = prev_exp
    prev_exp = exp
    if entry_day is None or exp < W0 or entry_day > W1:
        continue
    e_days = fut_settle.index[fut_settle.index > entry_day]
    if not len(e_days):
        missing.append((str(exp.date()), "no entry day")); continue
    ed = e_days[0]
    spot = fut_settle.get(ed, np.nan)
    ch = opt[(opt.d == ed) & (opt.exp == exp)]
    if not len(ch):
        missing.append((str(exp.date()), "no chain")); continue
    def pick(tgt, typ):
        cc = ch[(ch.OPTION_TYP == typ) & (ch.SETTLE_PR > 0.05) & (ch.CONTRACTS > 0)]
        if not len(cc):
            return None
        k = cc.iloc[(cc.STRIKE_PR - tgt).abs().argsort()].iloc[0]
        return float(k.STRIKE_PR), float(k.SETTLE_PR)
    put = pick(0.95 * spot, "PE"); call = pick(1.04 * spot, "CE")
    if put is None or call is None:
        missing.append((str(exp.date()), "no legs")); continue
    s_exp = fut_settle.get(exp, np.nan)
    if np.isnan(s_exp):
        missing.append((str(exp.date()), "no expiry settle")); continue
    put_pay = max(put[0] - s_exp, 0.0) - put[1]
    call_pay = call[1] - max(s_exp - call[0], 0.0)
    rows.append(dict(exp=exp, spot=spot, pk=put[0], pprem=put[1], ck=call[0], cprem=call[1],
                     s_exp=s_exp, pnl=(put_pay + call_pay - 4.0) / spot,
                     put_moneyness=put[0] / spot, call_moneyness=call[0] / spot))
df = pd.DataFrame(rows)
print(f"months collared: {len(df)} | missing: {len(missing)}")
if missing:
    print("missing:", missing[:20])
print(f"strike accuracy: put moneyness {df.put_moneyness.mean():.3f} (tgt .95), call {df.call_moneyness.mean():.3f} (tgt 1.04)")
yr = df.groupby(df.exp.dt.year).pnl.sum()
print("collar PnL %/yr:", " | ".join(f"{y}: {v*100:+.1f}%" for y, v in yr.items()))
big = df.reindex(df.pnl.abs().sort_values(ascending=False).index[:8])
print(big[["exp", "spot", "pk", "ck", "s_exp", "pnl"]].to_string(index=False))
