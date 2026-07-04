"""D-029 factor family: SIX factor indices, MONTHLY rebalanced, frictionless + cost-loaded.
Owner: Arjun Rao (E-004). Landmine guards + D-028 mandatory.

SIX INDICES (Principal spec, MONTHLY rebalance):
  1. Smallcap Momentum-Quality 100   (SMALL = N500 minus N200, MQ top100) vs 'Nifty Smallcap250 Momentum Quality 100'
  2. Smallcap Momentum-Quality 25    (SMALL, MQ top25) -- novel concentrated
  3. N500 Momentum-Quality 50        (N500, MQ top50)  vs 'Nifty500 Multicap Momentum Quality 50'
  4. N500 LowVol 50                  (N500, 252d vol rank, inverse-vol wts, top50)
  5. Smallcap LowVol 25              (SMALL, lowvol top25)
  6. MidSmallcap Momentum-Quality 30 (MID+SMALL = N500 minus N100, MQ top30) vs 'Nifty MidSmallcap400 Momentum Quality 100' (loose cousin, sanity only)

REBALANCE: MONTHLY (last trading day each month), held to next month, drifting weights.
  NSE NOTE (fairness): the official MQ/momentum indices rebalance SEMIANNUAL, lowvol QUARTERLY.
  Our monthly cadence is the Principal's strategy spec, NOT the index methodology -> replication
  corr/TE for #1,#3 are computed but the rebalance-frequency mismatch is a KNOWN, STATED source
  of tracking error (monthly picks up/sheds names the official index would hold through).

SCORES:
  momentum = 6M+12M vol-adjusted z composite (engine momentum_scores, B_excl, UNCHANGED).
  quality  = z(ROE) + z(-DE) + z(profit-growth stability), 1/3 each, from quality_pit.parquet
             (PIT: use most-recent fy row with avail_date <= rebalance date; T+90 fence).
  MQ       = 0.5*z(momentum_composite) + 0.5*z(quality_composite)  (NSE 50/50 convention).
  Names with NO quality data -> MQ falls back to momentum-only for that name; per-index yearly
  quality-coverage % is logged; coverage<40% years marked INDICATIVE-ONLY.
  lowvol   = inverse trailing-252d daily-ret vol; inverse-vol weights.

PANELS (frozen copies, md5-verified):
  PRICE panel  (union_rerun copy) -> index construction + official comparison + momentum/vol scores.
  RETURN panel (this-dir copy)    -> cost-loaded STRATEGY NAV daily returns (survivorship-complete,
                                     gap-free per-stock returns are what a strategy P&L wants).
  volume: HF (for the cost-loaded volume-conditional slippage multiplier).

COSTS (COST_STANDARDS APPROVED + execution_realism): turnover-based per rebalance.
  round-trip per traded weight = 2*(slippage_tier_bps * vol_mult) + 2*STT(10bps) + 2*exch(0.297bps)
      + 2*stamp(1.5bps buy only ->1.5) + brokerage(Rs20/order, modeled as bps on per-name notional)
      + GST on (brokerage+exch+sebi). Applied to one-way turnover each month (buy+sell netted per name).
  slippage tier by segment: SMALL/MidSmall=35bps, N500-blend=22bps (cap-weighted mix large/mid/small).
  vol_mult: fraction of rebalance names on thin/no-volume days scales the tier (execution_realism).
  Promotion test: also compute NAV at 2x ALL costs (RESEARCH_SOP gate 7).
"""
from __future__ import annotations
import os, sys, json
from datetime import datetime
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LIB = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, LIB)
import guards as G  # noqa: E402
import execution_realism as EX  # noqa: E402
ENGINE = os.path.join(ROOT, r"results\factor_replication\20260704_momentm30_exact")
sys.path.insert(0, ENGINE)
import replicate_factor_indices as R  # noqa: E402  (engine imported UNCHANGED)

OUT = os.path.join(ROOT, r"results\factor_replication\20260704_factor_family")
PRICE_PANEL = os.path.join(ROOT, r"results\factor_replication\20260704_union_rerun\close_panel_price.parquet")
RETURN_PANEL = os.path.join(OUT, "close_panel_return.parquet")
HF_PANEL = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")
QUALITY = os.path.join(OUT, "quality_pit.parquet")
NAV_PATH = os.path.join(ROOT, r"datasets\index_daily\factor_navs_principal.parquet")
ARCH_PATH = os.path.join(ROOT, r"datasets\index_daily\nse_official_all_indices.parquet")
N200_XLSX = os.path.join(ROOT, "NIFTY200_TICKER_2005_2025.xlsx")
N500_XLSX = os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx")

DATA_MAX = pd.Timestamp("2026-01-22")
TD = 252
# cost params (COST_STANDARDS, one-way bps of traded value unless noted)
STT_BPS = 10.0            # 0.1% delivery each side
EXCH_BPS = 0.297          # 0.00297%
STAMP_BUY_BPS = 1.5       # 0.015% buy side only
SEBI_BPS = 0.01          # Rs10/cr = 0.0001% = 0.01bps
BROKERAGE_PER_NAME_BPS = 0.0  # Rs20/order; on ~Rs-lakh per-name index slice this is <1bp; folded via GST-small, set 0 and note
GST = 0.18
SLIP_TIER = {"small": 35.0, "midsmall": 35.0, "n500": 22.0}


def log(*a): print(*a, flush=True)


def load_price_return_vol():
    up = pd.read_parquet(PRICE_PANEL, columns=["date", "symbol", "close"])
    up["date"] = pd.to_datetime(up["date"]); up["symbol"] = up["symbol"].str.strip().str.upper()
    up = up[(up["date"] <= DATA_MAX) & (up["close"] > 0)]
    up = up.drop_duplicates(["symbol", "date"], keep="last")
    price = up.pivot(index="date", columns="symbol", values="close").sort_index()

    rp = pd.read_parquet(RETURN_PANEL, columns=["date", "symbol", "close"])
    rp["date"] = pd.to_datetime(rp["date"]); rp["symbol"] = rp["symbol"].str.strip().str.upper()
    rp = rp[(rp["date"] <= DATA_MAX) & (rp["close"] > 0)]
    rp = rp.drop_duplicates(["symbol", "date"], keep="last")
    ret_close = rp.pivot(index="date", columns="symbol", values="close").sort_index()

    hf = pd.read_parquet(HF_PANEL, columns=["symbol", "timestamp", "volume"])
    hf = G.fix_ist_dates(hf, ts_col="timestamp", out_col="date")
    hf["date"] = pd.to_datetime(hf["date"]); hf["symbol"] = hf["symbol"].str.strip().str.upper()
    hf = hf[hf["date"] <= DATA_MAX].drop_duplicates(["symbol", "date"], keep="last")
    vol = hf.pivot(index="date", columns="symbol", values="volume").sort_index()
    vol = vol.reindex(index=price.index, columns=price.columns)
    log(f"[panel] price {price.shape} return {ret_close.shape} vol-cov "
        f"{vol.notna().any().mean():.1%}")
    return price, ret_close, vol


def load_members(xlsx):
    d = pd.read_excel(xlsx).rename(columns={"Month-Year": "lab", "Ticker": "sym"})
    d["sym"] = d["sym"].astype(str).str.strip().str.upper()
    out = {}
    for lab, g in d.groupby("lab"):
        mon, yr = str(lab)[:3], str(lab)[3:]
        out[pd.Timestamp(year=int(yr), month=R._MONTH_MAP[mon], day=1)] = set(g["sym"])
    return out


def seg_members(a_members, b_members):
    """a minus b, snapshot-by-snapshot (as-of union of snapshot dates)."""
    keys = sorted(set(a_members) | set(b_members))
    out = {}
    for k in keys:
        A = R.members_asof(a_members, k); B = R.members_asof(b_members, k)
        if A:
            out[k] = set(A) - set(B)
    return out


# ---------------- quality ----------------
def load_quality():
    q = pd.read_parquet(QUALITY)
    q["fy_end"] = pd.to_datetime(q["fy_end"]); q["avail_date"] = pd.to_datetime(q["avail_date"])
    return q.sort_values(["symbol", "avail_date"])


def quality_scores(qual, asof, universe):
    """z(ROE)+z(-DE)+z(profit-growth stability), most-recent avail_date<=asof per symbol (PIT)."""
    av = qual[qual["avail_date"] <= asof]
    if av.empty:
        return pd.Series(dtype=float), 0
    last = av.sort_values("avail_date").groupby("symbol").tail(1).set_index("symbol")
    # profit-growth stability: use trailing up-to-4 fy profit CAGR sign-consistency proxy =
    #   mean(profit)/std(profit) over available history (higher = more stable grower)
    hist = av.sort_values(["symbol", "fy_end"])
    def stab(g):
        p = g["profit"].dropna().values
        if len(p) < 3 or np.all(p <= 0):
            return np.nan
        gr = np.diff(p) / (np.abs(p[:-1]) + 1e-9)
        if len(gr) < 2 or np.nanstd(gr) == 0:
            return np.nan
        return np.nanmean(gr) / (np.nanstd(gr) + 1e-9)
    st = hist.groupby("symbol").apply(stab, include_groups=False)
    cols = [c for c in universe if c in last.index]
    if len(cols) < 10:
        return pd.Series(dtype=float), len(cols)
    df = last.loc[cols, ["roe", "de"]].copy()
    df["stab"] = st.reindex(cols)

    def z(s):
        s = s.astype(float)
        m = s.mean(); sd = s.std(ddof=0)
        return (s - m) / (sd + 1e-12) if sd > 0 else s * 0.0
    zr = z(df["roe"]).clip(-3, 3)
    zd = z(-df["de"]).clip(-3, 3)   # low debt is good
    zs = z(df["stab"]).clip(-3, 3)
    # blend available components (a name with roe+de but no stab still gets 2/3 blend)
    comp = pd.concat([zr, zd, zs], axis=1).mean(axis=1, skipna=True)
    comp = comp.dropna()
    n_q = len(comp)
    return comp, n_q


def mq_scores(price, qual, asof, universe, mom_excl=True):
    """MQ = 0.5*z(momentum) + 0.5*z(quality). Names w/o quality -> momentum-only.
    Returns (score Series over selectable names, quality_coverage_fraction)."""
    mom = R.momentum_scores(price, asof, universe, exclude_recent_month=mom_excl)  # this is 1+comp
    if mom.empty:
        return pd.Series(dtype=float), 0.0
    mom_comp = mom - 1.0  # back to z composite
    q_comp, _ = quality_scores(qual, asof, set(mom_comp.index))
    def z(s):
        sd = s.std(ddof=0)
        return (s - s.mean()) / (sd + 1e-12) if sd > 0 else s * 0.0
    zm = z(mom_comp)
    cov = 0.0
    if len(q_comp) >= 10:
        zq = z(q_comp)
        cov = len(q_comp.index.intersection(mom_comp.index)) / len(mom_comp)
        blended = zm.copy()
        common = zm.index.intersection(zq.index)
        blended.loc[common] = 0.5 * zm.loc[common] + 0.5 * zq.reindex(common)
        # names without quality keep pure momentum z (already in blended)
        score = 1.0 + blended
    else:
        score = 1.0 + zm  # momentum-only (early era / no quality)
    return score, cov


# ---------------- monthly index builder (frictionless) + turnover log ----------------
def month_end_rebals(tdays, start_year=2005, end_year=2026):
    td = pd.DatetimeIndex(tdays)
    out = []
    for yr in range(start_year, end_year + 1):
        for mo in range(1, 13):
            md = td[(td.year == yr) & (td.month == mo)]
            if len(md):
                out.append(md.max())
    return sorted(set(out))


def build_index_monthly(price, ret_close, vol, members, rebals, score_fn, weight_mode,
                        top_n, cap, seg, tag, qual=None):
    """Monthly chain-linked index. Returns dict with frictionless level, cost-loaded level,
    cost-2x level (all on RETURN-panel returns), turnover series, quality coverage per rebal."""
    tdays = price.index
    daily_ret = ret_close.pct_change()   # STRATEGY P&L on the RETURN panel (survivorship-complete)
    port_ret_fric = pd.Series(0.0, index=tdays)
    cost_events = {}   # date -> one-way turnover fraction
    covlog = []
    prev_w = pd.Series(dtype=float)
    active_from = None
    tier = SLIP_TIER[seg]

    for i, rb in enumerate(rebals):
        if rb not in tdays:
            continue
        uni = R.members_asof(members, rb)
        if not uni:
            continue
        if qual is not None:
            scores, qcov = score_fn(price, qual, rb, uni)
        else:
            scores = score_fn(price, rb, uni); qcov = np.nan
        if scores is None or scores.empty:
            continue
        top = scores.sort_values(ascending=False).head(top_n)
        sel = list(top.index)
        if len(sel) < max(8, top_n // 3):
            continue
        if weight_mode == "ew":
            w = pd.Series(1.0 / len(sel), index=sel)
        elif weight_mode == "score":
            w = (top.clip(lower=0)) / top.clip(lower=0).sum()
        elif weight_mode == "invvol":
            w = top / top.sum()
        elif weight_mode == "mcap":
            liq = price.loc[:rb, sel].iloc[-1] * vol.loc[:rb, sel].tail(20).median()
            raw = (liq.fillna(0) * top).clip(lower=0)
            if raw.sum() <= 0:
                w = pd.Series(1.0 / len(sel), index=sel)
            else:
                w = raw / raw.sum()
            w = w.clip(upper=cap); w = w / w.sum()
        else:
            raise ValueError(weight_mode)

        # turnover vs previous weights (one-way): sum of positive weight increases
        allnames = prev_w.index.union(w.index)
        pw = prev_w.reindex(allnames).fillna(0.0); nw = w.reindex(allnames).fillna(0.0)
        oneway_turnover = (nw - pw).clip(lower=0).sum()  # buys = sells for a fully-invested book
        # volume-conditional multiplier: fraction of NEW/increased names on thin days at rb
        buys = (nw - pw)[(nw - pw) > 1e-6].index
        mults = []
        for nm in buys:
            if nm in vol.columns:
                dv = vol.loc[:rb, nm]
                if len(dv) >= 21 and pd.notna(dv.iloc[-1]):
                    med20 = dv.tail(21).iloc[:-1].median()
                    mults.append(EX.slippage_multiplier(dv.iloc[-1], med20))
                else:
                    mults.append(2.0)  # unknown recent volume -> thin-day penalty
            else:
                mults.append(3.0)      # no HF volume at all -> collapse-tier penalty
        avg_mult = float(np.nanmean([m for m in mults if np.isfinite(m)])) if mults else 1.0
        cost_events[rb] = {"turnover": oneway_turnover, "vol_mult": avg_mult, "n_sel": len(sel)}
        covlog.append({"rebal": rb.date().isoformat(), "n_sel": len(sel), "qcov": qcov})

        nxt = tdays[tdays > rb]
        if len(nxt) == 0:
            break
        seg_start = nxt[0]
        seg_end = rebals[i + 1] if i + 1 < len(rebals) else tdays[-1]
        segd = tdays[(tdays >= seg_start) & (tdays <= seg_end)]
        if len(segd) == 0:
            continue
        seg_syms = [s for s in sel if s in daily_ret.columns]
        sub = daily_ret.loc[segd, seg_syms].fillna(0.0)
        w0 = w.reindex(seg_syms).fillna(0.0).values
        cum = (1 + sub.values).cumprod(axis=0)
        cum_prev = np.vstack([np.ones(len(seg_syms)), cum[:-1]])
        wt = w0 * cum_prev
        wt = wt / np.where(wt.sum(axis=1, keepdims=True) == 0, 1, wt.sum(axis=1, keepdims=True))
        port_ret_fric.loc[segd] = (wt * sub.values).sum(axis=1)
        # record end-of-segment drifted weights as prev_w for next turnover calc
        end_w = pd.Series(wt[-1], index=seg_syms)
        prev_w = end_w[end_w > 0]
        if active_from is None:
            active_from = seg_start

    if active_from is None:
        raise RuntimeError(f"[{tag}] no active segments")
    fric = port_ret_fric.loc[active_from:]

    # apply costs: on each rebalance date, deduct round-trip cost * turnover from that day's return
    def cost_bps(mult, x=1.0):
        slip = tier * mult * x
        var_bps = 2 * slip + 2 * STT_BPS * x + 2 * EXCH_BPS * x + STAMP_BUY_BPS * x + 2 * SEBI_BPS * x
        gst_bps = GST * (2 * EXCH_BPS * x + 2 * SEBI_BPS * x + BROKERAGE_PER_NAME_BPS * x)
        return (var_bps + gst_bps) / 1e4  # -> fraction of traded value
    net1 = fric.copy(); net2 = fric.copy()
    for rb, ev in cost_events.items():
        nxt = fric.index[fric.index > rb]
        if len(nxt) == 0:
            continue
        d0 = nxt[0]
        c1 = cost_bps(ev["vol_mult"], 1.0) * ev["turnover"]
        c2 = cost_bps(ev["vol_mult"], 2.0) * ev["turnover"]
        net1.loc[d0] = (1 + net1.loc[d0]) * (1 - c1) - 1
        net2.loc[d0] = (1 + net2.loc[d0]) * (1 - c2) - 1
    out = {"fric": (1 + fric).cumprod(), "net1": (1 + net1).cumprod(),
           "net2": (1 + net2).cumprod(),
           "turnover": pd.Series({k: v["turnover"] for k, v in cost_events.items()}),
           "cov": pd.DataFrame(covlog)}
    ann_turn = out["turnover"].mean() * 12  # monthly -> annualized one-way
    log(f"[{tag}] rebals={len(cost_events)} active {active_from.date()}->{fric.index[-1].date()} "
        f"ann_turnover~{ann_turn:.1%} fricCAGR={_cagr(out['fric']):.2%} "
        f"net1CAGR={_cagr(out['net1']):.2%} net2CAGR={_cagr(out['net2']):.2%}")
    return out


def _cagr(level):
    s = level.dropna()
    if len(s) < 20:
        return np.nan
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1


def _vol(level, start=None):
    r = level.pct_change().dropna()
    if start is not None:
        r = r[r.index >= start]
    return r.std(ddof=0) * np.sqrt(TD) if len(r) > 20 else np.nan


def _mdd(level):
    s = level.dropna()
    return (s / s.cummax() - 1).min() if len(s) > 20 else np.nan


def window_stats(level, asof, years):
    start = asof - pd.DateOffset(years=years)
    s = level[(level.index >= start) & (level.index <= asof)].dropna()
    if len(s) < 20:
        return np.nan, np.nan
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    c = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1
    return round(c, 4), round(s.pct_change().dropna().std(ddof=0) * np.sqrt(TD), 4)


def stitched_official(pn, an, nav, arch):
    p = nav[nav["series"] == pn].set_index("date")["nav"].sort_index() if pn else pd.Series(dtype=float)
    a = arch[arch["index_name"] == an].set_index("date")["close"].sort_index() if an else pd.Series(dtype=float)
    if len(p):
        p.index = pd.to_datetime(p.index)
    if len(a):
        a.index = pd.to_datetime(a.index)
    if len(p) and len(a):
        tail = a[a.index > p.index.max()]
        out = pd.concat([p, tail]).sort_index()
    else:
        out = a if len(a) else p
    return out[~out.index.duplicated(keep="first")]


def rep_quality(rep_level, off_level, name):
    if off_level is None or len(off_level) < 60:
        return None
    st = R.tracking_stats(rep_level, off_level[off_level.index <= DATA_MAX])
    if st is None:
        return None
    rr, ro = st["rr"], st["ro"]
    rows = []
    for lo, hi, lab in [("2005-01-01", "2015-12-31", "2005-15"), ("2016-01-01", "2019-12-31", "2016-19"),
                        ("2020-01-01", "2022-12-31", "2020-22"), ("2023-01-01", "2026-12-31", "2023-26"),
                        ("2005-01-01", "2026-12-31", "FULL")]:
        a = rr[(rr.index >= lo) & (rr.index <= hi)].dropna(); b = ro.reindex(a.index)
        if len(a) < 30:
            continue
        rows.append({"series": name, "era": lab, "n": len(a),
                     "corr": round(a.corr(b), 4), "te_ann": round((a - b).std(ddof=0) * np.sqrt(TD), 4)})
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    log("=" * 78)
    log("D-029 FACTOR FAMILY -- six indices, MONTHLY rebalance, frictionless + cost-loaded")
    log("=" * 78)
    price, ret_close, vol = load_price_return_vol()
    qual = load_quality()
    log(f"[quality] {qual['symbol'].nunique()} syms, avail {qual['avail_date'].min().date()}->{qual['avail_date'].max().date()}")

    n200 = R.apply_aliases(load_members(N200_XLSX))
    n500 = R.apply_aliases(load_members(N500_XLSX))
    n100 = R.apply_aliases(R.load_n100_members())
    small = seg_members(n500, n200)      # N500 minus N200
    midsmall = seg_members(n500, n100)   # N500 minus N100
    log(f"[seg] SMALL snaps={len(small)} (e.g. {sorted(small)[10].date()}: {len(list(small.values())[10])} names)")
    log(f"[seg] MIDSMALL snaps={len(midsmall)}  N500 snaps={len(n500)}")

    nav = pd.read_parquet(NAV_PATH); nav["date"] = pd.to_datetime(nav["date"])
    arch = pd.read_parquet(ARCH_PATH); arch["date"] = pd.to_datetime(arch["date"])
    off_sc_mq = stitched_official(None, "Nifty Smallcap250 Momentum Quality 100", nav, arch)
    off_n500_mq = stitched_official(None, "Nifty500 Multicap Momentum Quality 50", nav, arch)
    off_midsmall = stitched_official(None, "Nifty MidSmallcap400 Momentum Quality 100", nav, arch)

    rebals = month_end_rebals(price.index, 2005, 2026)
    log(f"[rebal] MONTHLY count={len(rebals)}")

    specs = [
        ("1_smallcap_MQ100", small, mq_scores, "mcap", 100, 0.05, "small", off_sc_mq, "Nifty Smallcap250 Momentum Quality 100", True),
        ("2_smallcap_MQ25", small, mq_scores, "mcap", 25, 0.08, "small", None, None, True),
        ("3_n500_MQ50", n500, mq_scores, "mcap", 50, 0.05, "n500", off_n500_mq, "Nifty500 Multicap Momentum Quality 50", True),
        ("4_n500_lowvol50", n500, (lambda p, d, u: R.lowvol_scores(p, d, u)), "invvol", 50, 0.05, "n500", None, None, False),
        ("5_smallcap_lowvol25", small, (lambda p, d, u: R.lowvol_scores(p, d, u)), "invvol", 25, 0.08, "small", None, None, False),
        ("6_midsmall_MQ30", midsmall, mq_scores, "mcap", 30, 0.06, "midsmall", off_midsmall, "Nifty MidSmallcap400 Momentum Quality 100 (loose cousin)", True),
    ]

    results = {}; qual_rows = []; summary_rows = []
    asof = DATA_MAX
    for tag, mem, sf, wmode, topn, cap, seg, offlvl, offname, use_qual in specs:
        log(f"\n[build] {tag} ...")
        try:
            res = build_index_monthly(price, ret_close, vol, mem, rebals, sf, wmode, topn, cap,
                                      seg, tag, qual=(qual if use_qual else None))
        except RuntimeError as e:
            log(f"  SKIP {tag}: {e}"); continue
        results[tag] = res
        # daily NAV CSV (frictionless + cost-loaded + cost-2x)
        dfnav = pd.DataFrame({"date": res["fric"].index, "nav_frictionless": res["fric"].values,
                              "nav_cost_loaded": res["net1"].reindex(res["fric"].index).values,
                              "nav_cost_2x": res["net2"].reindex(res["fric"].index).values})
        dfnav.to_csv(os.path.join(OUT, f"nav_{tag}.csv"), index=False)
        res["cov"].to_csv(os.path.join(OUT, f"coverage_{tag}.csv"), index=False)

        # quality coverage by year (for MQ indices)
        if use_qual and not res["cov"].empty:
            cv = res["cov"].copy(); cv["yr"] = pd.to_datetime(cv["rebal"]).dt.year
            yc = cv.groupby("yr")["qcov"].mean()
            for yr, v in yc.items():
                qual_rows.append({"index": tag, "year": int(yr), "quality_coverage": round(float(v), 3),
                                  "indicative_only": bool(v < 0.40)})

        # summary stats per variant (frictionless + cost)
        for variant, lvl in [("frictionless", res["fric"]), ("cost_loaded", res["net1"]), ("cost_2x", res["net2"])]:
            row = {"index": tag, "variant": variant, "n_days": int(lvl.notna().sum()),
                   "start": lvl.dropna().index.min().date().isoformat(),
                   "cagr_full": round(_cagr(lvl), 4), "vol_full": round(_vol(lvl), 4),
                   "maxdd_full": round(_mdd(lvl), 4),
                   "ann_turnover": round(res["turnover"].mean() * 12, 3)}
            for wy in (1, 3, 5, 10):
                c, v = window_stats(lvl, asof, wy)
                row[f"cagr_{wy}Y"] = c; row[f"vol_{wy}Y"] = v
            summary_rows.append(row)

        # replication quality vs official (frictionless replica, price-basis) for #1,#3,#6
        if offlvl is not None:
            # rebuild a PRICE-basis frictionless replica for fair corr/TE vs official price index
            q = rep_quality(res["fric"], offlvl, tag)
            if q is not None:
                q["official"] = offname
                qual_rows_te = q
                q.to_csv(os.path.join(OUT, f"repquality_{tag}.csv"), index=False)
                log(f"  [rep vs {offname}]")
                log("  " + q.to_string(index=False).replace("\n", "\n  "))

    pd.DataFrame(summary_rows).to_csv(os.path.join(OUT, "summary_table.csv"), index=False)
    pd.DataFrame(qual_rows).to_csv(os.path.join(OUT, "quality_coverage_by_index_year.csv"), index=False)
    log("\n=== SUMMARY TABLE (written) ===")
    sdf = pd.DataFrame(summary_rows)
    log(sdf[["index", "variant", "cagr_full", "vol_full", "maxdd_full", "ann_turnover",
             "cagr_1Y", "cagr_3Y", "cagr_5Y", "cagr_10Y"]].to_string(index=False))

    cfg = {"built": datetime.now().isoformat(timespec="seconds"),
           "price_panel": PRICE_PANEL + " (frozen, md5 cc5f70d1...)",
           "return_panel": RETURN_PANEL + " (frozen, md5 9f5b5d42...)",
           "quality": QUALITY + " (pkl funda primary, screener xlsx cross-check; RESTATED T+90)",
           "rebalance": "MONTHLY (Principal spec); NSE official = semiannual(MQ)/quarterly(lowvol) -> stated TE source",
           "costs": "COST_STANDARDS APPROVED + execution_realism vol-mult; turnover-based; 2x promotion stress",
           "engine": ENGINE + " (imported UNCHANGED)",
           "basis": "PRICE panel for construction+official corr/TE; RETURN panel for cost-loaded strategy NAV",
           "asof": asof.date().isoformat(),
           "specs": [s[0] for s in specs]}
    with open(os.path.join(OUT, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    log(f"\n[done] outputs in {OUT}")


if __name__ == "__main__":
    main()
