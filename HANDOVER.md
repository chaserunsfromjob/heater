# Handover

<!-- handover-commit: bd5db6f -->

Written at `bd5db6f` on `main`, 2026-09-17 about 02:10Z, on the Mac. Verify
with `bin/handover.py`. A snapshot, not a log; rewrite it, do not append.

Read `README.md` for what is built, `OPINIONS.md` for the operator's
positions, `rules/` for the rules, `handover/findings-pokerbot-pending.md`
for the next action on every pokerbot change, and the commit messages for
why. None of that is repeated here.

## Where things stand

Nothing is running. The operator stopped every agent on 2026-09-16 at
03:38Z, took a debrief (`handover/debrief-2026-09-16.md`), then worked a
full day from a PC session that landed three of the four surveys, the
design fix, the table-size notes and the licence/GitHub/OpenSpiel change on
pokerbot main. Both repositories are pushed and the Mac is caught up with
GitHub as of this commit.

The operator has now said **go**, in this exact order, and then to keep
going without asking:

1. **One worker rewrites the forefront rule in pokerbot/CLAUDE.md** in the
   operator's own words (task `a75654d078dc`, score 80, verbatim quote
   inside): an AI assistant may write the code that makes poker decisions;
   no model call may sit in the live decision path; decision code is
   ordinary testable code. Keep "hours on one laptop" (the operator had
   read it as a usage limit; the stoker explained it is a compute budget
   and they did not repeal it). Fold in "PC may push whenever" and the
   licence answer ("just use the code; private later"). Reason in the
   commit, never in the rule.
2. **One research worker writes a short note on what makes language models
   bad at poker**, naming the specific failure modes, so the rule can say
   "these stay out of the decision code". Cite real sources. Small
   document, one review round expected.
3. **A fresh reviewer judges the classmate's branch `codex/tonight`**
   (ten commits, ~5,000 lines of Python plus 75,000 lines of generated
   JSON; read-only assessment in
   `handover/codex-tonight-assessment-2026-09-17.md`) against the rule from
   step 1. His CLAUDE.md rewrite is NOT accepted as written; the operator's
   words replace it. He must open a pull request; no PR exists. The
   assessment judged his betting-rules bug fix sound.
4. Then the engine survey's Mac-only re-measurements
   (`findings-7f09949cb56f-engine-r2-remaining.md`), then the reconciliation
   brief in the pending file, now shorter: the action-chooser question is
   answered.

Also in flight from the PC session, reports lost with its context:
evaluation strategy fixer 7 (branch tip 6d800f9 on origin) and the
dickreuter assessment fixer 1 (worker/7eead182560d). Brief the next round of
each from its findings file plus a fresh read of the branch tip; do not
assume the fixer finished.

## Traps found this session

- The PC session lands by hand and does not close dispatch records; three
  landed changes still showed as "out" here until closed at `bd5db6f`.
  After any PC day: `git pull` both repositories, `git pull --ff-only` in
  each Mac worktree, then check `bin/dispatch.py list` against pokerbot
  main before believing it.
- `bin/dispatch.py land` does not push pokerbot main; push it by hand every
  time until the tooling task lands. GitHub is the single source of truth
  for pokerbot now; every pokerbot brief starts with pull, push the branch,
  open a draft pull request, and ends with push.
- The two-round landing rule is still not coded (task at 75). Never run
  reconcile while an open dispatch has a pass recorded and is unlanded.
  The operator's cap is also in force: a change at eight or more rounds
  lands on the next wording-only round.
- The operator found round numbers, commit ids and file names "gibberish".
  Report one line per document: its name, what it is about, and whether it
  is being checked, being fixed, or done. Nothing else.
- The fleet's guard was registered twice (project and personal settings);
  the personal copy was removed 2026-09-16 at the operator's request.
  Every command is still checked once by the project copy.
- Branch protection on pokerbot main requires a pull request; the owner's
  account bypasses it, so the stoker's push of main still works. The
  classmate (RohitV11, uses ChatGPT/Codex, unlimited usage) has write
  access.
- The engine fixer stopped on 2026-09-16 was waiting on a paired play
  session; its edits were autosaved and the PC then pushed further text
  fixes (6720c8a). Only the three Mac-only measurements remain.
- No live usage number exists yet (taper task). The operator's account is
  the limited one; the classmate's is not.

## Cost

This Mac session: about $64 by `~/.heater/context.json` at the debrief, more
since; 68 review rounds in the day to 2026-09-16, none with a dollar figure.
The cost hole is still open.
