"""Backtest the fade-after-100pt-spike strategies with REAL costs.
Rules:
  Capital ₹10,00,000. Margin ~12% of notional per short lot (~₹1.95L @ spot 25k).
  Sequential trades ordered by (date, entry_hm). 60-min hold. Skip signal if position open.
  1 lot per trade (conservative — max margin utilization ~20% for any single trade).
  Costs per round-trip:
    brokerage ₹20 x 2 = ₹40 flat
    STT 0.1% on SELL premium
    exchange txn 0.03503% on total premium turnover (both legs)
    IPFT 0.0005%, SEBI 0.0001% both sides
    GST 18% on (brokerage + exch + IPFT + SEBI)
    stamp 0.003% on buy-to-cover premium
    slippage half-spread each side: hs = max(₹0.10, 0.001 x premium) — practical for NIFTY liquidity
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

OUT = Path(__file__).parent
LOT = 65
CAP = 1_000_000
MARGIN_PCT = 0.12   # 12% of underlying notional (approx SPAN for naked short)

df = pd.read_csv(OUT / "race_events.csv")
df["d"] = pd.to_datetime(df["d"]).dt.date

# ---- back out exit premium from old-model P&L ---------------------------
# old model: pnl = (entry - exit) x LOT - abs(entry x LOT x 15/1e4)
def back_out_exit(entry, pnl):
    if pd.isna(entry) or pd.isna(pnl) or entry <= 0.1: return None
    old_cost = abs(entry * LOT * 15 / 1e4)
    return entry - (pnl + old_cost) / LOT

def real_cost(entry, exit):
    """Full round-trip cost for a SHORT (sell then buy-to-cover)."""
    if entry is None or exit is None or entry <= 0.1 or exit <= 0: return None
    brok = 40
    turnover = (entry + exit) * LOT
    ex_txn = 0.0003503 * turnover
    ipft   = 0.000005  * turnover
    sebi   = 0.000001  * turnover
    stt    = 0.001     * entry * LOT
    stamp  = 0.00003   * exit * LOT
    gst    = 0.18 * (brok + ex_txn + ipft + sebi)
    hs_e   = max(0.10, 0.001 * entry)
    hs_x   = max(0.10, 0.001 * exit)
    slip   = (hs_e + hs_x) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + slip

def reprice(entry, old_pnl):
    ex = back_out_exit(entry, old_pnl)
    if ex is None: return None
    gross = (entry - ex) * LOT
    c = real_cost(entry, ex)
    if c is None: return None
    return gross - c, ex, c

def repriced_col(entry_col, pnl_col, out_prefix):
    outs = df.apply(lambda r: reprice(r[entry_col], r[pnl_col])
                    if pd.notna(r[entry_col]) and pd.notna(r[pnl_col]) else None, axis=1)
    df[f"{out_prefix}_pnl"] = [x[0] if x else None for x in outs]
    df[f"{out_prefix}_exit"] = [x[1] if x else None for x in outs]
    df[f"{out_prefix}_cost"] = [x[2] if x else None for x in outs]

repriced_col("atm_prem", "atm_sell_pnl", "atm")
repriced_col("far_prem", "far_sell_pnl", "far")

# sort chronologically for sequential backtest
df = df.sort_values(["d", "e_hm"]).reset_index(drop=True)

def backtest(pnl_col, entry_col, name):
    trades = []
    equity = [CAP]
    open_until_hm = -1
    open_date = None
    for r in df.itertuples():
        pnl = getattr(r, pnl_col)
        e   = getattr(r, entry_col)
        d = r.d; ehm = r.e_hm
        if pnl is None or pd.isna(pnl) or pd.isna(e): continue
        if d == open_date and ehm < open_until_hm: continue  # overlap skip
        # margin check: 1 lot always fits at ~19.5% utilization
        trades.append(dict(d=d, hm=ehm, pnl=pnl, entry=e, dte=r.dte, sign=r.sign))
        equity.append(equity[-1] + pnl)
        open_date = d; open_until_hm = ehm + 60
    return trades, np.array(equity)

atm_tr, atm_eq = backtest("atm_pnl", "atm_prem", "ATM")
far_tr, far_eq = backtest("far_pnl", "far_prem", "FAR")

def stats(trades, eq, name):
    if not trades:
        return dict(name=name, n=0)
    p = np.array([t["pnl"] for t in trades])
    dts = pd.Series([t["d"] for t in trades])
    span_days = (dts.max() - dts.min()).days
    years = max(span_days/365.25, 0.5)
    by_day = pd.DataFrame(trades).groupby("d")["pnl"].sum()
    daily_ret = by_day / CAP
    total = p.sum()
    final = eq[-1]
    peak = np.maximum.accumulate(eq)
    dd = eq - peak
    ddp = dd / peak
    win_r = (p > 0).mean() * 100
    avg_win = p[p>0].mean() if (p>0).any() else 0
    avg_loss = p[p<0].mean() if (p<0).any() else 0
    return dict(
        name=name, n=len(p), ndays=int(dts.nunique()),
        trades_per_month=round(len(p) / max(span_days/30, 1), 1),
        win_pct=round(win_r, 1),
        avg_win=round(avg_win, 0), avg_loss=round(avg_loss, 0),
        expectancy_rs=round(p.mean(), 0),
        best_day_rs=round(by_day.max(), 0),
        worst_day_rs=round(by_day.min(), 0),
        total_pnl_rs=round(total, 0),
        final_equity_rs=round(final, 0),
        total_ret_pct=round((final-CAP)/CAP*100, 1),
        cagr_pct=round(((final/CAP)**(1/years) - 1) * 100, 1),
        max_dd_rs=round(dd.min(), 0),
        max_dd_pct=round(ddp.min()*100, 1),
        sharpe_daily=round(daily_ret.mean()/max(1e-9, daily_ret.std()) * np.sqrt(252), 2),
        # rough profit factor
        pf=round(p[p>0].sum() / max(1, abs(p[p<0].sum())), 2),
    )

a = stats(atm_tr, atm_eq, "SELL ATM same-direction")
f = stats(far_tr, far_eq, "SELL 200-OTM same-direction")

print("\n=== RESULTS ===")
tbl = pd.DataFrame([a, f]).set_index("name").T
print(tbl.to_string())
tbl.to_csv(OUT / "backtest_stats.csv")

# ------ plot ------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios":[3,1]})
ax1.plot(atm_eq, label=f'SELL ATM · final ₹{a["final_equity_rs"]/1e5:.1f}L · CAGR {a["cagr_pct"]}% · Sharpe {a["sharpe_daily"]} · maxDD {a["max_dd_pct"]}%', color='#2962ff', lw=1.4)
ax1.plot(far_eq, label=f'SELL 200-OTM · final ₹{f["final_equity_rs"]/1e5:.1f}L · CAGR {f["cagr_pct"]}% · Sharpe {f["sharpe_daily"]} · maxDD {f["max_dd_pct"]}%', color='#26a69a', lw=1.4)
ax1.axhline(CAP, color='#787b86', ls='--', alpha=0.5, label='₹10L baseline')
ax1.set_ylabel('Equity (₹)'); ax1.legend(loc='upper left', fontsize=9)
ax1.grid(alpha=0.3); ax1.set_title('Fade after 100-pt/15-min spike — realistic costs, 1 lot, seq. trades w/ 60-min overlap skip')

atm_pk = np.maximum.accumulate(atm_eq); atm_dd = (atm_eq - atm_pk)/atm_pk * 100
far_pk = np.maximum.accumulate(far_eq); far_dd = (far_eq - far_pk)/far_pk * 100
ax2.fill_between(range(len(atm_dd)), atm_dd, 0, color='#2962ff', alpha=0.4, label='ATM DD%')
ax2.fill_between(range(len(far_dd)), far_dd, 0, color='#26a69a', alpha=0.4, label='200-OTM DD%')
ax2.set_ylabel('Drawdown %'); ax2.set_xlabel('Trade #'); ax2.legend(fontsize=9); ax2.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "backtest_fade.png", dpi=110)
print(f"\nchart → {OUT}/backtest_fade.png")

# --- yearly attribution ---
def yearly(trades, name):
    if not trades: return pd.DataFrame()
    d = pd.DataFrame(trades)
    d["year"] = d["d"].apply(lambda x: x.year)
    return d.groupby("year").agg(
        n=("pnl","size"),
        pnl=("pnl","sum"),
        win_pct=("pnl", lambda x: round((x>0).mean()*100,1))).round(0)

print("\n=== YEARLY ==="); print("ATM:"); print(yearly(atm_tr, "ATM"))
print("\n200-OTM:"); print(yearly(far_tr, "FAR"))

# --- rewrite a full markdown report ---
lines = [
    "# BACKTEST — FADE AFTER 100-PT/15-MIN SPIKE",
    "Capital ₹10L · 12% approx-SPAN margin · 1 lot per trade · sequential, 60-min hold with overlap skip",
    "Real costs: brokerage ₹40 R/T + STT 0.1% sell + exch 0.03503% both + GST 18% + stamp 0.003% buy + half-spread max(₹0.10, 0.1% of premium) each side",
    "", "## Summary", tbl.to_string(), "",
    "## Yearly P&L", "### SELL ATM", yearly(atm_tr, "ATM").to_string(),
    "", "### SELL 200-OTM", yearly(far_tr, "FAR").to_string(),
]
(OUT / "BACKTEST_FADE.md").write_text("\n".join(lines), encoding="utf-8")
print("\nreport → BACKTEST_FADE.md")
