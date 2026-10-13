"""The licence line, measured: no file git would commit may share a run of 12 tokens with any shader in the private
corpus, except breaches declared as pre-existing in the baseline, which are measured every run and may only shrink.

    py -m arsenal shader licence-line            # scan the tree; exit 1 on a breach or a failure to measure
    py -m arsenal shader licence-line --json     # the full report: what was scanned, every hit and its verdict

WHY. The corpus under state/arsenal/shaders/corpus/ is other people's code (most of it CC BY-NC-SA) and this repository
is public under Apache-2.0. Techniques transfer; code does not. A rule kept by memory fails on the first tired night, so
this module measures it, and the house library's Apache-2.0 licence (build-spec rulings 2 and 8, 2026-10-13) rests on
that measurement rather than on anyone's care.

WHAT IS COMPARED. Every pass of every corpus shader (shaders/<id>/<pass>.glsl) becomes a set of 12-token shingles: its
code with comments stripped, plus the windows of commented-out code (a window whose comment text holds at least two of
`;`, an assignment and `(`), because uncommenting someone's code does not make it ours. A token is an identifier
(kept as written), a number (kept, because the constants carry the craft; only the spelling is normalised, so `1.`,
`1.0` and `1.00` are one token), or an operator.

WHAT IS SCANNED (judge's ruling a, 2026-10-13). Every file git would commit: `git ls-files` plus the untracked files
that are not ignored, minus the top-level state/ folder, read with read-only git commands. The files under state/ that
git would commit are listed in the report every run (not scanned, per the ruling), and one under the corpus folder fails
the scan. Every file is read whatever its extension: UTF-32 or UTF-16 when a byte-order mark says so (UTF-32 checked
first, since its mark begins with UTF-16's), UTF-8 (with or without its mark), else cp1252 with replacement. A file
with a NUL in its first 8000 bytes is binary by git's own rule: it is counted as binary and its printable text is still
read, so UTF-16 without a mark or a text file with one stray NUL hides nothing. A file that cannot be read (a mark on
bytes that are not that encoding, or that decode to NUL characters) fails the scan by name. A tree that is not the top
of a git work tree (a test's temp folder, a calibration folder under state/) is walked instead: every file except the
top-level state/ and .git folders.

HOW A FILE IS READ. Three times: without its comments, so a copy split by an inserted comment is still one run; with
them, so code pasted inside a comment is still code; and, when the file holds a block comment, with every block comment
read as code (its markers blanked, every `//` in it dropped to the end of its line) and every `//` comment dropped,
because the comment reader cannot see quotes and a `/*` inside a glob path, a MIME type or '*/*' opens a false comment
that would otherwise swallow the rest of the file. String quotes
and the glue between JS string pieces are dropped, and a `\\n` escape is a line break, so GLSL written as a JS string,
an array of lines or a one-line JSON string reads as GLSL (a `//` comment inside such a string ends at its escaped line
break, and reported lines stay the lines an editor shows).

WHAT IS EXEMPT, AND HOW IT IS STILL SEEN. A run that is only a function signature is the field's common tongue, and a
declared textbook idiom (licence_line_allow.json: one line, at most 40 tokens, with its public source) is shared
ancestry, not a copy. Both are reported as exempt with their reason; neither is hidden.

THE BASELINE (judge's rulings b and c). Breaches in files that were already tracked at commit 9d6f29ff are declared in
licence_line_baseline.json, one entry per (file, corpus id) with its breach count and token total. Each entry is
verified against that commit (git cat-file, read-only): a file absent there is new and is never baselined, and an entry
may not declare more than the file held then. Baselined hits are measured and printed every run with the verdict
'baseline', never 'pass'; a breach not in the baseline fails, and so does an entry whose count or tokens grow. In a file
changed since the commit, a hit is baseline only when it is part of a copy the file held then (its runs are contiguous
parts of the runs attributed to that entry at the commit), so a declared copy cannot be traded for a different copy of
the same shader; and a hit counts against a lower-ranked id only when that id ties for the top share.

LIMITS. Identifiers are kept as written, so a clean result means no 12-token run is shared verbatim; code copied and then
consistently renamed, or restructured, is not measured. A prefix on every line (a diff's `+`, a Markdown quote's `> `,
a Python `# `, `cat -n` numbers) breaks every run that crosses a line, so copied short lines held that way are not
measured. The report says both every run.

WHAT IS NEVER DONE. Corpus text is read into memory and nowhere else. A breach is reported by file, line and corpus id;
its text is not echoed (the house file already holds it, and a report should not become a second copy).
"""
from __future__ import annotations

import codecs
import json
import os
import re
import subprocess
from bisect import bisect_right
from collections import Counter, defaultdict, namedtuple
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import corpus as C

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ALLOW_FILE = HERE / "licence_line_allow.json"
BASELINE_FILE = HERE / "licence_line_baseline.json"
API = "arsenal.licence-line/v2"
RUN = 12
ALLOW_MAX_TOKENS = 40
PRIVATE_TOP = "state"          # runtime state: never committed, and the only place corpus text may live
BINARY_PROBE = 8000            # git's own rule: a NUL in the first 8000 bytes makes a file binary
LIMITS = ("verbatim runs only: a clean result means no 12-token run is shared verbatim (numbers compared by value). "
          "Identifiers are kept as written, so code that was copied and then consistently renamed, or restructured, is "
          "not measured; this guards against pasting, not against derivation. A prefix on every line (a diff's +, a "
          "Markdown quote's >, a Python #, cat -n line numbers) breaks every run that crosses a line, so copied short "
          "lines held that way are not measured; a line of 12 or more tokens still is.")

Tok = namedtuple("Tok", "text line comment")

# ---------- reading text as tokens ----------

_NUM = r"0[xX][0-9a-fA-F]+[uU]?|(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[uUfF]?"
_ID = r"[A-Za-z_][A-Za-z0-9_]*"
_OP = r"<<=|>>=|\+\+|--|\+=|-=|\*=|/=|%=|&=|\|=|\^=|==|!=|<=|>=|&&|\|\||\^\^|<<|>>|\S"
# Dropped, never tokens: the glue between two JS string pieces ("a" + "b", 'a', 'b'), a lone quote, and a backslash
# (string escaping or macro continuation, never code).
_DROP = r"[\"'`]\s*[+,]\s*[\"'`]|[\"'`]|\\"
_TOK = re.compile(f"(?:{_DROP})|({_NUM})|({_ID}|{_OP})")
_COMMENT = re.compile(r"//[^\n\r]*|/\*.*?(?:\*/|\Z)", re.S)
_LINE_COMMENT = re.compile(r"//[^\n\r]*")
_BLOCK_MARK = re.compile(r"/\*|\*/")
_MARK = re.compile(r"//|/\*|\*/")                     # comment markers inside a comment's body: never tokens
_DOC_STAR = re.compile(r"(?m)((?:^|\r)[ \t]*)\*(?=[ \t\r]|$)")  # the leading * of a /** ... */ block's lines
_ESC_BREAK = re.compile(r"\\[nr]")                     # "\n" in a JS, JSON or Python string: a line break of its GLSL
_ESC_TAB = re.compile(r"\\t")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_NUMBER = re.compile(r"\d")                            # a normalised number always starts with a digit


@lru_cache(maxsize=1 << 16)
def norm_number(s: str) -> str:
    """One spelling per value: `1.` `1.0` `1.00` -> 1.0, `.5` -> 0.5, `0x10` -> 16; int, float and unsigned stay apart."""
    low = s.lower()
    try:
        if low.startswith("0x"):
            unsigned = low.endswith("u")
            return str(int(low[2:-1] if unsigned else low[2:], 16)) + ("u" if unsigned else "")
        if low.endswith("u"):
            return str(int(low[:-1])) + "u"
        if low.endswith("f"):
            low = low[:-1]
        if "." in low or "e" in low:
            return repr(float(low))
        return str(int(low))
    except ValueError:
        return s


def _prep(text: str) -> str:
    """Escaped line breaks become a carriage return (which ends a // comment but is not counted as a line, so reported
    lines stay physical lines); escaped tabs become spaces. Both keep every offset where it was."""
    return _ESC_TAB.sub("  ", _ESC_BREAK.sub("\r ", text))


def _blank(s: str) -> str:
    return " " * len(s)


def _open_comment(s: str) -> str:
    """A comment's text with its delimiters, inner comment markers and doc-comment stars blanked, at the same length, so
    lexing it can neither nest nor recurse (a line of many `//` once took the whole scan down)."""
    if s.startswith("//"):
        return "  " + _MARK.sub(lambda m: _blank(m.group()), s[2:])
    closed = len(s) >= 4 and s.endswith("*/")
    inner = s[2:-2] if closed else s[2:]
    inner = _DOC_STAR.sub(lambda m: m.group(1) + " ", inner)
    return "  " + _MARK.sub(lambda m: _blank(m.group()), inner) + ("  " if closed else "")


def _segments(t: str) -> Iterable[Tuple[str, str, str]]:
    """(kind, piece, raw) pieces covering t in order: kind "code", "line" (a // comment) or "block" (a /* comment,
    closed or running to the end of the text); a comment's piece is its opened body and raw is its text as written.
    Each piece is lexed on its own, so no token, string glue or comment can reach across a comment's edge."""
    pos = 0
    for m in _COMMENT.finditer(t):
        a, b = m.span()
        if a > pos:
            yield "code", t[pos:a], ""
        raw = m.group()
        yield ("line" if raw.startswith("//") else "block"), _open_comment(raw), raw
        pos = b
    if pos < len(t):
        yield "code", t[pos:], ""


def _bare_block(raw: str) -> str:
    """The third reading of a block comment: its text with every // dropped to the end of its line and the block
    markers blanked, at the same length, read as code. The comment reader cannot see quotes, so a `/*` inside a glob
    path (`design/*.frag`), a MIME type ("audio/*") or '*/*' opens a false block comment that runs to the next `*/` or
    the end of the file; the code reading then loses everything it swallowed and the full reading mixes the // prose of
    those lines into their code. Read this way a swallowed copy is code again. The third reading is the code reading
    with every block comment read like this and every // comment dropped; it exists only where a block comment does."""
    return _BLOCK_MARK.sub("  ", _LINE_COMMENT.sub(lambda m: _blank(m.group()), raw))


def _texts(t: str) -> List[str]:
    return [norm_number(n) if n else w for n, w in _TOK.findall(t) if n or w]


def _toks(t: str, line: int, comment: bool, out: List[Tok]) -> int:
    """Append the tokens of piece `t` (which starts on `line`) to `out`; returns the line the piece ends on."""
    pos = 0
    for m in _TOK.finditer(t):
        n, w = m.group(1), m.group(2)
        if not (n or w):
            continue
        s = m.start()
        line += t.count("\n", pos, s)
        pos = s
        out.append(Tok(norm_number(n) if n else w, line, comment))
    return line + t.count("\n", pos)


def token_texts(text: str) -> Dict[str, List[str]]:
    """The fast reading: {"code": token texts outside comments, "full": every token, "bare": the third reading (the
    code list itself when nothing opens a block comment)}, without lines. The scan reads every file this way and
    re-reads exactly (streams) only a file that shares a window; the two must agree token for token."""
    t = _prep(text)
    if not _COMMENT.search(t):
        c = _texts(t)
        return {"code": c, "full": c, "bare": c}
    code: List[str] = []
    full: List[str] = []
    bare: List[str] = []
    blocks = False
    for kind, piece, raw in _segments(t):
        x = _texts(piece)
        full += x
        if kind == "code":
            code += x
            bare += x
        elif kind == "block":
            blocks = True
            bare += _texts(_bare_block(raw))
    return {"code": code, "full": full, "bare": bare if blocks else code}


def streams(text: str, third: bool = True) -> Dict[str, List[Tok]]:
    """The exact reading: {"code": tokens outside comments, "full": every token, each marked comment or not, "bare":
    the third reading (see _bare_block), the code list itself when the text holds no block comment or `third` is
    False}."""
    t = _prep(text)
    full: List[Tok] = []
    bare: List[Tok] = []
    blocks = False
    line = 1
    for kind, piece, raw in _segments(t):
        start = len(full)
        end = _toks(piece, line, kind != "code", full)
        if kind == "code":
            bare += full[start:]
        elif kind == "block" and third:
            blocks = True
            _toks(_bare_block(raw), line, False, bare)
        line = end
    code = [x for x in full if not x.comment]
    return {"code": code, "full": full if len(code) != len(full) else code, "bare": bare if blocks else code}


def lex(text: str) -> List[Tok]:
    """Every token of `text` with its 1-based line and whether it sat inside a comment."""
    return streams(text)["full"]


# ---------- the signature exemption ----------

_NOT_A_TYPE = {"return", "if", "else", "for", "while", "do", "switch", "case", "new", "typeof", "define", "ifdef",
               "ifndef", "elif", "undef", "delete", "await", "yield", "throw", "function", "def", "class", "lambda",
               "and", "or", "not", "in", "of", "async", "export", "default", "let", "var"}
_QUALIFIERS = {"highp", "mediump", "lowp", "precise", "invariant"}


def signature_spans(toks: Sequence[Tok]) -> List[Tuple[int, int]]:
    """Token index spans [start, end] of function declarations: `type name(type name, ...)` plus a following `{` or `;`.

    A call has the same shape inside its parentheses but never a type before its name and never two words per argument,
    so `d = sdBox(p, b)` is not a signature and `float sdBox(vec3 p, vec3 b)` is."""
    spans: List[Tuple[int, int]] = []
    n = len(toks)
    for k in range(2, n):
        if toks[k].text != "(":
            continue
        name, typ = toks[k - 1].text, toks[k - 2].text
        if not (_IDENT.match(name) and _IDENT.match(typ)) or typ in _NOT_A_TYPE or name in _NOT_A_TYPE:
            continue
        j, groups, cur, ok = k + 1, [], [], True
        while j < n and toks[j].text != ")":
            t = toks[j].text
            if t == ",":
                groups.append(cur)
                cur = []
            elif _IDENT.match(t) or t in ("[", "]") or _NUMBER.match(t):
                cur.append(t)
            else:
                ok = False
                break
            j += 1
        if not ok or j >= n:
            continue
        groups.append(cur)
        words = [[w for w in g if _IDENT.match(w)] for g in groups]
        if groups == [[]] or words == [["void"]]:
            pass
        elif not all(len(w) >= 2 for w in words):
            continue
        start = k - 2
        while start > 0 and toks[start - 1].text in _QUALIFIERS:
            start -= 1
        end = j + 1 if j + 1 < n and toks[j + 1].text in ("{", ";") else j
        if spans and start <= spans[-1][1]:
            continue
        spans.append((start, end))
    return spans


def loop_spans(toks: Sequence[Tok]) -> List[Tuple[int, int]]:
    """Token index spans of `for (...)` headers plus a following `{`. From the initialiser to the opening brace a
    counted loop is exactly 12 tokens and every C-family file spells it the same way. RULED EXEMPT (Vandor, judge of
    the shader-school build, 2026-10-13): a bare loop header is the field's common tongue, like a signature; it carries
    no one's expression. Still measured and reported, with the reason "loop header", never silently passed; a run that
    carries on past the header into a body is code and stays a breach."""
    spans: List[Tuple[int, int]] = []
    n = len(toks)
    for k in range(n - 1):
        if toks[k].text != "for" or toks[k + 1].text != "(":
            continue
        depth, j = 0, k + 1
        while j < n:
            depth += toks[j].text == "("
            depth -= toks[j].text == ")"
            if depth == 0:
                break
            j += 1
        if j < n:
            spans.append((k, j + 1 if j + 1 < n and toks[j + 1].text == "{" else j))
    return spans


def _inside(spans: List[Tuple[int, int]], a: int, b: int) -> bool:
    i = bisect_right(spans, (a, float("inf"))) - 1
    return i >= 0 and spans[i][0] <= a and b <= spans[i][1]


# ---------- the allowlist exemption ----------

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def load_allow(path) -> List[dict]:
    """The declared textbook idioms. Every entry is an object naming text, reason, source and date, and its text is one
    line of at most ALLOW_MAX_TOKENS tokens (one entry must never be able to exempt a whole shader); otherwise the whole
    list is refused."""
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", []) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ValueError(f"{path.name}: entries must be a list of objects")
    out = []
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise ValueError(f"{path.name} entry {i}: must be an object with text, reason, source and date, "
                             f"not {type(e).__name__}")
        for field in ("text", "reason", "source", "date"):
            if not str(e.get(field) or "").strip():
                raise ValueError(f"{path.name} entry {i}: missing {field} (every exemption names its text, the reason "
                                 "it is common tongue, its public source and the date it was declared)")
        if not _DATE.fullmatch(str(e["date"])):
            raise ValueError(f"{path.name} entry {i}: date {e['date']!r} is not YYYY-MM-DD")
        text = str(e["text"])
        if "\n" in text.strip() or "\r" in text.strip():
            raise ValueError(f"{path.name} entry {i}: text spans more than one line; an idiom is one line")
        tokens = token_texts(text)["code"]
        if len(tokens) > ALLOW_MAX_TOKENS:
            raise ValueError(f"{path.name} entry {i}: text is {len(tokens)} tokens; an idiom is at most "
                             f"{ALLOW_MAX_TOKENS} tokens")
        out.append(dict(e, tokens=tokens))
    return out


def _allowed_by(allow: Sequence[dict], texts: Sequence[str]) -> Optional[str]:
    needle = "\x1f" + "\x1f".join(texts) + "\x1f"
    for e in allow:
        if needle in "\x1f" + "\x1f".join(e["tokens"]) + "\x1f":
            return e["source"]
    return None


# ---------- the corpus side ----------

# Assignments, not comparisons: a `// =====` banner lexes as `==` runs and must not make a comment look like code.
_ASSIGN = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}


def _comment_windows(texts: Sequence[str], comment: Sequence[bool], run: int) -> List[int]:
    """Start indices of full-stream windows whose COMMENT tokens look like code (at least two of `;`, an assignment and
    `(` among them): commented-out code, which is still someone else's code, alone or between live lines. A prose
    comment, a banner, or a licence sentence never qualifies, even beside code."""
    n = len(texts)
    if n < run or not any(comment):
        return []
    pc, ps, pe, pp = [0], [0], [0], [0]
    for t, c in zip(texts, comment):
        pc.append(pc[-1] + c)
        ps.append(ps[-1] + (c and t == ";"))
        pe.append(pe[-1] + (c and t in _ASSIGN))
        pp.append(pp[-1] + (c and t == "("))
    out = []
    for i in range(n - run + 1):
        j = i + run
        if pc[j] == pc[i]:
            continue                      # pure code: already a code window
        if (ps[j] > ps[i]) + (pe[j] > pe[i]) + (pp[j] > pp[i]) >= 2:
            out.append(i)
    return out


def corpus_passes(corpus_root=None) -> List[Tuple[str, str, Path]]:
    """(shader id, pass stem, path) for every pass of every corpus shader, in a stable order."""
    shaders = Path(corpus_root or C.CORPUS) / "shaders"
    if not shaders.is_dir():
        return []
    return [(p.parent.name, p.stem, p) for p in sorted(shaders.glob("*/*.glsl"))]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


class CorpusIndex:
    """The corpus as a set of shingle hashes and the vocabulary those shingles use, plus each pass's token streams for
    naming where a shared run came from. Lives in memory only; it is rebuilt per scan and never written anywhere."""

    def __init__(self, passes: List[Tuple[str, str, Path]], run: int = RUN, root: Optional[Path] = None):
        self.passes, self.run, self.root = passes, run, root
        self.hashes = set()
        self.vocab = set()
        self.tokens = 0
        self.comment_windows = 0
        # per pass: (code texts, code lines, full texts or None, full lines or None, indexed full-window starts)
        self._streams: List[tuple] = []
        for _sid, _stem, path in passes:
            # GLSL has no strings, so no quoted `/*` can open a false comment here: the third reading is house-side.
            st = streams(_read(path), third=False)
            code, full = st["code"], st["full"]
            ct = [t.text for t in code]
            self.tokens += len(ct)
            self.vocab.update(ct)
            self.hashes.update(hash(tuple(ct[i:i + run])) for i in range(len(ct) - run + 1))
            ft = [t.text for t in full]
            extra = _comment_windows(ft, [t.comment for t in full], run)
            for i in extra:
                w = tuple(ft[i:i + run])
                self.hashes.add(hash(w))
                self.vocab.update(w)
            self.comment_windows += len(extra)
            self._streams.append((ct, [t.line for t in code], ft if extra else None,
                                  [t.line for t in full] if extra else None, extra))

    @property
    def shaders(self) -> int:
        return len({p[0] for p in self.passes})

    def locate(self, windows: set) -> Dict[tuple, List[Tuple[str, str, int]]]:
        """For each exact window, every (id, pass, line) of the corpus that holds it (in its code, or in an indexed
        window of commented-out code). A window absent here was a hash collision, not a shared run."""
        want = {hash(w) for w in windows}
        found: Dict[tuple, List[Tuple[str, str, int]]] = defaultdict(list)
        run = self.run
        for (sid, stem, _path), (ct, cl, ft, fl, extra) in zip(self.passes, self._streams):
            seen = set()
            for i in range(len(ct) - run + 1):
                w = tuple(ct[i:i + run])
                if hash(w) in want and w in windows:
                    found[w].append((sid, stem, cl[i]))
                    seen.add(w)
            for i in extra:
                w = tuple(ft[i:i + run])
                if w not in seen and hash(w) in want and w in windows:
                    found[w].append((sid, stem, fl[i]))
                    seen.add(w)
        return found


def build_index(corpus_root=None, run: int = RUN) -> Optional[CorpusIndex]:
    """The corpus index, or None when there is no corpus to measure against (a fresh clone)."""
    passes = corpus_passes(corpus_root)
    return CorpusIndex(passes, run, Path(corpus_root or C.CORPUS)) if passes else None


# ---------- the house side: what git would commit, read whatever its encoding ----------

def _git(root: Path, *args: str, stdin: Optional[bytes] = None) -> Optional[bytes]:
    """A read-only git command's stdout, or None. GIT_OPTIONAL_LOCKS=0: not even an index refresh is written."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", "-C", str(root), *args], input=stdin, capture_output=True, env=env, timeout=600)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def _git_paths(root: Path, *args: str) -> Optional[List[str]]:
    out = _git(root, *args)
    return None if out is None else [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def _is_git_top(root: Path) -> bool:
    out = _git(root, "rev-parse", "--show-toplevel")
    if out is None:
        return False
    top = out.decode("utf-8", "replace").strip()
    return bool(top) and os.path.normcase(os.path.realpath(top)) == os.path.normcase(os.path.realpath(str(root)))


def _private(rel: str) -> bool:
    return rel.split("/", 1)[0] == PRIVATE_TOP


def _listing(root: Path) -> Tuple[str, List[Tuple[str, str]], List[str]]:
    """house_files() plus the paths under the top-level state/ that git would commit (git mode only; ruling a leaves
    them out of the scan, so the report names them instead)."""
    if _is_git_top(root):
        tracked = _git_paths(root, "ls-files", "-z")
        others = _git_paths(root, "ls-files", "-z", "--others", "--exclude-standard")
        if tracked is None or others is None:
            raise RuntimeError(f"git could not list the files of {root}; the licence line cannot be measured")
        origin = {r: "tracked" for r in tracked}
        for r in others:
            origin.setdefault(r, "untracked")
        listed = sorted(origin.items())
        return "git", [(r, o) for r, o in listed if not _private(r)], [r for r, _o in listed if _private(r)]
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        top = rel_dir == "."
        dirnames[:] = sorted(d for d in dirnames if d != ".git" and not (top and d == PRIVATE_TOP))
        for f in sorted(filenames):
            files.append((f if top else f"{rel_dir}/{f}", "walk"))
    return "walk", sorted(files), []


def house_files(root=None) -> Tuple[str, List[Tuple[str, str]]]:
    """("git" or "walk", [(posix path relative to root, "tracked" | "untracked" | "walk")]).

    At the top of a git work tree: `git ls-files` plus `git ls-files --others --exclude-standard` (what git would
    commit), minus the top-level state/ folder. Anywhere else: every file, minus the top-level state/ and any .git."""
    mode, files, _private_committed = _listing(Path(root or ROOT))
    return mode, files


def corpus_leaks(paths: Iterable[str], corpus_rel: Optional[str]) -> List[str]:
    """The paths that lie under the corpus folder (posix, relative to the scanned root). Git committing any of them is
    corpus text published whatever ruling a leaves out of the scan, so each one fails the scan by name."""
    if not corpus_rel:
        return []
    prefix = corpus_rel.strip("/") + "/"
    return [p for p in paths if p.startswith(prefix)]


_PRINTABLE_RUN = re.compile(rb"[\t\n\r\x20-\x7e]{16,}")
# UTF-32 first: its little-endian mark (FF FE 00 00, what PowerShell 5.1 writes for -Encoding UTF32) begins with the
# UTF-16 one, and read as UTF-16 it puts a NUL after every character, so a copy scanned clean as a file that was read.
_BOMS = (((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE), "utf-32"), ((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE), "utf-16"))


def printable_text(raw: bytes) -> str:
    """What a binary file says in plain text: its NULs removed (so UTF-16 without a byte-order mark reads as its ASCII
    text), then every run of at least 16 printable ASCII characters; the line breaks in the gaps between runs are kept,
    so a text file with one stray NUL still reports its physical lines. Random bytes almost never hold 16 printable
    characters in a row, so an image or a model adds next to nothing to the scan."""
    b = raw.replace(b"\0", b"")
    out, pos = [], 0
    for m in _PRINTABLE_RUN.finditer(b):
        out.append("\n" * b.count(b"\n", pos, m.start()) + " ")
        out.append(m.group().decode("ascii"))
        pos = m.end()
    return "".join(out)


def decode(raw: bytes) -> Tuple[Optional[str], str, str]:
    """(text or None, how, why): UTF-32 or UTF-16 by its byte-order mark, UTF-8 (mark or not), else cp1252 with
    replacement. "binary" (a NUL in the first 8000 bytes, git's rule) returns the file's printable text (see
    printable_text): the file is counted as binary and still read. "unreadable" (a byte-order mark on bytes that are not
    that encoding, or that decode to text holding NUL characters, which means another encoding hides behind the mark)
    returns no text and fails the scan."""
    for marks, codec in _BOMS:
        if raw.startswith(marks):
            name = codec.upper()
            try:
                text = raw.decode(codec)
            except UnicodeDecodeError as exc:
                return None, "unreadable", f"starts with a {name} byte-order mark but is not {name} ({exc.reason})"
            if "\0" in text:
                return None, "unreadable", (f"starts with a {name} byte-order mark but decodes to text holding NUL "
                                            "characters: another encoding hides behind the mark")
            return text, codec, ""
    if b"\0" in raw[:BINARY_PROBE]:
        return printable_text(raw), "binary", ""
    try:
        return raw.decode("utf-8-sig"), ("utf-8-sig" if raw.startswith(codecs.BOM_UTF8) else "utf-8"), ""
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace"), "cp1252", ""


def read_house(path: Path) -> Tuple[Optional[str], str, str]:
    """decode() of a file on disk; "missing" for a listed path that is gone (a tracked file deleted in the work tree,
    which git would commit as a deletion) or is a folder (a submodule, whose content is another repository's);
    "unreadable" with the reason for anything else that cannot be read, which fails the scan."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None, "missing", ""
    except OSError as exc:
        if path.is_dir():
            return None, "missing", ""
        return None, "unreadable", f"{type(exc).__name__}: {exc}"
    return decode(raw)


# ---------- matching ----------

def _stretch(run: int):
    return re.compile(rb"\x01{%d,}" % run)


def _matching_spans(texts: List[str], index: "CorpusIndex", stop_at_first: bool = False) -> List[Tuple[int, int]]:
    """Token spans [a, b] covered by windows the corpus also holds; overlapping windows merge into one run. Only
    stretches of corpus vocabulary are hashed: a window holding a word the corpus never uses cannot match."""
    run = index.run
    spans: List[Tuple[int, int]] = []
    if len(texts) < run:
        return spans
    vocab, hashes = index.vocab, index.hashes
    mask = bytes([t in vocab for t in texts])
    for m in _stretch(run).finditer(mask):
        a, b = m.span()
        for i in range(a, b - run + 1):
            if hash(tuple(texts[i:i + run])) in hashes:
                if stop_at_first:
                    return [(i, i + run - 1)]
                if spans and i <= spans[-1][1]:
                    spans[-1] = (spans[-1][0], i + run - 1)
                else:
                    spans.append((i, i + run - 1))
    return spans


def scan_texts(index: CorpusIndex, named_texts: Iterable[Tuple[str, str]], allow: Sequence[dict] = (),
               stats: Optional[dict] = None) -> List[dict]:
    """Every shared run between the named texts and the corpus, merged per file by overlapping lines, each marked exempt
    (with its reasons) or not. Texts are held in memory; nothing is written."""
    run = index.run
    candidates = []  # (name, mode, texts, lines, a, b, sigs, loops)
    tokens = 0
    for name, text in named_texts:
        fast = token_texts(text)
        tokens += len(fast["full"])
        # The fast reading finds the runs; the exact one (streams, which agrees token for token) only adds their lines.
        found = [(m, fast[m], _matching_spans(fast[m], index)) for m in ("code", "full", "bare")
                 if m == "code" or fast[m] is not fast["code"]]
        if not any(spans for _m, _texts_m, spans in found):
            continue
        st = streams(text)
        for mode, texts, spans in found:
            if not spans:
                continue
            toks = st[mode]
            if len(toks) != len(texts):
                raise RuntimeError(f"{name}: the fast and exact {mode} readings disagree ({len(texts)} tokens against "
                                   f"{len(toks)}); the licence line cannot be measured")
            sigs, loops = signature_spans(toks), loop_spans(toks)
            lines = [t.line for t in toks]
            candidates += [(name, mode, texts, lines, a, b, sigs, loops) for a, b in spans]
    if stats is not None:
        stats["tokens"] = stats.get("tokens", 0) + tokens
    windows = {tuple(c[2][i:i + run]) for c in candidates for i in range(c[4], c[5] - run + 2)}
    where = index.locate(windows) if windows else {}

    runs = []
    for name, mode, texts, lines, a, b, sigs, loops in candidates:
        verified = [i for i in range(a, b - run + 2) if tuple(texts[i:i + run]) in where]
        sub: List[Tuple[int, int]] = []
        for i in verified:
            if sub and i <= sub[-1][1]:
                sub[-1] = (sub[-1][0], i + run - 1)
            else:
                sub.append((i, i + run - 1))
        for sa, sb in sub:
            ids: Counter = Counter()
            for i in range(sa, sb - run + 2):
                for sid in {loc[0] for loc in where.get(tuple(texts[i:i + run]), ())}:
                    ids[sid] += 1
            first = sorted(where[tuple(texts[sa:sa + run])])[0]
            ranked = sorted(ids.items(), key=lambda kv: (-kv[1], kv[0]))
            # How much of the run one corpus shader holds: near 1.0 reads "a copy of that shader", a low share reads
            # "stitched from idioms many shaders spell the same way". Both are reported; neither is excused by it.
            cover = round(ranked[0][1] / (sb - sa - run + 2), 3)
            reasons = []
            shape = "signature" if _inside(sigs, sa, sb) else "loop-header" if _inside(loops, sa, sb) else "code"
            if shape == "signature":
                reasons.append("signature")
            elif shape == "loop-header":
                reasons.append("loop header")
            source = _allowed_by(allow, texts[sa:sb + 1])
            if source:
                reasons.append(f"allowlist: {source}")
            runs.append({"file": name, "line": lines[sa], "end_line": lines[sb], "tokens": sb - sa + 1,
                         "exempt": bool(reasons), "reasons": reasons, "modes": [mode], "shape": shape,
                         "corpus": [sid for sid, _ in ranked], "cover": cover,
                         "corpus_first": {"id": first[0], "pass": first[1], "line": first[2]},
                         "_preview": " ".join(texts[sa:sb + 1]),
                         # In memory only, never reported: the run itself (the baseline checks that a declared copy
                         # is still part of what the file held at the commit) and the ids tied for the top share.
                         "_run": tuple(texts[sa:sb + 1]), "_top": {sid for sid, k in ranked if k == ranked[0][1]}})
    return _merge(runs)


def _merge(runs: List[dict]) -> List[dict]:
    """One hit per stretch of a file: runs from the three readings (code, full, bare) that overlap in lines are the same
    copy seen more than once. A merged hit is exempt only when every run in it is."""
    by_file: Dict[str, List[dict]] = defaultdict(list)
    for r in runs:
        by_file[r["file"]].append(r)
    hits = []
    for name in sorted(by_file):
        group = sorted(by_file[name], key=lambda r: (r["line"], r["end_line"], -r["tokens"]))
        merged: List[List[dict]] = []
        for r in group:
            if merged and r["line"] <= max(x["end_line"] for x in merged[-1]):
                merged[-1].append(r)
            else:
                merged.append([r])
        for parts in merged:
            longest = max(parts, key=lambda r: r["tokens"])
            exempt = all(p["exempt"] for p in parts)
            ids: List[str] = []
            for p in sorted(parts, key=lambda r: -r["tokens"]):
                ids += [i for i in p["corpus"] if i not in ids]
            hit = {"file": name, "line": min(p["line"] for p in parts), "end_line": max(p["end_line"] for p in parts),
                   "tokens": longest["tokens"], "exempt": exempt, "verdict": "exempt" if exempt else "breach",
                   "reasons": sorted({x for p in parts for x in p["reasons"]}) if exempt else [],
                   "modes": sorted({m for p in parts for m in p["modes"]}),
                   "shape": parts[0]["shape"] if len({p["shape"] for p in parts}) == 1 else "code",
                   "corpus": ids[:10], "corpus_count": len(ids), "cover": longest["cover"],
                   "corpus_first": min(parts, key=lambda r: (r["line"], -r["tokens"]))["corpus_first"],
                   "_ids": ids, "_runs": [p["_run"] for p in parts], "_top": set().union(*(p["_top"] for p in parts))}
            # An exempt run is house text the rule allows (a signature, a declared idiom), so it may be shown. A breach
            # is corpus code: report where it is, never echo it.
            hit["preview"] = longest["_preview"][:100] if exempt else None
            hits.append(hit)
    return hits


# ---------- the baseline: pre-existing breaches, declared, verified, never allowed to grow ----------

BASELINE_REASON = "pre-existing at 9d6f29ff; triage pending Daniel"
_BASELINE_FIELDS = ("file", "corpus", "breaches", "tokens", "date", "reason")
# held: every hit applied. grown: more hits or tokens than declared. changed: a hit that is not part of a copy the file
# held at the commit. cleared: nothing measured. invalid: the entry declares more than the commit held, or the file is
# new. unverified: no git history to check against. A held entry marks all its hits 'baseline'; a changed one marks
# only those that were part of a copy then; the others mark none.
BASELINE_STATES = ("held", "grown", "changed", "cleared", "invalid", "unverified")


def load_baseline(path) -> dict:
    """{"commit", "entries"}: the declared pre-existing breaches. A malformed entry refuses the whole file."""
    path = Path(path)
    if not path.exists():
        return {"file": str(path), "commit": None, "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries", []), list):
        raise ValueError(f"{path.name}: must be an object with a list of entries")
    commit = str(data.get("commit") or "")
    entries = data.get("entries", [])
    if entries and not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise ValueError(f"{path.name}: commit {commit!r} is not a commit id; entries are verified against it")
    out, seen = [], set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise ValueError(f"{path.name} entry {i}: must be an object, not {type(e).__name__}")
        for field in _BASELINE_FIELDS:
            v = e.get(field)
            if v is None or (isinstance(v, str) and not v.strip()):
                raise ValueError(f"{path.name} entry {i}: missing {field} (every entry names its file, corpus id, "
                                 "breach count, token total, date and reason)")
        for field in ("breaches", "tokens"):
            if not isinstance(e[field], int) or isinstance(e[field], bool) or e[field] < 1:
                raise ValueError(f"{path.name} entry {i}: {field} must be a positive whole number")
        if not _DATE.fullmatch(str(e["date"])):
            raise ValueError(f"{path.name} entry {i}: date {e['date']!r} is not YYYY-MM-DD")
        if _private(str(e["file"])):
            raise ValueError(f"{path.name} entry {i}: {e['file']} is under state/, which is never scanned")
        key = (e["file"], e["corpus"])
        if key in seen:
            raise ValueError(f"{path.name} entry {i}: {e['file']} {e['corpus']} is declared twice")
        seen.add(key)
        out.append(dict(e))
    return {"file": str(path), "commit": commit or None, "entries": out}


def git_at_commit(root: Path, commit: str) -> Callable[[List[str]], Dict[str, Optional[str]]]:
    """A reader of files as they were at `commit` (git ls-tree and git cat-file --batch, both read-only): path -> text,
    or None when the path did not exist there. Raises when the commit is not in this clone."""
    def fetch(rels: List[str]) -> Dict[str, Optional[str]]:
        names = _git_paths(root, "ls-tree", "-r", "-z", "--name-only", commit)
        if names is None:
            raise RuntimeError(f"commit {commit} is not in this clone; the baseline cannot be verified")
        present = set(names)
        want = [r for r in rels if r in present]
        out: Dict[str, Optional[str]] = {r: None for r in rels}
        if not want:
            return out
        data = _git(root, "cat-file", "--batch", stdin="".join(f"{commit}:{r}\n" for r in want).encode("utf-8"))
        if data is None:
            raise RuntimeError(f"git cat-file could not read the files of {commit}")
        pos = 0
        for r in want:
            nl = data.index(b"\n", pos)
            head = data[pos:nl].split()
            pos = nl + 1
            if len(head) < 3 or head[1] != b"blob":
                continue
            size = int(head[2])
            text, _how, _why = decode(data[pos:pos + size])
            out[r] = text if text is not None else ""
            pos += size + 1
        return out
    return fetch


def _attribute(hits: Sequence[dict], preferred: Dict[str, set]) -> Dict[Tuple[str, str], List[dict]]:
    """Breaches grouped by (file, corpus id). A hit counts against its top id; when several ids tie for the top share,
    against the first of them that the baseline declares for its file (so a tie cannot move a pre-existing copy out of
    its entry). An id lower in the ranking never takes the hit: a new copy of one shader must not hide in the entry of
    another shader it merely shares an idiom with."""
    groups: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for h in hits:
        if h["exempt"]:
            continue
        pref = preferred.get(h["file"], ())
        sid = next((i for i in h["_ids"] if i in pref and i in h["_top"]), h["_ids"][0])
        groups[(h["file"], sid)].append(h)
    return groups


def _run_key(run: Sequence[str]) -> str:
    # \x1e and \x1f are whitespace to the lexer, so no token holds them: a key is found inside a haystack of keys only
    # as a contiguous part of one run.
    return "\x1f" + "\x1f".join(run) + "\x1f"


def apply_baseline(index: CorpusIndex, hits: List[dict], baseline: dict, allow: Sequence[dict],
                   at_commit: Optional[Callable[[List[str]], Dict[str, Optional[str]]]],
                   current: Optional[Dict[str, int]] = None) -> dict:
    """Verify each entry against the commit, then give every breach its verdict: 'baseline' when its (file, id) entry
    holds it within the declared count and tokens AND the hit is part of a copy the file held at the commit (every
    run of it a contiguous part of a run attributed to that entry then), else 'breach'. Count and tokens alone would let
    a declared copy be traded for a different, no longer copy of the same shader. Returns the report's baseline
    section. `current` maps a file to hash() of its text now: a file unchanged since the commit is measured once, not
    twice, and holds exactly the copies it held then."""
    commit = baseline.get("commit")
    entries = [dict(e, measured=0, measured_tokens=0, state="held", why="") for e in baseline["entries"]]
    preferred: Dict[str, set] = defaultdict(set)
    for e in entries:
        preferred[e["file"]].add(e["corpus"])
    held_then: Dict[Tuple[str, str], str] = {}    # (file, id) of a file changed since the commit -> its runs then
    changed_files: set = set()
    if entries and at_commit is None:
        for e in entries:
            e.update(state="unverified", why="no git history to verify against, so the entry is not applied")
    elif entries:
        try:
            old = at_commit(sorted({e["file"] for e in entries}))
        except RuntimeError as exc:
            old = None
            for e in entries:
                e.update(state="unverified", why=str(exc))
        if old is not None:
            current = current or {}
            same = {r for r, t in old.items() if t is not None and r in current and hash(t) == current[r]}
            changed = [(r, t) for r, t in sorted(old.items()) if t is not None and r not in same]
            changed_files = {r for r, _t in changed}
            then = _attribute([h for h in hits if h["file"] in same] + scan_texts(index, changed, allow), preferred)
            held_then = {key: "\x1e".join(_run_key(r) for h in group for r in h["_runs"])
                         for key, group in then.items() if key[0] in changed_files}
            for e in entries:
                if old.get(e["file"]) is None:
                    e.update(state="invalid", why=f"absent at {commit}: a file new since then is never baselined")
                    continue
                held = then.get((e["file"], e["corpus"]), [])
                n0, t0 = len(held), sum(h["tokens"] for h in held)
                e["at_commit"] = {"breaches": n0, "tokens": t0}
                if e["breaches"] > n0 or e["tokens"] > t0:
                    e.update(state="invalid", why=f"declares {e['breaches']} breaches / {e['tokens']} tokens, but the "
                                                  f"file held {n0} / {t0} at {commit}")
    by_key = {(e["file"], e["corpus"]): e for e in entries}
    for key, group in _attribute(hits, preferred).items():
        n, t = len(group), sum(h["tokens"] for h in group)
        e = by_key.get(key)
        if e is not None:
            e["measured"], e["measured_tokens"] = n, t
        if e is None or e["state"] in ("invalid", "unverified"):
            continue
        if n > e["breaches"] or t > e["tokens"]:
            e.update(state="grown", why=f"declared {e['breaches']} breaches / {e['tokens']} tokens, measured {n} / {t}")
            continue
        # A file unchanged since the commit holds exactly the copies it held then; a changed one is checked hit by hit.
        new = [] if key[0] not in changed_files else \
            [h for h in group if not all(_run_key(r) in held_then.get(key, "") for r in h["_runs"])]
        new_ids = {id(h) for h in new}
        for h in group:
            if id(h) not in new_ids:
                h["verdict"] = "baseline"
        if new:
            lines = ", ".join(str(h["line"]) for h in new)
            e.update(state="changed", why=f"{len(new)} of its {n} hits (line {lines}) are not part of any copy the file "
                                          f"held at {commit}: a different copy, not the declared one")
    for e in entries:
        if e["state"] == "held" and e["measured"] == 0:
            e.update(state="cleared", why="no breach measured: the debt is paid here; lower or drop the entry")
    states = Counter(e["state"] for e in entries)
    return {"file": baseline.get("file"), "commit": commit, "entries": entries,
            **{s: states.get(s, 0) for s in BASELINE_STATES}}


# ---------- the whole measurement ----------

def scan(root=None, corpus=None, allow_path=None, index: Optional[CorpusIndex] = None, run: int = RUN,
         baseline_path=None, at_commit: Optional[Callable[[List[str]], Dict[str, Optional[str]]]] = None) -> dict:
    """Measure the licence line over the tree at `root` against the corpus at `corpus` (default: the repo's own).
    `at_commit` reads files as they were at the baseline commit; at the top of a git work tree it defaults to git."""
    root = Path(root or ROOT)
    corpus_root = Path(corpus) if corpus else (index.root if index is not None and index.root else C.CORPUS)
    report = {"api": API, "run": run, "root": str(root), "status": "skipped", "reason": "", "limits": LIMITS,
              "corpus": {"dir": str(corpus_root), "shaders": 0, "passes": 0, "tokens": 0, "shingles": 0,
                         "comment_windows": 0},
              "scanned": {"discovery": None, "files": 0, "tokens": 0}, "hits": [], "breaches": 0, "baselined": 0,
              "exempt": 0, "failures": []}
    if index is None:
        index = build_index(corpus_root, run)
    if index is None:
        report["reason"] = (f"the private corpus is absent ({corpus_root / 'shaders'} holds no passes; a fresh clone has "
                            "none), so there is nothing to measure against")
        return report
    allow_file = Path(allow_path or ALLOW_FILE)
    allow = load_allow(allow_file)
    baseline = load_baseline(baseline_path or BASELINE_FILE)
    discovery, listed, state_committed = _listing(root)
    try:
        corpus_rel: Optional[str] = corpus_root.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        corpus_rel = None                 # a corpus outside the scanned tree cannot be committed with it
    if at_commit is None and discovery == "git" and baseline["entries"]:
        at_commit = git_at_commit(root, baseline["commit"])

    encodings: Counter = Counter()
    binary, missing, unreadable = [], [], []
    declared = {e["file"] for e in baseline["entries"]}
    current: Dict[str, int] = {}

    def texts():
        for rel, _origin in listed:
            text, how, why = read_house(root / rel)
            if how == "binary":
                binary.append(rel)              # counted as binary, and its printable text is still read
            elif text is not None:
                encodings[how] += 1
            if text is not None:
                if rel in declared:
                    current[rel] = hash(text)
                yield rel, text
            elif how == "missing":
                missing.append(rel)
            else:
                unreadable.append({"file": rel, "error": why})

    stats: dict = {}
    hits = scan_texts(index, texts(), allow, stats)
    base = apply_baseline(index, hits, baseline, allow, at_commit, current)
    for h in hits:
        for k in ("_ids", "_runs", "_top"):
            h.pop(k, None)
    failures = [f"unreadable: {u['file']}: {u['error']}" for u in unreadable]
    failures += [f"baseline entry invalid: {e['file']} {e['corpus']}: {e['why']}"
                 for e in base["entries"] if e["state"] == "invalid"]
    failures += [f"corpus file committed: {p}: git would commit it, and corpus text never leaves state/ untracked"
                 for p in corpus_leaks(state_committed, corpus_rel)]
    n_breach = sum(h["verdict"] == "breach" for h in hits)
    n_base = sum(h["verdict"] == "baseline" for h in hits)
    status = "breach" if n_breach else "fail" if failures else "baseline" if n_base else "clean"
    origins = Counter(o for _r, o in listed)
    report.update(
        status=status,
        corpus={"dir": str(corpus_root), "shaders": index.shaders, "passes": len(index.passes), "tokens": index.tokens,
                "shingles": len(index.hashes), "comment_windows": index.comment_windows},
        scanned={"discovery": discovery, "listed": len(listed), "tracked": origins.get("tracked", 0),
                 "untracked": origins.get("untracked", 0), "files": sum(encodings.values()),
                 "tokens": stats.get("tokens", 0), "encodings": dict(sorted(encodings.items())),
                 "binary_files": binary, "missing": missing, "unreadable": unreadable,
                 "state_committed": state_committed},
        allow={"file": str(allow_file), "entries": len(allow)},
        baseline=base, failures=failures, hits=hits,
        breaches=n_breach, baselined=n_base, exempt=sum(h["verdict"] == "exempt" for h in hits))
    return report


def describe_hit(h: dict) -> str:
    where = f"{h['file']}:{h['line']}" + (f"-{h['end_line']}" if h["end_line"] != h["line"] else "")
    first = h["corpus_first"]
    verdict = h.get("verdict") or ("exempt" if h["exempt"] else "breach")
    loop = " (loop header)" if h.get("shape") == "loop-header" else ""
    head = f"exempt ({'; '.join(h['reasons'])})" if verdict == "exempt" else verdict.upper() + loop
    shared = h.get("corpus_count", 1)
    tail = f"  | {h['preview']}" if h.get("preview") else ""
    return (f"{head:<24} {where}  {h['tokens']} tokens  corpus {h['corpus'][0]} holds {h['cover']:.0%}, "
            f"shared by {shared} corpus shader{'s' if shared != 1 else ''}, "
            f"first window {first['id']} {first['pass']}:{first['line']}  [{','.join(h['modes'])}]{tail}")


def _human(r: dict) -> str:
    if r["status"] == "skipped":
        return f"licence line: SKIPPED: {r['reason']}"
    c, s, b = r["corpus"], r["scanned"], r["baseline"]
    out = [f"licence line: {r['status'].upper()}  ({r['breaches']} breaches, {r['baselined']} baseline, "
           f"{r['exempt']} exempt, {len(r['failures'])} failures)",
           f"  corpus: {c['shaders']} shaders, {c['passes']} passes, {c['tokens']} tokens, "
           f"{c['shingles']} distinct {r['run']}-token shingles ({c['comment_windows']} from commented-out code)",
           f"  scanned: {s['files']} text files, {s['tokens']} tokens ({s['discovery']}: {s.get('tracked', 0)} tracked, "
           f"{s.get('untracked', 0)} untracked; {len(s['binary_files'])} binary, read for their printable text; "
           f"{len(s['missing'])} missing; encodings " + ", ".join(f"{k} {v}" for k, v in s["encodings"].items()) + ")",
           f"  not scanned (ruling a): {len(s.get('state_committed', []))} files under state/ that git would commit "
           "(listed in --json; one under the corpus folder fails the scan)",
           f"  allowlist: {r['allow']['entries']} entries; baseline ({b['commit']}): "
           + ", ".join(f"{b.get(k, 0)} {k}" for k in BASELINE_STATES),
           f"  limits: {r['limits']}"]
    out += ["  " + describe_hit(h) for h in r["hits"]]
    out += [f"  baseline entry {e['state'].upper()}: {e['file']} {e['corpus']}: {e['why']}"
            for e in b["entries"] if e["state"] != "held"]
    out += [f"  FAILURE: {f}" for f in r["failures"]]
    return "\n".join(out)


# ---------- the door: py -m arsenal shader licence-line ----------

def _register(sub) -> None:
    p = sub.add_parser("licence-line", help="does any committable file share a 12-token run with a corpus shader?")
    p.add_argument("--root", help="the tree to scan (default: this repository)")
    p.add_argument("--corpus", help="the corpus root holding shaders/<id>/<pass>.glsl (default: state/.../corpus)")
    p.add_argument("--allow", help="the allowlist of declared textbook idioms (default: licence_line_allow.json)")
    p.add_argument("--baseline", help="the declared pre-existing breaches (default: licence_line_baseline.json)")
    p.set_defaults(fn=_cmd)


def _cmd(ns) -> int:
    from .cli import _print
    report = scan(root=ns.root, corpus=ns.corpus, allow_path=ns.allow, baseline_path=ns.baseline)
    _print(report, ns.json, _human)
    return 1 if report["status"] in ("breach", "fail") else 0


def _hook() -> None:
    from . import cli
    cli.VERBS["licence-line"] = _register


_hook()
