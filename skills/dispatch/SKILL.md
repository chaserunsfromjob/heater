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
every worker in a run has landed and every one of them put its work in the trunk
or had none to put there, the run is reported fully consolidated and nothing of
it is left anywhere.

It works out what to do by reading git rather than by trusting a flag, so it is
safe to run at any time and safe to run again after one is interrupted.

What it does with each case, without asking:

| Case | What happens |
| --- | --- |
| Work left uncommitted | Committed on the worker's own branch first. Loose work is the easiest to lose and the least worth refusing over. |
| The trunk moved while the worker was out | The trunk is merged into the worker's branch, then the landing is retried. |
| A real conflict | The branch, its checkout and its slot are all kept, and it is reported as needing a fixer. Dispatch one. |
| Nothing was done | The slot and branch are cleared away, and the sweep reports it as closed with nothing to consolidate rather than as work that reached the trunk. |
| The slot went back with its work unmerged | Reported as commits left on the named branch. The branch still holds the work, so the sweep does not say it cleaned up after it. |
| Git cannot say where the commits went | Reported as could not check, never as nothing to consolidate. An unanswered question and an empty branch look identical in silence. |
| Not yet reviewed | Left alone and listed as awaiting review, with its branch. Record a round; nothing lands unreviewed. |
| The last review round failed | Left alone and reported as needing a fixer, naming the branch, the round and its review id. Only the highest round counts, so an earlier pass does not rescue it. |
| A dispatch closes with no passing round | The alarm rides whichever line its commit state prints: landed WITHOUT a passing review for work in the trunk, and the failed round appended to the left-on-a-branch and could-not-check lines. A worker that did nothing raises none. |
| Every worker in a run has closed | The run reads fully consolidated only when every member's commits reached the trunk or never existed. Anything else — left on a branch, unchecked, or never recorded — lists the run under work still to account for. |
| The trunk is dirty | Everything is held. The operator has uncommitted work there and mixing it in is not a call to make for them. |

Nothing is deleted until its commits are provably reachable from the trunk. That
check is the invariant the whole sweep rests on, and `finish` raises rather than
clean up a branch that has not landed.

## When one worker reports on its own

1. Read the report. The worker has committed on its branch; it has not merged.
2. Run the adversarial-review loop against the change. Never judge it yourself,
   and never accept the worker's own assessment that it is ready.
3. Record each round with `bin/store.py review --change <dispatch-id>`. Landing
   reads the store for the highest round number recorded against the change, so
   an unrecorded round did not happen, and writing round 1 down after round 2
   does not make round 1 the answer. When two rounds share a number, the one
   recorded later is the one that stands. When they share the recorded time as
   well, the fail stands, so which file happens to load first never decides
   whether work merges. A round number that is not a whole number — missing,
   written as text, or a decimal — cannot be placed against the others, so it
   never counts as a pass and it blocks landing whatever its verdict says.
4. Land it:

```sh
bin/dispatch.py land <id> --gate "<the project's gate command>"
```

Landing does the whole end of the cycle in one step: it merges the branch back
into the branch it was cut from, deletes the spent branch, removes the extra
checkout, frees the slot, and closes the dispatch as `landed`. A merge that
leaves the checkout behind and a checkout deleted before its merge are both ways
to lose work, so neither half happens alone.

It refuses, changing nothing, when the highest recorded review round is not a
pass, when the worker left uncommitted changes, when the gate does not exit 0,
when the main checkout is dirty or on the wrong branch, or when the merge
conflicts. A change that passed round 1 and failed round 2 is refused: the
highest round counts, and an earlier pass describes a change that no longer exists.
The refusal names the round it read. A conflicting merge is aborted rather than
left half-applied for someone to find.

`--skip-review` exists for a human who has read the change themselves. It is not
for getting past a review the loop has not finished.

## When it did not work out

```sh
bin/dispatch.py close <id> --outcome failed --note "..."
```

Outcomes are `landed`, `pushed`, `escalated`, `failed`, `abandoned`. Close it
even when it failed — an open record means a worker is still owed a reply, and
one left open makes every later bearings read wrong.

Closing frees the slot too, and refuses while the branch holds work that exists
nowhere else, recording why on the dispatch instead of destroying it.
