"""arsenal.media.words -- speech to text with a time for every word, on the source's own clock, without the
hallucinated "if if if".

Whisper invents words over stretches with no speech: on 120 s of League audio (17-51-11, 600-720 s) large-v3-turbo
at beam 5 wrote "oh oh oh" in every run with the voice-activity filter off (once also seven "I"s in a row), and no
repeat in any run with it on; base wrote "if if if" the same way, though not every time. So words() always asks
arsenal.stt for VAD, and every result says whether its own text holds a repeated-word run (repeat_runs), the
cheapest hallucination check there is.

    words(src)                                  # the first audio track, the whole file
    words(src, track=1, span=(600, 720), model="large-v3-turbo")

The chosen track and span are cut to 16 kHz mono through ff (the original is only read), handed to
arsenal.stt.transcribe(vad=True), and every word time is shifted back onto the source clock, so a word at 12.7 s into
the span is written as 612.7. Long stretches go through in chunks of chunk_s seconds, which keeps memory flat on a
33-minute recording. Measured on this machine end to end (cut, model load, CPU int8, VAD on, 120 s of game audio):
small 36x realtime, large-v3-turbo 18x, base 55x. Without VAD turbo fell to 3.7x: it decodes the noise too.
Continuous speech leaves VAD little to skip: 463 s of narration (the studio animatic's scratch voice) ran at 8x with
small, 7x without VAD, and VAD cost no accuracy there (word error rate 10.8% on, 11.7% off).
"""
from __future__ import annotations

import json
import re
import tempfile
import time
import wave
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import ff, receipt

SAMPLE_RATE = 16000
CHUNK_S = 600.0          # longer stretches go to the model in pieces this long (memory stays flat)
RUN_MIN = 3              # a word said 3+ times in a row is reported as a repeat run
SPAN_SLACK_S = 0.5       # a span may overshoot the end by this much (containers round their duration)
COVER_SLACK_S = 0.1      # audio this much shorter than the span still counts as covering it (codec frame rounding)

BLIND = [
    "one mixed track holds voice and game together: speech under loud game sound can be dropped by VAD, and the "
    "model cannot tell whose voice it hears (OBS multi-track or stems fix this at the source)",
    "VAD can also cut a quiet word at the edge of speech; turning it off brings the hallucinated repeats back",
    "word times are Whisper's alignment, not a phonetic one: expect tens of milliseconds of slop per word",
    'letters that rhyme with "ee" (B C D E G P T V Z) are often confused even at high probability (stt EAR_NOTE)',
    "a word straddling a chunk edge (every chunk_s seconds of a long span) can be cut or lost",
    "a span the audio track does not reach (the video runs on past it) is heard only up to the track's end: "
    "audio_s counts the seconds actually decoded, and no audio is not silence",
    "times count from the file's first timestamp (format start_time), the same clock as arsenal.media.frames",
]


# =================================================================================================
# source facts
# =================================================================================================

def audio_tracks(src) -> Tuple[List[dict], float]:
    """(audio streams in order, file duration in s): one ffprobe call."""
    j = ff.probe_json(src, entries=("-select_streams", "a", "-show_entries",
                                    "stream=index,codec_name,channels,sample_rate,start_time:stream_tags=title,"
                                    "handler_name:format=duration"))
    return list(j.get("streams") or []), float((j.get("format") or {}).get("duration") or 0.0)


def resolve_track(streams: Sequence[dict], track: Optional[int], src) -> int:
    if not streams:
        raise ff.MediaError(f"{Path(src).name} has no audio track")
    t = 0 if track is None else int(track)
    if not 0 <= t < len(streams):
        raise ff.MediaError(f"audio track {t} is missing: {Path(src).name} has {len(streams)} audio track(s), "
                            f"0..{len(streams) - 1}")
    return t


def resolve_span(span, duration: float) -> Tuple[float, float]:
    """(t0, t1) inside the file; None is the whole file. Fails closed on an empty or outside range."""
    if span is None:
        if duration <= 0:
            raise ff.MediaError("the file reports no duration; give a span")
        return 0.0, duration
    t0, t1 = (float(v) for v in span)
    if t0 < 0 or t1 <= t0:
        raise ff.MediaError(f"bad span {t0:g}-{t1:g}: it needs 0 <= start < end")
    if duration > 0 and t0 >= duration:
        raise ff.MediaError(f"span start {t0:g} s is past the end of the file ({duration:.3f} s)")
    if duration > 0 and t1 > duration + SPAN_SLACK_S:
        raise ff.MediaError(f"span end {t1:g} s is past the end of the file ({duration:.3f} s)")
    return t0, min(t1, duration) if duration > 0 else t1


def parse_span(text: str) -> Tuple[float, float]:
    """'10:00-12:00', '600-720', '1:02:03-1:02:30' -> seconds."""
    from .frames import parse_time
    lo, sep, hi = str(text).partition("-")
    if not sep:
        raise ff.MediaError(f"bad span {text!r}: write start-end, e.g. 10:00-12:00")
    return parse_time(lo), parse_time(hi)


def cut_wav(src, track: int, t0: float, dur: float, out: Path) -> Path:
    """One audio track of [t0, t0+dur) as 16 kHz mono PCM. aresample's first_pts=0 pads a late-starting track with
    silence, so sample 0 is file time t0 even when the audio begins after the video."""
    ff.run(["-v", "error", *(["-ss", f"{t0:.6f}"] if t0 else []), "-i", str(src), "-t", f"{dur:.6f}",
            "-map", f"0:a:{track}", "-vn", "-sn", "-dn", "-af", "aresample=async=1:first_pts=0",
            "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-y", str(out)])
    return out


# =================================================================================================
# words on the source clock
# =================================================================================================

def _norm(word: str) -> str:
    return re.sub(r"[^\w']+", "", word.lower())


def repeat_runs(words: Sequence[dict], n: int = RUN_MIN) -> List[dict]:
    """Runs of n or more identical words in a row ("Oh. oh, OH" counts as three): Whisper's hallucination
    signature on stretches without speech. [{word, count, start, end}]"""
    out, i = [], 0
    toks = [_norm(w["word"]) for w in words]
    while i < len(toks):
        j = i
        while toks[i] and j + 1 < len(toks) and toks[j + 1] == toks[i]:
            j += 1
        if j - i + 1 >= n:
            out.append({"word": toks[i], "count": j - i + 1, "start": words[i]["start"], "end": words[j]["end"]})
        i = j + 1
    return out


def shift(words: Sequence[dict], t0: float) -> List[dict]:
    """Word times from the clip's clock (0 = span start) onto the source clock."""
    return [dict(w, start=round(w["start"] + t0, 3), end=round(w["end"] + t0, 3)) for w in words]


def cadence(words: Sequence[dict], t0: float, t1: float) -> str:
    """stt's cadence render on source-clock words. render() measures the opening silence from 0; on a span it is
    measured from the span start instead."""
    from arsenal import stt
    lines = stt.render(list(words), t1).splitlines()
    if words and words[0]["start"] >= stt.SPAN_S:          # render wrote an opening "no speech" line from 0
        lines = lines[1:]
        lead = words[0]["start"] - t0
        if lead >= stt.SPAN_S:
            lines.insert(0, f"       [{lead:.1f}s no speech]")
    if not words and t1 - t0 > 0:
        lines = [f"       [{t1 - t0:.1f}s no speech]"]
    return "\n".join(lines)


def _chunks(t0: float, t1: float, chunk_s: float) -> List[Tuple[float, float]]:
    out, a = [], t0
    while a < t1 - 1e-6:
        b = min(t1, a + chunk_s)
        if t1 - b < 1.0:                                     # never leave a sliver of under a second on its own
            b = t1
        out.append((a, b))
        a = b
    return out


def _secs(t: float) -> str:
    return f"{t:.3f}".rstrip("0").rstrip(".")


def _default_stem(src, track: int, t0: float, t1: float, model: str, vad: bool) -> Path:
    """<state>/words/<name>.a<track>.<t0>-<t1>.<model>: the model may be a local folder or a repo id, so only its
    last part, in safe characters, goes into the name; the span keeps its milliseconds so close spans never share."""
    tag = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(model).name).strip("._") or "model"
    name = f"{Path(src).stem}.a{track}.{_secs(t0)}-{_secs(t1)}.{tag}" + ("" if vad else ".novad")
    return ff.state_dir() / "words" / name


def _require_whisper() -> None:
    """Before any cut: without faster-whisper the work would end in a traceback after the decode."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError as exc:
        raise ff.MediaError(f"missing optional package faster-whisper ({exc}): words needs it for the model "
                            f"(faster-whisper 1.2.1 is in the house Python 3.11)") from None


def _wav_seconds(path: Path) -> float:
    with wave.open(str(path)) as wf:
        return wf.getnframes() / wf.getframerate()


def _transcribe_chunks(src, track: int, pieces, model: str, vad: bool,
                       work: Path) -> Tuple[List[dict], str, float, Optional[float]]:
    """(words on the source clock, model description, seconds of audio heard, file time the audio ends at)."""
    from arsenal import stt
    words: List[dict] = []
    model_desc, heard, heard_end = "", 0.0, None
    for i, (a, b) in enumerate(pieces):
        wav = cut_wav(src, track, a, b - a, work / f"chunk{i:03d}.wav")
        secs = _wav_seconds(wav)
        if secs > 0:                                         # past the track's end ffmpeg writes an empty wav
            heard, heard_end = heard + secs, a + secs
            stem = str(work / f"chunk{i:03d}")
            res = stt.transcribe(str(wav), stem, model, vad=vad)
            model_desc = res["model"]
            clip = json.loads(Path(stem + ".words.json").read_text(encoding="utf-8"))
            words.extend(shift(clip["words"], a))
        wav.unlink(missing_ok=True)                          # one chunk on disk at a time
    return words, model_desc, heard, heard_end


def words(src, *, track: Optional[int] = None, span: Optional[Tuple[float, float]] = None, model: str = "small",
          vad: bool = True, out_stem=None, chunk_s: float = CHUNK_S) -> dict:
    """Transcribe one audio track (the first by default) over span (the whole file by default).

    Writes <out_stem>.words.json (stt's format, times on the source clock) and <out_stem>.cadence.txt; returns the
    house result with {words_json, cadence_txt, words, unsure, vad, model, repeat_runs, span, track, audio_s,
    elapsed_s, x_realtime}."""
    from arsenal import stt
    src = Path(src)
    if not src.is_file():
        raise ff.MediaError(f"no such file: {src}")
    if chunk_s < 30:
        raise ff.MediaError(f"chunk_s {chunk_s:g} is too short; Whisper reads 30 s windows")
    streams, duration = audio_tracks(src)
    tr = resolve_track(streams, track, src)
    t0, t1 = resolve_span(span, duration)
    _require_whisper()
    stem = Path(out_stem) if out_stem else _default_stem(src, tr, t0, t1, model, vad)
    stem.parent.mkdir(parents=True, exist_ok=True)
    pieces = _chunks(t0, t1, chunk_s)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="words-", dir=stem.parent) as tmp:
        ws, model_desc, heard, heard_end = _transcribe_chunks(src, tr, pieces, model, vad, Path(tmp))
    elapsed = time.perf_counter() - started
    if heard_end is None:
        raise ff.MediaError(f"audio track {tr} holds no audio in {t0:g}-{t1:g} s: the track ends before the span "
                            f"starts (the video runs on without it)")
    short = heard_end < t1 - COVER_SLACK_S
    title = (streams[tr].get("tags") or {}).get("title") or (streams[tr].get("tags") or {}).get("handler_name")
    doc = {"model": model_desc, "vad": vad, "duration_s": round(t1 - t0, 3), "audio_s": round(heard, 3),
           "audio": src.name, "source": str(src.resolve()), "track": tr, "track_title": title, "span": [t0, t1],
           "clock": "file_t: seconds on the source's clock", "words": ws}
    words_json = Path(str(stem) + ".words.json")
    cadence_txt = Path(str(stem) + ".cadence.txt")
    words_json.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    text = cadence(ws, t0, heard_end if short else t1)
    if short:
        text += f"\n       [no audio after {heard_end:.1f}s: the track ends {t1 - heard_end:.1f}s before the span]"
    cadence_txt.write_text(text.lstrip("\n") + "\n", encoding="utf-8", newline="\n")
    params = {"track": tr, "span": [t0, t1] if span is not None else None, "model": model, "vad": vad,
              "out_stem": str(stem), "chunk_s": chunk_s, "sample_rate": SAMPLE_RATE, "language": "en",
              "beam_size": 5, "device": "cpu", "compute_type": "int8"}
    runs = repeat_runs(ws)
    payload = {"words_json": str(words_json), "cadence_txt": str(cadence_txt), "words": len(ws),
               "unsure": sum(w["p"] < stt.UNSURE_P for w in ws), "vad": vad, "model": model_desc,
               "repeat_runs": runs, "span": [t0, t1], "track": tr, "track_title": title, "chunks": len(pieces),
               "audio_s": round(heard, 3), "audio_ends_s": round(heard_end, 3) if short else None,
               "elapsed_s": round(elapsed, 2), "x_realtime": round(heard / elapsed, 1) if elapsed > 0 else None}
    blind = BLIND + ([f"the audio track ends at {heard_end:.3f} s, {t1 - heard_end:.1f} s before the span does: "
                      f"nothing after it was heard"] if short else [])
    return receipt.result("words", src, params, payload, blind, engine=_engine())


def _engine() -> Dict[str, Optional[str]]:
    import importlib.metadata
    try:
        return {"faster_whisper": importlib.metadata.version("faster-whisper")}
    except importlib.metadata.PackageNotFoundError:
        return {"faster_whisper": None}


# =================================================================================================
# CLI: py -m arsenal.media words <src> [--track 1] [--span 10:00-12:00] [--model large-v3-turbo] [--no-vad]
# =================================================================================================

def cli(verb: str, argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media words",
                                 description="speech to text with word timestamps (faster-whisper + VAD), times on "
                                             "the source's clock; writes .words.json and .cadence.txt")
    ap.add_argument("src")
    ap.add_argument("--track", type=int, default=None, help="audio track index (default 0, the first)")
    ap.add_argument("--span", help="start-end, e.g. 10:00-12:00 or 600-720 (default: the whole file)")
    ap.add_argument("--model", default="small",
                    help="small (indexing, ~32x realtime) or large-v3-turbo (final captions, ~16x); base is fastest")
    ap.add_argument("--no-vad", action="store_true", help="keep the stretches without speech (brings back the "
                                                          "hallucinated repeats; for comparison only)")
    ap.add_argument("--out", help="output stem (default: <state>/words/<name>.a<track>.<t0>-<t1>.<model>)")
    ap.add_argument("--chunk", type=float, default=CHUNK_S, help=f"seconds per model call (default {CHUNK_S:g})")
    ap.add_argument("--json", action="store_true", help="print the whole result")
    a = ap.parse_args(argv)
    res = words(a.src, track=a.track, span=parse_span(a.span) if a.span else None, model=a.model,
                vad=not a.no_vad, out_stem=a.out, chunk_s=a.chunk)
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    t0, t1 = res["span"]
    print(f"{res['model']} | track {res['track']} | {t0:.1f}-{t1:.1f} s | {res['words']} words, {res['unsure']} "
          f"unsure | {res['elapsed_s']} s ({res['x_realtime']}x realtime)")
    if res["audio_ends_s"] is not None:
        print(f"! the audio track ends at {res['audio_ends_s']:.1f} s: only {res['audio_s']:.1f} s of the span "
              f"were heard")
    for run in res["repeat_runs"]:
        print(f"! repeat run: {run['word']!r} x{run['count']} at {run['start']:.2f} s (likely hallucinated)")
    print(Path(res["cadence_txt"]).read_text(encoding="utf-8"), end="")
    print(f"-> {res['words_json']}")
    return 0
