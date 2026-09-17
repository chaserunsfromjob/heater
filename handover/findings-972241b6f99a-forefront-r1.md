# Forefront rule rewrite 972241b6f99a — round 1 findings (fail; F1-F4 substantive)

Delete this file in the landing commit. Branch worker/972241b6f99a, checkout
`.heater/worktrees/pokerbot/review-972241b6f99a`, tip 8915251, draft PR #2.
Lens default. Lines at 8915251. Suite for pokerbot is pytest, run with
`.heater/worktrees/pokerbot/9fd7bd8ad257/.venv/bin/python -m pytest tests -q`
(system python3 has no pytest); README.md:45-76 gives the real commands.

Sound and not to be re-checked: the rewritten section says what the operator
decided; all 21 bullets imperative and under fifty words (longest 35); no
reason or history in the rule text; Compute budget byte-identical to trunk;
only CLAUDE.md touched; style_lint clean; three of the four extra deletions
(old bullets 1, 2 and the left-column bullet) right.

- F1 (substantive, red suite) tools/check_design_numbers.py:287 and :1510
  look up the deleted two-column table by its header
  (FOREFRONT_HEADER = "| Allowed to AI-written opponent-model code | Reserved
  to the engine |"); tests/test_design_numbers.py fails twice
  (test_every_derived_number_matches_its_constants,
  test_checker_reports_a_drifted_forefront_table): 2 failed, 25 passed.
  Proved caused by this change (trunk CLAUDE.md swapped in: 27 passed).
  Resolve: retire the forefront-table check and its two tests in this same
  change, or re-point the check at the new bullets.
- F2 (substantive) five places still assert the repealed boundary:
  OPPONENT_MODEL_DESIGN.md:120-147 ("that table is the authority", then the
  reserved list) and :1053; RESOURCES_BOTS.md:910, :1055-1078;
  TABLE_SIZE_AND_SIZING_NOTES.md:149 ("who chooses the action ... the operator
  has not granted"); tests/ground_truth/test_hand_ranking.py:5 ("CLAUDE.md
  forbids letting an AI model evaluate a hand or read a board"). Also filed
  by the worker: REFERENCE_NOTES.md:346, RESOURCES_EXPLOITATION.md:516 cite
  the table and CLAUDE.md line numbers. Resolve in this change: rewrite each
  passage to state the new rule (AI-written decision code allowed; no live
  model call), cite CLAUDE.md by section not line, keep every number.
- F3 (substantive, deleted design decision) old CLAUDE.md:33, the
  observed-population bullet, carried a definition nothing now repeats: the
  observed population is the whole database, seated players' stored rows
  included, with being seated never the criterion for inclusion;
  OPPONENT_MODEL_DESIGN.md:138-147 leans on it. Resolve: restore a bullet
  carrying that definition, dropping only the superseded tail ("and hand that
  result to the engine, which still chooses the action").
- F4 (substantive) CLAUDE.md:16-17 bans model calls at decision time only;
  nothing bans a model deciding ahead of time and freezing its answers into a
  table or weights the bot loads. The operator's words ("just shouldnt be the
  same as LLMs playing poker") close it. Resolve: add the provenance half in
  one bullet: the content of every poker decision comes from code a reviewer
  can follow, never from stored language-model output (a table, weights, or
  text a model produced).
- F5 (wording, with the ordering the operator gave) CLAUDE.md:53 "never let a
  licence question block a change" against :50-52 (public, GPL-3.0, derived
  work published). Resolve by sequencing in the text, from the operator's own
  words "just use the code and we will make our repository private later":
  use the code now; publishing anything GPL-incompatible waits on the
  repository going private, which is the operator's call.
- F6 (wording) CLAUDE.md:21 names LLM_POKER_FAILURE_MODES.md, which does not
  exist yet (branch worker/bc7299f59f85, PR pending). Resolve: state in the PR
  body that this branch lands after that one; the stoker sequences the merge.

Every finding wording only: NO.

Round-1 cost: 14 tool calls, about 8 minutes, 44k tokens; no dollar figure.
