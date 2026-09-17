# bench blinds 0a62853153e4 — round 3 findings (fail; R3-F1, R3-F2 factual, R3-F3 test tie)

Delete this file in the landing commit. Branch worker/0a62853153e4, tip f229ed3,
PR #23. Recorded in the store as round 3. Lens default. Lines at f229ed3.

Resolved and not to be re-checked: everything from rounds 1 and 2, plus
R2-F1 (the smuggled value raises ValueError before interpolation; fchpa,
fcpa, fullgame are real engine menu names; no caller in the tree passes
anything outside them) and R2-F2 (memory figures re-measured: 22.1 MiB in
every case). Gate 354 passed 1 skipped, exit 0.

- R3-F1 (factual) DECISION_LAYER_SEARCH.md:151. The Conditions row's new
  clause "(firstPlayer 2 1 1 1, against the table's 1 2 2 2, so the big
  blind acts first before the flop and last afterwards)" is the inverse of
  what the engine does. Measured on the old string (blind=100 50,
  firstPlayer=2 1 1 1): Spent [P0: 100 P1: 50], so the big blind is engine
  seat 0; first to act preflop is player 1 (the small blind), first on the
  flop is player 0 (the big blind). Resolve: keep the firstPlayer numbers
  and replace the "so ..." clause with: the small blind (engine seat 1)
  acts first before the flop and the big blind first afterwards, which is
  the table's own order by blind role with the two seats' labels exchanged.
- R3-F2 (factual) research/decision_layer/raw/bench_fullgame.txt:2-5 and
  raw/bench_table_budget_10s.txt:2-5 say the runs had "the heads-up acting
  order reversed", but neither file has a two-seat run (both are seats 3
  and 6 only), and at three or more seats the old benchmark's firstPlayer
  "3 1 1 1" equals the table's. bench_fcpa.txt has seats 2, 3, 6 and its
  header is right. Resolve: in those two files say only that the blinds
  were posted in reverse seat order and that the acting order at three and
  six seats already matched the table's; scope the clause at
  DECISION_LAYER_SEARCH.md:753 the same way (line 151 already says "in the
  two-seat runs").
- R3-F3 (test tie) tests/test_bench_matches_the_table.py:36-39 and :127.
  ENGINE_BET_MENUS is called "The engine's own bet menus" but the engine
  also accepts fc (universal_poker.cc:1279-1285); the tuple is the menus
  this adapter allows. And test_every_accepted_bet_menu_keeps_the_table_s_
  blinds_and_order parametrises over that local tuple with nothing
  asserting it equals pokerbot.table.BETTING_ABSTRACTIONS. Resolve: assert
  set(BETTING_ABSTRACTIONS) == set(ENGINE_BET_MENUS) in a test so divergence
  fails loudly, and reword the comment to say these are the menus this
  adapter allows, a subset of the engine's four.

Every finding wording only: NO. No recorded figure changes.

Round-3 cost: 14 tool calls, about 12 minutes, one venv build, two gate
runs, four short measurement runs. No dollar figure.
