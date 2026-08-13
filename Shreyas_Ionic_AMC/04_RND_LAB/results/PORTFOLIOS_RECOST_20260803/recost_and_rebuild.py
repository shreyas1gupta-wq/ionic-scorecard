"""PORTFOLIOS RE-COST — Budget-2026 STT hike applied to the 5-sleeve book (2026-08-03, Vikram Shah).

WHAT THIS DOES
  1. Loads the 5 permitted sleeves (SWEEP, CALENDAR, OVERSHOOT, LD_SELL, BOOK) exactly as built in
     THREE_PORTFOLIOS_20260731/build_portfolios.py -- this is the HISTORICAL / "old rate throughout"
     series, used UNCHANGED (it already reflects the STT law that was actually in force at each
     historical date; correct for what actually happened).
  2. Builds a per-sleeve FORWARD-COST DELTA daily series: the INCREMENTAL rupee cost that would have
     applied if every historical trade had instead paid the post-Budget-2026 STT rate (0.05% futures
     sale value, 0.15% options sale premium), computed per-trade from the CONTEMPORANEOUS spot/premium
     where trade-level detail exists on disk, with every approximation stated loudly where it does not.
  3. FORWARD series = HISTORICAL series - delta (this is "new rate throughout", i.e. what we would
     face running this book from here).
  4. Re-runs the IDENTICAL portfolio-construction methodology from build_portfolios.py (walk-forward
     NAIVE-vs-FITTED weight search, same caps, same seeds, same CPPI overlay test) on BOTH the
     HISTORICAL and FORWARD sleeve sets, and reports before/after.

PER-SLEEVE RECOST METHOD (stated per sleeve, per the mandate's instruction to never silently flat-haircut)
  SWEEP (futures, delta-1 NIFTY, LOT=75 -- the sleeve's own embedded lot convention, NOT recost.py's
    illustrative LOT=65 which was a generic worked example, not tied to this sleeve's actual build):
    REAL per-trade entry/exit spot from SWEEP_11YR_20260729/trades_E_swing3_trail60_1lot.csv.
    STT is charged on the SELL leg only (one leg per round trip): for a LONG (dir=+1) the sell leg is
    the EXIT; for a SHORT (dir=-1) the sell leg is the ENTRY. delta_rs = (STT_FUT_NEW-STT_FUT_OLD) *
    sell_leg_spot * 75, aggregated by the trade's entry "date" (matches how the baseline series itself
    is date-aggregated in build_ranking.py). EXACT, no premium/spot assumption needed.
  BOOK (existing_book = STACKED_BOOK_20260711/book_daily_pnl.csv "total", decomposed into its 4 REAL
    components -- this is a REFINEMENT of the task's "BOOK is futures-based" framing, verified against
    stacked_book.py):
      - midsmall, breakout: EQUITY CASH sleeves (momentum/rotation). This Budget change is an F&O STT
        change only; equity delivery STT is untouched. delta = 0 for both, EXACTLY (not an
        approximation -- these instruments are simply outside the scope of the F&O STT hike).
      - s1f: 0DTE short straddle, OPTIONS, 3 lots x LOT 75. final_three_trades.csv (source) carries NO
        premium column, so premium is ASSUMED at 110 pts (re-using recost.py's own established
        assumption for this exact same S1-F cell, rather than inventing a new number) -- flagged
        [INFERENCE]. delta_rs = (STT_OPT_NEW-STT_OPT_OLD) * 110 * 75 * 3, applied on every day the
        book's own "s1f" column is non-zero.
      - b1b: futures OVERLAY sized at a FIXED Rs 50L notional (not lot-count-based -- confirmed from
        stacked_book.py: "B1b flow (Rs 50L notional futures)"). Because STT = rate x notional value and
        the notional here is already a fixed rupee amount (not spot x lots), delta_rs = (STT_FUT_NEW-
        STT_FUT_OLD) * 50,00,000 EXACTLY on every day the book's own "b1b" column is non-zero -- no
        spot approximation needed, and this is in fact MORE precise than a spot-reconstruction would be.
  CALENDAR (ATM/ATM 1x1 monthly calendar, options, LOT=75): RATIO_CALENDAR_20260730/grid_a_trades_raw.csv
    carries strike/DTE/IV data but NO option premium column. Premium ASSUMED at 150 pts (re-using
    recost.py's own established assumption for this exact cell) -- flagged [INFERENCE]. Structural
    caveat also flagged: a real calendar has TWO sell-side STT events per round trip (sell-to-open the
    near leg, AND sell-to-close the far leg at exit) where this uses ONE -- likely UNDERSTATES
    CALENDAR's true incremental cost by up to ~2x, but even doubled the rupee impact is trivial against
    this sleeve's Rs10L natural base (see results: <0.1pp of CAGR either way).
  OVERSHOOT (0-1DTE spike-sell, delta-hedged, options, LOT=65 per this session's own scoreboard header):
    No single on-disk trade log maps 1:1 to the exact 913-day final series (multiple candidate CSVs in
    SPIKE_OVERSHOOT_SELL_20260730/ test different variants of the same idea). Premium ASSUMED at 60 pts
    (re-using recost.py's own established assumption) applied on every day the OVERSHOOT series itself
    is non-zero (913 days) -- flagged [INFERENCE]. OVERSHOOT is capped hard regardless of this result
    (no crash data), so precision here does not change any allocation decision.
  LD_SELL (biweekly 0.10-delta naked strangle, options, LOT=65 -- confirmed via credit_pt*65==pl_rs_gross
    exactly on-disk): REAL per-trade premium from LONGDATED_SELLING_20260730/best_config_trades.csv
    "credit_pt" column -- the most precise of the three options sleeves, no premium assumption needed.
    delta_rs = (STT_OPT_NEW-STT_OPT_OLD) * credit_pt * 65, aggregated by exit_day.

Files read (all pre-existing, none rebuilt):
  FINAL_RANKING_20260730/all_sleeves_daily.json      -- the 5 baseline sleeve series (HISTORICAL)
  SWEEP_11YR_20260729/trades_E_swing3_trail60_1lot.csv
  RATIO_CALENDAR_20260730/grid_a_trades_raw.csv
  LONGDATED_SELLING_20260730/best_config_trades.csv
  STACKED_BOOK_20260711/book_daily_pnl.csv           -- BOOK's 4-way decomposition
"""
from __future__ import annotations
import json, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
         r"\Shreyas_Ionic_AMC\04_RND_LAB\results")
OUT = R / "PORTFOLIOS_RECOST_20260803"
OUT.mkdir(exist_ok=True, parents=True)

NATURAL_CAP = 1_000_000.0
TOTAL_CAPITAL = 1_00_00_000.0
SLEEVES = ["SWEEP", "CALENDAR", "OVERSHOOT", "LD_SELL", "BOOK"]

# ---------------------------------------------------------------- STT constants (STT_RECOST_20260803)
STT_FUT_OLD, STT_FUT_NEW = 0.0002, 0.0005
STT_OPT_OLD, STT_OPT_NEW = 0.0010, 0.0015
D_OPT = STT_OPT_NEW - STT_OPT_OLD   # 0.0005 (per pt of premium)

LOT_SWEEP, LOT_CALENDAR, LOT_OVERSHOOT, LOT_LD_SELL, LOT_S1F = 75, 75, 65, 65, 75
N_LOTS_S1F = 3
B1B_NOTIONAL = 50_00_000.0
PREM_ASSUMED_CALENDAR = 150.0
PREM_ASSUMED_OVERSHOOT = 60.0
PREM_ASSUMED_S1F = 110.0

# ==================================================================== 1. LOAD HISTORICAL (baseline)
raw = json.load(open(R / "FINAL_RANKING_20260730" / "all_sleeves_daily.json"))
hist = {}
for item in raw:
    s = pd.Series(item["daily"], dtype=float)
    s.index = pd.to_datetime(s.index)
    hist[item["name"]] = s.sort_index()
assert set(SLEEVES).issubset(hist.keys())
print("Loaded HISTORICAL series:",
      {k: (len(v), f"{v.index[0]:%Y-%m-%d}..{v.index[-1]:%Y-%m-%d}") for k, v in hist.items() if k in SLEEVES})

# ==================================================================== 2. BUILD FORWARD-COST DELTAS
delta = {k: pd.Series(dtype=float) for k in SLEEVES}

# ---- SWEEP: real entry/exit spot, real dir, LOT=75 ---------------------------------------------
t = pd.read_csv(R / "SWEEP_11YR_20260729" / "trades_E_swing3_trail60_1lot.csv")
t["date"] = pd.to_datetime(t["date"])
sell_leg_spot = np.where(t["dir"] > 0, t["exit"], t["entry"])
t["delta_rs"] = (STT_FUT_NEW - STT_FUT_OLD) * sell_leg_spot * LOT_SWEEP
delta["SWEEP"] = t.groupby(t["date"].dt.normalize())["delta_rs"].sum().sort_index()
print(f"\nSWEEP: {len(t)} trades, mean contemporaneous sell-leg spot {sell_leg_spot.mean():,.0f}, "
      f"mean delta/trade Rs{t['delta_rs'].mean():.2f}, total delta Rs{t['delta_rs'].sum():,.0f}")

# ---- CALENDAR: assumed premium 150pt, LOT=75 ----------------------------------------------------
rc = pd.read_csv(R / "RATIO_CALENDAR_20260730" / "grid_a_trades_raw.csv")
c = rc[(rc.strike_struct == "ATM_ATM") & (rc.ratio == "1x1") & (rc.exit_variant == "3d_before")]
c = c.drop_duplicates(subset=["day0", "near_expiry"]).copy()
c["exit_day"] = pd.to_datetime(c["exit_day"])
c["delta_rs"] = D_OPT * PREM_ASSUMED_CALENDAR * LOT_CALENDAR   # flat per trade [INFERENCE: assumed premium]
delta["CALENDAR"] = c.groupby(c["exit_day"].dt.normalize())["delta_rs"].sum().sort_index()
print(f"CALENDAR: {len(c)} trades, delta/trade Rs{c['delta_rs'].iloc[0]:.2f} (assumed {PREM_ASSUMED_CALENDAR}pt "
      f"premium, single sell-leg only), total delta Rs{c['delta_rs'].sum():,.0f}")

# ---- OVERSHOOT: assumed premium 60pt, LOT=65, applied on the sleeve's own active days -----------
ov_active = hist["OVERSHOOT"][hist["OVERSHOOT"] != 0]
delta_per_day = D_OPT * PREM_ASSUMED_OVERSHOOT * LOT_OVERSHOOT
delta["OVERSHOOT"] = pd.Series(delta_per_day, index=ov_active.index)
print(f"OVERSHOOT: {len(ov_active)} active days treated as 1 trade/day, delta/trade Rs{delta_per_day:.2f} "
      f"(assumed {PREM_ASSUMED_OVERSHOOT}pt premium), total delta Rs{delta['OVERSHOOT'].sum():,.0f}")

# ---- LD_SELL: REAL credit_pt premium, LOT=65 ------------------------------------------------------
ld = pd.read_csv(R / "LONGDATED_SELLING_20260730" / "best_config_trades.csv")
ld["exit_day"] = pd.to_datetime(ld["exit_day"])
ld["delta_rs"] = D_OPT * ld["credit_pt"] * LOT_LD_SELL
delta["LD_SELL"] = ld.groupby(ld["exit_day"].dt.normalize())["delta_rs"].sum().sort_index()
print(f"LD_SELL: {len(ld)} trades, REAL premium (credit_pt) mean {ld['credit_pt'].mean():.1f}pt, "
      f"mean delta/trade Rs{ld['delta_rs'].mean():.2f}, total delta Rs{ld['delta_rs'].sum():,.0f}")

# ---- BOOK: decompose into midsmall/breakout (0) + s1f (assumed prem) + b1b (fixed notional) -----
bk = pd.read_csv(R / "STACKED_BOOK_20260711" / "book_daily_pnl.csv", index_col=0, parse_dates=True)
s1f_days = bk.index[bk["s1f"] != 0]
b1b_days = bk.index[bk["b1b"] != 0]
d_s1f = D_OPT * PREM_ASSUMED_S1F * LOT_S1F * N_LOTS_S1F
d_b1b = (STT_FUT_NEW - STT_FUT_OLD) * B1B_NOTIONAL
book_delta = pd.Series(0.0, index=bk.index)
book_delta.loc[s1f_days] += d_s1f
book_delta.loc[b1b_days] += d_b1b
delta["BOOK"] = book_delta[book_delta != 0]
print(f"BOOK components: midsmall/breakout (equity cash) = ZERO delta, exact, not an approximation.")
print(f"  s1f: {len(s1f_days)} days, delta/day Rs{d_s1f:.2f} (assumed {PREM_ASSUMED_S1F}pt premium x 3 lots)")
print(f"  b1b: {len(b1b_days)} days, delta/day Rs{d_b1b:.2f} (EXACT -- fixed Rs50L notional, no spot needed)")
print(f"  BOOK total delta Rs{delta['BOOK'].sum():,.0f}")

# ==================================================================== 3. FORWARD series = hist - delta
fwd = {}
for k in SLEEVES:
    d = delta[k].reindex(hist[k].index).fillna(0.0)
    fwd[k] = hist[k] - d

print("\nTOTAL FORWARD-COST DELTA BY SLEEVE (rupees, full history, natural 1x = Rs10L):")
for k in SLEEVES:
    tot_hist = hist[k].sum()
    tot_fwd = fwd[k].sum()
    print(f"  {k:<10} hist net Rs{tot_hist:>14,.0f}   fwd net Rs{tot_fwd:>14,.0f}   "
          f"delta Rs{tot_hist - tot_fwd:>12,.0f}  ({100*(tot_hist-tot_fwd)/abs(tot_hist):+.1f}% of hist net)")

json.dump({k: {"hist_net": round(float(hist[k].sum())), "fwd_net": round(float(fwd[k].sum())),
               "delta_total": round(float(delta[k].sum())), "n_delta_days": int(len(delta[k]))}
          for k in SLEEVES}, open(OUT / "sleeve_delta_summary.json", "w"), indent=2)

# ==================================================================== 4. PORTFOLIO BUILD (identical
#            methodology to THREE_PORTFOLIOS_20260731/build_portfolios.py) -- parameterised by series
CRASH_WINDOWS = {
    "2015-16 (Aug15-Feb16)": ("2015-08-01", "2016-02-29"),
    "2018 (Jan-Mar VIX-plosion)": ("2018-01-01", "2018-03-31"),
    "COVID (Feb-Apr 2020)": ("2020-02-15", "2020-04-15"),
    "2022 (Jan-Jun selloff)": ("2022-01-01", "2022-06-30"),
}
CAP_TABLE = pd.DataFrame({
    "LOW_RISK":  {"SWEEP": 0.25, "CALENDAR": 0.20, "OVERSHOOT": 0.08, "LD_SELL": 0.10, "BOOK": 0.25},
    "HIGH_CAGR": {"SWEEP": 0.50, "CALENDAR": 0.50, "OVERSHOOT": 0.25, "LD_SELL": 0.35, "BOOK": 0.50},
    "BALANCED":  {"SWEEP": 0.35, "CALENDAR": 0.35, "OVERSHOOT": 0.15, "LD_SELL": 0.20, "BOOK": 0.35},
}).reindex(SLEEVES)
MANDATES = {
    "LOW_RISK": dict(objective="CAGR", mdd_limit=10.0, w_cap=CAP_TABLE["LOW_RISK"].values, gross_cap=1.0, cagr_floor=6.0),
    "HIGH_CAGR": dict(objective="CAGR", mdd_limit=25.0, w_cap=CAP_TABLE["HIGH_CAGR"].values, gross_cap=2.5, cagr_floor=6.0),
    "BALANCED": dict(objective="CALMAR", mdd_limit=25.0, w_cap=CAP_TABLE["BALANCED"].values, gross_cap=1.5, cagr_floor=8.0),
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
    w, l = s[s > 0], s[s <= 0]
    return dict(span=f"{s.index.min():%Y-%m-%d}..{s.index.max():%Y-%m-%d}", years=round(yrs, 2),
                net_rs=round(float(s.sum())), CAGR_pct=round(100 * cagr, 2) if np.isfinite(cagr) else None,
                maxDD_pct=round(100 * float(dd.min()), 2), maxDD_rs=round(float((eq - pk).min())),
                Calmar=round(float(cagr / abs(dd.min())), 3) if dd.min() else None,
                Sharpe=round(sh, 2) if np.isfinite(sh) else None,
                PF=round(float(w.sum() / abs(l.sum())), 2) if l.sum() else None,
                months=int(len(mo)), month_win_pct=round(100 * float((mo > 0).mean()), 1),
                worst_month_pct=round(100 * float(mo.min() / cap), 2),
                worst_day_pct=round(100 * float(s.min() / cap), 2),
                active_days=int((s != 0).sum()))


def worst_n_month_stretch(mo, n):
    if len(mo) < n:
        return float(mo.sum())
    return float(mo.rolling(n).sum().min())


def _batch_eval(M, W, cap, yrs):
    """M: (T,k) float64, W: (n,k) float64 -> per-candidate cagr/mdd/sharpe/calmar. Chunked to bound
    peak memory (this machine runs with ~2GB free, so a single 40k-sample (727,40000) float64 array
    is too large to allocate alongside its siblings -- see run_log.txt ArrayMemoryError caught during
    this build)."""
    n = W.shape[0]
    cagr = np.empty(n); mdd = np.empty(n); sharpe = np.empty(n); calmar = np.empty(n)
    CHUNK = 4000
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
    return cagr, mdd, sharpe, calmar


def scan_weights(mat, n_samples, w_cap, gross_cap, objective, mdd_limit, seed, cagr_floor=None):
    rng = np.random.default_rng(seed)
    k = len(SLEEVES)
    dirs = rng.dirichlet(np.ones(k) * 2.0, size=n_samples)
    dirs = np.array([cap_and_renorm(row, w_cap, 1.0) for row in dirs])
    gross = rng.uniform(0.02, gross_cap, size=n_samples)
    W = dirs * gross[:, None]
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
    raw = combined(mat, w_base)
    s = pd.Series(raw, index=idx)
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


def run_pipeline(series: dict, label: str) -> dict:
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
    for pname, cfg in MANDATES.items():
        w_fit, info_fit = scan_weights(mat_fit, 40000, cfg["w_cap"], cfg["gross_cap"], cfg["objective"],
                                        cfg["mdd_limit"], SEEDS[pname], cfg["cagr_floor"])
        rng2 = np.random.default_rng(SEEDS[pname] + 1)
        for _ in range(3):
            noise = rng2.normal(0, 0.03, size=(20000, len(SLEEVES)))
            cand = np.clip(w_fit[None, :] + noise, 0, cfg["w_cap"])
            gross_r = rng2.uniform(0.9, 1.1, size=20000)
            cand = cand * gross_r[:, None]
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
        naive_scaled_w = cap_and_renorm(naive_w_raw.values, cfg["w_cap"], 1.0)
        lo_g, hi_g = 0.01, cfg["gross_cap"]
        for _ in range(40):
            mid = (lo_g + hi_g) / 2
            w_try = naive_scaled_w * mid
            m_try = eq_metrics(pd.Series(combined(mat_fit, w_try), index=idx_fit), TOTAL_CAPITAL)
            if abs(m_try["maxDD_pct"]) <= cfg["mdd_limit"]:
                lo_g = mid
            else:
                hi_g = mid
        w_naive_final = naive_scaled_w * lo_g

        def score(w, mat, idx):
            return eq_metrics(pd.Series(combined(mat, w), index=idx), TOTAL_CAPITAL)

        fit_naive, eval_naive = score(w_naive_final, mat_fit, idx_fit), score(w_naive_final, mat_eval, idx_eval)
        fit_fitted, eval_fitted = score(w_fit, mat_fit, idx_fit), score(w_fit, mat_eval, idx_eval)
        oos_is_naive = round(eval_naive["Calmar"] / fit_naive["Calmar"], 3) if fit_naive["Calmar"] else None
        oos_is_fitted = round(eval_fitted["Calmar"] / fit_fitted["Calmar"], 3) if fit_fitted["Calmar"] else None

        obj_key = "CAGR_pct" if cfg["objective"] == "CAGR" else "Calmar"
        obj_wins = (eval_fitted[obj_key] or -9) > 1.10 * (eval_naive[obj_key] or -9)
        not_degenerate = (eval_fitted["CAGR_pct"] or 0) >= 0.5 * (eval_naive["CAGR_pct"] or 0)
        use_fitted = obj_wins and not_degenerate
        chosen_w = w_fit if use_fitted else w_naive_final
        chosen_label = "FITTED" if use_fitted else "NAIVE"
        results[pname] = dict(weights_naive=dict(zip(SLEEVES, np.round(w_naive_final, 4).tolist())),
                               weights_fitted=dict(zip(SLEEVES, np.round(w_fit, 4).tolist())),
                               fit_naive=fit_naive, eval_naive=eval_naive, oos_is_naive=oos_is_naive,
                               fit_fitted=fit_fitted, eval_fitted=eval_fitted, oos_is_fitted=oos_is_fitted,
                               chosen_label=chosen_label,
                               chosen_weights=dict(zip(SLEEVES, np.round(chosen_w, 4).tolist())),
                               chosen_w_arr=chosen_w)

    # CPPI overlay re-test (on chosen weights, all 3 mandates; headline = HIGH_CAGR)
    cppi_results = {}
    for pname in MANDATES:
        w_ = results[pname]["chosen_w_arr"]
        static_m_ = eq_metrics(pd.Series(combined(mat_full, w_), index=idx_full), TOTAL_CAPITAL)
        cppi_full_ = cppi_overlay(mat_full, w_, idx_full, TOTAL_CAPITAL)
        cppi_m_ = eq_metrics(cppi_full_, TOTAL_CAPITAL)
        cppi_results[pname] = dict(static=static_m_, cppi=cppi_m_)

    # final metrics (chosen weights, FULL_EXT)
    final_rows = {}
    for pname in MANDATES:
        w = results[pname]["chosen_w_arr"]
        s_full = pd.Series(combined(mat_full, w), index=idx_full)
        m = eq_metrics(s_full, TOTAL_CAPITAL)
        mo = s_full.resample("ME").sum()
        m["worst_3mo_stretch_pct"] = round(100 * worst_n_month_stretch(mo, 3) / TOTAL_CAPITAL, 2)
        util = sum(w[i] * (mat_full[SLEEVES[i]] != 0).mean() for i in range(len(SLEEVES)))
        m["capital_deployed_pct"] = round(100 * w.sum(), 1)
        m["capital_utilisation_pct"] = round(100 * util, 1)
        final_rows[pname] = m

    return dict(results=results, cppi_results=cppi_results, final_rows=final_rows,
                mat_full=mat_full, idx_full=idx_full)


print("\n" + "=" * 100)
print("RUNNING PIPELINE: HISTORICAL (old rate throughout -- unchanged baseline, sanity check vs "
      "PORTFOLIOS.md)")
print("=" * 100)
out_hist = run_pipeline(hist, "HISTORICAL")
for pname in MANDATES:
    print(pname, out_hist["final_rows"][pname])
    print("  weights:", out_hist["results"][pname]["chosen_weights"], out_hist["results"][pname]["chosen_label"])

print("\n" + "=" * 100)
print("RUNNING PIPELINE: FORWARD (new STT rate throughout -- what we'd face running this book today)")
print("=" * 100)
out_fwd = run_pipeline(fwd, "FORWARD")
for pname in MANDATES:
    print(pname, out_fwd["final_rows"][pname])
    print("  weights:", out_fwd["results"][pname]["chosen_weights"], out_fwd["results"][pname]["chosen_label"])

print("\n" + "=" * 100)
print("CPPI OVERLAY RE-TEST, HIGH_CAGR, FORWARD-costed")
print("=" * 100)
print("HISTORICAL:", out_hist["cppi_results"]["HIGH_CAGR"])
print("FORWARD   :", out_fwd["cppi_results"]["HIGH_CAGR"])

# ==================================================================== write outputs
def pack(o):
    return dict(final_rows=o["final_rows"],
                chosen_weights={p: o["results"][p]["chosen_weights"] for p in MANDATES},
                chosen_label={p: o["results"][p]["chosen_label"] for p in MANDATES},
                cppi=o["cppi_results"])

json.dump(dict(HISTORICAL=pack(out_hist), FORWARD=pack(out_fwd)),
          open(OUT / "before_after.json", "w"), indent=2, default=str)

print("\n" + "=" * 100)
print("PER-SLEEVE STANDALONE METRICS, natural 1x = Rs10L, HISTORICAL vs FORWARD (full available history)")
print("=" * 100)
sleeve_before_after = {}
for k in SLEEVES:
    mh = eq_metrics(hist[k], NATURAL_CAP)
    mf = eq_metrics(fwd[k], NATURAL_CAP)
    sleeve_before_after[k] = dict(historical=mh, forward=mf)
    print(f"{k:<10} HIST  CAGR={mh['CAGR_pct']:<7} MDD={mh['maxDD_pct']:<7} Calmar={mh['Calmar']:<6} "
          f"Sharpe={mh['Sharpe']:<6} monthwin%={mh['month_win_pct']}")
    print(f"{'':<10} FWD   CAGR={mf['CAGR_pct']:<7} MDD={mf['maxDD_pct']:<7} Calmar={mf['Calmar']:<6} "
          f"Sharpe={mf['Sharpe']:<6} monthwin%={mf['month_win_pct']}")

json.dump(sleeve_before_after, open(OUT / "sleeve_before_after.json", "w"), indent=2, default=str)
print("\nWROTE:", OUT / "sleeve_delta_summary.json", OUT / "before_after.json", OUT / "sleeve_before_after.json")
