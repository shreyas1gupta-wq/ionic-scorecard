"""P0 pre-index builder for the FnO Replay Game (ROADMAP.md section 3).

Produces into fno_game/data/:
  eligible_days.json  - sampling pool with per-day metadata
  coverage_gaps.json  - every excluded day + reason (honest pool report)
  lot_sizes.json      - historical lot per (trading_day, expiry) from bhavcopy
                        (reveal-screen/validation only; gameplay lot = 65, ruling L7)

Idempotent, re-runnable. ASCII-only output (cp1252 console).
"""
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SPOT_PQ = ROOT / r"intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet"
OPT_DIR = ROOT / r"intraday_options_strategy\datasets\raw\hf_index_options_1m\options\NIFTY"
VIX_1M = ROOT / r"intraday_options_strategy\datasets\processed\vix_1min.parquet"
VIX_DAILY_CANDIDATES = [
    ROOT / r"datasets\index_daily\india_vix.parquet",
    ROOT / r"intraday_options_strategy\datasets\index_daily\india_vix.parquet",
    ROOT / r"intraday_options_strategy\datasets\raw\india_vix_daily.csv",
]
BHAV_DIR = ROOT / r"intraday_options_strategy\datasets\raw\options"
OUT_DIR = ROOT / r"Shreyas_Ionic_AMC\09_PRODUCT\fno_game\data"

# Eligibility thresholds (ROADMAP section 3; tune only with a note in coverage_gaps meta)
MIN_SPOT_BARS = 360
MIN_STRIKES_COVERED = 8      # strikes within +-200 of open with >= MIN_COVERAGE, per side
MIN_COVERAGE = 0.60          # fraction of 09:15-15:25 minutes with a bar
MIN_STRIKES_TRADED = 5       # strikes with any volume>0 within +-200, per side
STRIKE_WINDOW = 200
KNOWN_LOTS = (25, 50, 65, 75)
SESSION_MINUTES = 371        # 09:15..15:25 inclusive

ICONIC_BLACKLIST = {
    "2024-06-04",  # election results crash
    "2024-06-03",  # exit-poll gap day
    "2022-02-24",  # Russia-Ukraine invasion
    "2021-11-04",  # Muhurat (safety; screen should exclude anyway)
    "2024-01-22",  # special session (Ram Mandir closure adjacent)
    "2025-06-13",  # Israel-Iran strike gap
    "2024-08-05",  # yen-carry unwind crash
    "2024-07-23",  # budget day FY25
    "2025-02-01",  # budget day FY26
    "2026-02-01",  # budget day FY27
    "2023-02-01",  # budget day FY24 (Adani-Hindenburg week)
    "2021-10-28",  # Oct-2021 top reversal
}


def log(msg):
    print(msg, flush=True)


def load_spot():
    df = pq.read_table(SPOT_PQ, columns=["timestamp", "open", "high", "low", "close"]).to_pandas()
    ts = pd.to_datetime(df["timestamp"])
    ts = ts.dt.tz_convert("Asia/Kolkata") if ts.dt.tz is not None else ts.dt.tz_localize("Asia/Kolkata")
    df["ts"] = ts
    df["d"] = ts.dt.date  # landmine #1: date AFTER tz conversion
    df["hm"] = ts.dt.hour * 60 + ts.dt.minute
    df = df[df["hm"] >= 9 * 60 + 15]  # landmine #2: drop pre-open auction bars
    return df


def spot_day_stats(df):
    out = {}
    for d, g in df.groupby("d"):
        g = g[g["hm"] <= 15 * 60 + 29]
        out[d] = {
            "bars": len(g),
            "first_hm": int(g["hm"].min()) if len(g) else -1,
            "has_1525": bool((g["hm"] >= 15 * 60 + 25).any()),
            "open_0915": float(g.loc[g["hm"].idxmin(), "open"]) if len(g) else None,
        }
    return out


def expiry_files():
    files = {}
    for p in sorted(OPT_DIR.glob("*.parquet")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", p.stem)
        if m:
            files[date.fromisoformat(m.group(1))] = p
    return files


def scan_expiry_file(path, spot_opens):
    """Per trading_day option-coverage stats for one expiry file. Returns {day: stats}."""
    cols = ["trading_day", "strike", "option_type", "volume", "timestamp"]
    df = pq.read_table(path, columns=cols).to_pandas()
    ts = pd.to_datetime(df["timestamp"])
    ts = ts.dt.tz_convert("Asia/Kolkata") if ts.dt.tz is not None else ts.dt.tz_localize("Asia/Kolkata")
    hm = ts.dt.hour * 60 + ts.dt.minute
    df = df[(hm >= 9 * 60 + 15) & (hm <= 15 * 60 + 25)]
    df = df.assign(td=pd.to_datetime(df["trading_day"]).dt.date, hm=hm)
    # some early files carry fully duplicated bars (seen 2021: 2x376 rows/strike)
    df = df.drop_duplicates(subset=["td", "strike", "option_type", "hm"])
    stats = {}
    for d, g in df.groupby("td"):
        opn = spot_opens.get(d)
        if opn is None:
            continue
        w = g[(g["strike"] >= opn - STRIKE_WINDOW) & (g["strike"] <= opn + STRIKE_WINDOW)]
        row = {}
        for side in ("CE", "PE"):
            s = w[w["option_type"] == side]
            per_strike = s.groupby("strike").agg(nbar=("volume", "size"), vol=("volume", "sum"))
            row[side] = {
                "covered": int((per_strike["nbar"] >= MIN_COVERAGE * SESSION_MINUTES).sum()),
                "traded": int((per_strike["vol"] > 0).sum()),
                "strikes": int(len(per_strike)),
            }
        stats[d] = row
    return stats


def detect_lot_old_schema(df):
    """Old NSE schema: median of VAL_INLAKH*1e5/(CONTRACTS*(STRIKE_PR+CLOSE)) per expiry."""
    o = df[(df["INSTRUMENT"] == "OPTIDX") & (df["SYMBOL"] == "NIFTY")
           & (df["CONTRACTS"] > 50) & (df["CLOSE"] > 0)]
    lots = {}
    for exp, g in o.groupby("EXPIRY_DT"):
        est = (g["VAL_INLAKH"] * 1e5 / (g["CONTRACTS"] * (g["STRIKE_PR"] + g["CLOSE"]))).median()
        snap = min(KNOWN_LOTS, key=lambda k: abs(est - k))
        lots[exp] = snap if abs(est - snap) / snap <= 0.12 else None  # None = failed snap
    return lots


def build_lot_table():
    table = defaultdict(dict)   # {expiry_iso: {trading_day_iso: lot}}
    failures = []
    files = sorted(BHAV_DIR.glob("fo_*.csv"))
    log(f"lot table: scanning {len(files)} bhavcopy files")
    for i, p in enumerate(files):
        day = p.stem.replace("fo_", "")
        day_iso = f"{day[:4]}-{day[4:6]}-{day[6:]}"
        try:
            head = pd.read_csv(p, nrows=0)
            cols = {c.strip() for c in head.columns}
            if "NewBrdLotQty" in cols:  # UDiFF
                df = pd.read_csv(p, usecols=lambda c: c.strip() in
                                 {"TckrSymb", "FinInstrmTp", "XpryDt", "NewBrdLotQty"})
                df.columns = [c.strip() for c in df.columns]
                n = df[(df["TckrSymb"] == "NIFTY") & (df["FinInstrmTp"].isin(("IDO", "IDF")))]
                for exp, g in n.groupby("XpryDt"):
                    lot = int(g["NewBrdLotQty"].mode().iloc[0])
                    exp_iso = pd.to_datetime(exp).date().isoformat()
                    if lot in KNOWN_LOTS:
                        table[exp_iso][day_iso] = lot
                    else:
                        failures.append({"file": p.name, "expiry": exp_iso, "lot": lot,
                                         "reason": "UDiFF lot not in known ladder"})
            elif "INSTRUMENT" in cols:  # old schema
                df = pd.read_csv(p, usecols=lambda c: c.strip() in
                                 {"INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR",
                                  "CLOSE", "CONTRACTS", "VAL_INLAKH"})
                df.columns = [c.strip() for c in df.columns]
                for exp, lot in detect_lot_old_schema(df).items():
                    exp_iso = pd.to_datetime(exp).date().isoformat()
                    if lot is None:
                        failures.append({"file": p.name, "expiry": exp_iso,
                                         "reason": "old-schema snap failed 12pct tol"})
                    else:
                        table[exp_iso][day_iso] = lot
            else:
                failures.append({"file": p.name, "reason": "unknown schema"})
        except Exception as e:  # noqa: BLE001 - per-file resilience, logged
            failures.append({"file": p.name, "reason": f"read error: {e}"})
        if (i + 1) % 50 == 0:
            log(f"  bhavcopy {i + 1}/{len(files)}")
    # collapse: one lot per expiry (mode); flag intra-expiry contradictions
    by_expiry, contradictions = {}, []
    for exp, obs in table.items():
        c = Counter(obs.values())
        lot, _ = c.most_common(1)[0]
        by_expiry[exp] = lot
        if len(c) > 1:
            contradictions.append({"expiry": exp, "observations": dict(c)})
    return {"by_expiry": by_expiry, "observations": {k: v for k, v in table.items()},
            "contradictions": contradictions, "failures": failures}


def vix_dates():
    d1m, ddaily = set(), set()
    try:
        v = pq.read_table(VIX_1M).to_pandas().reset_index()  # 'dt' is the pandas index
        ts = pd.to_datetime(v["dt"])
        if ts.dt.tz is not None:
            ts = ts.dt.tz_convert("Asia/Kolkata")
        d1m = set(ts.dt.date)  # tz-naive values are IST wall time already
    except Exception as e:  # noqa: BLE001
        log(f"vix 1min unavailable: {e}")
    for cand in VIX_DAILY_CANDIDATES:
        if cand.exists():
            try:
                if cand.suffix == ".parquet":
                    v = pq.read_table(cand, columns=["timestamp"]).to_pandas()
                    ddaily = set(pd.to_datetime(v["timestamp"]).dt.date)
                else:
                    v = pd.read_csv(cand, usecols=["Date"])
                    ddaily = set(pd.to_datetime(v["Date"]).dt.date)
                break
            except Exception as e:  # noqa: BLE001
                log(f"vix daily candidate {cand.name} failed: {e}")
    return d1m, ddaily


def main():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    log("1/4 spot scan...")
    spot = load_spot()
    sstats = spot_day_stats(spot)
    days = sorted(sstats)
    log(f"  {len(days)} spot trading days {days[0]} .. {days[-1]}")

    log("2/4 lot table from bhavcopy...")
    lots = build_lot_table()
    log(f"  {len(lots['by_expiry'])} expiries observed, "
        f"{len(lots['contradictions'])} contradictions, {len(lots['failures'])} failures")

    log("3/4 options coverage scan (one pass per expiry file)...")
    efiles = expiry_files()
    exps = sorted(efiles)
    spot_opens = {d: s["open_0915"] for d, s in sstats.items()}
    # map each day -> front expiry
    front = {}
    for d in days:
        nxt = [e for e in exps if e >= d]
        front[d] = nxt[0] if nxt else None
    # group days by front expiry, scan each file once
    by_file = defaultdict(list)
    for d, e in front.items():
        if e:
            by_file[e].append(d)
    ostats = {}
    for i, (e, dl) in enumerate(sorted(by_file.items())):
        try:
            res = scan_expiry_file(efiles[e], spot_opens)
            # keep stats ONLY for days whose FRONT expiry is this file — the same
            # trading day also appears in later files (as thin next-weekly rows)
            # and must never overwrite its front-weekly stats
            for d in dl:
                ostats[d] = res.get(d, {"error": "no rows for day in front expiry file"})
        except Exception as ex:  # noqa: BLE001
            for d in dl:
                ostats[d] = {"error": str(ex)}
        if (i + 1) % 25 == 0:
            log(f"  expiry file {i + 1}/{len(by_file)}")

    log("4/4 vix coverage + eligibility assembly...")
    v1m, vdaily = vix_dates()

    eligible, gaps = [], []
    for i, d in enumerate(days):
        s = sstats[d]
        reason = None
        if s["bars"] < MIN_SPOT_BARS:
            reason = f"spot bars {s['bars']} < {MIN_SPOT_BARS} (truncated/half day)"
        elif s["first_hm"] != 9 * 60 + 15:
            reason = "first bar not 09:15 (special session)"
        elif not s["has_1525"]:
            reason = "no spot bar at/after 15:25"
        elif front[d] is None:
            reason = "no expiry file >= day"
        elif i == 0 or sstats[days[i - 1]]["bars"] < MIN_SPOT_BARS:
            reason = "no valid previous trading day (D-1 chart)"
        elif i < 5:
            reason = "fewer than 5 prior sessions (prev-week levels)"
        elif d.isoformat() in ICONIC_BLACKLIST:
            reason = "iconic-day blacklist"
        elif d not in v1m and d not in vdaily:
            reason = "no VIX coverage (1min or daily)"
        else:
            o = ostats.get(d)
            if not o or "error" in o:
                reason = f"options scan failed: {o.get('error', 'no rows for day') if o else 'no rows for day'}"
            else:
                for side in ("CE", "PE"):
                    if o[side]["covered"] < MIN_STRIKES_COVERED:
                        reason = (f"{side} covered strikes {o[side]['covered']} < {MIN_STRIKES_COVERED}")
                        break
                    if o[side]["traded"] < MIN_STRIKES_TRADED:
                        reason = f"{side} traded strikes {o[side]['traded']} < {MIN_STRIKES_TRADED}"
                        break
        if reason:
            gaps.append({"date": d.isoformat(), "reason": reason})
        else:
            e = front[d]
            eligible.append({
                "date": d.isoformat(),
                "expiry": e.isoformat(),
                "expiry_file": efiles[e].name,
                "dte": (e - d).days,
                "spot_bars": s["bars"],
                "spot_open": s["open_0915"],
                "ce_covered": ostats[d]["CE"]["covered"],
                "pe_covered": ostats[d]["PE"]["covered"],
                "vix": "1min" if d in v1m else "daily",
                "lot_hist": lots["by_expiry"].get(e.isoformat()),
            })

    meta = {
        "built_at": pd.Timestamp.now(tz="Asia/Kolkata").isoformat(),
        "thresholds": {"MIN_SPOT_BARS": MIN_SPOT_BARS, "MIN_STRIKES_COVERED": MIN_STRIKES_COVERED,
                       "MIN_COVERAGE": MIN_COVERAGE, "MIN_STRIKES_TRADED": MIN_STRIKES_TRADED,
                       "STRIKE_WINDOW": STRIKE_WINDOW},
        "spot_days": len(days), "eligible": len(eligible), "excluded": len(gaps),
        "blacklist": sorted(ICONIC_BLACKLIST),
    }
    (OUT_DIR / "eligible_days.json").write_text(
        json.dumps({"meta": meta, "days": eligible}, indent=1), encoding="utf-8")
    (OUT_DIR / "coverage_gaps.json").write_text(
        json.dumps({"meta": meta, "gaps": gaps}, indent=1), encoding="utf-8")
    (OUT_DIR / "lot_sizes.json").write_text(json.dumps(lots, indent=1), encoding="utf-8")

    reasons = Counter(g["reason"].split("(")[0].split(":")[0].strip() for g in gaps)
    log(f"DONE in {time.time() - t0:.0f}s: {len(eligible)} eligible / {len(days)} spot days")
    for r, n in reasons.most_common():
        log(f"  excluded {n:4d}: {r}")


if __name__ == "__main__":
    sys.exit(main())
