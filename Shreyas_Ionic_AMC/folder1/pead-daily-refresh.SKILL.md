---
name: pead-daily-refresh
description: "Daily PEAD scan: cache-busted live Tijori pull, score, update the tracker artifact, post a digest."
---

You are running the daily PEAD (Post-Earnings-Announcement-Drift) scan for an Indian-equities trader. Be fully self-contained; work through these steps.

STEP 1 — Fetch data (IMPORTANT: bust the CDN cache).
The bare Tijori URL is served from a stale CDN cache. You MUST append a unique cache-busting query parameter every run, e.g. web_fetch on https://www.tijorifinance.com/results/quarterly-results/?nocache=YYYYMMDDHHMM (substitute the current date-time so the value is unique each run). This returns the live quarterly-results feed (public, no login). Confirm the "Latest Quarterly Results" date at the top of the page equals today or yesterday; if it is older, the cache-bust did not work — try again with a different unique parameter value before proceeding, and note the discrepancy in the digest.
Each result row has: company name, company URL, result date (may say "Today"/"Yesterday" — resolve to an actual YYYY-MM-DD), Market Cap (₹ Cr; note "L Cr" = lakh crore = ×100000), PE, and a table with Sales / Operating Profit / Net Profit rows showing YoY Growth %, QoQ Growth %, and three quarterly absolute values (latest quarter, previous quarter, year-ago quarter). The first page of latest results is enough.

STEP 2 — Parse every row into an object with fields:
{name, ticker, date (YYYY-MM-DD), mcap (number, Cr), pe, salesYoY, salesQoQ, opYoY, npYoY, npQoQ, sMar(latest sales), sDec(prev-qtr sales), sPrev(year-ago sales), opMar(latest OP), opPrev(year-ago OP), npMar(latest NP), npDec(prev-qtr NP), npPrev(year-ago NP), url}. Use null for blank/"-" cells. For `ticker`, put the NSE trading symbol when you can identify it (e.g. Steel Strips Wheels = SSWL, Jindal Saw = JINDALSAW, Tata Elxsi = TATAELXSI); otherwise use an empty string. This ticker powers the in-app TradingView chart link, so accuracy matters — leave it blank rather than guessing wrong.

STEP 3 — Compute the funda PEAD Score (0–100) for each row, exactly this logic:
- Growth magnitude (max 30): +clamp((npYoY-25)/75,0,1)*14; +clamp((salesYoY-8)/22,0,1)*8; +clamp((opYoY-15)/45,0,1)*8.
- Acceleration (max 20): +5 if salesQoQ>0; +5 if npQoQ>0; +5 if npMar>npDec; +5 if npMar>npPrev.
- Margin/operating-leverage (max 25): if opMar,sMar>0,opPrev,sPrev>0 add clamp((opMar/sMar*100 - opPrev/sPrev*100)/4,0,1)*13; if opYoY>salesYoY add clamp((opYoY-salesYoY)/30,0,1)*12.
- Quality of beat (start 25, subtract): -12 & flag "NP up OP down" if opYoY<=0 and npYoY>0; else -8 & flag "NP>>OP" if npYoY>opYoY+40; -8 & flag "sales down" if salesYoY<0 and npYoY>0; -10 & flag "low base" if |npMar|<5; -15 & flag "loss qtr" if npMar<0. Floor at 0.
Total = sum, rounded. Grade: >=75 A, >=60 B, >=45 C, else D. (Banks/NBFCs have odd "operating profit" — treat their scores with caution and note it.)

STEP 4 — Update the tracker artifact.
Call list_artifacts, find id "pead-scanner-tracker", Read its `path`. In the HTML, replace the `const FEED_META={...};` line with updated asOf (the feed's latest date), fetched (today's date), and an appropriate note. Replace the entire `const FEED=[ ... ];` array with the freshly parsed rows (all rows, not just >500 — the UI filters), including the `ticker` field on each. Keep all other HTML/JS byte-for-byte identical. Write the modified HTML to a file in the outputs directory and call update_artifact with id "pead-scanner-tracker", the new html_path, and a one-line update_summary. Do NOT touch localStorage logic — the user's watchlist must survive.

STEP 5 — Post a short digest (plain, skimmable):
- The feed's latest date (and a warning only if it is still stale after cache-busting).
- Companies reporting in the last 2 days with mcap > 500 Cr, sorted by PEAD Score. For each: name, mcap, Sales/OP/NP YoY, PEAD Score + grade, and any quality flags.
- Explicitly call out grade A or B names above 500 Cr as the ones worth eyeballing on the chart for a 5%+ gap. If none qualify, say so in one line.
Keep it concise. The user filters mcap > 500 Cr and hunts fly-worthy prints (big, clean, durable beats), not routine 15% growth. They handle price/volume and entries manually.
