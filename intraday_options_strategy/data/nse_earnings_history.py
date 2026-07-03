"""Fetch historical NSE board meetings (earnings dates) in 3-month windows.
Goes back ~5 years to build a comprehensive earnings calendar.
Saves to datasets/nse_earnings_dates/
"""
import truststore; truststore.inject_into_ssl()
import requests
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DEST = ROOT / "datasets" / "nse_earnings_dates"
DEST.mkdir(parents=True, exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.nseindia.com/companies-listing/corporate-filings-board-meetings',
}

session = requests.Session()
session.headers.update(headers)

print("Getting NSE session...")
r = session.get("https://www.nseindia.com/", timeout=15)
print(f"  Status: {r.status_code}")

all_meetings = []
window_months = 3
end = datetime.now()
start_limit = datetime(2020, 1, 1)  # go back to 2020

window_end = end
failures = 0

print(f"\nFetching board meetings from {start_limit.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}...")
print(f"Window size: {window_months} months\n")

while window_end > start_limit and failures < 5:
    window_start = window_end - timedelta(days=window_months * 30)
    if window_start < start_limit:
        window_start = start_limit

    url = (f"https://www.nseindia.com/api/corporate-board-meetings?"
           f"index=equities"
           f"&from_date={window_start.strftime('%d-%m-%Y')}"
           f"&to_date={window_end.strftime('%d-%m-%Y')}")

    for attempt in range(5):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    count = len(data)
                    all_meetings.extend(data)
                    print(f"  {window_start.strftime('%Y-%m-%d')} to {window_end.strftime('%Y-%m-%d')}: {count} meetings (total: {len(all_meetings)})")
                    failures = 0
                    break
                else:
                    print(f"  Unexpected response type: {type(data)}")
                    break
            elif r.status_code == 401:
                print(f"  Session expired, refreshing...")
                session.get("https://www.nseindia.com/", timeout=15)
                time.sleep(2)
            else:
                print(f"  HTTP {r.status_code}, retrying...")
                time.sleep(3)
        except Exception as e:
            print(f"  Error: {e}, retrying...")
            time.sleep(5)
            try:
                session.get("https://www.nseindia.com/", timeout=15)
            except:
                pass
    else:
        failures += 1
        print(f"  FAILED window {window_start.strftime('%Y-%m-%d')} to {window_end.strftime('%Y-%m-%d')}")

    window_end = window_start - timedelta(days=1)
    time.sleep(2)  # be nice to NSE

# Also fetch corporate actions (dividends, splits, bonuses)
print(f"\nFetching corporate actions...")
all_actions = []
window_end = end
while window_end > start_limit and failures < 5:
    window_start = window_end - timedelta(days=window_months * 30)
    if window_start < start_limit:
        window_start = start_limit

    url = (f"https://www.nseindia.com/api/corporates-corporateActions?"
           f"index=equities"
           f"&from_date={window_start.strftime('%d-%m-%Y')}"
           f"&to_date={window_end.strftime('%d-%m-%Y')}")

    for attempt in range(5):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    all_actions.extend(data)
                    print(f"  {window_start.strftime('%Y-%m-%d')} to {window_end.strftime('%Y-%m-%d')}: {len(data)} actions (total: {len(all_actions)})")
                    break
                else:
                    break
            elif r.status_code == 401:
                session.get("https://www.nseindia.com/", timeout=15)
                time.sleep(2)
            else:
                time.sleep(3)
        except Exception as e:
            time.sleep(5)
            try:
                session.get("https://www.nseindia.com/", timeout=15)
            except:
                pass
    else:
        failures += 1

    window_end = window_start - timedelta(days=1)
    time.sleep(2)

# Save
print(f"\n=== RESULTS ===")
print(f"Board meetings: {len(all_meetings)}")
print(f"Corporate actions: {len(all_actions)}")

if all_meetings:
    with open(DEST / 'board_meetings_all.json', 'w', encoding='utf-8') as f:
        json.dump(all_meetings, f, indent=2, ensure_ascii=False)
    print(f"  Saved board_meetings_all.json")

    # Extract just earnings dates
    earnings = []
    for m in all_meetings:
        purpose = m.get('bm_purpose', '')
        if 'Financial Results' in purpose or 'Quarterly' in purpose or 'Annual' in purpose:
            earnings.append({
                'symbol': m.get('bm_symbol'),
                'date': m.get('bm_date'),
                'purpose': purpose,
                'company': m.get('sm_name'),
                'isin': m.get('sm_isin'),
            })
    with open(DEST / 'earnings_dates.json', 'w', encoding='utf-8') as f:
        json.dump(earnings, f, indent=2, ensure_ascii=False)
    print(f"  Extracted {len(earnings)} earnings dates -> earnings_dates.json")

    # Also save as CSV
    try:
        import csv
        with open(DEST / 'earnings_dates.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['symbol', 'date', 'purpose', 'company', 'isin'])
            w.writeheader()
            w.writerows(earnings)
        print(f"  Also saved as earnings_dates.csv")
    except:
        pass

if all_actions:
    with open(DEST / 'corporate_actions_all.json', 'w', encoding='utf-8') as f:
        json.dump(all_actions, f, indent=2, ensure_ascii=False)
    print(f"  Saved corporate_actions_all.json")

    # Count action types
    types = {}
    for a in all_actions:
        s = a.get('subject', 'unknown')
        key = s.split('-')[0].strip() if '-' in s else s[:30]
        types[key] = types.get(key, 0) + 1
    print("  Action types:")
    for t, c in sorted(types.items(), key=lambda x: -x[1])[:10]:
        print(f"    {c:5d}  {t}")

print("\nDone.")
