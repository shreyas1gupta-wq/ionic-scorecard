"""pathsafe — makes PATH-DEPENDENT backtest claims honest by construction.

WHY THIS EXISTS (three real failures on 2026-07-30, all the same error class):
  1. ITM option + fixed 25-pt trail reported **+3.03 pts => 69% CAGR**. Re-run with a conservative
     candle trail: **-0.46 pts**. The gap was purely how intra-bar ambiguity was resolved.
  2. S1 z-score fade: clipping endpoint P&L at -40 reported **Calmar 9.88 / 226% CAGR**. Replayed with
     a REAL stop against 1-min bars: **Calmar 0.043 / 0.7%**. A 230x overstatement.
  3. Overshoot measured at **+9.58 pts** by inverting a pre-spike price against the POST-spike spot.
     Corrected: **+2.12 pts** (median -0.16). A 4.5x overstatement.
In every case the flattering answer came from data that could not resolve the question, and in every
case the error ran in the direction the researcher was hoping for. Vigilance is not a control; code is.

THE THREE RULES THIS MODULE ENFORCES
  R1  A stop/trail/target result may only be computed from a BAR PATH with high+low. Endpoint-only
      data raises PathSafeError. `clip_pnl_as_stop` raises unconditionally — clipping endpoint P&L is
      NOT a stop and never was.
  R2  Every path-dependent exit returns BOTH bounds (adverse-first and favourable-first). There is no
      API that returns a single number. `pnl` is an alias for the PESSIMISTIC bound.
  R3  A summary whose optimistic/pessimistic spread exceeds `max_spread_frac` of the pessimistic mean
      is marked UNRELIABLE and must be reported as a RANGE. `assert_reliable()` raises on it.

USAGE
    from pathsafe import simulate_exit, summarize, require_path
    res = [simulate_exit(bars_for_trade, entry, direction=+1, stop=60, trail=60) for ...]
    s = summarize(res)            # prints both bounds + ambiguity rate
    s.assert_reliable()           # raises if the bounds disagree materially
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = ["PathSafeError", "ExitResult", "Summary", "require_path", "simulate_exit",
           "summarize", "clip_pnl_as_stop", "self_test"]


class PathSafeError(RuntimeError):
    """Raised when a path-dependent claim is attempted without the path, or on a banned shortcut."""


# --------------------------------------------------------------------------- R1: data validation
def require_path(bars, *, need=("high", "low"), min_bars: int = 3) -> pd.DataFrame:
    """Validate that `bars` can actually answer a path question. Raise loudly if not."""
    if bars is None:
        raise PathSafeError("no bars supplied: a stop/trail/target result requires a bar path")
    if not isinstance(bars, pd.DataFrame):
        raise PathSafeError(f"bars must be a DataFrame with {need}; got {type(bars).__name__}")
    missing = [c for c in need if c not in bars.columns]
    if missing:
        raise PathSafeError(
            f"bars is missing {missing} -> this is ENDPOINT-ONLY data. A stop/trail/target result "
            "cannot be computed from it. (On 2026-07-30 clipping endpoint P&L at -40 produced a "
            "Calmar of 9.88 where the real stop gave 0.043 - a 230x error.)")
    if len(bars) < min_bars:
        raise PathSafeError(f"only {len(bars)} bars; need >= {min_bars} to resolve a path")
    return bars


def clip_pnl_as_stop(*_a, **_k):
    """BANNED. Clipping endpoint P&L is not a stop-loss and systematically overstates."""
    raise PathSafeError(
        "clip_pnl_as_stop() is BANNED. Clipping endpoint P&L at -X credits the benefit of a stop "
        "(trades that END worse than -X are truncated) while ignoring its cost (trades that DIP to "
        "-X intraday and then RECOVER are stopped out and become losses). Use simulate_exit() with "
        "a real bar path. Measured error from this exact shortcut: 230x (Calmar 9.88 vs 0.043).")


# --------------------------------------------------------------------------- R2: dual-bound result
@dataclass
class ExitResult:
    """A path-dependent exit outcome. Carries BOTH bounds; never a single number."""
    pnl_pessimistic: float          # intra-bar ties resolved AGAINST the position
    pnl_optimistic: float           # intra-bar ties resolved FOR the position
    reason_pessimistic: str
    reason_optimistic: str
    n_ambiguous_bars: int           # bars where both a favourable and adverse trigger were reachable
    n_bars: int

    @property
    def pnl(self) -> float:
        """Default = the PESSIMISTIC bound. Deliberate: the honest number is the easy one."""
        return self.pnl_pessimistic

    @property
    def is_ambiguous(self) -> bool:
        return self.n_ambiguous_bars > 0 or self.pnl_pessimistic != self.pnl_optimistic

    @property
    def spread(self) -> float:
        return self.pnl_optimistic - self.pnl_pessimistic


def simulate_exit(bars, entry: float, direction: int, *, stop: float = 0.0,
                  trail: float = 0.0, target: float = 0.0,
                  final_close_col: str = "close") -> ExitResult:
    """Simulate stop/trail/target on a real bar path, returning BOTH intra-bar resolutions.

    bars      : DataFrame with high/low (and close for the timeout exit), ordered, entry bar EXCLUDED
    direction : +1 long, -1 short
    stop/trail/target : in the same units as price. 0 disables that rule.
    A TARGET is treated as a resting LIMIT (exact fill, unambiguous). STOP and TRAIL are the
    ambiguous ones, so they drive the two bounds.
    """
    require_path(bars)
    if direction not in (1, -1):
        raise PathSafeError(f"direction must be +1 or -1, got {direction!r}")
    if not (stop or trail or target):
        raise PathSafeError("no exit rule given; for a pure timeout use the close directly")
    hi = bars["high"].to_numpy(float)
    lo = bars["low"].to_numpy(float)
    cl = (bars[final_close_col].to_numpy(float)
          if final_close_col in bars.columns else bars["high"].to_numpy(float))
    s = int(direction)

    def _run(adverse_first: bool):
        peak = 0.0
        for k in range(len(hi)):
            fav = (hi[k] - entry) if s > 0 else (entry - lo[k])
            adv = (lo[k] - entry) if s > 0 else (entry - hi[k])
            hit_stop = bool(stop) and adv <= -stop
            hit_trail = bool(trail) and (max(peak, fav) > trail) and ((max(peak, fav) - fav) >= trail)
            hit_tgt = bool(target) and fav >= target
            if adverse_first:
                if hit_stop:
                    return -stop, "stop", k
                if hit_tgt:
                    return target, "target", k
                if hit_trail:
                    return max(peak, fav) - trail, "trail", k
            else:
                if hit_tgt:
                    return target, "target", k
                if hit_trail:
                    return max(peak, fav) - trail, "trail", k
                if hit_stop:
                    return -stop, "stop", k
            peak = max(peak, fav)
        return s * (cl[-1] - entry), "timeout", len(hi) - 1

    p_pnl, p_why, _ = _run(True)
    o_pnl, o_why, _ = _run(False)
    amb = 0
    peak = 0.0
    for k in range(len(hi)):
        fav = (hi[k] - entry) if s > 0 else (entry - lo[k])
        adv = (lo[k] - entry) if s > 0 else (entry - hi[k])
        favourable = ((bool(target) and fav >= target) or
                      (bool(trail) and (max(peak, fav) > trail) and ((max(peak, fav) - fav) >= trail)))
        if (bool(stop) and adv <= -stop) and favourable:
            amb += 1
        peak = max(peak, fav)
    return ExitResult(float(p_pnl), float(o_pnl), p_why, o_why, amb, len(hi))


# --------------------------------------------------------------------------- R3: honest summary
@dataclass
class Summary:
    n: int
    mean_pessimistic: float
    mean_optimistic: float
    median_pessimistic: float
    ambiguous_trade_frac: float
    max_spread_frac: float = 0.25
    _rows: list = field(default_factory=list, repr=False)

    @property
    def spread(self) -> float:
        return self.mean_optimistic - self.mean_pessimistic

    @property
    def spread_frac(self) -> float:
        d = abs(self.mean_pessimistic)
        return float("inf") if d < 1e-9 else abs(self.spread) / d

    @property
    def reliable(self) -> bool:
        return self.spread_frac <= self.max_spread_frac

    def assert_reliable(self):
        if not self.reliable:
            raise PathSafeError(
                f"UNRELIABLE: pessimistic {self.mean_pessimistic:+.3f} vs optimistic "
                f"{self.mean_optimistic:+.3f} (spread {self.spread_frac:.0%} of the pessimistic mean, "
                f"limit {self.max_spread_frac:.0%}). {self.ambiguous_trade_frac:.1%} of trades had "
                "intra-bar ambiguity. Report this as a RANGE, not a number, or get finer bars.")
        return self

    def report(self) -> str:
        flag = "RELIABLE" if self.reliable else "*** UNRELIABLE - REPORT AS A RANGE ***"
        return (f"n={self.n}  pessimistic {self.mean_pessimistic:+.3f}  "
                f"optimistic {self.mean_optimistic:+.3f}  spread {self.spread_frac:.0%}  "
                f"ambiguous trades {self.ambiguous_trade_frac:.1%}  -> {flag}\n"
                f"  QUOTE THE PESSIMISTIC NUMBER ({self.mean_pessimistic:+.3f}). The optimistic bound "
                f"exists only to size the uncertainty.")


def summarize(results, *, max_spread_frac: float = 0.25, verbose: bool = True) -> Summary:
    rs = [r for r in results if isinstance(r, ExitResult)]
    if not rs:
        raise PathSafeError("summarize() needs ExitResult objects from simulate_exit()")
    p = np.array([r.pnl_pessimistic for r in rs], float)
    o = np.array([r.pnl_optimistic for r in rs], float)
    s = Summary(len(rs), float(p.mean()), float(o.mean()), float(np.median(p)),
                float(np.mean([r.is_ambiguous for r in rs])), max_spread_frac, rs)
    if verbose:
        print(s.report())
    return s


# --------------------------------------------------------------------------- self-test
def self_test():
    """Reproduces the 2026-07-30 failure modes and proves the guards catch them."""
    print("pathsafe self-test")
    # a path that dips to -50 then rallies to +100: a -40 stop MUST kill it
    bars = pd.DataFrame({"high": [100, 101, 160], "low": [95, 50, 150], "close": [100, 60, 155]})
    r = simulate_exit(bars, entry=100.0, direction=1, stop=40, trail=0, target=0)
    assert r.pnl_pessimistic == -40, r
    print(f"  [ok] dip-then-rally: real stop = {r.pnl_pessimistic:+.0f} "
          f"(a clip on the +55 endpoint would have shown +55)")
    # endpoint-only data must be refused
    try:
        simulate_exit(pd.DataFrame({"close": [1, 2, 3]}), 1.0, 1, stop=1)
        raise AssertionError("should have raised")
    except PathSafeError as e:
        print(f"  [ok] endpoint-only refused: {str(e)[:60]}...")
    # the banned shortcut
    try:
        clip_pnl_as_stop(pd.Series([1.0, -99.0]), -40)
        raise AssertionError("should have raised")
    except PathSafeError:
        print("  [ok] clip_pnl_as_stop() is banned")
    # ambiguity detection: one bar contains both stop and target
    amb = pd.DataFrame({"high": [100, 150, 120], "low": [99, 50, 110], "close": [100, 100, 115]})
    r2 = simulate_exit(amb, entry=100.0, direction=1, stop=40, target=40)
    assert r2.is_ambiguous and r2.pnl_pessimistic == -40 and r2.pnl_optimistic == 40
    print(f"  [ok] ambiguity flagged: pess {r2.pnl_pessimistic:+.0f} / opt {r2.pnl_optimistic:+.0f}")
    s = summarize([r, r2], verbose=False)
    try:
        s.assert_reliable()
        raise AssertionError("should have raised")
    except PathSafeError:
        print("  [ok] unreliable summary raises instead of reporting one number")
    print("all guards active")


if __name__ == "__main__":
    self_test()
