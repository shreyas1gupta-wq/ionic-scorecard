import pandas as pd
BASE = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"

df = pd.read_parquet(BASE + "/datasets/nse_bhavcopy_daily/close_all.parquet")
print("close_all:", df.shape)
print(df.dtypes)
print(df.head(3))
print("date range:", df.iloc[:,0].min() if df.index.name is None else None)
print("index:", df.index[:3], df.index.name)

xl = pd.ExcelFile(BASE + "/NIFTY500_TICKER_2005_2025_Final.xlsx")
print("sheets:", xl.sheet_names[:50], "n=", len(xl.sheet_names))
s = xl.parse(xl.sheet_names[0])
print(s.shape); print(s.head(5)); print(s.columns.tolist()[:10])

idx = pd.read_parquet(BASE + "/datasets/index_daily/nse_official_all_indices.parquet")
print("indices:", idx.shape, idx.columns.tolist())
print(idx.head(2))
names = idx[idx.columns[0]].unique() if idx.columns[0].lower() in ("index","index_name","symbol") else None
print([n for n in idx['index_name'].unique() if 'NIFTY 50' in str(n).upper()][:10] if 'index_name' in idx.columns else idx.columns)
