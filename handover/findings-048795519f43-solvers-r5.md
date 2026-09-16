# Solvers survey 048795519f43 — round 5 findings (fail; F1-F4 substantive)

Delete this file, and `findings-048795519f43-solvers-r{3,4}.md`, in the
landing commit. Branch worker/048795519f43, checkout
`/Users/chasethompson/.heater/worktrees/pokerbot/85f4140c6fae`, tip 474402d
as reviewed. Recorded in the store as round 5 (42bddf3b2301). Fixer 5
dispatched 2026-09-16 with these. Lines in RESOURCES_SOLVERS.md at 474402d;
re-locate by content.

Sound and not to be re-checked: all eight round-4 fixes (F6's Deepsolver
on-demand tier confirmed on the live page); the settled/open split settles
nothing unrecorded and hands the engine road to the reconciliation in five
places; every GTO Wizard quotation in entry 17; monkerware, holdemsolver,
pokerai.bet and its terms, HRC pricing, Simple 3-way, spinwize, gtostrategy,
gtobase; every GitHub fact (star drift of one on TexasSolver and phevaluator
is drift); GTOpen README claims; CLAUDE.md :13-15, :17, :24, :26; summary,
shortlist and Part 4 agree with the entries; treys (209,818/s) and
phevaluator (789,680 and 2,509,048/s) re-run at load 3.74 inside the file's
ranges, ratio 12.0x inside the stated 5-15x.

- F1 (substantive, fail-class) :889, :899, :900-901, :944, :1034, :1087.
  "$69 to $499" for MonkerGuy ranges, six times including the closing cost
  sentence. On https://www.monkerguy.com/ the only $499 item is "6-MAX PLO
  MTT (BB ANTE) Pack (10bb-100bb) $499", Pot-Limit Omaha. The hold'em
  ladder: 6-MAX 100BB 2.5x Open $69, 6-MAX 150BB 2.5x $69, 6-MAX 3x 100bb
  $69, 6-MAX NL (2BB ANTE) $139, 9 PLAYERS NLH 100bb 2.5x $199, 6-MAX NL
  (HIGH RAKE) Pack $209, 6-MAX NLH Pack (20bb-200bb) $249, 8max (BB ANTE)
  MTT Packs $319; Heads-up MTT $129, Spin&Go 3-way $209, HU SNG $209. :889's
  coverage cell names hold'em products only, so its price ceiling is
  unreachable by anything in the cell. Resolve: replace at all six sites
  with a range from the hold'em products, naturally "$69 (6-max 100bb) to
  $319 (8-max MTT pack)", noting $199 for the 9-player 100bb sim this
  project would want; the Part 4 row's price cell names which product each
  end is. Read date beside it.
- F2 (substantive) :1068-1070 "about 13,000 play-outs per decision against
  a four-move menu, but only about 242 with full bet sizing", attributed to
  ENGINE_ALTERNATIVES.md. Those were its figures at d6817d4/c1db53c; the
  current draft on worker/7f09949cb56f
  (/Users/chasethompson/.heater/worktrees/pokerbot/92e2a2c459ef/ENGINE_ALTERNATIVES.md:863-865)
  reads "7,370 - 12,373 - 13,285 play-outs per 250 ms decision" and "117 -
  244 - 250". Resolve: drop the two precise counts (the point survives), or
  restate as the other document's current min-median-max with a note that
  it is a draft under review and may move before the reconciliation. Read
  the engine survey's tip at fix time; it is still being fixed.
- F3 (substantive) :105-111 (summary finding 4), :392-403 (entry 3),
  :1078-1081 (open list). The "+40 to +80 bb/100" promise and "0 to 461
  bb/100" warning from GTOpen's docs/player_types.md are exact (line 117;
  table lines 127-136; Nit row line 130), but the file's head-note at lines
  3-6 says: "September 2026: generated profiles now use separate limp-entry
  defenses and the app defaults to adaptive large-bet responses. Historical
  results below used fixed profiles and should not be read as current
  adaptive-model predictions. See the correction and its limits
  (preflop_modeling_fix.md)." The survey presents them as predictions.
  Resolve: one sentence in entry 3 recording the head-note and its date,
  and a half-clause at :105-111 and :1078-1081 marking the figures as the
  author's historical fixed-profile results. No number changes.
- F4 (substantive, minor) :68, :199, :913, :1007, :1108 "0.56 to 0.71 s of
  solver time (5.5 to 8 s wall)". The lower end traces
  (texassolver_turn_run.log `time used: 0.561`; the note records 5.45 s wall
  at load 3.40). "0.71" appears in no file under research/solvers/; the
  note says only that an earlier run on a busier machine took about 8 s
  wall with load not recorded. Resolve: add the earlier run's solver timer
  to texassolver_turn_run_note.txt if it exists in a probe file (copied,
  not retyped), else drop the upper end and publish the single traced
  measurement with the 8 s wall as an untimed remark.
- F5 (wording) :990 heading "Settled by measurement, and safe to adopt
  now." sits over one timings-only bullet that says it nominates nothing.
  Retitle, e.g. "Settled by measurement: timings only, no tool nominated".
- F6 (wording) :1086 "The settled part costs nothing and uses only ISC and
  Apache code": the settled part is timings and uses no code. Say the code
  that was timed is ISC and Apache and would cost nothing if adopted.
- F7 (wording) :90-92 "no source here cites" versus :1068's cited 13,000
  play-outs: different quantities (equity play-outs in a Python loop versus
  full-hand rollouts in a 250 ms budget). Half a sentence at one site or
  the other distinguishing them.

Round-5 cost: 33 tool calls, about 25 minutes, 158,184 tokens; no dollar
figure. Five rounds on this change so far.
