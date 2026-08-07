"""ask_bg -- a helper call that outlives your turn without becoming a seat (T205).

THE FRICTION THIS REMOVES, measured on 2026-08-06. Every fence that day ran serially --
24s, 43s, 48s, 54s of dead wall-clock each -- because `ask` blocks and its answer lands in
the caller's context whole. The fan primitive existed (ask_many, six workers) and was
unaffordable for exactly one reason: attention, not capability. So I asked two helpers
instead of six and paid the latency on both.

T204 removed the other half of the problem by taking the token ceiling off: with output
landing in a file rather than a context window, there is no longer any reason for a
background answer to hold back.

STILL NOT A SEAT (T171's law, and pinned). No identity, no singleton lock, no cursor, no
mailbox, no heartbeat, no roster row, no reaper protection. A backgrounded ask is a CALL
whose result lands somewhere durable instead of in the caller's window. Nothing addresses
it but the handle its caller holds -- which is also why it needs no wake machinery at all.

DESIGNED AGAINST ONE SPECIFIC FAILURE: this repo has 1,324 unopened mailbox items. "Write
it somewhere and check it later" is precisely the pattern that produced them. So:
  * the handle is printed immediately and `--get` is one hop
  * RUNNING, DONE, FAILED and ORPHANED are four distinct readings -- an unfinished ask must
    never look like an empty answer, or the reader learns to stop looking
  * a record whose process is gone but whose status never advanced reads ORPHANED, so a
    dead child cannot look busy forever (the wedge shape this fleet already knows)
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

ASK_DIR = Path(__file__).resolve().parents[2] / "state" / "asks"
#: A record still "running" past this with no live process is ORPHANED rather than busy.
ORPHAN_AFTER_S = float(os.getenv("AKASHIC_ASK_BG_ORPHAN_S", "1800"))


def new_handle() -> str:
    """Short enough to type from a terminal, unique enough not to collide in a session."""
    return uuid.uuid4().hex[:8]


def _path(handle: str) -> Path:
    return ASK_DIR / f"{handle}.json"


def write_record(handle: str, rec: Dict[str, Any]) -> None:
    """Best-effort durable write. Never raises: losing bookkeeping must not lose the ask."""
    try:
        ASK_DIR.mkdir(parents=True, exist_ok=True)
        rec = {"handle": handle, "started": rec.get("started", time.time()), **rec}
        _path(handle).write_text(json.dumps(rec, ensure_ascii=False, default=str),
                                 encoding="utf-8")
    except Exception:
        # Was `except OSError`, which made "Never raises" false: a circular reference
        # raises ValueError out of json.dumps and would have propagated into a caller
        # that was promised it could not. Same fan-out audit as _alive below.
        pass


def read_record(handle: str) -> Optional[Dict[str, Any]]:
    """The record, or None for an unknown handle. None is NOT an empty answer -- a typo and
    a silent helper are different facts and must render differently."""
    try:
        return json.loads(_path(str(handle)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def finish(handle: str, result: Dict[str, Any]) -> None:
    """Attach the child's structured result -- the same shape `ask --json` produces, so the
    background and foreground paths cannot drift into reporting different things."""
    rec = read_record(handle) or {"handle": handle}
    rec["status"] = "done" if result.get("ok") or result.get("partial") else "failed"
    rec["result"] = result
    rec["finished"] = time.time()
    write_record(handle, rec)
    _emit_completed(handle, rec, result)


def _emit_completed(handle: str, rec: Dict[str, Any], result: Dict[str, Any]) -> None:
    """One durable event per finished ask (T206).

    WHY AN EVENT AND NOT MAIL. A background ask is PULL -- the caller must remember to
    `--get` -- and "remember to check later" is what produced this repo's 1,324 unopened
    mailbox items. Mail would fix the remembering by adding a wake surface, a cursor, and
    one more thing that accumulates unread; all three were measured failing on 2026-08-06.
    An event adds none of them: durable, append-only, queryable by any reader, and it does
    not demand attention -- the right default for something that may fire dozens of times
    an hour. Waking someone stays opt-in, because a notification that always fires is how
    a reader learns to ignore notifications.

    IT IS ALSO THE ANCHOR THE METRICS LACKED. Sol's friction list named commands per task,
    operator interventions and recovery time, and all three were unbuildable because
    nothing durable recorded a DELEGATION. This does: cost, duration, model, outcome,
    truncation class, and whether the ask was grounded in files.

    The answer BODY never rides along -- the firehose is a durable index, not a document
    store, and the body is one hop away via the handle. Never raises: observability must
    not be able to destroy the thing it observes.
    """
    try:
        from core.events.event_log import capture_event
        outcome = ("partial" if result.get("partial")
                   else "done" if result.get("ok") else "failed")
        started = rec.get("started")
        detail = {
            "handle": handle, "outcome": outcome,
            "model": result.get("model"), "usd": result.get("usd"),
            "elapsed_s": result.get("elapsed_s"),
            "prompt_tokens": result.get("prompt_tokens"),
            "completion_tokens": result.get("completion_tokens"),
            "reasoning_tokens": result.get("reasoning_tokens"),
            "truncation": result.get("truncation"),
            "continuations": result.get("continuations"),
            # The T203 lever, recorded so its effect is measurable rather than believed:
            # did this ask carry source files, or was the helper reasoning blind?
            "grounded": bool(rec.get("with")),
            "n_files": len(rec.get("with") or []),
            "why": result.get("why"),
            "waited_s": (round(time.time() - float(started), 2) if started else None),
        }
        capture_event("ask_completed",
                      f"background ask {handle} {outcome}"
                      + (f" ({result.get('model')})" if result.get("model") else ""),
                      agent_id=os.environ.get("AKASHIC_AGENT_ID", "claude"),
                      refs=[handle], detail=detail)
    except Exception:
        pass


def _alive(pid: Any) -> Optional[bool]:
    """Is that pid still running? None when we cannot tell -- and cannot-tell must not be
    reported as dead, or a healthy child gets declared orphaned."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    # FOUND BY A FAN-OUT OVER THIS REPO'S OWN DOCSTRINGS (T215), hours after it was
    # written: the original caught (OSError, SubprocessError) and returned False, so a
    # `tasklist` TIMEOUT -- which is a SubprocessError -- reported a healthy child as
    # dead, and summarize() rendered it ORPHANED: "no longer running, re-ask, nothing
    # will arrive". That is precisely the failure the docstring above forbids, violated
    # one screen below where the law is stated. Each failure now maps to what it actually
    # proves.
    import subprocess
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                                 capture_output=True, text=True, timeout=10,
                                 stdin=subprocess.DEVNULL)
            if out.returncode != 0:
                return None                     # the probe failed: cannot tell
            return str(pid) in (out.stdout or "")
        os.kill(pid, 0)
        return True
    except subprocess.SubprocessError:
        return None                             # timeout/probe failure: cannot tell
    except ProcessLookupError:
        return False                            # the ONE error that proves death
    except PermissionError:
        return True                             # it exists; we merely may not signal it
    except OSError:
        return None                             # any other OS failure: cannot tell
    except Exception:
        return None


def summarize(rec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """One state and one next step. Four readings, deliberately distinct."""
    if not rec:
        return {"state": "UNKNOWN", "next": "no ask by that handle -- check the id, or "
                                            "`ask --list` to see recent ones"}
    status = str(rec.get("status") or "")
    result = rec.get("result") or {}
    if status == "done":
        # T226: a backgrounded FAN has branches and no single `answer`, so this rendered
        # "DONE" with an empty body -- three paid-for answers on disk and nothing shown.
        # A fan is summarised as a fan: how many landed, what they cost, and whether they
        # were N findings or one finding billed N times (the T182 verdict is the whole
        # reason to read a fan at all).
        branches = result.get("branches") or []
        if branches:
            n, n_ok = result.get("n") or len(branches), result.get("n_ok")
            div = result.get("diversity")
            body = "\n\n".join(
                f"--- branch {b.get('i')} "
                f"[{'ok' if b.get('ok') and not b.get('partial') else ('PARTIAL' if b.get('partial') else 'FAIL')}] "
                f"{'-' * 40}\n{b.get('answer') or '(' + str(b.get('why') or 'no answer') + ')'}"
                for b in branches)
            # T228: whoever reads a retrieved fan may never have seen the command that made
            # it, so this is the surface where the shape MOST needs saying. One shared
            # prescription with the CLI renderer.
            nxt = f"read {n_ok} of {n} branches"
            if div:
                from core.comm.ask import diversity_prescription
                nxt += " -- " + (result.get("diversity_next") or diversity_prescription(
                    div, bool(result.get("homogeneous")), n_compared=n_ok or n))
            return {"state": "DONE", "handle": rec.get("handle"), "answer": body,
                    "usd": result.get("usd"), "partial": bool(result.get("partial")),
                    "n": n, "n_ok": n_ok, "diversity": div, "next": nxt}
        return {"state": "DONE", "handle": rec.get("handle"),
                "answer": result.get("answer"), "usd": result.get("usd"),
                "partial": bool(result.get("partial")),
                "next": "read the answer" + (" -- it is PARTIAL, see `why`"
                                             if result.get("partial") else "")}
    if status == "failed":
        return {"state": "FAILED", "handle": rec.get("handle"),
                "why": result.get("why") or rec.get("why") or "unreported",
                "next": "read `why` -- a STARVED ask needs a narrower question, not a retry"}
    # Still marked running. Is anything actually behind it?
    alive = _alive(rec.get("pid"))
    age = time.time() - float(rec.get("started") or time.time())
    if alive is False or (alive is None and age > ORPHAN_AFTER_S):
        return {"state": "ORPHANED", "handle": rec.get("handle"),
                "next": f"the child is no longer running and never wrote a result "
                        f"(age {age:.0f}s) -- re-ask; nothing will arrive"}
    return {"state": "RUNNING", "handle": rec.get("handle"),
            "age_s": round(age, 1),
            "next": "still working -- do something else and check back with "
                    "`ask --get <handle>`"}


def list_records(limit: int = 20) -> List[Dict[str, Any]]:
    """Recent asks, newest first. Bounded, because an unbounded listing of a growing
    directory is how a listing surface stops being read."""
    out: List[Dict[str, Any]] = []
    try:
        for p in ASK_DIR.glob("*.json"):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
    except OSError:
        return []
    out.sort(key=lambda r: float(r.get("started") or 0), reverse=True)
    return out[:max(1, int(limit))]
