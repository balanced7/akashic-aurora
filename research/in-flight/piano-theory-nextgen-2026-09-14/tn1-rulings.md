# TN1 rulings (conductor, 2026-09-14 night)

These rulings answer the open decisions from the TN1 build, repair round and round-2 verifiers (workflow run wf_c49fee45-f3b). Where this file and `theory-nextgen-spec.md` disagree, this file wins for TN1 and later slices.

## Receipts restated

| Receipt | Was | Ruling | Why |
|---|---|---|---|
| NG2 gains | at least 188 windows (568 s) | **Accept the A1-adjusted count.** Count the 8 windows (10.8 s) where the offline engine forces a dominant with no 3rd heard and A1 reads `m7(no3)` in the key as agreement. | Both verifiers call A1 right by ear. The offline reference carries the defect A1 fixes, so the floor measured against it cannot require the defect. |
| NG3 HUD close | at most 70 windows | **At most 75**, counted as the spec counts it (close only when no canvas ALSO shows). Do not tune costs for this receipt. | Every close counted is a same-notes full reading on another root or bass (`Cmaj9/E` against `Em7b13`, 6 against m7 over its bass). Those are honest alternates, not noise. Revisit with Daniel's gold set (ultimate-practice plan #3). |
| NG3 ALSO loss coverage | at least 61 (any length) and 42 (held 1 s) | **A share of losses: at least 90% any length and at least 65% held 1 s.** Round 2 measured 43 of 46 (93%) and 32 of 46 (70%). | The absolute targets assumed 63 losses; A5 and the repair fixed 17. |
| NG3 "0 ALSO names from a colour-tone slash bass" | ♭9, 9, ♯11, ♭13 | **♭9, 9 and ♯11 only.** A former name over its ♭13 bass (`Bbm11/Gb`) is allowed, because the lab table requires it. | The clause contradicted the spec's own lab table. |

## Rules

- **Stacked-4ths band cap: ratified.** Three pitch classes holding bass+5 and bass+10 (D G C) are never *clear*. Record it under A6. It demotes 3 real windows and changes no fixture band.
- **Cluster band: `none`.** When `kind` is `cluster`, `read()` reports `band: "none"`. A cluster makes no chord-name claim, so the HUD must not show a *clear* band beside it. Cluster cases write the ceiling `none`.
- **Corpus edits made without sign-off: ratified in part.**
  - Removing accept names whose notes do not sound (`F13/A`, `G11`, `Cmaj13#11`) is ratified. The same rule applies to the two seed-card accept names round 2 found.
  - The hand values the repair added (16 leaning ceilings, 15 ALSO names, the chip and defect columns) are ratified only after the musical-truth verifier reviews them one by one.
- **Seed cases carry band ceilings and canvas ALSO (spec 2.6).** The runner's HAND list includes seeds, so a gap is reported.
- **Template fallback and `bassMidi`.** When the grammar has no reading, the fallback name must use `opts.bassMidi` when it is given, and never another sounding bass.

## Must-fix before TN2 wires the reader into the page

1. **The 6/9 no-5th voicing.** Root, 3rd, 6th and 9th with no 5th (C E A D, F A D G, Bb D G C, Gb Bb Eb Ab) must read `C6/9` on top, in every key and with no key. The fix must be structural, not a cost nudge that flips the 5th-present cases: `Ebm(add11)/Gb` against `Gb6/9` with the 5th sounding must keep its current, verified reading. Add the voicing in all 12 keys, with and without the 5th, to the corpus as strict cases.
2. **`installReader` keeps `Theory.detect`'s info shape (spec 2.2).** When the top reading is rootless, `info.notes`, `info.pcNames` and every field `piano.js` reads (the `spellForKey` path near its line 2077, the chord HUD and the practice-log chord event) stay consistent. A rootless root that does not sound is exposed as an additive field, never by breaking the existing arrays. Add a contract test that runs the page's own consumers of `info` on rootless tops.
3. **Two seed-card accept names** that name a non-sounding 6th are removed.
4. **Seed cases** get band ceilings and ALSO, and the runner checks them.

## Round 4 rulings (2026-09-15, after repair rounds 3-4)

Status after round 4: the full runner gives 6732 passed and 0 failed, the contracts give 6116 passed, and the real-window lane holds 19/19. The musical-truth verifier passes. The code verifier still fails on one contract defect (below).

- **Same-notes twin band cap: ratified.** Two same-notes twins are never *clear* while the other is a reading within 1.5, whichever is on top. The twins are:
  - the Lydian 4 against the gospel 5 over 4, which requires the dominant's 5th and 9;
  - a maj13 with no 9 against its relative minor over its 3rd.

  Why ratified: it is structural, not a cost nudge, and it follows design-engine 9.9 and 5. It moves 8 real windows out of clear and changes 0 tops. Clear-band agreement rises from 0.960 to 0.966, and the voicer's 5-over-4 slots without their 5th stay clear.
- **The doubled-root no-3rd 9 rank rule: ratified.** `C3 G3 C4 D4 Bb4` reads `C9(no3)` (or `Cm9(no3)` where the key gives a minor 3rd) ahead of `Gm(add11)/C` by 0.25. With the root only in the bass (`C3 G3 Bb3 D4`), the reading stays `Gm/C`, ambiguous. The 132 strict cases are ratified.
  - The 12 cases expecting `m9(no3)` where the key's 3rd is minor (for example C G C D Bb in A♭ major) follow A1 and stand for now. They are flagged for Daniel's ear in the gold-set sitting (ultimate-practice plan #3).
- **HUD close for the doubled 9(no3) is `Gm(add11)/C`: accepted for v1.** It follows the 6/9 precedent (close `Am(add11)/C`, with the canvas ALSO beside it). Revisit the closeOf wording with the gold set rather than tuning it now.
- **Must-fix before TN2 (code verifier, round 4).** `detect()` must honour `opts.bassMidi` on its template path. When every listed reading is rootless (chordread.js around lines 652-654), it currently calls `detectTemplates(overBass(notes, bassIn))`. overBass moves nothing when the bass pitch class already sounds above the lowest note, so the template names the chord over a different sounding note. Pin it with a case where the bass pitch class sounds both lowest-but-one and above.
- **Also for that follow-up (cheap, same file):**
  - Runner-up and rootless basses follow the page's ODD spelling rule: never B♯, E♯, C♭ or F♭ unless the key's scale has them. This covers `G#7b13/B#` at bias 1 and the off-key runner-up basses (`Am7b5(11)/E#` in B♭).
  - A result whose kind is `cluster` reports band `none` on every path, including the all-rootless template path (ruling above).
  - The root-position aug(add9) (`C3 E3 G#3 D4`) should list `C+(add9)` among its readings.

