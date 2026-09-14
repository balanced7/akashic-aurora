# Practice along: adversarial fact-check

| | |
|---|---|
| Date | 2026-09-14 |
| Checked | `practice-along-plan.md` (PLAN), `spotify.md` (SPOT), `windows-media-controls.md` (WMC), `live-key-bpm.md` (LIVE) |
| Method | Primary sources fetched tonight: Spotify developer blog, docs, Policy, Terms, User Guidelines and Terms of Use; Microsoft Learn; Chromium source; GitHub repos and PyPI; arXiv / ar5iv; MIREX wiki; MDN. Where the tempo review PDF would not render, its text was extracted locally with the already-installed PyMuPDF (no install). Repo code read: `arsenal/web/piano/nashville.js` 420-759, `arsenal/web/piano.js` 2470-2595, `arsenal/practice.py` (grep). |
| Scope rules kept | No code edited, nothing installed or downloaded, no accounts, no Spotify commands, no windows. Quotes are short phrases only. Reading of legal texts, not legal advice. |
| Verdict words | **Confirmed** (primary source agrees) · **Corrected** (source or code says otherwise; fix given) · **Unverified** (no primary source reachable; the drill or check that settles it is named) |

---

## 0. Corrections that change the plan

Ranked by consequence.

### C1. The song-key tracker cannot take the bass-tonic bonus without editing `nashville.js` (Corrected, code)

- PLAN 2.2 says the bass-tonic tie-break "enters through `rankKeys`' existing `bonus` argument", and AL4 says
  `songkey.js` "imports `createKeyTracker` read-only". LIVE 4.4 says "no tracker internals change".
- The code does not allow that. `createKeyTracker({holdSec, margin, minR})` returns `{update, lock, state}`, and
  `update(hist, t, chord)` has no bonus input (`nashville.js` 502, 600). The tracker builds its own bonus from cadence
  evidence and passes it to `rankKeys` inside the closure (`majorBonus`, `rank()`, 636-654). No caller can reach it.
- **Change:** AL4 needs a small `nashville.js` edit, for example an optional `extraBonus` (24 values, `keyIndex`
  order) on `update`, added to `majorBonus` inside `rank()`. That edit needs an owner and a wave slot under JAM 13.1.
  Keep it outside `rankKeys` itself: `arsenal/practice.py` line 139 mirrors `rankKeys`' leading-tone numbers, so a
  `rankKeys` signature change would widen the twin-parity work.

### C2. With `chord = null`, the tracker's near-tie correction never runs (Corrected, code)

- PLAN 2.2 feeds the audio tracker `update(audioPc, t, null)`. LIVE 4.2 says only the cadence and home-chord cues
  switch off. More switches off than that.
- `update` fills `sounding` (seconds each pitch class sounded) only from `chord.notes` (624-627). With `chord = null`
  it stays all zero.
- The provisional-key re-examination (707-721) switches only if
  `outShare(sounding, best) < outShare(sounding, key)` (711). With `sounding` all zero, both sides are 0, so the test
  is never true. That is the rule that swaps a near-tie first key for a related key: relative, parallel or a fifth
  away (`related`, 527). It is exactly the confusion LIVE 4.5 names as the common audio error.
- With `chord = null` a provisional key clears only in two ways. It is confirmed after leading by `margin` for
  `holdSec` (726-728), or it is replaced by the normal switch path, which needs a `margin` lead plus fast-histogram
  support (683-701). Until then `state.confidence` reads `unsure` (735).
- `homes` is also `null` (630), so the home-chord rule is off, as LIVE says.
- **Change:**
  - Either add a hook so the audio path can supply a `sounding` surrogate (gated chroma seconds per pitch class),
    which is part of the same `nashville.js` edit as C1;
  - or accept the gap and make AL-C5 measure it. Add a relative-key near-tie fixture (vi-IV-I-V opening on vi) that
    asserts the time spent `unsure` and whether the key flips.
  - AL-C5's "shown key or runner-up correct 24 of 24 on vi-IV-I-V" should be marked at risk until then.
- Also note that `state` has `candidate` (a key banking a lead), not a runner-up (729-737). `songkey.js` must call
  the exported `rankKeys` on `audioPc` to get the `runnerUp` that PLAN 2.2 lists in `state()`. That needs no edit.

### C3. The accuracy expectation mixes neural and template systems (Corrected, primary table)

- PLAN 0.3: "Published exact-key rates are 65-80% on pop for the best offline systems." LIVE 4.5 plans for "about
  60-75%" exact for our tracker.
- Korzeniowski & Widmer 2018, Table 2 ([ar5iv](https://ar5iv.labs.arxiv.org/html/1808.05340)), whole-track and
  offline:
  - **CNN (AllConv), pop-type sets:** exact 79.9 on Billboard, 76.3 on Isophonics, 72.4 on Robbie Williams, and 70.0
    on KeyFinder. EDM (GiantSteps) is 67.9.
  - **Template and classic systems:** `bgate` profile 65.0 on KeyFinder; MIREX BD1 66.0 on Isophonics; HS1 68.8 on
    Robbie Williams.
- So 70-80% is the neural range. The best published template-style figures on these sets are **65-69%**, and those
  are whole-track, offline results.
- Faraldo et al. report `bgate`/`edma` outperforming the classic Krumhansl-Kessler profile
  ([Faraldo 2016](https://link.springer.com/chapter/10.1007/978-3-319-30671-1_25)), and v1 uses KK.
- **Planning figure for a live KK template tracker: at or below about 65% exact once settled, lower in the first
  10-20 s.** The top of LIVE's 60-75% is above every template result found.
- **Change:**
  - Fix the figure in PLAN 0.3 and in the risk table (section 10).
  - Revisit the Q3 default "Follow on = auto at `fair`". Recommended: auto-apply at `sure`, or when a stored per-song
    key exists. At `fair`, offer `[Use E♭]`. At about 35-40% wrong, auto at `fair` would renumber a third of songs
    wrongly.
  - The runner-up, one-tap fixes and per-song memory already in the plan are the right mitigation, and become more
    important.

### C4. The zero-output AudioWorklet question is settled in Chromium's source (Corrected; D5 shrinks)

- PLAN 2.2 and D5 treat "does Chrome process a zero-output worklet with no path to the destination" as open, with a
  gain-0 fallback.
- Blink's `AudioWorkletHandler::UpdatePullStatusIfNeeded` adds the node to the context's automatic-pull list whenever
  none of its outputs is connected ([audio_worklet_handler.cc](https://github.com/chromium/chromium/blob/main/third_party/blink/renderer/modules/webaudio/audio_worklet_handler.cc)).
  A node with `numberOfOutputs: 0` is therefore rendered every quantum while the context runs. The tracker bug
  "AudioWorkletNode with zero output must be pulled" is crbug 831245. Brave uses the same Blink code.
- Keep `process()` returning `true`. Per [MDN](https://developer.mozilla.org/en-US/docs/Web/API/AudioWorkletProcessor/process),
  returning false lets the node go inactive when its inputs stop. A live MediaStream input keeps it active anyway,
  but `true` removes the doubt.
- **Change:**
  - Make the zero-output node the planned path, and demote the gain-0 route to a contingency. Then the "never
    connected" comment in `piano.js` stays true.
  - D5 becomes a confirm-in-Brave plus CPU baseline, not a design fork.

### C5. Chrome does populate `MediaTrackSettings.latency` (Corrected; D4 gains a cross-check)

- LIVE 5.6 says MDN lists `getSettings().latency` as unsupported in Chrome. MDN's page shows it as not Baseline; its
  compatibility table did not render for the fetcher.
- Chromium's `MediaStreamTrackImpl::getSettings` sets `latency` whenever the platform settings have one
  ([media_stream_track_impl.cc](https://github.com/chromium/chromium/blob/main/third_party/blink/renderer/modules/mediastream/media_stream_track_impl.cc)).
  BCD lists the `latency` constraint in Chrome since 59
  ([BCD MediaStreamTrack.json](https://raw.githubusercontent.com/mdn/browser-compat-data/main/api/MediaStreamTrack.json)).
- What the number means (buffer size or true capture latency) is unverified.
- **Change:** D4 records `audioIn.stream.getAudioTracks()[0].getSettings().latency` next to the click-measured
  `L_in`. It is a free cross-check, not a replacement.

### C6. Clause numbers and dates in the terms section (Corrected, minor text fixes)

- **Link-back clause:** the Developer Policy numbers it **II.4.2**, not II.4.b
  ([policy](https://developer.spotify.com/policy)). Fix PLAN 3, PLAN 6.4 and SPOT 2.
- **Developer Terms numbering:** the storage clause renders as **IV.3.1.a** and the personal-use grant as **III.1.a**
  ([terms](https://developer.spotify.com/terms)). SPOT wrote IV.3.a and III.1.1. Medium confidence on the exact
  rendering; the wording matches.
- **Refresh-token expiry:** new apps from 2026-06-18, and **existing apps from 2026-07-20**
  ([blog](https://developer.spotify.com/blog/2026-06-18-refresh-token-expiration)). No plan change, because any app
  Daniel registers is new.

### C7. The consumer Terms of Use are broader than "recording" (Corrected, wording of PLAN 6.1)

- PLAN 6.1 and SPOT 2 read the consumer side as the User Guidelines naming recording, not listening. That reading of
  the Guidelines is right: the list covers copying, ripping, recording, transferring, circumvention, scraping and
  ML/AI training ([User Guidelines](https://www.spotify.com/us/legal/user-guidelines/)).
- The Terms of Use (last updated **2026-09-04**) do two further things
  ([Terms of Use](https://www.spotify.com/us/legal/end-user-agreement/)):
  - they grant only personal, non-commercial use (s.3);
  - they also have the user agree not to use the Service or Content in any manner not expressly permitted.
- Practising along at home is personal and non-commercial, so the plan's conclusion stands. PLAN 6.1 should cite the
  catch-all as well, and the REC notice stays as designed. This is a reading of the text, not legal advice.

---

## 1. Spotify Web API

| Claim (where) | Verdict | Source and note |
|---|---|---|
| Audio Features and Audio Analysis closed to new apps on 2024-11-27, along with Recommendations, Related Artists, Featured and Category playlists, 30 s previews in multi-get responses, and algorithmic/editorial playlists; existing Development Mode apps without a pending extension request lost them too; extended-mode apps kept them (SPOT 1.1, PLAN 0.2) | **Confirmed** | [Spotify blog 2024-11-27](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api) |
| Not reopened since (SPOT 1.1, PLAN 0.2) | **Confirmed, as far as searchable** | Feb 2026 changelog has no mention ([changelog](https://developer.spotify.com/documentation/web-api/references/changes/february-2026)). No Spotify blog post after 2026-07-23 was found. The blog index and changelog index returned 404 to the fetcher. Forum threads through 2026 still report 403 ([community](https://community.spotify.com/t5/Spotify-for-Developers/403-Forbidden-on-v1-audio-features-using-both-user-and-client/td-p/7200198)). |
| Dev Mode (Feb 2026): owner must have Premium; 5 users; 1 Client ID; new Client IDs from 2026-02-11, existing from 2026-03-09 (SPOT 1.4) | **Confirmed** | [blog 2026-02-06](https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security). On 9 March Spotify postponed only the *endpoint* restrictions for existing apps; Premium, the user cap and the Client ID limit went ahead. A lapsed owner Premium stops the app ([migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide), via search snippet). |
| 5 users is per Client ID; non-allowlisted users get 403 | **Confirmed** | [quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes) |
| Client IDs raised from 1 to 25; Dev Mode Client IDs share one quota per developer account; quota 429s carry `reason: QUOTA_EXCEEDED`; no numbers published (SPOT 1.2/1.4, PLAN 12) | **Confirmed** | [blog 2026-07-23](https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates). The post gives no effective date. |
| Rate limit counted over a rolling 30 s window; 429 with `Retry-After` | **Confirmed** | [rate limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits) |
| Extended quota: organisations only (not individuals) since May 2025; registered business, launched service, at least 250k MAU, key markets | **Confirmed** | [quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes) |
| Refresh tokens expire 6 months after authorisation; refreshing does not extend them; `400 invalid_grant`; re-login | **Confirmed**, plus a date | [blog 2026-06-18](https://developer.spotify.com/blog/2026-06-18-refresh-token-expiration); existing apps from 2026-07-20 (C6) |
| Redirect URIs: `localhost` banned; `http://127.0.0.1:PORT` or `http://[::1]:PORT`; HTTP only for loopback literals; port may be left off for loopback; new apps from 2025-04-09, existing by Nov 2025 | **Confirmed** | [redirect URI](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri) |
| Start/Resume Playback is Premium-only, needs `user-modify-playback-state`, takes `context_uri`/`uris`/`offset`/`position_ms`; order of execution with other player calls not guaranteed | **Confirmed** | [start playback](https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback) |
| Player endpoints still available in Dev Mode; Search `limit` max 10 (default 5); playlist `/tracks` became `/items` | **Confirmed** | [Feb 2026 changelog](https://developer.spotify.com/documentation/web-api/references/changes/february-2026) |
| Web Playback SDK: Premium (not mobile-only plans); Chrome/Firefox/Safari/Edge; needs EME; no commercial use without written approval | **Confirmed** | [SDK](https://developer.spotify.com/documentation/web-playback-sdk) |
| Brave ships Widevine off; enabling it in `brave://settings/extensions` installs a Google component | **Confirmed** (search snippets of Brave's own help page and tracker; the help page returned 403 to the fetcher) | [Brave help](https://support.brave.app/hc/en-us/articles/360023851591-How-do-I-view-DRM-protected-content), [brave-browser#14130](https://github.com/brave/brave-browser/issues/14130) |
| PKCE verifier in `localStorage` is per origin, so a `localhost`/`127.0.0.1` mismatch breaks login (SPOT 1.4) | **Confirmed** (web platform fact) | Same-origin rule; the redirect page above bans `localhost` |

## 2. Developer Policy, Developer Terms, consumer terms

| Claim | Verdict | Source and note |
|---|---|---|
| Developer Policy effective 15 May 2025 | **Confirmed** | [policy](https://developer.spotify.com/policy) |
| III.13 no analysis of Spotify Content "for any purpose"; III.7 no segue, mix, re-mix or overlap with other audio; III.6 no syncing sound recordings with visual media; III.2 no games including trivia; III.14 no ML/AI training or ingestion | **Confirmed** (numbers and wording) | [policy](https://developer.spotify.com/policy) |
| II.4.b link back | **Corrected: II.4.2** | C6 |
| The Policy binds developers using the Spotify Platform, so Route W plus the listener are outside it (PLAN 6.1) | **Confirmed** (reading) | Policy introduction; Terms II.9 defines an SDA as an app that accesses Spotify through, or incorporates, the Platform (widgets excluded) ([terms](https://developer.spotify.com/terms)) |
| Developer Terms v10, 15 May 2025; II.8 Spotify Content includes data and metadata; storage/compilation ban beyond what is strictly necessary; ML/AI ban (IV.2.a) | **Confirmed**, numbering per C6 | [terms](https://developer.spotify.com/terms) |
| Hobby apps are bound (personal use is inside the licence grant) | **Confirmed** | Terms III.1.a: private personal use, on Approved Devices, under the Policy |
| User Guidelines forbid recording, ripping, copying, transferring, circumvention, scraping and ML/AI training | **Confirmed** | [User Guidelines](https://www.spotify.com/us/legal/user-guidelines/) (no dated version on the page) |
| Terms of Use effective 4 Sep 2026; s.3 grants personal, non-commercial use | **Confirmed**, plus the catch-all in C7 | [Terms of Use](https://www.spotify.com/us/legal/end-user-agreement/) |

## 3. Windows media controls (SMTC)

| Claim | Verdict | Source and note |
|---|---|---|
| `GlobalSystemMediaTransportControlsSessionManager`: Windows 10 1809 (17763), UniversalApiContract v7, capability `globalMediaControl` | **Confirmed** | [Learn](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessionmanager) |
| An unpackaged `powershell.exe` needs no manifest | **Confirmed locally by WMC** (not re-run; that would read his sessions) | WMC 2 probe |
| 2020 report: Spotify returned true on `TryChangePlaybackPositionAsync` and did nothing | **Confirmed** as a report | [winrt-api#1725](https://github.com/MicrosoftDocs/winrt-api/issues/1725), opened 2020-07-14, closed; no later comment visible on whether Spotify fixed it |
| Spotify SMTC seek works today | **Unverified** | No 2024-2026 primary source either way. One search summary claiming Windows 11's flyout can scrub Spotify came from a secondary blog and does not count. **D2 stays required.** |
| PS 7 cannot use `ContentType=WindowsRuntime` | **Confirmed** | [PowerShell#13042](https://github.com/PowerShell/PowerShell/issues/13042), closed "Resolution-By Design" (2020, PS 7.1 preview 4) |
| Spotify publishes the timeline about every 4.5 s; its `lastUpdatedTime` is when the value was read; re-anchor only on a new value | **Confirmed** as a third-party README (matches WMC's local 4.50 s measurement) | [VybecordTS](https://github.com/TheUnknownMurda/VybecordTS) |
| Chromium: SMTC seek is registered only when the page enables seekto (`SetIsSeekToEnabled`); timeline from `SetPosition` → `UpdateTimelineProperties`; `PlaybackPositionChangeRequested` → `OnSeekTo` | **Confirmed** | [system_media_controls_win.cc](https://github.com/chromium/chromium/blob/main/components/system_media_controls/win/system_media_controls_win.cc) |
| pywinrt `winrt-Windows.Media.Control` 3.2.1, released 2025-06-06, wheels cp39-cp314 | **Corrected date:** PyPI upload **2025-05-20**; cp39-cp314 wheels (win32, amd64, arm64) confirmed; no newer release | [PyPI JSON](https://pypi.org/pypi/winrt-Windows.Media.Control/json), [simple index](https://pypi.org/simple/winrt-windows-media-control/) |
| `winsdk` deprecated in favour of per-namespace `winrt-*` | **Not re-checked** (low stakes; W-B is not planned) | [python-winsdk](https://github.com/pywinrt/python-winsdk) |

## 4. Browser and Web Audio

| Claim | Verdict | Source and note |
|---|---|---|
| Zero-output worklet may not be processed | **Corrected:** it is auto-pulled | C4 |
| `AudioContext.outputLatency` is Baseline 2025 | **Confirmed** (newly available March 2025) | [MDN](https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/outputLatency) |
| `MediaTrackSettings.latency` unsupported in Chrome | **Corrected:** Chromium populates it when known | C5 |
| Chrome 153 stable 2026-09-08 adds `renderSizeHint` (`128` default, an integer, or `"hardware"`) | **Confirmed** | [Chrome 153](https://developer.chrome.com/release-notes/153) |
| `http://127.0.0.1` is a secure context (EME and `crypto.subtle` work) | **Confirmed** (standard; not re-fetched) | [MDN Secure Contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts) |
| `--use-file-for-fake-audio-capture` works in this Chrome | **Unverified** (PLAN already flags it) | the section 8 wiring check |
| Recorder adds the Loopback track to takes (`piano.js` 2572-2573) | **Confirmed** (code) | `startRecording`: `stream.addTrack(track.clone())`, `rec.withAudio` |
| `audioIn` constraints: EC/NS/AGC off, `channelCount` ideal 2, analyser `fftSize` 1024, never connected to a destination | **Confirmed** (code) | `piano.js` 2471-2523 |

## 5. Libraries and licences

| Library | Plan/lane claim | Verdict | Source |
|---|---|---|---|
| Essentia.js | AGPL-3.0, "no commercial option in the file" | **Confirmed AGPL-3.0**; **corrected:** UPF/MTG offers a commercial licence, and Essentia's pre-trained models are **CC BY-NC-ND 4.0** (or proprietary on request). The 0.1.3 version and AudioWorklet support were not re-checked. | [repo](https://github.com/MTG/essentia.js), [licensing](https://essentia.upf.edu/licensing_information.html) |
| Essentia (Python) | AGPL; no Windows wheels | **Confirmed:** AGPL-3.0-only; latest 2.1b6.dev1438 (2026-05-19) has manylinux x86_64 and macOS arm64 wheels only | [PyPI JSON](https://pypi.org/pypi/essentia/json) |
| Meyda | MIT; chroma, no key or tempo | **Confirmed** | [repo](https://github.com/meyda/meyda), [features](https://meyda.js.org/audio-features) |
| aubio | GPL | **Confirmed: GPL-3.0-or-later** | [repo](https://github.com/aubio/aubio) |
| aubiojs | MIT wrapper linking GPL code | **Confirmed MIT wrapper** (pitch and tempo exposed); a build containing aubio is GPL in practice | [repo](https://github.com/qiuxiang/aubiojs) |
| realtime-bpm-analyzer | Apache-2.0; folds to 90-180; no beat phase; `bpmStable` after about 5-15 s | **Confirmed** (5.0.15 not re-checked) | [repo](https://github.com/dlepaux/realtime-bpm-analyzer), [guide](https://www.realtime-bpm-analyzer.com/guide/realtime-bpm-detection) |
| web-audio-beat-detector | MIT; AudioBuffer only; 90-180 default; `guess` gives an offset | **Confirmed** | [repo](https://github.com/chrisguttandin/web-audio-beat-detector) |
| libKeyFinder | GPL-3.0-or-later | **Confirmed** | [repo](https://github.com/mixxxdj/libkeyfinder) |
| BTrack | GPL-3; causal; DAFx-09 paper | **Confirmed** | [repo](https://github.com/adamstark/BTrack) |
| madmom | code BSD, models CC BY-NC-SA 4.0 | **Confirmed** | [repo](https://github.com/CPJKU/madmom) |
| Beat This! | MIT code and weights; ISMIR 2024; beats and downbeats | **Confirmed** | [repo](https://github.com/CPJKU/beat_this) |
| BeatNet | CC-BY-4.0; needs torch, madmom, pyaudio; streaming mode | **Confirmed.** Note: its README flags madmom 0.16.1 problems on Python ≥ 3.10 and NumPy ≥ 1.24, which is another reason it is a poor fit on this 3.11 / NumPy 2.4 machine. | [repo](https://github.com/mjhydri/BeatNet) |
| librosa 0.10.2 ISC, mir_eval MIT | as stated | **Not re-checked** (well established; librosa is already installed) | |

Plan consequence: none. PLAN 4 already keeps every AGPL/GPL/NC option out. The Essentia commercial licence does not
change that for a public Apache-2.0 repo.

## 6. Accuracy claims

| Claim | Verdict | Source and note |
|---|---|---|
| Korzeniowski & Widmer 2018 numbers quoted in LIVE 4.5 (GiantSteps AllConv 74.6/67.9; Billboard 85.1/79.9; KeyFinder `bgate` 72.4/65.0; Isophonics BD1 75.1/66.0; classical 96.6/95.2) | **Confirmed** | Table 2, [ar5iv](https://ar5iv.labs.arxiv.org/html/1808.05340) |
| Fifth plus relative errors "11-21%" | **Corrected: 9.8-21.1%** across the non-classical rows (Billboard AllConv 5.6 + 4.2; R. Williams AllConv 10.8 + 10.3; GiantSteps AllConv 7.0 + 8.1 = 15.1) | same table |
| "65-80% exact on pop for the best offline systems" (PLAN 0.3) and our tracker "60-75%" (LIVE 4.5) | **Corrected** | C3 |
| MIREX 2017 weighted ranges: GiantSteps 50.5-74.1; Billboard 67.4-82.3 | **Corrected ranges:** GiantSteps **27.02-74.11** (top FK1); Billboard 2012 **16.03-82.33** (top HS2); Isophonics top BD1 75.06; Robbie Williams top HS1 77.14. Top scores were right; the low ends were not. | [MIREX 2017](https://music-ir.org/mirex/wiki/2017:Audio_Key_Detection_Results) |
| Review arXiv 2401.00209: ACF, comb and DFT methods "suffered from frequent octave confusion" | **Confirmed** (Luck, submitted 2023-12-30) | [arXiv](https://arxiv.org/abs/2401.00209), text extracted locally |
| Dutta 2018 Acc1 69.6 / Acc2 91.2; Wu 2015 Acc1 78.5 Ballroom, 62.6 Songs; Schreiber & Müller 2018 Acc1 74.2 / Acc2 92.1 on Combined, 73.0 Acc1 on GiantSteps | **Confirmed** as reported by the review | same |
| "Classical estimators score around 50-78% Acc1 but about 90% Acc2" (LIVE 1.3) | **Corrected framing:** the quoted figures come from octave-corrected (Dutta, Wu) or CNN (Schreiber & Müller) systems, not plain ACF or comb. Plain estimators do worse on Acc1. No plan change; it strengthens ÷2/×2 and the stored level. | same |
| Acc1 = ±4%; Acc2 also accepts octave errors | **Confirmed** | same |
| Temperley profiles (major 5 2 3.5 2 4.5 4 2 4.5 2 3.5 1.5 4; minor 5 2 3.5 4.5 2 4 2 4.5 3.5 2 1.5 4) | **Confirmed** values (Temperley's revised K-S profiles, published 1999 and restated in the 2001 book) | [Essentia Key docs](https://essentia.upf.edu/reference/std_Key.html) via search; values only, not code |
| `bgate`/`edma` beat KK on dance and pop | **Confirmed** (qualitative) | [Faraldo et al. 2016](https://link.springer.com/chapter/10.1007/978-3-319-30671-1_25) |
| Every accuracy number for *this* tracker on real music | **Unverified** | AL5, D7 (PLAN already says so) |

## 7. Third-party BPM and key lookups (off in the plan)

| Claim | Verdict | Source |
|---|---|---|
| GetSongBPM: free key after email registration; backlink mandatory for any use, private included | **Confirmed** (the API page's own text, via search snippet; direct fetch was 403) | [getsongbpm.com/api](https://getsongbpm.com/api) |
| GetSongBPM 3,000 requests/hour | **Unverified** (third-party only) | [MusicTech Lab](https://musictechlab.io/blog/software-development/integrating-tempus-metronome-with-the-getsongbpm-api-what-bpm-really-means-and-how-to-use-it) |
| ReccoBeats takes Spotify ids; terms not found | **Confirmed** (still no terms page found) | [ReccoBeats docs](https://reccobeats.com/docs/apis/get-track-audio-features) |
| AcousticBrainz shut in 2022 partly because BPM and key were often "clearly wrong"; CC0 dumps | **Substance confirmed; quote corrected.** The post says BPM was incorrect for many recordings, key was accurate only on some styles, and there were no confidence values. The phrase "clearly wrong" was not found. Dumps are CC0. | [MetaBrainz blog](https://blog.metabrainz.org/2022/02/16/acousticbrainz-making-a-hard-decision-to-end-the-project/) |

## 8. Still unverified after this pass (carried, with the check that settles each)

1. Spotify honours SMTC seek → **D2**.
2. SMTC position error while playing (working bound about 2 s) → **D3**.
3. Command-to-audible latency and jitter for SMTC transport → **D1**.
4. The meaning of Chrome's `getSettings().latency` on the Focusrite Loopback → **D4** (C5).
5. The zero-output worklet in *Brave* specifically. The Blink source says yes; confirm in the browser he uses → **D5** (C4).
6. How a live KK tracker with `chord = null` behaves on relative-key near-ties → **AL-C5 plus a new near-tie fixture** (C2).
7. Real-music key and tempo accuracy → **AL5, D7** (C3).
8. The fake-capture flag in headless Chrome → the section 8 wiring check.
9. Any Spotify developer change after 2026-07-23: none found, but the blog and changelog indexes were not fetchable. Re-check before Route S is ever built.

---

## 9. Edits to make in PLAN (one line each)

- 0.3 and 10: exact-key figure → "neural 70-80%, best template about 65-69% whole-track; plan for ≤ 65% live" (C3).
- 2.2 song key: "enters through `rankKeys`' bonus" → "needs an `extraBonus` hook on `createKeyTracker.update`
  (nashville.js edit)"; add a `sounding` surrogate or a measured-gap note (C1, C2).
- 7 AL4: drop "read-only"; add the `nashville.js` hook slice and its owner and wave (C1).
- 8 AL-C5: add a vi-first near-tie fixture; mark the relative-key bar at risk (C2).
- 2.2 worklet and 9 D5: zero-output node is the planned path; `process()` returns `true`; gain-0 only as a
  contingency (C4).
- 9 D4: log `getSettings().latency` beside `L_in` (C5).
- 3 and 6.4: II.4.b → II.4.2 (C6).
- 6.1: add the Terms of Use catch-all sentence (C7).
- 4 and 11 Q3: recommended default → auto at `sure` or a stored per-song key; `[Use]` at `fair` (C3).
