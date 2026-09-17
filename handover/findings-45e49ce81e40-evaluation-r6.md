# Evaluation strategy 45e49ce81e40 — round 6 findings (fail; F1 substantive)

Delete this file, and `findings-45e49ce81e40-evaluation-r{3,4,5}.md`, in the
landing commit. Branch worker/45e49ce81e40, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\evaluation` on the PC, tip 5640284
as reviewed. Recorded in the store as round 6 (a1e3c5b7d9f2). Lens default.
Lines at 5640284.

Sound and not to be re-checked: rounds 4 and 5's lists; round-5 F1/F6 (MIVAT
expansion, both quotations, DIVAT, pages 1976-1981, title, authors, the
Sources entry — all against the PDF fetched 00:59Z); F2 (paragraph and
provenance row agree and state only 54afe67's table); F4 (Tier 0 and §4.5
both define green against what the engine can deal, NOT RUN never passed,
seat counts 2-7 match trunk REFERENCE_NOTES.md); F5 (OpenSpiel passage
framed as the operator's recorded decision; the today's-engine block
re-framed, its arithmetic unchanged); W1-W5 of round 5 (ACPC/SE/SD/HULHE/
VPIP expanded, SHA glossed outside the gate; 6720c8a cited and its figures
unchanged; "checks"; 4h54m pinned); 278 links / 0 broken verified; the five
new mutation tests are real; the checker standard-library, encoding-safe,
nothing hard-coded outside CONSTANTS; suite 34 passed; 222 checks; no
design decision settled. Coverage that IS complete (verified by mutation):
the sample-size and paired-ρ tables, the LBR grid, the worker breakeven,
the deck arithmetic, the engine seconds, the today's-engine block, every
hand count and hour in §3.6.

- F1 (substantive; third round running) :1990-2003 and
  tools/check_evaluation_numbers.py:30-38 still claim more than the
  checker does. (a) :1991 "every column of the budget table" — the check
  reads columns 3-8 only (:735-745); mutating the routine check's seat
  list at :1124 ("2, 6, 8, 9" → "2, 6, 8, 7"), the full grid's "all of
  2…9" at :1126, or a run name exits 0 — a real gap, the seat axis is what
  the document turns on. (b) :1994-1995 "every figure the example arena
  report block prints" — the weights line :931 (n6=0.50→0.55), the cycle
  :930 (3>4>5>7→3>4>5>8) and the illustrative intervals :942 (+51.1) all
  exit 0; the intervals are declared invented at :2038, so :1994 cannot be
  true as written. (c) :1997-1999 and the docstring "checks every place" —
  false for 4,438 (unchecked at :1014, :1753, :2046), 47,564 (:2046), the
  weights (:931), the cycle in a>b>c>d form (:930). Resolve: extend the
  checker (budget-table columns 1-2 against the run names and
  NIGHTLY_FIXED_SEATS / SEAT_COUNTS; every_occurrence over all copies of
  ENGINE_HANDS_PER_SEC_REAL_SIZING and _MENU; the report block's weights
  line and the a>b>c>d cycle) with a mutation test per new pin, AND drop
  or qualify the illustrative intervals in :1994; or narrow all three
  sentences and the docstring to exactly what a check names. Do not leave
  "every column" / "every figure" standing.
- W1 (wording) :1465-1466 §4.5 "every seat count that did run" vs §3.7
  :1202-1204 "every seat count the engine can actually deal"; make §4.5
  say the latter word for word.
- W2 (wording) :104 (contents) and :273 (the §2.4 heading) print MIVAT
  before its expansion at :307-308; retitle §2.4 (e.g. "Variance
  reduction: duplicate, baseline, and the two card-correction tools") or
  gloss at the section's opening.
- W3 (wording) checker :142 ENGINE_SUPERSEDED_HANDS_PER_SEC = "56,414" is
  used only by an absent() guard (:1005-1007) for a phrase that no longer
  exists; point the guard at the current phrasing, or comment that the
  constant exists only to stop the superseded figure returning as a live
  throughput.

Every finding wording only: NO (F1).

Round-6 cost: about 50 tool calls, 33 mutations, one fetch, about 15
minutes; no dollar figure. Six rounds on this change so far.
