"""Stage 4: SHORT-ONLY metrics with CAGR/XIRR primary. Equal-notional (equal-weight) daily book,
full capital deployed & split across the day's shorts, flat overnight, daily compounding.
Also gross diagnostics (t-stat, gross Sharpe/CAGR) to separate cost-dominated vs wrong-direction.
OUT: REPORT.md, metrics.json
"""
import os, sys, json
import numpy as np, pandas as pd
ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_SHORTONLY_20260707/MOM2W")
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/lib")); import guards as G

def eq_stats(daily):
    """daily = mean net book return per day. -> (Sharpe ann, CAGR, MaxDD, n_days, final_equity)."""
    d = daily.dropna()
    if len(d) < 5:
        return 0.0, 0.0, 0.0, len(d), 1.0
    sh = d.mean() / (d.std() + 1e-12) * np.sqrt(252)
    eq = (1 + d).cumprod()
    yrs = len(d) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else -1.0
    dd = (eq / eq.cummax() - 1).min()
    return sh, cagr, dd, len(d), eq.iloc[-1]

def analyze(name):
    df = pd.read_csv(os.path.join(OUT, f"trades_{name}.csv"), parse_dates=["date"])
    r, g = df["net_ret"], df["gross_ret"]
    win = (r > 0).mean()
    pf = r[r > 0].sum() / abs(r[r < 0].sum()) if (r < 0).any() else np.inf
    wl = r[r > 0].mean() / abs(r[r <= 0].mean() + 1e-12)
    dn = df.groupby("date")["net_ret"].mean()      # equal-weight daily book (net 1x)
    dg = df.groupby("date")["gross_ret"].mean()
    d2 = df.groupby("date")["net_2x"].mean()
    sh_n, cagr_n, dd_n, ndays, feq_n = eq_stats(dn)
    sh_g, cagr_g, dd_g, _, feq_g = eq_stats(dg)
    sh_2, cagr_2, dd_2, _, _ = eq_stats(d2)
    # gross t-stat (per-trade, is the short edge real?)
    tstat = g.mean() / (g.std() / np.sqrt(len(g)))
    # per year
    yr = []
    for y, gg in df.groupby(df["date"].dt.year):
        s, c, dd, _, _ = eq_stats(gg.groupby("date")["net_ret"].mean())
        yr.append((y, len(gg), (gg.net_ret > 0).mean()*100, gg.net_ret.mean()*100,
                   gg.gross_ret.mean()*100, c, s))
    # concentration
    persym = df.groupby("symbol")["net_ret"].sum()
    tot = df["net_ret"].sum()
    top1 = persym.abs().max() / (abs(tot) + 1e-12)
    top5g = df.groupby("symbol")["gross_ret"].sum().sort_values(ascending=False).head(5)
    flags = G.degenerate_flags(dn, df, ret_col="net_ret", sym_col="symbol")
    exitmix = df["exit_reason"].value_counts(normalize=True)
    return dict(name=name, n=len(df), ndays=ndays, tpd=len(df)/ndays, win=win, pf=pf, wl=wl,
                avg_gross_bps=g.mean()*1e4, avg_net_pct=r.mean()*100, med_net_pct=r.median()*100,
                tstat=tstat, sh_n=sh_n, cagr_n=cagr_n, dd_n=dd_n, feq_n=feq_n,
                sh_g=sh_g, cagr_g=cagr_g, dd_g=dd_g, feq_g=feq_g,
                sh_2=sh_2, cagr_2=cagr_2, dd_2=dd_2,
                total_net_pct=tot*100, cost_drag_bps=(g.mean()-r.mean())*1e4,
                yr=yr, top1=top1, top5g=top5g, flags=flags, exitmix=exitmix)

R = {tf: analyze(tf) for tf in ["5m", "15m"]}
json.dump({tf: {k: (v if not isinstance(v, (pd.Series,)) else v.to_dict())
                for k, v in R[tf].items() if k not in ("yr", "top5g", "exitmix", "flags")}
           for tf in R}, open(os.path.join(OUT, "metrics.json"), "w"), indent=1, default=str)

def L(*a): out.append(" ".join(str(x) for x in a))
out = []
L("# SHORT-ONLY ORB x 2-WEEK MOMENTUM-50 (NIFTY 500) — RESULTS")
L(f"Owner: Arjun Rao (Head of Quant). Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}.")
L("")
L("## HEADLINE — CAGR/XIRR FIRST (primary objective = compounded return)")
L("Sizing: EQUAL-NOTIONAL per day — capital split equally across the day's shorts, flat overnight,")
L("daily compounding, 1x (no leverage). XIRR == CAGR here (single lumpsum in, no external cashflows,")
L("full daily reinvestment). Chosen over equal-risk because equal-risk/ATR-normalisation amplifies")
L("micro-ATR trades and needs an arbitrary leverage cap; equal-notional maps the %-of-price per-trade")
L("stats directly onto the equity curve and matches the intraday flat-overnight reality.")
L("")
L("| Timeframe | NET CAGR/XIRR | GROSS CAGR | NET CAGR@2x-slip | Ann.Sharpe(net) | MaxDD(net) | N | Win% | PF | Avg net %/tr | Avg gross bps/tr | gross t-stat |")
L("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for tf in ["5m", "15m"]:
    x = R[tf]
    L(f"| {tf}-ORB | {x['cagr_n']*100:+.1f}% | {x['cagr_g']*100:+.1f}% | {x['cagr_2']*100:+.1f}% | "
      f"{x['sh_n']:.2f} | {x['dd_n']*100:.1f}% | {x['n']:,} | {x['win']*100:.1f} | {x['pf']:.2f} | "
      f"{x['avg_net_pct']:+.3f} | {x['avg_gross_bps']:+.1f} | {x['tstat']:+.1f} |")
L("")
L("## Data lineage")
L("- Ranking: HF daily close `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` "
  "(IST date via guards.fix_ist_dates; already split/bonus-adjusted => raw close, price-return momentum).")
L("- Execution: HF minute `.../minute/train-0000{0..7}.parquet` (713M 1-min, 2022-01-03->2026-01-21 IST), "
  "resampled to 45,002,418 5-min bars for 627 union syms; 15-min DERIVED (bar15=bar5//3, identical OHLC to 1-min build).")
L("- Universe: `NIFTY500_TICKER_2005_2025_Final.xlsx` 42 semi-annual PIT snaps, most-recent<=rebal (causal, L6). "
  "Top-50 by trailing 10-td (2-week) return, ranked as-of last td strictly BEFORE rebal; BI-WEEKLY rebalance "
  "(every 10 td == lookback). 100 rebalances, 1008 trading days, 627 union syms, 49,900 active symbol-days.")
L("- Guards: L1 IST-date, L2 preopen, L5 next-bar entry (strictly after signal), causal Wilder ATR(14) on "
  "continuous per-timeframe series, zero-volume next bar = DROP (D-031 no-fill=drop).")
L("")
L("## Method (SHORT ONLY)")
L("- 5m-ORB: OR = first 5-min bar (09:15-09:19). 15m-ORB: OR = first 15-min bar (09:15-09:29). SHORT when a")
L("  LATER same-timeframe bar CLOSES < OR-low (close-confirm, not wick). First signal/day only. Enter NEXT bar OPEN.")
L("- Stop = entry + 1.0xATR(14) at signal bar (proven-better stop; 0.25x whipsaw settled prior test, not re-run).")
L("- Exit = EOD flat at last bar close (proven-better exit). Gap-through honored (open>=stop => fill at open).")
L("- Costs: SLIP 15bps/side, DOUBLED to 30bps on STOP/GAP exits; FIXED ~8.2bps (STT-sell 2.5 + exch/GST 1.4 +")
L("  stamp 0.3 + brokerage 4bps). Round-trip ~38bps (EOD) / ~53bps (stop). net_2x = 2x-slippage stress. Identical")
L("  cost model to the prior 3-month test for apples-to-apples. %-of-ENTRY-PRICE per trade (stable denom).")
L("")
for tf in ["5m", "15m"]:
    x = R[tf]
    L(f"### {tf}-ORB detail")
    L(f"- N={x['n']:,} over {x['ndays']} days = {x['tpd']:.1f} trades/day. Win {x['win']*100:.1f}%, PF {x['pf']:.2f}, "
      f"W/L {x['wl']:.2f}, median net {x['med_net_pct']:+.3f}%.")
    L(f"- GROSS: avg {x['avg_gross_bps']:+.1f} bps/tr, t-stat {x['tstat']:+.1f}, Sharpe {x['sh_g']:.2f}, CAGR {x['cagr_g']*100:+.1f}%.")
    L(f"- NET(1x): avg {x['avg_net_pct']:+.3f}%/tr, Sharpe {x['sh_n']:.2f}, CAGR {x['cagr_n']*100:+.1f}%, MaxDD {x['dd_n']*100:.1f}%. "
      f"Cost drag {x['cost_drag_bps']:.1f} bps/tr.")
    L(f"- NET@2x: Sharpe {x['sh_2']:.2f}, CAGR {x['cagr_2']*100:+.1f}%.")
    L("- Exit mix: " + ", ".join(f"{k} {v*100:.0f}%" for k, v in x["exitmix"].items()))
    L(f"- Concentration: top-1 symbol = {x['top1']*100:.1f}% of |net P&L|. Top-5 gross contributors: "
      + ", ".join(f"{s} {v*100:+.1f}%pts" for s, v in x["top5g"].items()))
    L(f"- Degenerate flags: {x['flags'] if x['flags'] else 'NONE'}")
    L("- Per-year (N, win%, avg net%/tr, avg gross%/tr, NET CAGR, net Sharpe):")
    L("  | Year | N | Win% | Avg net% | Avg gross% | NET CAGR | Sharpe |")
    L("  |---|---:|---:|---:|---:|---:|---:|")
    for y, nn, w, an, ag, c, s in x["yr"]:
        L(f"  | {y} | {nn:,} | {w:.1f} | {an:+.3f} | {ag:+.3f} | {c*100:+.1f}% | {s:.2f} |")
    L("")

open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(out))
print("=== CONSOLE SUMMARY ===")
for tf in ["5m", "15m"]:
    x = R[tf]
    print(f"{tf}: N={x['n']} tpd={x['tpd']:.1f} win={x['win']*100:.1f}% PF={x['pf']:.2f} "
          f"grossbps={x['avg_gross_bps']:+.1f} t={x['tstat']:+.1f} | NET CAGR={x['cagr_n']*100:+.1f}% "
          f"Sh={x['sh_n']:.2f} DD={x['dd_n']*100:.1f}% | GROSS CAGR={x['cagr_g']*100:+.1f}% Sh_g={x['sh_g']:.2f} "
          f"| CAGR@2x={x['cagr_2']*100:+.1f}% flags={x['flags']}")
print("REPORT + metrics.json written")
