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

1. Read the report. The worker has pushed a branch; it has not merged.
2. Run the adversarial-review loop against the change. Never judge it yourself,
   and never accept the worker's own assessment that it is ready.
3. Take the merge once review passes, the suite is green, and the gate exits 0.
4. Close the record:

```sh
bin/dispatch.py close <id> --outcome pushed --note "..."
```

Outcomes are `pushed`, `escalated`, `failed`, `abandoned`. Close it even when it
failed — an open record means a worker is still owed a reply, and one left open
makes every later bearings read wrong.

Closing gives the slot back. It refuses while the branch still holds work that
exists nowhere else, and records why on the dispatch instead of destroying it.
Push the branch, then close again.
