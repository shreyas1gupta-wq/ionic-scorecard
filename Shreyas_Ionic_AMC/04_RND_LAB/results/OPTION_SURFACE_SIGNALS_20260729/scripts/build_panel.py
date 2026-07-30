"""
Build the daily option-surface feature panel for the NEW-IDEA option-surface-signals
exploration (Ishaan Gupta, 2026-07-29). See PREREGISTRATION.md for exact definitions.

Outputs (this dir's parent /panel):
  panel_raw.parquet   - one row per usable trading day, all raw IV/OI/spot fields
  oi_coverage.csv      - OI-populated-fraction by year, near-ATM band only (Candidate 3 gate)
  build_log.txt        - progress + drop-reason counts

Run: python build_panel.py  (writes as it goes, safe to inspect mid-run)
"""
import sys, time, gc, datetime as dt
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(REPO / "intraday_options_strategy" / "buying"))
import chain as nchain  # NIFTY chain helpers (reused per firm rule: don't rewrite)

from vollib.black_scholes.implied_volatility import implied_volatility as bs_iv

OUT = REPO / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "OPTION_SURFACE_SIGNALS_20260729"
LOG = open(OUT / "build_log.txt", "a", encoding="utf-8")

def log(msg):
    line = f"[{dt.datetime.now():%H:%M:%S}] {msg}"
    print(line)
    LOG.write(line + "\n")
    LOG.flush()

R = 0.065  # flat risk-free, per pre-registration
IV_LO, IV_HI = 0.01, 1.00  # sanity cap (Lesson 2026-07 INFY IV=133% blowup)

BN_BASE = REPO / "intraday_options_strategy" / "datasets" / "raw" / "hf_index_options_1m"
BN_OPT_DIR = BN_BASE / "options" / "BANKNIFTY"
BN_INDEX = BN_BASE / "index" / "BANKNIFTY.parquet"


# ---------- BANKNIFTY equivalents of chain.py (index-parameterized, not touching original) ----------
@lru_cache(maxsize=1)
def bn_build_expiry_index():
    mapping = {}
    for p in BN_OPT_DIR.glob("*.parquet"):
        try:
            mapping[dt.datetime.strptime(p.stem, "%Y-%m-%d").date()] = p
        except ValueError:
            continue
    exps = sorted(mapping)
    log(f"[bn_chain] {len(exps)} BANKNIFTY expiries {exps[0]}..{exps[-1]}")
    return mapping, exps


def bn_load_expiry(exp):
    # NOT lru_cached: raw df is large; the caller (bn_snap_by_day) is the cache layer and
    # only needs this transiently to build its small aggregate. Memory-constrained box
    # (several other python jobs running concurrently) blew up with two cache layers stacked.
    mapping, _ = bn_build_expiry_index()
    df = pq.read_table(mapping[exp]).to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df["trading_day"] = df["trading_day"].astype(str)
    return df


def bn_nearest_expiry(day, min_dte=0, max_dte=35):
    _, exps = bn_build_expiry_index()
    cands = [e for e in exps if min_dte <= (e - day).days <= max_dte]
    return cands[0] if cands else None


@lru_cache(maxsize=1)
def bn_load_index():
    df = pq.read_table(BN_INDEX).to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.drop_duplicates("t").set_index("t").sort_index()
    return df[["open", "high", "low", "close"]]


# ---------- snapshot window ----------
# WIDENED 2026-07-29 09:20-09:30 -> 09:15-11:00, BEFORE any predictive test was run (coverage-only
# decision, verified by inspecting raw ticks on 2022-03-15's E2 leg: only ONE deep-ITM strike (13000 PE)
# printed in the original 09:20-09:30 window -- next-week/monthly options are genuinely thin at the
# open; this is a real liquidity fact, not a bug. Original narrow window gave 0% NaN on the E1 skew
# leg but 74%/90% NaN on ts_near/ts_far respectively. Same widened window applied uniformly to ALL
# legs (E1/E2/Em/BANKNIFTY/PCR/spot) for a same-epoch comparison, not selectively to "fix" one number.
SNAP_START_MIN, SNAP_END_MIN = 9 * 60 + 15, 11 * 60  # 09:15..11:00 inclusive


def _snap_mask(df):
    mins = df["t"].dt.hour * 60 + df["t"].dt.minute
    return (mins >= SNAP_START_MIN) & (mins <= SNAP_END_MIN)


# ---------- snapshot per-expiry cache: build once per expiry file ----------
# IMPORTANT (memory): this box runs several other python jobs concurrently and blew up an
# ArrayMemoryError when both this cache AND chain.py's internal load_expiry lru_cache(64) held
# full raw dfs (300-600k rows) at once. Fix: this is the ONLY long-lived cache (small, aggregated
# to strike/day/type); the raw df is discarded (and chain.py's cache forcibly cleared) right after
# use, every call, so at most ONE raw df is ever resident.
# CACHE SIZES CUT HARD 2026-07-29: box has only ~1.7GB free system-wide (other jobs running) and a
# wider snapshot window (more rows/day to aggregate) segfaulted with maxsize=24/12. 6/3 is still more
# than the ~3-4 expiries ever concurrently in flight (E1, E2, Em, +occasional BANKNIFTY-DTE-matched leg).
@lru_cache(maxsize=6)
def nifty_snap_by_day(exp):
    df = nchain.load_expiry(exp)
    win = df[_snap_mask(df)]
    g = win.groupby(["trading_day", "strike", "option_type"]).agg(
        px=("close", "mean"), oi=("open_interest", "max")
    ).reset_index()
    g["px"] = g["px"].astype("float32")
    g["oi"] = g["oi"].astype("int32")
    out = {day: sub for day, sub in g.groupby("trading_day")}
    del df, win, g
    nchain.load_expiry.cache_clear()
    gc.collect()
    return out


@lru_cache(maxsize=3)
def bn_snap_by_day(exp):
    df = bn_load_expiry(exp)
    win = df[_snap_mask(df)]
    g = win.groupby(["trading_day", "strike", "option_type"]).agg(
        px=("close", "mean"), oi=("open_interest", "max")
    ).reset_index()
    g["px"] = g["px"].astype("float32")
    g["oi"] = g["oi"].astype("int32")
    out = {day: sub for day, sub in g.groupby("trading_day")}
    del df, win, g
    gc.collect()
    return out


def nearest_strike_iv(sub, target_strike, opt_type, spot, T, want="single"):
    """sub: day-snapshot df (strike, option_type, px, oi). Returns (iv, strike_used, px) or None."""
    cand = sub[sub["option_type"] == opt_type]
    if cand.empty or T <= 0:
        return None
    cand = cand.assign(dist=(cand["strike"] - target_strike).abs()).sort_values("dist")
    row = cand.iloc[0]
    px, K = float(row["px"]), float(row["strike"])
    if px <= 0:
        return None
    flag = "c" if opt_type == "CE" else "p"
    try:
        iv = bs_iv(px, spot, K, T, R, flag)
    except Exception:
        return None
    if not (IV_LO < iv < IV_HI):
        return None
    return iv, K, px


def atm_iv(sub, spot, T):
    """Average call+put IV at the strike nearest spot; falls back to whichever side is sane."""
    strikes = sub["strike"].unique()
    if len(strikes) == 0:
        return None
    k_atm = strikes[np.argmin(np.abs(strikes - spot))]
    c = nearest_strike_iv(sub, k_atm, "CE", spot, T)
    p = nearest_strike_iv(sub, k_atm, "PE", spot, T)
    ivs = [x[0] for x in (c, p) if x is not None]
    if not ivs:
        return None
    return float(np.mean(ivs)), k_atm


def main():
    t0 = time.time()
    idx = nchain.load_index()  # NIFTY spot, naive IST index
    bn_idx = bn_load_index()

    # daily close (last bar) + snapshot (09:20-09:30 mean) for both indices
    def daily_series(df):
        d = df.copy()
        d["day"] = d.index.date
        close_d = d.groupby("day")["close"].last()
        mins = d.index.hour * 60 + d.index.minute
        snap = d[(mins >= SNAP_START_MIN) & (mins <= SNAP_END_MIN)]
        snap_d = snap.groupby(snap.index.date)["close"].mean()
        return close_d, snap_d

    n_close, n_snap = daily_series(idx[idx.index.time >= dt.time(9, 15)])
    b_close, b_snap = daily_series(bn_idx[bn_idx.index.time >= dt.time(9, 15)])

    mapping, nifty_exps = nchain.build_expiry_index()
    bn_mapping, bn_exps = bn_build_expiry_index()

    days = sorted(set(n_snap.index) & set(n_close.index))
    log(f"total NIFTY trading days candidate: {len(days)} ({days[0]}..{days[-1]})")

    # RESUME support (2026-07-29): box has ~1.7GB free RAM system-wide and this job has segfaulted
    # once already under contention from other jobs. Segfaults are not catchable in Python, so the
    # defense is checkpoint + resume, not try/except. If a partial panel from THIS run exists, skip
    # the days already in it.
    rows = []
    done_days = set()
    partial_path = OUT / "panel_partial_v2.parquet"
    if partial_path.exists():
        prev = pd.read_parquet(partial_path)
        rows = prev.to_dict("records")
        done_days = set(prev["day_str"])
        log(f"RESUMING: {len(rows)} rows already done, skipping those days")

    drops = {"no_E1": 0, "no_spot": 0, "no_atm_E1": 0, "no_bn": 0, "error": 0}
    for i, day in enumerate(days):
        if day.isoformat() in done_days:
            continue
        if i % 100 == 0:
            log(f"...{i}/{len(days)} days processed, elapsed {time.time()-t0:.0f}s, rows so far {len(rows)}")
        if i % 100 == 0 and rows:
            pd.DataFrame(rows).to_parquet(partial_path)
            gc.collect()
        try:
            _process_one_day(day, n_snap, nifty_exps, b_snap, drops, rows)
        except Exception as e:
            drops["error"] += 1
            log(f"ERROR on day {day}: {type(e).__name__}: {e}")
            continue
    pd.DataFrame(rows).to_parquet(partial_path)
    _finish(rows, drops, n_close, b_close, t0)


def _process_one_day(day, n_snap, nifty_exps, b_snap, drops, rows):
        day_str = day.isoformat()
        spot = n_snap.get(day)
        if spot is None or np.isnan(spot):
            drops["no_spot"] += 1
            return

        E1 = nchain.nearest_expiry(day, 2, 9)
        if E1 is None:
            drops["no_E1"] += 1
            return
        E2 = nchain.nearest_expiry(day, 10, 16)
        Em = nchain.nearest_expiry(day, 21, 35)

        snap1 = nifty_snap_by_day(E1).get(day_str)
        if snap1 is None or snap1.empty:
            drops["no_atm_E1"] += 1
            return
        T1 = (E1 - day).days / 365.0

        a1 = atm_iv(snap1, spot, T1)
        if a1 is None:
            drops["no_atm_E1"] += 1
            return
        atm1_iv, atm1_k = a1

        # --- Candidate 1: fixed-strike-distance skew on E1 ---
        put_target, call_target = 0.98 * spot, 1.02 * spot
        pr = nearest_strike_iv(snap1, put_target, "PE", spot, T1)
        cr = nearest_strike_iv(snap1, call_target, "CE", spot, T1)
        skew = pr[0] - cr[0] if (pr and cr) else np.nan
        put_iv = pr[0] if pr else np.nan
        call_iv = cr[0] if cr else np.nan

        # --- Candidate 2: term structure ---
        ts_near = ts_far = np.nan
        atm2_iv = atmm_iv = np.nan
        if E2 is not None:
            snap2 = nifty_snap_by_day(E2).get(day_str)
            if snap2 is not None and not snap2.empty:
                T2 = (E2 - day).days / 365.0
                a2 = atm_iv(snap2, spot, T2)
                if a2:
                    atm2_iv = a2[0]
                    ts_near = atm2_iv - atm1_iv
        if Em is not None:
            snapm = nifty_snap_by_day(Em).get(day_str)
            if snapm is not None and not snapm.empty:
                Tm = (Em - day).days / 365.0
                am = atm_iv(snapm, spot, Tm)
                if am:
                    atmm_iv = am[0]
                    ts_far = atmm_iv - atm1_iv

        # --- Candidate 3: OI near-ATM band on E1 (+/-10%) ---
        band = snap1[(snap1["strike"] >= 0.90 * spot) & (snap1["strike"] <= 1.10 * spot)]
        oi_pe = band.loc[band["option_type"] == "PE", "oi"].sum()
        oi_ce = band.loc[band["option_type"] == "CE", "oi"].sum()
        pcr = (oi_pe / oi_ce) if oi_ce > 0 else np.nan

        # --- Candidate 4: NIFTY-BANKNIFTY IV spread ---
        bn_spot = b_snap.get(day)
        ivspread = np.nan
        bn_atm_iv = np.nan
        nifty_matched_iv = np.nan
        if bn_spot is not None and not np.isnan(bn_spot):
            E_bn = bn_nearest_expiry(day, 0, 35)
            if E_bn is not None:
                bn_snap = bn_snap_by_day(E_bn).get(day_str)
                if bn_snap is not None and not bn_snap.empty:
                    Tbn = max((E_bn - day).days, 1) / 365.0
                    a_bn = atm_iv(bn_snap, bn_spot, Tbn)
                    if a_bn:
                        bn_atm_iv = a_bn[0]
                        dte_bn = (E_bn - day).days
                        # NIFTY expiry with DTE closest to BANKNIFTY leg's DTE
                        cands = [e for e in nifty_exps if -3 <= (e - day).days <= 40]
                        if cands:
                            e_match = min(cands, key=lambda e: abs((e - day).days - dte_bn))
                            sm = nifty_snap_by_day(e_match).get(day_str)
                            if sm is not None and not sm.empty:
                                Tm2 = max((e_match - day).days, 1) / 365.0
                                a_m = atm_iv(sm, spot, Tm2)
                                if a_m:
                                    nifty_matched_iv = a_m[0]
                                    ivspread = bn_atm_iv - nifty_matched_iv
        if bn_spot is None or np.isnan(bn_spot):
            drops["no_bn"] += 1

        rows.append(dict(
            day=day, day_str=day_str, spot=spot, bn_spot=bn_spot,
            E1=E1, E2=E2, Em=Em, dte1=(E1 - day).days,
            dte2=(E2 - day).days if E2 else np.nan, dtem=(Em - day).days if Em else np.nan,
            atm1_iv=atm1_iv, atm1_k=atm1_k, atm2_iv=atm2_iv, atmm_iv=atmm_iv,
            skew=skew, put_iv=put_iv, call_iv=call_iv,
            ts_near=ts_near, ts_far=ts_far,
            oi_pe=oi_pe, oi_ce=oi_ce, pcr=pcr,
            bn_atm_iv=bn_atm_iv, nifty_matched_iv=nifty_matched_iv, ivspread=ivspread,
        ))


def _finish(rows, drops, n_close, b_close, t0):
    panel = pd.DataFrame(rows)
    log(f"panel rows: {len(panel)}  drops: {drops}")
    panel.to_parquet(OUT / "panel_raw.parquet")
    log(f"wrote {OUT/'panel_raw.parquet'}  shape={panel.shape}")

    # forward daily-close series for targets (attach separately, saved alongside)
    n_close.rename("nifty_close").to_frame().to_parquet(OUT / "nifty_daily_close.parquet")
    b_close.rename("bn_close").to_frame().to_parquet(OUT / "bn_daily_close.parquet")

    # --- OI coverage-by-year gate for Candidate 3 (near-ATM band, the moneyness that matters for PCR) ---
    cov = panel.assign(year=panel["day"].map(lambda d: d.year))
    cov_stats = cov.groupby("year").apply(
        lambda g: pd.Series({
            "n_days": len(g),
            "frac_oi_ce_zero": (g["oi_ce"] == 0).mean(),
            "frac_oi_pe_zero": (g["oi_pe"] == 0).mean(),
            "frac_pcr_nan": g["pcr"].isna().mean(),
        }), include_groups=False
    )
    cov_stats.to_csv(OUT / "oi_coverage.csv")
    log(f"wrote {OUT/'oi_coverage.csv'}\n{cov_stats}")
    log(f"DONE in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
