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

## Also for that round

- **Clock going backwards.** A tracker reused after its clock goes back (a replay seek on the lab page) stops its meter, grid and level steps until the clock passes the old maximum. Rule: the lab page and `clean()` build a **new tracker on every seek**, and `beat.js` documents that its clock is monotonic. Add an assertion that throws in tests if time goes backwards.
- **Readout after ×0.5.** It stays null for about 7 s while the slow agent gathers 4 intervals. For LS3 and LS5, the header shows the requested tempo, dimmed, with the word `hold`, until the readout confirms. Never show a blank.
