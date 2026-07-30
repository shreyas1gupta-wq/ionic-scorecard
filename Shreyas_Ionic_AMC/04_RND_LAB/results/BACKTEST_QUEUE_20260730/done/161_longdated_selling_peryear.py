"""
161_longdated_selling_peryear.py -- Manoj Pillai (Ops), 2026-07-30.
PER-YEAR MEMORY-SAFE REWRITE of 111_longdated_selling.py (which died 3x on
numpy._core._exceptions._ArrayMemoryError: Unable to allocate 58.4 MiB for shape (7650351,) --
building ONE 4-level MultiIndex over the full 7.65M-row 16-year chain and sort_index()-ing it).

DESIGN IS UNCHANGED from LONGDATED_SELLING_20260730/PREREG.md (57 pre-registered trials: 54-config
grid of 3 tenor x 3 delta x 2 structure x 3 management, +3 overlay trials). Do NOT re-tune anything
here -- this file changes ONLY the memory access pattern. Any numeric difference vs a hypothetical
full-chain run is attributable to the LOT correction below, not to a design change.

WHAT CHANGED (memory pattern only):
  1. No global `by_strike`/`by_day` MultiIndex over all 16 years. Instead a `YearChainCache` loads
     ONE calendar year's NIFTY OPTIDX rows at a time (column-subset, parsed, deduped), indexes it by
     TIMESTAMP only (single-level, cheap sort_index on ~0.2-0.8M rows/yr, never 7.65M), and evicts
     to an LRU of 2 resident years (current + adjacent) via gc.collect(). Two years are enough
     because this arm's tenor grid caps at bimonthly (hi=100 DTE ~3.3 months) -- a position entered
     late in year Y can only expire, at the very latest, ~100 days into Y+1.
  2. Entry-sequence discovery (step 6 of the original) and raw-trade construction (step 7) are
     FUSED into one chronological sweep per tenor, so each tenor needs only ONE forward pass over
     TRADING_DAYS (not a separate global-index build then a second replay).
  3. Checkpointed per tenor (D-023 "checkpoint everything" / Manoj charter): after each tenor's
     sweep, its raw-trade dict is pickled to `_checkpoint_<tenor>.pkl`. A rerun skips any tenor
     whose checkpoint already exists -- this job is resumable if the queue runner's 1h timeout
     ever bites on a slow machine.
  4. guards.py imported (L7 assert_no_future_settlement + a custom physical-bound check: a short
     option position's net P&L can never exceed the credit collected).

ONE DATA CORRECTION (not a design tune): PREREG.md and the original 111 script used LOT=75, the
NIFTY lot size that was current when PREREG.md was written. The firm's lot-size history
(`SESSION_JOURNAL.md`, verified from `lot_sizes.json` built off the bhavcopy) is
75 -> 50 (Jul-21) -> 75 (May-24) -> 65 (Jan-26, CURRENT as of today 2026-07-30). Every other job
queued THIS session (152_three_posted.py, 156_indicator_mine_stage2.py, CHAIN_MICRO PRE_REGISTRATION,
INDICATOR_MINE PRE_REGISTRATION) already uses LOT=65, and the rebuild brief for this arm explicitly
states "lot = 65". Using 75 here would be silently reintroducing a stale constant while every
sibling job this session uses the corrected one. The GRID (tenor/delta/structure/mgmt) is untouched.

Pre-registration: Shreyas_Ionic_AMC/04_RND_LAB/results/LONGDATED_SELLING_20260730/PREREG.md
Owner: Vikram Shah (FM). Do NOT tune anything here after results exist.
"""
from __future__ import annotations
import sys, time, json, bisect, gc, pickle
import numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import norm

t_start = time.time()

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
BHAV_DIR = ROOT / "Shreyas_Ionic_AMC" / "05_DATA_OFFICE" / "data" / "fo_bhavcopy_hist"
OUT = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "LONGDATED_SELLING_20260730"
IV_CSV = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "INVERSE_VRP_NICHE_20260729" / "daily_vol_series.csv"
SPOT_PARQUET = ROOT / "datasets" / "index_daily" / "nse_official_all_indices.parquet"
OUT.mkdir(parents=True, exist_ok=True)
CKPT_DIR = OUT / "_checkpoints"
CKPT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
import guards as G  # noqa: E402

LOG_LINES = []
def log(*a):
    line = f"[{time.time()-t_start:7.1f}s] " + " ".join(str(x) for x in a)
    print(line, flush=True)
    LOG_LINES.append(line)

# ---------------------------------------------------------------- constants (pre-registered)
LOT = 65                       # CORRECTED from PREREG's 75 -- see docstring. Grid unchanged.
R = 0.065                      # flat risk-free proxy [INFERENCE], matches firm convention
BROKERAGE_RS = 25.0            # Rs per lot per SIDE per leg-execution (SHARED_CONTEXT mandate)
SLIP_PT = 0.4                  # index points per side per leg-execution, always against us
WING_PCT = 0.03                # condor wing = short strike +/- ~3% of spot, dynamic
MARGIN_NAKED_PCT = 0.10
MARGIN_HEDGED_PCT = 0.05
STT_EXERCISE_PCT = 0.00125     # 0.125% of intrinsic, LONG legs only (COST_STANDARDS)
STRIKE_TOL_FRAC = 0.07         # snap-to-liquid-strike tolerance vs target (7% of spot) else drop
CACHE_YEARS = 2                # max resident chain-years (bimonthly hi=100 DTE never needs a 3rd)

TENORS = {
    "biweekly": (7, 20, 12),
    "monthly": (20, 45, 30),
    "bimonthly": (45, 100, 60),
}
DELTAS = [0.10, 0.15, 0.25]
STRUCTURES = ["naked", "condor"]
MGMTS = ["hold", "buyback50", "stop2x"]

BUILD_END = pd.Timestamp("2023-12-31")
HELDOUT_START = pd.Timestamp("2024-01-01")
OVERALL_END = pd.Timestamp("2026-06-30")
IV_WIN_START = pd.Timestamp("2021-05-24")
IV_WIN_END = pd.Timestamp("2026-06-03")
YEARS = list(range(2011, 2027))

CHAIN_COLS = ["SYMBOL", "INSTRUMENT", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "CLOSE", "CONTRACTS", "TIMESTAMP"]

# ---------------------------------------------------------------- 0. lightweight global pass
# Only 4 columns per year, uniqued and discarded immediately -- never holds full-chain rows.
log("[0] lightweight pass: global EXPIRIES + TRADING_DAYS (column-subset, per year) ...")
# NOTE: no dedup here -- this pass only extracts .unique() date values from 4 columns
# (SYMBOL/INSTRUMENT/EXPIRY_DT/TIMESTAMP), which is correct regardless of duplicate underlying
# rows (a duplicate row contributes the same date twice, .unique() collapses it either way).
# Real row-level dedup (on the full identity EXPIRY_DT+OPTION_TYP+STRIKE_PR+TIMESTAMP, landmine #2)
# happens per-year inside YearChainCache._load_year() below, where it actually matters (price/
# contracts lookups), and is logged there.
expiry_set, ts_set = set(), set()
year_rowcounts = {}
for y in YEARS:
    p = BHAV_DIR / f"fo_idx_{y}.parquet"
    if not p.exists():
        continue
    d = pd.read_parquet(p, columns=["SYMBOL", "INSTRUMENT", "EXPIRY_DT", "TIMESTAMP"])
    d = d[(d.SYMBOL == "NIFTY") & (d.INSTRUMENT == "OPTIDX")]
    year_rowcounts[y] = len(d)
    ex = pd.to_datetime(d["EXPIRY_DT"], format="mixed", dayfirst=True)
    ts = pd.to_datetime(d["TIMESTAMP"], format="mixed", dayfirst=True)
    assert ex.isna().sum() == 0 and ts.isna().sum() == 0, f"L-date: NaT found in year {y}"
    expiry_set.update(ex.unique().tolist())
    ts_set.update(ts.unique().tolist())
    del d, ex, ts
    gc.collect()
EXPIRIES = sorted(expiry_set)
TRADING_DAYS = sorted(t for t in ts_set if t <= OVERALL_END)
log(f"date-parse guard OK: 0 NaT across all years (raw row counts below include case-variant "
    f"duplicates; per-year dedup happens in YearChainCache, logged there when it fires).")
log(f"global: {len(EXPIRIES)} distinct expiries, {len(TRADING_DAYS)} distinct trading days "
    f"(<= {OVERALL_END.date()}). per-year OPTIDX raw row counts: {year_rowcounts}")
DATA_MAX_DATE = max(ts_set)

# ---------------------------------------------------------------- 1. YearChainCache (the fix)
class YearChainCache:
    """Loads ONE year of NIFTY OPTIDX rows at a time, column-subset + deduped + parsed, indexed
    by TIMESTAMP only (single-level -- cheap). Keeps at most CACHE_YEARS resident; evicts the
    least-recently-used year and gc.collect()s. This is the direct fix for the crash: the original
    script's OOM was `opt.set_index([4 cols]).sort_index()` over 7,650,351 rows; here the biggest
    single sort_index() ever performed is on one year's ~0.2-0.8M rows."""

    def __init__(self):
        self.cache: dict[int, pd.DataFrame] = {}
        self.order: list[int] = []
        self.n_loads = 0

    def _load_year(self, y: int) -> pd.DataFrame:
        p = BHAV_DIR / f"fo_idx_{y}.parquet"
        if not p.exists():
            return pd.DataFrame(columns=["EXPIRY_DT", "OPTION_TYP", "STRIKE_PR", "CLOSE", "CONTRACTS"]).set_index(
                pd.DatetimeIndex([], name="TIMESTAMP"))
        df = pd.read_parquet(p, columns=CHAIN_COLS)
        df = df[(df.SYMBOL == "NIFTY") & (df.INSTRUMENT == "OPTIDX")].drop(columns=["SYMBOL", "INSTRUMENT"])
        df["EXPIRY_DT"] = pd.to_datetime(df["EXPIRY_DT"], format="mixed", dayfirst=True)
        df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], format="mixed", dayfirst=True)
        df["STRIKE_PR"] = df["STRIKE_PR"].astype("float64")
        df["CONTRACTS"] = df["CONTRACTS"].fillna(0).astype("float64")
        df["OPTION_TYP"] = df["OPTION_TYP"].astype(str)
        n0 = len(df)
        df = df.drop_duplicates(subset=["EXPIRY_DT", "OPTION_TYP", "STRIKE_PR", "TIMESTAMP"])
        if n0 - len(df):
            log(f"    year {y}: dropped {n0-len(df)} dup rows post-parse")
        df = df.set_index("TIMESTAMP").sort_index()
        self.n_loads += 1
        return df

    def get_year(self, y: int) -> pd.DataFrame:
        if y not in self.cache:
            while len(self.order) >= CACHE_YEARS:
                old = self.order.pop(0)
                del self.cache[old]
            gc.collect()
            self.cache[y] = self._load_year(y)
            self.order.append(y)
        elif self.order[-1] != y:
            self.order.remove(y)
            self.order.append(y)
        return self.cache[y]

    def day_slice(self, day: pd.Timestamp) -> pd.DataFrame:
        yr = self.get_year(day.year)
        if yr.empty:
            return yr
        try:
            sub = yr.loc[[day]]
        except KeyError:
            return yr.iloc[0:0]
        return sub

    def range_slice(self, start_day: pd.Timestamp, end_day: pd.Timestamp) -> pd.DataFrame:
        parts = []
        for y in range(start_day.year, end_day.year + 1):
            yr = self.get_year(y)
            if yr.empty:
                continue
            part = yr.loc[(yr.index > start_day) & (yr.index <= end_day)]
            if len(part):
                parts.append(part)
        if not parts:
            return pd.DataFrame(columns=["EXPIRY_DT", "OPTION_TYP", "STRIKE_PR", "CLOSE", "CONTRACTS"])
        return pd.concat(parts).sort_index()


cache = YearChainCache()

# ---------------------------------------------------------------- 2. underlying / spot proxy
log("[2] building underlying spot proxy (official Nifty50 close 2016+, FUTIDX near-month pre-2016) ...")
sp = pd.read_parquet(SPOT_PARQUET, columns=["index_name", "date", "close"])
sp = sp[sp.index_name == "Nifty 50"][["date", "close"]].copy()
sp["date"] = pd.to_datetime(sp["date"])
sp = sp.rename(columns={"close": "S"}).set_index("date").sort_index()

fut_frames = []
for y in range(2011, 2016):
    p = BHAV_DIR / f"fo_idx_{y}.parquet"
    if not p.exists():
        continue
    df = pd.read_parquet(p, columns=["SYMBOL", "INSTRUMENT", "EXPIRY_DT", "CLOSE", "TIMESTAMP"])
    df = df[(df.SYMBOL == "NIFTY") & (df.INSTRUMENT == "FUTIDX")].drop(columns=["SYMBOL", "INSTRUMENT"])
    df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], format="mixed", dayfirst=True)
    df["EXPIRY_DT"] = pd.to_datetime(df["EXPIRY_DT"], format="mixed", dayfirst=True)
    fut_frames.append(df.drop_duplicates())
    del df
fut = pd.concat(fut_frames, ignore_index=True)
del fut_frames
fut = fut.sort_values(["TIMESTAMP", "EXPIRY_DT"])
near = fut[fut.EXPIRY_DT >= fut.TIMESTAMP].groupby("TIMESTAMP", as_index=False).first()
near = near[["TIMESTAMP", "CLOSE"]].rename(columns={"TIMESTAMP": "date", "CLOSE": "S"}).set_index("date")
spot = pd.concat([near[near.index < "2016-01-01"], sp]).sort_index()
spot = spot[~spot.index.duplicated(keep="last")]
SPOT = spot["S"]
del fut, near
gc.collect()
log(f"    spot proxy: {len(SPOT)} days, {SPOT.index.min().date()}..{SPOT.index.max().date()} "
    f"({(SPOT.index < '2016-01-01').sum()} days on FUTIDX proxy, basis validated <1% typical, see PREREG)")

# ---------------------------------------------------------------- 3. realized vol + no-lookahead pct
log("[3] trailing realized vol + expanding no-lookahead percentile (self-computed, full 2011-2026) ...")
logret = np.log(SPOT).diff()
rv20 = logret.rolling(20).std() * np.sqrt(252)
rv20 = rv20.shift(1)

def expanding_pct_nolookahead(s: pd.Series, min_obs=60) -> pd.Series:
    vals = s.values
    hist = []
    out_pct = np.full(len(vals), np.nan)
    for i, v in enumerate(vals):
        if len(hist) >= min_obs and np.isfinite(v):
            lo = bisect.bisect_left(hist, v)
            hi = bisect.bisect_right(hist, v)
            out_pct[i] = 100.0 * (lo + hi) / 2.0 / len(hist)
        if np.isfinite(v):
            bisect.insort(hist, v)
    return pd.Series(out_pct, index=s.index)

RV_PCT = expanding_pct_nolookahead(rv20)
log(f"    rv20 valid {rv20.notna().sum()}, rv_pct valid {RV_PCT.notna().sum()}")

# ---------------------------------------------------------------- 4. IV-gate series (reused, not rebuilt)
log("[4] loading reused IV series (INVERSE_VRP_NICHE_20260729/daily_vol_series.csv) ...")
ivdf = pd.read_csv(IV_CSV, usecols=["day", "iv_pct"])
ivdf["day"] = pd.to_datetime(ivdf["day"])
IV_PCT = ivdf.set_index("day")["iv_pct"]
log(f"    {IV_PCT.notna().sum()} valid iv_pct rows, window {IV_PCT.index.min().date()}..{IV_PCT.index.max().date()}")

# ---------------------------------------------------------------- 5. BS helpers + cache-based lookups
def strike_for_target_delta(S, T, r, sigma, target_delta, is_call):
    if sigma <= 0 or T <= 0:
        return None
    if is_call:
        d1 = norm.ppf(target_delta)
    else:
        d1 = norm.ppf(1.0 + target_delta)
    lnSK = d1 * sigma * np.sqrt(T) - (r + 0.5 * sigma ** 2) * T
    return S * np.exp(-lnSK)

def expiry_is_tradeable(expiry, day, spot_today) -> bool:
    sub = cache.day_slice(day)
    if sub.empty:
        return False
    ce = sub[(sub["EXPIRY_DT"] == expiry) & (sub["OPTION_TYP"] == "CE") & (sub["CONTRACTS"] > 0)]
    if len(ce) < 3:
        return False
    near_money = ce[(ce["STRIKE_PR"] - spot_today).abs() <= 0.10 * spot_today]
    return len(near_money) > 0

def nearest_liquid_strike(expiry, otype, day, target_K, min_strike=None, max_strike=None):
    sub = cache.day_slice(day)
    if sub.empty:
        return None
    liquid = sub[(sub["EXPIRY_DT"] == expiry) & (sub["OPTION_TYP"] == otype) & (sub["CONTRACTS"] > 0)]
    if min_strike is not None:
        liquid = liquid[liquid["STRIKE_PR"] > min_strike]
    if max_strike is not None:
        liquid = liquid[liquid["STRIKE_PR"] < max_strike]
    if liquid.empty:
        return None
    # NOTE: `liquid`'s index is inherited from day_slice() = TIMESTAMP, i.e. every row shares the
    # SAME index label (this day). A label-based .loc[idxmin_label] on a non-unique index returns
    # ALL matching rows, not the nearest one -- must select POSITIONALLY (bug found + fixed here
    # after the first queue run crashed with "float() argument ... not 'Series'").
    strikes = liquid["STRIKE_PR"].to_numpy()
    diffs = np.abs(strikes - target_K)
    return float(strikes[np.argmin(diffs)])

def entry_close(day, expiry, otype, strike):
    sub = cache.day_slice(day)
    row = sub[(sub["EXPIRY_DT"] == expiry) & (sub["OPTION_TYP"] == otype) & (sub["STRIKE_PR"] == strike)]
    if row.empty:
        return None
    return float(row["CLOSE"].iloc[0])

def price_path(expiry, otype, strike, entry_day):
    s = cache.range_slice(entry_day, expiry)
    if s.empty:
        return None
    s = s[(s["EXPIRY_DT"] == expiry) & (s["OPTION_TYP"] == otype) & (s["STRIKE_PR"] == strike)]
    if s.empty:
        return None
    close_liquid = s["CLOSE"].where(s["CONTRACTS"] > 0)
    return pd.DataFrame({"close_ffill": close_liquid.ffill(), "contracts": s["CONTRACTS"]})

# ---------------------------------------------------------------- 6+7 fused: entry sequence + raw trades
def build_entries_and_trades(tenor_name, band):
    lo, hi, target = band
    seq = []
    raw = {}  # (delta, structure) -> list of trade dicts
    n = len(TRADING_DAYS)
    i = 0
    n_dropped = {"strike": 0, "wing": 0, "T": 0}
    while i < n:
        day = TRADING_DAYS[i]
        if day > OVERALL_END - pd.Timedelta(days=lo):
            break
        spot_entry = SPOT.get(day)
        if spot_entry is None or not np.isfinite(spot_entry):
            i += 1
            continue
        cands = [e for e in EXPIRIES if lo <= (e - day).days <= hi]
        cands.sort(key=lambda e: abs((e - day).days - target))
        chosen = None
        for e in cands:
            if expiry_is_tradeable(e, day, spot_entry):
                chosen = e
                break
        if chosen is None:
            i += 1
            continue
        expiry = chosen
        seq.append((day, expiry))
        i = bisect.bisect_right(TRADING_DAYS, expiry)

        spot_expiry = SPOT.get(expiry)
        sigma = rv20.get(day)
        T = (expiry - day).days / 365.0
        if spot_expiry is None or sigma is None or not np.isfinite(sigma) or T <= 0:
            n_dropped["T"] += 1
            continue

        for target_delta in DELTAS:
            Kc_t = strike_for_target_delta(spot_entry, T, R, sigma, target_delta, True)
            Kp_t = strike_for_target_delta(spot_entry, T, R, sigma, -target_delta, False)
            Kc = nearest_liquid_strike(expiry, "CE", day, Kc_t)
            Kp = nearest_liquid_strike(expiry, "PE", day, Kp_t)
            if Kc is None or Kp is None or abs(Kc - Kc_t) / spot_entry > STRIKE_TOL_FRAC \
               or abs(Kp - Kp_t) / spot_entry > STRIKE_TOL_FRAC:
                n_dropped["strike"] += 1
                continue
            ce_path = price_path(expiry, "CE", Kc, day)
            pe_path = price_path(expiry, "PE", Kp, day)
            if ce_path is None or pe_path is None:
                n_dropped["strike"] += 1
                continue
            ce_entry_px = entry_close(day, expiry, "CE", Kc)
            pe_entry_px = entry_close(day, expiry, "PE", Kp)
            if ce_entry_px is None or pe_entry_px is None:
                n_dropped["strike"] += 1
                continue
            base = dict(tenor=tenor_name, delta=target_delta, entry_day=day, expiry=expiry,
                        spot_entry=spot_entry, spot_expiry=spot_expiry, sigma=sigma,
                        Kc=Kc, Kp=Kp, ce_entry_px=ce_entry_px, pe_entry_px=pe_entry_px,
                        ce_path=ce_path, pe_path=pe_path)
            raw.setdefault((target_delta, "naked"), []).append(base)

            Kc_w = nearest_liquid_strike(expiry, "CE", day, Kc * (1 + WING_PCT), min_strike=Kc)
            Kp_w = nearest_liquid_strike(expiry, "PE", day, Kp * (1 - WING_PCT), max_strike=Kp)
            if Kc_w is None or Kp_w is None:
                n_dropped["wing"] += 1
                continue
            cew_path = price_path(expiry, "CE", Kc_w, day)
            pew_path = price_path(expiry, "PE", Kp_w, day)
            if cew_path is None or pew_path is None:
                n_dropped["wing"] += 1
                continue
            cew_entry_px = entry_close(day, expiry, "CE", Kc_w)
            pew_entry_px = entry_close(day, expiry, "PE", Kp_w)
            if cew_entry_px is None or pew_entry_px is None:
                n_dropped["wing"] += 1
                continue
            cbase = dict(base)
            cbase.update(Kc_w=Kc_w, Kp_w=Kp_w, cew_entry_px=cew_entry_px, pew_entry_px=pew_entry_px,
                         cew_path=cew_path, pew_path=pew_path)
            raw.setdefault((target_delta, "condor"), []).append(cbase)
    return seq, raw, n_dropped

log("[5/6/7] per-tenor chronological sweep (entry discovery + raw trade construction fused, "
    f"YearChainCache resident<= {CACHE_YEARS} yrs) ...")
raw_trades = {}   # (tenor, delta, structure) -> list of trade dicts
entry_seqs = {}
n_dropped_all = {}
for tenor_name, band in TENORS.items():
    ckpt_path = CKPT_DIR / f"raw_{tenor_name}.pkl"
    if ckpt_path.exists():
        with open(ckpt_path, "rb") as f:
            payload = pickle.load(f)
        seq, raw, ndrop = payload["seq"], payload["raw"], payload["ndrop"]
        log(f"    {tenor_name}: RESUMED from checkpoint ({len(seq)} entry cycles)")
    else:
        seq, raw, ndrop = build_entries_and_trades(tenor_name, band)
        with open(ckpt_path, "wb") as f:
            pickle.dump({"seq": seq, "raw": raw, "ndrop": ndrop}, f)
        log(f"    {tenor_name}: {len(seq)} entry cycles, "
            f"{seq[0][0].date() if seq else None}..{seq[-1][0].date() if seq else None}, dropped={ndrop} "
            f"(chain-year loads so far: {cache.n_loads})")
    entry_seqs[tenor_name] = seq
    n_dropped_all[tenor_name] = ndrop
    for (delta, structure), trades in raw.items():
        raw_trades[(tenor_name, delta, structure)] = trades
    gc.collect()

for k, v in raw_trades.items():
    log(f"    {k}: {len(v)} trades")

# ---------------------------------------------------------------- 8. cost helpers
def leg_cost_rs(n_legs, lot=LOT):
    return n_legs * (BROKERAGE_RS + SLIP_PT * lot)

def apply_management(mark_series, credit, mgmt):
    if mgmt == "hold" or mark_series is None or mark_series.empty:
        return None
    if mgmt == "buyback50":
        trig = mark_series[mark_series <= 0.5 * credit]
    elif mgmt == "stop2x":
        trig = mark_series[mark_series >= 2.0 * credit]
    else:
        return None
    if trig.empty:
        return None
    return trig.index[0], float(trig.iloc[0])

# ---------------------------------------------------------------- 9. simulate one (tenor,delta,structure,mgmt)
n_stale_wing_clips = 0  # diagnostic counter: forward-filled untraded strikes can print a mark
                        # that implies a NEGATIVE buy-back cost (arbitrage-free real markets can't
                        # do this; asynchronous stale EOD prints on illiquid far-OTM legs can). A
                        # credit position's buy-back cost is physically bounded below by 0 -- floor
                        # it there rather than let 2-in-2860 stale prints fabricate > 100%-of-credit
                        # P&L (caught by the L7b guard below on the FIRST run of this script).

def simulate(tenor, delta, structure, mgmt):
    global n_stale_wing_clips
    trades = raw_trades.get((tenor, delta, structure), [])
    out_rows = []
    for tr in trades:
        entry_day, expiry = tr["entry_day"], tr["expiry"]
        if structure == "naked":
            credit_pt = tr["ce_entry_px"] + tr["pe_entry_px"]
            mark = (tr["ce_path"]["close_ffill"] + tr["pe_path"]["close_ffill"]).dropna()
            n_legs_entry, n_legs_exit = 2, 2
            margin_rs = MARGIN_NAKED_PCT * tr["spot_entry"] * LOT
        else:
            credit_pt = (tr["ce_entry_px"] - tr["cew_entry_px"]) + (tr["pe_entry_px"] - tr["pew_entry_px"])
            ce_net = (tr["ce_path"]["close_ffill"] - tr["cew_path"]["close_ffill"])
            pe_net = (tr["pe_path"]["close_ffill"] - tr["pew_path"]["close_ffill"])
            mark = (ce_net + pe_net).dropna()
            n_legs_entry, n_legs_exit = 4, 4
            margin_rs = MARGIN_HEDGED_PCT * tr["spot_entry"] * LOT

        n_neg = int((mark < 0).sum())
        if n_neg:
            n_stale_wing_clips += n_neg
            mark = mark.clip(lower=0.0)

        trig = apply_management(mark, credit_pt, mgmt)
        entry_cost_rs = leg_cost_rs(n_legs_entry)

        if trig is not None:
            exit_day, exit_mark_pt = trig
            pl_pt = credit_pt - exit_mark_pt
            pl_rs_gross = pl_pt * LOT
            exit_cost_rs = leg_cost_rs(n_legs_exit)
            pl_rs_net = pl_rs_gross - entry_cost_rs - exit_cost_rs
            exit_reason = mgmt
        else:
            exit_day = expiry
            Sx = tr["spot_expiry"]
            if structure == "naked":
                intr_c, intr_p = max(Sx - tr["Kc"], 0.0), max(tr["Kp"] - Sx, 0.0)
                pl_pt = credit_pt - (intr_c + intr_p)
                pl_rs_gross = pl_pt * LOT
                exit_cost_rs = leg_cost_rs(2)
                stt_rs = 0.0
            else:
                intr_cs, intr_ps = max(Sx - tr["Kc"], 0.0), max(tr["Kp"] - Sx, 0.0)
                intr_cw, intr_pw = max(Sx - tr["Kc_w"], 0.0), max(tr["Kp_w"] - Sx, 0.0)
                pl_pt = credit_pt - ((intr_cs - intr_cw) + (intr_ps - intr_pw))
                pl_rs_gross = pl_pt * LOT
                exit_cost_rs = leg_cost_rs(4)
                stt_rs = STT_EXERCISE_PCT * (intr_cw + intr_pw) * LOT
            pl_rs_net = pl_rs_gross - entry_cost_rs - exit_cost_rs - stt_rs
            exit_reason = "expiry_itm" if (pl_pt < credit_pt) else "expiry_otm"

        margin_ret = pl_rs_net / margin_rs if margin_rs > 0 else np.nan
        out_rows.append(dict(tenor=tenor, delta=delta, structure=structure, mgmt=mgmt,
                              entry_day=entry_day, exit_day=exit_day, expiry=expiry,
                              credit_pt=credit_pt, pl_rs_gross=pl_rs_gross, pl_rs_net=pl_rs_net,
                              margin_rs=margin_rs, margin_ret=margin_ret, exit_reason=exit_reason,
                              spot_entry=tr["spot_entry"], spot_expiry=tr["spot_expiry"]))
    return pd.DataFrame(out_rows)

log("[8] running 54 base configs (3 tenor x 3 delta x 2 structure x 3 mgmt) ...")
all_results = {}
for tenor in TENORS:
    for delta in DELTAS:
        for structure in STRUCTURES:
            for mgmt in MGMTS:
                df = simulate(tenor, delta, structure, mgmt)
                all_results[(tenor, delta, structure, mgmt)] = df
log(f"    done, {len(all_results)} configs, elapsed {time.time()-t_start:.0f}s, "
    f"total chain-year loads={cache.n_loads}, stale-wing-mark clips (floored at 0)={n_stale_wing_clips}")

# ---------------------------------------------------------------- L7 guards: no future settlement,
# no physical-bound violation (a short premium position cannot net MORE than the credit collected)
for key, df in all_results.items():
    if df.empty:
        continue
    G.assert_no_future_settlement(df, exit_col="exit_day", data_max_date=DATA_MAX_DATE)
    max_gain_rs = df["credit_pt"] * LOT
    bad = (df["pl_rs_gross"] > max_gain_rs + 1e-6).sum()
    assert bad == 0, f"L7b physical bound: {bad} rows of {key} earn more than credit collected"

# ---------------------------------------------------------------- 10. metrics
def newey_west_t(x, lag=None):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 5:
        return np.nan, n
    if lag is None:
        lag = max(1, int(4 * (n / 100) ** (2 / 9)))
    mean = x.mean()
    resid = x - mean
    gamma0 = np.sum(resid ** 2) / n
    lrv = gamma0
    for l in range(1, min(lag, n - 1) + 1):
        gamma_l = np.sum(resid[l:] * resid[:-l]) / n
        lrv += 2 * (1 - l / (lag + 1)) * gamma_l
    lrv = max(lrv, 1e-12)
    se = np.sqrt(lrv / n)
    return mean / se if se > 0 else np.nan, n

def perf_metrics(df, ret_col="margin_ret", pl_col="pl_rs_net", label=""):
    if df.empty:
        return dict(label=label, n=0)
    df = df.sort_values("exit_day")
    rets = df[ret_col].values
    nav = np.cumprod(1 + np.nan_to_num(rets, nan=0.0))
    span_days = max((df["exit_day"].max() - df["entry_day"].min()).days, 1)
    years = span_days / 365.25
    cagr = nav[-1] ** (1 / years) - 1 if years > 0 and nav[-1] > 0 else np.nan
    run_max = np.maximum.accumulate(nav)
    dd = nav / run_max - 1
    maxdd = dd.min() if len(dd) else np.nan
    calmar = cagr / abs(maxdd) if maxdd and maxdd < 0 else np.nan
    trades_per_year = len(df) / years if years > 0 else np.nan
    sharpe = (np.nanmean(rets) / np.nanstd(rets)) * np.sqrt(trades_per_year) if np.nanstd(rets) > 0 else np.nan
    wins = df[df.pl_rs_net > 0]["pl_rs_net"].sum() if pl_col in df else np.nan
    losses = -df[df.pl_rs_net < 0]["pl_rs_net"].sum() if pl_col in df else np.nan
    pf = wins / losses if losses and losses > 0 else np.nan
    t_stat, n_t = newey_west_t(df[pl_col].values)
    monthly = df.set_index("exit_day")[pl_col].resample("ME").sum()
    win_rate_m = (monthly > 0).mean() if len(monthly) else np.nan
    worst_day_rs = df[pl_col].min()
    worst_day_pct_margin = (df[pl_col] / df["margin_rs"]).min()
    worst_month = monthly.min() if len(monthly) else np.nan
    worst_month_pct = (monthly / df.set_index("exit_day")["margin_rs"].resample("ME").mean()).min() if len(monthly) else np.nan
    return dict(label=label, n=len(df), cagr=cagr, maxdd=maxdd, calmar=calmar, sharpe=sharpe,
                pf=pf, nw_t=t_stat, win_rate_monthly=win_rate_m, worst_day_rs=worst_day_rs,
                worst_day_pct_margin=worst_day_pct_margin, worst_month_rs=worst_month,
                worst_month_pct_margin=worst_month_pct, trades_per_year=trades_per_year,
                span_start=str(df.entry_day.min().date()), span_end=str(df.exit_day.max().date()))

# ---------------------------------------------------------------- 11. build/held-out split + summary table
log("[9] computing build/held-out metrics for all 54 configs ...")
summary_rows = []
for key, df in all_results.items():
    tenor, delta, structure, mgmt = key
    build = df[df.exit_day <= BUILD_END]
    held = df[df.entry_day >= HELDOUT_START]
    gross_m = perf_metrics(build, ret_col="margin_ret", pl_col="pl_rs_gross", label="build_gross")
    net_m = perf_metrics(build, ret_col="margin_ret", pl_col="pl_rs_net", label="build_net")
    held_net_m = perf_metrics(held, ret_col="margin_ret", pl_col="pl_rs_net", label="held_net")
    held_gross_m = perf_metrics(held, ret_col="margin_ret", pl_col="pl_rs_gross", label="held_gross")
    summary_rows.append(dict(tenor=tenor, delta=delta, structure=structure, mgmt=mgmt,
                              **{f"build_net_{k}": v for k, v in net_m.items() if k != "label"},
                              **{f"build_gross_cagr": gross_m.get("cagr"), "build_gross_pf": gross_m.get("pf"),
                                 "build_gross_winrate_m": gross_m.get("win_rate_monthly")},
                              **{f"held_net_{k}": v for k, v in held_net_m.items() if k != "label"},
                              **{f"held_gross_cagr": held_gross_m.get("cagr"), "held_gross_pf": held_gross_m.get("pf"),
                                 "held_gross_winrate_m": held_gross_m.get("win_rate_monthly")}))
summary = pd.DataFrame(summary_rows)
summary.to_csv(OUT / "config_grid_summary.csv", index=False)
log(f"    wrote config_grid_summary.csv ({len(summary)} rows)")

valid = summary[summary.build_net_n >= 20].copy()
valid = valid.sort_values(["build_net_sharpe", "build_net_calmar"], ascending=False)
best = valid.iloc[0] if len(valid) else summary.sort_values("build_net_n", ascending=False).iloc[0]
best_key = (best.tenor, best.delta, best.structure, best.mgmt)
log(f"    BEST base config by build-window net Sharpe: {best_key} "
    f"(sharpe={best.get('build_net_sharpe')}, calmar={best.get('build_net_calmar')})")

# ---------------------------------------------------------------- 12. overlay tests on best config (+3 trials)
log("[10] overlay tests on best config: IV-gate, RV-skip, both stacked ...")
best_df = all_results[best_key].copy()
best_df["iv_pct_entry"] = best_df["entry_day"].map(IV_PCT)
best_df["rv_pct_entry"] = best_df["entry_day"].map(RV_PCT)

iv_window = best_df[(best_df.entry_day >= IV_WIN_START) & (best_df.entry_day <= IV_WIN_END)]
overlay_rows = []
overlay_rows.append(dict(overlay="baseline_in_iv_window",
                          **perf_metrics(iv_window, pl_col="pl_rs_net", label="baseline_in_iv_window")))
iv_gated = iv_window[iv_window.iv_pct_entry >= 90]
overlay_rows.append(dict(overlay="iv_gate_top_decile",
                          **perf_metrics(iv_gated, pl_col="pl_rs_net", label="iv_gate_top_decile")))
rv_skipped = best_df[(best_df.rv_pct_entry < 90) | best_df.rv_pct_entry.isna()]
overlay_rows.append(dict(overlay="rv_regime_skip_full_period",
                          **perf_metrics(rv_skipped, pl_col="pl_rs_net", label="rv_regime_skip_full_period")))
both = iv_window[(iv_window.iv_pct_entry >= 90) & ((iv_window.rv_pct_entry < 90) | iv_window.rv_pct_entry.isna())]
overlay_rows.append(dict(overlay="iv_gate_AND_rv_skip",
                          **perf_metrics(both, pl_col="pl_rs_net", label="iv_gate_AND_rv_skip")))
overlay_df = pd.DataFrame(overlay_rows)
overlay_df.to_csv(OUT / "overlay_tests.csv", index=False)
log(f"    wrote overlay_tests.csv\n{overlay_df.to_string()}")

# ---------------------------------------------------------------- 13. tail / era slices on best config
log("[11] tail and era-slice reporting on best config (descriptive, not selected on) ...")
era_windows = {
    "2015-16": ("2015-01-01", "2016-12-31"),
    "2018": ("2018-01-01", "2018-12-31"),
    "2020_covid": ("2020-01-01", "2020-12-31"),
    "2024-09": ("2024-08-15", "2024-10-31"),
}
era_rows = []
for name, (s, e) in era_windows.items():
    sub = best_df[(best_df.exit_day >= s) & (best_df.exit_day <= e)]
    era_rows.append(dict(era=name, n=len(sub), gross_rs=sub.pl_rs_gross.sum() if len(sub) else np.nan,
                          net_rs=sub.pl_rs_net.sum() if len(sub) else np.nan,
                          worst_trade_rs=sub.pl_rs_net.min() if len(sub) else np.nan,
                          worst_trade_pct_margin=(sub.pl_rs_net / sub.margin_rs).min() if len(sub) else np.nan))
era_df = pd.DataFrame(era_rows)
era_df.to_csv(OUT / "era_slices_best_config.csv", index=False)
log(f"    wrote era_slices_best_config.csv\n{era_df.to_string()}")

best_df.to_csv(OUT / "best_config_trades.csv", index=False)

all_trades_rows = []
for key, df in all_results.items():
    if df.empty:
        continue
    d = df.copy()
    d["tenor"], d["delta"], d["structure"], d["mgmt"] = key
    all_trades_rows.append(d)
if all_trades_rows:
    pd.concat(all_trades_rows, ignore_index=True).to_csv(OUT / "all_trades_full_grid.csv", index=False)
    log("    wrote all_trades_full_grid.csv")

# ---------------------------------------------------------------- 14. trials ledger entries
trials = []
for key in all_results:
    trials.append(dict(family="longdated_selling_20260730", config=str(key), n_trials_component=1))
for row in overlay_rows:
    # "baseline_in_iv_window" is a reporting baseline (same-window comparator for the gate), not a
    # new pre-registered trial -- PREREG.md counts exactly 3 overlay trials (IV-gate, RV-skip,
    # both stacked). Excluding it here keeps this ledger matching PREREG's fixed count of 57.
    if row["overlay"] == "baseline_in_iv_window":
        continue
    trials.append(dict(family="longdated_selling_20260730", config=f"overlay:{row['overlay']}", n_trials_component=1))
trials_df = pd.DataFrame(trials)
trials_df.to_csv(OUT / "trials_this_arm.csv", index=False)
log(f"    TOTAL TRIALS THIS ARM: {len(trials_df)} (pre-registered as 57 in PREREG.md)")

meta = dict(elapsed_seconds=round(time.time() - t_start, 1), n_configs=len(all_results),
            best_config=str(best_key), trading_days=len(TRADING_DAYS),
            expiries=len(EXPIRIES), dropped=n_dropped_all, lot_used=LOT,
            lot_correction_note="PREREG.md/original script used stale LOT=75; corrected to firm's "
                                 "current LOT=65 (effective Jan-2026, SESSION_JOURNAL) -- data "
                                 "correction, not a grid change.",
            chain_year_loads_total=cache.n_loads, cache_years_resident=CACHE_YEARS,
            stale_wing_mark_clips=n_stale_wing_clips,
            stale_wing_note="forward-filled untraded far-OTM wing/short CLOSE prints occasionally "
                             "imply a negative buy-back cost (asynchronous stale EOD quotes, not a "
                             "real arb) -- floored mark at 0 before applying mgmt triggers; count is "
                             "the total bars affected across all 54 configs, see L7b guard above.")
(OUT / "run_meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
(OUT / "run_log_peryear.txt").write_text("\n".join(LOG_LINES), encoding="utf-8")
log(f"[DONE] {json.dumps(meta, default=str)}")

# clean up checkpoints on successful completion (job is done, no need to resume)
for tenor_name in TENORS:
    ck = CKPT_DIR / f"raw_{tenor_name}.pkl"
    if ck.exists():
        ck.unlink()
