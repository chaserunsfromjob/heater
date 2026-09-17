# bench blinds 0a62853153e4 — round 2 findings (fail; R2-F1 substantive, R2-F2 evidence, R2-F3 wording)

Delete this file in the landing commit. Branch worker/0a62853153e4, tip 0f6bf4a,
PR #23. Recorded in the store as round 2. Lens default. Lines at 0f6bf4a.

Resolved and not to be re-checked: round 1's F1-F4 (extra_params gone from the
whole tree; the benchmark builds with_odds(game_string(config,
betting_abstraction=abstraction), odds_sims); with_odds raises on a second
calcOddsNumSims; the Conditions row and the provenance row are accurate;
the IS-MCTS child runs from the repository root; gate 346 passed 1 skipped).

- R2-F1 (substantive) pokerbot/table.py:175 interpolates betting_abstraction
  into the game definition unchecked, and universal_poker takes the last of
  a duplicated key, so
  game_string(TableConfig(seats=2, stacks=(20000,20000)),
              betting_abstraction="fcpa,blind=100 50,firstPlayer=2 1 1 1")
  loads with blind='100 50', firstPlayer='2 1 1 1' and no error: the
  reversed game, through the one surviving knob. The docstring at :151-157
  ("There is deliberately no knob ...") and the test
  tests/test_bench_matches_the_table.py:75-94
  (test_game_string_has_no_knob_that_can_overwrite_the_table) both claim
  this route does not exist; the test is a signature check and passes
  regardless. Resolve: validate the value in game_string before
  interpolation with an allow-list of the engine's menu names (fchpa,
  fcpa, fullgame; keep BETTING_ABSTRACTION in it), raising ValueError
  otherwise; add a behavioral test that the injected value above raises
  and that every accepted value leaves blind and firstPlayer equal to the
  table's; reword the docstring and the test's assertion message so they
  claim only what the code enforces. Keep the signature test if you like,
  but it is not the proof.
- R2-F2 (evidence) DECISION_LAYER_SEARCH.md:753 "changes nothing about
  their timing and memory claims" now has a throughput number beside it
  and no memory number. The reviewer measured on this branch, 2026-09-17:
  two clean child processes per case, 3000 random hands to terminal, peak
  resident set size old game vs new: 2 seats 22.2 MiB vs 22.1 MiB, 6 seats
  22.1 MiB vs 22.1 MiB. Resolve: add those figures to the same sentence.
- R2-F3 (wording) DECISION_LAYER_SEARCH.md:151 names only the blind
  reversal; the two-seat rows were also run with the heads-up acting order
  reversed (firstPlayer 2 1 1 1 against the table's 1 2 2 2). Name it in
  the row so it is self-contained.

Every finding wording only: NO.

Round-2 cost: 17 tool calls, about 14 minutes, one venv build, one short
benchmark run. No dollar figure.
