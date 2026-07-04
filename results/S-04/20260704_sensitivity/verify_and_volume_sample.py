"""S-04 sensitivity follow-ups (Sameer Bhat, E-027):
(1) explain center-reproduction delta (n 5031 -> 5084) — expect all-new late-2026 expiries;
(2) SOP-form plateau: best cell vs ITS +/-1-step corner neighborhood median;
(3) 300-trade SAMPLE volume audit of ENTRY fills (COST_STANDARDS circuit/thin-volume rule):
    per sampled center trade, re-derive kp/kc, read the raw expiry file, measure
    entry-day traded volume per leg + entry-print staleness (nearest-print day distance).
ASCII prints only (cp1252)."""
from __future__ import annotations
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "results/S-04/20260704_sensitivity"
sys.path.insert(0, str(ROOT / "intraday_options_strategy/buying"))
import dispersion_strategy as ds
import shortlist_shortvol as ss

T = pd.read_parquet(OUT / "trades_all_configs.parquet")
g = T[T["cfg"] == "dte14_otm5_pt50"].copy()
g = g[~((g["managed"] > 0.06) | (g["hold"] > 0.06))]          # same L7b as analysis
g["exp_d"] = pd.to_datetime(g["exp"])

# ---- (1) reproduction delta ----
reg = pd.read_parquet(ROOT / "intraday_options_strategy/buying/shortlist_shortvol.parquet")
reg_max_exp = pd.to_datetime(reg["exp"]).max()
newer = g[g["exp_d"] > reg_max_exp]
older = g[g["exp_d"] <= reg_max_exp]
print("registered parquet: n=%d mean=%+.4f%% max_exp=%s" %
      (len(reg), 100 * reg["strangle_managed"].mean(), reg_max_exp.date()))
print("rebuild center    : n=%d mean=%+.4f%%" % (len(g), 100 * g["managed"].mean()))
print("  trades with exp > registered max_exp : %d (mean %+.4f%%)" %
      (len(newer), 100 * newer["managed"].mean() if len(newer) else float("nan")))
print("  trades with exp <= registered max_exp: %d (mean %+.4f%%)  [vs registered +0.2241%%]" %
      (len(older), 100 * older["managed"].mean()))
# per-key overlap for the older subset
kreg = set(zip(reg["sym"], pd.to_datetime(reg["exp"]).dt.date.astype(str)))
kold = set(zip(older["sym"], older["exp_d"].dt.date.astype(str)))
print("  key overlap older-vs-registered: common=%d only_rebuild=%d only_registered=%d" %
      (len(kreg & kold), len(kold - kreg), len(kreg - kold)))

# ---- (2) SOP-form plateau for the best cell ----
GR = pd.read_csv(OUT / "grid.csv")
grid = GR[GR["kind"] == "grid"].copy()
best = grid.loc[grid["edge_pct_spot"].idxmax()]
dte_s, otm_s, pt_s = [12, 14, 16], [0.04, 0.05, 0.06], [0.4, 0.5, 0.6]

def neighbors(row):
    di, oi, pi = dte_s.index(row["dte"]), otm_s.index(row["otm"]), pt_s.index(row["pt"])
    sel = []
    for _, r in grid.iterrows():
        dd = abs(dte_s.index(r["dte"]) - di)
        od = abs(otm_s.index(r["otm"]) - oi)
        pdl = abs(pt_s.index(r["pt"]) - pi)
        if max(dd, od, pdl) <= 1 and not (dd == od == pdl == 0):
            sel.append(r["edge_pct_spot"])
    return np.array(sel)

nb = neighbors(best)
print("\nSOP plateau (best cell %s = %.4f%%): %d step-1 neighbors, median %.4f%%, ratio %.3f (rule: <=1.20)" %
      (best["cfg"], best["edge_pct_spot"], len(nb), np.median(nb),
       best["edge_pct_spot"] / np.median(nb)))
cent = grid[grid["cfg"] == "dte14_otm5_pt50"].iloc[0]
nbc = neighbors(cent)
print("   center cell %s = %.4f%%: %d neighbors, median %.4f%%, ratio %.3f" %
      (cent["cfg"], cent["edge_pct_spot"], len(nbc), np.median(nbc),
       cent["edge_pct_spot"] / np.median(nbc)))

# ---- (3) entry-fill volume sample audit ----
rng = np.random.default_rng(7)
samp = g.sample(n=min(300, len(g)), random_state=7)
rows = []
for _, tr in samp.iterrows():
    f = ds.SOPT / tr["sym"] / (tr["exp"] + ".parquet")
    if not f.exists():
        continue
    try:
        df = pq.read_table(f).to_pandas()
        df["trading_day"] = pd.to_datetime(df["trading_day"].astype(str))
    except Exception:
        continue
    schema = "daily" if "settle" in df.columns else "minute"
    strikes = sorted(df["strike"].unique())
    kp = ss.near(strikes, tr["spot"] * 0.95)
    kc = ss.near(strikes, tr["spot"] * 1.05)
    entry = pd.Timestamp(tr["entry"])
    rec = {"sym": tr["sym"], "exp": tr["exp"], "entry": tr["entry"], "schema": schema}
    for leg, k, ot in [("put", kp, "PE"), ("call", kc, "CE")]:
        leg_df = df[(df["strike"] == k) & (df["option_type"] == ot)]
        day_rows = leg_df[leg_df["trading_day"] == entry]
        vol = float(day_rows["volume"].sum()) if ("volume" in df.columns and len(day_rows)) else \
              (0.0 if "volume" in df.columns else np.nan)
        # staleness of the entry print actually used by the pipeline
        ser = ds._series(df, k, ot)
        px, pdate = ds._nearest(ser, entry.date(), 15)
        stale = abs((pd.Timestamp(pdate) - entry).days) if pdate is not None else np.nan
        rec[f"{leg}_day_rows"] = int(len(day_rows))
        rec[f"{leg}_day_volume"] = vol
        rec[f"{leg}_entry_stale_days"] = stale
    rows.append(rec)
S = pd.DataFrame(rows)
S.to_csv(OUT / "entry_fill_volume_sample.csv", index=False)
has_vol = S[["put_day_volume", "call_day_volume"]].notna().all(axis=1)
sv = S[has_vol]
res = {
    "sampled": int(len(S)),
    "with_volume_col": int(len(sv)),
    "schema_counts": S["schema"].value_counts().to_dict(),
    "either_leg_no_row_on_entry_day_pct": float(
        ((S["put_day_rows"] == 0) | (S["call_day_rows"] == 0)).mean() * 100),
    "either_leg_zero_volume_pct_of_with_vol": float(
        ((sv["put_day_volume"] == 0) | (sv["call_day_volume"] == 0)).mean() * 100) if len(sv) else None,
    "entry_stale_gt0d_pct": float(
        ((S["put_entry_stale_days"] > 0) | (S["call_entry_stale_days"] > 0)).mean() * 100),
    "entry_stale_gt2d_pct": float(
        ((S["put_entry_stale_days"] > 2) | (S["call_entry_stale_days"] > 2)).mean() * 100),
    "entry_stale_max_days": float(np.nanmax(
        S[["put_entry_stale_days", "call_entry_stale_days"]].values)),
}
print("\nENTRY-FILL VOLUME SAMPLE (n=%d):" % len(S))
print(json.dumps(res, indent=2))
(OUT / "entry_fill_volume_sample_summary.json").write_text(
    json.dumps(res, indent=2), encoding="utf-8")
print("saved entry_fill_volume_sample.csv + summary json")
