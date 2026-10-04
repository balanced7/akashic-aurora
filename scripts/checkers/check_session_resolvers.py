"""Session-resolver guardrail -- one meaning, one implementation, counted and ratcheted.

Semantic Relationship: Guardrails enforce OneResolverPerMeaning

WHY THIS EXISTS, AND IT IS A MEASURED NUMBER NOT A PREFERENCE
-------------------------------------------------------------
"Which session is this" was resolved in many places on 2026-10-03, and they did not agree.
Three env-var orders, three return shapes, two empty conventions, and TWO separate truncation
sites (`operator_reply` to 8 chars, `agent_cli._sid8_of`). A truncated id can never join a
full-length one, which is the same defect measured the same day on the target plane, where
two address classes intersected at ZERO of 365.

The consequence was countable: `context --stats` over 24h showed touch 796/796 and phase
88/88 carrying a session id, against boot 0/23, boot_unverified 0/22, fail 0/17 and
learning 0/4. A filed lesson could not be joined to the session that produced it.

`core/coord/session_id.py` is now the one resolver, and it lifted the BEST of the existing
contracts rather than the simplest: payload outranks the ambient environment, the source is
always returned ("payload" / "env" / "unknown"), and nothing is truncated -- callers take
their own display form via `short()`, at the point of display, where the loss is visible.

WHY A RATCHET RATHER THAN A SWEEP
---------------------------------
There are too many sites to migrate in one commit, several sit in other seats' lanes, and a
big-bang rewrite of session resolution is exactly the change that breaks a fleet quietly. So
this counts instead. `scripts/githooks/pre_commit.py` adopts the count at TODAY's level; from
the next commit on it may FALL or hold, and may never RISE -- the same counted-ratchet
discipline the other guardrails use, because a commit cannot be blamed for debt that predates
it.

The admission this file exists to prevent: the lesson
`when_a_fix_primitive_is_born_sweep_the_class_that_birthed_it` says to grep the tree for the
unfixed shape AT THE MOMENT the primitive lands. When `session_id.py` landed, its author named
TWO remaining sites, then grepped and found fifteen, then wrote this and found more still.
Naming is not sweeping, and memory is not a checker.

WHAT COUNTS, AND WHAT DELIBERATELY DOES NOT
-------------------------------------------
A violation is a session variable passed to an ENVIRONMENT READ outside the sanctioned module.
Three things are deliberately not violations, and the first version of this checker got all
three wrong -- it reported 36 by counting them:

  * comments and docstrings -- prose about the rule is not the rule;
  * a message string that merely names the variable, e.g.
    `print("ERROR: no session id (CLAUDE_CODE_SESSION_ID unset)")`, which is a human sentence;
  * two variables on one line counted as two sites.

A guardrail that fires on its own documentation is the punchline of the house lesson
`a_pin_that_reads_prose_measures_prose_and_it_fails_in_both_directions`, and this one quoted
that lesson in its docstring while doing it. The discriminator is therefore structural: a
RESOLVER passes the name to `os.getenv(...)` / `os.environ.get(...)` / `os.environ[...]`;
a message merely contains it.

Run: py scripts/checkers/check_session_resolvers.py     (0 = one resolver, 1 = more than one)
"""
from __future__ import annotations

import io
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: The sanctioned home. Every other reader delegates to it.
SANCTIONED = ("core/coord/session_id.py",)

#: Checkers and tests legitimately name the variables while policing or exercising them.
EXEMPT_PREFIXES = ("scripts/checkers/", "tests/")

SESSION_VARS = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID", "AKASHIC_SESSION_ID")

#: Reported SEPARATELY, never counted. In core/comm/bus.py and core/eye/position.py this is
#: the FIRST link of the session-resolution chain; in the runners it is a process incarnation
#: id with nothing to do with a Claude session. Folding them together would inflate the
#: ratchet with work that is not this class -- so it is surfaced as a note, not a violation.
INCARNATION_VAR = "BIFROST_INCARNATION"

_ENV_READ = ("getenv", "get", "environ")

SCAN_DIRS = ("core", "agent", "scripts")
SCAN_FILES = ("agent_cli.py", "ai_setup_mcp.py")


def _env_read_sites(path: Path, needles):
    """{line: text} for each line where a needle is passed to an environment read."""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except Exception:                                                     # noqa: BLE001
        return {}
    if not any(v in src for v in needles):
        return {}
    try:
        toks = [t for t in tokenize.generate_tokens(io.StringIO(src).readline)
                if t.type not in (tokenize.COMMENT, tokenize.NL)]
    except Exception:                                                     # noqa: BLE001
        return {}

    found, prev = {}, None
    for i, tok in enumerate(toks):
        if tok.type != tokenize.STRING:
            prev = tok.type
            continue
        is_doc = prev in (None, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)
        prev = tok.type
        if is_doc:
            continue
        # THE DISCRIMINATOR, third and simplest version. Is the literal EXACTLY a variable
        # name, or a sentence that happens to contain one?
        #
        #   os.getenv("CLAUDE_CODE_SESSION_ID")              -> exactly the name  -> count
        #   for _v in ("CLAUDE_CODE_SESSION_ID", "..."):      -> exactly the name  -> count
        #   print("ERROR: no session id (CLAUDE_... unset)")  -> a sentence        -> skip
        #
        # Version one matched the name anywhere and counted error messages (36). Version two
        # walked back for an `os.getenv(`-shaped opener and lost core/comm/liveness.py:165,
        # which reads the vars out of a tuple in a loop -- over-counting traded for
        # under-counting. A name used as a name is the property both were groping at.
        if tok.string.strip("'\"") in needles:
            found.setdefault(tok.start[0], tok.line.strip()[:84])
    return found


def check() -> int:
    targets = []
    for d in SCAN_DIRS:
        p = ROOT / d
        if p.is_dir():
            targets += [f for f in p.rglob("*.py") if "__pycache__" not in f.parts]
    for f in SCAN_FILES:
        p = ROOT / f
        if p.is_file():
            targets.append(p)

    offenders, incarnation = [], []
    for path in sorted(targets):
        rel = path.relative_to(ROOT).as_posix()
        if rel in SANCTIONED or rel.startswith(EXEMPT_PREFIXES):
            continue
        for ln, text in sorted(_env_read_sites(path, SESSION_VARS).items()):
            offenders.append((rel, ln, text))
        for ln, _t in sorted(_env_read_sites(path, (INCARNATION_VAR,)).items()):
            incarnation.append((rel, ln))

    print("=" * 60)
    print("Sanctioned resolver: " + ", ".join(SANCTIONED))
    print("Payload outranks the ambient environment; the source is always returned;")
    print("nothing is truncated inside a resolver.\n")

    if incarnation:
        print("NOTE, not counted: %d site(s) read %s. In bus.py and eye/position.py it is the"
              % (len(incarnation), INCARNATION_VAR))
        print("first link of the session chain; in the runners it is a process incarnation.")
        print("Two meanings on one variable -- worth resolving, but it is not this class.\n")

    if offenders:
        # The heading MUST start with "VIOLATIONS": pre_commit._count_violations only counts
        # itemised "- [" lines while inside a VIOLATIONS block, and otherwise falls back to
        # counting FAIL: summaries. The first version of this checker titled the block
        # "HAND-ROLLED SESSION RESOLVERS" and the ratchet adopted 1 instead of 16 -- a guard
        # with fifteen sites of silent slack, which is that function's own docstring warning
        # ("a baseline built from a wrong count is not a ratchet, it is a rubber stamp")
        # happening to the guard being added.
        print("VIOLATIONS -- hand-rolled session resolvers (%d):" % len(offenders))
        for rel, ln, text in offenders:
            print("  - [%s:%d] %s" % (rel, ln, text))
        print("\nFAIL: %d site(s) resolve a session id outside %s."
              % (len(offenders), SANCTIONED[0]))
        print("      Delegate: from core.coord.session_id import ambient_session_id, session_of")
        print("      Need a short form? short(sid) AT THE POINT OF DISPLAY -- never inside a")
        print("      resolver, because a truncated id cannot join a full-length one.")
        return 1

    print("PASS: every session id is resolved in one place.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
