# Handover

<!-- handover-commit: e49643c -->

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
  83, verbatim in OPINIONS.md opinion 14). The meter is live since
  b46a010: at 05:55Z it read weekly 80% used with 4 days left (resets Mon
  21 Sep 01:00 EDT), five-hour 40% used and slightly ahead of an even
  spread, band TOP_OF_LIST_ONLY (at most 3 agents). The WEEKLY figure is
  the binding one: at 80% with four days to go, keep to two or three agents
  on top-of-list work and read `bin/bearings.py` "Plan usage" before every
  dispatch.

## Where things stand

pokerbot main is at 6c40f4f: T1 the table (PR #11), T2 the first bot (PR #15), T3 the scoreboard (PR #16) and the Stage 2 measurement (PR #17) all landed tonight. The MORNING REPORT is queued (d9e05d4e4a29, 05:43Z): deliver it, do not write another.
Also landed tonight: OVERNIGHT.md + issue #13; bin/gate.sh (the pokerbot
land gate is now `bash bin/gate.sh`); DECISION_LAYER_BLUEPRINT.md. Rohit's
assistant has not started (no PR, codex/tonight unchanged at ca8339e).

One agent is out: the REVIEWER (round 1) for `b68dd506e0ee`, Stage 3 the
notebook, PR #22, tip 188b384, worktree pokerbot/2b7e5f5ce175. Built in
well under the planned 12-18 h: 2,781 lines, 58 tests (333 on the
branch), section 4.5's worked report reproduced character for character.
Two readings to settle at landing: PRIOR_STRENGTH per tier (50/25/15, as
section 4.3's table says) and the walk counting as a vpip opportunity
(Table C's reading against section 4.7's row; escalation 241e2f235c94 in
the queue, a design judgement the stoker may settle if the reviewer's
reading is clear). On the report: fixer, confirming round, land with
`bash bin/gate.sh`.
Everything dispatched before it has landed; reconcile at 08:00Z reported
nothing open. pokerbot main is at c5ed759: CLAUDE.md has a
"Firm requirements" section (2-9 players, true no-limit, exploitative play
keyed to the named player), and every document now quotes the current goal
line (PRs #19, #20, #21). heater main is at 895c954 or later.

Next work when the band allows (weekly 82% at 07:45Z, four days left): read
`bin/inbox.py tasks` and take the top actionable one. The top item, the
dickreuter PC push, cannot be done from the Mac. Below it are fleet
reporting-texture tasks (41-48) and one-line document staleness (36); none
is worth the weekly budget tonight. Stage 3 is out; Stage 4 (the bot that
plays the person) follows it and is what addresses the losses to nit and
tag; brief it from BUILD_PLAN.md once Stage 3 lands.

- `6e3f3af1ef5c` heater sweep/store truthfulness: LANDED 87f9569 (round 1
  fail, round 2 pass, two wording items by the session). The sweep's exit
  code is read off the whole report (unknown keys exit 1); a released slot
  with commits off the trunk closes `failed` and is named under
  `left_behind`; an empty branch given up on closes `abandoned`; the
  store's landed figure is judged on full history via tools/reviewloop.py
  (was 19, is 5, agrees with dispatch.reviewed). Tasks 68b249e08219,
  3259f1e2808e, 917775c34006 done; ee0851c19f8f, bc471f09618e filed.

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
- `c79a35661f9c` heater usage taper: LANDED b46a010 after eight rounds
  (reasoned --skip-review override recorded in the dispatch note). bearings
  now prints "Plan usage" (five-hour and weekly bands, a pacing line) once
  the status line has written ~/.heater/usage.json, which happens on its
  next render in an interactive session; until then it says so. At the
  five-hour 95% band: stop every agent and `bin/debrief.py --hours 5
  --queue`. Opinion 14 in OPINIONS.md carries the operator's words. Tasks
  32cbdf129bdf, ab4ea92fcb09, 001bbe019ca8, 06e6e60bc3f7, 62a5a521a2f4 done.
  Findings files r3-r5 deleted.
- `ced8b534b39b` heater live-worker hazards: LANDED 1ae176d (round 1 fail
  on a reclassification that made reconcile exit 1 with any worker out,
  fixed; round 2 pass, one rename by the session). tools/heartbeats.py now
  owns the 30-minute silence rule; reclaim and autosave both ask it. Tasks
  b3b71f0512ac, d80c47c137ae done; 999e3bf36821 filed (kept live worker
  shows as a bare id in awaiting_review).
- `9d68697caeb0` Stage 2 first measurement: LANDED 6c40f4f (PR #17,
  squash-merged because one intermediate commit did not import). The
  scoreboard header now prints a deviation line whenever `--hands` differs
  from the pre-registered 1,000. Result, in the README and in
  research/results/stage2_search_vs_personas.txt: ACCEPT vs always_call
  (+2368 bb/100 [+2028, +2692]); the bot beats 7 of 13, LOSES to nit and
  tag, too close to call vs 4. The morning report (queue d9e05d4e4a29) was
  amended at 06:45Z to carry this. Tasks d077f18909a7, 6805b01c7bd2 done.

Next work, in order, when the usage band allows (weekly was 81% at 06:30Z
with four days left: two agents at most, top of list only): (1) Stage 2
proper: the bot loses to nit and tag; BUILD_PLAN.md Stage 3/4 (the notebook
and the opponent model) is what addresses that, and the persona league is
the measurement; (2) d67cffad749a (jsonstore.REPO resolves
to the worktree; widen to the stores). D1/D2 remain the operator's.

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
  fix (auto-push five rounds, taper eight). Scope each fixer brief to the
  finding and each reviewer brief to "confirm the fix, say if wording
  only". Main's `land` now refuses without two consecutive wording-only
  passes; `--skip-review --reason "..."` is the override and the note
  records the reason.
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

Session about $320 by `~/.heater/context.json`; 55 review rounds over 21
changes today; no round carries a dollar figure.
