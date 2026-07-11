"""S4: metrics + CAGR/XIRR (PRIMARY) + equity curve + degenerate detectors -> REPORT.md
Position sizing = EQUAL-NOTIONAL daily-equal-weight book: each day capital split equally across that day's
short signals, fully deployed intraday, flat overnight (EOD), reinvested daily -> compounded equity curve.
CAGR = equity_final^(252/n_days)-1. XIRR = two-flow calendar-basis money-weighted cross-check.
Robustness: equal-RISK sizing (weight ~ 1/stop_fraction) net CAGR.
"""
import os, sys
import numpy as np, pandas as pd
ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_SHORTONLY_20260707/MOM1M")
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/lib")); import guards as G

TFS = ["5m", "15m"]

def sharpe(daily):
    d = daily.dropna()
    if d.std() == 0 or len(d) < 5: return 0.0
    return d.mean() / d.std() * np.sqrt(252)

def maxdd(daily):
    eq = (1 + daily.dropna()).cumprod()
    return (eq / eq.cummax() - 1).min()

def cagr_from_daily(daily):
    d = daily.dropna()
    eq = (1 + d).cumprod()
    yrs = max(len(d) / 252, 1e-9)
    return eq.iloc[-1] ** (1 / yrs) - 1, eq

def block(tf):
    df = pd.read_csv(os.path.join(OUT, f"trades_{tf}.csv"))
    df["date"] = pd.to_datetime(df["date"])
    r = df["net_ret"]; g = df["gross_ret"]; r2 = df["net_2x"]
    win = (r > 0).mean()
    pf = r[r > 0].sum() / abs(r[r < 0].sum()) if (r < 0).any() else np.inf
    wl = r[r > 0].mean() / abs(r[r <= 0].mean() + 1e-12)

    # EQUAL-NOTIONAL daily-equal-weight book (PRIMARY)
    dn = df.groupby("date")["net_ret"].mean()
    dg = df.groupby("date")["gross_ret"].mean()
    d2 = df.groupby("date")["net_2x"].mean()
    cagr_net, eq_net = cagr_from_daily(dn)
    cagr_gross, eq_gross = cagr_from_daily(dg)
    cagr_2x, _ = cagr_from_daily(d2)

    # XIRR (two-flow, calendar basis): equity_final^(365.25/cal_days)-1
    cal_days = (df["date"].max() - df["date"].min()).days
    xirr_net = eq_net.iloc[-1] ** (365.25 / max(cal_days, 1)) - 1
    xirr_gross = eq_gross.iloc[-1] ** (365.25 / max(cal_days, 1)) - 1

    # EQUAL-RISK robustness: weight ~ 1/stop_fraction (stop_frac = K*ATR/entry, K=1.0)
    df["stopfrac"] = (df["atr_entry"] / df["entry"]).clip(lower=1e-4)
    df["w"] = 1.0 / df["stopfrac"]
    def er_day(gg):
        w = gg["w"] / gg["w"].sum()
        return (w * gg["net_ret"]).sum()
    der = df.groupby("date").apply(er_day, include_groups=False)
    cagr_er, _ = cagr_from_daily(der)

    # gross diagnostics
    tstat = g.mean() / (g.std() / np.sqrt(len(g)))
    sh_gross = sharpe(dg)

    # per-year
    yr = []
    for y, gg in df.groupby(df["date"].dt.year):
        dy = gg.groupby("date")["net_ret"].mean()
        dyg = gg.groupby("date")["gross_ret"].mean()
        cg, _ = cagr_from_daily(dyg); cn, _ = cagr_from_daily(dy)
        yr.append((y, len(gg), (gg.net_ret > 0).mean()*100, gg.gross_ret.mean()*1e4,
                   gg.net_ret.mean()*1e4, sharpe(dy), cn*100))

    # concentration
    persym = df.groupby("symbol")["net_ret"].sum()
    tot = df["net_ret"].sum()
    top1 = persym.abs().max() / (abs(tot) + 1e-12)
    flags = G.degenerate_flags(dn, df, ret_col="net_ret", sym_col="symbol")
    exitmix = df["exit_reason"].value_counts(normalize=True)

    # save equity curve
    ec = pd.DataFrame({"date": eq_net.index, "book_net_ret": dn.values,
                       "equity_net": eq_net.values, "equity_gross": eq_gross.values})
    ec.to_csv(os.path.join(OUT, f"equity_{tf}.csv"), index=False)

    return dict(tf=tf, n=len(df), win=win, pf=pf, wl=wl,
                avg_gross=g.mean()*1e4, avg_net=r.mean()*1e4, med_net=r.median()*1e4,
                avg_net2x=r2.mean()*1e4,
                cagr_net=cagr_net*100, cagr_gross=cagr_gross*100, cagr_2x=cagr_2x*100,
                cagr_er=cagr_er*100, xirr_net=xirr_net*100, xirr_gross=xirr_gross*100,
                sharpe=sharpe(dn), sharpe_gross=sh_gross, sharpe2x=sharpe(d2),
                maxdd=maxdd(dn)*100, maxdd_gross=maxdd(dg)*100,
                tstat=tstat, tot_net=tot*100, ndays=df["date"].nunique(),
                tpd=len(df)/df["date"].nunique(), cost_drag=(g.mean()-r.mean())*1e4,
                yr=yr, top1=top1*100, flags=flags, exitmix=exitmix,
                eq_final_net=eq_net.iloc[-1], eq_final_gross=eq_gross.iloc[-1],
                dmin=df["date"].min().date(), dmax=df["date"].max().date())

res = {tf: block(tf) for tf in TFS}
best = "5m" if res["5m"]["cagr_net"] > res["15m"]["cagr_net"] else "15m"

L = []
L.append("# SHORT-ONLY OR-LOW-BREAKDOWN x MOMENTUM-50 (1-MONTH momentum) — RESULTS")
L.append(f"Owner: Arjun Rao (Head of Quant). Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}.")
L.append("Follow-up to ORB_MOMENTUM50_20260707 (3m/3m6m bidirectional). Narrowed to the ONLY live piece: SHORT side.")
L.append("")
L.append("## HEADLINE — CAGR/XIRR (PRIMARY metric this round)")
L.append("Position sizing = **equal-notional, daily-equal-weight book**: each trading day, capital is split")
L.append("equally across that day's short signals, fully deployed intraday, flat overnight (EOD exit),")
L.append("P&L reinvested daily -> compounded strategy equity curve. CAGR on 252-td basis; XIRR = calendar-basis")
L.append("(actual/365.25) money-weighted cross-check (equals CAGR here — single account, full reinvestment, no external flows).")
L.append("")
L.append("| Timeframe | Net CAGR | Net XIRR | Gross CAGR | CAGR @2x-slip | Net CAGR (equal-risk) | Final net equity (x) |")
L.append("|---|---:|---:|---:|---:|---:|---:|")
for tf in TFS:
    x = res[tf]
    L.append(f"| {tf}-ORB | {x['cagr_net']:+.1f}% | {x['xirr_net']:+.1f}% | {x['cagr_gross']:+.1f}% | {x['cagr_2x']:+.1f}% | {x['cagr_er']:+.1f}% | {x['eq_final_net']:.3f} |")
L.append("")
L.append("## SUMMARY TABLE (per-trade & risk-adjusted, net of 1x costs)")
L.append("| Timeframe | N | Win% | PF | W/L | Avg gross bps/tr | Avg net bps/tr | Ann.Sharpe(net) | Sharpe(gross) | MaxDD(net) | Sharpe@2x |")
L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for tf in TFS:
    x = res[tf]
    L.append(f"| {tf}-ORB | {x['n']:,} | {x['win']*100:.1f} | {x['pf']:.2f} | {x['wl']:.2f} | {x['avg_gross']:+.1f} | {x['avg_net']:+.1f} | {x['sharpe']:.2f} | {x['sharpe_gross']:.2f} | {x['maxdd']:.1f}% | {x['sharpe2x']:.2f} |")
L.append("")
L.append(f"Sample: {res['15m']['dmin']} -> {res['15m']['dmax']}. Trades/day: 5m {res['5m']['tpd']:.1f}, 15m {res['15m']['tpd']:.1f}. "
         f"Days with signals: 5m {res['5m']['ndays']}, 15m {res['15m']['ndays']}.")
L.append(f"Round-trip cost drag/trade: 5m {res['5m']['cost_drag']:.1f} bps, 15m {res['15m']['cost_drag']:.1f} bps "
         f"(15bps/side slip, doubled on stop/gap exits, +~8.2bps STT/exch/stamp/brokerage).")
L.append("")
L.append("## Data lineage")
L.append("- Ranking: HF daily close `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` — ALREADY split/bonus-adjusted (verified prior run) => raw close, NO re-adjust. Trailing 21-td (1-month) price return, causal (as-of last day before month start).")
L.append("- Universe: `NIFTY500_TICKER_2005_2025_Final.xlsx` 42 semi-annual PIT snaps; most-recent<=month (causal, L6). Top-50 by 21-td return, MONTHLY rebalance. 49 months, 570 union syms.")
L.append("- Execution: HF minute (2022-01-03 -> 2026-01-21 IST). UTC+5:30; time>=09:15 (L2 preopen dropped). Resampled to BOTH 5-min (idx 0..74) and 15-min (idx 0..24) bars.")
L.append("- Guards: L1 IST-date, L2 preopen, L5 next-bar entry (strictly after signal), causal Wilder ATR(14) on continuous per-symbol series, zero-volume=no-fill.")
L.append("")
L.append("## Method (SHORT-ONLY, frozen)")
L.append("- **5m-ORB**: OR = first 5-min bar (09:15-09:19); **15m-ORB**: OR = first 15-min bar (09:15-09:29). Self-consistent timeframe (OR + breakdown bars same size) = the conventional meaning of '5m ORB' / '15m ORB'.")
L.append("- SHORT signal = a later same-timeframe bar CLOSES < OR-low (close-confirmation, not intrabar wick). First short signal/day only; ENTER at NEXT bar OPEN (L5).")
L.append("- Stop = entry + 1.0xATR(14) (proven-best from 3m test; 0.25x = whipsaw, NOT re-tested). Exit = EOD flat at last bar close (proven-best; trailing NOT re-tested). Gap-through honored (open>=stop => fill at open).")
L.append("- Per-trade ret = %-of-ENTRY (stable denom, FIRM RULE). CAGR/XIRR from equal-notional daily-book compounded equity.")
L.append("")
for tf in TFS:
    x = res[tf]
    L.append(f"### {tf}-ORB detail")
    L.append(f"- N={x['n']:,} | win {x['win']*100:.1f}% | PF {x['pf']:.2f} | avg gross {x['avg_gross']:+.1f}bps (t={x['tstat']:+.1f}) | avg net {x['avg_net']:+.1f}bps | net@2x {x['avg_net2x']:+.1f}bps")
    L.append(f"- Net CAGR {x['cagr_net']:+.1f}% | Gross CAGR {x['cagr_gross']:+.1f}% | Sharpe(net) {x['sharpe']:.2f} | Sharpe(gross) {x['sharpe_gross']:.2f} | MaxDD(net) {x['maxdd']:.1f}% | MaxDD(gross) {x['maxdd_gross']:.1f}%")
    L.append("- Exit mix: " + ", ".join(f"{k} {v*100:.0f}%" for k, v in x["exitmix"].items()))
    L.append(f"- Concentration: top-1 symbol = {x['top1']:.1f}% of |net P&L|. Degenerate flags: {x['flags'] if x['flags'] else 'NONE'}")
    L.append("- Per-year (N, win%, gross bps/tr, net bps/tr, Sharpe(net), net CAGR%):")
    L.append("  | Year | N | Win% | Gross bps | Net bps | Sharpe | Net CAGR% |")
    L.append("  |---|---:|---:|---:|---:|---:|---:|")
    for y, nn, w, gb, nb, s, cn in x["yr"]:
        L.append(f"  | {y} | {nn:,} | {w:.1f} | {gb:+.1f} | {nb:+.1f} | {s:.2f} | {cn:+.1f} |")
    L.append("")

open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))
print("=== HEADLINE CAGR ===")
for tf in TFS:
    x = res[tf]
    print(f"{tf}: netCAGR {x['cagr_net']:+.1f}% | grossCAGR {x['cagr_gross']:+.1f}% | xirr {x['xirr_net']:+.1f}% | "
          f"N {x['n']:,} win {x['win']*100:.1f}% PF {x['pf']:.2f} netSharpe {x['sharpe']:.2f} grossSharpe {x['sharpe_gross']:.2f} "
          f"maxDD {x['maxdd']:.1f}% grossBps {x['avg_gross']:+.1f}(t={x['tstat']:+.1f}) netBps {x['avg_net']:+.1f} flags={x['flags']}")
print("BEST by net CAGR:", best)
print("REPORT written")
