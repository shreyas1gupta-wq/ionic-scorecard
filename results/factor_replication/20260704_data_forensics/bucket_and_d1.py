"""D-M4 forensics ROUND 2: (A) three-bucket decomposition of missing early-era N200 members,
(B) D1-closure test using TRUE outstanding-shares mcap weights (2020+ window).
Owner: Arjun Rao (E-004).

Coordinator reframe: the HF panel is NOT shallow -- it is SURVIVORSHIP-HOLED. It has deep
backfilled history for TODAY's listed names (699 start <=2007) but NEVER contains names
delisted/merged before the dump date. So the early-era coverage gap = naming mismatches +
genuinely-absent delisted names, NOT missing depth.

TASK A -- for rebalances 2006/2010/2014, classify each N200-member-as-of that lacks a full
252d history in the HF panel into:
  NAMING          : the same company exists in HF under a DIFFERENT ticker (alias map + fuzzy)
  DELISTED-ABSENT : name is in Master/Delisted xlsx or raw/nifty500 but NOT in HF
  TRULY-ABSENT    : nowhere on disk (HF, Master, Delisted, raw/nifty500)

TASK B -- re-run mom_mcap for 2020+ with TRUE mcap = shares(from pkl) * close, cap 5%, vs the
liquidity-proxy mcap from D-M4; report TE/corr delta = the D1 deviation cost, now measured.

Run: PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python bucket_and_d1.py
"""
from __future__ import annotations

import glob
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LIB = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, LIB)
import guards as G  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, r"results\factor_replication\20260704_momentm30_exact"))
import replicate_factor_indices as R  # noqa: E402

OUT = os.path.join(ROOT, r"results\factor_replication\20260704_data_forensics")
HF_PANEL = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")
COMBINED = os.path.join(OUT, "_combined_master_delisted_close.parquet")  # from task2
PKL = os.path.join(ROOT, "stocks_data_cache.pkl")
NAV_PATH = os.path.join(ROOT, r"datasets\index_daily\factor_navs_principal.parquet")
DATA_MAX_DATE = pd.Timestamp("2026-01-22")


def log(*a):
    print(*a, flush=True)


# manual/fuzzy naming map BEYOND the 23 D-M4 aliases: old ticker -> HF ticker if same co.
# Only entries whose RHS actually exists in HF get counted as NAMING (checked at runtime).
EXTRA_NAMING = {
    "ABIRLANUVO": None,        # Aditya Birla Nuvo -> demerged/dissolved 2017; no single HF successor
    "ALSTOMT&D": "GET&D",      # Alstom T&D -> GE T&D India
    "ALSTOMT": "GET&D",
    "CADILAHC": "ZYDUSLIFE",   # already in D-M4 aliases (dup-safe)
    "CENTURYTEX": None,        # merged into Grasim (UltraTech cement biz) 2023 - no clean map
    "SSLT": "VEDL",            # Sesa Sterlite -> Vedanta
    "SESAGOA": "VEDL",
    "MCDOWELL-N": "UNITDSPR",
    "TATAGLOBAL": "TATACONSUM",
    "MOTHERSUMI": "MOTHERSON",
    "UNIPHOS": "UPL",
    "TELCO": "TATAMOTORS",     # will fail (TATAMOTORS not in HF) -> not counted
    "HEROHONDA": "HEROMOTOCO",
    "BAJAUTOFIN": "BAJFINANCE",
    "SESAGOA": "VEDL",
    "ISPATIND": None,
    "JSWSTEEL": "JSWSTEEL",
    "KOTAKMAH": "KOTAKBANK",
    "ZEETELE": "ZEEL",
    "GUJAMBCEM": "AMBUJACEM",
    "GRASIMBOND": None,
    "UTIBANK": "AXISBANK",     # UTI Bank -> Axis Bank
    "BHARTITELE": "BHARTIARTL",
    "GLAXO": "GLAXO",
    "IPCL": None,              # merged into Reliance
    "MICO": "BOSCHLTD",        # MICO -> Bosch
    "PNBGILTS": "PNBGILTS",
}


def hf_symbols() -> set:
    s = pd.read_parquet(HF_PANEL, columns=["symbol"])["symbol"].astype(str).str.strip().str.upper()
    return set(s.unique())


def hf_wide_close() -> pd.DataFrame:
    df = pd.read_parquet(HF_PANEL, columns=["symbol", "timestamp", "close"])
    df = G.fix_ist_dates(df, ts_col="timestamp", out_col="date")
    df["date"] = pd.to_datetime(df["date"]); df["symbol"] = df["symbol"].astype(str).str.upper()
    return df.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").sort_index()


def raw_nifty500_names() -> set:
    files = glob.glob(os.path.join(ROOT, r"raw\nifty500\*.csv"))
    return {os.path.basename(f)[:-4].strip().upper() for f in files}


def task_a():
    log("=" * 90)
    log("TASK A -- THREE-BUCKET DECOMPOSITION of missing early-era N200 members")
    log("=" * 90)
    hfw = hf_wide_close()
    hf_syms = set(hfw.columns)
    combined = pd.read_parquet(COMBINED)
    combined.index = pd.to_datetime(combined.index)
    combined_syms = {str(c).strip().upper() for c in combined.columns}
    raw500 = raw_nifty500_names()
    n200 = R.apply_aliases(R.load_n200_members())  # aliases already applied (23 D-M4 renames)

    # resolve extra naming map to only-those-present-in-HF
    naming_ok = {k: v for k, v in EXTRA_NAMING.items() if v and v in hf_syms}

    def missing_in_hf(rb, uni):
        out = []
        hist = hfw.loc[:rb]
        for u in uni:
            if u in hfw.columns:
                s = hist[u].dropna() if u in hist.columns else pd.Series(dtype=float)
                if len(s) >= 253 and (s.tail(253) > 0).all():
                    continue  # fully covered, not missing
            out.append(u)
        return out

    def classify(u, rb):
        # NAMING: same co under different ticker present (+full hist) in HF
        alt = naming_ok.get(u)
        if alt and alt in hfw.columns:
            hs = hfw.loc[:rb, alt].dropna()
            if len(hs) >= 253:
                return "NAMING", alt
        # DELISTED-ABSENT: present in master/delisted xlsx OR raw/nifty500 but not HF
        if u in combined_syms or u in raw500:
            return "DELISTED-ABSENT", ""
        return "TRULY-ABSENT", ""

    rows = []
    detail = []
    for p in ["2006-06-30", "2010-06-30", "2014-06-30"]:
        rb = hfw.index[hfw.index <= pd.Timestamp(p)].max()
        uni = R.members_asof(n200, rb)
        miss = missing_in_hf(rb, uni)
        cnt = {"NAMING": 0, "DELISTED-ABSENT": 0, "TRULY-ABSENT": 0}
        for u in miss:
            b, alt = classify(u, rb)
            cnt[b] += 1
            detail.append({"rebal": str(rb.date()), "missing_sym": u, "bucket": b, "hf_alt": alt})
        rows.append({"rebal": str(rb.date()), "uni": len(uni), "missing_total": len(miss),
                     **cnt})
        log(f"  {rb.date()}: uni={len(uni)} missing={len(miss)}  "
            f"NAMING={cnt['NAMING']} DELISTED-ABSENT={cnt['DELISTED-ABSENT']} "
            f"TRULY-ABSENT={cnt['TRULY-ABSENT']}")
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "taskA_bucket_counts.csv"), index=False)
    pd.DataFrame(detail).to_csv(os.path.join(OUT, "taskA_bucket_detail.csv"), index=False)
    log(f"  [saved] taskA_bucket_counts.csv + taskA_bucket_detail.csv")
    return pd.DataFrame(rows)


def task_b():
    log("\n" + "=" * 90)
    log("TASK B -- D1 CLOSURE: TRUE mcap (shares*close) vs liquidity-proxy, 2020+ window")
    log("=" * 90)
    with open(PKL, "rb") as f:
        cache = pickle.load(f)
    shares = {str(k).strip().upper(): float(v) for k, v in cache["shares"].items()
              if v and float(v) > 0}
    log(f"  shares available for {len(shares)} names")

    close, vol = R.load_panel_wide()  # HF panel wide close+vol (D-M4 loader)
    n200 = R.apply_aliases(R.load_n200_members())
    navs = pd.read_parquet(NAV_PATH); navs["date"] = pd.to_datetime(navs["date"])
    mom_off = navs[navs["series"] == "NIFTY 200 Momentum 30"].set_index("date")["nav"].sort_index()
    tdays = close.index
    rebals = R.rebal_dates(tdays, months=(6, 12), start_year=2004, end_year=2026)

    # custom build with TRUE mcap weights. Reuse momentum_scores; override weighting inline.
    def build_true_mcap(top_n=30, cap=0.05):
        daily_ret = close.pct_change()
        port = pd.Series(0.0, index=tdays)
        active = None
        for i, rb in enumerate(rebals):
            if rb not in tdays:
                continue
            uni = R.members_asof(n200, rb)
            if not uni:
                continue
            sc = R.momentum_scores(close, rb, uni, exclude_recent_month=False)
            if sc.empty:
                continue
            top = sc.sort_values(ascending=False).head(top_n)
            sel = [s for s in top.index if s in shares and s in close.columns]
            if len(sel) < 15:
                continue
            px = close.loc[:rb, sel].iloc[-1]
            mcap = pd.Series({s: shares[s] * float(px[s]) for s in sel})
            raw = (mcap * top.reindex(sel)).clip(lower=0)
            w = raw / raw.sum()
            w = w.clip(upper=cap); w = w / w.sum()
            nxt = tdays[tdays > rb]
            if len(nxt) == 0:
                break
            seg_start = nxt[0]
            seg_end = rebals[i + 1] if i + 1 < len(rebals) else tdays[-1]
            seg = tdays[(tdays >= seg_start) & (tdays <= seg_end)]
            if len(seg) == 0:
                continue
            sub = daily_ret.loc[seg, sel].fillna(0.0)
            w0 = w.reindex(sel).fillna(0.0).values
            cum = (1 + sub.values).cumprod(axis=0)
            cum_prev = np.vstack([np.ones(len(sel)), cum[:-1]])
            wt = w0 * cum_prev; wt = wt / wt.sum(axis=1, keepdims=True)
            port.loc[seg] = (wt * sub.values).sum(axis=1)
            if active is None:
                active = seg_start
        ret = port.loc[active:]
        return (1 + ret).cumprod()

    level_true = build_true_mcap()
    st_true = R.tracking_stats(level_true, mom_off)

    # compare on 2020+ window vs the D-M4 liquidity-proxy variant
    proxy = pd.read_csv(os.path.join(
        ROOT, r"results\factor_replication\20260704_momentm30_exact\daily_mom_Aincl_mcap.csv"),
        parse_dates=["date"]).set_index("date")

    def win_stats(rep, off, lo="2020-01-01"):
        common = rep.index.intersection(off.index)
        r = rep.reindex(common); o = off.reindex(common)
        r = r / r.iloc[0] * o.iloc[0]
        rr = r.pct_change(); ro = o.pct_change()
        m = rr.index >= pd.Timestamp(lo)
        a = rr[m].dropna(); b = ro.reindex(a.index)
        return a.corr(b), (a - b).std(ddof=0) * np.sqrt(252), len(a)

    off = mom_off.copy(); off.index = pd.to_datetime(off.index)
    c_true, te_true, n_true = win_stats(level_true, off)
    # proxy already rebased vs official in its CSV; recompute 2020+ from stored series
    prr = proxy["replica"].pct_change(); pro = proxy["official"].pct_change()
    mp = prr.index >= pd.Timestamp("2020-01-01")
    pa = prr[mp].dropna(); pb = pro.reindex(pa.index)
    c_proxy, te_proxy = pa.corr(pb), (pa - pb).std(ddof=0) * np.sqrt(252)

    log(f"  2020+ TRUE-mcap  : corr={c_true:.4f} TE={te_true:.4%} n={n_true}")
    log(f"  2020+ proxy-mcap : corr={c_proxy:.4f} TE={te_proxy:.4%}")
    log(f"  D1 CLOSURE DELTA : dTE={te_true - te_proxy:+.4%}  dcorr={c_true - c_proxy:+.4f}")
    out = pd.DataFrame({"date": level_true.index, "replica_true_mcap": level_true.values})
    out.to_csv(os.path.join(OUT, "taskB_true_mcap_daily.csv"), index=False)
    cfg = {"shares_names": len(shares),
           "true_mcap_2020plus": {"corr": round(c_true, 4), "te": round(te_true, 4)},
           "proxy_mcap_2020plus": {"corr": round(c_proxy, 4), "te": round(te_proxy, 4)},
           "d1_delta_te": round(te_true - te_proxy, 4), "d1_delta_corr": round(c_true - c_proxy, 4)}
    with open(os.path.join(OUT, "taskB_d1_closure.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    a = task_a()
    b = task_b()
    log("\n[done] round-2 forensics (bucket + D1) written.")
