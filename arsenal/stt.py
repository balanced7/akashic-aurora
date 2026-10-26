"""Local speech-to-text with word timing, and the cadence render.

    py -m arsenal.stt <audio> <output stem>   ->  <stem>.words.json  and  <stem>.cadence.txt

The house had local speech-to-text in the voice era: a Faster-Whisper module, retired in the t342 dead-module sweep. It
came back on 2026-10-08, at Daniel's request ("I thought we had local transcription"), as faster-whisper 1.2.1 in the
main Python. The model is "small", int8 on the CPU (CTranslate2 has no AMD-GPU path on Windows). A 37 s clip took about
15 s, including the one-time model download.

The cadence render is Daniel's idea: "use the timing of the words as metadata so you can read it in the cadance it was
said in". Timing becomes layout, because a reader takes layout in at a glance and raw timestamps it has to subtract:
  - one line per breath group: a new line wherever the speaker pauses LINE_BREAK_S or more;
  - shorter pauses inside a line are marked " · ";
  - long stretches without speech get their own line with the duration;
  - every line starts with its time, so a moment can be cited and linked (&t=);
  - a short word the model stretched over a long span is marked [held Ns]: word timestamps absorb silence into the
    word, and the first real run hid a 2.2 s deadpan pause inside a spoken letter that way;
  - a word the model is unsure of (probability below UNSURE_P) carries "(?)", so the transcript states its own
    confidence. Whisper's habit of hallucinating a repeat at the end of a clip shows up as a run of (?).
  - but the probability covers only the doubts the model knows it has. The letter names that rhyme with "ee"
    (B C D E G P T V Z) differ only in a consonant a few hundredths of a second long, and a rushed one loses it: the
    first real run wrote Misha's "D" as "E" at p=0.96, and Daniel ruled it D by ear. So a line holding any of these
    letters is followed by a note asking for an ear. Five of the seven note names are among them, which makes music
    talk the worst case.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LINE_BREAK_S, DOT_S, SPAN_S, UNSURE_P = 0.6, 0.25, 2.0, 0.5
HELD_S, HELD_CHARS = 0.9, 3  # a word of at most HELD_CHARS letters lasting HELD_S or more was held, or hid a pause
EE_LETTERS = frozenset("BCDEGPTVZ")  # spoken, these differ only in a brief consonant: the probability can't vouch
EAR_NOTE = 'letters that rhyme with "ee" are easily confused; confirm by ear'


def mmss(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def token(w: dict) -> str:
    tok = w["word"]
    core = tok.strip(",.?!;:")
    if len(core) <= HELD_CHARS and w["end"] - w["start"] >= HELD_S:
        tok += f" [held {w['end'] - w['start']:.1f}s]"
    if w["p"] < UNSURE_P:
        tok += "(?)"
    return tok


def render(words: list, duration: float) -> str:
    out, line, letters, start, prev = [], [], [], None, None

    def flush():
        if line:
            out.append(f"[{mmss(start)}] " + "".join(line).strip())
        if letters:
            out.append(f"       [{', '.join(dict.fromkeys(letters))}: {EAR_NOTE}]")

    if words and words[0]["start"] >= SPAN_S:
        out.append(f"       [{words[0]['start']:.1f}s no speech]")
    for w in words:
        tok = token(w)
        if prev is None:
            start, line, letters = w["start"], [tok], []
        else:
            gap = w["start"] - prev
            if gap >= LINE_BREAK_S:
                flush()
                if gap >= SPAN_S:
                    out.append(f"       [{gap:.1f}s no speech]")
                start, line, letters = w["start"], [tok], []
            else:
                line.append((" · " if gap >= DOT_S else " ") + tok)
        if w["word"].strip(",.?!;:") in EE_LETTERS:
            letters.append(w["word"].strip(",.?!;:"))
        prev = w["end"]
    flush()
    if words and duration - words[-1]["end"] >= SPAN_S:
        out.append(f"       [{duration - words[-1]['end']:.1f}s no speech to the end]")
    return "\n".join(out)


def transcribe(audio: str, stem: str, model_size: str = "small", *, vad: bool = False) -> dict:
    """vad=True skips the stretches without speech (Silero VAD) before decoding. Off by default, as it always was:
    on game audio it is what stops the repeated-word hallucinations (large-v3-turbo, beam 5, 120 s of 17-51-11:
    "oh oh oh" in 3 of 3 runs with it off, no repeat in 4 runs with it on). On clean narration it cost nothing: the
    studio animatic's scratch voice (463 s, the stand-in for Daniel's take, small) against its locked script gave a
    word error rate of 10.8% with it on and 11.7% off, missing 4 script words against 15 (2026-10-12). That clears
    the spec's bar for flipping this default, which is Daniel's or Vandor's call; until then it stays.
    arsenal.media.words passes True."""
    from faster_whisper import WhisperModel  # imported here: the render needs no model

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio, word_timestamps=True, language="en", vad_filter=vad, beam_size=5)
    words = [
        {"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word.strip(), "p": round(w.probability, 2)}
        for seg in segments
        for w in (seg.words or [])
    ]
    meta = {
        "model": f"faster-whisper {model_size}, int8, cpu" + (", vad" if vad else ""),
        "duration_s": round(info.duration, 1),
        "audio": Path(audio).name,
    }
    Path(stem + ".words.json").write_text(
        json.dumps({**meta, "words": words}, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n"
    )
    cadence = render(words, info.duration)
    Path(stem + ".cadence.txt").write_text(cadence + "\n", encoding="utf-8", newline="\n")
    return {**meta, "words": len(words), "unsure": sum(w["p"] < UNSURE_P for w in words), "cadence": cadence}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__.split("\n\n")[0])
    r = transcribe(sys.argv[1], sys.argv[2])
    print(f"{r['model']} | {r['duration_s']} s of audio | {r['words']} words | {r['unsure']} unsure")
    print(r["cadence"])
