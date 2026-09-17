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

## Still open

- 45e49ce81e40 evaluation strategy (worker/45e49ce81e40 @ d865bb0):
  round 7 FAIL — the coverage passage over-reaches for the fifth round;
  fixer 7 RUNNING with orders to NARROW THE WORDS to what the checker pins
  (no more checker extension). Then round 8: wording-only → land (it is at
  seven rounds; the cap applies). Findings r3-r7 beside this file.
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
- 7f09949cb56f engine survey (worker/7f09949cb56f @ 6720c8a, pushed): text
  findings done; F1-F3 are MAC-ONLY re-measurements (see
  findings-7f09949cb56f-engine-r2-remaining.md). No round 3 until a Mac
  fixer closes them. Also owed there: criterion (e) for a public GPL-3.0
  repository, as the other surveys now have; and RESOURCES_SOLVERS.md
  :99-100 cites ENGINE_ALTERNATIVES.md:418-428 in origin's 52bd81d
  numbering — re-point at that landing.
- codex/tonight (Rohit): assessed, untouched, WAITS ON THE OPERATOR — see
  codex-tonight-assessment-2026-09-17.md. Do not merge.

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

## Operator questions outstanding

1. Did the operator authorise Rohit's rewrite of CLAUDE.md (forefront rule
   and laptop limit repealed)? heater's record says the carve-out is open.
2. May the PC open draft PRs / push branches as work starts (the rule
   both wrote; blocked by the permission classifier)?
3. The IRC Poker Database: copyright notice, no licence — usable as read
   data? (routed by the exploitation survey.)
4. fpdb-3's AGPL (routed by the exploitation survey).
5. Rohit's branch has no PR; the board only works if both sides use it.
