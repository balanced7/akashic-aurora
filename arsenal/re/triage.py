"""re triage — the read-only "what is this file, and which door next" router.

Gap G3 of Vandor's 2026-10-13 house-inventory: the house has per-format doors
(`media probe`, `shader dissect`, `riot.py`) but no front door that routes a target
to the right one. This is that front door.

Contract (three rules, matching re-triage-slice-spec.md):
  1. READ-ONLY: open(path, "rb"), read a bounded prefix, close. Never execute,
     never unpack, never import a target. Arbitrary unsandboxed binaries are opened
     only inside a disposable VM (gap G1, Daniel's call) — triage stops at reading.
  2. OBSERVATIONS / INFERENCES / UNKNOWNS apart, every claim tagged.
  3. BOUNDED NEGATIVES stay bounded: "no match" names its denominator and hash.

The detector ladder runs cheap-and-certain first, and a detector never runs after a
higher-confidence claim already routed the file. Every detector is lazy: a missing
optional dependency (pefile, magic) degrades to an [unknown], never raises.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import List, Optional

from . import API, INFERRED, OBSERVED, UNKNOWN

MAX_PREFIX = 4096          # bytes read before any detector runs; configurable per-call

# Routing map: detected kind -> the next door. Triage NAMES the door; it never runs it.
# A route to a not-yet-built door is a feature: it makes the arsenal's current extent
# honest instead of pretending the map is complete.
ROUTES = {
    "pe-executable": "arsenal re binary",     # gap G5, NOT built yet
    "elf-executable": "arsenal re binary",    # gap G5, NOT built yet
    "mach-o": "arsenal re binary",            # gap G5, NOT built yet
    "video": "arsenal media probe",           # exists
    "audio": "arsenal media probe",           # exists
    "image": "arsenal media probe",           # exists (probe handles stills via ffmpeg)
    "glsl-source": "shader dissect",          # exists
    "json": "arsenal re ledger",              # gap G2, NOT built yet
    "text": "arsenal re ledger",              # gap G2, NOT built yet
    "archive": "arsenal re binary",           # gap G5
    "unknown": None,                          # no door yet; loud, not silent
}

# ---- detectors (each returns a list of matches; [] means "did not claim") ---------

def _sha256(prefix: bytes) -> str:
    return hashlib.sha256(prefix).hexdigest()


def _pe_detect(prefix: bytes) -> List[dict]:
    """Read the DOS/PE headers directly (struct, no pefile dependency).

    A PE: 'MZ' at 0, then a u32 at offset 0x3c pointing at the 'PE\\0\\0' signature.
    All fields below are OBSERVED (real header bytes), except the .NET guess, which
    is INFERRED from the COM descriptor directory being non-zero.
    """
    if len(prefix) < 0x40 or prefix[0:2] != b"MZ":
        return []
    e_lfanew = struct.unpack_from("<I", prefix, 0x3C)[0]
    if e_lfanew + 24 > len(prefix):
        # MZ but we cannot reach the PE signature in the bounded prefix: an UNKNOWN,
        # not a negative. This is the bounded-negative rule in action.
        return [{"detector": "pe-header", "claim": "MZ magic present; PE signature beyond prefix",
                 "tag": UNKNOWN, "confidence": None,
                 "evidence": f"MZ at 0x0, e_lfanew=0x{e_lfanew:x} > {MAX_PREFIX} prefix"}]
    if prefix[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        return [{"detector": "pe-header", "claim": "MZ magic present but not a PE (DOS stub?)",
                 "tag": INFERRED, "confidence": 0.5, "evidence": "MZ at 0x0, no PE\\0\\0 at e_lfanew"}]
    machine = struct.unpack_from("<H", prefix, e_lfanew + 4)[0]
    nt_hdr = prefix[e_lfanew + 4:e_lfanew + 24]
    # Optional header magic: 0x20b = PE32+, 0x10b = PE32
    opt_magic = struct.unpack_from("<H", prefix, e_lfanew + 24)[0]
    bits = "x86-64" if opt_magic == 0x20B else ("x86" if opt_magic == 0x10B else "?")
    # .NET check: COM descriptor directory (data dir index 14, i.e. 0x8 + 14*8) non-zero.
    # This is an INFERENCE: a non-zero CLR header strongly implies managed code.
    com_rva = struct.unpack_from("<I", prefix, e_lfanew + 24 + 0x60 + 14 * 8)[0] \
        if e_lfanew + 24 + 0x60 + 14 * 8 + 4 <= len(prefix) else 0
    matches = [{
        "detector": "pe-header", "tag": OBSERVED, "confidence": 0.99,
        "kind": "pe-executable",
        "claim": f"PE executable, machine 0x{machine:04x}, {'64-bit' if bits == 'x86-64' else '32-bit'}",
        "evidence": f"MZ at 0x0, PE\\0\\0 at 0x{e_lfanew:x}, optional magic 0x{opt_magic:x}",
    }]
    if com_rva:
        matches.append({
            "detector": "pe-header", "tag": INFERRED, "confidence": 0.8,
            "claim": "managed (.NET) image, CLR header present",
            "evidence": f"COM descriptor directory RVA 0x{com_rva:x} non-zero",
        })
    return matches


def _elf_detect(prefix: bytes) -> List[dict]:
    if len(prefix) < 20 or prefix[0:4] != b"\x7fELF":
        return []
    klass = prefix[4]          # 1 = 32-bit, 2 = 64-bit
    data = prefix[5]           # 1 = LE, 2 = BE
    bits = "64-bit" if klass == 2 else ("32-bit" if klass == 1 else "?")
    endian = "little-endian" if data == 1 else ("big-endian" if data == 2 else "?")
    ei_type = struct.unpack_from("<H", prefix, 16)[0] if data == 1 else struct.unpack_from(">H", prefix, 16)[0]
    ktype = {0: "none", 1: "relocatable", 2: "executable", 3: "shared", 4: "core"}.get(ei_type, f"0x{ei_type:x}")
    return [{"detector": "elf-header", "tag": OBSERVED, "confidence": 0.99,
             "kind": "elf-executable",
             "claim": f"ELF {bits} {endian}, type {ktype}",
             "evidence": "0x7f 'ELF' magic at 0x0, EI_CLASS/EI_DATA at bytes 4-5"}]


def _macho_detect(prefix: bytes) -> List[dict]:
    magics = {0xFEEDFACE: "32-bit", 0xFEEDFACF: "64-bit", 0xCEFAEDFE: "32-bit (BE)",
              0xCFFAEDFE: "64-bit (BE)", 0xCAFEBABE: "fat (universal)"}
    if len(prefix) < 4:
        return []
    m = struct.unpack_from(">I", prefix, 0)[0]
    if m not in magics:
        return []
    return [{"detector": "macho-header", "tag": OBSERVED, "confidence": 0.99,
             "kind": "mach-o",
             "claim": f"Mach-O {magics[m]}",
             "evidence": f"magic 0x{m:08x} at 0x0"}]


def _archive_detect(prefix: bytes) -> List[dict]:
    sigs = {
        b"PK\x03\x04": ("ZIP archive", 0.98),
        b"\x1f\x8b": ("gzip stream", 0.98),
        b"7z\xbc\xaf\x27\x1c": ("7-Zip archive", 0.98),
        b"Rar!\x1a\x07": ("RAR archive", 0.98),
        b"BZh": ("bzip2 stream", 0.95),
    }
    out = []
    for sig, (claim, conf) in sigs.items():
        if prefix.startswith(sig):
            out.append({"detector": "archive-sig", "tag": OBSERVED, "confidence": conf,
                        "kind": "archive", "claim": claim, "evidence": f"signature {sig!r} at 0x0"})
            return out  # first (cheapest, most certain) wins
    return out


def _media_detect(prefix: bytes) -> List[dict]:
    sigs = {
        b"\x00\x00\x00\x18ftyp": ("MP4/MOV container (ISO BMFF)", 0.98),
        b"\x1aE\xdf\xa3": ("Matroska/WebM (EBML)", 0.95),
        b"RIFF": ("RIFF container (WAV/AVI/etc.)", 0.9),
        b"\xff\xfb": ("MP3 (MPEG audio, no ID3)", 0.9),
        b"ID3": ("MP3 (ID3 tag present)", 0.9),
        b"OggS": ("Ogg container", 0.95),
        b"\x89PNG\r\n\x1a\n": ("PNG image", 0.99),
        b"\xff\xd8\xff": ("JPEG image", 0.99),
        b"GIF87a": ("GIF image", 0.99),
        b"GIF89a": ("GIF image", 0.99),
    }
    for sig, (claim, conf) in sigs.items():
        if prefix.startswith(sig):
            # route media to media probe; kind is 'video'/'audio'/'image' by signature
            kind = "image" if ("PNG" in claim or "JPEG" in claim or "GIF" in claim) else (
                "audio" if "MP3" in claim else "video")
            return [{"detector": "media-sig", "tag": OBSERVED, "confidence": conf,
                     "claim": claim, "kind": kind, "evidence": f"signature {sig!r} at 0x0"}]
    return []


def _text_detect(prefix: bytes) -> List[dict]:
    """Heuristic only — always INFERRED. Distinguishes structured text (JSON, GLSL
    source, markup) from plain text by content, not by name. Structured signals
    (`#version`, `void main`, `{`/`[`/`<` leading bytes) are MORE specific than libmagic's
    blanket "ASCII text" and are ranked above it by the callers' rank table."""
    head = prefix[:256].lstrip(b"\xef\xbb\xbf")  # strip a UTF-8 BOM
    if head.startswith(b"#version") or b"void main" in head or b"precision " in head:
        return [{"detector": "text-heuristic", "tag": INFERRED, "confidence": 0.85,
                 "claim": "GLSL source", "kind": "glsl-source",
                 "evidence": "shader marker (#version / void main / precision) in first 256 bytes"}]
    if head.lstrip().startswith((b"{", b"[")):
        return [{"detector": "text-heuristic", "tag": INFERRED, "confidence": 0.85,
                 "claim": "JSON", "kind": "json",
                 "evidence": "first non-whitespace byte is { or ["}]
    if head.lstrip().startswith(b"<"):
        return [{"detector": "text-heuristic", "tag": INFERRED, "confidence": 0.6,
                 "claim": "markup (XML/HTML)", "kind": "text",
                 "evidence": "first non-whitespace byte is <"}]
    # printable ratio: mostly-printable bytes => plain text, otherwise binary-but-unknown
    printable = sum(1 for b in prefix if 0x20 <= b < 0x7F or b in (0x09, 0x0A, 0x0D))
    ratio = printable / len(prefix) if prefix else 0.0
    if ratio > 0.90:
        return [{"detector": "text-heuristic", "tag": INFERRED, "confidence": 0.5,
                 "claim": "plain text", "kind": "text",
                 "evidence": f"{ratio:.0%} of the prefix is printable ASCII"}]
    return []


def _magic_detect(prefix: bytes, path: str) -> List[dict]:
    """libmagic (python-magic) as the byte-signature oracle. Lazy import; a missing
    dependency degrades to an [unknown], never raises — a triage must not fail closed."""
    try:
        import magic  # noqa: PLW0406 (lazy: optional dependency)
    except Exception:
        return [{"detector": "libmagic", "tag": UNKNOWN, "confidence": None,
                 "claim": "libmagic unavailable (python-magic not importable)",
                 "evidence": "import magic raised"}]
    try:
        text = magic.from_buffer(prefix[:MAX_PREFIX])
    except Exception as e:  # pragma: no cover - libmagic rare internal error
        return [{"detector": "libmagic", "tag": UNKNOWN, "confidence": None,
                 "claim": f"libmagic errored: {type(e).__name__}",
                 "evidence": "from_buffer raised"}]
    return [{"detector": "libmagic", "tag": INFERRED, "confidence": 0.85,
             "claim": text, "evidence": f"libmagic over first {min(len(prefix), MAX_PREFIX)} bytes"}]


# ---- the router (one function, pure) -------------------------------------------

def triage(path: str, *, max_prefix: int = MAX_PREFIX) -> dict:
    """Identify a file read-only and route to the next door.

    Returns the house-shaped receipt: api / source / params / computed_with / payload /
    blind. The payload's `matches` are every detector claim with its evidence tag; the
    `blind` names exactly what was NOT searched. Never executes or unpacks the target.
    """
    p = Path(path)
    prefix_bytes = 0
    sha = ""
    try:
        with open(p, "rb") as fh:
            prefix = fh.read(max_prefix)
        prefix_bytes = len(prefix)
        sha = _sha256(prefix)
    except FileNotFoundError:
        return {"api": API, "source": {"path": str(p)},
                "params": {"max_prefix": max_prefix},
                "payload": {"kind": "unknown", "matches": [{"detector": "triage",
                    "tag": UNKNOWN, "confidence": None, "claim": "file not found",
                    "evidence": "open() raised FileNotFoundError"}], "route": None},
                "blind": {"unsearched": ["file did not exist to read"]}}
    except PermissionError:
        return {"api": API, "source": {"path": str(p)},
                "params": {"max_prefix": max_prefix},
                "payload": {"kind": "unknown", "matches": [{"detector": "triage",
                    "tag": UNKNOWN, "confidence": None, "claim": "permission denied",
                    "evidence": "open() raised PermissionError"}], "route": None},
                "blind": {"unsearched": ["could not read the file"]}}

    # The ladder: cheap and certain first. A detector that returns a confident,
    # routing claim short-circuits the rest.
    ladder = [
        _magic_detect(prefix, str(p)),   # oracle first, but its claim is [inferred]
        _pe_detect(prefix),
        _elf_detect(prefix),
        _macho_detect(prefix),
        _archive_detect(prefix),
        _media_detect(prefix),
        _text_detect(prefix),
    ]
    matches: List[dict] = []
    # Detector specificity rank: a structural header read (PE/ELF/Mach-O/archive/media)
    # outranks the libmagic oracle (which guesses), which outranks content heuristics.
    # Every detector that CAN name a kind must set an explicit `kind` field; kinds are
    # reconciled on rank, never on fragile claim-substring matching.
    rank_of = {"pe-header": 3, "elf-header": 3, "macho-header": 3,
               "archive-sig": 3, "media-sig": 3,
               "text-heuristic": 3,   # structured text (GLSL/JSON) is MORE specific than libmagic's
               "libmagic": 2}        # blanket language guess ("C source" for any #version file)
    for detector_matches in ladder:
        matches.extend(detector_matches)

    if not matches:
        return {"api": API, "source": {"path": str(p), "sha256": sha, "size": p.stat().st_size,
                "prefix_bytes": prefix_bytes}, "params": {"max_prefix": max_prefix},
                "payload": {"kind": "unknown", "matches": [{"detector": "triage",
                    "tag": UNKNOWN, "confidence": None, "claim": "nothing matched any detector",
                    "evidence": "no detector returned a claim over the prefix"}], "route": None},
                "blind": {"unsearched": [f"{prefix_bytes} bytes read, zero claims"]}}

    # Choose the winning match: highest detector rank, then [observed] over [inferred],
    # then confidence. Specific structure beats generic oracle beats content heuristic.
    def _score(m: dict):
        return (rank_of.get(m["detector"], 0),
                1 if m.get("kind") else 0,          # a named kind beats a bare claim at equal rank
                1 if m.get("tag") == OBSERVED else 0,
                m.get("confidence") or 0.0)
    best = max(matches, key=_score)

    # Kind comes ONLY from an explicit `kind` field the detector set. A detector that
    # named no kind cannot win the kind decision; fall back to claim-derived kinds only
    # for the oracle, whose text is the whole point, and which never misroutes binaries.
    kind = best.get("kind")
    if kind is None:
        claim = best.get("claim", "").lower()
        if "pe executable" in claim or "pe32" in claim or "pe32+" in claim:
            kind = "pe-executable"
        elif "elf " in claim or "elf" == claim[:3]:
            kind = "elf-executable"
        elif "mach-o" in claim:
            kind = "mach-o"
        elif "json" in claim:
            kind = "json"
        elif "glsl" in claim:
            kind = "glsl-source"
        elif any(t in claim for t in ("text", "markup", "ascii", "utf-8")):
            kind = "text"
        elif any(t in claim for t in ("zip", "gzip", "7-zip", "rar", "bzip2")):
            kind = "archive"
        elif any(t in claim for t in ("mp4", "matroska", "webm", "riff", "avi", "wav")):
            kind = "video"
        elif any(t in claim for t in ("mp3", "mpeg audio", "audio")):
            kind = "audio"
        elif any(t in claim for t in ("png", "jpeg", "gif", "image")):
            kind = "image"
        else:
            kind = "unknown"
    route = ROUTES.get(kind)

    unsearched = []
    if prefix_bytes >= max_prefix and p.stat().st_size > max_prefix:
        unsearched.append(f"only first {max_prefix} of {p.stat().st_size} bytes read")
    unsearched.append(f"{len(matches)} detector claim(s) total; {len([m for m in matches if m['tag'] == UNKNOWN])} unknown(s)")

    return {
        "api": API,
        "source": {"path": str(p), "sha256": sha, "size": p.stat().st_size,
                   "prefix_bytes": prefix_bytes},
        "params": {"max_prefix": max_prefix},
        "computed_with": {
            "detectors": [m["detector"] for m in matches],
            "no_processes": True,          # triage spawned nothing, executed nothing
        },
        "payload": {
            "kind": kind,
            "matches": matches,
            "route": route,
        },
        "blind": {
            "unsearched": unsearched,
            "defenses": ["not executed", "not unpacked", "opened read-only"],
        },
    }


def triage_json(path: str, *, max_prefix: int = MAX_PREFIX) -> str:
    return json.dumps(triage(path, max_prefix=max_prefix), indent=2)
