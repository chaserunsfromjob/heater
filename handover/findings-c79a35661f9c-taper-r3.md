# Usage taper c79a35661f9c — round 3 findings (fail; F1-F5 behavioural)

Delete this file in the landing commit. Branch worker/c79a35661f9c at 7e652cc,
checkout `.heater/worktrees/heater/03a2b608f262`. The round-3 fixer was
dispatched with these at the handover. The taper half (collection, bands,
boundaries, bearings flag, stop hook ordering, queue show) passed every probe
for the second round running; only the debrief and one crash path fail.

- F1 tools/debrief.py:54-60 PLAIN_WORDS, :192-210 _describe. Live page still
  carries machinery in 10 of 19 entries: CamelCase class names and dotted
  calls ("TestStopHook … context.state(None)"), a substitution inside the
  clause that names what it replaced ("checkout a folder on this machine
  (already on branch a separate copy of the work)"), a substitution inside
  backticks ("the SAME `a file in the project` invocation"), ALL_CAPS
  identifiers (MAX_SLOTS), relative paths and owner/name repos
  (vendor/poker_ai/, github.com/fedden/poker_ai), bare command names.
  Resolve: after substitution test the sentence for residual code shapes
  (CamelCase run, word.word( call, backticked token, ALL_CAPS_UNDERSCORE
  token, owner/name or dir/dir/ fragment) and if any survive move to the next
  sentence, then the done_when fallback, then an honest "what this one was
  about was written for another agent and does not translate"; drop a clause
  or parenthetical that contains a match rather than substituting inside it;
  extend the path rule to relative paths and owner/name shapes; change
  tests/test_debrief.py:244 which asserts "(e.g. under vendor/)" survives.
- F2 tools/debrief.py:188-192 _clip at 220 chars ends 7 of 19 entries
  mid-sentence. Prefer the done_when fallback when the sentence would clip,
  or clip at the last clause boundary and end with a full stop.
- F3 tools/debrief.py:337-347 "31 notes were left for you … all of which you
  have already seen": 29 are findings for the stoker, delivered_at means the
  stoker was woken. Split by kind; say "waiting to be judged / already
  judged"; reports and escalations are the ones written for the operator.
- F4 tools/debrief.py:247-264 _tally "N jobs went out" counts jobs created
  before the window (10 vs 5 at --hours 5). Count both and say both: "N
  agents were working in this window; M were sent out inside it".
- F5 tools/usage.py:106-111 read() catches OSError and JSONDecodeError only;
  bin/bearings.py now reads the file and dies with a UnicodeDecodeError
  traceback on a non-text usage.json, printing no report. The round-1
  dismissal of this was wrong: catch UnicodeDecodeError (or decode with
  errors="replace") so the existing "present but unreadable" line is reached,
  and change tests/test_usage.py:441 which asserts the raise; add a bearings
  test with a non-text file. The stop-hook ordering stays.
- F6 tools/debrief.py:166-168 "1 minutes ago"; singular.
- F7 tools/debrief.py:236-237 "2 times"; "twice".
- F8 tools/usage.py:80 TOP_OF_LIST_AGENTS = 3 has no env override and no
  README row; give it both.
- F9 README.md:134-141 the env table paraphrases band meanings; name the band
  per row and leave the meaning to tools/usage.py.
- F10 roles/stoker.md:16 names no command; name
  `bin/dispatch.py close <id> --outcome abandoned` (keep under fifty words).
- F11 README.md:123-126 and OPINIONS.md §13 promise the operator is told what
  it cost; 42 of 42 rounds carry no cost. Decision: soften both to "cost
  where a round recorded one" and keep the debrief's honest line; the
  collection hole is now a task (score 45: record subagent_tokens from task
  notifications).
- Prose note: entries 6/11, 7/12, 8/13, 9/14 are the same brief dispatched
  twice; one sentence saying so would stop "19 jobs" reading as nineteen
  distinct things.
- Pre-existing, not this change: hooks/statusline.py:53 exits 1 on non-UTF-8
  stdin (same on main); file as its own finding.
