import pandas as pd
for name in ('D_overnight1_trail40_1lot', 'E_swing3_trail60_1lot'):
    p = pd.read_csv(f'heatmap_{name}.csv', index_col=0)
    print('=' * 100)
    print(name, ' (Rs, 1 lot, net of costs)')
    mn = [c for c in p.columns if c != 'YEAR']
    hdr = 'Year |' + ''.join(f'{m:>8}' for m in mn) + f'{"YEAR":>11}'
    print(hdr); print('-' * len(hdr))
    for y, row in p.iterrows():
        cells = ''.join(('       .' if pd.isna(row[m]) else f'{int(row[m])/1000:>8.0f}') for m in mn)
        print(f'{int(y)} |{cells}{int(row["YEAR"])/1000:>11.0f}')
    yr = p['YEAR'].dropna()
    print(f'  positive years {(yr>0).sum()}/{len(yr)}   (values in Rs thousands)')
