import sys, io
import truststore; truststore.inject_into_ssl()
import requests
import pandas as pd

url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILWTICO"
s = requests.Session()
r = s.get(url, timeout=30)
r.raise_for_status()
df = pd.read_csv(io.StringIO(r.text))
df.columns = ['date','wti']
df['date'] = pd.to_datetime(df['date'])
df['wti'] = pd.to_numeric(df['wti'], errors='coerce')
df = df.dropna(subset=['wti'])
out = r"Shreyas_Ionic_AMC/05_DATA_OFFICE/data/wti_crude_fred_daily.parquet"
df.to_parquet(out, index=False)
print("rows", len(df), df['date'].min(), df['date'].max())
# D-009 spot checks: known WTI values
chk = df.set_index('date')['wti']
for d in ['2020-04-20','2008-07-03','2022-03-08']:
    d2 = pd.Timestamp(d)
    if d2 in chk.index:
        print(d, chk.loc[d2])
    else:
        print(d, 'NOT FOUND (holiday?), nearest:', chk.asof(d2))
