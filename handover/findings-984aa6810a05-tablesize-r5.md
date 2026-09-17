# Table-size notes 984aa6810a05 — round 5 findings (fail; F1-F5 substantive)

Delete this file, and `findings-984aa6810a05-tablesize-r4.md`, in the landing
commit. Branch worker/984aa6810a05, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\tablesize` on the PC, tip c859c66
as reviewed. Recorded in the store as round 5 (e8a3f61c2d47). Lens default.
Lines in TABLE_SIZE_AND_SIZING_NOTES.md at c859c66 unless stated; re-locate
by content. The branch must NOT merge trunk in (round-4 rule): trunk's
tests/test_design_numbers.py and tools/check_design_numbers.py are not on
it and that is expected.

Sound and not to be re-checked: all five round-4 findings resolved as
asked — §1.0 (:74-136) and its echoes at :489-498, :788-797, :1036-1051,
:1070-1081, :1159-1167, :1413-1414 all check against trunk
REFERENCE_NOTES.md (:8-11, :12-15, :16-19, :485-497, :499-503, :523-542);
"Computed by script" gone, checker named in 17 places, constants in one
block (:50-90); R6 :924-935 and Q4 :1185-1191 exact against 72eff27
(:1287-1288, :1292-1300) and 5f7a1a8 is still the latest commit on the
design; :458 correct against design :92-102; the three meanings of n at
:149-156, :534-542, :1000-1003. Checker: 232 figures, eighteen hand-traced
across all six tables and both multipliers, half-up rounding right,
repeat-guard proven by test_drift_in_the_blind_frequency_ratio. All 50
internal links resolve (55 targets, 0 broken). ENGINE_ALTERNATIVES.md never
quoted as settled (:314-316, :913-918, :1063, :1169-1181). No design
decision settled; three new files, nothing modified; every figure has a
provenance row. Round 4's sound list stands.

- F1 (substantive, code) tools/check_table_size_numbers.py:503-507 and
  tests/test_table_size_numbers.py:75-82. When a figure drifts, the
  failure line carries "≤" (Table 3) or "−" (Table 5, MINUS at :138); on a
  Windows console (cp1252) `print` raises UnicodeEncodeError and the
  script dies after "1 of 232 figures ... do not match:" with no detail
  line. test_drift_in_table_3 fails on this PC (12 passed, 1 failed);
  green only with PYTHONIOENCODING=utf-8. The exit code still reads 1, so
  the crash is disguised. Resolve: `sys.stdout.reconfigure(encoding=
  "utf-8", errors="replace")` at the top of main() (:495) or ASCII failure
  lines; add a test that runs the checker on a mutated copy with
  PYTHONIOENCODING=cp1252 and asserts the detail line "Table 3 9 vs 2 bound
  at spread 0.3" is present. Note the same shape in trunk's
  check_design_numbers.py for the eventual merge of the two checkers.
- F2 (substantive) :124-127, also :493-495 and :1043-1044. "the four
  surveys now in progress ... of which REFERENCE_NOTES.md is one" is wrong:
  REFERENCE_NOTES.md is the survey of the engine already in the repository,
  on trunk, not an input to the reconciliation. Resolve: name the documents
  — the reconciliation of ENGINE_ALTERNATIVES.md, RESOURCES_BOTS.md,
  RESOURCES_SOLVERS.md (and RESOURCES_EXPLOITATION.md, landed on main
  2026-09-17) — and say separately that REFERENCE_NOTES.md is the survey of
  the engine being replaced, already on trunk. Same substitution at all
  three sites.
- F3 (substantive, always-fail class) :1398-1402 "Consolidating them is
  filed as a task": task 8edd19d47712 fell past the list cap and is gone by
  rule (no store holds it; findings-pokerbot-pending.md:61-62). Resolve:
  drop the claim and state the work in the document, matching the script's
  own docstring (:19-21): the two checkers should be merged once both
  documents are on trunk; the duplication is the half-up rounding helpers,
  the markdown table reader, the Checker surface and the exit-code
  contract.
- F4 (substantive, minor) :114-128, :489-498, :1036-1051, :1159-1167. The
  engine dependency is one operator decision stale: on 2026-09-16 the
  operator decided the engine road is OpenSpiel `universal_poker`
  (heater commit fb353c6; fedden/poker_ai reference only; dickreuter/Poker
  the capture reference); the open question is the forefront-rule
  carve-out over who chooses the action. Resolve: one paragraph in §1.0
  after the "Waiting on which engine" bullet recording that decision as
  the operator's recorded decision (it is in worker/114e5b3f5b1b's
  CLAUDE.md, not yet on main), and "waits on the engine choice" → "waits
  on the OpenSpiel move" at :114-118, :493-498, :1043-1044. No
  recommendation changes.
- F5 (substantive, minor) :1155 "Thirty-two runs are inside that cap" is
  the one copy of the 32-run figure written in words; the checker's
  regular expression `(\d+) (?:offline )?solver runs` (script :429-433)
  sees digits only, so this copy would survive a change silently.
  Resolve: assert the phrase from the same `full` constant in
  check_solver_runs (extend spell() at :480-492 or build the phrase), and
  add a drift test that mutates "Thirty-two runs" and asserts exit 1.
- W1 (wording) :163 VPIP, :354 AF, :417 pp, :474 DBR, :533 DBBR, :955
  bb/100 never written out. DBR (Johanson & Bowling, data-biased response)
  and DBBR (Ganzfried & Sandholm, deviation-based best response) are
  different methods; say so in one clause at :474. Expand each on first
  use.
- W2 (wording) :213-217 the Table 2 caption leads with "Total variation
  distance" and the formula; lead with the plain reading already there
  ("the share of one table's hands that come from positional contexts the
  other table reaches at a different rate"), then the formula, then the
  name; gloss the TV column header at :245.
- W3 (wording) :74-101 §1.0 promises "Three questions ... already settled"
  but the third bullet is a supporting fact, not a question asked below
  (:130-136 names only E7, E8, E9). Reword: two questions settled and a
  third fact closes the obvious escape.
- W4 (wording) :97-99 "at a claimed 18.4 days ... 146.5 GiB of memory
  demanded" — source (REFERENCE_NOTES.md:8-11) says "at least 18.4 days"
  and "claimed" meaning reserved; and 18 days is a floor by scaling.
  Resolve: "at least 18.4 days of computing and 146.5 GiB of memory
  reserved in one piece — a floor worked out by scaling up a run that did
  finish, not a stopwatch reading".

Every finding wording only: NO.

Round-5 cost: 49 tool calls, about 25 minutes, no fetches; no dollar
figure. Five rounds on this change so far.
