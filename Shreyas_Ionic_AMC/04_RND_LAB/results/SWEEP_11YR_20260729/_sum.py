import json
r = json.load(open('report.json'))
for c in r['configs']:
    if c['config'] not in ('D_overnight1_trail40', 'E_swing3_trail60'):
        continue
    print('=' * 88)
    print(c['config'], '| kelly_f estimated on IS =', c['kelly_f_from_IS'])
    for mode in ('1lot', 'kelly01'):
        print('  --', mode)
        for w, m in c['sizing'][mode].items():
            if m.get('n', 0) < 10:
                print(f"     {w:20s} n={m.get('n')} (too thin)")
                continue
            print(f"     {w:20s} n={m['n']:>4} CAGR={m['CAGR_pct']:>7}% MDD={m['maxDD_pct']:>7}% "
                  f"Calmar={m['Calmar']} Sharpe={m['Sharpe']} PF={m['PF']} t={m['t_nw_daily']} "
                  f"hit={m['hit']} mo+={m['months_pos_net']}/{m['months']} tr/mo={m['trades_per_month']}")
    m = c['sizing']['1lot']['ALL_11yr']
    print(f"     exits: {m['exit_mix']}")
    print(f"     pts: max_win={m['max_win_pts']} p95={m['pts_p95']} worst={m['min_pts']} "
          f"mean={m['mean_gross_pts']} | cost={m['cost_pct_of_gross']}% of gross | "
          f"avg_hold={m['avg_hold_min']}min | max_trade_share={m['max_trade_share']}")
    print(f"     worst_month=Rs{m['worst_month_rs']:,} best_month=Rs{m['best_month_rs']:,}")
