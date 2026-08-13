"""Apply futures cost-of-carry to the spot-proxy sweep backtest (Principal ruling: +0.5%/month).

Long futures: you buy at spot+premium; the premium decays to spot by expiry => LONG PAYS carry.
Short futures: you sell the premium and it decays to you => SHORT RECEIVES carry.
So on a balanced long/short book the carry largely CANCELS. That balance is the thing to check.
carry_pts = entry_px * (0.005/30) * hold_days, signed by direction.
"""
import datetime as dt
import numpy as np
import pandas as pd

CARRY_MONTHLY = 0.005
LOT, CAPITAL = 75, 10_00_000.0
BROK, EXCH, GST, STAMP, SEBI_CR = 20.0, 0.0019/100, 0.18, 0.002/100, 10.0
STT_OLD, STT_NEW, SW = 0.0125/100, 0.020/100, dt.date(2024, 10, 1)


def rt_cost(e, x, lots, d):
    qty = lots*LOT; stt = (STT_OLD if d < SW else STT_NEW)*x*qty
    turn = (e+x)*qty; brok = BROK*2; exch = EXCH*turn
    return brok+exch+stt+GST*(brok+exch)+STAMP*e*qty+SEBI_CR*turn/1e7


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 10: return np.nan
    m = x.mean(); dv = x-m; n = len(x); v = (dv@dv)/n
    for L in range(1, min(lags, n-1)+1):
        v += 2*(1-L/(lags+1))*((dv[L:]@dv[:-L])/n)
    return m/np.sqrt(v/n) if v > 0 else np.nan


def met(tr, label):
    if len(tr) < 10: return {"w": label, "n": len(tr)}
    daily = tr.groupby("date")["net"].sum()
    eq = CAPITAL+daily.cumsum(); pk = eq.cummax()
    mdd = float(((eq-pk)/pk).min())
    yrs = max((max(tr.date)-min(tr.date)).days/365.25, .01)
    cagr = (float(eq.iloc[-1])/CAPITAL)**(1/yrs)-1 if eq.iloc[-1] > 0 else np.nan
    dr = daily/CAPITAL
    sh = float(dr.mean()/dr.std()*np.sqrt(252)) if dr.std() > 0 else np.nan
    w, l = tr[tr.net > 0].net, tr[tr.net <= 0].net
    m = tr.copy(); m["ym"] = pd.to_datetime(m.date).dt.to_period("M")
    mo = m.groupby("ym").net.sum()
    return {"w": label, "n": len(tr), "mean_pts": round(float(tr.eff_pts.mean()), 2),
            "CAGR": round(100*cagr, 2), "MDD": round(100*mdd, 2),
            "Calmar": round(float(cagr/abs(mdd)), 2) if mdd else None,
            "Sharpe": round(sh, 2),
            "PF": round(float(w.sum()/abs(l.sum())), 2) if l.sum() else None,
            "t": round(float(nw_t(daily.values)), 2),
            "mo+": f"{int((mo>0).sum())}/{len(mo)}"}


for cfg in ("D_overnight1_trail40", "E_swing3_trail60"):
    tr = pd.read_csv(f"trades_{cfg}_1lot.csv", parse_dates=["t"])
    tr["date"] = pd.to_datetime(tr["date"]).dt.date
    nlong, nshort = int((tr.dir > 0).sum()), int((tr.dir < 0).sum())
    hold_days = np.maximum(tr.hold_min/375.0, 0.0)      # 375 min per session
    carry = tr.entry*(CARRY_MONTHLY/30.0)*np.maximum(hold_days, 0.5)
    print("="*104)
    print(f"{cfg}:  long={nlong} ({100*nlong/len(tr):.1f}%)  short={nshort} ({100*nshort/len(tr):.1f}%)"
          f"  mean hold={tr.hold_min.mean()/375:.2f} sessions  mean carry={carry.mean():.2f} pts")
    for tag, adj in (("NO carry (as reported)", 0.0), ("WITH carry +0.5%/mo", 1.0)):
        d = tr.copy()
        # long pays carry, short receives it
        d["eff_pts"] = d.gross_pts - adj*np.sign(d.dir)*carry
        d["gross"] = d.eff_pts*LOT
        d["cost"] = [rt_cost(e, x, 1, dd) for e, x, dd in zip(d.entry, d.exit, d.date)]
        d["net"] = d.gross-d.cost
        wins = {"ALL_11yr": d,
                "OOS_2015_2021": d[d.date < dt.date(2021, 5, 1)],
                "IS_2021_2025": d[(d.date >= dt.date(2021, 5, 1)) & (d.date <= dt.date(2025, 12, 31))],
                "FWD_2026": d[d.date >= dt.date(2026, 1, 1)]}
        print(f"  -- {tag}")
        for k, v in wins.items():
            m = met(v, k)
            if m.get("n", 0) < 10:
                print(f"     {k:16s} n={m.get('n')} (thin)"); continue
            print(f"     {k:16s} n={m['n']:>4} pts={m['mean_pts']:>6} CAGR={m['CAGR']:>7}% "
                  f"MDD={m['MDD']:>7}% Calmar={m['Calmar']} Sh={m['Sharpe']} PF={m['PF']} "
                  f"t={m['t']} mo+={m['mo+']}")
