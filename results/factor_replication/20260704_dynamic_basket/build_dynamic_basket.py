"""D-029 wave 2: N500 enhanced mom-lowvol DYNAMIC-REGIME basket, monthly rebalanced.
Owner: Ishaan Gupta (E-012, ML desk). Pre-registered kills in config.json (written BEFORE this
run per RESEARCH_SOP). Landmine guards + D-028 lookahead discipline mandatory.

DESIGN (see config.json for the full pre-registration):
  - Universe: N500 PIT (NIFTY500_TICKER_2005_2025_Final.xlsx), monthly rebalance, engine reused
    UNCHANGED from build_factor_family.py / replicate_factor_indices.py (R.momentum_scores B_excl,
    R.lowvol_scores, build_index_monthly cost/turnover machinery).
  - Regime = india_vix.parquet (2016+) vs its OWN TRAILING 252d median (T6: expanding/rolling,
    NEVER full-sample or centered). Pre-2016 splice = N500 equal-weight trailing-63d realized vol
    proxy, stated loudly, no blending across the splice date.
  - RISK-ON (regime <= trailing median): blend = 0.70*mom_z + 0.30*lowvol_z
  - RISK-OFF (regime > trailing median): blend = 0.30*mom_z + 0.70*lowvol_z
  - Top-50 by blended z, weight = tilt (clip>=0, normalize, cap 5%), monthly, next-day fill.
  - Controls (same machinery/costs): pure momentum-50, pure lowvol-50.
  - OWN stale_mask built on this exact return panel (>=20 consecutive identical closes excluded
    from the draw pool at rebalance date), independent of the D-029 random-basket suite's mask
    (same threshold/logic, different build, per instruction "your own stale_mask").

Run (background, detached, checkpointed):
    PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python build_dynamic_basket.py
"""
from __future__ import annotations
import os, sys, json, time
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

OUT = os.path.join(ROOT, r"results\factor_replication\20260704_dynamic_basket")
PRICE_PANEL = os.path.join(ROOT, r"results\factor_replication\20260704_union_rerun\close_panel_price.parquet")
RETURN_PANEL = os.path.join(ROOT, r"results\factor_replication\20260704_factor_family\close_panel_return.parquet")
HF_PANEL = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")
N500_XLSX = os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx")
VIX_PATH = os.path.join(ROOT, r"datasets\index_daily\india_vix.parquet")
RANDOM_BENCH_SUMMARY = os.path.join(ROOT, r"datasets\derived\benchmarks_random\summary.csv")

DATA_MAX = pd.Timestamp("2026-01-22")
TD = 252
FROZEN_RUN_THRESHOLD = 20  # own stale_mask, same threshold as D-029 suite (stated, not re-tuned)

# cost params -- IDENTICAL to build_factor_family.py (COST_STANDARDS APPROVED D-021)
STT_BPS = 10.0
EXCH_BPS = 0.297
STAMP_BUY_BPS = 1.5
SEBI_BPS = 0.01
BROKERAGE_PER_NAME_BPS = 0.0
GST = 0.18
SLIP_TIER_N500 = 22.0  # cap-weighted large/mid/small blend, per factor_family convention

VIX_SPLICE_DATE = pd.Timestamp("2016-01-04")  # first real VIX obs; before this, realized-vol proxy
REGIME_TRAIL_WINDOW = 252  # 1y trailing median window (T6: expanding until full, then rolling)
RISK_ON_W = {"mom": 0.70, "lowvol": 0.30}
RISK_OFF_W = {"mom": 0.30, "lowvol": 0.70}
TOP_N = 50
CAP = 0.05
TURNOVER_TRIGGER = 2.50  # 250%/yr annualized one-way -> build turnover-banded contingency variant


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------
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
    log(f"[panel] price {price.shape} return {ret_close.shape} vol-cov {vol.notna().any().mean():.1%}")
    return price, ret_close, vol


def build_stale_mask(ret_close: pd.DataFrame) -> pd.DataFrame:
    """OWN stale_mask on THIS return panel (independent rebuild, same threshold/logic as the
    D-029 random-basket suite). >=20 consecutive identical closes -> frozen/dead-quote, excluded
    from the draw pool at rebalance date."""
    t0 = time.time()
    long = ret_close.stack().dropna().rename("close").reset_index()
    long.columns = ["date", "symbol", "close"]
    long = long.sort_values(["symbol", "date"]).reset_index(drop=True)
    same_as_prev = long.groupby("symbol")["close"].diff().eq(0)
    run_id = (~same_as_prev).groupby(long["symbol"]).cumsum()
    long["run_len"] = long.groupby(["symbol", run_id])["close"].cumcount() + 1
    long["frozen"] = long["run_len"] >= FROZEN_RUN_THRESHOLD
    n_flag = int(long["frozen"].sum()); n_sym = long.loc[long["frozen"], "symbol"].nunique()
    log(f"[stale_mask] {n_flag:,} rows ({n_flag/len(long):.2%}) flagged frozen, {n_sym} symbols, "
        f"threshold={FROZEN_RUN_THRESHOLD}d, built in {time.time()-t0:.1f}s")
    mask = long.pivot(index="date", columns="symbol", values="frozen").fillna(False)
    return mask.reindex(index=ret_close.index, columns=ret_close.columns).fillna(False)


def load_n500_members():
    return R.apply_aliases(_load_members_xlsx(N500_XLSX))


def _load_members_xlsx(xlsx):
    d = pd.read_excel(xlsx).rename(columns={"Month-Year": "lab", "Ticker": "sym"})
    d["sym"] = d["sym"].astype(str).str.strip().str.upper()
    out = {}
    for lab, g in d.groupby("lab"):
        mon, yr = str(lab)[:3], str(lab)[3:]
        out[pd.Timestamp(year=int(yr), month=R._MONTH_MAP[mon], day=1)] = set(g["sym"])
    return out


def month_end_rebals(tdays, start_year=2005, end_year=2026):
    td = pd.DatetimeIndex(tdays)
    out = []
    for yr in range(start_year, end_year + 1):
        for mo in range(1, 13):
            md = td[(td.year == yr) & (td.month == mo)]
            if len(md):
                out.append(md.max())
    return sorted(set(out))


# ---------------------------------------------------------------------------
# REGIME SIGNAL: VIX (2016+) vs TRAILING 252d median; pre-2016 realized-vol proxy splice
# T6 (D-028): median computed ONLY from observations <= rebalance date (no lookahead).
# ---------------------------------------------------------------------------
def build_regime_series(price: pd.DataFrame, n500_members: dict, stale_mask: pd.DataFrame) -> pd.Series:
    """Daily regime-input series: real VIX from VIX_SPLICE_DATE onward, N500 EW trailing-63d
    realized annualized vol (x100, VIX-like units) before that date. Indexed on trading days.
    IV/derived-input sanity discipline (Ishaan's own lesson, 2026-07): stale/frozen-print names
    are EXCLUDED from the equal-weight proxy return each day (per-day mask from build_stale_mask),
    since a single frozen-then-unfreezing microcap (e.g. VAIBHAVGBL +400% print on 2005-07-28) can
    dominate an equal-weight cross-sectional average and fabricate a fake vol spike that poisons
    the trailing-252d median for many months after. This is the SAME landmine documented in the
    D-029 random-basket README (frozen-price runs), independently re-caught here on the regime
    proxy specifically -- self-audit finding, fixed before the run counted."""
    vix = pd.read_parquet(VIX_PATH, columns=["timestamp", "close"])
    vix["date"] = pd.to_datetime(vix["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    vix = vix.drop_duplicates("date").set_index("date")["close"].sort_index()
    log(f"[regime] VIX raw {vix.index.min().date()}->{vix.index.max().date()} n={len(vix)}")

    # N500 equal-weight daily return proxy for the pre-2016 splice: use the UNION of all N500
    # snapshots' names (broad, PIT-agnostic proxy is fine here -- it's a REGIME proxy, not a
    # tradeable signal, and only feeds a binary on/off flag, never stock selection), EXCLUDING
    # stale/frozen-print (symbol,date) cells so a single dead-quote unfreeze cannot dominate the
    # cross-sectional mean on any given day.
    all_n500_syms = sorted(set().union(*n500_members.values())) if n500_members else []
    cols = [c for c in all_n500_syms if c in price.columns]
    px = price[cols].copy()
    frozen_aligned = stale_mask.reindex(index=px.index, columns=cols, fill_value=False).astype(bool)
    px_clean = px.mask(frozen_aligned)  # frozen cells -> NaN, excluded from that day's cross-section
    ew_ret = px_clean.pct_change().mean(axis=1, skipna=True)
    # extra belt-and-braces cap: a single-day equal-weight N500 average move beyond +-20% is not
    # physically plausible (even 2008/2020 crash days), so clip as an OUTLIER FLOOR (sanity-cap on
    # a DERIVED input before it enters the regime signal, per lesson learned 2026-07 IV blow-ups).
    ew_ret_capped = ew_ret.clip(-0.20, 0.20)
    n_capped = int((ew_ret != ew_ret_capped).sum())
    if n_capped:
        log(f"[regime] SANITY-CAP fired on {n_capped} day(s) where EW N500 proxy return exceeded "
            f"+-20% even after stale-mask exclusion (residual artifact) -- capped before use")
    realized_vol = ew_ret_capped.rolling(63, min_periods=40).std(ddof=0) * np.sqrt(252) * 100.0
    log(f"[regime] pre-2016 realized-63d-vol proxy built on {len(cols)} N500-ever names "
        f"(stale-masked + sanity-capped), range "
        f"{realized_vol.dropna().index.min().date()}->{realized_vol.dropna().index.max().date()}")

    idx = price.index
    proxy_part = realized_vol.reindex(idx)
    vix_part = vix.reindex(idx)
    regime = pd.Series(np.where(idx < VIX_SPLICE_DATE, proxy_part.values, vix_part.values), index=idx)
    n_nan = regime.isna().sum()
    log(f"[regime] spliced series built, splice_date={VIX_SPLICE_DATE.date()}, "
        f"NaN count={n_nan} (expected only in earliest ~63d warmup)")
    return regime


def trailing_median_asof(regime: pd.Series, asof: pd.Timestamp) -> float:
    """T6 STRICT: median computed using ONLY regime observations with date <= asof, last
    REGIME_TRAIL_WINDOW trading days (expanding until that many obs exist)."""
    hist = regime.loc[:asof].dropna()
    if len(hist) == 0:
        return np.nan
    window = hist.tail(REGIME_TRAIL_WINDOW)
    return float(window.median())


# ---------------------------------------------------------------------------
# Blended dynamic-regime score
# ---------------------------------------------------------------------------
def zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    return (s - s.mean()) / (sd + 1e-12) if sd > 0 else s * 0.0


def dynamic_blend_scores(price, asof, universe, w_mom, w_lv):
    mom = R.momentum_scores(price, asof, universe, exclude_recent_month=True)  # 1+z composite
    lv = R.lowvol_scores(price, asof, universe)  # inverse-vol raw
    if mom.empty or lv.empty:
        return pd.Series(dtype=float)
    mom_z = zscore(mom - 1.0).clip(-3, 3)
    lv_z = zscore(lv).clip(-3, 3)
    common = mom_z.index.intersection(lv_z.index)
    if len(common) < 30:
        return pd.Series(dtype=float)
    blended = w_mom * mom_z.reindex(common) + w_lv * lv_z.reindex(common)
    return 1.0 + blended  # keep engine's ">0-by-construction-ish" tilt convention


def pure_momentum_scores(price, asof, universe):
    mom = R.momentum_scores(price, asof, universe, exclude_recent_month=True)
    if mom.empty:
        return pd.Series(dtype=float)
    z = zscore(mom - 1.0).clip(-3, 3)
    return 1.0 + z


def pure_lowvol_scores(price, asof, universe):
    return R.lowvol_scores(price, asof, universe)  # inverse-vol raw, used directly as invvol weight


# ---------------------------------------------------------------------------
# Monthly index builder (adapted from build_factor_family.build_index_monthly):
# adds stale_mask exclusion at rebalance date, and (for dynamic) an optional turnover-band filter.
# ---------------------------------------------------------------------------
def build_index_monthly(price, ret_close, vol, stale_mask, members, rebals, score_fn, weight_mode,
                        top_n, cap, tag, rank_band=None, prior_sel_holder=None):
    """rank_band: if set (int), only ADD a name if it wasn't selected last month AND its rank is
    "new" by more than the band vs the union of (this month top_n+band, last month's holdings) --
    simplified structural rule: candidate pool = top_n; a name REPLACES an existing holding only
    if the incoming name's rank is within top_n while the outgoing (lowest-ranked current holding)
    has fallen outside top_n + rank_band. This keeps near-boundary churn out without hand-tuning."""
    tdays = price.index
    daily_ret = ret_close.pct_change()
    port_ret_fric = pd.Series(0.0, index=tdays)
    cost_events = {}
    covlog = []
    prev_w = pd.Series(dtype=float)
    prev_sel_ranked = []  # list of symbols in rank order from the prior rebalance (for banding)
    active_from = None

    for i, rb in enumerate(rebals):
        if rb not in tdays:
            continue
        uni = R.members_asof(members, rb)
        if not uni:
            continue
        # exclude stale/frozen names from the draw pool AT the rebalance date
        if rb in stale_mask.index:
            frozen_today = set(stale_mask.columns[stale_mask.loc[rb].values])
            uni = uni - frozen_today
        scores = score_fn(price, rb, uni)
        if scores is None or scores.empty:
            continue
        ranked = scores.sort_values(ascending=False)
        top = ranked.head(top_n)
        sel = list(top.index)
        if len(sel) < max(8, top_n // 3):
            continue

        if rank_band is not None and prev_sel_ranked:
            # rank-banded turnover control: keep prior holdings that are still within
            # top_n + rank_band of the NEW ranking; only admit new names to fill remaining slots.
            rank_pos = {s: p for p, s in enumerate(ranked.index)}
            keep = [s for s in prev_sel_ranked if rank_pos.get(s, 10**9) < top_n + rank_band]
            keep = keep[:top_n]
            fill_candidates = [s for s in sel if s not in keep]
            sel = keep + fill_candidates[: max(0, top_n - len(keep))]
            top = ranked.reindex(sel)

        if weight_mode == "score":
            w = (top.clip(lower=0)) / top.clip(lower=0).sum()
        elif weight_mode == "invvol":
            w = top / top.sum()
        else:
            raise ValueError(weight_mode)
        w = w.clip(upper=cap); w = w / w.sum()

        allnames = prev_w.index.union(w.index)
        pw = prev_w.reindex(allnames).fillna(0.0); nw = w.reindex(allnames).fillna(0.0)
        oneway_turnover = (nw - pw).clip(lower=0).sum()
        buys = (nw - pw)[(nw - pw) > 1e-6].index
        mults = []
        for nm in buys:
            if nm in vol.columns:
                dv = vol.loc[:rb, nm]
                if len(dv) >= 21 and pd.notna(dv.iloc[-1]):
                    med20 = dv.tail(21).iloc[:-1].median()
                    mults.append(EX.slippage_multiplier(dv.iloc[-1], med20))
                else:
                    mults.append(2.0)
            else:
                mults.append(3.0)
        avg_mult = float(np.nanmean([m for m in mults if np.isfinite(m)])) if mults else 1.0
        cost_events[rb] = {"turnover": oneway_turnover, "vol_mult": avg_mult, "n_sel": len(sel)}
        covlog.append({"rebal": rb.date().isoformat(), "n_sel": len(sel)})

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
        end_w = pd.Series(wt[-1], index=seg_syms)
        prev_w = end_w[end_w > 0]
        prev_sel_ranked = sel
        if active_from is None:
            active_from = seg_start

    if active_from is None:
        raise RuntimeError(f"[{tag}] no active segments")
    fric = port_ret_fric.loc[active_from:]

    def cost_bps(mult, x=1.0):
        slip = SLIP_TIER_N500 * mult * x
        var_bps = 2 * slip + 2 * STT_BPS * x + 2 * EXCH_BPS * x + STAMP_BUY_BPS * x + 2 * SEBI_BPS * x
        gst_bps = GST * (2 * EXCH_BPS * x + 2 * SEBI_BPS * x + BROKERAGE_PER_NAME_BPS * x)
        return (var_bps + gst_bps) / 1e4

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

    out = {"fric": (1 + fric).cumprod(), "net1": (1 + net1).cumprod(), "net2": (1 + net2).cumprod(),
           "turnover": pd.Series({k: v["turnover"] for k, v in cost_events.items()}),
           "cov": pd.DataFrame(covlog)}
    ann_turn = out["turnover"].mean() * 12
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


def _vol(level):
    r = level.pct_change().dropna()
    return r.std(ddof=0) * np.sqrt(TD) if len(r) > 20 else np.nan


def _mdd(level):
    s = level.dropna()
    return (s / s.cummax() - 1).min() if len(s) > 20 else np.nan


def checkpoint(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)
    log(f"  [checkpoint] wrote {path} ({len(df)} rows)")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    log("=" * 78)
    log("D-029 wave 2: N500 DYNAMIC mom-lowvol regime basket, monthly, kills pre-registered")
    log("=" * 78)

    price, ret_close, vol = load_price_return_vol()
    n500 = load_n500_members()
    log(f"[members] N500 snapshots={len(n500)} ({min(n500).date()}->{max(n500).date()})")

    stale_mask = build_stale_mask(ret_close)
    stale_mask.to_parquet(os.path.join(OUT, "stale_mask_own.parquet"))

    regime = build_regime_series(price, n500, stale_mask)

    rebals = month_end_rebals(price.index, 2005, 2026)
    log(f"[rebal] MONTHLY count={len(rebals)}")

    # ---------------- regime timeline (pre-registered, computed once, shared by dynamic build) ----
    timeline_rows = []
    regime_weight_by_rebal = {}
    for rb in rebals:
        if rb not in price.index:
            continue
        val = regime.loc[:rb].dropna()
        if val.empty:
            continue
        cur = float(val.iloc[-1])
        med = trailing_median_asof(regime, rb)
        if np.isnan(med):
            continue
        is_risk_on = cur <= med
        w = RISK_ON_W if is_risk_on else RISK_OFF_W
        regime_weight_by_rebal[rb] = w
        timeline_rows.append({
            "rebal": rb.date().isoformat(), "regime_value": round(cur, 4),
            "trailing_median_252d": round(med, 4), "regime": "RISK_ON" if is_risk_on else "RISK_OFF",
            "w_momentum": w["mom"], "w_lowvol": w["lowvol"],
            "series_used": "proxy_63d_realized_vol" if rb < VIX_SPLICE_DATE else "india_vix",
        })
    timeline_df = pd.DataFrame(timeline_rows)
    checkpoint(timeline_df, os.path.join(OUT, "regime_timeline.csv"))
    n_on = (timeline_df["regime"] == "RISK_ON").sum(); n_off = (timeline_df["regime"] == "RISK_OFF").sum()
    log(f"[regime] timeline built: {n_on} RISK_ON months, {n_off} RISK_OFF months "
        f"({n_on/(n_on+n_off):.1%} on)")

    # ---------------- DYNAMIC basket ----------------
    def dyn_score_fn(price_, rb, uni):
        w = regime_weight_by_rebal.get(rb, RISK_ON_W)
        return dynamic_blend_scores(price_, rb, uni, w["mom"], w["lowvol"])

    log("\n[build] DYNAMIC (regime-blended mom/lowvol) ...")
    res_dyn = build_index_monthly(price, ret_close, vol, stale_mask, n500, rebals, dyn_score_fn,
                                  "score", TOP_N, CAP, "dynamic")
    nav_dyn = pd.DataFrame({"date": res_dyn["fric"].index,
                            "nav_frictionless": res_dyn["fric"].values,
                            "nav_cost_loaded": res_dyn["net1"].reindex(res_dyn["fric"].index).values,
                            "nav_cost_2x": res_dyn["net2"].reindex(res_dyn["fric"].index).values})
    checkpoint(nav_dyn, os.path.join(OUT, "nav_dynamic.csv"))
    res_dyn["turnover"].rename("turnover").to_frame().reset_index().rename(
        columns={"index": "rebal"}).to_csv(os.path.join(OUT, "turnover_dynamic.csv"), index=False)
    ann_turn_dyn = res_dyn["turnover"].mean() * 12

    # ---------------- CONTROL: pure momentum-50 ----------------
    log("\n[build] CONTROL pure_momentum_50 ...")
    res_mom = build_index_monthly(price, ret_close, vol, stale_mask, n500, rebals,
                                  pure_momentum_scores, "score", TOP_N, CAP, "control_momentum")
    nav_mom = pd.DataFrame({"date": res_mom["fric"].index,
                            "nav_frictionless": res_mom["fric"].values,
                            "nav_cost_loaded": res_mom["net1"].reindex(res_mom["fric"].index).values,
                            "nav_cost_2x": res_mom["net2"].reindex(res_mom["fric"].index).values})
    checkpoint(nav_mom, os.path.join(OUT, "nav_control_momentum.csv"))
    res_mom["turnover"].rename("turnover").to_frame().reset_index().rename(
        columns={"index": "rebal"}).to_csv(os.path.join(OUT, "turnover_control_momentum.csv"), index=False)

    # ---------------- CONTROL: pure lowvol-50 ----------------
    log("\n[build] CONTROL pure_lowvol_50 ...")
    res_lv = build_index_monthly(price, ret_close, vol, stale_mask, n500, rebals,
                                 pure_lowvol_scores, "invvol", TOP_N, CAP, "control_lowvol")
    nav_lv = pd.DataFrame({"date": res_lv["fric"].index,
                          "nav_frictionless": res_lv["fric"].values,
                          "nav_cost_loaded": res_lv["net1"].reindex(res_lv["fric"].index).values,
                          "nav_cost_2x": res_lv["net2"].reindex(res_lv["fric"].index).values})
    checkpoint(nav_lv, os.path.join(OUT, "nav_control_lowvol.csv"))
    res_lv["turnover"].rename("turnover").to_frame().reset_index().rename(
        columns={"index": "rebal"}).to_csv(os.path.join(OUT, "turnover_control_lowvol.csv"), index=False)

    # ---------------- turnover trap: banded contingency if triggered ----------------
    banded_result = None
    if ann_turn_dyn > TURNOVER_TRIGGER:
        log(f"\n[turnover-trap] dynamic ann. turnover {ann_turn_dyn:.1%} > {TURNOVER_TRIGGER:.0%} "
            f"trigger -> building turnover-banded contingency variant (rank_band=5)")
        res_dyn_band = build_index_monthly(price, ret_close, vol, stale_mask, n500, rebals, dyn_score_fn,
                                           "score", TOP_N, CAP, "dynamic_banded", rank_band=5)
        nav_band = pd.DataFrame({"date": res_dyn_band["fric"].index,
                                 "nav_frictionless": res_dyn_band["fric"].values,
                                 "nav_cost_loaded": res_dyn_band["net1"].reindex(res_dyn_band["fric"].index).values,
                                 "nav_cost_2x": res_dyn_band["net2"].reindex(res_dyn_band["fric"].index).values})
        checkpoint(nav_band, os.path.join(OUT, "nav_dynamic_turnoverbanded.csv"))
        banded_result = res_dyn_band
    else:
        log(f"\n[turnover-trap] dynamic ann. turnover {ann_turn_dyn:.1%} <= {TURNOVER_TRIGGER:.0%} "
            f"trigger -> banded variant NOT built (not needed)")

    # ---------------- summary stats ----------------
    def stats_row(tag, res):
        rows = []
        for variant, lvl in [("frictionless", res["fric"]), ("cost_1x", res["net1"]), ("cost_2x", res["net2"])]:
            rows.append({"basket": tag, "variant": variant, "cagr": round(_cagr(lvl), 4),
                        "vol": round(_vol(lvl), 4), "maxdd": round(_mdd(lvl), 4),
                        "ann_turnover": round(res["turnover"].mean() * 12, 3),
                        "n_days": int(lvl.notna().sum())})
        return rows

    summary_rows = (stats_row("dynamic", res_dyn) + stats_row("control_momentum", res_mom)
                    + stats_row("control_lowvol", res_lv))
    if banded_result is not None:
        summary_rows += stats_row("dynamic_turnoverbanded", banded_result)
    summary_df = pd.DataFrame(summary_rows)
    checkpoint(summary_df, os.path.join(OUT, "summary_table.csv"))
    log("\n" + summary_df.to_string(index=False))

    # ---------------- KILL VERDICT ----------------
    rb_summary = pd.read_csv(RANDOM_BENCH_SUMMARY)
    rand_n500_50 = rb_summary[rb_summary["spec"] == "n500_50"].iloc[0]
    rand_mean_cagr = float(rand_n500_50["cagr_mean"])

    def get(tag, variant, col):
        r = summary_df[(summary_df["basket"] == tag) & (summary_df["variant"] == variant)]
        return float(r[col].iloc[0]) if len(r) else np.nan

    dyn_net1 = get("dynamic", "cost_1x", "cagr")
    dyn_net2 = get("dynamic", "cost_2x", "cagr")
    dyn_mdd1 = get("dynamic", "cost_1x", "maxdd")
    mom_net1 = get("control_momentum", "cost_1x", "cagr")
    lv_net1 = get("control_lowvol", "cost_1x", "cagr")
    mom_mdd1 = get("control_momentum", "cost_1x", "maxdd")

    k1_thresh = rand_mean_cagr + 0.01
    k1_pass = bool(dyn_net1 >= k1_thresh)
    k2_pass = bool((dyn_net1 > mom_net1) and (dyn_net1 > lv_net1))
    k3_pass = bool((dyn_net2 > 0) and (dyn_net2 >= rand_mean_cagr))
    k4_pass = bool(abs(dyn_mdd1) < abs(mom_mdd1))

    verdict = "SURVIVES-TO-GATE-4" if (k1_pass and k2_pass and k3_pass and k4_pass) else "KILLED"

    kill_rows = [
        {"kill": "K1", "desc": "dynamic net1x CAGR >= random-N500-50 mean +1pp",
         "dynamic_value": round(dyn_net1, 4), "threshold": round(k1_thresh, 4), "pass": k1_pass},
        {"kill": "K2a", "desc": "dynamic net1x CAGR > control_momentum net1x CAGR",
         "dynamic_value": round(dyn_net1, 4), "threshold": round(mom_net1, 4), "pass": bool(dyn_net1 > mom_net1)},
        {"kill": "K2b", "desc": "dynamic net1x CAGR > control_lowvol net1x CAGR",
         "dynamic_value": round(dyn_net1, 4), "threshold": round(lv_net1, 4), "pass": bool(dyn_net1 > lv_net1)},
        {"kill": "K3", "desc": "dynamic net2x CAGR positive AND >= random-N500-50 mean",
         "dynamic_value": round(dyn_net2, 4), "threshold": round(rand_mean_cagr, 4), "pass": k3_pass},
        {"kill": "K4", "desc": "dynamic net1x maxDD less severe than control_momentum net1x maxDD",
         "dynamic_value": round(dyn_mdd1, 4), "threshold": round(mom_mdd1, 4), "pass": k4_pass},
    ]
    kill_df = pd.DataFrame(kill_rows)
    checkpoint(kill_df, os.path.join(OUT, "kill_verdict_table.csv"))

    log("\n" + "=" * 78)
    log(f"VERDICT: {verdict}")
    log(kill_df.to_string(index=False))
    log("=" * 78)

    cfg_update = {
        "run_completed": datetime.now().isoformat(timespec="seconds"),
        "elapsed_sec": round(time.time() - t0, 1),
        "verdict": verdict,
        "random_n500_50_mean_cagr": rand_mean_cagr,
        "dynamic_ann_turnover": round(ann_turn_dyn, 4),
        "turnover_trigger_fired": bool(ann_turn_dyn > TURNOVER_TRIGGER),
    }
    with open(os.path.join(OUT, "run_result.json"), "w") as f:
        json.dump(cfg_update, f, indent=2)
    log(f"[done] outputs in {OUT}, total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
