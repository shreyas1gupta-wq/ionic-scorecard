# -*- coding: utf-8 -*-
"""mf_lookthrough.py — MF portfolio look-through engine (Principal 2026-07-25).
Ingests AMC monthly portfolio disclosures from a DROP FOLDER, normalizes to parquet, then computes
for a client book: true look-through stock/sector exposure (direct + via funds), the double-pay
table (stocks held both directly and inside funds), concentration, and DEBT-RISK FLAGS:
  - any single debt ISSUER > 10% of the client book on look-through -> flag;
  - debt sleeve > 10% of book AND holdings rated below AA (or issuer trips our leverage/coverage
    gate in the scored universe) -> flag. (No full FI framework — flags only, per Principal.)
Storage-frugal: raw drop files pruned after RETAIN_DAYS; normalized snapshots keep the last
6 month-ends, quarter-ends thereafter. Outputs a compact .md digest (token-cheap) + csv.

Usage:
  python mf_lookthrough.py ingest                      # normalize whatever is in incoming/, prune
  python mf_lookthrough.py run <client_holdings.csv>   # compute look-through for a client book
Client CSV contract: columns = type(stock|fund), name, isin(optional), value_inr.
Drop folder: datasets/mf_holdings/incoming/  (AMC monthly portfolio .xlsx/.xls, any layout with an
ISIN header row; scheme name auto-detected from the sheet header or filename).
"""
import os, sys, re, glob, io, datetime
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BASE = os.path.join(ROOT, "datasets", "mf_holdings")
INCOMING = os.path.join(BASE, "incoming")
NORM = os.path.join(BASE, "normalized")
for d in (INCOMING, NORM):
    os.makedirs(d, exist_ok=True)
RETAIN_DAYS = 180
SCORED = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results", "full750_scored.csv")

# below-AA pattern, word-bounded so AA+/AAA never false-positive ("CARE A" yes, "CRISIL AA+" no)
LOW_PAT = r"(?:\bAA-\b|\bA[+-]?\b|\bBBB[+-]?\b|\bBB[+-]?\b|\bB\b|\bC\b|\bD\b|UNRATED)"


def _find_header(df):
    for i in range(min(25, len(df))):
        row = " ".join(str(x).upper() for x in df.iloc[i].tolist())
        if "ISIN" in row and ("% " in row or "NAV" in row or "NET ASSET" in row or "MARKET" in row):
            return i
    return None


def ingest():
    """Normalize every workbook in incoming/ -> one parquet per (file, month). Heuristic parser:
    finds the ISIN header row per sheet; columns mapped by name similarity."""
    today = datetime.date.today()
    n_ok = n_fail = 0
    for path in glob.glob(os.path.join(INCOMING, "*.xls*")):
        try:
            xl = pd.ExcelFile(path)
            frames = []
            for sh in xl.sheet_names:
                raw = xl.parse(sh, header=None)
                hi = _find_header(raw)
                if hi is None:
                    continue
                df = xl.parse(sh, header=hi)
                cols = {c: str(c).strip().upper() for c in df.columns}
                def pick(*keys):
                    for c, u in cols.items():
                        if any(k in u for k in keys):
                            return c
                    return None
                c_isin = pick("ISIN"); c_name = pick("NAME OF", "INSTRUMENT", "COMPANY", "SECURITY")
                c_pct = pick("% TO NAV", "% OF NAV", "NET ASSET", "% TO NET")
                c_rat = pick("RATING", "INDUSTRY/RATING")
                c_ind = pick("INDUSTRY", "SECTOR")
                if not (c_isin and c_pct):
                    continue
                sub = pd.DataFrame({
                    "isin": df[c_isin].astype(str).str.strip(),
                    "instrument": df[c_name].astype(str).str.strip() if c_name else "",
                    "pct_nav": pd.to_numeric(df[c_pct], errors="coerce"),
                    "rating": df[c_rat].astype(str).str.strip() if c_rat else "",
                    "industry": df[c_ind].astype(str).str.strip() if c_ind else "",
                })
                sub = sub[sub["isin"].str.match(r"^IN[A-Z0-9]{10}$", na=False)]
                sub = sub.dropna(subset=["pct_nav"])
                if sub["pct_nav"].max() <= 1.5:      # fractions, not percents
                    sub["pct_nav"] *= 100
                sub["scheme"] = sh if len(xl.sheet_names) > 1 else os.path.splitext(os.path.basename(path))[0]
                frames.append(sub)
            if not frames:
                print(f"  [skip] {os.path.basename(path)}: no parsable sheet"); n_fail += 1; continue
            out = pd.concat(frames, ignore_index=True)
            ym = today.strftime("%Y-%m")
            m = re.search(r"(20\d{2})[-_ ]?(\d{2}|[A-Za-z]{3})", os.path.basename(path))
            if m:
                ym = f"{m.group(1)}-{m.group(2)[:2] if m.group(2).isdigit() else pd.to_datetime(m.group(2), format='%b').strftime('%m')}"
            tag = re.sub(r"[^A-Za-z0-9]+", "_", os.path.splitext(os.path.basename(path))[0])[:50]
            out.to_parquet(os.path.join(NORM, f"holdings_{ym}_{tag}.parquet"), index=False)
            print(f"  [ok] {os.path.basename(path)}: {len(out)} rows, {out['scheme'].nunique()} schemes -> {ym}")
            n_ok += 1
        except Exception as e:
            print(f"  [fail] {os.path.basename(path)}: {e}"); n_fail += 1
    # retention: prune raw drops; thin normalized to last 6 month-ends + quarter-ends
    for p in glob.glob(os.path.join(INCOMING, "*")):
        if (datetime.date.today() - datetime.date.fromtimestamp(os.path.getmtime(p))).days > RETAIN_DAYS:
            os.remove(p)
    norms = sorted(glob.glob(os.path.join(NORM, "holdings_*.parquet")))
    months = sorted({os.path.basename(p).split("_")[1] for p in norms})
    keep = set(months[-6:]) | {m for m in months if m[5:7] in ("03", "06", "09", "12")}
    for p in norms:
        if os.path.basename(p).split("_")[1] not in keep:
            os.remove(p)
    print(f"ingest done: {n_ok} ok, {n_fail} failed · normalized months kept: {sorted(keep) if norms else '[]'}")


def _latest_holdings():
    norms = sorted(glob.glob(os.path.join(NORM, "holdings_*.parquet")))
    if not norms:
        return pd.DataFrame(columns=["isin", "instrument", "pct_nav", "rating", "industry", "scheme"])
    latest_ym = max(os.path.basename(p).split("_")[1] for p in norms)
    return pd.concat([pd.read_parquet(p) for p in norms
                      if os.path.basename(p).split("_")[1] == latest_ym], ignore_index=True)


def run(client_csv):
    book = pd.read_csv(client_csv)
    book.columns = [c.strip().lower() for c in book.columns]
    total = book["value_inr"].sum()
    hold = _latest_holdings()
    if hold.empty:
        print("NOTE: no normalized fund holdings on disk — drop AMC monthly portfolio files into "
              f"{INCOMING} and run `ingest` first. Producing direct-only view.")
    stocks = book[book["type"].str.lower() == "stock"].copy()
    funds = book[book["type"].str.lower() == "fund"].copy()

    # look-through: fund value x pct_nav  (scheme matching is normalization-based, not exact)
    def _norm(s):
        return re.sub(r"[^a-z]", "", str(s).lower())   # letters only — dates/digits in filenames drop out
    def _match(a, b):
        a, b = _norm(a), _norm(b)
        n = min(len(a), len(b), 10)
        return n >= 6 and a[:n] == b[:n]
    rows = []
    for _, f in funds.iterrows():
        h = hold[hold["scheme"].map(lambda x: _match(f["name"], x))] if len(hold) else hold
        for _, r in h.iterrows():
            rows.append((r["instrument"], r["isin"], f["name"], f["value_inr"] * r["pct_nav"] / 100,
                         r["rating"], r["industry"]))
    lt = pd.DataFrame(rows, columns=["instrument", "isin", "via_fund", "value_inr", "rating", "industry"])

    # double-pay: same instrument direct + via fund
    dp = []
    for _, s in stocks.iterrows():
        via = lt[lt["instrument"].str.contains(str(s["name"]).split()[0], case=False, na=False)] if len(lt) else lt
        if len(via):
            dp.append((s["name"], s["value_inr"] / total * 100, via["value_inr"].sum() / total * 100,
                       via["via_fund"].nunique()))
    dp = pd.DataFrame(dp, columns=["stock", "direct_pct", "via_funds_pct", "n_funds"])

    # debt-risk flags (Principal: flags only, no framework)
    flags = []
    if len(lt):
        # debt = carries a credit rating (CRISIL/CARE/ICRA AAA..D pattern) OR non-equity ISIN series
        _rat = lt["rating"].str.upper().str.contains(
            r"(?:\bAAA\b|\bAA[+-]?\b|\bA1\+?|\bA[+-]?\b|\bBBB|\bBB\b|\bSOV\b|\bD\b)", regex=True, na=False)
        _series = lt["isin"].str[9:11].isin(["07", "08", "24"])   # NCD/bond/CP series
        debt = lt[lt["isin"].str.match(r"^INE.{9}$", na=False) & (_rat | _series)]
        by_issuer = debt.groupby("instrument")["value_inr"].sum() / total * 100
        for issuer, pct in by_issuer[by_issuer > 10].items():
            flags.append(f"ISSUER CONCENTRATION: {issuer} = {pct:.1f}% of book on look-through (>10%)")
        debt_sleeve = debt["value_inr"].sum() / total * 100
        low = debt[debt["rating"].str.upper().str.contains(LOW_PAT, regex=True, na=False)]
        if debt_sleeve > 10 and len(low):
            flags.append(f"CREDIT QUALITY: debt sleeve {debt_sleeve:.1f}% of book (>10%) includes "
                         f"{len(low)} below-AA holdings ({low['value_inr'].sum()/total*100:.1f}% of book)")
        # cross-ref scored universe leverage gate for listed issuers
        if os.path.exists(SCORED):
            sc = pd.read_csv(SCORED, usecols=["symbol", "debt_equity", "interest_coverage"])
            risky = sc[(pd.to_numeric(sc["debt_equity"], errors="coerce") > 2.5) |
                       (pd.to_numeric(sc["interest_coverage"], errors="coerce") < 2.0)]["symbol"].tolist()
            hit = by_issuer[by_issuer.index.str.upper().str.split().str[0].isin([r.split()[0] for r in risky])]
            for issuer, pct in hit[hit > 3].items():
                flags.append(f"ISSUER STRESS: {issuer} ({pct:.1f}% look-through) trips the scored-universe "
                             f"leverage/coverage gate (non-financial)")

    # outputs: csv + compact md digest
    out_csv = os.path.splitext(client_csv)[0] + "_lookthrough.csv"
    (lt.groupby(["instrument", "industry"])["value_inr"].sum().sort_values(ascending=False)
       .reset_index()).to_csv(out_csv, index=False)
    md = [f"# Look-through digest — {os.path.basename(client_csv)} ({datetime.date.today()})",
          f"- Book: Rs {total/1e7:.2f} Cr · {len(stocks)} stocks ({stocks['value_inr'].sum()/total*100:.0f}%) · "
          f"{len(funds)} funds ({funds['value_inr'].sum()/total*100:.0f}%)",
          f"- Fund holdings snapshot: {'NONE — direct-only view' if hold.empty else f'{hold.scheme.nunique()} schemes, latest month on disk'}"]
    if len(dp):
        md.append("\n## Double-pay (direct + via funds)")
        for _, r in dp.iterrows():
            md.append(f"- {r['stock']}: {r['direct_pct']:.1f}% direct + {r['via_funds_pct']:.1f}% via {int(r['n_funds'])} fund(s)")
    md.append("\n## Debt-risk flags" if flags else "\n## Debt-risk flags\n- none tripped")
    md += [f"- {f}" for f in flags]
    md.append(f"\nFull table: {os.path.basename(out_csv)} · flags per Principal rule (2026-07-25): "
              f">10% issuer look-through, >10% debt sleeve with sub-AA, scored-universe leverage gate.")
    dig = os.path.splitext(client_csv)[0] + "_LOOKTHROUGH.md"
    io.open(dig, "w", encoding="utf-8").write("\n".join(md))
    print("\n".join(md))
    print("\nwritten:", out_csv, "+", dig)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        ingest()
    elif len(sys.argv) > 2 and sys.argv[1] == "run":
        run(sys.argv[2])
    else:
        print(__doc__)
