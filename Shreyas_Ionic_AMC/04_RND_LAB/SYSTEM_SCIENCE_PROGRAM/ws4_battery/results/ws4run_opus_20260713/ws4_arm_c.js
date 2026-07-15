export const meta = { name: 'ws4-arm-c', description: 'WS-4 arm C: 3-stage pipeline, <=3 tasks concurrent', phases: [ { title: 'ArmC' } ] }
const VARIANT = "C"
const RES = "c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/ws4_battery/results/ws4run_opus_20260713/raw"
const ARM_PROMPT = "You are reviewing a quantitative research submission for a trading firm.\nThe task text below contains a scenario and either code or a results write-up.\n\nReview this. Identify any defects that would make the result wrong or fake.\nBe specific.\n\nRules for your answer:\n- If you find defects, name each one: the exact line/field/claim, the mechanism\n  by which it corrupts the result, and the correct fix.\n- Some submissions contain NO material defect. If so, say exactly that: \"No\n  material defect.\" Do not invent problems; minor style or robustness notes must\n  be clearly labelled as non-material comments.\n- Finish with a numbered list: your claimed material defects (or \"none\").\n\n[TASK.MD TEXT PASTED HERE]"
const TASKS = [
  ["T13", "# T13 \u2014 Review request: 12-1 momentum on the NIFTY-500\n\nClassic cross-sectional momentum submission. Prices are the survivorship-complete\nadjusted union panel (includes delisted names). Execution is next-open entry with\ncircuit/zero-volume no-fill checks and 45bp/side costs.\n\nReported result: 2013-2025, top-50 monthly-rebalanced basket 24.8% CAGR vs index 12.1%.\n\n```python\nimport pandas as pd\n\nclose = pd.read_parquet(\"union_close_panel.parquet\")   # adjusted, incl. delisted names\n\nuniverse = pd.read_csv(\"nifty500_constituents.csv\")[\"Symbol\"].tolist()\n# downloaded from the index provider's website, 2026-07 refresh, 500 symbols\n\nclose = close[[c for c in close.columns if c in universe]]\nret = close.pct_change()\n\n# 12-1 momentum: return from t-252 to t-21 (skip the most recent month)\nmom = close.shift(21).pct_change(231)\n\nmonth_ends = close.groupby(close.index.to_period(\"M\")).tail(1).index\nweights = pd.DataFrame(0.0, index=close.index, columns=close.columns)\n\nfor me in month_ends:\n    row = mom.loc[me].dropna()\n    if len(row) < 200:\n        continue\n    top = row.nlargest(50).index\n    nxt = close.index[close.index.searchsorted(me, side=\"right\")]\n    weights.loc[nxt:, :] = 0.0\n    weights.loc[nxt:, top] = 1.0 / 50\n\n# next-open entries approximated at next session; no-fill on circuit-locked or\n# zero-volume opens handled inside apply_fill_rules()\nport = apply_fill_rules(weights.shift(1) * ret)\nport -= turnover_costs(weights, bps_per_side=45)\nprint(\"CAGR:\", ann_return(port), \" maxDD:\", max_drawdown(port))\n```\n\n**Review this. Identify any defects that would make the result wrong or fake. Be specific.**\n"],
  ["T15", "# T15 \u2014 Review request: IV-percentile strangle seller\n\nWeekly short-vol rule on the index. The author standardizes the IV level before\nthresholding, \"so the rule generalizes across vol regimes\". Entry-day option prices\nare verified; entries are next-session-open after the signal evaluates true.\n\nReported result: 2015-2025, 214 entries, avg +1.7% of premium net, hit 79%,\nworst trade -21% of premium (Mar-2020 skipped by the crash filter).\n\n```python\nimport pandas as pd\n\nhist = pd.read_parquet(\"nifty_iv_daily.parquet\")       # 2015-2025 daily ATM IV\n\nmu = hist[\"iv\"].mean()\nsd = hist[\"iv\"].std()\nhist[\"iv_z\"] = (hist[\"iv\"] - mu) / sd\n\n# entry: IV meaningfully rich vs its normal level, but not crash regime\nhist[\"entry\"] = (hist[\"iv_z\"] > 1.0) & (hist[\"iv_z\"] < 2.5)\n\ntrades = []\nfor d in hist.index[hist[\"entry\"]]:\n    t = sell_weekly_strangle(\n        signal_day=d,\n        entry=\"next_open\",                 # fills at next session's open prints\n        wings=(0.97, 1.03),\n        exit_rule=(\"hold_to_expiry\",),\n        liquidity=(\"both_legs_traded\",),   # skip if either leg had no trades\n    )\n    if t is not None:\n        trades.append(t.net_pnl_pct_premium)\n\ntr = pd.Series(trades)\nprint(\"entries:\", len(tr), \" mean:\", round(tr.mean(), 2), \"% of premium\",\n      \" hit:\", round((tr > 0).mean() * 100, 1), \"%\")\n```\n\n**Review this. Identify any defects that would make the result wrong or fake. Be specific.**\n"],
]

const OUT = { type: 'object', properties: { answer: { type: 'string' } }, required: ['answer'] }
const SAVED = { type: 'object', properties: { saved: { type: 'string' } }, required: ['saved'] }
const NOFILES = " HARD CONSTRAINT: do not read, list, or search ANY files or directories; no code execution; the text above is your entire evidence. Return {answer: <your full review>}."

// VARIANT is set at generation time: 'C' (full firm: real persona agentTypes) or 'C2' (ablated: neutral roles, no personas)
async function runTask(tid, txt) {
  const base = ARM_PROMPT + "\n---BEGIN TASK---\n" + txt + "\n---END TASK---\n"
  const full = VARIANT === 'C'
  const o1 = full ? { agentType: 'quant-head-arjun-rao' } : {}
  const o2 = full ? { agentType: 'red-team-nikhil-bose' } : {}
  const o3 = full ? { agentType: 'cio-rajan-mehta' } : {}
  const p1 = full ? "Review this submission in your capacity as Head of Quant.\n" : "You are an experienced quantitative code and results reviewer.\n"
  const p2 = full ? "Red-team this: attack BOTH the submission AND the prior reviewer's findings — refute weak claims, find what was missed, flag invented defects.\n" : "You are a skeptical second reviewer instructed to refute: attack BOTH the submission AND the prior reviewer's findings — refute weak claims, find what was missed, flag invented defects.\n"
  const p3 = full ? "As CIO, issue the consolidated verdict after the two reviews below. Keep only defects that survive; obey the answer rules verbatim.\n" : "You are the final arbiter consolidating two reviews below into one verdict. Keep only defects that survive; obey the answer rules verbatim.\n"
  const r1 = await agent(p1 + base + NOFILES, { label: VARIANT + '1rev:' + tid, phase: 'Arm' + VARIANT, schema: OUT, ...o1 })
  const r2 = await agent(p2 + base + "\n---PRIOR REVIEWER FINDINGS---\n" + (r1 ? r1.answer : '(reviewer unavailable)') + "\n---END PRIOR---\n" + NOFILES, { label: VARIANT + '2red:' + tid, phase: 'Arm' + VARIANT, schema: OUT, ...o2 })
  const r3 = await agent(p3 + base + "\n---REVIEWER---\n" + (r1 ? r1.answer : '') + "\n---RED TEAM---\n" + (r2 ? r2.answer : '') + "\n---END---\n" + NOFILES.replace('Return {answer: <your full review>}', 'Write your COMPLETE consolidated final answer to ' + RES + '/' + tid + '_arm' + VARIANT + '.md and return {saved: "ok"}'), { label: VARIANT + '3syn:' + tid, phase: 'Arm' + VARIANT, schema: SAVED, ...o3 })
  return r3
}

const out = []
for (let i = 0; i < TASKS.length; i += 3) {
  const chunk = TASKS.slice(i, i + 3)
  const r = await parallel(chunk.map(([tid, txt]) => () => runTask(tid, txt)))
  out.push(...r)
  log('ArmC done ' + Math.min(i + 3, TASKS.length) + '/20')
}
return { armC_completed: out.filter(Boolean).length }
