# pokerbot changes still in the review loop

pokerbot now HAS a private remote (created 2026-09-16 at the operator's
request): https://github.com/chaserunsfromjob/pokerbot, origin, all seven
branches pushed. Every brief from now on tells workers to push their branch;
landing pushes main. The HANDOVER trap saying "pokerbot has no remote" is
stale.

Delete each section in that change's landing commit. Every open finding is
in a `findings-<change>-<name>-r<N>.md` file beside this one; if a fixer's
or reviewer's report never arrives, brief the next one from that file plus
the store note (`store/reviews`, by change id). Snapshot as of
2026-09-16T03:40Z. THE OPERATOR STOPPED ALL AGENTS at 03:38Z and asked for a
debrief (handover/debrief-2026-09-16.md). Nothing is running. Every RUNNING
below is now STOPPED: the exploitation round-8 reviewer and solvers round-6
reviewer had barely started (re-dispatch fresh); the engine round-2 fixer was
waiting on a paired play session and its edits were autosaved at 52bd81d on
worker/7f09949cb56f (resume from disk).

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
- Exploitation survey 76bbf2823a53: fixer 7 done at fdd263c (DriveHUD
  standalone converter tiers with two page contradictions flagged; Hand2Note
  emulator-on-Windows caveat and (d) split; W1-W3). Review round 8 RUNNING at
  checkout 41a874aea055. Wording-only → confirming round 9 →
  `bin/dispatch.py land`; the stoker has proposed to the operator (2026-09-16)
  capping each survey at one more fix and one more check, remaining nits
  recorded in the document as known gaps. Never run reconcile while its pass
  is recorded and it is unlanded. Seven rounds so far.
- Bots survey 14d64950c0bc: LANDED and DONE. Wording fixer landed on
  pokerbot main at 3fbd279 (2026-09-16 23:15Z) after rounds 6 and 7 both
  came back wording-only; findings files deleted. Nothing left to do.
- Solvers survey 048795519f43: fixer 5 done at 72d5b7f (MonkerGuy hold'em
  ladder $69-$319 at six sites; engine-survey play-out counts dropped;
  GTOpen head-note quoted; 0.706 s timer copied into the turn run note;
  F5-F7). Review round 6 RUNNING at checkout 85f4140c6fae. Wording-only →
  confirming round 7 → `bin/dispatch.py land`, subject to the cap proposed
  to the operator. Five rounds so far.
- Evaluation strategy 45e49ce81e40: round 4 FAILED at fa819e5 (5
  substantive: the today's-engine grid unsized, the seat sweep misquoted and
  X6/X1 overstated, a stale 56,414 hands/s figure, the release gate
  unattributed, a false "not yet on main"; plus no number checker and six
  wording); `findings-45e49ce81e40-evaluation-r4.md`. Fixer 4 HELD behind
  the surveys (operator 2026-09-16). Then round 5.
- Table-size notes 984aa6810a05: fixer 4 done at c859c66 (new §1.0 states
  the vendored engine's answers from REFERENCE_NOTES.md and splits R1-R14
  into reachable-now and waits-on-engine; tools/check_table_size_numbers.py
  pins 232 figures with 13 tests, 33 tests total; R6 gains a sentence on
  72eff27; F4, F5 applied; Q4 now states 24 runs on the vendored engine).
  Review round 5 HELD behind the surveys (operator 2026-09-16); brief it
  from `findings-984aa6810a05-tablesize-r4.md` plus this note. Checker
  consolidation was filed, promoted at 30 and fell past the list cap; it is
  gone by rule, not parked.
- After all four surveys pass: dispatch ONE worker to reconcile them into a
  plan with measured numbers and record the forefront-rule decision in
  pokerbot/CLAUDE.md. Known unknown for that brief: how the bot sees a real
  table and acts on it; no survey settled it.
