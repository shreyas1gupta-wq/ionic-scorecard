import pandas as pd, numpy as np
p = pd.read_parquet("close_panel_return.parquet")
print("SHAPE:", p.shape)
print("COLUMNS:", list(p.columns))
print("DTYPES:")
print(p.dtypes)
print("HEAD:")
print(p.head(3).to_string())
print("NUNIQUE symbols:", p['symbol'].nunique() if 'symbol' in p.columns else 'NO symbol col')
if 'date' in p.columns:
    print("DATE min/max:", p['date'].min(), p['date'].max())
    print("date dtype:", p['date'].dtype)
# is it long or wide?
print("index name:", p.index.name)
