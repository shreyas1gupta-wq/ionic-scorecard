import pandas as pd, numpy as np, json, sys
pd.set_option('display.width', 160)

paths = {
 "MASTER_fund": "data/fundamentals/MASTER_fundamentals_pit.parquet",
 "sector_map": "data/universe/sector_map.parquet",
 "universe_final_scores": "results/universe_final_scores.parquet",
 "canonical_7leg": "rnd/panel/canonical_7leg_scores.parquet",
 "panel_long": "rnd/panel/panel_long.parquet",
 "panel_main": "rnd/panel/panel.parquet",
}

for name, p in paths.items():
    print("="*80)
    print(name, p)
    try:
        df = pd.read_parquet(p)
    except Exception as e:
        print("ERROR:", e)
        continue
    print("shape:", df.shape)
    print("columns:", list(df.columns))
    print("dtypes:\n", df.dtypes)
    # print small head
    with pd.option_context('display.max_columns', 20):
        print(df.head(3))
