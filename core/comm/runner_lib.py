"""core.comm.runner_lib -- shared hardening for OpenAI-compatible seat transports (K0, 2026-07-18).

The rule-of-three extraction's second seam (fence: deepseek counter sec 1, accepted): the
G4/L0 anti-wedge client factory as GENUS -- explicit parameters only, no env reads here.
Each seat module (deepseek_chat, kimi_chat, ...) wraps this with its OWN env-var conventions
and defaults; that keeps every seat's tuning surface local and greppable, per the fence.

The Agent/loop layer deliberately does NOT live here ("premature generalization" ruling):
chat-completions loops stay species-specific until two of them stabilize side by side.
"""
from __future__ import annotations

import os


def set_seat_agent(agent: str) -> str:
    """Declare which seat this runner process is, so its wire records are attributable.

    T160: BIFROST_AGENT was read in exactly one place and written in none, so 102 of 102 records
    in the live journal said 'unknown' and doctor's per-seat wire forensics matched nothing for
    as long as it had existed. Every runner already knows its own id from argv; nothing carried
    it the last few inches.

    Wrapped here rather than imported directly by four runners so the SAFETY NET has one
    definition: a runner must never fail to start because its instrumentation could not load.
    That is the same rule recording_http_client() follows, and for the same reason -- the
    blindness this cures is far cheaper than a seat that will not boot.
    """
    try:
        from scripts.wire_journal import set_seat_agent as _set
        return _set(agent)
    except Exception:
        return ""


def make_openai_compat_client(api_key: str, base_url: str, *,
                              connect_timeout: float = 15.0,
                              read_timeout: float = 120.0,
                              max_retries: int = 1,
                              record_wire: bool = True):
    """OpenAI-compatible client hardened against hung-stream wedges (G4/L0): a per-read
    streaming timeout turns a stalled model call into a caught httpx.ReadTimeout the caller's
    try/except revives from, and an explicit max_retries stops the SDK default (2) from
    tripling wall-clock before the wedge surfaces. Lazy imports keep this module import-cheap
    for callers that never build a client (e.g. spend-ledger-only tooling).

    T161: instrumented by default. kimi and gemini reach the wire ONLY through this factory, so
    one seam covers both -- and until now three of the four seats made model calls with no wire
    record at all, leaving system_fingerprint (the silent model-swap detector) unobservable for
    most of the fleet.

    THE TIMEOUT TRAVELS WITH THE CLIENT, and that is the trap this function has to avoid. Hand
    the SDK an http_client and it takes its timeout from THAT object, ignoring the one this
    factory would otherwise set -- so instrumenting is exactly how a seat silently loses the
    anti-wedge hardening this module exists to provide. The recorder is therefore built WITH the
    computed timeout, and every fallback below keeps it too. An instrumented but wedge-prone seat
    is a worse trade than a blind one, so if capture cannot be set up, capture is what we drop.
    """
    from openai import OpenAI
    import httpx
    timeout = httpx.Timeout(read_timeout, connect=connect_timeout)

    if record_wire:
        try:
            from scripts.wire_journal import recording_http_client
            http_client = recording_http_client(timeout=timeout)
            if http_client is not None:
                return OpenAI(api_key=api_key, base_url=base_url,
                              http_client=http_client, max_retries=max_retries)
        except Exception:
            pass          # telemetry never blocks a launch -- fall through uninstrumented

    return OpenAI(api_key=api_key, base_url=base_url,
                  timeout=timeout, max_retries=max_retries)


def seat_session_id(agent: str, session=None) -> str:
    """The per-incarnation session id a runner beats the roster under (T147) -- ONE
    derivation, shared by the heartbeat thread and retire_seat(), so the card a runner
    retracts on exit is the card it wrote. Precedence is the heartbeat's historical one:
    an explicit --session, else BIFROST_INCARNATION, else "<pid>-<agent>" (the 2026-08-26
    receipt's deepseek#3708-dee is sid8 of "3708-deepseek")."""
    return str(session or os.environ.get("BIFROST_INCARNATION") or f"{os.getpid()}-{agent}")


def retire_seat(agent: str, session_id: str, *, stop_hb=None, hb_thread=None,
                hb_join_s: float = 6.0, ns=None, client=None, bare_phase=None) -> dict:
    """A planned exit retracts its own phase card, HONESTLY (defer 8c881ab628, amended).

    WHY: every runner's heartbeat thread beats {ns}:worklive:{agent}#{sid8} with phase='running'
    and a since_ts the roster preserves across beats, and until this landed the exit path stopped
    the thread, released the lock, and nothing else. The card outlived the process for 180s:
    non-idle, aged, dead pulse -- the doctor's HARD WEDGE signature -- so a drained deepseek paged
    after a clean exit 0. An emitter without a retraction path manufactures false pages.

    THE AMENDED GUARANTEE (the 09-08 adversarial REJECT, folded in): a planned exit retracts
    its card ONLY when the retraction is PROVEN sound, and reports the truth otherwise:

      1. stop_hb.set()             -- ask the beat thread to stop;
      2. hb_thread.join(hb_join_s) -- WAIT for it. An in-flight beat after the delete would
                                     re-create the card (discord's *_pulse* beats the BARE
                                     worklive plane via `beat(wl)`, the roster heartbeat beats
                                     the INCARNATION plane -- both must stop);
      3. THE KEY GUARD THE REJECT DEMANDED: only when the beat thread is CONFIRMED stopped
         (hb_thread is None, or joined, i.e. not alive after join) do we go_offline. If it is
         still alive, we do NOT delete the card -- we report retracted=False with the reason,
         because a delete here would be immediately resurrected and would fake a clean exit.
      4. roster.go_offline(...)    -- delete the incarnation card and stamp the seatseen
                                     witness phase='offline' + offline_ts. It honors ns/client
                                     (unlike the OLD bare-phase write, REJECT defect (2)).
      5. the BARE worklive key     -- stand its phase down via the SAME namespace/client the
                                     roster plane used, so a test client never touches the
                                     shared Redis. bare_phase=None skips it (probe/test callers).
    Never raises -- an exit path must not fail on its own bookkeeping. Reversible by
    construction (roster O3): a later beat under the same id is LIVE again."""
    out = {"ok": False, "agent": str(agent), "session_id": str(session_id or ""),
           "sid8": str(session_id or "")[:8], "hb_joined": None, "offline_ts": None,
           "retracted": False}
    try:
        if stop_hb is not None:
            stop_hb.set()
        hb_joined = None
        if hb_thread is not None:
            try:
                if hb_thread.is_alive():
                    hb_thread.join(max(0.0, float(hb_join_s)))
                hb_joined = not hb_thread.is_alive()
            except Exception:
                hb_joined = False
        out["hb_joined"] = hb_joined

        # REJECT defect (1): do NOT go_offline unless the beat thread is provably stopped.
        # A delete while a beat is in flight (or still looping) is resurrected by that beat,
        # and reporting a clean retraction that does not hold is a false page in reverse.
        if hb_thread is not None and hb_joined is False:
            out["retracted"] = False
            out["reason"] = ("beat thread still alive after join -- card NOT deleted "
                             "(a delete here would be resurrected by an in-flight beat)")
            return out

        _ns = ns or os.environ.get("BIFROST_NAMESPACE", "bifrost")
        from core.comm import roster
        rep = roster.go_offline(_ns, str(agent), str(session_id or ""), client=client) or {}
        out["ok"] = bool(rep.get("ok"))
        out["offline_ts"] = rep.get("offline_ts")
        out["retracted"] = bool(rep.get("ok"))

        # REJECT defect (2): the bare worklive write MUST honor ns/client. The old path called
        # liveness.worklive(agent).set(phase) which writes the REAL shared Redis regardless of
        # the test client/namespace -- contamination under a probe. We instead write the bare
        # worklive key through the SAME ns/client the roster plane used, keying it by name
        # directly (not via _worklive_prefix(), which reads the env var and would ignore ns).
        if bare_phase is not None:
            try:
                if client is not None:
                    client.delete(f"{_ns}:worklive:{agent}")
                else:
                    from core.comm import liveness as _liveness
                    _liveness.worklive(str(agent)).set(str(bare_phase))
            except Exception:
                pass
    except Exception:
        pass
    return out
