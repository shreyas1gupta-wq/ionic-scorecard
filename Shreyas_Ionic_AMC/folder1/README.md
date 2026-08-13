# PEAD Scanner — Project Handover

A daily **Post-Earnings-Announcement-Drift (PEAD)** workflow for Indian equities.
Every day it pulls the latest quarterly results, scores each company on a
fundamental "fly-worthy beat" score (0–100), refreshes a browser-based
tracker, and posts a short digest of the best names above ₹500 Cr market cap.

It is **fundamentals only** — no price or volume. The trader reads the tape and
manages entries/exits manually; this tool's job is to surface *which* prints are
big, clean and durable enough to be worth charting.

## What's in this package

| File | What it is |
|---|---|
| `README.md` | This file — overview, setup, and the one known issue. |
| `PEAD_SCORING.md` | The scoring methodology in full: the four pillars, the exact formulas, worked examples, and the banks/NBFC caveat. Read this first to understand the score. |
| `pead_score.py` | Standalone reference scorer in Python. No dependencies. Run it on the built-in sample or on your own rows. This is the source of truth for the math. |
| `pead-daily-refresh.SKILL.md` | The automation spec — the exact 5-step instruction set the daily scheduled task runs (fetch → parse → score → update tracker → digest). |
| `pead-scanner-tracker.html` | The tracker web app. Open in any browser. Two tabs: **Latest results feed** (auto-scored) and **My watchlist** (your saved candidates + catalyst notes + manual price log). |

## How the pieces fit together

```
   Tijori quarterly-results feed  (public, no login)
                |
                v
   [ pead-daily-refresh.SKILL.md ]   <- runs once a day, automated
                |
     parse rows -> score each (logic == pead_score.py / PEAD_SCORING.md)
                |
        +-------+--------+
        v                v
  updates FEED in     posts a skimmable
  pead-scanner-       digest (A/B names
  tracker.html        > 500 Cr, sorted)
```

- **The score** is defined once (`PEAD_SCORING.md`) and implemented twice,
  identically: in `pead_score.py` and in the `scoreEP()` JavaScript inside
  `pead-scanner-tracker.html`. Change one, change the other.
- **The tracker** stores your watchlist and price logs in the browser's
  `localStorage`, so it survives daily data refreshes. Nothing is sent anywhere;
  it's a single self-contained HTML file.

## Quick start

**Score some data offline:**
```bash
python3 pead_score.py                      # scores the built-in sample feed
python3 pead_score.py rows.json            # scores your own rows (JSON list)
python3 pead_score.py rows.json --min-mcap 500
```
Row schema is documented at the top of `pead_score.py` and in `PEAD_SCORING.md`.

**Use the tracker:** open `pead-scanner-tracker.html` in a browser. The *Latest
results feed* tab is pre-loaded with the last refresh; hit **+ Watch** on a name
to move it to *My watchlist*, where you can add catalysts (rate their
durability) and log daily price/volume to watch the base build.

**Automate the daily refresh:** the workflow in `pead-daily-refresh.SKILL.md`
is designed to run as a scheduled task in a Claude Cowork/agent environment that
has web-fetch and the tracker artifact. It re-fetches, re-scores and updates the
tracker's embedded `FEED` array in place each morning.

## Data source
[Tijori Finance — Quarterly Results](https://www.tijorifinance.com/results/quarterly-results/).
Public, free tier, no login required. Fields used: company, market cap, PE, and
the Sales / Operating Profit / Net Profit table (YoY %, QoQ %, and the three
quarterly absolute values). Note Tijori writes large caps as "L Cr" = lakh crore
= ×100000. Page 1 (the latest ~20 rows) is enough for the daily scan.

## Known issue — feed cache staleness (READ THIS)
Tijori's bare results URL is served through a **CDN edge cache** that can lag the
live site by several days. Your browser sees fresh results because it runs the
page's JavaScript / hits a live edge; a plain server-side fetch of the bare URL
can get a stale cached copy.

The fix baked into the workflow is to append a **unique cache-busting query
parameter every run** (`?nocache=YYYYMMDDHHMM`). That normally forces a fresh
copy. Two caveats for whoever runs this:
1. Some sandboxed fetch tools only allow URLs returned verbatim by a web search,
   which rejects the cache-buster variant and can leave you pinned to the stale
   copy. If that happens, either fetch through a real browser (rendering the
   page's JS) or paste the rows in manually.
2. The workflow already tells the agent to **check the feed's "Latest Quarterly
   Results" date against today/yesterday and warn in the digest if it's stale**.
   Trust that warning — if it fires, the scores reflect an older batch, not
   today's prints.
