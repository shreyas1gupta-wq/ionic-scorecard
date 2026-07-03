---
name: paper
description: Paper-trading desk — log intended trades BEFORE action, mark fills vs Angel quotes, weekly reconcile. Use for /paper log <trade>, /paper mark, /paper reconcile.
---
# /paper — paper-trading SOP (RESEARCH_SOP §12)
1. LOG (before market action): append to PAPER_LEDGER open-positions — timestamp, strategy ID, legs, intended price, size, stop/kill. Signals must be logged BEFORE fills are known.
2. MARK: fetch actual Angel quotes (angel_cfg login) at action time; record marked fill vs intended.
3. RECONCILE (weekly, Tara): close-out rows, tracking error decomposition, reconciliation-log row. TE unexplained = post-mortem trigger.
4. Ledger is append-only; corrections = new rows. DoD progress tracked per strategy (≥20 trades / 8 weeks).
