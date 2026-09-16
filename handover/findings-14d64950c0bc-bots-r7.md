# Bots survey 14d64950c0bc — round 7 (confirming) wording findings

Delete this file, and `findings-14d64950c0bc-bots-r4.md` and `-r5.md`, in
the landing commit of the wording fixer. The survey is already on pokerbot
main at ea013b5 (landed early by reconcile after round 6). Round 6 passed
wording-only, round 7 confirmed it (store df518a0f396c), so review is over:
one fixer on a fresh branch from trunk applies these, then the stoker lands
it with `bin/dispatch.py land <new id> --change 14d64950c0bc`. Lines in
`RESOURCES_BOTS.md` on trunk at ea013b5; re-locate by content.

- F2 (carried from round 6) :682-683 "trained models and solver databases
  are excluded intentionally" is not a string in PokerScreenBot's README.
  Its lines 74-75 read "The **trained models** (`models/` folder) and the
  **solver database** (`solver_db/` folder) are **not included** in this
  public repository" and "this is intentional, to protect proprietary
  data". Quote exactly or drop the marks.
- W1 :468 "-13.1 bb/100 against live Slumbot over 86K hands" is in quotation
  marks but not the source string; robopoker's README line 25 reads
  "**−13.1 bb/100** against live [Slumbot](https://www.slumbot.com) over
  86 K hands" (Unicode minus, "86 K"). Quote exactly or drop the marks and
  keep the figure as a paraphrase; naming the README line matches the
  standard used elsewhere.
- W2 :471-472 "Action translation: pseudo-harmonic mapping over finite
  lattices" is a reconstruction of a two-cell table row
  (`| **Action translation⁷,⁸** | Pseudo-harmonic mapping over finite lattices |`).
  Render as the row it is, or drop the marks.
- W3 :172 "it does not come with a strategy, and it never will" is verbatim
  from the fork `openholdem-next/openholdembot` README.md:14; the original
  `OpenHoldem/openholdembot` has no README. Attribute it to the fork's
  README.md:14.
- W4 :607-609 `decide_ppl` returns only `(kind, amount)`; the trace is
  appended to `PPLBot.thoughts`, not returned. One clause.
- W5 :190-196 `CAutoplayer.cpp:500-518`, `SwagAdjustment.cpp` and
  `CSymbolEnginePokerTracker.cpp` omit their `OpenHoldem/` directory while
  `Shared/MagicNumbers/MagicNumbers.h:67-76` is repo-root relative. Prefix
  the three. All line references are correct.

Round-7 cost: about 40 tool calls, 135,035 tokens, 14.7 minutes; no dollar
figure.
