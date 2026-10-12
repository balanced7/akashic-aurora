"""arsenal.media.parse -- the small text formats around a recording: OBS file names, captions, chapters.

Why it exists: these were re-parsed by hand every time. vttwords.py was written twice, analyze_video.py grew its own
caption reader, and FFMETADATA chapter files were typed out by hand. One reader each, pure Python, no ffmpeg:

  obs_time(name)           OBS names a recording after its local start time: "2026-10-11 17-51-11.mp4" -> datetime
  subtitles(path)          WebVTT / SRT / ASS -> words (when the file carries word times) or segments
  read_ffmetadata(src)     ;FFMETADATA1 text -> {"tags", "chapters": [{t0, t1, title, tags}]}
  write_ffmetadata(chs)    chapters -> ;FFMETADATA1 text, ready for `ffmpeg -i in -i ch.txt -map_chapters 1`

Times are float seconds on the file's own clock. Words use the house word shape (arsenal.stt's words.json):
{"start", "end", "word"}; segments are {"start", "end", "text"}; chapters are {"t0", "t1", "title"} like every other
time-ranged row in the media catalog.
"""
from __future__ import annotations

import re
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

# =================================================================================================
# OBS file names
# =================================================================================================

#: OBS's default "%CCYY-%MM-%DD %hh-%mm-%ss": the stamp may sit inside a longer name ("... tiktok 28-52.mp4").
_OBS_STAMP = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})[ _T](\d{2})-(\d{2})-(\d{2})(?!\d)")


def obs_time(name) -> Optional[datetime]:
    """The local wall-clock start time OBS put in a file name, as a naive datetime; None when the name holds none.

    The stamp is LOCAL time (OBS formats it from the machine clock), so it is returned naive on purpose: pair it with
    local_epoch() for an instant, never with UTC."""
    m = _OBS_STAMP.search(Path(str(name)).name)
    if not m:
        return None
    try:
        return datetime(*(int(g) for g in m.groups()))
    except ValueError:          # 2026-13-45 is a stamp-shaped name, not a time
        return None


def local_epoch(dt: datetime) -> float:
    """Seconds since the epoch for a naive LOCAL datetime (DST from this machine's zone rules); an aware datetime
    keeps its own offset."""
    return dt.timestamp()


# =================================================================================================
# captions: WebVTT, SRT, ASS/SSA
# =================================================================================================

_TS = r"(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3}"
_CUE = re.compile(rf"({_TS})\s*-->\s*({_TS})")
_INLINE_TS = re.compile(rf"<({_TS})>")
_TAG = re.compile(r"<[^>]+>")
_ASS_OVERRIDE = re.compile(r"\{[^}]*\}")
_ASS_KARAOKE = re.compile(r"\{[^}]*?\\[kK][fo]?(\d+)[^}]*\}")


def _sec(stamp: str) -> float:
    """'01:02:03.450', '02:03,450', '0:02:03.45' -> seconds."""
    whole, _, frac = stamp.replace(",", ".").partition(".")
    total = 0
    for part in whole.split(":"):
        total = total * 60 + int(part)
    return total + (float(f"0.{frac}") if frac else 0.0)


#: A one-line string ending in one of these names a file, never caption or chapter text.
_TEXT_FILE_EXTS = frozenset((".vtt", ".srt", ".ass", ".ssa", ".txt", ".ffmeta", ".ffmetadata", ".meta"))


def _read_text(src) -> str:
    """The text of a file, or src itself when it is the text. A one-line string that looks like a path (an absolute
    path, or a caption/metadata file extension) and is not a file refuses: a mistyped path must not read as
    'this file has no captions'."""
    if isinstance(src, Path):
        return src.read_text(encoding="utf-8-sig", errors="replace")
    text = str(src)
    if "\n" in text or len(text) >= 1024:
        return text
    p = Path(text.strip())
    if p.is_file():
        return p.read_text(encoding="utf-8-sig", errors="replace")
    if p.suffix.lower() in _TEXT_FILE_EXTS or p.is_absolute():
        raise FileNotFoundError(f"no such caption or metadata file: {text}")
    return text


def _format_of(path, text: str) -> str:
    ext = Path(str(path)).suffix.lower() if isinstance(path, (str, Path)) and "\n" not in str(path) else ""
    head = text.lstrip()[:200]
    if ext in (".ass", ".ssa") or head.startswith("[Script Info]"):
        return "ass"
    if ext == ".vtt" or head.startswith("WEBVTT"):
        return "vtt"
    return "srt"


def _cues(text: str) -> List[tuple]:
    """(start, end, body) for every WebVTT/SRT cue; cue numbers, NOTE/STYLE blocks and settings are dropped."""
    out = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        m = _CUE.search(block)
        if not m:
            continue
        rest = block[m.end():]
        body = rest.split("\n", 1)[1] if "\n" in rest else ""
        out.append((_sec(m.group(1)), _sec(m.group(2)), body.strip("\n")))
    return out


def _clean(line: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub("", line)).strip()


def _vtt_words(cues: List[tuple]) -> List[dict]:
    """YouTube-style word times: <00:00:01.234><c> word</c>. Only the lines that carry tags are read: a rolling
    caption repeats the previous line untagged in the next cue, and reading it would double every word."""
    words = []
    for start, end, body in cues:
        for line in body.split("\n"):
            if not _INLINE_TS.search(line) and "<c>" not in line:
                continue
            pieces = _INLINE_TS.split(line)        # text, ts, text, ts, text ...
            t = start
            for k, piece in enumerate(pieces):
                if k % 2 == 1:
                    t = _sec(piece)
                    continue
                for w in _clean(piece).split():
                    words.append({"start": round(t, 3), "word": w, "_cue_end": end})
    return words


def _spread(cues: List[tuple]) -> List[dict]:
    """Words of untimed cues, spread evenly over each cue (marked timed=False: the times are a guess)."""
    words = []
    for start, end, body in cues:
        toks = _clean(body.replace("\n", " ")).split()
        step = (end - start) / len(toks) if toks else 0.0
        for k, w in enumerate(toks):
            words.append({"start": round(start + k * step, 3), "word": w, "_cue_end": end, "timed": False})
    return words


def _finish_words(words: List[dict]) -> List[dict]:
    """End of a word = the next word's start, but never past its cue and never longer than 1 s (the rule
    analyze_video.py used for YouTube captions). A word that already knows its end (ASS karaoke) keeps it."""
    words.sort(key=lambda w: w["start"])
    for k, w in enumerate(words):
        cue_end = w.pop("_cue_end")
        if "end" in w:
            continue
        nxt = words[k + 1]["start"] if k + 1 < len(words) else cue_end
        w["end"] = round(max(w["start"], min(nxt, cue_end, w["start"] + 1.0)), 3)
    return words


def _segments(cues: List[tuple]) -> List[dict]:
    """One row per cue; a cue that only repeats the text of the one before it extends it instead (rolling captions)."""
    out: List[dict] = []
    for start, end, body in cues:
        text = "\n".join(_clean(ln) for ln in body.split("\n") if _clean(ln))
        if not text:
            continue
        if out and out[-1]["text"] == text and start - out[-1]["end"] <= 0.05:
            out[-1]["end"] = round(max(out[-1]["end"], end), 3)
            continue
        out.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    return out


def _ass_events(text: str) -> List[dict]:
    """Dialogue events of an ASS/SSA script, fields named by its own [Events] Format line."""
    fmt: Optional[List[str]] = None
    in_events = False
    events = []
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if line.startswith("["):
            in_events = line.lower() == "[events]"
            continue
        if not in_events:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        if key == "format":
            fmt = [f.strip().lower() for f in value.split(",")]
        elif key == "dialogue" and fmt:
            fields = value.lstrip().split(",", len(fmt) - 1)
            if len(fields) == len(fmt):
                events.append(dict(zip(fmt, fields)))
    return events


def _ass_text(raw: str) -> str:
    return re.sub(r"\s+", " ", _ASS_OVERRIDE.sub("", raw).replace("\\N", " ").replace("\\n", " ")
                  .replace("\\h", " ")).strip()


def _ass(text: str, level: str) -> List[dict]:
    events = [(_sec(ev.get("start", "0:00:00.00")), _sec(ev.get("end", "0:00:00.00")), ev.get("text", ""))
              for ev in _ass_events(text)]
    karaoke = any(_ASS_KARAOKE.search(raw) for _, _, raw in events)
    if level == "segments" or (level == "auto" and not karaoke):
        return [{"start": round(a, 3), "end": round(b, 3), "text": _ass_text(raw)}
                for a, b, raw in events if _ass_text(raw)]
    words: List[dict] = []
    for start, end, raw in events:
        if not _ASS_KARAOKE.search(raw):
            words += _spread([(start, end, _ass_text(raw))])
            continue
        t = start                            # {\k50}syl: each syllable lasts its centiseconds, in order
        for m in re.finditer(r"\{([^}]*)\}([^{]*)", raw):
            k = re.search(r"\\[kK][fo]?(\d+)", m.group(1))
            dur = int(k.group(1)) / 100.0 if k else 0.0
            syl = _ass_text(m.group(2))
            if syl:
                words.append({"start": round(t, 3), "end": round(min(t + dur, end), 3), "word": syl,
                              "_cue_end": end})
            t += dur
    return _finish_words(words)


def subtitles(path, *, level: str = "auto") -> List[dict]:
    """Captions -> rows on the file's clock. path: a .vtt/.srt/.ass/.ssa file, or the caption text itself; a path
    that is not a file raises FileNotFoundError.

    level: "auto" gives words when the file carries word times (YouTube <c> tags, ASS karaoke \\k) and segments
    otherwise; "words" always gives words (untimed cues spread evenly, each such word marked timed=False);
    "segments" always gives one row per cue."""
    if level not in ("auto", "words", "segments"):
        raise ValueError(f"level must be auto, words or segments, not {level!r}")
    text = _read_text(path)
    kind = _format_of(path, text)
    if kind == "ass":
        return _ass(text, level)
    cues = _cues(text)
    timed = any(_INLINE_TS.search(b) for _, _, b in cues)
    if level == "segments" or (level == "auto" and not timed):
        return _segments(cues)
    return _finish_words(_vtt_words(cues) if timed else _spread(cues))


# =================================================================================================
# FFMETADATA chapters
# =================================================================================================

_ESCAPE = {"=": "\\=", ";": "\\;", "#": "\\#", "\\": "\\\\", "\n": "\\\n"}


def _escape(value: str) -> str:
    return "".join(_ESCAPE.get(ch, ch) for ch in str(value))


def _logical_lines(text: str) -> Iterable[str]:
    """Join backslash-continued lines (an escaped newline belongs to the value)."""
    buf = ""
    for raw in text.replace("\r", "").split("\n"):
        buf += raw
        trailing = len(buf) - len(buf.rstrip("\\"))
        if trailing % 2 == 1:           # an odd run of backslashes escapes the newline
            buf = buf[:-1] + "\n"
            continue
        yield buf
        buf = ""
    if buf:
        yield buf


def _split_kv(line: str):
    """key=value with \\-escapes undone; the first UNESCAPED '=' splits."""
    key: List[str] = []
    value: List[str] = []
    cur, escaped, seen_eq = key, False, False
    for ch in line:
        if escaped:
            cur.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "=" and not seen_eq:
            seen_eq = True
            cur = value
        else:
            cur.append(ch)
    return ("".join(key), "".join(value)) if seen_eq else (None, None)


def read_ffmetadata(src) -> dict:
    """;FFMETADATA1 text (or a path to it) -> {"tags": {...}, "chapters": [{"t0", "t1", "title", "tags"}]}.

    START/END are converted with each chapter's own TIMEBASE (default 1/1000, ffmpeg's)."""
    text = _read_text(src)
    if not text.lstrip().startswith(";FFMETADATA"):
        raise ValueError("not an FFMETADATA file: the first line must be ;FFMETADATA1")
    tags: Dict[str, str] = {}
    chapters: List[dict] = []
    section, cur = "global", tags
    for line in list(_logical_lines(text))[1:]:
        if not line.strip() or line.lstrip().startswith((";", "#")):
            continue
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1].upper()
            cur = {}
            if section == "CHAPTER":
                chapters.append(cur)
            continue
        k, v = _split_kv(line)
        if k is not None and section in ("global", "CHAPTER"):
            cur[k] = v
    out = []
    for ch in chapters:
        base = Fraction(ch.pop("TIMEBASE", "1/1000"))
        start, end = int(ch.pop("START", 0)), int(ch.pop("END", 0))
        title = ch.pop("title", None)
        out.append({"t0": float(start * base), "t1": float(end * base), "title": title, "tags": ch})
    return {"tags": tags, "chapters": out}


def write_ffmetadata(chapters: Iterable[dict], out=None, *, tags: Optional[dict] = None,
                     timebase: Union[str, Fraction] = "1/1000") -> str:
    """Chapters [{t0, t1, title}] (start/end keys also accepted) -> ;FFMETADATA1 text, written to `out` if given.

    Times are rounded to the timebase; a chapter without an end runs to the next chapter's start."""
    base = Fraction(timebase)
    rows = []
    for ch in chapters:
        t0 = ch.get("t0", ch.get("start"))
        t1 = ch.get("t1", ch.get("end"))
        if t0 is None:
            raise ValueError(f"chapter without a start: {ch}")
        rows.append((float(t0), None if t1 is None else float(t1), ch.get("title"), ch.get("tags") or {}))
    rows.sort(key=lambda r: r[0])
    lines = [";FFMETADATA1"]
    lines += [f"{_escape(k)}={_escape(v)}" for k, v in (tags or {}).items()]
    for i, (t0, t1, title, extra) in enumerate(rows):
        if t1 is None:
            if i + 1 >= len(rows):
                raise ValueError(f"the last chapter (at {t0} s) needs an end")
            t1 = rows[i + 1][0]
        if t1 < t0:
            raise ValueError(f"chapter at {t0} s ends before it starts ({t1} s)")
        lines += ["", "[CHAPTER]", f"TIMEBASE={base.numerator}/{base.denominator}",
                  f"START={round(Fraction(t0) / base)}", f"END={round(Fraction(t1) / base)}"]
        if title is not None:
            lines.append(f"title={_escape(title)}")
        lines += [f"{_escape(k)}={_escape(v)}" for k, v in extra.items()]
    text = "\n".join(lines) + "\n"
    if out is not None:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return text
