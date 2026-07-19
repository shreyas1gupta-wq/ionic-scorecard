"""Phase-0: (1) pull MARUTI to replace the delisted-ticker TATAMOTORS,
(2) run D-009 schema-sanity checks on all pilot price parquets."""
import os, time, glob
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import truststore; truststore.inject_into_ssl()
import pandas as pd, numpy as np, yfinance as yf

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
OUT = os.path.join(BASE, "data", "prices")

# (1) replacement pull
fp = os.path.join(OUT, "MARUTI.parquet")
if not os.path.exists(fp):
    df = yf.download("MARUTI.NS", period="2y", interval="1d", auto_adjust=False, progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.to_parquet(fp); print("MARUTI pulled:", len(df), "rows")

# (2) D-009 schema-sanity across all pilot parquets
print("\nD-009 SCHEMA-SANITY CHECKS")
print(f"{'TICKER':<11} {'ROWS':<5} {'OHLC_ok':<8} {'NaN':<4} {'neg':<4} {'dup_dt':<6} {'maxgap_d':<8} {'monoinc':<7}")
for f in sorted(glob.glob(os.path.join(OUT, "*.parquet"))):
    tk = os.path.basename(f).replace(".parquet","")
    d = pd.read_parquet(f)
    ohlc_ok = bool(((d['High'] >= d['Low']) & (d['Close'] <= d['High']+1e-6) & (d['Close'] >= d['Low']-1e-6) &
                    (d['Open'] <= d['High']+1e-6) & (d['Open'] >= d['Low']-1e-6)).all())
    nan = int(d[['Open','High','Low','Close']].isna().sum().sum())
    neg = int((d[['Open','High','Low','Close']] <= 0).sum().sum())
    dup = int(d.index.duplicated().sum())
    gaps = d.index.to_series().diff().dt.days.dropna()
    maxgap = int(gaps.max()) if len(gaps) else 0
    monoinc = bool(d.index.is_monotonic_increasing)
    print(f"{tk:<11} {len(d):<5} {str(ohlc_ok):<8} {nan:<4} {neg:<4} {dup:<6} {maxgap:<8} {str(monoinc):<7}")
