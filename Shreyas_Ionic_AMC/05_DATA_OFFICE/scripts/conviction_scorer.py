"""Add a CONVICTION score (/100) + sector + earnings/event risk flags to the execution sheet.
Conviction = strategy base edge + per-trade signal strength + liquidity - risk deductions.
News adjustment is a separate column (filled from the news-research agent). Writes a scored CSV.
"""
import datetime as dt, re
from pathlib import Path
import numpy as np, pandas as pd

PROJ = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
EXD = PROJ / "FINAL_STRATEGY_FORWARD_CHECK" / "08_Execution"
FWD = pd.read_csv(PROJ / "datasets/nse_earnings_dates/forthcoming_results.csv")
FWD["d"] = pd.to_datetime(FWD["date"], format="%d-%b-%Y", errors="coerce")
earn_dates = {}
for _, r in FWD.dropna(subset=["d"]).iterrows():
    earn_dates.setdefault(r["symbol"], []).append(r["d"].date())
FRONT_EXP = dt.date(2026, 7, 28)

SECTOR = {
    # IT
    "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "TECHM": "IT", "COFORGE": "IT", "WIPRO": "IT",
    "LTIM": "IT", "PERSISTENT": "IT", "MPHASIS": "IT", "KPITTECH": "IT", "TATAELXSI": "IT", "OFSS": "IT",
    # Private banks
    "HDFCBANK": "Private Bank", "ICICIBANK": "Private Bank", "AXISBANK": "Private Bank",
    "KOTAKBANK": "Private Bank", "INDUSINDBK": "Private Bank", "FEDERALBNK": "Private Bank",
    "IDFCFIRSTB": "Private Bank", "RBLBANK": "Private Bank", "YESBANK": "Private Bank", "BANDHANBNK": "Private Bank",
    # PSU banks
    "SBIN": "PSU Bank", "BANKBARODA": "PSU Bank", "PNB": "PSU Bank", "CANBK": "PSU Bank",
    "BANKINDIA": "PSU Bank", "UNIONBANK": "PSU Bank", "INDIANB": "PSU Bank",
    # FMCG
    "NESTLEIND": "FMCG", "COLPAL": "FMCG", "HINDUNILVR": "FMCG", "DABUR": "FMCG", "MARICO": "FMCG",
    "ITC": "FMCG", "BRITANNIA": "FMCG", "TATACONSUM": "FMCG", "GODREJCP": "FMCG", "PATANJALI": "FMCG",
    # Pharma
    "CIPLA": "Pharma", "DRREDDY": "Pharma", "SUNPHARMA": "Pharma", "LUPIN": "Pharma",
    "TORNTPHARM": "Pharma", "ZYDUSLIFE": "Pharma", "GLENMARK": "Pharma", "LAURUSLABS": "Pharma", "MANKIND": "Pharma",
    # Auto
    "BAJAJ-AUTO": "Auto", "M&M": "Auto", "HEROMOTOCO": "Auto", "MARUTI": "Auto", "TVSMOTOR": "Auto",
    "EICHERMOT": "Auto", "ASHOKLEY": "Auto", "BHARATFORG": "Auto Ancillary", "MOTHERSON": "Auto Ancillary",
    "BOSCHLTD": "Auto Ancillary", "SONACOMS": "Auto Ancillary", "UNOMINDA": "Auto Ancillary", "TIINDIA": "Auto Ancillary",
    # Adani
    "ADANIGREEN": "Adani-group", "ADANIENSOL": "Adani-group", "ADANIPOWER": "Adani-group",
    "ADANIPORTS": "Adani-group", "ADANIENT": "Adani-group",
    # Defence / capital goods
    "BDL": "Defence", "BEL": "Defence", "HAL": "Defence", "MAZDOCK": "Defence", "COCHINSHIP": "Defence",
    "ABB": "Capital Goods", "SIEMENS": "Capital Goods", "CGPOWER": "Capital Goods", "POWERINDIA": "Capital Goods",
    # Metals
    "JSWSTEEL": "Metals", "TATASTEEL": "Metals", "HINDALCO": "Metals", "VEDL": "Metals", "JINDALSTEL": "Metals",
    "NATIONALUM": "Metals", "SAIL": "Metals", "NMDC": "Metals", "HINDZINC": "Metals",
    # Cement
    "ULTRACEMCO": "Cement", "SHREECEM": "Cement", "DALBHARAT": "Cement", "AMBUJACEM": "Cement",
    # Insurance / capital markets
    "HDFCLIFE": "Insurance", "ICICIPRULI": "Insurance", "ICICIGI": "Insurance", "SBILIFE": "Insurance",
    "ANGELONE": "Capital Markets", "BSE": "Capital Markets", "CDSL": "Capital Markets", "CAMS": "Capital Markets",
    "MCX": "Capital Markets", "NUVAMA": "Capital Markets", "KFINTECH": "Capital Markets", "360ONE": "Capital Markets",
    # Others
    "APOLLOHOSP": "Hospital", "MAXHEALTH": "Hospital", "FORTIS": "Hospital",
    "COALINDIA": "PSU Energy", "NTPC": "Power", "POWERGRID": "Power", "TATAPOWER": "Power",
    "RELIANCE": "Energy/Conglomerate", "BLUESTARCO": "Consumer Durables", "CUMMINSIND": "Capital Goods",
}


def sector(s):
    return SECTOR.get(s, "Other")


def has_earnings_before_expiry(sym, entry, expiry):
    for d in earn_dates.get(sym, []):
        if entry <= d <= expiry:
            return d
    return None


def score_trade(strat, sym, signal, entry, expiry):
    """Return (base_conviction 0-100, risk_flags list)."""
    flags = []
    ff = ivrv = credit = None
    m = re.search(r"FF=([\d.]+)", str(signal));  ff = float(m.group(1)) if m else None
    m = re.search(r"([\d.]+)%spot", str(signal)); credit = float(m.group(1)) if m else None

    if strat == "FF_Calendar":
        base = 60
        if ff is not None:
            if ff < 0.5: base += 2
            elif ff < 0.75: base += 10
            elif ff < 1.5: base += 12
            else: base += 6; flags.append(f"very high FF={ff:.1f} (usually earnings-driven)")
        ed = has_earnings_before_expiry(sym, entry, expiry)
        if ed:
            base -= 15; flags.append(f"earnings {ed} inside front expiry -> gap risk on short front leg")
    elif strat == "Short_Strangle":
        base = 70
        if credit is not None:
            if credit < 2: base += 2
            elif credit <= 4: base += 8
            else: base += 4; flags.append(f"high credit {credit:.1f}%spot = high IV = bigger move risk")
        ed = has_earnings_before_expiry(sym, entry, expiry)
        if ed:
            base -= 18; flags.append(f"earnings {ed} before expiry -> strangle gap risk (consider skipping)")
    elif strat == "Earnings_ShortVol":
        base = 62                       # 60% hit but +39% fwd payoff
        flags.append("binary event trade: IV-crush edge, but a surprise gap is the tail")
    else:
        base = 50
    return int(np.clip(base, 0, 100)), flags


d = pd.read_csv(EXD / "execution_ALL.csv")
d["entry_date"] = pd.to_datetime(d["entry_date"]).dt.date
rows = []
# score per (strategy, symbol) trade, apply to both legs
seen = {}
for _, r in d.iterrows():
    key = (r["strategy"], r["symbol"])
    if key not in seen:
        exp = FRONT_EXP if "JUL" in str(r["expiry"]) else dt.date(2026, 8, 25)
        seen[key] = score_trade(r["strategy"], r["symbol"], r["signal"], r["entry_date"], exp)
    conv, flags = seen[key]
    rr = r.to_dict()
    rr["sector"] = sector(r["symbol"])
    rr["conviction"] = conv
    rr["risk_flags"] = "; ".join(flags) if flags else "-"
    rr["news_note"] = ""            # filled from news agent
    rows.append(rr)

out = pd.DataFrame(rows)
out = out.sort_values(["entry_date", "conviction", "strategy", "symbol", "opt"],
                      ascending=[True, False, True, True, True])
out.to_csv(EXD / "execution_scored.csv", index=False)

# per-trade summary (one row per structure, not per leg)
trades = out.drop_duplicates(["strategy", "symbol", "entry_date"])[
    ["entry_date", "strategy", "symbol", "sector", "signal", "conviction", "risk_flags"]]
trades.to_csv(EXD / "execution_conviction_summary.csv", index=False)
print(f"scored {len(out)} legs / {len(trades)} trades")
print("\n=== conviction by strategy (trade-level) ===")
for st, g in trades.groupby("strategy"):
    print(f"  {st:18s} n={len(g):3d}  conviction mean {g['conviction'].mean():.0f}  range {g['conviction'].min()}-{g['conviction'].max()}")
print("\n=== TOP 12 trades by conviction ===")
print(trades.sort_values("conviction", ascending=False).head(12).to_string(index=False))
print("\n=== FF calendars with earnings-in-window (lower conviction) ===")
ff = trades[(trades.strategy == "FF_Calendar")].sort_values("conviction")
print(ff.to_string(index=False))
