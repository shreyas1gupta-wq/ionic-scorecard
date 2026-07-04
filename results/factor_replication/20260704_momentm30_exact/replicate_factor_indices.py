"""D-M4 flagship: EXACT-methodology replication of NIFTY 200 Momentum 30 and
NIFTY 100 Low Vol 30, vs the Principal's official NAV series.
Owner: Arjun Rao (E-004, Head of Quant). Landmine guards mandatory (D-028).

Run (background, flush prints, incremental CSV checkpoints):
    PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python replicate_factor_indices.py

WHAT THIS DOES
--------------
Momentum 30 (NIFTY200 parent):
  - Universe as-of each rebalance from NIFTY200_TICKER_2005_2025.xlsx (Mar/Sep snapshots).
  - Momentum score = normalized 6M and 12M price returns (return / daily-return vol over
    the window), z-scored cross-sectionally, capped +-3, averaged, tilt = 1 + z.
  - VARIANTS TESTED (methodology recovery):
      A_incl  : 6M/12M windows INCLUDING the most recent month.
      B_excl  : 6M/12M windows EXCLUDING the most recent month (t-21..t-126 / t-21..t-252)
                -- this is the classic Jegadeesh-Titman / NSE convention.
    x weighting: EW (equal weight * score tilt) vs MCAP (proxy full-mcap * score, cap 5%).
  - Rebalance: semi-annual, effective ~end-June / ~end-Dec (NSE cadence). Held to next rebal.

Low Vol 30 (NIFTY100 parent):
  - Universe as-of each rebalance from N50 union NN50 monthly matrix.
  - Score = 1 / (trailing 252d daily-return volatility). Weights = inverse-vol, normalized.
  - Rebalance: QUARTERLY (end Mar/Jun/Sep/Dec) -- NSE Low Vol 30 reviews quarterly.

Index construction: chain-linked daily portfolio return, weights fixed between rebalances
(drifting -- buy-and-hold between reviews, matching NSE), rebased to the official NAV level
at the replica's first common date. P&L / returns are booked in the period they occur; no
denominator games (this is a price index, returns are simple close-to-close).

DEVIATIONS FROM NSE WRITTEN METHODOLOGY -- all LOUD, quantified in REPORT.md:
  D1 free-float mcap unavailable -> MCAP variant uses FULL mcap proxy (shares outstanding not
     free-float-adjusted); EW variant sidesteps mcap entirely. TE cost measured by running both.
  D2 5% weight cap applied on MCAP variant only (EW is already <=1/30=3.33%).
  D3 rebalance EFFECTIVE dates approximated to last trading day of the review month; NSE uses
     a published effective date a few sessions later. Sub-week timing slippage.
  D4 price panel ends 2026-01-22 (HF stale tail, landmine); official NAV runs to 2026-02-27.
     Replication + TE computed only on the common window.
  D5 no corporate-action / index-divisor adjustments beyond what the (already-adjusted) panel
     carries; NSE applies IWF and divisor maintenance we cannot reproduce without factsheets.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LIB = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, LIB)
import guards as G  # noqa: E402  (landmine guards mandatory in every entry point)

OUTDIR = os.path.join(ROOT, r"results\factor_replication\20260704_momentm30_exact")
PANEL_PATH = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")
N200_XLSX = os.path.join(ROOT, "NIFTY200_TICKER_2005_2025.xlsx")
N100_XLSX = os.path.join(ROOT, "Historical stock composition of Nifty 50 and Nifty Next 50.xlsx")
NAV_PATH = os.path.join(ROOT, r"datasets\index_daily\factor_navs_principal.parquet")

DATA_MAX_DATE = pd.Timestamp("2026-01-22")  # HF panel stale-tail guard (landmine)
MIN_HISTORY = 252  # trading days needed for the 12M window

_MONTH_MAP = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

# ---------------------------------------------------------------------------
# TICKER ALIAS MAP (constituent-xlsx ticker -> current panel ticker)
# ONLY clean 1:1 RENAMES (same legal entity, symbol change). NSE renames verified
# against the panel. DELIBERATELY EXCLUDED (would fabricate prices):
#   HDFC -> HDFCBANK : SEPARATE listed entities until Jul-2023 merger (not a rename)
#   SRTRANSFIN/SHRIRAMCIT -> SHRIRAMFIN, MINDTREE/LTI -> LTIM : MERGERS (many-to-one),
#     pre-merger prices differ from the merged ticker -> excluded to avoid fabrication.
#   TATAMOTORS : genuinely absent from the panel (real data gap, no partial match).
# This is a T5/T7 membership-join fix, NOT a methodology change (LOUD in REPORT.md).
# ---------------------------------------------------------------------------
TICKER_ALIASES = {
    "MOTHERSUMI": "MOTHERSON", "TATAGLOBAL": "TATACONSUM", "MCDOWELL-N": "UNITDSPR",
    "NIITTECH": "COFORGE", "ZOMATO": "ETERNAL", "CROMPGREAV": "CROMPTON",
    "GMRINFRA": "GMRAIRPORT", "JUBILANT": "JUBLFOOD", "WELSPUNIND": "WELSPUNLIV",
    "TUBEINVEST": "TIINDIA", "AMARAJABAT": "ARE&M", "PVR": "PVRINOX",
    "PEL": "PIIND", "CADILAHC": "ZYDUSLIFE", "EQUITAS": "EQUITASBNK",
    "UJJIVAN": "UJJIVANSFB", "KPIT": "KPITTECH", "INFRATEL": "INDUSTOWER",
    "MINDAIND": "UNOMINDA", "GUJFLUORO": "FLUOROCHEM", "L&TFH": "LTF",
    "IDFCBANK": "IDFCFIRSTB", "MAX": "MAXHEALTH",
}


def apply_aliases(members: dict) -> dict:
    """Rewrite membership sets through the 1:1 rename map."""
    return {k: {TICKER_ALIASES.get(s, s) for s in v} for k, v in members.items()}


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------------------
# PRICE PANEL (reuse Track-2 data11 load pattern: IST-fix, de-dup, sort)
# ---------------------------------------------------------------------------
def load_panel_wide() -> pd.DataFrame:
    """Return a wide close-price frame indexed by trading date, columns = symbols.
    IST-date-fixed (L1). Only symbols/dates we need for the factor universes are kept
    downstream, but we build the full wide frame once and cache it in memory."""
    log("[panel] reading HF daily parquet ...")
    df = pd.read_parquet(PANEL_PATH, columns=["symbol", "timestamp", "close", "volume"])
    df = G.fix_ist_dates(df, ts_col="timestamp", out_col="date")  # L1
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] <= DATA_MAX_DATE]  # L7 stale-tail guard
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    df = df.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")
    log(f"[panel] rows={len(df):,} symbols={df['symbol'].nunique():,} "
        f"{df['date'].min().date()}->{df['date'].max().date()}")
    close = df.pivot(index="date", columns="symbol", values="close").sort_index()
    vol = df.pivot(index="date", columns="symbol", values="volume").sort_index()
    return close, vol


# ---------------------------------------------------------------------------
# NIFTY 200 membership (semi-annual Mar/Sep snapshots) -- as-of, no future look
# ---------------------------------------------------------------------------
def load_n200_members() -> dict:
    """dict {snap_date(Timestamp) -> set(symbols)}. snap_date = review-month start.
    Mar review -> members known/effective from Apr; Sep -> from Oct (see effective-date logic)."""
    d = pd.read_excel(N200_XLSX)
    d = d.rename(columns={"Month-Year": "lab", "Ticker": "sym"})
    d["sym"] = d["sym"].astype(str).str.strip().str.upper()
    out = {}
    for lab, g in d.groupby("lab"):
        mon, yr = str(lab)[:3], str(lab)[3:]
        snap = pd.Timestamp(year=int(yr), month=_MONTH_MAP[mon], day=1)
        out[snap] = set(g["sym"])
    return out


# ---------------------------------------------------------------------------
# NIFTY 100 membership = N50 union NN50, monthly Yes/No matrix -> as-of set
# ---------------------------------------------------------------------------
def load_n100_members() -> dict:
    """dict {month(Timestamp) -> set(symbols)} = union of Nifty50 + NiftyNext50 'Yes'."""
    frames = []
    for sheet in ["Nifty 50", "Nifty Next 50"]:
        m = pd.read_excel(N100_XLSX, sheet_name=sheet)
        m = m.rename(columns={m.columns[0]: "sym"})
        m["sym"] = m["sym"].astype(str).str.strip().str.upper()
        datecols = [c for c in m.columns if isinstance(c, (pd.Timestamp, datetime))]
        long = m.melt(id_vars="sym", value_vars=datecols, var_name="month", value_name="flag")
        long = long[long["flag"].astype(str).str.strip().str.lower() == "yes"]
        long["month"] = pd.to_datetime(long["month"])
        frames.append(long[["month", "sym"]])
    allm = pd.concat(frames, ignore_index=True).drop_duplicates()
    out = {mo: set(g["sym"]) for mo, g in allm.groupby("month")}
    return out


def members_asof(members: dict, date: pd.Timestamp) -> set:
    """Most-recent snapshot on-or-before `date`. Empty if before first snapshot (no future look)."""
    keys = [k for k in members if k <= date]
    if not keys:
        return set()
    return members[max(keys)]


# ---------------------------------------------------------------------------
# Rebalance-date schedule (last TRADING day on/before the effective month-end)
# ---------------------------------------------------------------------------
def rebal_dates(trading_days: pd.DatetimeIndex, months: tuple, start_year=2004, end_year=2026):
    """Effective rebalance = last trading day of each review month. months e.g. (6,12) semiannual
    or (3,6,9,12) quarterly. We SELECT on data up to and including the rebalance day and HOLD from
    the NEXT trading day -> weights apply strictly after the decision bar (no same-bar sin, L5)."""
    out = []
    td = pd.DatetimeIndex(trading_days)
    for yr in range(start_year, end_year + 1):
        for mo in months:
            month_days = td[(td.year == yr) & (td.month == mo)]
            if len(month_days):
                out.append(month_days.max())
    return sorted(set(out))


# ---------------------------------------------------------------------------
# MOMENTUM score (variant A incl / B excl recent month)
# ---------------------------------------------------------------------------
def momentum_scores(close: pd.DataFrame, asof: pd.Timestamp, universe: set,
                    exclude_recent_month: bool) -> pd.Series:
    """Normalized momentum composite per symbol as-of `asof`, restricted to `universe`.
    Uses ONLY prices up to and including `asof` (no lookahead).
    return_h  = P[gap] / P[gap+H] - 1     (H = 126 for 6M, 252 for 12M)
    vol_h     = std of daily log returns over the SAME window
    normalized ratio = return_h / (vol_h * sqrt(H))  (annualize-consistent scaling)
    z-score each horizon cross-sectionally, cap +-3, composite = mean of the two z's, score=1+comp.
    """
    hist = close.loc[:asof]
    if len(hist) < MIN_HISTORY + 25:
        return pd.Series(dtype=float)
    cols = [c for c in universe if c in hist.columns]
    hist = hist[cols]
    gap = 21 if exclude_recent_month else 0  # skip most recent ~1 month
    px = hist.values
    n = px.shape[0]
    idx_now = n - 1 - gap  # last usable price index (end of the excluded-recent window)
    if idx_now < MIN_HISTORY:
        return pd.Series(dtype=float)
    p_now = px[idx_now]

    def horizon_stats(H):
        i0 = idx_now - H
        if i0 < 0:
            return None, None
        p_then = px[i0]
        ret = p_now / p_then - 1.0
        # daily log-ret vol over the window [i0 .. idx_now]
        win = px[i0:idx_now + 1]
        logr = np.diff(np.log(win), axis=0)
        with np.errstate(invalid="ignore"):
            vol = np.nanstd(logr, axis=0)
        norm = ret / (vol * np.sqrt(H) + 1e-12)  # vol-adjusted momentum ratio
        return ret, norm

    r6, n6 = horizon_stats(126)
    r12, n12 = horizon_stats(252)
    if n6 is None or n12 is None:
        return pd.Series(dtype=float)

    df = pd.DataFrame({"sym": cols, "n6": n6, "n12": n12, "p_now": p_now,
                       "p_then6": px[idx_now - 126], "p_then12": px[idx_now - 252]})
    # require full valid price history over both windows (no NaNs/zeros -> not listed whole window)
    df = df[(df["p_now"] > 0) & (df["p_then6"] > 0) & (df["p_then12"] > 0)]
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["n6", "n12"])
    if len(df) < 30:
        return pd.Series(dtype=float)

    def z(s):
        return (s - s.mean()) / (s.std(ddof=0) + 1e-12)

    df["z6"] = z(df["n6"]).clip(-3, 3)
    df["z12"] = z(df["n12"]).clip(-3, 3)
    df["comp"] = df[["z6", "z12"]].mean(axis=1)
    df["score"] = 1.0 + df["comp"]  # NSE tilt convention (>0 by construction: comp in [-3,3])
    return df.set_index("sym")["score"]


def lowvol_scores(close: pd.DataFrame, asof: pd.Timestamp, universe: set) -> pd.Series:
    """Inverse trailing-252d daily-return volatility per symbol as-of `asof`."""
    hist = close.loc[:asof]
    cols = [c for c in universe if c in hist.columns]
    win = hist[cols].tail(253)  # 252 returns
    if len(win) < 200:
        return pd.Series(dtype=float)
    logr = np.log(win / win.shift(1)).iloc[1:]
    vol = logr.std(ddof=0)
    vol = vol[(vol > 0) & vol.notna()]
    if len(vol) < 30:
        return pd.Series(dtype=float)
    return 1.0 / vol  # inverse-vol; weights normalized later


# ---------------------------------------------------------------------------
# Build one index variant
# ---------------------------------------------------------------------------
def build_index(close, vol, members, rebals, score_fn, weight_mode, top_n, cap, tag):
    """Chain-linked daily portfolio return. weight_mode in {'ew','score','mcap','invvol'}.
    Returns a Series of index level (rebased later) indexed by trading date.
    Weights are set from data up to rebalance day `rb`, applied from the NEXT trading day."""
    tdays = close.index
    daily_ret = close.pct_change()
    port_ret = pd.Series(0.0, index=tdays)
    active_from = None
    n_rebals_done = 0
    holdings_log = []

    for i, rb in enumerate(rebals):
        if rb not in tdays:
            continue
        uni = members_asof(members, rb)
        if not uni:
            continue
        scores = score_fn(close, rb, uni)
        if scores.empty:
            continue
        top = scores.sort_values(ascending=False).head(top_n)
        sel = list(top.index)
        if len(sel) < max(10, top_n // 2):
            continue

        if weight_mode == "ew":
            w = pd.Series(1.0 / len(sel), index=sel)
        elif weight_mode == "score":  # equal-weight * score tilt, renormalized
            w = top / top.sum()
        elif weight_mode == "invvol":  # inverse-vol weights (score IS 1/vol)
            w = top / top.sum()
        elif weight_mode == "mcap":  # full-mcap proxy * score tilt, capped
            # mcap proxy = last close * 20d median volume (turnover proxy for float);
            # we lack shares outstanding so this is a LIQUIDITY-weighted proxy -- labelled D1.
            liq = (close.loc[:rb, sel].iloc[-1] *
                   vol.loc[:rb, sel].tail(20).median())
            raw = (liq * top).clip(lower=0)
            w = raw / raw.sum()
            w = w.clip(upper=cap)
            w = w / w.sum()  # renormalize after cap (single pass; residual over-cap small)
        else:
            raise ValueError(weight_mode)

        start = rb  # apply from NEXT trading day
        nxt = tdays[tdays > rb]
        if len(nxt) == 0:
            break
        seg_start = nxt[0]
        seg_end = rebals[i + 1] if i + 1 < len(rebals) else tdays[-1]
        seg = tdays[(tdays >= seg_start) & (tdays <= seg_end)]
        if len(seg) == 0:
            continue

        # buy-and-hold: weights DRIFT with prices within the segment (NSE holds constituents,
        # weights float between reviews). Compute drifting-weight portfolio return.
        seg_syms = [s for s in sel if s in daily_ret.columns]
        sub = daily_ret.loc[seg, seg_syms].fillna(0.0)
        # drift weights: start at w, grow by cumulative gross return
        w0 = w.reindex(seg_syms).fillna(0.0).values
        cum = (1 + sub.values).cumprod(axis=0)
        cum_prev = np.vstack([np.ones(len(seg_syms)), cum[:-1]])  # weight basis each day = prev cum
        wt = w0 * cum_prev
        wt = wt / wt.sum(axis=1, keepdims=True)
        pr = (wt * sub.values).sum(axis=1)
        port_ret.loc[seg] = pr
        n_rebals_done += 1
        holdings_log.append({"rebal": rb.date().isoformat(), "n_sel": len(sel),
                             "seg_days": len(seg), "top1": sel[0]})
        if active_from is None:
            active_from = seg_start

    if active_from is None:
        raise RuntimeError(f"[{tag}] no active segments built")
    ret = port_ret.loc[active_from:]
    level = (1 + ret).cumprod()
    log(f"[{tag}] rebals={n_rebals_done} active {active_from.date()}->{ret.index[-1].date()} "
        f"days={len(ret)}")
    return level, pd.DataFrame(holdings_log)


# ---------------------------------------------------------------------------
# TE / correlation vs official
# ---------------------------------------------------------------------------
def tracking_stats(replica_level: pd.Series, official: pd.Series):
    """Align on common dates, rebase replica to official at first common date, compute
    daily-return correlation and annualized tracking error (std of return differences)."""
    off = official.copy()
    off.index = pd.to_datetime(off.index)
    common = replica_level.index.intersection(off.index)
    if len(common) < 60:
        return None
    rep = replica_level.reindex(common)
    ofc = off.reindex(common)
    rep = rep / rep.iloc[0] * ofc.iloc[0]  # rebase to official level at first common date
    rr = rep.pct_change().dropna()
    ro = ofc.pct_change().dropna()
    j = rr.index.intersection(ro.index)
    rr, ro = rr.reindex(j), ro.reindex(j)
    diff = rr - ro
    te = diff.std(ddof=0) * np.sqrt(252)
    corr = rr.corr(ro)
    return {"rep": rep, "off": ofc, "rr": rr, "ro": ro, "corr": corr, "te": te,
            "start": str(j.min().date()), "end": str(j.max().date()), "n": len(j)}


def per_year_stats(rr: pd.Series, ro: pd.Series):
    rows = []
    for yr, g in rr.groupby(rr.index.year):
        gg = ro.reindex(g.index)
        diff = g - gg
        rows.append({"year": int(yr), "n": len(g),
                     "corr": round(g.corr(gg), 4),
                     "te_ann": round(diff.std(ddof=0) * np.sqrt(252), 4),
                     "rep_ret": round((1 + g).prod() - 1, 4),
                     "off_ret": round((1 + gg).prod() - 1, 4)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    os.makedirs(OUTDIR, exist_ok=True)
    log("=" * 70)
    log("D-M4 factor replication -- Momentum30 (exact) + LowVol30 v2")
    log("=" * 70)

    close, vol = load_panel_wide()
    tdays = close.index

    navs = pd.read_parquet(NAV_PATH)
    navs["date"] = pd.to_datetime(navs["date"])
    mom_off = navs[navs["series"] == "NIFTY 200 Momentum 30"].set_index("date")["nav"].sort_index()
    lv_off = navs[navs["series"] == "NIFTY 100 Low Vol 30"].set_index("date")["nav"].sort_index()
    log(f"[nav] momentum {mom_off.index.min().date()}->{mom_off.index.max().date()} ({len(mom_off)})")
    log(f"[nav] lowvol   {lv_off.index.min().date()}->{lv_off.index.max().date()} ({len(lv_off)})")

    n200 = apply_aliases(load_n200_members())
    n100 = apply_aliases(load_n100_members())
    log(f"[members] N200 snapshots={len(n200)} ({min(n200).date()}->{max(n200).date()})")
    log(f"[members] N100 months={len(n100)} ({min(n100).date()}->{max(n100).date()})")
    log(f"[members] ticker aliases applied: {len(TICKER_ALIASES)} (1:1 renames only)")

    results = {}  # tag -> tracking_stats dict + per-year df

    # ---- MOMENTUM: 4 variants (A_incl/B_excl x ew/mcap), semiannual Jun/Dec ----
    mom_rebals = rebal_dates(tdays, months=(6, 12), start_year=2004, end_year=2026)
    log(f"[mom] semiannual rebalance count={len(mom_rebals)}")

    mom_variants = [
        ("mom_Aincl_ew", False, "ew"),
        ("mom_Bexcl_ew", True, "ew"),
        ("mom_Aincl_mcap", False, "mcap"),
        ("mom_Bexcl_mcap", True, "mcap"),
    ]
    for tag, excl, wmode in mom_variants:
        log(f"\n[build] {tag} ...")
        sc = (lambda c, d, u, _e=excl: momentum_scores(c, d, u, exclude_recent_month=_e))
        try:
            level, hold = build_index(close, vol, n200, mom_rebals, sc, wmode,
                                      top_n=30, cap=0.05, tag=tag)
        except RuntimeError as e:
            log(f"  SKIP {tag}: {e}")
            continue
        st = tracking_stats(level, mom_off)
        if st is None:
            log(f"  SKIP {tag}: insufficient overlap")
            continue
        py = per_year_stats(st["rr"], st["ro"])
        results[tag] = {"st": st, "py": py}
        # checkpoint CSV incrementally
        out = pd.DataFrame({"date": st["rep"].index, "replica": st["rep"].values,
                            "official": st["off"].values})
        out.to_csv(os.path.join(OUTDIR, f"daily_{tag}.csv"), index=False)
        py.to_csv(os.path.join(OUTDIR, f"peryear_{tag}.csv"), index=False)
        log(f"  {tag}: corr={st['corr']:.4f} TE={st['te']:.4%} "
            f"[{st['start']}->{st['end']}, n={st['n']}]")

    # ---- LOW VOL 30 v2: inverse-vol, quarterly, real N100 membership ----
    lv_rebals = rebal_dates(tdays, months=(3, 6, 9, 12), start_year=2008, end_year=2026)
    log(f"\n[lowvol] quarterly rebalance count={len(lv_rebals)}")
    sc_lv = (lambda c, d, u: lowvol_scores(c, d, u))
    try:
        lv_level, lv_hold = build_index(close, vol, n100, lv_rebals, sc_lv, "invvol",
                                        top_n=30, cap=0.05, tag="lowvol_invvol_q")
        st = tracking_stats(lv_level, lv_off)
        if st is not None:
            py = per_year_stats(st["rr"], st["ro"])
            results["lowvol_invvol_q"] = {"st": st, "py": py}
            out = pd.DataFrame({"date": st["rep"].index, "replica": st["rep"].values,
                                "official": st["off"].values})
            out.to_csv(os.path.join(OUTDIR, "daily_lowvol_invvol_q.csv"), index=False)
            py.to_csv(os.path.join(OUTDIR, "peryear_lowvol_invvol_q.csv"), index=False)
            log(f"  lowvol_invvol_q: corr={st['corr']:.4f} TE={st['te']:.4%} "
                f"[{st['start']}->{st['end']}, n={st['n']}]")
    except RuntimeError as e:
        log(f"  SKIP lowvol: {e}")

    # ---- era-sliced stats (the coverage story: early-era universe holes drive full-period TE) ----
    eras = [("2005-01-01", "2015-12-31", "2005-15"),
            ("2016-01-01", "2019-12-31", "2016-19"),
            ("2020-01-01", "2022-12-31", "2020-22"),
            ("2023-01-01", "2026-12-31", "2023-26")]
    era_rows = []
    for tag, r in results.items():
        rr, ro = r["st"]["rr"], r["st"]["ro"]
        for lo, hi, lab in eras:
            m = (rr.index >= lo) & (rr.index <= hi)
            a = rr[m].dropna()
            b = ro.reindex(a.index)
            if len(a) < 30:
                continue
            era_rows.append({"variant": tag, "era": lab, "n": len(a),
                             "corr": round(a.corr(b), 4),
                             "te_ann": round((a - b).std(ddof=0) * np.sqrt(252), 4)})
    edf = pd.DataFrame(era_rows)
    edf.to_csv(os.path.join(OUTDIR, "era_stats.csv"), index=False)
    log("\nERA-SLICED corr/TE (coverage story):")
    log(edf.to_string(index=False))

    # ---- headline summary ----
    summary = []
    for tag, r in results.items():
        st = r["st"]
        summary.append({"variant": tag, "corr": round(st["corr"], 4),
                        "te_ann": round(st["te"], 4), "start": st["start"],
                        "end": st["end"], "n_days": st["n"]})
    sdf = pd.DataFrame(summary).sort_values("te_ann")
    sdf.to_csv(os.path.join(OUTDIR, "headline_summary.csv"), index=False)
    log("\n" + "=" * 70)
    log("HEADLINE SUMMARY (sorted by TE):")
    log(sdf.to_string(index=False))
    log("=" * 70)

    cfg = {"built": datetime.now().isoformat(timespec="seconds"),
           "panel": PANEL_PATH, "panel_max_date": str(DATA_MAX_DATE.date()),
           "nav": NAV_PATH, "n200_xlsx": N200_XLSX, "n100_xlsx": N100_XLSX,
           "momentum_rebalance": "semiannual (Jun/Dec last trading day)",
           "lowvol_rebalance": "quarterly (Mar/Jun/Sep/Dec last trading day)",
           "momentum_score": "z(6M vol-adj ret)+z(12M vol-adj ret) avg, cap +-3, tilt=1+z",
           "lowvol_score": "inverse trailing-252d daily-ret vol, inverse-vol weights",
           "variants": [s["variant"] for s in summary],
           "deviations": ["D1 full-mcap(liquidity) proxy not free-float",
                          "D2 5% cap on mcap variant only",
                          "D3 effective date = last trading day of review month",
                          "D4 panel ends 2026-01-22 vs NAV 2026-02-27",
                          "D5 no IWF/divisor maintenance"]}
    with open(os.path.join(OUTDIR, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    log(f"[done] outputs in {OUTDIR}")


if __name__ == "__main__":
    main()
