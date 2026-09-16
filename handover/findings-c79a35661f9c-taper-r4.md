# Usage taper c79a35661f9c — round 4 findings (fail; F1-F4 substantive)

Delete this file, and `findings-c79a35661f9c-taper-r3.md`, in the landing
commit. Branch worker/c79a35661f9c at 53338df on origin, checkout
`.heater/worktrees/heater/03a2b608f262`. The taper half passed every probe
for the third round running (bands, overrides, crash path, bearings exit,
queue route, opinion 13 verbatim, rule bullet). All four fails are on the
debrief page. The round-4 fixer was dispatched with these.

Lines in tools/debrief.py unless named. Render the page with
`python3 bin/debrief.py --hours 8` against the trunk stores read-only
(HEATER_STATE_DIR to a scratch dir; HEATER_DISPATCHES_DIR, HEATER_REVIEWS_DIR,
HEATER_LEASES_DIR, HEATER_QUEUE_DIR at the trunk folders; never `--queue`).

- F1 :318-336 (_describe). Dispatch ca03e4463c49 ("Raise
  tools/worktrees.py's MAX_SLOTS constant from 3 to 6") renders as "Update
  the constant's comment if it references the old number." Sentence 1 dies
  on MAX_SLOTS with no clause boundary before it, sentence 2 the same, and a
  trailing housekeeping sentence wins by default, so the page says an agent
  was spent on editing a comment. Resolve: when the opening sentence is
  dropped for machinery, do not accept an incidental later sentence; fall
  through to done_when and then DOES_NOT_TRANSLATE, or require the chosen
  sentence to be among the first two and carry an imperative about the work.
- F2 same function. Dispatch 3ea2c1c2c6b7 (stop two test classes reading
  live session state) renders as "Confirmed: the module passes 20/20 in a
  clean worktree and fails 7/20 in the main checkout right now, with
  byte-identical code." A diagnostic note presented as the brief, carrying
  three unexplained terms. Same resolve as F1.
- F3 :54-68 (PLAIN_WORDS), :76-85 (CODE_SHAPE), tests/test_debrief.py:373-378.
  Machinery still reaches the page: "wherever poker_ai is being vendored" (a
  bare repository name; the slash rules need a slash); "into this repo"
  (pinned as wanted output by the test at :376); "between a separate copy of
  the work and main in pokerbot" (a bare branch name). Resolve: treat a bare
  lowercase identifier with an underscore as a project name; treat a bare
  branch word (main, trunk) as "the shared copy"; swap "repo" for "project";
  change the assertion at tests/test_debrief.py:376.
- F4 :418-434 (_repeats). "4 of the entries below describe work already
  listed above them … 15 separate pieces of work, not 19" is computed by
  comparing rendered descriptions, which are deliberately lossy, so two
  different jobs can render identical and the page would then assert a
  figure the store does not support. Right today (the reviewer checked the
  four pairs); latent. Resolve: derive the repeat count from the normalized
  task text on the records; use rendered text only for display.
- F5 (wording) :462-472 (_note_lines) "2 notes … They are: an account an
  agent wrote for you." Plural subject, singular list. When every note is
  one kind: "Both are accounts an agent wrote for you."
- F6 (wording) tools/usage.py:265-270 (_age_words) "read 0 minutes ago";
  debrief._ago says "just now" for the same case. Say "read just now" below
  one minute.
- F7 (wording) tools/usage.py:88-90 (ALLOWS[NOTHING_NEW]) names neither the
  queue nor the flag; roles/stoker.md:17 names `bin/debrief.py --hours 5
  --queue`. Name the full command in ALLOWS.
- F8 (wording) OPINIONS.md opinion 13: "The third quote is the whole of what
  can be sourced: the operator's verdict on the barriers in an earlier
  draft, which is why they were raised to where they now sit." No object,
  and "an earlier draft" is prior practice written into the record. Say
  plainly that "a little bit low" was the operator's verdict on lower
  barriers, which is why these sit where they do, or drop the sentence.
- F9 (wording) page nits: entries whose clause carrying (b) was trimmed
  still show a lone "(a)"; shouted words left over from file names ("BOTS",
  "SOLVERS", "EXPLOIT"). Drop a lone list marker when its siblings are
  trimmed; lowercase an all-caps word that is an ordinary English word.
