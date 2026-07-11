"""Static AST lookahead scanner (adopted from Vibe-Trading's purity-gate concept, 2026-07-11).
Mechanically flags common lookahead patterns (T1-T10 taxonomy instances) in a backtest script
BEFORE it runs. Complements lib/lookahead_audit.py (runtime one-day-lag test).

Usage: python ast_lookahead_scan.py <script.py> [more.py ...]
Exit 0 = clean, 1 = findings (review each; some may be justified — document why in the run card).
"""
import ast
import sys
from pathlib import Path


class LookaheadVisitor(ast.NodeVisitor):
    def __init__(self):
        self.findings = []

    def flag(self, node, code, msg):
        self.findings.append((node.lineno, code, msg))

    def visit_Call(self, node):
        f = node.func
        name = getattr(f, "attr", getattr(f, "id", ""))
        # .shift(-n) — future values pulled backward
        if name == "shift":
            for a in node.args:
                if isinstance(a, ast.UnaryOp) and isinstance(a.op, ast.USub):
                    self.flag(node, "T-SHIFT", "shift(-n): future value into present row")
                if isinstance(a, ast.Constant) and isinstance(a.value, (int, float)) and a.value < 0:
                    self.flag(node, "T-SHIFT", "shift(negative): future value into present row")
        # centered rolling windows see the future
        if name in ("rolling", "ewm"):
            for kw in node.keywords:
                if kw.arg == "center" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.flag(node, "T-CENTER", "rolling(center=True): window includes future bars")
        # backfill propagates future data backward
        if name in ("bfill", "backfill"):
            self.flag(node, "T-BFILL", "bfill: future observation fills past NaN")
        if name == "fillna":
            for kw in node.keywords:
                if kw.arg == "method" and isinstance(kw.value, ast.Constant) and str(kw.value.value) in ("bfill", "backfill"):
                    self.flag(node, "T-BFILL", "fillna(method='bfill')")
        # whole-sample normalization (mean/std/min/max/quantile over full frame then applied per-row)
        if name in ("mean", "std", "min", "max", "quantile", "median", "zscore"):
            # only flag when called on a bare Name (likely the full panel), not on a slice/rolling
            tgt = getattr(f, "value", None)
            if isinstance(tgt, ast.Name):
                self.flag(node, "T-FULLSAMPLE?", f"full-object .{name}(): if used to normalize signals, "
                                                 "it leaks the whole sample (use expanding/rolling)")
        # train_test_split without shuffle=False on time series
        if name == "train_test_split":
            if not any(kw.arg == "shuffle" and isinstance(kw.value, ast.Constant) and kw.value.value is False
                       for kw in node.keywords):
                self.flag(node, "T-SPLIT", "train_test_split default shuffle=True: temporal leakage")
        self.generic_visit(node)

    def visit_Subscript(self, node):
        # iloc[i+1] style forward indexing inside loops — heuristic: BinOp Add on loop var
        if isinstance(node.slice, ast.BinOp) and isinstance(node.slice.op, ast.Add):
            self.flag(node, "T-FWDIDX?", "index arithmetic [x+y]: verify not future-row access "
                                         "(fills at next bar are OK IF execution-time, not signal-time)")
        self.generic_visit(node)


def scan(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [(e.lineno or 0, "PARSE", str(e))]
    v = LookaheadVisitor()
    v.visit(tree)
    return v.findings


if __name__ == "__main__":
    total = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        finds = scan(p)
        print(f"== {p.name}: {len(finds)} finding(s)")
        for ln, code, msg in finds:
            print(f"   L{ln:<5} [{code}] {msg}")
        total += len(finds)
    sys.exit(1 if total else 0)
