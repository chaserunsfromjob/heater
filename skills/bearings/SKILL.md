---
name: bearings
description: One read that says where everything stands. Run it first after a night away, when picking up an unfamiliar fleet, and before deciding anything that depends on current state.
---

# Bearings

```sh
bin/bearings.py
```

Exit 0 means nothing is waiting. Exit 1 means something is.

Every figure comes from a live query at the moment it runs. Nothing here is
maintained by hand, so nothing here can be stale in the way a status file is.

## Reading it

| Section | What a number here means |
| --- | --- |
| Fleet | Queue items nobody has been woken for, findings nobody has judged, and the top of the task list. |
| Dispatches out | Workers still owed a report. `<- quiet` marks one out longer than the stale threshold. |
| Heartbeats | The last tool call each live session made. `<- may be dead` means silence, which is not the same as finished. |
| This machine | Whether this machine's links and hooks match the repository. |
| Pushed | Branches that existed on this machine only and have now been sent to `origin`. The read pushes, on every machine, by default, `main` included; it never forces, and a push origin refuses is reported and left alone. `HEATER_AUTOPUSH=0` turns the sweep off and `HEATER_AUTOPUSH_DEADLINE` caps how long it may take. |
| Fleet repository | Uncommitted and unpushed fleet state. |
| Review load | Rounds per change and cost over seven days. |

## Quiet is not dead, and neither is finished

A quiet dispatch means no tool call has returned recently. It may be thinking,
it may be waiting on something, or it may have died. Bearings will not tell you
which. Read the heartbeat beside it, then look at the branch it was working.

## What to do with it

Work the fleet section first: an unjudged finding blocks nothing but accumulates,
and an undelivered queue item means something asked for attention and did not get
it. Then the task list. Machine drift is fixed with `bin/deploy.py` and is never
a reason to delay other work.
