"""py -m arsenal shader card -- a module's test card: the small picture a module draws of itself, built from the house
library and rendered on SwiftShader with a receipt that says whether it compiled, showed anything, and stayed finite.

    py -m arsenal shader card <name>                 # compose the card: state/arsenal/shaders/cards/<name>/card.json
    py -m arsenal shader card <name> --render        # ... and picture it: PNGs, a NaN probe, receipt.json
    py -m arsenal shader card --all [--render]       # every card; with --render, in bursts under three minutes, and a
                                                     # table: name, compile ok, flat?, NaN pixels, ms
    options: --json, --cards-dir DIR, --dir MODULE_DIR (repeatable), --out DIR [--allow-tracked], and render's own
             --port, --lock-wait-min, --timeout, --fps, --page, --no-parity

WHY. A TV engineer does not judge a set by watching a film; he puts colour bars on it, because a fault in a known
picture shows as one wrong bar instead of "the film looks off". A card is that test pattern for one GLSL module: a curve
plot for a shaping function, a ramp for a colour map, a field for a noise. Daniel asked to "tweak one module and have
everything update" (2026-10-13); a card is how a seat that cannot see a screen knows a module still draws what it
promises before every surface that composes it changes too. (unified-architecture-draft.md, section 8 and the test plan; the
reconciled build spec beside it.)

THE FORMAT. A card is arsenal/web/glsl/cards/<module-name>.card -- NOT .glsl, so modules.load_library (which walks
*.glsl) never mistakes a card for a module. Its leading `//!` lines are one JSON header, read exactly as a module's
header is read (the same lines, joined the same way: one dialect, build-spec ruling 1); then a Shadertoy body:

    //! {"card": "<module name>", "uses": ["<module>", ...], "t": [0, 2], "size": [320, 180],
    //!  "note": "what to look for"}
    void mainImage(out vec4 color, in vec2 pixel) { ... }

    card   required; the module it pictures, and the file's name (<card>.card)
    uses   the modules to compose into Common (default: [card]); everything they need comes along by itself
    t      the times to picture, in seconds (default [0])
    size   [width, height] in pixels (default [320, 180])
    note   what a person should see, and what a broken module looks like instead

The entry point's parameter NAMES are free (the runtime calls mainImage by position). The house writes (out vec4 color,
in vec2 pixel): Shadertoy's template names followed by its usual first line are a run of 12+ tokens the licence line
finds in nearly every corpus shader (2026-10-13: 298 of them), and a house file may share no such run.

build_card composes Common = load_library().compose(uses) for the shader lab's runtime (target "toy") and Image = the
body, into the Shadertoy-shaped JSON the runtime reads. A card that names a module the library lacks, or calls a library
function from a module it does not use, is refused, naming the module.

THE THREE VERDICTS, each read from the pictures (render.py makes them; nothing here forks it):
  compile ok   every pass compiled, from the render page's own compile report
  not flat     some colour channel varies (its standard deviation, 0..255, reaches FLAT_STD) in every frame
  NaN-free     zero NaN or Inf pixels. A PNG cannot hold a NaN (by the time a picture exists it has become black, or
               whatever the driver chose), so every card is rendered TWICE: once as itself, and once through a probe
               that renames its mainImage and wraps it. The wrapper paints any pixel whose colour has a NaN or Inf in
               any channel pure magenta, and halves every finite pixel, so a finite pixel can never be pure magenta.
               The magenta pixels are then counted. A NaN is recognised three ways: isnan(), isinf(), and its IEEE 754
               bit pattern (exponent bits all ones means Inf or NaN), because a compiler that assumes finite maths may
               fold the first two away and cannot fold integer bit tests.
A card passes only when all three hold and both renders succeeded on a software renderer.

WHERE THINGS GO. state/arsenal/shaders/cards/<name>/: card.json and probe.json (the shaders), t<t>.png (the picture),
nan_t<t>.png (the probe, a dimmed picture with NaN in magenta), receipt.json (render.py's receipt plus a "card" block).
The lab server serves the PNGs at /cards/<name>/<file>.png. Times are SwiftShader's (the CPU): they rank cards against
each other and say nothing about a GPU.

LICENCE. Apache-2.0, our own code. Card bodies are house code too: written fresh, never copied from the corpus.
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import cli
from . import modules as M
from . import render as R
from . import serve as S

CARD_API = "arsenal.shader-card/v1"
CARDS_DIR = M.LIBRARY_DIR / "cards"
CARDS_OUT = R.STATE / "cards"
CARD_SUFFIX = ".card"
TARGET = "toy"                   # the shader lab's runtime: what renders a card
DEFAULT_TIMES = (0.0,)
DEFAULT_SIZE = (320, 180)
CARD_TIMEOUT_S = 60              # one job (one card, every t); a burst still ends under three minutes (render.py)
FLAT_STD = 2.0                   # a frame whose every channel's standard deviation is below this is one flat colour
MAGENTA_MIN, MAGENTA_MAX = 250, 5    # a probe pixel is NaN-magenta when red and blue >= 250 and green <= 5
PROBE_PREFIX = "nan_"            # the probe's frames: nan_t0.00.png beside t0.00.png
PROBE_ENTRY = "cardProbeImage"   # what the card's own mainImage is renamed to inside the probe
SHADER_OUTPUT = {"id": "4dfGRr", "channel": 0}   # the Image pass's output, as Shadertoy saves it (render.wrap_frag)
MAIN_IMAGE_RE = re.compile(r"\bvoid\s+mainImage\s*\(")

PROBE_WRAPPER = f"""\
// ---- NaN probe (arsenal/shaders/cards.py): the card's own entry point, renamed above, drawn through a check. Any NaN
// or Inf in any channel becomes pure magenta; every finite pixel is clamped and halved, so it is never pure magenta.
bool cardProbeNonFinite(float x) {{
    // isnan and isinf can be folded away by a compiler that assumes finite maths; the exponent bits cannot
    return isnan(x) || isinf(x) || (floatBitsToUint(x) & 0x7f800000u) == 0x7f800000u;
}}

void mainImage(out vec4 color, in vec2 pixel) {{
    vec4 seen = vec4(vec3(0.0), 1.0);     // what the runtime's own footer starts a pixel at
    {PROBE_ENTRY}(seen, pixel);
    bool bad = cardProbeNonFinite(seen.r) || cardProbeNonFinite(seen.g) || cardProbeNonFinite(seen.b)
            || cardProbeNonFinite(seen.a);
    color = bad ? vec4(1.0, 0.0, 1.0, 1.0) : vec4(0.5 * clamp(seen.rgb, 0.0, 1.0), 1.0);
}}
"""


class CardError(ValueError):
    """A card that cannot be read, built or written: the message names the card and what to change."""


@dataclass(frozen=True)
class Card:
    name: str
    path: str
    header: dict
    body: str
    uses: Tuple[str, ...]
    times: Tuple[float, ...]
    size: Tuple[int, int]
    note: str = ""


# ------------------------------------------------------------------------------------------------------------ reading
def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _header(text: str, path: str) -> Tuple[dict, str]:
    """(header, body): the leading `//!` lines read exactly as modules.parse_module reads a module's (one dialect)."""
    lines = M._source_lines(text)
    n = M._header_line_count(lines)
    if not n:
        raise CardError(f'{path}: no //! header on the first line (a card starts //! {{"card": "<module name>", ...}})')
    try:
        header = json.loads(" ".join(line.lstrip(" \t")[3:] for line in lines[:n]),
                            parse_constant=M._reject_constant, parse_int=M._json_int)
    except json.JSONDecodeError as exc:
        raise CardError(f"{path}: the //! header is not JSON ({exc.msg} at column {exc.colno})") from None
    except (ValueError, RecursionError) as exc:
        raise CardError(f"{path}: the //! header is not JSON ({exc})") from None
    return header, "\n".join(lines[n:])


def parse_card(text: str, path: str = "<text>") -> Card:
    """A card from its text. CardError names the file and the field when anything is missing or the wrong shape."""
    header, body = _header(text, path)
    if not isinstance(header, dict) or not isinstance(header.get("card"), str):
        raise CardError(f'{path}: the //! header needs "card": the name of the module this card pictures')
    name = header["card"]
    if not M.NAME_RE.fullmatch(name):
        raise CardError(f"{path}: a card's name is a module's name: letters, digits, '.', '_' or '-' (not {name!r})")
    p = Path(str(path))
    if p.suffix == CARD_SUFFIX and p.stem != name:
        raise CardError(f"{path}: the header names the card '{name}' but the file is '{p.name}'; a card lives in "
                        f"<module-name>{CARD_SUFFIX}")
    uses = header.get("uses", [name])
    if not isinstance(uses, list) or not all(isinstance(u, str) and M.NAME_RE.fullmatch(u) for u in uses):
        raise CardError(f'{path}: "uses" must be a list of module names (default: ["{name}"])')
    times = header.get("t", list(DEFAULT_TIMES))
    if (not isinstance(times, list) or not times or len(times) > R.MAX_TIMES
            or not all(_is_number(t) and math.isfinite(t) and t >= 0 for t in times)):
        raise CardError(f'{path}: "t" must be a list of 1 to {R.MAX_TIMES} times in seconds, each a number >= 0')
    size = header.get("size", list(DEFAULT_SIZE))
    if (not isinstance(size, list) or len(size) != 2
            or not all(isinstance(s, int) and not isinstance(s, bool) and 1 <= s <= R.MAX_SIDE for s in size)):
        raise CardError(f'{path}: "size" must be [width, height], whole pixels from 1 to {R.MAX_SIDE}')
    note = header.get("note", "")
    if not isinstance(note, str):
        raise CardError(f'{path}: "note" must be text (what a person should see)')
    if not MAIN_IMAGE_RE.search(M.strip_comments(body)):
        raise CardError(f"{path}: the card's body must define void mainImage(out vec4 color, in vec2 pixel), "
                        "Shadertoy style (any parameter names)")
    return Card(name=name, path=str(path), header=header, body=body, uses=tuple(dict.fromkeys(uses)),
                times=tuple(float(t) for t in times), size=(size[0], size[1]),
                note=" ".join(note.split()))   # a note wrapped across //! lines keeps no runs of indent


def card_path(name: str, cards_dir: Optional[Path] = None) -> Path:
    """Where the card named `name` lives. A name is a name, never a path."""
    if not isinstance(name, str) or not M.NAME_RE.fullmatch(name):
        raise CardError(f"not a card name: {name!r} (letters, digits, '.', '_' or '-')")
    return Path(cards_dir if cards_dir is not None else CARDS_DIR) / f"{name}{CARD_SUFFIX}"


def list_cards(cards_dir: Optional[Path] = None) -> List[str]:
    """Every card's name in the folder, sorted; [] when the folder does not exist yet."""
    d = Path(cards_dir if cards_dir is not None else CARDS_DIR)
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob(f"*{CARD_SUFFIX}") if p.is_file())


def load_card(name: str, cards_dir: Optional[Path] = None) -> Card:
    p = card_path(name, cards_dir)
    if not p.is_file():
        raise CardError(f"no card named '{name}' in {p.parent}")
    try:
        text = p.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CardError(f"{p}: is not UTF-8 text (byte {exc.start} cannot be decoded)") from None
    return parse_card(text, str(p))


# ------------------------------------------------------------------------------------------------------------ building
def probe_code(body: str) -> str:
    """The card's body with its mainImage renamed, then the wrapper that paints NaN and Inf magenta (see the header)."""
    return re.sub(r"\bmainImage\b", PROBE_ENTRY, body).rstrip("\n") + "\n\n" + PROBE_WRAPPER


def _missing_module(card: Card, name: str, lib: M.Library) -> str:
    if name in lib.lost_modules:
        where = lib.lost_modules[name]
        problem = next((p["problem"] for p in lib.problems if p["path"] == where), "see library.problems")
        return f"card '{card.name}' uses module '{name}', which was quarantined at load ({where}): {problem}"
    msg = f"card '{card.name}' uses module '{name}', which no library file defines"
    if lib.problems:
        paths = ", ".join(p["path"] for p in lib.problems[:5]) + (" ..." if len(lib.problems) > 5 else "")
        msg += f" ({len(lib.problems)} file(s) were quarantined at load and may have been meant to: {paths})"
    return msg


def _calls_outside(card: Card, lib: M.Library, closure: Iterable[str]) -> List[str]:
    """Library functions (and struct constructors) the body calls from modules outside `uses` and what they need: the
    compiler would only say "no matching function"; this says which module to add. A call nothing provides is left to
    the compiler, which names it."""
    code = M.strip_comments(card.body)
    own = {m.group(2) for m in M.DEFINITION_RE.finditer(code)}
    inside = set(closure)
    out = []
    for call in sorted(set(M.CALL_RE.findall(code)) - M.BUILTINS - M.ENTRY_POINTS - own):
        provider = lib.providers.get(call)
        if provider and provider not in inside:
            out.append(f"{call}() comes from module '{provider}'")
    return out


def build_card(card, library: Optional[M.Library] = None, cards_dir: Optional[Path] = None,
               lib_dirs: Optional[Iterable] = None, probe: bool = False) -> dict:
    """The card as a Shadertoy-shaped shader: Common = the library's composition of `uses` (absent when it uses none),
    Image = the body (or, with probe, the NaN probe around it), and a "card" block naming exactly what was composed.
    `card` is a Card or a name; the library is loaded leniently from lib_dirs when none is given, so one bad file
    elsewhere never blocks a card, while a card that needs that file is refused naming it."""
    c = card if isinstance(card, Card) else load_card(card, cards_dir)
    lib = library if library is not None else M.load_library(lib_dirs, strict=False)
    for name in c.uses:
        if name not in lib.modules:
            raise CardError(_missing_module(c, name, lib))
    try:
        order = lib.resolve(c.uses) if c.uses else []
        common = lib.compose(c.uses, target=TARGET) if c.uses else ""
    except M.ModuleError as exc:
        raise CardError(f"card '{c.name}' ({c.path}): {exc}") from None
    outside = _calls_outside(c, lib, order)
    if outside:
        raise CardError(f"card '{c.name}' ({c.path}) calls the library outside its \"uses\": " + "; ".join(outside)
                        + "; add those modules to \"uses\"")
    sha = None
    if common:
        head = common.splitlines()[2] if len(common.splitlines()) > 2 else ""
        sha = head.split(":", 1)[1].strip() if head.startswith("// sha256:") else None
    passes = []
    if common:
        passes.append({"name": "Common", "type": "common", "code": common, "inputs": [], "outputs": [],
                       "description": ""})
    passes.append({"name": "Image", "type": "image", "code": probe_code(c.body) if probe else c.body, "inputs": [],
                   "outputs": [dict(SHADER_OUTPUT)], "description": ""})
    return {
        "ver": "0.1",
        "info": {"id": f"card-{c.name}" + ("-nan" if probe else ""),
                 "name": f"card {c.name}" + (" (NaN probe)" if probe else ""),
                 "username": "akashic-house", "description": c.note,
                 "tags": ["card"] + (["nan-probe"] if probe else [])},
        "renderpass": passes,
        "card": {"api": CARD_API, "name": c.name, "uses": list(c.uses), "modules": list(order),
                 "versions": {n: lib.modules[n].version for n in order}, "composed_sha256": sha,
                 "t": list(c.times), "size": list(c.size), "note": c.note, "source": _rel(c.path), "probe": bool(probe),
                 "library_problems": len(lib.problems)},
    }


def _rel(path: str) -> str:
    try:
        return Path(path).resolve().relative_to(M.ROOT).as_posix()
    except ValueError:
        return str(path)


def _meta(card: Card, probe: bool = False) -> dict:
    """What a render receipt says about the subject: a house card, under the house licence."""
    tail = ("-nan", " (NaN probe)") if probe else ("", "")
    return {"id": f"card-{card.name}{tail[0]}", "name": f"card {card.name}{tail[1]}", "author": "akashic-house",
            "license": {"license": "Apache-2.0", "explicit": True, "line": ""}, "url": None}


def _check_out(out_root: Path, allow_tracked: bool) -> None:
    """Refuse an output folder outside state/ unless allowed, by render.py's own rule (a card is never corpus work)."""
    why = R.out_dir_refusal(out_root, R.Source(key="card", kind="json", path=out_root, src=""), allow_tracked)
    if why:
        raise CardError(why)


def _out_root(out_root) -> Path:
    p = Path(out_root) if out_root is not None else CARDS_OUT
    return p if p.is_absolute() else p.absolute()


def write_card(card, out_root: Optional[Path] = None, library: Optional[M.Library] = None,
               cards_dir: Optional[Path] = None, lib_dirs: Optional[Iterable] = None,
               allow_tracked: bool = False) -> dict:
    """Build the card and its probe and write <out_root>/<name>/card.json and probe.json. Returns a summary row."""
    root = _out_root(out_root)
    _check_out(root, allow_tracked)
    c = card if isinstance(card, Card) else load_card(card, cards_dir)
    lib = library if library is not None else M.load_library(lib_dirs, strict=False)
    shader = build_card(c, library=lib)
    probe = build_card(c, library=lib, probe=True)
    out = root / c.name
    R._write_json(out / "card.json", shader)
    R._write_json(out / "probe.json", probe)
    facts = shader["card"]
    return {"name": c.name, "ok": True, "stage": "build", "card_json": str(out / "card.json"),
            "probe_json": str(out / "probe.json"), "uses": facts["uses"], "modules": facts["modules"],
            "composed_sha256": facts["composed_sha256"], "t": facts["t"], "size": facts["size"], "note": c.note,
            "shader": shader, "probe": probe, "card": c}


# ----------------------------------------------------------------------------------------------------- the pictures
def image_facts(png) -> dict:
    """{std: [r, g, b], flat, mean_luma}: flat when every channel's standard deviation (0..255) is below FLAT_STD."""
    from PIL import Image, ImageStat
    with Image.open(png) as im:
        rgb = im.convert("RGB")
        std = [round(s, 3) for s in ImageStat.Stat(rgb).stddev]
        luma = ImageStat.Stat(rgb.convert("L")).mean[0]
    return {"std": std, "flat": max(std) < FLAT_STD, "mean_luma": round(luma, 2)}


def magenta_pixels(png) -> int:
    """How many pixels are the probe's NaN magenta (red and blue at least MAGENTA_MIN, green at most MAGENTA_MAX)."""
    from PIL import Image, ImageChops
    with Image.open(png) as im:
        r, g, b = im.convert("RGB").split()
        hot = lambda v: 255 if v >= MAGENTA_MIN else 0      # noqa: E731
        mask = ImageChops.multiply(ImageChops.multiply(r.point(hot), g.point(lambda v: 255 if v <= MAGENTA_MAX else 0)),
                                   b.point(hot))
        return mask.histogram()[255]


def _compile_ok(receipt: dict) -> Optional[bool]:
    """True when every drawn pass compiled; None when the page never reached the compile (nothing to judge)."""
    comp = receipt.get("compile")
    if not isinstance(comp, dict):
        return None
    passes = [p for p in comp.get("passes") or [] if p.get("key") != "sound"]
    return bool(passes) and all(p.get("ok") is True for p in passes)


def card_verdict(card: Card, shader: dict, plain: dict, probe: dict) -> dict:
    """The card block of a receipt: the three verdicts read from both renders' frames, frame by frame."""
    by_t = {f["t"]: f for f in probe.get("frames") or [] if f.get("png")}
    frames, nan_counts = [], []
    for f in plain.get("frames") or []:
        if not f.get("png"):
            continue
        row = {"t": f["t"], "png": f["png"], **image_facts(f["png"]), "nan_png": None, "nan_pixels": None}
        q = by_t.get(f["t"])
        if q:
            row["nan_png"], row["nan_pixels"] = q["png"], magenta_pixels(q["png"])
            nan_counts.append(row["nan_pixels"])
        frames.append(row)
    wanted = len(card.times)
    compile_ok = _compile_ok(plain)
    flat = any(f["flat"] for f in frames) if len(frames) == wanted else None
    nan = sum(nan_counts) if len(nan_counts) == wanted and len(probe.get("frames") or []) == wanted else None
    warm = (plain.get("timings") or {}).get("warm_ms")
    ms = [f["ms"] for f in plain.get("frames") or [] if _is_number(f.get("ms"))]
    ok = bool(plain.get("ok") and probe.get("ok") and compile_ok is True and flat is False and nan == 0)
    error = plain.get("first_error") or probe.get("first_error")
    if not error and not ok:
        error = ("flat: a frame is one flat colour" if flat else
                 f"{nan} NaN or Inf pixel(s), magenta in the probe frames" if nan else
                 "the NaN probe did not render" if nan is None else None)
    return {"api": CARD_API, "name": card.name, "ok": ok, "compile_ok": compile_ok, "flat": flat, "nan_pixels": nan,
            "ms": warm if _is_number(warm) else (round(sum(ms) / len(ms), 1) if ms else None),
            "ms_note": "SwiftShader (the CPU): ranks cards against each other; says nothing about a GPU",
            "error": error, "uses": list(card.uses), "modules": shader["card"]["modules"],
            "versions": shader["card"]["versions"], "composed_sha256": shader["card"]["composed_sha256"],
            "note": card.note, "source": shader["card"]["source"], "frames": frames,
            "probe": {"ok": probe.get("ok"), "status": probe.get("status"), "first_error": probe.get("first_error"),
                      "compile_ok": _compile_ok(probe)},
            "thresholds": {"flat_std": FLAT_STD, "magenta_red_blue_min": MAGENTA_MIN, "magenta_green_max": MAGENTA_MAX}}


def _summary(verdict: dict, receipt_path: Optional[Path], card_json: Optional[str]) -> dict:
    keys = ("name", "ok", "compile_ok", "flat", "nan_pixels", "ms", "error")
    return dict({k: verdict.get(k) for k in keys}, stage="render", frames=len(verdict.get("frames") or []),
                receipt=str(receipt_path) if receipt_path else None, card_json=card_json)


def _build_failure(name: str, error: str) -> dict:
    return {"name": name, "ok": False, "compile_ok": None, "flat": None, "nan_pixels": None, "ms": None,
            "error": error, "stage": "build", "frames": 0, "receipt": None, "card_json": None}


@dataclass
class _Planned:
    card: Card
    out: Path
    shader: dict
    plain: R.Source
    probe: R.Source
    request: dict = field(default_factory=dict)


def render_cards(names: Sequence[str], *, cards_dir: Optional[Path] = None, lib_dirs: Optional[Iterable] = None,
                 library: Optional[M.Library] = None, out_root: Optional[Path] = None, allow_tracked: bool = False,
                 port: int = S.DEFAULT_PORT, lock_wait_min: float = 10, timeout_s: Optional[float] = None,
                 fps: int = R.DEFAULT_FPS, page: str = R.DEFAULT_PAGE, parity: bool = True,
                 quiet: bool = False) -> dict:
    """Build every named card, render each twice (the picture, the NaN probe) in ONE run of render.py's driver -- which
    takes the house GPU lock and splits the work into bursts under three minutes -- and write each card's receipt.
    A card that does not build is reported and the rest still render. Returns {api, cards: [row], driver, out_root}."""
    root = _out_root(out_root)
    _check_out(root, allow_tracked)              # before any work: never a render into a folder the rules refuse
    lib = library if library is not None else M.load_library(lib_dirs, strict=False)
    timeout_ms = int(min(max(5.0, timeout_s or CARD_TIMEOUT_S), R.BURST_CAP_S) * 1000)
    rows: Dict[str, dict] = {}
    planned: List[_Planned] = []
    for name in dict.fromkeys(names):
        try:
            built = write_card(name, root, library=lib, cards_dir=cards_dir, allow_tracked=allow_tracked)
        except CardError as exc:
            rows[name] = _build_failure(name, str(exc))
            continue
        c, out = built["card"], root / name
        plain = R.Source(key=f"card-{name}", kind="json", path=out / "card.json",
                         src=R.stage_job(built["shader"], f"card-{name}"), meta=_meta(c))
        probe = R.Source(key=f"card-{name}-nan", kind="json", path=out / "probe.json",
                         src=R.stage_job(built["probe"], f"card-{name}-nan"), meta=_meta(c, probe=True))
        request = {"t": list(c.times), "w": c.size[0], "h": c.size[1], "fps": fps, "page": page,
                   "timeout_ms": timeout_ms, "parity": parity}
        planned.append(_Planned(c, out, built["shader"], plain, probe, request))
    merged = {"run_dir": None, "bursts": [], "refused": None, "error": None, "software": None, "rows": {}}
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    t0 = time.monotonic()
    if planned:
        with R._Lab(port) as base:
            jobs = []
            for p in planned:
                for src, prefix in ((p.plain, ""), (p.probe, PROBE_PREFIX)):
                    url = R.page_url(base, page, src.src, p.card.times, p.card.size, fps,
                                     max(5000, timeout_ms - 5000), parity)
                    jobs.append(R.Job(src.key, url, p.out, prefix, timeout_ms, p.card.size,
                                      allow_tracked=R.leaves_state(p.out)))
            merged = R.run_jobs(jobs, f"shader card ({len(planned)})", lock_wait_min, quiet=quiet)
    for p in planned:
        missing = {"status": "error", "error": merged.get("error") or "the driver returned no row"}
        plain = R.build_receipt(p.plain, dict(p.request), merged["rows"].get(p.plain.key) or missing, merged, started)
        probe = R.build_receipt(p.probe, dict(p.request, probe=True), merged["rows"].get(p.probe.key) or missing,
                                merged, started)
        verdict = card_verdict(p.card, p.shader, plain, probe)
        plain["card"] = verdict
        plain["probe_receipt"] = {k: probe.get(k) for k in ("id", "ok", "status", "first_error", "frames", "errors",
                                                             "compile")}
        R._write_json(p.out / "receipt.json", plain)
        rows[p.card.name] = _summary(verdict, p.out / "receipt.json", str(p.out / "card.json"))
    software = merged.get("software") or {}
    return {"api": CARD_API, "cards": [rows[n] for n in dict.fromkeys(names)], "out_root": str(root),
            "wall_ms": round((time.monotonic() - t0) * 1000),
            "driver": {"run_dir": merged.get("run_dir"), "bursts": len(merged.get("bursts") or []),
                       "refused": merged.get("refused"), "error": merged.get("error"),
                       "renderer": (software.get("webgl") or {}).get("renderer"), "chrome": merged.get("chrome")}}


# ------------------------------------------------------------------------------------------------------------- the verb
def _yes_no(v) -> str:
    return "-" if v is None else ("yes" if v else "no")


def _human_render(r: dict) -> str:
    d = r["driver"]
    lines = [f"{len(r['cards'])} card(s) in {r['wall_ms'] / 1000:.0f} s on {d['renderer'] or 'no renderer'} "
             f"({d['bursts']} burst(s)); out: {r['out_root']}",
             f"  {'card':<28} {'compile':<8} {'flat':<5} {'NaN px':>7} {'ms':>8}  verdict"]
    for c in r["cards"]:
        comp = "BUILD" if c["stage"] == "build" else ("ok" if c["compile_ok"] else "-" if c["compile_ok"] is None
                                                       else "FAIL")
        nan = "-" if c["nan_pixels"] is None else str(c["nan_pixels"])
        ms = "-" if c["ms"] is None else f"{c['ms']:g}"
        tail = "ok" if c["ok"] else f"FAIL: {(c['error'] or '')[:110]}"
        lines.append(f"  {c['name'][:28]:<28} {comp:<8} {_yes_no(c['flat']):<5} {nan:>7} {ms:>8}  {tail}")
    if d.get("refused"):
        lines.append(f"  REFUSED: {d['refused']}")
    if d.get("error"):
        lines.append(f"  driver: {str(d['error'])[:300]}")
    lines.append("  receipts: <out>/<card>/receipt.json; ms are SwiftShader's (the CPU), for ranking cards only")
    return "\n".join(lines)


def _human_build(r: dict) -> str:
    lines = [f"{len(r['cards'])} card(s) composed (not rendered: add --render for pictures and a receipt)"]
    for c in r["cards"]:
        if c["ok"]:
            lines.append(f"  {c['name']:<28} uses {', '.join(c['uses']) or '(none)'}; composes "
                         f"{', '.join(c['modules']) or '(nothing)'}"
                         + (f"; sha256 {c['composed_sha256'][:12]}" if c["composed_sha256"] else "")
                         + f"\n  {'':<28} {c['card_json']}")
        else:
            lines.append(f"  {c['name']:<28} REFUSED: {c['error']}")
    if r["library_problems"]:
        lines.append(f"  the library quarantined {len(r['library_problems'])} file(s) at load: "
                     + "; ".join(p["problem"][:120] for p in r["library_problems"][:3]))
    return "\n".join(lines)


def cmd_card(ns) -> int:
    if bool(ns.name) == bool(ns.all):
        print("give one card name, or --all (not both): py -m arsenal shader card <name>|--all [--render]",
              file=sys.stderr)
        return 2
    cards_dir = Path(ns.cards_dir) if ns.cards_dir else None
    names = list_cards(cards_dir) if ns.all else [ns.name]
    out_root = Path(ns.out).resolve() if ns.out else CARDS_OUT
    if not names:
        cli._print({"api": CARD_API, "cards": [], "cards_dir": str(cards_dir or CARDS_DIR)}, ns.json,
                   lambda r: f"no cards yet in {r['cards_dir']}")
        return 0
    if not ns.render:
        lib = M.load_library(ns.dir, strict=False)
        rows = []
        for name in names:
            try:
                row = write_card(name, out_root, library=lib, cards_dir=cards_dir, allow_tracked=ns.allow_tracked)
                rows.append({k: v for k, v in row.items() if k not in ("shader", "probe", "card")})
            except CardError as exc:
                if not ns.all:
                    print(str(exc), file=sys.stderr)
                    return 2
                rows.append(_build_failure(name, str(exc)))
        report = {"api": CARD_API, "rendered": False, "cards": rows, "library_problems": lib.problems}
        cli._print(report, ns.json, _human_build)
        return 0 if all(r["ok"] for r in rows) else 1
    try:
        report = render_cards(names, cards_dir=cards_dir, lib_dirs=ns.dir, out_root=out_root,
                              allow_tracked=ns.allow_tracked, port=ns.port, lock_wait_min=ns.lock_wait_min,
                              timeout_s=ns.timeout, fps=ns.fps, page=ns.page, parity=ns.parity, quiet=ns.json)
    except CardError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not ns.all and report["cards"][0]["stage"] == "build":
        print(report["cards"][0]["error"], file=sys.stderr)
        return 2
    report["rendered"] = True
    cli._print(report, ns.json, _human_render)
    if report["driver"].get("refused"):
        return R.EXIT_REFUSED
    return 0 if all(c["ok"] for c in report["cards"]) else 1


def register_card(sub) -> None:
    p = sub.add_parser("card", help="a module's test card: compose it from the house library; with --render, picture "
                                    "it on SwiftShader and judge it (compiles, not flat, no NaN)")
    p.add_argument("name", nargs="?", help=f"the card's name: arsenal/web/glsl/cards/<name>{CARD_SUFFIX}")
    p.add_argument("--all", action="store_true", help="every card in the cards folder")
    p.add_argument("--render", action="store_true",
                   help="render each card twice on SwiftShader (the picture, then the NaN probe) under the GPU lock")
    p.add_argument("--cards-dir", help="the folder of .card files (default arsenal/web/glsl/cards)")
    p.add_argument("--dir", action="append",
                   help="a module directory, repeatable (default: arsenal/web/glsl, then design/vfx-chunks)")
    R._out(p, "state/arsenal/shaders/cards; each card writes <out>/<name>/")
    R._common(p)
    p.set_defaults(fn=cmd_card)


cli.VERBS["card"] = register_card
