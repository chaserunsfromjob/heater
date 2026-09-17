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

## 10. Report the outcome, not the making of it

Tell me what changed and whether it works. Do not walk me through how it was
built, what went wrong on the way, or what was fixed before I ever saw it.

A defect found and fixed inside the same piece of work is not news. It is the
work. Narrating it turns me into a reviewer of your process, which is the job I
am specifically trying not to have.

The record of how something was made belongs in the commit message and the
handover note, where it is available if anyone ever needs it and invisible if
nobody does.

Raise something only when it changes a decision I have to make: a real
trade-off, a cost I am carrying, a thing I asked for that cannot be done.

## 11. No fixed limit on concurrent workers

I don't want a fixed number of workers capped in advance. Judge each dispatch on
whether the work is worth doing and whether the machine can actually carry it —
real resources, disk space above all — not against an arbitrary headcount.

The stoker doesn't raise or remove a cap on its own just to get past being
blocked. It waits, or it asks. I decide that one.

## 12. Full access beats menial labor

The operator, 2026-09-17, in their own words:

> i really dont like all this going back and forth and having to type in the
> terminal and everything. i created this system so i didnt have to work too
> hard to communicate to it. i would be willing to give the system and claude
> full access to my computer or any permissions it would need so that i dont
> have to do all of this menial labor.

What the fleet does: `permissions.defaultMode` is `bypassPermissions` in
`~/.claude/settings.json`, a session never asks the operator to type a command,
work another machine must do is queued for that machine's next wake, and
sessions push their own unpushed work on waking (change 20b9ff39b519, in
review).

## 13. Streamlined beats perfect

The operator, 2026-09-17, in their own words:

> this should be pretty streamlined so please pick up the pace, and at your
> discretion dont get too into the weeds on things. we dont need perfection
> here, just something that we know is beating real players

What the fleet does: a research document takes the round count opinion 15 sets,
the stoker applies small findings itself and records why in the store note, and
code still gets a fresh reviewer round.

## 14. Taper as the limits approach

> "as we get closer to both running out of 5 hour usage and weekly usage, i want
> to implement running less agents and using less usage more and more as we
> approach the limit. therefore, as we get closer, we should cut agents that are
> working on things that are not as important, and prioritize more important
> tasks at your discretion"

> "lets get it into my system about tapering off the usage as we get closer. you
> can use /usage or whatever you need to to see how close we are but the weekly
> usage is definitely more important so lets start with that"

> "a little bit low"

> "by the time we get to 95% usage in the 5 hour period i want to stop running
> agents and just get a full debrief of what they have accomplished over the 5
> hours in plain english"

> "just to be clear, the research element or step one of those four up above
> should be done by the time the usage gets to 100% on this five hour session"

> "I want to run agents exactly as many as I can in order to use the entire
> five-hour limit after five hours of usage. And I want to basically streamline
> the most important tasks. So however many agents I can have, running for the
> full five hours without using up all my usage should be running and doing the
> tasks that I deem most important or that you deem most important and you have
> discretion on that. But yeah, keep the tasks important that these agents are
> doing."

"a little bit low" is the whole of what can be sourced on the barriers the
operator did not name: it was their verdict on barriers lower than these, which
is why these sit where they do. The one barrier they did name is the five-hour
stop, at 95%.

The weekly window is the one that matters. Running it dry stops everything until
it resets, and the five-hour window only refills a few hours later, so weekly
comes first and the five-hour one is a brake on a burst.

This is a taper, not a cliff. I don't want the fleet running flat out and then
stopping dead. I want it narrowing: as the number climbs, fewer agents out, and
the ones still out on the things that matter most. Well below the barriers, the
stoker should already be leaning toward the more important work by its own
judgment — that is what the percentages are printed for.

Narrowing means cutting, not waiting. As each barrier is crossed the stoker
stops the agents working on the least important things rather than letting them
run to their own finish — "cut agents that are working on things that are not as
important" is the instruction, and a taper that merely declines to start
anything new is not one.

At 95% of the five-hour window the fleet stops outright. Every agent still
running is stopped, not allowed to finish, and the operator is sent one
plain-English account of what those five hours bought: what each agent was sent
to do, what came back, what the checks found, what is still unfinished, and what
it cost where a round recorded a cost. Where none did, the account says that
outright rather than pretending to a figure nothing measured.
`bin/debrief.py` writes that account and the queue carries it.

The barriers themselves sit high, because cutting work off early wastes the plan
just as surely as running out does. The five-hour stop is the figure the operator
named outright: 95%, level with the weekly stop.

The window is there to be spent, and spent evenly. As many agents as the five
hours will carry should be out, across the whole of the five hours, on the work
that matters most — a burst that spends the window in its first hour and then
stops dead wastes it as surely as leaving it unspent does. So beside the bands,
`bin/bearings.py` says in one line whether the usage is running ahead of the
clock or behind it, and the stoker holds a steady number of agents out on that.

Research the rest of the plan waits on finishes inside the window it started in.
The four surveys named in the 2026-09-16 words — engines, bots, solvers,
exploitation — did land inside that window, and the words stand as the standing
instruction for the next four.

This does not loosen opinion 11. There is still no standing cap on how many
workers may be out. The taper is a cap the usage number sets, not one I set in
advance, and it lifts on its own when the window resets.

## 15. One check for a document, two for everything else

The operator, 2026-09-17, in their own words:

> yes to document only changes we definitely only need one check. for bigger
> things we should stay at two but that can change to one.

A round spent on prose that cannot break anything buys less than the same round
spent on code that can, and review is not free. A change where every file it
touches is prose — anything ending `.md` or `.txt`, or anything under
`handover/` or `research/results/` — ends its review on one round that passes
finding only wording. The stoker applies those wording findings itself rather
than sending the change out for another round of commas.

Every other change keeps two consecutive rounds that find only wording. Code
that runs can be wrong in ways a second reader catches and a first one misses,
and I am not paying for that with documents.

"that can change to one" is mine to say when I want it, not a judgment an agent
makes about a particular change being small enough. Until I say so, two.

What the change touched decides which rule applies, read from the branch itself
rather than from what the brief called it: `bin/dispatch.py land` and
`bin/dispatch.py reconcile` take the list of changed files from git and refuse a
landing that is short a round.

The one round is for a change landed from its own leased checkout; anything
landed without a lease takes two.

---

## Scope of this build

`heater` is the fleet repository: the canonical home of the rules, roles, hooks,
skills, and stores. Machines receive them by symlink from this repo.

The orchestrator is the **stoker**. It dispatches, judges, and merges. It never
builds anything itself.
