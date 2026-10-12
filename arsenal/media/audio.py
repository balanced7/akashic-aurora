"""arsenal.media.audio -- every audio track of a recording: listed, measured, split out, mixed and checked.

Why it exists. Chromium here has no HTMLMediaElement.audioTracks (measured), so the editor plays ONE FILE PER TRACK and
mixes in WebAudio; ffmpeg's default stream selection silently keeps one audio track unless told `-map`; loudness was
measured by hand in 17 transcripts and two-pass loudnorm was built by hand 6 times. This module is the one copy.

    tracks(src)                              -> [{index, stream_index, codec, channels, sample_rate, title, house_name}]
    loudness(src, tracks="all", span=None)   -> I (LUFS), LRA, TP (dBTP) per track, ONE decode pass for all tracks
    silences(src, track=0)                   -> [[t0, t1], ...] on the source clock
    demux(src, out_dir, codec="copy")        -> one browser-playable file per track (Opus -> .ogg, AAC -> .m4a)
    split_channels(src, track, out_dir)      -> one mono WAV per channel
    mix(src, out, gains_db=, mute=, spans=)  -> one stereo file: per-track dB gains and mutes, or several clips on a
                                                timeline (the editor's render audio)
    loudnorm_2pass(src, out, target_i=-14)   -> measured two-pass loudnorm, verified by reading the output back
    qc(path, expect=...)                     -> loudness, true peak, black/freeze/silence, stream inventory, problems

Track names: a stream's own title wins; a generic name an encoder wrote ("simple_opus_recording0", "SoundHandler")
does not count as a title, and then the studio's 6-track OBS map names it (HOUSE_TRACKS: ffmpeg a:N = OBS track N+1).
Every track is addressed by its audio index N (ffmpeg's a:N); `stream_index` is the container's own index.

Times at the edges are float seconds on the source's clock. An MKV/WebM source keeps 1 ms timestamps, so a span on
one starts on that grid (a start at 1.23456 s began 21 samples late, measured); spans on an MP4 (1/48000 timebase)
are sample-exact (measured: three spans placed on a timeline match the source within 1 LSB of the float path).
A span must lie inside its file (check_span): one that starts after the audio ends or ends more than 1 ms past the
file is refused, since ebur128 reads no frames as I -70 LUFS / TP 0.0 dBTP. A span whose track ends early (audio
4 s in a 6 s file) is padded with silence to its full length, so later spans land where they were asked to.

Loudness targets fail soft only where nothing can be done: digital silence (loudnorm pass 1 prints -inf, which pass 2
rejects) renders plainly with a note; a read-back still off by more than 0.5 LU after the corrective render (sparse
content in dynamic mode: one render lands 3.4 LU loud, measured) comes back ok False with the miss in problems.

Measured 2026-10-12 on this machine (house ffmpeg N-124319); the synthetic oracles are in the tests:
  - 997 Hz sines at -20/-26/-30 dBFS on both channels read back at exactly -20.0/-26.0/-30.0 LUFS (FLAC and Opus);
  - a mixdown with gains {0: 0, 1: -6} and track 2 muted reads -18.1 LUFS against the coherent-sum prediction -18.05;
  - demux copy of Opus into Ogg decodes bit-identical to the source track and ends on the nominal length
    (WebM/MKV decode 648 samples longer); Chromium plays the .ogg/.m4a/.flac/.wav outputs, and seeks a 33-min Ogg
    to 1000 s in 51 ms when the server answers HTTP Range requests (without Range: duration Infinity, no seeking);
  - loudnorm_2pass: pink noise at -48.6 LUFS -> -14.1 (AAC, TP -3.5); modulated tones -> -14.0 after one corrective
    re-render (loudnorm's pass-1 meter read them 0.33 LU apart from ebur128); a real 10 s League clip at -41.2 LUFS
    -> -14.1 / -1.6 dBTP after the re-render fixed a -1.4 dBTP AAC overshoot;
  - 2026-10-11 17-51-11.mp4 (33 min, one Opus track): loudness 5.0 s, demux copy 0.25 s (warm file cache).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from . import ff, receipt

#: The studio's OBS track map (studio Part 3.3): ffmpeg a:N is OBS track N+1. A stream's own title beats it.
HOUSE_TRACKS = {0: "Mix", 1: "Voice", 2: "Game", 3: "Comms", 4: "Music", 5: "Piano"}

#: Names encoders and muxers write when nobody named the track; they are not titles.
_GENERIC_TITLE = re.compile(
    r"(?i)^\s*(|simple_\w*recording\d*|adv_\w*|soundhandler|videohandler|(obs |core media |gpac iso |apple )?"
    r"(sound|audio)( media)? handler|(sound|audio) ?track ?\d*|track ?\d+|stereo|mono)\s*$")

#: codec -> (extension, extra muxer args) for a stream copy Chromium's <audio> element and decodeAudioData play.
#: Opus goes to Ogg, not WebM: Ogg's granule position trims the encoder's end padding, so the file decodes to exactly
#: the source's nominal length (WebM and MKV decode 648 samples longer, measured).
_COPY_CONTAINER = {
    "opus": (".ogg", []),
    "aac": (".m4a", ["-movflags", "+faststart"]),
    "mp3": (".mp3", []),
    "flac": (".flac", []),
    "vorbis": (".ogg", []),
    "pcm_s16le": (".wav", []),
    "pcm_s24le": (".wav", []),
    "pcm_f32le": (".wav", []),
    "pcm_u8": (".wav", []),
}

#: codec name -> (encoder args, default extension) for files this module writes.
CODECS = {
    "aac": (["-c:a", "aac", "-b:a", "256k"], ".m4a"),
    "opus": (["-c:a", "libopus", "-b:a", "160k"], ".ogg"),
    "flac": (["-c:a", "flac"], ".flac"),
    "wav": (["-c:a", "pcm_s16le"], ".wav"),
    "wav24": (["-c:a", "pcm_s24le"], ".wav"),
}
_EXT_CODEC = {".m4a": "aac", ".mp4": "aac", ".mov": "aac", ".aac": "aac", ".ogg": "opus", ".opus": "opus",
              ".webm": "opus", ".flac": "flac", ".wav": "wav", ".mka": "flac", ".mkv": "flac"}

TrackSpec = Union[str, int, Sequence[Union[int, str]], None]
Span = Optional[Tuple[float, float]]


# =================================================================================================
# tracks
# =================================================================================================

def track_name(a_index: int, tags: Optional[dict]) -> Tuple[Optional[str], str, str]:
    """(title, house_name, name_source) for audio track a_index: the stream's own title when it is a real name,
    else the house map, else 'Track N+1'. The catalog's sidecar uses the same rule."""
    tags = {str(k).lower(): v for k, v in (tags or {}).items()}
    for key in ("title", "name", "handler_name"):
        value = str(tags.get(key) or "").strip()
        if value and not _GENERIC_TITLE.match(value):
            return value, value, "title"
    return None, HOUSE_TRACKS.get(a_index, f"Track {a_index + 1}"), "map"


def _duration_tag(tags: dict) -> Optional[float]:
    raw = next((v for k, v in (tags or {}).items() if k.upper() == "DURATION"), None)
    if not raw:
        return None
    try:
        h, m, s = str(raw).split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except ValueError:
        return None


def _stream_tags(j: dict, s: dict) -> dict:
    """A stream's tags; in an audio-only file of one stream (a demuxed track) the file's own title counts too, since
    FLAC and M4A keep a title only at the file level."""
    tags = dict(s.get("tags") or {})
    fmt = j.get("format") or {}
    if (int(fmt.get("nb_streams") or 0) == 1 and s.get("codec_type") == "audio"
            and not any(k.lower() in ("title", "name") for k in tags)):
        title = next((v for k, v in (fmt.get("tags") or {}).items() if k.lower() == "title"), None)
        if title:
            tags["title"] = title
    return tags


def tracks(src) -> List[dict]:
    """Every audio track of src, in a:N order. A cheap fact lookup (one ffprobe call), not a receipt. start_s is
    where the track starts in the file (README, "The house clock": its start_time minus the format start_time)."""
    j = ff.probe_json(src, entries=("-show_streams", "-show_format"), extra=("-select_streams", "a"))
    fmt_dur = float((j.get("format") or {}).get("duration") or 0.0)
    f0 = float((j.get("format") or {}).get("start_time") or 0.0)
    out = []
    for n, s in enumerate(j.get("streams") or []):
        tags = _stream_tags(j, s)
        title, house, source = track_name(n, tags)
        dur = s.get("duration")
        dur = float(dur) if dur not in (None, "N/A") else (_duration_tag(tags) or fmt_dur)
        out.append({"index": n, "stream_index": int(s["index"]), "codec": s.get("codec_name"),
                    "channels": int(s.get("channels") or 0), "layout": s.get("channel_layout"),
                    "sample_rate": int(s.get("sample_rate") or 0), "title": title, "house_name": house,
                    "name_source": source, "start_s": round(float(s.get("start_time") or f0) - f0, 6),
                    "duration_s": dur,
                    "language": tags.get("language"), "file_duration_s": fmt_dur})
    return out


_list = tracks          # for functions whose `tracks` parameter shadows the lister


def _describe(trs: List[dict]) -> str:
    return ", ".join(f"{t['index']} {t['house_name']}" for t in trs) or "none"


def _resolve_one(x, trs: List[dict], src) -> int:
    if isinstance(x, str) and not x.strip().lstrip("-").isdigit():
        hits = [t["index"] for t in trs if t["house_name"].lower() == x.strip().lower()]
        if not hits:
            raise ff.MediaError(f"no audio track named {x!r} in {Path(str(src)).name} (it has {_describe(trs)})")
        return hits[0]
    i = int(x)
    if not 0 <= i < len(trs):
        raise ff.MediaError(f"audio track {i} is not in {Path(str(src)).name} (it has {len(trs)}: {_describe(trs)})")
    return i


def pick(spec: TrackSpec, trs: List[dict], src="") -> List[int]:
    """'all' | None | 2 | '0,2' | 'Voice,Game' | [0, 'Game'] -> audio indices, refusing a track the file lacks."""
    if not trs:
        raise ff.MediaError(f"{Path(str(src)).name or 'source'} has no audio track")
    if spec is None or (isinstance(spec, str) and spec.strip().lower() in ("all", "")):
        return [t["index"] for t in trs]
    if isinstance(spec, str):
        spec = [p for p in spec.split(",") if p.strip()]
    elif isinstance(spec, int):
        spec = [spec]
    out = []
    for x in spec:
        i = _resolve_one(x, trs, src)
        if i not in out:
            out.append(i)
    return out


def _muted(spec, trs: List[dict], src) -> set:
    """mute= as a set of audio indices: an index, a name, '1,2' or a list of either. None, '' and [] mute nothing
    (pick() reads None and '' as every track, so they never reach it)."""
    if spec is None or (isinstance(spec, str) and not spec.strip()):
        return set()
    if not isinstance(spec, (str, int)):
        try:
            spec = list(spec)
        except TypeError:
            raise ff.MediaError(f"mute={spec!r}: give a track index, a name, '1,2' or a list of them") from None
        if not spec:
            return set()
    return set(pick(spec, trs, src))


def _gain_map(gains_db, trs: List[dict], src) -> Dict[int, float]:
    if not gains_db:
        return {}
    if isinstance(gains_db, (list, tuple)):
        return {i: float(g) for i, g in enumerate(gains_db)}
    try:
        items = dict(gains_db).items()
    except (TypeError, ValueError):
        raise ff.MediaError(f"gains_db={gains_db!r}: give {{track: dB}} or one dB per track "
                            f"(gain_db= on a span gains all of it)") from None
    return {_resolve_one(k, trs, src): float(v) for k, v in items}


def _span_args(span: Span) -> List[str]:
    if not span:
        return []
    t0, t1 = float(span[0]), float(span[1])
    if t1 <= t0 or t0 < 0:
        raise ff.MediaError(f"bad span {span}: need 0 <= start < end (seconds on the source clock)")
    return (["-ss", f"{t0:.6f}"] if t0 else []) + ["-t", f"{t1 - t0:.6f}"]


#: How far a span may end past the file: export's rule (1 ms), so an end read off the container's duration passes.
_END_TOL_S = 1e-3


def audio_end(trs: List[dict]) -> float:
    """Where the last audio track ends on the source clock."""
    return max(t["start_s"] + t["duration_s"] for t in trs)


def check_span(span: Span, trs: List[dict], src="") -> None:
    """Refuse a span the file cannot fill: one that starts at or after the audio ends, or ends past the end of the
    file (+1 ms). Unchecked, a span past the end measured I -70 LUFS / TP 0.0 dBTP (ebur128 got no frames) and mixed
    to zero samples while timeline_s claimed the requested length."""
    if not span:
        return
    t0, t1 = float(span[0]), float(span[1])
    name = Path(str(src)).name or "source"
    if t1 <= t0 or t0 < 0:
        raise ff.MediaError(f"bad span [{t0:g}, {t1:g}) of {name}: need 0 <= start < end (seconds on the source clock)")
    if not trs:
        raise ff.MediaError(f"{name} has no audio track")
    a_end = audio_end(trs)
    f_end = max(a_end, max(float(t.get("file_duration_s") or 0.0) for t in trs))
    if t0 >= a_end:
        raise ff.MediaError(f"bad span [{t0:g}, {t1:g}): the audio of {name} ends at {a_end:.3f} s")
    if t1 > f_end + _END_TOL_S:
        raise ff.MediaError(f"bad span [{t0:g}, {t1:g}): {name} ends at {f_end:.3f} s; need end <= duration")


def _codec_for(out, codec: Optional[str]) -> str:
    if codec:
        if codec not in CODECS:
            raise ff.MediaError(f"unknown codec {codec!r}: one of {', '.join(CODECS)}")
        return codec
    ext = Path(str(out)).suffix.lower()
    if ext not in _EXT_CODEC:
        raise ff.MediaError(f"cannot pick an audio codec for {ext or 'no extension'}; pass codec= one of "
                            f"{', '.join(CODECS)}")
    return _EXT_CODEC[ext]


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "track"


#: Windows refuses a command line over 32767 characters; leave room for quoting.
_CMDLINE_MAX = 32000


def _filter_args(graph: str) -> List[str]:
    """-filter_complex inline, or read from a file (ffmpeg's -/option syntax) when the graph would crowd the Windows
    command line. The file is named by the graph's hash, so a repeat reuses it instead of piling up."""
    if len(graph) < 8000:
        return ["-filter_complex", graph]
    d = ff.state_dir() / "tmp"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"graph-{hashlib.sha1(graph.encode('utf-8')).hexdigest()[:16]}.txt"
    if not path.is_file():
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(graph)
    return ["-/filter_complex", str(path)]


def _check_cmdline(args: Sequence[str], what: str) -> None:
    n = len(subprocess.list2cmdline(ff.argv_for(args)))
    if n > _CMDLINE_MAX:
        raise ff.MediaError(f"{what} needs a {n}-character command line (Windows stops at 32767): mix the spans in "
                            f"batches (each batch to a WAV, placed with its own `at`), then mix the batch files")


# =================================================================================================
# loudness, silences
# =================================================================================================

_PARSED = re.compile(r"\[Parsed_(\w+?)_(\d+) @ [^\]]*\]\s*(.*)")


def _num(m) -> Optional[float]:
    if not m:
        return None
    v = float(m.group(1))
    return None if math.isinf(v) else v


def parse_ebur128(stderr: str) -> Dict[int, dict]:
    """{parsed filter index: {I, LRA, TP, threshold}} from every ebur128 summary in one ffmpeg log. Integrated
    loudness is printed to 0.1 LU; TP is the true peak (dBTP), None for digital silence."""
    out = {}
    for m in re.finditer(r"\[Parsed_ebur128_(\d+) @ [^\]]*\]\s*Summary:(.*?)(?=\n\[|\Z)", stderr, re.S):
        body = m.group(2)
        out[int(m.group(1))] = {
            "I": _num(re.search(r"I:\s+(-?[\d.]+|-?inf) LUFS", body)),
            "threshold": _num(re.search(r"Threshold:\s+(-?[\d.]+|-?inf) LUFS", body)),
            "LRA": _num(re.search(r"LRA:\s+(-?[\d.]+|-?inf) LU\b", body)),
            "TP": _num(re.search(r"Peak:\s+(-?[\d.]+|-?inf) dBFS", body)),
        }
    return out


class _Graph:
    """A filtergraph built chain by chain, remembering each filter's parse index so log lines map back to tracks."""

    def __init__(self):
        self.chains: List[str] = []
        self._n = 0
        self.owner: Dict[int, Tuple[str, object]] = {}

    def add(self, head: str, filters: Sequence[Tuple[str, str]], tail: str, owner=None) -> None:
        parts = []
        for name, args in filters:
            if owner is not None:
                self.owner[self._n] = (name, owner)
            self._n += 1
            parts.append(f"{name}={args}" if args else name)
        self.chains.append(f"{head}{','.join(parts)}{tail}")

    def text(self) -> str:
        return ";".join(self.chains)


def _ebur128_filters() -> List[Tuple[str, str]]:
    return [("ebur128", "peak=true:framelog=quiet")]


def _measure(src, idx: List[int], span: Span, *, silence: Optional[Tuple[float, float]] = None,
             end_s: Optional[float] = None) -> dict:
    """One decode pass: ebur128 (and optionally silencedetect) on each chosen track -> {a_index: {...}}. A silence
    still open when the stream ends closes at the span end, else at end_s."""
    g = _Graph()
    outs = []
    for i in idx:
        filters = _ebur128_filters()
        if silence:
            filters = filters + [("silencedetect", f"noise={silence[0]}dB:d={silence[1]}")]
        g.add(f"[0:a:{i}]", filters, f"[m{i}]", owner=i)
        outs += ["-map", f"[m{i}]"]
    res = ff.run(["-nostats", *_span_args(span), "-i", str(src), *_filter_args(g.text()), *outs, "-f", "null", "-"])
    summaries = parse_ebur128(res.stderr)
    out: Dict[int, dict] = {i: {"I": None, "LRA": None, "TP": None, "threshold": None, "silences": []} for i in idx}
    for k, v in summaries.items():
        name, owner = g.owner.get(k, (None, None))
        if name == "ebur128":
            out[owner].update(v)
    if silence:
        found = _silence_spans(res.stderr, g, idx, t0=float(span[0]) if span else 0.0,
                               end_s=float(span[1]) if span else end_s)
        for i in idx:
            out[i]["silences"] = found[i]
    out["_argv"] = res.args
    return out


def _silence_spans(stderr: str, g: _Graph, owners: Iterable, *, t0: float = 0.0,
                   end_s: Optional[float] = None) -> Dict[object, List[list]]:
    """silencedetect log lines -> {owner: [[start, end], ...]}, shifted by t0 onto the source clock; a silence still
    open when the stream ends closes at end_s."""
    out: Dict[object, List[list]] = {o: [] for o in owners}
    open_at: Dict[object, float] = {}
    for line in stderr.splitlines():
        m = _PARSED.search(line)
        if not m or m.group(1) != "silencedetect":
            continue
        owner = g.owner.get(int(m.group(2)), (None, None))[1]
        st = re.search(r"silence_start:\s*(-?[\d.]+)", m.group(3))
        en = re.search(r"silence_end:\s*(-?[\d.]+)", m.group(3))
        if st:
            open_at[owner] = float(st.group(1))
        elif en and owner in open_at:
            out[owner].append([round(t0 + open_at.pop(owner), 6), round(t0 + float(en.group(1)), 6)])
    for owner, st in open_at.items():
        out[owner].append([round(t0 + st, 6), round(end_s, 6) if end_s is not None else None])
    return out


def loudness(src, *, tracks: TrackSpec = "all", span: Span = None) -> dict:
    """Integrated loudness (LUFS), loudness range (LU) and true peak (dBTP) of each chosen track, in one decode."""
    trs = _list(src)
    idx = pick(tracks, trs, src)
    check_span(span, trs, src)
    t = time.perf_counter()
    m = _measure(src, idx, span)
    rows = [{"index": i, "house_name": trs[i]["house_name"], "channels": trs[i]["channels"],
             **{k: m[i][k] for k in ("I", "LRA", "TP", "threshold")}} for i in idx]
    params = {"tracks": tracks, "span": list(span) if span else None, "meter": "ebur128 peak=true"}
    return receipt.result("loudness", src, params, {"tracks": rows, "seconds": round(time.perf_counter() - t, 3),
                                                    "argv": m["_argv"]},
                          blind=["I is printed by ebur128 to 0.1 LU",
                                 "a mono track is measured as mono (BS.1770 counts it once: 3 LU under the same "
                                 "signal on both channels of a stereo track)",
                                 "TP is the true peak of the decoded track, not of a later re-encode"])


def silences(src, *, track: Union[int, str] = 0, noise_db: float = -40.0, min_s: float = 0.5,
             span: Span = None) -> dict:
    """Stretches of track quieter than noise_db for at least min_s, as [t0, t1] on the source clock."""
    trs = tracks(src)
    i = pick([track], trs, src)[0]
    check_span(span, trs, src)
    m = _measure(src, [i], span, silence=(noise_db, min_s), end_s=trs[i]["start_s"] + trs[i]["duration_s"])
    params = {"track": track, "noise_db": noise_db, "min_s": min_s, "span": list(span) if span else None}
    return receipt.result("silences", src, params, {"index": i, "house_name": trs[i]["house_name"],
                                                    "silences": m[i]["silences"], "I": m[i]["I"]},
                          blind=["silence is a level threshold: quiet speech under noise_db counts as silence"])


# =================================================================================================
# demux, split
# =================================================================================================

def _default_dir(verb: str, src) -> Path:
    return ff.state_dir() / verb / receipt.quick_id(src)


def demux(src, out_dir=None, *, tracks: TrackSpec = "all", codec: str = "copy") -> dict:
    """One file per chosen track. codec='copy' keeps the packets (Opus -> .ogg, AAC -> .m4a, MP3, FLAC, PCM -> .wav;
    anything Chromium cannot play is re-encoded to FLAC and the row says so); 'flac' or 'wav' decode and re-encode.
    Every file is played by Chromium's <audio> element and decodeAudioData (measured for .ogg/.m4a/.flac/.wav)."""
    if codec not in ("copy", "flac", "wav"):
        raise ff.MediaError(f"demux codec {codec!r}: copy, flac or wav")
    trs = _list(src)
    idx = pick(tracks, trs, src)
    out = Path(out_dir) if out_dir else _default_dir("demux", src)
    out.mkdir(parents=True, exist_ok=True)
    stem = _safe(Path(str(src)).stem)
    args = ["-y", "-i", str(src)]
    rows = []
    for i in idx:
        t = trs[i]
        if codec == "copy" and t["codec"] in _COPY_CONTAINER:
            ext, extra = _COPY_CONTAINER[t["codec"]]
            enc, how = ["-c:a", "copy"], "copy"
        elif codec == "wav":
            pcm = "pcm_s24le" if t["codec"] == "pcm_s24le" else "pcm_s16le"
            ext, extra, enc, how = ".wav", [], ["-c:a", pcm], "wav"
        else:
            ext, extra, enc = ".flac", [], ["-c:a", "flac"]
            how = "flac" if codec == "flac" else f"flac (no browser container for {t['codec']} copy)"
        path = out / f"{stem}.a{i}.{_safe(t['house_name'])}{ext}"
        args += ["-map", f"0:a:{i}", *enc, "-map_chapters", "-1", "-map_metadata", "-1",
                 "-metadata", f"title={t['house_name']}", "-metadata:s:a:0", f"title={t['house_name']}",
                 *extra, str(path)]
        rows.append({"index": i, "house_name": t["house_name"], "codec": t["codec"], "how": how, "path": str(path),
                     "start_s": t["start_s"], "duration_s": t["duration_s"]})
    t0 = time.perf_counter()
    res = ff.run(args)
    params = {"tracks": tracks, "codec": codec, "out_dir": str(out)}
    return receipt.result("demux", src, params,
                          {"files": [r["path"] for r in rows], "tracks": rows,
                           "seconds": round(time.perf_counter() - t0, 3), "argv": res.args},
                          blind=["start_s is the track's start in the source file (a file time): a track that starts "
                                 "late in the source plays from 0 in its own file, so the editor offsets it by start_s",
                                 "a copy keeps the source's packets: an Ogg/WebM file has no video to sync against"])


def split_channels(src, track: Union[int, str] = 0, out_dir=None) -> dict:
    """One mono WAV per channel of a track (e.g. an OBS track carrying the mic left and the game right)."""
    trs = tracks(src)
    i = pick([track], trs, src)[0]
    t = trs[i]
    layout = t["layout"] or ("stereo" if t["channels"] == 2 else "mono" if t["channels"] == 1 else None)
    if not layout or t["channels"] < 2:
        raise ff.MediaError(f"track {i} has {t['channels']} channel(s) and layout {t['layout']!r}: nothing to split")
    out = Path(out_dir) if out_dir else _default_dir("split", src)
    out.mkdir(parents=True, exist_ok=True)
    labels = "".join(f"[c{k}]" for k in range(t["channels"]))
    args = ["-y", "-i", str(src), "-filter_complex", f"[0:a:{i}]channelsplit=channel_layout={layout}{labels}"]
    stem = _safe(Path(str(src)).stem)
    files = []
    for k in range(t["channels"]):
        path = out / f"{stem}.a{i}.ch{k}.wav"
        args += ["-map", f"[c{k}]", "-c:a", "pcm_s16le" if t["codec"] != "pcm_s24le" else "pcm_s24le", str(path)]
        files.append(str(path))
    res = ff.run(args)
    return receipt.result("split", src, {"track": track, "out_dir": str(out)},
                          {"index": i, "layout": layout, "files": files, "argv": res.args},
                          blind=["channel names follow ffmpeg's layout order (FL, FR, ...)"])


# =================================================================================================
# mix
# =================================================================================================

def _norm_spans(src, spans, *, tracks: TrackSpec, gains_db, mute, span: Span, info) -> List[dict]:
    """Spans as dicts with every field filled: src, start, end, at (timeline seconds), dur, tracks, gains."""
    if spans is None:
        if src is None:
            raise ff.MediaError("mix needs a source or a list of spans")
        spans = [{"src": src, "start": span[0] if span else 0.0, "end": span[1] if span else None}]
    if not spans:
        raise ff.MediaError("mix got an empty list of spans: nothing to render")
    out, cursor = [], 0.0
    for n, s in enumerate(spans):
        s = dict(s) if isinstance(s, dict) else {"start": s[0], "end": s[1]}
        path = s.get("src") or src
        if path is None:
            raise ff.MediaError(f"span {n} names no src and mix has no default source")
        trs = info(path)
        if not trs:
            raise ff.MediaError(f"span {n}: {Path(str(path)).name} has no audio track")
        start = float(s.get("start") or 0.0)
        end = s.get("end")
        stop = float(end) if end is not None else audio_end(trs)
        try:
            check_span((start, stop), trs, path)
        except ff.MediaError as exc:
            raise ff.MediaError(f"span {n}: {exc}") from None
        dur = stop - start
        at = float(s["at"]) if s.get("at") is not None else cursor
        if at < 0:
            raise ff.MediaError(f"span {n}: at={at} is before the timeline start")
        idx = pick(s.get("tracks", tracks), trs, path)
        if not idx:
            raise ff.MediaError(f"span {n} picks no audio track")
        gains = _gain_map(gains_db, trs, path)
        gains.update(_gain_map(s.get("gains_db"), trs, path))
        muted = _muted(s.get("mute", mute), trs, path)
        live = [i for i in idx if i not in muted]
        out.append({"src": str(path), "start": start, "end": end if end is None else float(end), "dur": dur,
                    "at": at, "tracks": live, "muted": sorted(muted & set(idx)),
                    "gains_db": {i: gains.get(i, 0.0) + float(s.get("gain_db", 0.0)) for i in live},
                    "fade_in_s": float(s.get("fade_in_s", s.get("fade_s", 0.0)) or 0.0),
                    "fade_out_s": float(s.get("fade_out_s", s.get("fade_s", 0.0)) or 0.0)})
        cursor = at + dur
    return out


def mix_graph(spans: List[dict], *, sample_rate: int = 48000, label: str = "mix") -> Tuple[List[str], str]:
    """(input args, filtergraph) mixing normalized spans into one stereo float bus [label]. Each span is one input,
    trimmed at the input (sample-exact on 1/sr timebases), each track resampled to stereo at sample_rate, gained,
    summed (amix normalize=0: a plain sum, no hidden 1/N), padded with silence to its full length when its audio
    ends early, faded, and delayed to its timeline position in samples."""
    if not spans:
        raise ff.MediaError("mix_graph got no spans")
    inputs: List[str] = []
    chains: List[str] = []
    buses = []
    for k, s in enumerate(spans):
        inputs += (["-ss", f"{s['start']:.6f}"] if s["start"] else [])
        inputs += (["-t", f"{s['dur']:.6f}"] if s["end"] is not None else [])
        inputs += ["-i", s["src"]]
        live = s["tracks"] or s["muted"][:1]          # every track muted: keep one at zero so the span keeps its length
        if not live:
            raise ff.MediaError(f"span {k} has no audio track to mix")
        legs = []
        for i in live:
            vol = f"volume={s['gains_db'][i]:.4f}dB" if s["tracks"] else "volume=0"
            chains.append(f"[{k}:a:{i}]aresample={sample_rate},aformat=sample_fmts=fltp:channel_layouts=stereo,"
                          f"{vol}[s{k}t{i}]")
            legs.append(f"[s{k}t{i}]")
        post = []
        if s["end"] is not None:      # audio that ends before the span does (a short track) still fills its place
            post.append(f"apad=whole_len={int(round(s['dur'] * sample_rate))}")
        if s["fade_in_s"] > 0:
            post.append(f"afade=t=in:st=0:d={s['fade_in_s']:.6f}")
        if s["fade_out_s"] > 0:
            post.append(f"afade=t=out:st={max(0.0, s['dur'] - s['fade_out_s']):.6f}:d={s['fade_out_s']:.6f}")
        delay = int(round(s["at"] * sample_rate))
        if delay:
            post.append(f"adelay=delays={delay}S:all=1")
        if len(legs) > 1:
            head = f"{''.join(legs)}amix=inputs={len(legs)}:normalize=0:duration=longest:dropout_transition=0"
            chains.append(head + ("," + ",".join(post) if post else "") + f"[b{k}]")
        else:
            chains.append(f"{legs[0]}{','.join(post) if post else 'anull'}[b{k}]")
        buses.append(f"[b{k}]")
    if len(buses) > 1:
        chains.append(f"{''.join(buses)}amix=inputs={len(buses)}:normalize=0:duration=longest:dropout_transition=0"
                      f"[{label}]")
    else:
        chains.append(f"{buses[0]}anull[{label}]")
    return inputs, ";".join(chains)


#: A two-pass render whose read-back I misses its target by more than this is rendered once more with the miss
#: subtracted: loudnorm's own pass-1 meter disagrees with ebur128 by up to 0.33 LU on modulated tones (measured).
_I_RETRY_LU = 0.2
#: The spec's bar for a two-pass render (P6: within +-0.5 LU); a final read-back further off is a problem in the result.
_I_OK_LU = 0.5

#: The ranges loudnorm accepts for pass 2's measured_* options. Pass 1 prints input_i -inf and target_offset inf for
#: digital silence (or audio wholly under the -70 LUFS gate), which pass 2 rejects outright (measured on anullsrc).
_LN_MEASURED = {"input_i": (-99.0, 0.0), "input_tp": (-99.0, 99.0), "input_lra": (0.0, 99.0),
                "input_thresh": (-99.0, 0.0), "target_offset": (-99.0, 99.0)}


def _loudnorm_json(stderr: str) -> dict:
    m = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr, re.S)
    if not m:
        raise ff.MediaError("loudnorm printed no measurement JSON", stderr=stderr)
    return json.loads(m[-1])


def loudnorm_unmeasurable(m1: dict) -> Optional[str]:
    """Why a loudnorm pass-1 measurement cannot drive pass 2 (None when it can). Any two-pass caller can use it."""
    for key, (lo, hi) in _LN_MEASURED.items():
        try:
            v = float(m1.get(key))
        except (TypeError, ValueError):
            return f"loudnorm pass 1 printed {key}={m1.get(key)!r}; rendered without loudness normalization"
        if not lo <= v <= hi:
            if key == "input_i" and v < lo:
                return ("the audio is digital silence (or wholly under the -70 LUFS gate); rendered without loudness "
                        "normalization")
            return (f"loudnorm pass 1 measured {key}={m1.get(key)} (pass 2 takes {lo:g}..{hi:g}); rendered without "
                    f"loudness normalization")
    return None


def normalize_render(inputs: List[str], graph: str, label: str, out, enc_args: List[str], *,
                     target: Optional[dict], sample_rate: int = 48000, tries: int = 2,
                     gpu: Optional[str] = None) -> dict:
    """Render [label] of graph to out with enc_args; with target {I, TP, LRA}, a measured two-pass loudnorm whose
    output is read back with ebur128 and, if it misses (|I - target| > 0.2 LU or TP over target, e.g. AAC overshoot),
    rendered once more with the miss subtracted. Shared by mix, loudnorm_2pass and export.

    Returns {argv, attempts, pass1, measured, normalized, notes, problems}: measured is the read-back of out (None
    without a target); problems names a target still missed after the last render (sparse content in dynamic mode
    can miss by 2 LU, measured); notes says why a render was not normalized (digital silence renders plainly)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    attempts = []

    def run(args: List[str], gpu_label: Optional[str] = None):
        _check_cmdline(args, f"mixing {inputs.count('-i')} inputs")
        return ff.run(args, gpu=gpu_label)

    def plain():
        return run(["-y", "-nostats", *inputs, *_filter_args(f"{graph};[{label}]aresample={sample_rate}[aout]"),
                    "-map", "[aout]", *enc_args, str(out)], gpu)

    if not target:
        return {"argv": plain().args, "attempts": attempts, "pass1": None, "measured": None, "normalized": False,
                "notes": [], "problems": []}
    meas_graph = (f"{graph};[{label}]loudnorm=I={target['I']}:TP={target['TP']}:LRA={target['LRA']}"
                  f":print_format=json[lm]")
    p1 = run(["-nostats", *inputs, *_filter_args(meas_graph), "-map", "[lm]", "-f", "null", "-"])
    m1 = _loudnorm_json(p1.stderr)
    pass1 = {k: m1.get(k) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    why = loudnorm_unmeasurable(m1)
    if why:
        argv = plain().args
        got = _measure(out, [0], None)[0]
        return {"argv": argv, "attempts": attempts, "pass1": pass1, "measured": {k: got[k] for k in ("I", "LRA", "TP")},
                "normalized": False, "notes": [why], "problems": []}
    aim_i, aim_tp = float(target["I"]), float(target["TP"])
    argv = None
    for n in range(max(1, tries)):
        ln = (f"loudnorm=I={aim_i:.2f}:TP={aim_tp:.2f}:LRA={target['LRA']}:measured_I={m1['input_i']}"
              f":measured_TP={m1['input_tp']}:measured_LRA={m1['input_lra']}:measured_thresh={m1['input_thresh']}"
              f":offset={m1['target_offset']}:linear=true:print_format=json")
        res = run(["-y", "-nostats", *inputs, *_filter_args(f"{graph};[{label}]{ln},aresample={sample_rate}[aout]"),
                   "-map", "[aout]", *enc_args, str(out)], gpu)
        argv = res.args
        mode = _loudnorm_json(res.stderr).get("normalization_type")
        got = _measure(out, [0], None)[0]
        attempts.append({"aim_I": round(aim_i, 2), "aim_TP": round(aim_tp, 2), "mode": mode,
                         "I": got["I"], "TP": got["TP"], "LRA": got["LRA"]})
        miss_i = (got["I"] - float(target["I"])) if got["I"] is not None else 0.0
        over_tp = (got["TP"] - float(target["TP"])) if got["TP"] is not None else -1.0
        if abs(miss_i) <= _I_RETRY_LU and over_tp <= 0.0:
            break
        aim_i -= miss_i
        if over_tp > 0:
            aim_tp -= over_tp + 0.1
    final = attempts[-1]
    problems = []
    if final["I"] is None or abs(final["I"] - float(target["I"])) > _I_OK_LU + 1e-9:
        problems.append(f"integrated loudness {final['I']} LUFS is not {target['I']} within {_I_OK_LU} LU after "
                        f"{len(attempts)} render(s) ({final['mode']} mode)")
    if final["TP"] is not None and final["TP"] > float(target["TP"]) + 1e-9:
        problems.append(f"true peak {final['TP']} dBTP is over {target['TP']}")
    return {"argv": argv, "attempts": attempts, "pass1": pass1, "measured": {k: final[k] for k in ("I", "LRA", "TP")},
            "normalized": True, "notes": [], "problems": problems}


def _mute_param(mute) -> object:
    """mute= as it goes into the receipt: a name or index stays itself, anything else iterable becomes a list."""
    if mute is None or isinstance(mute, (str, int)):
        return mute
    try:
        return list(mute)
    except TypeError:
        return repr(mute)


def mix(src, out, *, gains_db: Optional[dict] = None, mute: TrackSpec = (), tracks: TrackSpec = "all",
        span: Span = None, spans: Optional[Sequence[dict]] = None, codec: Optional[str] = None,
        loudnorm: Optional[float] = None, tp: float = -1.0, lra: float = 11.0, sample_rate: int = 48000,
        measure: bool = True) -> dict:
    """Mix audio tracks to one stereo file with per-track gains (dB) and mutes.

    One source: mix(src, out, gains_db={0: 0, 1: -6}, mute=[2], span=(10, 20)); mute takes an index, a name,
    '2,3' or a list. Several clips (the editor's render): spans=[{src, start, end, at=None, tracks=, gains_db=, mute=,
    gain_db=0, fade_in_s=0, fade_out_s=0}, ...]; a span without `at` follows the previous one, a span without `src`
    uses src. Overlapping spans sum. A span must lie inside its file (a span past the end is refused). codec None
    follows out's extension (.m4a aac, .ogg opus, .flac, .wav). loudnorm=-14 runs the measured two-pass loudnorm on
    the mix (TP and LRA targets tp, lra); ok/problems say whether the read-back met it, notes why it was skipped."""
    cache: Dict[str, List[dict]] = {}

    def info(p):
        key = str(p)
        if key not in cache:
            cache[key] = _list(p)
        return cache[key]

    plan = _norm_spans(src, spans, tracks=tracks, gains_db=gains_db, mute=mute, span=span, info=info)
    codec = _codec_for(out, codec)
    inputs, graph = mix_graph(plan, sample_rate=sample_rate)
    target = {"I": float(loudnorm), "TP": float(tp), "LRA": float(lra)} if loudnorm is not None else None
    t0 = time.perf_counter()
    done = normalize_render(inputs, graph, "mix", out, CODECS[codec][0], target=target, sample_rate=sample_rate)
    seconds = round(time.perf_counter() - t0, 3)
    if done["measured"] is not None:
        measured = done["measured"]                     # loudnorm already read the output back
    else:
        measured = _measure(out, [0], None)[0] if measure else None
    length = max(s["at"] + s["dur"] for s in plan)
    params = {"gains_db": {str(k): v for k, v in (gains_db or {}).items()} if isinstance(gains_db, dict) else gains_db,
              "mute": _mute_param(mute), "tracks": tracks, "span": list(span) if span else None,
              "spans": None if spans is None else len(spans), "codec": codec, "loudnorm": loudnorm, "tp": tp,
              "lra": lra, "sample_rate": sample_rate, "measure": measure}
    srcs = sorted({s["src"] for s in plan})
    payload = {"out": str(Path(out)), "codec": codec, "timeline_s": round(length, 6),
               "spans": [{**s, "gains_db": {str(k): v for k, v in s["gains_db"].items()}} for s in plan],
               "graph": graph, "argv": done["argv"], "loudnorm": done["pass1"], "attempts": done["attempts"],
               "normalized": done["normalized"] if target else None, "ok": not done["problems"],
               "problems": done["problems"], "notes": done["notes"],
               "measured": {k: measured[k] for k in ("I", "LRA", "TP")} if measured else None, "seconds": seconds}
    return receipt.result("mix", srcs[0] if len(srcs) == 1 else srcs, params, payload,
                          blind=["a mono track is upmixed to stereo at -3 dB per channel (swresample's default), "
                                 "which keeps its loudness: the same LUFS as the mono source, measured",
                                 "amix sums without limiting: gains that push the sum over 0 dBFS clip in the encoder; "
                                 "read measured.TP",
                                 "spans on an MKV/WebM source start on its 1 ms timestamp grid",
                                 "digital silence cannot be loudness-normalized: it renders plainly and notes say so"])


def loudnorm_2pass(src, out, *, target_i: float = -14.0, tp: float = -1.0, lra: float = 11.0,
                   track: Union[int, str, None] = None, span: Span = None, codec: Optional[str] = None,
                   sample_rate: int = 48000) -> dict:
    """Measured two-pass loudnorm of one track (None = a:0, OBS's mix) to target_i LUFS with true peak <= tp,
    read back with ebur128; a miss is corrected by one more render. One-pass loudnorm lands about 1 LU off.
    ok is False (and problems says why) when the final read-back is still more than 0.5 LU off or over tp;
    digital silence renders plainly with a note (normalized False)."""
    trs = tracks(src)
    i = pick([0 if track is None else track], trs, src)[0]
    check_span(span, trs, src)
    plan = [{"src": str(src), "start": float(span[0]) if span else 0.0, "end": float(span[1]) if span else None,
             "dur": (float(span[1]) - float(span[0])) if span else trs[i]["duration_s"], "at": 0.0, "tracks": [i],
             "muted": [], "gains_db": {i: 0.0}, "fade_in_s": 0.0, "fade_out_s": 0.0}]
    codec = _codec_for(out, codec)
    inputs, graph = mix_graph(plan, sample_rate=sample_rate)
    t0 = time.perf_counter()
    done = normalize_render(inputs, graph, "mix", out, CODECS[codec][0],
                            target={"I": target_i, "TP": tp, "LRA": lra}, sample_rate=sample_rate)
    params = {"target_i": target_i, "tp": tp, "lra": lra, "track": track, "span": list(span) if span else None,
              "codec": codec, "sample_rate": sample_rate}
    return receipt.result("loudnorm", src, params,
                          {"out": str(Path(out)), "index": i, "before": done["pass1"], "after": done["measured"],
                           "mode": done["attempts"][-1]["mode"] if done["attempts"] else None,
                           "normalized": done["normalized"], "ok": not done["problems"], "problems": done["problems"],
                           "notes": done["notes"], "attempts": done["attempts"], "argv": done["argv"],
                           "seconds": round(time.perf_counter() - t0, 3)},
                          blind=["dynamic mode (when linear gain would breach tp) compresses: LRA can shrink",
                                 "sparse content (a short sound over a quiet floor) puts loudnorm in dynamic mode, "
                                 "where the corrective render may not converge (1.9 LU too loud, measured): read ok",
                                 "the output is stereo; the source's video is not carried (export does that)"])


# =================================================================================================
# qc
# =================================================================================================

def _fps(s: dict) -> float:
    for key in ("avg_frame_rate", "r_frame_rate"):
        num, _, den = str(s.get(key) or "0/0").partition("/")
        try:
            if float(den or 1):
                v = float(num) / float(den or 1)
                if v > 0:
                    return v
        except ValueError:
            continue
    return 0.0


def streams(path) -> dict:
    """Stream inventory with exact packet counts (demux only, no decode) and the container duration."""
    j = ff.probe_json(path, entries=("-show_format", "-show_streams", "-count_packets"))
    rows, a_n = [], 0
    for s in j.get("streams") or []:
        tags = _stream_tags(j, s)
        kind = s.get("codec_type")
        dur = s.get("duration")
        dur = float(dur) if dur not in (None, "N/A") else _duration_tag(tags)
        row = {"index": int(s["index"]), "type": kind, "codec": s.get("codec_name"), "duration_s": dur,
               "packets": int(s["nb_read_packets"]) if str(s.get("nb_read_packets", "")).isdigit() else None}
        if kind == "video":
            row.update(w=s.get("width"), h=s.get("height"), fps=round(_fps(s), 6), pix_fmt=s.get("pix_fmt"),
                       alpha_mode=next((v for k, v in tags.items() if k.lower() == "alpha_mode"), None))
        elif kind == "audio":
            title, house, _ = track_name(a_n, tags)
            row.update(a_index=a_n, channels=s.get("channels"), sample_rate=int(s.get("sample_rate") or 0),
                       title=title, house_name=house)
            a_n += 1
        rows.append(row)
    fmt = j.get("format") or {}
    return {"streams": rows, "duration_s": float(fmt.get("duration") or 0.0), "format": fmt.get("format_name"),
            "size": int(fmt.get("size") or 0)}


def _video_checks(g: _Graph, outs: List[str], black: Tuple[float, float], freeze: Tuple[float, float]) -> None:
    g.add("[0:v:0]", [("scale", "320:-2"), ("blackdetect", f"d={black[1]}:pix_th={black[0]}"),
                      ("freezedetect", f"n={freeze[0]}dB:d={freeze[1]}")], "[vq]", owner="video")
    outs += ["-map", "[vq]"]


def _parse_video(stderr: str, g: _Graph, end_s: float) -> Tuple[List[list], List[list]]:
    black, freeze, fopen = [], [], None
    for line in stderr.splitlines():
        m = _PARSED.search(line)
        if not m or g.owner.get(int(m.group(2)), (None, None))[1] != "video":
            continue
        text = m.group(3)
        if m.group(1) == "blackdetect":
            b = re.search(r"black_start:\s*(-?[\d.]+)\s+black_end:\s*(-?[\d.]+)", text)
            if b:
                black.append([float(b.group(1)), float(b.group(2))])
        elif m.group(1) == "freezedetect":
            s = re.search(r"freeze_start:\s*(-?[\d.]+)", text)
            e = re.search(r"freeze_end:\s*(-?[\d.]+)", text)
            if s:
                fopen = float(s.group(1))
            elif e and fopen is not None:
                freeze.append([fopen, float(e.group(1))])
                fopen = None
    if fopen is not None:                     # frozen into the end of the file
        freeze.append([fopen, end_s])
    return black, freeze


def _expect_problems(expect: dict, inv: dict, loud: List[dict], black, freeze, silence) -> List[str]:
    probs = []
    vids = [s for s in inv["streams"] if s["type"] == "video"]
    auds = [s for s in inv["streams"] if s["type"] == "audio"]
    for key, have in (("video_streams", len(vids)), ("audio_streams", len(auds))):
        if key in expect and int(expect[key]) != have:
            probs.append(f"expected {expect[key]} {key.replace('_', ' ')}, found {have}")
    fps = vids[0]["fps"] if vids else 0.0
    if "duration_s" in expect:
        tol = float(expect.get("duration_tol_s") or ((1.0 / fps) if fps else 0.05))
        got = inv["duration_s"]
        if abs(got - float(expect["duration_s"])) > tol + 1e-6:
            probs.append(f"duration {got:.4f} s is not {float(expect['duration_s']):.4f} s within {tol:.4f} s")
    if "frames" in expect and vids:
        got = vids[0]["packets"]
        tol = int(expect.get("frames_tol", 1))
        if got is None or abs(got - int(expect["frames"])) > tol:
            probs.append(f"video has {got} frames, expected {expect['frames']} within {tol}")
    for key in ("w", "h"):
        if key in expect and vids and int(vids[0][key] or 0) != int(expect[key]):
            probs.append(f"video {key} {vids[0][key]}, expected {expect[key]}")
    if "fps" in expect and vids and abs(fps - float(expect["fps"])) > 0.01:
        probs.append(f"video fps {fps:.3f}, expected {expect['fps']}")
    if "titles" in expect:
        got_titles = [s["house_name"] for s in auds]
        if list(expect["titles"]) != got_titles:
            probs.append(f"audio titles {got_titles}, expected {list(expect['titles'])}")
    if loud:
        first = loud[int(expect.get("loudness_track", 0))] if len(loud) > int(expect.get("loudness_track", 0)) else None
        if first and "I" in expect:
            tol = float(expect.get("I_tol", 0.5))
            if first["I"] is None or abs(first["I"] - float(expect["I"])) > tol + 1e-9:
                probs.append(f"integrated loudness {first['I']} LUFS is not {expect['I']} within {tol} LU")
        if first and "TP_max" in expect and first["TP"] is not None and first["TP"] > float(expect["TP_max"]) + 1e-9:
            probs.append(f"true peak {first['TP']} dBTP is over {expect['TP_max']}")
    if expect.get("no_black") and black:
        probs.append(f"{len(black)} black stretch(es), first at {black[0][0]} s")
    if expect.get("no_freeze") and freeze:
        probs.append(f"{len(freeze)} frozen stretch(es), first at {freeze[0][0]} s")
    if expect.get("no_silence") and any(silence.values()):
        probs.append("silent stretch(es) in " + ", ".join(f"a:{k}" for k, v in silence.items() if v))
    return probs


def qc(path, *, expect: Optional[dict] = None, video: bool = True, audio: bool = True, hw: Optional[str] = "d3d11va",
       black: Tuple[float, float] = (0.10, 0.5), freeze: Tuple[float, float] = (-60.0, 2.0),
       silence: Tuple[float, float] = (-50.0, 1.0)) -> dict:
    """Check a finished file in one decode pass: per-track I/LRA/TP, black, frozen and silent stretches, the stream
    inventory (exact packet counts) and duration. expect (all optional): video_streams, audio_streams, duration_s
    (+ duration_tol_s, default one frame), frames (+ frames_tol, default 1), w, h, fps, titles, I (+ I_tol, default
    0.5), TP_max, loudness_track (default 0), no_black, no_freeze, no_silence. Each miss is one line in problems."""
    expect = dict(expect or {})
    t0 = time.perf_counter()
    inv = streams(path)
    vids = [s for s in inv["streams"] if s["type"] == "video"]
    auds = [s for s in inv["streams"] if s["type"] == "audio"]
    g, outs = _Graph(), []
    if video and vids:
        _video_checks(g, outs, black, freeze)
    if audio:
        for s in auds:
            g.add(f"[0:a:{s['a_index']}]", _ebur128_filters() + [("silencedetect",
                                                                 f"noise={silence[0]}dB:d={silence[1]}")],
                  f"[q{s['a_index']}]", owner=s["a_index"])
            outs += ["-map", f"[q{s['a_index']}]"]
    loud, black_s, freeze_s, silence_s, argv = [], [], [], {}, None
    if g.chains:
        dec = ["-hwaccel", hw] if (hw and video and vids) else []
        res = ff.run(["-nostats", *dec, "-i", str(path), "-filter_complex", g.text(), *outs, "-f", "null", "-"])
        argv = res.args
        summaries = parse_ebur128(res.stderr)
        by_track = {g.owner[k][1]: v for k, v in summaries.items() if k in g.owner}
        if audio:
            silence_s = _silence_spans(res.stderr, g, [s["a_index"] for s in auds], end_s=inv["duration_s"])
        if audio:
            loud = [{"index": s["a_index"], "house_name": s["house_name"],
                     **{k: (by_track.get(s["a_index"]) or {}).get(k) for k in ("I", "LRA", "TP")}} for s in auds]
        if video and vids:
            black_s, freeze_s = _parse_video(res.stderr, g, inv["duration_s"])
    problems = _expect_problems(expect, inv, loud, black_s, freeze_s, silence_s)
    first = loud[0] if loud else {}
    params = {"expect": expect, "video": video, "audio": audio, "hw": hw, "black": list(black),
              "freeze": list(freeze), "silence": list(silence)}
    payload = {"ok": not problems, "problems": problems, "I": first.get("I"), "TP": first.get("TP"),
               "LRA": first.get("LRA"), "loudness": loud, "black": black_s, "freeze": freeze_s,
               "silence": silence_s, "duration_s": inv["duration_s"], "streams": inv["streams"],
               "format": inv["format"], "argv": argv, "seconds": round(time.perf_counter() - t0, 3)}
    return receipt.result("qc", path, params, payload,
                          blind=["black and freeze are judged on a 320 px wide copy of the first video stream",
                                 "alpha is not decoded here (export checks it per preset)",
                                 "I/TP of the first audio track are the headline; every track is in loudness"])


# =================================================================================================
# CLI: py -m arsenal.media audio|mix|qc ...
# =================================================================================================

def _parse_span(s: Optional[str]) -> Span:
    if not s:
        return None
    from .frames import parse_time
    lo, _, hi = s.partition("-") if s.count("-") == 1 else s.partition("..")
    return parse_time(lo), parse_time(hi)


def _parse_gains(s: Optional[str]) -> Optional[dict]:
    if not s:
        return None
    out = {}
    for part in s.split(","):
        k, _, v = part.partition(":" if ":" in part else "=")
        out[k.strip()] = float(v)
    return out


def _print(res: dict, keys: Sequence[str]) -> None:
    print(json.dumps({k: res.get(k) for k in keys if k in res}, indent=2, default=str))


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    if verb == "mix":
        ap = argparse.ArgumentParser(prog="py -m arsenal.media mix",
                                     description="mix audio tracks with per-track gain/mute (dB), optional loudnorm")
        ap.add_argument("src", nargs="?", help="source file (or give --spans)")
        ap.add_argument("out")
        ap.add_argument("--gains", help="per-track dB, e.g. 0:0,1:-6 or Voice:-3")
        ap.add_argument("--mute", help="tracks to mute, e.g. 2,3")
        ap.add_argument("--tracks", default="all")
        ap.add_argument("--span", help="start-end in s or m:ss, e.g. 10:00-10:20")
        ap.add_argument("--spans", help="JSON file: [{src, start, end, at, gains_db, mute, fade_in_s, ...}]")
        ap.add_argument("--codec", choices=sorted(CODECS))
        ap.add_argument("--loudnorm", type=float, help="target LUFS for a measured two-pass loudnorm")
        ap.add_argument("--tp", type=float, default=-1.0)
        a = ap.parse_args(argv)
        spans = json.loads(Path(a.spans).read_text(encoding="utf-8")) if a.spans else None
        mute = [m for m in (a.mute or "").split(",") if m.strip()]
        res = mix(a.src, a.out, gains_db=_parse_gains(a.gains), mute=mute, tracks=a.tracks, span=_parse_span(a.span),
                  spans=spans, codec=a.codec, loudnorm=a.loudnorm, tp=a.tp)
        _print(res, ("out", "timeline_s", "measured", "ok", "problems", "notes", "attempts", "seconds", "receipt"))
        return 0 if res["ok"] else 1
    if verb == "qc":
        ap = argparse.ArgumentParser(prog="py -m arsenal.media qc",
                                     description="check an export: loudness, true peak, black/freeze/silence, streams")
        ap.add_argument("path")
        ap.add_argument("--expect", help='JSON, e.g. {"audio_streams": 3, "duration_s": 10, "I": -14, "TP_max": -1.5}')
        ap.add_argument("--no-video", action="store_true", help="skip the black/freeze decode")
        a = ap.parse_args(argv)
        res = qc(a.path, expect=json.loads(a.expect) if a.expect else None, video=not a.no_video)
        _print(res, ("ok", "problems", "I", "TP", "LRA", "duration_s", "black", "freeze", "silence", "loudness",
                     "seconds", "receipt"))
        return 0 if res["ok"] else 1
    ap = argparse.ArgumentParser(prog="py -m arsenal.media audio",
                                 description="audio tracks of a video: names, loudness (LUFS, true peak), silences, "
                                             "demux each track to its own file, split channels, two-pass loudnorm")
    ap.add_argument("src")
    ap.add_argument("--loudness", action="store_true", help="I/LRA/TP per track (one decode pass)")
    ap.add_argument("--silences", action="store_true", help="silent stretches of --track")
    ap.add_argument("--track", default="0")
    ap.add_argument("--span", help="start-end in s or m:ss")
    ap.add_argument("--demux", metavar="DIR", nargs="?", const="", help="one browser-playable file per track")
    ap.add_argument("--codec", default="copy", choices=("copy", "flac", "wav"))
    ap.add_argument("--split", metavar="DIR", nargs="?", const="", help="one mono WAV per channel of --track")
    ap.add_argument("--loudnorm", metavar="OUT", help="two-pass loudnorm of --track to OUT")
    ap.add_argument("--target", type=float, default=-14.0)
    ap.add_argument("--tp", type=float, default=-1.0)
    a = ap.parse_args(argv)
    span = _parse_span(a.span)
    track = int(a.track) if a.track.lstrip("-").isdigit() else a.track
    print(json.dumps({"tracks": tracks(a.src)}, indent=2))
    if a.loudness:
        _print(loudness(a.src, span=span), ("tracks", "seconds", "receipt"))
    if a.silences:
        _print(silences(a.src, track=track, span=span), ("silences", "I", "receipt"))
    if a.demux is not None:
        _print(demux(a.src, a.demux or None, codec=a.codec), ("files", "seconds", "receipt"))
    if a.split is not None:
        _print(split_channels(a.src, track, a.split or None), ("files", "receipt"))
    if a.loudnorm:
        res = loudnorm_2pass(a.src, a.loudnorm, target_i=a.target, tp=a.tp, track=track, span=span)
        _print(res, ("out", "before", "after", "mode", "ok", "problems", "notes", "attempts", "receipt"))
        return 0 if res["ok"] else 1
    return 0
