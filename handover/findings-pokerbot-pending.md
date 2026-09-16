# pokerbot changes still in the review loop

Delete each section in that change's landing commit. Every survey's open
findings are in the fixer briefs whose agents were RUNNING at the handover;
their reports arrive in the next context as messages. If a report never
arrives, the findings are in the review store notes (`store/reviews`, by
change id) and, for the engine survey, in `findings-7f09949cb56f-engine-r2.md`.

- Opponent-model design 36e2ae4be45b: LANDED on pokerbot main at 659c6b7 by
  reconcile on a stale round-4 pass, without round 8. NOT DONE. Next: fresh
  reviewer, round 8, default lens, against trunk's OPPONENT_MODEL_DESIGN.md
  plus tools/check_design_numbers.py (680 figures, 25 tests). Wording-only:
  record and done. Substantive: escalate the cost; no round 9 unasked.
- Engine survey 7f09949cb56f: round-2 fixer RUNNING (branch at autosave
  59022d1 + its work); findings in `findings-7f09949cb56f-engine-r2.md` with
  the measurement rule. Then round 3.
- Exploitation survey 76bbf2823a53: round-2 fixes at 5d274ee (all 16, six
  networks counted by research/count_phh_networks.py, reproduced byte for
  byte). Round-3 review RUNNING. Then land or fix.
- Bots survey 14d64950c0bc: round 3 FAILED (a quotation attributed to
  ENGINE_ALTERNATIVES.md that exists in no version of it; section 5 narrows
  the forefront rule below CLAUDE.md's table; ppl-interpreter (a) ✓
  contradicted by its code; the vendor-evidence rule applied inconsistently,
  decided by the stoker: a vendor's technical manual or price page may carry a
  labelled mark, a strength claim may not). Round-3 fixer RUNNING. Then round 4.
- Solvers survey 048795519f43: round 2 FAILED (heads-up engine "settled";
  opponent range in the settled plan is reserved to the engine; memory-bound
  claim unmeasured; GTOpen misread cost quoted from two cells of a 0-461
  table; 9 accuracy items; timings to re-run under the measurement rule).
  Round-2 fixer RUNNING. Then round 3.
- Evaluation strategy 45e49ce81e40: round 3 FAILED (8 findings, 4
  substantive: assumes a 52-card conversion REFERENCE_NOTES.md says is out; a
  4-seat figure in the summary; sha-gating rule stated inconsistently). Full
  findings only in the previous session's reviewer transcript
  (~/.claude/projects/-Users-chasethompson-heater/60db9bfd-…/subagents/agent-a7dfbff12396707c8.jsonl,
  last assistant message). Lower priority.
- Table-size notes 984aa6810a05: round-3 fixes at 9c4a168; needs round 4;
  judge cross-references against companion commit 5aa40b8.
- After all four surveys pass: dispatch ONE worker to reconcile them into a
  plan with measured numbers and record the forefront-rule decision in
  pokerbot/CLAUDE.md. Known unknown for that brief: how the bot sees a real
  table and acts on it; no survey settled it.
