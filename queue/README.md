# Fleet queue

Notes waiting for the stoker. One JSON file per item, written by
`bin/queue.py add` and read by the Stop hook at a turn boundary.

```json
{
  "id": "2785d14e85a8",
  "created": "2026-09-15T02:10:54.123456+00:00",
  "kind": "finding | escalation | report | failure",
  "urgency": "low | normal | high",
  "project": "api",
  "path": "src/parse.py",
  "origin": "worker",
  "summary": "one line, no more",
  "delivered_at": null
}
```

`delivered_at` is stamped when the Stop hook wakes the stoker with the item. It
is never deleted on delivery, so the queue keeps a record of what was raised and
when it was seen. The stoker resolves items by dismissing or promoting them.

A directory of files is the smallest thing that works. Items are tracked in git
so a queue is readable in a diff. If several machines start filing items at once
and merge conflicts become routine, that is the signal to move the queue to a
per-machine directory synced by the SessionEnd hook — not a reason to add a
database.
