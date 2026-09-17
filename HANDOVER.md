# Handover

<!-- handover-commit: 00648e2 -->

Written on `main`, 2026-09-17 about 05:05Z, on the Mac, at 34% context with
four agents out. Verify with `bin/handover.py`. A snapshot, not a log;
rewrite, do not append.

Read `README.md` for what is built, `OPINIONS.md` for the operator's
positions, `rules/` for the rules, `handover/findings-pokerbot-pending.md`
for the state of every pokerbot change, and the commit messages for why.
None of that is repeated here.

## The operator's asks for the morning

- ~04:25Z: "finish up any final research and by 9am tomorrow morning we
  should have a somewhat formed basic plan." Research is closed (every
  document on pokerbot main; the last, the blueprint note, landed b00802d).
  The plan is BUILD_PLAN.md. By 09:00 local (16:00Z) send ONE queue report
  in plain words: the plan, what landed overnight (T1 the table; T2 the
  first bot and T3 the scoreboard if their reviews pass), the link for
  Rohit (GitHub issue #13), and D1/D2 still theirs (report 8983491d91ab).
- ~04:35Z: run as many agents as the five-hour window allows, spread across
  the whole window, on the most important work (task ab4ea92fcb09, score
  83, verbatim in OPINIONS.md opinion 14 on the taper branch). Until the
  taper lands there is no usage reading; pace by hand at about five agents,
  never a burst of eight (that hit the limit at 03:45Z).

## Where things stand

pokerbot main is at 88ffff1: T1 the table (PR #11), T2 the first bot (PR #15) and T3 the scoreboard (PR #16) all landed tonight. The MORNING REPORT is queued (d9e05d4e4a29, 05:43Z): deliver it, do not write another.
Also landed tonight: OVERNIGHT.md + issue #13; bin/gate.sh (the pokerbot
land gate is now `bash bin/gate.sh`); DECISION_LAYER_BLUEPRINT.md. Rohit's
assistant has not started (no PR, codex/tonight unchanged at ca8339e).

One agent is out (taper fixer 7); each report needs one action. Compaction keeps them;
a fresh session must read the branches on origin instead.

- `8edc0ce3e009` T2 the first bot: LANDED 3a54ce2 (PR #15) on a round-2
  wording-only pass. Evidence: 1,000 hands at six seats vs random, 0
  invariant failures, max decision 82 ms, +2286 bb/100 [+801, +3824];
  1216 of 1242 decisions preflop (random opponents shove), stated in the
  README. T3 cut from 7b1545c: at its landing, merge may touch README.md
  (both add sections); then keep personas.py as the one home for the three
  trivial agents and shim arena.py to it; delete baselines.py (task
  6805b01c7bd2 covers the __init__ docstring).
- `1fd3a6ebe936` T3 the scoreboard: LANDED 88ffff1 (PR #16) on a round-2
  wording-only pass with the six wording edits applied by a fixer and the
  merge with T2 resolved (README both sections). 270 tests on main. The
  three trivial agents now exist twice (task d077f18909a7: keep personas.py,
  shim arena.py, delete baselines.py); the __init__ docstring names two
  layers of three (task 6805b01c7bd2).
- `20b9ff39b519` heater auto-push in bearings: LANDED 3b26e74 on a round-5
  clean pass (five rounds). Every bearings read now pushes unpushed local
  branches in every known checkout; HEATER_AUTOPUSH=0 turns it off; it
  pushed the taper fixer's in-progress commit on its first live run. The
  PC's next bearings run pushes the dickreuter branch.
- `ecc208e2d0d6` heater reconcile landing fixes: LANDED c6b30aa after four
  rounds (code mutation-proved each round; the last finding was prose,
  applied by the session, landed --skip-review). The sweep now: lands on
  the LATEST round; needs two consecutive wording-only passes; never treats
  an empty branch as landed; holds any checkout with a heartbeat under 30
  minutes on the empty, merged and --skip-review routes; `--reason` on land
  and reconcile. A REVIEWED checkout is still removed on the next sweep
  (documented in skills/dispatch and README step 7). Tasks f16c56933d8a,
  dc8e3ac0bd7f, f0b91b86f69f done. Siblings filed: b3b71f0512ac
  (worktrees.reclaim no heartbeat), d80c47c137ae (autosave before guards).
- `c79a35661f9c` heater usage taper (bands, pacing line, debrief page,
  opinion 14), tip 1d175b8, worktree heater/03a2b608f262. Seven rounds; the
  taper half was sound from round 4 and the status-line writer is verified
  against Claude Code 2.1.274; fixer 6 applied the four debrief-page
  findings plus tasks 001bbe019ca8 and 06e6e60bc3f7 (539 tests). Round 7
  FAIL on three page regressions and a merge conflict with main (README,
  tools/bearings.py); FIXER round 7 is out, told it is the last: the
  stoker lands on round 8 if only wording remains. On pass:
  `bin/dispatch.py land c79a35661f9c --gate "bash bin/gate.sh"`, push,
  delete handover/findings-c79a35661f9c-* in the landing commit (or right
  after), delete the branch; tasks 32cbdf129bdf, ab4ea92fcb09,
  001bbe019ca8, 06e6e60bc3f7 done then. Then ~/.heater/usage.json appears on
  the next status-line render and bearings shows the five-hour figure and
  the pacing line: pace agents by it.

Nothing else is dispatched. Next: land the taper; then Stage 2 of
BUILD_PLAN.md as one pokerbot worker: register T2's search bot with
league.register_bot, run `python -m pokerbot.scoreboard --bot search` over
the nine personas at seats 2/6/8/9 (about 4 minutes for the 52-cell grid),
commit the report (under 200 lines) and say what it shows; fold task
d077f18909a7 (one home for the trivial agents) into the same brief. D1/D2
remain the operator's.

## Traps

- Never close a dispatch as `pushed` before it lands; `land` closes it.
  Never chain `git push --delete` after `land`; delete only once
  `git branch -r --contains <tip>` shows origin/main.
- `bin/dispatch.py land` does not push pokerbot main: `git -C
  /Users/chasethompson/pokerbot pull -q origin main && git push -q origin
  main` after it. The GitHub rule "changes through a pull request" is
  bypassed for the owner; the PR shows MERGED once main is pushed.
- `bin/store.py review` refuses `--verdict pass` with findings > 0 unless
  `--wording-only`; record a pass-with-substantive-findings as fail.
- Under the pace rule (rules/global.md, Landing) the session applies wording
  findings itself for research documents and lands `--skip-review`; code
  gets a confirming round.
- Confirming rounds on fleet code keep finding one small thing in the last
  fix (auto-push: four rounds of it). Scope each fixer brief to the finding
  and each reviewer brief to "confirm the fix, say if wording only".
- Workers cannot file findings unless they run bin/queue.py add against the
  main checkout (some do); judge whatever appears in the inbox.
- The auto-mode classifier refuses briefs that edit `hooks/`.
- Any uncommitted queue/inbox/store file fails `bin/handover.py`; commit
  them with the handover.
- Two review records on main had an unescaped backslash and were silently
  dropped by jsonstore.load (repaired 2026-09-17); the taper fixer adds a
  count of unreadable records to the debrief page.
- pokerbot worktrees keep their own `.venv`; bin/gate.sh builds it.

## Cost

Session about $215 by `~/.heater/context.json`; 55 review rounds over 21
changes today; no round carries a dollar figure.
