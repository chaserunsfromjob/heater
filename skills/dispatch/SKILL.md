---
name: dispatch
description: Send one task to one worker, with a brief wrapped in the standing instructions. Use whenever the stoker needs code changed, since the stoker never builds anything itself.
---

# Dispatch

The stoker never builds. It sends a worker a brief and waits for a report.

## Before dispatching

Know what done looks like. A brief that cannot say when it is finished produces a
worker that either stops too early or never stops.

Take the task from the top of `bin/inbox.py tasks` unless something more urgent
arrived in the queue.

## Sending it

```sh
bin/dispatch.py open --task "..." --project api --done-when "..." \
  --task-id <id> --repo /path/to/project
```

This records the dispatch and prints the brief, already wrapped in
`roles/worker.md`. Hand that brief to the `worker` agent exactly as printed.

Pass `--repo` and every worker gets its own checkout on its own branch, first
one included. The project's own checkout is the consolidation target, never a
workspace: sharing it with a worker means the thing being merged into is the
thing being edited, and every clash between them becomes a decision somebody has
to make.

A checkout needs room on the disk. When too little is left, the dispatch is
refused rather than queued: reconcile first to hand the room back, and do not
lower the floor to get past it.

## Several workers on one task

```sh
bin/dispatch.py run --task "..." --repo /path/to/project --workers 2 \
  --part "the lexer" --part "the parser"
```

They share a run id and each gets its own checkout, so they cannot trample each
other. Give each a distinct part, or two workers will write the same code twice
and one of them will lose a merge for no reason.

One worker, one task. Two tasks in one brief produce a change nobody can review,
because the diff stops matching any single intent.

## While it is out

`bin/bearings.py` shows what is still owed and how long it has been quiet.

Do not ask a worker for progress. It reports when it is done or when it is
blocked, and a question mid-task costs a turn without changing the outcome.

## Consolidating

```sh
bin/dispatch.py reconcile --gate "<the project's gate command>"
```

Run this at the end of every wake and after any worker reports. It sweeps every
finished worker into the trunk and clears up behind them: merge the branch,
delete the branch, remove the checkout, free the slot, close the dispatch. When
every worker in a run has landed — or abandoned a branch it never committed on
— the run is reported finished and nothing of it is left anywhere.

It works out what to do by reading git rather than by trusting a flag, so it is
safe to run at any time and safe to run again after one is interrupted.

What it does with each case, without asking:

| Case | What happens |
| --- | --- |
| Work left uncommitted | Committed on the worker's own branch first. Loose work is the easiest to lose and the least worth refusing over. |
| The trunk moved while the worker was out | The trunk is merged into the worker's branch, then the landing is retried. |
| A real conflict | The branch, its checkout and its slot are all kept, and it is reported as needing a fixer. Dispatch one. |
| Nothing was done | The slot and branch are cleared away and the dispatch closes as `abandoned`. Nothing landed, so nothing may be counted as landed. |
| Not yet reviewed | Left alone and reported. Record the round; nothing lands unreviewed. |
| The trunk is dirty | Everything is held. The operator has uncommitted work there and mixing it in is not a call to make for them. |

The sweep exits 0 only when it finished everything it found. Work left for
somebody to answer — held, needing a fixer, or anything else it reports that is
not a landing, an abandoned empty branch or a worker still awaiting review —
exits 1, so a wake that reads the exit code alone still sees it.

Where the commits are already in the trunk, or the slot has gone back and git
shows the branch reached the trunk anyway, there is nothing to merge and the
dispatch closes as `landed` on the spot. Where the slot has gone back and the
branch still holds commits the trunk does not — a slot handed back by hand, or
reclaimed from a worker that never landed — nothing was abandoned and nothing
landed, so the dispatch closes as `failed`, the branch is named on screen, and
the sweep exits 1. A released slot whose branch or repository cannot be found,
or whose comparison against the trunk git could not answer, is reported the
same way: closed `failed`, named on screen, exit 1, because the point is to
stop guessing that work arrived. Every one of these closes says which review
state it rested on, so it can be checked afterwards rather than taken on trust.

Nothing is deleted until its commits are provably reachable from the trunk. That
check is the invariant the whole sweep rests on, and `finish` raises rather than
clean up a branch that has not landed.

## When one worker reports on its own

1. Read the report. The worker has committed on its branch; it has not merged.
2. Run the adversarial-review loop against the change. Never judge it yourself,
   and never accept the worker's own assessment that it is ready.
3. Record each round with `bin/store.py review --change <dispatch-id>`. Landing
   reads the store for a pass, so an unrecorded round did not happen.
4. Land it:

```sh
bin/dispatch.py land <id> --gate "<the project's gate command>"
```

Landing does the whole end of the cycle in one step: it merges the branch back
into the branch it was cut from, deletes the spent branch, removes the extra
checkout, frees the slot, and closes the dispatch as `landed`. A merge that
leaves the checkout behind and a checkout deleted before its merge are both ways
to lose work, so neither half happens alone.

It refuses, changing nothing, when there is no recorded review pass, when the
worker left uncommitted changes, when the gate does not exit 0, when the main
checkout is dirty or on the wrong branch, or when the merge conflicts. A
conflicting merge is aborted rather than left half-applied for someone to find.

`--skip-review` exists for a human who has read the change themselves. It is not
for getting past a review the loop has not finished. The sweep may carry it when
a reason is recorded, so a change a human has read is not stranded waiting for
rounds nobody is going to run. It never widens what the sweep may delete.

The sweep removes a checkout on three routes, and each asks a different
question first. A branch with nothing committed is removed only when its
dispatch is older than `EMPTY_BRANCH_STALE_HOURS` and the checkout has been
silent for `heartbeats.STALE_MINUTES`. A branch the trunk already contains is
removed only once the checkout has been silent for `heartbeats.STALE_MINUTES`.
A branch with commits to merge is removed once its review has ended, or, under
`--skip-review`, once the checkout has been silent for
`heartbeats.STALE_MINUTES`. That same half hour of silence also holds back the
two things the sweep does short of removing a checkout: committing what a
worker left loose, and `bin/worktrees.py reclaim` taking a slot back. A
recorded review pass is taken as the statement that the work is finished, so
a reviewed checkout is cleaned up on the next sweep even if a session is still
working in it: a reviewer or fixer dispatched into a worker's checkout should
expect that, and nobody should keep a reviewed checkout open expecting it to
survive.

## When it did not work out

```sh
bin/dispatch.py close <id> --outcome failed --note "..."
```

Outcomes are `landed`, `pushed`, `escalated`, `failed`, `abandoned`. Close it
even when it failed — an open record means a worker is still owed a reply, and
one left open makes every later bearings read wrong.

Closing frees the slot too, and refuses while the branch holds work that exists
nowhere else, recording why on the dispatch instead of destroying it. A close
whose slot is refused records `failed` rather than the outcome asked for when
that outcome was `landed` or `abandoned`, because both of those claim nothing
was left behind; the note names the branch that still holds the work. Every
sweep after that reports the slot under `left_behind` and exits 1 until the
branch is landed (`bin/dispatch.py land <id>`) or pushed
(`git push -u origin <branch>`).
