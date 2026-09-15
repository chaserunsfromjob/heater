---
name: handover
description: End a session safely and hand the work to the next one. Run before clearing context, before a long break, or whenever a session has grown long. Writes HANDOVER.md carrying only what the next session cannot look up for itself.
---

# Handover

Context is disposable in proportion to how much of it was written down. This
procedure writes the rest down, then proves the session is safe to end.

Run `bin/handover.py` to check. Exit 0 means safe to end.

## It starts on its own

Nobody watches a percentage. The status line records how full the context window
is, the Stop hook reads that, and past the threshold it refuses to let the turn
end quietly and says to hand over now. Work this instruction before anything
else: it names exactly what is outstanding.

Context usage is read from the transcript, which every hook is handed a path to,
so this works in a terminal and in a web session alike. The status line is a
second source where it runs: it knows the exact window size, which the transcript
does not carry.

There are two marks, not one, because being cut off mid-task costs the work
twice and no cost model shows that.

| Context | What happens |
| --- | --- |
| Below 30% | Nothing. |
| 30% to 45% — **armed** | Hand over at the next clean boundary. While work is in flight it says so once, then waits. Finish what you are doing; start nothing new. |
| Above 45% — **ceiling** | Discretion is over. Park what is in flight, commit it, name it unfinished in the note, and hand over. |

Being mid-task has an objective signature: changes not committed, commits not
pushed, or a worker still owed a reply. At a boundary all three are clear, which
is exactly when a fresh session can pick up from the repository alone.

Move either mark with `HEATER_HANDOVER_AT` and `HEATER_HANDOVER_CEILING`. A
ceiling set below the arming mark is clamped, because that would force a
handover the instant one is armed.

Cost per turn of real work bottoms out around 25% before the curve flattens.
Every tool call re-sends the whole conversation, not just every message, so the
bill grows with context far faster than the message count suggests.

The mark sits at 30% rather than 25% because a session is already near 10%
before the operator has said anything: the system prompt, the tool definitions
and `CLAUDE.md` all arrive first. The mark is measured against total usage, so
that floor is a toll paid before any working room is counted, and 25% left
about fifteen points of it rather than twenty-five.

Reaching compaction means this failed. The `PreCompact` hook leaves a mark, and
the next session is told its memory was edited by a machine and to write a
handover immediately.

## The end of it is automatic too

Nothing can clear the conversation from inside it: hook output cannot send input
into a session, and nothing may type into a terminal. So the ending happens one
level up. `bin/stoker.sh` is not a launcher that exits; it supervises. It starts
`claude` as its child and watches for a marker file.

Once the Stop hook has proved the handover is written, current and pushed, it
leaves that marker. The supervisor sees it, ends this session, removes the
marker, and starts a fresh session in the same folder, with the same role and
the same Remote Control name. The operator types nothing at any point, and the
new session opens on `HANDOVER.md`.

Stopping the stoker is still the operator's: `/exit` or Ctrl-C ends the session
without a marker, and the supervisor exits with it rather than reopening.

## A handed-over session is spent

Its notes are written and pushed, so everything it knew is now in the
repository. Leaving it open invites the operator back into a conversation that
has already said goodbye, and invites a second session editing the same files.

So archive it as the last act, where the session can be archived: a session
running in the cloud has an archive action, which turns it read-only and
releases its container. A terminal session under `bin/stoker.sh` has no
equivalent and needs none: the supervisor ends the process, which is the end of
it.

Archive only after the handover commit is pushed. An archived session cannot go
back and finish.

## Do not open the next session from this one

The successor is opened from outside, by the supervisor, never from in here. It
is tempting to seed one before archiving, so the work looks continuous. Do not.
A session created from inside another one arrives with no checkout: the
repository is named on its record, but nothing is on its disk, so it is never
filed under the project and never appears where the operator looks for it. It
also starts by re-cloning, which is work the operator watches instead of the
work they asked for.

The guard denies the session-creating tool for that reason, and the denial
stands whatever the handoff costs in continuity. Leave the successor to
`bin/stoker.sh`, which opens it in this same folder, with this same checkout.

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
6. Commit the handover and push it. The next turn's Stop hook sees a clean
   check, leaves the marker, and the session ends on its own from there.
7. Archive the session, if this session can be archived. Do not open the next
   one from here; `bin/stoker.sh` opens it.

## Writing it

Write for a competent stranger who has the repository and none of the
conversation. Lead with where things stand and what to do next. Keep it under
150 lines: a handover nobody reads is the same as no handover.

Delete the previous handover's content rather than appending to it. This file is
a snapshot, not a log. The log is the commit history.
