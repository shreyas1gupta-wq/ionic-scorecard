"""PORTFOLIOS RE-FIT -- BOTH corrections applied together (2026-08-03, Vikram Shah).
Correction 1: BOOK's AU relabeled at its TRUE native unit (Rs1cr, not the mislabeled Rs10L).
  VERIFIED NUMERICALLY (this script, section 0): hist['BOOK'] loaded from
  FINAL_RANKING_20260730/all_sleeves_daily.json sums to Rs 864,397.88 over 942 days; the RAW
  STACKED_BOOK_20260711/book_daily_pnl.csv 'total' column sums to Rs 8,643,978.85 over the same
  942 days -- EXACTLY 10x larger. So the json's 'BOOK' series is already the raw P&L PRE-DIVIDED
  by 10 ("Rs10L-equivalent" per chart_data.json's note). recost_and_rebuild.py's portfolio-scale
  factor is scale = w*(TOTAL_CAPITAL/NATURAL_CAP) = w*10 (both NATURAL_CAP and TOTAL_CAPITAL fixed
  at Rs10L/Rs1cr for every sleeve alike). Applied to the /10 series: w*10*(raw/10) = w*raw -- i.e.
  the code's dollar P&L contribution from BOOK ALREADY equals w*raw_book_pnl, which is the
  mathematically CORRECT contribution for a sleeve whose true native/tested size is Rs1cr (to
  deploy w fraction of a Rs1cr fund into a Rs1cr-native sleeve, you scale its own native P&L by
  exactly w). CONCLUSION: the $-P&L / CAGR / MaxDD numbers already reported for BOOK and for the
  3 mandates in PORTFOLIOS_RECOST.md are NOT invalidated by this bug -- the bug lives entirely in
  the DESCRIPTIVE AU-multiple used to describe BOOK's capacity utilisation (w*10 "AU at Rs10L-native"
  is the WRONG denominator; the correct one is w*1 "AU at Rs1cr-native", exactly per CAPACITY_WRITEUP
  section 3). This script computes both the corrected AU labels AND explores whether the now-confirmed
  capacity headroom justifies loosening BOOK/SWEEP's per-mandate weight caps (CAP_TABLE), which DOES
  change $ numbers.

Correction 2: SWEEP's forward per-trade edge, using the flat-spot-24000 method (Tara Singh,
  CAPACITY_WRITEUP/STT_RECOST) that gives 10.941 -> 3.741 pts/trade, INSTEAD of the real-per-trade-
  contemporaneous-spot method already used in PORTFOLIOS_RECOST.md's recost_and_rebuild.py (verified
  in this script to give 10.941 -> 6.512 pts/trade -- a materially SMALLER cost hit, because SWEEP's
  11.3-year trade history has mean entry spot of 14,759, only 61% of today's ~24,000, so a flat-
  today's-spot assumption applied to 2015-2020-era trades overstates their forward cost). Both are
  computed and reported; the task's instruction is followed (3.741 basis used for the headline
  re-fit) and the discrepancy is flagged loudly as an open methodological question for Quant Head.
"""
from __future__ import annotations
import json, warnings, gc
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
         r"\Shreyas_Ionic_AMC\04_RND_LAB\results")
OUT = R / "PORTFOLIOS_REFIT_20260803"
OUT.mkdir(exist_ok=True, parents=True)

NATURAL_CAP = 1_000_000.0     # Rs10L -- unchanged for SWEEP/CALENDAR/OVERSHOOT/LD_SELL
NATURAL_CAP_BOOK_TRUE = 10_000_000.0   # Rs1cr -- BOOK's TRUE native unit (correction 1)
TOTAL_CAPITAL = 1_00_00_000.0
SLEEVES = ["SWEEP", "CALENDAR", "OVERSHOOT", "LD_SELL", "BOOK"]

STT_FUT_OLD, STT_FUT_NEW = 0.0002, 0.0005
STT_OPT_OLD, STT_OPT_NEW = 0.0010, 0.0015
D_OPT = STT_OPT_NEW - STT_OPT_OLD

LOT_SWEEP, LOT_CALENDAR, LOT_OVERSHOOT, LOT_LD_SELL, LOT_S1F = 75, 75, 65, 65, 75
N_LOTS_S1F = 3
B1B_NOTIONAL = 50_00_000.0
PREM_ASSUMED_CALENDAR = 150.0
PREM_ASSUMED_OVERSHOOT = 60.0
PREM_ASSUMED_S1F = 110.0
SWEEP_FLAT_SPOT = 24000.0   # Tara/capacity-desk reference spot for the flat-delta method

# ==================================================================== 0. LOAD + VERIFY THE BOOK UNIT BUG
raw = json.load(open(R / "FINAL_RANKING_20260730" / "all_sleeves_daily.json"))
hist = {}
for item in raw:
    s = pd.Series(item["daily"], dtype=float)
    s.index = pd.to_datetime(s.index)
    hist[item["name"]] = s.sort_index()

bk_raw = pd.read_csv(R / "STACKED_BOOK_20260711" / "book_daily_pnl.csv", index_col=0, parse_dates=True)
book_json_sum = float(hist["BOOK"].sum())
book_raw_sum = float(bk_raw["total"].sum())
print("=== SECTION 0: BOOK unit-bug verification ===")
print(f"hist['BOOK'] (from all_sleeves_daily.json) sum = Rs{book_json_sum:,.2f} over {len(hist['BOOK'])} days")
print(f"book_daily_pnl.csv 'total' (RAW) sum         = Rs{book_raw_sum:,.2f} over {len(bk_raw)} days")
print(f"ratio raw/json = {book_raw_sum/book_json_sum:.4f}  (confirms hist['BOOK'] = raw/10, i.e. "
      f"'Rs10L-equivalent' pre-scaling is REAL in the data, not just a mislabeled comment)")
print("CONCLUSION: portfolio $ contribution from BOOK = w*10*(raw/10) = w*raw -- already correct.")
print("            The bug is the AU-multiple LABEL only: true_AU = w (native Rs1cr), not w*10 (mislabeled Rs10L).\n")

# ==================================================================== 1. SWEEP forward edge -- both methods
t = pd.read_csv(R / "SWEEP_11YR_20260729" / "trades_E_swing3_trail60_1lot.csv")
t["date"] = pd.to_datetime(t["date"])
sell_leg_spot = np.where(t["dir"] > 0, t["exit"], t["entry"])

delta_real_rs = (STT_FUT_NEW - STT_FUT_OLD) * sell_leg_spot * LOT_SWEEP
delta_flat_rs = (STT_FUT_NEW - STT_FUT_OLD) * SWEEP_FLAT_SPOT * LOT_SWEEP  # scalar, same for every trade

old_avg_pts = t["net"].mean() / LOT_SWEEP
fwd_real_avg_pts = (t["net"] - delta_real_rs).mean() / LOT_SWEEP
fwd_flat_avg_pts = (t["net"] - delta_flat_rs).mean() / LOT_SWEEP
print("=== SECTION 1: SWEEP forward-edge method comparison ===")
print(f"OLD-STT avg net pts/trade          : {old_avg_pts:.3f}  (matches CAPACITY_WRITEUP's 10.941)")
print(f"FWD real-per-trade-spot avg pts/trade: {fwd_real_avg_pts:.3f}  (mean entry spot {t['entry'].mean():,.0f}, "
      f"already embedded in PORTFOLIOS_RECOST.md's FORWARD SWEEP standalone CAGR 9.79%)")
print(f"FWD flat-spot-{SWEEP_FLAT_SPOT:.0f} avg pts/trade   : {fwd_flat_avg_pts:.3f}  (matches CAPACITY_WRITEUP's 3.741 "
      f"-- task's instructed basis)")
print("FLAGGED DISCREPANCY: the flat-spot method applies TODAY's spot to trades back to 2015 (mean spot "
      f"then ~{t[t['date']<'2020-01-01']['entry'].mean():,.0f}), overstating cost on ~87% of the trade history. "
      "Using per THE TASK'S EXPLICIT INSTRUCTION anyway for the headline re-fit; both shown throughout.\n")

# ---- build SWEEP forward delta series both ways, date-aggregated (same convention as recost_and_rebuild.py)
t["delta_real"] = delta_real_rs
t["delta_flat"] = delta_flat_rs
delta_sweep_real = t.groupby(t["date"].dt.normalize())["delta_real"].sum().sort_index()
delta_sweep_flat = t.groupby(t["date"].dt.normalize())["delta_flat"].sum().sort_index()

# ==================================================================== 2. Other sleeve deltas (UNCHANGED from
#            recost_and_rebuild.py -- CALENDAR/OVERSHOOT/LD_SELL/BOOK, all immaterial or already-correct)
rc = pd.read_csv(R / "RATIO_CALENDAR_20260730" / "grid_a_trades_raw.csv")
c = rc[(rc.strike_struct == "ATM_ATM") & (rc.ratio == "1x1") & (rc.exit_variant == "3d_before")]
c = c.drop_duplicates(subset=["day0", "near_expiry"]).copy()
c["exit_day"] = pd.to_datetime(c["exit_day"])
c["delta_rs"] = D_OPT * PREM_ASSUMED_CALENDAR * LOT_CALENDAR
delta_calendar = c.groupby(c["exit_day"].dt.normalize())["delta_rs"].sum().sort_index()

ov_active = hist["OVERSHOOT"][hist["OVERSHOOT"] != 0]
delta_per_day_ov = D_OPT * PREM_ASSUMED_OVERSHOOT * LOT_OVERSHOOT
delta_overshoot = pd.Series(delta_per_day_ov, index=ov_active.index)

ld = pd.read_csv(R / "LONGDATED_SELLING_20260730" / "best_config_trades.csv")
ld["exit_day"] = pd.to_datetime(ld["exit_day"])
ld["delta_rs"] = D_OPT * ld["credit_pt"] * LOT_LD_SELL
delta_ldsell = ld.groupby(ld["exit_day"].dt.normalize())["delta_rs"].sum().sort_index()

bk = pd.read_csv(R / "STACKED_BOOK_20260711" / "book_daily_pnl.csv", index_col=0, parse_dates=True)
s1f_days = bk.index[bk["s1f"] != 0]
b1b_days = bk.index[bk["b1b"] != 0]
d_s1f = D_OPT * PREM_ASSUMED_S1F * LOT_S1F * N_LOTS_S1F
d_b1b = (STT_FUT_NEW - STT_FUT_OLD) * B1B_NOTIONAL
book_delta_full = pd.Series(0.0, index=bk.index)
book_delta_full.loc[s1f_days] += d_s1f
book_delta_full.loc[b1b_days] += d_b1b
# book_delta_full is on the RAW (Rs1cr-native) scale; hist['BOOK'] is /10, so its delta must also be /10
# to stay dimensionally consistent with hist['BOOK'] before we do fwd = hist - delta
delta_book_scaled = (book_delta_full[book_delta_full != 0]) / 10.0

# ==================================================================== 3. Build FORWARD series (two SWEEP variants)
def build_fwd(sweep_delta):
    fwd = {}
    for k in SLEEVES:
        if k == "SWEEP":
            d = sweep_delta
        elif k == "CALENDAR":
            d = delta_calendar
        elif k == "OVERSHOOT":
            d = delta_overshoot
        elif k == "LD_SELL":
            d = delta_ldsell
        elif k == "BOOK":
            d = delta_book_scaled
        d = d.reindex(hist[k].index).fillna(0.0)
        fwd[k] = hist[k] - d
    return fwd

fwd_flat = build_fwd(delta_sweep_flat)    # HEADLINE per task instruction (3.741 basis)
fwd_real = build_fwd(delta_sweep_real)    # sensitivity cross-check (6.512 basis, = PORTFOLIOS_RECOST.md's own)

# ==================================================================== 4. Portfolio-build machinery (identical
#            to recost_and_rebuild.py / build_portfolios.py)
CAP_TABLE_ORIG = pd.DataFrame({
    "LOW_RISK":  {"SWEEP": 0.25, "CALENDAR": 0.20, "OVERSHOOT": 0.08, "LD_SELL": 0.10, "BOOK": 0.25},
    "HIGH_CAGR": {"SWEEP": 0.50, "CALENDAR": 0.50, "OVERSHOOT": 0.25, "LD_SELL": 0.35, "BOOK": 0.50},
    "BALANCED":  {"SWEEP": 0.35, "CALENDAR": 0.35, "OVERSHOOT": 0.15, "LD_SELL": 0.20, "BOOK": 0.35},
}).reindex(SLEEVES)

# LOOSENED variant: capacity confirmed non-binding for SWEEP (719x headroom) and BOOK (under-deployed,
# not over) -- raise ONLY these two sleeves' per-mandate ceilings. CALENDAR/OVERSHOOT/LD_SELL caps are
# LEFT UNCHANGED (their caps are crash-risk/thin-sample driven, per build_portfolios.py's own docstring
# lines 305-313 -- unrelated to capacity, task explicitly says do not loosen these).
CAP_TABLE_LOOSE = CAP_TABLE_ORIG.copy()
for pname in ["LOW_RISK", "HIGH_CAGR", "BALANCED"]:
    CAP_TABLE_LOOSE.loc["SWEEP", pname] = min(1.0, CAP_TABLE_ORIG.loc["SWEEP", pname] * 2.0)
    CAP_TABLE_LOOSE.loc["BOOK", pname] = min(1.0, CAP_TABLE_ORIG.loc["BOOK", pname] * 2.0)

MANDATE_CFG = {
    "LOW_RISK": dict(objective="CAGR", mdd_limit=10.0, gross_cap=1.0, cagr_floor=6.0),
    "HIGH_CAGR": dict(objective="CAGR", mdd_limit=25.0, gross_cap=2.5, cagr_floor=6.0),
    "BALANCED": dict(objective="CALMAR", mdd_limit=25.0, gross_cap=1.5, cagr_floor=8.0),
}
SEEDS = {"LOW_RISK": 101, "HIGH_CAGR": 202, "BALANCED": 303}


def cap_and_renorm(w, cap, target_sum=1.0, n_iter=50):
    w = np.array(w, dtype=float)
    cap = np.broadcast_to(np.asarray(cap, dtype=float), w.shape).astype(float).copy()
    w = w / w.sum() * target_sum if w.sum() > 0 else w.copy()
    capped = np.zeros_like(w, dtype=bool)
    for _ in range(n_iter):
        over = (w > cap) & (~capped)
        if not over.any():
            break
        excess = (w[over] - cap[over]).sum()
        w[over] = cap[over]
        capped |= over
        free = ~capped
        if not free.any() or w[free].sum() <= 0:
            break
        w[free] += excess * (w[free] / w[free].sum())
    return np.minimum(w, cap)


def eq_metrics(s: pd.Series, cap: float) -> dict:
    s = s.sort_index()
    eq = cap + s.cumsum()
    pk = eq.cummax()
    dd = (eq - pk) / pk
    yrs = max((s.index.max() - s.index.min()).days / 365.25, .01)
    cagr = (float(eq.iloc[-1]) / cap) ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else np.nan
    r = s / cap
    sh = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan
    mo = s.resample("ME").sum()
    return dict(CAGR_pct=round(100 * cagr, 2) if np.isfinite(cagr) else None,
                maxDD_pct=round(100 * float(dd.min()), 2),
                Calmar=round(float(cagr / abs(dd.min())), 3) if dd.min() else None,
                Sharpe=round(sh, 2) if np.isfinite(sh) else None,
                month_win_pct=round(100 * float((mo > 0).mean()), 1),
                net_rs=round(float(s.sum())))


def _batch_eval(M, W, cap, yrs):
    n = W.shape[0]
    cagr = np.empty(n); mdd = np.empty(n); sharpe = np.empty(n); calmar = np.empty(n)
    CHUNK = 1500
    for s in range(0, n, CHUNK):
        w_chunk = W[s:s + CHUNK]
        paths = (M @ w_chunk.T).astype(np.float64)
        eq = cap + np.cumsum(paths, axis=0)
        pk = np.maximum.accumulate(eq, axis=0)
        dd = (eq - pk) / pk
        mdd[s:s + CHUNK] = dd.min(axis=0)
        cagr[s:s + CHUNK] = np.where(eq[-1] > 0, (eq[-1] / cap) ** (1 / yrs) - 1, -1.0)
        r = paths / cap
        rstd = r.std(axis=0)
        sharpe[s:s + CHUNK] = np.where(rstd > 0, r.mean(axis=0) / rstd * np.sqrt(252), -1.0)
        calmar[s:s + CHUNK] = np.where(mdd[s:s + CHUNK] < -1e-9,
                                        cagr[s:s + CHUNK] / np.abs(mdd[s:s + CHUNK]), -1.0)
        del paths, eq, pk, dd
    gc.collect()
    return cagr, mdd, sharpe, calmar


def scan_weights(mat, n_samples, w_cap, gross_cap, objective, mdd_limit, seed, cagr_floor=None):
    rng = np.random.default_rng(seed)
    k = len(SLEEVES)
    dirs = rng.dirichlet(np.ones(k) * 2.0, size=n_samples)
    dirs = np.array([cap_and_renorm(row, w_cap, 1.0) for row in dirs])
    gross = rng.uniform(0.02, gross_cap, size=n_samples)
    W = dirs * gross[:, None]
    W = np.minimum(W, w_cap[None, :])   # re-enforce per-sleeve cap post-gross-scaling (see bug note above)
    scale = W * (TOTAL_CAPITAL / NATURAL_CAP)
    M = mat[SLEEVES].values
    cap = TOTAL_CAPITAL
    yrs = max((mat.index.max() - mat.index.min()).days / 365.25, .01)
    cagr, mdd, sharpe, calmar = _batch_eval(M, scale, cap, yrs)
    feasible = np.ones(n_samples, dtype=bool)
    if mdd_limit is not None:
        feasible &= (mdd >= -mdd_limit / 100.0)
    if cagr_floor is not None:
        feasible &= (cagr >= cagr_floor / 100.0)
    if not feasible.any():
        feasible = np.ones(n_samples, dtype=bool)
        best = int(np.argmax(mdd))
    else:
        obj_val = cagr if objective == "CAGR" else (calmar if objective == "CALMAR" else sharpe)
        obj_val = np.where(feasible, obj_val, -np.inf)
        best = int(np.argmax(obj_val))
    w_best = W[best].copy()
    info = dict(CAGR_pct=round(100 * cagr[best], 2), maxDD_pct=round(100 * mdd[best], 2),
                Sharpe=round(sharpe[best], 2), Calmar=round(calmar[best], 3), feasible=bool(feasible[best]))
    return w_best, info


def combined(mat, w, total_capital=TOTAL_CAPITAL):
    scale = w * (total_capital / NATURAL_CAP)
    return (mat[SLEEVES].values * scale).sum(axis=1)


def cppi_overlay(mat, w_base, idx, cap, floor_dd=0.06, deleverage_to=0.35, recover_dd=0.02):
    raw_ = combined(mat, w_base)
    s = pd.Series(raw_, index=idx)
    out = np.zeros(len(s))
    equity, hwm, mult = cap, cap, 1.0
    for i, (d, v) in enumerate(s.items()):
        dd_now = (equity - hwm) / hwm if hwm > 0 else 0.0
        if dd_now <= -floor_dd:
            mult = deleverage_to
        elif dd_now >= -recover_dd:
            mult = 1.0
        pnl_today = v * mult
        out[i] = pnl_today
        equity += pnl_today
        hwm = max(hwm, equity)
    return pd.Series(out, index=idx)


def run_pipeline(series: dict, cap_table: pd.DataFrame):
    CW_START = pd.Timestamp("2022-01-04")
    CW_END = pd.Timestamp("2025-12-31")
    FIT_START, FIT_END = CW_START, pd.Timestamp("2023-12-31")
    EVAL_START, EVAL_END = pd.Timestamp("2024-01-01"), CW_END
    FULL_END = max(series[n].index.max() for n in SLEEVES)
    idx_fit = pd.date_range(FIT_START, FIT_END, freq="D")
    idx_eval = pd.date_range(EVAL_START, EVAL_END, freq="D")
    idx_full = pd.date_range(CW_START, FULL_END, freq="D")
    mat_fit = pd.DataFrame({n: series[n].reindex(idx_fit).fillna(0.0) for n in SLEEVES})
    mat_eval = pd.DataFrame({n: series[n].reindex(idx_eval).fillna(0.0) for n in SLEEVES})
    mat_full = pd.DataFrame({n: series[n].reindex(idx_full).fillna(0.0) for n in SLEEVES})

    vol_fit = mat_fit.std()
    naive_w_raw = (1.0 / vol_fit); naive_w_raw = naive_w_raw / naive_w_raw.sum()

    results = {}
    for pname, cfg in MANDATE_CFG.items():
        w_cap = cap_table[pname].values
        w_fit, info_fit = scan_weights(mat_fit, 40000, w_cap, cfg["gross_cap"], cfg["objective"],
                                        cfg["mdd_limit"], SEEDS[pname], cfg["cagr_floor"])
        rng2 = np.random.default_rng(SEEDS[pname] + 1)
        for _ in range(3):
            noise = rng2.normal(0, 0.03, size=(20000, len(SLEEVES)))
            cand = np.clip(w_fit[None, :] + noise, 0, w_cap)
            gross_r = rng2.uniform(0.9, 1.1, size=20000)
            cand = cand * gross_r[:, None]
            # BUG FOUND during this re-fit (2026-08-03): the gross_r rescale above can push a sleeve
            # back OVER its per-mandate cap after the earlier np.clip -- this is how BOOK's fitted
            # weight silently exceeded its stated 0.50 HIGH_CAGR cap (came out at ~1.24x, i.e. 124% of
            # book) in this run and, on inspection, in the ALREADY-PUBLISHED PORTFOLIOS_RECOST.md too
            # (BOOK FORWARD AU=11.23x there implies w=1.123, also over its own 0.50 cap -- an error
            # that was not caught before this re-fit). Re-clipping here is the fix; flagged loudly in
            # the writeup, not silently patched.
            cand = np.minimum(cand, w_cap[None, :])
            row_sum = cand.sum(axis=1, keepdims=True)
            cand = cand * np.minimum(1.0, 1.0 / np.maximum(row_sum, 1e-9))
            scale = cand * (TOTAL_CAPITAL / NATURAL_CAP)
            M = mat_fit[SLEEVES].values
            cap = TOTAL_CAPITAL
            yrs = max((mat_fit.index.max() - mat_fit.index.min()).days / 365.25, .01)
            cagr, mdd, sharpe, calmar = _batch_eval(M, scale, cap, yrs)
            feas = mdd >= -cfg["mdd_limit"] / 100.0
            if cfg["cagr_floor"] is not None:
                feas &= (cagr >= cfg["cagr_floor"] / 100.0)
            if feas.any():
                obj_val = cagr if cfg["objective"] == "CAGR" else calmar
                obj_val = np.where(feas, obj_val, -np.inf)
                b = int(np.argmax(obj_val))
                cur_obj = info_fit["CAGR_pct"] / 100 if cfg["objective"] == "CAGR" else info_fit["Calmar"]
                if obj_val[b] > cur_obj:
                    w_fit = cand[b]
                    info_fit = dict(CAGR_pct=round(100 * cagr[b], 2), maxDD_pct=round(100 * mdd[b], 2),
                                     Sharpe=round(sharpe[b], 2), Calmar=round(calmar[b], 3), feasible=bool(feas[b]))
        naive_scaled_w = cap_and_renorm(naive_w_raw.values, w_cap, 1.0)
        lo_g, hi_g = 0.01, cfg["gross_cap"]
        for _ in range(40):
            mid = (lo_g + hi_g) / 2
            # SECOND CAP-BUG FOUND during this re-fit: naive_scaled_w*mid can ALSO push an individual
            # sleeve back over its per-mandate cap once mid>1 (gross_cap can be >1, e.g. BALANCED's
            # 1.5) -- this is how the ALREADY-PUBLISHED PORTFOLIOS_RECOST.md's BALANCED-NAIVE result
            # got CALENDAR to 52.5% against its own stated 35% cap (0.35 capped-then-renormed weight
            # * lo_g up to 1.5 = 0.525, matching that doc's AU=5.25x exactly). Re-clipping here too.
            w_try = np.minimum(naive_scaled_w * mid, w_cap)
            m_try = eq_metrics(pd.Series(combined(mat_fit, w_try), index=idx_fit), TOTAL_CAPITAL)
            if abs(m_try["maxDD_pct"]) <= cfg["mdd_limit"]:
                lo_g = mid
            else:
                hi_g = mid
        w_naive_final = np.minimum(naive_scaled_w * lo_g, w_cap)

        def score(w, mat, idx):
            return eq_metrics(pd.Series(combined(mat, w), index=idx), TOTAL_CAPITAL)

        fit_naive, eval_naive = score(w_naive_final, mat_fit, idx_fit), score(w_naive_final, mat_eval, idx_eval)
        fit_fitted, eval_fitted = score(w_fit, mat_fit, idx_fit), score(w_fit, mat_eval, idx_eval)

        obj_key = "CAGR_pct" if cfg["objective"] == "CAGR" else "Calmar"
        obj_wins = (eval_fitted[obj_key] or -9) > 1.10 * (eval_naive[obj_key] or -9)
        not_degenerate = (eval_fitted["CAGR_pct"] or 0) >= 0.5 * (eval_naive["CAGR_pct"] or 0)
        use_fitted = obj_wins and not_degenerate
        chosen_w = w_fit if use_fitted else w_naive_final
        chosen_label = "FITTED" if use_fitted else "NAIVE"
        results[pname] = dict(weights_naive=dict(zip(SLEEVES, np.round(w_naive_final, 4).tolist())),
                               weights_fitted=dict(zip(SLEEVES, np.round(w_fit, 4).tolist())),
                               eval_naive=eval_naive, eval_fitted=eval_fitted,
                               oos_is_naive=round(eval_naive["Calmar"] / fit_naive["Calmar"], 3) if fit_naive["Calmar"] else None,
                               oos_is_fitted=round(eval_fitted["Calmar"] / fit_fitted["Calmar"], 3) if fit_fitted["Calmar"] else None,
                               chosen_label=chosen_label,
                               chosen_weights=dict(zip(SLEEVES, np.round(chosen_w, 4).tolist())),
                               chosen_w_arr=chosen_w)

    cppi_results = {}
    final_rows = {}
    for pname in MANDATE_CFG:
        w_ = results[pname]["chosen_w_arr"]
        static_m_ = eq_metrics(pd.Series(combined(mat_full, w_), index=idx_full), TOTAL_CAPITAL)
        cppi_full_ = cppi_overlay(mat_full, w_, idx_full, TOTAL_CAPITAL)
        cppi_m_ = eq_metrics(cppi_full_, TOTAL_CAPITAL)
        cppi_results[pname] = dict(static=static_m_, cppi=cppi_m_)
        final_rows[pname] = static_m_
        final_rows[pname]["capital_deployed_pct"] = round(100 * w_.sum(), 1)

    gc.collect()
    return dict(results=results, cppi_results=cppi_results, final_rows=final_rows)


print("=" * 100)
print("RUNNING: FORWARD headline (SWEEP flat-spot 3.741-anchored, BOOK $ unchanged, ORIGINAL caps)")
print("=" * 100)
out_headline = run_pipeline(fwd_flat, CAP_TABLE_ORIG)
for pname in MANDATE_CFG:
    print(pname, out_headline["final_rows"][pname], out_headline["results"][pname]["chosen_label"])
    print("  weights:", out_headline["results"][pname]["chosen_weights"])

print("\n" + "=" * 100)
print("RUNNING: FORWARD cross-check (SWEEP real-per-trade-spot 6.512-anchored, ORIGINAL caps)")
print("=" * 100)
out_crosscheck = run_pipeline(fwd_real, CAP_TABLE_ORIG)
for pname in MANDATE_CFG:
    print(pname, out_crosscheck["final_rows"][pname], out_crosscheck["results"][pname]["chosen_label"])

print("\n" + "=" * 100)
print("RUNNING: FORWARD + LOOSENED SWEEP/BOOK caps (honest max CAGR exploration, 3.741-anchored)")
print("=" * 100)
out_loose = run_pipeline(fwd_flat, CAP_TABLE_LOOSE)
for pname in MANDATE_CFG:
    print(pname, out_loose["final_rows"][pname], out_loose["results"][pname]["chosen_label"])
    print("  weights:", out_loose["results"][pname]["chosen_weights"])

print("\n" + "=" * 100)
print("RUNNING: FORWARD + LOOSENED caps, cross-check SWEEP basis (6.512-anchored)")
print("=" * 100)
out_loose_real = run_pipeline(fwd_real, CAP_TABLE_LOOSE)
for pname in MANDATE_CFG:
    print(pname, out_loose_real["final_rows"][pname], out_loose_real["results"][pname]["chosen_label"])

# ==================================================================== TRUE AU LABELS (correction 1)
print("\n" + "=" * 100)
print("TRUE-NATIVE AU LABELS -- BOOK at Rs1cr native (correction 1), others unchanged at Rs10L native")
print("=" * 100)
au_rows = []
for tag, out in [("headline(orig caps)", out_headline), ("loosened caps", out_loose)]:
    for pname in MANDATE_CFG:
        w = out["results"][pname]["chosen_weights"]
        for sleeve in SLEEVES:
            native_cap = NATURAL_CAP_BOOK_TRUE if sleeve == "BOOK" else NATURAL_CAP
            mislabeled_au = w[sleeve] * (TOTAL_CAPITAL / NATURAL_CAP)
            true_au = w[sleeve] * (TOTAL_CAPITAL / native_cap)
            au_rows.append(dict(variant=tag, mandate=pname, sleeve=sleeve, weight_pct=round(100*w[sleeve],2),
                                 mislabeled_AU=round(mislabeled_au,3), true_AU=round(true_au,3)))
au_df = pd.DataFrame(au_rows)
print(au_df[au_df.sleeve=="BOOK"].to_string(index=False))

# ==================================================================== SAVE
def pack(o):
    return dict(final_rows=o["final_rows"],
                chosen_weights={p: o["results"][p]["chosen_weights"] for p in MANDATE_CFG},
                chosen_label={p: o["results"][p]["chosen_label"] for p in MANDATE_CFG},
                oos_is={p: dict(naive=o["results"][p]["oos_is_naive"], fitted=o["results"][p]["oos_is_fitted"]) for p in MANDATE_CFG},
                cppi=o["cppi_results"])

json.dump(dict(
    headline_3p741_origcaps=pack(out_headline),
    crosscheck_6p512_origcaps=pack(out_crosscheck),
    loosened_3p741=pack(out_loose),
    loosened_6p512_crosscheck=pack(out_loose_real),
    sweep_edge_check=dict(old_avg_pts=round(old_avg_pts,3), fwd_real_avg_pts=round(fwd_real_avg_pts,3),
                          fwd_flat_avg_pts=round(fwd_flat_avg_pts,3)),
    book_unit_check=dict(book_json_sum=round(book_json_sum,2), book_raw_sum=round(book_raw_sum,2),
                        ratio=round(book_raw_sum/book_json_sum,4)),
), open(OUT / "refit_results.json", "w"), indent=2, default=str)
au_df.to_csv(OUT / "au_labels.csv", index=False)
print("\nWROTE:", OUT / "refit_results.json", OUT / "au_labels.csv")
