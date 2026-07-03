---
name: to-md
description: TOKEN SAVER — convert docx/xlsx/csv/parquet/pdf to lean Markdown BEFORE reading (35x+ reduction typical). Use for /to-md <file>, or automatically whenever a task requires reading a binary/office file.
---
# /to-md — file-to-markdown digest (token discipline)
1. Run: `python Shreyas_Ionic_AMC/05_DATA_OFFICE/scripts/to_md.py <input> [out.md] [--rows N] [--sheet NAME]` (python = the pythoncore-3.14-64 path in CLAUDE.md).
2. Read the .md OUTPUT, never the binary. Tables get head-N + shape + numeric summary (enough for 95% of tasks; ask for more rows only if the digest is insufficient).
3. Digests of REUSED files go next to the source as `<name>.md`; one-off digests go to scratchpad.
4. RULE for all agents: reading a .docx/.xlsx/.pdf directly when a digest would do is a token-waste event (−5 AP per TOKEN_POLICY).
