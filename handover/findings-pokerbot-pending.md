# pokerbot changes with rounds still open (no findings text lost)

Delete each section in that change's landing commit.

- Opponent-model design 36e2ae4be45b: LANDED on pokerbot main at 659c6b7 by
  reconcile on a stale round-4 pass, without round 8 (rounds 5-7 had failed;
  the round-7 fixes 72eff27 and 5f7a1a8 are in). Treat as NOT DONE. Next: a
  fresh reviewer, round 8, default lens, against trunk's
  OPPONENT_MODEL_DESIGN.md + tools/check_design_numbers.py (680 figures, 25
  tests). Wording-only: record and it is done. Substantive: escalate the cost
  (seven rounds already) rather than run round 9 unasked.
- Bots survey 14d64950c0bc: round-2 fixes at 903c15e (autosave 814f417 is
  history). Round-3 review was stopped mid-way. Re-dispatch round 3. Open
  judgment for it: PokerSnowie's (a) ~ at :391-393 rests on vendor pages, the
  same evidence that demoted Shanky to ?; OpenHoldem (a) ✓ was kept on
  MagicNumbers.h:67-76 (kMaxNumberOfPlayers = 10).
- Solvers survey 048795519f43: round-1 fixes at de64884 (+ autosaves). Round-2
  review was stopped before it began. Re-dispatch round 2; the brief points at
  research/solvers/run_texassolver_flop.py and the Rust re-runs (:197-214,
  :246-266, commands :858-899).
- Evaluation strategy 45e49ce81e40: round 3 FAILED (8 findings, 4 substantive:
  assumes a 52-card conversion REFERENCE_NOTES.md says is out; a 4-seat figure
  in the summary; sha-gating rule stated inconsistently). The full findings are
  only in the previous session's reviewer transcript
  (~/.claude/projects/-Users-chasethompson-heater/60db9bfd-…/subagents/agent-a7dfbff12396707c8.jsonl,
  last assistant message). Lower priority under the taper.
- Table-size notes 984aa6810a05: round-3 fixes at 9c4a168; needs round 4.
  Reviewers must judge cross-references against the companion commit named in
  the round-3 brief (5aa40b8), not the moving tree.
