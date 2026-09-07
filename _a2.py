import pandas as pd
df = pd.read_excel(r"C:/tmp/dummy_statement.xlsx")
print(df.columns.tolist())
print(df.shape)
print(df.head(3).to_string())
