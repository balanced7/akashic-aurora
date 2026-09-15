# LS0+LS1 rulings (conductor, 2026-09-15)

These rulings answer the open decisions from the LS0-LS5 build (workflow run wf_5bc51ab6-c93). That run stopped after LS0+LS1: the re-verify found one must-fix, so LS2-LS5 never ran. Where this file and `plan-amendments.md` disagree, this file wins. The next build round copies these rows into the amendments file's "threshold changes" section.

## Threshold changes

| Receipt | Change | Why |
|---|---|---|
| **LR3b** (tempo flips per minute on Daniel's sessions) | Rates are computed only over sessions with **at least 2 minutes of locked playing**. Shorter sessions report their flip **count**, and the receipt fails a short session only if it has more than 2 flips. | S17 lasts 0.55 min and has one ×1.5 flip, which reads as 1.83/min. One event over half a minute is not a rate, and the original tracker reproduces it. On sessions of 2 minutes or more, bpmShown gives ×2 at most 0.21/min and ×1.5 at most 0.63/min, within the limits (≤ 0.5 and ≤ 1.0). |
| **LS1-level** (new) | Recorded as a receipt: ×2 on rub0 releases **at most 2 of 18** pieces, and Acc1 at the chosen level is **at least 0.90**; the same holds for ×0.5. rub1 and rub2 are reported, not gated. The suite **includes 6/8 and a simple meter where the tactus factor is 0.5** (see the must-fix). | The builder fixed the threshold. The amendments require recording it before it is claimed, and the current receipt passes only because it filters out 6/8. |
| **LR1** | LR1 measures the **tempo-lane configuration** (`LANE_BEAT_PARAMS`: `ibiAcrossHolds: true`, `shownConfirmBars: 0`), not the product defaults. The product readout drops intervals across holds and confirms bpmShown for a bar; its effect is reported beside LR1 as a delta, not gated. | This keeps LR1 comparable with the tempo lane's published numbers while the product fixes the S5 ×2 flips. |

## Must-fix before LS2

**Family buttons ignore the tactus conversion** (`score/beat.js`, `chooseLevel` and `familyOf`). The level target is `chosen.p / ratio` on the raw agent period, while the readout shows `bpm × factor`, and factor becomes 1 once a level is chosen.
- Failing case: `genPiece('6/8','arp',0,50,4242,{pickup:0})` under meter 6/8 shows 49.8 (factor 2/3). Pressing ×2 at 20 s gives 150 (×3 of the display); ×0.5 gives 37.5; ×1.5 gives 112.5; ×2/3 gives 50, no visible change.
- Fix: compute the family and the level target against the **shown tactus period** (`chosen.p / factor`). A button press must multiply the number Daniel sees by exactly the button's ratio (±3%).
- Pin it in 6/8, 12/8 and a simple meter with factor 0.5.

## LS2 rulings (2026-09-15, after LS2 repair round 2)

- **C2 sextuplets: the `d6MinGroups = 5` gate becomes the default.** The rhythm alphabet stays {1, 2, 3, 4, 6}, but d = 6 is only a candidate for a beat holding at least 5 onset groups.
  - C2 as written, where d = 6 competes on every beat, fails 6 gated receipts: LR4a bars 0.9359, LR4b 0.8376, LR4c 0.9612 / 0.8343, LR4d 0.8759 / 0.5354, LR4e +0.1096, and false d = 6 on 2.50% of beats.
  - Under the gate, all 66 checks pass: LR4a 0.9943 / 0.9713, LR4b 0.9189, LR4c 0.9814 / 0.9115, LR4d 0.9286 / 0.6727, LR4e +0.1864, false d = 6 on 0.07% of beats, and sextuplet recovery 0.9839 / 0.8715.
  - Why this is not loosening a receipt: the critic's own evidence for C2 was beats with 5 or more onsets, 0-22% of beats in Daniel's playing. Six even divisions are only plausible when about that many onsets are present, so the gate is the rule C2 meant.
  - Record it in plan-amendments.md threshold changes as a rule change: no threshold moves.
- **Phase-keep convention: ratified.** When a phase correction would leave partial the bar after a settled bar-line tie, the new phase starts one bar later. It fired 59 times on fixtures and 20 on sessions.
  - Why: *settled means never repainted*. Re-capping a frozen note's recorded duration would change a bar Daniel has already seen, which breaks the settle-then-freeze promise. Record it as a design note beside the C2 row.
- **Also for LS2 close:**
  - add the overlap count to `tests/score_settle.test.mjs` tieAudit, so the sessions check covers the same five properties as auditScore;
  - add a dedicated fixture for the frozen-tie overlap edge (a bar settling on a 2 s pause while a tie is claimed, then an onset in the same voice before the next bar's midpoint);
  - remove the dead line in `index.js` freezeBar.
- **LS1-level counting:** count levels that were already wrong before the press as misses, as the builder did (Acc1 0.914 / 0.915, gate 0.90). The two 6/8 ballads that read at double tempo with no press are a rung-4 level error, which LR2a and LR2d already count. Don't exclude them from the gate: the margin is thin, and it should stay visible.

## LS2close to LS5 rulings (2026-09-15, conventions the verifiers asked for)

- **The pin (LS2close): accepted, but per voice.** When a revision would place an onset inside a frozen continuation, only the notes in the conflicting voice move to the continuation's end (at most 6 ticks). Notes of the same onset group in other voices stay where they were heard. This fixes 12 of 19 fixture pins (and 3 of 7 session pins) that moved upper-staff notes for no reason. A pinned note that lands on the same tick as another group in its voice merges into that chord, counted as `pinMerged` in stats.
- **Clef versus octave lines (LS3).**
  - A clef change needs at least 2 consecutive bars that want it, and a clef never returns within 2 bars (no one-bar round trips).
  - A shorter excursion uses an octave line: **8va only above the treble staff and 8vb only below the bass staff** (T5). A bass-staff passage that climbs is handled by switching that staff to treble under the 2-bar rule, never by a bass-clef 8va.
  - Target: at most 5 clef changes per 100 bars on S1..Sn, and 0 one-bar round trips.
- **Beyond three ledger lines when nothing else holds (LS3):** use 15ma above the treble or 15mb below the bass for a passage of at least 2 notes. For a single note, accept the ledger lines and count it in stats. Never change clef mid-bar.
- **The beam writer (LS4): must-fix.** A beam group never spans an unbeamable item. Split the group at any quarter or longer note or rest, and write begin, continue and end only across consecutive beamable items. Add a MusicXML schema-level test that catches the failing case.
- **"freely" marks (LS4):** print "freely" once at the start of each free-time (tape) passage, and "a tempo" once where a tracked beat resumes, never on every measure. A clean-copy export with no taps and no jam beat is one free-time passage: one "freely" at the top, measures at the rough BPM in the key's meter, and no per-measure marks.
- **Short measures (LS4):** `implicit="yes"` only for a pickup at the very start of the score. A shorter measure mid-score, where a new segment starts, gets an explicit time signature for that measure (for example 2/4 inside 4/4) and restores the meter in the next measure. Never an unmarked short measure.
- **Accidentals (LS4 and LS5), standard engraving practice:**
  - Accidental state is tracked per staff and position, with written order by position and then by pitch. F4 and F♯4 at the same position print the F4 natural and the F♯4 sharp.
  - After a tied-in altered note, a later different spelling of that letter in the same bar prints a courtesy accidental in parentheses.
  - Duplicate pitches in two lanes at one position share the accidental decision, so both copies print it.
- **LS5 leave-out rule:** when a staff's second voice holds only an omitted tied-in piece, keep the two-voice layout for that bar and draw a hidden rest for voice 2, so stems do not flip mid-phrase.

## LS6 rulings: Daniel's answers (2026-09-15)

Daniel's words, verbatim:
- the ask: "I really liked the sheet music, if it could change depending on the key so we dont have a million flats that would be really cool. or have it change and adapt depending on what key the nashville numbers are from after playing."
- LQ1 (VexFlow): "Lets use it for a beta build then make our own".
- the key signature: "Auto, after it settles".

- **LQ1 VexFlow: approved for the beta.**
  - Load VexFlow 5.0.0 core pinned from jsDelivr, the same way three.js is loaded. It is the drawer behind the `engrave.js` interface for settled bars.
  - Critic C9 still applies: pin or self-host the Bravura font the page already loads, so the unpinned `@vexflow-fonts` host is never used, and skip Academico.
  - Keep the in-house drawer working behind the same interface. The long-term plan is our own engraver replacing VexFlow ("then make our own"), so nothing outside `engrave.js` may call VexFlow directly.
- **Key signatures follow the key the Nashville numbers use, after it settles.**
  - **Source:** the page's key tracker, the same key that numbers the chords. A manual key lock wins.
  - **Settle gate:** a new signature is adopted only after the tracker has held the new key with lock confidence for at least 2 bars, or 4 s in free time, and never inside an open bar. A key change is written at the next bar line with a double bar, the new signature and a small "→ D♭ major" tag. There are no courtesy naturals in the live strip; the clean copy may add them.
  - **Spelling:** every note is spelled in the signature's key by the one shared accidental-minimising speller (theory TN2 ruling), so accidentals appear only on notes outside the key. Flat keys never show sharps for diatonic notes, and a G♭ passage shows six flats once in the signature, not on every note.
  - **Ambiguity:** while the tracker is unsure (it read "home · D minor" under E♭m11 in Daniel's 2026-09-15 screenshot), keep the last settled signature and spell the outliers with accidentals. Never flip the signature back and forth: at most one signature change per 8 bars.
  - **The existing "now" staff** (`drawStaff` in piano.js) gets the same key signature rule in LS6, so the live staff and the score strip always agree.

## Also for that round

- **Clock going backwards.** A tracker reused after its clock goes back (a replay seek on the lab page) stops its meter, grid and level steps until the clock passes the old maximum. Rule: the lab page and `clean()` build a **new tracker on every seek**, and `beat.js` documents that its clock is monotonic. Add an assertion that throws in tests if time goes backwards.
- **Readout after ×0.5.** It stays null for about 7 s while the slow agent gathers 4 intervals. For LS3 and LS5, the header shows the requested tempo, dimmed, with the word `hold`, until the readout confirms. Never show a blank.
