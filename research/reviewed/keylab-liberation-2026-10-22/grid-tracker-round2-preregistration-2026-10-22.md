# Pre-registration, round 2 (DRAFT v2, 2026-10-23): trackers that hold REAL bass and beat beat_a loop by loop

**Status: a draft awaiting Daniel's approval.** No round-2 contestant exists yet. v1 of this draft was reviewed by
three adversarial critics, who found four blockers. Their full findings are in workflow run wf_5f8f4610-b26 and
are summarised under "What the review changed". The measuring tools were then rebuilt to match (commits 8fcb8998,
99bc103a, 8fd3ca65, 638ac626: 65+ new pins, mutation-checked, and a second independent check).

## In plain words (read this first)

- **F:** the share of beats a tracker lights within 70 ms of the real beat.
- **CMLt:** the share of the song where it stays locked on the right beat at the right speed. F cannot see a
  half-speed or double-speed lock; CMLt can.
- **pred_hit:** the share of the tracker's PREDICTIONS that land within 35 ms. These are the beats the pads
  actually light from.
- **Grid steadiness:** how much the time between the beats it reports wobbles. It is measured from the beat
  times, not from the BPM number it displays, so smoothing the display cannot fake it.
- **Seeded:** the tracker was told the song's BPM by a database first, as happens live.
- **Paired:** both trackers are scored on the same loops and compared loop by loop.

## Daniel's words, verbatim

- On the round-2 bar (bright-bass rows, a loop-by-loop comparison on a bigger sample, beat_w first): "2. lets try
  that"
- On recording real tracks: "3. most definitely ^__^" and "spotify"
- His ear check of the first reference grid (2026-10-23): "in the beginning the metranome lagged, then it synced
  up perfectly at 11 seconds it was dead, then during the quiet bit it stopped the trusted bpm and kept hunting,
  and started too early. it was almost completely out of phase for the whole section till end when it accidentally
  synced up at 1:04" and "the click kept playing throuought it just was hunting during the quiet part"
- "hitting the same bpm twice should re-enforce something, do we have any way to get a good guesser of how on beat
  we are?"
- "I can also slide a fader to correct!" and "or i can just tap the pad at the bpm"
- Ideas for contestants: "loops of beat detetctions ... we could break down beat detection by frequency as well
  perhaps"; "If we could somehow convert the audio to midi data, realtime audio chord analysis could really help us
  match beat events to rythm and flow"
- Round 1's question (waive the BPM-spread clause so beat_w ships) was **not answered**, so beat_a stays the default.

## What round 1, the live tests and the review taught

- **beat_w leads on the bench but not on real music.** It passed every synthetic row and beat beat_a's F and CMLt
  on all six loop classes, but failed the spread clause. Live on hardstyle it wandered (Hard Driver: 105-214
  BPM).
- **Every tracker fails a bright (sawtooth) bass.** beat_g and beat_w light the off-beat; beat_h locks at half
  tempo, with CMLt 0 in every case.
  - Heimdall's finding: a bright bass puts its harmonics where every accent rule looks for a hat, so the beat must
    come from REGULARITY over bars, not spectrum.
- **Real songs re-enter after a breakdown at a phase of their own,** so one grid per song is the wrong answer key.
  Daniel's ear caught it: Hard Driver jumps about 150 ms across its quiet part.
- **The live loop was dropping about 15 % of the audio** (fixed in c78e0288).
  - It fed every tracker holes that look like phase jumps, and scrambled the clock of the 1,115-tap session.
  - That session therefore cannot be an answer key; taps are re-collected after the fix.
- **v1's bar had four blockers:**
  - it never scored predict(), the thing the pads use;
  - the spread clause could be gamed by smoothing the displayed BPM;
  - its ±.02 margins were smaller than the noise, so even a clearly better tracker failed about 100 % of the time;
  - the held-out loops were not frozen.

## The bar (a contestant ships only if ALL rows hold)

| row | command (`py -m arsenal.keylab beatbench ...`) | criterion |
|---|---|---|
| drift, sine | `--suite drift` | means: F ≥ .85, CMLt ≥ .75, grid steadiness (ibi_spread) ≤ .02, ibi_flips ≤ .5, pred_hit ≥ .85; every case F ≥ .70 and CMLt ≥ .60 |
| drift, bright (NEW, public) | `--suite bright` | the same |
| drift, bright variants (NEW, HIDDEN) | `--suite bright_variants --variant-seed <secret>` | the same. The seed is committed below as a sha256 and revealed only at scoring |
| shift | `--suite shift` | means: F ≥ .85, CMLt ≥ .75, relock ≤ 4.0 s, never relocked = 0, pred_hit ≥ .80; every case F ≥ .70 |
| synthetic | `--suite synthetic` | means: F ≥ .95, CMLt ≥ .85, pred_hit ≥ .85; every case F ≥ .60 (drums_70's octave is genuinely ambiguous) |
| loops, paired, held out (REPLACES v1) | `--suite loops --manifest <frozen> --seeded --trackers a,<c> --vs a` | POOLED over the 6 groups (kick / tops / melodic × unseeded / seeded), with a pack-clustered 95 % bootstrap: lower bound of the mean per-loop difference (contestant − beat_a) ≥ −.02 for F, CMLt and pred_hit; each group's lower bound ≥ −.10 (no category much worse); pooled upper bound of the ibi_spread difference ≤ +.01 |
| real songs (NEW) | `--suite real --since <commit time> --vs a` | gates once ≥ 5 songs have confirmed answer keys: means F ≥ .80, CMLt ≥ .70, pred_hit ≥ .70; every song F ≥ .50 and CMLt ≥ .40 |
| speed | `--suite synthetic`, best of 3, CPU time with predict() every block | cpu_x_min ≥ 20 |
| contract | — | the strict check_tracker() == [] (predict required; finite bpm on every observed beat) |
| firewall | — | stdlib + numpy + scipy only, plus the stricter AST scan |
| honesty | — | causal; no bench constants; every tuning source disclosed; only the named trackers are imported |

**The firewall has a known blind spot.** Dynamic access (getattr chains, builtins reached through frames)
evades the AST scan. It guards against drift, not sabotage. Contestants are built by house agents whose
transcripts can be audited.

**What the paired loop row demands, measured before any contestant exists.** These come from round 1's per-loop
beat_w − beat_a differences: F SD .31, CMLt SD .40, n = 354, resampled at 100 loops × 6 groups.

| true mean difference vs beat_a | F passes | CMLt passes (with the group guard) |
|---|---|---|
| −0.03 (worse) | 1 % | 0 % |
| 0.00 (equal) | 29 % | 9 % |
| +0.03 | 96 % | 52 % |
| +0.05 | 99 % | 79 % |

In words: to replace the default, a tracker must be genuinely better, by about +.05 on CMLt. An equal one usually
does not ship, and a worse one essentially never does.

**Answer keys for real songs.** Sources, in order of trust:
1. Daniel's TAPS, from `beat --save --hand` after c78e0288, so the clock is sound. A stretch needs ≥ 8 steady taps
   and jitter ≤ 40 ms. The tap-to-kick offset is reported, not applied, unless Daniel decides it should be.
2. An offline reference grid that Daniel ear-confirmed by picking among its listed tempo candidates.

Every recording must carry its timing record (no capture gap). Only songs recorded after this bar is committed
count. The set freezes when the last contestant is submitted.

## Hidden seeds (committed now, revealed at scoring)

Drawn 2026-10-23 and kept in state/ (gitignored). Each hash is sha256 of `<name>=<seed>;salt=<salt>`.
- bright_variant_seed: `71a29356591164c2f1902b35d5739a84ecd54682fdd5d6b5c983e248e4148c09`
- loops_seed: `d08cbe25ca025e64a375e391b5f5b2263b6ca679893403c588a6149f54853866`

**The held-out loop manifest** is drawn at loops_seed with `--per-cat 100 --exclude-receipts` set to the two
round-1 receipts (188 loop names excluded; deduplicated by content), written with `--write-manifest` to state/,
and its sha1 is added to this record before any contestant is scored.

## Contestants (blind to each other; each with an adversarial auditor; Vandor scores, Heimdall re-runs)

- **w2: beat_w revised, the leader first.** Targets:
  - the bright-bass phase, keyed on regularity over bars;
  - grid steadiness;
  - predict() that stops within ~2 s of silence;
  - re-catching the beat after a breakdown (a phase jump at the same tempo);
  - the slow-tempo prior.
- **l1, l2: Daniel's "loops of beat detections, broken down by frequency"** (two independent builds).
  - A comb-filter bank per band (concurrent loops at each candidate beat and bar length). The loop memory is the
    averaged beat or bar, and the beat phase is read from it.
  - Bands vote by their regularity.
  - The harmonic/percussive split is stated honestly: it helps against SUSTAINED bass and chords only. A bright
    bass's attacks still count as hits, so the bright rows must be won by regularity.
  - At least one build reports with and without the chord cue (chordsense, the chord-change bar-line cue), as an
    observation row, so Daniel's chord idea gets a number.
- **beat_g and beat_h** may be revised by their authors (optional).

## Observation rows (reported, not gating)

- The referee's on-beat score against each answer key: is the live meter honest?
- The display BPM steadiness (bpm_spread).
- Bright bass low-passed.
- The off-bench variants.
- With/without chroma.

## Questions only Daniel can answer before this is committed

1. **Gate the DISPLAYED BPM number too?** It is reported but not gated. Gating it would ask that the number on
   screen stay steady, not just the lights.
2. **Pack clusters for the bootstrap.** The finest folder is used now. Using the top pack folder would be
   stricter, with wider intervals.
3. **The +.05 CMLt bar.** Is "must be clearly better to replace the default" the bar you want, or should an
   equal-but-steadier tracker be allowed to ship?
4. **Approve the bar.** Contestant builds start only after this record is committed as approved.

## What the review changed (v1 → v2)

| v1 problem | v2 answer | commit |
|---|---|---|
| predict() never scored | pred_hit gated in every row; predict() required | 8fcb8998 |
| BPM spread gameable through the display | grid steadiness from beat times; display reported only | 8fcb8998 |
| ±.02 per group on n≈100 (equal passes 5-12 %, +.05 passes rarely) | pooled pack-clustered bound with per-group guards; pass rates measured above | 8fcb8998 + this record |
| held-out loops not frozen; duplicates; a capped, drifting pool | whole-index pool, content dedupe, exclusion by receipt names, a frozen manifest, a hidden seed | 8fcb8998, 8fd3ca65, 638ac626 |
| fit_grid answer keys wrong on round-2 music | tap keys first; fit_grid lists candidates and is ear-confirmed; recordings with gaps refused | 8fcb8998 |
| real-song set could leak or be confirmed after scoring | since-filter on capture time; set frozen at the last submission | 8fcb8998 |
| one bright timbre, learnable | hidden-seed bright variants (5 timbres, glides, on-beat bass, sidechain, random start) | 8fcb8998 |
| mean-only rows hid a failed case | per-case floors | this record |
| speed measured loosely | CPU time with predict() every block, named run, best of 3 | 8fcb8998 + this record |
| contestants imported into the scorer | only the named trackers imported; stricter AST firewall (blind spot stated) | 8fcb8998 |
