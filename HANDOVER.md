# Handover

<!-- handover-commit: e613c99 -->

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

pokerbot main is at 7b1545c (T1 the table landed on a round-2 pass, PR #11).
Also landed tonight: OVERNIGHT.md + issue #13; bin/gate.sh (the pokerbot
land gate is now `bash bin/gate.sh`); DECISION_LAYER_BLUEPRINT.md. Rohit's
assistant has not started (no PR, codex/tonight unchanged at ca8339e).

Four agents are out (T2 fixer 1, T3 fixer 1, reconcile fixer 3, taper reviewer 7); each report needs one action. Compaction keeps them;
a fresh session must read the branches on origin instead.

- `8edc0ce3e009` T2 the first bot, PR #15, tip d1bf741, worktree
  pokerbot/732f0d699fca. Built: 1,000 hands at six seats vs random, 0
  invariant failures, max decision 61 ms, +2265 bb/100 [+849, +3750],
  reproduced by the reviewer to the decimal. Round 1 FAIL (store
  480b01dad5b2): seen_cards() took fchpa action codes 0-4 for cards, so
  imagined deals left out ~2.5 real cards per decision; result is preflop-
  only (1215/14/0/0 by street) and that was recorded nowhere. FIXER round 1
  is out (re-records the 1,000-hand run after the fix). Then a confirming
  round; land with `bin/dispatch.py land 8edc0ce3e009 --gate "bash
  bin/gate.sh"`, push pokerbot main, delete branch. At the second of T2/T3
  to land: keep T3's personas.py as the one home for always_fold/
  always_call/uniform_random and shim arena.py to it; delete baselines.py
  (reviewer's recommendation; the two differ in signature, not behaviour).
- `1fd3a6ebe936` T3 the scoreboard, PR #16, tip 7469d54, worktree
  pokerbot/4ecb51776067. Built; closed form, rule rejection, pairing and
  engine-only hand strength confirmed; full 52-cell run works (204 s).
  Round 1 FAIL, ten findings (store 92b454e6fb34): arena ships inside
  pokerbot/ against EVALUATION_STRATEGY.md sections 3.1/3.3 (fixer told to
  amend the document and add an import-graph guard, not move modules);
  169-class ranking at 120 rollouts is noise and its test cannot fail;
  one-sided p-value stars a zero difference; header weights differ from
  decide()'s; NOT RUN reason truncated; config rollouts unread; bot arm gets
  no memory calls; bot RNG carries across cells; rescaling undocumented.
  FIXER round 1 out. Then a confirming round; land; at the second of T2/T3
  to land, keep personas.py as the one home for the three trivial agents
  and shim arena.py to it (signature (hand, seat) -> Action); delete
  baselines.py.
- `20b9ff39b519` heater auto-push in bearings: LANDED 3b26e74 on a round-5
  clean pass (five rounds). Every bearings read now pushes unpushed local
  branches in every known checkout; HEATER_AUTOPUSH=0 turns it off; it
  pushed the taper fixer's in-progress commit on its first live run. The
  PC's next bearings run pushes the dickreuter branch.
- `ecc208e2d0d6` heater reconcile landing fixes (latest round decides; two
  consecutive wording-only rounds; empty branch never landed; merged branch
  told apart from never-started by the lease's base_sha), tip 79e31c2,
  worktree heater/5663ae84bf74. Round 2 FAIL: the already-in-trunk route
  has no heartbeat check, so a worker that pulled the trunk before its
  first commit loses its checkout. FIXER round 3 out (also adds `--reason`
  to land/reconcile --skip-review). Then a confirming round; land; tasks
  f16c56933d8a, dc8e3ac0bd7f, f0b91b86f69f done then. Pre-existing sibling
  filed as task b3b71f0512ac (worktrees.reclaim has no heartbeat check).
- `c79a35661f9c` heater usage taper (bands, pacing line, debrief page,
  opinion 14), tip 1d175b8, worktree heater/03a2b608f262. Seven rounds; the
  taper half was sound from round 4 and the status-line writer is verified
  against Claude Code 2.1.274; fixer 6 applied the four debrief-page
  findings plus tasks 001bbe019ca8 and 06e6e60bc3f7 (539 tests). REVIEWER
  round 7 (confirming, told to land on wording-only) is out. On pass:
  `bin/dispatch.py land c79a35661f9c --gate "bash bin/gate.sh"`, push,
  delete handover/findings-c79a35661f9c-* in the landing commit (or right
  after), delete the branch; tasks 32cbdf129bdf, ab4ea92fcb09,
  001bbe019ca8, 06e6e60bc3f7 done then. Then ~/.heater/usage.json appears on
  the next status-line render and bearings shows the five-hour figure and
  the pacing line: pace agents by it.

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

Session about $215 by `~/.heater/context.json`; 55 review rounds over 21
changes today; no round carries a dollar figure.
