Run each step only after Daniel ratifies the brief, and only through the doc verbs. Generated projections say DO NOT EDIT.

1. Mint the vision: `py agent_cli.py doc new --type design --title keylab-lit-vision-v2 --arc media-suite --draft --body-file <vision body>`. Use the arc Daniel picks in Q2.
2. Mint the brief: `py agent_cli.py doc new --type brief --title keylab-display-tie-in --arc media-suite --draft --body-file <brief body> --cite <vision id>`.
3. Mint a successor map to fa48f2 (`doc new --type map --cite art_20261007_design-night-roadmap-2026-10-07_fa48f2`):
   - mark H1 Piano Rescan hint as LANDED (git ef80715e, 4cd98cec, 2026-10-08) instead of "← FIRST";
   - add tracks K "KeyLab Lit" (pillars 1-4, 9, 10), R "The Engine Room" (pillars 5-8) and C "The Commons" (pillar 11, gated), with waves W0-W8;
   - fold W247 into track K's acceptance.
4. In that successor map, record that NP S4 "Ears" (1328e1:186-190) is superseded by the K-track beat engine, and that NP S3 and S5 are absorbed into the Light Language.
5. `doc new` has no `--supersedes` flag and there is no `doc revise`. Record the fa48f2 → successor edge by hand in the successor's body, and add this instance to the 2026-10-07 "a draft atom cannot absorb a refinement" wish (WISHLIST.md:2219).
6. If Daniel counts KeyLab Lit toward A12 THE FACE, mint a short ruling atom saying so. Do not edit c432a7. No house document places media-suite under A12 today.
7. Publish the running-order card (now W0+W1 / next W2-W3 / after attention, timeline, content, with a `pauses:` line) on the console and Discord, per memory sequence-visibly-when-threads-multiply.md:18.
8. Append the WISHES block to WISHLIST.md `## Open` and let the registry mint the numbers (the highest today is W265). Normalise the dates to the house `(MM-DD, ...)` form if the registry requires it.
9. WISHLIST housekeeping:
   - W58 is used twice (line 331 is kimi's LIBRARY tension; line 1849 is the aurora canvas bug). Renumber one.
   - Entries from 2026-09-06 onward sit as dated `##` sections after `## Declined` with no W-numbers, which drifts from the header format. Fold them into `## Open` with numbers, or record the second format in the header.
10. Make sure no KeyLab or .flp text links W228. It is the subprocess decode bug, not a .flp census.
11. Add to docs/ARCHITECTURE.md a section on arsenal/ (it has zero mentions today), including arsenal/keylab and the hub's place in arsenal serve.
12. state/coord/tasks.json has no arc field and its mtime is 2026-10-01. Confirm whether it is still the live task ledger before chartering K/R tasks against it, and add an arc field if it is.
13. Before the W0 commit, get Daniel's ruling on aubio-ledfx (GPLv3+, imported by arsenal/keylab/beatsync.py:7,61) in the Apache-2.0 repo. Record it as a ruling atom.
14. Fix arsenal/web/piano/instruments/keylab88mk3.js:34,519: re-lay the pads from 2x6 to the 9-5-1 3x4 grid using the shared pad table. Also correct the :63 comment ("idle at 50%" vs SCREEN_IDLE 0.46).
15. Recolour the warm entries in arsenal/keylab/chordview.py:18-25 to LED-safe hues, and stop marking the root white wherever warm hues are present (:51).
16. Add pytest pins for arsenal/keylab: CC64 sustain RED/GREEN, a GRID agreement test (chordview vs twin vs scene), and the burst property (≤12 per window).
17. Add a `.gitignore` negation for `state/drills/`, or a report-atom path, so KeyLab receipts are committed rather than left on gitignored paths.
18. Update memory keylab-mk3-liberation-2026-10-22.md:
    - add the 9-5-1 grid;
    - add that warm colours wash to white;
    - add the pad selector positions;
    - mark the :18 claim "only one process can hold the DAW output" as CONTESTED (probe P1);
    - point to the vision atom.
19. Add the keylab-mk3-liberation memory to the MEMORY.md index. It is missing today.
20. Add a pointer to the KeyLab vision in memory media-suite-project-2026-09-13.md and media-toolkit-vision-2026-10-11.md, as a new ask placed in the map.
21. Update memory shader-school-2026-10-13.md:79: "shared colour templates" is answered by the keylab-lit palette module, pending its build.
22. Update memory second-press-principle.md with the KeyLab applications (menus, unbound-control hints, attention escalation). Daniel picks which one is built first.
23. Offer a KeyLab Forest Walk (pads first) at the next walk day, per forest-walks-practice.md.
24. Refresh fljb/local-inventory.md counts with dated notes: 82 Splice WAVs (81 on 09-14); 913 .flp files, about 231 of them not autosaves (914 on 09-14).
25. In fljb/fl-scripting.md:208 and local-inventory.md:112, label the "256" buffer as the FL Studio ASIO driver's setting.
26. Use "Arsenal band" (arsenal/fl/vfx/README.md:1) wherever "Claude Band" appears in vision drafts.
27. Persist the prior-art findings (Bitwig KeyLab mk3 extension, saxofonbrian/keylab-mk3-sysex, both MIT) in full to research/reviewed/ with credit. Never headline them.
28. File three claude-attributed friction wishes:
    - the DAW-mode input map was never captured;
    - there is no :8787→:8793 cross-origin path;
    - theory.py is a second chord namer beside chordread.js.
29. Charter tasks K-W0 and K-W1 as the build watch, and R probes P6-P8 as the design watch. Any third thread names its `pauses:` (ORG.md:9-12,154).
