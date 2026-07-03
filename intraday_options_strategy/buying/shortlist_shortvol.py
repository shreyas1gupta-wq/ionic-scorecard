"""'Check more better': two remaining feasible SHORT-VOL structures on single-stock options,
entered near expiry (the only liquid window), with realistic frictions.

  JADE LIZARD    : short ~5% OTM put + short ~3% OTM call + long ~6% OTM call (call spread).
                   Credit collected; if credit >= call-spread width -> NO upside risk.
                   Left tail = short put. Hold to expiry, settle intrinsic.
  SHORT STRANGLE : short ~5% OTM call + short ~5% OTM put (~0.2 delta proxy), entered ~14 DTE.
                   Two exits tested: (a) hold-to-expiry, (b) MANAGED = buy back at 50% of
                   credit if reachable on any later session (Tastytrade-style).

P&L reported as % of SPOT (notional) for comparability with combo_menu, AND per rupee of
margin (SPAN proxy = 12% of notional). Slippage per leg via frictions.slippage_pct('stock').
Build 2021-2024 / forward 2025-2026.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import dispersion_strategy as ds
import frictions as fr

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SOPT = ds.SOPT
SPLIT = dt.date(2024, 12, 31)
ENTRY_DTE = 14              # calendar days before expiry to enter
MARGIN_FRAC = 0.12         # SPAN+exposure proxy for a short strangle on a large-cap
OTM_P = 0.05               # short put distance
OTM_C = 0.05               # short strangle call distance
JL_C_SHORT = 0.03          # jade lizard short call
JL_C_LONG = 0.06           # jade lizard long call (defines width)
SLIP = fr.slippage_pct("stock", "near_otm")   # ~0.021 per leg


def near(strikes, target):
    return min(strikes, key=lambda x: abs(x - target)) if strikes else None


def run():
    C = ds.stock_close()
    stocks = sorted({p.name for p in SOPT.iterdir() if p.is_dir()})
    recs = []
    for sym in stocks:
        if sym not in C.columns:
            continue
        cser = C[sym].dropna()
        for p in sorted((SOPT / sym).glob("*.parquet")):
            exp = dt.date.fromisoformat(p.stem)
            try:
                df = pq.read_table(p).to_pandas()
                df["trading_day"] = pd.to_datetime(df["trading_day"].astype(str))
            except Exception:
                continue
            tdays = sorted(df["trading_day"].dt.date.unique())
            if len(tdays) < 5:
                continue
            target = exp - dt.timedelta(days=ENTRY_DTE)
            cands = [d for d in tdays if d >= target and d < exp]
            entry = cands[0] if cands else tdays[0]
            later = [d for d in tdays if entry < d < exp]      # sessions to test 50%-take
            spot_e = cser.asof(pd.Timestamp(entry)); spot_x = cser.asof(pd.Timestamp(exp))
            if not (np.isfinite(spot_e) and np.isfinite(spot_x) and spot_e > 0):
                continue
            strikes = sorted(df["strike"].unique())
            kp = near(strikes, spot_e * (1 - OTM_P))
            kc = near(strikes, spot_e * (1 + OTM_C))
            kc_js = near(strikes, spot_e * (1 + JL_C_SHORT))
            kc_jl = near(strikes, spot_e * (1 + JL_C_LONG))
            if None in (kp, kc, kc_js, kc_jl) or not (kc_jl > kc_js > spot_e and kp < spot_e):
                continue

            def px(k, o, day=entry):
                return ds.price_asof(df, k, o, day)

            p_put, c_call = px(kp, "PE"), px(kc, "CE")
            jc_s, jc_l = px(kc_js, "CE"), px(kc_jl, "CE")
            if not all(np.isfinite(x) and x > 0 for x in (p_put, c_call, jc_s, jc_l)):
                continue

            def cintr(k):
                return max(0.0, spot_x - k)

            def pintr(k):
                return max(0.0, k - spot_x)

            def sell_pnl(prem, intr):
                return prem * (1 - SLIP) - intr * (1 + SLIP)

            def buy_pnl(prem, intr):
                return intr * (1 - SLIP) - prem * (1 + SLIP)

            # ---- short strangle, hold to expiry
            credit = (c_call + p_put)
            strangle_hold = sell_pnl(c_call, cintr(kc)) + sell_pnl(p_put, pintr(kp))

            # ---- short strangle, MANAGED at 50% of credit
            target_bb = 0.5 * credit          # buy back both legs for half the credit
            managed = strangle_hold; man_exit = exp
            for d in later:
                cc = px(kc, "CE", d); pp = px(kp, "PE", d)
                if np.isfinite(cc) and np.isfinite(pp):
                    cost_bb = (cc + pp) * (1 + SLIP)
                    if cost_bb <= target_bb:
                        managed = credit * (1 - SLIP) - cost_bb
                        man_exit = d
                        break

            # ---- jade lizard: short put + short call - long further call
            jl = sell_pnl(p_put, pintr(kp)) + sell_pnl(jc_s, cintr(kc_js)) + buy_pnl(jc_l, cintr(kc_jl))
            jl_credit = p_put + jc_s - jc_l
            jl_width = kc_jl - kc_js
            jl_no_upside = jl_credit >= jl_width

            recs.append({
                "sym": sym, "exp": exp, "entry": entry, "spot": spot_e,
                "strangle_hold": strangle_hold / spot_e,
                "strangle_managed": managed / spot_e,
                "man_exit": man_exit,
                "jade_lizard": jl / spot_e,
                "jl_no_upside_risk": jl_no_upside,
                "strangle_hold_margin": strangle_hold / (spot_e * MARGIN_FRAC),
                "strangle_managed_margin": managed / (spot_e * MARGIN_FRAC),
                "jade_margin": jl / (spot_e * MARGIN_FRAC),
            })
    return pd.DataFrame(recs)


def rep(D, col, label):
    x = D[col]; b = D[D["exp"] <= SPLIT][col]; f = D[D["exp"] > SPLIT][col]
    print(f"  {label:26s} mean {x.mean():>+8.3%} med {x.median():>+8.3%} hit {(x>0).mean():>4.0%} "
          f"| BUILD {b.mean():>+7.3%} FWD {f.mean():>+7.3%} | worst {x.min():>+7.1%} n={len(x)}")


if __name__ == "__main__":
    D = run()
    if D.empty:
        print("0 trades"); raise SystemExit
    D.to_parquet(ROOT / "intraday_options_strategy/buying/shortlist_shortvol.parquet")
    print(f"[events] {len(D)} trades  {D['exp'].min()}..{D['exp'].max()}  "
          f"avg entry DTE={(pd.to_datetime(D['exp'])-pd.to_datetime(D['entry'])).dt.days.mean():.0f}")
    print(f"  jade lizards with NO upside risk (credit>=width): {D['jl_no_upside_risk'].mean():.0%}\n")

    print("=== % of SPOT (notional) ===")
    rep(D, "strangle_hold", "short strangle (hold)")
    rep(D, "strangle_managed", "short strangle (50% mgd)")
    rep(D, "jade_lizard", "jade lizard")
    mgd = D[D["man_exit"] != D["exp"]]
    print(f"\n  managed strangle hit 50%-target early on {len(mgd)}/{len(D)} = {len(mgd)/len(D):.0%} of trades")

    print("\n=== per rupee of MARGIN (SPAN proxy = 12% notional) -> approx return on capital ===")
    rep(D, "strangle_hold_margin", "short strangle (hold)")
    rep(D, "strangle_managed_margin", "short strangle (50% mgd)")
    rep(D, "jade_margin", "jade lizard")
