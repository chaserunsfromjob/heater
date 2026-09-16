# Engine survey 7f09949cb56f — round 2 findings (fail, 4 substantive)

Delete this file in the landing commit. Branch worker/7f09949cb56f, checkout
`.heater/worktrees/pokerbot/92e2a2c459ef`. Round-2 fixer was stopped at the
usage limit; its half-written paired measurement runner is autosaved at 59022d1.
The MEASUREMENT RULE: check `uptime` first; if 1-min load > 4.0 wait (up to 30
min); record the load beside every figure; run chooser fcpa, chooser fullgame,
bench_speed, resample_opponents interleaved in one session, 3+ repeats.

Paths in ENGINE_ALTERNATIVES.md unless stated.

- F1 (decisive) :496-511 PyPokerEngine "cannot be used for decision-time
  search at all … no per-seat stacks" is FALSE: pypokerengine.api.emulator.Emulator
  takes per-seat stacks, generate_possible_actions answers a position, deepcopy +
  run_until_round_finish gave 659 play-outs in 5.0 s (132/s). Commit a script,
  reject it on measured speed and no solver, fill its speed cells at :564.
- F2 :123-124, :135-146, :292-297, :403-405, :652-657. Chooser play-outs per
  250 ms: file 13,131 fcpa / 242 fullgame; reviewer 4,992-5,600 / 74.
  resample_opponents: file 71,344 and 91,078/s; reviewer 34,385-47,042.
  bench_speed and headtohead reproduced. The 4.1x "mid-hand cheaper" explanation
  (:292-297) was 1.2x when measured back to back. Re-run interleaved, quote
  ranges, re-derive standard errors at :138-145 and :428, re-state or drop :292-297.
- F3 :209-229, :637-648. "still-new per round" depends on round count; at
  matched rounds pre-flop-only is above the 20-card row. bench_cfr.py:70-71 has
  marks every 100 rounds: report at a matched round count; rewrite :226-229,
  :641-646. Headline (no convergence in budget) stands.
- F4 :326-334 second reference engine adopted by assertion; condition on the
  reconciliation, name the CLAUDE.md bullet beside treys.
- F5 :100-101 "do not spend another hour adapting poker_ai" reverses
  CLAUDE.md's basis and stage 1 without flagging; say the edit is made at the
  reconciliation.
- F6 :14-18, :589 "Re-measured … 18 days": it is an extrapolated floor
  (REFERENCE_NOTES.md:399-430); drop "Re-measured".
- F7 :330-331 "only one still actively released" false: pokerkit 0.7.5
  2026-08-22, open_spiel 2.0.2 2026-08-12.
- F8 :491-494, :565 RLCard game imports on 3.13 but rlcard.agents/models fail
  (distutils); qualify both cells.
- F9 :151-193, :774-779 opponents draw from the same menu the chooser assumes:
  best case; one sentence beside the result and in "could not settle".
- F10 :126, :140, :143, :155, :171-172, :380, :428 plain words before
  "standard error", "confidence interval", "standard deviation", "half-width";
  expand ISMCTS.
- F11 :96-98, :190-192 add "on a four-move menu; acting with real sizing
  needs a translation nobody has built".
- F12 :53-55 "every measured number has a committed script" overstated for the
  candidate sections; commit bench_requirements.py or narrow the sentence.

Extra for the next fixer or reviewer (filed by the bots fixer, dismissed into
this loop): ENGINE_ALTERNATIVES.md:87 cites the forefront rule as
"CLAUDE.md:13-15"; cite it by section, since trunk's line numbers moved.
