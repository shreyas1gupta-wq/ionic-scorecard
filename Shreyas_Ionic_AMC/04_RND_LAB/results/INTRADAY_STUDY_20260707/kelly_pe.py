"""0.25x Kelly sizing on Rs.1cr for the SELL-cheap-PE 0DTE 12:00 strategy (Sharpe 2.60 raw).

Kelly frame: per-trade return = pnl / margin_per_lot. Full Kelly = argmax E[log(1 + f*r)].
Position each trade: n_lots = floor(0.25 * Kelly * capital / margin_per_lot), capped at freeze qty 27.
Capital compounds trade-to-trade.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar
from pathlib import Path

OUT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\INTRADAY_STUDY_20260707")

LOT = 65
MARGIN_PER_LOT = 195000     # approx 12% x 65 x 25000
FREEZE_QTY = 27             # max lots per order
CAP0 = 10_000_000           # Rs.1cr

# ---- load PE-only trades ----
df = pd.read_csv(OUT / "rev_A_sell_cheap_hold.csv")
df = df[df["side"] == "PE"].sort_values("d").reset_index(drop=True)
df["date"] = pd.to_datetime(df["d"])
print(f"PE trades: n={len(df)}, span {df['date'].min().date()} -> {df['date'].max().date()}")

# ---- per-lot stats (baseline) ----
p = df["pnl"].values
p_win = (p > 0).mean(); p_loss = 1 - p_win
W = p[p > 0].mean(); L = abs(p[p < 0].mean())
print(f"per-lot: win={p_win*100:.1f}%, avg_win=Rs.{W:.0f}, avg_loss=Rs.{L:.0f}, W:L={W/L:.2f}")

# ---- Kelly (numerical, log-growth-optimal) ----
# Per-trade return if we allocate ONE-margin-unit per trade: r_i = pnl_i / margin_per_lot
r = p / MARGIN_PER_LOT
def neg_log_growth(f):
    v = 1 + f * r
    if (v <= 0).any(): return 1e9
    return -np.mean(np.log(v))
res = minimize_scalar(neg_log_growth, bounds=(0.01, 30), method="bounded")
f_kelly = res.x
kelly_25 = 0.25 * f_kelly
print(f"Full Kelly leverage: {f_kelly:.2f}x  |  0.25x Kelly: {kelly_25:.2f}x")

# Sanity: discrete Kelly closed-form (avg win/loss)
b = W / L
kelly_bernoulli = (p_win * b - p_loss) / b
print(f"(sanity) discrete-Bernoulli Kelly = (p*b - q)/b = {kelly_bernoulli:.3f}  -- different frame, different meaning")

# ---- simulate compounded equity on 1cr ----
def simulate(kelly_mult, cap0=CAP0, freeze=FREEZE_QTY):
    equity = [cap0]; lots_hist = []; trade_pnl = []
    for pnl_1lot in p:
        cap = equity[-1]
        margin_budget = kelly_mult * cap
        n_lots = int(margin_budget / MARGIN_PER_LOT)
        n_lots = max(1, min(n_lots, freeze))
        pnl = pnl_1lot * n_lots
        equity.append(cap + pnl)
        lots_hist.append(n_lots); trade_pnl.append(pnl)
    return np.array(equity), np.array(lots_hist), np.array(trade_pnl)

def stats(eq, name):
    peak = np.maximum.accumulate(eq); dd = (eq - peak) / peak
    yrs = (df["date"].max() - df["date"].min()).days / 365.25
    final = eq[-1]
    cagr = (final/CAP0)**(1/yrs) - 1
    ret = np.diff(eq) / eq[:-1]
    return dict(name=name, final=final, total_ret=(final-CAP0)/CAP0,
                cagr=cagr, maxdd=dd.min(),
                sharpe_ann=ret.mean()/max(1e-9, ret.std()) * np.sqrt(20),  # 20 trades/yr
                worst_trade=np.diff(eq).min(), best_trade=np.diff(eq).max())

# Multiple sizing curves for comparison
sizings = [
    ("0.10x Kelly (very conservative)", 0.10 * f_kelly),
    ("0.25x Kelly (Principal spec)",  0.25 * f_kelly),
    ("0.50x Kelly",                  0.50 * f_kelly),
    ("Full Kelly (unsafe)",          1.00 * f_kelly),
    ("Fixed 5 lots (control)",       None),
    ("Fixed 15 lots (control)",      None),
]

results = []
eqs = {}
for name, km in sizings:
    if km is None:
        # fixed lots
        n_lots = 5 if "5 lots" in name else 15
        eq = [CAP0]
        for pnl_1lot in p:
            eq.append(eq[-1] + pnl_1lot * n_lots)
        eq = np.array(eq)
        lots_avg = n_lots
    else:
        eq, lots, _ = simulate(km)
        lots_avg = lots.mean()
    st = stats(eq, name); st["avg_lots"] = lots_avg
    results.append(st); eqs[name] = eq
    print(f"\n{name}:")
    print(f"  avg lots: {lots_avg:.1f}")
    print(f"  final: Rs.{st['final']:,.0f}   total: {st['total_ret']*100:.1f}%")
    print(f"  CAGR (XIRR-approx): {st['cagr']*100:.2f}%")
    print(f"  MaxDD: {st['maxdd']*100:.1f}%")
    print(f"  Sharpe (ann): {st['sharpe_ann']:.2f}")
    print(f"  worst trade: Rs.{st['worst_trade']:,.0f}")

# save summary
sdf = pd.DataFrame(results).set_index("name")
sdf.to_csv(OUT / "kelly_pe_summary.csv")

# ---- chart ----
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(13, 10), gridspec_kw={"height_ratios":[3,1.2,1]})
colors = ['#4dd0e1', '#ffd54f', '#26a69a', '#ef5350', '#787b86', '#607d8b']
for i, (name, eq) in enumerate(eqs.items()):
    st = next(r for r in results if r["name"] == name)
    ax1.plot(eq, label=f'{name}: Rs.{st["final"]/1e7:.2f}cr, CAGR {st["cagr"]*100:.1f}%, DD {st["maxdd"]*100:.1f}%',
             color=colors[i], lw=1.5, alpha=0.9)
ax1.axhline(CAP0, color='#787b86', ls='--', alpha=0.5, label='Rs.1cr start')
ax1.set_ylabel('Equity (Rs.)'); ax1.legend(fontsize=9, loc='best'); ax1.grid(alpha=0.3)
ax1.set_title('0DTE PE-sell (CE>1.1x PE @ 12:00, hold 15:20) - Kelly-scaled equity on Rs.1cr, 103 trades / 5 yrs')

# Log scale to see all sizings
ax2.set_yscale('log')
for i, (name, eq) in enumerate(eqs.items()):
    ax2.plot(eq, color=colors[i], lw=1.4)
ax2.axhline(CAP0, color='#787b86', ls='--', alpha=0.5)
ax2.set_ylabel('Equity (log Rs.)'); ax2.grid(alpha=0.3, which='both')

# Drawdown of the 0.25 Kelly line only
eq_25 = eqs["0.25x Kelly (Principal spec)"]
peak = np.maximum.accumulate(eq_25); dd_25 = (eq_25 - peak) / peak * 100
ax3.fill_between(range(len(dd_25)), dd_25, 0, color='#ffd54f', alpha=0.5, label='0.25x Kelly DD%')
ax3.set_ylabel('DD %'); ax3.set_xlabel('Trade #'); ax3.legend(fontsize=9); ax3.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(OUT / "kelly_pe_equity.png", dpi=110)
print(f"\nchart -> {OUT}/kelly_pe_equity.png")

# yearly for 0.25x Kelly
eq25, lots25, tpnl25 = simulate(kelly_25)
tl = pd.DataFrame({"date": df["date"], "lots": lots25, "pnl": tpnl25, "eq": eq25[1:]})
tl["year"] = tl["date"].dt.year
print("\n=== 0.25x Kelly yearly ===")
yr = tl.groupby("year").agg(n=("pnl","size"), pnl=("pnl","sum"),
                             lots_avg=("lots","mean"),
                             win_pct=("pnl", lambda x: round((x>0).mean()*100,1)),
                             eq_end=("eq","last")).round(0)
print(yr)
yr.to_csv(OUT / "kelly_pe_yearly.csv")
