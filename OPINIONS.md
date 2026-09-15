# Opinions

**Dated 2026-09-15. Only the operator edits this file.**

These are positions on direction, not rules. Rules are terse and imperative and
live in `rules/`. This file is allowed to argue with itself, carry reasons, and
be wrong in a way a rule may not be.

When a rule conflicts with an opinion here, the rule is rewritten. When an agent
cannot tell whether a change fits, it reads this file — not a note someone left
in a comment last month.

---

## 1. Zero operator input

The system may ask me a question once. It may never ask me the same question
twice.

Every answer I give is written down as a principle here or as a rule in
`rules/`, so the question cannot recur. A repeat question is a defect in the
recording, not a reasonable request for guidance.

Measure the system by how rarely it needs me.

## 2. The stoker is the center

Every change to every repository goes through the stoker. Anything that touches
a repo without going through it is a defect.

This includes me. My own hand-written commits are defects. I accept being
flagged by my own guard, because the moment the stoker's picture of the world
can be wrong, every decision it makes downstream is guesswork.

## 3. Fix failures after they happen

A defect that actually hit gets a reproduction, a failing test, and a fix. A
defect somebody imagined gets dismissed, and the dismissal reason is recorded so
the next agent does not raise it again.

Imagining failures is infinite. Acting on every imagined one fills the codebase
with guards nobody remembers the reason for and nobody dares delete.

Four exceptions may be hardened before they ever occur:

- Anything that would halt the whole fleet.
- Anything that would leak a secret.
- Anything that would destroy unrecoverable work.
- Anything a reviewer judges likely to fail, stated as a specific scenario.

The fourth is deliberately looser than the others. It is a bet that a reviewer
reading real code is a better predictor than a rule. Revisit it if speculative
guards start accumulating.

## 4. Decisions are data-backed

A number in a decision, a report, or a brief comes from a live query against a
store, run at the moment of writing, stamped with when it ran. A number typed
into a file is stale the next day.

If a number cannot be pulled from a store, that is a hole in collection. The
hole is the task. Do not estimate around it.

## 5. Nothing accumulates silently

The task list has a hard cap and a rank. The top is always being worked. What
falls off the bottom is deleted, not archived.

If something deleted actually mattered, it will come back on its own. Everything
kept "just in case" is a list nobody reads, which is worse than no list.

## 6. Reversibility bounds damage

An agent may take an irreversible-looking action while I am asleep if it can
state exactly how to reverse it and has proven the reversal works. A behavioral
test of the undo path, not a green suite.

An action with no real undo path stops and escalates. This is the one place I
accept work stalling overnight, because the alternative is waking up to damage I
cannot undo either.

A stated, verified undo path beats a human hold. A human hold beats no undo path
at all.

## 7. Cost is a first-class constraint

Every session and every review round records what it cost and how large the
change was. A change that exceeds its budget escalates rather than quietly
burning through the afternoon.

"Review is eating the week" must be a query I can run, not a feeling I have.

## 8. A rule lives in exactly one place

Each rule belongs in exactly one file, at the lowest tier that still reaches
everyone who acts on it. A rule restated for emphasis is a defect and the suite
fails it.

Two copies drift. Once they drift, some agent is following the stale one, and
nobody knows which.

## 9. Explanations are part of the work

I am not a programmer. I have very little computing background. An explanation I
cannot follow is a failed deliverable, exactly like a failing test.

Explain in everyday words first. Name the technical term afterwards, so I pick up
the vocabulary over time instead of being blocked by it on the way in.

Lead a decision with a recommendation and a reason. Never hand me a choice
between options I have not been given the words to compare — that is not
consulting me, it is stalling.

This does not loosen opinion 1. Zero operator input governs work the system does
while I am away: it must not wake me to decide things. This opinion governs the
conversation when I am here and asking. Asking whether an explanation landed is
not the kind of question opinion 1 is trying to eliminate.

---

## Scope of this build

`heater` is the fleet repository: the canonical home of the rules, roles, hooks,
skills, and stores. Machines receive them by symlink from this repo.

The orchestrator is the **stoker**. It dispatches, judges, and merges. It never
builds anything itself.
