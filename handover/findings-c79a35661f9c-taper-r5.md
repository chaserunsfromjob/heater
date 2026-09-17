# Usage taper c79a35661f9c — round 5 findings (fail; F1-F5 substantive)

Delete this file, and the r3 and r4 files beside it, in the landing commit.
Branch worker/c79a35661f9c at 11b3280 on origin, checkout
`.heater/worktrees/heater/03a2b608f262`. Taper half sound for the fourth
round (bands at nine points, overrides, NOTHING_NEW names `bin/debrief.py
--hours 5 --queue`, every page count independently recomputed and right).
All fails are on the debrief page. Fixer 5 NOT yet dispatched: it waits for
a slot behind the research (operator's instruction).

Lines in tools/debrief.py unless named. Render the page as the r4 file says.

- F1 :363-372 (_describe) the done_when fall-through prints a content-free
  stub: live entry 3 (ca03e4463c49, "Raise MAX_SLOTS from 3 to 6") renders
  in full as "Done when a file in the project passes." The brief's second
  sentence, "The operator wants more concurrent workers per project", is
  plain and says the work. Resolve: reject a done_when rendering whose
  surviving clause has no content word of its own (only a substitution plus
  a verb); take a first-or-second sentence that states what was wanted, or
  fall through to DOES_NOT_TRANSLATE.
- F2 :369-371 and :57-83 the done_when path leaks fleet jargon: entry 4
  reads "…run from a clean worktree or from a dirty checkout with a
  different context-usage reading". Add the fleet's own jargon (worktree,
  checkout where not the explained one, stub, monkeypatch, context-usage)
  to the reject set, not the swap set, and apply the same rejection to
  done_when as to the task.
- F3 :363-368 the new `break` takes the first non-meta sentence, which on 4
  of 18 entries (2 of 8 on the five-hour page) is background, not the work:
  "The operator has confirmed firm requirements…" and "We have no
  testing/evaluation strategy yet…" where the fourth sentence ("Research
  and write a new file, …") says the work. Keep scanning; accept only a
  sentence carrying an imperative about the work or stating what was
  wanted; reject background or diagnosis; then done_when; then the honest
  line.
- F4 tests/test_debrief.py:280-303 the two round-4 regression tests quote
  the live entries in their docstrings but use invented done_when text, so
  they pass on friendly data while the live page shows F1 and F2. Use the
  two records' actual task and done_when text verbatim and assert the
  output the operator gets.
- F5 :465-483 (_repeats) "3 of the entries below describe work already
  listed above them" counts briefs (correct) but says "entries", and the
  reader finds a fourth identical pair (entries 8 and 13). Say it of the
  jobs: "3 of the jobs below were the same brief sent out a second time".
- F6 (wording) tools/usage.py:266-273 "read 1 minutes ago" between one and
  two minutes; debrief._ago already handles it.
- F7 (wording) :478-483 "1 separate pieces of work, not 2" when all but one
  entry is a repeat.
- F8 (wording) page entry 1 "Vendor a ready-made project…": "Vendor" as a
  verb is programmer usage; "bring".
- F9 (wording) tools/usage.py:307 and :351-352 `{used:.0f}%` rounds 94.99 to
  "95% used" beside a band that is not the stop band; print one decimal or
  floor it.
- F10 (wording) entries 5 and 10: the (a)/(b) trim plus the lone-marker
  drop leaves "…that natively support: standard 52-card no-limit hold'em…"
  with the 2-to-9-players half gone after a colon; keep both items or drop
  the colon and the list.
- F11 (wording) OPINIONS.md:161-163 "the whole of what can be sourced on
  where the barriers belong" is contradicted by the fourth quote (95%) and
  :190; say it is the whole of what can be sourced on the three barriers
  the operator did not name.
