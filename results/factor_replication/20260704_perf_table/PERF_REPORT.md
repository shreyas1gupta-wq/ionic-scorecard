# Six-series momentum performance table (Principal request, 2026-07-04)
Filed by main desk from Arjun's returned report. PRICE-index basis, NO costs, dividends excluded uniformly (~1-1.5pp/yr understatement on ALL series; relative comparisons unaffected). As-of 2026-01-22 (binding common date = frozen panel end).

## 3-line summary
1. Momentum BEATS NIFTY 50 over 3Y/5Y/10Y (+5 to +9pp/yr over 5Y) but LOST to it over the last 1Y (2025 momentum drawdown: official N200M30 +3.8% vs N50 +9.2%).
2. Paid in vol (19-23% vs 14-16%) and pain (maxDD -68/-70% official vs -60% N50, GFC-concentrated).
3. Full-period official edge: N200M30 +5.1pp/yr, N500M50 +6.9pp/yr over NIFTY 50.

## Table (CAGR/vol per window; excess vs N50)
| Series | 1Y | 3Y | 5Y | 10Y | Full | MaxDD | Excess (1/3/5/10/full) |
|---|---|---|---|---|---|---|---|
| N200M30 replica | 2.3%/15.9% | 19.8%/21.0% | 21.3%/21.7% | 17.5%/21.0% | 16.7% | -71.3% | -6.9/+8.0/+9.3/+4.4/+5.1 |
| N200M30 OFFICIAL | 3.8%/16.4% | 16.9%/18.0% | 16.9%/19.1% | 17.9%/19.1% | 16.6% | -67.9% | -5.5/+5.1/+4.9/+4.8/+5.1 |
| N500M50 replica | 0.5%/19.2% | 17.3%/22.9% | 19.5%/23.1% | 15.1%/22.1% | 13.9% | -75.5% | -8.7/+5.5/+7.6/+2.0/+2.4 |
| N500M50 OFFICIAL | 2.2%/18.4% | 19.0%/20.3% | 20.9%/20.4% | 18.6%/20.2% | 18.4% | -70.5% | -7.0/+7.3/+9.0/+5.5/+6.9 |
| NIFTY 50 | 9.2%/11.5% | 11.8%/12.0% | 12.0%/13.9% | 13.0%/16.1% | 11.5% | -59.9% | benchmark |
| NIFTY 500 | 7.5%/12.8% | 14.3%/12.9% | 14.2%/14.3% | 14.0%/16.1% | 11.8% | -64.3% | -1.7/+2.6/+2.2/+0.9/+0.3 |

## Replication quality: N500M50 corr 0.93/TE 8.2-9.0% (first build); N200M30 0.933/8.5%. Replica window-CAGRs drift +-3-4pp at 3-5Y horizons (two-sided TE) — trust replicas at 10Y/full, officials for exact window returns. N200M30 replica 3Y/5Y ran HOT (+2.9/+4.4pp vs official); N500M50 replica systematically LOW (-1.4 to -3.5pp; float-weight + small/mid-tail coverage — known D-M4 residuals).
## Naming: NSE's N500 factor index is "Momentum 50" (no N500 Momentum 30 exists).
## Audits: degenerate detectors clean (GFC troughs land on real dates); benchmark splice 1:1 verified; D-028 PASS 0/0.
Detail: perf_table.csv, replication_quality_era.csv, level_*.csv, build_perf_table.py, run.log
