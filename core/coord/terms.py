"""terms -- the vocabulary a codebase TALKS ABOUT, as a comparable set (T214).

THE INSTRUMENT W133 ASKED FOR. That wish (filed 2026-08-07, and the oldest recurring
theme in the repo -- restated roughly every two weeks since 2026-06-19) wants a guard on
FORKED SEMANTICS: one concept implemented by several mechanisms that quietly disagree.
W134 then corrected its premise -- the naming guard already EXISTS and works
(check_boundaries: no-duplicate-class-names, no-duplicate-module-basename). It catches
HOMONYMS, two things sharing one identifier, which is greppable.

None of the four violations that motivated it were homonyms:

    drained    three different cursor keys, no shared token anywhere
    unread     _unread_count on one side, the consume door on the other
    wakeable   NOT AN IDENTIFIER AT ALL -- it exists only in prose and reasoning
    fixed      one identifier, one definition, two unshared assumptions

So this extractor deliberately does NOT read identifiers. It reads what the codebase
TALKS ABOUT -- comments and docstrings -- because that is where a concept lives before it
has a name, and `wakeable` cost six turns while never appearing as a token.

SPREAD, NOT FREQUENCY, IS THE SIGNAL. A word used two hundred times inside one module is
that module's local jargon and perfectly healthy. A word appearing in six DIFFERENT files
is shared vocabulary -- and shared vocabulary with no single definition is exactly how
`drained` came to mean three things at once.

IT PRODUCES CANDIDATES, NEVER VIOLATIONS. Most undefined words are fine. This is the cheap
wide tier of the pattern Daniil named: the index proposes, the fan disposes. Claiming a
violation from spread alone would be the confident-inference failure this entire arc has
been about.
"""
from __future__ import annotations

import ast
import os
import re
from typing import Any, Dict, Optional, Set

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: The four terms that MEASURABLY forked and cost real turns (2026-08-06/07). They are
#: this module's calibration set: any scoring change must be checked against them before
#: being believed. Known positives beat intuition about what "looks like" jargon.
KNOWN_FORKED = ("drained", "unread", "wakeable", "fixed")

BLIND = [
    "MEASURED NEGATIVE RESULT: ranking by rarity x subsystem-spread does NOT find forked "
    "semantics. Calibrated against the four known positives, they landed at the 71st, "
    "94th, 76th and 13th percentile -- three of four in the bottom quartile, i.e. the "
    "score is anti-correlated with truth. Do not trust this ranking as a detector",
    "WHY, and it inverts the intuition: forked words are LOW-spread. `drained` lives in "
    "6 files and `wakeable` in 3. They fork BECAUSE few authors touched them and each "
    "imported their own everyday meaning; a word in 100 files has been read by everyone "
    "and its meaning was forced into agreement. High spread means the meaning got "
    "socialised",
    "the four positives are also ordinary ENGLISH words used in specialised senses, "
    "which is exactly why they fork -- so no rarity filter can separate them from "
    "English, because they ARE English. Detection is a MEANING-level job (the fan); this "
    "module's honest role is to supply the CORPUS, not the ranking",
    "these are CANDIDATES, never a violation: a word discussed across files with no "
    "LEXICON entry is worth a LOOK, and most undefined words are perfectly fine",
    "extraction is heuristic -- comments and docstrings only, stopword-filtered, so it "
    "misses concepts discussed only in code shape and invents nothing about meaning",
    "spread counts FILES, not occurrences: local jargon used heavily in one module is "
    "invisible here by design, and a term used once in six files outranks one used two "
    "hundred times in one",
    "a term present in LEXICON is treated as defined without checking that the code "
    "AGREES with that definition -- this finds undefined vocabulary, not wrong definitions",
]

#: Words that are structure rather than vocabulary. Deliberately generous: a false drop
#: costs one candidate, a false keep costs the reader's attention on every run.
_STOP = frozenset("""
the and for that this with from into onto upon which where when what whom whose have has
had will would could should must been being were are was but not you your yours our ours
its it's they them their then than there here also just very much more most some such
each other another about above after again against because before below between during
under while only same over both any all can may might make makes made use uses used using
does did done doing get gets got set sets setting put puts run runs ran call calls called
return returns returned value values none true false self args kwargs param params
function method class module file files line lines code test tests string int bool list
dict tuple object type types name names key keys item items data result results
one two three first second next last new old same via per etc ie eg
""".split())

_WORD = re.compile(r"[a-z][a-z_]{3,}")
_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache",
              "artifacts", "docs", "research", "chronicles"}


def _prose_of(src: str) -> str:
    """Comments plus docstrings -- the places a codebase discusses a concept rather than
    naming one. Identifiers are deliberately excluded: `wakeable` never was one."""
    out = []
    for line in src.splitlines():
        if "#" in line:
            out.append(line.split("#", 1)[1])
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return " ".join(out)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            doc = ast.get_docstring(node)
            if doc:
                out.append(doc)
    return " ".join(out)


def score(rec: Dict[str, Any], n_files: int) -> float:
    """How much does this term look like SHARED VOCABULARY rather than English?

    First live run ranked by raw spread and returned 2,982 candidates topped by "every",
    "read", "live", "path" -- common words appearing in 123 of ~200 files. A term that
    appears EVERYWHERE carries no information, which is exactly what inverse document
    frequency measures, so raw spread was the wrong statistic.

    Two factors, multiplied:
      * IDF -- rarity across files. A word in 60% of files is English; one in 4% is jargon.
      * DIRECTORY spread -- a concept discussed in core/comm AND core/coord AND
        core/learning crosses subsystem boundaries, which is what makes a shared
        definition matter. A word confined to one package is that package's local jargon
        however often it appears.
    """
    import math
    files = max(1, int(rec.get("files", 1)))
    idf = math.log(max(2, n_files) / files)
    return round(idf * max(1, len(rec.get("dirs") or ())), 4)


def extract(root: Optional[str] = None, min_files: int = 3,
            subdir: str = "") -> Dict[str, Dict[str, Any]]:
    """term -> {files, hits, dirs, where}. One unreadable file costs that file, never
    the scan."""
    base = os.path.join(root or _ROOT, subdir) if subdir else (root or _ROOT)
    seen: Dict[str, Dict[str, Any]] = {}
    n_files = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8") as fh:
                    prose = _prose_of(fh.read())
            except (OSError, UnicodeDecodeError):
                continue
            rel = os.path.relpath(p, base).replace("\\", "/")
            top = rel.split("/")[0] if "/" in rel else "."
            n_files += 1
            for w in set(_WORD.findall(prose.lower())):
                if w in _STOP or w.endswith("_"):
                    continue
                rec = seen.setdefault(w, {"files": 0, "hits": 0, "where": [],
                                          "dirs": set()})
                rec["files"] += 1
                rec["hits"] += prose.lower().count(w)
                rec["dirs"].add(top)
                if len(rec["where"]) < 8:
                    rec["where"].append(rel)
    out = {}
    for w, r in seen.items():
        if r["files"] < int(min_files):
            continue
        r["dirs"] = sorted(r["dirs"])
        r["score"] = score(r, n_files)
        out[w] = r
    return out


def lexicon_terms(path: Optional[str] = None) -> Set[str]:
    """Terms the LEXICON actually defines: headings, backticked heads, and bold leads."""
    p = path or os.path.join(_ROOT, "docs", "LEXICON.md")
    try:
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return set()
    out: Set[str] = set()
    for pat in (r"^#{1,6}\s+`?([A-Za-z][\w .\-/]*)`?\s*$",
                r"^\s*[-*]?\s*\*\*([A-Za-z][\w .\-/]*)\*\*",
                r"^\s*[-*]\s+`([A-Za-z][\w.\-/]*)`"):
        for m in re.findall(pat, text, re.M):
            for token in re.split(r"[ /]", str(m).strip()):
                token = token.strip("`*_.-").lower()
                if len(token) > 3:
                    out.add(token)
    return out


def _terms_code(**_) -> Set[str]:
    """Shared vocabulary in core/: discussed in 3+ distinct files."""
    return set(extract(min_files=3, subdir="core").keys())


def _terms_lexicon(**_) -> Set[str]:
    return lexicon_terms()


def register() -> None:
    """Attach to the compare registry so vocabulary becomes diffable like any other
    domain: `compare terms:code terms:lexicon` is the W133 query."""
    from core.coord import compare as cmp_mod
    cmp_mod.DOMAINS.setdefault("terms:code", (_terms_code, "term"))
    cmp_mod.DOMAINS.setdefault("terms:lexicon", (_terms_lexicon, "term"))


register()
