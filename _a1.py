import sys, os, pickle, collections
sys.path.insert(0, r"C:/tmp/kit-publish/Shreyas_Ionic_AMC/09_PRODUCT/pr_template")
ctx = pickle.load(open(r"C:/tmp/kit-publish/_ctxD.pkl","rb"))
from lib import lookthrough as LT
t = ctx["totals"]
print("TOTALS keys:", sorted(t.keys()))
print("grand", t.get("grand"), "eq_pct", t.get("eq_pct"), "fi", t.get("fi_pct"), "alt", t.get("alt_pct"))
funds = ctx["funds"]; eq = ctx["equity"]; oth = ctx.get("other") or []
print("n funds", len(funds), "n equity", len(eq), "n other", len(oth))
print("fund categories:", collections.Counter(f.get("category") for f in funds))
print("fund asset_class:", collections.Counter(f.get("asset_class") for f in funds))
print("equity_gross_pct present:", sum(1 for f in funds if f.get("equity_gross_pct") is not None))
print("full_lookthrough_mix ->", LT.full_lookthrough_mix(ctx))
# debt funds by asset class
dbt = [f for f in funds if (f.get("asset_class") or "").lower().startswith("fixed")]
print("n fixed-income funds:", len(dbt), "sum weight", round(sum(f["weight_pct"] for f in dbt),4),
      "sum value", sum(f["value_inr"] for f in dbt))
for f in dbt: print("   ", f["name"][:48], round(f["weight_pct"],3), f.get("category"))
