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

Pass `--repo` and the checkout is decided for you. The first worker on a project
uses the project's own directory. A second worker while the first is still out
would trample it, so it is given its own checkout on its own branch, and the
brief tells it where to work. Nobody provisions anything, and nobody is asked
whether a pool is needed.

Slots are capped per project. When every slot is held, the dispatch is refused
rather than queued: wait for a worker to push, and do not raise the cap to get
past it.

One worker, one task. Two tasks in one brief produce a change nobody can review,
because the diff stops matching any single intent.

## While it is out

`bin/bearings.py` shows what is still owed and how long it has been quiet.

Do not ask a worker for progress. It reports when it is done or when it is
blocked, and a question mid-task costs a turn without changing the outcome.

## When it reports

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
