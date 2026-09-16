# Evaluation strategy 45e49ce81e40 — round 3 findings (fail; 1-4 substantive)

Delete this file in the landing commit. Branch worker/45e49ce81e40, checkout
`.heater/worktrees/pokerbot/9fd7bd8ad257`, one file EVALUATION_STRATEGY.md
(+1678). Recovered from the round-3 reviewer's transcript (previous session)
on 2026-09-16; every arithmetic cell in §2.5 and §3.6 reproduced clean, the
anchor check found no broken anchors, 20 tests passed. The round-3 fixer was
dispatched with these. Lines in EVALUATION_STRATEGY.md at the branch tip
the reviewer saw; re-locate by content.

- 1 (substantive) :1409-1424 gates every requirement on "the 52-card
  conversion landing first". Trunk REFERENCE_NOTES.md now records, landed:
  the 20-card deck seats seven at most, the engine is fixed-limit with one
  fixed raise size, and the 52-card conversion is OUT (18.4 days, 146.5
  GiB). X1, X2, X6 are already answered NO, and seats 8 and 9 (0.30 of the
  headline and the operator's second priority) cannot run on anything on
  main. Resolve: reconcile with trunk REFERENCE_NOTES.md (read it on trunk;
  do not rebase the branch), state what can run today and what waits on an
  engine decision the reconciliation of the four surveys will make.
- 2 (substantive) :62-65 "Roughly 113,000 hands, about four hours" is the
  abolished four-seat grid (16 × 7,064 = 113,024, 3.92 h); §3.6 settles
  nightly acceptance at 141,280 hands / 4.906 h. Make the summary match.
- 3 (substantive) :1011-1015 the four-seat comparison uses .50/.30/.10/.10
  (Σw²=0.36, n_eff 39,244, Δ 30.0, "buys 1.9"), which the document's own
  banding cannot produce: dropping the rotating seat leaves 2,6,8,9 →
  .50/.15/.15/.20, Σw²=0.335, n_eff=42,173, Δ=28.97; the fifth seat buys
  0.9, not 1.9. The "3.9 h" in the same sentence is the 2,6,8,9 grid.
- 4 (substantive) :1365-1368 vs :733-737, :955-958, :1092-1094, :1448. §6
  adds "different bot SHA ⇒ NOT GATED, blocks release"; the four other
  statements of the rule omit it, which makes a new sha need four
  consecutive nightly runs before any release, an unrecorded four-night
  cadence against "hours, not days"; :826-827's example (night 1 of 4,
  4/5/7 "too long ago") is impossible under an unbroken 3→4→5→7 cycle.
  Pick one rule, state it identically everywhere, state the cadence.
- 5 (wording) :1615 "the eight simultaneous per-table-size tests"
  contradicts :783-789 (five tests, family size 20).
- 6 (wording) :825 labels the weights "(config, operator 2026-09-15)"
  though :740-743 and :1670 say they are the stoker's design choice.
- 7 (wording) :915-916 28,800 hands/h = 3,600 × 8 treats 8 workers as equal
  on a machine :911 records as 4 performance + 6 efficiency cores; near the
  3.92-worker breakeven (:927-929) state the homogeneity assumption under X8.
- 8 (wording) :529-531 vs :641-644 "personas/ must not import anything under
  the bot's decision path" contradicts personas making "the engine's own
  evaluator, the same call the bot makes"; §3.3 settles it, §3.1 is what a
  builder encodes. Also trunk CLAUDE.md now says "enumerating the 169
  preflop hand classes" is ours but "anything that ranks or values a hand"
  is the engine's; §3.3's Chen-formula scoring table at :619-620 is quoted
  against the superseded two-bullet rule and must be re-read against the
  current table.
