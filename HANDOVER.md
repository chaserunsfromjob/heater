# Handover

<!-- handover-commit: 6550a18 -->

Written on `main`, 2026-09-17 about 05:05Z, on the Mac, at 29% context with
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

pokerbot main is at 7b1545c (T1 the table landed on a round-2 pass, PR #11).
Also landed tonight: OVERNIGHT.md + issue #13; bin/gate.sh (the pokerbot
land gate is now `bash bin/gate.sh`); DECISION_LAYER_BLUEPRINT.md. Rohit's
assistant has not started (no PR, codex/tonight unchanged at ca8339e).

Four agents are out; each report needs one action. Compaction keeps them;
a fresh session must read the branches on origin instead.

- `8edc0ce3e009` T2 the first bot, PR #15, tip d1bf741, worktree
  pokerbot/732f0d699fca. Built: 1,000 hands at six seats vs random, 0
  invariant failures, max decision 61 ms, +2265 bb/100 [+849, +3750]. Its
  REVIEWER round 1 is out. Then fixer, confirming round, land with
  `bin/dispatch.py land 8edc0ce3e009 --gate "bash bin/gate.sh"`, push
  pokerbot main, delete branch. Caveat to carry into the morning report:
  nearly all decisions were preflop (random opponents shove).
- `1fd3a6ebe936` T3 the scoreboard, PR #16, tip 7469d54, worktree
  pokerbot/4ecb51776067. Built: personas, split, paired deals, bootstrap,
  section 3.5 rule; 219 tests. REVIEWER round 1 out. Same landing path.
  T2 and T3 do not touch each other's files; T3's always_fold/always_call/
  uniform_random duplicate T2's baselines.py: reconcile at the second
  landing (keep one, task 6805b01c7bd2 covers the __init__ docstring).
- `20b9ff39b519` heater auto-push in bearings: LANDED 3b26e74 on a round-5
  clean pass (five rounds). Every bearings read now pushes unpushed local
  branches in every known checkout; HEATER_AUTOPUSH=0 turns it off; it
  pushed the taper fixer's in-progress commit on its first live run. The
  PC's next bearings run pushes the dickreuter branch.
- `ecc208e2d0d6` heater reconcile landing fixes (latest round decides; two
  consecutive wording-only rounds; empty branch never landed; merged branch
  told apart from never-started by the lease's base_sha), tip 79e31c2,
  worktree heater/5663ae84bf74. Round 1 fail on inert tests, fixed twice;
  REVIEWER round 2 out. On pass land the same way; tasks f16c56933d8a,
  dc8e3ac0bd7f, f0b91b86f69f done then.
- `c79a35661f9c` heater usage taper (bands, pacing line, debrief page,
  opinion 14), tip 6020302, worktree heater/03a2b608f262. Six rounds; the
  taper half is sound and the status-line writer was verified against
  Claude Code 2.1.274; every remaining fail is the debrief page. FIXER round
  6 is out with findings F1-F4 plus tasks 001bbe019ca8 and 06e6e60bc3f7
  folded in. Then round 7; land; delete handover/findings-c79a35661f9c-*
  in the landing commit; tasks 32cbdf129bdf, ab4ea92fcb09 done then.

Nothing else is dispatched. Next after these land: the morning report; then
Stage 2 of BUILD_PLAN.md (run T2's bot through T3's scoreboard, which is
the first real measurement of the plan), and D1/D2 remain the operator's.

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

Session about $193 by `~/.heater/context.json`; 50 review rounds over 20
changes today; no round carries a dollar figure.
