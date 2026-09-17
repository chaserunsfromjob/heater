# Engine survey 7f09949cb56f — what round 2 still needs, after the PC fixer

Read with `findings-7f09949cb56f-engine-r2.md`; delete both in the landing
commit. Branch worker/7f09949cb56f, tip 6720c8a (2026-09-17, PC session,
NOT pushed). The PC fixer verified F4-F12 were already applied by the
autosaved Mac fixer (59022d1..52bd81d) and applied the "Extra" citation fix
(forefront rule cited by section at :133, :825, :934, :938; treys bullet at
:476, :478). Suite on the branch: 20 passed. No benchmark was run on the PC.

## Open, and ONLY a Mac session can close them

F1, F2, F3 of round 2 all re-measure on the operator's Mac laptop under the
MEASUREMENT RULE (check `uptime`; 1-min load > 4.0 → wait up to 30 min;
record the load beside every figure; run chooser fcpa, chooser fullgame,
bench_speed, resample_opponents interleaved in one session, 3+ repeats).
The document's timings describe that machine; numbers from the PC would
describe a different computer and answer nothing. Do not dispatch review
round 3 until a Mac fixer has closed F1-F3: a reviewer would fail it on
them and the round would be wasted.

## Two small findings from the PC fixer, for that Mac fixer

- ENGINE_ALTERNATIVES.md:151-152 cites `CLAUDE.md:7-9` and `CLAUDE.md:35-37`
  by line number; stage 1 is lines 35-36 on trunk. Cite by section (the
  opening paragraph; "## Plan" stage 1). Note that worker/114e5b3f5b1b
  rewrites both passages (engine decision recorded), so cite the section
  and the words, not a line.
- ENGINE_ALTERNATIVES.md:239, :278, :356 are 114, 101 and 90 characters
  against the file's 79-80; re-wrap.

## Also outstanding on this branch (filed 2026-09-17)

Rating criterion (e) still assumes a never-distributed project; the
repository is public and GPL-3.0 as of worker/114e5b3f5b1b. Correct the
criterion's premise and re-check each (e) reason, as done for
RESOURCES_BOTS.md on that branch.
