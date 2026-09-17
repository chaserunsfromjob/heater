# Handover

<!-- handover-commit: dd9f533 -->

Written on `main`, 2026-09-17 about 17:50Z, on the Mac, at 35% context, the
operator clearing the session with one reviewer still out. Verify with `bin/handover.py`. A snapshot, not a log;
rewrite, do not append.

Read `README.md` for what is built, `OPINIONS.md` for the operator's
positions, `rules/` for the rules, pokerbot's `BUILD_PLAN.md` (landed today
at c8450db) for the stages and the operator's 17 September decisions, and
the commit messages for why. None of that is repeated here.

## What is in flight

- `e6dfe622fa6f` heater, the one-round rule for document-only changes
  (branch worker/e6dfe622fa6f @ bbf5ae9, checkout
  `~/.heater/worktrees/heater/dc76881cb2a5`, dispatch OPEN so `land` works).
  Reviewer round 1 (dispatch 347bdc7cae6a) was OUT when the operator
  cleared this session, so its report is LOST: no round 1 is recorded in
  the store for e6dfe622fa6f. First: `bin/dispatch.py close 347bdc7cae6a
  --outcome abandoned`, then dispatch round 1 afresh, the reviewer reading
  in that same checkout (no new lease; see Traps). Code change: two
  consecutive wording-only rounds. On pass: record with `bin/store.py
  review`, close the reviewer's dispatch, dispatch round 2 the same way; on
  two passes `bin/dispatch.py land e6dfe622fa6f --gate "bash bin/gate.sh"`,
  then `git push origin main`. On fail: fixer in the same checkout, then a
  fresh round 1. The worker's own report: tests written first (4 errors),
  then 74/74; full suite 670 OK; gate exit 0; it filed that `reconcile`
  still applies two rounds to documents (task at 50) and that opinion 13
  still says two (task at 47).
- Nothing else is out. Every pokerbot slot is released; `bin/worktrees.py
  list` should show only dc76881cb2a5.

## The next session's first job: the GTO Wizard answer key

The operator asked (17:30Z) to "get the GTO wizard part out of the way" now,
offering about 6% of the weekly meter. Agreed shape, told to the operator:
NOT the bot-spot checks (the baseline they test does not exist until Stage
4), but a PRE-REGISTERED preflop answer key so Stage 4's solver is graded
blind. Cap it at 4 points of the weekly meter (reads 89% at 17:29Z, resets
Mon 21 Sep 01:00 EDT); re-read `bin/bearings.py` "Plan usage" every 25
spots and stop at the cap.

Protocol, to write into the record file's header before the first spot:
- Site: app.gtowizard.com, already signed in in the operator's Chrome (tier
  NLH Cash Ultra; the stoker has the Chrome tools, workers do not). Use the
  Study library, cash, the seat counts the scoreboard weights: 2, 6, 8, 9.
  Prefer 200bb depth to match the table; if the library only has 100bb, say
  so in the header and use it. Record the exact solution set, rake and open
  size shown on screen.
- Spots: (1) first-in opening decision from every position at each seat
  count (25 spots); (2) big blind facing each position's open (about 22);
  (3) if the cap allows, small blind facing each open. For each spot record:
  the action frequencies shown (raise/call/fold %) and the range as text
  (the site copies a range as text by hand; paste it).
- Record file: pokerbot `research/results/theory_agreement/reference_preflop_2026-09-17.md`
  on a branch, opened as a draft PR, landed as a document-only change on one
  round. Nothing from it goes into the bot's tables; it is the answer key
  Stage 4's `bench`/harness compares against (queue 5a468f29fdf6 describes the
  harness; it is not built).
- Our menu is fchpa (half pot, pot, all-in), theirs is 2.5bb-style opens; the
  harness maps sizes (ACTION_TRANSLATION.md §7). Record theirs as shown; do
  not translate by hand.

## Traps found today, all costly

- NEVER `git checkout -B <worker branch>` inside a lease made for another
  dispatch. Leases are git worktrees of one repo; the branch ref becomes
  shared, and `worktrees.autosave` (run by reconcile AND bearings) commits
  every stale tree as "Autosave uncommitted work" onto the shared branch,
  and bearings' auto-push pushes it. Six such commits sit in
  worker/0a62853153e4's history (net content unchanged, verified by diff).
  Task f642286f63f2 is the fix. Until then: a reviewer or fixer on an
  existing branch reads the WORKER's own checkout (keep the worker's
  dispatch open), or a detached worktree in the scratchpad made with
  `git -C <repo> worktree add --detach <scratchpad path> origin/<branch>`
  and removed after with `git worktree remove --force`.
- Closing a dispatch `--outcome pushed` releases its slot and DELETES its
  checkout; `land` then cannot find a lease and the merge is by hand. Keep
  the worker's dispatch open until `land`.
- `bin/dispatch.py land` only works for a dispatch opened on this machine
  with a lease; a branch built on the PC (dickreuter) was landed by hand:
  `git merge --no-ff origin/<branch>` in `~/pokerbot` on main, gate, push,
  `git branch -r --contains` then `git push origin --delete <branch>`.
- `land` does not push pokerbot main; push it. The branch-protection
  message "Bypassed rule violations" is normal for the owner.
- `bin/store.py review` refuses `--verdict pass` with findings > 0 unless
  `--wording-only`; a pass-on-substance with one small fact slip is
  recorded as fail with the reasoning in --note, then landed
  `--skip-review --reason`. Done twice today (dickreuter r3, plan update r1).
- `work_at_risk` keys on the lease's own branch name; a checkout on another
  branch reads as unique work and needs `bin/worktrees.py release --force`
  after verifying HEAD is on origin or in main (task dff118e56feb).
- The task list cap (20) dropped six low items today; nothing about the bot.
- The auto-mode safety classifier timed out once (17:20Z) and blocked Bash
  for a minute; read-only tools kept working. Retry, do not reroute.

## Decisions the operator made today, all recorded verbatim in the queue

Baseline before exploitation (5333609531ed); search is the bot, thinking
before interfacing (548e5cdfe607); equilibrium baseline, "somewhat similar
to theory" postflop (6fe7874ab357, ecc3ee41979c); GTO Wizard checks, no
cap, standing browser permission (5a468f29fdf6); D2 answered: phone app
mirrored into a phone-shaped column on the right of the Mac (8513859a2c49);
final deliverable an installable Mac app (f2c5f8524add); one review round
for documents (385a5a2b3b24, in flight above). All but the last are now in
BUILD_PLAN.md. Stage 4 (the solved preflop baseline) is the top task on
the list at score 72 (from finding 5333609531ed); do NOT start it before
the Monday reset (11 points left this week; the operator was told this).

## Other state only this session knows

- Daniel-Shiven invited to pokerbot with write access 17:0xZ, pending.
- `git config --global user.name/email` set on this Mac to the GitHub
  noreply identity; the PC still needs the two lines (README says them).
- The operator's app and mirroring method are still unnamed; they said it
  does not matter yet.
- The operator narrowed dickreuter at 17:48Z: "dont base the whole project
  off of it"; it is context for screen capture only. Task f2ff0c6cbe23 is
  rescored to 30 and reduced to checking that CLAUDE.md says just that.
  Never describe the project as based on dickreuter.
- The operator's order of jobs for the next session: (1) the GTO Wizard
  answer key above, (2) finish landing e6dfe622fa6f, (3) nothing new until
  the Monday reset.
- The reviewer for the plan update ran with the safety classifier down; its
  four fact findings were each re-verified by the stoker before applying.

## Cost

Session about $60 by `~/.heater/context.json`; 11 review rounds over 4
changes today (3 landed: dickreuter bf148db, bench 4bb7daf, plan c8450db);
no round carries a dollar figure (task 3919e7a17ec6). Weekly meter 84% at
13:47Z, 89% at 17:29Z.
