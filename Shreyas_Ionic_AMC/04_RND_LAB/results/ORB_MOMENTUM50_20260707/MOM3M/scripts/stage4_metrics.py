"""Stage 4: metrics per combo + degenerate detectors + per-year + concentration -> REPORT.md"""
import os, sys
import numpy as np, pandas as pd
ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_MOMENTUM50_20260707/MOM3M")
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC/04_RND_LAB/lib")); import guards as G

LABELS = {"combo1": "SL 0.25xATR + EOD", "combo2": "SL 0.25xATR + Trail",
          "combo3": "SL 1.0xATR + EOD",  "combo4": "SL 1.0xATR + Trail"}

def sharpe_dd(daily):
    d = daily.dropna()
    if d.std() == 0 or len(d) < 5: return 0.0, 0.0
    sh = d.mean() / d.std() * np.sqrt(252)
    eq = (1 + d).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return sh, dd

def block(name):
    df = pd.read_csv(os.path.join(OUT, f"trades_{name}.csv"))
    df["date"] = pd.to_datetime(df["date"])
    r = df["net_ret"]; g = df["gross_ret"]
    win = (r > 0).mean()
    pf = r[r > 0].sum() / abs(r[r < 0].sum()) if (r < 0).any() else np.inf
    daily = df.groupby("date")["net_ret"].mean()
    sh, dd = sharpe_dd(daily)
    # per year
    yr = []
    for y, gg in df.groupby(df["date"].dt.year):
        dy = gg.groupby("date")["net_ret"].mean(); s, _ = sharpe_dd(dy)
        yr.append((y, len(gg), (gg.net_ret > 0).mean(), gg.net_ret.mean()*100, gg.net_ret.sum()*100, s))
    # long/short
    ls = {}
    for sd in ["L", "S"]:
        sub = df[df.side == sd]
        ls[sd] = (len(sub), (sub.net_ret > 0).mean() if len(sub) else 0, sub.net_ret.mean()*100 if len(sub) else 0)
    # concentration
    persym = df.groupby("symbol")["net_ret"].sum()
    tot = df["net_ret"].sum()
    top1 = persym.abs().max() / (abs(tot) + 1e-12)
    top5names = persym.sort_values(ascending=False).head(5)
    flags = G.degenerate_flags(daily, df, ret_col="net_ret", sym_col="symbol")
    exitmix = df["exit_reason"].value_counts(normalize=True)
    return dict(name=name, n=len(df), win=win, pf=pf, sharpe=sh, dd=dd,
                avg_gross=g.mean()*100, avg_net=r.mean()*100, med_net=r.median()*100,
                net2x_avg=df["net_2x"].mean()*100, total_net=tot*100,
                sh2x=sharpe_dd(df.groupby("date")["net_2x"].mean())[0],
                yr=yr, ls=ls, top1=top1, top5=top5names, flags=flags, exitmix=exitmix,
                cost_drag=(g.mean()-r.mean())*100, wl=r[r>0].mean()/abs(r[r<0].mean()+1e-12),
                trades_per_day=len(df)/df["date"].nunique(), ndays=df["date"].nunique())

res = {n: block(n) for n in LABELS}

L = []
L.append("# 15-min ORB x MOMENTUM-50 (PURE 3-month momentum) — RESULTS")
L.append(f"Owner: Arjun Rao (Head of Quant). Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}.")
L.append("")
L.append("## Data lineage")
L.append("- Ranking: HF daily close `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` (6,968,616 rows, 2,535 syms, ends IST 2026-01-22). ALREADY split/bonus-adjusted (verified TTKPRESTIG 10:1, IRCTC 5:1 => NO re-adjustment). Price-return momentum (ex-dividend).")
L.append("- Execution: HF minute `.../minute/train-0000{0..7}.parquet` (713M 1-min bars, 2022-01-03->2026-01-21 IST). UTC+5:30; time>=09:15 (L2). Resampled to 12.27M 15-min bars; 509 momentum-universe syms ALL found (namespace match).")
L.append("- Universe: `NIFTY500_TICKER_2005_2025_Final.xlsx` 42 semi-annual PIT snaps; most-recent<=month (causal, L6-survivorship). Top-50 by trailing 63-td return, monthly rebalance. 49 months, 509 union syms.")
L.append("- Guards: L1 IST-date, L2 preopen, L5 next-bar entry (strictly after signal bar), causal Wilder ATR(14) on continuous 15-min series, zero-volume=no-fill.")
L.append("")
L.append("## Method")
L.append("- OR = first 15-min bar 09:15-09:29. LONG = a later 15-min bar CLOSES > OR-high; SHORT = closes < OR-low (CLOSE-confirmation, not wick). BIDIRECTIONAL. First signal/day only; ENTER at NEXT 15-min bar OPEN. Max signal bar 23 (need next bar).")
L.append("- ATR(14) Wilder on continuous 15-min series (does not reset daily). Stop distance = ATR at signal bar.")
L.append("- Exits: EOD = flat at last 15-min close (no overnight). TRAIL = chandelier (long: exit when close-bar low <= highestClose-1.0xATR; short symmetric), initial hard SL as floor; else EOD. Gap-through honored (open beyond stop => fill at open).")
L.append("- Costs (COST_STANDARDS): slippage 15bps/side; DOUBLED to 30bps on stop/trail/gap exits (exit-into-weakness); +STT sell 2.5 + exch/GST 1.4 + stamp 0.3 + brokerage 4bps@Rs1L = ~8bps fixed. Round-trip ~0.38% (EOD) / ~0.53% (stop). net_2x = 2x slippage stress.")
L.append("- %-of-ENTRY-PRICE per trade (stable denom, FIRM RULE). Sharpe on DAILY equal-weight book return x sqrt(252) (NOT per-trade annualized). MaxDD from compounded daily equity.")
L.append("")
L.append("## SUMMARY TABLE (net of 1x costs)")
L.append("| Combo | SL x Exit | N | Win% | PF | W/L | Avg gross %/tr | Avg net %/tr | Ann.Sharpe | MaxDD | Total net % | Sharpe@2x |")
L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for n in LABELS:
    x = res[n]
    L.append(f"| {n} | {LABELS[n]} | {x['n']:,} | {x['win']*100:.1f} | {x['pf']:.2f} | {x['wl']:.2f} | {x['avg_gross']:+.3f} | {x['avg_net']:+.3f} | {x['sharpe']:.2f} | {x['dd']*100:.1f}% | {x['total_net']:+.0f} | {x['sh2x']:.2f} |")
L.append("")
L.append(f"All combos share IDENTICAL entries ({res['combo1']['n']:,} filled trades; ~{res['combo1']['trades_per_day']:.0f}/day over {res['combo1']['ndays']} trading days) — they differ ONLY in stop/exit. Avg cost drag/trade: " + ", ".join(f"{n} {res[n]['cost_drag']:.3f}%" for n in LABELS) + ".")
L.append("")
for n in LABELS:
    x = res[n]
    L.append(f"### {n} — {LABELS[n]}")
    L.append(f"- Long: N={x['ls']['L'][0]:,} win {x['ls']['L'][1]*100:.1f}% avg net {x['ls']['L'][2]:+.3f}% | Short: N={x['ls']['S'][0]:,} win {x['ls']['S'][1]*100:.1f}% avg net {x['ls']['S'][2]:+.3f}%")
    L.append("- Exit mix: " + ", ".join(f"{k} {v*100:.0f}%" for k, v in x["exitmix"].items()))
    L.append(f"- Concentration: top-1 symbol = {x['top1']*100:.1f}% of |net P&L|. Top-5 net contributors: " + ", ".join(f"{s} {v*100:+.0f}%pts" for s, v in x["top5"].items()))
    L.append(f"- Degenerate flags: {x['flags'] if x['flags'] else 'NONE'}")
    L.append("- Per-year (N, win%, avg net%/tr, sum net%, Sharpe):")
    L.append("  | Year | N | Win% | Avg net% | Sum net% | Sharpe |")
    L.append("  |---|---:|---:|---:|---:|---:|")
    for y, nn, w, an, tn, s in x["yr"]:
        L.append(f"  | {y} | {nn:,} | {w*100:.1f} | {an:+.3f} | {tn:+.1f} | {s:.2f} |")
    L.append("")

open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))
# console summary
print("COMBO | N | win% | PF | avgGrossbps | avgNetbps | Sharpe | MaxDD | Sharpe2x")
for n in LABELS:
    x = res[n]
    print(f"{n} | {x['n']:,} | {x['win']*100:.1f} | {x['pf']:.2f} | {x['avg_gross']*100:+.1f} | {x['avg_net']*100:+.1f} | {x['sharpe']:.2f} | {x['dd']*100:.1f}% | {x['sh2x']:.2f} | flags={x['flags']}")
print("REPORT written")
