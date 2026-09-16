# Table-size notes 984aa6810a05 — round 4 findings (fail; F1-F3 substantive)

Delete this file in the landing commit. Branch worker/984aa6810a05, checkout
`/Users/chasethompson/.heater/worktrees/pokerbot/8b0b4064141f`, tip 9c4a168
as reviewed, one file TABLE_SIZE_AND_SIZING_NOTES.md (+1235). Branch base
5558063 predates trunk's 5aa40b8, so the checkout carries neither
`tools/check_design_numbers.py` nor the companion documents; judge them on
trunk `/Users/chasethompson/pokerbot` read-only. Recorded in the store as
round 4 (ccddee884437). Fixer 4 dispatched 2026-09-16 with these. Lines at
9c4a168; re-locate by content.

Sound and not to be re-checked: every derived number reproduces (Tables 1-6,
TV(n,m) = (n-m)/n, the 1/(n+1) adjacent-seat claim, 4.5x and 2.25x, 32 and
16 runs, Table A re-derivations, Table 4 products); all 40 anchors; every
cross-reference into OPPONENT_MODEL_DESIGN.md resolves on trunk; four
primary sources verified by curl; the forefront table is not crossed;
nothing is quietly settled; Q5's claim about the queued CLAUDE.md task is
true.

- F1 (substantive) :516-524 (§2.3 Failure 2), :681-690 (R1's FULL = 7-9
  band), :904-937 (R10, E7/E8/E9 and their "if the answer is no" bullets),
  :1026-1031 (Q4's solve order). The string REFERENCE_NOTES appears nowhere
  in the file, nor "fixed-limit", "short deck", "20-card". Trunk
  REFERENCE_NOTES.md:12-15 and :485-503 record the 20-card deck seats seven
  at most and "the 8/9 band is impossible on the short deck"; :8-11 "The
  52-card conversion is out"; :16-19 and :524-542 the engine is fixed-limit,
  one big blind on top of the call, doubled turn and river, three raises a
  street, "no bet-sizing dimension anywhere in the tree". So E9 and E7 are
  posed as open questions trunk already answered for the current engine
  (commit 11c32a6), R10's E8 remedy (2) "inside the engine's own translation
  code" is unactionable on an engine with no bet sizes, and §2, R8, R9, R12,
  the FULL band and Q4 read as reachable now. Resolve: a short passage in §1
  or at the head of §2, echoed in the E7/E9 rows, citing REFERENCE_NOTES.md
  by line, stating the current engine's answers are already no (seven-seat
  ceiling, fixed-limit, 52-card conversion out), that seats 8 and 9 and all
  of §2 wait on the engine decision the four-survey reconciliation makes,
  and that E7/E8/E9 are asked of a candidate engine. No recommendation
  changes, only its stated dependency.
- F2 (substantive) :1217-1228 provenance rows for Tables 1, 2, 3, 5, 6 and
  the 32-run figure read "Computed by script 2026-09-15", as do the notes at
  :106, :144, :170, :340, :552, :604, and no script exists in the diff. The
  companion names its checker at every equivalent place and carries the rule
  (OPPONENT_MODEL_DESIGN.md:1781-1786) that a constant changes in the script
  and the prose together. Every figure is correct; this is a provenance and
  maintenance gap. Resolve: add a script that recomputes Tables 1-6, the
  4.5x blind-frequency ratio and the 2.25x fold_to_steal multiplier from one
  copy of the constants, with a test that runs it, and name it in every
  provenance row and note. (Stoker's steer: add `tools/check_table_size_numbers.py`
  and `tests/test_table_size_numbers.py` on this branch rather than merging
  trunk in to extend the existing checker; file a finding that the two
  checkers should be consolidated after both land.)
- F3 (substantive, minor) :818-828 (R6 "the genuine delta") and :1026-1031
  (Q4's recommendation). The file pins its cross-references to
  OPPONENT_MODEL_DESIGN.md at 5aa40b8 (:14-16); trunk is now 5f7a1a8, and
  72eff27 put into §4.5 the operator's solve order ("Solve 6-handed first;
  then 8- and 9-handed as one band; then every remaining seat count",
  :1290-1292) and the separate-runs rule for 8 and 9 (:1294-1300). R6's delta
  list is no longer the delta and Q4 recommends what §4.5 already states.
  Resolve: re-pin to trunk's current revision, or add one sentence to R6
  recording that §4.5 has since taken the solve order and the separate-runs
  rule, leaving the RESOURCES_SOLVERS.md pointer and the "banding is not the
  escape" point as the residue.
- F4 (wording) :385 "in the sentence immediately before the one it builds
  on" is wrong: on trunk (OPPONENT_MODEL_DESIGN.md:92-102) two sentences
  separate them. Say "two sentences earlier in the same paragraph" or drop
  the positional claim.
- F5 (wording) `n` is the seat count at :81 and throughout §1 and §3, the
  DBBR paper's public-history index at :450-452 and :878, and the
  opportunity count at :454-455. Name the paper's index as the paper's, or
  rename it in the prose.

Round-4 cost: 26 tool calls, 118,442 tokens, 11.4 minutes; no dollar figure.
