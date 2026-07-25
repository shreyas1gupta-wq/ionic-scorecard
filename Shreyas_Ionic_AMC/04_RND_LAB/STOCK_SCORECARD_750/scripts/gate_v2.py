# -*- coding: utf-8 -*-
"""Balance-sheet gate v2 (Principal-ratified 2026-07-25): context-aware recalibration
+ debt-free-cover fix. Step 1 REPRODUCES the engine's old final scores from composites
(validates my model of gate->penalty order); step 2 applies gate v2 and emits the diff.
"""
import os
import numpy as np
import pandas as pd

RES = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\STOCK_SCORECARD_750\results"
OUT = os.path.join(RES, "gate_v2_recalibration")
os.makedirs(OUT, exist_ok=True)

FIN = ("Financial Services",)
PSU = {"BHEL","GAIL","SBIN","HINDCOPPER","NATIONALUM","COCHINSHIP","POWERGRID","NTPC","ONGC","IOC",
       "BPCL","HINDPETRO","COALINDIA","SAIL","NMDC","IRCTC","IRFC","HAL","BEL","MAZDOCK","BDL","PFC",
       "RECLTD","NHPC","OIL","CANBK","BANKBARODA","PNB","UNIONBANK","INDIANB","MAHABANK","BANKINDIA",
       "LICI","NTPCGREEN","SJVN","CESC","ITI","FACT","MMTC","RVNL","IRCON","HCC","NBCC","ENGINERSIN",
       "RITES","CONCOR","GMDC","MOIL"}
LEASE_HEAVY = {"INDIGO","SAMHI","WEWORK","SMARTWORKS","AWFIS","DEVYANI","WESTLIFE","SAPPHIRE",
               "JUBLFOOD","PVRINOX","LEMONTREE","CHALET","EIHOTEL","INDHOTEL"}
JEWELLERY = {"TITAN","KALYANKJIL","SENCO","THANGAMAYL","PNGJL"}   # gold-metal-loan D/E
GROUP_CTX = ("ADANI","JSW","VEDL","HINDZINC","TATA","GRASIM","HINDALCO","ULTRACEMCO")  # log-only

def sector_kind(sector):
    s = str(sector).lower()
    if "financial" in s: return "fin"
    if s in ("power",) or "power" in s or "utilit" in s: return "utility"
    if "construction material" in s: return "cement"
    if "construction" in s: return "epc"
    if "realty" in s: return "realty"
    return "std"

def gate_v1(sector, de, icov):
    if sector_kind(sector) == "fin": return "N/A-financial-sector"
    if de > 2.5 or icov < 1.5: return "RED"
    if de > 1.5 or icov < 3: return "AMBER"
    return "GREEN"

def gate_v2(symbol, sector, de, icov):
    k = sector_kind(sector)
    if k == "fin": return "N/A-financial-sector", ""
    if de < 0:  # negative equity: always RED, no context rescues it
        return "RED", "negative equity"
    # D/E thresholds by industry norm
    if symbol in LEASE_HEAVY:
        de_red, de_amb = np.inf, np.inf          # judged on cover, not lease-inflated D/E
    elif symbol in JEWELLERY:
        de_red, de_amb = 4.0, 2.5                # gold-loan inventory financing
    elif k == "utility":
        de_red, de_amb = 4.0, 2.5
    elif k in ("epc", "cement"):
        de_red, de_amb = 3.0, 2.0
    else:                                        # incl. realty: leverage IS the risk
        de_red, de_amb = 2.5, 1.5
    # cover thresholds (utilities tolerate lower cover on regulated cash flows)
    ic_red, ic_amb = (1.2, 2.0) if k == "utility" else (1.5, 3.0)
    cover_active = de > 0.3                      # debt-free fix: cover leg needs real debt
    red = de > de_red or (cover_active and icov < ic_red)
    amb = de > de_amb or (cover_active and icov < ic_amb)
    flag = "RED" if red else ("AMBER" if amb else "GREEN")
    why = []
    if de > de_amb: why.append(f"D/E {de:.1f}")
    if cover_active and icov < ic_amb: why.append(f"cover {icov:.1f}")
    # PSU sovereign backing: one-notch relief, never on negative equity
    if symbol in PSU and flag in ("RED", "AMBER"):
        flag = "AMBER" if flag == "RED" else "GREEN"
        why.append("PSU one-notch relief")
    return flag, "; ".join(why)

def lev_flags(sector, de, icov, v2=False, symbol=""):
    """count of leverage red-flags feeding the penalty"""
    n = 0
    fin = sector_kind(sector) == "fin"
    if v2:
        f, _ = gate_v2(symbol, sector, de, icov)
        # penalty flags follow the same v2 logic: only a v2-RED counts leverage flags
        if f == "RED":
            if not fin and de > 2.5: n += 1
            if de > 0.3 and icov < 1.5: n += 1
    else:
        if icov < 1.5: n += 1
        if not fin and de > 2.5: n += 1
    return n

def other_flags(row):
    n = 0
    if row.get("revenue_growth_1y", 0) < 0: n += 1
    if (row.get("revenue_cagr_3y", 0) - row.get("revenue_growth_1y", 0)) > 15: n += 1
    return n

def penalty(n):
    return -min(10, 2 ** n - 1) if n > 0 else 0

def finalize(comp, flag, pen):
    x = comp
    if flag == "AMBER": x *= 0.85
    x += pen
    if flag == "RED": x = min(x, 39)   # engine's empirical cap
    return x

df = pd.read_csv(os.path.join(RES, "full750_scored.csv"))
df["de"] = pd.to_numeric(df["debt_equity"], errors="coerce").fillna(0)
df["ic"] = pd.to_numeric(df["interest_coverage"], errors="coerce").fillna(99)

# ---- step 1: reproduce old finals to validate the order model -------------------
errs = []
for _, r in df.iterrows():
    n = lev_flags(r["sector"], r["de"], r["ic"]) + other_flags(r)
    rep = finalize(r["composite_3y"], r["bs_flag"], penalty(n))
    errs.append(abs(rep - r["final_score_3y"]))
errs = pd.Series(errs)
print(f"repro |err|: median {errs.median():.3f}  p90 {errs.quantile(.9):.3f}  "
      f"within 0.51: {(errs < 0.51).mean()*100:.1f}%")

# ---- step 2: gate v2 ------------------------------------------------------------
rows = []
for _, r in df.iterrows():
    old_f = str(r["bs_flag"])
    new_f, why = gate_v2(r["symbol"], r["sector"], r["de"], r["ic"]) if old_f != "N/A-financial-sector" \
        else ("N/A-financial-sector", "")
    n_old = lev_flags(r["sector"], r["de"], r["ic"]) + other_flags(r)
    n_new = lev_flags(r["sector"], r["de"], r["ic"], v2=True, symbol=r["symbol"]) + other_flags(r)
    d_pen = penalty(n_new) - penalty(n_old)
    # carry any unmodeled term (the +3 clean-bill boost) via the old-row residual;
    # capped (RED) rows have no recoverable residual and no boost by construction
    resid = 0.0
    if old_f != "RED":
        resid = float(np.clip(r["final_score_3y"]
                              - finalize(r["composite_3y"], old_f, penalty(n_old)), -3.5, 3.5))
    f3 = finalize(r["composite_3y"] + resid, new_f, penalty(n_new))
    f1 = finalize(r["composite_1y"] + resid, new_f, penalty(n_new))
    # gate RED is an automatic Sell per the frozen rule, regardless of the capped score
    rec = "Sell" if (new_f == "RED" or f3 < 40 or f1 < 40) else "Hold"
    old_rec = str(r.get("recommendation_overall", ""))
    grp = any(g in str(r["symbol"]).upper() for g in GROUP_CTX)
    if new_f != old_f or abs(d_pen) > 0:
        rows.append(dict(symbol=r["symbol"], sector=r["sector"], de=round(r["de"], 2),
                         icov=round(r["ic"], 2), old_flag=old_f, new_flag=new_f, why=why,
                         old_3y=round(r["final_score_3y"], 1), new_3y=round(f3, 1),
                         old_1y=round(r["final_score_1y"], 1), new_1y=round(f1, 1),
                         old_rec=old_rec, new_rec=rec,
                         group_ctx_review=("YES" if grp else "")))

d = pd.DataFrame(rows).sort_values(["new_flag", "sector", "symbol"])
d.to_csv(os.path.join(OUT, "gate_v2_full750_diff.csv"), index=False)
print(f"\nflag/penalty changes: {len(d)} names -> {OUT}\\gate_v2_full750_diff.csv")
print("\nflag transitions:")
print(d.groupby(["old_flag", "new_flag"]).size().to_string())
chg = d[d.old_rec.str.lower() != d.new_rec.str.lower()]
print(f"\nRECOMMENDATION changes: {len(chg)}")
if len(chg):
    print(chg[["symbol", "sector", "old_flag", "new_flag", "old_3y", "new_3y", "old_1y",
               "new_1y", "old_rec", "new_rec", "group_ctx_review"]].to_string(index=False))
print(f"\ngroup-context names needing analyst review: {int((d.group_ctx_review=='YES').sum())}")
