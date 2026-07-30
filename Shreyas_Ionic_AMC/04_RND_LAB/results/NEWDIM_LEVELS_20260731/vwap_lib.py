"""DIMENSION 2 -- Anchored VWAP + sigma bands.
VOLUME SOURCE: same option-chain total_vol proxy as volume_profile.py (chain_front_15min.parquet),
same coverage 2021-05..2026-05, same limits (15-min resolution, options activity not underlying
volume) -- stated once here, applies to every anchor below.
vwap_proxy = cumsum(spot_ref * total_vol) / cumsum(total_vol), cumulative WITHIN an anchor group
that resets at: SESSION (each day), WEEK (each W-FRI period), MONTH (each calendar month), or
SWING (each confirmed 2-bar-fractal 15-min swing pivot -- resets at the CONFIRMATION bar, 2 bars
after the actual pivot bar, to stay strictly PIT-safe: you cannot anchor to a pivot before you
know it is one).
band_std = rolling 8-bucket (~2h) stdev of (spot_ref - vwap_proxy) WITHIN the anchor group.
upper/lower at k=1,2 sigma. PIT-safe: the band tested against bar t is the PRIOR bucket's
(shift 1), exactly the INDICATOR_MINE_20260730 A5/A6 convention this extends.
"""
import numpy as np
import pandas as pd

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"


def anchor_group(front: pd.DataFrame, kind: str, swing15: pd.DataFrame = None) -> pd.Series:
    if kind == "session":
        return front["date"]
    if kind == "week":
        return front["bucket"].dt.to_period("W-FRI").astype(str)
    if kind == "month":
        return front["bucket"].dt.to_period("M").astype(str)
    if kind == "swing":
        piv = swing15[(swing15["is_swing_high"]) | (swing15["is_swing_low"])].copy()
        piv = piv.dropna(subset=["confirmed_at"]).sort_values("confirmed_at")
        piv["epoch"] = np.arange(len(piv))
        piv["confirmed_at"] = pd.to_datetime(piv["confirmed_at"]).astype("datetime64[ns]")
        f = front.copy()
        f["bucket"] = pd.to_datetime(f["bucket"]).astype("datetime64[ns]")
        f = f.sort_values("bucket")
        m = pd.merge_asof(f, piv[["confirmed_at", "epoch"]].rename(columns={"confirmed_at": "bucket"}),
                           on="bucket", direction="backward")
        m["epoch"] = m["epoch"].fillna(-1)
        return m.set_index(f.index)["epoch"].reindex(front.index)
    raise ValueError(kind)


def build_bands(front: pd.DataFrame, kind: str, swing15: pd.DataFrame = None) -> pd.DataFrame:
    f = front.dropna(subset=["spot_ref"]).sort_values("bucket").reset_index(drop=True).copy()
    f["grp"] = anchor_group(f, kind, swing15).to_numpy()
    f["cw"] = f["spot_ref"] * f["total_vol"]
    g = f.groupby("grp")
    f["cum_w"] = g["cw"].cumsum()
    f["cum_v"] = g["total_vol"].cumsum()
    f["vwap_proxy"] = f["cum_w"] / f["cum_v"].replace(0, np.nan)
    f["resid"] = f["spot_ref"] - f["vwap_proxy"]
    if kind == "swing":
        # SWING anchors reset too often (every ~9 bars by construction) for an in-group rolling(8)
        # to ever populate -- band WIDTH here uses a trailing GLOBAL window (not anchor-reset) so
        # it reflects "how wide is normal dispersion right now" independent of the last reset;
        # only the vwap CENTERLINE resets per anchor group. Disclosed simplification, not hidden.
        f["band_std"] = f["resid"].rolling(8, min_periods=8).std()
    else:
        f["band_std"] = f.groupby("grp")["resid"].transform(lambda x: x.rolling(8, min_periods=8).std())
    for k in (1, 2):
        f[f"upper{k}_prior"] = (f["vwap_proxy"] + k * f["band_std"]).shift(1)
        f[f"lower{k}_prior"] = (f["vwap_proxy"] - k * f["band_std"]).shift(1)
    # a shift(1) at a group boundary would leak the PRIOR group's band into a brand-new group's
    # first bar -- null it out explicitly
    new_grp = f["grp"] != f["grp"].shift(1)
    for k in (1, 2):
        f.loc[new_grp, [f"upper{k}_prior", f"lower{k}_prior"]] = np.nan
    keep = ["bucket", "date"] + [f"{s}{k}_prior" for s in ("upper", "lower") for k in (1, 2)]
    return f[keep]


def main():
    front = pd.read_parquet(f"{OUT}/chain_front_15min.parquet")
    swing15 = pd.read_parquet(f"{OUT}/swing15.parquet")
    for kind in ("session", "week", "month", "swing"):
        bands = build_bands(front, kind, swing15)
        bands.to_parquet(f"{OUT}/vwap_bands_{kind}.parquet")
        cov = bands["upper1_prior"].notna().mean()
        print(f"{kind}: rows={len(bands)} band-coverage={cov:.3f}")


if __name__ == "__main__":
    main()
