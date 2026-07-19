"""
STOCK_SCORECARD_750 — Gate-3 cheap-test V2 (CURRENT v6.3 methodology, decile + IC).
Owner: Arjun Rao (Head of Quant). Date: 2026-07-19.

WHAT THIS IS: a deeper, PIT-safe falsification of the CURRENT frozen scoring engine
(FROZEN_METHODOLOGY.md v6.3) — recomputes the dual-horizon composite score at past
formation dates and asks: does it have real, non-placebo, non-regime-concentrated
cross-sectional forward-return power? Do the 3Y-weighted and 1Y-weighted composites
carry DISTINCT information? Extends the 2026-07-17 2-pillar quintile cheap-test.

FIDELITY: all pillar formulas reverse-validated against results/reference_full_with_portfolio.csv
(the frozen engine's current-date output). Pillars computed PIT here:
  Quality, Growth, Value(4-component), Stage-mechanical, Sector&Macro-mechanical, Accumulation.
DROPPED: Ownership Flow (FII/DII quarterly history absent in local data) -> base weights
renormalized over the 6 available pillars per horizon (recon corr vs CSV composite_3y = 0.963).
SKIPPED historically: regime weight-tilt + Sector&Macro regime_fit_adj (cannot PIT-reconstruct
the current-regime call without lookahead). Base weights = the spec's pre-regime-tilt table.

LANDMINES handled: PIT fundamentals (available_date<=formation, G.assert_pit); PE numerator =
Close (split-adj) / forward return = Adj Close (total-return); overlapping 12M -> Newey-West;
survivor-biased CURRENT membership BASELINE (placebo shuffles within same set -> decision robust,
absolute returns NOT tradeable). Analyst forward-growth red flag EXCLUDED (out of scope: no PIT
analyst estimates). shares held constant per symbol (dilution adds noise, conservative).
"""
import os, sys, json, glob
os.environ["PYTHONIOENCODING"] = "utf-8"; os.environ["PYTHONUNBUFFERED"] = "1"
import numpy as np, pandas as pd
from scipy.stats import spearmanr

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
AR   = os.path.join(ROOT, "ALPHA_RANKER", "data")
SC   = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750")
LIB  = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "lib")
OUT  = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "results", "STOCK_SCORECARD_750_CHEAPTEST_V2_20260719")
sys.path.insert(0, LIB)
import guards as G

SEED = 20260719
N_PLACEBO = 200
NQ = 10                       # DECILES
rng = np.random.default_rng(SEED)

# base weights (spec pre-regime-tilt), Ownership Flow dropped + renormalized per horizon
W3_RAW = dict(quality=.20, growth=.20, value=.18, stage=.14, sector_macro=.11, accumulation=.08)
W1_RAW = dict(quality=.16, growth=.16, value=.16, stage=.26, sector_macro=.13, accumulation=.05)
def _renorm(w):
    s = sum(w.values()); return {k: v / s for k, v in w.items()}
W3, W1 = _renorm(W3_RAW), _renorm(W1_RAW)

FIN_SECTORS = {"financial services"}    # D/E gate + D/E red-flag exempt (leverage = business model)
NEEDED = ["net profit","equity capital","reserves","borrowings","borrowing","operating profit",
          "eps in rs","sales","revenue","interest","free cash flow"]

# --------------------------------------------------------------------------- #
def winsor(s, lo=0.02, hi=0.98):
    s = pd.Series(s, dtype=float)
    ql, qh = s.quantile(lo), s.quantile(hi)
    return s.clip(ql, qh)

def pctile_sector_neutral(df, col, group_col="sector_norm", ascending=True, min_group=5):
    x = df[col] if ascending else -df[col]
    x = winsor(x)
    grp_n = df.groupby(group_col)[col].transform("count")
    within = x.groupby(df[group_col]).rank(pct=True) * 100
    univ = x.rank(pct=True) * 100
    return within.where(grp_n >= min_group, univ)

def pctile_universe(series, ascending=True):
    x = winsor(series if ascending else -pd.Series(series, dtype=float))
    return x.rank(pct=True) * 100

def pctile_sector_tier(df, col, ascending=True, min_group=5):
    x = winsor(df[col] if ascending else -df[col])
    st = df["sector_norm"].astype(str) + "|" + df["mcap_tercile"].astype(str)
    n_st = x.groupby(st).transform("count")
    r_st = x.groupby(st).rank(pct=True) * 100
    n_s = x.groupby(df["sector_norm"]).transform("count")
    r_s = x.groupby(df["sector_norm"]).rank(pct=True) * 100
    r_u = x.rank(pct=True) * 100
    out = r_st.where(n_st >= min_group, r_s.where(n_s >= min_group, r_u))
    return out

def newey_west_t(x, lag):
    x = np.asarray(x, float); n = len(x)
    if n < 3: return float("nan")
    mu = x.mean(); e = x - mu; var = (e @ e) / n
    for l in range(1, min(lag, n - 1) + 1):
        w = 1 - l / (lag + 1); var += 2 * w * (e[l:] @ e[:-l]) / n
    se = np.sqrt(var / n)
    return float(mu / se) if se > 0 else float("nan")

# --------------------------------------------------------------------------- #
print("Loading reference universe (332) + shares + prices + fundamentals ...", flush=True)
ref = pd.read_csv(os.path.join(SC, "results", "reference_full_with_portfolio.csv"))
ref["sector_norm"] = ref["sector_norm"].astype(str).str.strip().str.lower()
UNI = ref[["symbol","sector_norm","cyclicality_tag","market_cap_approx"]].drop_duplicates("symbol").copy()
symbols = UNI["symbol"].tolist()

PX = {}
for s in symbols:
    p = os.path.join(AR, "prices", s + ".parquet")
    if not os.path.exists(p): continue
    d = pd.read_parquet(p, columns=["Close","Adj Close","Volume"]).sort_index()
    d = d[~d.index.duplicated(keep="last")]
    d.columns = ["close","adj","vol"]
    PX[s] = d
SHARES = {}
for s in symbols:
    mc = UNI.loc[UNI.symbol == s, "market_cap_approx"].iloc[0]
    if s in PX and len(PX[s]) and mc == mc and mc > 0:
        SHARES[s] = float(mc) * 1e7 / float(PX[s]["close"].iloc[-1])

fund = pd.read_parquet(os.path.join(AR, "fundamentals", "MASTER_fundamentals_pit.parquet"),
                       columns=["nse_symbol","fiscal_year","metric_norm","value","available_date"])
fund = fund.rename(columns={"nse_symbol":"symbol"})
fund = fund[fund["symbol"].isin(symbols) & fund["metric_norm"].isin(NEEDED)].copy()
fund["available_date"] = pd.to_datetime(fund["available_date"])
SECMAP = dict(zip(UNI.symbol, UNI.sector_norm)); CYCMAP = dict(zip(UNI.symbol, UNI.cyclicality_tag))
print(f"  universe={len(UNI)}  priced={len(PX)}  shares={len(SHARES)}  fund_rows={len(fund)}", flush=True)

# --------------------------------------------------------------------------- #
def px_asof(s, dt, col, tol_days):
    if s not in PX: return np.nan
    ser = PX[s][col]; sub = ser[ser.index <= dt]
    if len(sub) == 0 or (dt - sub.index[-1]).days > tol_days: return np.nan
    return float(sub.iloc[-1])

def ret_over(s, dt, months):
    a = px_asof(s, dt - pd.DateOffset(months=months), "close", 20); b = px_asof(s, dt, "close", 10)
    if a and b and a > 0: return b / a - 1.0
    return np.nan

def tech_block(s, dt):
    if s not in PX: return None
    d = PX[s][PX[s].index <= dt]
    if len(d) < 60: return None
    close = d["close"]; vol = d["vol"]; out = {}
    for m, lbl in [(3,"3m"),(6,"6m"),(12,"12m"),(24,"24m")]:
        out["ret_" + lbl] = ret_over(s, dt, m)
    out["above_50"]  = float(close.iloc[-1]) > float(close.tail(50).mean())
    out["above_200"] = float(close.iloc[-1]) > float(close.tail(min(200,len(close))).mean())
    diff = close.diff().tail(15); up = diff.clip(lower=0).mean(); dn = (-diff.clip(upper=0)).mean()
    out["rsi14"] = 100 - 100/(1+up/dn) if dn > 0 else 100.0
    sign = np.sign(close.diff().fillna(0.0)); obv = (sign * vol).cumsum()
    def slope(n):
        y = obv.tail(n).values.astype(float)
        if len(y) < 5: return np.nan
        x = np.arange(len(y)); sc = np.mean(np.abs(y)) or 1.0
        return float(np.polyfit(x, y/sc, 1)[0])
    out["obv_long"]  = slope(min(180,len(obv))); out["obv_short"] = slope(min(60,len(obv)))
    out["turnover_60d"] = float((close.tail(60) * vol.tail(60)).median())
    return out

# --------------------------------------------------------------------------- #
def build_panel(form_date, fwd_months_list=(12,36)):
    fd = pd.Timestamp(form_date)
    pit = fund[fund["available_date"] <= fd]
    if pit.empty: return pd.DataFrame()
    G.assert_pit(pit.assign(action_date=fd), avail_col="available_date", act_col="action_date")
    rows = []
    for s in symbols:
        fs = pit[pit["symbol"] == s]
        if fs.empty or s not in SHARES: continue
        piv = fs.pivot_table(index="fiscal_year", columns="metric_norm", values="value", aggfunc="last").sort_index()
        for c in NEEDED:
            if c not in piv.columns: piv[c] = np.nan
        # --- Quality: 5yr trailing MEAN of annual ROE/ROCE ratios (cyclicality-aware lookback proxy;
        #     lifts fidelity vs reference quality_score 0.75->0.89 vs latest-year) ---
        equity_y = piv["equity capital"] + piv["reserves"]; equity_y = equity_y.where(equity_y > 0)
        bor_y = piv["borrowings"].fillna(piv["borrowing"])
        ce_y = (equity_y + bor_y.fillna(0)); ce_y = ce_y.where(ce_y > 0)
        roe  = float((piv["net profit"]/equity_y).tail(5).mean())
        roce = float((piv["operating profit"]/ce_y).tail(5).mean())
        # --- latest-year scalars for valuation, gates, growth ---
        last = piv.iloc[-1]; gl = lambda k: float(last[k]) if pd.notna(last[k]) else np.nan
        equity = float(equity_y.iloc[-1]) if pd.notna(equity_y.iloc[-1]) else np.nan
        borrow = gl("borrowings"); borrow = borrow if pd.notna(borrow) else gl("borrowing")
        opp, intr, eps = gl("operating profit"), gl("interest"), gl("eps in rs")
        de   = borrow/equity if (pd.notna(borrow) and pd.notna(equity)) else np.nan
        intcov = opp/intr if (pd.notna(opp) and pd.notna(intr) and intr > 0) else np.nan
        close_fd = px_asof(s, fd, "close", 10)
        mcap = SHARES[s]*close_fd if pd.notna(close_fd) else np.nan
        mcap_cr = mcap/1e7 if pd.notna(mcap) else np.nan
        pe = close_fd/eps if (pd.notna(close_fd) and pd.notna(eps) and eps > 0) else np.nan
        pb = mcap_cr/equity if (pd.notna(mcap_cr) and pd.notna(equity) and equity > 0) else np.nan
        fcf_ser = piv["free cash flow"].dropna()
        avg_fcf = float(fcf_ser.tail(5).mean()) if len(fcf_ser) else np.nan
        fcf_yield = avg_fcf/mcap_cr if (pd.notna(avg_fcf) and pd.notna(mcap_cr) and mcap_cr>0) else np.nan
        sv = piv["sales"].dropna()
        if len(sv) < 2: sv = piv["revenue"].dropna()
        cagr3 = g1 = np.nan
        if len(sv) >= 2:
            vals = sv.astype(float).values
            if vals[-2] and vals[-2] > 0: g1 = vals[-1]/vals[-2]-1
            if len(vals) >= 4 and vals[-4] and vals[-4] > 0: cagr3 = (vals[-1]/vals[-4])**(1/3)-1
        tb = tech_block(s, fd)
        if tb is None: continue
        rows.append(dict(symbol=s, sector_norm=SECMAP[s], cyc=CYCMAP.get(s),
            roe=roe, roce=roce, de=de, intcov=intcov, pe=pe, pb=pb, fcf_yield=fcf_yield,
            mcap=mcap, cagr3=cagr3, g1=g1, close_fd=close_fd, **tb))
    P = pd.DataFrame(rows)
    if len(P) < NQ*3: return pd.DataFrame()
    P["mcap_tercile"] = pd.qcut(P["mcap"].rank(method="first"), 3, labels=["Small","Mid","Large"])
    P["roe_pct"]  = pctile_sector_neutral(P, "roe"); P["roce_pct"] = pctile_sector_neutral(P, "roce")
    P["quality"]  = P[["roe_pct","roce_pct"]].mean(axis=1)
    P["growth_3y"] = pctile_universe(P["cagr3"]); P["growth_1y"] = pctile_universe(P["g1"])
    P["pe_abs"] = pctile_universe(-P["pe"])
    P["pe_st"]  = pctile_sector_tier(P, "pe", ascending=False)
    P["pb_st"]  = pctile_sector_tier(P, "pb", ascending=False)
    P["fcf_st"] = pctile_sector_tier(P, "fcf_yield", ascending=True)
    P["value"] = 0.25*P["pe_abs"] + 0.35*P["pe_st"] + 0.20*P["pb_st"] + 0.20*P["fcf_st"]
    for lbl in ["3m","6m","12m","24m"]:
        P["ret_"+lbl+"_u"] = pctile_universe(P["ret_"+lbl]); P["ret_"+lbl+"_s"] = pctile_sector_neutral(P, "ret_"+lbl)
    m3 = P[["ret_12m_u","ret_24m_u","ret_12m_s"]].mean(axis=1)
    P["stage_3y"] = m3 * np.where(P["above_200"], 1.0, 0.5)
    m1 = P[["ret_3m_u","ret_6m_u","ret_3m_s"]].mean(axis=1)
    rsi_nudge = np.select([P["rsi14"]>70, P["rsi14"]<30], [-2.0, 2.0], 0.0)
    P["stage_1y"] = m1 * np.where(P["above_50"], 1.0, 0.5) + rsi_nudge
    smr12 = P.groupby("sector_norm")["ret_12m"].transform("mean"); smr3 = P.groupby("sector_norm")["ret_3m"].transform("mean")
    P["sector_macro_3y"] = pctile_universe(smr12); P["sector_macro_1y"] = pctile_universe(smr3)
    P["accumulation_3y"] = pctile_universe(P["obv_long"]); P["accumulation_1y"] = pctile_universe(P["obv_short"])
    def comp(w, hz):
        return (w["quality"]*P["quality"].fillna(P["quality"].median())
              + w["growth"]*P[f"growth_{hz}"].fillna(P[f"growth_{hz}"].median())
              + w["value"]*P["value"].fillna(P["value"].median())
              + w["stage"]*P[f"stage_{hz}"].fillna(P[f"stage_{hz}"].median())
              + w["sector_macro"]*P[f"sector_macro_{hz}"]
              + w["accumulation"]*P[f"accumulation_{hz}"])
    P["composite_3y"] = comp(W3, "3y"); P["composite_1y"] = comp(W1, "1y")
    is_fin = P["sector_norm"].isin(FIN_SECTORS)
    de_red = (P["de"] > 2.5) & (~is_fin); de_amber = (P["de"] > 1.5) & (~is_fin)
    bs_red = de_red | (P["intcov"] < 1.5); bs_amber = de_amber | (P["intcov"] < 3)
    P["bs_flag"] = np.where(is_fin, "N/A-financial-sector", np.where(bs_red, "RED", np.where(bs_amber, "AMBER", "GREEN")))
    bar = P["mcap_tercile"].map({"Large":5e7, "Mid":1e7, "Small":2.5e6}).astype(float)
    liq_red = P["turnover_60d"] < bar
    rf = ( (P["intcov"] < 1.5).fillna(False).astype(int)
         + ((P["de"] > 2.5) & (~is_fin)).fillna(False).astype(int)
         + (P["g1"] < 0).fillna(False).astype(int)
         + ((P["cagr3"] - P["g1"]) > 0.15).fillna(False).astype(int) )
    P["redflag_count"] = rf; P["penalty"] = -np.minimum(10, 2.0**rf - 1)
    P["boost"] = np.where((rf == 0) & (P["quality"] > 60) & (P["value"] > 60), 3.0, 0.0)
    for hz in ["3y","1y"]:
        base = P[f"composite_{hz}"] + P["penalty"] + P["boost"]
        red = (P["bs_flag"] == "RED") | liq_red
        adj = np.where(red, np.minimum(base, 40), np.where(P["bs_flag"] == "AMBER", base*0.85, base))
        P[f"final_{hz}_adj"] = np.clip(adj, 0, 100)
    P["combined"] = 0.60*P["final_3y_adj"] + 0.40*P["final_1y_adj"]
    for fm in fwd_months_list:
        sell = fd + pd.DateOffset(months=fm)
        P[f"fwd_{fm}m"] = [ (px_asof(s, sell, "adj", 25) or np.nan) / (px_asof(s, fd, "adj", 10) or np.nan) - 1.0
                            for s in P["symbol"] ]
    P["form_date"] = fd
    return P

# ============================================================================ #
if os.environ.get("SCV2_MODE") == "validate":
    # fidelity check: recompute at a recent date, correlate my pillars vs reference CSV columns
    vd = pd.Timestamp("2026-06-29")
    P = build_panel(vd, fwd_months_list=())
    m = P.merge(ref, on="symbol", suffixes=("_me","_csv"))
    pairs = [("quality","quality_score"),("growth_3y","growth_3y_score"),("growth_1y","growth_1y_score"),
             ("value","value_score"),("pe_abs","pe_abs_pctile"),("pe_st","pe_sector_tier_pctile"),
             ("pb_st","pb_sector_tier_pctile"),("fcf_st","fcf_yield_sector_tier_pctile"),
             ("stage_3y","stage_3y_score"),("stage_1y","stage_1y_score"),
             ("sector_macro_3y","sector_macro_3y_score"),("accumulation_3y","accumulation_3y_score"),
             ("composite_3y_me","composite_3y_csv"),("composite_1y_me","composite_1y_csv"),
             ("final_3y_adj_me","final_3y_adj_csv"),("final_1y_adj_me","final_1y_adj_csv")]
    print(f"\n=== VALIDATION @ {vd.date()}  (n merged={len(m)}) : Spearman(my, CSV) ===")
    for a,b in pairs:
        d = m[[a,b]].dropna()
        if len(d) > 10:
            rho,_ = spearmanr(d[a], d[b]); pear = d[a].corr(d[b])
            print(f"  {a:18s} vs {b:26s} spearman={rho:+.3f}  pearson={pear:+.3f}  n={len(d)}")
    # mcap tercile agreement (both frames carry mcap_tercile -> suffixed)
    tt = m[["mcap_tercile_me","mcap_tercile_csv"]].dropna()
    print(f"  mcap_tercile exact-match: {(tt['mcap_tercile_me'].astype(str).str.lower()==tt['mcap_tercile_csv'].astype(str).str.lower()).mean()*100:.0f}%")
    print(f"  bs_flag N/A-financial: mine={(m['bs_flag_me']=='N/A-financial').sum()}  csv={(m['bs_flag_csv']=='N/A-financial').sum()}")
    sys.exit(0)

form_months = pd.date_range("2021-08-31", "2025-06-30", freq="ME")
print(f"\nPRIMARY: {len(form_months)} monthly formations {form_months[0].date()}..{form_months[-1].date()}", flush=True)

def decile_ladder(scores, rets, nq=NQ):
    r = pd.qcut(pd.Series(scores).rank(method="first"), nq, labels=False)
    df = pd.DataFrame({"q": r, "ret": np.asarray(rets)}); means = df.groupby("q")["ret"].mean()
    lad = [float(means.get(i, np.nan)) for i in range(nq)]
    return lad, lad[-1]-lad[0]

panels = {}; recs = {"3y": [], "1y": [], "combined": []}; ic_rows = []
for fm in form_months:
    P = build_panel(fm, fwd_months_list=(12,36))
    if P.empty: continue
    sub = P.dropna(subset=["fwd_12m","composite_3y","composite_1y"]).copy()
    if len(sub) < NQ*3: continue
    panels[fm] = sub[["final_3y_adj","final_1y_adj","composite_3y","composite_1y","combined",
                       "quality","value","growth_3y","growth_1y","stage_3y","stage_1y",
                       "sector_macro_3y","accumulation_3y","fwd_12m","fwd_36m",
                       "sector_norm","bs_flag","mcap_tercile","symbol"]].reset_index(drop=True)
    med = sub["fwd_12m"].median()
    for key, col in [("3y","final_3y_adj"),("1y","final_1y_adj"),("combined","combined")]:
        lad, spr = decile_ladder(sub[col].values, sub["fwd_12m"].values)
        topq = pd.qcut(sub[col].rank(method="first"), NQ, labels=False) == NQ-1
        hit = float((sub.loc[topq,"fwd_12m"] > med).mean()*100)
        ic, _ = spearmanr(sub[col].values, sub["fwd_12m"].values)
        recs[key].append(dict(form=str(fm.date()), n=int(len(sub)), ladder=lad, spread=float(spr),
                              hit_top_decile=hit, ic=float(ic)))
    rc, _ = spearmanr(sub["composite_3y"], sub["composite_1y"])
    ic3, _ = spearmanr(sub["composite_3y"], sub["fwd_12m"]); ic1, _ = spearmanr(sub["composite_1y"], sub["fwd_12m"])
    icc, _ = spearmanr(0.6*sub["composite_3y"].rank()+0.4*sub["composite_1y"].rank(), sub["fwd_12m"])
    # DECOMP: is any weakness the WINDOW (fundamentals out of favor) or the ADDED pillars?
    q = sub["quality"].fillna(sub["quality"].median()); v = sub["value"].fillna(sub["value"].median())
    ic_qv, _  = spearmanr(0.5*q.rank()+0.5*v.rank(), sub["fwd_12m"])   # pure quality+value (mirrors original 2-pillar)
    ic_qual,_ = spearmanr(q, sub["fwd_12m"]); ic_val,_ = spearmanr(v, sub["fwd_12m"])
    ic_mom3,_ = spearmanr(sub["stage_3y"].fillna(sub["stage_3y"].median()), sub["fwd_12m"])
    ic_rows.append(dict(form=str(fm.date()), rankcorr_3y_1y=float(rc), ic_comp3=float(ic3),
                        ic_comp1=float(ic1), ic_combo=float(icc), ic_qv=float(ic_qv),
                        ic_qual=float(ic_qual), ic_val=float(ic_val), ic_mom3=float(ic_mom3)))
    print(f"  {fm.date()} n={len(sub):3d} IC3={ic3:+.3f} IC1={ic1:+.3f} rc(3y,1y)={rc:.3f} spr3={recs['3y'][-1]['spread']:+.3f}", flush=True)

def agg(key):
    R = recs[key]; ladders = np.array([r["ladder"] for r in R]); spreads = np.array([r["spread"] for r in R])
    ics = np.array([r["ic"] for r in R]); hits = np.array([r["hit_top_decile"] for r in R])
    mean_lad = ladders.mean(axis=0); mono_rho, _ = spearmanr(np.arange(NQ), mean_lad)
    return dict(n_months=len(R), mean_decile_ladder=[float(x) for x in mean_lad],
        mean_spread_D10_D1=float(spreads.mean()), mean_spread_pp=float(spreads.mean()*100),
        months_spread_pos=int((spreads>0).sum()), monotonicity_spearman=float(mono_rho),
        ic_mean=float(ics.mean()), ic_std=float(ics.std(ddof=1)),
        ic_naive_t=float(ics.mean()/(ics.std(ddof=1)/np.sqrt(len(ics)))), ic_nw_t=newey_west_t(ics, 11),
        ic_hit_rate_pos=float((ics>0).mean()*100), hit_top_decile_mean=float(hits.mean()),
        spread_series=[float(x) for x in spreads], ic_series=[float(x) for x in ics])
AGG = {k: agg(k) for k in recs}

def placebo(colkey):
    col = {"3y":"final_3y_adj","1y":"final_1y_adj","combined":"combined"}[colkey]
    real = AGG[colkey]["mean_spread_D10_D1"]; null = np.empty(N_PLACEBO)
    for i in range(N_PLACEBO):
        sp = []
        for fm, pan in panels.items():
            _, s = decile_ladder(rng.permutation(pan[col].values), pan["fwd_12m"].values); sp.append(s)
        null[i] = np.mean(sp)
    return dict(real_spread=real, placebo_pctile=float((null < real).mean()*100),
               placebo_one_sided_p=float((null >= real).mean()), null_mean=float(null.mean()),
               null_sd=float(null.std()), null_p5=float(np.percentile(null,5)), null_p95=float(np.percentile(null,95)))
PLAC = {k: placebo(k) for k in recs}

def regime_split(key):
    R = recs[key]; fmd = pd.to_datetime([r["form"] for r in R]); sp = np.array([r["spread"] for r in R]); ic = np.array([r["ic"] for r in R])
    regimes = {"A_2021-08..2022-05_pre":(fmd>="2021-08-01")&(fmd<="2022-05-31"),
        "B_2022-06..2023-09_meltup":(fmd>="2022-06-01")&(fmd<="2023-09-30"),
        "C_2023-10..2025-06_recent":(fmd>="2023-10-01")&(fmd<="2025-06-30")}
    out = {}
    for nm, mk in regimes.items():
        out[nm] = dict(n=int(mk.sum()), mean_spread=float(sp[mk].mean()), mean_ic=float(ic[mk].mean()), pct_pos=float((sp[mk]>0).mean()*100))
    ex = ~regimes["B_2022-06..2023-09_meltup"]
    out["_ex_meltup_mean_spread"] = float(sp[ex].mean()); out["_ex_meltup_mean_ic"] = float(ic[ex].mean()); out["_ex_meltup_nw_t_ic"] = newey_west_t(ic[ex], 11)
    return out
REG = {k: regime_split(k) for k in recs}

rc_arr = np.array([r["rankcorr_3y_1y"] for r in ic_rows]); ic3_arr = np.array([r["ic_comp3"] for r in ic_rows])
ic1_arr = np.array([r["ic_comp1"] for r in ic_rows]); icc_arr = np.array([r["ic_combo"] for r in ic_rows])
DIST = dict(mean_rankcorr_3y_1y=float(rc_arr.mean()), min_rankcorr=float(rc_arr.min()), max_rankcorr=float(rc_arr.max()),
    ic_comp3_mean=float(ic3_arr.mean()), ic_comp3_nw_t=newey_west_t(ic3_arr,11),
    ic_comp1_mean=float(ic1_arr.mean()), ic_comp1_nw_t=newey_west_t(ic1_arr,11),
    ic_combo_mean=float(icc_arr.mean()), ic_combo_nw_t=newey_west_t(icc_arr,11),
    combo_beats_best_alone=bool(icc_arr.mean() > max(ic3_arr.mean(), ic1_arr.mean())))

# DECOMP: window vs composition — pure quality+value (mirrors original 2-pillar) vs single pillars vs momentum
fmd = pd.to_datetime([r["form"] for r in ic_rows])
meltup = (fmd>="2022-06-01")&(fmd<="2023-09-30"); recent = (fmd>="2023-10-01")&(fmd<="2025-06-30")
def _arr(k): return np.array([r[k] for r in ic_rows])
def _dec(k):
    a = _arr(k)
    return dict(ic_mean=float(a.mean()), ic_nw_t=newey_west_t(a,11),
                ic_meltup_tail=float(a[meltup].mean()), ic_recent=float(a[recent].mean()),
                pct_pos=float((a>0).mean()*100))
DECOMP = {name: _dec(name) for name in ["ic_qv","ic_qual","ic_val","ic_mom3","ic_comp3","ic_comp1"]}

sec = []
for fm, pan in panels.items():
    d = pan.dropna(subset=["fwd_36m"])
    if len(d) < NQ*3: continue
    _, spr = decile_ladder(d["final_3y_adj"].values, d["fwd_36m"].values); ic, _ = spearmanr(d["final_3y_adj"], d["fwd_36m"])
    sec.append(dict(form=str(fm.date()), n=int(len(d)), spread36=float(spr), ic36=float(ic)))
SEC = dict(n=len(sec), mean_spread36=float(np.mean([s["spread36"] for s in sec])) if sec else float("nan"),
           mean_ic36=float(np.mean([s["ic36"] for s in sec])) if sec else float("nan"), rows=sec)

fin_rows = []
for fm, pan in panels.items():
    q = pd.qcut(pan["final_3y_adj"].rank(method="first"), NQ, labels=False); is_fin = pan["sector_norm"].isin(FIN_SECTORS)
    fin_rows.append(dict(form=str(fm.date()), fin_share_universe=float(is_fin.mean()),
        fin_share_top_decile=float(is_fin[q==NQ-1].mean()) if (q==NQ-1).any() else np.nan,
        fin_share_bottom_decile=float(is_fin[q==0].mean()) if (q==0).any() else np.nan,
        fin_fwd_mean=float(pan.loc[is_fin,"fwd_12m"].mean()), nonfin_fwd_mean=float(pan.loc[~is_fin,"fwd_12m"].mean())))
FR = pd.DataFrame(fin_rows)
SECT_EXEMPT = dict(mean_fin_share_universe=float(FR["fin_share_universe"].mean()),
    mean_fin_share_top_decile=float(FR["fin_share_top_decile"].mean()),
    mean_fin_share_bottom_decile=float(FR["fin_share_bottom_decile"].mean()),
    top_over_universe_ratio=float(FR["fin_share_top_decile"].mean()/FR["fin_share_universe"].mean()),
    mean_fin_fwd12=float(FR["fin_fwd_mean"].mean()), mean_nonfin_fwd12=float(FR["nonfin_fwd_mean"].mean()), per_month=fin_rows)

for fm, pan in panels.items():
    pan.to_parquet(os.path.join(OUT, "panels", f"panel_{fm.date()}.parquet"))

metrics = dict(primary_horizon_months=12, n_formation_months=len(panels), n_deciles=NQ,
    final_3y_adj=AGG["3y"], final_1y_adj=AGG["1y"], combined_60_40=AGG["combined"],
    placebo=PLAC, regime_split=REG, distinctness_3y_vs_1y=DIST, secondary_36m_context=SEC,
    sector_exemption_check=SECT_EXEMPT, decomposition_window_vs_composition=DECOMP, ic_distinctness_rows=ic_rows,
    per_month_final_3y=recs["3y"], per_month_final_1y=recs["1y"])
with open(os.path.join(OUT, "metrics.json"), "w") as fh: json.dump(metrics, fh, indent=2)

config = dict(test="STOCK_SCORECARD_750 Gate-3 cheap-test V2 (CURRENT v6.3 methodology, decile+IC)",
    owner="Arjun Rao (quant-head)", date="2026-07-19", seed=SEED, n_placebo=N_PLACEBO, n_deciles=NQ,
    universe="reference_full_with_portfolio.csv (332 names; survivor-biased CURRENT membership; << full 750)",
    pillars_computed=["quality","growth","value_4comp","stage_mechanical","sector_macro_mechanical","accumulation"],
    pillars_dropped=["ownership_flow (no FII/DII PIT history) -> weights renormalized over 6 pillars"],
    regime_tilt="SKIPPED historically (cannot PIT-reconstruct current-regime call); base pre-tilt weights used",
    weights_3y=W3, weights_1y=W1, winsorization="2/98 each raw input within panel before ranking",
    value_blend="0.25 pe_abs(univ)+0.35 pe(sector x tier)+0.20 pb(sector x tier)+0.20 fcf_yield(sector x tier)",
    gates="BS(financial-sector D/E EXEMPT)+liquidity; penalty=-min(10,2^rf-1) [analyst-growth flag EXCLUDED]; boost=+3",
    shares="constant per symbol from current snapshot (mcap*1e7/latest_close); dilution=noise, conservative",
    pe_price="Close (split-adj)", return_price="Adj Close (total-return)", momentum_price="Close",
    formation="month-end 2021-08-31..2025-06-30", fwd_primary=12, fwd_context=36,
    fidelity_recon_corr_vs_reference_csv_composite3y={"all7_base_wts":0.987,"6pillar_no_ownership_renorm":0.963},
    known_limitations=[
        "Universe=CURRENT membership -> survivor-biased baseline; absolute decile returns inflated & NOT tradeable; placebo shuffles within same set so DECISION robust.",
        "Ownership Flow pillar dropped (no PIT FII/DII); composite is a 6/7-pillar proxy (recon corr 0.963).",
        "Regime tilt + regime_fit_adj omitted (would be lookahead); base weights used.",
        "n=332 -> ~33 names/decile: thin buckets; sector x tier value legs cascade to sector/universe constantly at this scale.",
        "Analyst forward-growth red flag & Ionic-Score forward layer OUT OF SCOPE (no PIT analyst estimates).",
        "Gross of costs (Gate-3 predictive read); Gate-4 needs PIT membership + cost/turnover-matched benchmark (D-029)."])
with open(os.path.join(OUT, "config.json"), "w") as fh: json.dump(config, fh, indent=2)

print("\n=== SUMMARY ===")
print(f"months={len(panels)}  final_3y: spread={AGG['3y']['mean_spread_pp']:+.2f}pp mono_rho={AGG['3y']['monotonicity_spearman']:+.2f} IC={AGG['3y']['ic_mean']:+.3f}(nwT={AGG['3y']['ic_nw_t']:.2f}) hit={AGG['3y']['hit_top_decile_mean']:.0f}%")
print(f"           final_1y: spread={AGG['1y']['mean_spread_pp']:+.2f}pp mono_rho={AGG['1y']['monotonicity_spearman']:+.2f} IC={AGG['1y']['ic_mean']:+.3f}(nwT={AGG['1y']['ic_nw_t']:.2f}) hit={AGG['1y']['hit_top_decile_mean']:.0f}%")
print(f"placebo 3y pctile={PLAC['3y']['placebo_pctile']:.1f} (p={PLAC['3y']['placebo_one_sided_p']:.3f})  1y pctile={PLAC['1y']['placebo_pctile']:.1f}")
print(f"distinctness: mean rankcorr(3y,1y)={DIST['mean_rankcorr_3y_1y']:.3f}  IC3={DIST['ic_comp3_mean']:+.3f} IC1={DIST['ic_comp1_mean']:+.3f} ICcombo={DIST['ic_combo_mean']:+.3f} combo_best={DIST['combo_beats_best_alone']}")
print(f"regime 3y: pre={REG['3y']['A_2021-08..2022-05_pre']['mean_spread']:+.3f} meltup={REG['3y']['B_2022-06..2023-09_meltup']['mean_spread']:+.3f} recent={REG['3y']['C_2023-10..2025-06_recent']['mean_spread']:+.3f} ex-meltup={REG['3y']['_ex_meltup_mean_spread']:+.3f}")
print(f"sector-exemption: fin share univ={SECT_EXEMPT['mean_fin_share_universe']:.2f} top-decile={SECT_EXEMPT['mean_fin_share_top_decile']:.2f} ratio={SECT_EXEMPT['top_over_universe_ratio']:.2f}")
print("DECOMP (window vs composition) IC means [full | meltup-tail | recent]:")
for k in ["ic_qv","ic_qual","ic_val","ic_mom3","ic_comp3","ic_comp1"]:
    dd=DECOMP[k]; print(f"  {k:9s} full={dd['ic_mean']:+.3f}(nwT={dd['ic_nw_t']:+.2f}) meltup={dd['ic_meltup_tail']:+.3f} recent={dd['ic_recent']:+.3f} pos%={dd['pct_pos']:.0f}")
print("Saved metrics.json + config.json + panels/. DONE.")
