# Findings inbox

A worker that notices something off-task never fixes it and never drops it. It
files a one-line finding and moves on. The stoker judges each one.

Findings themselves live in the queue store, not here. Keeping a second copy
would mean two records of one finding that could disagree; this directory holds
only what survives the judgement.

```
bin/inbox.py check --summary "..."    # already judged? exit 1 means do not file
bin/inbox.py list                     # findings waiting to be judged
bin/inbox.py dismiss <id> --reason    # most findings end here
bin/inbox.py promote <id> --score 70  # onto the task list
bin/inbox.py tasks                    # the ranked list
bin/inbox.py done <task-id>
```

## Why a dismissal needs a reason

The reason is the whole mechanism. `check` compares a proposed finding against
everything already dismissed and refuses a restatement, so the same observation
is judged once rather than every time a fresh worker reads that file. A
dismissal with no reason teaches nothing and the next worker files it again.

## The cap

`tasks/` holds at most `TASK_CAP` open tasks, ranked by score. Promoting past
the cap deletes the lowest-ranked task outright — no archive, no "deferred"
folder. If something deleted actually mattered, it comes back on its own.
Anything kept just in case becomes a list nobody reads, which is worse than no
list at all.
