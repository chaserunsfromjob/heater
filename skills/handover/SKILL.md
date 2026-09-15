---
name: handover
description: End a session safely and hand the work to the next one. Run before clearing context, before a long break, or whenever a session has grown long. Writes HANDOVER.md carrying only what the next session cannot look up for itself.
---

# Handover

Context is disposable in proportion to how much of it was written down. This
procedure writes the rest down, then proves the session is safe to end.

Run `bin/handover.py` to check. Exit 0 means safe to clear.

## It starts on its own

Nobody watches a percentage. The status line records how full the context window
is, the Stop hook reads that, and past the threshold it refuses to let the turn
end quietly and says to hand over now. Work this instruction before anything
else: it names exactly what is outstanding.

Hooks are never told the context size, so the status line is the only source.
`bin/deploy.py --check` reports a missing or foreign status line as drift,
because without it this never fires.

The threshold is 55%, well below the point where the conversation is summarised
automatically. Set `HEATER_HANDOVER_AT` to move it. Later is worse than it
sounds: automatic summarising keeps whatever it judges important, and nobody
chooses what it drops.

Reaching compaction means this failed. The `PreCompact` hook leaves a mark, and
the next session is told its memory was edited by a machine and to write a
handover immediately.

## The one part that is not automatic

Nothing can clear the conversation for you. Hook output cannot send input into a
session, so the last step is a person typing `/clear`. Everything before it —
noticing, writing, committing, pushing, verifying — happens without being asked.

## What the next session can look up, and must not be told again

- What the code does. It reads the code.
- What the rules are. It reads `rules/`.
- What the operator's positions are. It reads `OPINIONS.md`.
- What changed and why. It reads the commit messages.
- What is built and what is next. It reads the build order in `README.md`.

Repeating any of this wastes the handover and drifts from the source. Opinion 8
applies to handover notes as much as to rules.

## What only this session knows, and must write down

- An approach that was tried and abandoned, and the reason it failed. Without
  this the next session tries it again, because it looks reasonable on paper.
- A decision that a file records the outcome of but not the alternatives.
- A tension between two rules or two opinions, and how it was resolved.
- A trap: something that looks wrong and is deliberate, or looks safe and is not.
- Work that is genuinely in flight, with the next concrete action.

## Procedure

1. Run the gate. A handover written over a red suite hands over a broken repo.
2. Commit and push everything. Unpushed work does not survive a cleared session.
3. Write `HANDOVER.md` from the second list above, and nothing from the first.
4. Stamp it with the commit it describes, so a later reader can tell it is stale.
5. Run `bin/handover.py`. Fix whatever it names.
6. Commit the handover. Only then clear.

## Writing it

Write for a competent stranger who has the repository and none of the
conversation. Lead with where things stand and what to do next. Keep it under
150 lines: a handover nobody reads is the same as no handover.

Delete the previous handover's content rather than appending to it. This file is
a snapshot, not a log. The log is the commit history.
