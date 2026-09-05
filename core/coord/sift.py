"""sift -- the nested ask: a tiered read that returns dissent instead of consensus.

WHY THIS EXISTS. The fan-out playbook's closing finding was that the ORCHESTRATOR is the
bottleneck, not the helpers: six helpers finishing at once is six things to read, so the
metric is not "how many can I run" but "how much can I safely NOT read and still be
correct". Dissent-first rendering was named there as the highest-leverage unbuilt feature.
This is that feature, built as structure rather than as discipline.

THE TIERS, and what each is allowed to return:

    tier 0  EVIDENCE   word-boundary occurrences -> one content-addressed blob per term
    tier 1  FAN        N hats x K terms, each answering DESCRIPTIVELY, citing file:line
    tier 2  CURATE     per-term PAIRS, hats varied within the pair, over identical evidence
    tier 3  COMPARE    dissent table first, agreement inventory second, flip rate gated
    ---     ADJUDICATE not here. T207 proved this step is not automatable.

THE ONE IDEA THAT MAKES IT MORE THAN A FAN. Two curators reading the SAME evidence who
disagree is a measurement, not a nuisance: the flip rate over pairs IS the artifact rate of
the curation tier. That generalises L2 ("run the same fan twice with clean evidence and
diff the verdicts") one tier up, where it had never been applied.

AND THE TRAP THAT MAKES IT HONEST, contributed by claude#42d00626 within an hour of
shipping the bug it describes: disagreement has THREE causes, not two --

    1. real ambiguity in the material
    2. curation artifact (what we want to measure)
    3. THE CURATORS DID NOT RECEIVE THE SAME INPUTS

T216 (4875fe9) was cause 3 one tier down: `--with` was accepted on the fan path and
SILENTLY dropped, so five helpers returned well-formed confident answers about zero files.
It survived a night of heavy use because the big runs inlined their files by hand. So the
flip rate here REFUSES to compute unless every dossier's evidence hash matches, and says
which hashes diverged. Measuring input divergence and reporting it as curation noise would
be that same defect, rebuilt by the very tool meant to catch it.

WHAT THIS MODULE WILL NOT DO. It produces CANDIDATES and DISAGREEMENTS, never verdicts.
The adjudication is the reader's, and a fan-out's precision was measured at ~20% (10
hand-checked: 2 genuine, 4 false positives, 4 pedantic-but-true). Anything here that reads
like a conclusion is a bug in the prompt, not a finding.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.outcome import BoundaryOutcome

#: Above this share of dissenting pairs, L3 fires. NOT a discard threshold -- see
#: compare_dossiers. The prior seat's own correction: "use L3 to trigger a triage sample,
#: never to discard a result", because the 408-way audit's implausible 37% was partly real.
IMPLAUSIBLE_DISSENT_RATE = 0.40
IMPLAUSIBLE_MIN_N = 5          # below this, a high rate is small-n noise, not an alarm

DEFAULT_MAX_OCCURRENCES = 120

_CODE_SUFFIXES = (".py", ".md")

#: THE CORPUS HAS PLANES, and merging them is itself a forked-semantics bug -- which is
#: how this constant came to exist. The first live run of evidence_pack reported `drained`
#: in 67 files against a measured 6, and the breakdown was 56 tests / 51 docs / 27 source /
#: 2 ComfyUI-Zluda (a VENDORED third-party project living in the tree). Three of those are
#: not our vocabulary at all in the sense the question means:
#:
#:   source -- the mechanism. Two meanings here is a DEFECT.
#:   test   -- assertions ABOUT the mechanism. Two meanings here usually mirrors source.
#:   doc    -- prose about the mechanism. Two meanings here is often just English.
#:   vendor -- somebody else's project. Their word, not ours. Pure noise.
#:
#: A pack that answers "67 files" to a question that meant "source files" is the same
#: one-word-two-meanings disease the whole tool exists to find, so the plane is carried on
#: every occurrence rather than resolved silently at scan time.
PLANES: Dict[str, Tuple[str, ...]] = {
    "source": ("core", "scripts", "agent", "security", "mcp_servers"),
    "test":   ("tests",),
    "doc":    ("docs", "charters", "design"),
}

#: Vendored/foreign trees, named rather than pattern-matched so an addition is a decision.
#: ComfyUI-Zluda carries its own pyproject/package.json -- a whole separate project.
_VENDOR_DIRS = {"ComfyUI-Zluda", "dockerized-ai", "models", "build", "dist", "node_modules"}

#: Records of the past and machine spill. Every term's HISTORY lives here, so including
#: them makes everything look forked.
_NOISE_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".venv", "venv", "state", "chronicles",
    "research", "data", "logs", "sessions", "session_logs", "session_snapshots",
    "session_screenshots", "backups", "backup_wsl_migration", "temp", "scratch", "blobs",
    "artifacts", "store", "coordinator_logs", "blackboard_data", "dropbox", "refs",
    "requirements", "assets", "__pycache__",
}


def _plane_of(rel: str) -> Optional[str]:
    """Which plane a repo-relative path belongs to, or None if it is out of corpus.

    Top-level .py files (agent_cli.py, ai_setup_mcp.py) are source: they are the doors.
    """
    head = rel.replace("\\", "/").split("/")[0]
    if head in _VENDOR_DIRS or head in _NOISE_DIRS or head.startswith("."):
        return None
    for plane, roots in PLANES.items():
        if head in roots:
            return plane
    if head.endswith(".py"):
        return "source"
    return None


# ===================================================================== tier 0: evidence
@dataclass
class EvidencePack:
    """One term's real usages, content-addressed so downstream tiers can prove identity.

    `sha` addresses the BLOB, which is what a helper actually reads -- not the occurrence
    list, not the term. Two curators with the same sha provably saw the same bytes, which
    is the only thing that makes a flip rate mean anything.
    """
    term: str
    occurrences: List[Dict[str, Any]] = field(default_factory=list)
    blob: str = ""
    sha: str = ""
    truncated: bool = False
    blind: List[str] = field(default_factory=list)


def _word_re(term: str) -> "re.Pattern[str]":
    r"""Word-boundary matcher.

    L2, and it cost a whole re-run to learn: `git grep` without -w fed the fan
    'provenance' as usages of 'prove' and 'DeepSeek' as usages of 'deep'. Every answer came
    back well-formed and confident, and re-running with boundaries flipped 7 of 20
    verdicts. \b alone is not enough for identifiers, because `open` must not match
    `open_door` -- so the guards below also exclude adjacent underscores.
    """
    t = re.escape(term)
    return re.compile(rf"(?<![\w]){t}(?![\w])", re.IGNORECASE)


def _iter_repo_files(root: str) -> Iterable[str]:
    skip = _VENDOR_DIRS | _NOISE_DIRS
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith(_CODE_SUFFIXES):
                yield os.path.join(dirpath, fn)


def evidence_pack(term: str, *, corpus: Optional[Dict[str, str]] = None,
                  root: Optional[str] = None,
                  planes: Sequence[str] = ("source",),
                  max_occurrences: int = DEFAULT_MAX_OCCURRENCES) -> EvidencePack:
    """Gather word-boundary occurrences of `term` and address them by content.

    `corpus` (path -> text) is for tests and for feeding a pre-filtered set; omit it and
    the real tree is walked. Note that the real-tree path is deliberately exercised by a
    pin, because a pack that parses a hand-built dict but dies on reality is the L7 trap:
    a pin that supplies its own inputs tests the mechanism, not the wiring.
    """
    rx = _word_re(term)
    occ: List[Dict[str, Any]] = []
    total = 0
    truncated = False
    off_plane: Dict[str, int] = {}

    if corpus is None:
        root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        root = os.path.dirname(root) if os.path.basename(root) == "core" else root
        files: Iterable[Tuple[str, str]] = (
            (p, _read(p)) for p in _iter_repo_files(root))
        rel_to = root
    else:
        files = list(corpus.items())
        rel_to = None

    want = set(planes)
    # Gather EVERYTHING first, grouped by file, then sample. Capping during the walk keeps
    # whatever sorts first, which is truncation rather than sampling -- measured: 'open' at
    # cap 120 reached the fan as 26 of 163 files, with the CLI supplying 47 of them, so
    # the honest answer to that sample was "it means opening a file".
    per_file: Dict[str, List[Dict[str, Any]]] = {}
    for path, text in files:
        if not text:
            continue
        shown = (os.path.relpath(path, rel_to) if rel_to else path).replace("\\", "/")
        # A caller-supplied corpus is taken at its word: it was assembled deliberately, so
        # second-guessing its membership would silently discard a test's fixture.
        plane = _plane_of(shown) if corpus is None else "source"
        for i, line in enumerate(text.splitlines(), start=1):
            if not rx.search(line):
                continue
            if plane not in want:
                key = plane or "out-of-corpus"
                off_plane[key] = off_plane.get(key, 0) + 1
                continue
            total += 1
            per_file.setdefault(shown, []).append(
                {"file": shown, "line": i, "plane": plane, "text": line.strip()[:400]})

    if total <= max_occurrences:
        for f in sorted(per_file):
            occ.extend(per_file[f])
    else:
        # ROUND-ROBIN across files: every file contributes its first occurrence before any
        # file contributes its second. A term living in 163 files then reaches the helper as
        # 163 files, which is what the question is actually about.
        truncated = True
        order = sorted(per_file)
        depth = 0
        while len(occ) < max_occurrences:
            progressed = False
            for f in order:
                if depth < len(per_file[f]):
                    occ.append(per_file[f][depth])
                    progressed = True
                    if len(occ) >= max_occurrences:
                        break
            if not progressed:
                break
            depth += 1
        occ.sort(key=lambda o: (o["file"], o["line"]))

    blob = _render_blob(term, occ)
    blind = [
        f"PLANE: this pack contains {sorted(want)} only. A term can be coherent in source "
        f"and forked in docs, or the reverse, and this pack cannot see the difference",
        "occurrences are LINE-level: a fork visible only across a function boundary or in "
        "code shape rather than in a line containing the token is invisible here",
        "comments, docstrings and code are not distinguished within a plane -- a term "
        "discussed in a comment ranks the same as one executed",
        "case-insensitive matching, so a deliberate Type/value casing distinction reads as "
        "one term here",
    ]
    if off_plane:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(off_plane.items()))
        blind.insert(1, f"EXCLUDED BY PLANE, not absent: {detail}. Vendored trees "
                        f"(ComfyUI-Zluda et al) are a different project's vocabulary; "
                        f"history/research record the past. Counted here so the exclusion "
                        f"is a stated decision rather than a silent one")
    if truncated:
        dropped = total - len(occ)
        n_files = len({o["file"] for o in occ})
        blind.insert(0, f"CAPPED: showing {len(occ)} of {total} occurrences -- {dropped} "
                        f"dropped. SAMPLED round-robin across files, so all {n_files} of "
                        f"{len(per_file)} files with a usage are represented rather than "
                        f"the first few alphabetically; but per-file DEPTH is clipped, so a "
                        f"sense that only appears in one file's 12th usage is invisible. "
                        f"Any rate from this pack is a rate over the sample")
    return EvidencePack(term=term, occurrences=occ, blob=blob, sha=_sha(blob),
                        truncated=truncated, blind=blind)


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, UnicodeError):
        return ""


def _render_blob(term: str, occ: Sequence[Dict[str, Any]]) -> str:
    """The exact bytes a helper reads. Rendering is part of the address on purpose: two
    curators given the same occurrences but a different rendering did NOT read the same
    thing, and the gate should catch that too."""
    lines = [f"=== EVIDENCE: word-boundary usages of {term!r} ===", ""]
    for o in occ:
        tag = f"[{o['plane']}] " if o.get("plane") else ""
        lines.append(f"{tag}{o['file']}:{o['line']}: {o['text']}")
    return "\n".join(lines) + "\n"


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


# ============================================================ tier 0b: junction evidence
@dataclass
class JunctionPack:
    """Sites where a term is WRITTEN paired with sites where it is READ.

    A separate pack type rather than a flag on EvidencePack, because it answers a different
    question and a reader must never mistake one for the other. Enumerating senses and
    detecting whether senses MEET are different measurements with different blindness, and
    merging them under one name would be this repo's dominant bug class committed inside
    the tool built to find it.
    """
    term: str
    junctions: List[Dict[str, Any]] = field(default_factory=list)
    blob: str = ""
    sha: str = ""
    blind: List[str] = field(default_factory=list)


#: A term is WRITTEN when it is assigned, stored under a key, or returned as a field.
_WRITE_PATTERNS = (
    r"\[[\"']{t}[\"']\]\s*=",          # out["drained"] = ...
    r"\b{t}\s*=(?!=)",                  # drained = ...
    r"[\"']{t}[\"']\s*:",              # {"drained": ...}
    r"\bdef\s+{t}\b",                   # def drained(...)
    r"\bself\.{t}\s*=(?!=)",           # self.drained = ...
)
#: A term is READ when its value is consumed in a condition, an access, or an argument.
_READ_PATTERNS = (
    r"\[[\"']{t}[\"']\]\s*(?!=)",      # rep["drained"] > 0
    r"\.get\(\s*[\"']{t}[\"']",        # d.get("drained")
    r"\bif\s+.*\b{t}\b",                # if drained ...
    r"\breturn\s+.*\b{t}\b",
    r"\b{t}\s*[<>!=]=",                 # drained == ...
)


def _code_part(line: str) -> str:
    """The executable part of a line, with any trailing comment removed.

    A comment DESCRIBES a write; it does not perform one. Counting `# out["x"] = 1` as an
    assignment is how prose becomes evidence of a mechanism, and it is the same class as
    the text-scanning pin trap: the clearest code is the most heavily commented, so a
    detector blind to comments finds the most defects exactly where the author explained
    themselves best.

    Deliberately crude -- a '#' inside a string literal truncates the line early. That
    biases toward MISSING a write, never toward inventing one, which is the right direction
    for a candidate generator.
    """
    s = line.split("#", 1)[0]
    return s if s.strip() else ""


def _matches(patterns: Sequence[str], term: str, line: str) -> bool:
    code = _code_part(line)
    if not code:
        return False
    t = re.escape(term)
    return any(re.search(p.format(t=t), code) for p in patterns)


def junction_pack(term: str, *, corpus: Optional[Dict[str, str]] = None,
                  root: Optional[str] = None, planes: Sequence[str] = ("source",),
                  context: int = 2, max_sites: int = 40,
                  exclude_self: bool = True) -> JunctionPack:
    """Pair write-sites with read-sites, carrying surrounding lines.

    WHY THIS SHAPE. The first live sift round handed every hat a one-line-per-file breadth
    sample. The junction hat then voted NO_FORK on `drained` -- a term whose three cursor
    families demonstrably collide -- because the evidence could not show a producer and a
    consumer in the same frame. That verdict was a property of the sample, not of the code.

    The pairing here is DELIBERATELY CRUDE and says so in blind: it is lexical, so a write
    through an alias or a read via **kwargs is invisible. It proposes candidate junctions
    for a reader to adjudicate; it does not prove that two sites are the same concept.
    """
    files = _collect(corpus, root, planes)
    if exclude_self:
        # THE INSTRUMENT MUST NOT MEASURE ITSELF. This module holds _WRITE_PATTERNS and
        # _READ_PATTERNS as string literals, so a lexical scan finds them and reports
        # sift.py as a reader of whatever term it is hunting. The first live run's very
        # first crossing for `drained` was bifrost_pull.py -> core/coord/sift.py, pointing
        # at a regex. Self-reference is not a junction.
        files = [(f, t) for f, t in files if not f.endswith("core/coord/sift.py")]
    writes: List[Dict[str, Any]] = []
    reads: List[Dict[str, Any]] = []

    for shown, text in files:
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            rec = {"file": shown, "line": i, "text": line.strip()[:300],
                   "context": [l.strip()[:200]
                               for l in lines[max(0, i - 1 - context): i + context]]}
            if _matches(_WRITE_PATTERNS, term, line):
                writes.append(rec)
            elif _matches(_READ_PATTERNS, term, line):
                reads.append(rec)

    junctions: List[Dict[str, Any]] = []
    if writes and reads:
        # One junction record per (write-file, read-file) crossing, capped. A crossing
        # BETWEEN files is the interesting case: same-file write/read is usually one author
        # holding one meaning, which is precisely the case that does NOT fork.
        by_wfile: Dict[str, List[Dict]] = {}
        for w in writes:
            by_wfile.setdefault(w["file"], []).append(w)
        by_rfile: Dict[str, List[Dict]] = {}
        for r in reads:
            by_rfile.setdefault(r["file"], []).append(r)
        for wf in sorted(by_wfile):
            for rf in sorted(by_rfile):
                if len(junctions) >= max_sites:
                    break
                junctions.append({
                    "writes": by_wfile[wf][:3], "reads": by_rfile[rf][:3],
                    "same_file": wf == rf,
                    "crossing": f"{wf} -> {rf}",
                })

    blob = _render_junction_blob(term, junctions)
    blind = [
        "LEXICAL pairing: a write through an alias, a **kwargs read, or a value passed "
        "through a helper is INVISIBLE here. These are CANDIDATE junctions for a reader to "
        "adjudicate, never proof that two sites carry the same concept",
        "a crossing is listed per (write-file, read-file) pair, so one busy writer produces "
        "many rows -- row count is NOT a severity measure",
        f"write patterns are assignment-shaped and read patterns are access-shaped; a term "
        f"that travels only as a bare positional argument matches neither",
    ]
    if not junctions:
        why = ("no writer/reader pair found -- NO JUNCTION in this evidence. That is not "
               "proof of absence: the pairing is lexical (see above), so this reads as "
               "UNKNOWN rather than as 'the senses never meet'")
        blind.insert(0, why)
    elif not any(not j["same_file"] for j in junctions):
        blind.insert(0, "every junction found is SAME-FILE: one author holding one meaning, "
                        "which is the shape that does NOT fork. Cross-file crossings are the "
                        "ones worth reading")
    return JunctionPack(term=term, junctions=junctions, blob=blob, sha=_sha(blob),
                        blind=blind)


def _collect(corpus, root, planes) -> List[Tuple[str, str]]:
    """Shared file walk for both pack types, so they cannot drift apart on membership."""
    out: List[Tuple[str, str]] = []
    if corpus is not None:
        return [(p, t) for p, t in corpus.items()]
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = os.path.dirname(root) if os.path.basename(root) == "core" else root
    want = set(planes)
    for p in _iter_repo_files(root):
        shown = os.path.relpath(p, root).replace("\\", "/")
        if _plane_of(shown) in want:
            out.append((shown, _read(p)))
    return out


def _render_junction_blob(term: str, junctions: Sequence[Dict[str, Any]]) -> str:
    lines = [f"=== JUNCTION CANDIDATES for {term!r}: where it is WRITTEN vs READ ===", ""]
    if not junctions:
        lines.append("(none found -- see BLIND; the pairing is lexical)")
    for j in junctions:
        lines.append(f"--- {j['crossing']}{'  [same file]' if j['same_file'] else ''}")
        for w in j["writes"]:
            lines.append(f"  WRITE {w['file']}:{w['line']}: {w['text']}")
        for r in j["reads"]:
            lines.append(f"  READ  {r['file']}:{r['line']}: {r['text']}")
        lines.append("")
    return "\n".join(lines) + "\n"


# ========================================================================= tier 1: hats
#: Each hat asks what the code DOES. L1, measured at T207: five grounded factual lookups
#: were correct 5/5 with citations, while ONE normative question came back confidently
#: wrong -- with real, accurate citations -- by equivocating on the word 'wakeable'. The
#: same model got it right the day before when the question was decomposed. So: the
#: decomposition does the work, and should/better/more/fewer is the tell you are in the
#: danger zone. The jester is the deliberate exception, and is read as an argument.
DEFAULT_HATS: Dict[str, str] = {
    "outsider": (
        "You have no knowledge of this project. Using ONLY the evidence given, list what "
        "distinct THINGS this word refers to. Group the lines by the thing they describe. "
        "If two groups are actually the same thing described differently, say so. If you "
        "cannot tell, say UNCLEAR and name what you would need."),
    "junction": (
        "Find the places where two different uses of this word MEET: a value produced "
        "under one use and consumed under another, a shared dict key or Redis key, a "
        "comparison, an argument crossing a module boundary. For each, cite both file:line "
        "sites. If the uses never meet in this evidence, say NO JUNCTION FOUND."),
    "linguist": (
        "For each occurrence, classify the word's part of speech and sense: ordinary "
        "English polysemy (the same word doing normal verb/noun duty) versus a SPECIALISED "
        "sense that carries project-specific meaning. Report the count in each class and "
        "quote one line per sense."),
    "historian": (
        "Order the occurrences by what they suggest about arrival: which uses look like an "
        "older layer and which look newer (naming style, adjacent vocabulary, comment "
        "references to task ids). State what in the evidence supports each guess. Do not "
        "guess dates you cannot support."),
    "adversary": (
        "Argue that this word has exactly ONE coherent meaning here. Construct the "
        "strongest single-sense reading that accounts for every line. Then state which "
        "specific lines your reading fails to explain, if any. Your job is to make the "
        "fork claim work for its money."),
    "jester": (
        "What is the dumbest possible misreading of this word by someone new, and would "
        "the code survive it? Then argue -- seriously -- that the multiple meanings are a "
        "FEATURE worth keeping. A defence that collapses under its own evidence is the "
        "strongest confirmation available; a defence that holds is a finding of its own."),
}

#: RETIRED 2026-08-07 by ablation (pre-registered 93edb7c, result 7fc9d35), kept as a record
#: rather than deleted so the reason survives and nobody re-adds it reasonably.
#:
#: `economist` asked where a confusion between senses would produce a WRONG RESULT rather
#: than a confusing read. It measured 1/3 precision on the hand-adjudicated terms -- it
#: reached FORK on all three, including BOTH false positives in the cost-blind sample -- with
#: the second-highest uniqueness in the pool and ZERO marginal contribution. That combination
#: is the whole finding: a hat rewarded by rarity and refuted by truth. Its characteristic
#: output was precisely the lone-hat FORK that CONSENSUS_FLOOR now exists to suppress, so it
#: was manufacturing the defect another mechanism had to clean up.
#:
#: If someone wants a cost lens back, the honest version asks a DESCRIPTIVE question ("which
#: of these sites pass a value produced under one sense into code that reads it under
#: another") rather than a speculative one about hypothetical damage -- the speculative
#: framing is what made it a confabulation engine.
RETIRED_HATS = {
    "economist": "1/3 precision, 0 marginal contribution, generated both false positives "
                 "in the cost-blind sample (ablation 2026-08-07)",
}

_ANSWER_CONTRACT = (
    "\n\nANSWER FORMAT, strictly:\n"
    "VERDICT: FORK | NO_FORK | UNCLEAR\n"
    "SENSES: one line per distinct sense, each with ONE citation as file:line\n"
    "WHY: at most 4 lines, each citing file:line\n"
    "BLIND: what this evidence cannot show you\n\n"
    "Cite only file:line pairs present in the evidence. If the evidence does not support "
    "an answer, say UNCLEAR -- an abstention is a correct answer here and is preferred to "
    "a confident guess."
)


def hat_prompt(hat: str, pack: EvidencePack) -> str:
    """The question a single tier-1 helper answers. Evidence is passed separately (as a
    file) so the blob the helper reads is exactly the blob we hashed."""
    if hat not in DEFAULT_HATS:
        raise KeyError(f"unknown hat {hat!r}; known: {sorted(DEFAULT_HATS)}")
    return (f"The word under examination is: {pack.term!r}\n\n"
            f"{DEFAULT_HATS[hat]}{_ANSWER_CONTRACT}")


# ====================================================================== tier 2: curators
#: What a curator is allowed to hand upward. The two clauses that matter:
#:
#: POINTERS, NOT JUDGMENTS -- the discipline that makes the whole compression safe. "These
#: 4 of 20 sites write cursors, at these lines" is verifiable in seconds; "the cursor
#: design is fine" is a judgment the reader must redo the work to check. A tier that
#: returns judgments has not saved the reader any work, it has only hidden it.
#:
#: DROPPED -- no silent caps, applied to compression rather than to truncation. A curator
#: that discards a minority reading without saying so manufactures consensus, and consensus
#: is exactly the thing this pipeline is built to distrust.
CURATOR_CONTRACT = (
    "You are reading several independent analyses of ONE word. Each was written by a "
    "helper wearing a different hat, and every one of them was given the SAME evidence.\n\n"
    "Produce a dossier. RETURN POINTERS, NOT JUDGMENTS: 'these 4 sites write X, at these "
    "file:line' is checkable in seconds, while 'the design is fine' forces the reader to "
    "redo your work. Cite file:line from the analyses; do not invent citations.\n\n"
    "FORMAT, strictly:\n"
    "VERDICT: FORK | NO_FORK | UNCLEAR\n"
    "TALLY: FORK=<n> NO_FORK=<n> UNCLEAR=<n>  -- how many of the analyses reached each "
    "verdict. Count them; do not estimate.\n"
    "SENSES: one line per distinct sense, each with one file:line\n"
    "DISSENT: where the analyses disagreed with EACH OTHER, naming the hats\n"
    "DROPPED: what you did NOT carry forward, and why. A minority reading you discarded "
    "silently would manufacture consensus -- say it here instead.\n"
    "BLIND: what none of these analyses could see\n"
)

_TALLY_RE = re.compile(r"^\s*TALLY\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def parse_tally(answer: str) -> Dict[str, int]:
    """Recover the vote split a curator reported. {} when it reported none.

    The TALLY line exists because the first cost-blind sample's two false positives were
    both a lone hat promoted over a five-hat consensus, and the winning LABEL alone could
    not show that. An empty dict means UNKNOWN margin, never a low one.
    """
    m = _TALLY_RE.search(answer or "")
    if not m:
        return {}
    out: Dict[str, int] = {}
    for k, n in re.findall(r"(FORK|NO_FORK|UNCLEAR)\s*=\s*(\d+)", m.group(1), re.IGNORECASE):
        out[k.upper()] = int(n)
    return out


def curator_prompt(term: str, analyses: Sequence[Dict[str, str]]) -> Tuple[str, str]:
    """Build a curator's prompt and the address of what it read.

    Returns (prompt, evidence_sha). The sha covers the ANALYSES BUNDLE -- the bytes this
    curator actually consumed -- so two curators over the same bundle provably read the
    same thing and their disagreement is about curation rather than about input. That is
    the gate in compare_dossiers, and it is the whole reason the sha is computed here
    rather than being copied down from tier 0.
    """
    parts = [f"=== ANALYSES OF {term!r} ==="]
    for a in analyses:
        parts.append(f"\n--- hat: {a['hat']} ---\n{a['answer']}")
    bundle = "\n".join(parts) + "\n"
    prompt = f"{bundle}\n\n{CURATOR_CONTRACT}"
    return prompt, _sha(bundle)


#: A positive verdict must clear this share of the hats that voted, or it is CONTESTED.
#: Set from the measured failure rather than from taste: the two false positives in the
#: first cost-blind sample rested on 1 of 7 and 1 of 6 hats (0.14 and 0.17), while the one
#: genuine find had 5 of 7 (0.71). Anything strictly above a third clears.
CONSENSUS_FLOOR = 1 / 3


def settle_verdict(dossier: Dict[str, Any]) -> str:
    """The verdict a dossier is entitled to, given the margin it won by.

    MEASURED, first cost-blind sample (pre-registered at da5fbc7): two of three FORK
    verdicts were false positives, and both were a LONE hat promoted over a five- or
    six-hat NO_FORK consensus. `behaviour` and `remain` are ordinary English polysemy that
    6-of-7 and 5-of-7 hats respectively rejected, and the curator carried the minority
    forward anyway -- disclosing it honestly in DROPPED, but carrying it.

    The cost was not cosmetic. Untriaged, that sample showed a +43 point spread effect;
    triaged it showed +14, and those sit on OPPOSITE SIDES of a pre-registered 20-point
    line. A tier that reports the winning label without the margin will keep doing this.

    A MISSING TALLY IS NOT A LOW ONE. With no vote data the margin is UNKNOWN, and the
    verdict passes through untouched rather than being downgraded on an absence -- inferring
    weakness from silence is the same error as inferring absence from a blind instrument.
    """
    v = str(dossier.get("verdict", "")).upper()
    tally = dossier.get("tally") or {}
    if v not in {"FORK"} or not tally:
        return v or "UNCLEAR"
    total = sum(int(n) for n in tally.values() if isinstance(n, (int, float)))
    if not total:
        return v
    share = int(tally.get(v, 0)) / total
    return v if share > CONSENSUS_FLOOR else "CONTESTED"


def parse_verdict(answer: str) -> str:
    """Pull VERDICT off an answer, tolerantly. UNCLEAR when absent -- never a guess.

    Three states here too: reading a missing verdict as NO_FORK would turn 'the helper did
    not answer' into 'the helper found nothing', which is the UNKNOWN-collapses-to-negative
    failure that T155 cost a whole seat-hunt to learn.
    """
    if not answer:
        return "UNCLEAR"
    m = re.search(r"^\s*VERDICT\s*:\s*([A-Z_]+)", answer, re.MULTILINE | re.IGNORECASE)
    if not m:
        return "UNCLEAR"
    v = m.group(1).strip().upper()
    return v if v in {"FORK", "NO_FORK", "UNCLEAR"} else "UNCLEAR"


def curator_pairs(term: str, hats: Sequence[str],
                  evidence_sha: str = "") -> List[Tuple[Dict, Dict]]:
    """Pair hats WITHIN one term.

    claude#42d00626's point 2, and it is a computability constraint rather than a
    preference: two curators wearing different hats on DIFFERENT terms cannot be diffed at
    all, while two on the SAME term produce a diff whose disagreements are located. The
    result is dissent that points at a word instead of at a methodology.

    Pairs are adjacent-disjoint (0,1), (2,3), ... so each hat is used once per term: an
    overlapping scheme would double-count a single hat's idiosyncrasy as agreement.
    """
    hs = list(hats)
    out: List[Tuple[Dict, Dict]] = []
    for i in range(0, len(hs) - 1, 2):
        a = {"term": term, "hat": hs[i], "evidence_sha": evidence_sha}
        b = {"term": term, "hat": hs[i + 1], "evidence_sha": evidence_sha}
        out.append((a, b))
    return out


# ====================================================================== tier 3: compare
def compare_dossiers(dossiers: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Diff same-term dossiers; return dissent FIRST, and gate the flip rate on identity.

    THE GATE. Before any rate is computed, every dossier for a term must carry the same
    evidence_sha. If they do not, the function refuses and names the diverging hashes.
    Silence here would reproduce T216 one tier up: five well-formed answers about material
    nobody verified they received.

    THE FLIP RATE is dissenting-pairs / total-pairs. It is the curation tier's artifact
    rate in the same sense L2 measured the evidence tier's -- with the difference that a
    disagreement here may also be real ambiguity, which is why the output is a TABLE the
    reader adjudicates, never a verdict.
    """
    by_term: Dict[str, List[Dict[str, Any]]] = {}
    for d in dossiers:
        by_term.setdefault(d["term"], []).append(d)

    # --- identity gate, before anything is counted
    diverged: List[str] = []
    for term, ds in sorted(by_term.items()):
        shas = sorted({str(d.get("evidence_sha", "")) for d in ds})
        if len(shas) > 1:
            diverged.append(f"{term}: {' vs '.join(shas)}")
    if diverged:
        return {
            "flip_rate": None,
            "refused": ("evidence identity failed -- these curators did not read the same "
                        "bytes, so any disagreement between them measures INPUT DIVERGENCE, "
                        "not curation. Diverging hashes: " + "; ".join(diverged)),
            "dissents": [], "agreements": [],
            "triage_required": False, "triage_reason": "",
            "render_order": ["refused"],
            "blind": ["no comparison was performed; nothing here is a finding"],
        }

    dissents: List[Dict[str, Any]] = []
    agreements: List[Dict[str, Any]] = []
    undecided: List[Dict[str, Any]] = []
    for term, ds in sorted(by_term.items()):
        verdicts = {str(d.get("verdict", "")).upper() for d in ds}
        row = {"term": term,
               "verdicts": sorted(verdicts),
               "hats": sorted(str(d.get("hat", "")) for d in ds),
               "evidence_sha": str(ds[0].get("evidence_sha", "")),
               "dossiers": ds}
        # A term where EVERY curator abstained is neither agreement nor dissent -- nobody
        # decided anything. Counting it as agreement (which this did until the T221 hedging
        # sweep) is the same lie as reading UNKNOWN as a negative, and it let an abstention
        # silently improve the flip rate this function exists to report.
        if verdicts <= {"UNCLEAR", ""}:
            undecided.append(row)
        elif len(verdicts) > 1:
            dissents.append(row)
        else:
            agreements.append(row)

    # PER-DECISION denominator. Leaving abstentions in it would let the tier improve its own
    # artifact rate by declining to answer -- hedging made profitable in the one metric meant
    # to catch bad curation.
    n_deciding = len(dissents) + len(agreements)
    rate = (len(dissents) / n_deciding) if n_deciding else None

    n_pairs = n_deciding
    triage = (rate is not None and n_pairs >= IMPLAUSIBLE_MIN_N
              and rate >= IMPLAUSIBLE_DISSENT_RATE)
    reason = ""
    if triage:
        reason = (
            f"{len(dissents)}/{n_pairs} pairs ({rate:.0%}) disagree, at or above the "
            f"{IMPLAUSIBLE_DISSENT_RATE:.0%} alarm. L3 says an implausible base rate points "
            f"at the harness -- BUT ONLY AS A TRIGGER TO TRIAGE: hand-check a sample before "
            f"concluding anything, in EITHER direction. The 408-way docstring audit's "
            f"implausible 37% turned out to be partly real, and discarding it on the prior "
            f"would have thrown away genuine defects. Findings below are intact."
        )

    return {
        "flip_rate": rate,
        "refused": None,
        "dissents": dissents,
        "agreements": agreements,
        "undecided": undecided,
        "triage_required": triage,
        "triage_reason": reason,
        "render_order": ["dissents", "triage", "agreements", "undecided"],
        "blind": [
            (f"{len(undecided)} term(s) UNDECIDED -- every curator abstained, so they are in "
             f"NEITHER the agreement list nor the flip-rate denominator. Two people saying "
             f"'I do not know' is a shared blind spot, not consensus"
             if undecided else "no term was left undecided by every curator"),
            "a shared blind spot produces AGREEMENT, so agreement here is weaker evidence "
            "than disagreement -- two curators can be identically wrong",
            "verdict equality is compared as a STRING: two dossiers can agree on FORK while "
            "disagreeing entirely about which senses forked",
            "the flip rate measures the curation tier only; the evidence tier's own "
            "artifact rate is a separate measurement (L2) and is not folded in here",
        ],
    }


# ========================================================================== the aggregate
def summarise(*, n: int, n_ok: int, blind: Sequence[str],
              ref: Optional[str] = None, **detail) -> BoundaryOutcome:
    """Three states, never two.

    ask_many's docstring bought this line: "a binary fan verdict discards the partial
    result, which is exactly how nine tasks, two findings reads as failure instead of as
    two findings." Callers must branch failed -> partial -> done in that order, because
    .ok includes partials -- a trap that struck twice in one hour on 2026-08-05.
    """
    d = dict(detail); d.update(n=n, n_ok=n_ok, blind=list(blind))
    if n_ok <= 0:
        return BoundaryOutcome.failed(
            f"every one of {n} branches failed -- that is a configuration state to check, "
            f"not {n} independent model failures", ref=ref, **d)
    if n_ok < n:
        return BoundaryOutcome.partially(
            f"{n_ok} of {n} branches landed; the {n - n_ok} missing are UNKNOWN, not "
            f"negative", ref=ref, **d)
    return BoundaryOutcome.done(ref=ref, **d)
