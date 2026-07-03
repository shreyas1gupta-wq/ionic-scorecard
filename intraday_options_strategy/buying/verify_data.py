"""Raw data verification: pull actual option rows so the user can eyeball realism."""
from __future__ import annotations

import datetime as dt
import random

import pandas as pd

import chain

pd.set_option("display.width", 220, "display.max_columns", None)
random.seed(7)
STEP = 50


def show_22000_dec2025():
    print("=" * 80)
    print("(A) 22000 CE — Dec-2025 monthly expiry (2025-12-30)")
    print("=" * 80)
    exp = dt.date(2025, 12, 30)
    df = chain.load_expiry(exp)
    strikes = sorted(df["strike"].unique())
    print(f"file strike range: {strikes[0]} .. {strikes[-1]}  ({len(strikes)} strikes)")
    sub = df[(df["strike"] == 22000) & (df["option_type"] == "CE")]
    if sub.empty:
        near = min(strikes, key=lambda x: abs(x - 22000))
        print(f"22000 not listed; nearest deep-ITM CE strike = {near}")
        sub = df[(df["strike"] == near) & (df["option_type"] == "CE")]
    # snapshots across a few days
    sub = sub.sort_values("t")
    days = sorted(sub["trading_day"].unique())
    print(f"trading days present: {days[0]} .. {days[-1]} ({len(days)} days)")
    for d in [days[0], days[len(days)//2], days[-1]]:
        g = sub[sub["trading_day"] == d]
        print(f"\n  --- {d} (5 rows) ---")
        print(g[["t", "strike", "option_type", "open", "high", "low", "close",
                 "volume", "open_interest"]].head(5).to_string(index=False))


def show_atm_jan2024():
    print("\n" + "=" * 80)
    print("(B) ATM CE & PE on 2024-01-01, -05, -10 (spot, nearest expiry, ATM chain)")
    print("=" * 80)
    spot = chain.load_index()
    for d in [dt.date(2024, 1, 1), dt.date(2024, 1, 5), dt.date(2024, 1, 10)]:
        day_spot = spot[spot.index.date == d]
        if day_spot.empty:
            print(f"\n{d}: NO SPOT (holiday/absent)")
            continue
        exp = chain.nearest_expiry(d, 0, 7)
        cdf = chain.day_chain(exp, d) if exp else pd.DataFrame()
        for hhmm in ["09:20", "12:00", "15:15"]:
            t = pd.Timestamp(d) + pd.Timedelta(hours=int(hhmm[:2]), minutes=int(hhmm[3:]))
            s0 = day_spot[day_spot.index <= t]["close"]
            if s0.empty or cdf.empty:
                continue
            s0 = s0.iloc[-1]
            k = int(round(s0 / STEP) * STEP)
            avail = sorted(cdf["strike"].unique())
            k = min(avail, key=lambda x: abs(x - k))
            ce = cdf[(cdf["strike"] == k) & (cdf["option_type"] == "CE") & (cdf["t"] <= t)]
            pe = cdf[(cdf["strike"] == k) & (cdf["option_type"] == "PE") & (cdf["t"] <= t)]
            ce_c = ce["close"].iloc[-1] if not ce.empty else float("nan")
            pe_c = pe["close"].iloc[-1] if not pe.empty else float("nan")
            ce_v = ce["volume"].iloc[-1] if not ce.empty else 0
            pe_v = pe["volume"].iloc[-1] if not pe.empty else 0
            print(f"{d} {hhmm}  exp={exp}({(exp-d).days}dte)  spot={s0:8.1f}  ATM={k}  "
                  f"CE={ce_c:7.2f}(vol {ce_v})  PE={pe_c:7.2f}(vol {pe_v})")


def show_random():
    print("\n" + "=" * 80)
    print("(C) 5 random raw snapshots (random expiry / strike / minute)")
    print("=" * 80)
    _, exps = chain.build_expiry_index()
    for i in range(5):
        exp = random.choice(exps)
        df = chain.load_expiry(exp)
        row = df.sample(1, random_state=random.randint(0, 10**6)).iloc[0]
        print(f"\n#{i+1} expiry-file {exp}:")
        print(f"   t={row['t']}  {row['symbol']} {int(row['strike'])}{row['option_type']} "
              f"exp={row['expiry']}  O={row['open']} H={row['high']} L={row['low']} "
              f"C={row['close']}  vol={row['volume']} OI={row['open_interest']}")


if __name__ == "__main__":
    show_22000_dec2025()
    show_atm_jan2024()
    show_random()
