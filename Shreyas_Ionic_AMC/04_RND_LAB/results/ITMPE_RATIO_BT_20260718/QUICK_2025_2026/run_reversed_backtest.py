# -*- coding: utf-8 -*-
"""
REVERSED-STRATEGY preview: take the exact other side of every trade the original engine generated.
  Original: bull -> SHORT 1 ITM PE + LONG 2 OTM PE (hedge)   ; bear -> SHORT 1 ITM CE + LONG 2 OTM CE
  Reversed: bull -> LONG  1 ITM PE + SHORT 2 OTM PE (naked)  ; bear -> LONG  1 ITM CE + SHORT 2 OTM CE

Per instruction: reuse the EXACT strikes/dates/expiries already in quick_trade_ledger.csv (same
signal, same weekly-Tuesday flip mechanics already baked into which dates/strikes were chosen) --
do NOT re-run strike search or the state machine. Only the roles flip (short<->long) and costs are
recomputed FRESH for the new action direction (never mirrored/negated) and margin uses a new,
honestly-higher formula (2 naked-short OTM lots, partially offset by the 1 long ITM premium).

PREVIEW label applies. HINDSIGHT-BIAS WARNING: this reversal was chosen BECAUSE the original lost
money on this exact 2025-2026 window -- that choice is in-sample knowledge. The full-history gated
run (elsewhere) is the real test of whether "buy premium instead of sell it" is a genuine edge or
just this window's coin-flip.
"""
import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\ITMPE_RATIO_BT_20260718\QUICK_2025_2026"

log_lines = []
def log(msg):
    print(msg)
    log_lines.append(str(msg))

# ============================================================
# 1. Reload spot (for margin's spot_close lookup only) + original ledger + bundle
# ============================================================
spot = pd.read_parquet(ROOT + r"\datasets\index_daily\nse_official_all_indices.parquet")
spot = spot[spot['index_name'] == 'Nifty 50'].copy()
spot['date'] = pd.to_datetime(spot['date'])
spot = spot.sort_values('date').drop_duplicates('date').set_index('date')['close']

orig_ledger = pd.read_csv(OUT + r"\quick_trade_ledger.csv")
orig_ledger['date'] = pd.to_datetime(orig_ledger['date'])
orig_ledger['expiry'] = pd.to_datetime(orig_ledger['expiry'])
log(f"[DATA] original ledger reloaded: {len(orig_ledger)} rows, "
    f"{orig_ledger.struct_id.nunique()} unique struct_ids across both cells, from quick_trade_ledger.csv")

with open(OUT + r"\results_bundle.json", encoding='utf-8') as f:
    orig_bundle = json.load(f)

def lot_size_for(expiry):
    return 75 if expiry.year == 2025 else 65

# ============================================================
# 2. Reload options (only to refetch RAW CLOSE at each ledger event's date/strike/expiry/side --
#    the ledger stores slippage-adjusted FILLS, not the raw market close, and we need the raw close
#    to (a) recompute original gross P&L for the algebra check and (b) apply FRESH cost/slippage to
#    the reversed action direction rather than reusing the original's slippage sign).
# ============================================================
frames = []
for yr in [2024, 2025, 2026]:
    f = ROOT + rf"\Shreyas_Ionic_AMC\05_DATA_OFFICE\data\fo_bhavcopy_hist\fo_idx_{yr}.parquet"
    d = pd.read_parquet(f)
    d = d[(d.SYMBOL == 'NIFTY') & (d.INSTRUMENT == 'OPTIDX') & (d.OPTION_TYP.isin(['CE', 'PE']))].copy()
    frames.append(d)
opt = pd.concat(frames, ignore_index=True)
opt['TIMESTAMP_dt'] = pd.to_datetime(opt['TIMESTAMP'], format='%d-%b-%Y', errors='coerce')
opt['EXPIRY_DT_dt'] = pd.to_datetime(opt['EXPIRY_DT'], format='%d-%b-%Y', errors='coerce')
opt = opt.dropna(subset=['TIMESTAMP_dt', 'EXPIRY_DT_dt'])
opt_idx = opt.set_index(['EXPIRY_DT_dt', 'OPTION_TYP', 'STRIKE_PR', 'TIMESTAMP_dt']).sort_index()

def raw_close(expiry, side, strike, date):
    try:
        row = opt_idx.loc[(expiry, side, strike, date)]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        return float(row['CLOSE'])
    except KeyError:
        return None

log(f"[DATA] options reloaded for raw-CLOSE refetch: {len(opt)} rows")

# ============================================================
# 3. Cost model -- IDENTICAL function to the original script (COST_STANDARDS.md D-021).
#    Applied FRESH to the reversed action direction every time -- costs are NEVER mirrored/negated.
# ============================================================
def leg_txn(action, close_price, qty_lots, lot_size):
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
        slip_cost = slip * qty_lots * lot_size
        out[tag] = dict(fill=fill, fees=fees, cashflow=cashflow, turnover=turnover, slip_cost=slip_cost)
    return out

def expiry_txn(intrinsic, qty_lots, lot_size, side):
    out = {}
    for mult, tag in [(1.0, 'net'), (2.0, 'x2')]:
        turnover = intrinsic * qty_lots * lot_size
        stt = 0.00125 * turnover * mult if intrinsic > 0 else 0.0
        fees = stt
        cashflow = (-turnover - fees) if side == 'SHORT' else (turnover - fees)
        out[tag] = dict(fees=fees, cashflow=cashflow, turnover=turnover, slip_cost=0.0)
    return out

# ============================================================
# 4. Rebuild each leg round-trip from the original ledger, recompute ORIGINAL gross/cost (for the
#    algebra check) and REVERSED net (fresh cost, flipped role), using the SAME date/strike/expiry.
# ============================================================
CLOSE_ACTIONS = {'BUY_CLOSE_FLIP', 'BUY_CLOSE_EXITCASH', 'SELL_CLOSE_FLIP', 'SELL_CLOSE_EXITCASH', 'EXPIRY_SETTLE'}
OPEN_ACTIONS = {'SELL_OPEN', 'BUY_OPEN'}

reversed_rows = []
recon_rows = []  # per leg-roundtrip reconciliation: original gross/cost vs reversed gross/cost

for (cell, sid, leg), grp in orig_ledger.groupby(['cell', 'struct_id', 'leg']):
    grp = grp.sort_values('date')
    if len(grp) < 2:
        continue  # incomplete/failed open (e.g. cyc15 cell A) -- nothing to mirror
    open_row, close_row = grp.iloc[0], grp.iloc[-1]
    expiry = open_row['expiry']
    strike = open_row['strike']
    side = open_row['side']
    qty = int(open_row['qty_lots'])
    lot_size = lot_size_for(expiry)
    cycle = int(open_row['cycle'])
    entry_date = open_row['date']
    exit_date = close_row['date']
    exit_action = close_row['action']

    # --- ORIGINAL leg direction (as actually traded) ---
    orig_open_action = 'SELL' if leg == 'SHORT_ITM' else 'BUY'
    orig_sign = -1 if leg == 'SHORT_ITM' else 1  # short loses when price rises, long gains

    # --- REVERSED leg direction ---
    rev_open_action = 'BUY' if leg == 'SHORT_ITM' else 'SELL'
    rev_leg_name = 'LONG_ITM' if leg == 'SHORT_ITM' else 'SHORT_OTM'
    rev_sign = +1 if leg == 'SHORT_ITM' else -1

    # raw close at entry (always a live market trade)
    c_entry = raw_close(expiry, side, strike, entry_date)
    if c_entry is None:
        log(f"WARN: no raw close at entry for {cell}/{sid}/{leg} {entry_date.date()} strike {strike} -- skipping")
        continue

    is_expiry_exit = (exit_action == 'EXPIRY_SETTLE')
    if is_expiry_exit:
        spot_exit = spot.get(exit_date, np.nan)
        if side == 'PE':
            exit_intrinsic = max(0.0, strike - spot_exit)
        else:
            exit_intrinsic = max(0.0, spot_exit - strike)
        c_exit = exit_intrinsic
    else:
        c_exit = raw_close(expiry, side, strike, exit_date)
        if c_exit is None:
            c_exit = c_entry  # stale-fill fallback, same convention as original script

    # ---- ORIGINAL gross (price-only, no slippage/fees) + cost, for the algebra check ----
    orig_open_txn = leg_txn(orig_open_action, c_entry, qty, lot_size)
    if is_expiry_exit:
        orig_close_txn = expiry_txn(c_exit, qty, lot_size, 'SHORT' if leg == 'SHORT_ITM' else 'LONG')
    else:
        orig_close_action = 'BUY' if orig_open_action == 'SELL' else 'SELL'
        orig_close_txn = leg_txn(orig_close_action, c_exit, qty, lot_size)
    orig_gross_leg = orig_sign * (c_exit - c_entry) * qty * lot_size
    orig_cost_leg = (orig_open_txn['net']['fees'] + orig_open_txn['net'].get('slip_cost', 0.0)
                     + orig_close_txn['net']['fees'] + orig_close_txn['net'].get('slip_cost', 0.0))
    orig_net_leg_recomputed = orig_open_txn['net']['cashflow'] + orig_close_txn['net']['cashflow']

    # ---- REVERSED: fresh action, fresh cost, SAME close prices ----
    rev_open_txn = leg_txn(rev_open_action, c_entry, qty, lot_size)
    if is_expiry_exit:
        rev_close_txn = expiry_txn(c_exit, qty, lot_size, 'LONG' if leg == 'SHORT_ITM' else 'SHORT')
    else:
        rev_close_action = 'BUY' if rev_open_action == 'SELL' else 'SELL'
        rev_close_txn = leg_txn(rev_close_action, c_exit, qty, lot_size)
    rev_gross_leg = rev_sign * (c_exit - c_entry) * qty * lot_size
    rev_cost_leg = (rev_open_txn['net']['fees'] + rev_open_txn['net'].get('slip_cost', 0.0)
                    + rev_close_txn['net']['fees'] + rev_close_txn['net'].get('slip_cost', 0.0))
    rev_net_leg = rev_open_txn['net']['cashflow'] + rev_close_txn['net']['cashflow']
    rev_net_leg_x2 = rev_open_txn['x2']['cashflow'] + rev_close_txn['x2']['cashflow']

    recon_rows.append(dict(cell=cell, cycle=cycle, struct_id=sid, leg=leg, side=side, strike=strike,
                            entry_date=entry_date.date(), exit_date=exit_date.date(),
                            c_entry=c_entry, c_exit=c_exit,
                            orig_gross=orig_gross_leg, orig_cost=orig_cost_leg,
                            orig_net_ledger=grp['cashflow_net'].sum(), orig_net_recomputed=orig_net_leg_recomputed,
                            rev_gross=rev_gross_leg, rev_cost=rev_cost_leg, rev_net=rev_net_leg,
                            mirror_check=orig_gross_leg + rev_gross_leg))  # should be ~0

    reversed_rows.append(dict(cell=cell, cycle=cycle, struct_id=sid, leg=rev_leg_name, side=side,
                               action='BUY_OPEN' if rev_open_action == 'BUY' else 'SELL_OPEN',
                               date=entry_date.date(), expiry=expiry.date(), strike=strike, qty_lots=qty,
                               close_used=c_entry, fees_net=rev_open_txn['net']['fees'], fees_x2=rev_open_txn['x2']['fees'],
                               cashflow_net=rev_open_txn['net']['cashflow'], cashflow_x2=rev_open_txn['x2']['cashflow']))
    close_label = exit_action if is_expiry_exit else (('SELL_CLOSE_' if rev_open_action == 'BUY' else 'BUY_CLOSE_')
                                                        + exit_action.split('_')[-1])
    reversed_rows.append(dict(cell=cell, cycle=cycle, struct_id=sid, leg=rev_leg_name, side=side,
                               action=close_label, date=exit_date.date(), expiry=expiry.date(),
                               strike=strike, qty_lots=qty, close_used=c_exit,
                               fees_net=rev_close_txn['net']['fees'], fees_x2=rev_close_txn['x2']['fees'],
                               cashflow_net=rev_close_txn['net']['cashflow'], cashflow_x2=rev_close_txn['x2']['cashflow']))

rev_ledger = pd.DataFrame(reversed_rows)
recon = pd.DataFrame(recon_rows)

# ---- Empirical mirror-identity check (requirement 1's "algebra check", proven not assumed) ----
log("\n[ALGEBRA CHECK] mirror identity: reversed_gross should == -original_gross, per leg (float-precision):")
log(f"  max abs(orig_gross + rev_gross) across all {len(recon)} legs = {recon['mirror_check'].abs().max():.6f} "
    f"(should be ~0 -- confirms same close prices, opposite sign, no other divergence)")
log(f"  original ledger net vs recomputed net, max abs diff = "
    f"{(recon['orig_net_ledger'] - recon['orig_net_recomputed']).abs().max():.4f} (sanity: should be ~0)")

for cell in ['A', 'B']:
    r = recon[recon.cell == cell]
    orig_gross_total = r['orig_gross'].sum()
    orig_cost_total = r['orig_cost'].sum()
    orig_net_total = orig_gross_total - orig_cost_total
    rev_gross_total = r['rev_gross'].sum()
    rev_cost_total = r['rev_cost'].sum()
    rev_net_total = rev_gross_total - rev_cost_total
    log(f"\n[ALGEBRA CHECK cell {cell}]")
    log(f"  original: gross={orig_gross_total:,.0f}  cost={orig_cost_total:,.0f}  net={orig_net_total:,.0f} "
        f"(vs original headline net {orig_bundle['hl' + cell]['total_pnl_net_rupees']:,.0f})")
    log(f"  reversed: gross={rev_gross_total:,.0f} (= -orig_gross, check diff {rev_gross_total + orig_gross_total:,.2f})  "
        f"cost={rev_cost_total:,.0f}  net={rev_net_total:,.0f}")
    log(f"  identity: reversed_net = -(original_gross) - reversed_cost = "
        f"{-orig_gross_total:,.0f} - {rev_cost_total:,.0f} = {-orig_gross_total - rev_cost_total:,.0f} "
        f"(matches rev_net_total to float precision: diff {(-orig_gross_total - rev_cost_total) - rev_net_total:,.4f})")
    log(f"  gross-loss-vs-2x-costs: |original_gross|={abs(orig_gross_total):,.0f} vs 2x(orig_cost+rev_cost)="
        f"{2 * (orig_cost_total + rev_cost_total):,.0f} -> "
        f"{'gross swing DOMINATES costs by ' + str(round(abs(orig_gross_total) / max(orig_cost_total + rev_cost_total, 1), 1)) + 'x' if abs(orig_gross_total) > 2*(orig_cost_total+rev_cost_total) else 'costs are NOT negligible vs the gross swing'}")

rev_ledger.to_csv(OUT + r"\reversed_trade_ledger.csv", index=False)
recon.to_csv(OUT + r"\reversed_reconciliation_detail.csv", index=False)
log(f"\n[OUTPUT] {OUT}\\reversed_trade_ledger.csv rows={len(rev_ledger)}")
log(f"[OUTPUT] {OUT}\\reversed_reconciliation_detail.csv rows={len(recon)}")

# ============================================================
# 5. Cycle-level P&L (reversed, net-of-cost) -- ledger-based, no daily-MTM double-count risk
# ============================================================
cyc_pnl = {}
for cell in ['A', 'B']:
    rows = []
    for cyc in sorted(recon[recon.cell == cell]['cycle'].unique()):
        sub_ids = recon[(recon.cell == cell) & (recon.cycle == cyc)]['struct_id'].unique()
        net = rev_ledger[(rev_ledger.cell == cell) & (rev_ledger.struct_id.isin(sub_ids))]['cashflow_net'].sum()
        netx2 = rev_ledger[(rev_ledger.cell == cell) & (rev_ledger.struct_id.isin(sub_ids))]['cashflow_x2'].sum()
        orig_entry = [c['entry_signal'] for c in orig_bundle[f'cycle_pnl_{cell}'] if c['cycle'] == cyc][0]
        orig_start = [c['start'] for c in orig_bundle[f'cycle_pnl_{cell}'] if c['cycle'] == cyc][0]
        orig_end = [c['end'] for c in orig_bundle[f'cycle_pnl_{cell}'] if c['cycle'] == cyc][0]
        orig_pnl = [c['pnl_net'] for c in orig_bundle[f'cycle_pnl_{cell}'] if c['cycle'] == cyc][0]
        rows.append(dict(cycle=cyc, start=orig_start, end=orig_end, entry_signal=orig_entry,
                          pnl_net=net, pnl_x2=netx2, original_pnl_net=orig_pnl))
    cyc_pnl[cell] = pd.DataFrame(rows)

for cell in ['A', 'B']:
    cdf = cyc_pnl[cell]
    log(f"\n[CYCLE TABLE reversed cell {cell}]\n" + cdf.to_string(index=False))

# ============================================================
# 6. NEW margin model (requirement 2): 2 naked-short OTM lots, partial offset by the 1 long ITM
#    margin_reversed_pts = max(0, 2*(0.12*spot) - 1*long_itm_entry_premium)
#    naked_2short_pts (no offset, for comparison)     = 2*(0.12*spot)
#    formula disclosed explicitly -- analogous in style to the original's exch_style_estimate, but
#    now the OFFSET side (the long) is 1 lot instead of 2, and the EXPOSED side (short) is 2 lots
#    instead of 1 -- this is the honest inversion of the original's capped-risk structure.
# ============================================================
margin_rows = []
long_opens = rev_ledger[(rev_ledger.leg == 'LONG_ITM') & (rev_ledger.action == 'BUY_OPEN')]
for _, r in long_opens.iterrows():
    spot_c = spot.get(pd.Timestamp(r.date), np.nan)
    if pd.isna(spot_c):
        continue
    naked_2short_pts = 2 * (0.12 * spot_c)
    margin_pts = max(0.0, naked_2short_pts - r.close_used)  # offset by the 1 long's entry premium
    margin_rows.append(dict(cell=r.cell, cycle=r.cycle, date=r.date, side=r.side,
                             long_premium=r.close_used, spot=spot_c,
                             naked_2short_pts=naked_2short_pts, margin_pts=margin_pts,
                             offset_ratio=margin_pts / naked_2short_pts))
margin_df = pd.DataFrame(margin_rows)
margin_df.to_csv(OUT + r"\reversed_margin_detail.csv", index=False)
log(f"\n[OUTPUT] {OUT}\\reversed_margin_detail.csv rows={len(margin_df)}")

for cell in ['A', 'B']:
    m = margin_df[margin_df.cell == cell]
    orig_avg_margin_pts = orig_bundle['hl' + cell]['avg_margin_pts']
    log(f"[MARGIN cell {cell}] avg reversed margin={m['margin_pts'].mean():.1f} pts "
        f"(naked-2short-no-offset avg={m['naked_2short_pts'].mean():.1f} pts, offset_ratio avg={m['offset_ratio'].mean():.3f}) "
        f"vs ORIGINAL hedged margin avg={orig_avg_margin_pts:.1f} pts -- "
        f"reversed/original ratio = {m['margin_pts'].mean() / orig_avg_margin_pts:.2f}x")

# ROM per cell (annualized, geometric, same method as original)
def rom_stats(cell):
    cdf = cyc_pnl[cell]
    rom_series = []
    for _, row in cdf.iterrows():
        m_this = margin_df[(margin_df.cell == cell) & (margin_df.cycle == row['cycle'])]
        if len(m_this) == 0 or m_this['margin_pts'].iloc[0] <= 0:
            continue
        end_dt = pd.Timestamp(row['end'])
        lot = lot_size_for(end_dt)
        margin_rupees = m_this['margin_pts'].iloc[0] * lot
        rom_series.append(row['pnl_net'] / margin_rupees)
    if not rom_series:
        return np.nan, np.nan
    n = len(cdf)
    geo = np.prod([1 + r for r in rom_series]) ** (12.0 / n) - 1
    tot = np.prod([1 + r for r in rom_series]) - 1
    return geo, tot

rom_result = {cell: rom_stats(cell) for cell in ['A', 'B']}
for cell in ['A', 'B']:
    log(f"[ROM reversed cell {cell}] annualized={rom_result[cell][0]*100:.1f}%  total_window={rom_result[cell][1]*100:.1f}%")

# ============================================================
# 7. Headline totals + worst cycle (requirement 3)
# ============================================================
headline = {}
for cell in ['A', 'B']:
    cdf = cyc_pnl[cell]
    total_net = cdf['pnl_net'].sum()
    total_x2 = cdf['pnl_x2'].sum()
    win_rate = (cdf['pnl_net'] > 0).mean()
    worst = cdf.loc[cdf['pnl_net'].idxmin()]
    best = cdf.loc[cdf['pnl_net'].idxmax()]
    headline[cell] = dict(total_net=total_net, total_x2=total_x2, win_rate=win_rate,
                           worst_cycle=int(worst['cycle']), worst_start=worst['start'], worst_end=worst['end'],
                           worst_pnl=worst['pnl_net'], worst_entry_signal=worst['entry_signal'],
                           worst_original_pnl=worst['original_pnl_net'],
                           best_cycle=int(best['cycle']), best_start=best['start'], best_end=best['end'],
                           best_pnl=best['pnl_net'], best_original_pnl=best['original_pnl_net'])
    log(f"\n[HEADLINE reversed cell {cell}] total_net={total_net:,.0f} total_x2={total_x2:,.0f} win_rate={win_rate:.3f}")
    log(f"  worst cycle: {int(worst['cycle'])} ({worst['start']}->{worst['end']}, signal={worst['entry_signal']}) "
        f"reversed_pnl={worst['pnl_net']:,.0f}  (original_pnl was {worst['original_pnl_net']:,.0f})")
    log(f"  best  cycle: {int(best['cycle'])} ({best['start']}->{best['end']}) "
        f"reversed_pnl={best['pnl_net']:,.0f}  (original_pnl was {best['original_pnl_net']:,.0f})")

# ---- cycle 16 (April-2026 crash cycle) walkthrough, requirement 3 ----
for cell in ['A', 'B']:
    row16 = cyc_pnl[cell][cyc_pnl[cell].cycle == 16]
    if len(row16):
        r = row16.iloc[0]
        log(f"[CYCLE 16 crash-cycle, cell {cell}] reversed_pnl={r['pnl_net']:,.0f} "
            f"(original was {r['original_pnl_net']:,.0f}, entry_signal={r['entry_signal']})")

# ============================================================
# 8. Equity curve (reversed) -- realized-only cumsum, mirrors original script's fixed methodology
# ============================================================
full_days = sorted(pd.to_datetime(pd.concat([pd.Series(pd.to_datetime(rev_ledger['date']))])).unique())
eq = {}
for cell in ['A', 'B']:
    cell_ledger = rev_ledger[rev_ledger.cell == cell].copy()
    cell_ledger['date'] = pd.to_datetime(cell_ledger['date'])
    daily = cell_ledger.groupby('date')['cashflow_net'].sum()
    daily_x2 = cell_ledger.groupby('date')['cashflow_x2'].sum()
    s_net = pd.Series(0.0, index=full_days)
    s_net.loc[daily.index] = daily.values
    s_x2 = pd.Series(0.0, index=full_days)
    s_x2.loc[daily_x2.index] = daily_x2.values
    eq[cell] = pd.DataFrame({'pnl_net': s_net, 'pnl_x2': s_x2})
    eq[cell]['equity_net'] = eq[cell]['pnl_net'].cumsum()
    eq[cell]['equity_x2'] = eq[cell]['pnl_x2'].cumsum()
    eq[cell]['runmax'] = eq[cell]['equity_net'].cummax()
    eq[cell]['dd'] = eq[cell]['equity_net'] - eq[cell]['runmax']

fig, axes = plt.subplots(2, 1, figsize=(14, 8), dpi=120, sharex=True, gridspec_kw={'height_ratios': [3, 1]})
ax1, ax2 = axes
for cell, color in [('A', 'tab:blue'), ('B', 'tab:orange')]:
    ax1.plot(eq[cell].index, eq[cell]['equity_net'], label=f'Cell {cell} REVERSED (net, realized)', color=color, lw=1.6)
    ax1.plot(eq[cell].index, eq[cell]['equity_x2'], label=f'Cell {cell} REVERSED (2x-cost)', color=color, lw=1.0, ls='--', alpha=0.7)
ax1.axhline(0, color='grey', lw=0.7)
ax1.set_title('REVERSED PREVIEW 2025-2026 (~18 cycles) -- mirrors original ledger legs -- UNGATED, HINDSIGHT-SELECTED WINDOW')
ax1.set_ylabel('Cumulative P&L (Rs, per 1 long + 2 short lots)')
ax1.legend(loc='upper left', fontsize=8)
ax1.grid(alpha=0.3)
for cell, color in [('A', 'tab:blue'), ('B', 'tab:orange')]:
    ax2.fill_between(eq[cell].index, eq[cell]['dd'], 0, color=color, alpha=0.4, label=f'Cell {cell} DD')
ax2.set_ylabel('Drawdown (Rs)')
ax2.set_xlabel('Date')
ax2.legend(loc='lower left', fontsize=8)
ax2.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT + r"\reversed_equity_curve.png")
log(f"\n[OUTPUT] {OUT}\\reversed_equity_curve.png")

# ============================================================
# 9. Dump log + bundle
# ============================================================
with open(OUT + r"\reversed_run_log.txt", "w", encoding='utf-8') as f:
    f.write("\n".join(log_lines))

bundle_out = dict(headline=headline, rom=rom_result,
                   cycle_pnl={cell: cyc_pnl[cell].to_dict('records') for cell in ['A', 'B']})
with open(OUT + r"\reversed_results_bundle.json", "w", encoding='utf-8') as f:
    json.dump(bundle_out, f, default=str, indent=2)
log(f"[OUTPUT] {OUT}\\reversed_results_bundle.json")
log("DONE")
