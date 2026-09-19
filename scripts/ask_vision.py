"""ask_vision -- ONE targeted question about ONE frame, with retries, provenance and a cache.

WHY THIS EXISTS. A vision model is a useful second pair of eyes for a seat that has none, and a
dangerous one to quote loosely, for two reasons measured on this host (2026-09-18):

  (1) A LEADING QUESTION MANUFACTURES THE ANSWER. The same model, the same frame, minutes apart:
      asked "is there a figure -- concentric rings, a mandala, or a repeated pattern -- or a
      featureless field?" it answered "yes, very diffuse concentric rings" for a frame whose luma
      std is 0.0055 and whose annulus means are flat (no rings, measured independently). Asked
      neutrally -- "is the brightness spread evenly, and is there any repeating or radial
      structure? if none, say none" -- it answered "the top area is subtly lighter than the
      bottom. PATTERN: None", which is correct. THE PROMPT IS PART OF THE INSTRUMENT.

  (2) THE FREE TIER IS TRANSIENTLY UNAVAILABLE (a live 503 'high demand' on the first probe). A
      failed look must never be readable as "nothing there" -- so this door prints NO_EYES and
      exits non-zero rather than an empty answer.

WHAT IT ADDS OVER scripts/ask_gemini_vision.py (which it calls, and does not replace): retry with
backoff, a cache keyed by image-hash + question + region so the same look is never bought twice,
optional region cropping so a question can be asked about the part of the frame that matters, and a
PROVENANCE STAMP on every answer so a description can never wear the face of a first-hand sighting.

USAGE
  py scripts/ask_vision.py <image> "<question>" [--region x,y,w,h] [--json] [--no-cache]
                                           [--attempts 3] [--model gemini-2.5-flash]

HOUSE RULES FOR THE QUESTION (not enforced -- they are the discipline):
  * never name the answer in the question (see (1) above);
  * one axis at a time; let "none" and "cannot tell" be first-class answers;
  * prefer comparisons to absolute numbers;
  * ask the SAME question of a pair whose difference you know -- if both answers match, the answer
    carries no information;
  * when the model and a metric disagree, the metric wins, and the disagreement is a finding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "state" / "coord" / "vision_answers.jsonl"
DOOR = ROOT / "scripts" / "ask_gemini_vision.py"
DEFAULT_MODEL = "gemini-2.5-flash"
RETRYABLE = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "502", "504")


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crop_to(src: Path, region: str, dest: Path) -> None:
    """Region is fractional x,y,w,h in 0..1 -- the same convention the floors use, so a question
    about 'the top octave' means the same thing to the eye, the metric and the model."""
    sys.path.insert(0, str(ROOT))
    from arsenal import floors as F          # imported here so a cache hit needs no numpy/av
    from arsenal import storyboard as S
    x, y, w, h = (float(v) for v in region.split(","))
    rgb = F.load_rgb(str(src))
    S._write_png(F.crop(rgb, (x, y, w, h)), str(dest))


def cache_lookup(key: str):
    if not CACHE.exists():
        return None
    hit = None
    for line in CACHE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("key") == key:
            hit = row                                   # last one wins: a re-ask may supersede
    return hit


def cache_store(row: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with CACHE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def ask(image: Path, question: str, model: str, attempts: int):
    """Returns (text, error). Retries only on the transient signatures -- a bad question must fail
    immediately, not three times slowly."""
    delay = 2.0
    last = None
    for i in range(attempts):
        proc = subprocess.run([sys.executable, str(DOOR), str(image), question, "--model", model],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if out and proc.returncode == 0:
            return out, None
        last = err or out or f"exit {proc.returncode}"
        if not any(tok in last for tok in RETRYABLE):
            return None, last
        if i < attempts - 1:
            time.sleep(delay)
            delay *= 3
    return None, last


def main() -> int:
    ap = argparse.ArgumentParser(description="One targeted question about one frame.")
    ap.add_argument("image")
    ap.add_argument("question")
    ap.add_argument("--region", help="fractional crop x,y,w,h in 0..1 -- ask about the part that matters")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    src = Path(args.image)
    if not src.exists():
        print(f"NO_EYES: no such image {src}", file=sys.stderr)
        return 2

    subject = src
    tmp = None
    if args.region:
        tmp = Path(f"{src.parent}/.crop-{hashlib.sha256(args.region.encode()).hexdigest()[:8]}{src.suffix}")
        try:
            crop_to(src, args.region, tmp)
            subject = tmp
        except Exception as exc:                       # a bad region is a caller bug, loudly
            print(f"NO_EYES: could not crop {args.region}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2

    stamp = f"{sha_of(subject)[:12]}" + (f" r={args.region}" if args.region else "")
    key = hashlib.sha256(f"{stamp}|{args.model}|{args.question}".encode()).hexdigest()[:32]

    if not args.no_cache:
        hit = cache_lookup(key)
        if hit:
            text, err, cached, attempts_used = hit.get("answer"), None, True, 0
        else:
            text, err, cached, attempts_used = None, None, False, 0
    else:
        text, err, cached, attempts_used = None, None, False, 0

    if text is None:
        text, err = ask(subject, args.question, args.model, args.attempts)
        attempts_used = args.attempts if err else 1
        if text is not None and not args.no_cache:
            cache_store({"key": key, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "image": str(src),
                         "region": args.region, "sha12": stamp, "model": args.model,
                         "question": args.question, "answer": text})

    if tmp is not None:
        try:
            tmp.unlink()
        except OSError:
            pass

    if text is None:
        # The whole point: a look that did not happen must never read as "nothing there".
        print(f"NO_EYES: {err}", file=sys.stderr)
        print("Treat this as UNKNOWN. Do not record it as an absence of content.", file=sys.stderr)
        return 3

    # PROVENANCE, always: this text is a description by another model, never a first-hand sighting.
    prov = (f"[described by {args.model}, {stamp}{', cached' if cached else ''}, "
            f"q={args.question!r}] -- A DESCRIPTION, NOT AN OBSERVATION BY THIS SEAT")
    if args.json:
        print(json.dumps({"answer": text, "provenance": prov, "model": args.model,
                          "sha12": stamp, "region": args.region, "cached": cached,
                          "question": args.question}, indent=2, ensure_ascii=False))
    else:
        print(text)
        print(prov, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
