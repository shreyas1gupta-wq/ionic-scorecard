"""Theta-paid vs gamma-captured decomposition, split by DTE and era -- the mechanism table."""
import pandas as pd

CKPT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
        r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\checkpoints")
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731")

rows = []
for dte in (15, 30, 45, 60, 90):
    df = pd.read_csv(f"{CKPT}\\trades_dte{dte}_expiry.csv", parse_dates=["entry_date"])
    df["entry_extr"] = df["entry_premium"] - df["entry_intrinsic"]
    df["exit_extr"] = df["exit_value"] - df["exit_intrinsic"]
    df["theta_paid"] = df["entry_extr"] - df["exit_extr"]
    df["gamma_captured"] = df["exit_intrinsic"] - df["entry_intrinsic"]
    eras = [
        ("pre2019", df["entry_date"] < pd.Timestamp("2019-02-01")),
        ("2019_2024sep", (df["entry_date"] >= pd.Timestamp("2019-02-01")) & (df["entry_date"] < pd.Timestamp("2024-10-01"))),
        ("2024oct_plus", df["entry_date"] >= pd.Timestamp("2024-10-01")),
        ("HELDOUT_2026", df["entry_date"] >= pd.Timestamp("2026-01-01")),
        ("ALL", df["entry_date"].notna()),
    ]
    for label, mask in eras:
        sub = df[mask]
        if len(sub) == 0:
            continue
        theta = sub["theta_paid"].mean()
        gamma = sub["gamma_captured"].mean()
        rows.append(dict(dte=dte, era=label, n=len(sub), theta_paid=theta, gamma_captured=gamma,
                          gamma_over_theta=gamma / theta if theta else float("nan"),
                          net_pnl=sub["net_pnl"].mean(), win_pct=(sub["net_pnl"] > 0).mean() * 100))

out = pd.DataFrame(rows)
out.to_csv(f"{OUT}\\theta_gamma_by_dte_and_era.csv", index=False)
pd.set_option("display.width", 160)
print(out.to_string(index=False))
