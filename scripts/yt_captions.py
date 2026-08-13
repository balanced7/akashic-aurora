"""yt_captions -- YouTube captions to clean readable text (the W154 `captions` verb).

Born 2026-08-13, mid-laughter: the Clarke & Dawe archive run proved the flow by hand
and Daniil ruled it a verb ("I am having a blast"). Named `captions`, NOT `transcript`:
transcripts are dead sessions in this house (the eye's plane), and load-bearing words
do not get forked for recreation.

Two halves, deliberately unequal:
  clean_vtt_text()  PURE and pinned (tests/test_w154_captions_verb.py) -- strips WEBVTT
                    headers, cue timings, bare cue indices, inline styling tags; collapses
                    the rolling duplicates YouTube auto-captions emit; preserves order.
  fetch()           a thin yt-dlp passthrough (their contract, not ours). Captions ONLY --
                    --skip-download is not a courtesy, it is the contract: this verb never
                    pulls video. Fails with a TEACHING error when yt-dlp is absent.

Standalone: py scripts/yt_captions.py <url> [--out DIR]
House door:  py agent_cli.py captions <url> [--out DIR] [--langs SPEC] [--keep-vtt]
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import List

MISSING_YTDLP_HINT = (
    "yt-dlp is not importable from this interpreter. Install it into the fleet python:\n"
    "    py -3.11 -m pip install yt-dlp\n"
    "(then retry; the verb calls `<this python> -m yt_dlp`, so the install must land in "
    "the same interpreter family the CLI runs under)"
)

_TAG = re.compile(r"<[^>]+>")


def clean_vtt_text(vtt_text: str) -> str:
    """WEBVTT -> plain deduplicated text. Pure; order-preserving; never raises."""
    lines: List[str] = []
    prev = None
    for ln in (vtt_text or "").splitlines():
        ln = ln.strip()
        if (not ln or "-->" in ln or ln.isdigit()
                or ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE"))):
            continue
        ln = _TAG.sub("", ln).strip()
        if ln and ln != prev:
            lines.append(ln)
            prev = ln
    return "\n".join(lines)


def fetch(url: str, out_dir: str, langs: str = "en.*", keep_vtt: bool = False) -> List[Path]:
    """Pull caption files for `url` into out_dir, convert each to .txt, return txt paths.

    Never downloads video. On missing yt-dlp, raises RuntimeError carrying the
    teaching hint (the door prints it and exits nonzero -- errors that teach)."""
    out = Path(out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    before = set(out.glob("*.vtt"))
    cmd = [sys.executable, "-m", "yt_dlp", "--skip-download",
           "--write-subs", "--write-auto-subs", "--sub-langs", langs,
           "--restrict-filenames", "-P", str(out), url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except FileNotFoundError as e:
        raise RuntimeError(MISSING_YTDLP_HINT) from e
    if r.returncode != 0 and "No module named yt_dlp" in (r.stderr or ""):
        raise RuntimeError(MISSING_YTDLP_HINT)
    if r.returncode != 0:
        raise RuntimeError(f"yt-dlp failed (rc={r.returncode}):\n{(r.stderr or '')[-600:]}")
    fresh = sorted(set(out.glob("*.vtt")) - before)
    # Prefer the plain .en.vtt over .en-orig.vtt twins (identical content, less noise).
    fresh = [p for p in fresh if not p.name.endswith(".en-orig.vtt")] or fresh
    txts: List[Path] = []
    for vtt in fresh:
        txt = vtt.with_suffix("").with_suffix(".txt") if vtt.suffix == ".vtt" else vtt
        txt = Path(str(vtt)[: -len(".vtt")] + ".txt")
        txt.write_text(clean_vtt_text(vtt.read_text(encoding="utf-8", errors="replace")) + "\n",
                       encoding="utf-8")
        txts.append(txt)
        if not keep_vtt:
            try:
                vtt.unlink()
            except OSError:
                pass
    # drop the -orig twins we skipped converting, unless the caller wants raw vtt kept
    if not keep_vtt:
        for stray in set(out.glob("*.en-orig.vtt")):
            try:
                stray.unlink()
            except OSError:
                pass
    return txts


def main(argv: List[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="YouTube captions -> clean text (captions only, never video)")
    ap.add_argument("url")
    ap.add_argument("--out", default=str(Path.home() / "Desktop" / "captions"))
    ap.add_argument("--langs", default="en.*")
    ap.add_argument("--keep-vtt", action="store_true")
    a = ap.parse_args(argv)
    try:
        txts = fetch(a.url, a.out, a.langs, a.keep_vtt)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2
    if not txts:
        print("no caption tracks found for this video (it may have none in the requested langs)")
        return 1
    for t in txts:
        print(t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
