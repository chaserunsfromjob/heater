# Solvers survey 048795519f43 — round 7 findings (fail; F1-F2 substantive, small)

Delete this file, and `findings-048795519f43-solvers-r{3,4,5,6}.md`, in the
landing commit. Branch worker/048795519f43, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\solvers` on the PC, tip b063a2b
as reviewed. Recorded in the store as round 7 (d1f7a3e5b208). Lens default.
Lines in RESOURCES_SOLVERS.md at b063a2b. All fetches 2026-09-17
00:30-00:39Z, 23 of them, all HTTP 200.

Sound and not to be re-checked: rounds 5 and 6's lists; the three F1
prices re-fetched and exact (PioSOLVER €450/€800 "+applicable taxes", two
computers, one year of updates; GTO+ $75/$40/$50 one-time, no $375 on the
page; jesolver.com root and index one byte, cmdref no price — UNVERIFIED
right); entry 19's verdict unchanged and says so (:828-832); Preflop Wizard
row exact (no PDF; iOS/Android only; argues against printing; "Updated July
2026"); criterion (e) restated at :169-177 matches worker/114e5b3f5b1b's
CLAUDE.md:59-64 on every point; the four moved ratings right (three
AGPL-3.0 3→2, GTOpen no-licence 2→1) and the twenty-one left right, 25 = all;
AGPL treatment now consistent with RESOURCES_BOTS.md (~ / 2 of 3); Appendix
B's new block accurate; W2 and W3 of round 6 fully applied; twelve fresh
GitHub citations exact (TexasSolver, postflop-solver last commit 2023-10-01,
desktop-postflop 349, OMPEval last commit 2016-08-21, slumbot2019, treys,
pokerstove, amaster97, ArtemIyX, masterai NOASSERTION, DecisionHoldem,
phevaluator); every CLAUDE.md line citation resolves against trunk; no
design decision settled (Part 5 slots 1-2, five open items :1069-1157,
withdrawn nominations); twelve files all additions; suite 20 passed.

NOTE FOR THE LANDING (not a finding): worker/114e5b3f5b1b inserts an intro
paragraph into CLAUDE.md and renumbers it — :13-15 → :15-17, :17 → :19,
:24 → :22, :26 → :24. Re-point this document's (and the engine survey's)
CLAUDE.md citations in the commit that lands after the licence change.
ALSO: the solvers survey now scores unlicensed code 1 of 3 while
RESOURCES_BOTS.md scores it ~ (middle); queue finding 4799555bda86 covers
the bots survey's internal tension; the cross-document disagreement is
new and is for the reconciliation.

- F1 (substantive) :96-101. The round-6 F2 clause is wrong the other way:
  ENGINE_ALTERNATIVES.md (6720c8a and 52bd81d, :402-429 byte-identical)
  carries TWO play-out counts and distinguishes them at :419-421 — the
  engine table's last column "Play-outs in a 250 ms decision" counts
  COMPLETE hands dealt from scratch (~11,900 per quarter-second for
  OpenSpiel menu mode), while :198-199 "Play-outs per decision, fcpa:
  7,370 - 12,373 - 13,285" are the chooser's part-played play-outs. The
  document's sentence is true of :198 and false of the table. Resolve: name
  both — "ENGINE_ALTERNATIVES.md reports two counts and distinguishes them
  at its own :419-429: the engine table's last column, complete hands
  dealt from scratch, and the chooser's play-outs per 250 ms decision,
  which continue a hand already part-played. Neither is this file's
  ten-thousand figure: both play a hand out to a showdown inside a game
  engine, where these count deals of the remaining cards to settle one
  hand's equity in a Python loop." Conclusion unchanged; no number moves.
- F2 (substantive) :169-177, :39-40, :1161-1162. Criterion (e) states the
  bot is "itself licensed GPL-3.0" as present fact. Live:
  api.github.com/repos/chaserunsfromjob/pokerbot (00:37Z) private:false,
  license:null; origin/main has no LICENSE and no Licence section; both
  live only on worker/114e5b3f5b1b, local, unpushed, round 2 failed today.
  Resolve: one parenthesis at the criterion and at the AGPL glossary
  entry — "(the repository is already public; the GPL-3.0 licence is change
  114e5b3f5b1b, not yet landed: as of 2026-09-17 LICENSE is not on main and
  GitHub reports no licence)". No rating moves.
- W1 (wording) :3-6 and seven measurement sites (:77, :229, :344, :379,
  :401, :1242, Appendix B :1317). The header is now a date range, so :6
  "run on this machine today" anchors to nothing, and Appendix B :1331-1333
  says the 17 September work was PC page reads, not Mac measurements.
  Resolve: :6 "was run on this machine on 15 September 2026"; the seven
  sites then resolve unchanged. (Of the fifteen remaining "today"s: ~7 Mac
  measurements, 5 present-tense prose fine as is (:116, :971, :1036, :1110,
  :1153), one inside a quotation (:724), two page reads — W2.)
- W2 (wording) :108 "GTOpen (Rust, active this week, no licence file)" and
  :368 "pushed 15 Sep 2026 (today)" are page reads left undated; GTOpen's
  pushed_at is now 2026-09-17T00:25:43Z. Resolve: "(read 2026-09-15)" at
  both; date rather than "this week" at :108. (Created 13 Jun 2026, 14
  stars, no licence — all confirmed.)
- W3 (wording) :816-818 GTO+ quotation stops before the page's "Taxes may
  still be added depending on your location." while PioSOLVER's carries
  "(+applicable taxes)". Add the sentence or "taxes may be added".
- W4 (wording) :443 vs :860-863 GTOpen "no licence" scores 1, Holdem Solver
  "licence unstated" scores 2, difference unstated. Resolve: entry 20's (e)
  reason "(free now, terms unknown; a closed tool we run, not code we
  copy)".
- W5 (wording) :1165-1168 "the AGPL network clause would then ride along
  with that part, and this repository is public" — publicity is not the
  trigger; the glossary :37-42 has it right (offered to others over a
  network). Drop the four words or "and it would bite if the bot were ever
  offered to others over a network".

Every finding wording only: NO (F1, F2; both local, no number, rating or
recommendation moves).

Round-7 cost: 27 tool calls, about 12 minutes, 23 fetches; no dollar
figure. Seven rounds on this change so far.
