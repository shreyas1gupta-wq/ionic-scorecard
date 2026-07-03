"""Download Times of India Headlines (2001-2020, 3.3M headlines) from Harvard Dataverse."""
import os, time
from pathlib import Path
import truststore; truststore.inject_into_ssl()
import requests

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "datasets" / "toi_headlines"
DEST.mkdir(parents=True, exist_ok=True)
LOCAL = DEST / "india-news-headlines.csv"

URL = "https://dataverse.harvard.edu/api/access/datafile/:persistentId?persistentId=doi:10.7910/DVN/DPQMQH/P2Z4PM"

SEGMENT = 80 * 1024 * 1024
READ_SZ = 4 * 1024 * 1024
MAX_RETRY = 20

if LOCAL.exists() and LOCAL.stat().st_size > 100_000_000:
    print(f"SKIP  {LOCAL.name} ({LOCAL.stat().st_size/1e6:.0f}MB already)")
    exit()

print(f"Downloading TOI Headlines from Harvard Dataverse...")
try:
    r = requests.head(URL, allow_redirects=True, timeout=30)
    total = int(r.headers.get("content-length", 0))
    print(f"  Total: {total/1e6:.0f}MB")
except Exception as e:
    print(f"  HEAD failed, trying without size: {e}")
    total = 0

existing = LOCAL.stat().st_size if LOCAL.exists() else 0
if existing:
    print(f"  Resuming from {existing/1e6:.0f}MB")

pos = existing
t0 = time.time()
with open(LOCAL, "ab" if existing else "wb") as f:
    if total > 0:
        while pos < total:
            end = min(pos + SEGMENT - 1, total - 1)
            hdrs = {"Range": f"bytes={pos}-{end}"}
            for attempt in range(MAX_RETRY):
                try:
                    r = requests.get(URL, headers=hdrs, stream=True, timeout=60)
                    r.raise_for_status()
                    written = 0
                    for chunk in r.iter_content(READ_SZ):
                        if chunk:
                            f.write(chunk)
                            written += len(chunk)
                    pos += written
                    elapsed = time.time() - t0
                    mbps = (pos - existing) / elapsed / 1e6 if elapsed > 0 else 0
                    pct = pos / total * 100 if total else 0
                    print(f"  {pct:5.1f}%  {pos/1e6:7.0f}MB  {mbps:.1f}MB/s", flush=True)
                    break
                except Exception as e:
                    wait = min(3 * (attempt + 1), 15)
                    print(f"  RETRY att {attempt+1}: {e}", flush=True)
                    f.flush()
                    pos = LOCAL.stat().st_size
                    time.sleep(wait)
            else:
                print(f"  FAILED at {pos/1e6:.0f}MB")
                break
    else:
        print("  Streaming (no content-length)...")
        for attempt in range(MAX_RETRY):
            try:
                r = requests.get(URL, stream=True, timeout=120)
                r.raise_for_status()
                for chunk in r.iter_content(READ_SZ):
                    if chunk:
                        f.write(chunk)
                        pos += len(chunk)
                        if pos % (20 * 1024 * 1024) < READ_SZ:
                            elapsed = time.time() - t0
                            mbps = pos / elapsed / 1e6 if elapsed > 0 else 0
                            print(f"  {pos/1e6:7.0f}MB  {mbps:.1f}MB/s", flush=True)
                break
            except Exception as e:
                wait = min(3 * (attempt + 1), 15)
                print(f"  RETRY att {attempt+1}: {e}", flush=True)
                time.sleep(wait)

final = LOCAL.stat().st_size if LOCAL.exists() else 0
elapsed = time.time() - t0
print(f"\nDone: {LOCAL.name} {final/1e6:.0f}MB in {elapsed:.0f}s ({final/elapsed/1e6:.1f}MB/s avg)")
