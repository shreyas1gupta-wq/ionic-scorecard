"""NICHE 1 (IV-percentile trough) + NICHE 2 (realized-vol trough) — long ATM straddle test.
Reads daily_vol_series.csv (build_iv_rv_series.py). Per PREREG.md niches 1 & 2.

Cells: BASELINE (all eligible days), BOTTOM_IV (iv_pct<=10), TOP_IV (iv_pct>=90),
       BOTTOM_RV (rv_pct<=10)  [reuses BASELINE as its comparator, per prereg]
All cells use the SAME long-straddle construction: buy 1x ATM CE + 1x ATM PE of the reference
expiry (1<=DTE<=8), hold to expiry (cash-settled at intrinsic if still open), no stop/target,
cost_model=cost_standards, dynamic slippage, no_overlap=True per leg-stream.
"""
import sys
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "OPTION_PL_HARNESS_20260729"))
import opt_pl  # noqa: E402
from opt_pl import OptCfg

OUT = Path(__file__).parent
CFG = OptCfg(min_dte=1, max_dte=8, strike_offset=0, max_hold_days=9,
             hold_days_are_trading_days=False, squareoff_hhmm="15:25",
             expiry_handling="settle_intrinsic", cost_model="cost_standards",
             slippage_mode="dynamic", lots=1, no_overlap=True,
             allow_opposite_signal_exit=False)


def run_straddle(days: pd.Series, tag: str) -> pd.DataFrame:
    """days: Series of pd.Timestamp entry signals (t_iv bar). Returns per-straddle trades."""
    sigs_ce = [{"t": t, "direction": 1, "tag": tag} for t in days]
    sigs_pe = [{"t": t, "direction": -1, "tag": tag} for t in days]
    tr_ce = opt_pl.run_signals(sigs_ce, CFG)
    tr_pe = opt_pl.run_signals(sigs_pe, CFG)
    ce = tr_ce.add_prefix("ce_").rename(columns={"ce_signal_t": "signal_t"})
    pe = tr_pe.add_prefix("pe_").rename(columns={"pe_signal_t": "signal_t"})
    m = ce.merge(pe, on="signal_t", how="inner")
    m["both_filled"] = (m["ce_status"] == "filled") & (m["pe_status"] == "filled")
    f = m[m["both_filled"]].copy()
    f["gross"] = f["ce_gross"] + f["pe_gross"]
    f["costs"] = f["ce_costs"] + f["pe_costs"]
    f["net_pnl"] = f["gross"] - f["costs"]
    f["entry_prem"] = f["ce_entry_fill"] + f["pe_entry_fill"]
    f["qty"] = f["ce_qty"]
    f["ret_pct_net"] = f["net_pnl"] / (f["entry_prem"] * f["qty"])
    f["exit_t"] = f[["ce_exit_t", "pe_exit_t"]].max(axis=1)
    f["tag"] = tag
    f["n_signals"] = len(days)
    return f


def metrics(f: pd.DataFrame, label: str) -> dict:
    if f.empty:
        return dict(label=label, n=0)
    n = f["net_pnl"]; g = f["gross"]
    pos = n[n > 0].sum()
    m = dict(
        label=label, n_signals=int(f["n_signals"].iloc[0]) if len(f) else 0, n_filled=len(f),
        gross_mean=g.mean(), net_mean=n.mean(), net_median=n.median(), net_std=n.std(),
        t=n.mean() / (n.std(ddof=1) / np.sqrt(len(n))) if len(n) > 1 and n.std(ddof=1) > 0 else np.nan,
        win_pct=100 * (n > 0).mean(), skew=n.skew(),
        p95=n.quantile(0.95), worst=n.min(), best=n.max(),
        top1_profit_share=float(n.max() / pos) if pos > 0 else np.nan,
        cost_frac_of_gross=f["costs"].sum() / g.sum() if g.sum() != 0 else np.nan,
        avg_hold_days=(pd.to_datetime(f["exit_t"]) - pd.to_datetime(f["signal_t"])).dt.days.mean(),
    )
    mm = f.copy()
    mm["month"] = pd.to_datetime(mm["exit_t"]).dt.to_period("M")
    gm = mm.groupby("month")[["gross", "net_pnl"]].sum()
    m["pos_months_gross_pct"] = 100 * (gm["gross"] > 0).mean() if len(gm) else np.nan
    m["pos_months_net_pct"] = 100 * (gm["net_pnl"] > 0).mean() if len(gm) else np.nan
    m["n_months"] = len(gm)
    return m


def main():
    df = pd.read_csv(OUT / "daily_vol_series.csv", parse_dates=["day", "t_iv"])
    uni = df[df["iv_pct"].notna() & df["rv_pct"].notna()].copy()
    print(f"[niche1/2] eligible universe (both percentiles defined): {len(uni)} / {len(df)} days")

    cells = {
        "BASELINE_ALL": uni,
        "N1_BOTTOM_IV_DECILE": uni[uni["iv_pct"] <= 10],
        "N1_TOP_IV_DECILE": uni[uni["iv_pct"] >= 90],
        "N2_BOTTOM_RV_DECILE": uni[uni["rv_pct"] <= 10],
    }
    overlap = len(set(cells["N1_BOTTOM_IV_DECILE"]["day"]) & set(cells["N2_BOTTOM_RV_DECILE"]["day"]))
    print(f"[niche1/2] overlap(bottom_iv, bottom_rv) = {overlap} of "
          f"{len(cells['N1_BOTTOM_IV_DECILE'])} / {len(cells['N2_BOTTOM_RV_DECILE'])} days")

    all_trades = []
    rows = []
    for name, sub in cells.items():
        f = run_straddle(sub["t_iv"], name)
        f["day"] = pd.to_datetime(f["signal_t"]).dt.normalize()
        f["build"] = f["day"] < pd.Timestamp("2026-01-01")
        all_trades.append(f)
        for split_name, split_mask in [("FULL", pd.Series(True, index=f.index)),
                                        ("BUILD(<=2025-12)", f["build"] if len(f) else None),
                                        ("HELDOUT_2026H1", ~f["build"] if len(f) else None)]:
            g = f[split_mask] if split_mask is not None else f
            m = metrics(g, f"{name}::{split_name}")
            m["n_signal_days_in_cell"] = len(sub)
            rows.append(m)
        print(f"  {name}: {len(sub)} signal days -> {len(f)} filled straddles", flush=True)

    trades_all = pd.concat(all_trades, ignore_index=True)
    trades_all.to_csv(OUT / "niche1_niche2_trades.csv", index=False)
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / "niche1_niche2_summary.csv", index=False)
    print("\n=== NICHE 1 / 2 SUMMARY ===")
    print(summ.to_string(index=False))
    print("\nsaved ->", OUT)


if __name__ == "__main__":
    main()
