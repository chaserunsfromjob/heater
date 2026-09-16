# Solvers survey 048795519f43 — round 4 findings (fail; F1-F7 substantive, F8 wording)

Delete this file, and the r3 file beside it, in the landing commit. Branch
worker/048795519f43 at f237c6d, checkout
`.heater/worktrees/pokerbot/85f4140c6fae`. The evidence base held in full:
the three published flop logs are byte-identical to their originating runs,
every per-run figure exact, range counts recomputed, the four vendor pages
verbatim, six further citations exact, benchmarks re-run at load 3.65
(13.0x, inside the stated 5-15x), CLAUDE.md citations correct against
trunk. The round-4 fixer was dispatched with these.

Lines in RESOURCES_SOLVERS.md.

- F1 (fail-class) :949-962 under "Settled by measurement, and safe to adopt
  now" the second bullet "Preflop: buy or transcribe ranges for 2 to 9
  seats rather than solving preflop at all" has no measurement behind it
  and, read with :860-862 ("buy a MonkerGuy text pack … and never solve
  preflop ourselves"), is a decision-time call against trunk CLAUDE.md:26
  ("Producing the strategy itself" is the engine's). Resolve: say which
  meaning is intended; if it touches the decision path, move it beside the
  heads-up-engine bullet in the open list; if it is study material, restate
  it as a market fact ("2-9 seat preflop ranges are available free or for
  $69-$499, so no preflop solving is needed to obtain them — Part 4") and
  retitle the heading so the list claims no measurement it lacks.
- F2 :628-643, knock-on :47-52 and :906-909. The vendor-page-scoped
  sentences are true (monkerware.com solver, guide, faq and trees pages
  document no API or scripting). The unscoped ones are too broad: "there is
  no way to drive it from a program" (:642-643) and "no scripting
  interface" (:908, :50). https://plodalong.com/articles/monkersolver-scripting
  (PlodAlong, 31 March 2026, MonkerSolver Series Part 3) documents a
  built-in Scripting tool under the Solve menu: point it at a saved .tree
  with ranges and a comma-separated board list, set volatility 2.0 and
  "reset avg after iterations" 7, choose a save folder, Start; it solves
  each board in sequence "overnight or across multiple days". (d) does not
  move (that is multi-day batch work). Resolve: cite the guide with URL and
  date in entry 16; one sentence on what the tool is and is not (a GUI
  dialog that batch-solves a board list against one saved tree, started by
  hand, output to files; no command line, no API, no way for a program to
  start or read a solve); rest the exclusion on "no external program
  control, and batches run overnight to days"; replace the bare wording at
  :908 and :50. Keep :628-636.
- F3 :1058 Appendix A row 3 "iterations 0, 2 and 3 printed … on all three
  runs": run 2 printed only [0, 2] (run2 log line 8). Say "0 and 2 on every
  run, 3 on two of the three; 226.39% at iteration 0 and 221.72% at
  iteration 2 on all three", or point at the per-run table.
- F4 :206, :1078, :1155 run 2's start load 3.29 is in no committed file
  (its log records no load). It is genuine: the 9aadbb23 scratchpad's
  flop_r2/probe.txt first line is "=== BEFORE  t=20:49:31  load=3.29 4.46
  4.74". Commit that line as a header in the run-2 log or a one-line run
  note beside it, as texassolver_turn_run_note.txt does.
- F5 :80-85 "of the order of ten thousand play-outs and is therefore a
  tens-of-milliseconds job": the 10,000 has no source and is not marked as
  an assumption, and at the file's own 0.9-2.6 M hands/s it is 3.8-11 ms.
  Mark the assumption, show the arithmetic, give the range it yields; or
  drop "therefore" and say the loop was not measured.
- F6 :794-795 Deepsolver "$0.025 per calculation on demand" is the overage
  rate inside the Scale $4,875/month plan; "consumer plans $10/$76/$209 per
  month (no API)" is not on deepsolver.com/api. State the overage
  correctly; cite the consumer tiers' page or mark them UNVERIFIED.
- F7 :1045-1051 vs :341-344 and :1184. The Appendix A header says rows
  without a load were carried from earlier rounds; row 6 (GTOpen cargo
  build) was "Re-built today" with no load. Entry 3 makes 3 min 20 s the
  first build and 1 min 53 s the rebuild; Appendix B says the reverse.
  Exempt row 6 in the header sentence; make Appendix B agree with entry 3.
- F8 (wording) RAM :54, CPU :55, JSON :65, HTTP :90, GUI :160, CLI :430
  never expanded; plain words first as the file does for its other
  acronyms.
