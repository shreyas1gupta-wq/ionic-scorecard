import pandas as pd, numpy as np, os
ROOT=r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"

# HF panel (original bt11 source) columns
hf = pd.read_parquet(os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet"))
print("HF COLUMNS:", list(hf.columns))
print("HF shape:", hf.shape, "HF symbols:", hf['symbol'].nunique())

# PIT universe tickers vs union panel symbols overlap
raw = pd.read_excel(os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx"))
raw.columns = [c.strip() for c in raw.columns]
tick_col = [c for c in raw.columns if 'Ticker' in c or 'ticker' in c][0]
pit_syms = set(raw[tick_col].astype(str).str.strip().str.upper())
print("PIT distinct tickers:", len(pit_syms))

u = pd.read_parquet("close_panel_return.parquet")
u_syms = set(u['symbol'].astype(str).str.strip().str.upper())
print("Union symbols:", len(u_syms))
print("PIT tickers present in union (raw):", len(pit_syms & u_syms))
print("PIT tickers MISSING from union (raw):", len(pit_syms - u_syms))

# apply alias map old->new then check
al = pd.read_csv("symbol_aliases.csv")
alias = dict(zip(al['old_ticker'].str.upper(), al['new_ticker'].str.upper()))
# union already uses new tickers presumably; map PIT old->new
pit_mapped = set(alias.get(s, s) for s in pit_syms)
print("PIT tickers (alias-mapped) present in union:", len(pit_mapped & u_syms))
print("PIT tickers (alias-mapped) MISSING from union:", len(pit_mapped - u_syms))
miss = sorted(pit_mapped - u_syms)
print("sample missing:", miss[:30])

# source breakdown
print("\nUnion source counts:")
print(u['source'].value_counts())
print("spliced rows:", int(u['spliced'].sum()))
