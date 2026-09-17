# Handover

<!-- handover-commit: 257dc31 -->

Written on `main`, 2026-09-17 about 03:25Z, on the Mac, at 33% context
with two workers still out. Verify with `bin/handover.py`. A
snapshot, not a log; rewrite it, do not append.

Read `README.md` for what is built, `OPINIONS.md` for the operator's
positions, `rules/` for the rules, `handover/findings-pokerbot-pending.md`
for the next action on every pokerbot change, and the commit messages for
why. None of that is repeated here.

## Where things stand

pokerbot main is at `96aa546` on GitHub, up from `b5924bf` this session.
Landed today, in order: the evaluation strategy; the forefront rule rewritten
in the operator's words (CLAUDE.md now has "What may be coded" and "What may
not be coded"); LLM_POKER_FAILURE_MODES.md; ACTION_TRANSLATION.md; the engine
survey ENGINE_ALTERNATIVES.md; a sweep of the old rule's wording out of nine
documents; DECISION_LAYER_SEARCH.md; OPPONENT_BASELINE.md (observe first; keep
s = 50); BUILD_PLAN.md, the reconciliation. The classmate's branch codex/tonight was
reviewed against the new rule: 24 required changes in
`handover/codex-tonight-required-changes-2026-09-17.md` and GitHub issue #4;
his move, do not merge.

**Two workers are out and will report into this session** (compaction keeps
background agents; a fresh session would not hear them and should check the
branches on origin instead):

- `baed4c5203a7` DECISION_LAYER_BLUEPRINT.md, branch worker/baed4c5203a7,
  pre-computed strategy options with timed CFR runs. On report: one reviewer
  round, then land on small findings applied by the session.
- `70884871cf3e` build task T1, branch worker/70884871cf3e: the OpenSpiel
  adapter for 2-9 seats (fchpa menu) plus invariants I1-I7 as aborting tests,
  determinism test, per-seat NOT RUN table. This is CODE: on report, one
  fresh reviewer round (default lens), fix, land through the checkout's own
  .venv pytest plus the three checkers. Then dispatch T2 (the depth-limited
  search bot) and T3 (the persona league) from BUILD_PLAN.md section 4.

The research phase is closed: BUILD_PLAN.md landed at 96aa546. Two decisions
are the operator's, queued as report 8983491d91ab: D1 take the classmate's
arena and rules fix (recommended, OpenSpiel stays referee, PokerKit a
checker); D2 how the bot sees a real table (type hands in first; the
operator must say where they play). T2 does not wait on D1: it falls back to
three trivial opponents.

Then: the taper change `c79a35661f9c` (heater, branch tip on origin; findings
r3-r5 beside this file) has waited two days; brief its next fixer from a fresh
read of the branch tip. The dickreuter assessment `7eead182560d` exists only
on the PC (task at 52); nothing can be done from the Mac.

## Operator decisions this session (verbatim in the task list, scores 80-82)

- "we dont need perfection here, just something that we know is beating real
  players": research documents land within two review rounds; the session
  applies small findings itself and lands with `--skip-review`, recording
  why in the store note. Applied all day; not yet in OPINIONS.md or
  rules/global.md (task 30372a82869a).
- "you just need to know what types of things you are allowed to code and
  not allowed to code": the rule is two lists, done.
- Around eight agents on research at once: the operator asked for it; the
  laptop ran at load 4-7 and every measurement records its load.
- Context resets itself at 35%: `autoCompactWindow: 350000` is set in
  `~/.claude/settings.json` (backup beside it). Write this file at 30%
  without being asked; never ask the operator to type `/clear`.

## Traps found this session

- **Never close a dispatch as `pushed` before it lands.** Closing releases
  the worktree, so the reviewer has nowhere to stand and `land` then refuses
  ("already closed"). Leave it open; `land` closes it. Recovered once by
  re-pushing the branch from a hand-made worktree and merging by hand.
- **Never chain `git push --delete <branch>` after `land` in one command.**
  When land refused, the delete still ran and closed PR #2; the branch had to
  be re-pushed and the PR reopened. Delete only after
  `git branch -r --contains <tip> | grep origin/main` says it is merged.
- `bin/store.py review` refuses `--verdict pass` with findings > 0 unless
  `--wording-only`; record such a round as fail and say in the note that the
  reviewer passed it with edits.
- pokerbot has no gate script and no pytest in system python; the venv with
  pytest moves as worktrees are removed. The search-note worktree's own
  `.venv` (now gone) had it last. Task 79e6cd271cff adds a gate; until then
  the land gate is `./.venv/bin/python -m pytest tests -q -p no:cacheprovider`
  plus the three `tools/check_*_numbers.py` checkers, run in the worker's
  checkout, and a worker may have to `pip install pytest treys` there.
- `python3 -m unittest discover -s tests` runs zero tests and exits 0 in
  pokerbot; never use it as proof.
- A findings file can be staler than the branch: the engine survey's
  "remaining" note sent a fixer to re-measure work already committed. Read
  the branch tip before briefing from a findings file.
- `bin/inbox.py check --summary` needs an argument; workers cannot file a
  finding themselves (no `file` subcommand), so they hand it back in the
  report and the stoker runs `bin/queue.py add`.
- `gh pr create --draft` refuses an empty branch; workers commit a
  placeholder first. The GitHub rule says the worker marks the PR ready; the
  briefs keep it draft until review (task 33364d7ca3e1 at 40 says which).
- `tools/style_lint.py` is for rule files; research notes fail it by design
  (11-127 problems each). Not a gate for them.

## Cost

Session so far: about $83 by `~/.heater/context.json`; 36 review rounds over
14 changes today, median 1.5 rounds per change under the pace decision; no
round carries a dollar figure (the cost hole is still open, task dropped past
the cap today and worth re-filing).
