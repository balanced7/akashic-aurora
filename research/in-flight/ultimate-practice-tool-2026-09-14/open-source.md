# Open-source and research projects for the ultimate practice and jam tool

Filed 2026-09-14 by a research seat for Vandor. This is research only: nothing was downloaded, installed or run, no servers or browsers were started, and no code under `arsenal/` was changed. Each fact comes from a web page read tonight and is cited. Wording is paraphrased, with at most a short phrase quoted.

Daniel asked on Discord: "I wonder how we can make this be the ultimate practice / jamming tool, are there any other projects that are similar that we could look at for features we can integrate? Any ideas on how to improve chord accuracy? I also love how our system shows you the chord for notes arpegiated with sustain! What other detections or analysis do you think would be really cool to display?"

This lane covers **open-source and academic projects** only: visualizers, symbolic chord recognition, harmonic analysis, accompaniment and jamming, and beat tracking from MIDI. Other lanes cover commercial apps and the house's own designs.

Confidence labels: **high** means the primary page (repo, paper abstract or PyPI) was read tonight. **medium** means a search summary or secondary page. **low** means inference, or a detail that was not checked.

---

## 0. The answer in one screen

1. **No open project does what ours does live.** The strong research chord recognisers all work offline, on quantised scores or MusicXML: BACHI (ICASSP 2026), the Harmony Transformer, AugmentedNet and ChordGNN. None reads unquantised, pedalled, arpeggiated playing as it happens. Our live reader (theory-nextgen `chordread.js` + `harmony.js`) is already in rarer territory than any repo found. Their value to us is **ideas and a yardstick**, not code to drop in.
2. **The biggest chord-accuracy win is a benchmark, not a model.** Score our reader against human-corrected piano data: POP909-CL (MIT, pop piano, about 35% of the original POP909 chord labels fixed by musicians) and When in Rome (CC BY 4.0, over 2,000 classical analyses). Use BACHI's released weights (MIT code) as an offline second opinion on Daniel's own practice log. After that, "improve chord accuracy" becomes a number that moves.
3. **Three published ideas map straight onto our reader's cost function:**
   - segment **purity and coverage** (Masada and Bunescu's semi-CRF);
   - **boundary first, then root, then quality, then bass** (BACHI, which models it on ear training);
   - a **non-chord-tone filter** before naming (AnalysisGNN, 2025).
   Section 2 turns each into a concrete change.
4. **The best jam UX finding in the literature is ReaLJam (CHI 2025).** Upcoming chords fall toward the keys about 4 beats ahead. **Committed** chords are drawn solid and **tentative** ones translucent, and the commit window is a user setting. Users strongly disagreed about the best settings, so the knobs matter. The code is MIT and ships a web client, a server and checkpoints (realchords-pytorch). This is a direct upgrade for our Try ghosts and suggestion chips.
5. **Detections worth displaying that research already computes** (section 3):
   - a **tonal tension ribbon** (spiral array, in partitura, Apache-2.0);
   - a **consonance and roughness meter** (incon, MIT, 18 models);
   - **melodic surprise** (IDyOM information content, GPL: take the idea, not the code);
   - **cadence detection**, and **named progression idioms** in the style of Impro-Visor's "bricks";
   - **Tonnetz moves** (P, L, R);
   - **performance qualities**: PercePiano's 19 perceptual labels such as pedal clean or blurred, timing stability and articulation (MIT);
   - **beats and hand split from free playing** (PM2S, MIT);
   - **"how common is this progression"** from Chordonomicon (666k songs, but CC BY-NC).
6. **Following the player is solved research, as score following.** CPJKU's Matchmaker (Apache-2.0, ISMIR 2025) and the ACCompanion (Apache-2.0 code, non-commercial models) follow a pianist's tempo live. Free-form online beat tracking from MIDI with no score has no mature open implementation; the audio trackers (BeatNet, BEAST) don't take MIDI. The jam spec's v2 "Follow me" should be built in-house from the published methods (section 5).
7. **Licences matter because Akashic Aurora is a public Apache-2.0 repo.**
   - We can port or vendor MIT, BSD or Apache code: music21, partitura, pretty_midi, symusic, tonal, BACHI, PM2S, realchords-pytorch, Notochord, Aria, TonnetzViz, incon.
   - GPL projects are **study-only**: Neothesia, PianoBooster, Impro-Visor, Somax2, MMA, MusicLang Predict, IDyOM, and the BPS-FH dataset itself.
   - Non-commercial data and models stay **local and unshipped**: Chordonomicon, Hooktheory, the DCML corpora, PIG fingering, and the ACCompanion and madmom models. TikTok monetisation is an open question for these (section 9).
8. **Skip list:**
   - Magenta RealTime 2: audio only, and real-time needs Apple Silicon.
   - magenta.js: the npm package has not been published in years, and the main `magenta/magenta` Python repo was archived in January 2026.
   - Harmony Transformer v2 and ChenSu21: TensorFlow 1, no licence file.
   - ChordGNN: archived June 2026, MusicXML only.
   - Aria's real-time demo: MLX, Apple only.
   The house machine is Windows, AMD GPU, Python 3.11, so any CUDA-only model runs on CPU here.

---

## 1. What we already have (so this file does not re-propose it)

- **Live** (`arsenal/web/piano.js`): chord names that stay steady through pedal and arpeggios, Nashville numbers from a steady key tracker, grand staff, practice log, and Claude's cues.
- **Offline** (`arsenal/practice.py`): key frames and key paths.
- **Band:** FL band and pianocue CLI.
- **Designed:**
  - reader + live harmonic window + 28 scales + function labels (`piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md`);
  - cards, loops, Try, riff reports, `groove.js` with swing and call-and-response, and a v2 "Follow me" that takes loop tempo from his first bars (`piano-jam-2026-09-14/jam-spec.md`);
  - rarity tiers (`piano-spectacle-2026-09-13`);
  - chord suggestions and key lights, with Piano LED Visualizer and Synthesia protocols already researched in `key-lights.md`;
  - song key and BPM from audio, with madmom and BeatNet already assessed in `live-key-bpm.md` (`practice-along-2026-09-14`).
- A Heimdall idea already proposed a circle-of-fifths wheel view (`piano-ideas-2026-09-13/heimdall-deepseek.md`). The Tonnetz below is its companion, not a repeat.
- The local inventory says `music21` and `pretty_midi` are not installed (`fl-jam-bridge-2026-09-14/local-inventory.md`). Anything Python-side below needs an approved install.

---

## 2. Chord accuracy: what research knows, and what to steal

### 2.1 The landscape

| Project | What it does | Licence | Maturity, recency | Fit for us | Conf. |
|---|---|---|---|---|---|
| **BACHI** ([paper](https://arxiv.org/abs/2510.06528), [code](https://github.com/AndyWeasley2004/BACHI_Chord_Recognition)) | Symbolic chord recognition. Finds chord **boundaries**, then iteratively ranks **root, quality, bass** with masked decoding, which the authors liken to ear training. State of the art on pop and classical. | Code MIT | ICASSP 2026. PyTorch 2. Weights on Hugging Face: a classical model (When in Rome + DCML) and a pop model (POP909-CL). **Offline only.** Input is beat-quantised (12 ticks per quarter by default) and limited to piano range 21-108. Output lines look like `C_M_C` (root, quality, bass). | Offline **judge** for practice-log sessions once they are quantised against the tempo map. Its decision order is a design cue for the live reader. | high |
| **POP909-CL** ([repo](https://github.com/AndyWeasley2004/POP909-CL-Dataset)) | POP909 with human-corrected chords, beats, keys and time signatures. About 35% of chord labels and 40.6% of start beats were fixed. | MIT | Released with BACHI. 909 songs. | **The** pop-piano benchmark for our reader. | high |
| **POP909** ([repo](https://github.com/music-x-lab/POP909-Dataset)) | 909 pop songs as melody, bridge and piano tracks, with beat, chord and key files. The original labels were largely algorithmic. | MIT | 2020 | Use the CL version for accuracy work. | high |
| **Semi-CRF chord recognition**, Masada and Bunescu ([TISMIR 2019](https://arxiv.org/abs/1810.10002), [code](https://github.com/kristenmasada/chord_recognition_semi_crf)) | Segments and labels together. Its **segment-level features** measure how pure a span is (few notes outside the chord) and how completely the chord's notes are covered. Tested on classical corpora and a rock corpus. | Code licence not checked | 2017-2019, research code, MusicXML | **Ideas only**: purity and coverage as reader cost terms. | high (paper); low (code licence) |
| **Harmony Transformer v2** ([repo](https://github.com/Tsung-Ping/Harmony-Transformer-v2)), **ChenSu21** ([repo](https://github.com/napulen/ChenSu21)), [TISMIR 2021](https://transactions.ismir.net/articles/10.5334/tismir.65) | Chord segmentation inside a transformer. Covers the 24 major and minor chords and Roman numerals on BPS-FH. | No licence file in either repo | TensorFlow >= 1.8, inactive | Skip the code. The joint segmentation idea is covered by BACHI. | high |
| **BPS-FH** ([repo](https://github.com/Tsung-Ping/functional-harmony)) | Beethoven's 32 sonata first movements, with key, degree, quality, inversion and Roman numeral labels plus beats and phrases. | **GPL-3.0** (data) | Stable | Local test set only; never commit it into the repo. | high |
| **AugmentedNet** ([repo](https://github.com/napulen/AugmentedNet)) | CRNN for Roman numerals: key, degree, quality, inversion. Trained with **synthetic block-chord** augmentation and a pitch-spelling input. | MIT | v1.9.1, Dec 2022, MusicXML in | Idea: synthetic augmentation, which our fixture generator can copy (2.2 d). | high |
| **ChordGNN** ([repo](https://github.com/manoskary/ChordGNN)) and **AnalysisGNN** ([CMMR 2025](https://arxiv.org/abs/2509.06654)) | Graph networks over individual notes, with onset-wise Roman numeral output. AnalysisGNN adds a **non-chord-tone prediction** step that filters notes before analysis, and trains across differently labelled corpora. | ChordGNN MIT; AnalysisGNN code not stated | ChordGNN **archived 2026-06-11**. AnalysisGNN is Sept 2025. | Idea: filter passing and neighbour tones before naming. | high |
| **When in Rome** ([repo](https://github.com/MarkGotham/When-in-Rome), [TISMIR](https://transactions.ismir.net/articles/10.5334/tismir.165)) | Meta-corpus of more than 2,000 human functional analyses of about 1,500 works, in RomanText, with a "spell checker" for analyses. | CC BY 4.0 | Maintained | Classical benchmark for the function labels (TN series). | medium |
| **DCML ABC and Distant Listening Corpus** ([ABC](https://github.com/DCMLab/ABC), [DLC](https://github.com/DCMLab/distant_listening_corpus)) | Expert harmony labels. The DLC has 1,283 pieces with Roman numerals, keys, **phrases and cadences**. | CC BY-NC-SA 4.0 | Curated, reviewed | Local benchmark for cadence detection (section 3). | medium |
| **ChoCo** ([repo](https://github.com/smashub/choco)) | 20,080 JAMS files merging 18 chord datasets (Harte chord syntax, keys). | Mostly CC BY 4.0; the Chordify, Mozart sonata and jazz-aligned parts are CC BY-NC-SA | 2023, stable | Cross-genre chord **vocabulary** and a progression-statistics source. | high |
| **music21** ([repo](https://github.com/cuthbertLab/music21), [releases](https://github.com/cuthbertLab/music21/releases)) | Toolkit: Krumhansl-Schmuckler key finding, a floating key over a measure window (4 measures by default), chord naming, Roman numerals. | BSD-3 | **v10.5.0, 2025-06-17**, Python 3.11-3.14, which matches the house 3.11 pin | Offline reference namer for disagreement tests. | high (release); medium (window default) |
| **partitura** ([repo](https://github.com/CPJKU/partitura), [PyPI](https://pypi.org/project/partitura/), [analysis API](https://partitura.readthedocs.io/en/latest/modules/partitura.musicanalysis.html)) | `estimate_key`, `estimate_spelling` (ps13 pitch spelling), `estimate_voices`, `estimate_tonaltension`, `estimate_time` (tempo, meter numerator, beats), performance encoding. MIDI and MusicXML I/O. | Apache-2.0 | **1.9.0, 2026-05-25**, Python 3.10-3.12 | Pitch spelling and voice separation as offline yardsticks; tension (section 3). | high |
| **tonal** ([repo](https://github.com/tonaljs/tonal)) | TypeScript theory library. `Chord.detect` turns a note list into ranked chord names. | MIT | Maintained, npm | Cheap third opinion in node receipts (needs an npm install). | medium |

### 2.2 Six changes that follow from the research

Each one names where it would land in the existing specs. None needs a model at runtime.

**a. Add segment purity and coverage to the reader's cost** (from the semi-CRF). The theory-nextgen reader scores a window's notes against readings. The semi-CRF shows two segment-level features that carry much of the accuracy:
- **purity**: the share of sounding weight, salience-weighted, that falls on the reading's chord tones;
- **coverage**: the share of the reading's required tones actually present in the window.

Pedalled arpeggios are exactly where these help. A pedal wash has high coverage but lower purity because of passing tones, and the cost can tolerate that on purpose. Landing: reader cost terms, with receipts on the `window_sessions` fixtures (spec 2.6).

**b. Decide in BACHI's order: boundary, root, quality, bass.** BACHI's ablations support solving these as separate steps rather than one joint label. Our live window already decides boundaries (the H-series split rules). The change is inside the reader: settle the **root** first, with bass, salience and the previous-root prior; then **quality** given that root; then **bass** or inversion. This cuts the combinatorial confusions such as `F/G` against `G9sus4` (spec 2.1 lists that pair as ambiguous). It also gives a display idea for free (3.1, "lock-in").

**c. Filter non-chord tones before naming** (AnalysisGNN, and classical analysis practice generally). Classify each note in the window as a chord tone or an ornament before the reader sees it. Cues that research models use and our data already has:
- duration relative to the window;
- stepwise approach and departure;
- metric position against the tempo map, when a jam run is active;
- velocity relative to the hand's median;
- whether the pedal is holding it past its key release.

Down-weight, don't delete: the salience input (`design-engine.md` 4.2) is the hook. This mainly helps melody notes on top of pedalled left-hand harmony, which is Daniel's signature texture.

**d. Generate training-style fixtures from his voicings** (AugmentedNet's synthetic block chords). AugmentedNet gained accuracy from synthetic chord templates. Our version: render every reading in the chord grammar through Daniel's timing profile. That means arpeggio orders, the 190/250/400 ms note-gap quartiles, pedal-down share, and a melody note added above. Feed the result to the reader as an exhaustive property test. It grows the frozen TN0 corpus without hand labelling. The corpus is frozen, so this goes through the conductor as an addition.

**e. Separate the hands and voices before reading** (PM2S predicts hand parts; partitura has `estimate_voices`). A melody in the right hand should inform the key and function labels but mostly stay out of the chord name. Offline, PM2S (MIT) can label hands in practice-log sessions. Those labels become ground truth to tune a cheap live split rule, such as a register gap plus a top-voice continuity score. Live, this needs no model.

**f. Measure it** (this makes the other five provable).
- A `practice.py`-side benchmark verb scores the reader on POP909-CL and When in Rome.
- Metrics follow MIREX-style chord evaluation: root, major/minor, sevenths, bass, and segmentation.
- Plus a **session agreement** score against BACHI on Daniel's own logged sessions, after quantising through the tempo map or PM2S.
- Report disagreements as a ranked list of moments for Vandor to listen to: a judge, not an oracle.
- Needs approved downloads: the POP909-CL repo, When in Rome, BACHI weights, and PyTorch 2 on CPU. Sizes were not checked (low).

### 2.3 Honest limits

- Every model above trains on **scores or quantised MIDI**. Daniel plays rubato with the pedal down. Their accuracy numbers will not carry over to live readings, and BACHI's own README limits input to beat-aligned piano rolls (high).
- Functional (Roman numeral) recognition is much harder than root and quality. Published composite scores stay well below chord-symbol scores ([TISMIR 2021](https://transactions.ismir.net/articles/10.5334/tismir.65)). Keep function labels confidence-gated, as the theory spec already does.
- No 2025-2026 **streaming** symbolic chord recogniser with public code turned up in this search. The closest causal MIDI model is Notochord (section 4), which generates rather than analyses (medium: absence of evidence).

---

## 3. Detections and analysis worth displaying

Each item is something an open project or paper already computes, reframed as a thing on screen. Cost is rough: **S** is an afternoon in JS, **M** is a build slice, **L** needs a model or dataset.

### 3.1 Harmony

| Display | Source | What Daniel would see | Cost | Licence path |
|---|---|---|---|---|
| **Tension ribbon** | Spiral-array tonal tension in partitura, `estimate_tonaltension` ([API](https://partitura.readthedocs.io/en/latest/modules/partitura.musicanalysis.html)). The three ribbons in the original Herremans and Chew model are cloud diameter, cloud momentum and tensile strain (medium: from the original paper, not re-read tonight). | A thin glowing line above the staff that rises as harmony pulls away from the key and falls on resolution. It makes the "lush but going home" arc visible, and suits TikTok. | M | Apache-2.0; port the math to JS with attribution |
| **Consonance and roughness meter** | incon ([repo](https://github.com/pmcharrison/incon)): 18 consonance models, including Hutchinson-Knopoff roughness and Harrison-Pearce harmonicity; input is MIDI pitch sets. | A small meter per chord, from sweet to crunchy. Register matters: the same chord voiced low reads rougher, a real effect his voicings exploit. | S (one roughness model in JS) | MIT (R); port one model |
| **Chord lock-in sequence** | BACHI's boundary, root, quality, bass order (2.2 b) | On a new window, the label assembles in that order: root letter first, then quality, then the slash bass. It mirrors how an ear player hears it. | S | idea only |
| **Named progression idioms ("bricks")** | Impro-Visor's roadmaps chunk chord progressions into named bricks and draw them over the lead sheet ([repo](https://github.com/Impro-Visor/Impro-Visor)) | Captions like "ii-V-I into 4", "turnaround", "backdoor", "deceptive" under the Nashville row as he plays. Complements the function labels with the words players use. | M | GPL-2.0: write our own brick table, do not copy its dictionary files |
| **Cadence detector** | Cadence labels in the DCML Distant Listening Corpus ([repo](https://github.com/DCMLab/distant_listening_corpus)); AnalysisGNN's multi-task analysis | A one-word banner on arrival: authentic, half, deceptive, plagal. It fits the spectacle rarity tiers as its own event type. | S rules; M to benchmark on DLC | Rules are ours; DLC is NC (local test only) |
| **Tonnetz moves** | TonnetzViz, a web MIDI Tonnetz ([repo](https://github.com/cifkao/tonnetz-viz), [live](https://cifkao.github.io/tonnetz-viz/)) | Each triad is a triangle on the lattice. Moving to the next chord highlights the flip and names it: **P** (major to minor on the same root), **R** (to the relative), **L** (leading-tone exchange). It shows why his favourite moves feel smooth: one note moves. | M | MIT |
| **"How common is this progression"** | Chordonomicon ([HF](https://huggingface.co/datasets/ailsntua/Chordonomicon), [paper](https://arxiv.org/abs/2410.22046)): 666k songs with genre, section labels and Spotify IDs. Also ChoCo (mostly CC BY). | A rarity score for the last 4 chords ("1 in 40 songs", "rare in pop, common in gospel"). It could feed spectacle rarity with a real-world prior instead of hand tiers. | L (offline n-gram table) | **CC BY-NC 4.0**: compute locally, never commit the data; the derived table's status is an open question (section 9) |

### 3.2 Melody and time

| Display | Source | What Daniel would see | Cost | Licence path |
|---|---|---|---|---|
| **Melodic surprise** | IDyOM ([repo](https://github.com/mtpearce/idyom), [site](https://mtpearce.github.io/idyom)) models listener expectation with variable-order Markov models and gives each note an **information content** and **entropy**. Python routes: IDyOMpy, py2lispIDyOM ([JOSS](https://joss.theoj.org/papers/10.21105/joss.04738)). | A spark on notes that are surprising **for him**, from a model trained on his own practice log, plus a calm or unpredictable meter for the moment. "You did something new" is a natural cue for Claude. | M (a small PPM-style model in JS or Python, our own) | GPL, Common Lisp: reimplement the published method |
| **Motif and riff recurrence** | SIATEC repeated-pattern discovery; ostinato is an MIT Python implementation but immature (1 star) ([repo](https://github.com/pauldhein/ostinato)) | Offline in the riff report: "this figure came back 5 times, twice transposed up a 4th." It ties into jam riff reports. | M | MIT idea; write our own |
| **Beats, bar lines and rubato curve from free playing** | PM2S ([repo](https://github.com/cheriell/PM2S), [ISMIR 2022](https://archives.ismir.net/ismir2022/paper/000047.pdf)): beats, downbeats, time and key signatures, **hand parts** and quantisation from performance MIDI. Also Murgul and Heizmann's transformer beat tracker for performance MIDI ([SMC 2025](https://arxiv.org/abs/2507.00466)), and partitura `estimate_time`. | In the practice log: bar lines under a free improvisation, a tempo curve showing where he breathes, a swing ratio, and left and right hands coloured apart. | L offline (PyTorch 1.12 pins are old; needs its own venv) | MIT |
| **Performance qualities** | PercePiano ([repo](https://github.com/JonghoKimSNU/PercePiano), [Sci. Reports 2024](https://www.nature.com/articles/s41598-024-73810-0)): 19 expert-rated perceptual features in 8 groups, such as timing stability, articulation short or long, pedal sparse or saturated and clean or blurred, dynamic range. Profy ([June 2026](https://arxiv.org/abs/2606.10627)) shows feedback works when **localised** to passages with evidence, not as global scores. | Practice-log cards: "pedal blur rose in bars 12-16" (non-chord tones overlapping under the pedal), "arpeggio velocities evened out since last week", each with a replay link to the exact moment. Use PercePiano's labels as the vocabulary; compute simple features ourselves. | M | MIT (labels as vocabulary; no trained weights are shipped) |
| **Fingering hints on Try ghosts** | pianoplayer ([repo](https://github.com/marcomusy/pianoplayer)) finds low-effort fingerings for MIDI and MusicXML; the PIG dataset is research-only ([site](https://beam.kisarazu.ac.jp/~saito/research/PianoFingeringDataset/index-ja.html)) | Small finger numbers on ghost notes for a card he is learning. Low priority for an ear player; useful for dense voicings. | M | MIT code; PIG non-commercial |
| **"Sounds like" style tag** | Aria ([repo](https://github.com/EleutherAI/aria)): a 1B piano model trained on about 60k hours, with an **embedding** checkpoint for classification | A session-level tag in the practice log (ballad, gospel, impressionist). Offline only here: CUDA or MLX, and this box is AMD on Windows, so CPU. | L | Apache-2.0 code and weights (conflict: the Aria-Duet paper page lists CC BY-SA 4.0, likely the paper's own licence; low) |

---

## 4. Jamming and accompaniment: projects to learn from

### 4.1 Real-time partners (research)

- **ReaLJam and ReaLchords.** [ReaLJam, CHI EA 2025](https://arxiv.org/html/2502.21267); [ReaLchords, ICML 2024](https://arxiv.org/abs/2506.14723); code: [realchords-pytorch](https://github.com/lukewys/realchords-pytorch), MIT. High confidence.
  - **Setup.** The user plays melody from MIDI or the computer keyboard, and the agent answers with chords. The client talks to a model server and keeps playing cached chords to hide the round trip.
  - **Display.** Upcoming chords fall toward the keyboard as a **waterfall** about **4 beats** ahead: solid inside the commit window, translucent beyond it where the model may still revise. The commit window was tested at 0, 2 and 4 beats.
  - **Findings.** The RL-tuned model beat the pretrained one by a wide margin. Participants disagreed about showing chords, the metronome and commit length. Their enjoyment did not always follow the musicality metrics.
  - **What the repo ships.** Server and web client, checkpoints on Hugging Face, and training on Hooktheory, POP909, Nottingham and Wikifonia. Training needs a 48 GB GPU; inference cost is not stated.
  - **Steal.**
    1. The solid-versus-translucent split for our **incoming ghosts** in Try and for suggestion chips.
    2. A per-player **commit window** setting.
    3. Settings exposed rather than fixed, because the study found tastes differ.
    4. As a model: an optional "Claude answers your melody with chords" mode run as a separate local process. It runs on CPU here (low: speed unknown).
- **Streaming accompaniment trade-offs.** [Wu et al., Oct 2025](https://arxiv.org/abs/2510.22105). Seeing further ahead improves coherence but demands faster inference. Bigger output chunks help throughput but hurt responsiveness. Plain maximum-likelihood training is not enough for live jamming. High. **Lesson for `groove.js`:** our "one bar plus pickups" hand-off is the chunk-size knob. Keep reactions (duck, stop, next) outside the chunk, as jam-spec C3 already does.
- **StreamMUSE.** [RTAS 2026](https://arxiv.org/abs/2606.11886). A client-server framework for language-model jamming that models latency from system settings and finds real-time performance tracks music quality. Code is on the project page, licence not checked. Medium. It confirms the spec's "page keeps time" choice.
- **Aria-Duet.** [Nov 2025](https://arxiv.org/html/2511.01663); [Aria repo](https://github.com/EleutherAI/aria), Apache-2.0.
  - **Hand-off.** The pianist hands off by pressing the **una corda (left) pedal**, and takes the turn back with the same pedal.
  - **Latency.** Continuous prefill updates the model's cache during his playing, removing a 1-2 s delay.
  - **Hardware.** Runs on Apple Silicon with a Disklavier.
  - **Steal.** A **pedal or pad as the turn-taking gesture** for call and response (jam-spec 5.10 currently uses fixed call bars). Whether the KeyLab 88 mk3 has a spare pedal input free for this was not checked (low).
- **Notochord.** [repo](https://github.com/Intelligent-Instruments-Lab/notochord), MIT; [IIL page](https://iil.is/research/notochord). A causal MIDI model that makes one event at a time with little delay and allows constraints on pitch, time, velocity and instrument. It ships a harmonizer and the Homunculus terminal app (ICMC 2025). No latency figure is published. Medium. A lightweight candidate for "Claude improvises a counter-line" if a model voice is ever wanted.
- **Somax2.** [repo](https://github.com/DYCI2/Somax2), GPL-3.0. IRCAM's corpus-based co-improviser. It listens to MIDI or audio and answers in the style of a loaded corpus, and needs Max 8.6+ or 9 on Windows 10+. High. Idea: **Daniel's own practice log as the corpus**, so the partner "plays like you". Study-only because of the GPL and the Max dependency.
- **Structure-aware piano accompaniment.** [Feb 2026](https://arxiv.org/abs/2602.15074). A small transformer plans a per-measure style from the phrase structure and functional harmony. A retriever then picks human-played piano patterns, scored on harmonic fit, voice-leading continuity, style consistency and structural role. Code not stated. High (abstract). **v2 idea for `groove.js`:** retrieve bars from **his own logged comping**, scored on those four terms, instead of only hand-written groove tables.

### 4.2 Backing-band software (mature, run as separate apps)

- **JJazzLab.** [repo](https://github.com/jjazzboss/JJazzLab), **LGPL-2.1**, Java. Type chord symbols, pick a style, get drums, bass, guitar, piano and strings. It supports live chord edits during playback, song structure with variations, MIDI out to external synths over virtual cables, a loop restart bar and MIDI remote commands (v5.2.x). The latest release seen is v5.2.1 from "April 13"; the year was not checked (low). **Use:** a heavier backing band beside FL over loopMIDI, driven by a card's chords. **Learn:** its song-structure and style-variation model for card sections.
- **Impro-Visor.** [repo](https://github.com/Impro-Visor/Impro-Visor), GPL-2.0, v10.2 from June 2019. Grammar-learned solos, **trading** (call and response against MIDI input), roadmaps and bricks (3.1), guide-tone lines and a voicing editor. High. Study the brick vocabulary and trading modes.
- **MMA (Musical MIDI Accompaniment).** [mirror](https://github.com/infojunkie/mma), GPL. Grooves as plain-text pattern libraries. Medium. It is a proven format for groove definitions, if `groove.js` tables ever move to data files.
- **MusicLang Predict.** [repo](https://github.com/MusicLang/musiclang_predict), **GPL-3.0** code and models. A LLaMA-2-style model trained on Lakh MIDI; chord-conditioned generation with one chord per bar, and it runs without a GPU. Medium. It can draft offline "backing for this card" ideas as a separate process. Never vendor it.

### 4.3 Score following and "follow me"

- **Matchmaker.** [repo](https://github.com/pymatchmaker/matchmaker), Apache-2.0; [ISMIR 2025](https://arxiv.org/abs/2510.10087). Real-time alignment of live MIDI or audio to a score. The MIDI default is a pitch-based HMM, with online time-warping variants available. Python 3.10-3.13. High. **Use:** a "play a piece, the page follows you" practice mode: Neothesia's play-along and PianoBooster's "follow you" (4.4), with our visuals.
- **ACCompanion.** [repo](https://github.com/CPJKU/accompanion); [IJCAI 2023](https://arxiv.org/html/2304.12939v2). Apache-2.0 code; **CC BY-NC-SA 4.0** models and data. It plays the accompaniment part while following the soloist's tempo, dynamics and articulation, with a beginner mode where it plays the left hand. Built on partitura, live MIDI input. High. **Learn:** its tempo model is the reference design for jam v2 "Follow me".
- **Free-form beat tracking with no score** is where open code runs out. BeatNet and BEAST are audio trackers (see `live-key-bpm.md`). The performance-MIDI trackers (PM2S, Murgul and Heizmann) are offline. **Recommendation for Follow me:**
  1. Seed tempo from the loop's first bars, as designed.
  2. Track it with an onset-interval histogram plus a Kalman or particle filter on his note onsets, weighting bass notes and chord strikes. This is the classic published approach used by BeatRoot-era trackers; low: not re-read tonight.
  3. Never move the bar line more than a set amount per bar.
  4. Validate offline against PM2S beats on his logged sessions.

### 4.4 Visualizers and practice apps

| Project | What to learn | Licence, recency | Conf. |
|---|---|---|---|
| **Neothesia** ([repo](https://github.com/PolyMeilex/Neothesia), [releases](https://github.com/PolyMeilex/Neothesia/releases)) | Rust and wgpu falling notes. v0.4.0 (2025-01-31) added **free play** and **chord detection** on input. v0.3.0 (May 2024) added playback speed, play-along logic, per-channel MIDI out, guide lines and video encoding. | GPL-3.0, about 1.5k stars. Study only. | high |
| **MIDIVisualizer** ([repo](https://github.com/kosua20/MIDIVisualizer), [releases](https://github.com/kosua20/MIDIVisualizer/releases)) | C++ and OpenGL. **Records live MIDI sessions**, exports video (including ProRes), has a transparent-window overlay mode, sustain pedal visuals, particle options, split-mode colours and looping (v7.3, 2024-12-14). The author says it is rarely updated. | MIT | high |
| **PianoBooster** ([repo](https://github.com/pianobooster/PianoBooster)) | "Follow you" skill level: the accompaniment waits when you stop. Also scoring. | GPL-3.0 | medium |
| **Piano LED Visualizer** ([repo](https://github.com/onlaj/Piano-LED-Visualizer)) | Learn mode waits for the right notes and lights the next key. Already covered in `key-lights.md`. | MIT | high |
| **Magenta demos**: AI Jam, AI Duet, Piano Genie ([demos](https://github.com/magenta/magenta-demos), [magenta-js](https://github.com/magenta/magenta-js)) | Piano Genie maps 8 buttons onto 88 keys in real time, a lovely "anyone can play" idea. AI Jam pairs a piano with drum pads for duets. | Apache-2.0. `@magenta/music` is at 1.23.1, not republished in years; `magenta/magenta` (Python) was archived 2026-01-06. UX lessons only. | medium |
| **Magenta RealTime 2** ([repo](https://github.com/magenta/magenta-realtime)) | Live **audio** generation steered by text or audio style prompts. Real-time needs Apple Silicon; offline inference runs on NVIDIA. No MIDI input in the main docs. | Apache-2.0 code | high. **Not a fit** for this machine. |

---

## 5. Libraries (plumbing, if the Python side grows)

| Library | Why | Licence | Version | Conf. |
|---|---|---|---|---|
| **symusic** ([repo](https://github.com/Yikai-Liao/symusic)) | C++20 core; the project claims MIDI parsing 100-1000x faster than mido; piano rolls; SoundFont rendering | MIT | 0.6.0 | high |
| **pretty_midi** ([repo](https://github.com/craffel/pretty-midi)) | Familiar API, chroma, piano rolls | MIT | 0.2.11 (2025-10-08), post0 (2026-07-28) | medium |
| **partitura** | Analysis functions (2.1), performance and score alignment, the base of Matchmaker and ACCompanion | Apache-2.0 | 1.9.0 (2026-05-25) | high |
| **music21** | Key windows, chord and Roman numeral objects, MusicXML | BSD-3 | 10.5.0 (2025-06-17) | high |
| **tonal** (JS) | Browser-side names and scales for node receipts | MIT | current | medium |

---

## 6. Recommended steal list, ranked

| # | Steal | From | Lands in | Effort | Licence risk |
|---|---|---|---|---|---|
| 1 | Chord benchmark verb (POP909-CL, When in Rome) plus BACHI as offline judge on his sessions | BACHI, POP909-CL, When in Rome | `practice.py` verb; theory-nextgen receipts | M, plus approved downloads | none (MIT, CC BY) |
| 2 | Purity and coverage cost terms; boundary, root, quality, bass order; non-chord-tone down-weighting | semi-CRF, BACHI, AnalysisGNN | `chordread.js` / `harmony.js` (TN owners) | M | ideas only |
| 3 | Solid (committed) against translucent (tentative) ghosts; per-player commit window | ReaLJam | jam Try ghosts; suggestion chips | S | ideas only |
| 4 | Tension ribbon | spiral array (partitura) | display layer; TikTok mode | M | Apache port |
| 5 | Cadence banner, Tonnetz P/L/R move names, progression "bricks" | DCML, TonnetzViz, Impro-Visor | caption row; spectacle event types | S-M | own tables |
| 6 | Synthetic fixtures from his timing profile and chord grammar | AugmentedNet | TN0 corpus (conductor-gated) | S | idea |
| 7 | Follow-me tempo: onset-interval histogram plus filter, validated on PM2S beats | ACCompanion, Matchmaker, PM2S | jam v2 "Follow me" | M | MIT for offline checks |
| 8 | Practice-log performance cards (pedal blur, evenness, timing stability), localised with replay links | PercePiano, Profy | practice log | M | vocabulary only |
| 9 | Personal melodic surprise sparks | IDyOM method | cues; practice log | M | reimplement (GPL source) |
| 10 | Pedal or pad turn-taking for call and response | Aria-Duet | jam 5.10 | S | idea |
| 11 | "Page follows your piece" mode | Matchmaker, Neothesia, PianoBooster | new practice mode | M-L | Apache |
| 12 | Progression rarity prior | Chordonomicon, ChoCo | spectacle rarity | L | NC data: local only |
| 13 | Separate-app backing band over loopMIDI | JJazzLab | FL band alternative | S to try (install) | LGPL app, not vendored |

---

## 7. Licence map for a public Apache-2.0 repo

- **Port or vendor with attribution** (MIT, BSD, Apache): music21, partitura, pretty_midi, symusic, tonal, BACHI code, POP909 and POP909-CL, PM2S, realchords-pytorch, Notochord, Aria (code and weights per its repo), TonnetzViz, incon, pianoplayer, MIDIVisualizer, AugmentedNet, ChordGNN, ostinato, PercePiano code, Matchmaker, ACCompanion code, magenta-js.
- **Study only** (GPL or LGPL; LGPL apps are fine to run separately): Neothesia, PianoBooster, Impro-Visor, Somax2, MMA, MusicLang Predict, IDyOM, **BPS-FH data**, JJazzLab.
- **Non-commercial; keep local, never commit:** Chordonomicon (CC BY-NC 4.0), Hooktheory TheoryTab data (CC BY-NC-SA 3.0, and research groups note they cannot redistribute it; [Sheet Sage](https://github.com/chrisdonahue/sheetsage)), DCML ABC and DLC (CC BY-NC-SA 4.0), ChoCo's three NC parts, PIG fingering (research-only), ACCompanion models and data (CC BY-NC-SA 4.0), madmom models (per `live-key-bpm.md`).
- **Licence not found:** Harmony Transformer v2, ChenSu21, the semi-CRF code, MIDI2ScoreTransformer ([repo](https://github.com/TimFelixBeyer/MIDI2ScoreTransformer)), AnalysisGNN code, StreamMUSE, the Magenta RealTime 2 weights.

---

## 8. Unverified or not checked tonight

- The year of JJazzLab v5.2.1 ("April 13").
- Inference speed on CPU for BACHI, ReaLchords, Aria and Notochord on this machine.
- Download sizes for POP909-CL, When in Rome and the BACHI weights.
- Whether the KeyLab 88 mk3 has a free pedal input for a turn-taking gesture.
- Whether PM2S's pinned Python 3.8 and PyTorch 1.12 can install beside the house 3.11 pin, or needs its own venv.
- The three tension-ribbon names and the BeatRoot-style tracker description come from memory of the original papers, not a fresh read.
- Absence claim: no open streaming symbolic chord recogniser was found. That is a search result, not proof.

## 9. Questions for Daniel (each with a recommended default)

1. **Do TikTok videos count as commercial use?** If they are or might be monetised, anything trained on or derived from non-commercial data (Chordonomicon rarity, DCML cadence tuning, ACCompanion models) should stay out of what is shown on video. *Default: treat the videos as commercial. Use NC data only for private benchmarks, and build the displayed features on MIT, BSD, Apache or CC BY sources.*
2. **May we download the benchmark data** (POP909-CL, When in Rome, BACHI weights) and install CPU PyTorch in a separate venv, to put a real accuracy number on the chord reader? *Default: yes to the benchmark. It is the only way "improve chord accuracy" becomes provable.*
3. **A model partner or a rules partner?** ReaLchords, Notochord and Aria can answer his playing, but they cost install weight and CPU latency on this machine. The rules-and-cards jam is already designed. *Default: rules first. Take ReaLJam's display ideas now, and revisit a model voice after the jam build has had real nights.*
