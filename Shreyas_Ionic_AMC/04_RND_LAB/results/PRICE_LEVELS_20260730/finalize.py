"""Final cell aggregation (no placebo dependency by default -- placebo is only worth running
on cells that clear a POSITIVE + significant + adequately-powered bar; see scan below).
Writes cells.csv (all 284 cells, ranked by t) and top10.csv (top 10 by |t|, negative extremes
included -- those are the real, Bonferroni-clearing findings in this study).
"""
import numpy as np
import pandas as pd
from scipy import stats

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
BUILD_END = pd.Timestamp("2024-10-01")
HOLDOUT_START = pd.Timestamp("2026-01-01")
BONFERRONI_M = 284
BONFERRONI_T = float(stats.norm.ppf(1 - (0.05 / BONFERRONI_M) / 2))


def era_of(dates):
    return np.select([dates < BUILD_END, dates >= HOLDOUT_START],
                      ["BUILD", "HOLDOUT_2026"], default="RECENT")


def block(sub, n_months):
    n = len(sub)
    if n == 0:
        return dict(n=0, mean=np.nan, t=np.nan)
    x = sub["net_pess"].to_numpy()
    t = stats.ttest_1samp(x, 0).statistic if n > 1 and x.std() > 0 else np.nan
    return dict(n=n, mean=float(x.mean()), t=float(t) if np.isfinite(t) else np.nan)


def main():
    trades = pd.read_parquet(f"{OUT}/trades_real.parquet")
    trades["era"] = era_of(trades["date"])

    n_months_all = (HOLDOUT_START - trades["date"].min()).days / 30.44
    n_months_build = (BUILD_END - trades["date"].min()).days / 30.44
    n_months_recent = (HOLDOUT_START - BUILD_END).days / 30.44
    n_months_hold = (trades["date"].max() - HOLDOUT_START).days / 30.44

    rows = []
    for key, g in trades.groupby(["system", "level_name", "hypothesis", "exit_cfg"]):
        system, level_name, hyp, cfg = key
        priority = bool(g["priority"].iloc[0])
        g_all = g[g["era"] != "HOLDOUT_2026"]
        n = len(g_all)
        if n == 0:
            continue
        x = g_all["net_pess"].to_numpy()
        mean = float(x.mean())
        sd = float(x.std(ddof=1)) if n > 1 else np.nan
        t = float(stats.ttest_1samp(x, 0).statistic) if n > 1 and sd > 0 else np.nan
        win = x > 0
        win_pct = float(win.mean() * 100)
        avg_win = float(x[win].mean()) if win.any() else np.nan
        avg_loss = float(-x[~win].mean()) if (~win).any() else np.nan
        avg_rr = (avg_win / avg_loss) if (avg_loss and avg_loss > 0) else np.nan
        tpm = n / n_months_all

        # pathsafe reliability: spread between optimistic/pessimistic GROSS bounds (pre-cost;
        # cost is a constant shift and cancels out of the spread itself, kept gross to match
        # pathsafe.Summary's own convention of judging the raw exit-path ambiguity)
        gp = g_all["pnl_pess"].to_numpy()
        go = g_all["pnl_opt"].to_numpy()
        mp, mo = gp.mean(), go.mean()
        spread_frac = abs(mo - mp) / abs(mp) if abs(mp) > 1e-9 else np.inf
        reliable = spread_frac <= 0.25
        amb_frac = float(g_all["is_ambiguous"].mean())

        b = block(g[g.era == "BUILD"], n_months_build)
        r = block(g[g.era == "RECENT"], n_months_recent)
        h = block(g[g.era == "HOLDOUT_2026"], n_months_hold)

        rows.append(dict(
            system=system, level_name=level_name, hypothesis=hyp, exit_cfg=cfg, priority=priority,
            n=n, trades_per_month=round(tpm, 2), win_pct=round(win_pct, 1), mean_net_pts=round(mean, 2),
            avg_rr=round(avg_rr, 2) if pd.notna(avg_rr) else np.nan, t=round(t, 2) if pd.notna(t) else np.nan,
            reliable=reliable, spread_frac=round(spread_frac, 2) if np.isfinite(spread_frac) else np.nan,
            ambiguous_frac=round(amb_frac, 3),
            build_n=b["n"], build_mean=round(b["mean"], 2) if pd.notna(b["mean"]) else np.nan,
            build_t=round(b["t"], 2) if pd.notna(b["t"]) else np.nan,
            recent_n=r["n"], recent_mean=round(r["mean"], 2) if pd.notna(r["mean"]) else np.nan,
            recent_t=round(r["t"], 2) if pd.notna(r["t"]) else np.nan,
            hold26_n=h["n"], hold26_mean=round(h["mean"], 2) if pd.notna(h["mean"]) else np.nan,
            hold26_t=round(h["t"], 2) if pd.notna(h["t"]) else np.nan,
        ))

    cells = pd.DataFrame(rows).sort_values("t", ascending=False)
    cells.to_csv(f"{OUT}/cells.csv", index=False)
    print(f"cells.csv written: {len(cells)} rows. Bonferroni |t| bar at m={BONFERRONI_M}: {BONFERRONI_T:.2f}")

    # ---------------- scan for placebo-worthy cells ------------------------------------
    candidates = cells[(cells["mean_net_pts"] > 0) & (cells["t"].abs() >= 3.0) & (cells["n"] >= 150)]
    print(f"\nPOSITIVE + |t|>=3.0 + n>=150 candidates for placebo: {len(candidates)}")
    if len(candidates):
        print(candidates.to_string(index=False))
    else:
        print("NONE. Max positive t in the whole study:",
              cells.loc[cells['mean_net_pts'] > 0, 't'].max())

    # ---------------- top 10 by |t| (negative extremes included, as instructed) --------
    disp = cells[cells["n"] >= 20].copy()
    disp["abs_t"] = disp["t"].abs()
    top10 = disp.sort_values("abs_t", ascending=False).head(10).drop(columns=["abs_t"])
    top10.to_csv(f"{OUT}/top10.csv", index=False)
    pd.set_option("display.width", 240)
    print("\n=== TOP 10 BY |t| ===")
    print(top10.to_string(index=False))

    # ---------------- REJECT vs BREAK mirror check (mechanism) -------------------------
    print("\n=== REJECT vs BREAK mirror (mean net pts, all-era, tight_atr) ===")
    piv = cells[cells.exit_cfg == "tight_atr"].pivot_table(
        index=["system", "level_name"], columns="hypothesis", values="mean_net_pts")
    piv["sum"] = piv.get("REJECT", np.nan) + piv.get("BREAK", np.nan)
    print(f"mean(REJECT)={piv['REJECT'].mean():.2f}  mean(BREAK)={piv['BREAK'].mean():.2f}  "
          f"mean(REJECT+BREAK)={piv['sum'].mean():.2f}  (2x tight_atr cost ~ -9.9 to -12.9)")


if __name__ == "__main__":
    main()
