"""VWAP + RSI intraday momentum, executed via ATM NIFTY weekly options (BUYING).
Owner: Arjun Rao (Quant). Task 2026-07-07.

Signal on 5-min NIFTY spot bars:
  VWAP  = session-cumulative EQUAL-WEIGHT typical-price avg ((H+L+C)/3), reset daily,
          causal (expanding mean up to & incl current bar).
          *** Spot-index volume is identically 0 in the dataset -> a true volume-weighted
          VWAP is impossible. Equal-weight session-anchored mean is the honest fallback.
          This is the single weakest assumption; documented in REPORT. ***
  RSI   = 14-period Wilder RSI on 5-min close (causal).
  LONG  = close > VWAP AND RSI bullish ; SHORT = close < VWAP AND RSI bearish.

Execution: 1-bar lag (signal at close of bar t -> ENTER at OPEN of bar t+1).
  LONG -> buy ATM CE, SHORT -> buy ATM PE. ATM = round(spot/50)*50.
  Expiry = nearest weekly with DTE>=1 (on expiry day roll to next week).
  Intraday only; force-flat at EOD (last bar <=15:25). No overnight.

Grid: RSI-def {A1:55/45, A2:60/40, A3:cross-50} x exit {B1:EOD, B2:underlying +30/-20,
  B3:trailing 30% off peak premium} = 9 cells. Reversed (fade) variant computed for all.

Costs: COST_STANDARDS.md (APPROVED D-021), options liquid ATM index.
Report: rupee-points (premium pts) + %-of-spot per trade. Never %-of-premium.
"""
from __future__ import annotations
import sys, json, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
import chain
import guards as G

OUT = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "VWAP_RSI_MOMENTUM_20260707"
TRADES = OUT / "trades"

# ---------------- config ----------------
STRIKE_STEP = 50
TICK = 0.05
RSI_N = 14
BAR = "5min"
SESSION_START = dt.time(9, 15)
SESSION_END = dt.time(15, 30)
LAST_ENTRY = dt.time(15, 0)      # no new entries after 15:00 (need room to hold + EOD flat)
EOD_FLAT = dt.time(15, 25)       # square off at/by this bar
TARGET_PTS = 30.0                # B2 underlying target (long sense)
STOP_PTS = 20.0                  # B2 underlying stop
TRAIL = 0.30                     # B3 trailing stop, frac off peak premium

RSI_DEFS = {
    "A1_55_45": ("level", 55, 45),
    "A2_60_40": ("level", 60, 40),
    "A3_cross50": ("cross", 50, 50),
}
EXITS = ["B1_EOD", "B2_uls_tgtstop", "B3_trail_prem"]


def lot_size(d: dt.date) -> int:
    # NIFTY lot: 50 pre-2024-11-20 SEBI revision, 75 after. (brokerage->points term only)
    return 75 if d >= dt.date(2024, 11, 20) else 50


# ---------------- indicators ----------------
def wilder_rsi(close: pd.Series, n: int = RSI_N) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    # Wilder smoothing = EMA with alpha=1/n, adjust=False
    au = up.ewm(alpha=1 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False).mean()
    rs = au / ad.replace(0.0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.where(ad != 0, 100.0)   # all-gains -> 100
    return rsi


def build_day_signals(bars: pd.DataFrame, rsi_kind, hi, lo) -> pd.DataFrame:
    """bars indexed by time (one trading day), cols o/h/l/c. Returns signal df."""
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3.0
    vwap = tp.expanding().mean()                 # equal-weight session-cumulative (vol=0)
    rsi = wilder_rsi(bars["close"], RSI_N)
    b = bars.copy()
    b["vwap"] = vwap
    b["rsi"] = rsi
    if rsi_kind == "level":
        bull = (b["close"] > b["vwap"]) & (b["rsi"] > hi)
        bear = (b["close"] < b["vwap"]) & (b["rsi"] < lo)
    else:  # cross of 50
        prev = b["rsi"].shift(1)
        up_cross = (prev <= 50) & (b["rsi"] > 50)
        dn_cross = (prev >= 50) & (b["rsi"] < 50)
        bull = (b["close"] > b["vwap"]) & up_cross
        bear = (b["close"] < b["vwap"]) & dn_cross
    b["sig"] = 0
    b.loc[bull, "sig"] = 1
    b.loc[bear, "sig"] = -1
    b.loc[b["rsi"].isna(), "sig"] = 0    # warmup: RSI undefined
    return b


# ---------------- option access ----------------
def resample_day_opts(day_chain_df: pd.DataFrame, lo_k: int, hi_k: int) -> dict:
    """Return {(strike,otype): df[o,h,l,c,vol] indexed by 5-min bar start} for strikes in range."""
    d = day_chain_df[(day_chain_df["strike"] >= lo_k) & (day_chain_df["strike"] <= hi_k)].copy()
    d = d[(d["t"].dt.time >= SESSION_START) & (d["t"].dt.time <= SESSION_END)]
    if d.empty:
        return {}
    out = {}
    d = d.set_index("t")
    for (k, ot), g in d.groupby(["strike", "option_type"]):
        r = g.resample(BAR, label="left", closed="left").agg(
            o=("open", "first"), h=("high", "max"), l=("low", "min"),
            c=("close", "last"), vol=("volume", "sum"))
        r = r.dropna(subset=["c"])
        r = r[r["vol"] > 0]              # only bars with a real print
        if not r.empty:
            out[(int(k), str(ot))] = r
    return out


def opt_price_at(opts: dict, strike: int, otype: str, bar_time, field: str):
    key = (strike, otype)
    if key not in opts:
        return None
    r = opts[key]
    if bar_time in r.index:
        v = r.at[bar_time, field]
        return float(v) if v == v else None
    return None


def opt_series_from(opts: dict, strike: int, otype: str, start_time):
    key = (strike, otype)
    if key not in opts:
        return None
    r = opts[key]
    return r[r.index >= start_time]


# ---------------- cost model (points) ----------------
def net_from_gross(entry_open, exit_px, ent_spot, lot, stress=1.0):
    slip_buy = max(TICK, 0.0025 * entry_open)
    slip_sell = max(TICK, 0.0025 * exit_px)
    brok = 2 * (20.0 / lot)
    exch = 0.00035 * (entry_open + exit_px)
    stt = 0.001 * exit_px
    stamp = 0.00003 * entry_open
    sebi = 1e-6 * (entry_open + exit_px)
    gst = 0.18 * (brok + exch + sebi)
    other = brok + exch + stt + stamp + sebi + gst
    gross = exit_px - entry_open
    net = gross - stress * (slip_buy + slip_sell) - stress * other
    return gross, net


# ---------------- one trade simulation ----------------
def simulate_position(direction, opts, sig_bars, entry_idx, ent_spot, exit_style, lot):
    """direction: +1 long(->CE) / -1 short(->PE). entry at OPEN of bar entry_idx.
    Returns dict or None (no fill)."""
    otype = "CE" if direction > 0 else "PE"
    strike = int(round(ent_spot / STRIKE_STEP) * STRIKE_STEP)
    entry_time = sig_bars.index[entry_idx]
    entry_open = opt_price_at(opts, strike, otype, entry_time, "o")
    if entry_open is None or entry_open <= 0:
        return None                                  # no liquid quote -> DROP (D-031)
    os_ = opt_series_from(opts, strike, otype, entry_time)
    if os_ is None or len(os_) < 1:
        return None
    # bars strictly after entry bar up to EOD
    hold = os_[os_.index > entry_time]
    # align to spot bars for underlying-based exit (B2)
    exit_px = None
    exit_time = None
    exit_reason = None
    peak = entry_open
    # iterate hold bars
    for bt, row in hold.iterrows():
        btime = bt.time()
        opt_c = row["c"]
        # underlying at this bar
        if bt in sig_bars.index:
            uh = sig_bars.at[bt, "high"]
            ul = sig_bars.at[bt, "low"]
        else:
            uh = ul = None
        # forced EOD (intraday square-off, applies to all exit styles)
        if btime >= EOD_FLAT:
            exit_px, exit_time, exit_reason = opt_c, bt, "EOD"
            break
        if exit_style == "B1_EOD":
            continue  # will exit at last bar (handled after loop / EOD branch)
        elif exit_style == "B2_uls_tgtstop":
            if uh is not None:
                if direction > 0:
                    hit_stop = ul <= ent_spot - STOP_PTS
                    hit_tgt = uh >= ent_spot + TARGET_PTS
                else:
                    hit_stop = uh >= ent_spot + STOP_PTS
                    hit_tgt = ul <= ent_spot - TARGET_PTS
                if hit_stop:            # stop assumed first if both
                    exit_px, exit_time, exit_reason = opt_c, bt, "stop"
                    break
                if hit_tgt:
                    exit_px, exit_time, exit_reason = opt_c, bt, "target"
                    break
        elif exit_style == "B3_trail_prem":
            peak = max(peak, opt_c)
            if opt_c <= peak * (1 - TRAIL):
                exit_px, exit_time, exit_reason = opt_c, bt, "trail"
                break
    if exit_px is None:
        # never triggered -> exit at last available hold bar (EOD flat)
        if len(hold) == 0:
            return None
        last = hold.iloc[-1]
        exit_px, exit_time, exit_reason = float(last["c"]), hold.index[-1], "EOD_last"
    gross, net = net_from_gross(entry_open, exit_px, ent_spot, lot, stress=1.0)
    _, net2x = net_from_gross(entry_open, exit_px, ent_spot, lot, stress=2.0)
    return dict(strike=strike, otype=otype, entry_time=entry_time, exit_time=exit_time,
                entry_prem=round(entry_open, 2), exit_prem=round(exit_px, 2),
                ent_spot=round(ent_spot, 2), exit_reason=exit_reason,
                gross_pts=round(gross, 3), net_pts=round(net, 3), net2x_pts=round(net2x, 3),
                gross_pct=gross / ent_spot, net_pct=net / ent_spot, net2x_pct=net2x / ent_spot)


def run_day(sig_bars, opts, exit_style, day, reverse=False):
    """State machine: one position at a time; re-enter after exit; force flat EOD."""
    trades = []
    lot = lot_size(day)
    n = len(sig_bars)
    i = 0
    while i < n - 1:
        sig = sig_bars["sig"].iloc[i]
        if sig != 0:
            entry_idx = i + 1                       # 1-bar lag
            if sig_bars.index[entry_idx].time() > LAST_ENTRY:
                break
            direction = int(sig)
            if reverse:
                direction = -direction              # fade the signal (still an option BUY)
            ent_spot = float(sig_bars["close"].iloc[entry_idx])  # spot at entry bar
            tr = simulate_position(direction, opts, sig_bars, entry_idx, ent_spot, exit_style, lot)
            if tr is not None:
                tr["day"] = day.isoformat()
                tr["dir"] = direction
                trades.append(tr)
                # jump to bar after exit to avoid overlap
                ex_t = tr["exit_time"]
                pos = sig_bars.index.get_indexer([ex_t])[0]
                i = max(pos + 1, i + 1)
                continue
        i += 1
    return trades


# ---------------- metrics ----------------
def cell_metrics(trades: pd.DataFrame, trading_days: int, colnet="net_pct", colpts="net_pts"):
    if trades.empty:
        return dict(N=0)
    r = trades[colnet].values
    pts = trades[colpts].values
    N = len(r)
    win = float((pts > 0).mean())
    gains = pts[pts > 0].sum()
    losses = -pts[pts <= 0].sum()
    pf = float(gains / losses) if losses > 0 else float("inf")
    # daily aggregate %spot for Sharpe (over ALL trading days, zeros on no-trade days)
    daily = trades.groupby("day")[colnet].sum()
    # build a proper daily series padded with zeros for no-trade days
    ser = np.concatenate([daily.values, np.zeros(max(0, trading_days - len(daily)))])
    sharpe = float(ser.mean() / (ser.std(ddof=1) + 1e-12) * np.sqrt(252)) if ser.std() > 0 else 0.0
    # equity in %spot units (additive), maxDD
    eq = np.cumsum(daily.sort_index().values)
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak)
    maxdd = float(dd.min()) if len(dd) else 0.0
    # per-trade
    ptmean = float(np.mean(pts))
    ptstd = float(np.std(pts, ddof=1)) if N > 1 else 0.0
    return dict(N=N, win=round(win, 3), PF=round(pf, 3),
                net_pts_mean=round(ptmean, 3), net_pts_std=round(ptstd, 3),
                net_pct_mean=round(float(np.mean(r)) * 100, 5),
                gross_pts_mean=round(float(trades["gross_pts"].mean()), 3),
                gross_pct_mean=round(float(trades["gross_pct"].mean()) * 100, 5),
                net2x_pts_mean=round(float(trades["net2x_pts"].mean()), 3),
                sharpe_ann=round(sharpe, 3), maxdd_pctspot=round(maxdd * 100, 4),
                total_net_pts=round(float(pts.sum()), 1))


# ---------------- main ----------------
def main():
    mapping, exps = chain.build_expiry_index()
    idx = chain.load_index()
    # spot 5-min bars per day
    idx = idx[(idx.index.time >= SESSION_START) & (idx.index.time <= SESSION_END)]
    idx = idx.copy()
    idx["day"] = idx.index.date
    print(f"[spot] {len(idx):,} 1-min bars, {idx['day'].nunique()} trading days")

    exps_arr = np.array(exps)

    def pick_expiry(day):
        cands = [e for e in exps if (e - day).days >= 1]
        return cands[0] if cands else None

    # collect trades: dict[(rsi_key, exit_key, reverse)] -> list
    from collections import defaultdict
    buckets = defaultdict(list)

    import os
    all_days = sorted(idx["day"].unique())
    _lim = os.environ.get("DAYS_LIMIT")
    if _lim:
        all_days = all_days[-int(_lim):]   # most-recent N days for smoke test
    trading_days = len(all_days)
    processed = 0
    skipped_noexp = 0
    skipped_nochain = 0
    for day in all_days:
        gsp = idx[idx["day"] == day]
        # resample spot to 5-min
        sig_base = gsp[["open", "high", "low", "close"]].resample(
            BAR, label="left", closed="left").agg(
            open=("open", "first"), high=("high", "max"),
            low=("low", "min"), close=("close", "last")).dropna()
        sig_base = sig_base[(sig_base.index.time >= SESSION_START) &
                            (sig_base.index.time <= SESSION_END)]
        if len(sig_base) < RSI_N + 3:
            continue
        exp = pick_expiry(day)
        if exp is None:
            skipped_noexp += 1
            continue
        try:
            dc = chain.day_chain(exp, day)
        except Exception:
            skipped_nochain += 1
            continue
        if dc.empty:
            skipped_nochain += 1
            continue
        G.assert_intraday_capable(dc)   # ensure minute schema
        spot_lo = sig_base["low"].min()
        spot_hi = sig_base["high"].max()
        lo_k = int((spot_lo - 300) // STRIKE_STEP * STRIKE_STEP)
        hi_k = int((spot_hi + 300) // STRIKE_STEP * STRIKE_STEP)
        opts = resample_day_opts(dc, lo_k, hi_k)
        if not opts:
            skipped_nochain += 1
            continue
        processed += 1
        for rkey, (kind, hi, lo) in RSI_DEFS.items():
            sig_bars = build_day_signals(sig_base, kind, hi, lo)
            # verify next-bar (L5): entries strictly after signal bar - by construction (i+1)
            for ekey in EXITS:
                for rev in (False, True):
                    trs = run_day(sig_bars, opts, ekey, day, reverse=rev)
                    buckets[(rkey, ekey, rev)].extend(trs)
    print(f"[proc] {processed} days processed, {skipped_noexp} no-expiry, {skipped_nochain} no-chain")

    # write per-cell csv + metrics
    rows = []
    for (rkey, ekey, rev), trs in sorted(buckets.items()):
        df = pd.DataFrame(trs)
        tag = f"{rkey}__{ekey}__{'REV' if rev else 'ORIG'}"
        if not df.empty:
            df.to_csv(TRADES / f"{tag}.csv", index=False)
        m = cell_metrics(df, trading_days) if not df.empty else dict(N=0)
        m.update(dict(rsi_def=rkey, exit=ekey, variant="REV" if rev else "ORIG"))
        rows.append(m)
    mdf = pd.DataFrame(rows)
    cols = ["rsi_def", "exit", "variant", "N", "win", "PF", "net_pts_mean", "net_pts_std",
            "net_pct_mean", "gross_pts_mean", "gross_pct_mean", "net2x_pts_mean",
            "sharpe_ann", "maxdd_pctspot", "total_net_pts"]
    mdf = mdf.reindex(columns=cols)
    mdf.to_csv(OUT / "grid_metrics.csv", index=False)
    print("\n=== GRID METRICS ===")
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(mdf.to_string(index=False))
    (OUT / "grid_metrics.json").write_text(mdf.to_json(orient="records", indent=1))
    print(f"\n[done] trading_days={trading_days}")


if __name__ == "__main__":
    main()
