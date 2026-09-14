# Lane: Windows media controls (SMTC) for practice-along

Date: 2026-09-14. Status: research and design only. No installs, downloads, logins or code edits were made.
Question from Daniel (Discord): "Can we integrate Spotify as well and auto set bpm and key? That way I can practice along
to music and control Spotify via the preview!"

This lane answers one part: can a local process read what Spotify (or a browser) is playing and drive its transport
through Windows' System Media Transport Controls, with **no Spotify OAuth**?

## 1. Short answer

- **Yes for reading and for play/pause/next/previous, with nothing to install.** Tested on this machine, read-only:
  Windows PowerShell 5.1 loads `Windows.Media.Control` and lists live sessions. Spotify 1.298.301.0 (Microsoft Store
  build) shows up with title, artist, play state, shuffle/repeat, and a timeline (start, end, position, seek range).
- **Seek is uncertain for Spotify.** Spotify now *advertises* seek (`IsPlaybackPositionEnabled=True`). A 2020 report
  says the call "returned true" and did nothing. It was not tested here, because sending a command would change
  Daniel's playback. It needs a short drill with him present (section 7).
- **Position is coarse.** Spotify republishes its timeline about every **4.5 s** (measured here, section 4). Between
  publishes the position must be extrapolated. That is fine for a progress bar, but too coarse to line beats up with.
  Beat and bar alignment should come from the loopback audio the piano page already receives.
- **SMTC carries no BPM or key.** Spotify's Audio Features and Audio Analysis endpoints have been closed to new apps
  since 2024-11-27 ([Spotify dev blog](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)). So BPM
  and key have to come from our own analysis of the audio. SMTC's job is **track identity** (a changed title means
  resetting the estimators), **transport**, and **coarse position**.

## 2. What is on this machine (read-only checks, 2026-09-14)

| Item | Finding | How checked |
|---|---|---|
| Windows | Windows 11 Pro 10.0.26200 (25H2) | environment |
| Spotify | Store/MSIX package `SpotifyAB.SpotifyMusic` **1.298.301.0**, at `C:\Program Files\WindowsApps\SpotifyAB.SpotifyMusic_1.298.301.0_x64__zpdnekdrzrea0`. No classic `%APPDATA%\Spotify\Spotify.exe`. It was already running (pid 17316), not started by me. | `Get-AppxPackage`, `Get-Process` |
| Windows PowerShell | 5.1.26100.9168. `[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]` **loads**. | type load |
| PowerShell 7 (`pwsh`) | not installed. That doesn't matter: PS 7 can't use the `ContentType=WindowsRuntime` syntax anyway ([PowerShell#13042](https://github.com/PowerShell/PowerShell/issues/13042)). | `Get-Command pwsh` |
| Python | 3.11.9 (pinned default) and 3.14 installed | `py -0p` |
| Python WinRT packages | **none**: no `winrt-*`, no `winsdk`. Present but not useful for this: `pywin32 311`, `comtypes 1.4.16`. Also present: `av 17.0.0`, `librosa 0.10.2`, `numpy 2.4.4` (relevant to the BPM/key lanes). | `py -m pip list` |
| Node | v24.14.1. No SMTC binding found in the repo. | `node --version`, repo grep |
| Existing repo SMTC code | none in `arsenal/`. `serve.py` is a `ThreadingHTTPServer` that already has an SSE pattern (`GET /api/piano/cues`) and an Origin guard limited to 127.0.0.1/localhost (`_cue_post`). | Grep/Read `arsenal/serve.py` |

### Live session snapshot (read-only probe; titles and artists deliberately not recorded)

| Session (AUMID) | Status | Controls advertised | Timeline |
|---|---|---|---|
| `SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify` (Windows' "current" session) | Paused | play, toggle, next, prev, stop, **seek(position)=True**, shuffle, repeat, ff, rw; rate=False | end 2:34, position 2:21.726, seek range 0 to 2:34, LastUpdatedTime 3.3 s old |
| `Brave` | Paused | play, toggle, stop, seek=True; next/prev=False (the page had no handlers) | position 0:14.76 of 0:47.66, LastUpdatedTime about 5.4 h old |
| `com.riotgames.RiotGames.RiotClient` | Paused | play, toggle, stop only | empty timeline, LastUpdatedTime = 1601 epoch (zero DateTime) |

Lessons from the snapshot:
- (a) Other apps publish sessions too, such as the Riot client. Pick the session **by AUMID prefix**, not with
  `GetCurrentSession()`.
- (b) A timeline with a zero or very old `LastUpdatedTime` is garbage and must be ignored.
- (c) Browsers register under the browser's name (`Brave`), not under the site's name.

## 3. The API surface (primary: Microsoft Learn)

`Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager` has these members:
- `RequestAsync()`
- `GetCurrentSession()`
- `GetSessions()`
- events `CurrentSessionChanged` and `SessionsChanged`

Each `GlobalSystemMediaTransportControlsSession` has ([class page](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssession)):
- `SourceAppUserModelId`
- `TryGetMediaPropertiesAsync()`: title, artist, album, thumbnail, playback type
- `GetPlaybackInfo()`: status, rate, shuffle, repeat, and `Controls.Is*Enabled`
- `GetTimelineProperties()`: StartTime, EndTime, MinSeekTime, MaxSeekTime, Position, LastUpdatedTime
- commands: `TryPlayAsync`, `TryPauseAsync`, `TryTogglePlayPauseAsync`, `TrySkipNextAsync`, `TrySkipPreviousAsync`,
  `TryStopAsync`, `TryChangePlaybackPositionAsync(Int64 ticks)` (1 tick = 100 ns), `TryChangePlaybackRateAsync`,
  `TryChangeShuffleActiveAsync`, `TryChangeAutoRepeatModeAsync`, `TryFastForwardAsync`, `TryRewindAsync`
- events `MediaPropertiesChanged`, `PlaybackInfoChanged`, `TimelinePropertiesChanged`

Requirements and definitions:
- Minimum Windows 10 1809 (17763).
- The docs list the `globalMediaControl` app capability. That applies to packaged apps. **An unpackaged desktop
  process needs no manifest.** This was proven here: plain `powershell.exe` read every session.
- `LastUpdatedTime` is defined as "The UTC time at which the timeline properties were last updated"
  ([Learn](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessiontimelineproperties.lastupdatedtime)).

A `Try*Async` result of `true` only means the request was delivered. It does **not** mean the app acted on it. That is
exactly how the Spotify seek no-op shows up (section 5).

## 4. Latency and position accuracy (measured here unless marked)

| Operation | Measured | Notes |
|---|---|---|
| `RequestAsync()` (first call in a process) | 21 ms | one-time |
| `TryGetMediaPropertiesAsync()` per session | 0.4 to 3.8 ms | fast enough to call on every change event |
| `GetPlaybackInfo()` + `GetTimelineProperties()` | about 0.01 ms | synchronous, so polling at 4 to 10 Hz costs nothing |
| `powershell.exe -NoProfile` cold start + WinRT type load | 107 to 112 ms (3 runs) | paid once if a sidecar stays alive, per call if spawned per command |
| Command round trip (play/pause/next/seek to Spotify reacting) | **not measured** | needs the drill in section 7 |
| Spotify timeline publish cadence | **about 4.50 s**: stamps 14:05:56.990, 14:06:01.491, 14:06:06.006 (sampled every 100 ms for 12 s, while paused) | position stayed at 2:21.726 while paused, but `LastUpdatedTime` still advanced |

The 4.5 s cadence matches an independent project's note that Spotify "does so every 4.5s", and its warning that
Spotify's `lastUpdatedTime` marks when the value was *read*, not measured. A resync can therefore look fresh while being
about two seconds behind. Its remedy is to extrapolate from a monotonic anchor and re-anchor only on a position value
not seen before ([VybecordTS README](https://github.com/TheUnknownMurda/VybecordTS); not re-verified here while music
was playing).

Design consequence: SMTC position error while playing should be treated as **up to about 2 s** until the drill
measures it. For practice-along, SMTC position is good for:
- a progress bar
- "which section of the song"
- seek targets

It is **not** good for bar-one alignment. Tempo phase should come from onset analysis of the Focusrite loopback the
page already has (`audioIn` in `arsenal/web/piano.js`).

## 5. Known limits with Spotify and browsers

- **Spotify seek.** There is a July 2020 report (MicrosoftDocs/winrt-api
  [#1725](https://github.com/MicrosoftDocs/winrt-api/issues/1725)) that `TryChangePlaybackPositionAsync` on Spotify
  "returned true" with no effect, while Movies & TV jumped to the start. Today's Spotify 1.298 advertises
  `IsPlaybackPositionEnabled=True`, which may mean it was fixed. I found no 2024 to 2026 primary source either way.
  FluentFlyout only says its seek slider appears when a player supports it
  ([FluentFlyout](https://github.com/unchihugo/FluentFlyout)). **Status: UNVERIFIED, drill required.**
- **Spotify metadata.** Title and artist are present. SMTC has no album-art URL, BPM, key or track ID. A song change
  can only be detected from a title/artist change.
- **Spotify extra controls.** One third-party widget reads Spotify's favorites, shuffle, repeat and volume through UI
  Automation, because "there is no clean API"
  ([spotify-taskbar-widget](https://github.com/mechanicwb2-hub/spotify-taskbar-widget)). That is out of scope here.
- **Seek fallbacks if SMTC seek is a no-op:**
  - Spotify Web API [seek](https://developer.spotify.com/documentation/web-api/reference/seek-to-position-in-currently-playing-track)
    needs OAuth and Premium. That is an account step, so Daniel's decision.
  - Keyboard seek shortcuts need Spotify focused. Spotify's own
    [shortcuts page](https://support.spotify.com/us/article/keyboard-shortcuts/) lists play/pause, next, previous,
    shuffle and repeat, but **no seek**. Third-party lists claim Shift+Left/Right; that is unverified. Stealing focus
    from the piano page defeats the purpose anyway.
  - Accept "previous = restart track" and loop sections from our own analysis instead.
- **Browsers / YouTube.**
  - Chromium publishes the page's Media Session to SMTC and handles `PlaybackPositionChangeRequested` by forwarding
    `OnSeekTo`. It updates timeline properties from the page's position state (`SetPosition`, then
    `UpdateTimelineProperties`) ([chromium source](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/system_media_controls/win/system_media_controls_win.cc)).
  - Seek therefore works when the site implements the `seekto` action and position state
    ([web.dev Media Session](https://web.dev/articles/media-session)). Next/prev appear only when the site registers
    handlers. The Brave session here showed next/prev=False.
  - The session is named after the browser. Several tabs can compete, and SMTC exposes one session per browser media
    session, as Windows picks it.
- **FL Studio.** Not seen in the session list. It is unlikely to publish SMTC; its transport belongs to the separate
  fl-jam-bridge lane.

## 6. Library options

| Option | Install needed | Read | Control | Events | Verdict |
|---|---|---|---|---|---|
| **Windows PowerShell 5.1 + WinRT projection** (built in) | none | yes (proven here) | yes (API present; not exercised) | `Register-ObjectEvent` on WinRT events is possible but awkward; polling the sync getters at 4 to 10 Hz is cheap | **Zero-install route.** A long-lived hidden sidecar speaking JSON lines over stdin/stdout. |
| **pywinrt modular packages** for Python 3.11: `winrt-runtime`, `winrt-Windows.Media.Control`, `winrt-Windows.Foundation`, `winrt-Windows.Foundation.Collections` (+ `winrt-Windows.Storage.Streams` for thumbnails) | yes: 4 to 5 wheels from PyPI, v3.2.1 released 2025-06-06, wheels for cp39 to cp314 (win_amd64/arm64/win32) on the PyPI simple index, so both Python 3.11 and 3.14 are covered ([PyPI](https://pypi.org/project/winrt-Windows.Media.Control/), [changelog](https://github.com/pywinrt/pywinrt/blob/main/CHANGELOG.md)) | yes | yes | `add_*_changed` handlers. Callbacks arrive on a non-main thread outside an STA GUI thread, and the async methods are awaitable but "are not" coroutines ([pywinrt types](https://pywinrt.readthedocs.io/en/latest/types.html)) | **Cleanest in-process route** inside `arsenal/serve.py`. Needs Daniel's install approval. |
| `winsdk` (monolithic) | yes | yes | yes | yes | **Deprecated**: replaced in September 2023 by the per-namespace `winrt-*` packages ([python-winsdk](https://github.com/pywinrt/python-winsdk)). Do not use. |
| npm `windows-media-sessions` 1.0.3 (2026-05) | yes: npm package plus a bundled ~15 MB self-contained .NET 8 exe | yes | **no**: it reports `canPlay`/`canSkipNext` but documents no command methods ([repo](https://github.com/Gyom03/windows-media-sessions), [registry](https://registry.npmjs.org/windows-media-sessions)) | yes (~1 s position updates) | Read-only, so no good for a remote control. |
| npm `@nodert-win10-20h1/windows.media.control` | yes, plus native build (node-gyp, VS build tools) | yes | yes | yes | Last published about 5 years ago ([npm](https://www.npmjs.com/package/@nodert-win10-20h1/windows.media.control)). Stale; avoid. |
| .NET `Dubya.WindowsMediaController` (NuGet) | yes, plus a .NET build | yes | yes | yes (session, focus, property, playback and timeline events) | Good library ([repo](https://github.com/DubyaDude/WindowsMediaController)), but it adds a build toolchain to a Python project. |

Summary: the arsenal server is Python, so **Node is the wrong home**. There are two sound routes:
- **Route A (now, no approvals):** `serve.py` spawns one hidden `powershell.exe -NoProfile -NonInteractive` sidecar
  (Popen with `CREATE_NO_WINDOW`). The sidecar polls sessions at about 4 Hz, prints JSON lines on change, and reads
  JSON commands on stdin. It costs about 110 ms once at startup.
- **Route B (after approval):** pywinrt in a `serve.py` worker thread with its own asyncio loop and event handlers. It
  has lower overhead and no child process, but needs 4 to 5 wheels.

Both expose the same HTTP surface, so the page doesn't care which one is running.

The PS 5.1 await helper that makes Route A work (load-bearing; it was the non-obvious part):

```powershell
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
  $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $null = $task.Wait(5000); $task.Result }
```

Commands would use the same helper with `[bool]` as the result type, for example
`Await ($s.TryTogglePlayPauseAsync()) ([bool])`.

## 7. Proposed design for the /piano page (for the jam-spec owner to fold in)

HTTP surface on `arsenal/serve.py`. It reuses the existing Origin guard (127.0.0.1/localhost only) and the SSE hub
pattern:
- `GET /api/media-session`: a snapshot of `{sessions:[{aumid, app, title, artist, status, controls{...}, timeline{startMs,
  endMs, positionMs, lastUpdatedUtc, anchorMonoMs}}], selected}`.
- Change events pushed on the existing `/api/piano/cues` stream as a new frame type, or on a sibling SSE stream:
  `track` (title/artist changed, so the page resets its tempo/key estimator), `status`, and `timeline`.
- `POST /api/media-session/control {action: play|pause|toggle|next|previous|seek, positionMs?, aumid?}` returns
  `{delivered: bool, observed: bool|null}`. `observed` is filled in by re-reading status/timeline about 300 ms later,
  so the page can tell "Spotify ignored the seek" apart from "done".
- Session selection: prefer an AUMID starting with `SpotifyAB.SpotifyMusic`, then any browser with a non-stale
  timeline. Ignore sessions whose `LastUpdatedTime` is the zero DateTime.
- Position on the page: a monotonic-clock extrapolation from `(positionMs, anchor)`. Re-anchor only on a position value
  not seen before; freeze while not Playing.
- Privacy: titles and artists stay in memory. If the practice log records them, they stay on local disk, per the house
  rule. Nothing leaves the machine and no Spotify account is involved.

### Drills to run with Daniel present (each changes his playback, so ask first)

1. Toggle play/pause and next/previous on Spotify from the sidecar. Time it from the command to `PlaybackInfoChanged`,
   and to audible change on the loopback.
2. `TryChangePlaybackPositionAsync` on Spotify 1.298 to a mid-track point (ticks = ms x 10,000). Record `delivered`
   and whether the position actually moved. This settles the 2020 no-op question.
3. While Spotify plays, sample the timeline every 50 ms for 30 s. Compare the extrapolated position with the real one.
   Use a loopback onset cross-correlation against a known track position to bound SMTC's error (the working assumption
   is up to about 2 s).
4. Same as 1 and 2 on a YouTube tab in Brave.

## 8. Open questions

- Does Spotify 1.298 honour SMTC seek now that it advertises it? (drill 2)
- Real command latency Spotify-side, and SMTC position error while playing. (drills 1 and 3)
- Can a PS 5.1 sidecar subscribe to WinRT events cleanly, or is 4 Hz polling the steady state? Polling is already
  enough on cost grounds.
- Should practice logs record track title/artist (local only)? That is Daniel's call.
