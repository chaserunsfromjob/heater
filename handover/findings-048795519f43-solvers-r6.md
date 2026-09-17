# Solvers survey 048795519f43 — round 6 findings (fail; F1 fail-class, F2-F4 substantive)

Delete this file, and `findings-048795519f43-solvers-r{3,4,5}.md`, in the
landing commit. Branch worker/048795519f43, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\solvers` on the PC, tip 72d5b7f
as reviewed. Recorded in the store as round 6 (3c1f0a7d9e2b). Lens default.
Lines in RESOURCES_SOLVERS.md at 72d5b7f; re-locate by content. All fetches
2026-09-17 00:07-00:14Z with a desktop browser user-agent.

Sound and not to be re-checked: every round-5 fix (F1-F7) verified against
the live source — monkerguy.com hold'em ladder $69-$319 at all six sites,
$499 is PLO only; GTOpen docs/player_types.md head-note (branch `master`,
not `main`) quoted exact at :416-420 with the read date, and its numbers
(+40-80 bb/100 line 117; Nit row 0|126|194|187|270|287|461 line 130; §4.1
at lines 107-149); the 0.706 s timer copied (typo "precent" and all) into
research/solvers/texassolver_turn_run_note.txt:26-27, committed; the stale
play-out counts gone from :1093-1100; F5-F7 wording as asked. Eleven fresh
citations exact: OMPEval Constants.h:6 `MAX_PLAYERS = 6` and
EquityCalculator.cpp:17; Simple Preflop Holdem $250 / 1-year / 2-10 players;
preflopranges.app, pokercoaching.com, gtosims.com Part 4 rows; the PioSOLVER
UPI docs page exists; CLAUDE.md:13-15, :17, :24, :26 resolve against TRUNK
(the branch's own CLAUDE.md is the old 27-line copy — do not "fix" the line
numbers against it). Summary, shortlist, Part 4, Appendix A and the entries
agree on every cross-checked number. Suite: 20 passed. treys and phevaluator
benches re-run on the PC: 80,087/s and 782,785/s — outside the Mac ranges as
expected on other hardware; the ratio 9.8x is inside the stated 5-15x. No
design decision settled (:1015 heading; five open items hand it to the
reconciliation); every branch file is an addition.

- F1 (substantive, fail-class) :785, :789, :791, entry 19 "PioSOLVER,
  GTO+, Jesolver". The two cited site roots carry no prices. Live:
  piosolver.com/products — "PioSOLVER 3.0 Pro … € 450.00 (+applicable
  taxes)", "PioSOLVER 3.0 Edge … € 800.00 (+applicable taxes)", each with
  "1 year of software updates", usable on two computers (document says "Pro
  $249, Edge $475 one-time": wrong currency, about half the price).
  gtoplus.com/purchase — "Main License: $75  Second License: $40 … Upgrade
  from CREV: $50", "The registration fee is one-time. All future updates
  are included." ($375 appears nowhere). jesolver.com/ and /index.html
  return a one-byte page; /cmdref.html is a command list with no price; no
  live source for "$200". Resolve: cite the two product pages with the read
  date and state what they say (PioSOLVER 3.0 Pro €450 and Edge €800 plus
  applicable taxes, two computers, one year of updates; GTO+ $75 main
  licence, $40 second licence, $50 upgrade from CREV, one-time with all
  future updates); mark Jesolver's $200 UNVERIFIED in the words entry 17
  uses for GTO Wizard's tiers, or cite a page that shows it. Say explicitly
  that entry 19's verdict does not move (the free TexasSolver and
  postflop-solver give the same capability natively on macOS). The "Not
  recommended" line at :1001-1003 needs no change.
- F2 (substantive, minor) :92-96. The round-5 F7 sentence says the engine
  survey's play-out counts "count whole hands played out to the end";
  ENGINE_ALTERNATIVES.md:418-427 on origin/worker/7f09949cb56f says the
  opposite — its play-outs start from a hand already dealt and part-played,
  and the "cheaper because already dealt" explanation is withdrawn.
  Resolve: at :94 say "those count the rest of an already part-played hand
  being played out to the end inside a quarter-second of thinking". One
  clause; no number changes.
- F3 (substantive, minor) :908, Part 4 Preflop Wizard row, Format "web page
  / printable PDF". preflopwizard.app/blog/9-max-preflop-chart has no PDF
  and no download except its phone apps, and argues against printing
  charts. Resolve: "web page only (the ranges are tables inside the
  article); no download and no PDF", read date beside it. Coverage cell's
  "updated Jul 2026" is correct; keep.
- F4 (substantive, filed 2026-09-17 from change 114e5b3f5b1b) the rating
  criterion (e) and every (e) reason still assume a private,
  never-distributed project. The repository is PUBLIC and licensed GPL-3.0
  (LICENSE at root on worker/114e5b3f5b1b; CLAUDE.md Licence section
  rewritten there). Resolve: restate criterion (e) — GPL-compatible code is
  acceptable because the project is itself GPL-3.0 and publishes its
  source; paid tools acceptable for the operator's own use; AGPL and
  GPL-incompatible licences are the ones to watch — then re-read every (e)
  and change a verdict only where the new premise changes it, else the
  reason in as few words as possible; list each in the report.
- W1 (wording) :3 "Research date: 15 September 2026" while :416 and :911
  carry 2026-09-16 and about eight sites say only "today" (:186, :305,
  :663, :704, :725-728, :810, :852-854, :904). Resolve: header "researched
  15 September 2026, revised through <date>"; replace each bare "today"
  with the date read.
- W2 (wording) :911 quoted MonkerGuy product names carry commas the page
  lacks: page reads "6-MAX 100BB 2.5x Open" and "9 PLAYERS NLH 100bb - 2.5x
  Open". Drop the commas or the quotation marks.
- W3 (wording) :68, :938, :1032, :1145 "5.5 to 8 s wall" as a flat range;
  texassolver_turn_run_note.txt:18 has the 8 s only as "about 8 s … load
  not recorded", and :207-209 already says so. Resolve: "5.5 s measured;
  the earlier run's wall clock was noted only as about 8 s", or at least
  "about" before the 8 at all four sites.

Every finding wording only: NO.

Round-6 cost: 33 tool calls, about 20 minutes, 19 fetches, three pip
installs, two benches; no dollar figure. Six rounds on this change so far.
