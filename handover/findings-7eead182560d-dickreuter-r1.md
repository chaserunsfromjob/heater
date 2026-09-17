# dickreuter assessment 7eead182560d — round 1 findings (fail; F1-F6 substantive)

Delete this file in the landing commit. Branch worker/7eead182560d, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\dickreuter` on the PC, tip b0c5b4a
as reviewed, cut from local main 03622d6 (main is now f8dc012; the checkout's
CLAUDE.md is the OLD one — the document's CLAUDE.md quotations are verbatim
against main; the fixer merges main in first). Recorded in the store as
round 1 (a2c4e6f8b1d5). Lens default. Lines at b0c5b4a. The worker's clone
and install areas: `…\scratchpad\dickreuter\` (reuse; do not re-clone).

Sound and not to be re-checked: the no-opponent-modelling finding
(table_screen_based.py:258-278 commented out; decisionmaker.py:247-268 calls
get_flop_frequency_of_player, defined nowhere, inside a bare except;
t.PlayerNames assigned nowhere; no vpip/pfr/aggression/fold_rate anywhere);
the server dependency exactly as described (config.ini db, login guest;
six modules; pymongo unused; no template shipped; strategy_handler
:118-139 unguarded second request; endpoints 200 as guest 01:28Z); vboxapi
GPL-2-only or CDDL, 4,539 lines, imported nowhere; screen_operations.py:16
imports vbox_manager which imports virtualbox; every architecture line
number (main.py 28-step chain; the Decision methods; curvefitting;
genetic_algorithm 8 checks, maxChanges 2; five-entry bet menu; card CNN;
169 preflop entries; total_players - 2 clamp); README quotations verbatim
(:61, :291, :297); Dockerfile/README name a missing requirements.txt; the
unused-dependency list; all GitHub facts (2,463/589/147/34; five Jan-2024
releases; #228, #241) and OpenSpiel facts (kMaxUniversalPokerPlayers = 10
at :52; the BettingAbstraction enum :62; the settings block :152-213);
capture tests 24 passed live; full suite 3 failed / 28 passed / 14 skipped;
the four meanings distinct and the ranking follows the evidence; nothing
settled, no carve-out granted; the UNVERIFIED list honest; suite 25.

- F1 (substantive) :363-367 and :630-634 "never 9" seats — false:
  poker/gui/ui/table_setup_form.ui's max_players QComboBox offers 6, 2, 3,
  4, 5, 7, 8, 9, written straight to max_players
  (table_setup_actions_and_signals.py:211-219; table_scraper.py:19).
  Resolve: say the setup window offers 2 to 9; re-argue criterion (a) on
  the limits that are true — README :291 "only works for tables with 6
  players", no published nine-seat template, the total_players - 2 clamp.
- F2 (substantive) :97-113, :656-659 "same scale as RESOURCES_SOLVERS.md":
  (1) :108-110's caveat that the solvers' (e) predates the public/GPL
  decision is stale — main's RESOURCES_SOLVERS.md:171-180 already reads
  "fits a public GPL-3.0 project"; delete. (2) :657 quotes GTOpen as (e) 3;
  RESOURCES_SOLVERS.md:446-448 gives (e) 1. (3) criterion (b) is redefined
  — solvers: "arbitrary bet sizes, not fixed-limit" (a sizing menu scores 3
  there, :528); this file: "not a fixed menu" and scores five sizes 1.
  Resolve: restore the solvers wording and re-score, or say plainly (b) is
  redefined and the columns are not comparable. (d) is reworded too but
  argued; say so.
- F3 (substantive) :80-84, :259-266, :731-743, :887-892. The tie-counting
  diagnosis is right (eval_best_hand stable sort; winner < CollusionPlayers
  + 1). But pooled over 800,000 deals dickreuter gives 0.6825 +/- 0.0005,
  ABOVE both references (treys 400k: 0.6797 splits-whole, 0.6714 halved);
  ":263-264 matches the second" does not hold. Second cause missed:
  montecarlo_python.py:210-222 pops deck[random_card1] then
  deck.pop(random_card2) on the shortened deck, so the card originally at
  random_card1 + 1 (same rank, next suit, given create_card_deck's order)
  is never dealt as the second card — fewer opponent pocket pairs — and
  the range filter checks deck[random_card2] but a different card is
  dealt. Resolve: quote the pooled measurement above both references; add
  the dealing defect; re-word :743 and :887-892 — the evaluator swap is one
  of at least two fixes, not the whole job.
- F4 (substantive) :695 (the §5 allowed-column table) and :315-322 (§1.6).
  poker/tools/game_logger.py keeps no local record: every method is an
  HTTP POST to the config.ini db (lines 34, 69, 121, 125, 138, 144, 161,
  171, 178, 185, 192, 198, 205); write_log_file :40-69 posts the strategy
  settings, the table reading, the history and the decision, stamped with
  os.environ["COMPUTERNAME"] (:57), to insert_round on dickreuter.com:7778.
  Resolve: add the upload direction to §1.6 with the one-line note that
  hands are uploaded with the computer name; move game_logger.py out of
  the allowed column or annotate it "the shape of the record, not the code
  — no local store".
- F5 (substantive) :673-681. "the rule's first two bullets, which are
  about AI-written code" — the first bullet is about an AI MODEL deciding
  at run time ("Never let an AI model decide a poker action…"). And the
  reading that "AI-written code" does not reach third-party human-written
  code widens what the rule permits for any third-party project; §5 opens
  "because it decides everything after it" and settles it. Resolve:
  describe the first bullet correctly; present the narrowing as a reading
  the operator is asked to confirm, in the voice of §5's other deferrals.
- F6 (substantive) four counts: :412 "29 packages" → 30; :415-417 "Nine
  are pinned" then lists ten (tesserocr==2.6.1 is the Mac file's pin; the
  Windows file leaves it unpinned — the preceding sentence says so);
  :120-121 "68 files, 14,449 lines" → 69 / 14,452 (9,123 own lines);
  :294-296 "Seven window layouts" → eight (setup_form.ui missing).
- W1 :176 main.py:206-207 → :207-208. W2 :347 update_checker.py:18 → :17.
  W3 :227, :64-66 decisionmaker.py:246-262 → :247-268 (the range stops
  inside the elif). W4 :225, :635-636 the second size is minBet x
  BetPlusInc + minBet (decisionmaker.py:565-567), a multiple of the
  minimum bet, not minimum plus big blinds. W5 :795-796
  universal_poker.h:56 is one line with five members (kHalfPot under
  fchpa). W6 :230-231 "three mentions" → two (:251, :253). W7 GPL-3.0
  (:108), CDDL (:503), API (:401) never written out in the document's
  voice; "equity" unglossed from :237 on.

Every finding wording only: NO.

Round-1 cost: 29 tool calls, about 15 minutes, 12 fetches, three equity
runs; no dollar figure.
