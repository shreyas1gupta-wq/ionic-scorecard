"""
STEP 2+3 (DATA-PREP / ALPHA_RANKER concall harvest): parse screener_live/<SYM>.json
documents[] for concall/transcript/PPT links across the NIFTY-750 universe, skip names
already covered by datasets/india_earnings_calls/extracted_texts.zip, and download the
latest ~6 quarters per remaining name. Resumable (skips files already on disk), polite
(~1.5s/req), backoff on 429/5xx, logs every attempt (success or failure) to _coverage.csv
so nothing is silently dropped. Bounded first pass -- full-history backfill is a separate,
larger job (see PROGRESS note at bottom).
"""
import os, sys, json, csv, time, random
import truststore; truststore.inject_into_ssl()
import requests

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
ALPHA = os.path.join(BASE, "ALPHA_RANKER")
UNIVERSE_FILE = os.path.join(ALPHA, "data", "universe", "symbols_750.txt")
SCREENER_DIR = os.path.join(ALPHA, "data", "fundamentals", "screener_live")
CONCALLS_DIR = os.path.join(ALPHA, "data", "concalls")
ZIP_INDEX = os.path.join(CONCALLS_DIR, "_existing_zip_index.json")
COVERAGE_CSV = os.path.join(CONCALLS_DIR, "_coverage.csv")
MAX_QUARTERS_PER_NAME = 6
DELAY_SEC = 1.5
MAX_RETRIES = 3

with open(ZIP_INDEX) as f:
    zip_index = json.load(f)  # ticker -> [quarter labels] already in extracted_texts.zip
already_covered = set(zip_index.keys())

universe = [x.strip() for x in open(UNIVERSE_FILE, encoding="utf-8") if x.strip()]
targets = [t for t in universe if t not in already_covered]
print(f"universe={len(universe)} already_covered_by_zip={len(already_covered)} targets_this_pass={len(targets)}")

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

# resume: load already-logged (ticker, href) pairs so re-runs don't re-attempt done work
done_keys = set()
write_header = not os.path.exists(COVERAGE_CSV)
if not write_header:
    with open(COVERAGE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done_keys.add((row["ticker"], row["href"]))

fcsv = open(COVERAGE_CSV, "a", newline="", encoding="utf-8")
writer = csv.DictWriter(fcsv, fieldnames=["ticker", "idx", "href", "text_label", "status",
                                          "http_status", "content_type", "bytes", "saved_path", "note"])
if write_header:
    writer.writeheader()
    fcsv.flush()

KEYWORDS = ("transcript", "concall", "earnings call")


def pick_links(doc_list):
    """Return up to MAX_QUARTERS_PER_NAME transcript-ish links, newest-first (list order
    in screener_live json is already reverse-chronological), falling back to PPT if no
    transcript-labeled link exists at all."""
    transcript_links = []
    ppt_links = []
    for doc in doc_list:
        txt = (doc.get("text") or "").strip().lower()
        href = doc.get("href") or ""
        if not href:
            continue
        if any(k in txt for k in KEYWORDS):
            transcript_links.append((doc.get("text", ""), href))
        elif txt == "ppt" or "investor" in txt:
            ppt_links.append((doc.get("text", ""), href))
    if transcript_links:
        return transcript_links[:MAX_QUARTERS_PER_NAME], "transcript"
    return ppt_links[:MAX_QUARTERS_PER_NAME], "ppt_fallback"


def safe_ext(content_type, href):
    if content_type and "pdf" in content_type:
        return "pdf"
    if href.lower().endswith(".pdf"):
        return "pdf"
    return "bin"


n_downloaded = 0
n_failed = 0
n_skipped_existing = 0

for ti, ticker in enumerate(targets):
    jpath = os.path.join(SCREENER_DIR, f"{ticker}.json")
    if not os.path.exists(jpath):
        writer.writerow(dict(ticker=ticker, idx=0, href="", text_label="", status="NO_SCREENER_JSON",
                              http_status="", content_type="", bytes="", saved_path="", note=""))
        fcsv.flush()
        continue
    try:
        d = json.load(open(jpath, encoding="utf-8"))
    except Exception as e:
        writer.writerow(dict(ticker=ticker, idx=0, href="", text_label="", status="JSON_PARSE_ERROR",
                              http_status="", content_type="", bytes="", saved_path="", note=str(e)[:200]))
        fcsv.flush()
        continue

    links, mode = pick_links(d.get("documents", []))
    if not links:
        writer.writerow(dict(ticker=ticker, idx=0, href="", text_label="", status="NO_LINKS_FOUND",
                              http_status="", content_type="", bytes="", saved_path="", note=""))
        fcsv.flush()
        continue

    tdir = os.path.join(CONCALLS_DIR, ticker)
    os.makedirs(tdir, exist_ok=True)

    for idx, (label, href) in enumerate(links, start=1):
        if (ticker, href) in done_keys:
            continue  # already attempted in a prior run
        # resumable: skip if a valid-looking file already on disk for this idx
        existing_candidates = [f for f in os.listdir(tdir) if f.startswith(f"q{idx}_")]
        if existing_candidates and os.path.getsize(os.path.join(tdir, existing_candidates[0])) > 2000:
            n_skipped_existing += 1
            continue

        attempt = 0
        status, http_status, ctype, nbytes, saved_path, note = "FAILED", "", "", 0, "", ""
        while attempt < MAX_RETRIES:
            attempt += 1
            try:
                r = session.get(href, timeout=20)
                http_status = str(r.status_code)
                ctype = r.headers.get("Content-Type", "")
                if r.status_code == 200 and r.content[:4] == b"%PDF":
                    ext = safe_ext(ctype, href)
                    saved_path = os.path.join(tdir, f"q{idx}_{mode}.{ext}")
                    with open(saved_path, "wb") as fh:
                        fh.write(r.content)
                    nbytes = len(r.content)
                    status = "OK"
                    n_downloaded += 1
                    break
                elif r.status_code == 200:
                    status = "NOT_PDF_SPA_SHELL"
                    nbytes = len(r.content)
                    note = "200 but not %PDF (likely SPA fallback / login wall)"
                    break  # don't retry a genuine non-PDF 200
                elif r.status_code in (429, 500, 502, 503, 504):
                    backoff = (2 ** attempt) + random.uniform(0, 1)
                    note = f"retrying after {r.status_code}, backoff {backoff:.1f}s"
                    time.sleep(backoff)
                    continue
                else:
                    status = f"HTTP_{r.status_code}"
                    break
            except requests.exceptions.RequestException as e:
                note = str(e)[:200]
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                status = "REQUEST_EXCEPTION"
                break

        if status != "OK":
            n_failed += 1
        writer.writerow(dict(ticker=ticker, idx=idx, href=href, text_label=label, status=status,
                              http_status=http_status, content_type=ctype, bytes=nbytes,
                              saved_path=saved_path, note=note))
        fcsv.flush()
        time.sleep(DELAY_SEC + random.uniform(0, 0.4))

    if (ti + 1) % 20 == 0:
        print(f"[{ti+1}/{len(targets)}] tickers processed | downloaded={n_downloaded} failed={n_failed} skipped_existing={n_skipped_existing}")

fcsv.close()
print(f"DONE. downloaded={n_downloaded} failed={n_failed} skipped_existing={n_skipped_existing}")
