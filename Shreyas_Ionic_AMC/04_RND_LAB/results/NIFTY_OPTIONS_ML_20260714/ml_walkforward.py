"""
ML WALK-FORWARD: does an XGBoost-timed short-straddle beat the unconditional
baseline, out-of-sample, net of costs? Also fits a small MLP (the "deep
learning" comparison) on the same tabular features to see if it adds anything.

Methodology:
  - Expanding-window walk-forward by calendar year (train <= Dec Y, test Y+1).
    This is genuine OOS: the model never sees the year it's scored on.
  - Costs: 2% and 4% of entry-premium value round trip (two legs open + two
    legs close) — ILLUSTRATIVE assumption (COST_STANDARDS is still DRAFT per
    firm policy), reported at both so the reader can judge sensitivity.
  - Decision rules tested: (a) always-short baseline, (b) short only if
    model predicts payoff>0, (c) short only if predicted payoff in top
    tercile of that fold's test predictions (higher conviction, fewer trades),
    (d) mirror-image LONG straddle using the same features (sign-flipped
    decision) to directly re-test whether ML timing can make BUYING work.
  - Honesty check: label-shuffle placebo on the training data only, refit,
    confirm OOS Sharpe collapses towards zero (rules out leakage/luck).

Why XGBoost and not a transformer: this dataset is ~1,200-1,300 ROWS total
(daily frequency), with only ~250-300 rows per walk-forward test year.
Transformer architectures need orders of magnitude more examples than this to
learn genuine structure rather than memorize noise — at this N a transformer
is close to guaranteed to overfit. A small MLP is fit below as an honest
empirical check of whether "more flexible" helps here (it is not expected to,
and the result is reported either way, not assumed).
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NIFTY_OPTIONS_ML_20260714"

df = pd.read_csv(os.path.join(OUT, "daily_straddle_base.csv"), parse_dates=["trading_day"])
df = df.sort_values("trading_day").reset_index(drop=True)
print(f"Loaded {len(df)} days, {df['trading_day'].min().date()} -> {df['trading_day'].max().date()}")

FEATS = ["dte", "is_0dte", "dow", "entry_premium_pct", "ivrv_proxy", "gap_pct",
         "rv5_prior", "rv10_prior", "rv20_prior", "vix_entry", "vix_chg",
         "prior_payoff_1d", "prior_payoff_5d_mean"]
df = df.dropna(subset=FEATS + ["payoff_pct"]).reset_index(drop=True)
print(f"After dropna on features: {len(df)} rows")
df["year"] = df["trading_day"].dt.year

def sharpe(x):
    x = x.dropna()
    return x.mean() / x.std() * np.sqrt(252) if len(x) > 5 and x.std() > 0 else np.nan

def cost_pct(row, frac):
    # round-trip cost = frac (e.g. 0.02 = 2%) of entry premium value, expressed
    # as a % of spot (same units as payoff_pct, which is already %-of-spot)
    return row["entry_premium_pct"] * frac

from xgboost import XGBRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

YEARS = sorted(df["year"].unique())
test_years = [y for y in YEARS if y >= YEARS[0] + 1]  # need >=1 yr of train history
print(f"Walk-forward test years: {test_years}\n")

results = {"baseline": [], "xgb_any": [], "xgb_top": [], "xgb_long": [], "mlp_any": [], "placebo": []}
all_rows = []

for test_yr in test_years:
    train = df[df["year"] < test_yr]
    test = df[df["year"] == test_yr]
    if len(train) < 100 or len(test) < 20:
        continue
    Xtr, ytr = train[FEATS], train["payoff_pct"]
    Xte, yte = test[FEATS], test["payoff_pct"]

    xgb = XGBRegressor(n_estimators=150, max_depth=3, learning_rate=0.05,
                       subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0, random_state=42)
    xgb.fit(Xtr, ytr)
    pred = xgb.predict(Xte)

    # MLP comparison (small, regularized, standardized features)
    sc = StandardScaler().fit(Xtr)
    mlp = MLPRegressor(hidden_layer_sizes=(16, 8), alpha=1.0, max_iter=2000,
                       early_stopping=True, random_state=42)
    mlp.fit(sc.transform(Xtr), ytr)
    pred_mlp = mlp.predict(sc.transform(Xte))

    # placebo: shuffle train labels, refit, predict OOS
    ytr_shuf = ytr.sample(frac=1.0, random_state=1).reset_index(drop=True)
    xgb_p = XGBRegressor(n_estimators=150, max_depth=3, learning_rate=0.05,
                        subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0, random_state=42)
    xgb_p.fit(Xtr, ytr_shuf.values)
    pred_placebo = xgb_p.predict(Xte)

    tst = test.copy()
    tst["pred"] = pred
    tst["pred_mlp"] = pred_mlp
    tst["pred_placebo"] = pred_placebo
    tst["top_tercile_cut"] = np.quantile(pred, 2/3)
    all_rows.append(tst)

    for mult, tag in [(0.02, "2pct"), (0.04, "4pct")]:
        tst["cost"] = tst.apply(lambda r: cost_pct(r, mult), axis=1)
        tst["net_baseline"] = tst["payoff_pct"] - tst["cost"]
        tst["net_xgb_any"] = np.where(tst["pred"] > 0, tst["payoff_pct"] - tst["cost"], 0.0)
        tst["net_xgb_top"] = np.where(tst["pred"] >= tst["top_tercile_cut"], tst["payoff_pct"] - tst["cost"], 0.0)
        tst["net_xgb_long"] = np.where(tst["pred"] < 0, -tst["payoff_pct"] - tst["cost"], 0.0)
        tst["net_mlp_any"] = np.where(tst["pred_mlp"] > 0, tst["payoff_pct"] - tst["cost"], 0.0)
        tst["net_placebo"] = np.where(tst["pred_placebo"] > 0, tst["payoff_pct"] - tst["cost"], 0.0)

        for key, col in [("baseline","net_baseline"), ("xgb_any","net_xgb_any"), ("xgb_top","net_xgb_top"),
                          ("xgb_long","net_xgb_long"), ("mlp_any","net_mlp_any"), ("placebo","net_placebo")]:
            results[key].append({"year": test_yr, "cost_tag": tag, "n": len(tst),
                                 "n_traded": (tst[col] != 0).sum() if key not in ("baseline",) else len(tst),
                                 "mean": tst[col].mean(), "sharpe": sharpe(tst[col]),
                                 "win": (tst[col] > 0).mean()*100 if key != "baseline" else (tst[col]>0).mean()*100})

print("="*100)
print("PER-YEAR OOS RESULTS (net of costs)")
print("="*100)
for key in ["baseline", "xgb_any", "xgb_top", "xgb_long", "mlp_any", "placebo"]:
    print(f"\n--- {key} ---")
    rdf = pd.DataFrame(results[key])
    print(rdf.to_string(index=False))

# pooled OOS (concat all test years' daily P&L, compute one Sharpe across the whole OOS period)
full = pd.concat(all_rows, ignore_index=True)
print("\n" + "="*100)
print("POOLED OOS (all test years concatenated, one Sharpe across full OOS period)")
print("="*100)
for mult, tag in [(0.02, "2pct"), (0.04, "4pct")]:
    full["cost"] = full.apply(lambda r: cost_pct(r, mult), axis=1)
    full["net_baseline"] = full["payoff_pct"] - full["cost"]
    full["net_xgb_any"] = np.where(full["pred"] > 0, full["payoff_pct"] - full["cost"], 0.0)
    full["net_xgb_top"] = np.where(full["pred"] >= full.groupby("year")["pred"].transform(lambda x: np.quantile(x, 2/3)), full["payoff_pct"] - full["cost"], 0.0)
    full["net_mlp_any"] = np.where(full["pred_mlp"] > 0, full["payoff_pct"] - full["cost"], 0.0)
    full["net_placebo"] = np.where(full["pred_placebo"] > 0, full["payoff_pct"] - full["cost"], 0.0)
    print(f"\n[cost={tag}]")
    for key, col in [("baseline","net_baseline"), ("xgb_any","net_xgb_any"), ("xgb_top","net_xgb_top"),
                      ("mlp_any","net_mlp_any"), ("placebo","net_placebo")]:
        n_traded = (full[col] != 0).sum() if key != "baseline" else len(full)
        print(f"  {key:<12} n_traded={n_traded:>4}/{len(full)} | mean {full[col].mean():>6.3f}% | "
              f"Sharpe {sharpe(full[col]):>5.2f} | win {(full[col]>0).mean()*100:>5.1f}% | "
              f"total {full[col].sum():>7.1f}pts")

full.to_csv(os.path.join(OUT, "oos_predictions_full.csv"), index=False)

# feature importance from the LAST fold's xgb (indicative only)
imp = pd.Series(xgb.feature_importances_, index=FEATS).sort_values(ascending=False)
print("\nFeature importances (last fold XGB, indicative):")
print(imp.to_string())
print("\nSaved oos_predictions_full.csv")
