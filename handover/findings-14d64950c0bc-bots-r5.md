# Bots survey 14d64950c0bc — round 5 findings (fail, 2 substantive)

Delete this file, and `findings-14d64950c0bc-bots-r4.md`, in the landing
commit. Branch worker/14d64950c0bc at 5e5bbb9, checkout
`.heater/worktrees/pokerbot/b1f72dd635fa`. Every round-4 fix confirmed; the
seven-row enumeration exact; ~20 citations, prices and reproductions exact.
Both fails are in the two sentences the round-4 fixer added on its own at
:1037-1042. The round-5 fixer was dispatched with these and told to add
nothing beyond them.

Lines in RESOURCES_BOTS.md. Trunk CLAUDE.md is `/Users/chasethompson/pokerbot/CLAUDE.md`.

- S1 :1037-1038 "and the pairing is the whole limit" asserts an
  exhaustiveness CLAUDE.md does not record and that is false against trunk
  CLAUDE.md:31: "Derive any opponent archetype fed to the solver from
  measured action frequencies alone; never hand-write one, and never let it
  reference hole cards, board cards, or hand strength." The survey names
  "archetype" as a permitted output at :1035 and :1040 and never carries
  that limit. Resolve: delete the clause, or keep it and carry CLAUDE.md:31's
  limit beside the archetype mention.
- S2 :1038-1042 the gloss "combining rates across the observed population —
  the standing database —" drops trunk CLAUDE.md:30's clause "the whole
  database, seated players' stored rows included, with being seated never
  the criterion for inclusion", then contrasts it with "the players in the
  hand being played", inviting exactly the misreading the clause forbids.
  Resolve: restore the clause verbatim inside the gloss.
- W1 (wording) :310-311 "521.7M infosets, 391M exported strategies, 16GB,
  1h56m" is exact at noregrets README.md:668 but is also cited to
  BASELINES.md:470, which reads "521.7M infosets, 391.3M stored strategies,
  16GB, 57.2k iters/s (1h56m)". Cite README.md:668 and name BASELINES.md:470
  as corroboration, or quote both.
- W2 (wording) :539 `"can be moved to any PC"` is not a string on
  bonusbots.com/pricing.htm ("License can be moved as often as needed";
  "(to any PC you wish)"). Quote exactly or drop the marks.
- W3 (wording) :221-222 the quoted decisionmaker.py:23 line omits the spaces
  after the commas the source has.
- W4 (wording) :1012 "measures the player it is keyed to" overstates
  OpenHoldem, which looks statistics up in a PokerTracker database (:185-187,
  :195). "Looks up measured statistics by name".
- W5 (wording) GTO glossed at :93 but the letters never written out; GUI
  (:213, :391, :832), YOLO and SAM2 (:654-655), YOLOv8, ResNet18,
  MobileNetV2, FastAPI (:672-674) with no plain-words explanation.
- W6 (wording) :743 "~18 days and ~147 GiB" has no source; trunk
  REFERENCE_NOTES.md:414 (18.4 days) and :427 (146.5 GiB). Name file and
  lines.
- W7 (wording) :478-480 the 10-day free trial is on pokersnowie.com/free-trial,
  not the /pricing page the line credits; $29.90 and $16.66 are on /pricing.
  Name the second page.
