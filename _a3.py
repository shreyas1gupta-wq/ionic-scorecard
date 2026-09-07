import pandas as pd
df = pd.read_excel(r"C:/tmp/dummy_statement.xlsx", skiprows=3)
df.columns = ["ISIN","Asset Name","Asset Class","Category","Market Value"]
df = df.dropna(subset=["Asset Name"])
d = df[df["Asset Class"].notna()].copy()
d["Market Value"]=d["Market Value"].astype(float)
G = d["Market Value"].sum()
print("rows", len(d), "grand", repr(G))
totrow = df[df["Asset Name"].astype(str).str.strip().eq("TOTAL")]
print("stated TOTAL:", repr(totrow["Market Value"].iloc[0]))
for ac,g in d.groupby("Asset Class"):
    print(f"{ac:14s} n={len(g):3d} sum={g['Market Value'].sum():,.2f}  pct={100*g['Market Value'].sum()/G:.4f}")
print()
mf = d[d["Category"].astype(str).str.strip().eq("Mutual Funds")]
print("MF sleeve n=",len(mf), f"{mf['Market Value'].sum():,.2f}", round(100*mf['Market Value'].sum()/G,4))
mfd = mf[mf["Asset Class"].eq("Fixed Income")]
print("MF fixed income n=",len(mfd), f"{mfd['Market Value'].sum():,.2f}", round(100*mfd['Market Value'].sum()/G,4))
de = d[d["Category"].astype(str).str.strip().eq("Direct Equity")]
print("Direct Equity n=",len(de), f"{de['Market Value'].sum():,.2f}", round(100*de['Market Value'].sum()/G,4))
