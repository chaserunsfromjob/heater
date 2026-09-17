# Evaluation strategy 45e49ce81e40 — round 7 findings (fail; F1 substantive — fifth round on one defect)

Delete this file, and `findings-45e49ce81e40-evaluation-r{3,4,5,6}.md`, in the
landing commit. Branch worker/45e49ce81e40, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\evaluation` on the PC, tip d865bb0
as reviewed; merges clean into main f8dc012. Recorded in the store as round 7
(b6d8f2a4c7e1). Lens default. Lines at d865bb0. THE OPERATOR'S CAP APPLIES:
fixer 7 NARROWS THE WORDS to exactly what the checker pins (no further
checker extension), round 8 records any wording as observations and lands
on its pass.

Sound and not to be re-checked (682 mutations this round): every claim the
coverage passage makes about the sample-size, paired-ρ, multiplier and
factorial tables (115 mutations, 0 escapes); every column of the budget
table (25, 0); every row of the rotation-night table (17, 0); the example
report block's claimed items (32, 0) — and "all 8 seat counts" at :941 is
unpinned and NOT claimed, the fixer was right; both engine throughputs in
every copy (5 x 4,438; 2 x 47,564); the five gate copies byte-identical and
counted; the declared-unpinned per-seat/per-persona figures behave as
declared; round-6 W1 (:1472 word for word with §3.7), W2 (gloss not
retitle — the §2.4 anchor has 8 links), W3 resolved; the checker
standard-library, encoding-safe, nothing hard-coded outside CONSTANTS,
weight_order() derived from PRIMARY/SECONDARY_SEATS; the seven new tests
real; nothing settles the engine (:1665-1680 the operator's recorded
decision), table size or carve-out; suite 41; 234 checks.

- F1 (substantive) the coverage passage :1990-2040 still over-reaches in
  four places. (a) :2021 "the budget figures the provenance table below
  restates" — nine figures in that row (:2088) are unpinned: 23.5x, ≈11 ms,
  16 routine cells, 28,256, 0.98 h, 1.23 h, Σw² 0.315, 3.92, 10-hour; and
  all of :2087 (4 decisions/hand; 8 workers; 1.0 bot-second; 28,800). (b)
  :2010-2012 "every hand count and hour in §3.6, including the worker
  breakeven and the headroom" — escapes at :1058 (141,280), :1150 (141,280
  / 70,640), :1155 (14,128), :1153 (3.9 h / 4.9 h), :1069 (3.92), :985 and
  :1059 (the 10-hour cap, held as ACCEPTANCE_CAP_HOURS, no copy in §3.6
  pinned). (c) :2024-2032 the every-copy paragraph lists five figure
  groups; three are not pinned everywhere: cores (:1043, :2085 unpinned),
  141,280 (:72, :1058, :1150 unpinned), the four-run window (:1142, :1777,
  :2084 unpinned). (d) :2018-2020 "absence from every phrasing that would
  print it as a live throughput" — the guard is three fixed phrasings.
  RESOLVE BY NARROWING THE WORDS, not the code: :2021 name the three
  groups check_provenance_rows covers (the full grid, the nightly run, the
  pooled headline) and say the rest of that row is not pinned; :2010-2012
  replace "every hand count and hour in §3.6" with the enumerated
  arithmetic the checks quote, or add "except where §3.6 restates a figure
  in passing"; :2028-2030 drop cores, the nightly budget figures and the
  four-run window from the every-copy list (or name the one phrasing each
  pattern covers); :2019 "from the three phrasings this document uses to
  print a live throughput". Make the docstring (:30-45) say the same.
- W1 (wording) :2007-2009 "its hands per cell" — only the right-hand 7,064
  at :1716 is pinned; say "on today's-engine side" (or pin the left cell —
  but the cap says narrow).
- W2 (wording) :2034-2037 the exemption names "per-seat and per-persona"
  figures; the primary line :946 (+34.2 [+11.8, +56.9]) is also invented
  and unpinned; say "every win rate and interval the block prints".

Every finding wording only: NO (F1 — but it is entirely wording on one
passage and the docstring; a fixer that narrows the words closes it).

Round-7 cost: about 40 tool calls, 682 mutations, about 40 minutes; no
dollar figure. Seven rounds on this change so far.
