"""S-04 Gate-4 SENSITIVITY BATTERY — Dr. Sameer Bhat (E-027), 2026-07-04.

Mandatory per RESEARCH_SOP Gate-4: parameter perturbation, plateau check,
subsample stability, decay read. Closes the gap left by tonight's 2x-cost
certification (results/S-04/20260704_cost_cert/), which certified COSTS only.

REUSES the certified pipeline verbatim (shortlist_shortvol.py + dispersion_strategy.py
loaders); does NOT rebuild P&L logic. Center cell (DTE=14, OTM=5%, PT=50%) must
reproduce the registered +0.2241%/spot on n=5031 EXACTLY or the whole grid is void.

GRID (27 cells): entry DTE {12,14,16} x OTM band {4%,5%,6%} x profit-take {40%,50%,60% of credit}
VARIANTS at center (fill-honesty + no-op stop dimension):
  pos        : buyback prints must be >0 (not just finite)   [zero-print guard]
  fresh      : buyback prints must be SAME-DAY (window=0)    [kills +/-15d stale-print fills]
  pos_fresh  : both
  stop{1.5,2.0,2.5} : add stop-loss at cost_bb >= k x credit  [certified config has NO stop]

Pre-registered thresholds (BEFORE computing, per charter):
  PLATEAU  : certified cell within 20% of 26-neighbor median  -> else OVERFIT flag
  SUBSAMPLE: edge sign stable across years/IV-terciles/odd-even -> sign flip = flag
  PERTURB  : no grid cell sign-flips; cost-sensitivity <50% of edge (from cost cert)
Edges reported in %/spot AND rupees per Rs.6,00,000 lot (denominator rule).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "results/S-04/20260704_sensitivity"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/lib"))
sys.path.insert(0, str(ROOT / "intraday_options_strategy/buying"))
import guards as G                    # firm guards — imported, not copy-pasted
import dispersion_strategy as ds      # SOPT, _series, _nearest, price semantics
import shortlist_shortvol as ss       # combined_close, near, SLIP — the certified pipeline

SLIP = ss.SLIP                        # 0.021/leg, baked exactly as in the certified run
NOTIONAL = 600_000.0                  # Rs per lot (cost-cert convention)
DTE_GRID = [12, 14, 16]
OTM_GRID = [0.04, 0.05, 0.06]
PT_GRID = [0.4, 0.5, 0.6]
CENTER = (14, 0.05, 0.5)
STOP_GRID = [1.5, 2.0, 2.5]
L7B_MAX = 0.06                        # same physical-bound drop rule as certified builder


class PriceBook:
    """Per-expiry-file lazy cache over ds._series/_nearest. Same semantics, no re-filtering."""

    def __init__(self, df):
        self.df = df
        self._ser = {}

    def series(self, strike, otype):
        key = (strike, otype)
        if key not in self._ser:
            self._ser[key] = ds._series(self.df, strike, otype)
        return self._ser[key]

    def px(self, strike, otype, day, window=15):
        """(price, print_date) nearest print within +/-window calendar days."""
        return ds._nearest(self.series(strike, otype), day, window)


def scan_managed(book, kp, kc, later, credit, pt_list, stops, fresh=False, pos=False):
    """One pass over later sessions; returns dict keyed by ('pt',pt) / ('stop',k):
    (managed_pnl, exit_day, stale_days) or None if never triggered.
    Mirrors certified logic exactly when fresh=pos=False, stops=[]."""
    out = {}
    pending_pt = set(pt_list)
    pending_st = set(stops)
    win = 0 if fresh else 15
    for d in later:
        if not pending_pt and not pending_st:
            break
        cc, dc = book.px(kc, "CE", d, win)
        pp, dp = book.px(kp, "PE", d, win)
        if not (np.isfinite(cc) and np.isfinite(pp)):
            continue
        if pos and not (cc > 0 and pp > 0):
            continue
        cost_bb = (cc + pp) * (1 + SLIP)
        stale = max(abs((pd.Timestamp(dc) - pd.Timestamp(d)).days),
                    abs((pd.Timestamp(dp) - pd.Timestamp(d)).days))
        for pt in sorted(pending_pt):
            if cost_bb <= pt * credit:
                out[("pt", pt)] = (credit * (1 - SLIP) - cost_bb, d, stale)
                pending_pt.discard(pt)
        for k in sorted(pending_st):
            # stop fires only if the PT for the paired config (0.5) has not fired this day
            if cost_bb >= k * credit and not cost_bb <= 0.5 * credit:
                out[("stop", k)] = (credit * (1 - SLIP) - cost_bb, d, stale)
                pending_st.discard(k)
    return out


def build():
    t0 = time.time()
    C = ss.combined_close()
    stocks = sorted({p.name for p in ds.SOPT.iterdir() if p.is_dir()})
    recs = []
    nfiles = 0
    for si, sym in enumerate(stocks):
        if sym not in C.columns:
            continue
        cser = C[sym].dropna()
        data_end = cser.index.max().date()                       # L7 guard (as certified)
        for p in sorted((ds.SOPT / sym).glob("*.parquet")):
            exp = dt.date.fromisoformat(p.stem)
            if exp > data_end:
                continue
            try:
                df = pq.read_table(p).to_pandas()
                df["trading_day"] = pd.to_datetime(df["trading_day"].astype(str))
            except Exception:
                continue
            tdays = sorted(df["trading_day"].dt.date.unique())
            if len(tdays) < 5:
                continue
            nfiles += 1
            schema = G.option_schema(df)                          # L6 era tag
            book = PriceBook(df)
            spot_x = cser.asof(pd.Timestamp(exp))
            if not np.isfinite(spot_x):
                continue

            for dte in DTE_GRID:
                target = exp - dt.timedelta(days=dte)
                cands = [d for d in tdays if d >= target and d < exp]
                entry = cands[0] if cands else tdays[0]
                later = [d for d in tdays if entry < d < exp]
                spot_e = cser.asof(pd.Timestamp(entry))
                if not (np.isfinite(spot_e) and spot_e > 0):
                    continue
                strikes = sorted(df["strike"].unique())
                # jade-lizard legs are part of the certified SAMPLE FILTER — replicate
                kc_js = ss.near(strikes, spot_e * (1 + ss.JL_C_SHORT))
                kc_jl = ss.near(strikes, spot_e * (1 + ss.JL_C_LONG))
                for otm in OTM_GRID:
                    kp = ss.near(strikes, spot_e * (1 - otm))
                    kc = ss.near(strikes, spot_e * (1 + otm))
                    if None in (kp, kc, kc_js, kc_jl) or not (kc_jl > kc_js > spot_e and kp < spot_e):
                        continue
                    p_put, _ = book.px(kp, "PE", entry)
                    c_call, _ = book.px(kc, "CE", entry)
                    jc_s, _ = book.px(kc_js, "CE", entry)
                    jc_l, _ = book.px(kc_jl, "CE", entry)
                    if not all(np.isfinite(x) and x > 0 for x in (p_put, c_call, jc_s, jc_l)):
                        continue
                    credit = c_call + p_put
                    cintr = max(0.0, spot_x - kc)
                    pintr = max(0.0, kp - spot_x)
                    hold = (c_call * (1 - SLIP) - cintr * (1 + SLIP)
                            + p_put * (1 - SLIP) - pintr * (1 + SLIP))

                    is_center_slice = (dte == CENTER[0] and otm == CENTER[1])
                    res = scan_managed(book, kp, kc, later, credit, PT_GRID, [])
                    for pt in PT_GRID:
                        hit = res.get(("pt", pt))
                        managed = hit[0] if hit else hold
                        recs.append({
                            "cfg": f"dte{dte}_otm{int(otm*100)}_pt{int(pt*100)}",
                            "kind": "grid", "dte": dte, "otm": otm, "pt": pt,
                            "sym": sym, "exp": str(exp), "entry": str(entry),
                            "spot": spot_e, "credit_pct": credit / spot_e,
                            "hold": hold / spot_e, "managed": managed / spot_e,
                            "early": hit is not None,
                            "stale_days": hit[2] if hit else -1,
                            "schema": schema,
                        })
                    if is_center_slice:
                        # fill-honesty variants (PT=0.5 only)
                        for name, fresh, pos in [("pos", False, True),
                                                 ("fresh", True, False),
                                                 ("pos_fresh", True, True)]:
                            r2 = scan_managed(book, kp, kc, later, credit, [0.5], [],
                                              fresh=fresh, pos=pos)
                            hit = r2.get(("pt", 0.5))
                            managed = hit[0] if hit else hold
                            recs.append({
                                "cfg": f"variant_{name}", "kind": "variant",
                                "dte": dte, "otm": otm, "pt": 0.5,
                                "sym": sym, "exp": str(exp), "entry": str(entry),
                                "spot": spot_e, "credit_pct": credit / spot_e,
                                "hold": hold / spot_e, "managed": managed / spot_e,
                                "early": hit is not None,
                                "stale_days": hit[2] if hit else -1,
                                "schema": schema,
                            })
                        # add-a-stop variants (PT=0.5 + stop k)
                        r3 = scan_managed(book, kp, kc, later, credit, [0.5], STOP_GRID)
                        pt_hit = r3.get(("pt", 0.5))
                        for k in STOP_GRID:
                            st_hit = r3.get(("stop", k))
                            # first trigger wins
                            use = None
                            if pt_hit and st_hit:
                                use = pt_hit if pt_hit[1] <= st_hit[1] else st_hit
                            else:
                                use = pt_hit or st_hit
                            managed = use[0] if use else hold
                            recs.append({
                                "cfg": f"variant_stop{k}", "kind": "variant",
                                "dte": dte, "otm": otm, "pt": 0.5,
                                "sym": sym, "exp": str(exp), "entry": str(entry),
                                "spot": spot_e, "credit_pct": credit / spot_e,
                                "hold": hold / spot_e, "managed": managed / spot_e,
                                "early": use is not None,
                                "stale_days": use[2] if use else -1,
                                "schema": schema,
                            })
        if (si + 1) % 25 == 0 or si == len(stocks) - 1:
            el = time.time() - t0
            msg = f"[{si+1}/{len(stocks)}] {sym}  files={nfiles} recs={len(recs)}  {el:.0f}s"
            print(msg, flush=True)
            (OUT / "progress.txt").write_text(msg, encoding="utf-8")
            pd.DataFrame(recs).to_parquet(OUT / "_partial_trades.parquet")
    T = pd.DataFrame(recs)
    T.to_parquet(OUT / "trades_all_configs.parquet")
    print(f"BUILD DONE {len(T)} recs, {nfiles} files, {time.time()-t0:.0f}s", flush=True)
    return T


def l7b_drop(g):
    """Same physical-bound drop rule as the certified builder."""
    viol = (g["managed"] > L7B_MAX) | (g["hold"] > L7B_MAX)
    return g[~viol], int(viol.sum())


def analyse(T):
    rows = []
    for cfg, g in T.groupby("cfg"):
        g, ndrop = l7b_drop(g)
        m = g["managed"]
        rows.append({
            "cfg": cfg, "kind": g["kind"].iloc[0],
            "dte": g["dte"].iloc[0], "otm": g["otm"].iloc[0], "pt": g["pt"].iloc[0],
            "n": len(g), "l7b_dropped": ndrop,
            "edge_pct_spot": m.mean() * 100, "edge_med_pct": m.median() * 100,
            "edge_rs_per_lot": m.mean() * NOTIONAL,
            "hit_rate": (m > 0).mean(), "early_exit_rate": g["early"].mean(),
            "worst_trade_pct": m.min() * 100, "std_pct": m.std() * 100,
        })
    GR = pd.DataFrame(rows).sort_values(["kind", "dte", "otm", "pt"])
    GR.to_csv(OUT / "grid.csv", index=False)
    print("grid.csv written:", len(GR), "configs", flush=True)

    grid = GR[GR["kind"] == "grid"].copy()
    ckey = f"dte{CENTER[0]}_otm{int(CENTER[1]*100)}_pt{int(CENTER[2]*100)}"
    cent = grid[grid["cfg"] == ckey].iloc[0]
    nbr = grid[grid["cfg"] != ckey]["edge_pct_spot"]
    plateau = {
        "center_cfg": ckey,
        "center_edge_pct": float(cent["edge_pct_spot"]),
        "center_n": int(cent["n"]),
        "neighbor_median_pct": float(nbr.median()),
        "neighbor_min_pct": float(nbr.min()), "neighbor_max_pct": float(nbr.max()),
        "center_vs_median_ratio": float(cent["edge_pct_spot"] / nbr.median()),
        "cells_negative": int((grid["edge_pct_spot"] <= 0).sum()),
        "best_cfg": grid.loc[grid["edge_pct_spot"].idxmax(), "cfg"],
        "best_edge_pct": float(grid["edge_pct_spot"].max()),
        "best_vs_neighborhood_median": float(grid["edge_pct_spot"].max() / nbr.median()),
        "worst_cfg": grid.loc[grid["edge_pct_spot"].idxmin(), "cfg"],
        "worst_edge_pct": float(grid["edge_pct_spot"].min()),
    }

    # ---- subsamples on the CENTER config trade set ----
    g = T[T["cfg"] == ckey].copy()
    g, _ = l7b_drop(g)
    g["exp_d"] = pd.to_datetime(g["exp"])
    g = g.sort_values(["entry", "sym"]).reset_index(drop=True)
    subs = []

    def sub(name, mask):
        x = g.loc[mask, "managed"]
        if len(x) == 0:
            return
        subs.append({"slice": name, "n": len(x), "edge_pct_spot": x.mean() * 100,
                     "edge_rs_per_lot": x.mean() * NOTIONAL, "hit_rate": (x > 0).mean(),
                     "worst_pct": x.min() * 100})

    for y, gy in g.groupby(g["exp_d"].dt.year):
        sub(f"year_{y}", g.index.isin(gy.index))
    q1, q2 = g["credit_pct"].quantile([1 / 3, 2 / 3])
    sub("iv_tercile_low(credit)", g["credit_pct"] <= q1)
    sub("iv_tercile_mid", (g["credit_pct"] > q1) & (g["credit_pct"] <= q2))
    sub("iv_tercile_high", g["credit_pct"] > q2)
    sub("odd_trades", g.index % 2 == 1)
    sub("even_trades", g.index % 2 == 0)
    sub("build_le2024", g["exp_d"] <= "2024-12-31")
    sub("fwd_gt2024", g["exp_d"] > "2024-12-31")
    sub("regime_2022_rateshock", g["exp_d"].dt.year == 2022)
    sub("regime_2024_election(AprJun)",
        (g["exp_d"] >= "2024-04-01") & (g["exp_d"] <= "2024-06-30"))
    sub("regime_2026_ytd", g["exp_d"] >= "2026-01-01")
    sub("era_minute_schema(HF)", g["schema"] == "minute")
    sub("era_daily_schema(bhavcopy)", g["schema"] == "daily")
    SU = pd.DataFrame(subs)
    SU.to_csv(OUT / "subsamples.csv", index=False)

    # ---- stale-print exposure on center config (fill-optimism evidence) ----
    tr = g[g["early"]]
    stale = {
        "early_exits_n": int(len(tr)),
        "stale0d_frac": float((tr["stale_days"] == 0).mean()),
        "stale_gt2d_frac": float((tr["stale_days"] > 2).mean()),
        "stale_gt5d_frac": float((tr["stale_days"] > 5).mean()),
        "stale_max_days": int(tr["stale_days"].max()) if len(tr) else None,
    }

    # ---- bootstrap CI on the center headline ----
    rng = np.random.default_rng(42)
    m = g["managed"].values
    boots = np.concatenate([
        rng.choice(m, size=(500, len(m)), replace=True).mean(axis=1)
        for _ in range(20)])
    ci = np.percentile(boots, [2.5, 97.5]) * 100

    # ---- decay read ----
    yr = g.groupby(g["exp_d"].dt.year)["managed"].mean() * 100
    yrs = yr.index.values.astype(float)
    def fit(x, y):
        b, a = np.polyfit(x, y, 1)
        return float(b), float(a), float(-a / b) if b < 0 else None
    b_all, a_all, zero_all = fit(yrs, yr.values)
    m25 = yrs <= 2025
    b_25, a_25, zero_25 = fit(yrs[m25], yr.values[m25])
    bm = g[g["exp_d"] <= "2024-12-31"]; fm = g[g["exp_d"] > "2024-12-31"]
    t_b = bm["exp_d"].mean(); t_f = fm["exp_d"].mean()
    slope_bf = (fm["managed"].mean() - bm["managed"].mean()) * 100 / ((t_f - t_b).days / 365.25)
    zero_bf = t_f + pd.Timedelta(days=365.25 * (fm["managed"].mean() * 100 / -slope_bf)) \
        if slope_bf < 0 else None
    decay = {
        "yearly_edge_pct": {int(k): round(float(v), 4) for k, v in yr.items()},
        "build_edge_pct": float(bm["managed"].mean() * 100), "build_n": len(bm),
        "fwd_edge_pct": float(fm["managed"].mean() * 100), "fwd_n": len(fm),
        "build_midpoint": str(t_b.date()), "fwd_midpoint": str(t_f.date()),
        "slope_buildfwd_pct_per_yr": float(slope_bf),
        "zero_cross_buildfwd": str(zero_bf.date()) if zero_bf is not None else "no decay",
        "slope_yearly_all_pct_per_yr": b_all,
        "zero_cross_yearly_all": round(zero_all, 1) if zero_all else "no decay",
        "slope_yearly_ex2026_pct_per_yr": b_25,
        "zero_cross_yearly_ex2026": round(zero_25, 1) if zero_25 else "no decay",
    }

    variants = GR[GR["kind"] == "variant"][
        ["cfg", "n", "edge_pct_spot", "edge_rs_per_lot", "hit_rate",
         "early_exit_rate", "worst_trade_pct"]]

    summary = {
        "run": "20260704_sensitivity", "owner": "Dr. Sameer Bhat (E-027)",
        "center_reproduction": {
            "expected_edge_pct": 0.2241, "got_edge_pct": float(cent["edge_pct_spot"]),
            "expected_n": 5031, "got_n": int(cent["n"]),
            "exact": bool(abs(cent["edge_pct_spot"] - 0.2241) < 0.0005
                          and int(cent["n"]) == 5031),
        },
        "plateau": plateau,
        "bootstrap_CI95_center_pct": [round(float(ci[0]), 4), round(float(ci[1]), 4)],
        "stale_print_exposure": stale,
        "decay": decay,
        "trials_added_to_family_ledger": int(GR["cfg"].nunique()),
        "grid_dims": {"dte": DTE_GRID, "otm": OTM_GRID, "pt": PT_GRID,
                      "stops_tested": STOP_GRID,
                      "note": "certified config has NO stop-loss; stop dim is additive"},
    }
    (OUT / "config.json").write_text(json.dumps(summary, indent=2, default=str),
                                     encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str), flush=True)
    print("\nVARIANTS:\n", variants.to_string(index=False), flush=True)
    print("\nSUBSAMPLES:\n", SU.to_string(index=False), flush=True)
    print("\nGRID:\n", grid[["cfg", "n", "edge_pct_spot", "edge_rs_per_lot",
                             "hit_rate", "early_exit_rate",
                             "worst_trade_pct"]].to_string(index=False), flush=True)


if __name__ == "__main__":
    cached = OUT / "trades_all_configs.parquet"
    if cached.exists() and "--rebuild" not in sys.argv:
        print("using cached trades_all_configs.parquet", flush=True)
        T = pd.read_parquet(cached)
    else:
        T = build()
    analyse(T)
