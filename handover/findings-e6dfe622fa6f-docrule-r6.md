# Review round 6 findings, dispatch e6dfe622fa6f (document-only one-round rule)

Reviewer verdict FAIL at branch worker/e6dfe622fa6f @ bfd0a82. Round-5 fixes
verified. Suite 698 OK, gate exit 0. Delete this file in the landing commit.

## F1, substantive: `land` reads an already-in-trunk document branch as code

`tools/dispatch.py:374`. `land` counts from `rounds_needed(lease)`, which
diffs `<trunk>...HEAD` in the checkout. Once the branch's commits are in the
trunk (merged by hand), that diff is empty and an empty diff reads as code,
so `land` demands 2 rounds where `reconcile` (round-5 fix) takes 1 on the
same branch. `git merge --no-ff` on an ancestor exits 0 "Already up to
date", so `land` runs to completion. Resolve: `land` falls back to
`rounds_needed_without_reading_the_checkout` when the checkout diff is empty
because the commits are already in the trunk; test: a document merged by
hand then landed with `land` lands on one wording-only round and is stamped.

## F2, substantive: the already-in-trunk stamp can label somebody else's work

`tools/dispatch.py:616-617`, helper `:252-278`. The route is also reached by
an empty branch that merely caught up with a trunk that moved (comment
`:603-610`); `empty_branch` returns "" and `worktrees.landed` is True, so
`base_sha...branch` is only what the trunk gained from others. A dispatch
that did no work can be stamped `document_only=True` and counted by
`store.changes_landed`. Resolve: before reading that branch's paths, check
the branch carries commits of its own; skip the stamp otherwise; test: a
caught-up empty branch on a documents-only trunk is not stamped.

## F3, wording: skill misdescribes where both path lists are read

`skills/adversarial-review/SKILL.md:55-57`: "read both lists wherever the
checkout still exists" is false for the already-in-trunk route, which reads
committed paths only. Say a branch the trunk already contains is read from
its commits against the base the lease recorded, checkout standing or not.

## F4, wording: README names only `land`

`README.md:178`: name `bin/dispatch.py reconcile` beside `land`, as every
other tier does.
