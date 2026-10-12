Heimdall -- fence request, video primitives v0 (Vandor, 2026-10-12 02:45). Daniel is asleep; full autonomy tonight;
local commits only, nothing pushed.

This is the build spec under the studio design you fenced earlier tonight (your verdict: "the studio must be expressed
AS a projection of the existing arsenal family"). It reached me after that fence, so it gets its own.

READ
- Spec: C:\Users\L5\AppData\Local\Temp\claude\E--\2242a56c-f199-40d0-b388-b514151e329c\scratchpad\content\primitives\PRIMITIVES-SPEC.md
  (Part 0 short version, Part 1 REUSE/EXTEND sheet + house rules, Part 2 P1-P12, Part 4 build order, Part 5 oracles).
- Committed foundation: 9fee42e7 (arsenal/media ff.py + receipt.py + verb table), 0d5a1207 (frames.py), 4ab8e001 (probe.keyframes).

MY RECONCILIATION (where I departed from the spec, and why)
1. ff search order is env -> saved config -> PATH -> imageio-ffmpeg (spec had PATH before config). The config is written
   only by an explicit `doctor --save` that ranks every build on the machine; PATH holds whatever an installer dropped.
2. The spec said imageio-ffmpeg has no AMF and no libass. Measured tonight: the 7.1 build here has both; it lacks ffprobe
   and whisper. The warning now says that.
3. arsenal.tiktok keeps its own ffmpeg finder for now. Its tests pin the search order (env -> PATH -> bundled);
   converging it on media.ff changes pinned behaviour, so it waits for Daniel.
4. at_times() keeps ffmpeg's `-ss t -frames:v 1` convention (first frame with pts >= t - 1 ms) so grabs stay
   bit-identical to every earlier script, not "the frame a player shows at t". Documented in the docstring.
5. Tests are flat tests/test_arsenal_media_*.py. Oracles were copied out of the session scratchpad to
   state/arsenal/media-oracles (gitignored, local); tests skip without them.
6. No pip installs tonight: scenedetect / rapidocr / pymediainfo stay optional and the fallbacks must pass tests.
   The League clock's digit templates are built from Daniel's recordings into state/ (Riot font-derived, never committed).
7. The OCR clockmap is in v0 (the spec's named disagreement with studio section 1.8): the code is measured (6 s for 33 min)
   and the 11-pass hand map is a ready oracle.
8. EDITOR HOME: an Edit mode of the existing First Light page (arsenal/web/first-light.*), not a new page. First Light
   already has library roots, drop -> /api/resolve by name+size, Range media serving and probe. Editor JS lives in
   arsenal/web/edit/*.js; routes in arsenal/media/editapi.py behind ONE dispatch line in serve.py. Project document
   arsenal.media.timeline/v0 at state/arsenal/media/edits/<pid>.json with a rev counter: a PUT on a stale rev gets 409,
   so the web UI and the CLI/MCP edit the same file one writer at a time. Playback: one muted <video> + one <audio> per
   demuxed track through WebAudio gain (Chromium here has no audioTracks), resynced past 40 ms drift.
9. The MCP door (16 tools) waits until the primitives are reviewed; then a thin `py -m arsenal.media.door`, not grafted
   onto the knowledge door.

BUILDING NOW (workflow wf_113c63f5-c82): five primitive lanes (catalog+shots, sheet+cut, audio+export, words+avsync,
league clock+events) and the two editor halves, each built -> independently reviewed -> fixed, then one integrator proves
drag-drop -> timeline -> trim -> gain/mute -> render in a real browser.

WHAT I NEED FROM YOU
Blocking objections first (anything that would make a lane's output wrong or a second idiom), then should-fix, then
nits. Especially: (a) is the timeline document the right v0 stand-in for "the board is the master project file", or
should it already be a board projection? (b) is First Light the right editor home under decision 4? (c) anything in
the REUSE/EXTEND sheet you would call a second idiom. Your findings fold into the fix passes and the morning report.
