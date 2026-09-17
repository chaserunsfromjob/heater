# Table-size notes 984aa6810a05 — round 7 findings (fail; F1 substantive, a one-sentence regression)

Delete this file, and `findings-984aa6810a05-tablesize-r{4,5,6}.md`, in the
landing commit. Branch worker/984aa6810a05, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\tablesize` on the PC, tip 6c5f807
as reviewed; trunk NOT merged in (confirmed). Recorded in the store as
round 7 (c7e2a9b4d1f6). Lens default. Lines at 6c5f807.

Sound and not to be re-checked: rounds 4-6's lists; every round-6 finding
resolved and verified (F1 clause gone and the premise re-confirmed; W1's
"two places below" counted; W2 glosses true; W3 parses; W4 — the R3
heading may stay as it is, the codes are written out at :361-362 before
it; the wsd and A/B glosses match the design; W5 four of five glosses
clean; W6's fb353c6 citation exact); every abbreviation expanded at or
before first use except SPR; 142 links / 55 targets / 0 broken verified;
checker 233; 35 passed under both encodings; round-5 code fixes in place;
nothing settled, nothing irreversible, every figure with provenance; the
design pins 5aa40b8/72eff27/5f7a1a8 exist and order correctly; Q5's queued
task 96243ce4163a exists.

- F1 (substantive; regression by fixer 6) :391-394 "One of the two
  thresholds below turns on how hard a player pushes, measured as their
  bets and raises divided by their calls: OPPONENT_MODEL_DESIGN.md §4.2
  defines that ratio as the aggression factor and writes it AF." Neither
  VPIP_SPLIT nor AFQ_SPLIT is bets÷calls: AFQ_SPLIT is compared against
  afq, bets or raises ÷ ALL voluntary actions (§4.2 :686 on trunk), which
  the design keeps apart from AF (reported only, never acted on). As an AF
  value 0.50 means passive; as an AFq value, aggressive — a coding task
  would flip the flag. Resolve: keep plain-words-first but scope the gloss
  to the quotation: lead with "how hard a player pushes, measured as their
  bets and raises divided by their calls — OPPONENT_MODEL_DESIGN.md §4.2
  calls that ratio the aggression factor and writes it AF", then "the
  AF > 1 in the quotation below is that ratio; AFQ_SPLIT is the design's
  own aggression-frequency cut, a different quantity that descends from
  it."
- W1 (wording) :323-325 wsd listed as a "street-local" stat beside
  fold_to_cbet; §4.2 gives fold_to_cbet a street key and wsd none (opportunity
  "reached showdown", a whole-hand outcome). Nothing downstream depends on
  it. Resolve: "stats whose opportunity is defined by a situation rather
  than by a seat, such as fold_to_cbet, or by an outcome of the whole hand,
  such as … won at showdown, written wsd."
- W2 (wording) :146-149 "a third program again" — drop "again".
- W3 (wording) :148-151 "That decision is written into CLAUDE.md…" reads
  as the carve-out (just said NOT granted); say "The engine decision is
  written into…".
- W4 (wording; landing record) fixer 6's commit message says six links
  point at the R3 heading; none do (grep 0; five never-linked anchors
  include it). The document is unaffected; the next fixer's commit message
  notes the correction. (Its "four links" for §1.2 is right.)
- W5 (wording) :750 SPR used before "stack-to-pot ratio"; put the words
  first.
- W6 (wording) :502 "PPAD-complete" never glossed and sits in the
  argument about project direction: "belongs to a class of problems for
  which no method that finishes in reasonable time is known or expected —
  PPAD-complete".
- W7 (wording) :371 (118 chars), :892 and :1411 (107), :1424 — re-wrap the
  lines carrying the lengthened §1.2 link.

Every finding wording only: NO (F1 only; a one-sentence fix, no figure,
link or test touched).

Round-7 cost: 29 tool calls, about 30 minutes, no fetches; no dollar
figure. Seven rounds on this change so far.
