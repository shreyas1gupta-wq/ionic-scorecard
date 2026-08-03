"""PLEDGE_SAFE_20260802 -- Rs 50L gov bond + Rs 50L equity MF, both pledged, margin used to run
S1-F (frozen spec, unchanged) as a yield overlay. See PRE_REGISTRATION.md for full spec/assumptions.
"""
import time
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
TRADES = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\SELLSIDE_20260710\final_three\final_three_trades.csv"
SPOT_1MIN = ROOT + r"\intraday_options_strategy\datasets\raw\kaggle\debashis74017__nifty-50-minute-data\NIFTY 50_minute.csv"
N500 = ROOT + r"\datasets\index_daily\nifty500.parquet"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PLEDGE_SAFE_20260802"

BOND0, MF0 = 5_000_000.0, 5_000_000.0
BOOK0 = BOND0 + MF0
BOND_RATE, MF_FLAT_RATE = 0.08, 0.12
LOT, MARGIN_RATE = 75, 0.15
MARGIN_CAP_FRAC = 0.40          # RISK_LIMITS.md book-level rule, not invented here
HAIRCUT_BOND, HAIRCUT_MF = 0.10, 0.30   # [ASSUMPTION] see PRE_REGISTRATION.md


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_s1_trades_with_spot_and_veto():
    tr = pd.read_csv(TRADES)
    s1 = tr[tr.strat == "S1"].copy()
    s1["date"] = pd.to_datetime(s1.day)
    sp = pd.read_csv(SPOT_1MIN, parse_dates=["date"]).set_index("date").sort_index()
    import datetime as dt
    sp = sp[sp.index.time >= dt.time(9, 15)]
    dcl = sp["close"].groupby(sp.index.date).last()
    dcl.index = pd.to_datetime(dcl.index)
    s1["spot"] = s1["date"].map(dcl)
    s1 = s1.dropna(subset=["spot"]).sort_values("date").reset_index(drop=True)

    d = dcl.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 5, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 5, adjust=False).mean()
    rsi5 = (100 - 100 / (1 + up / dn)).shift(1)
    pret = dcl.pct_change().shift(1) * 100
    s1["veto"] = s1["date"].map(lambda x: bool((rsi5.get(x, 50) >= 80) | (rsi5.get(x, 50) <= 20) | (abs(pret.get(x, 0)) > 1.5)))

    # crash-halving rule, approximated on DAILY realized vol (3d vs 1yr trailing median, D-1 values)
    dlogret = np.log(dcl / dcl.shift(1))
    rv3 = dlogret.rolling(3).std() * np.sqrt(252)
    med1y = rv3.rolling(252, min_periods=60).median()
    crash_flag = (rv3.shift(1) > 2 * med1y.shift(1)).fillna(False)
    s1["crash_halve"] = s1["date"].map(lambda x: bool(crash_flag.get(x, False)))
    return s1


def load_mf_real_returns(start, end):
    n5 = pd.read_parquet(N500)
    n5["date"] = pd.to_datetime(n5["timestamp"]).dt.tz_localize(None).dt.normalize()
    n5 = n5.set_index("date").sort_index()["close"]
    n5 = n5[(n5.index >= start) & (n5.index <= end)]
    ret = n5.pct_change().fillna(0.0)
    cagr = (n5.iloc[-1] / n5.iloc[0]) ** (365.25 / (n5.index[-1] - n5.index[0]).days) - 1
    log(f"  NIFTY 500 price-index real CAGR over sample window: {cagr:+.2%} (price return, ex-dividend)")
    return ret   # daily simple return series, indexed by calendar date (ffill on weekends via reindex later)


def run_variant(s1, mf_mode, mf_daily_ret_lookup=None):
    """mf_mode: 'flat' or 'real'. Returns a daily-ish panel keyed by every S1 event date (expiry days)
    plus book-level bond/MF marks compounded continuously between events."""
    all_dates = pd.date_range(s1["date"].min(), s1["date"].max(), freq="D")
    bond, mf = BOND0, MF0
    cash_pnl = 0.0
    rows = []
    s1_idx = s1.set_index("date")
    lots_series, margin_used_series = [], []
    prev_date = all_dates[0]
    bond_daily_factor = (1 + BOND_RATE) ** (1 / 365.25)
    mf_daily_factor = (1 + MF_FLAT_RATE) ** (1 / 365.25)

    for d in all_dates:
        ndays = (d - prev_date).days
        if ndays > 0:
            bond *= bond_daily_factor ** ndays
            if mf_mode == "flat":
                mf *= mf_daily_factor ** ndays
            else:
                r = mf_daily_ret_lookup.get(d, 0.0)
                mf *= (1 + r)
        prev_date = d

        lots, margin_used, net_today = 0, 0.0, 0.0
        if d in s1_idx.index:
            row = s1_idx.loc[d]
            book_now = bond + mf
            margin_budget = MARGIN_CAP_FRAC * book_now
            margin_per_lot = float(row["spot"]) * LOT * MARGIN_RATE
            if not row["veto"]:
                lots = int(margin_budget / margin_per_lot)
                if row["crash_halve"]:
                    lots = lots // 2
            margin_used = lots * margin_per_lot
            net_today = lots * float(row["net"]) * LOT
            cash_pnl += net_today

        total = bond + mf + cash_pnl
        rows.append(dict(date=d, bond=bond, mf=mf, cash_pnl=cash_pnl, total=total,
                          lots=lots, margin_used=margin_used, book_now=bond + mf,
                          net_today_rs=net_today))
        lots_series.append(lots); margin_used_series.append(margin_used)

    panel = pd.DataFrame(rows).set_index("date")
    return panel


def metrics(panel, label):
    total = panel["total"]
    days = (total.index[-1] - total.index[0]).days
    yrs = days / 365.25
    cagr = (total.iloc[-1] / total.iloc[0]) ** (1 / yrs) - 1
    dd = (total - total.cummax()) / total.cummax()
    maxdd = dd.min()
    daily_ret = total.pct_change().dropna()
    sharpe = (daily_ret.mean() / daily_ret.std()) * np.sqrt(252) if daily_ret.std() > 0 else np.nan
    calmar = cagr / abs(maxdd) if maxdd != 0 else np.nan
    max_util = (panel["margin_used"] / (0.40 * panel["book_now"])).replace([np.inf, -np.inf], np.nan).max()
    worst_day_rs = panel["net_today_rs"].min()
    worst_day_pct_book = (panel["net_today_rs"] / panel["book_now"]).min()
    log(f"[{label}] final Rs {total.iloc[-1]:,.0f} | CAGR {cagr:+.2%} | MaxDD {maxdd:+.2%} | "
        f"Sharpe {sharpe:.2f} | Calmar {calmar:.2f} | max margin util vs 40% cap: {max_util:.1%} | "
        f"worst expiry-day: Rs {worst_day_rs:,.0f} ({worst_day_pct_book:+.3%} of book) | "
        f"lots range {panel['lots'].min()}-{panel['lots'].max()} | "
        f"avg margin used Rs {panel['margin_used'][panel['margin_used']>0].mean():,.0f}")
    return dict(label=label, final_rs=total.iloc[-1], cagr=cagr, maxdd=maxdd, sharpe=sharpe,
                calmar=calmar, max_margin_util_vs_cap=max_util, worst_day_rs=worst_day_rs,
                worst_day_pct_book=worst_day_pct_book, min_lots=int(panel["lots"].min()),
                max_lots=int(panel["lots"].max()),
                avg_margin_used=float(panel["margin_used"][panel["margin_used"] > 0].mean()),
                haircut_available_rs=(1 - HAIRCUT_BOND) * BOND0 + (1 - HAIRCUT_MF) * MF0,
                cap40_rs=MARGIN_CAP_FRAC * BOOK0)


def main():
    log("loading S1-F real trades + spot + veto/crash flags ...")
    s1 = load_s1_trades_with_spot_and_veto()
    log(f"  {len(s1)} expiry-day events, {s1['date'].min().date()}..{s1['date'].max().date()}, "
        f"vetoed {s1['veto'].mean():.1%}, crash-halve {s1['crash_halve'].mean():.1%}")

    log(f"haircut-derived available margin: Rs {(1-HAIRCUT_BOND)*BOND0 + (1-HAIRCUT_MF)*MF0:,.0f} | "
        f"RISK_LIMITS 40%-of-book cap: Rs {MARGIN_CAP_FRAC*BOOK0:,.0f} "
        f"-> {'RISK_LIMITS cap BINDS' if MARGIN_CAP_FRAC*BOOK0 < (1-HAIRCUT_BOND)*BOND0+(1-HAIRCUT_MF)*MF0 else 'haircut BINDS'}")

    log("running FLAT-assumption variant (bond 8%, MF 12%, both daily-compounded)...")
    panel_flat = run_variant(s1, "flat")
    panel_flat.to_csv(f"{OUT}/panel_flat.csv")
    m_flat = metrics(panel_flat, "FLAT 8%/12%")

    log("loading real NIFTY 500 daily returns for MF-sleeve robustness check...")
    mf_ret = load_mf_real_returns(s1["date"].min() - pd.Timedelta(days=5), s1["date"].max())
    mf_ret_lookup = mf_ret.to_dict()
    log("running REAL-MF variant (bond 8%, MF = actual NIFTY 500 daily returns)...")
    panel_real = run_variant(s1, "real", mf_ret_lookup)
    panel_real.to_csv(f"{OUT}/panel_real_mf.csv")
    m_real = metrics(panel_real, "REAL bond8%/NIFTY500")

    summary = pd.DataFrame([m_flat, m_real])
    summary.to_csv(f"{OUT}/summary_metrics.csv", index=False)
    log(f"\nsaved: panel_flat.csv, panel_real_mf.csv, summary_metrics.csv")
    log("DONE")


if __name__ == "__main__":
    main()
