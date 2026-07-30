"""NICHE 3 — Overnight tail BUY: mirror of NS-1 (which killed the SELL side, 2026-07-25).
Buy 1x CE + 1x PE at strike distance d from spot (dynamically %, not fixed step count),
entered at D-1 last bar <=15:25 (D0 = the expiring day), exit D0 first bar >=09:15.
Same population as NS-1 (every valid weekly expiry, 2021-05->2026-06), same 5 distances.
Costs via the shared opt_pl.round_trip_costs (COST_STANDARDS D-021, binding).
Per PREREG.md Niche 3.
"""
import sys, datetime as dt
import numpy as np, pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "OPTION_PL_HARNESS_20260729"))
import chain    # noqa: E402
import opt_pl   # noqa: E402

OUT = Path(__file__).parent
LOT = 75
DISTANCES = [0.0, 0.005, 0.010, 0.015, 0.020]  # 0%, 0.5%, 1.0%, 1.5%, 2.0% OTM


def main():
    spot = opt_pl.load_spot()
    sdate = pd.Series(spot.index.date, index=spot.index)
    tdays = sorted(set(spot.index.date))
    tpos = {d: i for i, d in enumerate(tdays)}
    mapping, exps = chain.build_expiry_index()

    rows = []
    for i, exp in enumerate(exps):
        d0 = exp
        if d0 not in tpos or tpos[d0] == 0:
            continue
        dm1 = tdays[tpos[d0] - 1]
        s0, s1_ = spot[sdate == d0], spot[sdate == dm1]
        if len(s0) < 50 or len(s1_) < 50:
            continue
        pre = s1_[s1_.index.time <= dt.time(15, 25)]
        if not len(pre):
            continue
        t_entry = pre.index[-1]
        spot_entry = float(pre["close"].iloc[-1])
        post = s0[s0.index.time >= dt.time(9, 15)]
        if not len(post):
            continue
        t_exit = post.index[0]
        spot_exit = float(post["close"].iloc[0])

        try:
            df = pq.read_table(
                mapping[exp],
                columns=["timestamp", "strike", "option_type", "close", "volume", "trading_day"],
                filters=[("trading_day", "in", [str(d0), str(dm1)])],
            ).to_pandas()
        except Exception as ex:
            print(f"  ! {exp} read failed: {ex}")
            continue
        if not df.empty:
            ts = pd.to_datetime(df["timestamp"])
            if getattr(ts.dt, "tz", None) is not None:
                ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
            df = df.assign(t=ts)
        avail_ce = set(df.loc[df.option_type == "CE", "strike"].unique())
        avail_pe = set(df.loc[df.option_type == "PE", "strike"].unique())

        for d in DISTANCES:
            k_ce = round((spot_entry * (1 + d)) / 50) * 50
            k_pe = round((spot_entry * (1 - d)) / 50) * 50
            if k_ce not in avail_ce or k_pe not in avail_pe:
                rows.append(dict(d=d, day=str(d0), status="no_strike")); continue

            def px(strike, otype, t):
                s = df[(df.strike == strike) & (df.option_type == otype)].set_index("t")
                s = s[~s.index.duplicated(keep="last")].sort_index()
                b = s[s.index <= t]
                return (None, None) if b.empty else (float(b["close"].iloc[-1]), float(b["volume"].iloc[-1]))

            ce_e, ce_ev = px(k_ce, "CE", t_entry)
            pe_e, pe_ev = px(k_pe, "PE", t_entry)
            if ce_e is None or pe_e is None:
                rows.append(dict(d=d, day=str(d0), status="no_entry_bar")); continue

            def px_after(strike, otype, t):
                s = df[(df.strike == strike) & (df.option_type == otype)].set_index("t")
                s = s[~s.index.duplicated(keep="last")].sort_index()
                a = s[s.index >= t]
                return (None, None) if a.empty else (float(a["close"].iloc[0]), float(a["volume"].iloc[0]))

            ce_x, ce_xv = px_after(k_ce, "CE", t_exit)
            pe_x, pe_xv = px_after(k_pe, "PE", t_exit)
            if ce_x is None or pe_x is None:
                rows.append(dict(d=d, day=str(d0), status="no_exit_bar")); continue

            gross = ((ce_x - ce_e) + (pe_x - pe_e)) * LOT
            cost = (opt_pl.round_trip_costs(ce_e, ce_x, LOT, "cost_standards", d0, exercised=False)
                    + opt_pl.round_trip_costs(pe_e, pe_x, LOT, "cost_standards", d0, exercised=False))
            net = gross - cost
            entry_prem = (ce_e + pe_e)
            exit_prem = (ce_x + pe_x)
            rows.append(dict(
                d=d, day=str(d0), status="filled", strike_ce=k_ce, strike_pe=k_pe,
                spot_entry=spot_entry, spot_exit=spot_exit,
                entry_prem=entry_prem, exit_prem=exit_prem,
                gross_pts=gross / LOT, cost_pts=cost / LOT, net_pts=net / LOT,
                gross_rs=gross, cost_rs=cost, net_rs=net,
                zero_vol_entry=int(ce_ev == 0 or pe_ev == 0),
                zero_vol_exit=int(ce_xv == 0 or pe_xv == 0),
            ))
        if (i + 1) % 40 == 0:
            print(f"  [{i+1}/{len(exps)}] {exp}", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "niche3_overnight_buy_trades.csv", index=False)
    f = out[out.status == "filled"].copy()
    f["day"] = pd.to_datetime(f["day"])
    f["build"] = f["day"] < "2026-01-01"

    print(f"\n=== NICHE 3 — overnight BUY, mirror of NS-1 ({len(exps)} expiries scanned) ===")
    summary_rows = []
    for d in DISTANCES:
        for split_name, split_mask in [("FULL", pd.Series(True, index=f.index)),
                                        ("BUILD(<=2025-12)", f["build"]),
                                        ("HELDOUT_2026H1", ~f["build"])]:
            g = f[(f.d == d) & split_mask]
            if g.empty:
                continue
            n = g["net_pts"]
            pos = n[n > 0].sum()
            top1 = float(n.max() / pos) if pos > 0 else np.nan
            summary_rows.append(dict(
                d=d, split=split_name, n=len(g),
                gross_mean=g["gross_pts"].mean(), cost_mean=g["cost_pts"].mean(),
                net_mean=n.mean(), net_median=n.median(), net_std=n.std(),
                t=n.mean() / (n.std(ddof=1) / np.sqrt(len(n))) if len(n) > 1 and n.std(ddof=1) > 0 else np.nan,
                win_pct=100 * (n > 0).mean(),
                skew=n.skew(), p95=n.quantile(0.95), worst=n.min(), best=n.max(),
                top1_profit_share=top1,
                cost_frac_of_gross=g["cost_pts"].sum() / g["gross_pts"].sum() if g["gross_pts"].sum() != 0 else np.nan,
                zero_vol_entry_frac=g["zero_vol_entry"].mean(),
                zero_vol_exit_frac=g["zero_vol_exit"].mean(),
                monthly_win_pct_net=(g.assign(m=g["day"].dt.to_period("M")).groupby("m")["net_pts"].sum() > 0).mean() * 100
                if split_name != "HELDOUT_2026H1" or len(g) else np.nan,
                monthly_win_pct_gross=(g.assign(m=g["day"].dt.to_period("M")).groupby("m")["gross_pts"].sum() > 0).mean() * 100,
            ))
    summ = pd.DataFrame(summary_rows)
    summ.to_csv(OUT / "niche3_summary.csv", index=False)
    print(summ.to_string(index=False))
    print("\nsaved ->", OUT)


if __name__ == "__main__":
    main()
