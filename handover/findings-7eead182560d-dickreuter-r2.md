# dickreuter assessment 7eead182560d — round 2 findings (fail; R2-1 to R2-4 substantive)

Delete this file in the landing commit. Branch worker/7eead182560d, tip d094cf4
as reviewed (fixer 1's commit on a merge of main at 5653c6b; origin/main is now
69286e6, 145 commits on). Recorded in the store as round 2 (5d3bc90d65ac).
Lens default. Line numbers are at d094cf4. The dickreuter clone the reviewer
verified against is at commit cae3a108, the one the document read.

Resolved and not to be re-checked: F1-F6 and W2-W7 from round 1, every one
verified against the dickreuter source (seat combobox 2-9; the solvers scale
restored with (b) flagged as redefined; the pooled equity 0.6817 +/- 0.0003
over 2.4M above both treys references; the deck.pop dealing defect described
correctly, pair rate 0.04431 vs 0.05878 reproduced; game_logger's thirteen
requests.post at the listed lines and no open(); the first CLAUDE.md bullet
described correctly; 30 packages, nine Windows pins, 69 files / 14,452 lines /
9,123 own, eight .ui layouts).

W1 from round 1 is DISMISSED: poker/main.py:206-207 is correct at cae3a108
(206 `d = Decision(...)`, 207 `d.make_decision(...)`). Do not change line 201.

- R2-1 (substantive) :814-820, :824-834, :932-936 and all of §5 and §7 that
  rest on them. §5 quotes four CLAUDE.md sentences verbatim (the forefront
  rule bullets and "Treat who chooses the action on top of the engine as
  open ... the exception to this rule is not granted") and sorts files into
  its two-column table. CLAUDE.md on main no longer contains any of them:
  the forefront rule is replaced by "What may be coded" / "What may not be
  coded", whose first permitted bullet is "Let an AI assistant write the
  poker code: the code that picks an action, assigns a range to an opponent,
  reads the board, and combines opponent rates", plus a "Firm requirements"
  section ("Play every table size from 2 to 9 players"; "never restrict the
  bot to a fixed ladder of raise amounts"). The §5 argument about whether
  "AI-written code" reaches third-party human code is moot; the "Permitted
  as written? No" verdicts for options (ii) :913-921 and (iii) :932-936 rest
  on table cells and an exception clause that no longer exist.
  Resolve: merge origin/main into the branch first; rewrite §5 against main's
  "What may be coded" / "What may not be coded" / "Firm requirements"
  sections, quoting the current text; re-derive "Permitted as written?" for
  each of (i)-(iv) and the §7 ranking from it. (ii) likely still fails, on
  "Take the game rules and hand evaluation from the engine road ... rather
  than hand-rolling them" (calc_score); (iii) needs a fresh ground; cite the
  firm requirements under criteria (a) and (b). Keep the document's stance
  that it settles nothing and hands the operator the choice.
- R2-2 (substantive) :110, :112, :115, :122, :126, :133, :801. Every
  RESOURCES_SOLVERS.md:NNN citation is off by six against main (six lines
  added above the rating key): :165/:166/:167-168/:169-170/:171-181 are now
  :171/:172/:173-174/:175-176/:177-187; GTOpen :446-448 is :452-454;
  TexasSolverLib :528 is :534. Resolve: after the merge, re-derive all seven
  from the merged file, not by shifting.
- R2-3 (substantive) :302 "about nine standard errors above the halved
  figure and about six above the generous one". From the document's own
  figures (dickreuter SE 3.01e-4 over 2.4M; treys halved SE 3.29e-4 over
  2M; SE of the difference 4.46e-4; gap 0.0112) the halved multiple is
  about 25, not nine; six (6.5) for the generous figure is right. Resolve:
  write the multiple the numbers give, or drop the multiples and keep the
  gaps.
- R2-4 (substantive) :487-488 "a two-seat table hits the floor of 2 from
  the other side" is wrong. The clamp min(max(assumedPlayers, 2),
  total_players - 2) at montecarlo_python.py:347 gives 0 at two seats and 1
  at three; the floor never binds below four seats; run_montecarlo_wrapper
  :315 sets assumedPlayers = 2 preflop before the clamp, so heads-up equity
  is simulated with zero opponents. Resolve: say so.
- R2-5 (wording) :316 distribute_cards_to_players cited :210-224; the
  drawing block is 211-225 and 225 is the second pop. Cite :211-225.
- R2-6 (wording) :176 "poker/main.py:171-200 runs twenty-odd steps": the
  chain is 172-199, 28 calls. Cite :172-199 and say twenty-eight.
- R2-8 (wording) :467 table_scraper.py:19 → :18 (the max_players read).

Every finding wording only: NO.

Round-2 cost: 42 tool uses, 130,290 tokens, 650 s; one clone; a 400,000-hand
replication; the 32-test suite run (32 passed). No dollar figure.
