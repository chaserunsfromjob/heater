# Solvers survey 048795519f43 — round 3 findings (fail, 6 substantive, 0 wording)

Delete this file in the landing commit. Branch worker/048795519f43 at
25948cc, checkout `.heater/worktrees/pokerbot/85f4140c6fae`. Everything the
reviewer sampled that is not listed here held: range counts, turn log,
bincode pin, GTOpen table, every GTO Wizard quotation and date, vendor
prices, repository metadata, the page-fault paragraph; postflop-solver
re-ran at 0.18-0.21 s at load 3.41. Four of the six fails are prose claiming
more than, or other than, the evidence. The round-3 fixer was dispatched
with these.

Lines in RESOURCES_SOLVERS.md.

- F1 (fail-class) :905-918 and :841-846. Under "Settled by measurement, and
  safe to adopt now" the bullet titled "Hand ranking and equity: phevaluator
  now, OMPEval when the loop is hot" carries the bolded imperative "where a
  runtime path needs an evaluator, use phevaluator", then four lines later
  says nominating the runtime evaluator belongs to the reconciliation. The
  shortlist repeats the nomination at :845. No project file records a
  runtime evaluator (trunk CLAUDE.md:16-17 reserves ranking a hand to the
  engine and keeps treys to tests). Resolve: keep only the measurement in
  the settled list (phevaluator 5-15x treys here; OMPEval faster with its
  6-player cap); retitle the bullet with no now/when nomination; move every
  imperative about what the bot calls at decision time (heading, bolded
  sentence, :845) into the "Open, and for the reconciliation to decide" list
  beside the heads-up-engine bullet.
- F2 :196-208, :1005 (table row 3), :1019-1023. "four runs … 421 to 423 s
  wall, 462 to 700 s CPU (1.1 to 1.7 cores), 3.4 to 5.8 GiB peak, iterations
  0 to 3 … 221.7% at iteration 2 on every run" merges runs of different
  lengths. The runs on this machine: 423.1 s / 699.8 s CPU / 1.65 cores /
  5.79 GiB / [0,2,3] (tasks/br3xvl2n0.output under the 60db9bfd session
  dir); 422.5 s / 462.2 s / 1.09 / 5.41 GiB / [0,2,3] (flop_probe2.out,
  load 3.75); 421.4 s / 493.4 s / 1.17 / 4.95 GiB / [0,2] (flop_r2/
  runner.txt); 181.5 s / 302.4 s / 1.67 / 3.44 GiB / [0,2] (flop_rev2.out);
  151.6 s / 343.5 s / 2.27 / 4.43 GiB / [0,2] (flop_review.out); all under
  the 9aadbb23 scratchpad unless named. So: three deadline runs, not four;
  the 3.4 GiB floor is from the 181 s probe while full runs used 4.95-5.79
  GiB; the 2.27-core run is dropped; "0 to 3" and "on every run" are false
  for the [0,2] runs; "three mine, one an independent re-run" is backwards
  (two deadline runs are the fixer's, one the reviewer's). Resolve: report
  the three ~420 s runs as the population with each run's wall, CPU, cores,
  peak RSS, iterations and start load per run; list the 151.6 s and 181.5 s
  runs separately as short probes; publish the runner's stdout for the full
  runs under research/solvers/ as was done for the turn run.
- F3 :730-731, knock-on :46-49, :870-873. Holdem Solver "converged after 20
  million iterations in 9 min 05 s" is reversed: holdemsolver.com shows
  "20,050,063 iterations · 9m 05s  Δ 0.0010 · precision low" and says "20
  million iterations in and still converging". "Take RAM and hours on
  multiway postflop trees" has no measurement or vendor statement for
  Holdem Solver. Resolve: quote the vendor verbatim with its own caption;
  source the "hours" claim or mark it UNVERIFIED and let "no scripting,
  driven by hand" carry the exclusion.
- F4 :649-663. The Feb 3 2026 patch note the file quotes also states
  "After Early Bird, standard Ultra pricing will be: Annual: $289/month
  Monthly: $359/month", so the press $289/$359 figures are vendor-confirmed
  too; the Sep 15 2026 ICM patch note says "Early Bird pricing ends October
  15, 2026 at 1:00 PM CEST". Resolve: four Ultra figures vendor-confirmed
  ($229/$279 Early Bird, $289/$359 standard), the Early Bird end date, and
  only Starter/Premium/Elite left as press-sourced and unconfirmed.
- F5 :51-53, :610-612. "MonkerSolver's own community drives it with
  keyboard macros / AutoHotkey macros" carries no URL or date; the vendor
  page says nothing about AutoHotkey; the claim is the stated evidence for
  "no API", which drives finding 1, the (d) rating and shortlist slot 7.
  Resolve: cite the thread with its date, or drop the sentence and rest the
  conclusion on the vendor page documenting no API and no scripting.
- F6 :1052-1057 (Appendix B) names bench_phe.py and bench_treys.py, which
  are not under research/solvers/; the phevaluator (0.9-2.6 M hands/s) and
  treys (165 k hands/s) figures decide shortlist slots 2 and 12 and the
  "5 to 15 times faster" claim. The published turn log records the solver's
  timer but not the 5.45 s wall or the 3.40 load quoted beside it. Resolve:
  commit the two benchmark scripts beside the solver command files; put the
  wall time and load in the turn log header or a one-line run note.

Landing note: merge-base 5558063 is far behind trunk; re-check the three
CLAUDE.md line citations (:13-15, :17, :24) after the merge.
