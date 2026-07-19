"""
One-shot runner for worker hypotheses H028/H032/H033/H034.
Writes cards to rnd/cards/, prints a compact verdict table.
"""
from __future__ import annotations
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H
import builders_neutral as B

panel, panel_source = H.load_panel()
print(f"panel_source={panel_source} shape={panel.shape}")

results = {}

# ---------------------------------------------------------------- H028 ----
# main: size factor, unconditional, 1Y (5Y fwd_ret is 100% NaN in this build -- skip)
size_factor = B.build_size_factor(panel)
results["H028_size_1Y"] = H.evaluate(size_factor, "1Y", return_basis="resid",
                                      factor_id="H028_size_1Y", panel=panel,
                                      panel_source=panel_source, family="H028")

# quality-conditional cut: attach coarse ROA-like quality proxy (PIT, sparse/annual),
# split panel into quality-high (top tercile by symbol-level mean quality) vs
# quality-low (bottom tercile), run the SAME size factor within each subset.
panel_q = B.attach_quality_pit(panel)
sym_quality = panel_q.groupby("symbol")["quality"].mean().dropna()
if len(sym_quality) >= 30:
    q_hi = sym_quality[sym_quality >= sym_quality.quantile(2/3)].index
    q_lo = sym_quality[sym_quality <= sym_quality.quantile(1/3)].index
    panel_hi = panel[panel["symbol"].isin(q_hi)]
    panel_lo = panel[panel["symbol"].isin(q_lo)]
    size_hi = B.build_size_factor(panel_hi)
    size_lo = B.build_size_factor(panel_lo)
    results["H028_size_1Y_qualHI"] = H.evaluate(size_hi, "1Y", return_basis="resid",
                                                  factor_id="H028_size_1Y_qualHI", panel=panel_hi,
                                                  panel_source=panel_source, family="H028")
    results["H028_size_1Y_qualLO"] = H.evaluate(size_lo, "1Y", return_basis="resid",
                                                  factor_id="H028_size_1Y_qualLO", panel=panel_lo,
                                                  panel_source=panel_source, family="H028")
    print(f"quality proxy: n_symbols={len(sym_quality)}, hi_n={len(q_hi)}, lo_n={len(q_lo)}")
else:
    print(f"H028 quality split SKIPPED -- only {len(sym_quality)} symbols with quality proxy")

# ---------------------------------------------------------------- H032 ----
mom = B.build_momentum_12_1_factor(panel)
for basis in ("raw", "excess", "resid"):
    fid = f"H032_mom121_1Y_{basis}"
    results[fid] = H.evaluate(mom, "1Y", return_basis=basis, factor_id=fid,
                                panel=panel, panel_source=panel_source, family="H032")

# ---------------------------------------------------------------- H033 ----
# NOTE: 'resid' basis subtracts beta_252(t)*mkt_fwd from the target -- testing
# beta itself against that target would be mechanically ~tautological (the
# beta contribution is defined OUT of the target). Use 'excess' (raw - mkt_fwd,
# not stock-beta-adjusted) as the non-circular basis for a standalone-beta test.
beta_factor = B.build_beta_factor(panel)
results["H033_beta_1Y_excess"] = H.evaluate(beta_factor, "1Y", return_basis="excess",
                                              factor_id="H033_beta_1Y_excess", panel=panel,
                                              panel_source=panel_source, family="H033")
# size-controlled cut: beta IC within size terciles (small/mid/large mktcap_log)
mktcap_mean = panel.groupby("symbol")["mktcap_log"].mean().dropna()
terciles = {"small": mktcap_mean[mktcap_mean <= mktcap_mean.quantile(1/3)].index,
            "large": mktcap_mean[mktcap_mean >= mktcap_mean.quantile(2/3)].index}
for name, syms in terciles.items():
    p_t = panel[panel["symbol"].isin(syms)]
    b_t = B.build_beta_factor(p_t)
    fid = f"H033_beta_1Y_excess_{name}cap"
    results[fid] = H.evaluate(b_t, "1Y", return_basis="excess", factor_id=fid,
                                panel=p_t, panel_source=panel_source, family="H033")

# ---------------------------------------------------------------- H034 ----
rev5 = B.build_shortterm_reversal_factor(panel, lookback=5)
results["H034_rev5d_1M_resid"] = H.evaluate(rev5, "1M", return_basis="resid",
                                              factor_id="H034_rev5d_1M_resid", panel=panel,
                                              panel_source=panel_source, family="H034")
rsi2 = B.build_rsi2_factor(panel)
results["H034_rsi2_1M_resid"] = H.evaluate(rsi2, "1M", return_basis="resid",
                                             factor_id="H034_rsi2_1M_resid", panel=panel,
                                             panel_source=panel_source, family="H034")

# supplementary non-monotone (U-shape) check for H034: decile mean fwd raw
# return for the RSI2 factor, extremes vs middle (outside harness's single
# monotonicity number, which only tests LINEAR rank order).
f = H._normalize_factor(rsi2)
p = panel[["date", "symbol", "fwd_ret_1M_raw"]].rename(columns={"fwd_ret_1M_raw": "target_raw"})
merged = f.merge(p, on=["date", "symbol"], how="inner").dropna()
merged["decile"] = merged.groupby("date")["factor"].transform(
    lambda s: __import__("pandas").qcut(s.rank(method="first"), 10, labels=False, duplicates="drop"))
decile_means = merged.groupby("decile")["target_raw"].mean()
print("\nRSI2 decile mean fwd_1M_raw (0=most-overbought/least-oversold factor value .. 9=most-oversold):")
print(decile_means.to_string())

# ------------------------------------------------------------- summary ----
print("\n=== VERDICT TABLE ===")
for k, v in results.items():
    ic = v.get("ic", {}).get("ic_mean")
    icir = v.get("ic", {}).get("ic_ir")
    verdict = v.get("verdict", v.get("status"))
    n_obs = v.get("n_obs")
    print(f"{k:32s} IC={ic!s:>8.4s} IC_IR={icir!s:>8.4s} n_obs={n_obs!s:>7s} -> {verdict}")

out_path = Path(__file__).resolve().parents[1] / "cards" / "_worker_batch_summary.json"
out_path.write_text(json.dumps({k: v for k, v in results.items()}, indent=2, default=str), encoding="utf-8")
print(f"\nsummary written: {out_path}")
