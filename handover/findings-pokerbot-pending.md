# pokerbot changes: the next action for every change

Snapshot 2026-09-17 about 02:50Z, written on the PC session. Delete each
section in that change's landing commit. Every open finding is in a
`findings-<change>-<name>-r<N>.md` file beside this one; every round is in
`store/reviews/`. pokerbot main is at b5924bf on GitHub; heater main is
pushed. Operator's cap in force: a change at eight or more rounds lands on
the next wording-only round, and a single-token substantive finding at
that stage is applied by the session and landed.

## LANDED on main today (nothing left to do)

- 76bbf2823a53 exploitation survey — 03622d6 (rounds 8-9 wording-only).
- 114e5b3f5b1b public repository, GPL-3.0 LICENSE, GitHub rules, OpenSpiel
  decision recorded in CLAUDE.md; RESOURCES_BOTS (e) and REFERENCE_NOTES
  corrected — e67825b (round 5 empty).
- 048795519f43 solvers survey — 0565d1a (rounds 8-9 wording-only), plus
  f8dc012 correcting its "licence not yet landed" note.
- 36e2ae4be45b opponent-model design rounds 8-11 — 5653c6b (warm-up gates
  the load rule; flags report-only until Tier 2; 684 figures pinned; the
  checker encoding-safe).
- 8a80689e7354 exploitation touch-up — 351abbb (rounds 3-4 wording-only;
  the IRC corpus's copyright question routed to the operator).
- 984aa6810a05 table-size notes — b5924bf (round 9's single stale commit
  id applied and landed under the cap; 233 figures pinned).
- 45e49ce81e40 evaluation strategy — 5f13aa8 (round 8's single wrong clause
  applied and landed under the cap; 234 checks pinned; three wording
  observations recorded in the fix commit, not applied).

## LANDED 2026-09-17 (Mac session, under the pace decision)

- 972241b6f99a forefront rule rewritten in the operator's words — 2d411f3
  (two rounds; the leftover stale references are the sweep task 90c430775d15).
- bc7299f59f85 LLM_POKER_FAILURE_MODES.md — f959aad (one round, three
  one-sentence fixes applied by the session).

- 5a58d580c339 ACTION_TRANSLATION.md — 8bd3490 (one round, five edits
  applied by the session; recommendation: fchpa menu with randomised
  pseudo-harmonic mapping in pot fractions).

- 7f09949cb56f ENGINE_ALTERNATIVES.md engine survey — 3e02af3 (three rounds;
  round 3's rewrite of the forefront passages landed on the fixer's report).
- 3b2131f2f81c stale forefront-reference sweep — 1b83bf7 (automated checks).

## Still open

- 7eead182560d RESOURCES_DICKREUTER.md (worker/7eead182560d @ b0c5b4a):
  round 1 FAIL on six substantive (nine seats ARE offered; not on the
  solvers' scale; the equity gap has a second cause in the opponent-deal
  loop; game_logger.py uploads every hand with the computer name to the
  author's server; the forefront reading presented as settled; four counts
  off) — the recommendation itself (capture layer + architecture, OpenSpiel
  decides; not its brain) judged right. Fixer 1 RUNNING (merges main
  first). Then round 2. When it lands: record the one clause in CLAUDE.md
  the operator delegated ("add that in if you think its good") —
  dickreuter's architecture as the template and its capture layer as the
  eyes; OpenSpiel makes the decisions — as a separate small change.
- codex/tonight (Rohit): reviewed against the new rule 2026-09-17; 24 required
  changes in codex-tonight-required-changes-2026-09-17.md and GitHub issue #4.
  His move. Do not merge.

## After the surveys: the reconciliation (not yet dispatched)

ONE worker reads the four surveys (bots, exploitation, solvers, engine —
the engine survey still on its branch), the dickreuter assessment, the
table-size notes and the design, and puts the open decisions to the
operator as plain choices: (1) the forefront carve-out — who chooses the
action on top of OpenSpiel; (2) the opponent baseline — the 2009 archive
vs observe-first; (3) what "based on dickreuter" means (the assessment's
recommendation); (4) the licence questions routed to them — fpdb-3's AGPL
and the IRC corpus's copyright notice; (5) whether unlicensed code scores
1 of 3 (solvers) or ~ (bots). Known unknown for that brief: how the bot
sees a real table and acts on it — the dickreuter assessment now answers
the "sees" half. Also for the reconciler: the three number checkers
(design, table-size, evaluation) share scaffolding and are filed for
consolidation (queue 78dfd89d332f).

## Operator answers 2026-09-17 (Mac session; verbatim in the task at score 80)

1. Rohit's CLAUDE.md rewrite: NOT authorised as written, but the substance is
   now decided: AI may WRITE decision code; no model call in the live
   decision path; decision code is ordinary testable code. Rewrite the rule
   in the operator's words, then review codex/tonight against it; he opens a
   PR.
2. PC may push branches without prompting.
3-4. Licences: "just use the code"; repository may go private later.
5. "Hours on one laptop" is KEPT (compute budget, not usage; the operator
   had read it as usage).
6. A research note on LLM poker failure modes is owed; its named mistakes
   stay out of the decision code.
