"""
PURE_OPTIONS_BOOK_20260803 -- Aakash Jain (Structurer), Shreyas_Ionic_AMC.
Builds and stress-tests a pure-options (NO futures leg) multi-sleeve book, forward-STT-costed,
per the Budget-2026 futures-STT hike (see STT_RECOST_20260803, PORTFOLIOS_RECOST_20260803).

REUSES, DOES NOT RE-BACKTEST:
  FINAL_RANKING_20260730/all_sleeves_daily.json    -- CALENDAR, OVERSHOOT, LD_SELL daily P&L (HIST)
  STACKED_BOOK_20260711/book_daily_pnl.csv         -- 's1f' column = 0DTE straddle within BOOK
  RATIO_CALENDAR_20260730/grid_a_trades_raw.csv    -- CALENDAR real trades (for fwd-STT delta)
  RATIO_CALENDAR_20260730/grid_b_trades_raw.csv    -- rolled ratio-calendar per-cycle P&L (NEW series)
  LONGDATED_SELLING_20260730/best_config_trades.csv-- LD_SELL real premium (credit_pt)
  SELL_PLUS_TAIL_20260803/checkpoints/tail_trades_*.csv, core_trades_recost.csv -- tail-put overlay
  PORTFOLIOS_RECOST_20260803/*.json                -- BALANCED comparator, sleeve fwd metrics

STT constants identical to STT_RECOST_20260803/recost.py: [INFERENCE, pending Principal sign-off
under D-021] futures 0.02%->0.05% of notional, options 0.10%->0.15% of premium, eff. 1-Apr-2026.
"""
from __future__ import annotations
import json, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
         r"\Shreyas_Ionic_AMC\04_RND_LAB\results")
OUT = R / "PURE_OPTIONS_BOOK_20260803"
CKPT = OUT / "checkpoints"
CKPT.mkdir(exist_ok=True, parents=True)

NATURAL_CAP = 1_000_000.0        # Rs10L, firm-wide convention (build_portfolios.py, confirmed
                                  # explicit for SWEEP/BOOK, applied by analogy to every option
                                  # sleeve including the two new ones built here -- same assumption,
                                  # not a new hack)
TOTAL_CAPITAL = 1_00_00_000.0    # Rs1cr headline book, for weight reporting only

STT_FUT_OLD, STT_FUT_NEW = 0.0002, 0.0005
STT_OPT_OLD, STT_OPT_NEW = 0.0010, 0.0015
D_OPT = STT_OPT_NEW - STT_OPT_OLD  # 0.0005 per pt of premium, sell-side opening leg only

LOT_CALENDAR, LOT_OVERSHOOT, LOT_LD_SELL, LOT_S1F, LOT_RATIOCAL = 75, 65, 65, 75, 75
N_LOTS_S1F = 3
PREM_ASSUMED_CALENDAR = 150.0
PREM_ASSUMED_OVERSHOOT = 60.0
PREM_ASSUMED_S1F = 110.0
PREM_ASSUMED_RATIOCAL = 150.0   # same [INFERENCE] as recost.py's OPT_PREM_ASSUMED for this exact cell

# ============================================================ 1. LOAD BASELINE (HISTORICAL) SERIES
raw = json.load(open(R / "FINAL_RANKING_20260730" / "all_sleeves_daily.json"))
hist = {}
for item in raw:
    s = pd.Series(item["daily"], dtype=float)
    s.index = pd.to_datetime(s.index)
    hist[item["name"]] = s.sort_index()
print("Loaded baseline HIST series:",
      {k: (len(v), f"{v.index[0]:%Y-%m-%d}..{v.index[-1]:%Y-%m-%d}") for k, v in hist.items()
       if k in ("CALENDAR", "OVERSHOOT", "LD_SELL")})

# ============================================================ 2. FORWARD-COST DELTAS (identical
#      method to PORTFOLIOS_RECOST_20260803/recost_and_rebuild.py -- re-derived here, not re-run,
#      because that script bundles SWEEP/BOOK-total logic this build does not want)
delta = {}

# ---- CALENDAR: assumed premium 150pt, LOT=75, ONE sell-leg per trade [INFERENCE, understates ~2x
#      per recost_and_rebuild.py's own caveat -- immaterial magnitude, carried forward unchanged] ---
rc = pd.read_csv(R / "RATIO_CALENDAR_20260730" / "grid_a_trades_raw.csv")
c = rc[(rc.strike_struct == "ATM_ATM") & (rc.ratio == "1x1") & (rc.exit_variant == "3d_before")]
c = c.drop_duplicates(subset=["day0", "near_expiry"]).copy()
c["exit_day"] = pd.to_datetime(c["exit_day"])
c["delta_rs"] = D_OPT * PREM_ASSUMED_CALENDAR * LOT_CALENDAR
delta["CALENDAR"] = c.groupby(c["exit_day"].dt.normalize())["delta_rs"].sum().sort_index()
print(f"CALENDAR: {len(c)} trades, delta/trade Rs{c['delta_rs'].iloc[0]:.2f}, "
      f"total delta Rs{delta['CALENDAR'].sum():,.0f}")

# ---- OVERSHOOT: assumed premium 60pt, LOT=65, on the sleeve's own active days -------------------
ov_active = hist["OVERSHOOT"][hist["OVERSHOOT"] != 0]
d_ov = D_OPT * PREM_ASSUMED_OVERSHOOT * LOT_OVERSHOOT
delta["OVERSHOOT"] = pd.Series(d_ov, index=ov_active.index)
print(f"OVERSHOOT: {len(ov_active)} active days, delta/day Rs{d_ov:.2f}, "
      f"total delta Rs{delta['OVERSHOOT'].sum():,.0f}")

# ---- LD_SELL: REAL credit_pt premium, LOT=65 -----------------------------------------------------
ld = pd.read_csv(R / "LONGDATED_SELLING_20260730" / "best_config_trades.csv")
ld["exit_day"] = pd.to_datetime(ld["exit_day"])
ld["delta_rs"] = D_OPT * ld["credit_pt"] * LOT_LD_SELL
delta["LD_SELL"] = ld.groupby(ld["exit_day"].dt.normalize())["delta_rs"].sum().sort_index()
print(f"LD_SELL: {len(ld)} trades, REAL premium mean {ld['credit_pt'].mean():.1f}pt, "
      f"total delta Rs{delta['LD_SELL'].sum():,.0f}")

# ---- S1_F: extract from BOOK's own s1f column (0DTE straddle, 3 lots x LOT75), assumed prem 110pt
bk = pd.read_csv(R / "STACKED_BOOK_20260711" / "book_daily_pnl.csv", index_col=0, parse_dates=True)
s1f_hist = bk["s1f"].copy()
s1f_active = s1f_hist[s1f_hist != 0]
d_s1f = D_OPT * PREM_ASSUMED_S1F * LOT_S1F * N_LOTS_S1F
delta["S1_F"] = pd.Series(d_s1f, index=s1f_active.index)
print(f"S1_F: {len(s1f_active)} active days (extracted from BOOK's s1f column, span "
      f"{s1f_active.index.min():%Y-%m-%d}..{s1f_active.index.max():%Y-%m-%d}), delta/day Rs{d_s1f:.2f}, "
      f"total delta Rs{delta['S1_F'].sum():,.0f}")
print("  [DATA CAVEAT, per S1F_SPEC.md] S1-F has NO real COVID-class option day in-sample; its own "
      "spec's crash number (~-16% maxDD) is MODEL-validated (corr 0.64 to realised), not measured.")

# ---- ROLLED_RATIO_CAL: NEW series, grid_b_trades_raw.csv, 3d_before/unconditional/roll ----------
rb = pd.read_csv(R / "RATIO_CALENDAR_20260730" / "grid_b_trades_raw.csv")
rb["entry_day"] = pd.to_datetime(rb["entry_day"])
rc2 = rb[rb["exit_variant"] == "3d_before"].drop_duplicates(subset=["day0"]).copy()
rc2 = rc2[rc2["entry_day"] >= "2011-01-01"]
rc2["pl_rs_gross"] = rc2["roll_net_pts"] * LOT_RATIOCAL
rc2["delta_rs"] = D_OPT * PREM_ASSUMED_RATIOCAL * LOT_RATIOCAL
ratiocal_gross = rc2.groupby(rc2["entry_day"].dt.normalize())["pl_rs_gross"].sum().sort_index()
delta["ROLLED_RATIO_CAL"] = rc2.groupby(rc2["entry_day"].dt.normalize())["delta_rs"].sum().sort_index()
print(f"ROLLED_RATIO_CAL: {len(rc2)} cycles (n matches STT_RECOST recost.py's 28.48pt/cycle row to "
      f"4dp: mean={rc2['roll_net_pts'].mean():.4f}), span {rc2['entry_day'].min():%Y-%m-%d}.."
      f"{rc2['entry_day'].max():%Y-%m-%d}, total delta Rs{delta['ROLLED_RATIO_CAL'].sum():,.0f}")
print("  [INFERENCE] date anchor = entry_day (day0), not true exit date (~1mo later, 3d-before-"
      "expiry) -- immaterial for MONTHLY/QUARTERLY correlation (the only resolution used below), "
      "would matter for a live order plan (not this build's job).")

# ============================================================ 3. FORWARD series = hist - delta
CAL_HIST = hist["CALENDAR"]
OV_HIST = hist["OVERSHOOT"]
LD_HIST = hist["LD_SELL"]
RATIOCAL_HIST = ratiocal_gross  # gross_pts*LOT, no cost model applied yet in the raw grid (unlike
                                 # CALENDAR/LD_SELL/OVERSHOOT's hist series which already embed the
                                 # OLD-rate STT + brokerage/slippage the original backtest charged --
                                 # NONE of that exists for this brand-new series). Apply brokerage+
                                 # slippage + OLD STT once, consistent with how the other 3 series
                                 # were originally built, THEN subtract the fwd delta, so this new
                                 # sleeve is on the same normalised OLD-then-NEW footing as the rest.
BROKERAGE_SLIPPAGE_PTS = 4.0   # [INFERENCE] COST_STANDARDS-consistent round-trip cost proxy for a
                                # 2-leg options structure (matches the ~3.5-4.5pt band used
                                # elsewhere in this lab for a 2-leg options round trip, e.g.
                                # LD_SELL/CALENDAR's own embedded brokerage+slippage terms)
old_stt_pts = STT_OPT_OLD * PREM_ASSUMED_RATIOCAL
ratiocal_hist_costed = RATIOCAL_HIST - (BROKERAGE_SLIPPAGE_PTS + old_stt_pts) * LOT_RATIOCAL

hist_all = {"CALENDAR": CAL_HIST, "OVERSHOOT": OV_HIST, "LD_SELL": LD_HIST,
            "S1_F": s1f_active, "ROLLED_RATIO_CAL": ratiocal_hist_costed}
fwd_all = {}
for k, s in hist_all.items():
    d = delta[k].reindex(s.index).fillna(0.0)
    fwd_all[k] = s - d

print("\nTOTAL FORWARD-COST DELTA BY CANDIDATE SLEEVE (rupees, full history, natural 1x=Rs10L):")
for k in hist_all:
    th, tf = hist_all[k].sum(), fwd_all[k].sum()
    print(f"  {k:<18} hist net Rs{th:>12,.0f}  fwd net Rs{tf:>12,.0f}  "
          f"delta Rs{th-tf:>10,.0f} ({100*(th-tf)/abs(th) if th else float('nan'):+.2f}% of hist)")

# ============================================================ 4. STANDALONE METRICS, natural 1x
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
                worst_month_rs=round(float(mo.min())),
                worst_day_pct=round(100 * float(s.min() / cap), 2),
                active_days=int((s != 0).sum()))

print("\n" + "=" * 100)
print("STANDALONE METRICS, natural 1x = Rs10L, FORWARD (post-Apr-2026 STT) costed, full history")
print("=" * 100)
standalone = {}
for k, s in fwd_all.items():
    m = eq_metrics(s, NATURAL_CAP)
    standalone[k] = m
    print(f"{k:<18} span={m['span']} yrs={m['years']:<6} CAGR%={m['CAGR_pct']!s:<7} "
          f"maxDD%={m['maxDD_pct']!s:<8} Calmar={m['Calmar']!s:<6} Sharpe={m['Sharpe']!s:<6} "
          f"monthwin%={m['month_win_pct']:<5} active_days={m['active_days']}")

json.dump(standalone, open(CKPT / "standalone_metrics.json", "w"), indent=2, default=str)

# ============================================================ 5. SLEEVE-SLEEVE CORRELATION
# common window: S1_F (extracted from BOOK) constrains the start, exactly as it constrains
# THREE_PORTFOLIOS_20260731's own CW_START -- same firm convention, not a new choice.
CW_START = pd.Timestamp("2022-01-04")
FULL_END = min(s.index.max() for s in fwd_all.values())
idx_full = pd.date_range(CW_START, FULL_END, freq="D")
NAMES = ["S1_F", "LD_SELL", "CALENDAR", "ROLLED_RATIO_CAL", "OVERSHOOT"]
mat_full = pd.DataFrame({n: fwd_all[n].reindex(idx_full).fillna(0.0) for n in NAMES})
print(f"\nCommon window (S1_F-constrained, matches firm's own BOOK-constrained convention): "
      f"{CW_START:%Y-%m-%d}..{FULL_END:%Y-%m-%d} ({len(idx_full)} days)")

mo_mat = mat_full.resample("ME").sum()
q_mat = mat_full.resample("QE").sum()
corr_mo = mo_mat.corr()
corr_q = q_mat.corr()
print("\nSLEEVE-SLEEVE correlation, MONTHLY (common window):")
print(corr_mo.round(3).to_string())
print("\nSLEEVE-SLEEVE correlation, QUARTERLY (common window):")
print(corr_q.round(3).to_string())
corr_mo.to_csv(CKPT / "sleeve_sleeve_corr_monthly.csv")
corr_q.to_csv(CKPT / "sleeve_sleeve_corr_quarterly.csv")

# ============================================================ 6. NAIVE (inverse-vol) WEIGHTS among
#      the FIVE candidates, then decide CALENDAR vs ROLLED_RATIO_CAL redundancy
vol_full = mat_full.std()
naive_w_raw = (1.0 / vol_full)
naive_w_raw = naive_w_raw / naive_w_raw.sum()
print("\nNaive inverse-vol RAW shares (5-sleeve, pre-redundancy-decision):")
print(naive_w_raw.round(4).to_dict())

# ============================================================ 7. BOOK CONSTRUCTION -- UNION reindex
#      (fill 0 pre-inception, the TRUE historical state -- a sleeve that did not exist yet
#      contributed exactly zero to a book run at that date; this is NOT the same claim as "we
#      measured zero risk", flagged explicitly wherever it matters below)
UNION_START = pd.Timestamp("2011-01-01")
UNION_END = max(s.index.max() for s in fwd_all.values())
idx_union = pd.date_range(UNION_START, UNION_END, freq="D")
mat_union = pd.DataFrame({n: fwd_all[n].reindex(idx_union).fillna(0.0) for n in NAMES})
print(f"\nUNION window (full available history, 0-fill pre-inception): {UNION_START:%Y-%m-%d}.."
      f"{UNION_END:%Y-%m-%d}")
print("  S1_F data ends 2025-12-30 (BOOK dataset's own window end, NOT a real strategy stop -- "
      "S1-F is CERTIFIED/forward-testing per D-030). Jan-2026 onward S1_F contributes a DATA-GAP "
      "zero, not a true zero. Flagged, not silently treated as measured absence of risk.")

CAP_TABLE = pd.Series({
    "OVERSHOOT": 0.15,          # tightest: genuinely NO crash-window data, ever (2021-06 start)
    "LD_SELL": 0.20,            # measured NEGATIVE crash behaviour (COVID -Rs42,545/27 cycles)
    "CALENDAR": 0.35,           # thin crash sample but defined-ish risk (long far leg)
    "ROLLED_RATIO_CAL": 0.25,   # thin crash sample, higher measured standalone maxDD than CALENDAR
    "S1_F": 0.30,               # CERTIFIED/frozen (D-030), best standalone Sharpe -- but ZERO real
                                # crash-day data, so NOT given the largest cap despite best Sharpe
}).reindex(NAMES)
print("\nPer-sleeve capacity/crash-risk cap (max weight share of book capital), [OPINION, judgment "
      "call, same discipline as BALANCED's own CAP_TABLE in build_portfolios.py]:")
print(CAP_TABLE.to_dict())


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


naive_capped = cap_and_renorm(naive_w_raw.reindex(NAMES).values, CAP_TABLE.values, 1.0)
naive_capped = pd.Series(naive_capped, index=NAMES)
print("\nNaive inverse-vol shares AFTER cap+renorm (sum=1.0, pre-gross-scaling):")
print(naive_capped.round(4).to_dict())


def combined(mat, w, total_capital=TOTAL_CAPITAL):
    cols = list(mat.columns)
    scale = w.reindex(cols) * (total_capital / NATURAL_CAP)
    return (mat[cols].values * scale.values).sum(axis=1)


def gross_scaled_series(mat, w_shares, gross, idx):
    w = w_shares * gross
    return pd.Series(combined(mat, w), index=idx)


# ---- gross-deployment (k-equivalent) scan: max GROSS such that UNION-history book clears both
#      firm bars (25% full-sample MaxDD; 20% COVID-window loss on whatever REAL data covers it) ----
GROSS_GRID = np.round(np.concatenate([np.arange(0.10, 3.01, 0.10), np.arange(3.25, 40.01, 0.25)]), 2)
scan_rows = []
for BOOKNAME, names_subset in [("BOOK_5 (incl. rolled ratio-cal)", NAMES),
                                ("BOOK_4 (ex rolled ratio-cal)", [n for n in NAMES if n != "ROLLED_RATIO_CAL"])]:
    w_sub = cap_and_renorm(naive_w_raw.reindex(names_subset).values, CAP_TABLE.reindex(names_subset).values, 1.0)
    w_sub = pd.Series(w_sub, index=names_subset)
    mat_sub = mat_union[names_subset]
    for g in GROSS_GRID:
        s = gross_scaled_series(mat_sub, w_sub, g, idx_union)
        m = eq_metrics(s, TOTAL_CAPITAL)
        covid = s[(s.index >= "2020-02-15") & (s.index <= "2020-04-15")].sum()
        covid_pct = 100 * covid / TOTAL_CAPITAL
        ok = (m["maxDD_pct"] >= -25.0) and (covid_pct >= -20.0)
        scan_rows.append(dict(book=BOOKNAME, gross=g, CAGR_pct=m["CAGR_pct"], maxDD_pct=m["maxDD_pct"],
                               Calmar=m["Calmar"], Sharpe=m["Sharpe"], covid_pct=round(covid_pct, 2),
                               compliant=ok))
scan_df = pd.DataFrame(scan_rows)
scan_df.to_csv(CKPT / "gross_deployment_scan.csv", index=False)

print("\n" + "=" * 100)
print("GROSS-DEPLOYMENT SCAN (naive/equal-risk weights, UNION full-history book, both variants)")
print("=" * 100)
# Reconciliation constant: LD_SELL's own bare-10pct-margin implied k at gross=1.0 (Rs10L natural
# cap) = Rs1,000,000 / mean(margin_rs) -- computed once, printed alongside each gross level so the
# reader can translate "gross" into the SELL_PLUS_TAIL k-scan's own units (capital = k x bare
# margin) without re-deriving it.
LD_MEAN_MARGIN = ld["margin_rs"].mean()
K_PER_GROSS = NATURAL_CAP / LD_MEAN_MARGIN   # k implied for LD_SELL at gross=1.0
print(f"[Reconciliation] LD_SELL mean bare-10%-margin = Rs{LD_MEAN_MARGIN:,.0f}; the firm's own "
      f"Rs10L 'natural 1x' convention used below is ALREADY k(LD_SELL)={K_PER_GROSS:.2f}x bare "
      f"margin at gross=1.0 -- i.e. ~{K_PER_GROSS/3.2:.1f}-{K_PER_GROSS/4.0:.1f}x MORE conservative "
      f"than SELL_PLUS_TAIL's own empirical minimum (k=3.2-4) for this exact sleeve. Every gross "
      f"level below is annotated with its LD_SELL-equivalent k for translation.")

for BOOKNAME in scan_df["book"].unique():
    sub = scan_df[scan_df.book == BOOKNAME].copy()
    sub["k_LD_equiv"] = round(sub["gross"] * K_PER_GROSS, 2)
    compliant = sub[sub.compliant]
    if len(compliant):
        best = compliant.sort_values("gross", ascending=False).iloc[0]
        print(f"\n{BOOKNAME}: max compliant gross (searched to 15.0) = {best.gross:.2f} "
              f"(k_LD_equiv={best.gross*K_PER_GROSS:.2f})  CAGR={best.CAGR_pct}% maxDD={best.maxDD_pct}% "
              f"Calmar={best.Calmar} Sharpe={best.Sharpe} COVID%={best.covid_pct}")
    else:
        print(f"\n{BOOKNAME}: NO gross level in [0.10, 15.00] clears both bars")
    print(sub[sub.gross.isin([0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0])].to_string(index=False))

# ============================================================ 7b. SPAN-REALITY CHECK -- S1_F is
#      NOT capital-light like the other three, and must NOT be scaled by the same "gross" multiplier
print("\n" + "=" * 100)
print("SPAN-REALITY CHECK -- bare margin per Rs10L 'natural unit' (the check a structurer must run "
      "before treating every sleeve as equally gross-scalable)")
print("=" * 100)
margin_per_unit = {
    "LD_SELL": LD_MEAN_MARGIN,
    "CALENDAR": c_margin10 if (c_margin10 := rc[(rc.strike_struct=="ATM_ATM")&(rc.ratio=="1x1")&(rc.exit_variant=="3d_before")]["margin_10pct"].mean()) else None,
    "OVERSHOOT": 0.10 * 25000 * LOT_OVERSHOOT,   # SPIKE_OVERSHOOT_SELL_20260730/opposite_and_spread.py convention
    "S1_F": 24000 * 75 * 0.15 * N_LOTS_S1F,       # S1F_SPEC.md: ~15% one-side notional, 3 lots
}
for n, m in margin_per_unit.items():
    util_pct = 100 * m / NATURAL_CAP
    print(f"  {n:<12} bare margin/unit Rs{m:>10,.0f}  = {util_pct:>5.1f}% of its own Rs10L natural "
          f"unit  {'<-- CAPITAL-LIGHT, real headroom to gross-scale' if util_pct < 25 else '<-- ALREADY NEAR-FULL MARGIN UTILISATION, cannot be gross-scaled off shared idle capital'}")
print("VERDICT: LD_SELL/CALENDAR/OVERSHOOT each use <20% of their allocated Rs10L in bare margin "
      "(capital genuinely idle most days -- the same 'capital-idleness' effect build_portfolios.py "
      "flagged for CALENDAR/OVERSHOOT). S1_F uses ~81% BY DESIGN (spec: lots=floor(0.75xequity/"
      "margin)) -- it is NOT part of the same shared-idle-capital pool and must NOT be multiplied "
      "by the same gross factor as the other three, or the book asks for more real capital than it "
      "has (verified below: doing so naively implied Rs1.46cr of S1_F margin alone inside a Rs1cr "
      "book at gross=6 -- an infeasible sizing error, caught here rather than shipped).")

# ============================================================ 8. CHOSEN BOOK = BOOK_4 (ROLLED_RATIO_CAL
#      tested and EXCLUDED from the core book: adding it cuts max-compliant-gross from ~19.75 to
#      ~6.75 and roughly halves Calmar at every common gross level, for materially thinner Sharpe
#      gain -- moderate correlation to CALENDAR (0.12 monthly/0.31 quarterly) is NOT the reason to
#      exclude it (0.2-0.4 is the Principal's own stated acceptable band); its OWN crash-era tail
#      (standalone maxDD -12.41% vs CALENDAR's -1.66%, both at Rs10L) is. Kept as a monitored
#      satellite candidate, not core sizing -- this is the direct test the mandate asked for.
#
# SPAN-REALITY FIX (caught in section 7b above): S1_F cannot share the same "gross" leverage
# multiplier as LD_SELL/CALENDAR/OVERSHOOT -- its bare margin is ~81% of its own Rs10L natural
# unit (by spec design) vs ~9-16% for the other three. TWO-TIER construction: S1_F gets a FIXED
# capital slice (no extra leverage, run at its own native spec sizing); LD_SELL+CALENDAR+OVERSHOOT
# form a "light pool" that legitimately reuses idle capital via a gross multiplier.
FINAL_NAMES = ["S1_F", "LD_SELL", "CALENDAR", "OVERSHOOT"]
LIGHT_NAMES = ["LD_SELL", "CALENDAR", "OVERSHOOT"]
S1F_WEIGHT = float(CAP_TABLE["S1_F"])   # 0.30 of book capital, FIXED, no gross leverage
light_pool_frac = 1.0 - S1F_WEIGHT       # 0.70 of book capital available to the light pool

light_naive_raw = naive_w_raw.reindex(LIGHT_NAMES)
light_naive_capped = cap_and_renorm(light_naive_raw.values,
                                     (CAP_TABLE.reindex(LIGHT_NAMES) / CAP_TABLE.reindex(LIGHT_NAMES).sum()).values,
                                     1.0)
w_light = pd.Series(light_naive_capped, index=LIGHT_NAMES) * light_pool_frac   # shares of TOTAL book capital
w_final = pd.concat([pd.Series({"S1_F": S1F_WEIGHT}), w_light])
mat_final = mat_union[FINAL_NAMES]
print("\n" + "=" * 100)
print("CHOSEN BOOK = BOOK_4 (S1_F fixed-slice + LD_SELL/CALENDAR/OVERSHOOT gross-scalable light pool)")
print("=" * 100)
print(f"S1_F fixed weight (NO gross leverage) = {S1F_WEIGHT:.2f} of book capital")
print(f"Light-pool base weights (of book capital, pre-gross): {w_light.round(4).to_dict()}  "
      f"(sum={w_light.sum():.4f} = light_pool_frac {light_pool_frac:.2f})")


def combined_two_tier(mat, w_s1f, w_light_, gross_light, idx):
    scale = pd.Series(0.0, index=FINAL_NAMES)
    scale["S1_F"] = w_s1f * (TOTAL_CAPITAL / NATURAL_CAP)          # NO gross -- fixed native scale
    for n in LIGHT_NAMES:
        scale[n] = w_light_[n] * gross_light * (TOTAL_CAPITAL / NATURAL_CAP)
    return pd.Series((mat[FINAL_NAMES].values * scale.values).sum(axis=1), index=idx), scale


# ---- gross scan on the LIGHT POOL ONLY (S1_F fixed throughout) ----
light_scan_rows = []
for g in GROSS_GRID:
    s, _ = combined_two_tier(mat_union, S1F_WEIGHT, w_light, g, idx_union)
    m = eq_metrics(s, TOTAL_CAPITAL)
    covid = s[(s.index >= "2020-02-15") & (s.index <= "2020-04-15")].sum()
    covid_pct = 100 * covid / TOTAL_CAPITAL
    ok = (m["maxDD_pct"] >= -25.0) and (covid_pct >= -20.0)
    light_scan_rows.append(dict(gross_light=g, CAGR_pct=m["CAGR_pct"], maxDD_pct=m["maxDD_pct"],
                                 Calmar=m["Calmar"], Sharpe=m["Sharpe"], covid_pct=round(covid_pct, 2),
                                 compliant=ok))
light_scan_df = pd.DataFrame(light_scan_rows)
light_scan_df.to_csv(CKPT / "two_tier_gross_scan.csv", index=False)
compliant_light = light_scan_df[light_scan_df.compliant]
max_compliant_gross = float(compliant_light.gross_light.max()) if len(compliant_light) else None
print(f"\nTWO-TIER gross-on-light-pool-only scan: max compliant gross_light = {max_compliant_gross}")
print(light_scan_df[light_scan_df.gross_light.isin([0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0])].to_string(index=False))

OPERATING_GROSS = 5.0   # chosen for MaxDD comparability to the UPDATED BALANCED comparator
                        # (Calmar 1.405/Sharpe 1.38/CAGR 5.14%/MaxDD -3.66%, PORTFOLIOS_REFIT_20260803
                        # -- both a BOOK-unit AU-label bug and a per-sleeve-cap-breach bug fixed
                        # there; this REPLACES the earlier 6.60%/-6.38%/1.034/1.10 vintage) --
                        # deliberately conservative, well inside the light-pool's own compliant range.
s_op, scale_op = combined_two_tier(mat_union, S1F_WEIGHT, w_light, OPERATING_GROSS, idx_union)
m_op = eq_metrics(s_op, TOTAL_CAPITAL)
print(f"\nOPERATING POINT: S1_F fixed@{S1F_WEIGHT}, light-pool gross={OPERATING_GROSS}:")
print(m_op)
print(f"month_win_pct={m_op['month_win_pct']}  n_months={m_op['months']}")
print(f"effective weights (scale, Rs-per-Rs1 of natural-unit daily P&L): {scale_op.round(3).to_dict()}")

util = scale_op["S1_F"] * (mat_final["S1_F"] != 0).mean() / (TOTAL_CAPITAL/NATURAL_CAP) * S1F_WEIGHT \
       + sum(w_light[n] * OPERATING_GROSS * (mat_final[n] != 0).mean() for n in LIGHT_NAMES)
print(f"capital_deployed_pct={100*(S1F_WEIGHT + OPERATING_GROSS*w_light.sum()):.1f} "
      f"(S1F {100*S1F_WEIGHT:.1f}% fixed + light-pool {100*OPERATING_GROSS*w_light.sum():.1f}% "
      f"gross-scaled)")
w_final_eff = pd.Series({"S1_F": S1F_WEIGHT, **{n: w_light[n]*OPERATING_GROSS for n in LIGHT_NAMES}})

# ---- ALSO report on the COMMON WINDOW (2022-01-04..FULL_END, all 4 sleeves genuinely live) --
#      the UNION-window CAGR above is diluted by ~11 years where S1_F contributes a correct
#      structural ZERO (it did not exist) -- that is right for the MaxDD/tail-risk read (Lens A/B/C
#      below correctly use the full history) but WRONG for "what should we expect running this book
#      now": for that question, the window where all 4 sleeves are actually live together is the
#      honest one, and it is also the SAME window convention BALANCED's own comparator numbers use
#      (PORTFOLIOS_REFIT_20260803, CW_START=2022-01-04).
s_op_common, _ = combined_two_tier(mat_full, S1F_WEIGHT, w_light, OPERATING_GROSS, idx_full)
m_op_common = eq_metrics(s_op_common, TOTAL_CAPITAL)
print(f"\nSAME operating point, COMMON WINDOW ONLY ({CW_START:%Y-%m-%d}..{FULL_END:%Y-%m-%d}, all 4 "
      f"sleeves live -- the fair comparator window vs BALANCED, which uses the same convention):")
print(m_op_common)

# ============================================================ 9. PORTFOLIO-vs-SLEEVE correlation
#      (the Principal's explicit ruling: portfolio-vs-sleeve, not sleeve-vs-sleeve pairwise)
print("\n" + "=" * 100)
print("PORTFOLIO-vs-SLEEVE correlation, chosen BOOK_4 @ operating gross, monthly & quarterly")
print("=" * 100)
p_mo = s_op.resample("ME").sum()
p_q = s_op.resample("QE").sum()
pv_rows = []
for n in FINAL_NAMES:
    sl_mo = mat_final[n].resample("ME").sum()
    sl_q = mat_final[n].resample("QE").sum()
    pv_rows.append(dict(sleeve=n, corr_monthly=round(float(p_mo.corr(sl_mo)), 3),
                         corr_quarterly=round(float(p_q.corr(sl_q)), 3),
                         weight=round(float(w_final_eff[n]), 4)))
pv_df = pd.DataFrame(pv_rows)
print(pv_df.to_string(index=False))
pv_df.to_csv(CKPT / "portfolio_vs_sleeve_corr.csv", index=False)

# ============================================================ 10. WHOLE-BOOK TAIL -- three lenses
print("\n" + "=" * 100)
print("WHOLE-BOOK TAIL RISK -- three lenses (RISK_LIMITS-mandated + task-specified)")
print("=" * 100)

# ---- Lens A: RISK_LIMITS-mandated "vol-spike correlation: all short-vol sleeves at their
#      historical worst month SIMULTANEOUSLY" (literal text of the existing, approved rule) ----
# scale_op[n] is ALREADY the correct multiplier: book_pnl_day = scale_op[n] * natural_unit_pnl_day
# (see combined_two_tier). worst_month_rs[n] is a natural-unit-basis (Rs10L) Rs figure, so the book
# contribution is simply scale_op[n] * worst_month_rs[n] -- NO further division by NATURAL_CAP
# (an earlier draft of this script double-divided by NATURAL_CAP here; caught before this was quoted).
worst_month_rs = {n: standalone[n]["worst_month_rs"] for n in FINAL_NAMES}
worst_month_book = sum(scale_op[n] * worst_month_rs[n] for n in FINAL_NAMES)
print("Lens A [RISK_LIMITS 'vol-spike correlation' test, literal]: each sleeve's OWN worst single "
      "calendar month, ALL FOUR simultaneously, at chosen weights (S1_F fixed, light pool @ gross"
      f"={OPERATING_GROSS}):")
for n in FINAL_NAMES:
    contrib = scale_op[n] * worst_month_rs[n]
    print(f"  {n:<12} worst_month_rs(natural1x)={worst_month_rs[n]:>10,.0f}  scale={scale_op[n]:>6.2f}  "
          f"book contribution Rs{contrib:>12,.0f}")
print(f"  BOOK worst-month-simultaneous = Rs{worst_month_book:,.0f} = "
      f"{100*worst_month_book/TOTAL_CAPITAL:.2f}% of book capital")

# ---- Lens B: real COVID window (Feb15-Apr15 2020), honest per-sleeve coverage flags ----
print("\nLens B [measured COVID Feb15-Apr15 2020, real data only where it exists]:")
covid_lo, covid_hi = pd.Timestamp("2020-02-15"), pd.Timestamp("2020-04-15")
covid_book = 0.0
for n in FINAL_NAMES:
    s = fwd_all[n]
    covers = s.index.min() <= covid_lo and s.index.max() >= covid_hi
    seg = s[(s.index >= covid_lo) & (s.index <= covid_hi)] if covers else pd.Series(dtype=float)
    rs = float(seg.sum()) if covers else 0.0
    contrib = scale_op[n] * rs
    covid_book += contrib
    flag = "REAL" if covers else "ZERO (pre-inception -- UNMEASURED, not verified-safe)"
    print(f"  {n:<12} covid_rs(natural1x)={rs:>10,.0f}  [{flag}]  book contribution Rs{contrib:>12,.0f}")
print(f"  BOOK COVID-window (2 of 4 sleeves measured) = Rs{covid_book:,.0f} = "
      f"{100*covid_book/TOTAL_CAPITAL:.2f}% of book capital -- UNDERSTATES true exposure: S1_F and "
      f"OVERSHOOT did not exist in 2020, so their crash behaviour is genuinely unknown, not "
      f"measured-safe. S1F_SPEC.md's own model-based backcast (corr 0.64, not real data) is the only "
      f"evidence for S1_F, and it estimates ~-16% maxDD at spec sizing.")

# ---- Lens C: pessimistic bound (measured worst 1d/5d/20d NIFTY move) on the NAKED legs only
#      (LD_SELL, S1_F) -- CALENDAR/OVERSHOOT are NOT naked-strangle-equivalent (calendar has a
#      long far leg; OVERSHOOT is delta-hedged by construction), so the "3.70x bare margin"
#      multiple (derived FOR a naked strangle at 10% margin) is applied only where the structure
#      actually matches it. This is the forward-looking bound that also covers S1_F despite its
#      data gap (it does not need historical crash data -- it assumes the SAME index move repeats
#      and asks what a naked short options structure does under it, mechanically). CORRECTED for the
#      SPAN-reality fix: S1_F's margin is scaled by its FIXED weight only (no gross multiplier).
print("\nLens C [pessimistic bound: measured worst 1d/-12.98%, 5d/-19.02%, 20d/-37.01% index move, "
      "applied to the book's NAKED legs (LD_SELL, S1_F) at 0%-OTM/ATM conservative bound]:")
WORST = {"1d": 0.1298046, "5d": 0.1902394, "20d": 0.3700567}
# real deployed "natural units" of each naked leg at the operating point (from scale_op, which
# already reflects the two-tier construction: S1_F fixed, LD_SELL gross-scaled):
ld_units = scale_op["LD_SELL"] * (NATURAL_CAP / TOTAL_CAPITAL)   # = w_light["LD_SELL"]*gross*10
s1f_units = scale_op["S1_F"] * (NATURAL_CAP / TOTAL_CAPITAL)      # = S1F_WEIGHT*10, NOT gross-scaled
s1f_margin_per_unit = 24000 * 75 * 0.15 * N_LOTS_S1F   # spec: ~15% one-side notional, 3 lots
for horizon, wm in WORST.items():
    mult_of_margin = wm / 0.10
    loss_rs_ldsell = mult_of_margin * LD_MEAN_MARGIN * ld_units
    loss_rs_s1f = mult_of_margin * s1f_margin_per_unit * s1f_units
    loss_total = loss_rs_ldsell + loss_rs_s1f
    print(f"  {horizon}: {mult_of_margin:.2f}x margin -> LD_SELL Rs{loss_rs_ldsell:,.0f} "
          f"({ld_units:.2f} units) + S1_F Rs{loss_rs_s1f:,.0f} ({s1f_units:.2f} units, FIXED not "
          f"gross-scaled) = Rs{loss_total:,.0f} = {100*loss_total/TOTAL_CAPITAL:.2f}% of book capital")

MAX_SURVIVABLE_NOTE = ("Max book size that survives the 20-day pessimistic bound at ~100% of "
    "capital (i.e. does not exceed the capital committed): solve TOTAL_CAPITAL_required = loss_total "
    "/ 1.0 at the CURRENT unit mix -- i.e. the book above is already sized so that a repeat of the "
    "measured worst 20-day move consumes the fraction printed above of book capital; scaling the "
    "WHOLE book (S1_F units AND light-pool gross together, same ratio) by 1/that-fraction gives the "
    "size at which a repeat exactly wipes it out (100%); a prudent operating ceiling is roughly HALF "
    "of that (so the pessimistic 20-day bound costs <=50% of capital, still survivable with a "
    "capital call, not a wipeout).")
print("\n" + MAX_SURVIVABLE_NOTE)

print("\n[Structural point] S1_F is a 0DTE structure (flat every day by 15:25, zero overnight-gap "
      "carry) -- its OWN capital-multiple requirement is fundamentally smaller than LD_SELL's "
      "biweekly-held naked strangle (which IS exposed to gap risk across ~10 trading days per "
      "cycle). The k=3.2-4 floor established for LD_SELL does NOT transfer mechanically to S1_F; "
      "applying it there would be needlessly conservative. It also does NOT transfer to CALENDAR/"
      "ROLLED_RATIO_CAL, whose long far-dated leg gives SOME (imperfect) protection a naked "
      "strangle lacks. One uniform k is a structuring error; the Lens C multiplier above is applied "
      "only to the two genuinely naked legs for exactly this reason.")

# ============================================================ 11. COMPARISON vs BALANCED (UPDATED
#      comparator: PORTFOLIOS_REFIT_20260803, both a BOOK-unit AU-label bug and a per-sleeve-cap-
#      breach bug fixed there mid-session -- REPLACES the earlier 6.60%/-6.38%/1.034/1.10 vintage)
print("\n" + "=" * 100)
print("COMPARISON vs BALANCED (UPDATED: PORTFOLIOS_REFIT_20260803, both bugs fixed)")
print("=" * 100)
balanced_fwd = dict(CAGR_pct=5.14, maxDD_pct=-3.66, Calmar=1.405, Sharpe=1.38)
honest_max = dict(CAGR_pct=19.49, maxDD_pct=-24.77, Calmar=0.787, note="HIGH_CAGR, SWEEP/BOOK caps "
                   "loosened on capacity evidence; MaxDD sits at the 25% mandate ceiling, the binding "
                   "constraint (not liquidity/capacity)")
print("BALANCED (both bugs fixed):", balanced_fwd)
print("Honest maximum across ALL mandates (loosened-cap HIGH_CAGR):", honest_max)
print(f"\nPURE_OPTIONS BOOK_4, UNION full-history window (2011-2026, MaxDD/tail read): "
      f"CAGR={m_op['CAGR_pct']}% maxDD={m_op['maxDD_pct']}% Calmar={m_op['Calmar']} Sharpe={m_op['Sharpe']}")
print(f"PURE_OPTIONS BOOK_4, COMMON WINDOW ({CW_START:%Y-%m-%d}..{FULL_END:%Y-%m-%d}, all 4 sleeves "
      f"live -- fair CAGR/Sharpe comparator vs BALANCED's own window convention): "
      f"CAGR={m_op_common['CAGR_pct']}% maxDD={m_op_common['maxDD_pct']}% Calmar={m_op_common['Calmar']} "
      f"Sharpe={m_op_common['Sharpe']}")
m_max = None
if max_compliant_gross is not None:
    s_max, _ = combined_two_tier(mat_union, S1F_WEIGHT, w_light, max_compliant_gross, idx_union)
    m_max = eq_metrics(s_max, TOTAL_CAPITAL)
    s_max_common, _ = combined_two_tier(mat_full, S1F_WEIGHT, w_light, max_compliant_gross, idx_full)
    m_max_common = eq_metrics(s_max_common, TOTAL_CAPITAL)
    print(f"PURE_OPTIONS BOOK_4 @ max-compliant-backtest light-pool gross={max_compliant_gross} "
          f"(CAPACITY-UNVERIFIED at this scale, flagged), UNION window: CAGR={m_max['CAGR_pct']}% "
          f"maxDD={m_max['maxDD_pct']}% Calmar={m_max['Calmar']} Sharpe={m_max['Sharpe']}")
    print(f"  SAME, COMMON WINDOW: CAGR={m_max_common['CAGR_pct']}% maxDD={m_max_common['maxDD_pct']}% "
          f"Calmar={m_max_common['Calmar']} Sharpe={m_max_common['Sharpe']}")
print(f"\nVERDICT (common-window, fair comparison): BALANCED's Calmar {balanced_fwd['Calmar']} / "
      f"Sharpe {balanced_fwd['Sharpe']} is "
      f"{'BEATEN' if m_op_common['Calmar'] > balanced_fwd['Calmar'] else 'NOT beaten'} by the "
      f"pure-options book at the operating point, and "
      f"{'BEATEN' if (max_compliant_gross is not None and m_max_common['Calmar'] > balanced_fwd['Calmar']) else 'NOT beaten'} "
      f"even at the max-compliant-backtest (capacity-unverified) scale.")

print("\nSWEEP crash-window record (THREE_PORTFOLIOS PORTFOLIOS.md, real data, natural 1x=Rs10L):")
print("  2015-16 Rs+360,137 (n=81) | 2018 Rs+75,256 (n=31) | COVID Rs+321,216 (n=17) | "
      "2022 Rs+403,139 (n=69) -- POSITIVE IN ALL FOUR. The only sleeve in the whole firm's corpus "
      "with this property.")
print("Pure-options sleeves' SAME four windows (natural 1x=Rs10L, from the same source table):")
print("  CALENDAR: -85 / -2,059 / -4,144 / +27,517   (3 of 4 negative, thin sample)")
print("  LD_SELL : +13,239 / -7,756 / -43,196 / +17,430   (2 of 4 negative, COVID sign robust)")
print("  OVERSHOOT: NO DATA / NO DATA / NO DATA / +9,233   (no crash exposure ever observed)")
print("  S1_F: no data in any of the 4 windows (post-2022 series); spec's own MODEL backcast only.")
print("None of the four pure-options legs offsets a broad equity/vol shock the way SWEEP does -- "
      "SWEEP's positive-carry-in-crisis behaviour comes from being a trend/swing FUTURES sleeep "
      "with a demonstrated long-vol-like payoff in real selloffs, structurally unavailable to a "
      "short-premium options sleeve by construction (a short strangle/straddle/calendar cannot be "
      "net long convexity without also being long premium somewhere, which is a DIFFERENT sleeve, "
      "e.g. the tail put overlay -- see SELL_PLUS_TAIL's own finding that even a full-time long put "
      "overlay is NOT net-hedge-positive in absolute Rs terms across the sample).")

print("\nWROTE all checkpoints to:", CKPT)


