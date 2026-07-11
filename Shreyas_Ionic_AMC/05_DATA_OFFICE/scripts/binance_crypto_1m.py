"""D-033 pull: Binance 1-min klines BTCUSDT + ETHUSDT, 2018-01 -> 2026-06 (monthly zips).
Source: data.binance.vision (exchange-official public dumps). Resume-safe: skips saved months.
Output: 05_DATA_OFFICE/data/crypto_1m/{sym}_{yyyy}.parquet (yearly consolidation).
"""
import io, datetime as dt, time, zipfile
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/crypto_1m"
OUT.mkdir(parents=True, exist_ok=True)
DONE = OUT / "done_months.txt"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_vol", "trades", "taker_base", "taker_quote", "ignore"]

done = set(DONE.read_text().split()) if DONE.exists() else set()
sess = requests.Session()
sess.headers.update({"User-Agent": "Mozilla/5.0 Chrome/126"})

for sym in ["BTCUSDT", "ETHUSDT"]:
    buf, cur_year = [], None

    def flush(y):
        if not buf:
            return
        p = OUT / f"{sym}_{y}.parquet"
        new = pd.concat(buf, ignore_index=True)
        if p.exists():
            new = pd.concat([pd.read_parquet(p), new], ignore_index=True)
        new = new.drop_duplicates("ts").sort_values("ts")
        new.to_parquet(p, index=False)
        print(f"CHECKPOINT {p.name}: {len(new)} rows", flush=True)
        buf.clear()

    m = dt.date(2018, 1, 1)
    while m <= dt.date(2026, 6, 1):
        tag = f"{sym}-{m:%Y-%m}"
        if tag in done:
            m = (m.replace(day=28) + dt.timedelta(days=5)).replace(day=1)
            continue
        if cur_year is not None and m.year != cur_year:
            flush(cur_year)
        cur_year = m.year
        url = f"https://data.binance.vision/data/spot/monthly/klines/{sym}/1m/{sym}-1m-{m:%Y-%m}.zip"
        try:
            r = sess.get(url, timeout=120)
            if r.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    df = pd.read_csv(z.open(z.namelist()[0]), header=None, names=COLS)
                # binance switched open_time to microseconds in 2025 files; normalize to ms
                if df.open_time.iloc[0] > 10**14:
                    df["open_time"] = df["open_time"] // 1000
                df["ts"] = pd.to_datetime(df["open_time"], unit="ms")
                buf.append(df[["ts", "open", "high", "low", "close", "volume", "trades"]])
                print(f"{tag}: {len(df)} rows", flush=True)
            else:
                print(f"{tag}: HTTP {r.status_code}", flush=True)
            with open(DONE, "a", encoding="utf-8") as f:
                f.write(tag + "\n")
        except Exception as e:
            print(f"{tag}: ERR {type(e).__name__} {str(e)[:80]}", flush=True)
            time.sleep(5)
        time.sleep(0.4)
        m = (m.replace(day=28) + dt.timedelta(days=5)).replace(day=1)
    flush(cur_year)

# verification: BTC known monthly landmark — 2021-04 ATH region ~64.8k intramonth high
try:
    chk = pd.read_parquet(OUT / "BTCUSDT_2021.parquet")
    apr = chk[(chk.ts >= "2021-04-01") & (chk.ts < "2021-05-01")]
    print(f"VERIFY BTC 2021-04 high={apr.high.max():.0f} (expect ~64800), n={len(apr)} (expect ~43200)", flush=True)
except Exception as e:
    print("verify err", e)
print("ALL DONE", flush=True)
