"""seat_identity -- WHO AM I, resolved per SESSION instead of per PROCESS.

THE DEFECT THIS REPLACES (measured 2026-08-01, receipts in tests/test_seat_identity_resolver.py):
every hook resolved identity as `os.getenv("AKASHIC_AGENT_ID") or "claude"`. That env lives in a
settings.json shared by every home-rooted session, and a running session cannot mutate its own
process env -- so a seat could not declare its own name, and the fallback did not merely lose
information, it IMPERSONATED THE CONDUCTOR. One session held two roster rows; advisory locks
locked a seat out of its own files; the stop hook's wakeability check could not see a correctly
named watcher and prescribed arming a duplicate under the conductor's name.

THE THREE BRANCHES, in order. Each is a different kind of knowledge:
    1. BINDING   what this SESSION declared about itself     -- ground truth, session-scoped
    2. ENV       what the PROCESS was launched believing     -- ambient, inherited, shared
    3. UNKNOWN   we do not know, and we say so out loud      -- never a real peer's name

Branch 3 is the load-bearing one. Prior art is unanimous that a two-level name needs an explicit
binding step (XMPP resource binding, Matrix device_id, Kafka group.instance.id, OTel
service.instance.id, Elixir Registry via-tuples -- atom art_20260801_concurrent-seats-one-program-
prior-art_a69ecf). XMPP's Bind 2 goes further and REFUSES a stanza with no explicit sender
(`unknown-sender`) when several resources share one stream, which is exactly one Claude Code
process hosting several seats. We take that posture one notch softer -- loud, never fatal --
because a hook must never break a session (fail-open is the hook contract, T029/K8).

WHY unknown-<sid8> AND NOT A BARE "unknown": two identity-less seats must not collide into one
row. The session discriminator keeps them distinct while still reading as unresolved to a human.

PHYSICS: this module is in core/ and imports NOTHING outward -- no scripts/, no agent/, no
harness. It touches one file per session in the OS temp dir, the same plane wake_seat uses for
session markers, so a crashed session leaves no durable garbage in the repo.
"""
from __future__ import annotations

import os
import re
import tempfile
from typing import Optional

# A seat id is a short kebab/underscore token. Anything else is refused rather than trusted:
# an id is used to build Redis keys and file names, so it is an injection surface.
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._#-]{0,63}$", re.IGNORECASE)

_PREFIX = "akashic_seat_"
_SUFFIX = ".id"


def _dir(binding_dir: Optional[str]) -> str:
    return binding_dir if binding_dir else tempfile.gettempdir()


def _path(session_id: str, binding_dir: Optional[str]) -> str:
    return os.path.join(_dir(binding_dir), f"{_PREFIX}{session_id}{_SUFFIX}")


def sid8(session_id: str) -> str:
    """The 8-char session discriminator every seat row is keyed by."""
    return (str(session_id or "").strip() or "unknown")[:8]


def unknown_id(session_id: str) -> str:
    """The loud fallback. Reads as unresolved to a human and stays unique per session."""
    return f"unknown-{sid8(session_id)}"


def valid(agent_id: str) -> bool:
    return bool(agent_id) and bool(_ID_RE.match(str(agent_id).strip()))


def declare(agent_id: str, session_id: str, binding_dir: Optional[str] = None) -> bool:
    """Bind THIS session to a seat name. Idempotent; last declaration wins.

    Returns False rather than raising on any failure -- a seat that cannot write its binding
    still has to run, it just keeps resolving to unknown-<sid8>, which is the honest state.
    """
    if not session_id or not valid(agent_id):
        return False
    try:
        d = _dir(binding_dir)
        os.makedirs(d, exist_ok=True)
        tmp = _path(session_id, binding_dir) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(str(agent_id).strip())
        os.replace(tmp, _path(session_id, binding_dir))   # atomic: never a half-written id
        return True
    except Exception:
        return False


def declared(session_id: str, binding_dir: Optional[str] = None) -> Optional[str]:
    """The binding alone, with no env fallback. None when this session never declared."""
    if not session_id:
        return None
    try:
        with open(_path(session_id, binding_dir), encoding="utf-8") as fh:
            got = fh.read().strip()
        return got if valid(got) else None
    except Exception:
        return None


def resolve(session_id: str, binding_dir: Optional[str] = None,
            env_var: str = "AKASHIC_AGENT_ID") -> str:
    """binding -> env -> unknown-<sid8>. NEVER raises, NEVER returns a peer's name on a guess.

    Backward compatible by construction: with no binding file and the env set, this returns
    exactly what every call site returned before the slice. The only behaviour that CHANGES is
    the case that was previously a silent lie.
    """
    got = declared(session_id, binding_dir)
    if got:
        return got
    try:
        env = (os.getenv(env_var) or "").strip()
    except Exception:
        env = ""
    if valid(env):
        return env
    return unknown_id(session_id)


def resolved_from(session_id: str, binding_dir: Optional[str] = None,
                  env_var: str = "AKASHIC_AGENT_ID") -> str:
    """Which branch answered: 'binding' | 'env' | 'unknown'. For doors that must SHOW their
    work -- a surface that cannot say where an identity came from is how this defect hid."""
    if declared(session_id, binding_dir):
        return "binding"
    try:
        if valid((os.getenv(env_var) or "").strip()):
            return "env"
    except Exception:
        pass
    return "unknown"


#: Non-routable by construction (RFC 6762 reserves .local for mDNS), so a seat address can
#: never resolve, never receive mail, and never collide with a real GitHub account. A seat
#: that borrowed a routable address would mis-attribute work to a PERSON.
GIT_IDENTITY_DOMAIN = "akashic-aurora.local"


def git_identity_env(agent_id) -> dict:
    """The env a launcher merges into a seat's process so git records the SEAT as author.

    t384 RULING 2. The measured defect: commit b66e6f67 was authored by a seat per the bus
    and the ledger, while git recorded the machine owner -- because seats commit through
    exec using the human's git config. The seam is the LAUNCHER, not a commit hook: git
    resolves authorship when it builds the commit object, so a hook (running in a child
    process, after the fact) cannot change the author already in flight.

    AUTHOR only, never COMMITTER -- that is git's own distinction between who wrote a change
    and who applied it, and it keeps the human honestly in the history rather than erasing
    them. Returns {} for an unidentified or malformed id: an unknown process must fall
    through to the human's git config, which is at least honest about not knowing, rather
    than receive a fabricated seat identity. Reusing valid() also makes the values
    shell-safe for free -- _ID_RE admits no spaces, quotes, or metacharacters.
    """
    aid = str(agent_id).strip() if agent_id else ""
    if not valid(aid):
        return {}
    return {"GIT_AUTHOR_NAME": aid,
            "GIT_AUTHOR_EMAIL": f"{aid}@{GIT_IDENTITY_DOMAIN}"}


def clear(session_id: str, binding_dir: Optional[str] = None) -> bool:
    """Drop this session's binding (its own only -- a sibling's is unreachable from here)."""
    try:
        os.remove(_path(session_id, binding_dir))
        return True
    except Exception:
        return False
