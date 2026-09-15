# Handover

<!-- handover-commit: 1470d47 -->

Written at `1470d47` on `claude/artifact-system-continuation-ko9236`. Verify with
`bin/handover.py`. A snapshot, not a log — rewrite it, do not append.

Read `README.md` for what is built and what is next, `OPINIONS.md` for the
operator's positions, `rules/` for the rules, and the commit messages for why
each change looks the way it does. **None of that is repeated here.** What
follows is only what you cannot look up.

---

## Start here

Everything through step 2 is landed, pushed, and green: 116 tests, `bin/gate.sh`
passes. Nothing is half-finished. No pull request is open and the operator has
not asked for one.

**The next action is step 3, the adversarial review loop.** The operator was
asked whether they wanted to be walked through its decisions first or have it
built and explained afterwards, and the question went unanswered — they moved on
to other topics. I recommended building it and explaining after, because the
choices there are technical rather than matters of their taste. Confirm or
proceed; do not treat silence as approval of a large design.

## The operator

This is the single most important thing in this file.

**They are not a programmer and have little computing background.** An
explanation they cannot follow is a failed deliverable, exactly like a failing
test. This is recorded as opinion 9 and as the rules under "Talking to the
operator", so the standard is enforceable rather than a matter of tone.

The chosen style: plain words carry the explanation, and the technical term is
named last, after the plain version already stands on its own.

**The mistake to avoid.** Early on they were asked to choose between
architectural options using vocabulary they had never been given. They answered
"i dont understand" three times in a row. That was a failure of the question,
not of the person. Never present a choice between unexplained options — explain,
recommend, then ask.

They want context cleared often and deliberately. That is why the handover
procedure was built before the review loop.

## Do not try to read the source artifact

The design derives from reference notes the operator pasted into the session,
titled "Everythingdev Field Guide". The artifact at
`https://claude.ai/artifact/94SNUmhCsGxeAEEe6WcKGT` is **not readable** by a
Claude session: it is shared with the operator rather than owned by them, and
every read path fails with "served to you as a public (non-member) reader".
Artifact read, a targeted extraction prompt, and WebFetch were all tried.

Ask the operator to paste anything you need from it. Everything already borrowed
lives in `OPINIONS.md` and `rules/`.

## Decisions whose alternatives left no trace

Each of these looks arbitrary in the code and is not. Re-deriving them costs a
session; reversing them costs more.

**Near-duplicate detection uses character matching, not token overlap.** Token
overlap was written first, then measured against the real rule files: a plural
variant scored 0.82 while the closest genuinely different pair scored 0.33 — too
thin a margin. Character matching scored the same pairs 0.99 and 0.60. The 0.85
threshold sits in that gap. Token overlap looks simpler and is wrong.

**Deploy drift is deliberately not in the gate.** Whether a given machine is
symlinked is a property of that machine, not of a change, so gating on it would
fail every run on a machine that has not deployed. The link table is checked by
tests instead.

**`settings.json` is merged, `CLAUDE.md` is symlinked.** The asymmetry is
deliberate: symlinking settings would wipe whatever else the operator has
configured there. The merge replaces only groups whose commands point into this
repo.

**The guard warns rather than denies on unrouted git writes.** Opinion 2 calls an
unrouted repo write a defect, which argues for a denial. The stoker does not
exist until step 6, so denying now would lock the operator out of their own
repository. The README marks step 6 as where this flips.

**Queue items are tracked in git.** Chosen for diff-readability over
conflict-avoidance, with eyes open. `queue/README.md` records the intended
response if conflicts become routine: move to per-machine directories synced by
the SessionEnd hook, and specifically *not* adopt a database.

## A tension already resolved — do not re-litigate

Opinion 1 says the system must stop needing the operator and must never ask the
same question twice. Opinion 9 says to check whether an explanation landed. Read
carelessly these contradict.

The resolution is written into opinion 9: opinion 1 governs work the system does
while the operator is away and must not wake them to decide; opinion 9 governs
the conversation when they are present and asking. Leave it settled.

## Traps

- `OPINIONS.md` is deliberately not linted. It carries dates and prose by
  design; the linter targets `rules/` and `roles/` only. `roles/` does not exist
  yet and its absence is handled.
- **`bin/deploy.py` has never been run against a real machine.** Every session so
  far has been an ephemeral container where deploying accomplishes nothing. It is
  tested against temporary directories only. Treat the first real run as unproven.
- Two ordering bugs were caught by tests rather than by reading: the urgency rank
  was reversed twice, so `normal` sorted above `high`, and second-precision
  timestamps lost arrival order within the same second. Both are pinned by tests
  now. Ordering in this repo is worth testing rather than eyeballing.
- The guard denies by pattern, so it will miss spellings nobody has thought of.
  That is the accepted design: it denies only what it is certain about, and the
  rule covers the rest. Do not widen it into blocking on suspicion.
- Hook scripts must stay executable. A test asserts this, because a registered
  hook that cannot run fails silently.

## Conventions worth knowing before you write anything

- Every rule file is linted: one imperative bullet, under fifty words, at most
  two sentences, no dates or prior-practice prose, and no restatement anywhere in
  the tree. A prose edit can fail the suite. That is intended.
- Commit messages carry the reason for a change. Rules never do.
- This session runs in Claude Code on the web, so `/voice` and any real deploy
  are unavailable here. Both work on the operator's own machine.
