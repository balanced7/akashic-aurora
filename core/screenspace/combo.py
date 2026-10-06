"""The compound verb: hand a brief to a NEW Claude Desktop session (T386 sec.6 step 5).

Daniel, 2026-10-06: "Lets build those and verbify the Ctrl + N and handoff + start new session
combo." The design already named this step ``desktop_prompt``.

WHAT MAKES THIS DIFFERENT FROM THE HAND-DRIVEN VERSION. Last night the same sequence worked by
hand, with ``time.sleep()`` between steps and my own eyes as the oracle. That is not a verb, it
is an anecdote: every step asserted nothing, so a slow frame would have read as success and the
next keystroke would have gone somewhere unintended. Each step here carries a post-condition
that is READ rather than waited out, and the whole chain carries a causal receipt.

THE RECEIPT IS A FILE, NOT A PIXEL. Claude Desktop writes one JSONL per session under
``~/.claude/projects/<slug>/``. So "did a new session actually start, and did it receive MY
text" is answerable on the filesystem: a new ``*.jsonl`` appears and contains the nonce this
module embedded in the brief. That is a causal proof the UI cannot fake -- strictly better than
any screenshot, and the thing design sec.6 step 4 asks for ("prove causal reply + continuity").

HONEST FAILURE MODES, because this drives the operator's real desktop:
  - ``submit=False`` is the DEFAULT. The brief is staged in the composer and NOT sent, which is
    design step 3 ("Dry actions ... no submit"). Submitting is a separate, explicit decision.
  - If the read-back cannot see the composer, the result is ``unverified``, never ``ok``. The
    composer is a Chromium contenteditable with no EditControl, so read-back is best-effort by
    nature and must say so rather than borrow confidence from the keystrokes being dispatched.
  - Every step stops the chain on refusal. A combo that carries on past a failed focus is how
    you type a handoff brief into somebody's YouTube tab.
"""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from core.screenspace import act as A


# --------------------------------------------------------------------------- the receipt plane


def projects_root() -> Path:
    """Where Claude Desktop keeps per-session JSONL transcripts."""
    return Path(os.path.expanduser("~")) / ".claude" / "projects"


def session_dir(session_id: Optional[str] = None) -> Optional[Path]:
    """The project folder holding THIS session's transcript, found by locating our own file.

    Derived rather than assumed: the folder name is a slug of the working directory and this
    host has six of them (``E--``, ``E--AI-Setup``, ``C--Users-L5``, ...), so guessing the slug
    from ``cwd`` picks the wrong one. We look for the file named after our own session instead,
    which is the only self-verifying way to answer "where will a sibling session land".
    """
    root = projects_root()
    if not root.is_dir():
        return None
    sid = session_id
    if not sid:
        try:
            from core.coord.session_id import ambient_session_id
            sid, _src = ambient_session_id()
        except Exception:  # noqa: BLE001
            sid = None
    if sid:
        for d in root.iterdir():
            if d.is_dir() and (d / f"{sid}.jsonl").exists():
                return d
    # Fall back to the folder with the most recently modified transcript -- stated as a fallback
    # in the result so a caller never mistakes it for the derived answer.
    best, best_mt = None, -1.0
    for d in root.iterdir():
        if not d.is_dir():
            continue
        for f in d.glob("*.jsonl"):
            mt = f.stat().st_mtime
            if mt > best_mt:
                best, best_mt = d, mt
    return best


def session_files(d: Optional[Path]) -> frozenset:
    return frozenset(p.name for p in d.glob("*.jsonl")) if d and d.is_dir() else frozenset()


# --------------------------------------------------------------------------- result shape


@dataclass
class Step:
    name: str
    ok: bool
    detail: str = ""
    refusal: Optional[str] = None
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return {"step": self.name, "ok": self.ok, "refusal": self.refusal,
                "detail": self.detail[:400], "elapsed_ms": round(self.elapsed_ms, 1)}


@dataclass
class ComboResult:
    #: ok | staged | unverified | refused -- four OUTCOMES, not a bool. "staged" (typed, not
    #: sent) and "unverified" (sent, read-back blind) are real results that a bool would round
    #: to the wrong neighbour in both directions.
    status: str = "refused"
    nonce: str = ""
    steps: List[Step] = field(default_factory=list)
    new_session: Optional[str] = None
    detail: str = ""
    elapsed_ms: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status in ("ok", "staged")

    def to_dict(self) -> dict:
        return {"status": self.status, "nonce": self.nonce, "new_session": self.new_session,
                "detail": self.detail, "elapsed_ms": round(self.elapsed_ms, 1),
                "steps": [s.to_dict() for s in self.steps]}

    def render(self) -> str:
        out = ["[screen prompt] %s  (%.0f ms)" % (self.status.upper(), self.elapsed_ms)]
        for s in self.steps:
            mark = "ok  " if s.ok else "REFUSED"
            out.append("  %-7s %-16s %-22s %s"
                       % (mark, s.name, s.refusal or "", s.detail[:96]))
        # Only when something was actually staged. Printing a receipt nonce beside a refusal
        # reads as "this went out with id X" when nothing left the process.
        if self.nonce and self.status != "refused":
            out.append("  receipt nonce: %s" % self.nonce)
        if self.new_session:
            out.append("  NEW SESSION: %s" % self.new_session)
        if self.detail:
            out.append("  %s" % self.detail)
        return "\n".join(out)


# --------------------------------------------------------------------------- post-conditions


def _centre_strip(bounds: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """A small central region of the window, as (left, top, w, h).

    Used as the 'the view changed' observable after Ctrl+N. Small on purpose: hashing the whole
    8.4M-pixel window costs 88 ms and changes on any repaint anywhere; a 600x200 centre strip
    costs ~1 ms and changes when the CONVERSATION AREA changes, which is the question.
    """
    l, t, r, b = bounds
    cx, cy = (l + r) // 2, (t + b) // 2
    return (cx - 300, cy - 100, 600, 200)


def make_nonce(text: str) -> str:
    """A short, content-derived marker. Content-derived so the same brief yields the same
    receipt (re-checkable later), with the clock mixed in so two sends of one brief are still
    distinguishable."""
    h = hashlib.sha256(("%s|%.3f" % (text[:4096], time.time())).encode("utf-8")).hexdigest()
    return h[:10]


RECEIPT_TEMPLATE = "\n\n(akashic handoff receipt: {nonce})"


# --------------------------------------------------------------------------- the combo


def new_session_prompt(text: str, *, submit: bool = False, window_title: str = "Claude",
                       hwnd: Optional[int] = None, agent_id: Optional[str] = None,
                       timeout_s: float = 8.0, nonce: Optional[str] = None,
                       new_chat_keys: str = "{Ctrl}n") -> ComboResult:
    """Focus the desktop app, open a NEW session, stage ``text`` in it, and verify each step.

    Returns a :class:`ComboResult` whose ``status`` is one of:
      ``staged``     -- typed and read back, deliberately NOT sent (the default)
      ``ok``         -- sent, and a new session file containing the nonce appeared
      ``unverified`` -- sent, but the receipt never appeared; the text may or may not have gone
      ``refused``    -- a step declined; nothing further was attempted
    """
    t0 = time.time()
    res = ComboResult()
    res.nonce = nonce or make_nonce(text)
    body = text.rstrip() + RECEIPT_TEMPLATE.format(nonce=res.nonce)

    def step(name: str, ok: bool, detail: str = "", refusal: Optional[str] = None,
             ms: float = 0.0) -> Step:
        s = Step(name=name, ok=ok, detail=detail, refusal=refusal, elapsed_ms=ms)
        res.steps.append(s)
        return s

    def stop(status: str, detail: str) -> ComboResult:
        res.status = status
        res.detail = detail
        res.elapsed_ms = 1000 * (time.time() - t0)
        return res

    # ---- 0. preflight. Refuse BEFORE touching anything.
    locked = A.workstation_locked()
    step("preflight:lock", locked is False,
         "workstation_locked() -> %r" % (locked,),
         refusal=None if locked is False else "locked")
    if locked is not False:
        return stop("refused",
                    "the workstation is locked (or the probe is unavailable: %r). The window "
                    "stays readable while locked, so this is checked rather than inferred. %s"
                    % (locked, A.locked_detail()))

    # ---- 1. locate the window (no control name: the keyboard path needs the window itself)
    got = A.locate(window_title=window_title, hwnd=hwnd, ttl_s=max(30.0, timeout_s * 2))
    step("locate", got.ok, got.detail, got.refusal.value if got.refusal else None,
         got.elapsed_ms)
    if not got.ok:
        extra = (" candidates: %s" % (list(got.candidates),)) if got.candidates else ""
        return stop("refused", "%s%s" % (got.detail, extra))
    tgt = got.target

    # ---- 2. focus, and ASSERT it took. Windows refuses foreground changes from a process with
    #        no recent input, so this is a real failure mode and not a formality.
    r = A.act(tgt, "focus", timeout_s=timeout_s, agent_id=agent_id)
    step("focus", r.ok, r.detail, r.refusal.value if r.refusal else None, r.elapsed_ms)
    if not r.ok:
        return stop("refused", r.detail)

    # ---- 3. Ctrl+N, asserted by a REAL repaint of the conversation area.
    before = A._region_sha(_centre_strip(tgt.bounds))
    r = A.act(tgt, "keys", new_chat_keys,
              expect=(lambda: A._region_sha(_centre_strip(tgt.bounds)) != before) if before
                     else None,
              expect_what="the conversation area repainted after %s" % new_chat_keys,
              timeout_s=timeout_s, agent_id=agent_id)
    step("new-chat", r.ok, r.detail or ("view changed after %s" % new_chat_keys),
         r.refusal.value if r.refusal else None, r.elapsed_ms)
    if not r.ok:
        return stop("refused", r.detail)

    # ---- 4. stage the brief through the CLIPBOARD (never SendKeys: {}()!+^% are its syntax,
    #         so prose would not merely garble, it would execute).
    r = A.act(tgt, "type", body, timeout_s=timeout_s, agent_id=agent_id)
    step("stage-text", r.ok, r.detail, r.refusal.value if r.refusal else None, r.elapsed_ms)
    if not r.ok:
        return stop("refused", r.detail)

    # ---- 5. G3 read-back. Best-effort BY NATURE, and it says so.
    rb = A.act(tgt, "read_back", timeout_s=timeout_s, agent_id=agent_id)
    seen = (rb.observed or "")
    verified = res.nonce in seen
    step("read-back", verified,
         ("nonce found in %d chars of composer text" % len(seen)) if verified
         else ("could not confirm the nonce (%d chars read); the composer is a Chromium "
               "contenteditable with no EditControl, so this is best-effort" % len(seen)),
         refusal=None if verified else "unverified", ms=rb.elapsed_ms)

    if not submit:
        return stop("staged" if verified else "unverified",
                    "brief is staged in a NEW session and NOT sent (submit=False is the "
                    "default). Press Enter in the window, or re-run with submit=True."
                    + ("" if verified else " Read-back could not confirm it -- LOOK before "
                                           "sending."))

    # ---- 6. submit, and take the causal receipt off the FILESYSTEM.
    d = session_dir()
    pre = session_files(d)
    r = A.act(tgt, "keys", "{Enter}", timeout_s=timeout_s, agent_id=agent_id)
    step("submit", r.ok, r.detail, r.refusal.value if r.refusal else None, r.elapsed_ms)
    if not r.ok:
        return stop("refused", r.detail)

    def receipt() -> bool:
        for name in sorted(session_files(d) - pre):
            try:
                if res.nonce in (d / name).read_text(encoding="utf-8", errors="ignore"):
                    res.new_session = name
                    return True
            except Exception:  # noqa: BLE001
                continue
        return False

    got_receipt = A.settle(receipt, timeout_s=max(timeout_s, 20.0), interval_s=0.4,
                           what="a new session transcript containing nonce %s" % res.nonce)
    step("receipt", got_receipt.ok,
         ("new transcript %s contains the nonce" % res.new_session) if got_receipt.ok
         else ("no new transcript carried the nonce after %d polls / %.0f ms in %s"
               % (got_receipt.polls, got_receipt.elapsed_ms, d)),
         refusal=None if got_receipt.ok else "postcondition_failed",
         ms=got_receipt.elapsed_ms)
    if not got_receipt.ok:
        return stop("unverified",
                    "Enter was dispatched but no new session transcript carried the nonce. The "
                    "message may have gone to an EXISTING session, or the app may write its "
                    "transcript lazily -- check the window before re-sending, because re-running "
                    "would send it twice.")
    return stop("ok", "new session %s received the brief (nonce %s)"
                      % (res.new_session, res.nonce))


# --------------------------------------------------------------------------- status door


def status(window_title: str = "Claude", agent_id: Optional[str] = None) -> dict:
    """Everything the actuator would check, WITHOUT acting -- the preflight as a read.

    Exists because every refusal above should be answerable before a caller commits to a
    sequence, and because "why did it refuse" is the question an operator actually asks.
    """
    wins = A.windows_matching(window_title)
    locked = A.workstation_locked()
    fg = A._foreground_hwnd()
    caps = {}
    for verb in sorted(A.VERB_CAPS):
        allowed, why = A._capable(agent_id, verb)
        caps[verb] = {"allowed": allowed, "why": why}
    d = session_dir()
    out = {
        "seat": agent_id or A.ambient_agent_id(),
        "uia": A._uia() is not None,
        "workstation_locked": locked,
        "foreground_hwnd": fg,
        "windows": [{"hwnd": h, "title": t, "pid": A._pid_for(h), "dpi": A._dpi_for(h),
                     "iconic": A._is_iconic(h), "is_foreground": h == fg} for h, t in wins],
        "caps": caps,
        "session_dir": str(d) if d else None,
        "session_count": len(session_files(d)),
    }
    if len(wins) > 1:
        out["ambiguous"] = ("%d windows match %r -- pass --hwnd to disambiguate; picking the "
                            "first would be a coin flip over which live session gets the input."
                            % (len(wins), window_title))
    out["remedy"] = _remedy(agent_id)
    return out


def _remedy(agent_id: Optional[str]) -> Optional[str]:
    """ONE grant command covering every missing tier, or None when nothing is missing.

    Synthesised here rather than left to the per-verb refusal, because six refusals each naming
    one cap invite six sequential grants -- and since `grant --caps` REPLACES the set, running
    them one at a time would leave the seat holding only the last one. The whole point of a
    remedy is that following it literally works.

    Withholds screen.launch and screen.privileged: no verb maps to them (see act.VERB_CAPS), and
    the design reserves privileged for authenticated daniil. A remedy should grant what is
    needed and not a tier more.
    """
    try:
        from core.trust import registry
        from core.trust.capabilities import Cap
        seat = agent_id or A.ambient_agent_id()
        grant = registry.resolve(seat)
        if grant is None:
            return None
        need = {Cap(v) for v in set(A.VERB_CAPS.values())}
        missing = sorted(c.value for c in need - set(grant.caps))
        if not missing:
            return None
        full = sorted({c.value for c in grant.caps} | set(missing))
        return ("A SECOND PARTY must grant %s (self-grant raises PermissionError). One command, "
                "restating existing caps because --caps REPLACES them:\n"
                "  py agent_cli.py grant %s --role %s --by daniil --hours 12 \\\n"
                "    --caps %s \\\n"
                "    --reason 'screenspace actuator drill: Ctrl+N + handoff combo'"
                % (", ".join(missing), seat, grant.role, ",".join(full)))
    except Exception:  # noqa: BLE001
        return None
