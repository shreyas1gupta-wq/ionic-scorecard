"""I-016 cadence test (Devika Menon, E-016) — LowVol50 quarterly + MQ50 semiannual.

Reuses the D-029 factor-family engine and FROZEN panels EXACTLY (no rebuild):
  engine        results/factor_replication/20260704_momentm30_exact/replicate_factor_indices.py
  family driver results/factor_replication/20260704_factor_family/build_factor_family.py (logic copied,
                not imported, so we can vary the rebalance schedule + inject the stale mask cleanly)
  PRICE panel   results/factor_replication/20260704_union_rerun/close_panel_price.parquet
  RETURN panel  results/factor_replication/20260704_factor_family/close_panel_return.parquet  (strategy P&L)
  quality       results/factor_replication/20260704_factor_family/quality_pit.parquet         (MQ only)
  volume        swing_momentum/data/hf_stock_minute/day/train-00000.parquet

NEW LAYER (D-029, found AFTER the family build): stale_mask.parquet (212 frozen-price symbols,
0.9% of rows). Applied as a (symbol,date) veto:
  - SELECTION: a symbol whose price is frozen at the rebalance date's trailing window is
    excluded from that rebalance's candidate pool (critical for LowVol — a frozen run has
    ~0 measured vol => inverse-vol would massively over-weight fabricated-stable names).
  - P&L: the RETURN-panel daily return of any (symbol,date) inside a frozen run is set to 0
    (no fabricated move booked; matches the benchmark suite's frozen-run exclusion intent).

RUNS:
  A. n500_lowvol50 MONTHLY   (restate family monthly WITH mask -> apples-to-apples)
  B. n500_lowvol50 QUARTERLY (Mar/Jun/Sep/Dec)   <- I-016 variant 1
  C. n500_MQ50     MONTHLY   (restate family monthly WITH mask)
  D. n500_MQ50     SEMIANNUAL(Jun/Dec)           <- I-016 variant 2

Cost model: IDENTICAL to build_factor_family (COST_STANDARDS approved + execution_realism vol-mult),
turnover-based, 1x and 2x. Annualized turnover = mean per-rebalance one-way turnover * rebals/yr.

D-028 lookahead discipline: selection uses ONLY prices <= rebalance day; weights applied from the
NEXT trading day; PIT membership via members_asof (most-recent snapshot on/before rb). No same-bar.
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

FAM = os.path.join(ROOT, r"results\factor_replication\20260704_factor_family")
OUT = os.path.join(ROOT, r"results\factor_replication\20260704_i016_cadence")
PRICE_PANEL = os.path.join(ROOT, r"results\factor_replication\20260704_union_rerun\close_panel_price.parquet")
RETURN_PANEL = os.path.join(FAM, "close_panel_return.parquet")
HF_PANEL = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")
QUALITY = os.path.join(FAM, "quality_pit.parquet")
STALE_MASK = os.path.join(ROOT, r"datasets\derived\benchmarks_random\stale_mask.parquet")
N200_XLSX = os.path.join(ROOT, "NIFTY200_TICKER_2005_2025.xlsx")
N500_XLSX = os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx")

DATA_MAX = pd.Timestamp("2026-01-22")
TD = 252
# cost params (identical to build_factor_family.py)
STT_BPS = 10.0; EXCH_BPS = 0.297; STAMP_BUY_BPS = 1.5; SEBI_BPS = 0.01
BROKERAGE_PER_NAME_BPS = 0.0; GST = 0.18
SLIP_TIER = {"small": 35.0, "midsmall": 35.0, "n500": 22.0}

CKPT = os.path.join(OUT, "_checkpoint.json")
def log(*a): print(*a, flush=True)
def ckpt(stage): json.dump({"stage": stage, "ts": datetime.now().isoformat(timespec="seconds")}, open(CKPT, "w"))


# ---------------- panels + stale mask ----------------
def load_all():
    up = pd.read_parquet(PRICE_PANEL, columns=["date", "symbol", "close"])
    up["date"] = pd.to_datetime(up["date"]); up["symbol"] = up["symbol"].str.strip().str.upper()
    up = up[(up["date"] <= DATA_MAX) & (up["close"] > 0)].drop_duplicates(["symbol", "date"], keep="last")
    price = up.pivot(index="date", columns="symbol", values="close").sort_index()

    rp = pd.read_parquet(RETURN_PANEL, columns=["date", "symbol", "close"])
    rp["date"] = pd.to_datetime(rp["date"]); rp["symbol"] = rp["symbol"].str.strip().str.upper()
    rp = rp[(rp["date"] <= DATA_MAX) & (rp["close"] > 0)].drop_duplicates(["symbol", "date"], keep="last")
    ret_close = rp.pivot(index="date", columns="symbol", values="close").sort_index()

    hf = pd.read_parquet(HF_PANEL, columns=["symbol", "timestamp", "volume"])
    hf = G.fix_ist_dates(hf, ts_col="timestamp", out_col="date")
    hf["date"] = pd.to_datetime(hf["date"]); hf["symbol"] = hf["symbol"].str.strip().str.upper()
    hf = hf[hf["date"] <= DATA_MAX].drop_duplicates(["symbol", "date"], keep="last")
    vol = hf.pivot(index="date", columns="symbol", values="volume").sort_index()
    vol = vol.reindex(index=price.index, columns=price.columns)

    # stale mask -> wide boolean frozen(symbol,date), reindexed to the PRICE panel grid
    sm = pd.read_parquet(STALE_MASK, columns=["date", "symbol", "frozen"])
    sm["date"] = pd.to_datetime(sm["date"]); sm["symbol"] = sm["symbol"].str.strip().str.upper()
    sm = sm[sm["frozen"]].drop_duplicates(["symbol", "date"])
    frozen = pd.DataFrame(False, index=price.index, columns=price.columns)
    sm = sm[sm["symbol"].isin(frozen.columns) & sm["date"].isin(frozen.index)]
    # set frozen True at (date,symbol) via pivot then reindex to the full grid
    frz_wide = sm.assign(v=True).pivot(index="date", columns="symbol", values="v")
    frz_wide = frz_wide.reindex(index=price.index, columns=price.columns).fillna(False).astype(bool)
    log(f"[panel] price {price.shape} return {ret_close.shape} vol-cov {vol.notna().any().mean():.1%} "
        f"| frozen cells {int(frz_wide.values.sum())} ({frz_wide.values.mean():.3%}) syms={int((frz_wide.any()).sum())}")
    return price, ret_close, vol, frz_wide


def lowvol_scores_masked(price, frz_wide, asof, universe):
    """Inverse trailing-252d vol, but any symbol whose price is FROZEN at the asof date (or with
    a frozen run covering the trailing window such that measured vol is fake) is excluded from the
    candidate pool. Practically: exclude symbols frozen on asof OR frozen for >=40% of the trailing
    253-session window (fabricated-stable => must not be picked as 'low vol')."""
    hist = price.loc[:asof]
    cols = [c for c in universe if c in hist.columns]
    if not cols:
        return pd.Series(dtype=float)
    win = hist[cols].tail(253)
    if len(win) < 200:
        return pd.Series(dtype=float)
    # frozen fraction over the same trailing window
    fwin = frz_wide.loc[win.index, [c for c in cols if c in frz_wide.columns]]
    frozen_frac = fwin.mean()
    frozen_today = frz_wide.loc[asof, [c for c in cols if c in frz_wide.columns]] if asof in frz_wide.index else pd.Series(False, index=cols)
    logr = np.log(win / win.shift(1)).iloc[1:]
    vol = logr.std(ddof=0)
    vol = vol[(vol > 0) & vol.notna()]
    inv = 1.0 / vol
    # veto frozen names
    bad = set(frozen_frac[frozen_frac >= 0.40].index) | set(frozen_today[frozen_today].index)
    inv = inv[[s for s in inv.index if s not in bad]]
    if len(inv) < 30:
        return pd.Series(dtype=float)
    return inv


# ---- quality + MQ (copied verbatim from build_factor_family.py so schedule/mask can vary) ----
def load_quality():
    q = pd.read_parquet(QUALITY)
    q["fy_end"] = pd.to_datetime(q["fy_end"]); q["avail_date"] = pd.to_datetime(q["avail_date"])
    return q.sort_values(["symbol", "avail_date"])

def quality_scores(qual, asof, universe):
    av = qual[qual["avail_date"] <= asof]
    if av.empty:
        return pd.Series(dtype=float), 0
    last = av.sort_values("avail_date").groupby("symbol").tail(1).set_index("symbol")
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
        s = s.astype(float); m = s.mean(); sd = s.std(ddof=0)
        return (s - m) / (sd + 1e-12) if sd > 0 else s * 0.0
    zr = z(df["roe"]).clip(-3, 3); zd = z(-df["de"]).clip(-3, 3); zs = z(df["stab"]).clip(-3, 3)
    comp = pd.concat([zr, zd, zs], axis=1).mean(axis=1, skipna=True).dropna()
    return comp, len(comp)

def mq_scores_masked(price, qual, frz_wide, asof, universe):
    """MQ = 0.5*z(mom)+0.5*z(quality), momentum-only fallback; exclude frozen-today names."""
    mom = R.momentum_scores(price, asof, universe, exclude_recent_month=True)
    if mom.empty:
        return pd.Series(dtype=float), 0.0
    mom_comp = mom - 1.0
    # veto frozen-today names from selection pool
    if asof in frz_wide.index:
        ft = frz_wide.loc[asof]
        bad = set(ft[ft].index)
        mom_comp = mom_comp[[s for s in mom_comp.index if s not in bad]]
    if len(mom_comp) < 30:
        return pd.Series(dtype=float), 0.0
    q_comp, _ = quality_scores(qual, asof, set(mom_comp.index))
    def z(s):
        sd = s.std(ddof=0); return (s - s.mean()) / (sd + 1e-12) if sd > 0 else s * 0.0
    zm = z(mom_comp); cov = 0.0
    if len(q_comp) >= 10:
        zq = z(q_comp); cov = len(q_comp.index.intersection(mom_comp.index)) / len(mom_comp)
        blended = zm.copy(); common = zm.index.intersection(zq.index)
        blended.loc[common] = 0.5 * zm.loc[common] + 0.5 * zq.reindex(common)
        score = 1.0 + blended
    else:
        score = 1.0 + zm
    return score, cov


# ---------------- schedule ----------------
def rebals_for(tdays, months):
    td = pd.DatetimeIndex(tdays); out = []
    for yr in range(2005, 2027):
        for mo in months:
            md = td[(td.year == yr) & (td.month == mo)]
            if len(md):
                out.append(md.max())
    return sorted(set(out))


# ---------------- masked index builder (mirrors build_index_monthly, generic schedule) ----------------
def build_index(price, ret_close, vol, frz_wide, members, rebals, kind, qual, top_n, cap, seg, tag,
                rebals_per_year):
    tdays = price.index
    daily_ret = ret_close.pct_change()
    # P&L stale guard: zero out returns on frozen (symbol,date) cells so no fabricated move is booked
    frz_ret = frz_wide.reindex(index=daily_ret.index, columns=daily_ret.columns).fillna(False).astype(bool)
    daily_ret = daily_ret.mask(frz_ret, 0.0)

    port_ret_fric = pd.Series(0.0, index=tdays)
    cost_events = {}; covlog = []; prev_w = pd.Series(dtype=float); active_from = None
    tier = SLIP_TIER[seg]

    for i, rb in enumerate(rebals):
        if rb not in tdays:
            continue
        uni = R.members_asof(members, rb)
        if not uni:
            continue
        if kind == "lowvol":
            scores = lowvol_scores_masked(price, frz_wide, rb, uni); qcov = np.nan
            weight_mode = "invvol"
        else:
            scores, qcov = mq_scores_masked(price, qual, frz_wide, rb, uni)
            weight_mode = "mcap"
        if scores is None or scores.empty:
            continue
        top = scores.sort_values(ascending=False).head(top_n)
        sel = list(top.index)
        if len(sel) < max(8, top_n // 3):
            continue
        if weight_mode == "invvol":
            w = top / top.sum()
        else:  # mcap
            liq = price.loc[:rb, sel].iloc[-1] * vol.loc[:rb, sel].tail(20).median()
            raw = (liq.fillna(0) * top).clip(lower=0)
            w = pd.Series(1.0 / len(sel), index=sel) if raw.sum() <= 0 else raw / raw.sum()
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
        end_w = pd.Series(wt[-1], index=seg_syms); prev_w = end_w[end_w > 0]
        if active_from is None:
            active_from = seg_start

    if active_from is None:
        raise RuntimeError(f"[{tag}] no active segments")
    fric = port_ret_fric.loc[active_from:]

    def cost_bps(mult, x=1.0):
        slip = tier * mult * x
        var_bps = 2 * slip + 2 * STT_BPS * x + 2 * EXCH_BPS * x + STAMP_BUY_BPS * x + 2 * SEBI_BPS * x
        gst_bps = GST * (2 * EXCH_BPS * x + 2 * SEBI_BPS * x + BROKERAGE_PER_NAME_BPS * x)
        return (var_bps + gst_bps) / 1e4
    net1 = fric.copy(); net2 = fric.copy()
    for rb, ev in cost_events.items():
        nxt = fric.index[fric.index > rb]
        if len(nxt) == 0:
            continue
        d0 = nxt[0]
        c1 = cost_bps(ev["vol_mult"], 1.0) * ev["turnover"]; c2 = cost_bps(ev["vol_mult"], 2.0) * ev["turnover"]
        net1.loc[d0] = (1 + net1.loc[d0]) * (1 - c1) - 1
        net2.loc[d0] = (1 + net2.loc[d0]) * (1 - c2) - 1
    turn = pd.Series({k: v["turnover"] for k, v in cost_events.items()})
    out = {"fric": (1 + fric).cumprod(), "net1": (1 + net1).cumprod(), "net2": (1 + net2).cumprod(),
           "turnover": turn, "ann_turnover": turn.mean() * rebals_per_year,
           "cov": pd.DataFrame(covlog), "active_from": active_from}
    log(f"[{tag}] rebals={len(cost_events)} {active_from.date()}->{fric.index[-1].date()} "
        f"annTurn~{out['ann_turnover']:.1%} fricCAGR={_cagr(out['fric']):.2%} "
        f"net1={_cagr(out['net1']):.2%} net2={_cagr(out['net2']):.2%}")
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
    s = level.dropna(); return (s / s.cummax() - 1).min() if len(s) > 20 else np.nan

def _cagr_window(level, lo, hi):
    s = level[(level.index >= lo) & (level.index <= hi)].dropna()
    if len(s) < 40:
        return np.nan
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1


# ---------------- N500 total-return hurdle (from D-029 benchmark, mean net + gross) ----------------
def n500_tr_hurdle():
    """The N500 TR hurdle = the random-N500-50 net MEAN (the D-029 firm bar). We report both:
       - net mean 12.74% (post-cost dart-throw) as the '2x-costs vs TR hurdle' comparator, AND
       - gross mean 16.06% as the frictionless TR reference.
    Criterion (a) compares OUR 2x-cost CAGR against the N500 TR hurdle. We use the random-N500-50
    NET mean (12.74%) as the operational TR hurdle number the idea file pre-registered against
    (b uses the same 12.74% for the '1x vs mean' check)."""
    return 12.74, 16.06


def main():
    os.makedirs(OUT, exist_ok=True)
    log("=" * 80); log("I-016 CADENCE TEST — LowVol50 quarterly + MQ50 semiannual (+ monthly restatement, MASKED)")
    log("=" * 80)
    ckpt("load")
    price, ret_close, vol, frz = load_all()
    qual = load_quality()
    n200 = R.apply_aliases(_load_members(N200_XLSX)); n500 = R.apply_aliases(_load_members(N500_XLSX))
    log(f"[members] N500 snaps={len(n500)}")

    schedules = {
        "A_lowvol50_monthly":    ("lowvol", list(range(1, 13)), 12, None),
        "B_lowvol50_quarterly":  ("lowvol", [3, 6, 9, 12],       4, None),
        "C_MQ50_monthly":        ("mq",     list(range(1, 13)), 12, qual),
        "D_MQ50_semiannual":     ("mq",     [6, 12],             2, qual),
    }
    results = {}
    for tag, (kind, months, rpy, q) in schedules.items():
        ckpt(f"build_{tag}")
        log(f"\n[build] {tag} ...")
        rebals = rebals_for(price.index, months)
        res = build_index(price, ret_close, vol, frz, n500, rebals, kind, q, 50, 0.05, "n500", tag, rpy)
        results[tag] = res
        dfnav = pd.DataFrame({"date": res["fric"].index,
                              "nav_frictionless": res["fric"].values,
                              "nav_cost_1x": res["net1"].reindex(res["fric"].index).values,
                              "nav_cost_2x": res["net2"].reindex(res["fric"].index).values})
        dfnav.to_csv(os.path.join(OUT, f"nav_{tag}.csv"), index=False)
        res["cov"].to_csv(os.path.join(OUT, f"coverage_{tag}.csv"), index=False)

    # ---------------- verdict per I-016 pre-registered kills ----------------
    ckpt("verdict")
    hurdle_net, hurdle_gross = n500_tr_hurdle()   # 12.74 / 16.06
    bench_mean_1x = 12.74      # criterion (b) mean-at-1x bar (random-N500-50 net mean)
    bench_p75_net = 19.92      # on-disk net p75 CAGR (hard, conservative floor)
    bench_p75_fric_est = 19.92 + 3.31   # drag-adjusted frictionless-p75 estimate (~23.2%); flagged approx

    rows = []
    for tag, res in results.items():
        cagr_fric = _cagr(res["fric"]) * 100
        cagr_1x = _cagr(res["net1"]) * 100
        cagr_2x = _cagr(res["net2"]) * 100
        mdd = _mdd(res["net2"]) * 100
        # (a) 2x vs N500 TR hurdle by >= +0.5pp/yr full period
        a_margin = cagr_2x - hurdle_net
        a_pass = a_margin >= 0.5
        # (b) beat random mean (12.74) at 1x AND p75 at frictionless
        b_mean_pass = cagr_1x > bench_mean_1x
        b_p75_pass_hard = cagr_fric > bench_p75_net             # vs on-disk net p75 (strict floor)
        b_p75_pass_est = cagr_fric > bench_p75_fric_est          # vs drag-adj frictionless p75 (approx)
        b_pass = b_mean_pass and b_p75_pass_est                  # judge on the frictionless estimate
        # (c) no post-2020 sign flip vs hurdle: full-period excess (2x vs hurdle) and post-2020 excess
        #     must carry the SAME sign (edge doesn't invert in the recent regime).
        post2020 = _cagr_window(res["net2"], pd.Timestamp("2020-01-01"), DATA_MAX) * 100
        c_excess = post2020 - hurdle_net
        full_excess = cagr_2x - hurdle_net
        c_pass = (np.sign(c_excess) == np.sign(full_excess)) and (c_excess > 0 if full_excess > 0 else True)
        # (d) maxDD <= -50% floor (i.e. not worse than -50%)
        d_pass = mdd >= -50.0
        verdict = "PROMOTE-TO-GATE-4" if (a_pass and b_pass and c_pass and d_pass) else "KILL"
        rows.append({"variant": tag, "cagr_fric": round(cagr_fric, 2), "cagr_1x": round(cagr_1x, 2),
                     "cagr_2x": round(cagr_2x, 2), "maxdd_2x": round(mdd, 1),
                     "ann_turnover": round(res["ann_turnover"] * 100, 1),
                     "post2020_2x": round(post2020, 2),
                     "a_2xvsHurdle_margin_pp": round(a_margin, 2), "a_pass": a_pass,
                     "b_mean_pass": b_mean_pass, "b_p75hard_pass": b_p75_pass_hard,
                     "b_p75est_pass": b_p75_pass_est, "b_pass": b_pass,
                     "full_excess_pp": round(full_excess, 2),
                     "c_post2020_excess_pp": round(c_excess, 2), "c_pass": c_pass,
                     "d_maxdd_pass": d_pass, "VERDICT": verdict})
    vdf = pd.DataFrame(rows)
    vdf.to_csv(os.path.join(OUT, "verdict_table.csv"), index=False)

    # turnover comparison monthly vs new cadence
    turn_rows = [
        {"sleeve": "LowVol50", "monthly_annturn_pct": round(results["A_lowvol50_monthly"]["ann_turnover"]*100,1),
         "newcadence": "quarterly", "new_annturn_pct": round(results["B_lowvol50_quarterly"]["ann_turnover"]*100,1)},
        {"sleeve": "MQ50", "monthly_annturn_pct": round(results["C_MQ50_monthly"]["ann_turnover"]*100,1),
         "newcadence": "semiannual", "new_annturn_pct": round(results["D_MQ50_semiannual"]["ann_turnover"]*100,1)},
    ]
    pd.DataFrame(turn_rows).to_csv(os.path.join(OUT, "turnover_comparison.csv"), index=False)

    cfg = {"built": datetime.now().isoformat(timespec="seconds"),
           "engine": ENGINE + " (imported UNCHANGED)",
           "price_panel": PRICE_PANEL, "return_panel": RETURN_PANEL,
           "stale_mask": STALE_MASK + " (212 frozen syms, 0.9% rows; selection veto + P&L zero)",
           "bars": {"hurdle_net_TR": hurdle_net, "hurdle_gross_TR": hurdle_gross,
                    "bench_mean_1x": bench_mean_1x, "bench_p75_net_ondisk": bench_p75_net,
                    "bench_p75_fric_est": round(bench_p75_fric_est,2),
                    "NOTE": "on-disk benchmark percentile paths are NET; frictionless p75 not on disk -> "
                            "estimated as net_p75 + N500-50 cost_drag (3.31pp). Flagged approximation."},
           "data_max": DATA_MAX.date().isoformat()}
    json.dump(cfg, open(os.path.join(OUT, "config.json"), "w"), indent=2)

    log("\n=== VERDICT TABLE ===")
    log(vdf.to_string(index=False))
    log("\n=== TURNOVER COMPARISON ===")
    log(pd.DataFrame(turn_rows).to_string(index=False))
    ckpt("done")
    log(f"\n[done] outputs in {OUT}")


def _load_members(xlsx):
    d = pd.read_excel(xlsx).rename(columns={"Month-Year": "lab", "Ticker": "sym"})
    d["sym"] = d["sym"].astype(str).str.strip().str.upper()
    out = {}
    for lab, g in d.groupby("lab"):
        mon, yr = str(lab)[:3], str(lab)[3:]
        out[pd.Timestamp(year=int(yr), month=R._MONTH_MAP[mon], day=1)] = set(g["sym"])
    return out


if __name__ == "__main__":
    main()
