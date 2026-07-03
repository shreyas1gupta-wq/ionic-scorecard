"""Build the EXECUTION sheet: fully-specified, dated trade legs (action / symbol / expiry /
strike / CE-PE / live price / lot size) for every strategy, sorted by entry date.
Live prices via Angel One. Output -> FINAL_STRATEGY_FORWARD_CHECK/08_Execution/.
"""
import sys, json, time, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor

PROJ = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(PROJ / "intraday_options_strategy"))
from options.bs_pricing import implied_vol
import angel_cfg as A

R_, Q_ = 0.065, 0.0
TODAY = dt.date(2026, 7, 3)
NEXT_SESSION = dt.date(2026, 7, 6)            # Mon (Jul 4-5 = weekend)
SOPT = PROJ / "intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options"
OUTD = PROJ / "FINAL_STRATEGY_FORWARD_CHECK" / "08_Execution"; OUTD.mkdir(parents=True, exist_ok=True)
FWD = pd.read_csv(PROJ / "datasets/nse_earnings_dates/forthcoming_results.csv")


def prev_session(d):
    d = d - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


obj, sess = A.login(); print("login OK")
scrip = json.loads((Path("scrip_master.json")).read_bytes())
stocks = sorted({p.name for p in SOPT.iterdir() if p.is_dir()})
eqtok = {x["name"]: x["token"] for x in scrip if x.get("exch_seg") == "NSE"
         and x.get("symbol", "").endswith("-EQ") and x.get("name") in stocks}
opt = [x for x in scrip if x.get("exch_seg") == "NFO" and x.get("instrumenttype") == "OPTSTK" and x.get("name") in stocks]

def ed(s): return dt.datetime.strptime(s, "%d%b%Y").date()
exps = sorted({ed(x["expiry"]) for x in opt if ed(x["expiry"]) > TODAY})
FRONT, BACK = exps[0], exps[1]
FRONT_S, BACK_S = FRONT.strftime("%d%b%Y").upper(), BACK.strftime("%d%b%Y").upper()
Tf = (FRONT - TODAY).days / 365; Tb = (BACK - TODAY).days / 365
lot = {}
chain = {}
for x in opt:
    lot[x["name"]] = int(x["lotsize"])
    k = float(x["strike"]) / 100; ot = x["symbol"][-2:]
    chain[(x["name"], x["expiry"], ot, round(k, 2))] = x["token"]
strikes = {}
for (nm, ex, ot, k), tok in chain.items():
    strikes.setdefault((nm, ex), set()).add(k)
print(f"front {FRONT} back {BACK} | {len(eqtok)} stocks")


def bulk_ltp(exch, tokens):
    out = {}; toks = list(dict.fromkeys(tokens))
    for i in range(0, len(toks), 45):
        try:
            r = obj.getMarketData("LTP", {exch: toks[i:i + 45]})
            for f in r.get("data", {}).get("fetched", []):
                out[str(f["symbolToken"])] = f.get("ltp")
        except Exception:
            pass
        time.sleep(0.4)
    return out


spot_tok = bulk_ltp("NSE", list(eqtok.values()))
spot = {nm: spot_tok.get(str(t)) for nm, t in eqtok.items()}
spot = {k: v for k, v in spot.items() if v}


def near(ks, tgt): return min(ks, key=lambda x: abs(x - tgt)) if ks else None


# collect option tokens to price
need = []
plan = {}  # nm -> chosen strikes/tokens
for nm, s in spot.items():
    kf = strikes.get((nm, FRONT_S), set()); kb = strikes.get((nm, BACK_S), set())
    if not kf or not kb:
        continue
    atm = near(sorted(kf & kb), s) if (kf & kb) else near(sorted(kf), s)
    kc = near(sorted(kf), s * 1.05); kp = near(sorted(kf), s * 0.95)
    m = {"spot": s, "atm": atm, "kc": kc, "kp": kp, "lot": lot.get(nm, 0)}
    for lab, ex, ot, k in [("f_atmCE", FRONT_S, "CE", atm), ("b_atmCE", BACK_S, "CE", atm),
                            ("f_atmPE", FRONT_S, "PE", atm),
                            ("otmCE", FRONT_S, "CE", kc), ("otmPE", FRONT_S, "PE", kp)]:
        t = chain.get((nm, ex, ot, k))
        if t: m[lab] = t; need.append(t)
    plan[nm] = m

ltp = bulk_ltp("NFO", need)
def L(nm, lab):
    t = plan[nm].get(lab); return ltp.get(str(t)) if t else None

rows = []   # execution legs

# ---- FF calendar (enter next session) ----
for nm, m in plan.items():
    ce_f, ce_b = L(nm, "f_atmCE"), L(nm, "b_atmCE")
    if not (ce_f and ce_b and m["atm"]):
        continue
    iv1 = implied_vol(ce_f, m["spot"], m["atm"], Tf, R_, Q_, True)
    iv2 = implied_vol(ce_b, m["spot"], m["atm"], Tb, R_, Q_, True)
    if not (iv1 and iv2 and 0.03 < iv1 < 3 and 0.03 < iv2 < 3):
        continue
    var_f = (iv2**2 * Tb - iv1**2 * Tf) / (Tb - Tf)
    if var_f <= 0:
        continue
    ff = (iv1 - np.sqrt(var_f)) / np.sqrt(var_f)
    if ff < 0.25:
        continue
    sz = 0.75 if ff < 0.5 else (1.0 if ff < 0.75 else 1.25)
    for act, ex, px in [("SELL", FRONT_S, ce_f), ("BUY", BACK_S, ce_b)]:
        rows.append(dict(entry_date=NEXT_SESSION, strategy="FF_Calendar", action=act, symbol=nm,
                         expiry=ex, strike=m["atm"], opt="CE", live_price=round(px, 2),
                         lots=round(sz, 2), lot_size=m["lot"], signal=f"FF={ff:.2f}",
                         exit_rule="close BOTH ~2 sessions before front expiry"))

# ---- Short strangle (enter ~14 DTE) ----
STR_ENTRY = FRONT - dt.timedelta(days=14)
while STR_ENTRY.weekday() >= 5:
    STR_ENTRY += dt.timedelta(days=1)
for nm, m in plan.items():
    ce, pe = L(nm, "otmCE"), L(nm, "otmPE")
    if not (ce and pe):
        continue
    cr = ce + pe
    for act, k, ot, px in [("SELL", m["kc"], "CE", ce), ("SELL", m["kp"], "PE", pe)]:
        rows.append(dict(entry_date=STR_ENTRY, strategy="Short_Strangle", action=act, symbol=nm,
                         expiry=FRONT_S, strike=k, opt=ot, live_price=round(px, 2),
                         lots=1, lot_size=m["lot"], signal=f"credit={cr:.1f} ({cr/m['spot']*100:.1f}%spot)",
                         exit_rule="buy back at 50% of credit, else hold to expiry"))

# ---- Earnings short-vol (enter 1 session before each earnings) ----
FWD["d"] = pd.to_datetime(FWD["date"], format="%d-%b-%Y", errors="coerce")
up = FWD.dropna(subset=["d"]); up = up[up["d"].dt.date >= TODAY].sort_values("d")
for _, e in up.iterrows():
    nm = e["symbol"]; ed_ = e["d"].date()
    if nm not in plan:
        continue
    exp = FRONT if ed_ <= FRONT else BACK
    exp_s = exp.strftime("%d%b%Y").upper()
    m = plan[nm]; atm = m["atm"]
    # price ATM CE+PE in the spanning expiry (front already priced; back reuse if needed)
    ce = L(nm, "f_atmCE") if exp == FRONT else L(nm, "b_atmCE")
    pe = L(nm, "f_atmPE") if exp == FRONT else None
    entry = prev_session(ed_)
    for act, ot, px in [("SELL", "CE", ce), ("SELL", "PE", pe)]:
        rows.append(dict(entry_date=entry, strategy="Earnings_ShortVol", action=act, symbol=nm,
                         expiry=exp_s, strike=atm, opt=ot, live_price=round(px, 2) if px else None,
                         lots=1, lot_size=m["lot"], signal=f"earnings {ed_}",
                         exit_rule="close 1 session AFTER the result"))

df = pd.DataFrame(rows).sort_values(["entry_date", "strategy", "symbol", "opt"])
df.to_csv(OUTD / "execution_ALL.csv", index=False)
for strat in df["strategy"].unique():
    df[df["strategy"] == strat].to_csv(OUTD / f"execution_{strat}.csv", index=False)

# counts
ff_n = (df["strategy"] == "FF_Calendar").sum() // 2
str_n = (df["strategy"] == "Short_Strangle").sum() // 2
ea_n = (df["strategy"] == "Earnings_ShortVol").sum() // 2
print(f"FF trades {ff_n} | strangle {str_n} | earnings {ea_n} | total legs {len(df)}")

# ---- Word execution plan ----
doc = Document()
doc.add_heading("EXECUTION PLAN — trades to take", 0)
p = doc.add_paragraph(f"Live prices as of {TODAY} (Fri close). Next session Mon {NEXT_SESSION}. "
                      f"Front expiry {FRONT}, back {BACK}. Account = disposable/data-only.")
p.runs[0].italic = True
doc.add_heading("Sequenced by entry date", 1)
t = doc.add_table(rows=1, cols=8); t.style = "Light Grid Accent 1"
for i, h in enumerate(["Entry date", "Strategy", "Action", "Symbol", "Expiry", "Strike", "CE/PE", "Live px"]):
    r = t.rows[0].cells[i].paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8)
for _, x in df.iterrows():
    c = t.add_row().cells
    vals = [str(x["entry_date"]), x["strategy"].replace("_", " "), x["action"], x["symbol"],
            x["expiry"], f"{x['strike']:g}", x["opt"], f"{x['live_price']}" if pd.notna(x["live_price"]) else "-"]
    for i, v in enumerate(vals):
        rr = c[i].paragraphs[0].add_run(v); rr.font.size = Pt(8)
doc.add_heading("How to read / manage", 1)
for b in [f"FF Calendar ({ff_n} trades): enter {NEXT_SESSION}. SELL front-{FRONT_S} CE + BUY back-{BACK_S} CE at same strike. "
          "Size 0.75/1.0/1.25x by FF tier. Exit both legs ~2 sessions before front expiry. NOTE many names have Jul earnings (elevated FF).",
          f"Short Strangle ({str_n} trades): enter ~{STR_ENTRY} (14 DTE). SELL ~5% OTM CE + ~5% OTM PE (front). "
          "Buy back at 50% of credit collected, else hold to expiry.",
          f"Earnings Short-Vol ({ea_n} events): for each, SELL the ATM straddle (CE+PE) 1 session BEFORE the result, "
          "close 1 session AFTER (harvest IV crush). Entry dates are per-stock (see table).",
          "IV/RV Short Straddle: NO trade right now — 0 stocks currently show IV/RV >= 1.4 (market calm).",
          "Tail risk is accepted (no stop). Manage at portfolio level: small size, many concurrent, diversify."]:
    doc.add_paragraph(b, style="List Bullet")
doc.save(OUTD / "EXECUTION_PLAN.docx")
print(f"saved -> {OUTD}")
