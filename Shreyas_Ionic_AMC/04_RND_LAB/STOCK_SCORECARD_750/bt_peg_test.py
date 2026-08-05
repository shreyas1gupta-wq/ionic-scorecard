# -*- coding: utf-8 -*-
"""bt_peg_test.py - would PEG fix the U-shaped decile curve? (Principal question, 2026-08-05)

WHY THIS IS THE RIGHT QUESTION TO ASK
The decomposition showed deciles 2-3 outperform while scoring POORLY on our Value pillar (40.2 vs
66.4 for D8-10) and carrying growth well above quality (D3: growth 47.3, quality 33.6). Our Value
pillar is roughly 60% raw P/E by construction:
    0.25*pctile(-PE universe) + 0.35*pctile(-PE sector) + 0.20*pctile(-PB) + 0.20*pctile(FCF yield)
A raw-P/E pillar marks DOWN every fast grower for being expensive. PEG does not - it asks whether
the multiple is justified by the growth. So the hypothesis is precise and falsifiable:

    H  the U-shape is an artefact of valuing on P/E instead of P/E-relative-to-growth. Names that
       are dear on P/E but reasonable on PEG get pushed into the lower-middle deciles and then
       outperform.

WHAT IS TESTED
  1. PEG by decile. If D2-3 are dear on P/E but CHEAP on PEG, the pillar is mispricing them.
  2. Forward returns by PEG decile, ranked on PEG alone, against the existing score's deciles.
  3. A swapped composite: Value rebuilt on PEG instead of P/E, rescored, re-deciled. Does the
     U-shape flatten and does D10-D1 widen?

PEG DEFINITION AND ITS TRAPS, HANDLED EXPLICITLY
  PEG = P/E divided by earnings growth in percent. Three failure modes, all of which produce
  nonsense if ignored:
    negative or zero growth  -> PEG is meaningless (a negative PEG is not "cheap"). EXCLUDED, and
                                the excluded count is reported rather than hidden.
    tiny positive growth     -> PEG explodes toward infinity. Winsorised at the 2nd/98th percentile
                                before ranking, the same treatment every other pillar gets.
    negative earnings        -> P/E already undefined upstream, so those rows never arrive.
  Standard PEG uses EPS growth; sales growth is computed alongside as a cross-check because EPS is
  the noisier line and a conclusion that only survives on one of them is not a conclusion.

NO-LOOKAHEAD unchanged: all inputs come from the same PIT frames at the same formation dates, via
bt_pit_quant. Nothing here reads a price or a filing later than the formation date.

Outputs -> results/PEG_TEST_20260805/
"""
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bt_pit_quant as B                                              # noqa: E402

OUT = os.path.join(HERE, "results", "PEG_TEST_20260805")
os.makedirs(OUT, exist_ok=True)

NDEC = 10
FORMATIONS = ["2023-03-31", "2023-09-30", "2024-03-31", "2024-09-30", "2025-03-31"]
W3 = B.W3


def trim(x, p=0.05):
    a = np.sort(np.asarray(pd.Series(x).dropna(), dtype=float))
    k = int(len(a) * p)
    core = a[k:len(a) - k] if len(a) > 2 * k else a
    return float(core.mean()) if len(core) else np.nan


def raw_inputs(t, fund, mem, sect, pxm):
    """P/E, EPS growth and sales growth at formation, from the same PIT frames the scorer uses."""
    uni = B.members_asof(mem, t)
    px_t = pxm.loc[:t]
    rows = []
    for s in uni:
        g = fund.get(s)
        if g is None or s not in pxm.columns:
            continue
        av = g[g["avail"] <= t]
        if av.empty:
            continue
        y0 = int(av.index.max())
        if y0 not in g.index:
            continue
        r0 = g.loc[y0]
        if isinstance(r0, pd.DataFrame):
            r0 = r0.iloc[-1]
        ps = px_t[s].dropna()
        if len(ps) < 260:
            continue
        p = ps.iloc[-1]

        def gy(y, c):
            return g.loc[y, c] if y in g.index else np.nan

        eps0, eps1, eps3 = r0.get("eps"), gy(y0 - 1, "eps"), gy(y0 - 3, "eps")
        sal0, sal3 = r0.get("sales"), gy(y0 - 3, "sales")
        pe = (p / eps0) if pd.notna(eps0) and eps0 > 0 else np.nan
        # EPS growth: 3y CAGR where both ends are positive, else 1y
        if pd.notna(eps0) and pd.notna(eps3) and eps3 > 0 and eps0 > 0:
            eg = ((eps0 / eps3) ** (1 / 3) - 1) * 100
        elif pd.notna(eps0) and pd.notna(eps1) and eps1 > 0:
            eg = (eps0 / eps1 - 1) * 100
        else:
            eg = np.nan
        sg = (((sal0 / sal3) ** (1 / 3) - 1) * 100
              if pd.notna(sal0) and pd.notna(sal3) and sal3 > 0 else np.nan)
        rows.append(dict(sym=s, pe=pe, eps_growth=eg, sales_growth=sg))
    return pd.DataFrame(rows)


def main():
    print("loading ...")
    fund, mem, sh, sect, pxm, vol, idx = B.load()

    frames = []
    for t_str in FORMATIONS:
        t = pd.Timestamp(t_str)
        sc = B.score_asof(t, fund, mem, sh, sect, pxm, vol)
        if sc is None or sc.empty:
            continue
        ri = raw_inputs(t, fund, mem, sect, pxm)
        sc = sc.merge(ri, on="sym", how="left")

        e0 = B.next_session(pxm, t)
        e1 = pxm.index[pxm.index <= t + pd.DateOffset(months=12)].max()
        f = []
        for s in sc["sym"]:
            a, b = pxm[s].asof(e0), pxm[s].asof(e1)
            f.append(b / a - 1 if pd.notna(a) and pd.notna(b) and a > 0 else np.nan)
        sc["fwd"] = f
        sc = sc.dropna(subset=["fwd"])

        # PEG, with the traps handled and the exclusions counted
        ok = sc["pe"].notna() & (sc["pe"] > 0) & sc["eps_growth"].notna() & (sc["eps_growth"] > 0)
        sc["peg"] = np.where(ok, sc["pe"] / sc["eps_growth"], np.nan)
        ok_s = sc["pe"].notna() & (sc["pe"] > 0) & sc["sales_growth"].notna() & (sc["sales_growth"] > 0)
        sc["peg_sales"] = np.where(ok_s, sc["pe"] / sc["sales_growth"], np.nan)

        sc["formation"] = t_str
        sc["dec"] = pd.qcut(sc["final"].rank(method="first"), NDEC,
                            labels=range(1, NDEC + 1)).astype(int)
        # PEG pillar: low PEG is good, so rank on -PEG, winsorised like every other pillar
        sc["value_peg"] = B.winz_pct(-sc["peg"])
        # swapped composite: same weights, Value replaced by the PEG pillar
        pill = ["quality", "growth", "value_peg", "stage"]
        W = np.array([W3["quality"], W3["growth"], W3["value"], W3["stage"]], float)
        M = sc[pill].astype(float).values
        mask = ~np.isnan(M)
        wsum = (mask * W).sum(1)
        sc["composite_peg"] = np.nansum(np.nan_to_num(M) * W, 1) / np.where(wsum == 0, np.nan, wsum)
        # like-for-like control: the SAME four pillars with the original P/E-based Value
        M2 = sc[["quality", "growth", "value", "stage"]].astype(float).values
        m2 = ~np.isnan(M2)
        w2 = (m2 * W).sum(1)
        sc["composite_pe4"] = np.nansum(np.nan_to_num(M2) * W, 1) / np.where(w2 == 0, np.nan, w2)

        n_ex = int((~ok).sum())
        print(f"  {t_str}: n={len(sc)}  PEG excluded (growth<=0 or no P/E): {n_ex} "
              f"({n_ex/len(sc)*100:.0f}%)")
        frames.append(sc)

    d = pd.concat(frames, ignore_index=True)
    d.to_csv(os.path.join(OUT, "peg_detail.csv"), index=False)
    print(f"\npooled {len(d)} obs, {d['formation'].nunique()} formations")
    print(f"PEG available on {d['peg'].notna().sum()} of {len(d)} "
          f"({d['peg'].notna().mean()*100:.0f}%)")

    # ---- 1. PEG by the EXISTING score decile -------------------------------------
    g = d.groupby("dec", observed=True)
    t1 = pd.DataFrame({
        "n": g.size(),
        "fwd_trim5": g["fwd"].apply(lambda x: trim(x) * 100).round(1),
        "value_pillar": g["value"].mean().round(1),
        "pe_med": g["pe"].median().round(1),
        "eps_gr_med": g["eps_growth"].median().round(1),
        "peg_med": g["peg"].median().round(2),
        "peg_lt1_pct": (g["peg"].apply(lambda x: (x < 1).mean()) * 100).round(0),
    })
    print("\n=== 1. PEG profile of the EXISTING deciles ===")
    print(t1.to_string())
    t1.to_csv(os.path.join(OUT, "peg_by_existing_decile.csv"))

    # ---- 2. rank on PEG alone ----------------------------------------------------
    dp = d.dropna(subset=["peg"]).copy()
    dp["peg_dec"] = pd.qcut(dp["peg"].rank(method="first"), NDEC, labels=range(1, NDEC + 1)).astype(int)
    gp = dp.groupby("peg_dec", observed=True)
    t2 = pd.DataFrame({"n": gp.size(),
                       "peg_med": gp["peg"].median().round(2),
                       "fwd_trim5": gp["fwd"].apply(lambda x: trim(x) * 100).round(1)})
    print("\n=== 2. deciles ranked on PEG alone (1 = cheapest PEG) ===")
    print(t2.to_string())
    t2.to_csv(os.path.join(OUT, "deciles_by_peg.csv"))

    # ---- 3. swapped composite vs like-for-like control ---------------------------
    print("\n=== 3. Value pillar: P/E versus PEG, same weights, same four pillars ===")
    res = {}
    for name, col in (("P/E-based (control)", "composite_pe4"), ("PEG-based", "composite_peg")):
        sub = d.dropna(subset=[col]).copy()
        sub["dd"] = pd.qcut(sub[col].rank(method="first"), NDEC,
                            labels=range(1, NDEC + 1)).astype(int)
        gg = sub.groupby("dd", observed=True)["fwd"]
        tr = (gg.apply(lambda x: trim(x) * 100)).round(1)
        ic = sub[[col, "fwd"]].corr(method="spearman").iloc[0, 1]
        spread = tr.loc[NDEC] - tr.loc[1]
        mono = bool((tr.diff().dropna() > 0).all())
        # how deep is the mid-decile dip: mean of D4-7 against the mean of the flanks
        dip = tr.loc[4:7].mean() - (tr.loc[2:3].mean() + tr.loc[8:10].mean()) / 2
        res[name] = dict(n=int(len(sub)), spread=round(float(spread), 2),
                         ic=round(float(ic), 4), monotonic=mono, mid_dip_pp=round(float(dip), 2))
        print(f"\n  {name}: n={len(sub)}")
        print("   " + tr.to_string().replace("\n", "\n   "))
        print(f"    D10-D1 = {spread:+.2f}pp   IC = {ic:+.4f}   monotonic = {mono}   "
              f"mid-decile dip = {dip:+.2f}pp")

    print("\n=== VERDICT ===")
    a, b = res["P/E-based (control)"], res["PEG-based"]
    print(f"  spread   : P/E {a['spread']:+.2f}pp   ->   PEG {b['spread']:+.2f}pp   "
          f"({b['spread']-a['spread']:+.2f}pp)")
    print(f"  IC       : P/E {a['ic']:+.4f}   ->   PEG {b['ic']:+.4f}")
    print(f"  mid dip  : P/E {a['mid_dip_pp']:+.2f}pp  ->   PEG {b['mid_dip_pp']:+.2f}pp   "
          f"(less negative = flatter, U-shape reduced)")
    pd.DataFrame(res).T.to_csv(os.path.join(OUT, "verdict.csv"))


if __name__ == "__main__":
    main()
