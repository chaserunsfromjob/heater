# one-round document rule e6dfe622fa6f — round 1 findings (fail; F1-F6 substantive)

Delete this file in the landing commit. Branch worker/e6dfe622fa6f, tip bbf5ae9,
checkout ~/.heater/worktrees/heater/dc76881cb2a5 (dispatch OPEN; the fixer
works there). Recorded in the store as round 1. Lens default. Lines at bbf5ae9.

Verified and not to be re-checked: the classifier's suffix and directory lists
match all three prose statements; every unknown path shape falls to the strict
side; changed_paths uses three dots and returns [] on git failure; land still
refuses on uncommitted changes and takes the no-lease close as before;
reviewed/review_note default to the strict count; ROUNDS_TO_END_REVIEW keeps 2;
suite 670 OK; new test class 7 OK; gate exit 0.

- F1 (behaviour, number) tools/store.py:121 still calls reviewloop.ended with
  the 2-round default and review records carry no path or document field, so
  every document change that lands on one round is never counted as landed
  by `bin/store.py query`, and "rounds spent on documents" cannot be
  answered; tools/dispatch.py:34-36 still claims store and land share the
  rule. Resolve: `bin/store.py review` records a document_only flag (or the
  rounds needed) on the review record; changes_landed reads it; record the
  field in the contract doc or OPINIONS.md.
- F2 (fact) README.md:194-197: the new sentence sits inside step 7, which is
  about reconcile, but reconcile (tools/dispatch.py:436, :494, :525) still
  requires two rounds. Resolve: state the one-round rule where land is
  documented; in step 7 say the sweep's check still needs two until task
  3a0e461e279d lands.
- F3 (rule meaning) rules/global.md:35 "wording-only findings you apply
  yourself": the rule is loaded by reviewers with no write tools, so name
  the stoker; and the dropped clause "records why in the store note" was
  load-bearing. Resolve: name the stoker and restore the store-note clause
  (or record its removal as a decision).
- F4 (rule meaning) rules/global.md:35, OPINIONS.md:259-261, the skill
  :44-45 say "every path is a document", which literally makes an empty
  diff document-only, while reviewloop.py:43-52 and dispatch.py:193-194
  treat empty/unreadable/no-lease as code. Resolve: state the boundary once
  in the skill's "When review ends": an empty or unreadable diff counts as
  code.
- F5 (behaviour) tools/dispatch.py:187-196 rounds_needed returns two when
  lease_id is empty (the project-checkout path land supports at :283-287),
  so a document written in the project's own checkout never gets one round.
  Resolve: read the diff from record["workdir"] against the repo's trunk,
  or state in the rule that the count is read from a leased checkout and a
  change without one takes two.
- F6 (claim with no number) OPINIONS.md:258-259 "Review is the most
  expensive thing the fleet does, and most of it is spent on changes that
  cannot break anything": the store records no cost (139 of 139) and cannot
  split rounds by document vs code. Resolve: cut the quantified claim,
  keeping the operator's words and the qualitative reason; the reasoning
  with the live query figures (139 rounds, 39 changes, median 2, worst 10
  at 2026-09-17T17:37:48Z) belongs in the commit message.

Every finding wording only: NO.

Round-1 cost: 14 tool calls, about 11 minutes, two suite runs. No dollar figure.
