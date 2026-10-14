"""py -m arsenal shader explain <id|name> [--detail summary|full] [--json] -- one shader's FINDING LEDGER: everything the
house knows about it, each claim labelled by HOW it is known, pointed at the evidence that earned it, with the edge of
its search said out loud, and the things nobody has looked at listed instead of left out.

WHY. Daniel, 2026-10-13: "I want us to know how to reverse engineer anything." The tools to take a shader apart already
exist (dissect reads the code, render and filmstrip picture it, the study notes hold our own reading of it), but each
answers in its own voice, and a reader cannot tell a line the dissector matched from a guess a study note made, or a
picture of the shader from a picture of a stand-in texture. The discipline that fixes this is credited to morluto/rea
(github.com/morluto/rea, the reverse-engineer-anything skill): keep observations, inferences and unknowns apart, cite
an evidence id for each, keep a ledger with confidence and search boundary, revisit the checklist before calling it done,
and never repeat an identical analysis without a changed input. This verb is that discipline for one corpus shader.

THE LABELS (every claim carries exactly one). The rule: only a raw fact may be observed or measured; every claim that
interprets (a detector recognising a technique, a prediction, our own notes) is inferred.
    observed-in-code     a raw fact read directly from the source or the shader's own configuration (shader.json): a
                         pass and its inputs as declared, a cycle the declared inputs close, a uniform or a declared
                         channel read on the line cited (iTime, iFrame, iMouse, iChannel<n>: the ledger checks that a
                         token of LIVE code on that line holds it, so a comment, an #if branch the preprocessor drops, a
                         function no entry point reaches (and nothing in a pass with no entry point found, its own
                         helpers included), a #define that only renames it (or renames a renaming) and a function's or
                         macro's own parameter named like it (`#define WAVE(t) sin(t)` or `float wave(float t)` beside
                         `#define t iTime`) are never a read; a macro or function Common defines is live code of every
                         pass that reaches it, and a #define alias (an alias of an alias too) counts in its own pass
                         and, from Common, in every pass; when the dissector's line is not a live read, the first live
                         read is cited instead, and with none a channel's read falls back to its declaration), a
                         function present at a line (mainSound), functions no entry point reaches when the reader
                         followed every pass that could reach them
    observed-in-render   a receipt written by `render` or `filmstrip` says the page compiled, drew, walked or jumped
    measured             a number a receipt measured: mean luma of a frame, milliseconds per frame on SwiftShader
    inferred             a reading made from evidence rather than seen: every technique the dissector recognises from
                         the shape of the math (a sphere trace, a box distance, a gamma curve: its interpretation, with
                         its own number as `score`), a function NAME alone (the weakest reading, bounded "function name
                         only; shape not matched" and never counted as a technique), a read the dissector reports that
                         no line of live code holds or that sits in a pass the reader could not follow (its word alone,
                         kind read_unchecked), the dead-function list when the reader could not follow a whole pass (an
                         #if it could not evaluate, code it could not follow, no entry point found), the static cost
                         estimate of a pass with an entry point, what the media folder predicts a render will draw, and
                         the study note: every heading and its corroboration section (our earlier reading of the code
                         and of the renders, not re-checked here)
    unknown              what no evidence reaches: a pass in which the reader found no entry point (kind no_entry) and
                         its static cost (kind cost_unknown: no call graph was walked, so none is estimated),
                         inputs drawn by stand-ins, silence fed to an audio input, inputs or passes the runtime could
                         not draw, a Sound pass never run, times never rendered, the detector groups that found nothing
                         ("not detected by dissect v1": a detector's miss is never proof of absence), GPU timing

THE CONFIDENCE. Every claim carries `confidence`, one of high / moderate / low (CONFIDENCE): how sure the ledger is that
the sentence is true as written. It is confidence, not likelihood (ICD 203 keeps the two apart). A claim the dissector
fed also carries `score`, the dissector's own number, which dissect.py calls a judgement scale, not a probability; the
confidence of a recognised technique is banded from it by the dissector's own bands (confidence_band). A raw fact, a
receipt and a measurement are high; a name alone is low; an unknown is high, because what was not reached is known
exactly.

THE EVIDENCE IDS. A sha8 is the first 8 hex digits of SHA-256 over the bytes as they sit on disk.
    code     <id>@<sha8 of the pass source>:<pass>:<first line>-<last line>      (from the dissector's evidence rows)
    config   config:<id>@<sha8 of shader.json>:<pass>:pass | iChannel<n>        (the shader's own declaration; also
                                                                                 cited for a channel no line reads, and
                                                                                 alone for a channel row in a pass with
                                                                                 no entry point)
    render   render:<sha8 of the receipt file>, with the receipt's path in the claim's `paths`
    study    study:<id>@<sha8 of the note>#<section number, else a slug of the heading>   (always labelled inferred)

ROUTING FIRST. Before any claim, the ledger names what kind of artifact this is (single-pass, buffer feedback, a Sound
pass, a cubemap pass, texture inputs, audio-reactive, interactive) and the one rule that keeps a reading of that kind
honest (ROUTES below; the shader-craft skill's routing table carries the same rows, and a pin keeps them together).

THE CACHE. A ledger is keyed by every input it was made from: each pass's sha8, shader.json's sha8, meta.json's sha8
(name, author, url, the licence reading), the sha8 (or absence) of every /media/ file an input names (a cubemap is six:
the file the JSON names and its faces <hash>_1 .. _5, see media_files), each receipt's
sha8, the study note's sha8 and its corroboration section's own sha8, the dissector's version and the sha8 of its code
(dissect.py + glsl.py), the sha8 of the code that reads the rest (this file, shelf.py, corpus.py: CODE) and the
confidence floor. A repeat with the same key returns the stored ledger and says so; nothing is re-analysed. Any changed
input (a new render, a media file arriving, an edited note or meta.json, a dissector fix) makes a new ledger.

THE CHECKLIST. Every ledger ends with the questions a dissection owes (what is it made of, how is it wired, what does it
look like, how does it move, what does it cost, why was it built this way; and, where they apply, how does it sound and
how does it respond to input), each marked answered, partial or unresolved from the claims, never from hope. "Made of"
is answered only by a technique recognised from the shape of the math: a clock read, a declared input or a function
name says what the shader touches, not what it is built from, so alone they leave it partial.

WHAT IT DOES NOT DO. It renders nothing (no GPU, no browser: `render`/`filmstrip` make receipts, this reads them), and
it never picks a shader for you: a name that matches more than one shader is refused with the candidates listed.

THE LICENCE LINE. A ledger names other people's work (corpus shaders, their function names in the dissector's details,
our study notes' headings about them). It is written under state/arsenal/shaders/ledger/ (gitignored) and refused
anywhere else. Apache-2.0, our own code and words; no corpus code passes through this file.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import corpus as C
from . import dissect as D
from . import glsl as G

API = "arsenal.shader-explain/v1"
LABELS = ("observed-in-code", "observed-in-render", "measured", "inferred", "unknown")
CONFIDENCE = ("high", "moderate", "low")
HERE = Path(__file__).resolve().parent
# The code a ledger is computed by, hashed into the cache key: the dissector, and the readers this verb leans on
# (shelf.study_facts and licence_for; corpus.pass_stem and _input_row).
CODE: Dict[str, Tuple[Path, ...]] = {
    "dissect": (HERE / "dissect.py", HERE / "glsl.py"),
    "explain": (HERE / "explain.py", HERE / "shelf.py", HERE / "corpus.py"),
}
# Dissector tags that report a raw read rather than a reading: the uniform the cited line must hold in live code, or
# None for a channel the configuration declares (params.channel; a use of a literal #define alias counts, in its own
# pass and, from Common, in every pass; the #define line itself does not). A row whose line holds no live read is not
# an observation as it stands: the first live read is cited instead (in the pass files or in Common); with none, a
# channel tag cites the declaration and says no read was found, and a uniform's row is inferred, the dissector's word
# alone. When the reader found no entry point in a pass the read could sit in, "no read found" was never searched for:
# the row is inferred, and says so (a channel row whose line sits in that pass cites the declaration alone). A
# function's or macro's own parameter is never a read, whatever it is named (glsl.Fn.param_names).
RAW_READS: Dict[str, Optional[Tuple[str, ...]]] = {
    "animation.time": tuple(sorted(D.TIME_UNIFORMS)),
    "animation.frame": ("iFrame",),
    "input.mouse": ("iMouse",),
    "audio.sound_pass": ("mainSound",),
    "input.keyboard": None,
    "audio.input": None,
    "feedback.self": None,
}
DECLARED = frozenset({"feedback.cycle"})      # computed from the declared inputs and outputs alone: cited by them
NAME_ONLY_BOUNDARY = "function name only; shape not matched"
ROOT = HERE.parents[1]
STATE_ROOT = ROOT / "state"                    # gitignored; a ledger never leaves it
STATE = STATE_ROOT / "arsenal" / "shaders"
LEDGER = STATE / "ledger"
RENDERS = STATE / "renders"
STUDY = STATE / "study"
RECEIPTS = (("receipt.json", "stills"), ("filmstrip.json", "filmstrip"))
SHADERTOY_FPS = 60
MEDIA_TYPES = frozenset({"texture", "cubemap", "volume", "video", "webcam"})
SUMMARY_UNKNOWNS = 8                           # unknowns the summary lists by name; --detail full lists all
PRIVATE = ("private: this ledger names other people's work and our study notes about it; it stays under state/ "
           "(gitignored)")

# The routing table for a corpus shader: (route, the rule that keeps a reading of that kind honest). The shader-craft
# skill's table (.claude/skills/shader-craft/references/dissecting-shaders.md) has a row for each; a pin binds them.
ROUTES: Dict[str, str] = {
    "single-pass": "render jump: no pass keeps a frame, so the still at t is drawn straight from t",
    "buffer chain": "buffers that keep no frame recompute every frame from t: a jump is safe only while the receipt's "
                    "history flag says no pass keeps a frame",
    "buffer feedback": "walk from a reset, never jump: the picture at t folds in every frame before it",
    "sound pass": "compile only: the runtime builds the Sound pass and never plays it, so what it sounds like is unknown",
    "cubemap pass": "Cube A is drawn, six faces, before Image every frame: judge it through the Image that samples it, "
                    "and if it reads itself the feedback rule applies",
    "texture inputs": "check the receipt's stand-ins before judging: a medium the corpus lacks is drawn by a procedural "
                      "stand-in, not the author's picture",
    "audio-reactive": "feed an audio texture or you are judging silence: the harness feeds none, so a render shows the "
                      "shader at rest",
    "interactive": "the renders press no key and move no mouse: the picture is the shader untouched, interaction unknown",
}


class ExplainError(LookupError):
    """No shader matches, or more than one does: the message names what to give instead."""


# ------------------------------------------------------------------------------------------------------- helpers
def sha8(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:8]


def _file_sha8(paths: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        h.update(Path(p).read_bytes())
    return h.hexdigest()[:8]


def dissect_version() -> str:
    """'v1' from the dissector's API string: the version a 'not detected by dissect vN' unknown names."""
    return D.API.rsplit("/", 1)[-1]


def code_id(sid: str, sha: str, stem: str, lo: int, hi: Optional[int] = None) -> str:
    return f"{sid}@{sha}:{stem}:{int(lo)}-{int(hi if hi is not None else lo)}"


def config_id(sid: str, sha: str, stem: str, what: str) -> str:
    return f"config:{sid}@{sha}:{stem}:{what}"


def render_id(sha: str) -> str:
    return f"render:{sha}"


def study_id(sid: str, sha: str, anchor: str) -> str:
    return f"study:{sid}@{sha}#{anchor}"


def confidence_band(score: float) -> str:
    """The dissector's number onto the ledger's one scale, by the dissector's own bands (dissect.py): 0.9+ the shape is
    unmistakable -> high; 0.7-0.89 the shape with one ambiguity -> moderate; below that a weaker shape -> low."""
    return "high" if score >= 0.9 else "moderate" if score >= 0.7 else "low"


_CORROBORATION = re.compile(r"^##\s+corroboration\b", re.I)


def corroboration_section(text: str) -> Optional[Tuple[str, str]]:
    """(heading, the section's text) of a study note's `## Corroboration ...` section, or None. Fenced code is skipped
    when looking for the headings that open and close it."""
    lines, start, end, fence = text.split("\n"), None, None, False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            fence = not fence
            continue
        if fence or not line.startswith("## "):
            continue
        if start is None and _CORROBORATION.match(line):
            start = i
        elif start is not None:
            end = i
            break
    if start is None:
        return None
    return lines[start][3:].strip(), "\n".join(lines[start:end])


_NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\.?\s")


def heading_anchor(heading: str) -> str:
    """'4.1 A bead traced...' -> '4.1'; an unnumbered heading -> a short slug of its words."""
    m = _NUMBERED.match(heading.strip())
    if m:
        return m.group(1)
    slug = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
    return slug[:48].rstrip("-") or "note"


def _g(x: float) -> str:
    return f"{round(float(x), 3):g}"


def line_count(code: str) -> int:
    """The lines a reader counts: a final newline ends the last line, it does not open another. (glsl.py's size counts
    one more for a source that ends in a newline, the empty string after it; the line NUMBERS agree.)"""
    text = G.normalize_newlines(code)
    return text.count("\n") + (0 if not text or text.endswith("\n") else 1)


def media_files(src: str, typ: Optional[str]) -> List[str]:
    """The corpus file names one /media/ input stands for: its own, and for a cubemap on the site's media path the five
    further faces <hash>_1 .. _5 the shader JSON never names (the rule corpus.media_to_fetch harvests by)."""
    name = Path(src).name
    if typ == "cubemap" and C._SITE_MEDIA.match(src) and "." in name:
        stem, ext = name.rsplit(".", 1)
        return [name] + [f"{stem}_{k}.{ext}" for k in range(1, 6)]
    return [name]


def _read_json(path: Path) -> Optional[dict]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def resolve(query: str, corpus: Optional[Path] = None) -> str:
    """One corpus id for a query, or ExplainError: never a pick among several."""
    hits = C.resolve(query, corpus)
    if not hits:
        raise ExplainError(f"no corpus shader matches {query!r}; try: py -m arsenal shader list")
    if len(hits) > 1:
        names = ", ".join(f"{h} ({C.load_meta(h, corpus).get('name')!r})" for h in hits[:12])
        more = f" ... +{len(hits) - 12}" if len(hits) > 12 else ""
        raise ExplainError(f"{query!r} matches {len(hits)} shaders: {names}{more}. Name one by its id; "
                           f"explain does not choose for you")
    return hits[0]


def ledger_path(sid: str, ledger_dir: Optional[Path] = None, state_root: Optional[Path] = None) -> Path:
    """Where a ledger goes; refused (ValueError) outside state/, before any work is done."""
    out = (Path(ledger_dir) if ledger_dir is not None else LEDGER) / f"{sid}.json"
    root = Path(state_root) if state_root is not None else STATE_ROOT
    if not out.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"refused: {out} is outside {root}; a ledger names other people's work and stays under state/")
    return out


# ------------------------------------------------------------------------------------------------------- inputs
class _Inputs:
    """Everything one ledger is made from, read once, with the hashes the cache key and the evidence ids use."""

    def __init__(self, sid: str, corpus: Path, renders_dir: Path, study_dir: Path, min_conf: float):
        self.sid, self.corpus, self.min_conf = sid, corpus, min_conf
        self.dir = corpus / "shaders" / sid
        self.shader_path = self.dir / "shader.json"
        raw = self.shader_path.read_bytes()
        self.shader = json.loads(raw.decode("utf-8"))
        self.config_sha = sha8(raw)
        self.meta_path = self.dir / "meta.json"
        raw = self.meta_path.read_bytes()
        self.meta = json.loads(raw.decode("utf-8"))
        self.meta_sha = sha8(raw)
        self.passes: List[dict] = []
        for rp in self.shader.get("renderpass") or []:
            code = rp.get("code") or ""
            stem = C.pass_stem(rp.get("name"))
            self.passes.append({"name": rp.get("name") or stem, "type": rp.get("type") or "image", "stem": stem,
                                "file": stem + ".glsl", "code": code, "sha": sha8(code.encode("utf-8")),
                                "lines": line_count(code), "inputs": [C._input_row(i) for i in rp.get("inputs") or []],
                                "outputs": [o.get("id") for o in rp.get("outputs") or [] if o.get("id")],
                                "path": str(self.dir / (stem + ".glsl"))})
        self.by_file = {p["file"]: p for p in self.passes}
        # every /media/ file an input stands for (a cubemap's six faces), as the corpus holds it now: the sha8 of its
        # bytes, or None when absent
        self.media_dir = corpus / "media"
        self.media: Dict[str, Optional[str]] = {}
        for p in self.passes:
            for i in p["inputs"]:
                src = i.get("src") or ""
                if not src.startswith("/media/"):
                    continue
                for name in media_files(src, i.get("type")):
                    if name not in self.media:
                        f = self.media_dir / name
                        self.media[name] = sha8(f.read_bytes()) if f.is_file() else None
        self.renders_dir = renders_dir / sid
        self.receipts: List[dict] = []
        for name, kind in RECEIPTS:
            p = self.renders_dir / name
            if p.is_file():
                raw = p.read_bytes()
                try:
                    rec = json.loads(raw.decode("utf-8"))
                except ValueError:
                    rec = None
                self.receipts.append({"name": name, "kind": kind, "path": str(p), "sha": sha8(raw),
                                      "receipt": rec if isinstance(rec, dict) else None})
        self.study_dir = study_dir
        self.study_path = study_dir / f"{sid}.md"
        self.study_sha = self.corroboration = self.corroboration_sha = None
        if self.study_path.is_file():
            raw = self.study_path.read_bytes()
            self.study_sha = sha8(raw)
            self.corroboration = corroboration_section(raw.decode("utf-8", errors="replace"))
            if self.corroboration is not None:
                self.corroboration_sha = sha8(self.corroboration[1].encode("utf-8"))

    def cache_inputs(self) -> dict:
        """Every input the ledger is made from (see THE CACHE): any one changing changes the key."""
        return {
            "explain": f"{API}+{_file_sha8(CODE['explain'])}",
            "dissect": f"{D.API}+{_file_sha8(CODE['dissect'])}",
            "config": self.config_sha,
            "meta": self.meta_sha,
            "passes": {p["file"]: p["sha"] for p in self.passes},
            "media": dict(self.media),
            "receipts": {r["name"]: r["sha"] for r in self.receipts},
            "study": self.study_sha,
            "corroboration": self.corroboration_sha,
            "min_conf": self.min_conf,
        }


def cache_key(inputs: dict) -> str:
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------------------------------------------- the ledger
class _Book:
    def __init__(self) -> None:
        self.claims: List[dict] = []

    def add(self, label: str, claim: str, evidence: Sequence[str], boundary: str, paths: Sequence[str] = (),
            confidence: str = "high", **extra) -> str:
        assert label in LABELS, label
        assert confidence in CONFIDENCE, f"one fixed scale ({', '.join(CONFIDENCE)}), not {confidence!r}"
        evidence = list(dict.fromkeys(e for e in evidence if e))
        assert evidence, f"a claim with no evidence: {claim}"
        cid = f"C{len(self.claims) + 1:03d}"
        row = {"id": cid, "label": label, "claim": claim, "evidence": evidence, "boundary": boundary,
               "paths": list(dict.fromkeys(str(p) for p in paths)), "confidence": confidence}
        row.update({k: v for k, v in extra.items() if v is not None})
        self.claims.append(row)
        return cid

    def ids(self, label: Optional[str] = None, **match) -> List[str]:
        return [c["id"] for c in self.claims if (label is None or c["label"] == label)
                and all(c.get(k) == v for k, v in match.items())]


def _has_entry(unit: G.Unit) -> bool:
    """Whether the reader recognised an entry point in a pass: a function named like one (glsl.ENTRY_POINTS), or
    top-level code that calls one (a mainImage built by a function-like macro), and something reached from it. A pass
    that is one object-like macro Common defines (`IMAGE` on its own line) has neither: the reader follows none of its
    code, so nothing in it can be called live or dead, and no read in it can be checked."""
    return bool(unit.reachable()) and any(e in G.ENTRY_POINTS or e == G.TOPLEVEL for e in unit.entries())


def _name_only(row: dict) -> bool:
    """An evidence row the dissector earned from a function's NAME alone (sdBox, smin, opRep...), not from its math.
    Read from the row itself: its own `by`/`variant` mark when it has one, else the dissector's "named f()" detail."""
    params = row.get("params") or {}
    return (params.get("by") == "name" or params.get("variant") == "named" or row.get("tag") == "sdf.named"
            or str(row.get("detail") or "").startswith("named "))


class _Builder:
    def __init__(self, inp: _Inputs, rep: dict, view: Optional[D.ShaderView] = None):
        self.inp, self.rep, self.book = inp, rep, _Book()
        self.sid = inp.sid
        self.ver = dissect_version()
        self.floor = rep.get("min_conf", D.MIN_CONF)
        self.tags = set(rep.get("tags") or [])
        self.route: List[dict] = []
        self.owner = {o: p for p in inp.passes for o in p["outputs"]}
        self.stand_ins: Dict[str, dict] = {}
        self.render_frames: List[Tuple[dict, dict]] = []      # (receipt row, frame)
        self.jump_conflict = False
        self.view = view if view is not None else D.view_from_json(inp.shader, str(inp.shader_path))
        self._index_live_code()
        self.rows = {t["tag"]: [self.resolve_row(t["tag"], e) for e in t["evidence"]] for t in rep["techniques"]}

    def _index_live_code(self) -> None:
        """What the dissector's own reachability walk calls live, per pass, by (file, line): every token in the body of
        a function or macro an entry point reaches (Common's under each pass that prepends it), with the macro's name
        when the token sits in one, except the body's own parameters; and the head line of each live function. A token
        in an #if branch the preprocessor dropped never enters a body, so an inactive line holds no live token. A pass
        with no entry point the reader recognises reaches nothing (glsl.Unit, library=False), so none of its tokens is
        live, its own helpers included."""
        self.live: Dict[str, Dict[Tuple[str, int], set]] = {}
        self.live_heads: Dict[str, set] = {}
        self._names_seen: Dict[Tuple[Tuple[str, ...], Optional[str]], set] = {}     # _visible's cache
        # glsl.py files every token of a #define continued over several lines under the define's first line, so a
        # read there is cited by the define's whole span (first line -> last line), which is where the token really is.
        self.spans: Dict[Tuple[str, int], int] = {}
        for pv in self.view.passes:
            toks: Dict[Tuple[str, int], set] = {}
            heads = set()
            for name in pv.unit.reachable():
                for fn in pv.unit.nodes(name):
                    macro = fn.name if fn.kind == "macro" else None
                    if macro is not None and (getattr(fn, "end_line", None) or fn.line) > fn.line:
                        self.spans[(fn.file, fn.line)] = fn.end_line
                    heads.add((fn.file, fn.line, fn.name))
                    # A macro's own parameter stands for the argument it is called with, and a function's shadows what
                    # it is named like, so neither is ever a read of anything, even when it is named like a uniform or
                    # an alias (`#define WAVE(t) sin(t)`, `float wave(float t)` beside `#define t iTime`).
                    params = fn.param_names
                    for t in fn.toks[fn.start:fn.end]:
                        if t.text not in params:
                            toks.setdefault((fn.file, t.line), set()).add((t.text, macro))
            self.live[pv.file], self.live_heads[pv.file] = toks, heads
        # The passes in which the reader recognised no entry point (_has_entry): none of their code is in the live
        # index, so a read there cannot be checked and their dead-function lists are only a reading.
        self.no_entry = {pv.file for pv in self.view.passes if not _has_entry(pv.unit)}
        self.progs = {pv.file: pv.prog for pv in self.view.passes}
        if self.view.common is not None:
            self.progs[self.view.common.file] = self.view.common
        self.dead_names = {p["file"]: {d["name"] for d in p["dead"]} for p in self.rep["passes"]}
        if self.rep.get("common"):
            self.dead_names[self.rep["common"]["file"]] = {d["name"] for d in self.rep["common"]["dead"]}

    # evidence helpers ---------------------------------------------------------------------------------------
    def code(self, file: str, lo: int, hi: Optional[int] = None) -> str:
        p = self.inp.by_file.get(file)
        stem = p["stem"] if p else Path(file).stem
        sha = p["sha"] if p else "00000000"
        return code_id(self.sid, sha, stem, lo, hi)

    def _read_id(self, file: str, line: int) -> str:
        """The code id of a read on a line of live code: that line, or a continued #define's whole span (self.spans)."""
        return self.code(file, line, self.spans.get((file, line)))

    def _line(self, file: str, line: int) -> str:
        p = self.inp.by_file.get(file)
        lines = (p["code"] if p else "").split("\n")
        return lines[line - 1] if 1 <= line <= len(lines) else ""

    def _channel_names(self, ch, pass_file: Optional[str] = None) -> List[str]:
        """iChannel<ch> and every literal #define alias of it that Common, and pass_file's own pass, define."""
        return self._aliases([f"iChannel{ch}"], pass_file)

    def _aliases(self, names: Sequence[str], pass_file: Optional[str] = None) -> List[str]:
        """The names and every literal #define alias of one of them (`#define keyTex iChannel1`, `#define T iTime`)
        that Common defines (it is prepended to every pass) and, when pass_file is given, that pass's own code defines.
        Another pass's #define is never included: Buffer A's `#define T iTime` does not make Image's own `T` the clock.
        Renamings are followed through renamings (`#define KEYS Pressed` beside `#define Pressed iChannel2`). A use of
        any of these names is a read; each #define line itself only renames."""
        out = list(dict.fromkeys(names))
        codes = [p["code"] for p in self.inp.passes
                 if p["type"] == "common" or (pass_file is not None and p["file"] == pass_file)]
        while True:
            rx = re.compile(r"^\s*#\s*define\s+(\w+)\s+\(?\s*(?:" + "|".join(map(re.escape, out)) + r")\s*\)?\s*$",
                            re.M)
            more = [n for code in codes for n in rx.findall(code) if n not in out]
            if not more:
                return out
            out += list(dict.fromkeys(more))

    def _visible(self, base: Tuple[str, ...], pf: str, file: str, in_macro: bool) -> set:
        """The names a read goes by in one token of `file` reached from pass `pf`: the raw names and Common's aliases;
        the pass's own aliases too in its own file and inside a macro's body, because a macro is expanded where the
        pass uses it (a Common macro that names NOISE_CHANNEL reads whatever channel the using pass defines
        NOISE_CHANNEL as); never another pass's."""
        own = pf if (file == pf or in_macro) else None
        key = (base, own)
        if key not in self._names_seen:
            self._names_seen[key] = set(self._aliases(base, own))
        return self._names_seen[key]

    def _read_scope(self, tag: str, row: dict) -> List[str]:
        """The passes whose live code a read may sit in: for a channel, the pass the row names and the pass that
        declares the channel (iChannel1 in another pass is another input); for a uniform or mainSound, every pass."""
        if RAW_READS[tag] is None:
            own, decl = self.inp.by_file.get(row["file"]), self._declaring_pass(tag, row)
            files = [p["file"] for p in (own, decl) if p is not None and p["file"] in self.live]
            if files:
                return list(dict.fromkeys(files))
        return list(self.live)

    def _holds_read(self, tag: str, scope: Sequence[str], file: str, line: int, base: Tuple[str, ...]) -> bool:
        """The line holds a read in LIVE code: a token of one of the base names, or of an alias the code there sees
        (_visible), in the body of a function or macro an entry point reaches (not a comment, not a dropped #if branch,
        not an unreached function, not the #define that only renames it); for mainSound, the head of a live
        mainSound()."""
        for pf in scope:
            if tag == "audio.sound_pass":
                if any((file, line, n) in self.live_heads[pf] for n in self._visible(base, pf, file, False)):
                    return True
                continue
            for text, macro in self.live[pf].get((file, line), ()):
                names = self._visible(base, pf, file, macro is not None)
                if text in names and macro not in names:
                    return True
        return False

    def _live_read_lines(self, tag: str, scope: Sequence[str], file: str, base: Tuple[str, ...]) -> List[int]:
        if tag == "audio.sound_pass":
            return sorted({ln for pf in scope for f, ln, n in self.live_heads[pf]
                           if f == file and n in self._visible(base, pf, f, False)})
        return sorted({ln for pf in scope for f, ln in self.live[pf] if f == file
                       and self._holds_read(tag, [pf], f, ln, base)})

    def _why_not_read(self, file: str, line: int, base: Tuple[str, ...]) -> str:
        """Why a cited line is not a read in live code, in words a reader can check at the line."""
        names = set(self._aliases(base, file))
        prog = self.progs.get(file)
        if prog is None:
            return "a line of no pass the ledger read"
        if file in self.no_entry:
            return "a line of a pass in which the reader found no entry point"
        if line in prog.inactive_lines:
            return "a line in an #if branch the preprocessor drops"
        if any(d.line == line and name in names for name, d in prog.own_defines.items()):
            return "a #define that renames it, not a read"
        dead = self.dead_names.get(file, set())
        for fn in prog.all_functions():
            if fn.name in dead and fn.line <= line <= fn.end_line:
                return f"inside {fn.name}(), which no entry point reaches"
        return "a line that holds no read of it in live code"

    def _declaring_pass(self, tag: str, row: dict) -> Optional[dict]:
        """The pass whose configuration declares the channel a channel tag's row is about."""
        ch = (row.get("params") or {}).get("channel")
        own = self.inp.by_file.get(row["file"])

        def declares(p: dict) -> bool:
            for i in p["inputs"]:
                if i.get("channel") != ch:
                    continue
                if tag == "feedback.self":
                    return self.owner.get(i.get("id")) is p
                if tag == "audio.input":
                    return i.get("type") in D.AUDIO_TYPES
                return i.get("type") == "keyboard"
            return False
        if own is not None and declares(own):
            return own
        return next((p for p in self.inp.passes if declares(p)), None)

    def resolve_row(self, tag: str, row: dict) -> dict:
        """One dissector evidence row as the ledger cites it: {row, ids, basis, note, file, line}. basis is "read" (a
        raw read a line of LIVE code holds), "declared" (a fact of the configuration, cited by it), "unchecked" (a read
        the dissector reports that no live line holds: its word alone), "shape" (the dissector's reading of the math)
        or "name" (a function name alone). file and line are where the claim points: the row's own, or, when the row's
        line is no read in live code (an unreached function, a dropped #if branch, a renaming #define), the first line
        of live code that is. at is "config" when an unchecked channel row cites the declaration alone (its line sits
        in a pass in which the reader found no entry point)."""
        out = {"row": row, "ids": [self.code(row["file"], row["line"])], "basis": "shape", "note": "",
               "file": row["file"], "line": row["line"]}
        if tag in DECLARED:
            members = set((row.get("params") or {}).get("passes") or [])
            ids = [self.cfg(p, f"iChannel{i.get('channel')}") for p in self.inp.passes if p["file"] in members
                   for i in p["inputs"] if (self.owner.get(i.get("id")) or {}).get("file") in members]
            if ids:
                out.update(ids=ids, basis="declared")
            return out
        if tag in RAW_READS:
            return self._resolve_read(tag, row, out)
        if _name_only(row):
            out["basis"] = "name"
        return out

    def _resolve_read(self, tag: str, row: dict, out: dict) -> dict:
        ch = (row.get("params") or {}).get("channel")
        # The raw names; the aliases a read may also go by depend on where the token sits (_visible).
        base = tuple(RAW_READS[tag]) if RAW_READS[tag] is not None else (f"iChannel{ch}",)
        scope = self._read_scope(tag, row)
        decl = self._declaring_pass(tag, row) if RAW_READS[tag] is None else None
        cfg = [self.cfg(decl, f"iChannel{ch}")] if decl is not None else []
        file, line = row["file"], row["line"]
        if self._holds_read(tag, scope, file, line, base):
            out.update(basis="read", ids=cfg + [self._read_id(file, line)])
            return out
        why = f"dissect {self.ver} cited {file}:{line}, {self._why_not_read(file, line, base)}"
        # Every file the scope passes' live code sits in: the row's own, the passes', then any other the live index
        # keys, which is Common (prepended to each pass, so a macro or function it defines that a pass reaches is
        # that pass's live code, and a read inside it is a read).
        files = [file] + list(scope) + sorted({f for pf in scope for f, _ in self.live[pf]})
        for f in dict.fromkeys(files):
            found = self._live_read_lines(tag, scope, f, base)
            if found:
                out.update(basis="read", file=f, line=found[0], ids=cfg + [self._read_id(f, found[0])], note=why)
                return out
        blind = sorted(f for f in scope if f in self.no_entry)
        if blind:
            # The reader followed none of these passes' code, so "no read found" would be a negative over a search that
            # never ran: the dissector's word stands alone (inferred), and the gap is said. A channel row whose own line
            # sits in such a pass points at a line the dissector never read either (with no live token there it falls
            # back to the pass's line 1): the row cites the configuration that declares the channel, and nothing else.
            at_config = bool(cfg) and file in self.no_entry
            gap = (f"the reader found no entry point in {', '.join(blind)}, so none of its code was followed as live "
                   f"and whether it reads it there is unknown")
            out.update(ids=cfg if at_config else cfg + out["ids"], basis="unchecked",
                       at="config" if at_config else None, note=gap if at_config else f"{gap} ({why})")
            return out
        if decl is not None:
            out.update(ids=cfg, basis="declared", note=f"no read found in the live code of {decl['file']} ({why})")
            return out
        out.update(basis="unchecked", note=f"no line of live code holds the read ({why})")
        return out

    def row_text(self, tag: str, r: dict) -> str:
        """One raw row in plain words: what the cited line holds, or what the configuration declares."""
        e = r["row"]
        ch = (e.get("params") or {}).get("channel")
        if r["basis"] == "declared":
            if tag in DECLARED:
                return f"{e['detail']} (the declared inputs and outputs)"
            if tag == "feedback.self":
                p = self._declaring_pass(tag, e)
                return (f"{p['name'] if p else e['file']}'s configuration wires its own output back in on iChannel{ch}; "
                        f"{r['note']}")
            return f"{e['detail']}: declared in configuration; {r['note']}"
        note = f"; {r['note']}" if r["note"] else ""
        if tag == "audio.sound_pass":
            return f"mainSound() defined at {r['file']}:{r['line']}" + (f" ({r['note']})" if r["note"] else "")
        return f"{e['detail']} (first at {r['file']}:{r['line']}{note})"

    def where(self, r: dict) -> str:
        e = r["row"]
        if r["basis"] == "declared" or r.get("at") == "config":
            ch = (e.get("params") or {}).get("channel")
            return "in the configuration" + (f" (iChannel{ch})" if ch is not None else "")
        return f"at {r['file']}:{r['line']}"

    def tag_evidence(self, tags: Iterable[str]) -> List[str]:
        tags = set(tags)
        return [i for tag, rows in self.rows.items() if tag in tags for r in rows for i in r["ids"]]

    def whole(self, p: dict) -> str:
        return code_id(self.sid, p["sha"], p["stem"], 1, max(p["lines"], 1))

    def cfg(self, p: dict, what: str = "pass") -> str:
        return config_id(self.sid, self.inp.config_sha, p["stem"], what)

    def pass_paths(self, files: Iterable[str] = ()) -> List[str]:
        files = list(files)
        return [p["path"] for p in self.inp.passes if not files or p["file"] in files]

    # 1. the configuration: passes and inputs, read from the shader's own declaration ---------------------------
    def configuration(self) -> None:
        boundary = "the shader's own configuration (shader.json renderpass) and the pass source"
        for p in self.inp.passes:
            article = "an" if p["type"][:1] in "aeiou" else "a"
            self.book.add("observed-in-code", f"{p['name']} is {article} {p['type']} pass of {p['lines']} lines ({p['file']})",
                          [self.cfg(p), self.whole(p)], boundary, [self.inp.shader_path, p["path"]], "high",
                          kind="config")
            for inp in p["inputs"]:
                ch, typ, src = inp.get("channel"), inp.get("type") or "?", inp.get("src") or ""
                text = f"{p['name']} reads iChannel{ch} as {typ}"
                src_pass = self.owner.get(inp.get("id")) if typ in ("buffer", "cubemap") else None
                if src_pass is not None:
                    text += (" -- its own previous frame" if src_pass is p else f" -- the output of {src_pass['name']}")
                elif src:
                    text += f" ({Path(src).name})"
                self.book.add("observed-in-code", text, [self.cfg(p, f"iChannel{ch}")], boundary,
                              [self.inp.shader_path], "high", kind="config")
                if src_pass is None and typ in MEDIA_TYPES and src.startswith("/media/"):
                    self.media_claim(p, ch, typ, src)

    def media_claim(self, p: dict, ch, typ: str, src: str) -> None:
        """What the media folder predicts a render will draw for one input: a prediction, so inferred. A cubemap is
        six files (media_files): the author's cubemap is predicted only when the corpus holds every face."""
        names = media_files(src, typ)
        name = names[0]
        held = [n for n in names if self.inp.media.get(n) is not None]
        head = f"{p['name']} iChannel{ch} ({typ} {name})"
        if len(names) > 1 and held and len(held) < len(names):
            missing = ", ".join(str(k) for k, n in enumerate(names) if self.inp.media.get(n) is None)
            text = (f"{head}: the corpus holds {len(held)} of its {len(names)} faces (missing face(s) {missing}), so "
                    f"a render may draw a stand-in, not the author's {typ}")
        elif not held:
            text = (f"{head}: the corpus does not hold " + (f"any of its {len(names)} faces" if len(names) > 1 else
                                                            "this file")
                    + f", so a render would draw a stand-in, not the author's {typ}")
        else:
            shas = ", ".join(self.inp.media[n] for n in names)
            text = (f"{head}: the corpus holds " + (f"all {len(names)} faces" if len(names) > 1 else "this file")
                    + f" (sha8 {shas}), so a render can feed the author's {typ} rather than a stand-in")
        self.book.add("inferred", text, [self.cfg(p, f"iChannel{ch}")],
                      f"a prediction from {self.inp.media_dir} as it stands; the receipts' `substituted` lists say what a "
                      f"render actually drew", [self.inp.shader_path] + [self.inp.media_dir / n for n in names],
                      "moderate", kind="media")

    # 2. the route, before any reading of the pictures ------------------------------------------------------------
    def routes(self) -> None:
        P = self.inp.passes
        drawn = [p for p in P if p["type"] not in ("common", "sound")]
        buffers = [p for p in P if p["type"] == "buffer"]
        cubes = [p for p in P if p["type"] == "cubemap"]
        sounds = [p for p in P if p["type"] == "sound"]
        feedback = sorted(t for t in self.tags if t.startswith("feedback."))
        media = [(p, i) for p in P for i in p["inputs"]
                 if i.get("type") in MEDIA_TYPES and not (i.get("type") == "cubemap" and i.get("id") in self.owner)]
        audio = [(p, i) for p in P for i in p["inputs"] if i.get("type") in D.AUDIO_TYPES]

        def add(name: str, evidence: List[str], why: str) -> None:
            self.route.append({"route": name, "rule": ROUTES[name], "why": why,
                               "evidence": list(dict.fromkeys(evidence))})

        if not buffers and not cubes:
            add("single-pass", [self.cfg(p) for p in drawn] or [self.cfg(P[0])],
                f"{len(drawn)} drawn pass(es), no buffer or cubemap pass")
        if feedback:
            add("buffer feedback", self.tag_evidence(feedback), f"dissect {self.ver} found {', '.join(feedback)}")
        elif buffers:
            add("buffer chain", [self.cfg(p) for p in buffers],
                f"{len(buffers)} buffer pass(es); no feedback detected by dissect {self.ver}")
        if cubes:
            add("cubemap pass", [self.cfg(p) for p in cubes], f"{len(cubes)} cubemap pass(es)")
        if sounds:
            add("sound pass", [self.cfg(p) for p in sounds], f"{len(sounds)} Sound pass(es)")
        if media:
            add("texture inputs", [self.cfg(p, f"iChannel{i.get('channel')}") for p, i in media],
                f"{len(media)} media input(s): " + ", ".join(sorted({i.get('type') for _, i in media})))
        if audio or "audio.input" in self.tags:
            ev = [self.cfg(p, f"iChannel{i.get('channel')}") for p, i in audio]
            ev += self.tag_evidence(["audio.input"])
            if "audio.input" in self.tags:
                why = f"dissect {self.ver} found audio.input" + (" on a declared audio input" if audio else "")
            else:
                why = (f"an audio input is declared, but dissect {self.ver} found no line that reads it, so the picture "
                       f"may not depend on it")
            add("audio-reactive", ev, why)
        inter = sorted(self.tags & {"input.mouse", "input.keyboard"})
        if inter:
            add("interactive", self.tag_evidence(inter), f"dissect {self.ver} found {', '.join(inter)}")

    # 3. what the code says outright, and what the dissector reads into it ----------------------------------------
    def code_claims(self) -> None:
        rep, floor = self.rep, self.floor
        files = ", ".join(p["file"] for p in self.inp.passes)
        searched = (f"dissect {self.ver}: the live functions of {files} (Common prepended as the compiler does); dead "
                    f"code is not searched")
        named_groups: Dict[str, List[str]] = {}
        for t in rep["techniques"]:
            tag, rows = t["tag"], self.rows[t["tag"]]
            score = float(t["conf"])
            paths = self.pass_paths({r["file"] for r in rows})       # where each row points (a re-cited read moves)
            raw = [r for r in rows if r["basis"] in ("read", "declared")]
            shape = [r for r in rows if r["basis"] == "shape"]
            named = [r for r in rows if r["basis"] == "name"]
            unchecked = [r for r in rows if r["basis"] == "unchecked"]
            raw_ok = [r for r in raw if r["row"]["conf"] >= floor]
            shape_ok = [r for r in shape if r["row"]["conf"] >= floor]
            named_ok = [r for r in named if r["row"]["conf"] >= floor]
            unchecked_ok = [r for r in unchecked if r["row"]["conf"] >= floor]
            if raw_ok:                       # a raw fact: live code holds the read, or the configuration declares it
                parts = [self.row_text(tag, r) for r in raw_ok[:4]]
                more = f"; +{len(raw_ok) - 4} more" if len(raw_ok) > 4 else ""
                read = any(r["basis"] == "read" for r in raw_ok)
                self.book.add("observed-in-code", f"{tag}: " + "; ".join(parts) + more,
                              [i for r in raw_ok for i in r["ids"]],
                              (searched + "; each read checked on the line cited: a token of live code, not a "
                                          "comment, a dropped #if branch, an unreached function or a renaming "
                                          "#define") if read else
                              "the shader's own configuration (shader.json inputs and outputs)",
                              paths, "high", tag=tag, kind="read" if read else "declared", score=score)
            elif unchecked_ok:               # a read the dissector reports that no live line holds: its word alone
                best = max(float(r["row"]["conf"]) for r in unchecked_ok)
                first = unchecked_ok[0]
                self.book.add("inferred",
                              f"{tag}: {D.TAGS.get(tag, '')}, reported by dissect {self.ver}, but {first['note']}",
                              [i for r in unchecked_ok for i in r["ids"]],
                              searched + "; each read checked against the live code, and none holds this one" + (
                                  "; a pass it could sit in was never followed (no entry point found)"
                                  if any("no entry point" in r["note"] for r in unchecked_ok) else ""),
                              paths, "low", tag=tag, kind="read_unchecked", score=best)
            elif shape_ok:                   # the dissector's reading of the math: an interpretation, so inferred
                best = max(float(r["row"]["conf"]) for r in shape_ok)
                first = shape_ok[0]["row"]
                note = f"; the cited line does not hold the read dissect {self.ver} names" if any(
                    r["note"] for r in shape_ok) else ""
                also = f"; {len(named)} more by function name only" if named else ""
                self.book.add("inferred",
                              f"{tag}: {D.TAGS.get(tag, '')} (x{len(shape_ok)}; first at {first['file']}:{first['line']}: "
                              f"{first['detail']}{also}{note})",
                              [i for r in shape_ok for i in r["ids"]],
                              searched + f"; the dissector recognised the shape of the math (its score {best:g}, a "
                                         f"judgement scale, not a probability)",
                              paths, confidence_band(best), tag=tag, kind="technique", score=best)
            elif named_ok:                   # a name and nothing else: the weakest reading there is
                best = max(float(r["row"]["conf"]) for r in named_ok)
                names = ", ".join(f"{re.sub(r'^named ', '', r['row']['detail'])} at {r['row']['file']}:{r['row']['line']}"
                                  for r in named_ok[:4])
                cid = self.book.add("inferred",
                                    f"{tag}: suggested by a function name only: {names} (x{len(named_ok)}); no shape "
                                    f"dissect {self.ver} knows for {tag} was matched in its math",
                                    [i for r in named_ok for i in r["ids"]],
                                    f"{NAME_ONLY_BOUNDARY}; {searched}", paths, "low", tag=tag, kind="name_only",
                                    score=best)
                named_groups.setdefault(tag.split(".")[0], []).append(cid)
            else:
                self.book.add("unknown",
                              f"{tag} below the floor (score {score:.2f} < {floor}) {self.where(rows[0])}: a weaker "
                              f"reading, not counted and not ruled out"
                              + (f" ({rows[0]['row']['detail']}; {rows[0]['note']})" if rows[0]["note"] else ""),
                              [i for r in rows for i in r["ids"]], searched, paths, "high", tag=tag,
                              kind="below_floor", score=score)
        self.dead_claims()
        for p in rep["passes"]:
            if p["file"] in self.no_entry:
                self.book.add("unknown",
                              f"{p['file']}: the reader found no entry point in this pass (no function named "
                              f"{', '.join(G.ENTRY_POINTS)}, and no top-level code that calls one), so none of its "
                              f"code was followed as live: which functions it reaches and what it reads are unknown "
                              f"from the code", [self.whole(self.inp.by_file[p["file"]])],
                              "glsl.py's reader: an entry point is a function it finds by name, or top-level code that "
                              "calls one; a pass written as one object-like macro (a bare name, no call) is not "
                              "followed", self.pass_paths([p["file"]]), "high", kind="no_entry")
            if p["unsure_ifs"]:
                self.book.add("unknown",
                              f"{p['file']}: #if at line(s) {p['unsure_ifs']} could not be evaluated; the first branch "
                              f"was read, the others never were", [self.code(p["file"], ln) for ln in p["unsure_ifs"]],
                              "glsl.py's preprocessor: literal #define values only", self.pass_paths([p["file"]]),
                              "high")
            for problem in p["problems"]:
                self.book.add("unknown", f"{p['file']}: the reader could not follow part of the code: {problem}",
                              [self.code(p["file"], 1, max(self.inp.by_file.get(p["file"], {}).get("lines", 1), 1))],
                              "glsl.py's reader", self.pass_paths([p["file"]]), "high")
        # the detector groups that found nothing by the math: a bounded negative, said as one. A group only a function
        # name points at is still not detected; the name-only claim is named beside it.
        found = {c["tag"].split(".")[0] for c in self.book.claims
                 if c.get("tag") and c.get("kind") in ("read", "declared", "technique", "read_unchecked")}
        searched_ids = [self.whole(p) for p in self.inp.passes]
        for group, label in D.GROUPS.items():
            if group in found:
                continue
            shapes = [t for t in D.TAGS if t.split(".")[0] == group]
            hint = (f"; only a function name suggests it ({', '.join(named_groups[group])}), which is not a detection"
                    if group in named_groups else "")
            blind = (f"; the reader found no entry point in {', '.join(sorted(self.no_entry))}, so no live function "
                     f"of those passes was searched" if self.no_entry else "")
            self.book.add("unknown", f"{label} ({group}.*): not detected by dissect {self.ver}{hint}", searched_ids,
                          f"searched for {len(shapes)} shape(s) ({', '.join(shapes)}) in the live functions of every "
                          f"pass; a technique written in a shape the detector does not know, or only in dead code, is "
                          f"not seen{blind}", self.pass_paths(), "high", kind="not_detected", group=group)

    def dead_claims(self) -> None:
        """Functions nothing reaches: a fact of the call graph when the reader followed the whole pass; when it could
        not (an #if it could not evaluate, code it could not follow, no entry point found in the pass), the same list is
        only a reading. Common's list is a fact only when the reader followed every pass."""
        rep = self.rep
        unsure = {p["file"] for p in rep["passes"] if p["unsure_ifs"] or p["problems"]} | self.no_entry
        reach = "glsl.py's call graph from the pass's entry point"
        gap = ("the reader did not follow every line of {what} (an #if it could not evaluate, code it could not "
               "follow, or no entry point found: see the unknowns), so a call may have been missed")
        for p in rep["passes"]:
            if p["dead"]:
                names = ", ".join(f"{d['name']}() line {d['line']}" for d in p["dead"][:12])
                sure = p["file"] not in unsure
                self.book.add("observed-in-code" if sure else "inferred",
                              f"{p['file']}: {len(p['dead'])} function(s) no entry point reaches: {names}",
                              [self.code(p["file"], d["line"]) for d in p["dead"]],
                              reach if sure else f"{reach}; {gap.format(what='this pass')}",
                              self.pass_paths([p["file"]]), "high" if sure else "moderate", kind="dead")
        common = rep.get("common")
        if common and common.get("dead"):
            names = ", ".join(f"{d['name']}() line {d['line']}" for d in common["dead"][:12])
            sure = not unsure
            self.book.add("observed-in-code" if sure else "inferred",
                          f"{common['file']}: {len(common['dead'])} function(s) no pass reaches: {names}",
                          [self.code(common["file"], d["line"]) for d in common["dead"]],
                          "the call graphs of every pass that prepends Common" + (
                              "" if sure else f"; {gap.format(what=', '.join(sorted(unsure)))}"),
                          self.pass_paths([common["file"]]), "high" if sure else "moderate", kind="dead")

    # 4. the static cost: an inference from the code -------------------------------------------------------------
    def cost_claims(self) -> None:
        for p in self.rep["passes"]:
            c = p["cost"]
            src = self.inp.by_file.get(p["file"])
            if p["file"] in self.no_entry:
                # The estimate walks the call graph from an entry point; with none found nothing was walked, and the
                # dissector's "heaviest path 1, ~0 calls" is the empty walk, not a cheap pass.
                self.book.add("unknown",
                              f"{p['file']}: static cost unknown: the reader found no entry point in this pass, so no "
                              f"call graph was walked and no per-pixel cost was estimated",
                              [self.whole(src)] if src is not None else [self.code(p["file"], 1)],
                              "glsl.py's reader: the static cost walks the call graph down from an entry point (a "
                              "function it finds by name, or top-level code that calls one); this pass has none it "
                              "could follow", self.pass_paths([p["file"]]), "high", kind="cost_unknown")
                continue
            steps = [s for s in c.get("path") or [] if s.get("file") and s.get("line")]
            ev = [self.code(s["file"], s["line"]) for s in steps]
            if not ev and src is not None:
                ev = [self.whole(src)]
            if not ev:
                continue
            self.book.add("inferred",
                          f"{p['file']}: static cost estimate, heaviest path {c['heaviest']:,} = {c['text']}; "
                          f"~{c['calls_per_pixel']:,} user calls and ~{c['work']:,} tokens executed per pixel",
                          ev, f"static: literal loop bounds along the call graph from {c.get('entry') or 'the entry'}; "
                              f"a loop with no literal bound counts 1 in the heaviest path and {D.ASSUMED_TRIPS} trips in "
                              f"the work; nothing was timed", self.pass_paths([p["file"]]),
                          "low" if c.get("unknown_loops") else "moderate", kind="cost")
            if c.get("unknown_loops"):
                self.book.add("unknown",
                              f"{p['file']}: {c['unknown_loops']} loop(s) with no literal bound; their trip counts are "
                              f"unknown, so the cost estimate guesses them", [self.whole(src)] if src is not None else ev,
                              "glsl.py's loop reader: literal bounds and bounds bound at call sites",
                              self.pass_paths([p["file"]]))

    # 5. the receipts: what the renders saw and measured ---------------------------------------------------------
    def _locate(self, src: str) -> str:
        for p in self.inp.passes:
            for i in p["inputs"]:
                s = i.get("src") or ""
                if s and (s == src or Path(src).name.startswith(Path(s).stem)):
                    return f"{p['name']} iChannel{i.get('channel')}"
        return "an input"

    def render_claims(self) -> None:
        feedback = any(t.startswith("feedback.") for t in self.tags)
        for r in self.inp.receipts:
            rec, rid, path = r["receipt"], render_id(r["sha"]), r["path"]
            if rec is None:
                self.book.add("unknown", f"the {r['kind']} receipt does not parse as JSON; what it saw is unknown", [rid],
                              f"{path}", [path])
                continue
            req = rec.get("request") or {}
            size = f"{req.get('w', '?')}x{req.get('h', '?')}"
            fps = req.get("fps")
            ts = ", ".join(_g(t) for t in req.get("t") or [])
            boundary = (f"the {r['kind']} receipt: SwiftShader (the CPU) at {size}, {fps} fps steps, t = {ts}; "
                        f"written by `shader {'render' if r['kind'] == 'stills' else 'filmstrip'}`")
            comp = rec.get("compile") or {}
            passes = comp.get("passes") or []
            if passes:
                ok = [p for p in passes if p.get("ok")]
                bad = [p for p in passes if not p.get("ok")]
                text = (f"{len(ok)}/{len(passes)} pass(es) compiled (" +
                        ", ".join(f"{p.get('name')} parity {p.get('parity') or '?'}" for p in passes) + ")")
                if bad:
                    text += "; first error: " + str(bad[0].get("firstError") or bad[0].get("mappedLog") or "?")[:200]
                self.book.add("observed-in-render", text, [rid], boundary, [path], "high", kind="compile")
            if not rec.get("ok"):
                self.book.add("observed-in-render",
                              f"the {r['kind']} render did not finish ok: {rec.get('status')}: "
                              f"{(rec.get('first_error') or 'no first error recorded')[:200]}", [rid], boundary, [path],
                              "high", kind="render_failed")
            frames = [f for f in rec.get("frames") or [] if f.get("png")]
            if frames:
                flat = [f for f in frames if f.get("flat")]
                walked = [f for f in frames if f.get("reset") and not f.get("jumped")]
                jumped = [f for f in frames if f.get("jumped")]
                how = []
                if jumped:
                    how.append(f"jumped to t = {', '.join(_g(f['t']) for f in jumped)}")
                if walked:
                    how.append(f"walked from a reset to t = {', '.join(_g(f['t']) for f in walked)} "
                               f"({sum(int(f.get('frames_walked') or 0) for f in walked)} frames drawn)")
                hist = rec.get("history")
                text = (f"drew {len(frames)} frame(s) at t = {', '.join(_g(f['t']) for f in frames)}: "
                        f"{len(frames) - len(flat)} not flat, {len(flat)} one flat colour"
                        + (f"; {'; '.join(how)}" if how else "")
                        + ("" if hist is None else f"; the page judged history {'present' if hist else 'none'}"))
                self.book.add("observed-in-render", text, [rid], boundary, [path], "high", kind="frames")
                self.render_frames += [(r, f) for f in frames]
                lum = [f for f in frames if isinstance(f.get("mean_luma"), (int, float))]
                if lum:
                    self.book.add("measured", "mean luma (0-255): " +
                                  ", ".join(f"t={_g(f['t'])} {f['mean_luma']:g}" for f in lum), [rid],
                                  boundary + "; PIL's mean over each PNG's luma, one number per frame, not a look",
                                  [path], kind="luma")
                warm = (rec.get("timings") or {}).get("warm_ms")
                ms = [f.get("ms") for f in frames if isinstance(f.get("ms"), (int, float))]
                if isinstance(warm, (int, float)) or ms:
                    text = "SwiftShader frame time at " + size + ": "
                    text += (f"{warm:g} ms per frame warm" if isinstance(warm, (int, float)) else "no warm frame timed")
                    if ms:
                        text += (f"; {', '.join(f'{m:g}' for m in ms)} ms per still (each includes the walk to its t, "
                                 f"and the first the compile)")
                    self.book.add("measured", text, [rid],
                                  boundary + "; SwiftShader timing never stands for GPU timing: it ranks shaders against "
                                             "each other on the CPU, nothing more", [path], kind="timing")
                if feedback and jumped:
                    self.jump_conflict = True
                    self.book.add("unknown",
                                  f"the code keeps a frame (feedback, dissect {self.ver}) but this render reached "
                                  f"t = {', '.join(_g(f['t']) for f in jumped)} by a jump: those stills may not be the "
                                  f"author's picture; re-render walking from a reset", [rid] + self.route_evidence("buffer feedback"),
                                  boundary, [path], kind="jump_conflict")
            if fps is not None and fps != SHADERTOY_FPS:
                self.book.add("unknown", f"rendered in {fps} fps steps, not Shadertoy's {SHADERTOY_FPS}: motion counted "
                                         f"in frames may differ from the author's", [rid], boundary, [path])
            for s in rec.get("substituted") or []:
                if isinstance(s, dict) and s.get("src"):
                    row = self.stand_ins.setdefault(s["src"], {"s": s, "ids": [], "paths": []})
                    row["ids"].append(rid)
                    row["paths"].append(path)
            for u in rec.get("unsupported") or []:
                if isinstance(u, dict) and not (u.get("what") == "sound playback"):
                    self.book.add("unknown", f"the runtime does not support {u.get('what')} {u.get('name') or ''}: "
                                             f"{u.get('reason') or ''}: what the author meant there was not drawn".strip(),
                                  [rid], boundary + "; the receipt's `unsupported` list (the runtime's own report)",
                                  [path], kind="unsupported")
        for src, row in self.stand_ins.items():
            s, where, name = row["s"], self._locate(src), Path(src).name
            if s.get("kind") == "audio":
                text = (f"{where}: audio {name} was fed silence ({s.get('reason') or 'no audio fed'}): every picture "
                        f"shows the shader at rest, never under sound")
            else:
                text = (f"{where}: {s.get('kind') or 'input'} {name} was drawn by a stand-in "
                        f"({s.get('reason') or 'stand-in'}{', style ' + s['style'] if s.get('style') else ''}): the "
                        f"picture is not the author's for that input")
            self.book.add("unknown", text, row["ids"], "the receipts' `substituted` lists (the runtime's own report)",
                          row["paths"], kind="stand_in")

    def route_evidence(self, name: str) -> List[str]:
        return next((r["evidence"] for r in self.route if r["route"] == name), [])

    # 6. what no evidence reaches -----------------------------------------------------------------------------------
    def unknown_claims(self) -> None:
        receipts = [r for r in self.inp.receipts if r["receipt"]]
        rids = [render_id(r["sha"]) for r in self.inp.receipts]
        rpaths = [r["path"] for r in self.inp.receipts]
        drawn = [p for p in self.inp.passes if p["type"] not in ("common", "sound")] or self.inp.passes[:1]
        for p in [p for p in self.inp.passes if p["type"] == "sound"]:
            said = [render_id(r["sha"]) for r in receipts
                    if any(isinstance(u, dict) and u.get("what") == "sound playback" for u in r["receipt"].get("unsupported") or [])]
            self.book.add("unknown", f"the Sound pass ({p['file']}) was never executed or heard: the runtime compiles it "
                                     f"and never plays it", [self.cfg(p)] + said,
                          "the shader's configuration and the runtime's own unsupported list", [p["path"]] + rpaths,
                          kind="sound_pass")
        times = sorted({round(float(f["t"]), 3) for _, f in self.render_frames})
        boundary = f"the frames the receipts in {self.inp.renders_dir} name (receipt.json, filmstrip.json)"
        clockless = not (self.tags & {"animation.time", "animation.frame"}) and not any(
            t.startswith("feedback.") for t in self.tags)
        note = (f"; dissect {self.ver} detected no clock (iTime, iDate, iFrame) and no feedback, so time may not "
                f"matter, but that is not ruled out") if clockless else ""
        if not times:
            self.book.add("unknown", f"never rendered: no receipt in renders/{self.sid}/ holds a frame, so how it looks "
                                     f"and moves is unknown{note}", [self.cfg(p) for p in drawn] + rids,
                          boundary, rpaths, kind="time")
        else:
            gaps = [(b - a, a, b) for a, b in zip(times, times[1:])]
            text = f"t > {_g(times[-1])} never rendered"
            if times[0] > 0:
                text += f"; t < {_g(times[0])} never pictured"
            if gaps:
                g, a, b = max(gaps)
                text += (f"; between the rendered times (t = {', '.join(_g(t) for t in times)}) never pictured, widest "
                         f"gap {_g(g)} s ({_g(a)} to {_g(b)})")
            if times[0] > 0 or gaps:
                text += " (a walk from a reset may draw through those frames, but keeps none)"
            self.book.add("unknown", text + note, rids, boundary, rpaths, kind="time")
        self.book.add("unknown", "GPU timing: never measured here; every timing in this ledger is SwiftShader's (the CPU), "
                                 "and SwiftShader timing never stands for GPU timing",
                      rids or [self.cfg(p) for p in drawn], "the house renders on SwiftShader under the GPU lock; a GPU "
                                                            "timing is Daniel's call (GPU-LOCK.md)", rpaths, kind="gpu")
        inter = sorted(self.tags & {"input.mouse", "input.keyboard"})
        if inter:
            self.book.add("unknown", f"{' and '.join(t.split('.')[1] for t in inter)} read in the code (dissect "
                                     f"{self.ver}); no receipt presses a key or moves the mouse, so interaction was "
                                     f"never rendered", self.route_evidence("interactive"),
                          "the receipts record no input events", rpaths + self.pass_paths(), kind="interaction")

    # 7. the study note: our earlier reading, always inferred ----------------------------------------------------
    def study_claims(self) -> None:
        from . import shelf as SH
        facts = SH.study_facts(self.sid, self.inp.study_dir)
        if facts.get("missing"):
            drawn = [p for p in self.inp.passes if p["type"] not in ("common", "sound")] or self.inp.passes[:1]
            self.book.add("unknown", "no study note: why it was built this way has not been read",
                          [self.cfg(p) for p in drawn], f"looked for {self.inp.study_path}", [], kind="study_missing")
            return
        sha = self.inp.study_sha or "00000000"
        path = facts.get("path") or str(self.inp.study_path)
        heads = [h for h in facts.get("techniques") or facts.get("headings") or [] if not _CORROBORATION.match("## " + h)]
        for h in heads:
            self.book.add("inferred", re.sub(r"\s+", " ", h.replace("`", "")).strip(),
                          [study_id(self.sid, sha, heading_anchor(h))],
                          "a heading of the private study note: our earlier reading of the code, not re-verified by "
                          "this verb", [path], "moderate", kind="study")
        if self.inp.corroboration is not None:
            heading, text = self.inp.corroboration
            tally = [re.sub(r"\s+", " ", m).strip().rstrip(".") for m in re.findall(r"^\*\*([^*\n]+)\*\*", text, re.M)
                     if re.search(r"\d", m)]
            self.book.add("inferred",
                          f"the study note's {heading} section: " + ("; ".join(tally) if tally else "no tally given"),
                          [study_id(self.sid, sha, heading_anchor(heading))],
                          "the study note's own corroboration section: an earlier check of the note against renders; "
                          "its readings of the pictures are cited here, not re-measured or re-run by this verb",
                          [path], "moderate", kind="corroboration")

    # 8. the checklist, revisited from the claims ----------------------------------------------------------------
    def checklist(self) -> List[dict]:
        b = self.book
        out = []

        def q(key, question, status, because, ids):
            out.append({"key": key, "question": question, "status": status, "because": because, "claims": ids})

        read = [c["id"] for c in b.claims if c.get("kind") in ("read", "declared")]
        shape = [c["id"] for c in b.claims if c.get("kind") == "technique"]
        named = [c["id"] for c in b.claims if c.get("kind") == "name_only"]
        weak = [c["id"] for c in b.claims if c.get("kind") == "below_floor"]
        unchecked = [c["id"] for c in b.claims if c.get("kind") == "read_unchecked"]
        # Made of is answered by a technique recognised from the shape of the math and by nothing less: a clock read,
        # a declared input or a function name says what the shader touches, not what it is built from.
        if shape:
            q("made_of", "What is it made of?", "answered",
              f"{len(shape)} technique(s) inferred by dissect {self.ver} from the shape of the math"
              + (f", beside {len(read)} read or declared outright" if read else "")
              + "; reads, declarations and function names alone never answer it", shape + read)
        elif read or named or weak or unchecked:
            parts = (([f"{len(read)} read or declared outright"] if read else [])
                     + ([f"{len(unchecked)} read reported by dissect {self.ver} that no live line holds"] if unchecked
                        else [])
                     + ([f"{len(named)} suggested by a function name only"] if named else [])
                     + ([f"{len(weak)} reading(s) below the confidence floor"] if weak else []))
            q("made_of", "What is it made of?", "partial",
              f"no technique recognised from the shape of the math by dissect {self.ver}; only " + ", ".join(parts),
              read + unchecked + named + weak)
        else:
            q("made_of", "What is it made of?", "unresolved", f"dissect {self.ver} detected no technique", [])
        cfg = [c["id"] for c in b.claims if c.get("kind") == "config"]
        q("wiring", "How are its passes and inputs wired?", "answered",
          f"{len(self.inp.passes)} pass(es) read from the shader's own configuration", cfg)
        frames = [c["id"] for c in b.claims if c.get("kind") == "frames"]
        stand = [c["id"] for c in b.claims if c.get("kind") == "stand_in"]
        unsupported = [c["id"] for c in b.claims if c.get("kind") == "unsupported"]
        failed = [c["id"] for c in b.claims if c.get("kind") == "render_failed"]
        flat = any(f.get("flat") for _, f in self.render_frames)
        conflict = [c["id"] for c in b.claims if c.get("kind") == "jump_conflict"]
        why: List[str] = []
        if stand:
            why.append(f"{len(stand)} input(s) drawn by a stand-in or fed silence")
        if unsupported:
            why.append(f"the runtime reports {len(unsupported)} input(s) or pass(es) it does not support")
        if flat:
            why.append("a frame is one flat colour")
        if failed:
            why.append("a render did not finish ok")
        if conflict:
            why.append("a feedback shader's frames were reached by a jump")
        why_ids = stand + unsupported + failed + conflict
        if not frames:
            q("look", "What does it look like?", "unresolved", "no receipt holds a frame", failed + unsupported)
        elif why:
            q("look", "What does it look like?", "partial", "; ".join(why), frames + why_ids)
        else:
            q("look", "What does it look like?", "answered", "SwiftShader frames, every input fed", frames)
        film = [r for r in self.inp.receipts if r["kind"] == "filmstrip" and r["receipt"] and r["receipt"].get("ok")]
        time_ids = [c["id"] for c in b.claims if c.get("kind") == "time"]
        if not frames:
            q("motion", "How does it change over time?", "unresolved", "never rendered", time_ids)
        elif film and not why:
            q("motion", "How does it change over time?", "answered", "a filmstrip over time; see the time unknowns for "
              "the span it covers", frames + time_ids)
        else:
            q("motion", "How does it change over time?", "partial",
              "; ".join((["stills only"] if not film else []) + why), frames + time_ids + why_ids)
        # The cost line names only what the claims hold: a static estimate when a pass has one, SwiftShader timing when
        # a receipt timed a frame. With neither, nothing answers the question (GPU timing is always unknown here).
        cost = [c["id"] for c in b.claims if c.get("kind") in ("cost", "cost_unknown", "timing", "gpu")]
        est = sum(1 for c in b.claims if c.get("kind") == "cost")
        blind = sum(1 for c in b.claims if c.get("kind") == "cost_unknown")
        timed = any(c.get("kind") == "timing" for c in b.claims)
        have = (["a static estimate" + (f" for {est} pass(es)" if blind else "")] if est else []) \
            + (["SwiftShader timing"] if timed else [])
        because = ([" and ".join(have)] if have else []) \
            + ([f"no static estimate for {blind} pass(es) with no entry point found"] if blind else []) \
            + ([] if timed else ["never timed on SwiftShader (no receipt times a frame)"]) + ["GPU timing is unknown"]
        q("cost", "What does it cost?", "partial" if est or timed else "unresolved", "; ".join(because), cost)
        study = [c["id"] for c in b.claims if c.get("kind") == "study"]
        corr = [c["id"] for c in b.claims if c.get("kind") == "corroboration"]
        missing = [c["id"] for c in b.claims if c.get("kind") == "study_missing"]
        q("intent", "Why was it built this way?", "partial" if study or corr else "unresolved",
          (f"{len(study)} heading(s) of our study note, all inferred"
           + ("; its corroboration section is cited, inferred, not re-run" if corr else ""))
          if study or corr else "no study note", (study + corr) or missing)
        if any(r["route"] in ("audio-reactive", "sound pass") for r in self.route):
            ids = [c["id"] for c in b.claims if c.get("kind") == "sound_pass"
                   or (c.get("kind") == "stand_in" and "silence" in c["claim"])]
            q("sound", "How does it sound, or respond to sound?", "unresolved",
              "the harness feeds silence and never plays a Sound pass", ids)
        if any(r["route"] == "interactive" for r in self.route):
            q("interaction", "How does it respond to input?", "unresolved", "no render pressed a key or moved the mouse",
              [c["id"] for c in b.claims if c.get("kind") == "interaction"])
        return out

    def build(self) -> dict:
        self.configuration()
        self.routes()
        self.code_claims()
        self.cost_claims()
        self.render_claims()
        self.unknown_claims()
        self.study_claims()
        checklist = self.checklist()
        counts = {lab: sum(1 for c in self.book.claims if c["label"] == lab) for lab in LABELS}
        from . import shelf as SH
        lic = SH.licence_for(self.inp.meta, {p["file"]: p["code"] for p in self.inp.passes})
        return {
            "api": API, "id": self.sid, "name": self.inp.meta.get("name"), "author": self.inp.meta.get("author"),
            "url": self.inp.meta.get("url"), "licence": lic["name"], "private": PRIVATE,
            "written_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "dissect_version": self.ver,
            "boundary": (f"one corpus shader: its configuration, every pass's source (dissect {self.ver}), the receipts in "
                         f"renders/{self.sid}/ and its study note; this verb executed nothing"),
            "route": self.route, "counts": counts, "claims": self.book.claims, "checklist": checklist,
        }


# ------------------------------------------------------------------------------------------------------- the verb
def explain(query: str, *, corpus: Optional[Path] = None, renders_dir: Optional[Path] = None,
            study_dir: Optional[Path] = None, ledger_dir: Optional[Path] = None, state_root: Optional[Path] = None,
            min_conf: float = D.MIN_CONF) -> dict:
    """The ledger for one corpus shader: the stored one when every input is unchanged (cached=True), else a fresh one,
    written under state/. Raises ExplainError for no match or an ambiguous one, ValueError for a path outside state/."""
    corpus = Path(corpus) if corpus is not None else C.CORPUS
    sid = resolve(query, corpus)
    out = ledger_path(sid, ledger_dir, state_root)
    inp = _Inputs(sid, corpus, Path(renders_dir) if renders_dir is not None else RENDERS,
                  Path(study_dir) if study_dir is not None else STUDY, min_conf)
    inputs = inp.cache_inputs()
    key = cache_key(inputs)
    old = _read_json(out)
    if old and (old.get("cache") or {}).get("key") == key and old.get("api") == API:
        return {**old, "cached": True, "ledger_path": str(out)}
    view = D.view_from_json(inp.shader, str(inp.shader_path))
    rep = D.dissect_view(view, min_conf)
    ledger = _Builder(inp, rep, view).build()
    ledger["cache"] = {"key": key, "inputs": inputs}
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(ledger, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(out)
    return {**ledger, "cached": False, "ledger_path": str(out)}


# ------------------------------------------------------------------------------------------------------- printing
def _short(text: str, n: int = 150) -> str:
    text = re.sub(r"\s+", " ", text)
    return text if len(text) <= n else text[: n - 3] + "..."


def summary(led: dict) -> str:
    """Summary first: who, the route, the counts, the checklist, the unknowns by name, where the ledger is."""
    head = f"EXPLAIN {led['id']} \"{led.get('name') or '?'}\" by {led.get('author') or '?'}  ({led.get('licence')})"
    if led.get("cached"):
        head += f"  [cached: inputs unchanged since {led.get('written_at')}; nothing re-analysed]"
    c = led["counts"]
    out = [head,
           "  route: " + "; ".join(f"{r['route']} ({_short(r['rule'], 60)})" for r in led["route"]),
           f"  claims: {sum(c.values())}  (" + ", ".join(f"{lab} {c.get(lab, 0)}" for lab in LABELS) + ")",
           "  checklist: " + ", ".join(f"{q['key']} {q['status']}" for q in led["checklist"])]
    unknown = [x for x in led["claims"] if x["label"] == "unknown" and x.get("kind") != "not_detected"]
    missed = [x for x in led["claims"] if x.get("kind") == "not_detected"]
    out.append(f"  unknowns: {c.get('unknown', 0)} ({len(missed)} detector groups not detected by dissect "
               f"{led.get('dissect_version')}: {', '.join(x.get('group', '?') for x in missed) or 'none'})")
    for x in unknown[:SUMMARY_UNKNOWNS]:
        out.append(f"    - {x['id']} {_short(x['claim'])}")
    if len(unknown) > SUMMARY_UNKNOWNS:
        out.append(f"    ... +{len(unknown) - SUMMARY_UNKNOWNS} more (--detail full)")
    out.append(f"  ledger: {led.get('ledger_path')}   (--detail full prints every claim with its evidence and boundary)")
    return "\n".join(out)


def full(led: dict) -> str:
    out = [summary(led), "CLAIMS"]
    for lab in LABELS:
        rows = [x for x in led["claims"] if x["label"] == lab]
        if not rows:
            continue
        out.append(f"  [{lab}] {len(rows)}")
        for x in rows:
            rated = f"confidence {x.get('confidence')}" + (f", score {x['score']:g}" if "score" in x else "")
            out.append(f"    {x['id']} {x['claim']}  ({rated})")
            out.append(f"        evidence: {', '.join(x['evidence'])}")
            out.append(f"        boundary: {x['boundary']}")
            if x.get("paths") and x.get("kind") != "not_detected":    # every pass, every time: the JSON keeps them
                out.append(f"        paths: {', '.join(x['paths'])}")
    out.append("ROUTE")
    for r in led["route"]:
        out.append(f"  {r['route']}: {r['rule']}  ({r['why']}; {', '.join(r['evidence'][:4])})")
    out.append("CHECKLIST (revisited)")
    for q in led["checklist"]:
        out.append(f"  {q['status']:<10} {q['question']}  -- {q['because']}" +
                   (f"  [{', '.join(q['claims'][:8])}{' ...' if len(q['claims']) > 8 else ''}]" if q["claims"] else ""))
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------------- the door
def _register(sub) -> None:
    p = sub.add_parser("explain", help="one shader's finding ledger: claims labelled observed/measured/inferred/unknown, "
                                       "each with an evidence id and its search boundary (cached on unchanged inputs)")
    p.add_argument("target", help="a corpus id, or a piece of a name that matches exactly one shader")
    p.add_argument("--detail", choices=("summary", "full"), default="summary",
                   help="summary first (default), or every claim with its evidence and boundary")
    p.add_argument("--min-conf", type=float, default=D.MIN_CONF, help=f"the dissector's floor (default {D.MIN_CONF})")
    p.set_defaults(fn=_cmd)


def _cmd(ns) -> int:
    from .cli import _print
    try:
        led = explain(ns.target, min_conf=ns.min_conf)
    except (ExplainError, ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print(led, ns.json, full if ns.detail == "full" else summary)
    return 0


def _hook() -> None:
    from . import cli
    cli.VERBS["explain"] = _register


_hook()
