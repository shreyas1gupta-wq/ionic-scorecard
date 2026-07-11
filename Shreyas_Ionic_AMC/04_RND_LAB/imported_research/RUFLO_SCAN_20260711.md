# Ruflo scan (2026-07-11, one-fetch assessment, Principal-requested)
**Repo:** github.com/ruvnet/ruflo — claude-flow REBRANDED (63.9k stars, v3.25.6 Jul-2026, TypeScript/Rust). Agent meta-harness: 100+ agents, swarm topologies, vector memory (AgentDB/HNSW), 12 auto-triggered background workers, multi-provider routing, MCP-based.

## Verdict: DO NOT INSTALL — ADOPT 3 IDEAS
Blocked/incompatible: needs Node.js (absent); swarms + auto background workers directly contradict the sequential one-task rule and would multiply token burn; 35-plugin surface is unauditable for a 2-desk shop.

## Adoptable ideas (all Python/markdown, ~0 marginal tokens)
1. **Vector index over firm knowledge** (their AgentDB concept): local embeddings (sentence-transformers via HF, one-time ~100MB download) + hnswlib over KNOWLEDGE_BASE + KILLED_IDEAS + SESSION_JOURNAL + ideas/. Upgrades Lakshmi's prior-art checks from grep to semantic recall ("have we tried this before" catches rephrased ideas). → IDEA_PIPELINE ops-tooling intake; needs Principal data-download nod (HF model weights).
2. **Trajectory learning / ReasoningBank concept**: after each campaign, distill WHAT-WORKED/WHAT-FAILED patterns into a reusable playbook — we already do this via /retro + KNOWLEDGE_BASE lessons; the delta is their structured trigger→action→outcome format for lessons. Cheap format upgrade for KNOWLEDGE_BASE entries.
3. **Behavioral trust scoring** (their federation formula, 0.4*success + 0.2*uptime + 0.2*threat + 0.2*integrity): adapt weights for persona AlphaPoints/leaderboard scoring in SELF_IMPROVEMENT.md — score agents on catch-rate/kill-honesty/cost-discipline rather than gut feel. CEO/board-meet material, not urgent.

Not adopted: GOAP planner (our gate pipeline already encodes this), multi-provider routing (single-provider shop), cost-tracker plugin (TOKEN_POLICY + /spend-report cover it).
