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

- f541eb44075b DECISION_LAYER_SEARCH.md — e744a9d (one round; fixer's rewrite
  against the new rule landed on its report). Recommends one depth-limited
  search with biased continuation strategies; OpenSpiel's IS-MCTS segfaults
  above two players (universal_poker.cc:1111 at v2.0.2).

- 6c3c2652b22d OPPONENT_BASELINE.md — ac34ffc (one round; five wording edits
  applied by the session). Answer: observe first; keep design §4.3 and s = 50;
  an archive-seeded prior is worth 22-31 hands; crossover about 30 observed
  hands; Table C's fold-to-c-bet opportunity rate is 0.030 not 0.15.

- c91832fe9882 BUILD_PLAN.md, the reconciliation — 96aa546 (one round, seven
  exact edits by a fixer). D1 arena/rules fix and D2 seeing the table are the
  operator's; T1 dispatched.

- baed4c5203a7 DECISION_LAYER_BLUEPRINT.md — b00802d (one round, eight
  exact edits by a fixer; the unreproducible six-handed tree figures
  withdrawn). Research is closed: every planned document is on main.
- 8cf14f9f446f OVERNIGHT.md — 568d029; also GitHub issue #13, the link for
  Rohit's assistant tonight.
- 3b3236e88284 bin/gate.sh + requirements-research.txt — a209ff1 (session's
  own read; proved passing and failing). The land gate for pokerbot is now
  `bash bin/gate.sh`.
- 70884871cf3e T1 the table (OpenSpiel adapter 2-9 seats, invariants I1-I7,
  determinism) — 7b1545c, PR #11 (two rounds: pass-with-seven, then a
  confirming pass with one wording fix). 143 tests; I3 at 2 seats NOT RUN
  by design.

## Building (dispatched 2026-09-17 ~05:05Z, cut from 7b1545c)

- 8edc0ce3e009 T2 the first bot (depth-limited search + equity rule as a
  logged check + three trivial opponents + arena runner), branch
  worker/8edc0ce3e009. Code: one fresh reviewer round, fixer, confirming
  round, land through `bash bin/gate.sh`.
- 1fd3a6ebe936 T3 the scoreboard (personas, split, paired deals, bootstrap,
  section 3.5 rule), branch worker/1fd3a6ebe936. Same landing path. T2's
  baselines and T3's calibration agents may overlap: reconcile at landing.

## Still open

- codex/tonight (Rohit): reviewed against the new rule 2026-09-17; 24 required
  changes in codex-tonight-required-changes-2026-09-17.md and GitHub issue #4.
  His move. Do not merge.

## After the surveys

The reconciliation is BUILD_PLAN.md on main. Build from its stages; T1 first.
