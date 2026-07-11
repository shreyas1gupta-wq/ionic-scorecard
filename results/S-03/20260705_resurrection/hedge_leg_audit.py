"""FF near-month vehicle (Candidate B) -- HEDGE-LEG liquidity audit (Tara Singh, Execution & TCA).
Companion to results/S-03/20260705_resurrection/fill_audit.py (SAME methodology, NEW leg).

Question: for the 673 causal FF-signal dates in causal_per_trade.csv (sym, ca_D=causal entry
day, ca_strike=short/ATM strike, m1_exp=near-month expiry), was there a TRADEABLE near-month
OTM CE at strike distances 1..8 above the short strike, AT SIGNAL TIME (ca_D, same day the FF
signal fires -- this is the entry day BEFORE the old back-leg ex-ante gate is even relevant,
since Candidate B has no back-leg to gate on)?

Reuses fill_audit.py's load_file/day_table/classify/leg_eval verbatim (byte-identical tiering:
NORMAL >=0.5x trailing-20-session median, THIN 0.2-0.5x, THIN-ABRUPT <0.2x, UNTRADED = zero/no
row) -- so the drop-rate number here is directly comparable to the back-leg's 59.3%/61.3%.

Strike ladder = ALL strikes ever seen in the symbol's OWN near-month file (full-life listed set,
not just what happened to print a row on ca_D) -- avoids under-counting distance from HF-schema
days where a strike with zero interest simply has no row. The per-day TIER check (UNTRADED etc.)
still correctly gates on that day's actual activity; the ladder just decides "distance."
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "results/S-03/20260705_resurrection"))
sys.path.insert(0, str(ROOT / "intraday_options_strategy/buying"))
import fill_audit as fa   # noqa: E402  (load_file/day_table/leg_eval/classify)

OUT = ROOT / "results/S-03/20260705_resurrection"
MAX_DIST = 8

_strike_universe_cache: dict[tuple, list] = {}


def strike_universe(front_df, key):
    if key not in _strike_universe_cache:
        _strike_universe_cache[key] = sorted(
            front_df.loc[front_df["option_type"] == "CE", "strike"].astype(float).unique()
        )
    return _strike_universe_cache[key]


def row_oi(front_df, strike, day_iso):
    sub = front_df[(front_df["strike"].astype(float) == float(strike))
                   & (front_df["option_type"] == "CE")
                   & (front_df["trading_day"] == day_iso)]
    if sub.empty:
        return None, False
    oi = float(sub["oi"].sum()) if "oi" in sub.columns else None
    return oi, True


def process(row) -> dict:
    sym = row["sym"]
    m1_exp = pd.Timestamp(row["m1_exp"])
    ca_D = pd.Timestamp(row["ca_D"])
    short_strike = float(row["ca_strike"])
    day_iso = ca_D.date().isoformat()

    rec = dict(sym=sym, m1_exp=row["m1_exp"], ca_D=row["ca_D"], period=row["period"],
               short_strike=short_strike)

    front = fa.load_file(sym, m1_exp)
    if front is None:
        rec.update(status="front_file_missing")
        for d in range(1, MAX_DIST + 1):
            rec[f"d{d}_tier"] = "NO_FILE"
        rec["drop_1_3"] = True
        rec["drop_1_8"] = True
        return rec

    key = (sym, m1_exp.date().isoformat())
    strikes = strike_universe(front, key)
    higher = [k for k in strikes if k > short_strike]

    any_ok_3 = False
    any_ok_8 = False
    no_row_count = 0
    zero_vol_zero_oi_count = 0
    zero_vol_pos_oi_count = 0
    for d in range(1, MAX_DIST + 1):
        if d - 1 >= len(higher):
            rec[f"d{d}_tier"] = "NO_STRIKE"
            rec[f"d{d}_strike"] = None
            rec[f"d{d}_vol"] = None
            rec[f"d{d}_oi"] = None
            continue
        k = higher[d - 1]
        tab = fa.day_table(front, k)
        ev = fa.leg_eval(tab, ca_D)
        oi_val, had_row = row_oi(front, k, day_iso)
        rec[f"d{d}_strike"] = k
        rec[f"d{d}_tier"] = ev["tier"]
        rec[f"d{d}_vol"] = ev["volume"] if ev["present"] else None
        rec[f"d{d}_oi"] = oi_val
        tradeable = ev["tier"] not in ("UNTRADED",)
        if tradeable:
            if d <= 3:
                any_ok_3 = True
            any_ok_8 = True
        else:
            if not had_row:
                no_row_count += 1
            elif oi_val is not None and oi_val > 0:
                zero_vol_pos_oi_count += 1
            else:
                zero_vol_zero_oi_count += 1

    rec["drop_1_3"] = not any_ok_3
    rec["drop_1_8"] = not any_ok_8
    rec["untraded_no_row_count_1_8"] = no_row_count
    rec["untraded_zero_vol_zero_oi_count_1_8"] = zero_vol_zero_oi_count
    rec["untraded_zero_vol_pos_oi_count_1_8"] = zero_vol_pos_oi_count
    rec["status"] = "ok"
    return rec


def main():
    df = pd.read_csv(OUT / "causal_per_trade.csv")
    assert len(df) == 673, f"expected 673 signals, got {len(df)}"

    recs = []
    for i, row in df.iterrows():
        recs.append(process(row))
        if (i + 1) % 100 == 0:
            print(f"[checkpoint] {i+1}/{len(df)} processed", flush=True)

    out = pd.DataFrame(recs)
    out.to_csv(OUT / "hedge_leg_audit_per_trade.csv", index=False)
    print(f"[checkpoint] wrote {OUT / 'hedge_leg_audit_per_trade.csv'} rows={len(out)}", flush=True)

    def summarize(sub, tag):
        n = len(sub)
        d3 = sub["drop_1_3"].mean()
        d8 = sub["drop_1_8"].mean()
        print(f"\n===== {tag} (n={n}) =====")
        print(f"  DROP rate (no tradeable strike within 1-3 above short strike): {d3:.1%} ({int(sub['drop_1_3'].sum())}/{n})")
        print(f"  DROP rate (no tradeable strike within 1-8 above short strike): {d8:.1%} ({int(sub['drop_1_8'].sum())}/{n})")
        # per-distance tier breakdown
        for d in range(1, MAX_DIST + 1):
            col = f"d{d}_tier"
            if col not in sub.columns:
                continue
            vc = sub[col].value_counts(dropna=False)
            total = vc.sum()
            untraded = vc.get("UNTRADED", 0) + vc.get("NO_STRIKE", 0)
            print(f"  dist {d}: UNTRADED/NO_STRIKE={untraded}/{total} ({untraded/total:.1%})  "
                  f"tiers={dict(vc)}")
        # standing-OI supplementary on the untraded-1-8 cohort
        dropped8 = sub[sub["drop_1_8"]]
        if len(dropped8):
            no_row = dropped8["untraded_no_row_count_1_8"].sum()
            zv_zo = dropped8["untraded_zero_vol_zero_oi_count_1_8"].sum()
            zv_po = dropped8["untraded_zero_vol_pos_oi_count_1_8"].sum()
            tot = no_row + zv_zo + zv_po
            print(f"  [supplementary OI check on drop_1_8 cohort's 8 candidate slots] "
                  f"no_row={no_row} ({no_row/tot:.1%}) zero_vol&zero_oi={zv_zo} ({zv_zo/tot:.1%}) "
                  f"zero_vol&pos_oi={zv_po} ({zv_po/tot:.1%})")

    summarize(out, "FULL (673)")
    summarize(out[out["period"] == "BUILD"], "BUILD")
    summarize(out[out["period"] == "FWD"], "FWD")

    summary = {
        "n": len(out),
        "drop_1_3_full": float(out["drop_1_3"].mean()),
        "drop_1_8_full": float(out["drop_1_8"].mean()),
        "drop_1_3_fwd": float(out.loc[out["period"] == "FWD", "drop_1_3"].mean()),
        "drop_1_8_fwd": float(out.loc[out["period"] == "FWD", "drop_1_8"].mean()),
        "drop_1_3_build": float(out.loc[out["period"] == "BUILD", "drop_1_3"].mean()),
        "drop_1_8_build": float(out.loc[out["period"] == "BUILD", "drop_1_8"].mean()),
    }
    with open(OUT / "hedge_leg_audit_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print("\n[done]", summary)


if __name__ == "__main__":
    main()
