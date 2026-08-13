"""Build the extended scheduled-event calendar for OPTBUY_VOLEXPANSION_20260731.
Sources stated inline. Written once, not re-tuned after seeing backtest results.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"

# ---------------------------------------------------------------- 1. BUDGET (source: known GoI practice, Feb-1 since 2017; 2024 election-year had interim Feb-1 + full Jul-23)
budget = [
    ("2021-02-01", "BUDGET", "Union Budget FY22"),
    ("2022-02-01", "BUDGET", "Union Budget FY23"),
    ("2023-02-01", "BUDGET", "Union Budget FY24"),
    ("2024-02-01", "BUDGET", "Interim Budget FY25 (election year)"),
    ("2024-07-23", "BUDGET", "Full Budget FY25 (post-election)"),
    ("2025-02-01", "BUDGET", "Union Budget FY26"),
    ("2026-02-01", "BUDGET", "Union Budget FY27"),
]

# ---------------------------------------------------------------- 2. RBI MPC decision day (source: RBI press-release schedules found via web search
# 2026-07-31; 3-day meeting, decision on final day; some years' exact final day inferred from the
# bi-monthly rhythm where the specific press release wasn't in the search results -> [INFERENCE])
rbi = [
    ("2021-02-05", "verified-ish"), ("2021-04-07", "verified-ish"), ("2021-06-04", "verified-ish"),
    ("2021-08-06", "verified-ish"), ("2021-10-08", "verified-ish"), ("2021-12-08", "verified-ish"),
    ("2022-02-10", "verified-ish"), ("2022-04-08", "verified-ish"), ("2022-05-04", "OFF-CYCLE emergency hike"),
    ("2022-06-08", "verified-ish"), ("2022-08-05", "verified-ish"), ("2022-09-30", "verified-ish"),
    ("2022-12-07", "verified-ish"),
    ("2023-02-08", "verified-ish"), ("2023-04-06", "verified-ish"), ("2023-06-08", "verified-ish"),
    ("2023-08-10", "verified-ish"), ("2023-10-06", "verified-ish"), ("2023-12-08", "verified-ish"),
    ("2024-02-08", "verified-ish"), ("2024-04-05", "verified-ish"), ("2024-06-07", "verified-ish"),
    ("2024-08-08", "verified-ish"), ("2024-10-09", "verified-ish"), ("2024-12-06", "verified-ish"),
    ("2025-02-07", "verified-ish"), ("2025-04-09", "verified-ish"), ("2025-06-06", "verified-ish"),
    ("2025-08-06", "[INFERENCE] est bi-monthly"), ("2025-10-01", "[INFERENCE] est bi-monthly"),
    ("2025-12-05", "[INFERENCE] est bi-monthly"),
    ("2026-02-06", "verified-ish (Feb 4-6 meeting per news)"), ("2026-04-08", "[INFERENCE] est"),
    ("2026-06-05", "[INFERENCE] est"),
]
rbi = [(d, "RBI", note) for d, note in rbi]

# ---------------------------------------------------------------- 3. US Fed FOMC decision day
#  (source: federalreserve.gov/monetarypolicy/fomccalendars.htm, fetched 2026-07-31 -- authoritative)
fed_dates = {
    2021: ["01-27", "03-17", "04-28", "06-16", "07-28", "09-22", "11-03", "12-15"],
    2022: ["01-26", "03-16", "05-04", "06-15", "07-27", "09-21", "11-02", "12-14"],
    2023: ["02-01", "03-22", "05-03", "06-14", "07-26", "09-20", "11-01", "12-13"],
    2024: ["01-31", "03-20", "05-01", "06-12", "07-31", "09-18", "11-07", "12-18"],
    2025: ["01-29", "03-19", "05-07", "06-18", "07-30", "09-17", "10-29", "12-10"],
    2026: ["01-28", "03-18", "04-29", "06-17"],   # only through option-data coverage (~Jun-2026)
}
fed = [(f"{y}-{md}", "FED", "FOMC decision (IST reaction next session)") for y, mds in fed_dates.items() for md in mds]

# ---------------------------------------------------------------- 4. Election RESULT days (verified via web search 2026-07-31)
elections = [
    ("2021-05-02", "ELECTION", "WB/Assam/TN/Kerala/Puducherry state results"),
    ("2022-03-10", "ELECTION", "UP/Punjab/Uttarakhand/Goa/Manipur state results"),
    ("2023-05-13", "ELECTION", "Karnataka state result"),
    ("2023-12-03", "ELECTION", "Rajasthan/MP/Chhattisgarh/Telangana/Mizoram results"),
    ("2024-06-04", "ELECTION", "Lok Sabha general election result (largest single-day move)"),
    ("2024-10-08", "ELECTION", "Haryana + J&K state results"),
    ("2024-11-23", "ELECTION", "Maharashtra + Jharkhand state results"),
    ("2025-02-08", "ELECTION", "Delhi state result"),
    ("2025-11-14", "ELECTION", "Bihar state result"),
    ("2026-05-04", "ELECTION", "Assam/Kerala/TN/WB/Puducherry state results"),
]

# also keep the pre-given exclusion-list dates the task cited (some are duplicates/near-duplicates
# of the above, kept for traceability -- e.g. 2024-06-03 exit-poll euphoria day paired with 2024-06-04)
given = [
    ("2024-06-03", "ELECTION", "Exit-poll euphoria day (pre-result rally), paired with 2024-06-04"),
]

rows = []
for d, cat, note in budget:
    rows.append(dict(date=d, category=cat, note=note, source="known GoI Feb-1 practice"))
for d, cat, note in rbi:
    rows.append(dict(date=d, category=cat, note=note, source="RBI schedule releases (web search 2026-07-31) + bi-monthly rhythm"))
for d, cat, note in fed:
    rows.append(dict(date=d, category=cat, note=note, source="federalreserve.gov/monetarypolicy/fomccalendars.htm (fetched 2026-07-31)"))
for d, cat, note in elections + given:
    rows.append(dict(date=d, category=cat, note=note, source="web search 2026-07-31 (news reports)"))

ev = pd.DataFrame(rows)
ev["date"] = pd.to_datetime(ev["date"])
ev = ev.drop_duplicates(subset=["date", "category"]).sort_values("date").reset_index(drop=True)

# ---------------------------------------------------------------- 5. EARNINGS CLUSTERS from PIT data
e = pd.read_parquet(r"datasets/earnings_pit/unified_quarterly_pit.parquet")
TOP10 = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "ITC", "LT", "BHARTIARTL", "SBIN", "KOTAKBANK"]
sub = e[e.symbol.isin(TOP10)].copy()
sub["available_date"] = pd.to_datetime(sub["available_date"], errors="coerce")
sub = sub.dropna(subset=["available_date"]).sort_values("available_date")

# cluster: a 5-calendar-day rolling window containing >=3 distinct TOP10 names' available_date
clusters = []
dates = sub["available_date"].sort_values().unique()
used = set()
for d0 in dates:
    win = sub[(sub.available_date >= d0) & (sub.available_date <= d0 + pd.Timedelta(days=5))]
    names = set(win.symbol.unique())
    if len(names) >= 3:
        clusters.append(dict(start=win.available_date.min(), end=win.available_date.max(),
                              n_names=len(names), names=",".join(sorted(names))))
cl = pd.DataFrame(clusters).drop_duplicates(subset=["start", "end"]) if clusters else pd.DataFrame()
if len(cl):
    # merge overlapping windows (greedy)
    cl = cl.sort_values("start")
    merged = []
    cur = None
    for _, r in cl.iterrows():
        if cur is None:
            cur = r.to_dict()
        elif r["start"] <= cur["end"] + pd.Timedelta(days=1):
            cur["end"] = max(cur["end"], r["end"])
            cur["names"] = ",".join(sorted(set(cur["names"].split(",")) | set(r["names"].split(","))))
            cur["n_names"] = len(cur["names"].split(","))
        else:
            merged.append(cur)
            cur = r.to_dict()
    if cur is not None:
        merged.append(cur)
    cl = pd.DataFrame(merged)
    cl = cl[cl.n_names >= 3].reset_index(drop=True)

print(f"[earnings clusters] {len(cl)} clusters, n_names>=3, from TOP10={TOP10}")
print(cl.head(30).to_string())

cl.to_csv(f"{OUT}/earnings_clusters.csv", index=False)
ev.to_csv(f"{OUT}/events_scheduled.csv", index=False)
print(f"\n[events] {len(ev)} scheduled events written")
print(ev.groupby("category").size())
print(ev.date.min(), ev.date.max())
