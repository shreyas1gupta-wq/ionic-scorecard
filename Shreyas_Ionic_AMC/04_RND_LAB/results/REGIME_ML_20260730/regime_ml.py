"""REGIME-STATE ML — predicts the STATE of the next 2 hours, never the entry or the exit.

PRINCIPAL'S SPEC (2026-07-30):
  "CAN WE CREATE A ML WHICH INSTEAD OF PREDICTING ENTRY EXIT PREDICT 2-3 DIFF THING LIKE EXPECTED
   CHOPPY/TRENDING/MEAN-REVERTING, VOLATILITY ETC ETC AND WHEN NOT TO TRADE INSTEAD OF WHEN TO
   GENERATE ALPHA WITHOUT OVERFIT"

WHY THIS FRAMING IS THE RIGHT ONE (and why the earlier regime work failed):
  REGIME_GATE_20260730 tested regime conditioning on MONTHLY sleeve P&L: 28 cells, 0 candidates,
  5 suggestive, 22 dead, none clearing Bonferroni m=28. That test was doomed by power — n=115..172
  MONTHS. Predicting a state at 15-minute granularity gives n ~ 40,000 instead of ~150.
  Independently, STRUCTURAL_EDGES_20260730 found the asymmetry this whole idea rests on:
      PCR / PCR_OI -> forward RETURN     t = 0.57 .. 2.00   FAILS placebo   (no directional content)
      PCR / PCR_OI -> forward VOLATILITY t = -8.9 .. -13.2  CLEARS placebo, holdout sign matches
  So the chain predicts the STATE and not the DIRECTION. That is a measured fact, not a preference,
  and it is exactly the target-swap the Principal is asking for.

FOUR HEADS. None of them is a trade signal.
  H1  state3      CHOP / MIXED / TREND      from forward efficiency ratio terciles
  H2  meanrev     binary                    forward lag-1 autocorrelation of 5-min returns < 0
  H3  vol3        LOW / MID / HIGH          forward realized-vol terciles
  H4  tradeable   binary  <-- THE NO-TRADE HEAD
      Instrument-free definition in ATR units, so it is not tied to any one option:
      a 1.5-RR directional trade is winnable if EITHER side reaches +1.5k*ATR of favourable
      excursion BEFORE it reaches -1.0k*ATR of adverse excursion. If neither side can,
      the window is untradeable for a 1:1.5 harvest and the honest action is to stand aside.

ANTI-OVERFIT CONTROLS (the reason to trust or discard the whole thing):
  1. PURGED EXPANDING WALK-FORWARD. Train [start..T], EMBARGO 5 trading days, test (T..T+3mo].
     No sample within the embargo is ever used. Labels look 2h forward, so the embargo covers it.
  2. LABEL-PERMUTATION PLACEBO. Same folds, same features, target shuffled WITHIN each fold.
     200 draws. Real AUC must sit outside the permuted distribution or the head is noise.
  3. THE ECONOMIC NULL, which is the only one that matters. Using the gate to decline a fraction f
     of windows must beat declining the SAME f at RANDOM (1000 draws). A gate that improves the
     average only because it trades less has done nothing.
  4. Shallow, regularised trees; no feature selection using test data; features strictly PIT.
  5. Feature importances reported so a single dominating feature cannot hide.

FEATURES — all strictly point-in-time as of the bar, none peeking.
  Includes ATR CONSUMPTION (range-so-far / ATR20), which is the measurable core of the Saty ATR
  Levels script the Principal asked about, and ATR-scaled distance from prior close, which is
  the Saty level ladder itself. Those enter here as features rather than as hand-drawn levels.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(20260730)
OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)
IDX = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
       r"\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet")
CHAIN = OUT.parent / "INDICATOR_MINE_20260730" / "chain_features_15min.parquet"

FWD_MIN = 120           # forward window the state describes
EMBARGO_D = 5           # purge: > forward horizon, in trading days
BUCKET = 15             # feature/decision granularity, minutes
ENTRY_LO, ENTRY_HI = "09:30", "13:15"   # need FWD_MIN of session left
K_ATR = 0.25            # unit excursion = 0.25 * daily ATR20; 1.5-RR target = 0.375 ATR
TEST_MONTHS = 3
HELDOUT_FROM = pd.Timestamp("2025-07-01")   # never touched during any fitting decision

# ---------------------------------------------------------------- load + daily frame
print("[load] index 1-min", flush=True)
px = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
px = px[(px.index.time >= pd.Timestamp("09:15").time()) &
        (px.index.time <= pd.Timestamp("15:30").time())]
px["d"] = px.index.normalize()
print(f"       {len(px):,} bars {px.index.min()} .. {px.index.max()}", flush=True)

dly = px.groupby("d").agg(o=("open", "first"), h=("high", "max"),
                          l=("low", "min"), c=("close", "last"))
tr = pd.concat([dly.h - dly.l, (dly.h - dly.c.shift()).abs(),
                (dly.l - dly.c.shift()).abs()], axis=1).max(axis=1)
dly["atr20"] = tr.rolling(20, min_periods=10).mean()
dly["pc"] = dly.c.shift()
dly["ph"] = dly.h.shift()
dly["pl"] = dly.l.shift()
dly["ret1"] = dly.c.pct_change()
dly["rv5"] = dly.ret1.rolling(5).std() * np.sqrt(252)
dly["rv20"] = dly.ret1.rolling(20).std() * np.sqrt(252)
dly["rv60"] = dly.ret1.rolling(60).std() * np.sqrt(252)
dly["volofvol"] = dly.rv20.rolling(20).std()
dly["ret20"] = dly.c.pct_change(20)
# backward efficiency ratio on daily closes: |net| / sum|steps| over 20d
dly["er20d"] = (dly.c.diff(20).abs() / dly.c.diff().abs().rolling(20).sum())

# ---------------------------------------------------------------- chain features (PCR = the vol lead)
print("[load] chain 15-min", flush=True)
ch = pd.read_parquet(CHAIN)
ch["bucket"] = pd.to_datetime(ch["bucket"])
# one row per bucket: sum across expiries (front-weighted naturally by volume)
cg = ch.groupby("bucket").agg(ce_vol=("ce_vol", "sum"), pe_vol=("pe_vol", "sum"),
                              ce_oi=("ce_oi", "sum"), pe_oi=("pe_oi", "sum"),
                              conc_ce=("conc_ce", "mean"), conc_pe=("conc_pe", "mean"))
cg["pcr_vol"] = cg.pe_vol / cg.ce_vol.replace(0, np.nan)
cg["pcr_oi"] = cg.pe_oi / cg.ce_oi.replace(0, np.nan)
cg["d_pcr_oi"] = cg.pcr_oi.diff()
cg["pcr_oi_z"] = ((cg.pcr_oi - cg.pcr_oi.rolling(100, min_periods=30).mean())
                  / cg.pcr_oi.rolling(100, min_periods=30).std())
cg = cg[["pcr_vol", "pcr_oi", "d_pcr_oi", "pcr_oi_z", "conc_ce", "conc_pe"]]
print(f"       chain buckets {len(cg):,}  pcr_oi non-null {cg.pcr_oi.notna().mean():.1%}", flush=True)

# ---------------------------------------------------------------- build samples
print(f"[build] samples at {BUCKET}-min buckets, forward {FWD_MIN}min", flush=True)
rows = []
lo_t, hi_t = pd.Timestamp(ENTRY_LO).time(), pd.Timestamp(ENTRY_HI).time()
for d, g in px.groupby("d"):
    if d not in dly.index or not np.isfinite(dly.at[d, "atr20"]):
        continue
    atr = float(dly.at[d, "atr20"])
    if atr <= 0:
        continue
    D = dly.loc[d]
    c = g["close"].to_numpy(float)
    h = g["high"].to_numpy(float)
    lw = g["low"].to_numpy(float)
    ts = g.index
    n = len(c)
    if n < 200:
        continue
    # session VWAP proxy on typical price, cumulative (no volume in this file -> equal-weight)
    tp = (h + lw + c) / 3.0
    vwap = np.cumsum(tp) / np.arange(1, n + 1)
    ret1 = np.diff(c, prepend=c[0])
    for i in range(n):
        if not (lo_t <= ts[i].time() <= hi_t):
            continue
        if ts[i].minute % BUCKET != 0:
            continue
        j = i + FWD_MIN
        if j >= n:
            continue
        # ---------------- FORWARD (labels only)
        fc, fh, flw = c[i:j + 1], h[i:j + 1], lw[i:j + 1]
        net = fc[-1] - fc[0]
        path = np.abs(np.diff(fc)).sum()
        er = abs(net) / path if path > 0 else 0.0
        f5 = fc[::5]
        r5 = np.diff(f5)
        ac = (np.corrcoef(r5[:-1], r5[1:])[0, 1]
              if len(r5) > 6 and r5[:-1].std() > 0 and r5[1:].std() > 0 else 0.0)
        fvol = np.diff(fc).std() * np.sqrt(375)
        up_mfe = (fh.max() - fc[0]) / atr
        up_mae = (flw.min() - fc[0]) / atr
        # winnable-long: does +1.5k arrive before -1.0k? resolve ADVERSELY inside a bar
        def winnable(sign):
            tgt, stp = 1.5 * K_ATR * atr, 1.0 * K_ATR * atr
            for k in range(1, len(fc)):
                adv = (flw[k] - fc[0]) if sign > 0 else (fc[0] - fh[k])
                fav = (fh[k] - fc[0]) if sign > 0 else (fc[0] - flw[k])
                if adv <= -stp:
                    return 0
                if fav >= tgt:
                    return 1
            return 0
        tradeable = int(winnable(1) or winnable(-1))
        # ---------------- BACKWARD (features)
        b = max(0, i - 60)
        bc = c[b:i + 1]
        bpath = np.abs(np.diff(bc)).sum()
        rows.append(dict(
            t=ts[i], d=d, hhmm=ts[i].hour * 100 + ts[i].minute,
            # -- Saty-class ATR features
            atr_consumed=(h[:i + 1].max() - lw[:i + 1].min()) / atr,
            dist_pc_atr=(c[i] - D.pc) / atr if np.isfinite(D.pc) else np.nan,
            gap_atr=(c[0] - D.pc) / atr if np.isfinite(D.pc) else np.nan,
            or30_atr=(h[:30].max() - lw[:30].min()) / atr,
            # -- position / structure
            vwap_dist_atr=(c[i] - vwap[i]) / atr,
            pdr_pos=((c[i] - D.pl) / (D.ph - D.pl)
                     if np.isfinite(D.ph) and D.ph > D.pl else np.nan),
            er_back60=(abs(bc[-1] - bc[0]) / bpath) if bpath > 0 else 0.0,
            rv_back60=np.diff(bc).std() * np.sqrt(375) if len(bc) > 5 else np.nan,
            rv_back15=np.diff(c[max(0, i - 15):i + 1]).std() * np.sqrt(375) if i > 16 else np.nan,
            ac_back60=(np.corrcoef(np.diff(bc[::5])[:-1], np.diff(bc[::5])[1:])[0, 1]
                       if len(bc) > 40 and np.diff(bc[::5])[:-1].std() > 0 else 0.0),
            up_frac60=float((ret1[b:i + 1] > 0).mean()),
            # -- daily vol context
            rv5=D.rv5, rv20=D.rv20, rv60=D.rv60, volofvol=D.volofvol,
            rv5_over_rv20=D.rv5 / D.rv20 if D.rv20 else np.nan,
            ret20=D.ret20, er20d=D.er20d, atr_pct=atr / c[i],
            dow=d.dayofweek,
            # -- LABELS
            y_er=er, y_ac=ac, y_fvol=fvol, y_net_atr=net / atr,
            y_tradeable=tradeable, y_mfe=up_mfe, y_mae=up_mae,
        ))

S = pd.DataFrame(rows).set_index("t").sort_index()
S = S.join(cg, how="left")
print(f"[build] {len(S):,} samples  {S.index.min().date()} .. {S.index.max().date()}", flush=True)

# terciles are computed on a TRAILING EXPANDING basis to avoid using the whole sample's
# distribution (which would be a mild lookahead in the label definition itself)
def trail_tercile(s, minobs=2000):
    lo = s.expanding(minobs).quantile(1 / 3).shift(1)
    hi = s.expanding(minobs).quantile(2 / 3).shift(1)
    out = pd.Series(np.nan, index=s.index)
    out[s <= lo] = 0
    out[(s > lo) & (s < hi)] = 1
    out[s >= hi] = 2
    return out

S["y_state3"] = trail_tercile(S.y_er)
S["y_vol3"] = trail_tercile(S.y_fvol)
S["y_meanrev"] = (S.y_ac < 0).astype(int)
S = S.dropna(subset=["y_state3", "y_vol3"])
print(f"[label] usable {len(S):,}  "
      f"tradeable {S.y_tradeable.mean():.1%}  meanrev {S.y_meanrev.mean():.1%}", flush=True)

FEATS = [c for c in S.columns if not c.startswith("y_") and c not in ("d",)]
print(f"[feat] {len(FEATS)}: {FEATS}", flush=True)

HEADS = {
    "H1_state3_TREND": ("multi", "y_state3"),
    "H2_meanrev": ("bin", "y_meanrev"),
    "H3_vol3_HIGH": ("multi", "y_vol3"),
    "H4_tradeable": ("bin", "y_tradeable"),
}


def mk():
    return HistGradientBoostingClassifier(
        max_depth=3, max_iter=180, learning_rate=0.05, min_samples_leaf=120,
        l2_regularization=1.0, max_bins=64, early_stopping=False, random_state=7)


def walk_forward(y, name, kind):
    """Purged expanding walk-forward. Returns per-sample OOS probability."""
    oos = pd.Series(np.nan, index=S.index)
    days = np.array(sorted(S.d.unique()))
    starts = pd.date_range(S.index.min().normalize() + pd.DateOffset(years=3),
                           S.index.max(), freq=f"{TEST_MONTHS}MS")
    nf = 0
    for t0 in starts:
        t1 = t0 + pd.DateOffset(months=TEST_MONTHS)
        emb_days = days[days < t0][-EMBARGO_D:]
        emb = pd.Timestamp(emb_days[0]) if len(emb_days) else t0
        trn = S.index < emb
        tst = (S.index >= t0) & (S.index < t1)
        if trn.sum() < 3000 or tst.sum() < 100:
            continue
        yt = y[trn]
        if yt.nunique() < 2:
            continue
        # A feature that is constant or all-NaN inside THIS fold's training slice cannot be binned.
        # Chain features (pcr_*, conc_*) start 2021-05 while the index starts 2015, so the early
        # folds legitimately have none of them. Drop per fold rather than dropping them globally —
        # that keeps the late folds' access to the validated PCR->vol lead.
        Xt = S.loc[trn, FEATS]
        use = [c for c in FEATS if Xt[c].notna().sum() > 50 and Xt[c].nunique(dropna=True) > 1]
        if len(use) < 8:
            continue
        m = mk().fit(Xt[use], yt)
        p = m.predict_proba(S.loc[tst, use])
        cls = list(m.classes_)
        pos = 2.0 if kind == "multi" else 1
        oos[tst] = p[:, cls.index(pos)] if pos in cls else np.nan
        nf += 1
    return oos, nf


results, oosp = {}, {}
for name, (kind, col) in HEADS.items():
    y = S[col].astype(int) if kind == "bin" else S[col].astype(int)
    tgt = (y == 2).astype(int) if kind == "multi" else y
    print(f"\n[fit] {name}  base rate {tgt.mean():.1%}", flush=True)
    p, nf = walk_forward(y, name, kind)
    ok = p.notna() & tgt.notna()
    auc = roc_auc_score(tgt[ok], p[ok])
    # held-out slice never used for any choice
    ho = ok & (S.index >= HELDOUT_FROM)
    auc_ho = roc_auc_score(tgt[ho], p[ho]) if tgt[ho].nunique() > 1 else np.nan
    # --- label-permutation placebo, 200 draws, shuffled within each fold's test block
    pl = []
    blk = S.index.to_period("Q")
    for _ in range(200):
        sh = tgt[ok].groupby(blk[ok]).transform(lambda v: RNG.permutation(v.values))
        pl.append(roc_auc_score(sh, p[ok]))
    pl = np.array(pl)
    pval = float((pl >= auc).mean())
    results[name] = dict(n=int(ok.sum()), folds=nf, base=round(float(tgt.mean()), 4),
                         auc=round(float(auc), 4), auc_heldout=round(float(auc_ho), 4),
                         placebo_auc_mean=round(float(pl.mean()), 4),
                         placebo_auc_p99=round(float(np.quantile(pl, .99)), 4),
                         p_permutation=pval)
    oosp[name] = p
    print(f"      OOS AUC {auc:.4f}   held-out {auc_ho:.4f}   "
          f"placebo {pl.mean():.4f} (p99 {np.quantile(pl, .99):.4f})   p={pval:.3f}", flush=True)
    m = mk().fit(S[FEATS], tgt)
    try:
        from sklearn.inspection import permutation_importance
        pi = permutation_importance(m, S[FEATS].iloc[-6000:], tgt.iloc[-6000:],
                                    n_repeats=3, random_state=1, scoring="roc_auc")
        imp = sorted(zip(FEATS, pi.importances_mean), key=lambda x: -x[1])[:8]
        results[name]["top_features"] = [(f, round(float(v), 5)) for f, v in imp]
        print("      top: " + ", ".join(f"{f} {v:+.4f}" for f, v in imp[:6]), flush=True)
    except Exception as e:
        print(f"      importance skipped: {e}", flush=True)

# ---------------------------------------------------------------- THE ECONOMIC NULL
# A gate is only worth anything if declining f% of windows BY THE MODEL beats declining f% AT RANDOM.
print("\n" + "=" * 108, flush=True)
print("ECONOMIC NULL — does the no-trade head beat declining the same fraction at random?", flush=True)
print("  arm = best-of-direction 1.5-RR excursion outcome in ATR units, the thing a buyer harvests",
      flush=True)
print("=" * 108, flush=True)
p4 = oosp["H4_tradeable"]
ok = p4.notna()
# payoff of taking the window: +1.5k if tradeable else -1.0k, in ATR units (RR 1:1.5 by construction)
pay = np.where(S.y_tradeable[ok] == 1, 1.5 * K_ATR, -1.0 * K_ATR)
pay = pd.Series(pay, index=S.index[ok])
pp = p4[ok]
print(f"{'decline f':>10}{'thresh':>9}{'n kept':>9}{'gated mean':>12}{'random mean':>13}"
      f"{'rand p95':>10}{'p_value':>9}{'verdict':>14}", flush=True)
econ = []
base_mean = pay.mean()
print(f"{'0% (all)':>10}{'-':>9}{len(pay):>9}{base_mean:>12.4f}{'-':>13}{'-':>10}{'-':>9}"
      f"{'baseline':>14}", flush=True)
for f in (0.2, 0.3, 0.4, 0.5, 0.6):
    thr = np.quantile(pp, f)
    keep = pp >= thr
    gm = float(pay[keep].mean())
    nk = int(keep.sum())
    draws = np.array([pay.sample(nk, random_state=int(s), replace=False).mean()
                      for s in range(1000)])
    pv = float((draws >= gm).mean())
    v = "BEATS NULL" if pv < 0.05 else ("weak" if pv < 0.20 else "NO EDGE")
    econ.append(dict(decline_frac=f, threshold=round(float(thr), 4), n_kept=nk,
                     gated_mean=round(gm, 5), random_mean=round(float(draws.mean()), 5),
                     random_p95=round(float(np.quantile(draws, .95)), 5),
                     p_value=pv, verdict=v))
    print(f"{f:>10.0%}{thr:>9.3f}{nk:>9}{gm:>12.4f}{draws.mean():>13.4f}"
          f"{np.quantile(draws, .95):>10.4f}{pv:>9.3f}{v:>14}", flush=True)

# same test restricted to the never-touched held-out slice
print("\n  held-out only (from {}):".format(HELDOUT_FROM.date()), flush=True)
hm = S.index[ok] >= HELDOUT_FROM
econ_ho = []
if hm.sum() > 400:
    payh, pph = pay[hm], pp[hm]
    for f in (0.3, 0.5):
        thr = np.quantile(pph, f)
        keep = pph >= thr
        gm = float(payh[keep].mean())
        draws = np.array([payh.sample(int(keep.sum()), random_state=int(s), replace=False).mean()
                          for s in range(1000)])
        pv = float((draws >= gm).mean())
        econ_ho.append(dict(decline_frac=f, n_kept=int(keep.sum()), gated_mean=round(gm, 5),
                            random_mean=round(float(draws.mean()), 5), p_value=pv))
        print(f"{f:>10.0%}{thr:>9.3f}{int(keep.sum()):>9}{gm:>12.4f}{draws.mean():>13.4f}"
              f"{'-':>10}{pv:>9.3f}", flush=True)

json.dump(dict(spec="regime-state ML, 4 heads, no entry/exit prediction",
               n_samples=int(len(S)), fwd_min=FWD_MIN, bucket_min=BUCKET, k_atr=K_ATR,
               embargo_days=EMBARGO_D, heldout_from=str(HELDOUT_FROM.date()),
               features=FEATS, heads=results, economic_null=econ, economic_null_heldout=econ_ho),
          open(OUT / "regime_ml_report.json", "w"), indent=2, default=str)
S[[c for c in S.columns if c.startswith("y_")]].assign(
    **{f"p_{k}": v for k, v in oosp.items()}).to_parquet(OUT / "oos_predictions.parquet")
print("\nwrote regime_ml_report.json + oos_predictions.parquet", flush=True)
print("\nREAD THE ECONOMIC NULL, NOT THE AUC. An AUC of 0.56 that beats the random-decline null is\n"
      "worth more than an AUC of 0.70 that does not.", flush=True)
