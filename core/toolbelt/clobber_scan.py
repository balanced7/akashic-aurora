"""clobber_scan — unconditional shared-control-key writes, flagged statically (W47).

DESIGN: kimi (tools hunt #3). BUILD: claude from kimi's spec (their builder round stalled;
credited, fence invited). The class this makes systematic: K2, kimi's pause-clobber race --
control.pause is an unconditional `c.set(_pause_key(), ...)` that voids a human's persistent
pause, found by ONE lucky trace. A clobber-scan over a diff/module makes the reviewer LOOK
at every mutating ceremony instead of hoping someone traces the right line.

v1 is a REVIEWER-PROMPT LINT (regex + FUNCTION-SCOPE guard tracking): it flags CANDIDATES
for a human/fence to confirm, not a pass/fail gate. A write to a control-plane key FAMILY
(pause/halt/cursor/expect/drain + the _pause_key()/_halt_key() helpers) is flagged UNLESS a
read of the same family (is_paused/was_paused/exists/get/read_lane_cursor/...) appeared
EARLIER IN THE SAME FUNCTION. That scope matters: kimi's K2 was_paused guard reads at the
TOP of a ceremony and mutates many lines below, so a fixed line-window cries wolf on the
exact fixed code -- guard scope = the enclosing def, reset at each new def/class.

Laws: SCOPED (only control families -- data/telemetry/projection writes are not clobbers);
FUNCTION-GUARD (a same-family read earlier in the def clears every later write of it);
NON-EXECUTABLE-SKIP (comments/defs/docstrings never flag -- a lint that cries wolf gets
ignored, kimi's own guard-design law applied to itself); HONEST (findings are review
candidates that say why, not confirmed bugs).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# control-plane key FAMILIES whose unconditional mutation can strand fleet state.
_CONTROL_FAMILIES = ("pause", "halt", "cursor", "expect", "drain", "resume")
# pause/resume/halt all touch ONE control SURFACE (the pause key -- halt extends it,
# resume clears it), so an is_paused/was_paused guard clears writes to any of them. cursor/
# expect/drain are their own surfaces. Normalizing prevents the resume()-after-was_paused
# false positive (K2's own fix uses exactly that shape).
_SURFACE = {"pause": "pause", "resume": "pause", "halt": "pause", "paused": "pause",
            "cursor": "cursor", "expect": "expect", "drain": "drain"}


def _surface(fam: str) -> str:
    return _SURFACE.get(fam, fam)
# key-builder helpers that name a control family (control.py idiom: _pause_key() etc.)
_KEY_HELPER = re.compile(r"_(" + "|".join(_CONTROL_FAMILIES) + r")_key\s*\(")
# a literal control-family key: {ns}:pause / :control:paused / "...:cursor:..."
_KEY_LITERAL = re.compile(r"[:_](" + "|".join(_CONTROL_FAMILIES) + r")(?:d)?\b")
# a mutation call: c.set(/ .set(/ hset(/ .delete(/ c.delete(/ control.pause(/ .resume(
_WRITE = re.compile(r"\b(?:set|hset|delete|pause|resume|halt|expire)\s*\(")
# a read that guards a family: is_<fam>/was_<fam> name the family directly; the generic
# reads (exists/get/read_lane_cursor/...) guard whichever family the enclosing def mutates.
_GUARD_FAMILY = re.compile(r"\b(?:is|was)_(\w+)\b")
_GUARD_GENERIC = re.compile(
    r"\b(exists|\.get\(|hget|read_lane_cursor|drain_requested|pause_status|holder|cursor\(\))\b")
_DEF_RE = re.compile(r"^(?:async\s+)?def\s|^class\s")


def _families_on_line(line: str) -> set:
    fams = set(_KEY_HELPER.findall(line))
    fams |= set(_KEY_LITERAL.findall(line))
    # a bare control.pause()/resume()/halt() names its family by the verb itself
    for fam in _CONTROL_FAMILIES:
        if re.search(r"\b(?:control\.)?" + fam + r"\s*\(", line):
            fams.add(fam)
    return fams


def _is_executable(line: str) -> bool:
    """Skip non-code lines that produce pure false positives (kimi's cry-wolf warning):
    comments, def/class headers, and obvious docstring/prose (a line with no assignment,
    call-with-arg, or dot-call that just contains a family word in prose)."""
    s = line.strip()
    if not s or s.startswith("#") or s.startswith(("def ", "class ", "async def ")):
        return False
    if s.startswith(('"""', "'''", '"', "'")):        # docstring / bare-string prose
        return False
    return True


def scan(text: str) -> List[Dict[str, Any]]:
    """Findings: [{line_no, family, snippet, why}] -- one per unconditional control-key
    write with no same-family read-guard within GUARD_WINDOW lines above. Non-executable
    lines (comments, defs, docstrings) are skipped -- a lint that cries wolf gets ignored
    (kimi's own guard-design law, applied to itself)."""
    lines = str(text or "").splitlines()
    out: List[Dict[str, Any]] = []
    guarded_surfaces: set = set()  # control SURFACES read (is_/was_/generic) since last def
    generic_guard = False          # a family-agnostic guard read seen in this def
    in_docstring = False           # inside a triple-quoted block (prose, never a write)
    for i, line in enumerate(lines):
        triples = line.count('"""') + line.count("'''")
        was_in_docstring = in_docstring
        if triples % 2 == 1:
            in_docstring = not in_docstring
        if was_in_docstring or (in_docstring and triples):   # this line is docstring prose
            continue
        if _DEF_RE.match(line):                       # new function scope -> reset guards
            guarded_surfaces, generic_guard = set(), False
        # accumulate guard-reads FIRST (a guard earlier in the def clears later writes)
        for g in _GUARD_FAMILY.findall(line):
            guarded_surfaces.add(_surface(g))
        if _GUARD_GENERIC.search(line):
            generic_guard = True
        if not _is_executable(line) or not _WRITE.search(line):
            continue
        for fam in sorted(_families_on_line(line)):
            if _surface(fam) in guarded_surfaces or generic_guard:
                continue
            out.append({"line_no": i + 1, "family": fam,
                        "snippet": line.strip()[:120],
                        "why": (f"unconditional write to the '{fam}' control family with no "
                                f"same-family read-guard earlier in this function -- a clobber "
                                f"can strand fleet state (K2 genus). REVIEW: add a "
                                f"was_{fam}/is_{fam} guard, or confirm the overwrite is intended.")})
    return out


def render(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return "clobber-scan: clean -- no unguarded control-key writes"
    rows = [f"clobber-scan: {len(findings)} unguarded control-key write(s)"]
    for f in findings:
        rows.append(f"  L{f['line_no']} [{f['family']}]: {f['snippet']}")
    return "\n".join(rows)
