"""arsenal.media.peaks -- waveform peaks for the editor's audio lanes, without installing BBC audiowaveform.

One ffmpeg decode per track to 16-bit PCM, streamed through numpy in 2 MB chunks (a 33-minute recording never sits in
memory), reduced to the min and max of every `spp` samples. Three files from one pass:
  .json   audiowaveform JSON v2: {version, channels, sample_rate, samples_per_pixel, bits, length, data: [min, max,
          ...]} -- peaks.js and waveform-data.js read it natively, and any canvas can draw it (pixel x spans
          samples [x*spp, (x+1)*spp) of the track, i.e. x*spp/sample_rate seconds after start_s);
  .dat    the same data in audiowaveform's binary v2 (24-byte header + int8/int16 pairs), what peaks.js prefers;
  .wavesurfer.json  {duration, peaks: [[0..1 per pixel]]} for wavesurfer.js v7 (WaveSurfer.create({peaks, duration})).
8-bit by default (peaks.js recommends it: half the size, visually identical); an 8-bit value is the 16-bit value
shifted right by 8 (floor), so -32768 -> -128 and 32767 -> 127. The last pixel covers the leftover samples only:
length = ceil(samples / spp), and every pixel's min/max equal numpy's over exactly its samples.

Measured 2026-10-12: the 33-min OBS Opus track of 2026-10-11 17-51-11 at spp 512 -> 190,149 pixels in 3.3 s (the
spec's budget is 5 s), a 380,322-byte (371 KB) .dat and a 951 KB JSON that Chromium fetched and parsed.
"""
from __future__ import annotations

import json
import math
import struct
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

from . import ff, receipt

_CHUNK_PIXELS = 2048          # pixels per read: 2 MB of mono s16 at spp 512
FORMATS = ("dat", "json", "wavesurfer")


def compute(src, *, track: Union[int, str] = 0, spp: int = 512, bits: int = 8, channels: str = "mono",
            span: Optional[Tuple[float, float]] = None, sample_rate: Optional[int] = None) -> dict:
    """The waveform as audiowaveform v2 fields with `data` a numpy array (per pixel: ch0 min, ch0 max, ch1 min, ...),
    plus `samples` (decoded samples per channel) and `start_s` (where pixel 0 starts on the source clock)."""
    import numpy as np
    from .audio import _span_args, check_span, pick, tracks
    if spp < 2 or bits not in (8, 16) or channels not in ("mono", "split"):
        raise ff.MediaError(f"peaks: need spp >= 2, bits 8 or 16, channels mono|split (got {spp}, {bits}, {channels})")
    trs = tracks(src)
    i = pick([track], trs, src)[0]
    check_span(span, trs, src)          # a span past the end decoded nothing and returned length 0 as a success
    sr = int(sample_rate or trs[i]["sample_rate"] or 48000)
    ch = 1 if channels == "mono" else max(1, trs[i]["channels"])
    proc = ff.popen(["-v", "error", *_span_args(span), "-i", str(src), "-map", f"0:a:{i}", "-ac", str(ch),
                     "-ar", str(sr), "-c:a", "pcm_s16le", "-f", "s16le", "-"])
    block = spp * ch * 2
    mins: List["np.ndarray"] = []
    maxs: List["np.ndarray"] = []
    samples = 0
    try:
        while True:
            buf = proc.stdout.read(block * _CHUNK_PIXELS)
            if not buf:
                break
            pcm = np.frombuffer(buf[: len(buf) - len(buf) % (2 * ch)], np.int16).reshape(-1, ch)
            samples += len(pcm)
            full = len(pcm) // spp
            if full:
                blk = pcm[: full * spp].reshape(full, spp, ch)
                mins.append(blk.min(axis=1))
                maxs.append(blk.max(axis=1))
            if len(pcm) % spp:                      # only at the end of the stream: a read is whole pixels otherwise
                rest = pcm[full * spp:]
                mins.append(rest.min(axis=0, keepdims=True))
                maxs.append(rest.max(axis=0, keepdims=True))
    finally:
        ff.finish(proc)
    mn = np.concatenate(mins) if mins else np.zeros((0, ch), np.int16)
    mx = np.concatenate(maxs) if maxs else np.zeros((0, ch), np.int16)
    if bits == 8:
        mn, mx = (mn >> 8).astype(np.int8), (mx >> 8).astype(np.int8)
    data = np.empty((len(mn), 2 * ch), mn.dtype)
    data[:, 0::2], data[:, 1::2] = mn, mx
    return {"version": 2, "channels": ch, "sample_rate": sr, "samples_per_pixel": spp, "bits": bits,
            "length": int(len(mn)), "data": data.reshape(-1), "samples": int(samples), "index": i,
            "house_name": trs[i]["house_name"], "start_s": float(span[0]) if span else 0.0}


def as_json(w: dict) -> dict:
    """The browser JSON (audiowaveform v2) for a compute() result: plain ints, no numpy."""
    return {"version": 2, "channels": w["channels"], "sample_rate": w["sample_rate"],
            "samples_per_pixel": w["samples_per_pixel"], "bits": w["bits"], "length": w["length"],
            "data": w["data"].tolist()}


def write_json(w: dict, path) -> str:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(as_json(w), fh, separators=(",", ":"))
    return str(path)


def write_dat(w: dict, path) -> str:
    """audiowaveform binary v2: int32 version, uint32 flags (1 = 8-bit), int32 sample_rate, int32 samples_per_pixel,
    uint32 length, int32 channels, then the interleaved min/max values little-endian."""
    import numpy as np
    flags = 1 if w["bits"] == 8 else 0
    with open(path, "wb") as fh:
        fh.write(struct.pack("<iIiiIi", 2, flags, w["sample_rate"], w["samples_per_pixel"], w["length"],
                             w["channels"]))
        fh.write(w["data"].astype(np.int8 if flags else "<i2").tobytes())
    return str(path)


def write_wavesurfer(w: dict, path) -> str:
    """wavesurfer.js v7: max |sample| per pixel normalized to [0, 1], one array per channel, plus the duration."""
    import numpy as np
    full = 128.0 if w["bits"] == 8 else 32768.0
    d = w["data"].reshape(w["length"], w["channels"], 2).astype(np.float64)    # float32 would print its noise
    amp = np.minimum(np.maximum(np.abs(d[..., 0]), np.abs(d[..., 1])) / full, 1.0)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"duration": round(w["samples"] / w["sample_rate"], 6),
                   "peaks": [np.round(amp[:, c], 3).tolist() for c in range(w["channels"])]},
                  fh, separators=(",", ":"))
    return str(path)


_WRITERS = {"dat": (".dat", write_dat), "json": (".json", write_json), "wavesurfer": (".wavesurfer.json",
                                                                                     write_wavesurfer)}


def peaks(src, *, track: Union[int, str] = 0, spp: int = 512, bits: int = 8, channels: str = "mono",
          span: Optional[Tuple[float, float]] = None, out_prefix=None,
          formats: Sequence[str] = FORMATS, refresh: bool = False) -> dict:
    """Write the waveform of one track as .dat / .json / .wavesurfer.json and return the house result (paths and the
    header fields; the data stays in the files). Without out_prefix the files live under <state>/peaks/<source id>/
    and a second call with the same parameters on the unchanged file returns them without decoding (cached: true)."""
    bad = [f for f in formats if f not in _WRITERS]
    if bad:
        raise ff.MediaError(f"unknown peaks format(s) {bad}: {', '.join(_WRITERS)}")
    from .audio import pick, tracks
    src_info = receipt.source(src)
    track = pick([track], tracks(src), src)[0]
    span_tag = f"_{span[0]:g}-{span[1]:g}" if span else ""
    prefix = Path(out_prefix) if out_prefix else (
        ff.state_dir() / "peaks" / src_info["id"] / f"a{track}_spp{spp}_{bits}bit_{channels}{span_tag}")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    params = {"track": track, "spp": spp, "bits": bits, "channels": channels, "span": list(span) if span else None,
              "out_prefix": str(prefix), "formats": list(formats)}
    meta_path = Path(f"{prefix}.meta.json")
    files = {f: f"{prefix}{_WRITERS[f][0]}" for f in formats}
    blind = ["peaks are min/max per pixel: they show level, not loudness (use loudness for LUFS)",
             "channels=mono is ffmpeg's downmix (the mean of the channels)"]
    if not refresh and not out_prefix and meta_path.is_file() and all(Path(p).is_file() for p in files.values()):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except ValueError:
            meta = {}
        if meta.get("source") == {k: src_info[k] for k in ("size", "mtime_ns", "id")} and meta.get("params") == params:
            return receipt.result("peaks", src_info, params, {**meta["header"], "files": files, "cached": True},
                                  blind=blind)
    t0 = time.perf_counter()
    w = compute(src, track=track, spp=spp, bits=bits, channels=channels, span=span)
    t1 = time.perf_counter()
    for f in formats:
        _WRITERS[f][1](w, files[f])
    header = {k: w[k] for k in ("version", "channels", "sample_rate", "samples_per_pixel", "bits", "length",
                                "samples", "index", "house_name", "start_s")}
    header["duration_s"] = round(w["samples"] / w["sample_rate"], 6)
    header["pixels_per_second"] = round(w["sample_rate"] / spp, 6)
    header["seconds"] = {"decode_reduce": round(t1 - t0, 3), "write": round(time.perf_counter() - t1, 3)}
    header["bytes"] = {f: Path(p).stat().st_size for f, p in files.items()}
    if not out_prefix:
        with open(meta_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"source": {k: src_info[k] for k in ("size", "mtime_ns", "id")}, "params": params,
                       "header": header}, fh)
    return receipt.result("peaks", src_info, params, {**header, "files": files, "cached": False}, blind=blind)


def expected_length(samples: int, spp: int) -> int:
    """Pixels for a track of `samples` samples: the last pixel may be partial."""
    return math.ceil(samples / spp)


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    from .audio import _parse_span
    ap = argparse.ArgumentParser(prog="py -m arsenal.media peaks",
                                 description="waveform peaks for one audio track (peaks.js .dat/.json, wavesurfer)")
    ap.add_argument("src")
    ap.add_argument("--track", default="0", help="a:N index or a track name (Voice, Game, ...)")
    ap.add_argument("--spp", type=int, default=512, help="samples per pixel (default 512 = 93.75 px/s at 48 kHz)")
    ap.add_argument("--bits", type=int, default=8, choices=(8, 16))
    ap.add_argument("--channels", default="mono", choices=("mono", "split"))
    ap.add_argument("--span", help="start-end in s or m:ss")
    ap.add_argument("--out", help="output prefix (default: <state>/peaks/<source id>/...)")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv)
    track = int(a.track) if a.track.lstrip("-").isdigit() else a.track
    res = peaks(a.src, track=track, spp=a.spp, bits=a.bits, channels=a.channels, span=_parse_span(a.span),
                out_prefix=a.out, refresh=a.refresh)
    print(json.dumps({k: res.get(k) for k in ("files", "length", "samples", "sample_rate", "samples_per_pixel",
                                              "duration_s", "seconds", "bytes", "cached", "receipt")}, indent=2))
    return 0
