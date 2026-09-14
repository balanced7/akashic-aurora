# Splice and sounds: the sound side of the FL jam bridge

- Lane: SPLICE AND SOUNDS (fl-jam-bridge research, 2026-09-14)
- Author: claude research subagent. This machine was only READ: no downloads, installs, logins, or setting changes, and no GUI apps were launched.
- Scope: how Splice works for a producer in 2025-2026; where files land; licensing; DAW integrations (Bridge, the Sounds Plugin, INSTRUMENT, FL Studio); whether Claude can search Splice without Daniel's login; a practical "Claude suggests, Daniel downloads" flow; free and legal alternatives; how generated bass and drum MIDI maps onto GM, FPC, Addictive Drums 2, Transistor Bass and Kontakt basses.
- Citation rules: every external claim has a URL, and "as of" gives the date the source shows. Local facts come from read-only PowerShell reads on 2026-09-14 and are marked **[local]**.

---

## 0. TL;DR for the jam bridge

1. **Splice is already on this machine.** Installed: the Splice desktop app 5.4.12 (a Microsoft Store/MSIX package), Splice Bridge 5.1.1, and Splice INSTRUMENT 1.1.15. `Documents\Splice\Samples\packs` holds 67 pack folders with 81 licensed WAVs (about 106 MB). FL Studio's plugin database already lists Splice Bridge, Splice INSTRUMENT, Addictive Drums 2, Kontakt 8, Analog Lab V and Serum 2. **[local]**
2. **Claude cannot use Splice by itself, and it should not try.** Splice publishes no API. Its Terms of Use ban automated access ("spiders, robots, scrapers, crawlers"). Licensing a sound needs Daniel's login and credits. So the legal path is: **Claude writes a shopping list, Daniel searches and downloads in the Splice app, and Claude reads the files that land in `Documents\Splice`.**
3. **Splice Bridge is the best live-jam piece.** It runs inside FL. It syncs Splice previews to FL's tempo, transport and key. Daniel can audition loops in time with the groove Claude is driving, then drag in the keepers.
4. **FL Studio has no native Splice integration.** Ableton Live 12.3 has one. As of Sept 2025, Image-Line support pointed FL users to Bridge. The new **Splice Sounds Plugin** (public beta since April 2026, VST3) works in any VST3 DAW, including FL, but it is not installed here.
5. **Splice INSTRUMENT is a MIDI-playable instrument, and it is the new home of Spitfire LABS.** The free plan has about 500 presets. The standalone LABS app stops being supported on 31 Oct 2026. Claude-generated MIDI can drive INSTRUMENT presets in FL like any other synth.
6. **Free sound sources already here:** FPC with 707/808/909/House/Linn/acoustic kits, 2,687 stock WAVs in FL's Packs folder, Addictive Drums 2, Kontakt bass libraries (DjinnBass, DjinnBass II, Nolly Bass Library), Analog Lab V and Serum 2. Freesound CC0 and FL Cloud Sounds are extra options. Transistor Bass is **All Plugins Edition only**, so check Daniel's edition before relying on it.
7. **Drum MIDI contract:** use **integer MIDI note numbers** with GM roles (kick 36, snare 38, closed hat 42, open hat 46...). Never use note names: FL calls middle C (MIDI 60) **C5**, while most other tools call it C4. FPC's *Empty* preset is pre-mapped to GM keys, and Addictive Drums 2 has a GM map preset.

---

## 1. Local inventory (read-only, 2026-09-14) [local]

| Item | What was found |
|---|---|
| Splice desktop app | Appx package `Splice` v5.4.12.0, publisher Distributed Creation Inc., at `C:\Program Files\WindowsApps\Splice_5.4.12.0_x64__xpwcknj9p1bc6`; alias `%LOCALAPPDATA%\Microsoft\WindowsApps\splice.exe` |
| Splice Bridge | "Splice Bridge v5.1.1" in the uninstall list; `C:\Program Files\Common Files\VST3\SpliceBridge.vst3` |
| Splice INSTRUMENT | v1.1.15; `C:\Program Files\Common Files\VST3\Splice\Splice INSTRUMENT.vst3` plus a standalone `C:\Program Files\Splice\Splice INSTRUMENT\Splice INSTRUMENT.exe`; content root `C:\Users\L5\Splice\INSTRUMENT` (only "INSTRUMENT Common" IRs, about 4 MB, so few or no presets are downloaded yet) |
| Splice Sounds Plugin (beta) | **Not installed** (no matching VST3) |
| Splice folder | `C:\Users\L5\Documents\Splice\` with `Samples\packs\<Pack Name>\<vendor folder>\...`, an empty `presets\`, and a hidden `.splice\id`. 67 packs, 81 WAVs, 0 MIDI, about 106 MB; last write 2025-11-03. Genres lean trap, RnB, house, dubstep, techno, DnB and vocal packs (e.g. "Sounds of KSHMR Vol 5 - Drums", "Drums That Knock 11", "Virtual Riot X Modestep Spicy Riddim Drums Vol. 2", "Vital Techno Kicks") |
| FL Studio | FL Studio 2026 26.1.3.5570 and FL Studio 2025 25.2.5.5319 are both installed |
| FL plugin database (`Documents\Image-Line\FL Studio\Presets\Plugin database`) | Contains Splice Bridge, Splice INSTRUMENT, Addictive Drums 2, Kontakt 8, Analog Lab V/4, Serum/Serum 2, so FL has already scanned all of them |
| FL stock generators (FL 2026 folder) | FPC, FLEX, BooBass, Transistor Bass, Drumaxx, Kepler, Harmor, Sytrus, Toxic Biohazard, MIDI Out, and others. The DLL being present does **not** mean the plugin is licensed (see 5.2) |
| FPC presets | `Data\Patches\Plugin presets\Generators\FPC\`: `Default.fst`, `Empty.fst`, Acoustic (Breakbeat, Gretch, HQ Funk/Jazz/Metal/Rock Kit, Tama...), Electronic (707, 808, 909, Dubstep, House, Linn), plus multi-output variants |
| FPC GM names file | `...\Generators\FPC\Data\MIDI\GM Drums.txt`: 61 names, "High Q" through "Open Surdo" (see 6.2) |
| FL stock sample packs | `Data\Patches\Packs\`: Drums (Kicks, Snares, Hats, Toms, Cymbals, Percussion, Kits, SFX), Drums (ModeAudio), Instruments\Bass, Loops, FLEX, Vocals, and more. 2,687 WAVs |
| FL Cloud Sounds | `Documents\Image-Line\Downloads\FL CLOUD Sounds\` has 8 pack folders but **0 files** |
| Drum plugins | XLN Addictive Drums 2 (VST3), FPC |
| Kontakt libraries (registry names) | Bass: **DjinnBass, DjinnBass II, The Nolly Bass Library**. Keys: Neo-Soul Keys, Session Keys Electric S, Ultimate Stage Pianos, and others |
| Synths | Serum 2 (2.1.4), Analog Lab V 5.12.4 (large Arturia preset bank set incl. Mini V4, Jup-8, Prophet), reFX Nexus, SynthMaster 3, a set of Cymatics plugins |
| MIDI files in Downloads | Kontakt 8 **Chords tool** library data (`Downloads\Kontakt\Kontakt 8\Content\Tools\Chords\Library Data\MIDI Files\...`), not Splice downloads |

Not checked, on purpose: Daniel's FL edition or registration (license keys are sensitive and out of scope), and the Splice app's internal database.

---

## 2. How Splice works in 2025-2026

### 2.1 Plans and credits

- **Credits:** each sample costs 1 credit. MIDI patterns and presets cost up to 3. Unused credits roll over (no cap is stated). Credits expire 28 days after the last billing period of a cancelled plan. A plan can be paused for up to two months. Re-downloading something already licensed is free on every Splice surface. Source: Splice Help "Splice plans - FAQ", updated "this week" when fetched 2026-09-14: https://support.splice.com/en/articles/8652592-splice-plans-faq
- **Current plan names:** Sounds+, Creator, Creator+, Splice x Ableton Live, Splice x Studio One, Splice x Pro Tools, INSTRUMENT (same FAQ). The Sounds Plugin FAQ also lists legacy "Sounds 100/300/600/1000" plans as eligible: https://support.splice.com/en/articles/12997860-faq-splice-sounds-plugin-now-in-beta (updated 2026-07-20).
- **Prices (US, fetched 2026-09-14):** the Splice plans page shows Creator at $19.99/mo with about 200 credits/mo (first month $4.99 trial), and Sounds at $12.99/mo billed yearly with about 100 credits/mo: https://splice.com/plans. INSTRUMENT alone is $12.99/mo: https://splice.com/instrument. Third-party pages give other numbers (e.g. Creator $13.99 for 300 credits), probably older or legacy plans. **Daniel's own account page is the only truth for his plan.**
- Creator and Creator+ include INSTRUMENT premium content. **Splice credits cannot be spent inside INSTRUMENT**: https://support.splice.com/en/articles/12270038-splice-instrument-plans-and-pricing (updated 2026-07-21).

### 2.2 The desktop app

- The desktop app is the main way to browse, license and download. Downloads go into the Splice folder. The folder can be moved or renamed, but the new location must then be set in the app's Preferences, or features like drag-and-drop break: https://support.splice.com/en/articles/8652662-where-is-my-splice-folder (2024-01-24).
- **Default location:** Windows `Documents\Splice`; macOS `~/Splice`. Samples are organized by pack. Presets go to plugin-specific folders; for example Serum presets go to `~/Documents/Xfer/Serum Presets/Presets/Splice`: https://support.splice.com/en/articles/8652631-where-do-my-downloaded-samples-presets-midi-files-go (updated 2024-07-15). The folder on this machine matches: `Samples\packs\<Pack>\<vendor folder>\...` **[local]**.
- **MIDI is the exception.** MIDI files can only be downloaded from the website, and they go to the browser's Downloads folder, not the Splice folder (same article). The 2026 Sounds Plugin FAQ confirms the plugin still does not support MIDI.
- Re-download or "Sync All" from the library view: https://support.splice.com/en/articles/9792288-how-do-i-re-download-sounds-i-previously-licensed (2024-10-23).
- **Search features:**
  - Keyword, tag and filename search.
  - Filters for samples vs presets, loops vs one-shots, BPM (exact or range), key and mode, instrument and genre, plus sort order: https://support.splice.com/en/articles/8652594-finding-sounds-with-your-splice-plan
  - **Describe a Sound** (beta, updated 2026-02-18): natural-language search in the desktop app and the Sounds Plugin, capped at 50 results, no sorting: https://support.splice.com/en/articles/13764370-how-to-use-describe-a-sound-in-the-splice-desktop-app
  - **Create / Stacks** (AI loop-matching song starters): https://splice.com/blog/introducing-create-a-stack/ and https://splice.com/blog/create-feature-update-june-24/

### 2.3 Licensing (what Daniel can do with Splice sounds)

Source: Splice Help "Splice Sounds Licensing FAQ", updated 2024-09-06: https://support.splice.com/en/articles/8652642-splice-sounds-licensing-faq

- **Royalty-free** use in new music and other creative works (games, film, video), commercial or not, with no credit to Splice or the sound's creator required.
- The license is **perpetual**: it survives cancelling or pausing the plan.
- **Not allowed:** redistributing sounds on their own (as samples, loops, or sample packs), and using the creator's name or likeness.
- **AI training is explicitly not allowed.** The FAQ says using downloaded content "for the purposes of training/modeling data for AI is not permitted".
  - **Implication for Akashic:** Claude may read file names, BPM/key tags and folder structure to suggest and organize. Splice audio must **never** go into any training, fine-tuning or embedding dataset. Deeper audio-content analysis of Splice files is a grey area (see Open questions).
- Content ID claims are not guaranteed to be avoided. Splice can issue a certified license document to dispute a claim: https://support.splice.com/en/articles/8652641-how-do-i-generate-a-certified-license-for-my-samples

---

## 3. Splice in the DAW (and in FL Studio)

### 3.1 Splice Bridge (installed, and the best fit for jamming)

- **Setup:** load Bridge as a plugin on a MIDI or instrument track (in FL, a Channel Rack generator; FL's database files it under Generators\Instrument **[local]**). The desktop app must be open and logged in. A link icon in the app turns blue when Bridge is connected: https://support.splice.com/en/articles/8652857-how-do-i-use-splice-bridge (2024-01-24).
- **What it syncs:**
  - Previews play back **through the DAW** at the project tempo, aligned to the beat grid.
  - While the DAW plays or records, previews follow the metronome in real time.
  - Samples with key data can be pitch-shifted to the project key, with half-time and double-time options.
  - Keepers go in by drag-and-drop, or through "copy modified sample" to keep pitch/time changes.
  - Same article, plus https://splice.com/tools/bridge
- **Compatibility:** officially tested on FL Studio 20.8+ (VST3/AU): https://support.splice.com/en/articles/8652858-will-my-daw-work-with-splice-bridge (2024-01-24).
- **Why it matters for the jam:** Claude drives bass and drums in FL, and Bridge sits on a spare channel. Daniel can flip through Splice loops (or a list Claude prepared) and hear each one **in time and in key** with the running groove, without stopping.

### 3.2 Splice Sounds Plugin (public beta, not installed)

- Announced 2026-04-03: https://splice.com/blog/introducing-splice-sounds-plugin-beta/
- **Formats:** VST3/AU (the product page also lists AAX): https://splice.com/tools/sounds-plugin
- **What it does:** browse, tempo-synced audition, drag in, and license with credits inside the DAW. It adds Search with Sound, Describe a Sound, a drum-pad builder, and **Variations** (AI-generated key/tempo versions of Splice samples).
- **Limits:** no MIDI support; licenses one sound at a time. Whole packs and MIDI still need the desktop app or website. Eligible plans: Sounds+, Creator, Creator+ and legacy Sounds plans, **not** the INSTRUMENT-only plan. Windows 10 22H2+. Source: https://support.splice.com/en/articles/12997860-faq-splice-sounds-plugin-now-in-beta (2026-07-20).
- It is not announced as replacing Bridge; Splice calls Bridge and the desktop app companions: https://splice.com/blog/introducing-splice-sounds-plugin-beta/
- Installing it would mean a download plus a login, so it needs Daniel's OK.

### 3.3 Splice INSTRUMENT (installed): LABS' new home, a real MIDI instrument

- **Formats:** VST3/AU/AAX plus a standalone app; Windows 10+; about 150 MB. It needs a Splice account. Content includes pianos, strings, woodwinds, choirs, synths, percussion and drum machines. INSTRUMENT plan $12.99/mo; included in Creator and Creator+. Lists FL Studio as compatible: https://splice.com/instrument
- **Free plan:** about 500 presets plus regular "Free Drops". No credits are used: https://support.splice.com/en/articles/12270038-splice-instrument-plans-and-pricing (2026-07-21) and https://support.splice.com/en/articles/12277768-splice-instrument-faq
- **Spitfire and LABS history:**
  - Splice acquired Spitfire Audio, including LABS, announced 2025-04-28: https://splice.com/blog/splice-acquires-spitfire-audio/ and https://www.kvraudio.com/news/splice-acquires-spitfire-audio-63679
  - LABS content now lives in INSTRUMENT under the "LABS" and "Spitfire" labels: https://support.splice.com/en/articles/11139645-splice-x-spitfire-audio-customer-faqs
  - **From 31 Oct 2026, LABS and LABS+ get no new content, updates or support.** Installed LABS keeps working for now. INSTRUMENT offers to import LABS content on first launch. Discontinued legacy packs cannot be imported. Sources: https://support.splice.com/en/articles/12270040-migrating-to-splice-instrument-from-labs and https://support.spitfireaudio.com/en/articles/12247087-what-is-happening-to-labs
- **For the jam bridge:** INSTRUMENT is just another FL generator. Chord backings or pads that Claude generates can play through INSTRUMENT presets (felt pianos, strings, choirs), the same way they would through Kontakt.

### 3.4 Native FL Studio integration: none

- Ableton Live 12.3 added native Splice browsing, preview and licensing, plus "Search with Sound": https://www.ableton.com/en/blog/live-12-3-is-here/ and https://help.ableton.com/hc/en-us/articles/22060471916316-Splice-integration-in-Ableton-Live-FAQ
- An Image-Line forum thread (2025-09-03/04) asked for the same in FL. Image-Line Technical Support replied that users can use "the bridge" and committed to nothing: https://forum.image-line.com/viewtopic.php?t=336226
- A search of FL Studio 2026 release coverage found no Splice integration: https://rekkerd.org/image-line-launches-fl-studio-2026-redesigned-flex-secure-cloud-project-backup-smart-assistance-more/ (negative finding, medium confidence).
- Image-Line's older "Splice supports FL Studio" news refers to **Splice Studio** (project backup and collaboration), not samples: https://www.image-line.com/fl-studio-news/splice-supports-fl-studio

---

## 4. Can Claude search Splice without Daniel's login?

| Question | Answer | Evidence |
|---|---|---|
| Public developer API? | **None found.** Searches for a Splice sounds API returned only unrelated projects. Negative finding, medium confidence. | WebSearch 2026-09-14 |
| Is the catalog publicly browsable? | **Yes, for humans.** `splice.com/sounds/search/samples` shows results and preview buttons without login (about 3.4M samples listed). URL patterns: pack `/sounds/packs/<creator>/<pack-slug>` (e.g. `/sounds/packs/dropgun-samples/g-tech-house-3`), sample `/sounds/sample/<hash>`, tag filters as UUIDs. | Fetched once for this research: https://splice.com/sounds/search/samples |
| May Claude automate it? | **No.** The Terms of Use ban manual or automated software "including but not limited to spiders, robots, scrapers, crawlers". robots.txt also disallows tag-filtered `/sounds` URLs, `/sounds/search*?*filepath=`, and `/plugins/search?*q=`. The internal GraphQL the web app uses is undocumented, and calling it is automated access. | https://splice.com/terms and https://splice.com/robots.txt |
| Can Claude license or download? | **No.** Licensing needs Daniel's account and credits, and logins are off-limits for Claude. | Plans FAQ above |
| What Claude *can* do legally | Read `Documents\Splice\Samples` (already licensed files) and the FL stock packs, and write search phrases for Daniel to type in. Vendor names often carry BPM/key in file names. | [local] |

**Bottom line:** Claude never touches Splice's servers. Splice knowledge flows **through Daniel's hands and his local disk**.

---

## 5. Practical flow: Claude suggests, Daniel downloads

### 5.1 The loop

1. **Claude writes a sound brief** into the jam space as concept cards, for example: *"dusty 90 BPM boom-bap kit, loose hats; warm fingered electric bass one-shots in F minor; 4-bar Rhodes loop 90 BPM F minor"*. Each card holds:
   - **Keyword search phrases** for the Splice search bar.
   - A **Describe a Sound** sentence (Splice's natural-language search).
   - Filters: loop or one-shot, BPM range, key, instrument, genre.
   - Optionally, a **pack name Daniel already owns**, taken from the local folder (e.g. "Sounds of KSHMR Vol 5 - Drums"), so no new credits are spent.
   - Optionally, a public pack URL Daniel has pasted into chat or found himself.
2. **Daniel opens the Splice app** (his login, his credits), searches, and auditions in sync through **Bridge on an FL channel** while Claude's groove plays. Keepers are licensed, and each costs 1 credit per sample.
3. **Files land in `Documents\Splice\Samples\packs\...`**. Claude (read-only) sees the new files and indexes pack, file name, loop/one-shot, and BPM/key parsed from the name.
4. **Claude proposes placement:** which WAVs go on which FPC pads (kick on the GM-36 pad, snare on 38...), and which loops to drag into the Playlist. Daniel drags them in FL. Any automated file placement into FL is the FL-control lane's job, not this one.
5. **MIDI packs:** if Daniel licenses a Splice MIDI pattern (up to 3 credits, website only), it lands in `Downloads`. Claude can read it and remap it to the GM contract in section 6.

### 5.2 Credit economy

Re-downloads are free, and the 67 packs already sampled are a starting palette. Suggest **one-shots**, which are more reusable for pattern-driven jams, over long loops. Prefer **Bridge auditions before licensing**, since previews cost nothing.

---

## 6. Free and legal alternatives (drums, bass, keys)

### 6.1 Already on the machine (no download, no cost)

- **FPC**, included in all FL editions: https://www.image-line.com/fl-studio/compare
  - 16 pads per bank (banks A and B), multi-layer, velocity-sensitive.
  - The **Empty** preset has pads "already assigned to the appropriate General MIDI keys".
  - The **Default** layout matches the Akai MPC series.
  - Option "Show GM note names"; per-pad Play Key set via Learn, Last hit, or "Map notes for entire bank"; per-pad mixer Output Offset.
  - Pattern Manager loads MIDI drum loops from an "FPC drumloops" folder.
  - Source: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/FPC.htm
  - Stock kits present: 707, 808, 909, House, Linn, Dubstep, Breakbeat, HQ Funk/Jazz/Rock/Metal **[local]**.
- **FL stock sample packs:** 2,687 WAVs incl. Drums, Drums (ModeAudio) and Instruments\Bass **[local]**.
- **BooBass** (all editions) for simple bass; **FLEX** (rebuilt in FL 2026, all editions): https://www.image-line.com/fl-studio/compare and https://www.image-line.com/fl-studio/release/2026
- **Transistor Bass** is a TB-303-style subtractive bass synth:
  - Internal 16-step sequencer.
  - **Accent** when velocity is above about 75%.
  - **Slide** from overlapping notes or a portamento note.
  - To play from piano-roll MIDI, the internal sequencer must be switched off.
  - Trial in other editions; source: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Transistor%20Bass.htm
  - **"All Plugins Edition only"**: https://www.image-line.com/fl-studio/compare. Its DLL is on disk **[local]**, but that does not prove a license.
- **Addictive Drums 2 (XLN):**
  - Default map puts kick on 36 and snare (open hit) on 38.
  - The MIDI Mapping window has map presets **including General MIDI (GM)**. In plugin use, those settings live in the DAW-side preferences.
  - Sources: https://support.xlnaudio.com/hc/en-us/articles/16593408783389-MIDI-Mapping-Window and https://support.xlnaudio.com/hc/en-us/articles/16925247222045-Addictive-Drums-2-Keymap (keymap page returned 403 to the fetcher; the 36/38 values come from search snippets of the XLN keymap, medium confidence).
- **Kontakt 8 bass libraries:** DjinnBass, DjinnBass II, The Nolly Bass Library **[local]**.
  - Realistic basses use **keyswitches** and string-forcing notes. DjinnBass II, for example, uses "Force String" keyswitches placed at G8: https://www.scribd.com/document/728792289/DjinnBass-II-Manual (third-party copy of the manual, medium confidence). Product page: https://www.submissionaudio.com/products/djinnbass2
  - **Generated bass lines must stay inside each library's playable range and away from its keyswitch zone.** Look up each library's range in its manual before use.
- **Splice INSTRUMENT free plan** (about 500 presets, LABS content, needs Splice login): see 3.3.
- **Analog Lab V / Serum 2 / Nexus:** synth basses and pads **[local]**.

### 6.2 Free, but they need Daniel to create an account or download (his OK)

- **Freesound (CC0 and CC BY):**
  - Licenses: CC0, CC BY, CC BY-NC, and legacy Sampling+.
  - **CC0** allows almost anything, even selling. **CC BY** needs credit. **CC BY-NC** is non-commercial only.
  - **Downloading needs a logged-in account.** Source: https://freesound.org/help/faq/
  - **API:** `GET /apiv2/search/` with `filter=license:"Creative Commons 0"`, plus `bpm:`, `tonality:"C minor"`, `tag:`, `duration:[a TO b]`. Results include MP3/OGG preview URLs: https://freesound.org/docs/api/resources_apiv2.html
  - **Every API call needs an API key**, which needs a Freesound account (apply at `https://freesound.org/apiv2/apply`). **Downloading originals needs OAuth2**, meaning a user login: https://freesound.org/docs/api/authentication.html
  - API terms: commercial use is negotiated case by case; volume limits are at Freesound's discretion; no scraping or full copies: https://freesound.org/help/tos_api/
  - **So:** if Daniel creates an account and a personal API key (his action), Claude could search CC0 drums and bass and hand him links and previews. He still downloads.
- **FL Cloud Sounds:**
  - Built into FL's browser as a "Sounds" tab (search, audition, drag in). Royalty-free, kept after cancelling.
  - Free tier: 500 MB backup, 10 plugins, and only a **limited starter** sound set. Plus: full sound library. Pro: 90+ plugins, FLEX packs.
  - Sources: https://www.image-line.com/fl-cloud and https://www.image-line.com/news/whats-new-in-fl-cloud26
  - An image-line.com search summary says every edition includes free FL Cloud Sounds and Mastering access plus a one-month full trial: https://www.image-line.com/fl-studio/compare-editions (search snippet, medium confidence).
- **Native Instruments Komplete Start** (free):
  - Kontakt 8 Player, Acoustic Drums Leap expansion, Massive X Player with Bass Music Essentials, Factory Select 2, 1,500 samples, Guitar Rig 7 Player.
  - Source: https://www.native-instruments.com/products/komplete-start
  - Daniel already owns full Kontakt 8, so the gain is the extra expansions.

---

## 7. Mapping generated MIDI (bass, drums) onto FL

### 7.1 Octave naming: use numbers, never names

- MIDI note 60 is middle C. **FL's piano roll labels it C5**, while Wave Candy, Parametric EQ 2 and most other software call it C4. The label changes only the display, not the notes sent or received.
- Sources: https://forum.image-line.com/viewtopic.php?t=76662 and https://www.kvraudio.com/forum/viewtopic.php?t=299240 (forum sources, consistent with FL behaviour, high confidence).
- **Contract:** the jam bridge carries integer notes (0-127). The GM kick, note 36, shows as **C3 in FL** and C2 in GM tables.

### 7.2 General MIDI drum map (GM Level 1, channel 10, notes 35-81)

Source: https://en.wikipedia.org/wiki/General_MIDI (GM1 percussion key map; channel 10 is reserved for percussion).

| Role in generated pattern | GM note | GM name |
|---|---|---|
| Kick (alt) | 35 | Acoustic Bass Drum |
| **Kick** | **36** | Bass Drum 1 / Electric Bass Drum |
| Rim / side stick | 37 | Side Stick |
| **Snare** | **38** | Acoustic Snare |
| Clap | 39 | Hand Clap |
| Snare (alt/electric) | 40 | Electric Snare |
| Low floor tom | 41 | Low Floor Tom |
| **Closed hat** | **42** | Closed Hi-hat |
| High floor tom | 43 | High Floor Tom |
| Pedal hat | 44 | Pedal Hi-hat |
| Low tom | 45 | Low Tom |
| **Open hat** | **46** | Open Hi-hat |
| Low-mid / high-mid tom | 47 / 48 | Low-Mid Tom / High-Mid Tom |
| Crash | 49 (57 alt) | Crash Cymbal 1 (2) |
| High tom | 50 | High Tom |
| Ride | 51 (59 alt) | Ride Cymbal 1 (2) |
| China | 52 | Chinese Cymbal |
| Ride bell | 53 | Ride Bell |
| Tambourine | 54 | Tambourine |
| Splash | 55 | Splash Cymbal |
| Cowbell | 56 | Cowbell |
| Bongos | 60 / 61 | High / Low Bongo |
| Congas | 62 / 63 / 64 | Mute High / Open High / Low Conga |
| Timbales | 65 / 66 | High / Low Timbale |
| Shakers | 69 / 70 | Cabasa / Maracas |
| Claves, woodblocks | 75 / 76 / 77 | Claves / High / Low Woodblock |
| Triangle | 80 / 81 | Mute / Open Triangle |

**FPC's extended list [local]:** `FPC\Data\MIDI\GM Drums.txt` has 61 names, "High Q" through "Open Surdo". Lines 9-55 match the GM1 names for notes 35-81 exactly, so line *n* is note *n + 26* and the file covers **notes 27-87**. The extra names (27 High Q, 28 Slap, 29/30 Scratch Push/Pull, 31 Sticks, 32 Square Click, 33/34 Metronome Click/Bell, 82 Shaker, 83 Jingle Bell, 84 Bell Tree, 85 Castanets, 86/87 Mute/Open Surdo) are the GS/GM2 extension. This is an inference from the file, but a high-confidence one. The file is most likely the table behind FPC's "Show GM note names" option.

### 7.3 Target instruments: one role map, several receivers

| Receiver in FL | How the generated drum MIDI lands | Notes |
|---|---|---|
| **FPC, *Empty* preset** | Pads come pre-assigned to GM keys, so load samples onto the pads for 36/38/42/46... and GM notes work unchanged | Manual: FPC.htm. Load the kit samples (Splice or stock) onto those pads. For *Default* or stock kits, check or remap pad keys with "Map notes for entire bank" or Learn |
| **FPC stock kits (808/909/House...)** | Layout may not be GM; read pad names or use "Show GM note names" | Remap once, then save as a user preset (Daniel's action in the GUI) |
| **Addictive Drums 2** | Kick 36 and snare 38 work by default; for full GM, choose the **GM map preset** in AD2's MIDI Mapping | XLN support pages above |
| **Splice INSTRUMENT drum-machine presets** | Unknown pad or key layout | **Open question**: check a preset's key layout in the plugin |
| **FL Channel Rack, one sample per channel** | No note mapping needed: route each role to its own channel and send a fixed note (C5 = 60) | Simplest for Splice one-shots; the FL-control lane decides routing |

**Bass receivers:**

- **BooBass / FLEX / Serum 2 / Analog Lab:** plain notes.
  - Generate within MIDI 28-55 (E1-G3 in GM numbering) for a normal bass register.
  - GM "bass" program numbers 33-40 (Acoustic ... Synth Bass 2) apply only to GM sound modules, not to FL plugins: https://en.wikipedia.org/wiki/General_MIDI
- **Transistor Bass:**
  - Monophonic 303 behaviour.
  - Encode **accent as velocity > about 75%** and **slide as overlapping consecutive notes**.
  - Switch its internal sequencer off so it follows piano-roll or MIDI input.
  - Requires All Plugins Edition (manual and compare page above).
- **Kontakt real basses (DjinnBass I/II, Nolly):**
  - Keep notes inside the playable range.
  - Keep the separate keyswitch or force-string lane off by default.
  - Round-robin and articulation choices come from velocity and keyswitches, and are library-specific.

### 7.4 Getting MIDI files into FL (when Claude writes .mid instead of live MIDI)

- FL imports note and controller events from standard MIDI files.
  - **Import MIDI File** in the Piano roll or Event Editor menu: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/pianoroll_midi.htm
  - Or **drag a .mid from the Browser** onto the Piano roll: https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fformats_other_mid.htm
- Splice MIDI (website downloads) and Kontakt Chords-tool MIDI in Downloads **[local]** can be read by Claude, remapped to the contract, and re-saved as new files for Daniel to drag in.

---

## 8. Findings with confidence (short list)

See the StructuredOutput findings; each maps to the sections above.

## 9. Open questions (for Daniel or the next lane)

1. **Which Splice plan, and how many credits, does Daniel have?** Is it Creator (includes INSTRUMENT premium and Sounds Plugin eligibility) or INSTRUMENT-only (no Sounds Plugin, no sample credits)?
2. **Which FL Studio edition does Daniel own?** Transistor Bass and Drumaxx are All Plugins Edition only. Daniel can check Help > About in FL. Registration was not read here.
3. **Is analyzing Splice audio OK?** The license bans AI training on Splice content. Reading file names and tags is clearly fine. Should the riff/loop analyzer run on Splice WAVs (tempo or key detection, no storage of embeddings), or only on Daniel's own playing and the FL stock packs? This needs Daniel's call, and possibly Splice support's.
4. **Freesound:** does Daniel want to create a Freesound account and personal API key? That is the only legal automated sound search Claude could run; downloads would still be his.
5. **Splice Sounds Plugin beta:** install it (download plus login, his OK)? Bridge already covers in-sync auditioning; the new plugin adds in-FL search, Describe a Sound and Variations.
6. **INSTRUMENT drum-machine presets:** what are their key layouts? GM-compatible or not? Needs a look inside the plugin, which is a GUI step for Daniel.
7. **FL browser extra search folder:** adding `Documents\Splice` to FL's browser search folders would put Splice sounds in FL's browser. This is an FL settings change for Daniel. It was not verified against the manual in this lane.
8. **FL CLOUD Sounds folder:** it holds 8 empty pack folders. Was the FL Cloud trial used and did it expire, or were downloads never completed? It only matters if FL Cloud becomes a sound source.
