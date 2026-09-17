---
name: adversarial-review
description: The per-change gate. Dispatch a fresh reviewer that judges a change against its intent and proves it runs, then a fixer for any findings, until two consecutive rounds find only wording, or one round for a document-only change. Run before landing any non-trivial change.
---

# Adversarial review

Nobody grades their own work. The worker that wrote a change does not review it,
and a reviewer that failed a change does not review the fix.

`rules/global.md` applies and is not repeated here.

## Route the change to its lenses

Pick the lenses before dispatching anything.

| Lens | When it runs |
| --- | --- |
| `default` | Always. |
| `failure-mode` | The change touches waiting, retrying, queueing, locking, or state shared between callers. |
| `environment` | CI will not exercise this. Paths, permissions, versions, installed binaries, clock, locale. |

## The loop

1. **Dispatch the default lens first**, as a fresh `reviewer`. One lens, one
   reviewer, one round.
2. **Record the round** with `bin/store.py review` the moment it returns, with
   its verdict, finding count, change size, and cost. A round that is not
   recorded did not happen, because the cost question is answered from the store.
3. **On fail**, dispatch a `fixer` with the findings. The fixer applies them,
   proves the suite, and commits. Then go back to step 1 with a **new**
   reviewer — never the one that failed it, and never the fixer.
4. **On pass**, dispatch the remaining lenses, one at a time, each a fresh
   reviewer. A lens that fails sends the change back to step 3.

Dispatching every lens at once wastes a fixer round: the default lens finds the
problems that make the other lenses moot.

## When review ends

Review ends when **two consecutive rounds find only wording** — or, for a
**document-only change**, on the **first** such round.

A change is document-only when every path in `git diff --name-only <trunk>...HEAD`
ends `.md` or `.txt` or sits under `handover/` or `research/results/`. The stoker
applies that round's wording findings itself and lands; it does not send a
document out again. `bin/dispatch.py land` reads the diff and enforces both counts.

For everything else, run one final round. Record its wording findings as
observations rather than findings, and land on its pass. A third round of commas
is the loop failing to stop, not diligence.

The reviewer states whether its findings are wording-only. Never infer it from
the finding count.

## What a reviewer cannot pass

These are in `agents/reviewer.md` and bind every round:

- A change that quietly settles a design decision the project has not recorded.
- An irreversible path with no behavioral test and no verified undo path.
- A number in a decision, report, or brief that no store can produce.

## Landing

Three things, and nothing else:

- A fresh independent review pass.
- A green full suite.
- Exit 0 from the project's own gate script.

It lands at any hour. No operator approval.

## Cost

Escalate rather than continue when a change exceeds its cost budget. Read the
current state with `bin/store.py query --days 7` before claiming review is or is
not expensive; the answer is a query, not an impression.
