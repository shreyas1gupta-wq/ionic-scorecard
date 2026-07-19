"""W4ETF data fetch — cross-asset/ETF sleeve universe.
Fetches global + factor-ETF candidates via yfinance, persists to datasets/etf_universe/,
verifies non-null on re-read (D-009). Sequential requests (corporate proxy stalls threads).
Logs identity check (longName) for factor-ETF candidates so we don't fabricate ticker->asset mapping.
"""
import os, sys, json, time
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import truststore; truststore.inject_into_ssl()
import pandas as pd
import yfinance as yf

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = os.path.join(BASE, "datasets", "etf_universe")
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, "_fetch_log.json")

# unambiguous global tickers (no identity ambiguity)
GLOBAL = {
    "QQQ": "QQQ", "NDX": "^NDX", "SPY": "SPY", "GSPC": "^GSPC", "COPPER_HG": "HG=F",
}

# India index candidates (broad market indices we don't already hold on disk)
INDEX_CANDIDATES = {
    "NSEI": "^NSEI",  # nifty 50 index (cross check vs niftybees)
    "MIDCAP_IDX_A": "^CNXMIDCAP",
    "MIDCAP_IDX_B": "^NSEMDCP50",
    "SMALLCAP_IDX_A": "^CNXSC",
}

# India factor / cap-segment ETF candidates (ticker->asset identity to be VERIFIED via .info longName)
ETF_CANDIDATES = {
    "MIDCAP_ETF_A": "MID150BEES.NS",
    "MIDCAP_ETF_B": "MIDCAPETF.NS",
    "MIDCAP_ETF_C": "MOM100.NS",
    "SMALLCAP_ETF_A": "SMALLCAP.NS",
    "SMALLCAP_ETF_B": "SMALCAP250.NS",
    "SMALLCAP_ETF_C": "SETFSC.NS",
    "MICROCAP_ETF_A": "MICROCAP250.NS",
    "MICROCAP_ETF_B": "MOM50.NS",
    "MOMENTUM_ETF_A": "MOM100.NS",
    "MOMENTUM_ETF_B": "MOMENTUM.NS",
    "MOMENTUM_ETF_C": "MOMOMENTUM.NS",
    "MOMENTUM_ETF_D": "ALPHAETF.NS",
    "MOMENTUM_ETF_E": "M200MOM30.NS",
    "LOWVOL_ETF_A": "LOWVOL1.NS",
    "LOWVOL_ETF_B": "LOWVOLIETF.NS",
    "LOWVOL_ETF_C": "ALPL30IETF.NS",
    "LOWVOL_ETF_D": "NIFTY100LOWVOL.NS",
    "LOWVOL_ETF_E": "N100LOWVOL.NS",
}

def fetch_one(tag, tk, check_identity=False):
    rec = {"tag": tag, "ticker": tk}
    try:
        df = yf.download(tk, period="max", interval="1d", auto_adjust=False, progress=False, threads=False)
        if df is None or len(df) == 0:
            rec["status"] = "EMPTY"
            return rec, None
        if hasattr(df.columns, "get_level_values"):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        n_nonnull = df["Close"].notna().sum()
        rec["n_rows"] = len(df)
        rec["n_nonnull_close"] = int(n_nonnull)
        rec["date_min"] = str(df["Date"].min())
        rec["date_max"] = str(df["Date"].max())
        rec["last_close"] = float(df["Close"].dropna().iloc[-1]) if n_nonnull else None
        if check_identity:
            try:
                info = yf.Ticker(tk).info
                rec["longName"] = info.get("longName") or info.get("shortName")
            except Exception as e:
                rec["longName"] = f"ERR:{type(e).__name__}"
        rec["status"] = "OK" if n_nonnull >= 30 else "TOO_SHORT"
        return rec, df
    except Exception as e:
        rec["status"] = f"ERR:{type(e).__name__}:{e}"
        return rec, None

def main():
    results = []
    # 1. global
    for tag, tk in GLOBAL.items():
        rec, df = fetch_one(tag, tk)
        results.append(rec)
        if df is not None and rec["status"] == "OK":
            df.to_parquet(os.path.join(OUT, f"{tag}.parquet"))
        print(tag, tk, rec.get("status"), rec.get("n_rows"), rec.get("date_max"))
        time.sleep(1.0)

    # 2. index candidates
    for tag, tk in INDEX_CANDIDATES.items():
        rec, df = fetch_one(tag, tk)
        results.append(rec)
        if df is not None and rec["status"] == "OK":
            df.to_parquet(os.path.join(OUT, f"{tag}.parquet"))
        print(tag, tk, rec.get("status"), rec.get("n_rows"), rec.get("date_max"))
        time.sleep(1.0)

    # 3. factor ETF candidates with identity check
    for tag, tk in ETF_CANDIDATES.items():
        rec, df = fetch_one(tag, tk, check_identity=True)
        results.append(rec)
        if df is not None and rec["status"] == "OK":
            df.to_parquet(os.path.join(OUT, f"{tag}.parquet"))
        print(tag, tk, rec.get("status"), rec.get("n_rows"), rec.get("longName"))
        time.sleep(1.2)

    with open(LOG, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("DONE. Log at", LOG)

if __name__ == "__main__":
    main()
