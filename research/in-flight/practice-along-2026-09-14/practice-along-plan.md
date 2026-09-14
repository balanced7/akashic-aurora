# Practice along: the plan (Now Playing, song key and BPM, follow the song)

| | |
|---|---|
| Status | Plan, 2026-09-14. Research and design only: no code edited, nothing installed or downloaded, no accounts touched, no Spotify command sent. |
| Asked | Daniel, Discord, from work: "Can we integrate Spotify as well and auto set bpm and key? That way I can practice along to music and control Spotify via the preview!" ("the preview" = his /piano page.) |
| Built from | The three lanes in this folder: `spotify.md` (SPOT), `windows-media-controls.md` (WMC), `live-key-bpm.md` (LIVE); the jam build spec `research/in-flight/piano-jam-2026-09-14/jam-spec.md` (JAM); code read tonight: `arsenal/web/piano.js` (`audioIn` 2475-2542, `tickKey`/`setKeyChoice` 1682-1713, `startRecording` 2555-2592, upload 2616), `arsenal/serve.py` (`HOST` 34, `_cue_post` 506, SSE 536-560, `_recording` 621-654), `arsenal/web/piano/nashville.js` (`createKeyTracker`), `.gitignore` (`state/*` ignored). |
| Supersedes | The lanes where they disagree (section 12 lists each call). They stay the reference for detail cited by section. |

---

## 0. The answer in one screen

1. **Yes, and v1 needs no install, no account and no download.** Three parts:
   - **Control:** a hidden Windows PowerShell 5.1 sidecar talks to the running Spotify desktop app through Windows
     media controls (SMTC). That gives play/pause, next, previous, title/artist/art and a coarse position. Seek is
     advertised but unproven (WMC 5).
   - **Listen:** the page already hears the speakers through the Focusrite "Loopback L + R". An AudioWorklet
     listener estimates **song key** (a second, separate `createKeyTracker`), **BPM** and **beat phase** from that
     audio. It works for any source: Spotify, YouTube, FL.
   - **Follow:** two toggles hand the song's key and tempo to the page. The Nashville numbers read in the song's key,
     the jam key follows, loops start at the song's tempo, and the count-in lands on the song's beat.
2. **Spotify cannot supply BPM or key.** Audio Features and Audio Analysis have returned 403 to new apps since
   2024-11-27 and have not reopened ([Spotify blog](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)).
   "Auto set" therefore means **listening**, with honest confidence and one-tap fixes.
3. **Expect template-level accuracy.** Published exact-key rates are 65-80% on pop for the best offline systems. Most
   misses are the relative key or a fifth away, and half/double tempo is the main tempo failure (LIVE 4.5, 5.3). The
   panel shows a runner-up and has Lock / Relative / ±5th / ÷2 / ×2 / Tap / "This is 1", and remembers corrections
   per song, locally.
4. **Spotify Web API (Route S) is a v2 option only.** It adds search, playlists and queue. It costs Premium, a
   Development Mode app registration, acceptance of the Developer Terms, and a re-login every 6 months. It also makes
   /piano a Spotify Developer app, whose policy forbids analysing Spotify audio and overlapping it with other audio.
   The Web Playback SDK is not planned.
5. **Two limits we keep:**
   - No audio is stored or uploaded. Analysis is transient and in memory, and titles stay on this machine.
   - **REC is the one live policy edge.** The recorder adds the Loopback track to takes (`piano.js` 2572-2573), so a
     take made while a song plays contains the song. Spotify's User Guidelines name recording. The default is
     Daniel's call (Q2).
6. **How it fits the jam build:**
   - The listener, the sidecar and the panel are new files. They can be built alongside jam wave 1.
   - A small early integration (panel, song key → Nashville numbers, transport buttons, REC notice) fits the jam
     wave-2 window, when `piano.js` is untouched.
   - Tempo follow and the beat-synced count-in need the jam transport, so they come after J9.
   - Over a playing song, Claude's loops default to silent ghosts. Claude can play in the song's key, but it does
     not know the song's chords until v2 reads them from the audio.

---

## 1. What Daniel gets (v1)

A DOM panel outside the recorded canvas. Early on it is docked at the stage's top-left and collapses to a 28 px pill;
after J9 it becomes a "Song" row in the deck's Now header:

```
NOW PLAYING  Spotify ▶   [|◀] [⏯] [▶|]   1:12 ━━━━━━○────── 3:48        (position is approximate)
SONG   E♭ major · fair · or C minor   [Lock] [Relative] [−5th] [+5th]     You: E♭ major · 94% in key
       72 bpm · steady  (36 · 144)    [÷2] [×2] [Tap] [This is 1]          beat ● ○ ○ ○
FOLLOW [✓ Key → numbers and jam]  [  Tempo → loops]                       [Count me in]
```

- **Transport buttons** send SMTC commands. The scrub bar appears only if drill D2 proves Spotify honours seek.
  Otherwise the bar is display-only, and `|◀` restarts the track.
- **Song key** shows the tracker's own confidence words (`unsure` / `fair` / `sure`), a runner-up, and the fixes.
  `You: …` is Daniel's existing MIDI tracker plus `outShare` agreement (LIVE 6.2).
- **BPM** shows the tempo family and a steadiness word (`steady` / `loose` / `lost`). Beat pips show only when phase
  confidence clears its floor. A rubato ballad honestly shows none (LIVE 5.4).
- **Follow Key**: the Nashville row, chips and chord spelling read in the song's key, and the Key select reads
  `song: E♭`. A jam run started while Follow Key is on uses the song key. Section 2.4 gives the order of precedence.
- **Follow Tempo** (after J9): Loop and Try start at the song's BPM. The count-in is placed so bar 0 lands on the
  song's beat, and a running loop trims itself to stay on it (2.5).
- **Count me in** (after J9): a one-bar count-in (visual 4-3-2-1 and quiet ticks) on the song's beat. It can start a
  Try (silent ghosts) or just count him in.
- **No new keyboard shortcuts in v1.** JAM 8.7 already uses the free keys, and `KEYMAP` holds 32 more.

---

## 2. Architecture

```
Spotify desktop ─(SMTC)─> smtc_sidecar.ps1 (powershell.exe 5.1, hidden, JSON lines, 4 Hz poll, allowlist in-sidecar)
                                 │ stdin/stdout
                  arsenal/along/bridge.py ──> serve.py  GET  /api/piano/source            (snapshot)
                                                        GET  /api/piano/source/art        (thumbnail bytes, local)
                                                        POST /api/piano/source/control    {op, position_ms?, by}
                                                        event "source" on /api/piano/cues (caps source1)
                                                        POST /api/piano/along/state  <─ page (≤1 Hz, on change)
                                                        GET  /api/piano/along        ─> CLI / Claude (no titles)

speakers ─> Focusrite Loopback ─> audioIn (existing getUserMedia, EC/NS/AGC off)
              └─> AudioWorkletNode "listen" (0 outputs)  onset bands 10 ms · chroma 250 ms @ 6 kHz
                     └─> main thread: tempo.js (ACF + pulse + prior + hysteresis, family, comb + PLL)
                                      songkey.js (audio pc history ─> createKeyTracker #2, bass-tonic bonus)
                          gates <─ Daniel's MIDI note-ons (weights, onset gates) · Claude's cue notes (gates, freeze)
page along.js: panel · follow logic · key-source resolver · count-in placement · per-song memory
      ├─> keyView display override (Nashville row, chips, spelling)       (early integration, AL7)
      └─> transport.js: bpm, start epoch aligned to beat, phase trims    (after J9, AL8)
```

### 2.1 Source bridge (Route W, variant A: zero install)

- **Sidecar** `arsenal/along/smtc_sidecar.ps1`, run with
  `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File …`. It is spawned by `bridge.py` with
  `CREATE_NO_WINDOW`, and it pins Windows PowerShell 5.1: PS 7 cannot load WinRT types this way
  ([PowerShell#13042](https://github.com/PowerShell/PowerShell/issues/13042)). It uses the WMC 6 `AsTask` await helper.
  - Polls `GetSessions()` at 4 Hz. The synchronous getters cost about 0.01 ms (WMC 4). `TryGetMediaPropertiesAsync`
    (0.4-3.8 ms) runs only when a session's status or timeline stamp changes.
  - **Allowlist inside the sidecar.** It emits only sessions whose AUMID starts `SpotifyAB.SpotifyMusic`, plus
    `Brave` / `Chrome` / `MSEdge` when the setting "Follow browser media" is on (default off). Riot Client and every
    other app never leave the sidecar process.
  - Drops timelines whose `LastUpdatedTime` is the zero DateTime (1601) or more than 60 s stale while Playing.
  - Emits a JSON line only on change: `track`, `status` or `timeline`, plus a `hello` with the PS version.
    Commands arrive on stdin: `{id, op, position_ms?}`. It replies `{id, delivered}`, then re-reads 300 ms later and
    replies `{id, observed}` (WMC 7). That is how "Spotify accepted the seek and ignored it" becomes visible.
- **`bridge.py` (`SourceBridge`)** starts the sidecar lazily on the first `source1` subscriber or GET, and stops it
  60 s after the last. It restarts with 1/2/5/10 s backoff. It keeps a monotonic anchor for position:
  - it re-anchors only when the position value is one not seen before (VybecordTS rule, WMC 4);
  - it freezes the anchor while the source is not Playing.

  Health goes in `/api/piano/cues/status` as `{source: {running, ps, restarts, last_error}}`. `--no-media-session`
  turns the bridge off.
- **Routes** follow JAM 5 conventions: the `_cue_post` origin check (127.0.0.1/localhost only) and `by` on writes.
  - `GET /api/piano/source` returns `{available, reason?, session: {kind: "spotify"|"browser", status, controls:
    {play, pause, next, previous, seek}, title, artist, has_art, timeline: {position_ms, end_ms, anchor_epoch_ms,
    playing}} | null}`.
  - `POST /api/piano/source/control` returns `{delivered, observed, status, position_ms}`. It answers 409 when the
    control is not enabled, and 503 when the sidecar is down.
  - `GET /api/piano/source/art` serves the thumbnail stream copied to memory. The page never gets a remote URL.
- **Events:** a `source` frame on the one stream (JAM C4: no second SSE), ops `track | status | timeline | gone`.
  Like `deck` and `jam` frames, these are never dropped as stale, and the state route is the truth on reconnect.
- **Variant B (pywinrt in-process)** needs 4-5 PyPI wheels (`winrt-runtime`, `winrt-Windows.Media.Control`, …
  v3.2.1, [PyPI](https://pypi.org/project/winrt-Windows.Media.Control/)). It exposes the same routes. Swap to it only
  if Daniel approves the install *and* the sidecar misbehaves.

### 2.2 The listener (source-agnostic)

LIVE 3-6 is adopted as written, with these v1 choices:

- **Worklet** (`listen/worklet.js`, Blob-registered like `transport-test.html`). It has 0 outputs and hangs off
  `audioIn.source`, and the analyser stays for the meter.
  - Onset path: 1024 Hann, 480 hop, three log-flux bands.
  - Chroma path: ÷8 decimation to 6 kHz, 4096 FFT every 250 ms, peaks mapped to 12 + 12 bass bins, tuning, tonal gate.
  - Pure DSP lives in `listen/dsp.js` so Node runs the same code over PyAV-decoded PCM.
  - If S0 shows Chrome skips a zero-output node, the fallback is a gain-0 path to the destination, with a comment,
    because `piano.js` says the input is "never connected".
- **Tempo** (`listen/tempo.js`): LIVE 5.2-5.4 in full.
  - Unbiased ACF over 6 s, pulse enhancement, a log-normal prior at 105 bpm (σ 0.9 oct), and a 3 s hysteresis.
  - The tempo family {T/2, T, 2T} (plus 2T/3 and 3T/2 on triple feel), with the octave chosen by: stored choice >
    low-band periodicity > a 70-150 range.
  - Comb phase every 100 ms, smoothed by a PLL (k 0.15, k₂ 0.01), with phase confidence from comb prominence.
  - **Bar phase has no automatic downbeat in v1.** "This is 1" (a click, or a tap on beat 1) sets it, and the PLL
    carries it at 4 (or 3) beats.
- **Song key** (`listen/songkey.js`): a **new** `createKeyTracker({holdSec: 8, minR: 0.45})` instance fed by an audio
  pitch-class history on the `pcHistory` contract (τ 12 s, about 4 units/s, `chroma_norm`, gated frames only). It
  calls `update(audioPc, t, null)` at 10 Hz from the same tick as `tickKey`.
  - The bass-tonic tie-break enters through `rankKeys`' existing `bonus` argument.
  - The transposition-shaped jump rule is LIVE 4.4.
  - KK profiles only in v1. The profile parameter in `nashville.js` is a later edit, after B3 lands and only if
    validation says Temperley or `edma` wins.
- **Clocks.** Each frame carries its context sample index. The audible time is `context_time − L_in`, mapped to
  `performance.now()` through `audioIn.ctx.getOutputTimestamp()` pairs sampled every 100 ms. `L_in` comes from the
  click drill (LIVE 5.6) and is stored per device label.
- **State out:** `state()` returns `{key: {name, confidence, runnerUp, locked}, tempo: {bpm, family, level, steady},
  beat: {periodMs, nextBeatPerf, phaseConf, barPhase|null}, gates: {weightHis, frozen, gatedShare}}`, cached for
  the render loop. The render loop does no analysis.
- **Budget:** under 2% of one core, estimated (LIVE 3.4). AL-C12 measures it.

### 2.3 The practice-along module (`along.js`)

```js
// arsenal/web/piano/along.js
export function createAlong({ root, api, listener, keyView, isRecording, transport = null /* after J9 */,
  store /* per-song memory */, now = () => performance.now() }) -> {
  applySourceFrame(f), control(op, args), follow /* {key: bool, tempo: bool} */, setFollow(which, on),
  displayKey() /* {key, source: "manual"|"jam"|"song"|"me"} */, fix(kind) /* lock|relative|fifth±|half|double|tap|one */,
  countIn(opts) /* after J9 */, recChoice() /* for the REC notice */, stats() }

// arsenal/web/piano/listen/index.js
export function createListener({ ctx, sourceNode, onState, midi /* {playing(), onNoteOn(fn)} */,
  cues /* {onNote(fn), sounding()} */, latency /* {L_in, L_midi} */ }) -> {
  start(), stop(), reset(reason /* track|seek|device */), state(), lockKey(name|null), setTempoLevel(l),
  tap(tPerf), thisIsOne(tPerf), stats() }
```

- **Track change** (a `source` `track` frame, or 17 s of tonal silence): `listener.reset("track")` builds a fresh
  tracker and tempo state, then loads the song's stored corrections (2.7). An observed seek keeps the key and resets
  phase only.
- **Paused source:** the listener banks nothing (no growth), and the panel dims to "paused".

### 2.4 Which key the numbers use (precedence)

A display-level override that the numbers, chips and spelling read. It is not `keyTracker.lock()`, so Daniel's own
tracker is never re-seeded by the song or the jam.

| Order | Source | When | Key select shows |
|---|---|---|---|
| 1 | Manual | Daniel picked a key in the Key select (`theoryUi.key !== "auto"`) | the key |
| 2 | Jam | a run is active or ended < 2 s ago (JAM 8.10); with Follow Key on, the run was started in the song key, so they agree except inside a card's key items | `jam: E♭` |
| 3 | Song | Follow Key on, and song key `fair` or `sure` (or locked, or stored for this song) | `song: E♭` |
| 4 | Me | otherwise: his MIDI tracker, as today | `auto` |

- **Switching the song key while Follow Key is on** re-numbers at his next rest (JAM 8.9: 1.2 s with no note
  sounding), or after 4 s at most, with a toast: `Numbers now in F major (song)`. During a run, it becomes
  `control next {key}` with `at: "bar"` (the jam default for a key-only change is `pass`, too late for a song
  modulation).
- **With Follow Key off**, nothing changes by itself. The panel offers `[Use E♭]`.

JAM 8.10's "locks the key tracker's display key" should use this same override; section 12 covers the note to J9.

### 2.5 Tempo follow and a count-in on the song's beat (after J9)

**Starting a loop or Try with Follow Tempo on:**
1. `bpm` = the listener's float BPM at the chosen family level. It is not rounded; the tempo map is float
   (JAM 9.1).
2. The page predicts the song's next audible beats: `nextBeatPerf + k·periodMs`, already `L_in`-corrected. A downbeat
   needs a bar phase from "This is 1"; without one, the count-in aligns to beats, and the panel says `beat-aligned
   (tap "This is 1" for bars)`.
3. `bar0` = the first predicted downbeat (or beat) at or after `now + lead_ms + count_in·barMs`, and
   `start = bar0 − count_in·barMs`. Both are converted to epoch through the transport's offset (JAM 9.1).
4. The page starts the run with that start epoch. **Contract delta:** `jam/start` accepts `start_epoch_ms` from the
   owner page (at least now + 150 ms, the same rule as `launch`). The alternative is the `pending` + `launch` path,
   which already takes `epoch_ms`.
5. Claude's voice schedules through the fitted clock (JAM 9.7), so a tick planned at perf `t` sounds at `t`, the
   same instant the song's beat leaves the speakers.
6. **Fallbacks:** if phase confidence is below its floor or tempo is `loose`, the count-in runs at the song BPM from
   `now + lead_ms`, as JAM 9.2 does today, and the panel says `not synced to the song`.

**Staying on the song while a loop runs (phase trims):**
- At each bar hand-off, compare the run's next downbeat (tempo map) with the listener's predicted audible beat
  nearest to it. The difference is `e` ms.
- If phase confidence is good and |e| > 20 ms for 2 bars running, send one `control tempo` for bar B+2, which
  satisfies the 1 beat + 250 ms landing rule.
  - The trim BPM makes that bar's length `barMs − e`, clamped to ±2%.
  - A second `control tempo` for bar B+3 restores the base BPM.
- A confirmed song tempo change (the listener's 3 s hysteresis) becomes one `control tempo` at the next legal bar.
- **When it lets go:**
  - If |e| > 120 ms, or the tempo family level changes, following stops. The run keeps its tempo, and the panel says
    `lost the song's beat: Tap or This is 1`.
  - No trims are sent while more than 60% of the onset window is gated by Claude's notes (2.6). The panel says
    `holding tempo`.
- **Why trims matter:** a 0.1% BPM error drifts 300 ms over 5 minutes, which is audible.
- **Contract delta:** `bpm` in `control`, `start` and segments must accept floats (with at least 2 decimals kept).

**v2 experiment: "resume with count-in"** (Spotify paused → count-in → send play so the song resumes on beat). It
depends on the command-to-audible latency jitter from drill D1. Build it only if p95 jitter ≤ 30 ms.

### 2.6 Keeping the song estimate clean

What reaches the Loopback: the song, Daniel's piano (FL/Kontakt through the Focusrite, confirmed in D4), and Claude's
voice when the browser outputs through the Focusrite (JAM 8.6).

| Contaminant | Key evidence | Tempo and phase evidence | Why this rule |
|---|---|---|---|
| Daniel playing | chroma frames weighted `w_his` 0.3 while he plays (1 while silent) | mid/high ODF × 0.3 in `[t_on + L_midi − 10, + 40 ms]`; low band too below C3 | unbiased: he mostly plays in key, and masking his pitch classes would delete the true key's evidence (LIVE 6.2). SPOT's "freeze while he plays" would stall learning for a pianist who never stops |
| Claude's run or direct cue sounding | **song histogram frozen** | all three bands gated at each cue note-on (times known; `L_out` from the fitted clock, plus `L_in`); **tempo re-estimation frozen during runs** (phase trims only, from ungated frames) | Claude's backing is in the song key and tempo *by construction*, so learning from it would confirm itself (the self-lock loop). AL-C7 tests this |
| Silence, speech, noise risers, drum-only bars | tonal gate (LIVE 3.3) | ODF confidence hold (LIVE 5.1) | |
| All of the above, at the root | if the Focusrite can loop back a playback pair only Spotify uses, the Loopback carries the song alone (LIVE 6.5) | | a Windows settings change: his step, optional |

The listener never feeds `pcHistory`, `sounding`, `detect()`, the practice log or rarity. Daniel's label, numbers and
tracker stay his (INT invariant 1, JAM C11). AL-C6 checks it.

### 2.7 What is stored, where

| Data | Where | Contents | Never |
|---|---|---|---|
| Per-song corrections | `state/arsenal/along/tracks.json` (git-ignored by `state/*`), server-written through `POST /api/piano/along/track` | key `HMAC-SHA256(salt, title + "\0" + artist)` → `{key, key_locked, tempo_level, bpm_hint, updated_at, uses}`; the salt in `state/arsenal/along/salt` | titles in clear, detected feature series, chroma, audio |
| Page settings | `localStorage` `arsenal.piano.along.*` (`followKey`, `followTempo`, `countTicks`, `browserMedia`, `panel`) | toggles | |
| Latency calibration | `state/arsenal/jam/calibration.json` (JAM C17), new keys `L_in[device]`, `L_midi[device]` | ms numbers | |
| Listener buffers | memory only: an 8 s ODF ring, a 12 s decaying histogram | | written to disk, sent anywhere |
| Practice log | unchanged | Daniel's events only | song title, artist, song key (no new event kind: JAM C13) |
| Claude-readable state | `GET /api/piano/along` | key, confidence, runner-up, BPM, family, steadiness, follows, source status and position | title and artist, unless `pianocue along status --track` is run with Daniel's say-so (that sends them into the chat) |
| Drill receipts | `state/arsenal/receipts/along/<drill>-<date>/` | timings and counts | titles, audio |
| Takes | `/api/recordings` → first library root's recordings folder (`serve.py` 634), so a take appears in his library | per Q2 | |

---

## 3. Which path controls playback

| Path | What it gives | Costs and limits | Daniel's steps | Verdict |
|---|---|---|---|---|
| **W-A: SMTC via PowerShell 5.1 sidecar** | play, pause, toggle, next, previous; title, artist, art; status; position about ±2 s, republished about every 4.5 s (WMC 4); seek *advertised* | Seek may be a no-op on Spotify (a [2020 report](https://github.com/MicrosoftDocs/winrt-api/issues/1725); D2 settles it). No playback rate, so no slow-down practice. No track id. One child process (110 ms start). Works for YouTube in a browser when the site implements Media Session | none (the drills change his playback, so he says when) | **v1** |
| W-B: SMTC via pywinrt in `serve.py` | same, with events in-process | 4-5 wheel install; callbacks off the main thread | approve the install | swap-in only if W-A misbehaves |
| **S: Spotify Web API (PKCE)** | W plus search (10 results in Dev Mode), playlists, queue, devices, exact track URIs, reliable seek | Premium (the app owner too), a Development Mode app (5 users), Developer Terms. Redirect `http://127.0.0.1:8793/…` (localhost banned). Refresh token dies after 6 months ([blog](https://developer.spotify.com/blog/2026-06-18-refresh-token-expiration)). Every command is a cloud round trip on shared per-developer quota. **Makes /piano a Spotify Developer app**: Policy III.13 (no analysis), III.7 (no overlap with other audio), II.4.b (link back) | confirm Premium; log in to developer.spotify.com; accept the Terms; create the app; add the redirect URI; paste the Client ID; log in through the page; re-log in every 6 months | **v2, only on Q1 = yes.** While S is the source, the listener and Claude's sound stay off, and key and tempo come from his ear and Tap (SPOT 4.2) |
| Web Playback SDK | the page becomes a Spotify player | everything in S, plus EME: Brave ships Widevine off, and enabling it is a component download; DRM audio cannot be tapped anyway | S steps plus Widevine | **not planned** |
| `spotify:` URI, media keys, UI Automation | open an item; blind play/pause | steals focus, weaker than SMTC | none | no |

**Decision:** W-A for control, the listener for key and BPM, Route S behind Q1. If D2 shows seek is a no-op, v1 has
no scrub or A-B repeat (display-only position, `|◀` restarts), and A-B repeat moves to v2, contingent on Route S.

---

## 4. What needs Daniel's OK

| Item | Kind | v1? | Default if not asked |
|---|---|---|---|
| Drills D1-D3 and D7: the sidecar pauses, skips and seeks **his** Spotify | consent, with him present | yes | not run without him |
| Drill D4: clicks from the browser, and a few notes he plays | consent, with him present (makes sound) | yes | not run without him |
| REC behaviour while a song plays | policy choice (Q2) | yes | the song is kept out of the take |
| "Follow" auto-apply vs a Use click | preference (Q3) | yes | toggle on = auto at `fair` |
| Title/artist into chat (`along status --track`) | data leaving the machine | per use | off |
| Follow browser media (YouTube tabs) | setting | optional | off |
| Windows per-app output routing / Focusrite loopback pair | his settings change | optional | untouched |
| pywinrt wheels (W-B) | install | no | not installed |
| Route S: Premium, developer login, Developer Terms, app registration, PKCE login every 6 months | account and terms | no (Q1) | not done |
| Widevine in Brave (SDK) | download | no | not done |
| GetSongBPM (account plus mandatory public backlink) / ReccoBeats (egress, unknown terms) | account, egress | no | off (LIVE 8) |
| Essentia.js / aubio / madmom / Beat This! for comparison | download; AGPL/GPL/NC licences | no | not used; librosa 0.10.2 is already installed for validation |

---

## 5. How it composes with the jam build and Claude's cues

- **One stream, one run model.** `source` frames join `cue`, `deck` and `jam` on `/api/piano/cues` (caps `source1`).
  Follow Tempo drives the same `jam/start` and `control tempo` routes, with the landing rule unchanged (JAM 5.2, 9.4).
- **Jam key = song key** while Follow Key is on. The deck's key selector gains a fifth option, `song key`, beside
  *as written / my key now / his keys / all 12* (JAM 8.3). Chips re-resolve through `resolve?key=` as today, so a
  Kept card transposes to the song.
- **Claude comps in the song's key, honestly scoped:**
  - **v1:** Claude knows the song's key and tempo, not its chords. A card's progression played over a different
    song progression would clash. So while the source is Playing, Loop and Try default to `try_backing: ghosts` and
    the run starts `mute`d: silent ghosts in the song's key and tempo.
  - Daniel can unmute with one click (the `unmute` op exists). The `hold` groove on the 1 chord (a tonic pedal) is
    the safe sounding option to offer.
  - **v2:** beat-synchronous chroma → chords (LIVE 4.4). That gives a Nashville chart of the song itself and lets
    Claude comp the song's actual changes.
- **The courtesy gate** (JAM 8.9) gains one rule: while the source is Playing, a remote sounding action
  (`by: claude`, no `now`) always becomes a knock and never auto-launches over the song. Remote ghosts and `deck open`
  keep their rules.
  - Direct `pianocue play` / `progression` cues predate the gate (JAM 16). Recommendation: while a song plays,
    arrive as ghosts plus a knock. This is a small `piano.js` change, and Vandor's call.
- **Recording** (JAM 8.6 and Q1 there): Claude's voice is already kept out of the recorder's graph. The Loopback is
  the leak for both the song and Claude, and the REC notice (6.3) covers both.
- **Riff talk:** `practice riff` can note that a run followed a song (a run setting `follow: {key, tempo}` with no
  title). No song audio or title reaches the riff pipeline.
- **Claude in chat:** `GET /api/piano/along` / `pianocue along status` lets Claude say "you are in E♭ with the song
  at 72" without titles. With `--track`, the title is included, on Daniel's word.
- **/play page (v2):** the same listener's beat clock can replace `detectBeat`'s bass-threshold pulse there.

---

## 6. Privacy and terms

Reading of the texts, not legal advice (SPOT 2).

### 6.1 What v1 touches

- **Route W plus the listener never calls the Spotify Platform.** The Developer Policy and Terms bind apps built on
  it ([policy](https://developer.spotify.com/policy), [terms](https://developer.spotify.com/terms) II.9), so their
  analysis (III.13), overlap (III.7) and storage (IV.3.a) clauses do not attach.
- **The consumer [User Guidelines](https://www.spotify.com/us/legal/user-guidelines/) do attach.** They forbid
  copying, ripping or **recording** content, and using it to train ML/AI. Listening to the speakers in memory is none
  of those, but REC can be.

### 6.2 Hard rules the build enforces

1. No audio buffer, chroma series or onset series is written to disk or sent anywhere. The worklet's rings are memory
   only.
2. No request to any host other than 127.0.0.1 during practice-along (AL-C11 checks the network log).
3. Nothing trains on song audio. The only per-song data kept is Daniel's own corrections, under a salted hash.
4. Validation audio is synthetic or his own FL renders. No commercial recordings go into `tests/` or the public repo.
5. The sidecar forwards allowlisted sessions only. Other apps' media titles never leave the sidecar process.
6. Titles stay on the machine unless Daniel asks for them in chat.

### 6.3 The REC notice

When REC starts while the source is Playing (or the listener's tonal gate has been open for 5 s with Daniel silent),
a one-line choice appears before the recorder arms:

`A song is playing through your Loopback. [Keep the song out] [Include the song]`

- **Keep the song out:** the take has no audio track. The Loopback also carries his piano, so his sound drops too,
  but his notes are still in the practice log.
- **Include the song:** today's behaviour. The take lands in his media library with the song in it.
- The remembered default is Q2. The durable fix for "only my piano" is Loopback routing that separates the song
  (2.6), which is his settings step.

### 6.4 If Route S is ever on

- The listener stays off and Claude's sound stays muted while S is the source (III.13, III.7).
- The Now Playing card links back to the Spotify item (II.4.b).
- No per-track cache keyed by Spotify id (IV.3.a).
- Tokens live in a git-ignored file or the page's `localStorage`, and the page refuses to start login from
  `localhost` (SPOT 1.4).

---

## 7. Phased build plan

Ownership follows JAM 13.1: one owner per existing file per wave; new files belong to their creator; Vandor is the
sole committer; live checks never run on 8793. Along phases use port **8799**.

| Phase | Slot | Depends on | Scope (files) | Exit |
|---|---|---|---|---|
| **AL0 Drills, part 1** | now, with Daniel (about 10 min) | his OK | D1, D2, D3, D6 with scratch PowerShell scripts (nothing in `arsenal/`) | dated receipts; decides scrub/A-B and the position error bound |
| **AL1 Source bridge** | jam wave 1, parallel (new files only) | AL0 D6 | `arsenal/along/__init__.py`, `smtc_sidecar.ps1`, `bridge.py`, `tracks.py`; `tests/test_arsenal_along_bridge.py` with a fake-sidecar fixture | AL-C1, AL-C2 |
| **AL2 Listener DSP** | jam wave 1, parallel | none | `arsenal/web/piano/listen/dsp.js`, `worklet.js`, `index.js` (skeleton), `listen-test.html`; `tests/along_dsp.test.mjs`; the synthetic fixture generator `arsenal/lanes/along_fixtures.mjs` | AL-C3; **D4, D5** run on `listen-test.html` with Daniel |
| **AL3 Tempo and phase** | jam wave 1, parallel | AL2 | `listen/tempo.js`; `tests/along_tempo.test.mjs` | AL-C4 |
| **AL4 Song key** | jam wave 1, parallel | AL2 | `listen/songkey.js` (imports `createKeyTracker` read-only); `tests/along_songkey.test.mjs` | AL-C5 |
| **AL5 Offline validation** | after AL3 and AL4 | FL renders (Daniel renders them, or they come from his existing projects) | `arsenal/lanes/along_eval.mjs` (Node over PyAV PCM) plus a librosa reference script; fixtures under `state/` | the numbers report (exact key, weighted, switches/min, Acc1/Acc2, beat F, time to lock). **Report-only: pass bars are set after this run** |
| **AL6 Routes, event, CLI** | jam wave 2 (`serve.py` free) | J3 merged (`publish_event`), AL1 | `serve.py` (source routes, `along/state`, `along/track`, caps `source1`, status block); `arsenal/along/cli.py` registered through `jam/cli.py`; `tests/test_arsenal_along_routes.py` | AL-C1 (routes), AL-C11 (origin) |
| **AL7a Panel module** | jam wave 2 | AL3, AL4 | `arsenal/web/piano/along.js`, `along.css`, `along-test.html` (fake source and fake listener) | AL-C9 (logic half) |
| **AL7b Early integration** | end of jam wave 2, **before J9 starts** (otherwise its hook list is handed to J9) | AL6, AL7a | `piano.js`, `piano.html`, `piano.css`: mount the panel, the listener on `audioIn.source`, the 2.4 display override, gating hooks (`noteOn`, cue notes), the REC notice in `startRecording`, `window.__piano.along` | AL-C6, AL-C9, AL-C10, AL-C11, AL-C12 |
| **AL8 Follow tempo and count-in** | after J9 lands (wave 4) | J7, J9, contract deltas agreed in J0 terms (float BPM, `start_epoch_ms`) | `transport.js` (aligned start, trims, `holding`/`lost` states), `along.js` (count-in, follow tempo), `deck.js` (`song key` option), `piano.js` (courtesy rule for a playing song); `arsenal/lanes/along_verify.mjs` | AL-C7, AL-C8, AL-C9 (jam half) |
| **AL9 First night** | after AL8, and not the same night as J10 | Daniel | D7: 10 songs he knows, the contamination check, count-in feel | his verdicts in `state/arsenal/receipts/along/`; tuning of `holdSec`, `minR`, gates |
| **v2** | after AL9 | per item | Route S (Q1); A-B repeat (if D2 passes or S is on); resume with count-in (D1 jitter ≤ 30 ms); audio chords → song chart and Claude comping the song's changes; downbeat detection; chroma subtraction (calibration drill); `nashville.js` profile parameter (after B3); W-B pywinrt; /play beat clock | per feature |

**If Daniel wants it sooner than the jam:** AL0-AL4 plus AL6-AL7b give a working Now Playing panel, song key and BPM,
and the Nashville numbers in the song's key, with no jam dependency beyond J3's `publish_event`. If J3 is late,
AL6 can publish through a tiny `source` hub of its own, and J3 merges that hub into `publish_event`.

---

## 8. Acceptance checks

All scripted and headless (isolated Chrome, `--mute-audio`, the anti-throttling flags), on port 8799. Dated receipts
go under `state/arsenal/receipts/along/<check>-<date>/`.

- **Audio into headless checks:** the listener accepts any `AudioNode` as its source, so checks inject an
  `AudioBufferSourceNode` playing a fixture through a test-only `?along=fixture:<name>` hook.
- **One wiring check** proves the `getUserMedia` path using Chrome's `--use-fake-device-for-media-stream
  --use-file-for-fake-audio-capture=<wav>`. The file plays in a loop
  ([TestingBot](https://testingbot.com/resources/articles/fake-webcam-microphone-chrome)), and the flag is reported
  not to work in some Chrome setups ([cypress#5592](https://github.com/cypress-io/cypress/issues/5592)). If it fails
  here, the receipt says so and the buffer-source path stands.

| Check | Setup | Pass |
|---|---|---|
| **AL-C1 Bridge and routes** | fake sidecar replaying recorded JSON lines: Spotify, Brave, Riot (zero timeline), a stale Brave | 0 frames or route fields from non-allowlisted AUMIDs (and 0 Brave with the setting off); the zero-DateTime timeline ignored; `source` events only on change (0 duplicates over 60 s of identical polls); `control` returns `delivered` then `observed`; a POST with a foreign `Origin` gets 403; `control seek` while `seek` is disabled gets 409; sidecar exit → restart within 1 s, then backoff |
| **AL-C2 Sidecar hygiene** | real `powershell.exe` on this machine, read-only | process started with `CREATE_NO_WINDOW` and `MainWindowHandle == 0`; `hello.ps` major = 5; no stdout line contains a non-allowlisted AUMID over 120 s; idle CPU of the sidecar ≤ 0.5% of one core |
| **AL-C2b Position** | synthetic timeline updates every 4.5 s, with values up to 2 s stale | displayed position monotonic while Playing; re-anchored only on a new value; frozen while Paused; error against the synthetic truth within the D3-measured bound |
| **AL-C3 DSP** | Node fixtures | sine triads in 12 keys → chroma argmax on the triad's pitch classes 100%; click trains at 60/90/140 → ODF peaks within ±1 frame; a 432 Hz-tuned fixture → tuning −31.8 ± 5 cents; a 19 kHz tone → 0 chroma energy after decimation (no aliasing); byte-identical output in Node and in the worklet on the same PCM |
| **AL-C4 Tempo and phase** | synthetic drum-and-bass fixtures at 64, 72, 92, 128, 140, 174 bpm; a step 92→100 at 60 s; a 4-bar half-time bridge | Acc2 6 of 6 within 8 s; Acc1 6 of 6 when a stored level is given; the step shown within 5 s; 0 displayed flips on the half-time bridge; phase error after lock p95 ≤ 15 ms (fixture truth); a rubato fixture shows no beat pips (phase confidence below its floor ≥ 90% of the time) |
| **AL-C5 Song key** | synthetic progressions rendered with the page voice: I-IV-V-I and I-vi-IV-V in 24 keys; vi-IV-I-V; a +2 last chorus; a pad-only 20 s intro | exact key on I-IV-V-I 24 of 24 within 12 s; on vi-IV-I-V the shown key or runner-up is correct 24 of 24; the +2 modulation shown within 6 s; ≤ 1 switch/min on steady sections; the pad intro banks nothing (key stays unset until tonal frames arrive) |
| **AL-C6 Separation** | 60 s song fixture plus 300 scripted MIDI notes of Daniel's, including 20 s deliberately out of the song key; control = the same MIDI with no song | `stats().keyRaw` identical to the control; `pcHistory` identical; song key unchanged through the out-of-key 20 s; 0 listener writes to the practice log; `outShare` readout reflects the out-of-key stretch |
| **AL-C7 Self-lock guard** | song fixture at 92.00 bpm in E♭; a Loop at 92.60 in F with Claude's voice mixed into the listener input | the song key stays E♭ (histogram frozen while the run sounds); the tempo estimate stays 92.00 ± 0.3; trims move the run toward the song (final |e| ≤ 25 ms) or report `holding`, and never lock onto 92.60 |
| **AL-C8 Beat-synced count-in** | fixture with a known beat grid and bar phase set by `thisIsOne`; `L_in` injected as 0 (buffer source) and as 40 ms (delayed buffer) | plan level: every count-in tick `at` and the bar-0 downbeat within 1 ms of the predicted song beats; audio level (OfflineAudioContext render of ticks plus fixture): tick onsets within 5 ms of fixture beats; with `L_in` 40 ms the compensation holds to the same bound; the fallback path triggers below the phase floor and the panel says `not synced` |
| **AL-C9 Follow logic** | fake listener scripts: key fair→sure→modulate; tempo change; manual lock; a jam run | Follow Key on: numbers change at the next rest or ≤ 4 s; during a run a `control next {key, at: bar}` is sent; Follow Key off: 0 display changes over 100 scripted listener events and a `[Use]` offer appears; a manual lock wins 100 of 100; a jam run started with Follow Key on carries the song key; the Key select shows `song: …` / `jam: …` correctly |
| **AL-C10 REC notice** | source Playing, REC pressed | the choice appears before the recorder arms; **Keep the song out** → take has 0 audio tracks (`rec.withAudio === false`); **Include** → 1 track; the default follows the stored choice; with the source Paused and the tonal gate closed, no notice |
| **AL-C11 Privacy** | a 5-minute scripted session: source frames, listener on, a follow run, REC | CDP network log: 0 requests to any host other than 127.0.0.1; new files under `state/` limited to `tracks.json`, `salt`, `calibration.json` and receipts; `tracks.json` contains no title or artist substring; no new `.wav/.pcm/.raw/.webm` outside the recordings folder; `GET /api/piano/along` has no title/artist fields |
| **AL-C12 Cost** | 3D scene on, listener on vs off, 2 min each | listener (worklet plus main thread) ≤ 2% of one core; render frame time p95 changes ≤ 0.5 ms; worklet `process` p99 ≤ 1.5 ms per quantum |
| **AL-C13 Regression** | jam checks A1, A3, A5, A6 re-run with the listener on and the panel mounted | all pass unchanged |

---

## 9. Drills with Daniel present (drill doctrine: dated receipts, or presume broken)

| Drill | What happens | Measures | Decides |
|---|---|---|---|
| **D1 Transport** | the sidecar sends play/pause ×10, next ×5, previous ×5 to Spotify | command → `PlaybackInfoChanged` and command → audible change on the Loopback (RMS step): p50, p95, jitter | panel latency copy; whether "resume with count-in" (v2) is viable (p95 jitter ≤ 30 ms) |
| **D2 Seek** | `TryChangePlaybackPositionAsync` to 5 mid-track points | `delivered`; position moved; landing error from the timeline and a Loopback onset | scrub bar and A-B repeat in v1 or not |
| **D3 Position error** | 30 s of playback sampled at 50 ms; `previous` to restart, then the audio onset against position 0 | the SMTC extrapolation error bound | the AL-C2b bound; confirms beat sync must come from audio |
| **D4 Routing and latency** | Chrome click round trip (`L_in`), 20 s of Daniel's notes with the song paused (`L_midi`), confirm Spotify, FL/Kontakt and Chrome all reach the Loopback; read the Focusrite device label | `L_in`, `L_midi`, routing facts | gate constants; whether per-app routing is worth offering |
| **D5 Worklet** | `listen-test.html` with the 3D page open | zero-output node processes (yes/no); CPU | the fallback path; AL-C12 baseline |
| **D6 Sidecar hygiene** | spawn the sidecar for 2 min | no window flash (Daniel watches), allowlist output | AL1 go |
| **D7 First night** (AL9) | 10 songs he knows (his usual keys E♭ F D G♭ D♭ plus a couple of others); 20 s of out-of-key playing over one; 5 count-ins | his verdict per song (key, BPM level), confusion types, count-in feel, tick-vs-beat offset on the Loopback (target p95 ≤ 30 ms) | pass bars for real music; tuning |

---

## 10. Risks and unmeasured facts

| Risk | Consequence | Handling |
|---|---|---|
| Spotify ignores SMTC seek (2020 report) | no scrub or A-B in v1 | D2; A-B becomes v2 with Route S |
| SMTC position off by up to about 2 s | position cannot sync beats | beat phase from audio only (2.5) |
| Exact key about 60-75% (a hypothesis, LIVE 4.5) | wrong Nashville numbers | runner-up, one-tap fixes, per-song memory, Follow off by default |
| Half/double tempo | loops at the wrong feel | family display, ÷2/×2/Tap, stored level |
| Claude's backing reinforcing the estimate | self-lock drift | freeze plus gates; AL-C7 |
| Harmonic clash of card progressions over songs | Claude sounds wrong | ghosts and mute by default over a playing song; v2 chord reading |
| Loopback carries his piano, so "song out" also drops his sound in takes | silent takes | stated in the notice; per-app routing is the real fix |
| Zero-output worklet not processed | no listener | D5; gain-0 fallback |
| /piano may run in Brave (SPOT saw a Brave session) | untested browser | same Chromium engine; D5 runs in the browser he uses |
| Headless fake-capture flag unreliable | wiring check fails | buffer-source injection path (section 8) |
| Background throttling when he clicks into the Spotify app | none expected | the page stays visible; the transport uses a worker timer (JAM 9.7); the worklet runs regardless |

---

## 11. Questions for Daniel (four, each with a recommended default)

1. **Is controlling Spotify from the page with play/pause/next/previous (and seek if it works) enough, or do you want
   to search and pick playlists inside /piano?**
   - **Recommended: the simple controls for now.** They work with your Spotify app as it is, with no login.
   - Search inside the page needs Spotify Premium, registering a developer app on Spotify's site, and logging in
     again every 6 months.
2. **When you press REC while a song is playing, should the song be kept out of the take?**
   - **Recommended: keep it out.** Spotify's rules forbid recording its music, and the take would land in your
     library.
   - Honest catch: your piano sound travels through the same Loopback, so that take would be silent. Your notes are
     still saved in the practice log.
   - You'd get a one-click "include the song" each time you want it anyway.
3. **When you switch "Follow the song" on, should the key and tempo change by themselves once the page is fairly
   sure, or wait for you to press Use each time?**
   - **Recommended: change by themselves**, with a toast and one-tap undo. With Follow off it only ever suggests.
4. **Can we book about 15 minutes with you at the piano and Spotify open to test it?**
   - The test pauses, skips and jumps around in your Spotify, plays a few clicks, and has you play a few notes.
   - **Recommended: yes, before we build the panel.** It tells us whether jumping to a spot in a song works at all,
     and how far off Spotify's position reading is.

---

## 12. For Vandor (reconciliations and contract deltas)

**Lane disagreements, resolved:**

| Topic | SPOT | WMC | LIVE | This plan |
|---|---|---|---|---|
| Route names | `/api/piano/source*`, `source` event | `/api/media-session*` | n/a | `/api/piano/source*` plus a `source` event on the one stream (JAM C4 naming and bus) |
| Sidecar updates | WinRT events plus a 500 ms poll | 4 Hz poll | n/a | 4 Hz poll (cheap, proven); events are a later option |
| Chroma front end | analyser `fftSize` 16384 | n/a | worklet, ÷8 decimation, 4096 FFT | LIVE: no rAF sampling of analysers (duplicate or dropped frames, `play.js`) |
| Daniel's playing | freeze the song histogram while he plays | n/a | weight 0.3 plus onset gates | LIVE weighting; freeze reserved for Claude's sound (self-confirmation) |
| PS 7 | medium confidence | high (issue #13042) | n/a | pin 5.1 |
| Dev Mode Client IDs | 25 (July 2026 blog) | n/a | "one Client ID" (Feb 2026) | 25: the later source wins; it only matters for Route S |
| REC | per-take choice | n/a | flag only | a notice with a remembered default (Q2) |
| Metadata BPM/key APIs | not recommended | n/a | a prior, off by default | off; not in v1 or v2 without separate approval |

**Contract deltas for the jam build** (through the conductor, JAM 13.1 rule 3):
1. `bpm` accepts floats in `jam/start`, `control tempo` and segments, kept to at least 2 decimals.
2. `jam/start` accepts `start_epoch_ms` from the owner page (at least now + 150 ms).
3. Run settings gain `follow: {key: bool, tempo: bool}` (no title).
4. The stream caps gain `source1`.
5. JAM 8.10's jam key uses a display override (`keyView.override`) instead of `keyTracker.lock()`, shared with the
   song source (2.4).
6. Courtesy gate: remote sound over a Playing source always knocks.
7. The deck key selector gains `song key`.

**Other notes:**
- **Privacy before commit.** This folder contains no titles, session ids or transcriptions. WMC's probe deliberately
  printed none. Keep it that way in drill receipts.
- **Unverified facts carried into the plan:**
  - Spotify SMTC seek (D2);
  - SMTC position error while playing (D3);
  - the zero-output worklet (D5);
  - the fake-capture flag in this Chrome (section 8);
  - that FL/Kontakt reaches the Loopback (D4);
  - every accuracy figure for real music (AL5, D7).

## Daniel's decisions (2026-09-14, answered on Discord)

On Discord Daniel answered the questions below, sent with recommended defaults, with: "Yes to all of them! Really good ideas!". Recorded as:
- **Q1 (controls):** simple controls through Windows media controls. No Spotify app registration and no search or playlists in the page for now.
- **Q2 (recordings):** songs stay out of recordings by default, with a one-click include.
- **Q3 (following):** key and tempo apply automatically at "fair" confidence, with undo.
- **Q4 (drills):** yes to about 15 minutes of drills together, scheduled when Daniel is home. The drills play and pause his Spotify.
