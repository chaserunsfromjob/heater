# bench blinds 0a62853153e4 — round 1 findings (fail; F1-F3 substantive, F4 evidence)

Delete this file in the landing commit. Branch worker/0a62853153e4, tip f484e44,
PR #23. Recorded in the store as round 1. Lens default. Lines at f484e44.

Verified and not to be re-checked: every caller of _game_string (table.py
_deck_names and Hand, personas.py:105) gets a byte-identical string over seats
2-9, four blind pairs and three stack forms; the benchmark's loaded game
differs from the old one only in blind (all seats) and firstPlayer (2 seats);
the test pins against the table's own string and fails on the old code; the
sys.path bootstrap is needed for the IS-MCTS child and works from the repo
root and from research/decision_layer/; raw-file heads and the provenance
sentence are accurate; gate exit 0, 343 passed 1 skipped.

- F1 (substantive) pokerbot/table.py:136 and :165. extra_params is appended
  after bettingAbstraction and universal_poker takes the LAST duplicate key,
  so game_string(cfg, extra_params={"firstPlayer": "2 1 1 1", "blind":
  "100 50"}) loads with blind='100 50', firstPlayer='2 1 1 1' and no error:
  the reversed game this change removes, through a public knob.
- F2 (substantive) pokerbot/equity_rule.py:74 with_odds(game_string, sims)
  is already the project's recorded way to add calcOddsNumSims to a table
  game string, and it raises if the key is already set; extra_params is a
  second unguarded route to the same parameter and settles nothing on
  record. Resolve F1 and F2 together by DROPPING extra_params: build the
  benchmark's string as with_odds(game_string(config,
  betting_abstraction=abstraction), odds_sims), keep the betting_abstraction
  keyword, and say in game_string's docstring that with_odds is how an
  engine parameter is added. Add a test that build_game(seats, "fullgame",
  200) still carries calcOddsNumSims=200 and the table's blind/firstPlayer.
- F3 (fact) DECISION_LAYER_SEARCH.md:151 the Conditions row still reads
  "blinds 100/50" as if ordinary notation. Say the recorded runs posted the
  blinds in engine-seat order 100 then 50, the reverse of the table, and
  point to the provenance row.
- F4 (evidence) DECISION_LAYER_SEARCH.md:753 and the three raw-file heads
  say the reversal "changes nothing about their timing and memory claims"
  with no number behind it. The reviewer measured on this branch,
  2026-09-17: 3 x 3000 random hands to terminal, median play-outs per second,
  old game vs new: 2 seats 50497 vs 50727 (ratio 1.005); 6 seats 26076 vs
  25952 (ratio 0.995). Put that measurement beside the claim in the
  provenance row (one sentence; the raw-file heads may point to it).

Every finding wording only: NO.

Round-1 cost: 19 tool calls, about 12 minutes, one venv build. No dollar
figure.
