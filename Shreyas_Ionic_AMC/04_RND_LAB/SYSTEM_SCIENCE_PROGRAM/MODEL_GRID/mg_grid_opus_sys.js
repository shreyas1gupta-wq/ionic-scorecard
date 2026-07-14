export const meta = { name: 'mg-grid-opus_sys', description: 'MODEL-GRID opus_sys: single-call rows + optional system', phases: [ { title: 'Models' }, { title: 'System' } ] }
const RES = "c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/MODEL_GRID/results"
const JOBS = [
]
const SYS_TASKS = [
  ["MG01", "You are designing (not running) a backtest. Idea: monthly rebalanced momentum portfolio, top-20 by 6-month return, NIFTY500 universe, 2015-2026, Indian daily data. Write the complete backtest SPECIFICATION a junior quant could implement without asking questions: data requirements and their point-in-time rules, universe construction, signal timing and execution convention, cost model, the control experiments you would demand before believing any result, and explicit kill criteria. Be concrete; no platitudes.\n"],
  ["MG02", "Propose exactly 5 falsifiable alpha hypotheses for Indian equity or index-derivatives markets that a small research team could test cheaply. For each: the mechanism (WHY it should exist and who is on the losing side), the single cheapest test that could kill it, the data needed, and what result kills it. The 5 must be materially different from each other (not variants of one idea). Avoid ideas that require data a small team cannot get.\n"],
  ["MG03", "Design a resume-safe daily data-ingestion pipeline that pulls end-of-day files from an exchange archive through an unreliable corporate proxy (~0.7 MB/s, random stalls, occasional IP blocks). Requirements: nothing is ever lost or double-ingested across crashes/restarts, corrupt downloads never enter the dataset, a human is alerted only when action is genuinely needed, and a new machine can take over mid-history. Specify the mechanisms concretely (files, ledgers, checks, retries, alerts) - not principles.\n"],
  ["MG04", "Write a one-page pre-mortem risk memo: our paper book is short index options (defined-risk spreads plus some naked strangles) going into a week containing a central-bank decision and a national budget announcement. Assume it is 12 months from now; imagine the book just took its worst week ever. What killed it? Quantify the plausible tail (be numeric where possible), state the exact de-risk triggers you would pre-commit to, and be honest about what cannot be hedged at acceptable cost.\n"],
  ["MG05", "You draw n times, uniformly at random WITH replacement, from the set {1, 2, ..., n}. Let D be the number of DISTINCT values you observe. Give the exact closed-form expression for E[D], and the exact limit of E[D]/n as n approaches infinity. Show your derivation briefly, then state the final answers unambiguously.\n"],
  ["MG06", "Cards are drawn one at a time from an infinite stream where each card is one of the 4 suits, uniformly at random and independently. Let T be the number of draws until you have seen ALL 4 suits at least once. Give the exact expected value of T (as a fraction) and its decimal value, with a brief derivation.\n"],
  ["MG07", "We are considering adopting a third-party quarterly fundamentals dataset for Indian equities (vendor claims 2005-present, ~2000 companies, with announcement dates). Design the verification protocol you would run BEFORE this data is allowed anywhere near a backtest: the specific sampling and cross-checks, how you would test the announcement dates are genuinely point-in-time, how you would detect coverage or survivorship problems, and the quarantine/acceptance rules. Concrete steps, not principles.\n"],
  ["MG08", "A paper abstract claims: a machine-learning strategy on US equities achieves a 2.1 Sharpe ratio out-of-sample, 2010-2023, using 940 features derived from prices, fundamentals, and news sentiment. List the 6 most likely reasons this number will not survive scrutiny or replication, ranked by probability, each with the specific mechanism (HOW it inflates the number) and the single check you would run to confirm or clear it.\n"],
]

const OUT = { type: 'object', properties: { saved: { type: 'string' } }, required: ['saved'] }
const A = { type: 'object', properties: { answer: { type: 'string' } }, required: ['answer'] }
const NT = ' Answer in one pass. Do NOT use any tools except the single Write specified. Do not read, list, or search files. '
const NT2 = ' Answer in one pass. Do NOT use any tools; the task text is your entire input. '

phase('Models')
for (let i = 0; i < JOBS.length; i += 3) {
  const chunk = JOBS.slice(i, i + 3)
  await parallel(chunk.map(([m, tid, txt]) => () => agent(
    txt + '\n' + NT + 'Write your COMPLETE answer to ' + RES + '/' + tid + '_' + m + '.md and return {saved:"ok"}.',
    { label: 'MG:' + m + ':' + tid, phase: 'Models', schema: OUT, model: m })))
  log('models ' + Math.min(i + 3, JOBS.length) + '/' + JOBS.length)
}

phase('System')
for (let i = 0; i < SYS_TASKS.length; i += 2) {
  const chunk = SYS_TASKS.slice(i, i + 2)
  await parallel(chunk.map(([tid, txt]) => () => (async () => {
    const r1 = await agent('Answer this task in your capacity as Head of Quant.\n' + txt + NT2 + 'Return {answer: ...}', { label: 'SYS1:' + tid, phase: 'System', schema: A, agentType: 'quant-head-arjun-rao' })
    const r2 = await agent('Red-team the draft answer below: refute weak parts, add what is missing.\nTASK:\n' + txt + '\nDRAFT:\n' + (r1 ? r1.answer : '') + NT2 + 'Return {answer: ...}', { label: 'SYS2:' + tid, phase: 'System', schema: A, agentType: 'red-team-nikhil-bose' })
    return agent('As CIO, produce the final consolidated answer, integrating the draft and the red-team critique. Quality over length.\nTASK:\n' + txt + '\nDRAFT:\n' + (r1 ? r1.answer : '') + '\nCRITIQUE:\n' + (r2 ? r2.answer : '') + NT + 'Write the COMPLETE final answer to ' + RES + '/' + tid + '_SYSTEM.md and return {saved:"ok"}.', { label: 'SYS3:' + tid, phase: 'System', schema: OUT, agentType: 'cio-rajan-mehta' })
  })()))
  log('system ' + Math.min(i + 2, SYS_TASKS.length) + '/' + SYS_TASKS.length)
}
return { done: true, single: JOBS.length, system: SYS_TASKS.length }
