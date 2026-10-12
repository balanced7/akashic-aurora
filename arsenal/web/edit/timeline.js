// arsenal/web/edit/timeline.js
// The editor's timeline model: pure functions over the project document (arsenal.media.timeline/v0), with no DOM, no
// fetch and no clock, so node --test can hold every rule (tests/arsenal_edit_timeline.test.mjs).
//
// Why a model of its own: the browser, the CLI (py -m arsenal.media edit) and a future MCP tool all edit the same JSON
// file, one writer at a time by revision. The page's share of that contract is to change the document only through
// these functions, so a trim in the browser means exactly what edit.render will cut.
//
// Rules this module holds:
//  - Edits ripple: a trim, delete, insert or move shifts every later clip on V1 by exactly the length it added or
//    removed, so a timeline built here stays end to end from 0 and a gap someone else left (the CLI can place a
//    clip at any time; edit.render plays a gap as black and silence) survives every edit made elsewhere. pack()
//    closes gaps, and only when asked.
//  - A clip's audio entries are linked to it: they share src_in, src_out and at by construction, so they move and
//    trim with the picture. src_track n is the n-th audio stream (ffmpeg a:n); its lane is A(n+1).
//  - Times are float seconds: src_* are file times (seconds from the source file's start, what edit.render's -ss
//    means: arsenal/media/README.md, "The house clock"), at and every view time on the timeline's clock. A <video>
//    element counts on the container's own clock instead; elementTime/sourceTime convert at that edge.
//  - Trims and splits land on the source's frame grid, start_s + k / fps (start_s: the first frame's file time),
//    which is where cut.plan and edit.render cut; cutCost uses cut.plan's own rule (first frame >= start - 1 ms).
//  - Every edit returns a new document (the input is never mutated) and returns the input itself when nothing
//    changed, so the undo stack can skip no-ops by identity.

export const TIMELINE_API = "arsenal.media.timeline/v0";
export const HISTORY_CAP = 100;
export const DEFAULT_FPS = 60;
export const GAIN_MIN_DB = -60;
export const GAIN_MAX_DB = 12;
// ffmpeg a:N = OBS track N+1 (PRIMITIVES-SPEC P6 HOUSE_TRACKS); a stream's own title beats this map.
export const HOUSE_TRACKS = ["Mix", "Voice", "Game", "Comms", "Music", "Piano"];
// Handler names muxers write when a track has no title: not names a person gave the track.
const GENERIC_TITLES = new Set(["", "soundhandler", "sound handler", "obs audio handler", "obs video handler",
  "videohandler", "audio", "track", "stereo", "mono"]);

// ------------------------------------------------------------------ helpers --

const num = (v) => (typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" ? Number(v) : NaN);
const finite = (v, fallback) => (Number.isFinite(num(v)) ? num(v) : fallback);
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const clone = (o) => JSON.parse(JSON.stringify(o));

export function dbToGain(db) {
  return Math.pow(10, db / 20);
}

export function gainToDb(g) {
  return g > 0 ? 20 * Math.log10(g) : -Infinity;
}

/** "m:ss" (or "h:mm:ss"); with digits > 0 the seconds carry that many decimals ("1:05.25"). */
export function formatTime(t, digits = 0) {
  if (!Number.isFinite(t) || t < 0) t = 0;
  const scale = Math.pow(10, digits);
  const total = Math.round(t * scale) / scale; // round once, so 59.999 shows as 1:00, never 0:60
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total - h * 3600 - m * 60;
  let ss = digits > 0 ? s.toFixed(digits) : String(Math.floor(s));
  if (s < 10) ss = "0" + ss;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

/** "h:mm:ss:ff" with frames at fps, always four fields: the transport and monitor timecode. Three fields would read
 *  "1:01:30" for 1 min 1 s frame 30, which is also how formatTime writes 1 h 1 min 30 s. */
export function formatTimecode(t, fps = DEFAULT_FPS) {
  if (!Number.isFinite(t) || t < 0) t = 0;
  const rate = Math.round(fps) || DEFAULT_FPS;
  const f = Math.round(t * fps);
  const whole = Math.floor(f / fps);
  const frames = Math.min(rate - 1, f - Math.round(whole * fps));
  const h = Math.floor(whole / 3600);
  const m = Math.floor((whole % 3600) / 60);
  const s = whole % 60;
  const p2 = (n) => String(n).padStart(2, "0");
  return `${h}:${p2(m)}:${p2(s)}:${p2(frames)}`;
}

/** "60/1", "30000/1001", 59.94 or "59.94" -> frames per second; NaN when unknown. */
export function parseFps(v) {
  if (typeof v === "number") return v > 0 ? v : NaN;
  if (typeof v !== "string") return NaN;
  const m = v.match(/^\s*(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)\s*$/);
  if (m) return Number(m[2]) > 0 ? Number(m[1]) / Number(m[2]) : NaN;
  const n = Number(v);
  return n > 0 ? n : NaN;
}

/**
 * Nearest frame boundary on a source clock at fps, where frame k starts at start + k / fps. start is the video
 * stream's first pts: 0.025 s on two of the four oracle clips, so a grid from 0 lands every trim half a frame off.
 */
export function quantize(t, fps, start = 0) {
  if (!(fps > 0)) return t;
  const s = Number.isFinite(start) ? start : 0;
  return s + Math.round((t - s) * fps) / fps;
}

/**
 * The frame grid of a media's video: {fps, start_s}. start_s is the first frame's file time when the server reported
 * it, else the first keyframe (a stream's first frame is a keyframe), else 0. fps falls back to fallbackFps.
 */
export function frameGrid(media, keyframes = [], fallbackFps = DEFAULT_FPS) {
  const v = media && media.video;
  const fps = v && v.fps > 0 ? v.fps : fallbackFps;
  let start_s = v && Number.isFinite(v.start_s) ? v.start_s : null;
  if (start_s === null && Array.isArray(keyframes)) {
    for (const k of keyframes) if (Number.isFinite(k) && (start_s === null || k < start_s)) start_s = k;
  }
  return { fps, start_s: start_s === null ? 0 : start_s };
}

/**
 * A source file time as its <video> element's currentTime, and back. Every src_* time in the document is a file time;
 * Chrome's currentTime counts on the container's own clock (measured, Chrome 154: a source whose container clock
 * starts at 1.4 s opens at currentTime 1.4, and told 2.0 shows the frame at file time 0.6). media.container_start_s,
 * where file time 0 sits on that clock, is the difference: 0 on the OBS recordings, 1.4 s on an MPEG-TS remux.
 */
export function elementTime(media, srcT) {
  return srcT + containerStart(media);
}

export function sourceTime(media, elT) {
  return elT - containerStart(media);
}

function containerStart(media) {
  const v = media ? num(media.container_start_s) : NaN;
  return Number.isFinite(v) ? v : 0;
}

let idCounter = 0;
/** A short unique id; tests pass their own ids instead. */
export function newId(prefix = "c") {
  idCounter = (idCounter + 1) % 1e6;
  const rnd = Math.floor(Math.random() * 0xffffff).toString(16).padStart(6, "0");
  return `${prefix}${Date.now().toString(36)}${idCounter.toString(36)}${rnd}`;
}

// -------------------------------------------------------------------- media --

function basename(p) {
  if (typeof p !== "string" || !p) return "";
  const parts = p.split(/[\\/]/);
  return parts[parts.length - 1];
}

function cleanTitle(t) {
  if (typeof t !== "string") return null;
  const s = t.trim();
  return GENERIC_TITLES.has(s.toLowerCase()) ? null : s;
}

/**
 * The name a lane shows for source track n: the stream's own title, else its house name, else a label the server
 * gave that is more than "Track n", else the house track map, else "Track n+1".
 */
export function trackLabel(track, n) {
  const given = track && cleanTitle(track.label);
  const own = track ? cleanTitle(track.title) || cleanTitle(track.house_name) || cleanTitle(track.name)
    || (given && !/^track \d+$/i.test(given) ? given : null) : null;
  return own || HOUSE_TRACKS[n] || `Track ${n + 1}`;
}

/**
 * One shape for a media record, whatever produced it: the probe sidecar (arsenal.media.sidecar/v0: duration_s,
 * video.w/h/fps, audio[]) or an older probe (duration, width/height, rate "60/1"). Unknown numbers stay NaN or null
 * rather than being guessed.
 */
export function normalizeMedia(m) {
  if (!m || typeof m !== "object") return null;
  const v = m.video && typeof m.video === "object" ? m.video : null;
  const audioIn = Array.isArray(m.audio) ? m.audio : Array.isArray(m.audio_tracks) ? m.audio_tracks : [];
  const fmt = m.format && typeof m.format === "object" ? m.format : {};
  return {
    id: String(m.id || m.media_id || ""),
    name: m.name || basename(m.path) || String(m.id || ""),
    path: m.path || null,
    size: finite(m.size, null),
    duration: finite(m.duration_s, finite(m.duration, finite(fmt.duration, NaN))),
    container: m.container || fmt.format_name || null,
    // where file time 0 sits on the container's own clock, the clock a <video> element's currentTime counts on
    container_start_s: finite(m.container_start_s, 0),
    kind: m.kind || "unknown",
    recorded_at: m.recorded_at || null,
    encoder: m.encoder || null,
    links: m.links && typeof m.links === "object" ? m.links : {},
    video: v ? {
      codec: v.codec || v.codec_name || null,
      w: finite(v.w, finite(v.width, null)),
      h: finite(v.h, finite(v.height, null)),
      fps: parseFps(v.fps !== undefined ? v.fps : v.rate !== undefined ? v.rate : v.avg_frame_rate),
      vfr: v.vfr === undefined || v.vfr === null ? null : !!v.vfr,
      has_b_frames: finite(v.has_b_frames, null),
      pix_fmt: v.pix_fmt || null,
      keyint_s: finite(v.keyint_s, null),
      keyframes_n: finite(v.keyframes_n, null),
      // the first frame's file time: frame k sits at start_s + k / fps in the file (null when not reported)
      start_s: finite(v.start_s, finite(v.start_time, null)),
    } : null,
    audio: audioIn.map((a, i) => ({
      n: i,
      index: finite(a.index, i),
      codec: a.codec || a.codec_name || null,
      channels: finite(a.channels, null),
      sample_rate: finite(a.sample_rate, null),
      title: cleanTitle(a.title),
      house_name: a.house_name || null,
      label: trackLabel(a, i),
      // where the demuxed file's t = 0 sits in the source file (a track that starts late plays from 0 in its file)
      start_s: finite(a.start_s, 0),
    })),
  };
}

// ---------------------------------------------------------------- document --

export function emptyProject({ id = "", name = "Untitled edit", fps = DEFAULT_FPS, width = 1920, height = 1080 } = {}) {
  return {
    api: TIMELINE_API, id, name, rev: 0, created_at: null, updated_at: null,
    settings: { fps, width, height },
    lanes: { video: [{ id: "V1" }], audio: [] },
    clips: [], markers: [], board: null,
  };
}

export function docFps(doc) {
  const f = doc && doc.settings ? num(doc.settings.fps) : NaN;
  return f > 0 ? f : DEFAULT_FPS;
}

export const clipDuration = (c) => Math.max(0, c.src_out - c.src_in);
export const clipEnd = (c) => c.at + clipDuration(c);

/** The video lane's clips in timeline order (by at, ties by their place in the document). */
export function videoClips(doc) {
  return doc.clips
    .map((c, i) => [c, i])
    .filter(([c]) => (c.lane || "V1") === "V1")
    .sort((a, b) => a[0].at - b[0].at || a[1] - b[1])
    .map(([c]) => c);
}

export function totalDuration(doc) {
  let end = 0;
  for (const c of doc.clips) end = Math.max(end, clipEnd(c));
  return end;
}

const round9 = (t) => Math.round(t * 1e9) / 1e9;
const EPS_T = 1e-6;

/** Keeps the document's clip list in timeline order (V1 by at), which is the order edit.render and the CLI read. */
function sortClips(doc) {
  const rank = new Map(videoClips(doc).map((c, i) => [c.id, i]));
  doc.clips.sort((a, b) => (rank.has(a.id) ? rank.get(a.id) : 1e9) - (rank.has(b.id) ? rank.get(b.id) : 1e9));
  return doc;
}

/** Moves every V1 clip that starts at or after `from` by delta seconds (the ripple), except the clip `except`. */
function ripple(doc, from, delta, except = null) {
  if (Math.abs(delta) < 1e-12) return;
  for (const c of doc.clips) {
    if (c.id !== except && (c.lane || "V1") === "V1" && c.at >= from - EPS_T) c.at = round9(Math.max(0, c.at + delta));
  }
}

/** Closes every gap: the V1 clips end to end from 0 in their current order. Returns the input when already packed. */
export function pack(doc) {
  const order = videoClips(doc);
  let t = 0, changed = false;
  const at = new Map();
  for (const c of order) {
    const want = round9(t);
    if (Math.abs(c.at - want) > 1e-9) changed = true;
    at.set(c.id, want);
    t = want + clipDuration(c);
  }
  const sameOrder = order.every((c, i) => doc.clips[i] === c);
  if (!changed && sameOrder) return doc;
  const out = clone(doc);
  const byId = new Map(out.clips.map((c) => [c.id, c]));
  out.clips = order.map((c) => byId.get(c.id)).concat(out.clips.filter((c) => (c.lane || "V1") !== "V1"));
  for (const c of out.clips) if (at.has(c.id)) c.at = at.get(c.id);
  return out;
}

/** The gaps on V1 as [t0, t1] pairs (before the first clip, between clips); [] for a timeline built end to end. */
export function gaps(doc) {
  const out = [];
  let t = 0;
  for (const c of videoClips(doc)) {
    if (c.at > t + 1e-4) out.push([t, c.at]);
    t = Math.max(t, clipEnd(c));
  }
  return out;
}

/** The lane id for source audio track n. */
export const laneForTrack = (n) => `A${n + 1}`;

/** Adds the audio lanes a media's tracks need (A1..An), labelled from its track names; keeps every existing lane. */
export function ensureAudioLanes(doc, media) {
  const m = normalizeMedia(media); // idempotent: a raw server record and a normalized one read the same
  const want = m ? m.audio.length : 0;
  const have = new Map(doc.lanes.audio.map((l) => [l.id, l]));
  let changed = false;
  const lanes = doc.lanes.audio.map((l) => ({ ...l }));
  for (let n = 0; n < want; n++) {
    const id = laneForTrack(n);
    const label = m.audio[n].label || trackLabel(m.audio[n], n);
    const lane = have.get(id);
    if (!lane) {
      lanes.push({ id, label, gain_db: 0, mute: false, solo: false });
      changed = true;
    } else if (!lane.label) {
      lanes.find((l) => l.id === id).label = label;
      changed = true;
    }
  }
  if (!changed) return doc;
  lanes.sort((a, b) => laneNumber(a.id) - laneNumber(b.id));
  const out = clone(doc);
  out.lanes.audio = lanes;
  return out;
}

const laneNumber = (id) => Number(String(id).replace(/^\D+/, "")) || 0;

/** A clip of a whole media (or of [src_in, src_out]), with one linked audio entry per source track. */
export function makeClip(media, { id = newId(), src_in = 0, src_out = null, at = 0 } = {}) {
  const m = normalizeMedia(media);
  if (!m) throw new Error("makeClip needs a media record");
  const dur = Number.isFinite(m.duration) ? m.duration : 0;
  const out = src_out === null ? dur : src_out;
  return {
    id, media_id: m.id, lane: "V1", src_in, src_out: out, at,
    audio: m.audio.map((a, n) => ({ src_track: n, lane: laneForTrack(n), gain_db: 0, mute: false })),
  };
}

/**
 * Inserts a whole-media clip (or opts.src_in..src_out) at position index of the video lane (default: the end): it takes
 * the place where clip `index` starts and every clip from there on moves later by its length.
 */
export function insertClip(doc, media, index = Infinity, opts = {}) {
  const m = normalizeMedia(media);
  if (!m || !m.id) throw new Error("insertClip needs a media record with an id");
  if (!(m.duration > 0)) throw new Error(`media ${m.id} has no known duration`);
  let out = ensureAudioLanes(doc, m);
  out = out === doc ? clone(doc) : out;
  const order = videoClips(out);
  const i = clamp(Math.round(Number.isFinite(index) ? index : order.length), 0, order.length);
  const clip = makeClip(m, opts);
  clip.at = i < order.length ? order[i].at : order.length ? round9(clipEnd(order[order.length - 1])) : 0;
  ripple(out, clip.at, clipDuration(clip));
  out.clips.push(clip);
  return { doc: sortClips(out), clip: clip.id };
}

export const appendClip = (doc, media, opts = {}) => insertClip(doc, media, Infinity, opts);

/**
 * Moves a clip to position index of the video lane (index counts the order without the clip): it leaves its place
 * (later clips move up by its length) and takes the place of clip `index` (which moves on by the same length).
 */
export function moveClip(doc, clipId, index) {
  const order = videoClips(doc);
  const from = order.findIndex((c) => c.id === clipId);
  if (from < 0) return doc;
  const rest = order.filter((c) => c.id !== clipId);
  const to = clamp(Math.round(index), 0, rest.length);
  if (to === from) return doc;
  const out = clone(doc);
  const mc = out.clips.find((c) => c.id === clipId);
  const dur = clipDuration(mc);
  ripple(out, clipEnd(mc), -dur, clipId);
  const restOut = videoClips(out).filter((c) => c.id !== clipId);
  mc.at = to < restOut.length ? restOut[to].at : restOut.length ? round9(clipEnd(restOut[restOut.length - 1])) : 0;
  ripple(out, mc.at, dur, clipId);
  return sortClips(out);
}

/**
 * Trims one edge of a clip to source time srcT, clamped to [0, mediaDuration] and to at least minDur, on the
 * source's frame grid (start_s + k / fps) when fps is known; an in-edge before the first frame becomes 0, the file's
 * start. The clip keeps its start on the timeline; every later clip moves by the length gained or lost (the ripple).
 * edge is "in" or "out".
 */
export function trimClip(doc, clipId, edge, srcT, { mediaDuration = Infinity, fps = null, start_s = 0, minDur = null } = {}) {
  const c = doc.clips.find((x) => x.id === clipId);
  if (!c || !Number.isFinite(srcT)) return doc;
  const f = fps > 0 ? fps : docFps(doc);
  const min = minDur !== null ? minDur : 1 / f;
  const s0 = Number.isFinite(start_s) ? start_s : 0;
  let t = quantize(srcT, f, s0);
  const end = Number.isFinite(mediaDuration) ? mediaDuration : Infinity;
  if (edge === "in") {
    if (t < s0 - 1e-9) t = 0;
    t = clamp(t, 0, c.src_out - min);
    if (Math.abs(t - c.src_in) < 1e-9) return doc;
  } else if (edge === "out") {
    t = clamp(t, c.src_in + min, end);
    if (Math.abs(t - c.src_out) < 1e-9) return doc;
  } else {
    throw new Error(`trim edge must be "in" or "out", not ${edge}`);
  }
  const out = clone(doc);
  const oc = out.clips.find((x) => x.id === clipId);
  const oldEnd = clipEnd(oc), oldDur = clipDuration(oc);
  if (edge === "in") oc.src_in = t; else oc.src_out = t;
  ripple(out, oldEnd, clipDuration(oc) - oldDur, clipId);
  return sortClips(out);
}

/** The clip under timeline time t, with t on its source clock; the timeline's very end maps to the last clip. */
export function clipAtTime(doc, t) {
  const order = videoClips(doc);
  for (let i = 0; i < order.length; i++) {
    const c = order[i];
    // touching clips meet at the next one's `at`: at is rounded to 1e-9 s and src_in/src_out are not, so the computed
    // end of the previous clip can overshoot it by a nanosecond, and that instant must belong to the next clip (else
    // playback crossing the cut kept finding the old clip and stalled there)
    const next = order[i + 1];
    const end = next && next.at < clipEnd(c) ? next.at : clipEnd(c);
    if (t >= c.at && t < end) return { clip: c, index: i, srcT: c.src_in + (t - c.at) };
  }
  const last = order[order.length - 1];
  if (last && Math.abs(t - clipEnd(last)) < 1e-6) return { clip: last, index: order.length - 1, srcT: last.src_out };
  return null;
}

/**
 * Splits the clip under timeline time t into two at the nearest source frame (start_s + k / fps); the right half
 * gets newId. Does nothing within one frame of either edge.
 */
export function splitClip(doc, t, { newId: rightId = newId(), fps = null, start_s = 0 } = {}) {
  const hit = clipAtTime(doc, t);
  if (!hit) return doc;
  const c = hit.clip;
  const f = fps > 0 ? fps : docFps(doc);
  const s = quantize(hit.srcT, f, start_s);
  if (s - c.src_in < 1 / f - 1e-9 || c.src_out - s < 1 / f - 1e-9) return doc;
  const out = clone(doc);
  const i = out.clips.findIndex((x) => x.id === c.id);
  const left = out.clips[i];
  const right = clone(left);
  right.id = rightId;
  right.src_in = s;
  right.at = left.at + (s - left.src_in);
  left.src_out = s;
  out.clips.splice(i + 1, 0, right);
  return sortClips(out);
}

/** Removes a clip; every later clip moves up by its length, so the hole closes (and no other gap does). */
export function deleteClip(doc, clipId) {
  const c = doc.clips.find((x) => x.id === clipId);
  if (!c) return doc;
  const out = clone(doc);
  out.clips = out.clips.filter((x) => x.id !== clipId);
  ripple(out, clipEnd(c), -clipDuration(c));
  return sortClips(out);
}

/** Where a clip dropped at timeline time t goes: before the first clip whose middle lies after t. */
export function insertionIndex(doc, t) {
  const order = videoClips(doc);
  let i = 0;
  while (i < order.length && order[i].at + clipDuration(order[i]) / 2 <= t) i++;
  return i;
}

/**
 * The edit a finished pointer gesture makes, computed on doc as it is at release. A save landing mid-drag swaps the
 * document (a new rev), and a key pressed mid-drag can edit it; an edit computed from the document at the press
 * would put back whatever changed in between. gesture is {kind: "trim", id, edge, srcT, mediaDuration, fps, start_s}
 * or {kind: "move", id, t} (t: the timeline time under the pointer). Returns doc itself when nothing changes.
 */
export function applyGesture(doc, gesture) {
  const g = gesture || {};
  if (g.kind === "trim") {
    return trimClip(doc, g.id, g.edge, g.srcT, { mediaDuration: g.mediaDuration, fps: g.fps, start_s: g.start_s });
  }
  if (g.kind === "move" && Number.isFinite(g.t)) {
    const from = videoClips(doc).findIndex((c) => c.id === g.id);
    if (from < 0) return doc;
    const i = insertionIndex(doc, g.t);
    return moveClip(doc, g.id, i > from ? i - 1 : i);
  }
  return doc;
}

/** Changes one audio lane (label, gain_db within -60..+12, mute, solo). */
export function setLane(doc, laneId, patch) {
  const lane = doc.lanes.audio.find((l) => l.id === laneId);
  if (!lane) return doc;
  const next = { ...lane };
  if ("label" in patch) next.label = String(patch.label);
  if ("gain_db" in patch && Number.isFinite(num(patch.gain_db))) next.gain_db = clamp(num(patch.gain_db), GAIN_MIN_DB, GAIN_MAX_DB);
  if ("mute" in patch) next.mute = !!patch.mute;
  if ("solo" in patch) next.solo = !!patch.solo;
  if (JSON.stringify(next) === JSON.stringify(lane)) return doc;
  const out = clone(doc);
  out.lanes.audio = out.lanes.audio.map((l) => (l.id === laneId ? next : l));
  return out;
}

/** Changes one linked audio entry of a clip (gain_db, mute). */
export function setClipAudio(doc, clipId, srcTrack, patch) {
  const c = doc.clips.find((x) => x.id === clipId);
  const a = c && c.audio.find((x) => x.src_track === srcTrack);
  if (!a) return doc;
  const next = { ...a };
  if ("gain_db" in patch && Number.isFinite(num(patch.gain_db))) next.gain_db = clamp(num(patch.gain_db), GAIN_MIN_DB, GAIN_MAX_DB);
  if ("mute" in patch) next.mute = !!patch.mute;
  if (JSON.stringify(next) === JSON.stringify(a)) return doc;
  const out = clone(doc);
  const oc = out.clips.find((x) => x.id === clipId);
  oc.audio = oc.audio.map((x) => (x.src_track === srcTrack ? next : x));
  return out;
}

export function rename(doc, name) {
  const s = String(name || "").trim();
  if (!s || s === doc.name) return doc;
  return { ...clone(doc), name: s };
}

/** True when the lane is heard: not muted, and either no lane is soloed or this one is. */
export function laneAudible(doc, laneId) {
  const lane = doc.lanes.audio.find((l) => l.id === laneId);
  if (!lane || lane.mute) return false;
  const anySolo = doc.lanes.audio.some((l) => l.solo);
  return !anySolo || !!lane.solo;
}

/**
 * The linear gain one linked audio entry plays at: lane gain + clip-track gain in dB, zero when the lane is muted,
 * not soloed while another lane is, or the entry itself is muted. edit.render applies the same rule.
 */
export function effectiveGain(doc, entry) {
  if (!entry || entry.mute || !laneAudible(doc, entry.lane)) return 0;
  const lane = doc.lanes.audio.find((l) => l.id === entry.lane);
  return dbToGain(finite(lane.gain_db, 0) + finite(entry.gain_db, 0));
}

/** Problems that would make the server or the renderer refuse the document; empty when it is sound. */
export function validate(doc) {
  const problems = [];
  if (!doc || doc.api !== TIMELINE_API) problems.push(`api must be ${TIMELINE_API}`);
  if (!doc || !Array.isArray(doc.clips)) return problems.concat("clips must be a list");
  const ids = new Set();
  const lanes = new Set((doc.lanes && doc.lanes.audio || []).map((l) => l.id));
  for (const c of doc.clips) {
    if (!c.id || ids.has(c.id)) problems.push(`clip id ${c.id} is missing or repeated`);
    ids.add(c.id);
    if (!(c.src_out > c.src_in) || c.src_in < 0) problems.push(`clip ${c.id}: needs 0 <= src_in < src_out`);
    if (!(c.at >= 0)) problems.push(`clip ${c.id}: at must be >= 0`);
    for (const a of c.audio || []) {
      if (!lanes.has(a.lane)) problems.push(`clip ${c.id}: audio lane ${a.lane} does not exist`);
    }
  }
  const order = videoClips(doc);
  for (let i = 1; i < order.length; i++) {
    if (order[i].at < clipEnd(order[i - 1]) - 1e-6) problems.push(`clips ${order[i - 1].id} and ${order[i].id} overlap`);
  }
  return problems;
}

// ---------------------------------------------------------------- layout ----

/** The timeline's rows top to bottom: the ruler, V1, then one row per audio lane. */
export function layoutRows(doc, { ruler = 24, video = 56, audio = 44 } = {}) {
  const rows = [{ id: "ruler", kind: "ruler", label: "", y: 0, h: ruler }];
  let y = ruler;
  for (const v of doc.lanes.video) { rows.push({ id: v.id, kind: "video", label: v.id, y, h: video }); y += video; }
  for (const a of doc.lanes.audio) {
    rows.push({ id: a.id, kind: "audio", label: `${a.id} ${a.label || ""}`.trim(), y, h: audio });
    y += audio;
  }
  return { rows, height: y };
}

/** The row at y (content pixels), or null. */
export function rowAt(layout, y) {
  return layout.rows.find((r) => y >= r.y && y < r.y + r.h) || null;
}

// --------------------------------------------------------------- snapping ---

/**
 * Snap targets for dragging one edge of clip, in timeline seconds: the clip's media's shot cuts and keyframes
 * mapped through the clip's current placement (at, src_in), and the playhead. shots/keyframes are source seconds.
 */
export function trimSnapTargets(clip, { shots = [], keyframes = [], playhead = null } = {}) {
  const out = [];
  const map = (s) => clip.at + (s - clip.src_in);
  for (const s of shots) {
    const t = typeof s === "number" ? s : s && s.t;
    if (Number.isFinite(t)) out.push({ t: map(t), src: t, kind: "shot" });
  }
  for (const k of keyframes) if (Number.isFinite(k)) out.push({ t: map(k), src: k, kind: "keyframe" });
  if (Number.isFinite(playhead)) out.push({ t: playhead, src: clip.src_in + (playhead - clip.at), kind: "playhead" });
  return out;
}

/** The nearest target within threshold seconds of t ({t, kind}); otherwise t itself with kind null. */
export function snap(t, targets, threshold) {
  let best = null, bestD = threshold;
  for (const g of targets) {
    const d = Math.abs(g.t - t);
    if (d <= bestD && (best === null || d < bestD || rank(g.kind) < rank(best.kind))) { best = g; bestD = d; }
  }
  return best ? { t: best.t, kind: best.kind } : { t, kind: null };
}

// On a tie the playhead wins (it is where the person is looking), then a shot cut, then a keyframe.
const rank = (kind) => (kind === "playhead" ? 0 : kind === "shot" ? 1 : 2);

// cut.plan starts a cut on the first frame whose pts >= start - 1 ms (frames.at_times' convention)
export const CUT_START_SLACK_S = 1e-3;

/**
 * What a cut starting at source time start costs, from the media's keyframe list, by cut.plan's own rule: the cut
 * starts on the first frame at or after start - 1 ms, and is lossless when that frame is a keyframe; else a smart cut
 * re-encodes from start to the next keyframe. null when the keyframes are unknown.
 */
export function cutCost(keyframes, start, fps = DEFAULT_FPS) {
  if (!Array.isArray(keyframes) || !keyframes.length || !Number.isFinite(start)) return null;
  const frame = 1 / (fps > 0 ? fps : DEFAULT_FPS);
  const from = start - CUT_START_SLACK_S;
  let next = null;
  for (const k of keyframes) {
    // 1e-6: keyframe lists are printed to 6 decimals
    if (Number.isFinite(k) && k >= from - 1e-6 && (next === null || k < next)) next = k;
  }
  if (next !== null && next - from < frame - 1e-6) return { lossless: true, head_s: 0, keyframe: next };
  return { lossless: false, head_s: next === null ? null : Math.max(0, next - start), keyframe: next };
}

/** The trim hint's words, from cut.plan's answer or cutCost's: "lossless" or "re-encodes the first 1.4 s". */
export function costHint(plan) {
  if (!plan) return "";
  if (plan.lossless === true || plan.mode_suggested === "copy") return "lossless";
  const head = plan.head_reencode_s !== undefined ? plan.head_reencode_s : plan.head_s;
  if (Number.isFinite(head)) return `re-encodes the first ${head.toFixed(1)} s`;
  if (plan.mode_suggested === "exact") return "re-encodes the whole clip";
  return "re-encodes the head";
}

// ------------------------------------------------------------------ view ----

export const ZOOM_MAX_PPS = 2400; // 40 px a frame at 60 fps
export const MAX_CONTENT_PX = 3e7; // under Chromium's layout limit (2^31 / 64 px)

/** Zoom limits for a timeline of duration seconds shown in widthPx. */
export function zoomLimits(duration, widthPx) {
  const d = Math.max(duration, 1);
  const min = Math.max(1e-3, (Math.max(widthPx, 1) * 0.9) / d / 4);
  const max = Math.max(min, Math.min(ZOOM_MAX_PPS, MAX_CONTENT_PX / d));
  return { min, max };
}

/** pxPerSec that shows the whole timeline in widthPx (a little air at the end). */
export function fitPps(duration, widthPx) {
  if (!(duration > 0)) return 50;
  return Math.max(1e-3, (Math.max(widthPx, 1) * 0.94) / duration);
}

/**
 * Zoom by factor around anchorX (pixels from the viewport's left edge): the time under the anchor stays under it.
 * view = {pxPerSec, scrollLeft}; returns the new view with scrollLeft >= 0.
 */
export function zoomAround(view, factor, anchorX, limits = { min: 1e-3, max: ZOOM_MAX_PPS }) {
  const t = (view.scrollLeft + anchorX) / view.pxPerSec;
  const pps = clamp(view.pxPerSec * factor, limits.min, limits.max);
  return { pxPerSec: pps, scrollLeft: Math.max(0, t * pps - anchorX) };
}

const TICK_STEPS = [1 / 60, 1 / 30, 0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600];

/** Ruler ticks for [t0, t1] at pxPerSec: labelled majors at least minLabelPx apart, minors between. */
export function rulerTicks(t0, t1, pxPerSec, minLabelPx = 84) {
  const step = TICK_STEPS.find((s) => s * pxPerSec >= minLabelPx) || 3600 * Math.ceil(minLabelPx / pxPerSec / 3600);
  const sub = step >= 60 ? (step % 300 === 0 ? 5 : step === 120 ? 4 : 6) : step >= 1 ? (step === 2 || step === 15 ? 3 : 5) : 5;
  const minor = step / sub;
  const digits = step >= 1 ? 0 : step >= 0.1 ? 1 : 2;
  const major = [], minors = [];
  const first = Math.max(0, Math.floor(t0 / step) * step);
  for (let i = 0, t = first; t <= t1 + 1e-9 && i < 10000; i++, t = first + i * step) {
    major.push({ t, label: formatTime(t, digits) });
    for (let k = 1; k < sub; k++) {
      const m = t + k * minor;
      if (m >= t0 && m <= t1) minors.push(m);
    }
  }
  return { step, major, minor: minors };
}

// ----------------------------------------------------------------- peaks ----

/**
 * Peaks as the page keeps them: Float32Array of min,max pairs, each pair covering spp samples at sample_rate; start_s
 * is the source time of the first pair (0 unless the track starts late).
 */
export function toPeaks(json) {
  if (!json || !(json.sample_rate > 0) || !(json.spp > 0) || !json.data) return null;
  const data = json.data instanceof Float32Array ? json.data : Float32Array.from(json.data);
  return { sample_rate: json.sample_rate, spp: json.spp, data, bins: Math.floor(data.length / 2), start_s: finite(json.start_s, 0) };
}

/**
 * Per-column [min, max] of the waveform over source seconds [s0, s1] split into columns: the visible range only, so
 * the cost follows the screen, not the file. Columns past the data hold NaN.
 */
export function peaksColumns(peaks, s0, s1, columns) {
  const out = new Float32Array(Math.max(0, columns) * 2).fill(NaN);
  if (!peaks || columns <= 0 || !(s1 > s0)) return out;
  const lead = peaks.start_s || 0;
  s0 -= lead;
  s1 -= lead;
  const secPerBin = peaks.spp / peaks.sample_rate;
  const span = (s1 - s0) / columns;
  const d = peaks.data;
  for (let c = 0; c < columns; c++) {
    const a = s0 + c * span;
    let b0 = Math.floor(a / secPerBin);
    let b1 = Math.max(b0 + 1, Math.ceil((a + span) / secPerBin));
    b0 = Math.max(0, b0);
    b1 = Math.min(peaks.bins, b1);
    if (b0 >= b1) continue;
    let lo = Infinity, hi = -Infinity;
    for (let b = b0; b < b1; b++) {
      const mn = d[2 * b], mx = d[2 * b + 1];
      if (mn < lo) lo = mn;
      if (mx > hi) hi = mx;
    }
    out[2 * c] = lo;
    out[2 * c + 1] = hi;
  }
  return out;
}

export const WAVE_FLOOR_DB = -54;

/**
 * Where a waveform sample lands in its lane, -1..1, on a dB scale: game and piano recordings sit around -35 dBFS, so a
 * linear wave would be a flat line; floorDb maps to 0 and 0 dBFS to the lane edge. gain (linear) is the mixer's
 * effective gain, so a fader move shows in the lane.
 */
export function waveHeight(v, gain = 1, floorDb = WAVE_FLOOR_DB) {
  const a = Math.abs(v) * gain;
  if (!(a > 0)) return 0;
  const f = (20 * Math.log10(a) - floorDb) / -floorDb;
  return Math.sign(v) * Math.min(1, Math.max(0, f));
}

// --------------------------------------------------------------- history ----

/** A local undo stack of whole documents (they are small: 200 clips is about 60 KB). */
export function createHistory(doc, cap = HISTORY_CAP) {
  return { past: [], present: doc, future: [], cap };
}

/** Records doc as the new present; a no-op edit (the same object) records nothing. */
export function commit(h, doc) {
  if (doc === h.present) return h;
  const past = h.past.concat([h.present]);
  return { past: past.length > h.cap ? past.slice(past.length - h.cap) : past, present: doc, future: [], cap: h.cap };
}

export function undo(h) {
  if (!h.past.length) return h;
  return { past: h.past.slice(0, -1), present: h.past[h.past.length - 1], future: [h.present].concat(h.future), cap: h.cap };
}

export function redo(h) {
  if (!h.future.length) return h;
  return { past: h.past.concat([h.present]), present: h.future[0], future: h.future.slice(1), cap: h.cap };
}

export const canUndo = (h) => h.past.length > 0;
export const canRedo = (h) => h.future.length > 0;

/** Swaps the present without an undo step: a save's new rev, or the server's copy after a 409. */
export function replacePresent(h, doc) {
  return { ...h, present: doc };
}
