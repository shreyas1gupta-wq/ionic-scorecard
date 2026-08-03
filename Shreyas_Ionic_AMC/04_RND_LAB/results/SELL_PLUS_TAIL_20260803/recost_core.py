"""SELL_PLUS_TAIL_20260803 -- step 2: re-cost the LD_SELL short-premium core at the new STT.

LD_SELL = biweekly 0.10-delta naked strangle, stop-out@2x credit, 10% naked margin, LOT=65.
Source: LONGDATED_SELLING_20260730/best_config_trades.csv (286 trades, 2011-2026).

FINDING (confirmed by reading 111_longdated_selling.py): the ORIGINAL build's pl_rs_net has NO
seller-side STT at all -- leg_cost_rs() is brokerage+slippage only; STT_EXERCISE_PCT is applied
only to LONG condor wings (buyer side), never to the naked short legs. So "re-costing at the new
STT" here means ADDING a cost that was always missing, not bumping an existing one.

STT on options is charged on the SELL side, on PREMIUM. For a naked short strangle this is the
OPENING transaction (sell-to-open both legs) -- it does not recur on close (buy-to-close, if
stopped out, pays no STT; expiry-OTM has no closing transaction; expiry-ITM assignment on the
WRITER side is also not an STT event -- exercise STT is charged to the option HOLDER/buyer only,
per COST_STANDARDS.md and the 111_longdated_selling.py note). So:
    STT_rs = STT_rate * credit_pt * LOT   (charged once, at entry, every trade)
old rate 0.10%, new rate 0.15% (Budget 2026, effective 2026-04-01, per STT_RECOST_20260803).
"""
import numpy as np
import pandas as pd
from pathlib import Path

SRC = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\LONGDATED_SELLING_20260730\best_config_trades.csv")
OUT = Path(__file__).parent

LOT = 65
STT_OLD, STT_NEW = 0.0010, 0.0015

df = pd.read_csv(SRC, parse_dates=["entry_day", "exit_day", "expiry"])
print(f"loaded {len(df)} trades, {df['entry_day'].min().date()}..{df['exit_day'].max().date()}")

# sanity: margin_rs = 0.10 * spot_entry * LOT
implied_lot = (df["margin_rs"] / (0.10 * df["spot_entry"])).round(1)
assert (implied_lot == LOT).all(), f"LOT mismatch: {implied_lot.unique()}"

df["premium_rs"] = df["credit_pt"] * LOT
df["stt_old_rs"] = STT_OLD * df["premium_rs"]
df["stt_new_rs"] = STT_NEW * df["premium_rs"]
df["pl_rs_net_recost_old"] = df["pl_rs_net"] - df["stt_old_rs"]
df["pl_rs_net_recost_new"] = df["pl_rs_net"] - df["stt_new_rs"]
df["margin_ret_orig"] = df["pl_rs_net"] / df["margin_rs"]
df["margin_ret_recost_old"] = df["pl_rs_net_recost_old"] / df["margin_rs"]
df["margin_ret_recost_new"] = df["pl_rs_net_recost_new"] / df["margin_rs"]

# arithmetic disclosure -- show it, don't assume
tot_premium_rs = df["premium_rs"].sum()
tot_stt_new = df["stt_new_rs"].sum()
tot_pl_orig = df["pl_rs_net"].sum()
print(f"\nSTT ARITHMETIC (Part D):")
print(f"  total premium sold (credit_pt*LOT), {len(df)} trades: Rs{tot_premium_rs:,.0f}")
print(f"  total STT at OLD 0.10%: Rs{df['stt_old_rs'].sum():,.0f}")
print(f"  total STT at NEW 0.15%: Rs{tot_stt_new:,.0f}")
print(f"  original (no-STT) total net P&L: Rs{tot_pl_orig:,.0f}")
print(f"  STT-new as % of original net P&L: {100*tot_stt_new/tot_pl_orig:.2f}%")
print(f"  STT-new as % of premium sold: {100*tot_stt_new/tot_premium_rs:.4f}% (should be exactly 0.15%)")


def build_nav(sub, retcol):
    sub = sub.sort_values("exit_day").reset_index(drop=True)
    nav = (1 + sub[retcol]).cumprod()
    nav_dates = sub["exit_day"]
    return sub, nav, nav_dates


def summarize(sub, retcol, label):
    sub2 = sub.sort_values("exit_day").reset_index(drop=True)
    nav = (1 + sub2[retcol]).cumprod()
    n_years = (sub2["exit_day"].max() - sub2["entry_day"].min()).days / 365.25
    cagr = nav.iloc[-1] ** (1 / n_years) - 1
    peak = nav.cummax()
    dd = (nav - peak) / peak
    maxdd = dd.min()
    n = len(sub2)
    tpy = n / n_years
    mu, sd = sub2[retcol].mean(), sub2[retcol].std()
    sharpe = (mu / sd) * np.sqrt(tpy) if sd > 0 else np.nan
    calmar = cagr / abs(maxdd) if maxdd < 0 else np.nan
    print(f"\n[{label}] n={n} span={n_years:.2f}yr trades/yr={tpy:.1f} "
          f"CAGR={100*cagr:.2f}% MaxDD={100*maxdd:.2f}% Sharpe={sharpe:.2f} Calmar={calmar:.2f} "
          f"worst_trade_margin_ret={100*sub2[retcol].min():.1f}%")
    worst = sub2.loc[sub2[retcol].idxmin()]
    print(f"    worst trade: entry={worst['entry_day'].date()} exit={worst['exit_day'].date()} "
          f"margin_ret={100*worst[retcol]:.1f}% exit_reason={worst['exit_reason']}")
    return dict(label=label, n=n, span_yr=n_years, trades_per_yr=tpy, cagr_pct=100 * cagr,
                maxdd_pct=100 * maxdd, sharpe=sharpe, calmar=calmar,
                worst_trade_margin_ret_pct=100 * sub2[retcol].min())


results = []
for retcol, tag in (("margin_ret_orig", "ORIG_no_STT"), ("margin_ret_recost_old", "STT_old_0.10pct"),
                     ("margin_ret_recost_new", "STT_new_0.15pct")):
    results.append(summarize(df, retcol, f"FULL_2011-2026_{tag}"))
    sub16 = df[df["entry_day"] >= "2016-01-01"]
    results.append(summarize(sub16, retcol, f"2016-2026_{tag}"))

# COVID window isolation (2020 calendar year, matching FINDINGS' "COVID(2020) alone" framing)
covid = df[(df["entry_day"] >= "2020-01-01") & (df["entry_day"] <= "2020-12-31")]
print(f"\n[COVID 2020 core trades] n={len(covid)}")
for retcol, tag in (("pl_rs_net", "ORIG_no_STT"), ("pl_rs_net_recost_old", "STT_old"),
                     ("pl_rs_net_recost_new", "STT_new")):
    tot = covid[retcol].sum()
    worst_idx = covid[retcol].idxmin() if len(covid) else None
    worst_ret = covid.loc[worst_idx, "margin_ret_recost_new"] if worst_idx is not None else np.nan
    print(f"  {tag}: total net Rs{tot:,.0f}  worst single trade margin_ret(new STT)={100*worst_ret:.1f}%")

df.to_csv(OUT / "checkpoints" / "core_trades_recost.csv", index=False)
pd.DataFrame(results).to_csv(OUT / "checkpoints" / "core_summary.csv", index=False)
covid.to_csv(OUT / "checkpoints" / "core_covid_2020_trades.csv", index=False)
print("\nwrote checkpoints/core_trades_recost.csv, core_summary.csv, core_covid_2020_trades.csv")
