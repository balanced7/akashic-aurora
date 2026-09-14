# Practice-along: the Spotify lane

| | |
|---|---|
| Status | Research and design, 2026-09-14. No code edited, nothing downloaded or installed, no accounts touched. |
| Asked | Daniel, from work: "Can we integrate Spotify as well and auto set bpm and key? That way I can practice along to music and control Spotify via the preview!" |
| Checked on this machine tonight | Two read-only PowerShell probes of the Windows media-session API (no titles printed). Spotify is installed as the Microsoft Store build (`SpotifyAB.SpotifyMusic_zpdnekdrzrea0`) and was running. It publishes a Windows media session with play/pause, next and seek enabled and playback rate disabled. The session gives position, end time, seek range and a last-updated timestamp, and has title, artist, album and a thumbnail. It was the current session. A Brave media session was also open, so /piano probably runs in Brave, not Chrome. |
| Repo facts used | `arsenal/serve.py` binds `127.0.0.1`, port 8793 by default, and its POST origin check accepts `127.0.0.1` and `localhost`. `arsenal/web/piano.js`: `audioIn` (Loopback input, analyser `fftSize` 1024, level only). `startRecording()` adds the audio-input track to the take. The key tracker reads `pcHistory`, a 12-bin decaying pitch-class histogram fed only by Daniel's note-ons. `arsenal/analysis.py` computes band power, RMS and flux only: no tempo, no key, no chroma. |

---

## 0. The answer in one screen

1. **Spotify will not give us BPM and key.** A new app gets `403` from `audio-features` and `audio-analysis`. Those
   endpoints were closed to new apps on 2024-11-27, and nothing since has reopened them (sections 1.1 and 1.5).
2. **Controlling Spotify from /piano is easy, and can be done two ways:**
   - **Route W (Windows, no Spotify account steps).** Talk to the running desktop app through the Windows media
     session. That gives play/pause, next/previous, seek, title/artist/art and position. It works tonight with nothing
     installed. Verified: the API answers, and Spotify's session advertises seek.
   - **Route S (Spotify Web API).** Daniel registers a Development Mode app and logs in once. That adds search,
     playlists, queue, device choice and exact track ids. It needs **Premium on his account**, re-login every 6 months,
     and acceptance of the Developer Terms and Policy.
3. **Auto BPM and key therefore means listening.** The page already hears the speakers through the Focusrite Loopback.
   Add a detector: chroma into a Krumhansl-Kessler song key, onset strength into tempo and beat phase. Show it as a
   suggestion he confirms. This works for any source (Spotify, YouTube, FL), with no account and no network.
4. **Policy tension, stated plainly.** The Spotify Developer Policy forbids analysing Spotify Content, and forbids
   overlapping it with other audio or syncing recordings to visuals. The consumer User Guidelines forbid recording it.
   - Route W plus a source-agnostic listener never touches the Spotify developer platform, so the Developer Policy does
     not attach to it.
   - The consumer guidelines still forbid *recording* Spotify audio. /piano's REC button records the Loopback input.
   - This is a reading of the text, not legal advice. Daniel decides (section 5).
5. **Recommendation.** Build Route W and the listener first (v1). Offer Route S as a v2 upgrade only if he wants search
   and playlists inside the page, and only after he confirms Premium and agrees to register the app.

---

## 1. Spotify Web API: what exists in September 2026

### 1.1 Audio features and audio analysis (tempo, key, mode)

| Fact | Source | Confidence |
|---|---|---|
| From 2024-11-27, **new apps** and **existing Development Mode apps without a pending extension request** lost Audio Features, Audio Analysis, Recommendations, Related Artists, Featured and Category playlists, 30 s preview URLs and algorithmic or editorial playlists. Only apps that already had extended-mode access kept them. | https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api | high |
| The reference page for Get Track's Audio Features is marked **deprecated**. It encodes key as a pitch class (0 = C, -1 = none), mode as 1 major and 0 minor, tempo in BPM, and time signature 3..7. | https://developer.spotify.com/documentation/web-api/reference/get-audio-features | high |
| Apps registered after the cut-off get `403` on `/v1/audio-features`, including personal and educational projects. Requests to Spotify for an exception get little or no answer in the forum. | https://community.spotify.com/t5/Spotify-for-Developers/403-Forbidden-on-v1-audio-features-using-both-user-and-client/td-p/7200198 , https://community.spotify.com/t5/Spotify-for-Developers/Request-to-Enable-Access-to-Audio-Features-and-Audio-Analysis/td-p/6966479 | high (many independent reports; no staff statement found) |
| The February 2026 and March 2026 changelogs do not mention audio features, so nothing reopened them. | https://developer.spotify.com/documentation/web-api/references/changes/february-2026 , https://developer.spotify.com/documentation/web-api/references/changes/march-2026 | high |

**Conclusion.** An app Daniel registers today cannot read tempo or key from Spotify. Extended quota is not a way round
it (1.5).

### 1.2 Player endpoints (the "control Spotify" half)

| Fact | Source | Confidence |
|---|---|---|
| The February 2026 changelog lists the player endpoints as **still available** in Development Mode: playback state, devices, currently playing, play/pause, seek, queue, shuffle, repeat. | https://developer.spotify.com/documentation/web-api/references/changes/february-2026 | high |
| Start/Resume Playback (`PUT /me/player/play`) works **only for Premium users** and needs `user-modify-playback-state`. Its body takes `context_uri`, `uris`, `offset` and `position_ms`, plus an optional `device_id`. Spotify warns that execution order is not guaranteed when combined with other player calls. | https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback | high |
| Get Currently Playing (`user-read-currently-playing`) returns `is_playing`, `progress_ms`, `timestamp` (when state last changed), `item.duration_ms` and `currently_playing_type`. | https://developer.spotify.com/documentation/web-api/reference/get-the-users-currently-playing-track | high |
| Scopes: `user-read-playback-state` (playback state and devices), `user-modify-playback-state` (control), `user-read-currently-playing`. `streaming` is for the Web Playback SDK and needs Premium. `app-remote-control` is iOS and Android only. | https://developer.spotify.com/documentation/web-api/concepts/scopes | high |
| Development Mode Search is capped at `limit` 10 (default 5). Playlist tracks moved to `/playlists/{id}/items`. | https://developer.spotify.com/documentation/web-api/references/changes/february-2026 | high |
| Rate limits are counted over a rolling 30 s window; `429` comes with `Retry-After`. Since July 2026, quota is shared **per developer account**, and a quota `429` carries `"reason": "QUOTA_EXCEEDED"`. No numbers are published. | https://developer.spotify.com/documentation/web-api/concepts/rate-limits , https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates | high |

The desktop app shows up as a Spotify Connect device, so every Web API command reaches it through Spotify's cloud.
Expect a network round trip per command, not a local call. The size of that latency is not measured here.

### 1.3 Web Playback SDK (the page itself as a player)

| Fact | Source | Confidence |
|---|---|---|
| Needs Spotify **Premium** (mobile-only plans excluded). Supported browsers: Chrome, Firefox, Safari, Edge. Needs EME (encrypted media); initialisation fails without it. | https://developer.spotify.com/documentation/web-playback-sdk , https://developer.spotify.com/documentation/web-playback-sdk/reference | high |
| It creates a Connect device in the page. Methods include `connect`, `getCurrentState` (position, paused, `track_window`), `seek`, `togglePlay`, volume and `activateElement` (for autoplay rules). Events include `player_state_changed`, `autoplay_failed` and `playback_error`. | same | high |
| Not for commercial projects without Spotify's written approval. | https://developer.spotify.com/documentation/web-playback-sdk | high |
| **Brave ships Widevine disabled.** Enabling it in `brave://settings/extensions` installs a Google component and needs a restart. That counts as a download under house rules, so Daniel approves it. | https://support.brave.app/hc/en-us/articles/360023851591-How-do-I-view-DRM-protected-content | high |
| `http://127.0.0.1` is a secure context, so EME and `crypto.subtle` (PKCE) work on the arsenal server's origin without HTTPS. | https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts | high |
| SDK audio is DRM-protected media, so the page cannot tap it with Web Audio. It still leaves through Brave's output device, so it reaches the Loopback input if that device feeds the Focusrite. | inference from the EME design; not tested | medium |

**Verdict.** The SDK adds nothing Daniel needs while the desktop app is running. It costs a Widevine enable in Brave and
Premium. Keep it out of v1.

### 1.4 App registration, OAuth, redirect URIs

| Fact | Source | Confidence |
|---|---|---|
| **Redirect URIs.** `localhost` is **not allowed**. Use `http://127.0.0.1:PORT` or `http://[::1]:PORT`; only those loopback literals may use plain HTTP. A loopback URI may be registered without a port, with the port added at request time. Enforced for new apps from 2025-04-09 and for all apps by November 2025. | https://developer.spotify.com/documentation/web-api/concepts/redirect_uri | high |
| **PKCE** (Authorization Code with PKCE) is the recommended flow for single-page apps. No client secret; the verifier lives in `localStorage` across the redirect. A refresh may or may not return a new refresh token; keep the old one if it does not. | https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow | high |
| **Refresh tokens expire 6 months** after the original authorisation, and refreshing does not extend them. New apps are affected immediately (from 2026-06-18). Expiry returns `400 invalid_grant`, and the app must send the user through login again. Scopes carry over. | https://developer.spotify.com/blog/2026-06-18-refresh-token-expiration | high |
| **Development Mode (Feb 2026).** The app owner must have **active Premium**, or the app stops working. At most 5 allowlisted users, added in Dashboard > Settings > Users Management; a user not on the list gets `403`. New apps from 2026-02-11; existing ones migrated 2026-03-09. The Feb 2026 blog says the endpoint restrictions on existing apps were postponed; the migration guide gives 2026-03-09. Either way, a new app gets the restricted set. | https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security , https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide , https://developer.spotify.com/documentation/web-api/concepts/quota-modes | high |
| Development Mode is described as for learning, experimentation and **personal, non-commercial** projects. | https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security | high |
| **Client IDs per developer account** raised from 1 to 25 (2026-07-23). | https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates | high |
| **Extended quota** (unlimited users) requires a legally registered organisation, a launched service, at least 250,000 MAU, key markets and commercial viability. Since May 2025 individuals are not eligible. | https://developer.spotify.com/documentation/web-api/concepts/quota-modes | high |

**Gotcha for /piano.** `localStorage` is per origin. If /piano is opened at `http://localhost:8793` and the redirect
lands on `http://127.0.0.1:8793`, the PKCE verifier is on the other origin and the login fails. The Spotify button must
send the page to `127.0.0.1` first, or the page must refuse to start login from `localhost`.

### 1.5 Is there a sanctioned way back to tempo and key? No.

- Extended quota needs an organisation with 250k MAU (1.4).
- The one exception route is asking Spotify, which forum reports say goes unanswered (1.1).
- Treat the endpoints as gone for this project.

---

## 2. Terms that bear on practice-along

Quotes are short phrases only; the section numbers are the documents' own.

| Document | Clause | What it says (paraphrase, short quote) | Bears on |
|---|---|---|---|
| Developer Policy (effective 15 May 2025), III.13 | analysis | "Do not analyze the Spotify Content" for any purpose | any detector inside an app built on the Spotify Platform |
| Developer Policy, III.7 | overlap | no device or system may segue, mix, re-mix or **overlap** Spotify Content with other audio | Claude's backing loop sounding over a Spotify track *in the same app* |
| Developer Policy, III.6 | sync | do not synchronize sound recordings with visual media | recorded takes; arguably audio-reactive visuals |
| Developer Policy, III.2 | games | do not create a game, including trivia | scoring "found" or streaks against a Spotify track |
| Developer Policy, III.14; Developer Terms IV.2.a | AI | no training or ingesting Spotify Content into an ML/AI model | never hand Spotify audio or metadata to Claude for learning; a chat summary of a practice session is a grey edge |
| Developer Policy, II.4.b | link back | metadata and cover art must link back to the Spotify item | Route S "now playing" card |
| Developer Terms (v10, 15 May 2025), IV.3.a | databases | no storing, aggregating or compiling Spotify Content beyond what is strictly necessary; II.8 defines Spotify Content to include data and metadata | a local per-track cache of detected key and BPM keyed by Spotify id |
| Developer Terms, II.9 | scope | an SDA is anything that accesses Spotify through, or incorporates, the Spotify Platform. III.1.1 covers private personal use, so hobby apps are bound | Route S makes /piano an SDA; Route W does not use the Platform |
| Spotify User Guidelines | recording | no copying, "ripping," **recording** or transferring Content; no circumventing technology; no automated scraping | REC with Spotify in the Loopback; any "save the song" feature |
| Spotify Terms of Use (effective 4 Sep 2026), s.3 | grant | permission to make "personal, non-commercial use" of the service | the baseline for all of this |

Sources: https://developer.spotify.com/policy , https://developer.spotify.com/terms ,
https://www.spotify.com/us/legal/user-guidelines/ , https://www.spotify.com/us/legal/end-user-agreement/

**Reading (not legal advice):**
- The Developer Policy binds apps that use the Spotify Platform (APIs, SDKs, widgets).
- Route W plus a listener that reads the speakers never calls the Platform. The Developer Policy's analysis and overlap
  clauses do not attach to it.
- The consumer User Guidelines do attach, and they name recording, not listening.
- If Daniel chooses Route S, the same page becomes an SDA, and III.13 and III.7 then read directly against the listener
  and Claude's loop. In that case keep them apart: Route S controls, the listener is off while Spotify is the source,
  and he taps the tempo himself.

---

## 3. The Spotify desktop app's own local control options

| Option | What it gives | Verified | Notes |
|---|---|---|---|
| **Windows media session** (`Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager`) | play, pause, toggle, next, previous, `TryChangePlaybackPositionAsync` (seek, in ticks), title, artist, album, thumbnail, `GetTimelineProperties` (position, end, seek range, last updated), change events | **yes, read-only probe tonight** in Windows PowerShell 5.1 with no installs. Spotify's session: `playPause=True next=True seek=True rate=False`; position, end and `lastUpdated` present; title, artist, album and thumbnail present | Microsoft reference: https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssession . No playback rate, so no slow-down practice on Spotify tracks. Seek was advertised but not executed (that would change his playback). Position is event-updated; between events it must be interpolated (`pos + (now - lastUpdated)` while playing). The probe showed `lastUpdated` 1.3 s old while paused. |
| **`spotify:` URI scheme** | opens a track, album or playlist in the app | no | Community reports say it only auto-plays in some cases; a `#m:ss` suffix is a reported workaround: https://community.spotify.com/t5/Spotify-for-Developers/common-uri-commands-for-windows/td-p/5286728 (low confidence, forum). The Store build registers the scheme; launching it would bring the Spotify window forward, so avoid during REC. |
| Media keys (virtual key events) | play/pause, next, previous | no | Strictly weaker than the media session; skip. |
| Web API to the desktop device | everything in 1.2 | no (needs an app and a login) | round trip through Spotify's cloud |

**How the arsenal server reaches the media session without installs.**
- Python needs the `winrt`/`winsdk` packages for WinRT, and that is a pip install (needs approval).
- Instead, `serve.py` can spawn a small **Windows PowerShell 5.1 sidecar**: `powershell.exe -NoProfile`, with its window
  hidden or created without a console so no window shows. It speaks JSON lines on stdin and stdout.
- The WinRT projection used by the probe (`[Windows.Media.Control....,ContentType=WindowsRuntime]` plus `AsTask`) is
  built into Windows PowerShell 5.1.
- PowerShell 7 dropped built-in WinRT interop, so pin `powershell.exe` (medium confidence on PS 7; 5.1 verified tonight).

**Privacy.**
- The session manager lists every app's media (tonight: Riot Client, Brave, Spotify). Filter to
  `SourceAppUserModelId` starting `SpotifyAB.` (plus the FL Studio id if wanted), and never forward other sessions.
- Track titles stay in `state/` (git-ignored). The repo is public.

---

## 4. Design: practice-along on /piano

### 4.1 Pieces

```
Spotify desktop ──(Windows media session)──> smtc sidecar (powershell 5.1, JSON lines)
                                                   │
                                arsenal/serve.py   ├─ GET  /api/piano/source            {app, title, artist, art_url, is_playing, pos_ms, dur_ms, at_epoch_ms}
                                                   ├─ POST /api/piano/source/control    {op: play|pause|toggle|next|prev|seek, pos_ms?}
                                                   └─ event "source" on /api/piano/cues (same stream as cue/deck/jam)
speakers ──> Focusrite Loopback ──> audioIn (existing) ──> listen.js (new AudioWorklet or analyser pair)
                                                              ├─ chroma (12 bins) ──> createKeyTracker (a SECOND instance) ──> song key
                                                              └─ onset strength ──> tempo + beat phase ──> song tempo map
page: "Song" strip  ── song key, bpm, confidence, [Use for jam] [Tap] [Lock] ── transport buttons ── A-B repeat
```

- **Source bridge (Route W).**
  - The sidecar subscribes to `MediaPropertiesChanged`, `PlaybackInfoChanged` and `TimelinePropertiesChanged`, and also
    polls the timeline every 500 ms as a fallback.
  - The server publishes a `source` event only on change. The thumbnail stream is copied into a data URL or a local
    route, never a remote URL.
  - Controls map one-to-one onto the `Try*Async` methods. Refuse `seek` when `IsPlaybackPositionEnabled` is false.
  - POST goes through the existing `_cue_post` origin check.
- **Listener (`listen.js`, source-agnostic).**
  - **Key.** Log-frequency chroma from a second analyser (`fftSize` 16384 at 48 kHz, about 2.9 Hz bins, 80 Hz-5 kHz,
    harmonic weighting), or a constant-Q in an AudioWorklet. Frame chroma decays into a 12-bin histogram fed to
    `createKeyTracker({holdSec: 8})`. That reuses the Krumhansl-Kessler ranking and anti-flicker Daniel's tracker
    already has.
    **It must be a separate instance with its own histogram.** INT invariant 1 in the jam spec keeps Daniel's label,
    numbers and tracker his alone.
  - **Tempo.** Spectral-flux onset envelope at a ~10 ms hop, autocorrelation over 8-12 s, candidates 60-180 bpm with a
    prior near 100-120. Report half and double as alternates. Phase comes from a comb filter against the envelope.
  - **Confidence.** K-K correlation margin between the top two keys; peak-to-median ratio of the autocorrelation.
  - **Contamination guard.** The Loopback carries Daniel's own piano sound and Claude's voice as well as the song:
    - Freeze the song histogram while Daniel's notes sound (`sounding` non-empty) and while a jam run plays.
    - Or learn only in the first 20 s after a track change, before he joins.
    - Relative-minor and fifth confusions are the usual errors: show the runner-up as a one-tap swap.
- **Song strip (DOM, outside the recorded canvas, like the jam spec's Now header).**
  - Shows `Song · Eb major (listening 72%) · 92 bpm (or 46/184) · [Use] [Tap] [Lock]`, plus the source transport:
    `|< play/pause >|`, a scrub bar from `pos_ms`/`dur_ms`, and A-B repeat.
  - A-B repeat is a page timer that seeks back to A when interpolated position passes B. Spotify gives no loop points;
    seek latency is unmeasured, so expect a small gap.
- **Hand-off to the jam space.**
  - `Use` sets the jam key and bpm the same way the key selector and tap tempo do in jam-spec 8.3 ("song key" becomes a
    fourth option beside *my key now*).
  - Nashville chips then read relative to the song.
  - `Lock` pins them against further detection. Nothing changes the jam key without a click ("stage before correctness":
    a suggestion, not a verdict).
- **Recording.** When the source bridge reports Spotify playing, REC shows a one-line notice that the Loopback includes
  Spotify, with a per-take choice *record my input without the Loopback* (canvas plus no audio, or a second input).
  The User Guidelines name recording (section 2). The default is Daniel's call (Q3).

### 4.2 Route S (v2, only on Daniel's yes)

- **Page.** A `Connect Spotify` button that first moves to `http://127.0.0.1:8793/piano` (1.4 gotcha), then runs PKCE
  with scopes `user-read-playback-state user-modify-playback-state user-read-currently-playing`. Add `streaming
  user-read-email user-read-private` only if the SDK is wanted.
- **Tokens.** In the page's `localStorage` (per-viewer convenience) or a git-ignored `state/arsenal/spotify/token.json`
  written by the server. Handle `invalid_grant` by showing `Reconnect Spotify` (every 6 months).
- **Adds over Route W.** Search (limit 10), his playlists, queue a track, pick a device, exact `spotify:track:` URIs for
  A-B presets, a link back to the item on the now-playing card (Policy II.4.b).
- **Keep using Route W for position.** Polling `GET /me/player` at 1 Hz spends shared developer-account quota for
  something the media session gives locally for free.
- **Terms consequence.** The page becomes an SDA (section 2): while the source is Spotify via Route S, the listener stays
  off, Claude's loop does not sound over the track, and the key and tempo come from Daniel's ear and `Tap`.

### 4.3 Third-party BPM and key lookups (considered, not recommended for v1)

| Service | Access | Returns | Problem here | Source |
|---|---|---|---|---|
| ReccoBeats | free, no key stated, undisclosed rate limits | Spotify-shaped audio features by Spotify id, and extraction from uploaded audio | sends what he listens to off the machine ("practice data stays local"); needs the Spotify id (Route S); data origin undisclosed; uploading audio would transfer Spotify Content | https://reccobeats.com/docs/apis/reccobeats-api , https://reccobeats.com/docs/documentation/rate-limiting |
| GetSongBPM | free API key (account registration), 3,000 req/h reported | tempo, key, Open Key by title/artist search | mandatory public backlink or suspension, even for private use; account step; network egress of titles | https://getsongbpm.com/api (403 to our fetcher; terms via search snippets and https://metacpan.org/pod/WebService::GetSongBPM ), medium confidence |

Either could become an optional "second opinion" behind a switch, with Daniel's approval for the account (GetSongBPM)
and for the egress.

---

## 5. What Daniel does himself, per route

| Route | Daniel's steps | We build |
|---|---|---|
| **W + listener (v1)** | None to start. Optional: confirm Spotify's output reaches the Focusrite Loopback (it does if Windows' default output is the Focusrite), and choose the REC default (Q3). | sidecar, `/api/piano/source` routes and event, `listen.js`, Song strip, A-B repeat, REC notice, jam hand-off (`Use`) |
| **S (v2)** | Confirm Premium. Sign in at developer.spotify.com, accept the Developer Terms, create an app (Web API; Web Playback SDK only if wanted), add redirect URI `http://127.0.0.1:8793/spotify/callback`, paste the Client ID into the page or a git-ignored config. Log in once through the page's PKCE button. Re-login every 6 months. | PKCE module, token refresh and expiry path, search/playlist/queue panel, link-back card |
| **SDK (not planned)** | Everything in S, plus enabling Widevine in Brave (a Google component download; restart Brave). | a Connect device inside /piano |

---

## 6. Drills before calling anything done (drill doctrine: each path ships with a dated receipt)

1. **Media session control drill.** With Daniel's go: pause, play, next, and seek to 0:30 on Spotify from the sidecar.
   Record the seek landing error from `GetTimelineProperties` 500 ms later.
2. **Position accuracy.** Interpolated `pos` against the Loopback onset of a known track start, 10 trials. This decides
   whether A-B repeat and beat phase can use media-session time or must use the listener's phase.
3. **Detector accuracy.** 10 songs Daniel knows by ear (his keys: Eb F D Gb Db). Log detected key and bpm, runner-up and
   confidence, and his verdict. Pass bar is his call; report the confusion types (relative, fifth, half/double tempo).
4. **Contamination.** Play along on the KeyLab over a track and confirm the song key does not drift to his playing
   while the freeze guard is on.
5. **No window.** Confirm the sidecar spawns with no visible console (house rule: no visible windows).

---

## 7. Open questions for Daniel (one at a time in chat; Q1 first)

1. **Does your Spotify account have Premium?** Route S and the SDK need it. Route W does not.
2. Is *Windows media controls plus the page listening* enough for "control Spotify via the preview", or do you want
   search and playlists inside /piano (Route S, with the registration steps)?
3. When you hit REC while Spotify plays: record the Loopback (the song ends up in the take), or record only your side?
4. Should "auto set" apply automatically when confidence is high, or always wait for your `Use` click?
