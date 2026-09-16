# pokerbot changes still in the review loop

Delete each section in that change's landing commit. Every open finding is
in a `findings-<change>-<name>-r<N>.md` file beside this one; if a fixer's
or reviewer's report never arrives, brief the next one from that file plus
the store note (`store/reviews`, by change id). Snapshot as of
2026-09-16T03:15Z; the agents named as RUNNING report into the stoker's
context as "Subagent hand-back" messages.

- Opponent-model design 36e2ae4be45b: on pokerbot main (659c6b7, stale
  round-4 pass; round-7 fixes at 72eff27, 5f7a1a8). Round 8 FAILED: two
  substantive (warm-up gate not enforced by §4.5; exploit flags have no
  path into play) and four wording, in `findings-36e2ae4be45b-design-r8.md`.
  Escalated to the operator 2026-09-16 with the cost and a recommendation.
  NO round 9 or fixer until the operator answers. If yes: fixer 8 from that
  file on a fresh branch from trunk, then round 9; wording-only → confirming
  round → `bin/dispatch.py land`.
- Engine survey 7f09949cb56f: round-2 fixer RUNNING (long; started before
  the context clear); findings in `findings-7f09949cb56f-engine-r2.md`.
  Then round 3.
- Exploitation survey 76bbf2823a53: round 6 FAILED on one price claim
  (converter caveat generalises PT4's price to three other vendors) plus
  three wording; `findings-76bbf2823a53-exploitation-r6.md`. Fixer 6 done
  at 72c60d2 (HM3 converter price fetched from the vendor page, four
  separately sourced figures, two log entries). Round 7 RUNNING at checkout
  41a874aea055. Wording-only → confirming round 8 → `bin/dispatch.py land`.
  Never run reconcile while its pass is recorded and it is unlanded.
- Bots survey 14d64950c0bc: LANDED and DONE. Wording fixer landed on
  pokerbot main at 3fbd279 (2026-09-16 23:15Z) after rounds 6 and 7 both
  came back wording-only; findings files deleted. Nothing left to do.
- Solvers survey 048795519f43: fixer 4 done at 474402d (preflop bullet
  moved to the open list; MonkerSolver scripting scoped; run-2 load note
  added; Deepsolver pricing from the live pages, half of F6 judged
  mistaken by the fixer). Round 5 RUNNING at checkout 85f4140c6fae.
- Evaluation strategy 45e49ce81e40: round 4 FAILED at fa819e5 (5
  substantive: the today's-engine grid unsized, the seat sweep misquoted and
  X6/X1 overstated, a stale 56,414 hands/s figure, the release gate
  unattributed, a false "not yet on main"; plus no number checker and six
  wording); `findings-45e49ce81e40-evaluation-r4.md`. Fixer 4 HELD behind
  the surveys (operator 2026-09-16). Then round 5.
- Table-size notes 984aa6810a05: round 4 FAILED (never engages
  REFERENCE_NOTES.md; "computed by script" with no script; R6/Q4 one commit
  stale; two wording); `findings-984aa6810a05-tablesize-r4.md`. Fixer 4
  RUNNING at checkout 8b0b4064141f, adding tools/check_table_size_numbers.py.
  Then round 5.
- After all four surveys pass: dispatch ONE worker to reconcile them into a
  plan with measured numbers and record the forefront-rule decision in
  pokerbot/CLAUDE.md. Known unknown for that brief: how the bot sees a real
  table and acts on it; no survey settled it.
