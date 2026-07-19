# -*- coding: utf-8 -*-
"""
FAST PREVIEW backtest: ITM-Sell / 2x-OTM-Hedge premium-ratio system, 2025-2026 window only.
Mechanics per PREREG.md (../PREREG.md) sections 1-2, EXACTLY as pre-registered, restricted to:
  - window 2025-01-01 -> latest 2026 data available
  - MONTHLY expiry only
  - Cell A (two-sided) and Cell B (bull-only) only
  - NO placebo battery / lag test / sensitivity grid (that's the full run's job)

Labeled PREVIEW - ungated, NOT certified. See QUICK_RESULTS.md for the label and caveats.
"""
import os
import sys
import bisect
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\ITMPE_RATIO_BT_20260718\QUICK_2025_2026"
os.makedirs(OUT, exist_ok=True)

WINDOW_START = pd.Timestamp('2025-01-01')
PREMIUM_TARGET = 500.0
HEDGE_FRAC = 0.15
SEED = 42
np.random.seed(SEED)

log_lines = []
def log(msg):
    print(msg)
    log_lines.append(str(msg))

# ============================================================
# 1. LOAD SPOT (Nifty 50) + signal
# ============================================================
spot = pd.read_parquet(ROOT + r"\datasets\index_daily\nse_official_all_indices.parquet")
spot = spot[spot['index_name'] == 'Nifty 50'].copy()
spot['date'] = pd.to_datetime(spot['date'])
spot = spot.sort_values('date').drop_duplicates('date').reset_index(drop=True)
spot['dma20'] = spot['close'].rolling(20).mean()
spot['dma50'] = spot['close'].rolling(50).mean()
spot['bull'] = (spot['close'] > spot['dma20']) | (spot['close'] > spot['dma50'])
spot = spot.set_index('date')

# India VIX for the descriptive premium->ITM-depth mapping
vix = pd.read_parquet(ROOT + r"\datasets\index_daily\nse_official_all_indices.parquet")
vix = vix[vix['index_name'] == 'India VIX'].copy()
vix['date'] = pd.to_datetime(vix['date'])
vix = vix.sort_values('date').drop_duplicates('date').set_index('date')['close']

log(f"[DATA] spot 'Nifty 50' rows={len(spot)} range={spot.index.min().date()}..{spot.index.max().date()} "
    f"file=datasets/index_daily/nse_official_all_indices.parquet")

# ============================================================
# 2. LOAD OPTIONS (fo_idx bhavcopy 2024-2026, NIFTY OPTIDX only)
# ============================================================
frames = []
for yr in [2024, 2025, 2026]:
    f = ROOT + rf"\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\fo_bhavcopy_hist\fo_idx_{yr}.parquet"
    d = pd.read_parquet(f)
    d = d[(d.SYMBOL == 'NIFTY') & (d.INSTRUMENT == 'OPTIDX') & (d.OPTION_TYP.isin(['CE', 'PE']))].copy()
    log(f"[DATA] {f} yr={yr} NIFTY-OPTIDX-CE/PE rows={len(d)}")
    frames.append(d)
opt = pd.concat(frames, ignore_index=True)
opt['TIMESTAMP_dt'] = pd.to_datetime(opt['TIMESTAMP'], format='%d-%b-%Y', errors='coerce')
opt['EXPIRY_DT_dt'] = pd.to_datetime(opt['EXPIRY_DT'], format='%d-%b-%Y', errors='coerce')
before = len(opt)
opt = opt.dropna(subset=['TIMESTAMP_dt', 'EXPIRY_DT_dt'])
log(f"[DATA] combined options rows={before} -> {len(opt)} after date parse; "
    f"TIMESTAMP range {opt['TIMESTAMP_dt'].min().date()}..{opt['TIMESTAMP_dt'].max().date()}")

DATA_MAX = min(spot.index.max(), opt['TIMESTAMP_dt'].max())
log(f"[DATA] effective DATA_MAX (min of spot/options) = {DATA_MAX.date()}")

# is_monthly: last EXPIRY_DT within its own (year,month) group -- DATA_MAP.md §4.1 method
exp_ym = opt['EXPIRY_DT_dt'].dt.to_period('M')
max_exp_per_ym = opt.groupby(exp_ym)['EXPIRY_DT_dt'].transform('max')
opt['is_monthly'] = opt['EXPIRY_DT_dt'] == max_exp_per_ym

# attach spot close for moneyness
opt['spot_close'] = opt['TIMESTAMP_dt'].map(spot['close'])
before = len(opt)
opt = opt.dropna(subset=['spot_close'])
log(f"[DATA] rows with spot_close match: {before} -> {len(opt)}")

# trading-day calendar (spot index, restricted to a window with buffer before WINDOW_START)
calendar_all = sorted(spot.index[(spot.index >= pd.Timestamp('2024-11-01')) & (spot.index <= DATA_MAX)])

def next_trading_day(d):
    idx = bisect.bisect_right(calendar_all, d)
    if idx < len(calendar_all):
        return calendar_all[idx]
    return None

def snap_forward(d):
    idx = bisect.bisect_left(calendar_all, d)
    if idx < len(calendar_all):
        return calendar_all[idx]
    return None

def trading_days_between(start, end):
    i0 = bisect.bisect_left(calendar_all, start)
    i1 = bisect.bisect_right(calendar_all, end)
    return calendar_all[i0:i1]

# monthly expiries within [WINDOW_START, DATA_MAX]
monthly_expiries_all = sorted(pd.Timestamp(e) for e in opt.loc[opt.is_monthly, 'EXPIRY_DT_dt'].unique())
monthly_expiries = [e for e in monthly_expiries_all if WINDOW_START <= e <= DATA_MAX]
log(f"[DATA] monthly expiries in window ({WINDOW_START.date()}..{DATA_MAX.date()}): {len(monthly_expiries)}")
for e in monthly_expiries:
    log(f"    {e.date()}")

# build cycles: cycle i starts at WINDOW_START (snapped) for i=0, else next trading day after expiry[i-1]
cycles = []
for i, e in enumerate(monthly_expiries):
    if i == 0:
        start = snap_forward(WINDOW_START)
    else:
        start = next_trading_day(monthly_expiries[i - 1])
    if start is None or start > e:
        continue
    cycles.append((i + 1, start, e))
log(f"[DATA] cycles built: {len(cycles)} (first {cycles[0][1].date()}..{cycles[0][2].date()}, "
    f"last {cycles[-1][1].date()}..{cycles[-1][2].date()})" if cycles else "NO CYCLES")

# day-slice cache for strike search
opt_by_day = {ts: df for ts, df in opt.groupby('TIMESTAMP_dt')}

def pick_strike(day, expiry, opttype, moneyness, spot_close, target_premium):
    """moneyness in {'ITM_PE','ITM_CE','OTM_PE','OTM_CE'}. Returns (row, stale_flag) or (None, None)."""
    df = opt_by_day.get(day)
    if df is None:
        return None, None
    cand = df[(df.EXPIRY_DT_dt == expiry) & (df.OPTION_TYP == opttype)]
    if moneyness == 'ITM_PE':
        cand = cand[cand.STRIKE_PR > spot_close]
    elif moneyness == 'ITM_CE':
        cand = cand[cand.STRIKE_PR < spot_close]
    elif moneyness == 'OTM_PE':
        cand = cand[cand.STRIKE_PR < spot_close]
    elif moneyness == 'OTM_CE':
        cand = cand[cand.STRIKE_PR > spot_close]
    if len(cand) == 0:
        return None, None
    cand_liquid = cand[cand.CONTRACTS > 0]
    stale = len(cand_liquid) == 0
    use = cand_liquid if not stale else cand
    if len(use) == 0:
        return None, None
    use = use.copy()
    use['gap'] = (use['CLOSE'] - target_premium).abs()
    row = use.loc[use['gap'].idxmin()]
    return row, stale

# daily close lookup for MTM (forward-filled, flags stale)
opt_close_idx = opt.set_index(['EXPIRY_DT_dt', 'OPTION_TYP', 'STRIKE_PR', 'TIMESTAMP_dt']).sort_index()

def get_close_series(expiry, opttype, strike, days):
    try:
        sub = opt_close_idx.loc[(expiry, opttype, strike)]
    except KeyError:
        sub = None
    out = {}
    stale = {}
    last = None
    last_contracts_ok = None
    for d in days:
        if sub is not None and d in sub.index:
            row = sub.loc[d]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            c = row['CLOSE']
            ok = row['CONTRACTS'] > 0
            out[d] = c
            stale[d] = not ok
            last = c
        else:
            out[d] = last
            stale[d] = True
    return out, stale

def lot_size_for(expiry):
    return 75 if expiry.year == 2025 else 65

# ============================================================
# 3. Cost model (COST_STANDARDS.md D-021, PREREG §2.5)
# ============================================================
def leg_txn(action, close_price, qty_lots, lot_size):
    """action: 'SELL' (opening short or closing a long) or 'BUY' (opening long or closing a short).
       Returns dict with 'net' and 'x2' sub-dicts: fill, fees, cashflow, turnover."""
    out = {}
    for mult, tag in [(1.0, 'net'), (2.0, 'x2')]:
        slip = max(0.05, 0.0025 * close_price) * mult
        fill = close_price - slip if action == 'SELL' else close_price + slip
        turnover = fill * qty_lots * lot_size
        stt = 0.001 * turnover * mult if action == 'SELL' else 0.0
        exch = 0.00035 * turnover * mult
        brokerage = 20.0 * mult
        sebi = 10.0 * turnover / 1e7 * mult
        gst = 0.18 * (brokerage + exch + sebi)
        stamp = 0.00003 * turnover * mult if action == 'BUY' else 0.0
        fees = stt + exch + brokerage + sebi + gst + stamp
        cashflow = (fill * qty_lots * lot_size - fees) if action == 'SELL' else (-(fill * qty_lots * lot_size) - fees)
        out[tag] = dict(fill=fill, fees=fees, cashflow=cashflow, turnover=turnover)
    return out

def expiry_txn(intrinsic, qty_lots, lot_size, side):
    """side: 'SHORT' or 'LONG'. Auto cash-settlement at expiry -- STT on exercise only, no brokerage/exchange/slippage."""
    out = {}
    for mult, tag in [(1.0, 'net'), (2.0, 'x2')]:
        turnover = intrinsic * qty_lots * lot_size
        stt = 0.00125 * turnover * mult if intrinsic > 0 else 0.0
        fees = stt
        cashflow = (-turnover - fees) if side == 'SHORT' else (turnover - fees)
        out[tag] = dict(fees=fees, cashflow=cashflow, turnover=turnover)
    return out

# ============================================================
# 4. Simulation engine
# ============================================================
ledger_rows = []
# daily_pnl[cell][mult][date] = pnl contribution ; active_side[cell][date] = 'PE'/'CE'/'CASH'
daily_pnl = {'A': {'net': {}, 'x2': {}}, 'B': {'net': {}, 'x2': {}}}
active_side = {'A': {}, 'B': {}}
premium_depth_log = []  # empirical premium->ITM depth mapping
cycle_pnl = {'A': [], 'B': []}  # list of (cycle_no, start, end, pnl_net, pnl_x2, entry_signal)
warnings = []

def add_pnl(cell, date, net_amt, x2_amt):
    daily_pnl[cell]['net'][date] = daily_pnl[cell]['net'].get(date, 0.0) + net_amt
    daily_pnl[cell]['x2'][date] = daily_pnl[cell]['x2'].get(date, 0.0) + x2_amt

def open_structure(cell, cycle_no, day, expiry, side, lot_size, struct_id):
    """side: 'PE' or 'CE' (short-ITM + 2x hedge-OTM same side). Returns dict with strikes/fills or None if data missing."""
    spot_c = spot.loc[day, 'close']
    itm_kind = 'ITM_PE' if side == 'PE' else 'ITM_CE'
    otm_kind = 'OTM_PE' if side == 'PE' else 'OTM_CE'
    short_row, short_stale = pick_strike(day, expiry, side, itm_kind, spot_c, PREMIUM_TARGET)
    if short_row is None:
        warnings.append(f"{cell} cyc{cycle_no} {day.date()}: no ITM {side} strike found, structure open FAILED")
        return None
    short_txn = leg_txn('SELL', short_row['CLOSE'], 1, lot_size)
    hedge_target = HEDGE_FRAC * short_row['CLOSE']
    hedge_row, hedge_stale = pick_strike(day, expiry, side, otm_kind, spot_c, hedge_target)
    if hedge_row is None:
        warnings.append(f"{cell} cyc{cycle_no} {day.date()}: no OTM {side} hedge strike found, structure open FAILED")
        return None
    hedge_txn = leg_txn('BUY', hedge_row['CLOSE'], 2, lot_size)

    add_pnl(cell, day, short_txn['net']['cashflow'] + hedge_txn['net']['cashflow'],
            short_txn['x2']['cashflow'] + hedge_txn['x2']['cashflow'])

    itm_depth = abs(short_row['STRIKE_PR'] - spot_c)
    premium_depth_log.append(dict(cell=cell, cycle=cycle_no, date=day, side=side,
                                   strike=short_row['STRIKE_PR'], spot=spot_c,
                                   premium=short_row['CLOSE'], itm_depth=itm_depth,
                                   vix=vix.get(day, np.nan)))

    ledger_rows.append(dict(cell=cell, cycle=cycle_no, struct_id=struct_id, leg='SHORT_ITM', side=side,
                             action='SELL_OPEN', date=day.date(), expiry=expiry.date(),
                             strike=short_row['STRIKE_PR'], qty_lots=1,
                             premium_in=short_txn['net']['fill'], premium_out=np.nan,
                             itm_otm_depth=itm_depth, stale_fill=short_stale,
                             fees_net=short_txn['net']['fees'], fees_x2=short_txn['x2']['fees'],
                             cashflow_net=short_txn['net']['cashflow'], cashflow_x2=short_txn['x2']['cashflow']))
    ledger_rows.append(dict(cell=cell, cycle=cycle_no, struct_id=struct_id, leg='HEDGE_OTM', side=side,
                             action='BUY_OPEN', date=day.date(), expiry=expiry.date(),
                             strike=hedge_row['STRIKE_PR'], qty_lots=2,
                             premium_in=np.nan, premium_out=hedge_txn['net']['fill'],
                             itm_otm_depth=abs(hedge_row['STRIKE_PR'] - spot_c), stale_fill=hedge_stale,
                             fees_net=hedge_txn['net']['fees'], fees_x2=hedge_txn['x2']['fees'],
                             cashflow_net=hedge_txn['net']['cashflow'], cashflow_x2=hedge_txn['x2']['cashflow']))

    return dict(side=side, expiry=expiry, lot_size=lot_size,
                short_strike=short_row['STRIKE_PR'], short_entry_close=short_row['CLOSE'],
                hedge_strike=hedge_row['STRIKE_PR'], hedge_entry_close=hedge_row['CLOSE'],
                short_entry_date=day, hedge_entry_date=day,
                net_credit=short_row['CLOSE'] - 2 * hedge_row['CLOSE'])

def close_structure_flip_or_cash(cell, cycle_no, day, pos, struct_id, reason):
    """Close both legs at day's real CLOSE (BUY-to-cover short, SELL-to-close hedge)."""
    spot_c = spot.loc[day, 'close']
    short_row, short_stale = None, True
    df = opt_by_day.get(day)
    if df is not None:
        m = df[(df.EXPIRY_DT_dt == pos['expiry']) & (df.OPTION_TYP == pos['side']) & (df.STRIKE_PR == pos['short_strike'])]
        if len(m) > 0:
            short_row = m.iloc[0]
            short_stale = short_row['CONTRACTS'] <= 0
    if short_row is None:
        warnings.append(f"{cell} cyc{cycle_no} {day.date()}: short leg strike {pos['short_strike']} untraded on close day, using last mark")
        short_close = pos['short_entry_close']
    else:
        short_close = short_row['CLOSE']
    short_txn = leg_txn('BUY', short_close, 1, pos['lot_size'])

    hedge_row = None
    if df is not None:
        m2 = df[(df.EXPIRY_DT_dt == pos['expiry']) & (df.OPTION_TYP == pos['side']) & (df.STRIKE_PR == pos['hedge_strike'])]
        if len(m2) > 0:
            hedge_row = m2.iloc[0]
    hedge_close = hedge_row['CLOSE'] if hedge_row is not None else pos['hedge_entry_close']
    hedge_txn = leg_txn('SELL', hedge_close, 2, pos['lot_size'])

    add_pnl(cell, day, short_txn['net']['cashflow'] + hedge_txn['net']['cashflow'],
            short_txn['x2']['cashflow'] + hedge_txn['x2']['cashflow'])

    ledger_rows.append(dict(cell=cell, cycle=cycle_no, struct_id=struct_id, leg='SHORT_ITM', side=pos['side'],
                             action=f'BUY_CLOSE_{reason}', date=day.date(), expiry=pos['expiry'].date(),
                             strike=pos['short_strike'], qty_lots=1,
                             premium_in=np.nan, premium_out=short_txn['net']['fill'],
                             itm_otm_depth=abs(pos['short_strike'] - spot_c), stale_fill=short_stale,
                             fees_net=short_txn['net']['fees'], fees_x2=short_txn['x2']['fees'],
                             cashflow_net=short_txn['net']['cashflow'], cashflow_x2=short_txn['x2']['cashflow']))
    ledger_rows.append(dict(cell=cell, cycle=cycle_no, struct_id=struct_id, leg='HEDGE_OTM', side=pos['side'],
                             action=f'SELL_CLOSE_{reason}', date=day.date(), expiry=pos['expiry'].date(),
                             strike=pos['hedge_strike'], qty_lots=2,
                             premium_in=hedge_txn['net']['fill'], premium_out=np.nan,
                             itm_otm_depth=abs(pos['hedge_strike'] - spot_c), stale_fill=(hedge_row is None),
                             fees_net=hedge_txn['net']['fees'], fees_x2=hedge_txn['x2']['fees'],
                             cashflow_net=hedge_txn['net']['cashflow'], cashflow_x2=hedge_txn['x2']['cashflow']))

def settle_expiry(cell, cycle_no, expiry_day, pos, struct_id):
    spot_c = spot.loc[expiry_day, 'close']
    if pos['side'] == 'PE':
        short_intrinsic = max(0.0, pos['short_strike'] - spot_c)
        hedge_intrinsic = max(0.0, pos['hedge_strike'] - spot_c)
    else:
        short_intrinsic = max(0.0, spot_c - pos['short_strike'])
        hedge_intrinsic = max(0.0, spot_c - pos['hedge_strike'])
    short_e = expiry_txn(short_intrinsic, 1, pos['lot_size'], 'SHORT')
    hedge_e = expiry_txn(hedge_intrinsic, 2, pos['lot_size'], 'LONG')
    add_pnl(cell, expiry_day, short_e['net']['cashflow'] + hedge_e['net']['cashflow'],
            short_e['x2']['cashflow'] + hedge_e['x2']['cashflow'])
    ledger_rows.append(dict(cell=cell, cycle=cycle_no, struct_id=struct_id, leg='SHORT_ITM', side=pos['side'],
                             action='EXPIRY_SETTLE', date=expiry_day.date(), expiry=pos['expiry'].date(),
                             strike=pos['short_strike'], qty_lots=1,
                             premium_in=np.nan, premium_out=short_intrinsic,
                             itm_otm_depth=abs(pos['short_strike'] - spot_c), stale_fill=False,
                             fees_net=short_e['net']['fees'], fees_x2=short_e['x2']['fees'],
                             cashflow_net=short_e['net']['cashflow'], cashflow_x2=short_e['x2']['cashflow']))
    ledger_rows.append(dict(cell=cell, cycle=cycle_no, struct_id=struct_id, leg='HEDGE_OTM', side=pos['side'],
                             action='EXPIRY_SETTLE', date=expiry_day.date(), expiry=pos['expiry'].date(),
                             strike=pos['hedge_strike'], qty_lots=2,
                             premium_in=hedge_intrinsic, premium_out=np.nan,
                             itm_otm_depth=abs(pos['hedge_strike'] - spot_c), stale_fill=False,
                             fees_net=hedge_e['net']['fees'], fees_x2=hedge_e['x2']['fees'],
                             cashflow_net=hedge_e['net']['cashflow'], cashflow_x2=hedge_e['x2']['cashflow']))

# NOTE: earlier draft had a mtm_mark() that added interim daily price-path deltas into the SAME
# daily_pnl accumulator that also receives the lump-sum open/close/expiry cashflows. Since the
# open cashflow already books the full entry fill and the close/expiry cashflow already books the
# full exit fill (their difference already IS the leg's total P&L), adding interim daily deltas on
# top double-counted the entry-to-exit price move. CAUGHT via manual ledger reconciliation on
# cycle 16/cell A (ledger cashflows summed to -73,501 vs a reported -137,361 before the fix).
# Fix: daily_pnl now holds ONLY realized (ledger) cashflows -- the authoritative, auditable P&L
# source for every headline stat. A separate, non-accumulating unrealized-MTM overlay is computed
# in the equity-curve section below purely for the chart (PREREG §2.8), and nets to zero at every
# realization event so it never contaminates the realized total.

# ---- run one cell ----
def run_cell(cell):
    struct_counter = 0
    for cycle_no, cstart, cend in cycles:
        days = trading_days_between(cstart, cend)
        pos = None
        prev_short_mark = None
        prev_hedge_mark = None
        entry_signal = None
        cyc_pnl_before = sum(daily_pnl[cell]['net'].values())
        pending = None  # dict(effective_date=..., type='FLIP'/'EXIT_CASH', new_side=...)

        for di, day in enumerate(days):
            b = bool(spot.loc[day, 'bull'])

            # 0. day 0 of cycle: open per roll rule
            if di == 0:
                entry_signal = 'bull' if b else 'bear'
                if cell == 'A':
                    side = 'PE' if b else 'CE'
                    struct_counter += 1
                    pos = open_structure(cell, cycle_no, day, cend, side, lot_size_for(cend), struct_counter)
                    if pos:
                        prev_short_mark, prev_hedge_mark = pos['short_entry_close'], pos['hedge_entry_close']
                        active_side[cell][day] = side
                else:  # cell B
                    if b:
                        struct_counter += 1
                        pos = open_structure(cell, cycle_no, day, cend, 'PE', lot_size_for(cend), struct_counter)
                        if pos:
                            prev_short_mark, prev_hedge_mark = pos['short_entry_close'], pos['hedge_entry_close']
                            active_side[cell][day] = 'PE'
                    else:
                        pos = None
                        active_side[cell][day] = 'CASH'
                continue

            # 1. Execute pending action scheduled for today
            if pending is not None and pending['effective_date'] == day:
                if pending['type'] == 'FLIP' and pos is not None:
                    close_structure_flip_or_cash(cell, cycle_no, day, pos, struct_counter, 'FLIP')
                    struct_counter += 1
                    pos = open_structure(cell, cycle_no, day, cend, pending['new_side'], lot_size_for(cend), struct_counter)
                    if pos:
                        prev_short_mark, prev_hedge_mark = pos['short_entry_close'], pos['hedge_entry_close']
                elif pending['type'] == 'EXIT_CASH' and pos is not None:
                    close_structure_flip_or_cash(cell, cycle_no, day, pos, struct_counter, 'EXITCASH')
                    pos = None
                pending = None

            # 2. Cell B: same-day cash-entry when signal first turns bull (daily check)
            if cell == 'B' and pos is None and b:
                struct_counter += 1
                pos = open_structure(cell, cycle_no, day, cend, 'PE', lot_size_for(cend), struct_counter)
                if pos:
                    prev_short_mark, prev_hedge_mark = pos['short_entry_close'], pos['hedge_entry_close']

            # 3. track which side is active today (for bear-side P&L attribution) -- NO P&L booked here;
            #    realized P&L comes only from the lump-sum open/close/expiry cashflows above.
            if pos is not None:
                active_side[cell][day] = pos['side']
            else:
                active_side[cell][day] = 'CASH'

            # 4. weekly Tuesday check (only if currently holding, and no pending already queued)
            if day.weekday() == 1 and pos is not None and pending is None:
                if cell == 'A':
                    desired = 'PE' if b else 'CE'
                    if desired != pos['side']:
                        nd = next_trading_day(day)
                        if nd is not None and nd <= cend:
                            pending = dict(effective_date=nd, type='FLIP', new_side=desired)
                else:  # cell B
                    if not b:
                        nd = next_trading_day(day)
                        if nd is not None and nd <= cend:
                            pending = dict(effective_date=nd, type='EXIT_CASH')

            # 5. expiry settlement
            if day == cend and pos is not None:
                settle_expiry(cell, cycle_no, day, pos, struct_counter)
                pos = None
                active_side[cell][day] = 'SETTLED_' + (active_side[cell].get(day, 'PE'))

        cyc_pnl_after = sum(daily_pnl[cell]['net'].values())
        cyc_pnl_after_x2 = sum(daily_pnl[cell]['x2'].values())
        cycle_pnl[cell].append(dict(cycle=cycle_no, start=cstart.date(), end=cend.date(),
                                     entry_signal=entry_signal,
                                     pnl_net=cyc_pnl_after - cyc_pnl_before))

run_cell('A')
run_cell('B')

log(f"[INFO] warnings during simulation: {len(warnings)}")
for w in warnings[:30]:
    log("  WARN: " + w)

# ============================================================
# 5. Save ledger
# ============================================================
ledger_df = pd.DataFrame(ledger_rows)
ledger_path = OUT + r"\quick_trade_ledger.csv"
ledger_df.to_csv(ledger_path, index=False)
log(f"[OUTPUT] {ledger_path} rows={len(ledger_df)}")

# ============================================================
# 6. Build equity curves + drawdown
#    equity_net/equity_x2 = cumsum of REALIZED (ledger) cashflows only -- authoritative, matches
#    cycle_pnl exactly, immune to the double-count bug caught above.
#    equity_net_mtm = same realized cumsum PLUS an unrealized mark-to-market overlay for whatever
#    leg-intervals are open on day t (built fresh from the ledger's own entry/exit fills, zero on
#    every entry/exit day so it cannot double-count). Used only for the chart + max-DD (PREREG §2.8
#    "daily MTM using real CLOSE for the held strike").
# ============================================================
full_days = sorted(set(d for cyc in cycles for d in trading_days_between(cyc[1], cyc[2])))
eq = {}
for cell in ['A', 'B']:
    s_net = pd.Series({d: daily_pnl[cell]['net'].get(d, 0.0) for d in full_days}).sort_index()
    s_x2 = pd.Series({d: daily_pnl[cell]['x2'].get(d, 0.0) for d in full_days}).sort_index()
    eq[cell] = pd.DataFrame({'pnl_net': s_net, 'pnl_x2': s_x2})
    eq[cell]['equity_net'] = eq[cell]['pnl_net'].cumsum()
    eq[cell]['equity_x2'] = eq[cell]['pnl_x2'].cumsum()

    # --- unrealized MTM overlay, built from the ledger's own open/close rows per struct_id/leg ---
    unreal = pd.Series(0.0, index=full_days)
    cell_ledger = ledger_df[ledger_df.cell == cell]
    for (sid, leg), grp in cell_ledger.groupby(['struct_id', 'leg']):
        grp = grp.sort_values('date')
        if len(grp) < 2:
            continue  # a failed/incomplete open (see warnings) -- nothing to mark
        open_row, close_row = grp.iloc[0], grp.iloc[-1]
        entry_date = pd.Timestamp(open_row['date'])
        exit_date = pd.Timestamp(close_row['date'])
        entry_fill = open_row['premium_in'] if leg == 'SHORT_ITM' else open_row['premium_out']
        sign = -1 if leg == 'SHORT_ITM' else 1
        qty = open_row['qty_lots']
        expiry = pd.Timestamp(open_row['expiry'])
        strike = open_row['strike']
        lot_size = lot_size_for(expiry)
        between = [d for d in full_days if entry_date < d < exit_date]
        if not between:
            continue
        closes, stale = get_close_series(expiry, open_row['side'], strike, between)
        for d in between:
            c = closes.get(d)
            if c is None:
                continue
            unreal[d] += sign * (c - entry_fill) * lot_size * qty
    eq[cell]['equity_net_mtm'] = eq[cell]['equity_net'] + unreal
    eq[cell]['runmax_net'] = eq[cell]['equity_net_mtm'].cummax()
    eq[cell]['dd_net'] = eq[cell]['equity_net_mtm'] - eq[cell]['runmax_net']

# ============================================================
# 7. Margin / naked-margin per structure-open event (SHORT_ITM opens only)
# ============================================================
margin_rows = []
opens = ledger_df[ledger_df.action.isin(['SELL_OPEN'])]
hedges = ledger_df[ledger_df.leg == 'HEDGE_OTM']
for _, r in opens.iterrows():
    hrow = hedges[(hedges.cell == r.cell) & (hedges.struct_id == r.struct_id) & (hedges.action == 'BUY_OPEN')]
    if len(hrow) == 0:
        continue
    hrow = hrow.iloc[0]
    K_short = r.strike
    K_hedge = hrow.strike
    net_credit = r.premium_in - 2 * hrow.premium_out
    worst_case = max(0.0, abs(K_short - K_hedge) - net_credit)
    spot_c = spot.loc[pd.Timestamp(r.date), 'close']
    exch_style = 0.12 * spot_c - 2 * hrow.premium_out
    margin_pts = max(worst_case, exch_style)
    naked_pts = 0.12 * spot_c
    margin_rows.append(dict(cell=r.cell, cycle=r.cycle, date=r.date, side=r.side,
                             K_short=K_short, K_hedge=K_hedge, net_credit_pts=net_credit,
                             worst_case_pts=worst_case, exch_style_pts=exch_style,
                             margin_pts=margin_pts, naked_margin_pts=naked_pts,
                             margin_drop_ratio=margin_pts / naked_pts if naked_pts else np.nan))
margin_df = pd.DataFrame(margin_rows)
margin_path = OUT + r"\quick_margin_detail.csv"
margin_df.to_csv(margin_path, index=False)
log(f"[OUTPUT] {margin_path} rows={len(margin_df)}")

# ============================================================
# 8. Headline stats per cell
# ============================================================
def headline(cell):
    cdf = pd.DataFrame(cycle_pnl[cell])
    n_cyc = len(cdf)
    win_rate = (cdf['pnl_net'] > 0).mean() if n_cyc else np.nan
    total_net = eq[cell]['equity_net'].iloc[-1] if len(eq[cell]) else 0.0
    total_x2 = eq[cell]['equity_x2'].iloc[-1] if len(eq[cell]) else 0.0
    maxdd = eq[cell]['dd_net'].min() if len(eq[cell]) else 0.0
    worst_row = cdf.loc[cdf['pnl_net'].idxmin()] if n_cyc else None
    n_bull_entries = (cdf['entry_signal'] == 'bull').sum()
    n_bear_entries = (cdf['entry_signal'] == 'bear').sum()

    # bear-side (CE) contribution -- only meaningful for cell A. Computed directly off the ledger's
    # own 'side' column (every leg row is tagged PE or CE for the structure it belongs to), NOT off
    # a day-based active-side tag: on a FLIP day the old side's close and the new side's open land on
    # the SAME calendar day, so a day-tag approach mis-books the closing leg's cashflow under the
    # side that opened right after it. Grouping by the ledger's own side label avoids that entirely.
    bear_pnl = None
    if cell == 'A':
        bear_pnl = ledger_df[(ledger_df.cell == 'A') & (ledger_df.side == 'CE')]['cashflow_net'].sum()

    # avg credit vs hedge cost (per structure-open event, this cell)
    opens_c = ledger_df[(ledger_df.cell == cell) & (ledger_df.action == 'SELL_OPEN')]
    hedges_c = ledger_df[(ledger_df.cell == cell) & (ledger_df.action == 'BUY_OPEN')]
    avg_credit = opens_c['premium_in'].mean() if len(opens_c) else np.nan
    avg_hedge_cost = hedges_c['premium_out'].mean() * 2 if len(hedges_c) else np.nan  # *2 lots

    m_c = margin_df[margin_df.cell == cell]
    avg_margin_pts = m_c['margin_pts'].mean() if len(m_c) else np.nan
    avg_naked_pts = m_c['naked_margin_pts'].mean() if len(m_c) else np.nan
    avg_drop_ratio = m_c['margin_drop_ratio'].mean() if len(m_c) else np.nan

    # ROM annualized: geometric compounding of per-cycle return (pnl_net / margin at that cycle's open)
    rom_series = []
    for _, row in cdf.iterrows():
        m_this = margin_df[(margin_df.cell == cell) & (margin_df.cycle == row['cycle'])]
        if len(m_this) == 0 or m_this['margin_pts'].iloc[0] == 0:
            continue
        lot = lot_size_for(pd.Timestamp(row['end']))
        margin_rupees = m_this['margin_pts'].iloc[0] * lot
        rom_series.append(row['pnl_net'] / margin_rupees if margin_rupees else np.nan)
    rom_series = [r for r in rom_series if pd.notna(r)]
    if rom_series:
        n_months = n_cyc
        geo = np.prod([1 + r for r in rom_series]) ** (12.0 / n_months) - 1 if n_months else np.nan
        total_rom = np.prod([1 + r for r in rom_series]) - 1
    else:
        geo, total_rom = np.nan, np.nan

    # fixed Rs 10L notional return: total rupee P&L / 10L
    ret_on_10L = total_net / 1_000_000.0

    return dict(cell=cell, n_cycles=n_cyc, total_pnl_net_rupees=total_net, total_pnl_x2_rupees=total_x2,
                win_rate=win_rate, max_dd_rupees=maxdd,
                worst_cycle=None if worst_row is None else dict(cycle=int(worst_row['cycle']),
                                                                 start=str(worst_row['start']), end=str(worst_row['end']),
                                                                 pnl_net=worst_row['pnl_net'], entry_signal=worst_row['entry_signal']),
                n_bull_entries=int(n_bull_entries), n_bear_entries=int(n_bear_entries),
                bear_side_pnl=bear_pnl if cell == 'A' else None,
                avg_credit_rupees_per_lot=avg_credit, avg_hedge_cost_rupees_per_2lot=avg_hedge_cost,
                avg_margin_pts=avg_margin_pts, avg_naked_margin_pts=avg_naked_pts,
                avg_margin_drop_ratio=avg_drop_ratio,
                rom_annualized=geo, rom_total_window=total_rom,
                return_on_10L_notional=ret_on_10L)

hlA = headline('A')
hlB = headline('B')
log("[HEADLINE A] " + json.dumps(hlA, default=str, indent=2))
log("[HEADLINE B] " + json.dumps(hlB, default=str, indent=2))

# ============================================================
# 9. Premium -> ITM depth mapping
# ============================================================
depth_df = pd.DataFrame(premium_depth_log)
depth_path = OUT + r"\premium_itm_depth_mapping.csv"
depth_df.to_csv(depth_path, index=False)
depth_summary = depth_df.groupby('cell')['itm_depth'].agg(['count', 'mean', 'median', 'min', 'max', 'std'])
log(f"[OUTPUT] {depth_path} rows={len(depth_df)}")
log("[DEPTH SUMMARY]\n" + depth_summary.to_string())

# ============================================================
# 10. Equity curve plot
# ============================================================
fig, axes = plt.subplots(2, 1, figsize=(14, 8), dpi=120, sharex=True, gridspec_kw={'height_ratios': [3, 1]})
ax1, ax2 = axes
for cell, color in [('A', 'tab:blue'), ('B', 'tab:orange')]:
    ax1.plot(eq[cell].index, eq[cell]['equity_net_mtm'], label=f'Cell {cell} (net, daily MTM)', color=color, lw=1.6)
    ax1.plot(eq[cell].index, eq[cell]['equity_net'], label=f'Cell {cell} (net, realized-only)', color=color, lw=0.9, ls=':', alpha=0.6)
    ax1.plot(eq[cell].index, eq[cell]['equity_x2'], label=f'Cell {cell} (2x-cost, realized)', color=color, lw=1.0, ls='--', alpha=0.7)
ax1.axhline(0, color='grey', lw=0.7)
ax1.set_title('PREVIEW 2025-2026 (~18 monthly cycles) -- ITM-Sell/2x-OTM-Hedge -- UNGATED, NOT CERTIFIED')
ax1.set_ylabel('Cumulative P&L (Rs, per 1 short + 2 hedge lots)')
ax1.legend(loc='upper left', fontsize=8)
ax1.grid(alpha=0.3)

for cell, color in [('A', 'tab:blue'), ('B', 'tab:orange')]:
    ax2.fill_between(eq[cell].index, eq[cell]['dd_net'], 0, color=color, alpha=0.4, label=f'Cell {cell} DD')
ax2.set_ylabel('Drawdown (Rs, net)')
ax2.set_xlabel('Date')
ax2.legend(loc='lower left', fontsize=8)
ax2.grid(alpha=0.3)
plt.tight_layout()
png_path = OUT + r"\equity_curve.png"
plt.savefig(png_path)
log(f"[OUTPUT] {png_path}")

# ============================================================
# 11. Dump run log + headline json for the report-writer step
# ============================================================
with open(OUT + r"\run_log.txt", "w", encoding='utf-8') as f:
    f.write("\n".join(log_lines))

results_bundle = dict(hlA=hlA, hlB=hlB, n_cycles=len(cycles),
                       cycles=[dict(cycle=c[0], start=str(c[1].date()), end=str(c[2].date())) for c in cycles],
                       cycle_pnl_A=cycle_pnl['A'], cycle_pnl_B=cycle_pnl['B'],
                       data_max=str(DATA_MAX.date()), window_start=str(WINDOW_START.date()),
                       n_warnings=len(warnings), warnings_sample=warnings[:30])
with open(OUT + r"\results_bundle.json", "w", encoding='utf-8') as f:
    json.dump(results_bundle, f, default=str, indent=2)
log(f"[OUTPUT] {OUT}\\results_bundle.json")

log("DONE")
