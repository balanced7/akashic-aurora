"""py -m arsenal.media <verb> ... -- the house video toolbox from the command line.

Each verb lives in its own module, imported only when called, and the module's cli(verb, argv) parses the rest.
The help strings use the words agents type (ffmpeg, frame, contact sheet, trim, scene, loudness, waveform, clock,
Riot, timeline): recall-at-action matches them when an agent is about to hand-roll the same thing.
"""
from __future__ import annotations

import importlib
import sys

#: verb -> (module under arsenal.media, help)
VERBS = {
    "doctor": ("ff", "where ffmpeg and ffprobe live, what the build can do (AMF, whisper, libass, scdet), "
                     "optional packages; --save remembers the best ffmpeg"),
    "probe": ("probe", "ffprobe a video: duration, codec, fps, every audio track and its name, keyframe interval, "
                       "OBS encoder, recorded time; remembered in the media catalog"),
    "import": ("catalog", "import videos into the media catalog (probe + sidecar), never copying or touching them"),
    "find": ("catalog", "query the media catalog: recordings by kind, date, track count; resolve a dropped file"),
    "grab": ("frames", "grab frames from a video at times or over a span in one ffmpeg pass (hardware decode, "
                       "crop, resize); --sheet makes a contact sheet"),
    "sheet": ("sheet", "contact sheet: many frames or images on one labelled grid (file time + game time)"),
    "filmstrip": ("sheet", "filmstrip: a row of frames over the waveform of the same seconds, to watch 10 s at once"),
    "cut": ("cut", "trim/cut a video to the exact frame: copy (lossless, keyframe), smart (re-encode only the "
                   "head, copy the rest) or exact; keeps every audio track and its name; --plan shows the cost"),
    "audio": ("audio", "audio tracks of a video: list with names, loudness (LUFS, true peak), silences, demux "
                       "each track to its own file, split channels"),
    "mix": ("audio", "mix audio tracks with per-track gain and mute (dB), optional loudnorm"),
    "qc": ("audio", "check an export: loudness, true peak, black/freeze/silence, stream inventory, duration"),
    "peaks": ("peaks", "waveform peaks for one audio track (peaks.js .dat/.json, wavesurfer)"),
    "shots": ("shots", "scene detection: find the cuts/shots in a video (PySceneDetect or ffmpeg scdet on a "
                       "360p proxy; League clock jumps)"),
    "words": ("words", "speech to text with word timestamps (faster-whisper + VAD, no hallucinated 'if if if')"),
    "clockmap": ("league.clock", "League of Legends HUD clock OCR: map video time to game time (replay rewinds, "
                                 "0.25x/0.5x slow motion)"),
    "events": ("league.events", "Riot match-v5 timeline events (kills, items, objectives) pinned to video "
                                "frames; fight windows"),
    "replay": ("league.replay_api", "League Replay API (127.0.0.1:2999): status, swagger fetch, drive a planned "
                                    "take (seek, camera follow, speed, HUD off) while OBS records; capture run-sheet; "
                                    "--dry-run sends nothing"),
    "avsync": ("avsync","audio/video sync offset and drift between two recordings, or audio vs MIDI events"),
    "export": ("export", "export with platform presets (YouTube 4K, Shorts 9:16, edit proxy, alpha WebM/WebP) "
                         "and a loudness QC receipt"),
    "edit": ("edit", "the editor's timeline document: create, show, add clips/tracks, trim, render to a file"),
}


def _usage() -> str:
    width = max(len(v) for v in VERBS)
    lines = ["usage: py -m arsenal.media <verb> [args]   (each verb takes -h)", "", "verbs:"]
    lines += [f"  {verb.ljust(width)}  {help_}" for verb, (_mod, help_) in VERBS.items()]
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(_usage())
        return 0
    verb, rest = argv[0], argv[1:]
    if verb not in VERBS:
        print(f"unknown verb {verb!r}\n\n{_usage()}", file=sys.stderr)
        return 2
    module_name = f"arsenal.media.{VERBS[verb][0]}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            print(f"{verb}: not built yet ({module_name})", file=sys.stderr)
            return 3
        raise
    from .ff import MediaError
    try:
        return int(module.cli(verb, rest) or 0)
    except MediaError as exc:
        print(f"{verb}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
