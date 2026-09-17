# Handover

<!-- handover-commit: 062357b -->

Written on `main`, 2026-09-17 about 04:30Z, on the Mac, just after a
compaction at 39% (the summary was machine-made; this file was rewritten
from the repository and the four agent reports that arrived after it).
Verify with `bin/handover.py`. A snapshot, not a log; rewrite, do not append.

Read `README.md` for what is built, `OPINIONS.md` for the operator's
positions, `rules/` for the rules, `handover/findings-pokerbot-pending.md`
for the next action on every pokerbot change, and the commit messages for
why. None of that is repeated here.

## The operator's ask for the morning

2026-09-17 ~04:25Z: "finish up any final research and by 9am tomorrow
morning we should have a somewhat formed basic plan." The plan is
BUILD_PLAN.md on pokerbot main (96aa546), six stages, T1-T3 in section 4.
By 09:00 local (16:00Z) the operator should find: the blueprint note landed
(last research document), T1 landed, T2 and T3 dispatched or landed, and
one queue report saying in plain words what the plan is and what runs next.

## Where things stand

pokerbot main is at `96aa546`. Four branches are open on origin, all four
agents have reported, and each needs one action:

- `baed4c5203a7` DECISION_LAYER_BLUEPRINT.md, PR #5, tip 8035557. Review
  round 1 FAIL, 8 findings with exact replacements (store 5f6f9f2c5ed7).
  Next: fixer applies them; F1 by withdrawing the unreproducible six-handed
  figures (7.67M states / 37.2 s / 5.8 GB) and keeping the measured ones
  (47,474 infosets, 17.9M nodes, 18.5 s); F2/F3 re-anchor the CLAUDE.md
  quotes; F7 five lines in research/make_blueprint_table.py. Then land with
  `--skip-review` under the pace decision (gate: three checkers).
- `70884871cf3e` T1 adapter + invariants, PR #11, tip a6f937b. Worker
  reports 141 passed / 1 skipped in the checkout .venv; I3 at 2 seats is the
  one NOT RUN. Next: ONE fresh reviewer round (default lens; this is code),
  fixer, land through `.venv/bin/python -m pytest -q` plus the three
  checkers, mark PR ready, merge, delete branch. Fold in the one-line doc
  fix: EVALUATION_STRATEGY.md:1713 "8 and 9 do not deal" is false on
  OpenSpiel 2.0.2 (finding e00735b83991, dropped past the cap at 45).
  Reviewer's eye: pokerbot/replay.py play_scripted_hand draws uniformly from
  the menu (no cards read); worker judged it inside the rule.
- `8cf14f9f446f` OVERNIGHT.md, PR #12, issue #13, tip d85ff7a. Done and
  pushed. Next: session reads it for tone, lands `--skip-review`, and the
  queue report to the operator names issue #13 as the link for Rohit.
- `20b9ff39b519` heater auto-push (tools/unpushed.py in bearings). Review
  round 1 FAIL, 6 findings (store 3cfa1a00d9f5): F1 a branch named `+main`
  force-pushes (push `refs/heads/<b>:refs/heads/<b>`); F2 policy unrecorded
  (README + skills/bearings rows; the OPINIONS.md line is the operator's);
  F3 a reviewer session would push via bearings (enabled() must read the
  role); F4 offline pins exit 1 forever; F5 no whole-sweep deadline; F6
  HEATER_AUTOPUSH=0 in tests/__init__.py. Next: fixer, second reviewer
  round, `bin/dispatch.py land 20b9ff39b519 --gate "bash bin/gate.sh"`.
  Main has none of this code yet; only the worker branch pushes.

Then dispatch T2 (depth-limited search bot) and T3 (persona league) from
BUILD_PLAN.md section 4. OVERNIGHT.md assigns T3 to Rohit's assistant
tonight IF he boots it; the fleet builds T3 anyway if no branch from him
appears by morning.

Two decisions are the operator's, queued as report 8983491d91ab: D1 take
the classmate's arena and rules fix (recommended yes); D2 how the bot sees a
real table. Neither blocks T2.

Also open: taper change `c79a35661f9c` (heater), waiting two days; brief a
fixer from a fresh read of the branch tip. Pace and no-menial-labor
decisions (tasks 30372a82869a, a948f1d5cba7) still need a heater worker to
put one line each in rules/global.md; the OPINIONS.md lines are the
operator's to add. dickreuter assessment `7eead182560d` is on the PC only.

## Traps

- Never close a dispatch as `pushed` before it lands: closing frees the
  worktree and `land` then refuses. Never chain `git push --delete` after
  `land`; delete only once `git branch -r --contains <tip>` shows origin/main.
- `bin/store.py review` refuses `--verdict pass` with findings > 0 unless
  `--wording-only`; record as fail with a note.
- pokerbot has no gate script; the land gate is the worker checkout's
  `.venv/bin/python -m pytest -q` plus `tools/check_*_numbers.py` (three).
  `python3 -m unittest discover` runs zero tests there and exits 0.
- Read the branch tip before briefing a fixer from a findings file.
- Workers cannot file findings; they hand them back and the stoker runs
  `bin/queue.py add`. `bin/inbox.py check --summary` needs an argument.
- The auto-mode classifier refuses briefs that edit `hooks/`; put session
  behaviour in `tools/` or `bin/`.
- `tools/style_lint.py` is for rule files; research notes fail it by design.
- Compaction at 35% (`autoCompactWindow` in ~/.claude/settings.json) keeps
  background agents; a fresh session does not hear them and must read the
  branches on origin instead. Write this file at 30% without being asked.
- Any uncommitted queue/inbox file makes `bin/handover.py` fail "working
  tree clean": commit queue, inbox and store with the handover.

## Cost

Session so far about $115 by `~/.heater/context.json`; 40 review rounds
over 16 changes today, no round carries a dollar figure (task for the cost
hole dropped past the cap; worth re-filing when the list has room).
