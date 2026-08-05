# -*- coding: utf-8 -*-
"""bt_size_by_decile.py - large/mid/small composition of each score decile (Principal, 2026-08-05).

HIS POINT, AND IT LANDS ON A REAL GAP
"discount rate varies with large mid small for valuing a stock" - correct, and it exposes something
about what the backtest has actually been testing. The LIVE engine's Value pillar is specified as

    0.25*pctile(-PE, universe) + 0.35*pctile(-PE, sector x TIER) + 0.20*pctile(-PB) + 0.20*FCF yield

i.e. the sector bucket is crossed with a SIZE TIER. The PIT harness does not do that. In
bt_pit_quant.score_asof the line is

    v_pe_s = df.groupby("sector")["pe"].transform(lambda x: winz_pct(-x))     # sector only

so every backtest run so far has graded a small cap's P/E against large caps in the same sector. If
size drives the multiple - and it does, through the cost of equity - then part of the U-shaped decile
curve is an artefact of the harness's simplification rather than a property of the live engine.

SIZE WITHOUT LOOKAHEAD
full750_scored.csv carries `market_cap_approx` and `mcap_tercile`, but those are CURRENT (2026)
values. Classifying a stock's size at a 2023 formation from its 2026 market cap is lookahead, and
biased in the worst possible direction: a stock that compounded from small to large gets labelled
"large", so large caps inherit the winners. That would manufacture exactly the conclusion a size
study is meant to test.

PRIMARY measure is therefore point-in-time: median 60-day TRADED VALUE at the formation date, ranked
within that formation, split on the AMFI-style boundaries (top 100 large, 101-250 mid, rest small).
Traded value is not market cap, but it is computable from data at or before the formation and it
correlates strongly with size in Indian equities. It is a proxy and is labelled as one.
CROSS-CHECK is the current mcap tercile, run alongside and explicitly flagged as lookahead-tainted.
If the two agree the read is robust; if they diverge, the divergence measures winner migration.

Reads the banked detail from bt_decile_diagnose (no panel reload).
Outputs -> results/SIZE_BY_DECILE_20260805/
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
NIFTY = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
DIAG = os.path.join(HERE, "results", "DECILE_DIAG_20260805", "diag_detail.csv")
SCORED = os.path.join(NIFTY, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750",
                      "results", "full750_scored.csv")
OUT = os.path.join(HERE, "results", "SIZE_BY_DECILE_20260805")
os.makedirs(OUT, exist_ok=True)

LARGE_N, MID_N = 100, 250          # AMFI-style rank boundaries


def trim(x, p=0.05):
    a = np.sort(np.asarray(pd.Series(x).dropna(), dtype=float))
    k = int(len(a) * p)
    core = a[k:len(a) - k] if len(a) > 2 * k else a
    return float(core.mean()) if len(core) else np.nan


def main():
    d = pd.read_csv(DIAG)
    print(f"pooled {len(d)} obs, {d['formation'].nunique()} formations")

    # ---- PRIMARY: point-in-time size band from traded value, ranked WITHIN each formation ----
    def band(sub):
        r = sub["turnover"].rank(ascending=False, method="first")
        return pd.Series(np.where(r <= LARGE_N, "large",
                                  np.where(r <= MID_N, "mid", "small")), index=sub.index)
    d["size_pit"] = d.groupby("formation", group_keys=False).apply(band)

    # ---- CROSS-CHECK: current mcap tercile. LOOKAHEAD-TAINTED, kept only to test agreement ----
    try:
        sc = pd.read_csv(SCORED)
        symcol = "symbol" if "symbol" in sc.columns else sc.columns[0]
        mc = sc[[symcol, "mcap_tercile"]].rename(columns={symcol: "sym"})
        mc["sym"] = mc["sym"].astype(str).str.upper().str.strip()
        d = d.merge(mc, on="sym", how="left")
    except Exception as e:
        print("cross-check unavailable:", e)
        d["mcap_tercile"] = np.nan

    # ---- 1. composition of each decile ------------------------------------------------
    comp = (pd.crosstab(d["dec"], d["size_pit"], normalize="index") * 100).round(1)
    comp = comp.reindex(columns=[c for c in ("large", "mid", "small") if c in comp.columns])
    cnt = pd.crosstab(d["dec"], d["size_pit"])
    print("\n=== SIZE COMPOSITION OF EACH DECILE (point-in-time, % of decile) ===")
    print(comp.to_string())
    comp.to_csv(os.path.join(OUT, "composition_pct.csv"))
    cnt.to_csv(os.path.join(OUT, "composition_counts.csv"))

    # ---- 2. forward return by decile WITHIN each size band ----------------------------
    print("\n=== FORWARD RETURN (5% trimmed) BY DECILE, WITHIN EACH SIZE BAND ===")
    print("    if the U-shape survives inside every band it is not a size artefact")
    piv = {}
    for b in ("large", "mid", "small"):
        sub = d[d["size_pit"] == b]
        if len(sub) < 50:
            continue
        piv[b] = sub.groupby("dec")["fwd"].apply(lambda x: trim(x) * 100).round(1)
    piv = pd.DataFrame(piv)
    piv["all"] = d.groupby("dec")["fwd"].apply(lambda x: trim(x) * 100).round(1)
    print(piv.to_string())
    piv.to_csv(os.path.join(OUT, "return_by_decile_and_size.csv"))

    # ---- 3. the size effect itself ----------------------------------------------------
    print("\n=== SIZE EFFECT, ignoring score ===")
    sz = d.groupby("size_pit").agg(n=("fwd", "size"),
                                   fwd_trim5=("fwd", lambda x: round(trim(x) * 100, 1)),
                                   pe_med=("value", "median"))
    print(sz.to_string())

    # ---- 4. does the score's P/E-based Value pillar penalise small caps? -------------
    print("\n=== VALUE PILLAR BY SIZE BAND (the harness grades P/E sector-only, not sector x tier) ===")
    vb = d.groupby("size_pit").agg(value_pillar=("value", "mean"),
                                   quality=("quality", "mean"),
                                   growth=("growth", "mean"),
                                   stage=("stage", "mean"),
                                   final=("final", "mean")).round(1)
    print(vb.to_string())
    vb.to_csv(os.path.join(OUT, "pillars_by_size.csv"))

    # ---- 5. agreement between the PIT proxy and the lookahead-tainted current tercile --
    if d["mcap_tercile"].notna().any():
        print("\n=== PIT proxy versus CURRENT mcap tercile (agreement check) ===")
        ct = pd.crosstab(d["size_pit"], d["mcap_tercile"], normalize="index") * 100
        print(ct.round(0).to_string())
        print("  off-diagonal mass = winner migration; it is why current mcap must not be the "
              "primary measure")

    d.to_csv(os.path.join(OUT, "detail_with_size.csv"), index=False)
    print("\nwrote", OUT)


if __name__ == "__main__":
    main()
