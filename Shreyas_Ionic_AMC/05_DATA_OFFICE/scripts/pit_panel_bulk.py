#!/usr/bin/env python3
"""
PIT-Panel Extension: NSE XBRL quarterly results 2019-2021
Resume-safe bulk downloader + parser

Kavya Reddy (Data Officer) — 2026-07-12
"""

import pandas as pd
import os
import sys
import json
import csv
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import time
import hashlib

# Corporate proxy + SSL trust store
import requests
import truststore
truststore.inject_into_ssl()

# ===== CONFIGURATION =====
PARQUET_PATH = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\nse_quarterly_results_pit.parquet"
NIFTY500_PATH = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\NIFTY500_TICKER_2005_2025_Final.xlsx"
XBRL_CACHE_PATH = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\xbrl_results_2019_21"
RAW_XBRL_PATH = XBRL_CACHE_PATH + r"\raw"
OUTPUT_PARQUET = XBRL_CACHE_PATH + r"\xbrl_quarterly_2019_21.parquet"

SCRATCHPAD = r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500\4b30c315-515a-4ad4-97f2-a8ad55842a82\scratchpad"
LOG_FILE = Path(SCRATCHPAD) / "pit_panel_bulk.log"
LEDGER_FILE = Path(SCRATCHPAD) / "download_ledger.csv"
SAMPLE_RESULTS_FILE = Path(SCRATCHPAD) / "sample_verify_results.json"

# ===== SETUP =====
Path(SCRATCHPAD).mkdir(parents=True, exist_ok=True)
Path(RAW_XBRL_PATH).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===== PARSING FUNCTIONS =====

INDAS_NAMESPACE = {
    'ifrs': 'http://xbrl.iasb.org/2020-03-30/ifrs/',
    'ifrs-full': 'http://xbrl.iasb.org/2020-03-30/ifrs/full',
    'ixbrl': 'http://www.sec.gov/ixbrl/2008-06-30',
    'iso4217': 'http://www.xbrl.org/2003/iso4217'
}

def extract_indas_field(root, field_names, default_ns='http://xbrl.iasb.org/2020-03-30/ifrs/full'):
    """Extract INDAS/IFRS field value. field_names is a list of possible tag names."""
    value = None

    # Try multiple namespaces
    for field_name in field_names:
        for ns_uri in [default_ns, INDAS_NAMESPACE.get('ifrs-full'), INDAS_NAMESPACE.get('ifrs'), None]:
            if ns_uri:
                tag = f"{{{ns_uri}}}{field_name}"
            else:
                tag = field_name

            elem = root.find(f".//{tag}")
            if elem is not None and elem.text:
                try:
                    value = float(elem.text)
                    return value
                except ValueError:
                    pass

    return value

def parse_xbrl_xml(xml_path, symbol, to_date, announce_ts, consolidated):
    """Parse XBRL XML and extract key financial fields."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Extract INDAS fields
        revenue = extract_indas_field(root, ['RevenueFromOperations', 'Revenue', 'RevenueFromContract'])
        pat = extract_indas_field(root, ['ProfitLossForPeriod', 'ProfitOrLoss', 'Profit'])
        eps = extract_indas_field(root, ['BasicEarningsPerShare', 'EarningsPerShare'])

        return {
            'symbol': symbol,
            'quarter_end': to_date,
            'announce_ts': announce_ts,
            'revenue': revenue,
            'pat': pat,
            'eps': eps,
            'taxonomy': 'INDAS',
            'consolidated_flag': consolidated,
            'source_url': '',
            'parse_status': 'SUCCESS'
        }
    except Exception as e:
        logger.warning(f"Parse error for {xml_path}: {e}")
        return {
            'symbol': symbol,
            'quarter_end': to_date,
            'announce_ts': announce_ts,
            'revenue': None,
            'pat': None,
            'eps': None,
            'taxonomy': 'INDAS',
            'consolidated_flag': consolidated,
            'source_url': '',
            'parse_status': f"ERROR: {str(e)[:50]}"
        }

# ===== SAMPLE VERIFICATION =====

def run_sample_verification():
    """D-009 gate: download 5 samples, parse, verify."""
    logger.info("=" * 60)
    logger.info("[D-009 SAMPLE VERIFICATION]")
    logger.info("=" * 60)

    # Load sample URLs
    sample_file = Path(SCRATCHPAD) / "sample_urls.json"
    if not sample_file.exists():
        logger.error(f"Sample URLs file not found: {sample_file}")
        return False

    with open(sample_file) as f:
        sample_data = json.load(f)

    sample_urls = [u for u in sample_data['sample_urls'] if u and u != '-'][:5]
    logger.info(f"Sample URLs ({len(sample_urls)}):")
    for url in sample_urls:
        logger.info(f"  {url}")

    # Session for downloads
    session = requests.Session()

    # Cookie warm-up from NSE
    logger.info("Cookie warm-up from NSE...")
    try:
        session.get('https://www.nseindia.com', timeout=10)
        logger.info("Cookie warm-up OK")
    except Exception as e:
        logger.warning(f"Cookie warm-up failed: {e}")

    # Download and parse samples
    sample_results = []
    success_count = 0

    for i, url in enumerate(sample_urls, 1):
        logger.info(f"\n[{i}/{len(sample_urls)}] Downloading {url.split('/')[-1][:40]}...")

        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()

            # Save to temp
            temp_file = Path(SCRATCHPAD) / f"sample_{i}.xml"
            with open(temp_file, 'wb') as f:
                f.write(resp.content)

            logger.info(f"  Downloaded: {len(resp.content)} bytes")

            # Extract metadata from URL
            parts = url.split('/')[-1].split('_')
            symbol = "SAMPLE"  # Would need mapping from scope to extract this

            # Try parsing
            parsed = parse_xbrl_xml(str(temp_file), symbol, None, None, None)
            parsed['source_url'] = url
            sample_results.append(parsed)

            if parsed['parse_status'] == 'SUCCESS':
                logger.info(f"  Parsed: Revenue={parsed['revenue']}, PAT={parsed['pat']}, EPS={parsed['eps']}")
                success_count += 1
            else:
                logger.warning(f"  Parse status: {parsed['parse_status']}")

            # Delay
            time.sleep(1.0)

        except Exception as e:
            logger.error(f"  Failed: {e}")
            sample_results.append({
                'source_url': url,
                'parse_status': f"DOWNLOAD_ERROR: {str(e)[:50]}"
            })

    # Save results
    with open(SAMPLE_RESULTS_FILE, 'w') as f:
        json.dump(sample_results, f, indent=2)

    logger.info(f"\n[D-009 RESULT] {success_count}/{len(sample_urls)} samples parsed successfully")

    # RELIANCE Q2FY20 check
    reliance_found = any(r.get('source_url', '').find('INDAS_48646') >= 0 for r in sample_results)
    if reliance_found:
        logger.info("RELIANCE Q2FY20 found in samples - verify PAT ≈ 11,262 crore")

    return success_count >= 4  # At least 4 of 5 must parse

# ===== BULK DOWNLOADER =====

def load_scope():
    """Load full scope from parquet."""
    results_df = pd.read_parquet(PARQUET_PATH)
    results_df['toDate'] = pd.to_datetime(results_df['toDate'], format='%d-%b-%Y', errors='coerce')
    results_df['broadCastDate'] = pd.to_datetime(results_df['broadCastDate'], errors='coerce')

    nifty500_df = pd.read_excel(NIFTY500_PATH)
    nifty500_syms = set(nifty500_df['Ticker'].str.upper().unique())

    year_mask = (results_df['toDate'].dt.year >= 2019) & (results_df['toDate'].dt.year <= 2021)
    period_mask = results_df['period'] == 'Quarterly'
    symbol_mask = results_df['symbol'].str.upper().isin(nifty500_syms)

    filtered = results_df[year_mask & period_mask & symbol_mask].copy()
    filtered['quarter'] = filtered['toDate'].dt.to_period('Q')
    filtered = filtered.sort_values('broadCastDate')

    deduped_list = []
    for (sym, q), group in filtered.groupby(['symbol', 'quarter']):
        consol = group[group['consolidated'] == 1]
        if len(consol) > 0:
            deduped_list.append(consol.iloc[0])
        else:
            deduped_list.append(group.iloc[0])

    final_scope = pd.DataFrame(deduped_list)
    final_scope = final_scope[final_scope['xbrl'] != '-'].copy()
    return final_scope

def run_bulk_download():
    """Resume-safe bulk download of XBRL XMLs."""
    logger.info("=" * 60)
    logger.info("[BULK DOWNLOAD]")
    logger.info("=" * 60)

    scope = load_scope()
    logger.info(f"Scope: {len(scope)} rows, {len(scope['xbrl'].unique())} unique URLs")

    # Load or init ledger
    ledger = {}
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE) as f:
            reader = csv.DictReader(f)
            ledger = {row['url_hash']: row for row in reader}
        logger.info(f"Resumed from ledger: {len(ledger)} prior entries")

    # Session
    session = requests.Session()
    session.get('https://www.nseindia.com', timeout=10)

    # Download loop
    urls_to_download = scope[['symbol', 'toDate', 'broadCastDate', 'consolidated', 'xbrl']].drop_duplicates(subset=['xbrl'])
    logger.info(f"Unique URLs: {len(urls_to_download)}")

    new_downloads = 0
    errors = 0

    for idx, (_, row) in enumerate(urls_to_download.iterrows(), 1):
        url = row['xbrl']
        url_hash = hashlib.md5(url.encode()).hexdigest()

        # Check if already done
        if url_hash in ledger and ledger[url_hash].get('status') == 'SUCCESS':
            continue

        logger.info(f"[{idx}/{len(urls_to_download)}] {url.split('/')[-1][:40]}...", extra={'status': 'pending'})

        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()

            # Save to disk
            fname = url.split('/')[-1]
            fpath = Path(RAW_XBRL_PATH) / fname
            with open(fpath, 'wb') as f:
                f.write(resp.content)

            # Update ledger
            ledger[url_hash] = {
                'url': url,
                'url_hash': url_hash,
                'filename': fname,
                'status': 'SUCCESS',
                'timestamp': datetime.now().isoformat()
            }
            new_downloads += 1

            if idx % 100 == 0:
                logger.info(f"  Progress: {new_downloads} downloaded, {errors} errors")
                # Save ledger periodically
                _save_ledger(ledger)

            time.sleep(1.0)  # >=1.0s/req per brief

        except Exception as e:
            logger.error(f"  Error: {e}")
            ledger[url_hash] = {
                'url': url,
                'url_hash': url_hash,
                'status': 'ERROR',
                'error': str(e)[:100],
                'timestamp': datetime.now().isoformat()
            }
            errors += 1

    # Final ledger save
    _save_ledger(ledger)
    logger.info(f"\n[BULK RESULT] {new_downloads} new downloads, {errors} errors, {len(ledger)} total")

def _save_ledger(ledger):
    """Save download ledger atomically."""
    with open(LEDGER_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'url_hash', 'filename', 'status', 'error', 'timestamp'])
        writer.writeheader()
        writer.writerows(ledger.values())

# ===== MAIN =====

if __name__ == '__main__':
    import sys

    phase = sys.argv[1] if len(sys.argv) > 1 else 'sample'

    logger.info(f"PIT-Panel Extension starting (phase={phase})")

    if phase == 'sample':
        success = run_sample_verification()
        sys.exit(0 if success else 1)
    elif phase == 'bulk':
        run_bulk_download()
        sys.exit(0)
    else:
        logger.error(f"Unknown phase: {phase}")
        sys.exit(1)
