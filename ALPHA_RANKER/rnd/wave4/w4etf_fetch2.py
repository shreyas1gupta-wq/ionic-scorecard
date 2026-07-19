import os, time
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import truststore; truststore.inject_into_ssl()
import yfinance as yf

CANDIDATES = {
    "SMALL_A": "SMALL250.NS", "SMALL_B": "NIFTYSMALL250.NS", "SMALL_C": "SMALLCAP250ETF.NS",
    "SMALL_D": "MOSMALL250.NS", "SMALL_E": "ABSLSMALL.NS", "SMALL_F": "SMALLCAPWORLD.NS",
    "SMALL_G": "SML250EF.NS",
    "MICRO_A": "MOM50.NS", "MICRO_B": "MICROCAP.NS", "MICRO_C": "MOMICROCAP.NS",
    "MICRO_D": "MOM250.NS", "MICRO_E": "MOMICRO250.NS",
}
for tag, tk in CANDIDATES.items():
    try:
        df = yf.download(tk, period="5d", interval="1d", progress=False, threads=False)
        empty = df is None or len(df) == 0
        info = {}
        try:
            info = yf.Ticker(tk).info
        except Exception as e:
            info = {"err": str(e)}
        print(tag, tk, "EMPTY" if empty else f"rows={len(df)}", info.get("longName") or info.get("shortName") or info.get("err"))
    except Exception as e:
        print(tag, tk, "ERR", type(e).__name__)
    time.sleep(1.0)
