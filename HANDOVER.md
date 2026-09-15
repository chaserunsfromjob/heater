# Handover

<!-- handover-commit: 28587b7 -->

Written at `28587b7` on `main`. Verify with `bin/handover.py`. A snapshot, not
a log — rewrite it, do not append.

Read `README.md` for what is built and what is next, `OPINIONS.md` for the
operator's positions, `rules/` for the rules, and commit messages for why.
**None of that is repeated here.** What follows is only what you cannot look
up.

---

## Where things stand

The stoker's own machinery (dispatch, review, disk-based worker limits, gate
reliability) is solid and landed. The live work is on a second project,
**pokerbot** (`/Users/chasethompson/pokerbot`), a class-project no-limit
hold'em bot. It is a plain local git repo with **no GitHub remote** — that's
normal there, not a bug; don't expect `git push` to do anything in it.

The operator's firm requirements for pokerbot, stated directly, not to be
lost among sub-tasks: **the bot must work at every table size from 2 to 9
players, use true no-limit bet sizing, and play exploitatively based on
specific opponents' identities** (their app shows stable, unchangeable
player names, confirmed by the operator). Everything else is in service of
those three.

## Five dispatches were in flight when this session ended

Check each with `bin/dispatch.py list` / `bin/worktrees.py list`, or resume
the named agent directly if it's still alive in this session's agent list.

1. **`aebf85e3a420`** — vendored `fedden/poker_ai` into `vendor/poker_ai/`.
   Worker done, findings judged. A reviewer (`ad7b07069378f5c65`) was
   mid-review, not yet reported. **The load-bearing finding**: moving off
   the 20-card short deck to standard 52 cards is *not* a config flag — it's
   blocked by `clustering/card_combos.py` materializing every hole+board
   combo in memory (≈147 GiB at the river, ~6 months at the measured rate).
   Read `vendor/poker_ai/REFERENCE_NOTES.md` before scoping any 52-card work.
2. **`36e2ae4be45b`** — `OPPONENT_MODEL_DESIGN.md` + `CLAUDE.md`. Round 4
   passed with zero substantive findings, only wording. The fixer applied
   all 7 (commit `c74e72f`). **Round 5 review is running now**
   (`a84592e74df9ee79f`), not yet reported. If it comes back clean or
   wording-only, land it — this is the second consecutive wording-only
   round the review-ends rule asks for; don't spin a further round
   chasing commas.
3. **`2602cb34ab4d`** — researching whether a different engine handles true
   no-limit + 2-9 players better than `poker_ai` (writing
   `ENGINE_ALTERNATIVES.md`). Directly answers the 52-card blocker above.
4. **`ba8300646017`** — researching how table size and bet-sizing should
   change the opponent model (`TABLE_SIZE_AND_SIZING_NOTES.md`).
5. **`c86285d6c580`** — researching how to actually measure whether the bot
   is good (`EVALUATION_STRATEGY.md`), since we have no evaluation strategy
   beyond hand-ranking correctness.

**Trap:** dispatches 2–5 above were all told *not* to touch `CLAUDE.md` or
`OPPONENT_MODEL_DESIGN.md`, writing separate new files instead, specifically
because #2 was mid-edit on those same files. Don't dispatch anything else
that touches either file until #2 lands.

## Queued, not yet dispatched

Task `96243ce4163a` (score 50, top of the list once #2 above lands): record
the three firm requirements above explicitly in `pokerbot/CLAUDE.md`.
Deliberately held back to avoid a same-file conflict with dispatch #2.

Full list: `bin/inbox.py tasks`. Next after that one: the fixed-limit
betting + table-size scoping task (`23127556e5db`, score 45) — don't start
it blind; read `ENGINE_ALTERNATIVES.md` first once #3 reports, since the
52-card blocker may mean the right move is a different engine, not patching
this one further.

## Decisions this session made that aren't obvious from the files alone

- **Opinion 11** (no fixed worker-count cap) was the operator's direct
  instruction, recorded verbatim in `OPINIONS.md`. The old `MAX_SLOTS`
  headcount is gone entirely from `tools/worktrees.py`; leasing is now
  purely a disk-space check (5 GiB floor). Don't reintroduce a headcount.
- The opponent-model review's recurring failure mode across three rounds
  was "fix the instance a reviewer named, not the general class." Round 4
  finally fixed the class (wrote the live-field-vs-population distinction
  into `CLAUDE.md` itself). If a fifth round finds another *instance* of
  the same pattern, that's a sign the class-level fix still has a gap —
  don't just patch the instance again.
- The `treys` ground-truth fixture (`tests/ground_truth/`) is **not**
  independent of `poker_ai`'s own evaluator — both descend from `deuces`,
  same encoding. Task `b4b61d9860b7` covers replacing it with something
  from a genuinely different algorithm family; `phevaluator` worked well as
  a cross-check for a reviewer earlier this session.
- Dispatched workers/reviewers for pokerbot tasks still run
  `bin/queue.py`/`bin/inbox.py` from `/Users/chasethompson/heater` — that's
  where the tooling lives; pokerbot has no inbox of its own. Keep saying so
  in briefs.

## Nothing is currently blocked on the operator

They know all five dispatches were running and that a review loop closed
out (the gate-flakiness bug, the disk-redesign). No open question is
waiting on them right now.
