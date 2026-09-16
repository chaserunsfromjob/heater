# Evaluation strategy 45e49ce81e40 — round 4 findings (fail; F1-F5 substantive, F6 structural)

Delete this file in the landing commit. Branch worker/45e49ce81e40, checkout
`/Users/chasethompson/.heater/worktrees/pokerbot/9fd7bd8ad257`, tip fa819e5
as reviewed, one file EVALUATION_STRATEGY.md (+1850). Recorded in the store
as round 4 (79f7a56c699e). Fixer 4 is HELD behind the four surveys
(operator instruction 2026-09-16, task c8824a64b0a1); dispatch it from this
file once the surveys have landed. Lines at fa819e5; re-locate by content.
Delete `findings-45e49ce81e40-evaluation-r3.md` in the same landing commit.

Sound and not to be re-checked: every derived figure (the whole §2.5 table,
paired-ρ table, (1−r)² multipliers, SPRT bounds, 240 cells → 6,781,440 hands
→ 235.47 h, nightly 141,280 → 4.906 h, routine 28,256 → 0.981 h, the
3.92-worker breakeven, Σw² 0.315 → Δ 28.06 and 0.335 → Δ 28.94, "buys 0.9",
proportional Δ 22.4, the LBR grid's 22 points, n! for 2-9); the five release
gate statements byte-identical at :764, :1031, :1187, :1475 and inline at
:1618; both window examples consistent with an unbroken 3→4→5→7 cycle; no
broken anchors; every trunk cross-reference into CLAUDE.md,
REFERENCE_NOTES.md and OPPONENT_MODEL_DESIGN.md resolves except as F2 and
F5 say.

- F1 (substantive) :1571-1583 vs :736-748 and :1051-1060. The "buildable
  now on today's engine" split names nightly cells at n = 2-7, a different
  grid from the five seat counts §3.6 sizes, and nothing downstream is
  restated for it: the 0.30 secondary band (n = 8, 9) is orphaned so the
  weights do not sum to 1 (§3.5 says the band weights never move); the cell
  count is 6 × 4 = 24, so the Benjamini-Hochberg family size 20 at :839,
  :887, :1786 is wrong on every run that can execute today; no wall-clock
  line exists (24 × 7,064 = 169,536 hands ÷ 28,800 = 5.89 h), though §3.6
  says no sample size may be quoted without going through it. Resolve: state
  the today's-engine grid explicitly in §3.6 or the engine-requirements
  section: seat counts, cell count, hands, hours, family size, and how the
  headline is weighted when the secondary band cannot be dealt (renormalise
  over the seats that ran and say so, or state that no headline number is
  produced until an engine deals 8 and 9).
- F2 (substantive) :1547-1558 vs trunk REFERENCE_NOTES.md:464-497 and
  :1388-1392. (a) "a seat sweep recorded on main plays 50 complete random
  hands at every seat count" is false: research/seat_sweep.py fails at 8 and
  9 with `ValueError: Deck is empty` (REFERENCE_NOTES.md:479-483, 704-711);
  it plays 2-7 only. (b) "X6: yes" and "X1: partly yes ... seats 2 to 7
  configure and play today" upgrade "ran without crashing" to "requirement
  satisfied": trunk supports "side pots are implemented" by reading
  engine.py:99-108 (REFERENCE_NOTES.md:451-455) and "chips conserved over
  50 hands", which is invariant I1, not I3 (side pots correct) or I5
  (heads-up reversal). Resolve: X6 as "implemented, read from source at
  REFERENCE_NOTES.md:451-455; not behaviourally verified, I3 still has to
  run"; the same for X1's heads-up reversal (I5); "at every seat count" →
  "at seat counts 2 through 7; 8 and 9 do not deal".
- F3 (substantive) :950-953, :1601-1605, :1846. "56,414 complete six-player
  hands per second on one core" for OpenSpiel universal_poker, sourced to
  ENGINE_ALTERNATIVES.md on a branch, exists only in an earlier draft
  (54afe67, 2026-09-15 15:54). The current tip of worker/7f09949cb56f gives
  46,745 / 47,564 / 48,410 (min/median/max of 6 repeats) for menu mode fcpa
  and 4,251 / 4,438 / 4,628 for real no-limit sizing (fullgame), and says the
  earlier numbers were taken on a busy machine. The figure is stale and
  mislabelled (menu mode, where this project needs real sizing). The
  conclusion survives: 6,781,440 ÷ 56,414 = 120.2 s, and at 4,438/s it is
  1,528 s, still far below the bot's thinking time. Resolve: drop the
  specific figure and make the point qualitatively, or quote it with the
  source commit and betting mode beside it and redo the 120 s. (Note for
  the fixer: the engine survey is still in review; re-read its tip at
  dispatch time rather than trusting these numbers.)
- F4 (substantive) :1618 (Q2 row) and the provenance table :1812-1851. The
  four-run window, nightly cadence, 3→4→5→7 cycle and the choice not to gate
  on the bot SHA carry no attribution and no provenance row, while the
  weights (:1842) and hour caps (:1844) have both; and the gate sits inside
  the Q2 "Decided" cell that opens "The operator's own answer, 2026-09-15",
  so it reads as the operator's position. Resolve: a sentence in the Q2 cell
  separating the operator's answer (the table-size ordering) from the design
  choices made here (window length, cadence, rotation cycle, SHA not gated),
  and a provenance row for the four-run window on the same footing as :1842
  and :1844.
- F5 (substantive, small) :1403 "OPPONENT_MODEL_DESIGN.md (not yet on the
  main branch at the time of writing)" is false: it landed at a640a2d on
  2026-09-15 13:35, before this branch was cut at 15:29. Everything else §5
  says about it checks out (§6, V3 :1550-1558, V5 :1582-1588, E1 :1608,
  §2.4). Delete the parenthetical or say "on main".
- F6 (structural, non-blocking) The document has no executable number
  checker, while OPPONENT_MODEL_DESIGN.md is pinned by
  tools/check_design_numbers.py (680 figures) and
  tests/test_design_numbers.py. Resolve: a tools/check_evaluation_numbers.py
  on the same pattern with a test, or a recorded decision that this document
  is not pinned and why. (Stoker's steer: add the checker; the branch base
  predates trunk's checker, so add it standalone, standard library only, and
  file a finding that the checkers should be consolidated once all land.)
- W1 :237, :243, :1290-1295 and passim "mBB/h" never defined; §2.1
  (:154-160) reconciles mbb/hand, mbb/g, bb/100, mb/g and omits it. Define
  it there.
- W2 :357, :396 "HUNL" never written out as heads-up no-limit.
- W3 :253 onward "MIVAT" never expanded (AIVAT is, at :296).
- W4 :432 "CFR" never expanded.
- W5 :45 "p-value", :205 "PPAD-complete", :388 "80% power", :815
  "percentile bootstrap": technical terms before any plain-words
  explanation.
- W6 :65-66 "141,280 hands and 4.9 hours exactly" is 4.906 h. Drop
  "exactly" or quote 4.906.

Round-4 cost: 19 tool calls, about 13 minutes at load 3.8-4.3, 125,936
tokens; no dollar figure.
