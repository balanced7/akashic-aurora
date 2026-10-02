"""context.target.v1 -- the one key every plane joins a code location on.

SPEC: research/in-flight/context-system-navi-m1.md (sealed, Navi) AS AMENDED BY
      research/in-flight/context-system-navi-m1-amendment-1.md (Navi, 2026-10-02).
PINS: tests/test_context_target_v1.py (RED committed alone at 9aee64c9, before this file existed).
WAVE: W0.1 of the context-system build spec, fences/context-system/reconciliation.md section 4.

WHY THIS MODULE EXISTS, in the operator's words.
  2026-08-10: "We need to make all of my words queriable and to have links to what was around them
  at the time. an instant lookup rather than having to data mine each time. What do we need to
  truly make our knowledge queriable not just grepable."
  2026-08-16: "a string through a forest you can walk with by hand so you dont need to
  re-discover relationships between different things."
A string can only be walked if every knot on it has ONE name. Measured in this tree before a line
of this was written: one file carries at least four live spellings across the planes (repo-relative,
backslashed absolute, slashed absolute, lowercased lock key); `git worktree list` reports 62
worktrees whose leaf name collides 48 times on `shadow` and twice on `AI-Setup`; and six reference
spellings already ride `refs[]` that no resolver in the house can parse. Every one of those is a
join that silently does not happen.

THE LAW THIS MODULE OBEYS, and the one it is most tempted to break: a resolver may NOT mint new
ref kinds. The set is closed at eight for Wave 0. When something does not parse, this module says
so loudly or names it opaque -- it never guesses, and it never demotes a malformed reference to a
path, because a wrong join is worse than no join and strictly harder to notice.

DESIGN NOTES worth knowing before changing anything here:
  - Nothing in this module touches the disk, git, or Redis. Roots arrive as strings, existence as a
    callable, short-sha resolution as a callable. That is what makes the pins hermetic, and it is
    also what lets a caller decide the cost model: the expensive lookups (`git worktree list`,
    `git rev-parse`) are the CALLER's to cache per process, as the spec prices them.
  - Case: the drive letter and the root prefix fold (Windows drive letters are case-insensitive by
    Microsoft's own rule, and our roots are fixed); everything below the root is preserved verbatim
    (SARIF's producer rule: preserve the filesystem's casing even where the filesystem does not
    care). Five normalizers elsewhere in this tree fold case below the root. They are a migration,
    not an authority.
  - Worktree naming is collision-only: the bare leaf when it is unique, parent-leaf when it is not,
    and a loud refusal when parent cannot break it either. A hash suffix was rejected because the
    key has to stay walkable by hand, which is the whole point of a string through a forest.
"""
from __future__ import annotations

import posixpath
import re
import shlex
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

SCHEMA = "context.target.v1"

#: Closed for Wave 0 (sealed spec + amendment A5, which admitted `mem`). A resolver may not widen
#: this; a new kind is a parent-fence decision, never a convenience taken at a call site.
REF_KINDS: Tuple[str, ...] = ("event", "sha", "task", "lesson", "mem", "doc", "session", "seat")

#: Amendment B6. `move` carries BOTH ends (role "from" and "to") because a rename is a removal plus
#: a create, and folding it under `write` makes a file's lifecycle invisible -- which is exactly the
#: question a heat map or a lifecycle lens exists to answer. `delete` is its own action for the same
#: reason. Probe and enumeration (ls, Get-ChildItem, stat) are `search`.
ACTIONS: Tuple[str, ...] = ("read", "write", "exec", "search", "move", "delete")

#: Amendment B1. A column number without a declared unit cannot join: SARIF requires a per-run
#: columnKind, LSP negotiates an encoding (UTF-16 mandatory default), GCC counts display width,
#: git grep counts bytes. Four live sources, four different numbers for the same position. We pin
#: UTF-16 because our producers are overwhelmingly LSP-adjacent editors; a consumer counting in
#: another unit MUST recompute rather than assume.
COL_UNIT = "utf16CodeUnits"

#: Aliases are rewritten to their canonical kind AT PARSE TIME, so the by-reference index only ever
#: sees one key per referent (W3C PROV's `alternateOf` and OpenLineage's `symlinks` do the same
#: thing: an alias is a mapping onto a canonical name, never a second kind).
_SHA_PREFIXES = ("sha:", "commit:", "git:")

_HEX = re.compile(r"^[0-9a-fA-F]+$")
_TASK = re.compile(r"^T\d{2,4}$")
_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
_URL = re.compile(r"^https?://", re.I)
#: Opaque by amendment A5: real join keys the by-reference index uses, deliberately NOT parsed here.
_OPAQUE_PREFIXES = ("bifrost:", "blob:")


class TargetError(ValueError):
    """A spelling this schema refuses to guess at. Always names what it could not resolve."""


# --------------------------------------------------------------------------- the value types
@dataclass(frozen=True)
class Target:
    """One canonical location. `key` is the join key; the components are kept separately because
    every mature standard does (SARIF `region`, LSP `Position`, OpenTelemetry `code.*`) and because
    the colon string is an input and display convenience, never the authority."""
    kind: str                      # file | file_line | dir | ref | url | verb | question | opaque
    key: str
    work: Optional[str] = None     # canonical worktree name; None means the main checkout
    path: Optional[str] = None
    line: Optional[int] = None
    col: Optional[int] = None
    col_unit: Optional[str] = None
    ref_kind: Optional[str] = None
    stream: Optional[str] = None   # event refs only
    entry_id: Optional[str] = None # event refs only
    flags: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Touch:
    action: str
    target: Target
    role: Optional[str] = None     # "from" / "to" on a move; None otherwise


@dataclass(frozen=True)
class Extraction:
    """`targets is None` means COULD NOT SEE; `targets == []` means looked and there was nothing.
    Amendment B5, after SARIF's null-versus-empty rule, which is this house's own 'zero is not no'
    law (Rill, 2026-09) arriving from the outside and agreeing."""
    targets: Optional[List[Touch]]
    incomplete: bool


@dataclass
class Roots:
    """The planes a path may belong to. `worktrees` are absolute paths exactly as
    `git worktree list --porcelain` reports them; canonical names are derived here, once."""
    main: str
    worktrees: Sequence[str] = ()
    resolve_sha: Optional[Callable[[str], Optional[str]]] = None
    _named: Dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _ambiguous: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.main = _slashes(self.main).rstrip("/")
        paths = [_slashes(w).rstrip("/") for w in self.worktrees]
        # `git worktree list` ALWAYS reports the main checkout as its first entry, so a caller
        # handing that list straight in puts main on both sides. Its leaf then collides with
        # itself, A1's disambiguation fires, and every path in the main tree takes a `work:`
        # prefix built from its own drive letter -- a second key for one plane, which is the
        # defect B2 exists to refuse. Found by the context door's first live run, not by a pin:
        # every pin built Roots by hand with main held separate, and only the real git output has
        # this shape. Dropping it here fixes it for every caller rather than at each call site.
        paths = [w for w in paths if _fold_root(w) != _fold_root(self.main)]
        # The main checkout participates in the collision count (its leaf can collide with a
        # worktree's) but never itself takes a `work:` prefix -- amendment B2, one plane one key.
        leaves: Dict[str, int] = {}
        for p in [self.main] + paths:
            leaves[_leaf(p)] = leaves.get(_leaf(p), 0) + 1
        taken: Dict[str, str] = {}
        for p in paths:
            name = _leaf(p) if leaves[_leaf(p)] == 1 else f"{_parent_seg(p)}-{_leaf(p)}"
            if name in taken:
                # Parent could not break it either. Mark BOTH unresolvable rather than letting the
                # first one win silently: a key that depends on enumeration order is not a key.
                self._ambiguous[p] = name
                self._ambiguous[taken[name]] = name
                continue
            taken[name] = p
        for name, p in taken.items():
            if p not in self._ambiguous:
                self._named[name] = p


# --------------------------------------------------------------------------- small helpers
def _slashes(s: str) -> str:
    return str(s).replace("\\", "/")


def _leaf(p: str) -> str:
    return p.rstrip("/").rsplit("/", 1)[-1]


def _parent_seg(p: str) -> str:
    parts = p.rstrip("/").split("/")
    return parts[-2] if len(parts) >= 2 else ""


def _is_absolute(s: str) -> bool:
    return bool(_DRIVE.match(s)) or s.startswith("/")


def _fold_root(s: str) -> str:
    """Root comparison only. Below-root case is never touched (SARIF's producer rule)."""
    return s.lower()


def _clean_dots(rel: str) -> Tuple[str, bool]:
    """Collapse `.` and `..` WITHOUT following symlinks, clamping at the root. Returns the cleaned
    path and whether a clamp happened -- a clamp is a flag, never a silent rewrite."""
    out: List[str] = []
    clamped = False
    for seg in rel.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if out:
                out.pop()
            else:
                clamped = True
            continue
        out.append(seg)
    return "/".join(out), clamped


# --------------------------------------------------------------------------- ref parsing
def _parse_ref(text: str, roots: Roots) -> Optional[Target]:
    """Returns a ref Target, an opaque Target, or None when `text` is not reference-shaped.
    Raises when it IS reference-shaped but malformed -- a bad ref is never demoted to a path."""
    low = text.lower()

    for pre in _OPAQUE_PREFIXES:
        if low.startswith(pre):
            return Target(kind="opaque", key=text)

    if low.startswith("event:"):
        rest = text[len("event:"):]
        stream, sep, entry = rest.rpartition(":")   # the stream name is itself colonned
        if not sep or not stream or not entry:
            raise TargetError(
                f"malformed event ref {text!r}: expected event:<stream>:<entry-id>, where the "
                f"entry id is everything after the LAST colon")
        return Target(kind="ref", key=f"event:{stream}:{entry}", ref_kind="event",
                      stream=stream, entry_id=entry)

    for pre in _SHA_PREFIXES:
        if low.startswith(pre):
            return _sha_target(text[len(pre):], roots, text)
    if _HEX.match(text) and len(text) == 40:
        return _sha_target(text, roots, text)

    if low.startswith("task:"):
        tid = text[len("task:"):]
        if not _TASK.match(tid):
            raise TargetError(f"malformed task ref {text!r}: expected task:T followed by 2-4 digits")
        return Target(kind="ref", key=f"task:{tid}", ref_kind="task")

    if low.startswith("learn:experiment:"):          # alias of lesson: (amendment A6)
        name = text[len("learn:experiment:"):]
        if not name:
            raise TargetError(f"malformed lesson ref {text!r}: no experiment name")
        return Target(kind="ref", key=f"lesson:experiment:{name}", ref_kind="lesson")

    if low.startswith("lesson:"):
        rest = text[len("lesson:"):]
        if not rest:
            raise TargetError(f"malformed lesson ref {text!r}: no lesson id")
        return Target(kind="ref", key=f"lesson:{rest}", ref_kind="lesson")

    if low.startswith("mem:"):
        rest = text[len("mem:"):]
        if not rest or ":" not in rest:
            raise TargetError(f"malformed mem ref {text!r}: expected mem:<family>:<id>")
        return Target(kind="ref", key=f"mem:{rest}", ref_kind="mem")

    for kind in ("doc", "session", "seat", "verb"):
        if low.startswith(kind + ":"):
            rest = text[len(kind) + 1:]
            if not rest:
                raise TargetError(f"malformed {kind} ref {text!r}: nothing after the prefix")
            if kind == "verb":
                return Target(kind="verb", key=f"verb:{rest}")
            return Target(kind="ref", key=f"{kind}:{rest}", ref_kind=kind)

    return None


def _sha_target(hexish: str, roots: Roots, original: str) -> Target:
    """Amendment B3: the stored key is the FULL forty. A short sha is a leading substring that is
    unique only while the repository stays small, so storing one mints a key that decays."""
    if not _HEX.match(hexish) or not (7 <= len(hexish) <= 40):
        raise TargetError(f"malformed sha ref {original!r}: expected 7-40 hex characters")
    full = hexish.lower()
    if len(full) < 40:
        resolver = roots.resolve_sha
        full = (resolver(full) or "") if resolver else ""
        if not full:
            raise TargetError(
                f"short sha {original!r} could not be resolved to its full form; refusing rather "
                f"than storing a key that may become ambiguous")
        full = full.lower()
    return Target(kind="ref", key=f"sha:{full}", ref_kind="sha")


# --------------------------------------------------------------------------- path parsing
def _resolve_root(abs_path: str, roots: Roots) -> Tuple[Optional[str], str]:
    """Longest matching root wins, so a worktree nested inside the main checkout beats the main
    root that contains it (amendment A3). Returns (worktree name or None, repo-relative path)."""
    cand = _fold_root(abs_path)
    best: Optional[Tuple[int, Optional[str], str]] = None

    for name, root in roots._named.items():
        r = _fold_root(root)
        if cand == r or cand.startswith(r + "/"):
            rel = abs_path[len(root):].lstrip("/")
            if best is None or len(root) > best[0]:
                best = (len(root), name, rel)

    for amb_root, amb_name in roots._ambiguous.items():
        r = _fold_root(amb_root)
        if cand == r or cand.startswith(r + "/"):
            raise TargetError(
                f"worktree name collision: {amb_name!r} is claimed by more than one worktree and "
                f"the parent segment does not break it; refusing to mint an order-dependent key "
                f"for {abs_path!r}")

    r = _fold_root(roots.main)
    if (cand == r or cand.startswith(r + "/")) and (best is None or len(roots.main) > best[0]):
        best = (len(roots.main), None, abs_path[len(roots.main):].lstrip("/"))

    if best is None:
        raise TargetError(
            f"{abs_path!r} is outside every known root. The main checkout and the worktrees "
            f"`git worktree list` reports are the only planes this schema names; a separate clone "
            f"is a WORLD and belongs to that organ, not to work:")
    return best[1], best[2]


def _split_line_col(rel: str, exists: Callable[[str], bool], work: Optional[str]) -> Tuple[str, Optional[int], Optional[int]]:
    """Amendment B4. The all-digit tail is an INPUT convenience, and existence outranks it: on
    Windows the colon is reserved for NTFS alternate data streams, so `app.py:12` is a legal path
    to stream `12` of `app.py`. If such a path exists, it is a path."""
    if exists(_key_for(work, rel, None, None)):
        return rel, None, None

    line = col = None
    head, sep, tail = rel.rpartition(":")
    if sep and tail.isdigit() and head:
        head2, sep2, tail2 = head.rpartition(":")
        if sep2 and tail2.isdigit() and head2:
            return head2, int(tail2), int(tail)      # path:line:col
        return head, int(tail), None                 # path:line
    return rel, line, col


def _key_for(work: Optional[str], path: str, line: Optional[int], col: Optional[int]) -> str:
    key = f"work:{work}:{path}" if work else path
    if line is not None:
        key += f":{line}"
        if col is not None:
            key += f":{col}"
    return key


# --------------------------------------------------------------------------- the door
def parse(text: str, *, roots: Roots, cwd: Optional[str] = None,
          exists: Optional[Callable[[str], bool]] = None) -> Target:
    """Resolve one spelling to one canonical Target. Refuses rather than guesses."""
    raw = str(text or "").strip()
    if not raw:
        raise TargetError("empty anchor")
    exists = exists or (lambda _k: False)

    if _URL.match(raw):
        return Target(kind="url", key=raw)

    ref = _parse_ref(raw, roots)          # ref-before-path precedence (sealed)
    if ref is not None:
        return ref

    if any(ch.isspace() for ch in raw):   # bare prose routes to `cast`, never resolved as a path
        return Target(kind="question", key=raw)

    work: Optional[str] = None
    body = _slashes(raw)
    flags: List[str] = []
    # The trailing slash is the TYPE MARKER and it must be read off the input before any
    # normalization, because dot-cleaning drops empty segments and would silently eat it --
    # turning a directory anchor into a same-named file anchor, which is two planes one key again.
    is_dir = body.endswith("/")

    if body.lower().startswith("work:"):
        _, _, rest = body.partition(":")
        name, sep, tail = rest.partition(":")
        if not sep:
            raise TargetError(f"malformed work anchor {text!r}: expected work:<name>:<path>")
        if name.lower() == "main":
            raise TargetError(
                "there is no work:main: spelling. An unprefixed path IS the main checkout; a "
                "second key for one plane is the defect this schema exists to end")
        if name not in roots._named:
            raise TargetError(f"unknown worktree {name!r} in {text!r}")
        work, body = name, tail
    else:
        if body.lower().startswith("file:"):      # amendment A5: file: is a path alias
            body = body[len("file:"):]
        if _is_absolute(body):
            work, body = _resolve_root(body, roots)
        else:
            # Resolve the plane FIRST, then clean dots inside it. Cleaning an absolute join instead
            # would let `..` chew through the root's own segments and escape without ever tripping
            # the clamp -- the path would silently become a different plane's path.
            base = _slashes(cwd or roots.main).rstrip("/")
            base_work, base_rel = _resolve_root(base, roots)
            combined = posixpath.join(base_rel, body) if base_rel else body
            cleaned, clamped = _clean_dots(combined)
            if clamped:
                flags.append("clamped")
            work, body = base_work, cleaned

    body, clamped = _clean_dots(body)
    if clamped and "clamped" not in flags:
        flags.append("clamped")
    if is_dir:
        body += "/"
        return Target(kind="dir", key=_key_for(work, body, None, None), work=work, path=body,
                      flags=tuple(flags))

    path, line, col = _split_line_col(body, exists, work)
    key = _key_for(work, path, line, col)
    return Target(kind="file_line" if line is not None else "file", key=key, work=work, path=path,
                  line=line, col=col, col_unit=COL_UNIT if col is not None else None,
                  flags=tuple(flags))


# --------------------------------------------------------------------------- command extraction
_READ = {"cat", "head", "tail", "less", "more", "type", "get-content", "wc", "md5sum", "sha256sum"}
_SEARCH = {"grep", "rg", "ls", "dir", "find", "fd", "get-childitem", "select-string", "stat"}
_MOVE = {"mv", "move-item", "ren", "rename", "rename-item"}
_DELETE = {"rm", "del", "erase", "remove-item", "unlink", "rmdir"}
_COPY = {"cp", "copy", "copy-item", "xcopy", "robocopy"}
_EXEC = {"py", "py.exe", "python", "python3", "node", "bash", "sh", "pwsh", "powershell", "deno"}
_WRITE = {"tee", "out-file", "set-content", "add-content", "touch"}
_INPLACE = {"sed", "awk", "perl"}
#: Flags that take a path as their value rather than being one.
_PATH_FLAGS = {"-path", "-literalpath", "-destination", "-filepath", "-outfile", "-o", "--output"}
_HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")
_CMDSUB = re.compile(r"\$\(|`")
_STDIN_SCRIPT = re.compile(r"\b(py|py\.exe|python|python3|node|bash|sh|pwsh|powershell)\b\s+-\s*$")


def extract(command: str, *, shell: str = "bash", cwd: Optional[str] = None,
            roots: Roots, exists: Optional[Callable[[str], bool]] = None) -> Extraction:
    """What one shell command reads, writes, executes, searches, moves or deletes.

    Returns `targets=None` when the command cannot be seen into (a script fed on stdin, a command
    substitution), never a fabricated target and never a misleading empty list."""
    cmd = str(command or "")
    exists = exists or (lambda _k: False)

    first_line = cmd.split("\n", 1)[0]
    hd = _HEREDOC.search(first_line)
    if hd:
        before = first_line[:hd.start()]
        if _STDIN_SCRIPT.search(before.rstrip()):
            # A script arrives on stdin and opens whatever it likes. ShellCheck's SC1090 is the
            # precedent: say you could not follow it, by name, rather than reporting a clean zero.
            return Extraction(targets=None, incomplete=True)
        cmd = before                       # the heredoc body is data; the wrapper's redirect is not
    if _CMDSUB.search(cmd):
        return Extraction(targets=None, incomplete=True)

    touches: List[Touch] = []
    for stage in re.split(r"\|\||&&|[|;]", cmd):
        stage = stage.strip()
        if stage:
            _extract_stage(stage, shell, cwd, roots, exists, touches)

    # One target may be reached twice in a stage (`cp a a`); keep first-seen order, drop twins.
    seen = set()
    uniq: List[Touch] = []
    for t in touches:
        sig = (t.action, t.role, t.target.key)
        if sig not in seen:
            seen.add(sig)
            uniq.append(t)
    return Extraction(targets=uniq, incomplete=False)


def _extract_stage(stage: str, shell: str, cwd: Optional[str], roots: Roots,
                   exists: Callable[[str], bool], out: List[Touch]) -> None:
    try:
        tokens = shlex.split(stage, posix=False)
    except ValueError:
        tokens = stage.split()
    if not tokens:
        return

    def resolve(tok: str) -> Optional[Target]:
        """A token becomes a target only if it is an existing repo-relative path or an absolute
        path under a known root. Anything else is left alone: inventing a read from a bare word is
        how an extractor starts lying."""
        t = tok.strip("'\"")
        if not t or t.startswith("-"):
            return None
        body = _slashes(t)
        glob = ""
        if "*" in body or "?" in body:
            # A glob is captured LITERALLY as its directory; expanding it after the fact would
            # record files the command never touched.
            body, glob = (body.rsplit("/", 1)[0] + "/", "glob") if "/" in body else ("", "glob")
            if not body:
                return None
        try:
            tgt = parse(body, roots=roots, cwd=cwd, exists=exists)
        except TargetError:
            return None
        if tgt.kind not in ("file", "file_line", "dir"):
            return None
        if _is_absolute(_slashes(t)) or glob or exists(tgt.key):
            return tgt
        return None

    def emit(action: str, tok: str, role: Optional[str] = None) -> None:
        tgt = resolve(tok)
        if tgt is not None:
            out.append(Touch(action=action, target=tgt, role=role))

    # Redirections first: they are writes no matter what verb precedes them.
    args: List[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in (">", ">>", "1>", "2>", "&>"):
            if i + 1 < len(tokens):
                emit("write", tokens[i + 1])
            i += 2
            continue
        args.append(tok)
        i += 1

    if not args:
        return
    verb = args[0].strip("'\"").lower()
    rest = args[1:]

    # PowerShell path-bearing flags: the VALUE is the path, the flag is not.
    flagged: List[Tuple[str, str]] = []
    plain: List[str] = []
    j = 0
    while j < len(rest):
        a = rest[j]
        if a.lower() in _PATH_FLAGS and j + 1 < len(rest):
            flagged.append((a.lower(), rest[j + 1]))
            j += 2
            continue
        if not a.startswith("-"):
            plain.append(a)
        j += 1

    if verb in _WRITE:
        for _f, v in flagged:
            emit("write", v)
        for a in plain:
            emit("write", a)
        return
    if verb in _MOVE:
        if len(plain) >= 2:
            emit("move", plain[0], role="from")
            emit("move", plain[-1], role="to")
        for f, v in flagged:
            emit("move", v, role="to" if f in ("-destination",) else "from")
        return
    if verb in _DELETE:
        for a in plain:
            emit("delete", a)
        for _f, v in flagged:
            emit("delete", v)
        return
    if verb in _COPY:
        if len(plain) >= 2:
            emit("read", plain[0])
            emit("write", plain[-1])
        for f, v in flagged:
            emit("write" if f in ("-destination",) else "read", v)
        return
    if verb in _SEARCH:
        for a in plain:
            emit("search", a)
        for _f, v in flagged:
            emit("search", v)
        return
    if verb in _EXEC:
        for a in plain:
            if resolve(a) is not None:
                emit("exec", a)
                break                      # the script is the first path-shaped argument
        return
    if verb in _INPLACE:
        inplace = any(a.lower().startswith("-i") for a in rest)
        for a in plain:
            emit("write" if inplace else "read", a)
        return
    if verb in _READ:
        for a in plain:
            emit("read", a)
        for _f, v in flagged:
            emit("read", v)
        return
    # An unknown verb contributes nothing. `cd`, `git status` and `echo hello world` are CONTEXT,
    # and a measured zero is the honest answer for them.
    return
