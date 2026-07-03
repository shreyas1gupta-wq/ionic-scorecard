"""Unit tests for SIG-11 (Track-2 signal stack v1).

(a) synthetic series where each criterion's pass/fail is known by construction
(b) L3 PIT test: signals at date D unchanged when future rows are appended (prefix-equality)
(c) universe test: a symbol not in the PIT snapshot at D is excluded even if data exists

Run: PYTHONIOENCODING=utf-8 python test_sig11.py
"""
from __future__ import annotations

import os
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib"))
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\track2"))
import data11 as D11
import sig11 as S11

# enough history for MA200 + 22-session-rising + 252-session 52w window with margin
N = S11.SESSIONS_52W + S11.MA200_RISE_LOOKBACK + S11.MOM_12M + S11.MOM_SKIP + 30


def _bdate_range(n: int, start: str = "2015-01-01") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


def _make_series(symbol: str, closes: np.ndarray, volumes: np.ndarray | None = None) -> pd.DataFrame:
    dates = _bdate_range(len(closes))
    if volumes is None:
        volumes = np.full(len(closes), 100_000.0)
    return pd.DataFrame({
        "symbol": symbol,
        "date": dates,
        "open": closes,
        "high": closes,
        "low": closes,
        "close": closes,
        "volume": volumes,
        "oi": 0,
    })


def _steady_uptrend(n: int, start: float = 100.0, daily_ret: float = 0.0025) -> np.ndarray:
    """Smooth, monotonic uptrend -> should satisfy every Minervini criterion by construction:
    close always above every rising MA, 50>150>200 stacking holds once MAs mature, always
    within a few % of its running high (52w high), always far above its running low."""
    return start * (1.0 + daily_ret) ** np.arange(n)


def _flat_series(n: int, level: float = 100.0) -> np.ndarray:
    return np.full(n, level)


def _downtrend(n: int, start: float = 500.0, daily_ret: float = -0.0025) -> np.ndarray:
    return start * (1.0 + daily_ret) ** np.arange(n)


class TestCriteriaByConstruction(unittest.TestCase):
    """(a) Each synthetic symbol is built to isolate a specific pass/fail, then checked
    against compute_signals with a fully-permissive synthetic PIT universe."""

    @classmethod
    def setUpClass(cls):
        n = N
        panels = []

        # PASS_ALL: clean steady uptrend from a low base -> every criterion true.
        panels.append(_make_series("PASS_ALL", _steady_uptrend(n, start=50.0, daily_ret=0.0030)))

        # FAIL_FLAT: dead-flat price the whole history -> close==MA50==MA150==MA200 (not
        # strictly above), 200MA not rising, not 30% above a 52w low that equals the close,
        # fails almost everything -> definitely fails c1 (close > 150 & 200, strict).
        panels.append(_make_series("FAIL_FLAT", _flat_series(n, level=100.0)))

        # FAIL_DOWNTREND: monotonic decline -> close well below every MA, MA200 falling.
        panels.append(_make_series("FAIL_DOWNTREND", _downtrend(n, start=500.0, daily_ret=-0.0025)))

        # FAIL_NEAR_52W_LOW: uptrend for most of history, then a sharp recent plunge to
        # just above its own 52-week low, staying there -> fails c6 (>=30% above 52w low)
        # and c7 (within 25% of 52w high) even though MAs may still be somewhat stacked.
        base = _steady_uptrend(n - 60, start=50.0, daily_ret=0.0030)
        plunge_target = base[-1] * 0.55  # land near the base's own recent range, not the min
        plunge = np.linspace(base[-1], plunge_target, 40)
        tail = np.full(20, plunge_target)
        panels.append(_make_series("FAIL_NEAR_52W_LOW", np.concatenate([base, plunge, tail])))

        # FAIL_RS: uptrend but far weaker than PASS_ALL's, so its blended-momentum
        # percentile rank should land below the RS_PCT_GATE (70) in a cross-section that
        # includes PASS_ALL and other stronger names. Multiple weak-momentum names are
        # added so a single strong leader cannot be pushed below the 70th percentile
        # merely by outnumbering it.
        for i in range(6):
            panels.append(_make_series(f"WEAK_RS_{i}", _steady_uptrend(n, start=50.0, daily_ret=0.00005)))

        # FAIL_MA_STACK: long uptrend, then a decline that dwells near the trough (fills most
        # of the trailing 50d window with low prices, dragging MA50 down) followed by a
        # sharp recent V-bounce that lifts the close back above MA150/MA200 before MA50 has
        # had time to recover. Isolates c4 (50>150>200) as the failure while c1/c2/c3 hold.
        decl_len, dwell_len, bounce_len, frac = 30, 40, 5, 0.85
        pre_len = n - decl_len - dwell_len - bounce_len
        long_up = _steady_uptrend(pre_len, start=50.0, daily_ret=0.0030)
        decl = np.linspace(long_up[-1], long_up[-1] * frac, decl_len)
        dwell = np.full(dwell_len, long_up[-1] * frac)
        bounce = np.linspace(long_up[-1] * frac, long_up[-1] * frac * 1.15, bounce_len)
        panels.append(_make_series("FAIL_MA_STACK", np.concatenate([long_up, decl, dwell, bounce])))

        cls.panel = pd.concat(panels, ignore_index=True)
        cls.asof = cls.panel["date"].max()
        cls.universe = set(cls.panel["symbol"].unique())

        # Monkeypatch pit_universe to a fully-permissive synthetic universe covering exactly
        # the synthetic symbols (isolates the criteria logic from the real PIT snapshot file).
        cls._orig_pit_universe = S11.D11.pit_universe
        S11.D11.pit_universe = lambda date: cls.universe

        cls.sig = S11.compute_signals(cls.panel, cls.asof)
        cls.by_symbol = cls.sig.set_index("symbol")

    @classmethod
    def tearDownClass(cls):
        S11.D11.pit_universe = cls._orig_pit_universe

    def test_pass_all_passes_every_criterion(self):
        row = self.by_symbol.loc["PASS_ALL"]
        for c in S11.CRITERION_COLS:
            self.assertTrue(bool(row[c]), f"PASS_ALL should satisfy {c}")
        self.assertTrue(bool(row["ALL_PASS"]))

    def test_flat_fails_close_above_mas(self):
        row = self.by_symbol.loc["FAIL_FLAT"]
        self.assertFalse(bool(row["c1_close_above_150_200"]))
        self.assertFalse(bool(row["ALL_PASS"]))

    def test_downtrend_fails_close_above_mas_and_ma_stack(self):
        row = self.by_symbol.loc["FAIL_DOWNTREND"]
        self.assertFalse(bool(row["c1_close_above_150_200"]))
        self.assertFalse(bool(row["c3_200ma_rising"]))
        self.assertFalse(bool(row["c4_50_above_150_above_200"]))
        self.assertFalse(bool(row["ALL_PASS"]))

    def test_near_52w_low_fails_c6_and_c7(self):
        row = self.by_symbol.loc["FAIL_NEAR_52W_LOW"]
        self.assertFalse(bool(row["c6_above_52w_low"]))
        self.assertFalse(bool(row["c7_within_52w_high"]))
        self.assertFalse(bool(row["ALL_PASS"]))

    def test_weak_momentum_fails_rs_gate(self):
        row = self.by_symbol.loc["WEAK_RS_0"]
        self.assertLess(row["rs_pct"], S11.RS_PCT_GATE)
        self.assertFalse(bool(row["c8_rs_pct_ge70"]))
        self.assertFalse(bool(row["ALL_PASS"]))

    def test_ma_stack_fails_only_c4(self):
        row = self.by_symbol.loc["FAIL_MA_STACK"]
        self.assertTrue(bool(row["c1_close_above_150_200"]))
        self.assertTrue(bool(row["c2_150_above_200"]))
        self.assertTrue(bool(row["c3_200ma_rising"]))
        self.assertFalse(bool(row["c4_50_above_150_above_200"]))
        self.assertFalse(bool(row["ALL_PASS"]))

    def test_breakout_vol_flag_fires_on_volume_spike(self):
        n = N
        closes = _steady_uptrend(n, start=50.0, daily_ret=0.0030)
        volumes = np.full(n, 100_000.0)
        volumes[-1] = 100_000.0 * 3.0  # today's volume = 3x its own trailing 50d average
        df = _make_series("VOL_SPIKE", closes, volumes)
        universe = {"VOL_SPIKE"}
        orig = S11.D11.pit_universe
        S11.D11.pit_universe = lambda date: universe
        try:
            sig = S11.compute_signals(df, df["date"].max())
        finally:
            S11.D11.pit_universe = orig
        self.assertTrue(bool(sig.set_index("symbol").loc["VOL_SPIKE", "breakout_vol_flag"]))


class TestPrefixEquality(unittest.TestCase):
    """(b) L3 PIT: signals computed at date D must be IDENTICAL whether or not rows dated
    after D exist in the panel passed to compute_signals. This is the no-lookahead guarantee."""

    def test_future_rows_do_not_change_past_signal(self):
        n = N
        extra = 40
        closes_full = _steady_uptrend(n + extra, start=50.0, daily_ret=0.0025)
        full_df = _make_series("STABLE_A", closes_full)

        # a second name so RS percentile has a real cross-section, also extended into the future
        closes_full_b = _steady_uptrend(n + extra, start=80.0, daily_ret=0.0010)
        full_df_b = _make_series("STABLE_B", closes_full_b)

        panel_full = pd.concat([full_df, full_df_b], ignore_index=True)
        asof = panel_full["date"].sort_values().unique()[n - 1]  # a cut point strictly before the tail

        panel_prefix = panel_full[panel_full["date"] <= asof].copy()

        universe = {"STABLE_A", "STABLE_B"}
        orig = S11.D11.pit_universe
        S11.D11.pit_universe = lambda date: universe
        try:
            sig_prefix_only = S11.compute_signals(panel_prefix, asof)
            sig_with_future = S11.compute_signals(panel_full, asof)
        finally:
            S11.D11.pit_universe = orig

        sig_prefix_only = sig_prefix_only.reset_index(drop=True)
        sig_with_future = sig_with_future.reset_index(drop=True)

        pd.testing.assert_frame_equal(
            sig_prefix_only.sort_values("symbol").reset_index(drop=True),
            sig_with_future.sort_values("symbol").reset_index(drop=True),
            check_exact=False,
        )


class TestPITUniverseExclusion(unittest.TestCase):
    """(c) A symbol with full panel data but ABSENT from the PIT snapshot at date D must be
    excluded from compute_signals' output at D, even though its price history qualifies it
    on every price/volume criterion."""

    def test_non_member_with_qualifying_data_is_excluded(self):
        n = N
        member = _make_series("MEMBER_OK", _steady_uptrend(n, start=50.0, daily_ret=0.0030))
        # NONMEMBER has IDENTICAL price action to a name that would otherwise ALL_PASS.
        nonmember = _make_series("NONMEMBER_LEADER", _steady_uptrend(n, start=50.0, daily_ret=0.0035))
        panel = pd.concat([member, nonmember], ignore_index=True)
        asof = panel["date"].max()

        orig = S11.D11.pit_universe
        # PIT universe deliberately excludes NONMEMBER_LEADER despite qualifying data existing.
        S11.D11.pit_universe = lambda date: {"MEMBER_OK"}
        try:
            sig = S11.compute_signals(panel, asof)
        finally:
            S11.D11.pit_universe = orig

        self.assertIn("MEMBER_OK", set(sig["symbol"]))
        self.assertNotIn("NONMEMBER_LEADER", set(sig["symbol"]),
                          "L3 UNIVERSE LEAK: non-PIT-member symbol leaked into signal output")

    def test_universe_changes_membership_over_time(self):
        """A symbol eligible at D1 but dropped from the snapshot before D2 must disappear
        from compute_signals(D2) even though its raw panel rows still exist."""
        n = N
        s = _make_series("DROPPED_LATER", _steady_uptrend(n, start=50.0, daily_ret=0.0030))
        panel = s
        dates = sorted(panel["date"].unique())
        d1, d2 = dates[n // 2], dates[-1]

        orig = S11.D11.pit_universe

        def fake_pit(date):
            date = pd.Timestamp(date)
            return {"DROPPED_LATER"} if date <= d1 else set()

        S11.D11.pit_universe = fake_pit
        try:
            sig_d1 = S11.compute_signals(panel, d1)
            sig_d2 = S11.compute_signals(panel, d2)
        finally:
            S11.D11.pit_universe = orig

        self.assertIn("DROPPED_LATER", set(sig_d1["symbol"]))
        self.assertNotIn("DROPPED_LATER", set(sig_d2["symbol"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
