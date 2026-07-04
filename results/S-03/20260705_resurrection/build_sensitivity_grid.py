"""S-03 K-012 RESURRECTION -- Leg 1/3: premium-cap x FF-threshold sensitivity grid.
Owner: Dr. Sameer Bhat (Overfit & Sensitivity Analyst). 2026-07-05.

WHY THIS SCRIPT EXISTS (process note): the 2026-07-05 04:xx "SIZING_RECHECK" that produced
trading_brief_stats.json / SIZING_RECHECK.md was run interactively and NO SCRIPT SURVIVED in
results/S-03/20260704_shuffle/ (only the two output files, dated a day after the scripts in that
dir). The sizing formula had to be reverse-engineered from data + the two output artifacts before
any grid could be trusted. See VALIDATION block below and SENSITIVITY_FF_SIZING.md for the
reproduction evidence. LESSON: ad hoc analyses must checkpoint the script, not just the output.

RECONSTRUCTED METHODOLOGY (validated against trading_brief_stats.json to 4 sig figs):
  1. Universe: large-cap gate = symbols whose FIRST FF-candidate entry is before 2024-01-01
     (ex-ante liquid names only), computed ONCE on the full 4585-row universe (independent of
     the FF threshold grid parameter -- matches ff_shuffle.py/ff_points_decisive.py convention).
  2. FF filter: ff >= FF_MIN (grid parameter, chosen point 0.25).
  3. Per-trade P&L (CE-leg calendar, rupee points): pnl_i = LOT_MULT *
       (CE_fe*(1-SLIP) - CE_be*(1+SLIP) - CE_fx*(1+SLIP) + CE_bx*(1-SLIP))
     LOT_MULT=2 is a pure scale constant (matches the registered BASE absolute-rupee scale
     exactly: raw-formula sum*2 = 3497.27 vs registered 3497.0). It cancels in every ratio
     metric (per-Rs100, PF, win rate) and is kept ONLY so absolute-rupee columns (total, worst)
     are comparable to the register.
  4. Sizing (the parameter under test): target = median(CE_be) over the (large-cap, FF>=FF_MIN)
     slice for THIS cell (build+forward combined -- see LOOKAHEAD FLAG below).
       lots_i      = min(target / CE_be_i, CAP_MULT)      [CAP_MULT=inf => uncapped equal-premium]
       deployed_i  = lots_i * CE_be_i
       rupee_pnl_i = lots_i * pnl_i
  5. Aggregation: ALWAYS ratio-of-sums, never mean-of-ratios --
       P&L per Rs100 deployed = 100 * sum(rupee_pnl_i) / sum(deployed_i)     over the period slice
     (the denominator-artifact hard rule: per-trade pnl_i/CE_be_i ratios are NEVER averaged raw).
  6. BUILD = entry<=2024-12-31, FORWARD = entry>2024-12-31 (matches SIZING_RECHECK split).

VALIDATION (see build_sensitivity_grid_VALIDATION.txt written by this script):
  at FF_MIN=0.25, CAP_MULT=3, FULL (build+fwd) sample: this script's pf/win/total/worst match
  trading_brief_stats.json's RECOMMENDED row to <0.1%. SIZING_RECHECK.md's separately-reported
  BUILD/FORWARD per-Rs100 split (+12.43/+9.91) is NOT reproduced by this formula's own
  build/forward split (+26.7/+21.1 here) -- a systematic ~2.1x gap, sign and ordering preserved.
  This is flagged explicitly; it does not affect the trading_brief_stats.json reproduction (exact)
  or the internal validity of this grid (every cell uses the identical, self-consistent recipe).

LOOKAHEAD FLAG (D-028, self-audited): "target" is computed on the FULL (build+forward) slice,
i.e. the sizing constant uses information from the forward period to size build-period trades.
This matches what the original (unrecovered) script appears to have done (see validation), but a
LIVE trader in the build period would not know the forward median. This is a sizing CONSTANT, not
a signal, so severity is low, but it is a genuine T-class lookahead artifact and is called out
in the deliverable. A lookahead-safe variant (target fit on BUILD only, applied out-of-sample)
was also tested during reconstruction (see explore04 residuals) and is monotonically similar but
numerically different -- not the one carried into the headline register numbers.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
FF_PATH = ROOT / "intraday_options_strategy/buying/forward_factor_v2.parquet"
OUT = ROOT / "Shreyas_Ionic_AMC/results/S-03/20260705_resurrection"
OUT2 = ROOT / "results/S-03/20260705_resurrection"  # actual working results tree used this session
SLIP = 0.015
LOT_MULT = 2.0
SPLIT = pd.Timestamp(2024, 12, 31)

CAP_GRID = [1, 2, 3, 4, 5, None]      # None = uncapped equal-premium
FF_GRID = [0.15, 0.20, 0.25, 0.30, 0.35]

CSV_PATH = OUT2 / "sensitivity_grid.csv"
VALIDATION_PATH = OUT2 / "build_sensitivity_grid_VALIDATION.txt"

CSV_FIELDS = [
    "cap_mult", "ff_min", "period", "n", "total_pnl_rupees", "pnl_per_100_deployed",
    "profit_factor", "win_rate_pct", "worst_trade_rupees", "maxdd_pct_of_avg_monthly_deployed",
    "target_median_ce_be", "deployed_sum_rupees",
]


def load_base():
    ff = pd.read_parquet(FF_PATH)
    ff["entry"] = pd.to_datetime(ff["entry"])
    ff["m1_exp"] = pd.to_datetime(ff["m1_exp"])
    ff["pnl"] = LOT_MULT * (ff["CE_fe"] * (1 - SLIP) - ff["CE_be"] * (1 + SLIP)
                             - ff["CE_fx"] * (1 + SLIP) + ff["CE_bx"] * (1 - SLIP))
    ff["month"] = ff["m1_exp"].dt.to_period("M")
    first = ff.groupby("sym")["entry"].min()
    lc_syms = set(first[first < pd.Timestamp(2024, 1, 1)].index)
    L = ff[ff["sym"].isin(lc_syms)].copy()
    return ff, L, lc_syms


def cell_frame(L, ff_min):
    S = L[L["ff"] >= ff_min].copy()
    target = S["CE_be"].median()
    return S, target


def size_and_eval(df, target, cap_mult):
    ce_be = df["CE_be"].to_numpy(float)
    pnl = df["pnl"].to_numpy(float)
    if cap_mult is None:
        lots = target / ce_be
    else:
        lots = np.minimum(target / ce_be, float(cap_mult))
    deployed = lots * ce_be
    rpnl = lots * pnl

    n = len(df)
    total = float(rpnl.sum())
    deployed_sum = float(deployed.sum())
    per100 = 100.0 * total / deployed_sum if deployed_sum > 0 else np.nan
    wins = rpnl[rpnl > 0]
    losses = rpnl[rpnl <= 0]
    win_rate = 100.0 * len(wins) / n if n else np.nan
    pf = (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else np.inf
    worst = float(rpnl.min()) if n else np.nan

    # maxDD as % of avg monthly deployed: monthly-bucket (by exit month m1_exp) cumulative rupee
    # P&L curve, peak-to-trough max drawdown, expressed against the average monthly deployed capital.
    tmp = pd.DataFrame({"month": df["month"].to_numpy(), "rpnl": rpnl, "deployed": deployed})
    monthly = tmp.groupby("month").agg(rpnl=("rpnl", "sum"), deployed=("deployed", "sum")).sort_index()
    if len(monthly) > 0 and monthly["deployed"].mean() > 0:
        cum = monthly["rpnl"].cumsum()
        peak = cum.cummax()
        dd = peak - cum
        maxdd_rupees = float(dd.max())
        avg_monthly_deployed = float(monthly["deployed"].mean())
        maxdd_pct = 100.0 * maxdd_rupees / avg_monthly_deployed
    else:
        maxdd_pct = np.nan

    return dict(n=n, total_pnl_rupees=total, pnl_per_100_deployed=per100, profit_factor=pf,
                win_rate_pct=win_rate, worst_trade_rupees=worst,
                maxdd_pct_of_avg_monthly_deployed=maxdd_pct,
                deployed_sum_rupees=deployed_sum)


def run():
    ff, L, lc_syms = load_base()
    print(f"universe: full={len(ff)} large-cap-symbols={len(lc_syms)} large-cap-rows={len(L)}")

    # ---- VALIDATION BLOCK: reproduce trading_brief_stats.json at FF_MIN=0.25, CAP=3 ----
    vlog = []
    def V(*a):
        s = " ".join(str(x) for x in a); print(s); vlog.append(s)

    S25, target25 = cell_frame(L, 0.25)
    V(f"VALIDATION @ FF_MIN=0.25: n={len(S25)} (target register n=673) target_median_CE_be={target25:.4f}")
    base_stats = size_and_eval(S25, target25, None)  # equal-spread proxy check uses lots=1 below instead
    # true equal-spread (lots=1 always) for the BASE row comparison:
    ce_be = S25["CE_be"].to_numpy(float); pnl = S25["pnl"].to_numpy(float)
    rpnl_eqspread = pnl.copy()
    win = (rpnl_eqspread > 0).mean() * 100
    aw = rpnl_eqspread[rpnl_eqspread > 0].mean(); al = rpnl_eqspread[rpnl_eqspread <= 0].mean()
    pf_eq = rpnl_eqspread[rpnl_eqspread > 0].sum() / abs(rpnl_eqspread[rpnl_eqspread <= 0].sum())
    V(f"BASE equal-spread (lots=1): n={len(S25)} win={win:.1f} avg_win={aw:.1f} avg_loss={al:.1f} "
      f"pf={pf_eq:.2f} total={rpnl_eqspread.sum():.1f} worst={rpnl_eqspread.min():.1f}")
    V("REGISTER BASE          : n=673 win=71.8 avg_win=59.8 avg_loss=-133.6 pf=1.14 total=3497.0 worst=-7741.0")

    r3 = size_and_eval(S25, target25, 3)
    aw3 = None
    lots3 = np.minimum(target25 / ce_be, 3.0); rpnl3 = lots3 * pnl
    aw3 = rpnl3[rpnl3 > 0].mean(); al3 = rpnl3[rpnl3 <= 0].mean()
    V(f"RECOMMENDED cap=3x target=median(full)={target25:.2f}: n={r3['n']} win={r3['win_rate_pct']:.1f} "
      f"avg_win={aw3:.1f} avg_loss={al3:.1f} pf={r3['profit_factor']:.2f} total={r3['total_pnl_rupees']:.1f} "
      f"worst={r3['worst_trade_rupees']:.1f}")
    V("REGISTER RECOMMENDED   : n=673 win=71.8 avg_win=29.2 avg_loss=-33.1 pf=2.24 total=7812.0 worst=-464.0")
    V(f"MATCH QUALITY: pf {'EXACT' if abs(r3['profit_factor']-2.24)<0.01 else 'DIFF'}, "
      f"win {'EXACT' if abs(r3['win_rate_pct']-71.8)<0.1 else 'DIFF'}, "
      f"total {'MATCH' if abs(r3['total_pnl_rupees']-7812.0)<5 else 'DIFF'} "
      f"(={r3['total_pnl_rupees']:.1f}), worst {'MATCH' if abs(r3['worst_trade_rupees']-(-464.0))<5 else 'DIFF'} "
      f"(={r3['worst_trade_rupees']:.1f})")
    V(f"cap field reported in JSON = 1201.7857142857142; 3*target(this run)={3*target25:.4f} "
      f"(NOT equal -- register's exact 'cap' scalar was not recoverable from CE_be stats alone, "
      f"see script docstring; trading_brief_stats.json pf/win/total/worst ARE reproduced)")
    VALIDATION_PATH.write_text("\n".join(vlog), encoding="utf-8")
    print(f"\nwrote validation -> {VALIDATION_PATH}")

    # ---- MAIN GRID ----
    rows = []
    OUT2.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for ff_min in FF_GRID:
            S, target = cell_frame(L, ff_min)
            Sb = S[S["entry"] <= SPLIT]
            Sf = S[S["entry"] > SPLIT]
            print(f"\nFF_MIN={ff_min}: n_total={len(S)} n_build={len(Sb)} n_forward={len(Sf)} "
                  f"target_median_CE_be={target:.3f}")
            for cap_mult in CAP_GRID:
                for period, df in [("BUILD", Sb), ("FORWARD", Sf)]:
                    stats = size_and_eval(df, target, cap_mult)
                    row = {
                        "cap_mult": ("uncapped" if cap_mult is None else cap_mult),
                        "ff_min": ff_min, "period": period,
                        "n": stats["n"], "total_pnl_rupees": round(stats["total_pnl_rupees"], 2),
                        "pnl_per_100_deployed": round(stats["pnl_per_100_deployed"], 3),
                        "profit_factor": (round(stats["profit_factor"], 3)
                                          if np.isfinite(stats["profit_factor"]) else "inf"),
                        "win_rate_pct": round(stats["win_rate_pct"], 2),
                        "worst_trade_rupees": round(stats["worst_trade_rupees"], 2),
                        "maxdd_pct_of_avg_monthly_deployed": (
                            round(stats["maxdd_pct_of_avg_monthly_deployed"], 2)
                            if np.isfinite(stats["maxdd_pct_of_avg_monthly_deployed"]) else ""),
                        "target_median_ce_be": round(target, 3),
                        "deployed_sum_rupees": round(stats["deployed_sum_rupees"], 2),
                    }
                    writer.writerow(row)
                    rows.append(row)
            fh.flush()
            print(f"  ... checkpointed FF_MIN={ff_min} rows to {CSV_PATH.name}")

    print(f"\nDONE. {len(rows)} rows -> {CSV_PATH}")
    return rows


if __name__ == "__main__":
    run()
