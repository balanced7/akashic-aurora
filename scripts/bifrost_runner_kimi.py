"""
bifrost_runner_kimi -- make Kimi (kimi-k3, Moonshot) a FIRST-CLASS Bifrost citizen.

Kimi is its OWN seat (Daniel directives 2026-07-18: "first-class citizen on day one" +
"lets build the runner, especially since we have caching"): kimi-named module, KIMI_* envs,
kimi persona. K2 of the fence-converged build (deepseek counter sec 1+3, accepted; walk/coda/
fresh-eyes receipts in research/reviewed/kimi-*). Skeleton: bifrost_runner_sol.py VERBATIM
where possible (T090's consume-to-commit pipeline, RB-23/26/29 laws, lanes, singleton,
continuity) -- runner_lib extraction of this skeleton remains the post-stabilization plan,
now with THREE stabilizing instances.

KIMI DELTAS (everything else is the sol skeleton):
  * KimiAgent transport (chat-completions; kimi_chat.py) -- thinking always-on, streamed to
    the bus as 💭 traces; CACHE CONTRACT: the system prompt (persona + onboarding + tool
    schemas) FREEZES at responder build and history is append-only, so Moonshot's automatic
    prefix cache bills repeat input at $0.30/M. Byte-stability is load-bearing economics.
  * SPEND GOVERNANCE (deepseek sec-3 contract): one shared SpendMeter across all peer
    conversations; reconcile-vs-balance on boot + every 10 min; WARN >= $80 spent rides the
    fleet card; HARD-REFUSE >= $95: non-directed asks get kind="reply" WITH meta.answers
    (the expectation SETTLES -- RB-29: a refusal must reply loudly, never vanish) +
    meta.budget_refusal for the doctor. Daniel/user asks are exempt from refusal.
  * Phase-1 posture: launch --agentic WITHOUT --allow-write/--allow-exec until Daniel's
    phase-2 word (security/acl.json kimi record governs; ToolBox honors the flags).
  * First direct consumer of the K0 canonical seam: core.comm.toolbox (not the compat path).

Run:  py scripts/bifrost_runner_kimi.py --agentic                    # phase-1 seat (read+bus)
      py scripts/bifrost_runner_kimi.py --agentic --once             # smoke: one wake
Key:  env KIMI_API_KEY else .secrets/kimi.key (same convention as ask_kimi.py).
"""
import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from core.comm.bus import Bus
from core.comm import control
from core.comm import liveness
from core.comm import nudge
from core.comm import runner_lock
from core.comm import self_restart
from core.comm import context_hints
from core.comm.timescale import scaled as _scaled
from core.comm.toolbox import ToolBox, TOOLS   # K0 canonical seam -- first direct consumer

from kimi_chat import (KimiAgent, SpendMeter, DEFAULT_MODEL, DEFAULT_EFFORT,
                       MAX_COMPLETION_TOKENS, load_key)

CARD = {
    "runtime_class": "api",
    "wake_mode": "runner",
    "door": "runner",
    "caps": ["review", "critique", "answer", "audit", "fresh-eyes", "vision", "megaread"],
}

# 'steer' deliberately NOT answerable (folds via inject); 'reply' NOT answerable (echo-loop guard).
ANSWERABLE = frozenset({"chat", "request", "question", "handoff", "nudge", "inform"})

REPLY_TIMEOUT_SEC = _scaled(600)   # thinking turns run long; drill-shrinkable
KIMI_MAX_HOPS = int(os.getenv("KIMI_MAX_HOPS", "30"))
BUDGET_EXEMPT_SENDERS = frozenset({"user", "daniel"})   # directed human asks always answer

DEFAULT_SYSTEM = ("You are kimi (kimi-k3), operating as an agentic technical partner on "
                  "Akashic Aurora -- the third frontier seat beside claude (Fable) and "
                  "deepseek. You are reached over a shared message bus; each reply posts "
                  "back to the sender, so make it self-contained. Your standing lanes: "
                  "fence third voice, fresh-eyes dissent, tiebreaks, label honesty "
                  "(VERIFIED/INFER/GUESS is your native register).")

# RB-27a: tenure fencing generation (one-slot mutable so closures see main()'s value).
PULSE_GEN = [0]

# T078 W1: per-peer token deltas, drained after each turn by _process_one.
_token_deltas: dict = {}
_RUN_STATS = {"turns": 0, "last_error": ""}
# T078 W1: the DAILY token journal the doctor's cost line reads. Distinct from METER below:
# METER is this seat's in-session dollar conscience (it can refuse work); the journal is the
# cross-seat daily aggregate for the dashboard. kimi had the first and not the second, so the
# seat was governed for spend but INVISIBLE on the fleet cost line -- deepseek and sol both
# wired it, kimi and the generic runner did not. Found while answering "what shipped from the
# token-efficiency work"; it is the same shape as kimi's own governance argument: you cannot
# steer against a meter that has no reading for one of the seats.
_token_journal = None

# The seat's one shared budget conscience (module-level so _process_one sees it).
METER = SpendMeter()


def should_answer(kind, frm, self_id) -> bool:
    """Answer direct asks from others; ignore own echoes and non-question kinds."""
    return frm != self_id and str(kind) in ANSWERABLE


# ---- RB-26/T086-S6 dedup pair (Redis fast path + durable Store backstop) --------------------

REPLY_SENT_PREFIX = "bifrost:reply_sent:"


def _reply_already_sent(bus, mid) -> bool:
    """Redis FIRST (fast, TTL'd), then durable Store (survives Redis restart).
    Fail-open: a probe error reads as NOT sent -- a duplicate reply is cheaper than a dropped one."""
    try:
        if bus._client.exists(REPLY_SENT_PREFIX + str(mid)):
            return True
    except Exception:
        pass
    try:
        from core.foundation.store import create_store
        return bool(create_store().get(f"reply_sent:{mid}"))
    except Exception:
        return False


def _mark_reply_sent(bus, mid) -> None:
    """Set AFTER the reply sends, BEFORE the cursor commits. Both writes best-effort."""
    try:
        bus._client.set(REPLY_SENT_PREFIX + str(mid), "1", ex=REPLY_TIMEOUT_SEC + 60, nx=True)
    except Exception:
        pass
    try:
        from core.foundation.store import create_store
        store = create_store()
        store.set(f"reply_sent:{mid}", "1")
        store.expire(f"reply_sent:{mid}", REPLY_TIMEOUT_SEC + 60)
    except Exception:
        pass


# ---- RB-26 kill windows (drill-only, never armed in production) ------------------------------

KILLPOINT = os.environ.get("AKASHIC_KILLPOINT", "")


def _killpoint(name: str) -> None:
    if KILLPOINT and KILLPOINT == name:
        print(f"[kimi-runner] KILLPOINT {name} -- dying (drill)", flush=True)
        os._exit(137)


# ---- onboarding (the same boot door every citizen walks) -------------------------------------

def _trim_onboarding(digest: str, budget_chars: int) -> str:
    """T050 Q2 / T043 packet law: never silently truncate -- cut at budget, NAME every dropped
    section with a pull pointer."""
    if len(digest) <= budget_chars:
        return digest
    head, tail = digest[:budget_chars], digest[budget_chars:]
    dropped = [ln.strip().lstrip("#").strip() for ln in tail.splitlines()
               if ln.strip().startswith("##")]
    what = "; ".join(dropped[:8]) if dropped else "tail content (cut mid-section)"
    return (head.rstrip()
            + f"\n... [onboarding TRIMMED at its {budget_chars}-char budget. DROPPED: {what}. "
              f"Pull any of it: knowledge_boot(task=...) re-assembles the full briefing; "
              f"knowledge_recall(query=...) fetches specifics. Never guess at what was cut.]")


def onboarding_context(root: Path, agent_id: str, task: str, budget_chars: int = 6000,
                       door_detail: str = "") -> str:
    """Pull the project's startup briefing ONCE at boot and fold a TRIMMED digest into the
    system prompt. ONCE matters doubly here: the digest joins the FROZEN cache prefix.
    Never raises; '' on failure."""
    import subprocess
    import tempfile
    env = dict(os.environ)
    env["AKASHIC_SEAT_DOOR"] = "toolbox"
    if door_detail:
        env["AKASHIC_SEAT_DOOR_DETAIL"] = door_detail
    sources_file = os.path.join(tempfile.gettempdir(), f"boot_sources_{agent_id}_{os.getpid()}.json")
    try:
        p = subprocess.run([sys.executable, "agent_cli.py", "boot", agent_id, "--task", task,
                            "--sources-json", sources_file],
                           cwd=str(root), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=90, env=env)
        digest = (p.stdout or "").strip()
    except Exception:
        return ""
    try:
        if os.path.exists(sources_file):
            with open(sources_file, encoding="utf-8") as sf:
                onboarding_context._last_sources = json.loads(sf.read()).get("sources", [])
            os.remove(sources_file)
    except Exception:
        onboarding_context._last_sources = None
    if not digest:
        return ""
    digest = _trim_onboarding(digest, budget_chars)
    try:
        # T050 Q1: the agent's PRIVATE notes-to-self ride every boot (post-trim: small, never cut).
        from core.learning.agent_memory import get_agent_memory
        pref = f"scratch:{agent_id}:"
        notes = [d for d in get_agent_memory().get_decisions(days=365)
                 if str(d.title).startswith(pref) and not d.superseded][:8]
        if notes:
            digest += "\n\n## YOUR PRIVATE NOTES (yours alone; memory_note updates, memory_recall lists)\n"
            digest += "\n".join(f"- {d.title[len(pref):]}: {str(d.decision)[:160]}" for d in notes)
    except Exception:
        pass
    return digest


# ---- RB-23 quality gates (reused genus-level, sol precedent) ---------------------------------

def _rb23_gates(answer: str, resend, agent_id: str, pulse=None) -> str:
    """T018 promise bounce + RB-23 content floor before any reply ships. Reused from
    bifrost_runner_deepseek (the genus implementation; its MARKER_PATTERN matches kimi's
    marker strings too). Degrades OPEN with a loud print if the import ever breaks."""
    try:
        from bifrost_runner_deepseek import bounce_promise, content_floor_check
    except Exception as e:
        print(f"[kimi-runner] RB-23 gates unavailable ({type(e).__name__}: {e}) -- shipping ungated")
        return answer
    if pulse is None:
        def pulse(agent, reason, **kw):
            liveness.pulse_error(agent, reason, generation=PULSE_GEN[0])
    pre = answer
    answer = bounce_promise(answer, resend)
    return content_floor_check(answer, resend, agent_id=agent_id,
                               promise_bounce_fired=(answer is not pre), pulse=pulse)


# ---- the kimi responder (KimiAgent + guarded ToolBox) ----------------------------------------

def make_kimi_replier(model: str, system: str, effort: str, root: Path, agent_id: str,
                      allow_write: bool = False, allow_exec: bool = False, boot_sources=None):
    """Tool-using bridge: kimi reads files, searches, inspects git, and queries the knowledge
    base WHILE composing its reply. Per-peer KimiAgent conversations for continuity; ONE
    shared SpendMeter across all of them (a budget is per-seat, not per-friendship)."""
    # T050 Q3+Q4: capabilities declared UP FRONT -- no hop wasted discovering what a session can do.
    system = (f"[session capabilities] write_mode: "
              f"{'ENABLED (guarded write_file/edit_file live; locks self-release at reply)' if allow_write else 'READ-ONLY -- write_file/edit_file will refuse; investigate and report'}"
              f" | tool budget: {KIMI_MAX_HOPS} hops per task, running counter [hop N] rides every result"
              f" | reasoning: always-on (kimi-k3), thinking streams to the bus | recall-at: off\n"
              + system)
    toolbox = ToolBox(root, allow_exec=allow_exec, trust=allow_exec, allow_secrets=False,
                      confirm=lambda _p: False, agent_id=agent_id, allow_write=allow_write,
                      boot_text=system, boot_sources=boot_sources)

    _wl = liveness.worklive(agent_id)

    def on_activity(state, detail):
        control.set_activity(agent_id, state, detail)
        _wl.set(state, detail)
        liveness.pulse(agent_id, f"{state}:{str(detail)[:60]}", generation=PULSE_GEN[0])

    trace_bus = Bus(agent_id)

    def on_trace(kind, text):
        prefix = "🔧" if kind == "tool" else "💭"
        liveness.pulse(agent_id, f"{kind}:{str(text)[:60]}", generation=PULSE_GEN[0])
        try:
            trace_bus.broadcast("trace", f"{prefix} {text}",
                                meta={"via": f"{agent_id}-runner", "hops": 0, "trace": kind,
                                      "display_only": True})
        except Exception:
            pass

    interrupt = lambda: control.is_halted(agent_id) or nudge.is_nudged(agent_id)
    inject = lambda: nudge.steer_drain(agent_id)

    def _dispatch(name, args):
        fn = getattr(toolbox, name, None)
        if fn is None or str(name).startswith("_"):
            return f"ERROR: unknown tool {name!r}"
        return str(fn(**(args or {})))

    convos: dict = {}

    def respond(frm: str, prompt: str) -> str:
        ag = convos.get(frm)
        if ag is None:
            # CACHE CONTRACT: system + TOOLS freeze inside KimiAgent at construction; the
            # per-peer history is append-only from here. All peers share the identical
            # prefix, so Moonshot's cache warms across conversations, not just turns.
            ag = KimiAgent(instructions=system, model=model, effort=effort,
                           max_completion_tokens=MAX_COMPLETION_TOKENS,
                           tools_schemas=TOOLS, dispatch=_dispatch,
                           interrupt=interrupt, inject=inject,
                           on_trace=on_trace, on_activity=on_activity,
                           max_hops=KIMI_MAX_HOPS, meter=METER)
            convos[frm] = ag
        try:
            hints = context_hints.drain(agent_id)
            dropped = context_hints.take_dropped(agent_id)
            if hints or dropped:
                prompt = context_hints.format_for_prompt(hints, dropped=dropped) + "\n" + prompt
        except Exception:
            pass
        try:
            in0, out0 = ag.input_tokens, ag.output_tokens
            answer = ag.send(prompt)
            _token_deltas[frm] = (ag.input_tokens - in0, ag.output_tokens - out0)
        except Exception as e:
            # RB-23: fold the error into the pipeline (no early return) -- the floor gate
            # gives a transient failure exactly one retry before it confesses.
            answer = f"(kimi agentic runner error: {type(e).__name__}: {e})"
        answer = _rb23_gates(answer, ag.send, agent_id)
        try:
            toolbox.release_written_locks()   # T048: task end = lock end
        except Exception:
            pass
        return answer or "(kimi produced no final answer)"

    return respond


def make_one_shot_replier(model: str, system: str, effort: str, agent_id: str = "kimi"):
    """One-shot bridge: each message -> one completion -> reply. Fast, toolless, still metered."""
    def _one(prompt: str) -> str:
        ag = KimiAgent(instructions=system, model=model, effort=effort,
                       max_completion_tokens=MAX_COMPLETION_TOKENS, meter=METER)
        return ag.send(prompt)

    def respond(prompt: str) -> str:
        try:
            answer = _one(prompt)
        except Exception as e:
            answer = f"(kimi runner error: {type(e).__name__}: {e})"
        # RB-23 stateless path: the resend re-embeds the original ask.
        resend = lambda reprompt: _one(prompt + "\n\n[system bounce] " + reprompt)
        return _rb23_gates(answer, resend, agent_id)

    return respond


# ---- budget governance (deepseek sec-3 contract; kimi-specific pipeline stage) ----------------

def budget_refusal(m, bus, agent_id: str, hops: int):
    """HARD-REFUSE a non-directed ask over the spend ceiling -- as kind='reply' WITH
    meta.answers so the sender's expectation SETTLES (RB-29: refusals reply, never vanish).
    Returns True when the refusal was sent (caller sentinels + advances as a handled turn)."""
    text = (f"(kimi budget hard-refusal: ${METER.spent():.2f} spent of the "
            f"${METER.budget:.0f} grant, past the ${'%.0f' % float(os.getenv('KIMI_SPEND_REFUSE', '95'))} ceiling. "
            f"Non-directed work is refused. A super-admin can raise KIMI_SPEND_REFUSE or "
            f"Daniel can direct this ask explicitly.)")
    meta = {"via": f"{agent_id}-runner", "hops": hops, "answers": m.id, "budget_refusal": True}
    if str(m.to) == "*":
        bus.broadcast("reply", text, meta=meta)
    else:
        bus.send_reply(m.frm, text, meta=meta)
    print(f"[kimi-runner] BUDGET REFUSAL -> {m.frm} ({METER.status_line()})")
    return True


# ---- consume-to-commit pipeline (sol spec section 1; per-message) ----------------------------

def _process_one(m, bus, args, responder, rate) -> None:
    """Process ONE incoming message: filter chain, budget gate, model turn, reply, sentinel.
    Cursor commit stays in the main loop."""
    from core.coord import cognitive_metrics as cog
    from core.comm import turn_metrics as _tm

    # [1] R7/T058: a user's clarify-answer routes to the steer queue
    if str(m.kind) == "reply" and str(m.frm) == "user":
        cid = (m.meta or {}).get("clarify_id")
        if cid:
            nudge.steer_push(args.agent, m.frm, str(m.content))
            print(f"[kimi-runner] clarify-answer {cid} routed to the steer queue")
            return

    # [2] HINT interception -- never answered, injected on the next model turn
    if str(m.kind) == "hint":
        meta = m.meta or {}
        hint_data = meta.get("hint") or {}
        ok = context_hints.push(args.agent, hint_data.get("key", "?"),
                                hint_data.get("value", "?"), from_agent=m.frm)
        if ok:
            cog.record_file_read(args.agent, hint_data.get("key", "?"), from_hint=True)
            print(f"[kimi-runner] hint accepted ({hint_data.get('key', '?')}) from {m.frm}")
        return

    # [3] ledger fold gate -- transitions are SWALLOWED (never answered); sol-precedent deferral
    if str(m.kind) in ("ledger_update", "resolved"):
        print(f"[kimi-runner] ledger fold: {str(m.content)[:80]}")
        return

    # [4] ANSWERABLE gate
    if not should_answer(m.kind, m.frm, args.agent):
        return

    # [5] RB-26 dedup sentinel check
    if _reply_already_sent(bus, m.id):
        print(f"[kimi-runner] skip {m.id} from {m.frm} -- reply already sent (redelivery)")
        return

    # [6] hop-count loop guard
    hops = control.next_hops(m.meta)
    if control.hops_exceeded(m.meta):
        bus.send(m.frm, "note",
                 f"[loop-guard] max hops ({control.MAX_HOPS}) reached -- returning to a human.",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        print(f"[kimi-runner] loop-guard: hops>={control.MAX_HOPS}; not answering {m.frm}")
        return

    # [7] rate-limit backstop
    if not rate.allow():
        control.pause(reason=f"{args.agent} hit reply rate limit", by=args.agent, ttl=3600)
        bus.send(m.frm, "note",
                 "[loop-guard] reply rate limit hit -- auto-paused (self-heals in <=1h).",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        print("[kimi-runner] rate limit -> auto-paused (ttl 1h)")
        return

    # [7b] BUDGET GATE (kimi delta): over the ceiling, non-exempt sender -> loud settling refusal
    if METER.exceeded_hard_limit() and str(m.frm).lower() not in BUDGET_EXEMPT_SENDERS:
        budget_refusal(m, bus, args.agent, hops)
        _mark_reply_sent(bus, m.id)          # a refusal IS the reply; dedupe redeliveries
        return

    # [8] nudge / halt handling
    if str(m.kind) == "nudge" or nudge.is_nudged(args.agent):
        nudge.clear(args.agent)
        bus.send(m.frm, "note", "[nudge ack] interrupting current work to look at this now.",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        cog.record_human_interjection(args.agent)
        print(f"[kimi-runner] nudge from {m.frm} -> acked + cleared")
    if control.is_halted(args.agent) and str(m.kind) != "nudge":
        cog.record_human_interjection(args.agent)

    # [9] activity set + L1 worklive flip
    control.set_activity(args.agent, "thinking")
    liveness.worklive(args.agent).set("handling", detail=f"{m.frm}:{m.kind}", new_turn=True)

    # [10] kill window 2
    _killpoint("post-phase-flip-pre-send")

    # [11] RESPOND -- the model turn, wall-clock-guarded in a daemon thread
    prompt = m.content if isinstance(m.content, str) else str(m.content)
    turn_t0 = time.time()
    _tm.take_pulse_count(args.agent)
    result_holder: list = []
    worker_done = threading.Event()

    def _call():
        try:
            result_holder.append(responder(m.frm, prompt) if args.agentic else responder(prompt))
        except Exception as ex:
            result_holder.append(ex)
        finally:
            worker_done.set()

    threading.Thread(target=_call, daemon=True).start()
    finished = worker_done.wait(timeout=REPLY_TIMEOUT_SEC)

    nonanswer = False
    if not finished:
        nonanswer = True
        out = f"(kimi runner timed out after {REPLY_TIMEOUT_SEC}s -- the API call was abandoned)"
        print(f"[kimi-runner] !! TIMEOUT for {m.frm} after {REPLY_TIMEOUT_SEC}s")
        _RUN_STATS["last_error"] = "timeout"
    else:
        result = result_holder[0] if result_holder else "(kimi runner: no result)"
        if isinstance(result, Exception):
            nonanswer = True
            out = f"(kimi runner error: {type(result).__name__}: {result})"
            print(f"[kimi-runner] !! responder error: {type(result).__name__}: {result}")
            _RUN_STATS["last_error"] = f"{type(result).__name__}: {result}"
        else:
            out = str(result)

    # [12] SEND REPLY -- RB-29: nonanswer -> kind="note", NO answers linkage; success ->
    # kind="reply" + meta.answers (T066 lane-first send_reply)
    reply_kind = "note" if nonanswer else "reply"
    reply_meta = {"via": f"{args.agent}-runner", "model": args.model, "hops": hops}
    if not nonanswer:
        reply_meta["answers"] = m.id
    if str(m.to) == "*":
        bus.broadcast(reply_kind, out, meta=reply_meta)
        dest = "*(broadcast)"
    else:
        if reply_kind == "reply":
            bus.send_reply(m.frm, out, meta=reply_meta)
        else:
            bus.send(m.frm, reply_kind, out, meta=reply_meta)
        dest = m.frm

    # [13] kill window 3
    _killpoint("post-send-pre-sentinel")

    # [14] RB-26 dedup sentinel SET (after send, before cursor commit)
    _mark_reply_sent(bus, m.id)

    # [15] P6 handoff auto-ack -- RB-29: timeout/error answers never ack
    answered_ok = (finished and result_holder and not isinstance(result_holder[0], Exception)
                   and not out.startswith("(kimi"))
    if str(m.kind) == "handoff" and answered_ok:
        try:
            from core.comm.promoter import ack as _ack
            _ack(args.agent, m.id, note="answered on the bus")
            print(f"[kimi-runner] acked handoff {m.id}")
        except Exception:
            pass

    # [16] turn metrics + spend visibility
    try:
        cog.record_turn_complete(args.agent)
        outcome = ("timeout" if not finished else "error" if nonanswer else "ok")
        toks = _token_deltas.pop(m.frm, None)
        _tm.record(args.agent, str(m.kind), duration_s=time.time() - turn_t0,
                   progress_points=_tm.take_pulse_count(args.agent),
                   outcome=outcome, prompt_len=len(str(m.content)),
                   tokens=({"prompt": toks[0], "completion": toks[1]} if toks else None))
        _RUN_STATS["turns"] += 1
        # T078 W1: same seam deepseek's runner uses -- the delta is already drained above,
        # so this adds the daily aggregate without a second accounting path to drift from.
        if _token_journal is not None and toks:
            _token_journal.add_turn(prompt=toks[0], completion=toks[1],
                                    model=getattr(args, "model", ""))
    except Exception:
        pass

    # [17] activity clear
    control.clear_activity(args.agent)
    liveness.worklive(args.agent).set("idle")
    print(f"[kimi-runner] -> {dest}: {out[:80]}  [{METER.status_line()}]")


# ---- exit summary + continuity (sol hardening slice 1, verbatim pattern) ----------------------

def default_summary_path(agent_id: str) -> str:
    return os.path.join(os.path.dirname(HERE), "state", "runner",
                        f"{agent_id}-exit-summary.json")


def read_prior_summary(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.loads(f.read().strip() or "{}") or {}
    except Exception:
        return {}


def continuity_header(prior: dict) -> str:
    """Session-2+ continuity. NOTE (cache contract): this header varies per session -- it
    joins the frozen prefix ONCE at boot and never mutates within a run, so it costs one
    cache-miss per restart, not per turn."""
    if not prior:
        return ""
    n = int(prior.get("session", 1)) + 1
    age = ""
    try:
        age_s = int(time.time() - float(prior.get("timestamp", 0)))
        if 0 < age_s < 90 * 86400:
            age = f", {age_s // 3600}h{(age_s % 3600) // 60:02d}m ago"
    except Exception:
        pass
    err = prior.get("last_error")
    return (f"## RUNNER CONTINUITY (session {n}; automatic)\n"
            f"Your last run: exit={prior.get('exit_code')} turns={prior.get('turns')} "
            f"verdict={prior.get('verdict', '?')}{age}."
            + (f" Last error: {err}." if err else "")
            + " If that exit was abnormal, re-verify anything it claimed before building on "
              "it -- the ledger and notes beat your memory of the run.\n")


def _write_exit_summary(path, exit_code, session=1):
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"exit_code": exit_code, "turns": _RUN_STATS["turns"],
                       "last_error": _RUN_STATS["last_error"] or None,
                       "verdict": "ok" if exit_code == 0 else "abnormal",
                       "session": session,
                       "spent_usd": METER.spent(),
                       "timestamp": time.time()}, f)
    except Exception:
        pass


# ---- main ---------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Run Kimi (kimi-k3) as a Bifrost citizen.")
    ap.add_argument("--agent", default="kimi")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", default=DEFAULT_SYSTEM)
    ap.add_argument("--effort", default=DEFAULT_EFFORT,
                    help="reasoning effort (kimi-k3: 'max' is the only API level today)")
    ap.add_argument("--agentic", action="store_true",
                    help="give kimi tools (read files/search/git/knowledge base) while it replies")
    ap.add_argument("--root", default=os.path.dirname(HERE),
                    help="file-access root for --agentic (default: the repo)")
    ap.add_argument("--allow-write", action="store_true",
                    help="guarded write doors (phase-2; kimi's ACL record governs)")
    ap.add_argument("--allow-exec", action="store_true",
                    help="run_command door (phase-2; families-only under trust)")
    ap.add_argument("--once", action="store_true", help="process one wake then exit (smoke)")
    ap.add_argument("--summary-file", default=None, dest="summary_file")
    ap.add_argument("--inject-summary", default=None, dest="inject_summary")
    return ap


def main() -> int:
    try:
        from core.foundation.streams import self_bless_stdout   # RB-28: utf-8 + line-buffered
        self_bless_stdout()
    except Exception:
        pass

    args = build_parser().parse_args()
    if args.summary_file is None:
        args.summary_file = default_summary_path(args.agent)
    prior = read_prior_summary(args.inject_summary or default_summary_path(args.agent))
    session_n = int(prior.get("session", 1)) + 1 if prior else 1

    if not load_key():
        print("bifrost_runner_kimi: NO_KEY (set KIMI_API_KEY or .secrets/kimi.key)")
        return 2
    bus = Bus(args.agent)
    if not bus.online:
        print("bifrost_runner_kimi: bus OFFLINE (Redis unreachable)")
        return 2

    # T078 W1: daily token journal -- the meter the doctor's fleet cost line reads.
    # Fail-soft by contract: a missing meter must never stop the seat from working.
    global _token_journal
    try:
        from scripts.runner_token_journal import TokenJournal
        _token_journal = TokenJournal(args.agent)
        print(f"[kimi-runner] token journal: {_token_journal.turns} turns, "
              f"{_token_journal.prompt_tokens + _token_journal.completion_tokens} tokens today")
    except Exception:
        pass

    # RB-25 F1: a quarantined id gets NO runner.
    if not os.environ.get("AKASHIC_DRILL_ECHO"):
        try:
            from core.trust.registry import may_run_runner
            if not may_run_runner(args.agent):
                print(f"bifrost_runner_kimi: '{args.agent}' is quarantined (deny-by-default) -- "
                      f"refusing to start. A super-admin must grant it a role in security/acl.json.")
                return 3
        except Exception as e:
            print(f"[kimi-runner] may_run_runner check skipped ({type(e).__name__}) -- "
                  f"guard NOT active for '{args.agent}'", file=sys.stderr)

    # Singleton: at most ONE runner per agent id.
    lock_token = runner_lock.instance_token(args.agent)
    if not runner_lock.acquire(args.agent, lock_token):
        h = runner_lock.holder(args.agent) or {}
        tok = str(h.get("token", ""))
        if tok.startswith("session:"):
            print(f"bifrost_runner_kimi: a session '{tok}' holds the consumer seat for "
                  f"'{args.agent}' (since {h.get('ts')}). Wind it down or wait for TTL.")
        else:
            print(f"bifrost_runner_kimi: another '{args.agent}' runner is live (pid {h.get('pid')}).")
        return 3
    PULSE_GEN[0] = runner_lock.generation_of(lock_token)
    liveness.worklive(args.agent).set("starting", detail="onboarding")
    liveness.pulse(args.agent, "starting", generation=PULSE_GEN[0])

    # Budget conscience wakes FIRST: seed/reconcile against ground truth before any turn.
    bal = METER.reconcile(force=True)
    print(f"[kimi-runner] {METER.status_line()}"
          + ("" if bal is not None else " (balance endpoint unreachable -- ledger carries)"))
    if METER.exceeded_hard_limit():
        print("[kimi-runner] WARNING: seat is OVER the hard spend ceiling -- only "
              f"{sorted(BUDGET_EXEMPT_SENDERS)} asks will be answered.")

    # Hardening slice 1: session-2+ continuity header rides BOTH replier modes.
    header = continuity_header(prior)
    base_system = (header + "\n" + args.system) if header else args.system
    if header:
        print(f"[kimi-runner] continuity: session {session_n} "
              f"(prior exit={prior.get('exit_code')}, turns={prior.get('turns')})")

    if args.agentic:
        root = Path(args.root).resolve()
        system = base_system
        door_detail = (f"{len(TOOLS)} tools, write={'on' if args.allow_write else 'off'}, "
                       f"exec={'on' if args.allow_exec else 'off'}")
        onboard = onboarding_context(root, args.agent,
                                     "Live Bifrost session: third frontier seat (kimi-k3), "
                                     "collaborating with claude and deepseek on Akashic Aurora "
                                     "over the shared bus.",
                                     door_detail=door_detail)
        boot_sources = getattr(onboarding_context, "_last_sources", None)
        if boot_sources:
            print(f"[kimi-runner] boot sources from sidecar: {len(boot_sources)} entries")
        if onboard:
            system += ("\n\n=== PROJECT ONBOARDING (you are a booted Akashic Aurora citizen; honor "
                       "the AGENTS.md contract) ===\n" + onboard)
            print(f"[kimi-runner] onboarded via boot ({len(onboard)} chars folded into system prompt)")
        else:
            print("[kimi-runner] onboarding skipped (boot returned nothing; check agent_cli.py boot)")
        responder = make_kimi_replier(args.model, system, args.effort, root, args.agent,
                                      allow_write=args.allow_write, allow_exec=args.allow_exec,
                                      boot_sources=boot_sources)
        mode = (f"agentic tools @ {root}{' +write' if args.allow_write else ''}"
                f"{' +exec' if args.allow_exec else ''}")
    else:
        responder = make_one_shot_replier(args.model, base_system, args.effort,
                                          agent_id=args.agent)
        mode = "one-shot bridge"

    if os.environ.get("AKASHIC_DRILL_ECHO"):
        args.agentic = False
        responder = lambda prompt: f"[drill-echo] {str(prompt)[:120]}"
        mode = "drill-echo (offline)"

    bus.register(card=dict(CARD, spend=METER.status_line()))
    # RB-25 F2: a virgin cursor fast-forwards to the live tail.
    if not os.environ.get("AKASHIC_DRILL_ECHO") and bus.seed_cursor_at_tail():
        print(f"[kimi-runner] {args.agent} is new -- cursor seeded at the live tail "
              f"(stale broadcast backlog skipped; only new mail wakes it)")

    from core.coord import cognitive_metrics as cog
    cog.init(args.agent)
    rate = control.RateLimiter()

    stop_hb = threading.Event()

    def _heartbeat():
        beats = 0
        while not stop_hb.wait(5):
            beats += 1
            try:
                runner_lock.heartbeat(args.agent, lock_token)
                bus.register(card=dict(CARD, spend=METER.status_line()))   # W14: spend on the card
                liveness.worklive(args.agent).refresh()
                if beats % 120 == 0:                       # ~10 min: balance reconciliation
                    METER.reconcile()
            except Exception:
                pass

    threading.Thread(target=_heartbeat, daemon=True).start()

    # ---- OUT-OF-BAND CONTROL (2026-07-26) ---------------------------------------------
    # Born from this runner wedging for 12+ hours: up, heartbeating, and UNCOMMANDABLE,
    # because control.is_halted is only checked INSIDE message handling -- which cannot run
    # when the loop is blocked waiting for a message. The only path to the agent ran through
    # the path that had failed.
    #
    # This listener shares nothing with the bus: no Redis, no wslrelay, no Docker NAT, no
    # disk. It answers on its own thread while the main loop is dead.
    from core.comm.control_channel import ControlChannel
    _progress = {"last_msg_at": None, "last_msg_from": None, "handled": 0,
                 "loop_beats": 0, "started": time.time()}

    _control = ControlChannel(args.agent)

    def _cc_status(_arg: str) -> str:
        # PROGRESS, not mere liveness. The heartbeat proved the process was alive for twelve
        # hours while the loop was dead; the number that would have exposed that is how long
        # since the loop last ADVANCED, so that is what this reports.
        now = time.time()
        since_msg = (int(now - _progress["last_msg_at"])
                     if _progress["last_msg_at"] else None)
        return (f"agent={args.agent} pid={os.getpid()} "
                f"uptime_s={int(now - _progress['started'])} "
                f"loop_beats={_progress['loop_beats']} handled={_progress['handled']} "
                f"last_msg_age_s={since_msg if since_msg is not None else 'never'} "
                f"last_from={_progress['last_msg_from'] or '-'}")

    def _cc_stand_down(arg: str) -> str:
        # os._exit, deliberately. A wedged process cannot unwind: the main thread is parked in
        # a C-level recv that no Python thread can interrupt, so a graceful shutdown would
        # block on the very thing we are escaping. The cursor was never advanced, so RB-26
        # redelivers whatever was in flight and the daemon relaunches us.
        reason = arg or "control stand-down"
        print(f"[kimi-runner] STAND-DOWN via control channel: {reason}", flush=True)
        threading.Timer(0.25, lambda: os._exit(0)).start()   # let the reply flush first
        return f"standing down: {reason}"

    _control.register("status", _cc_status)
    _control.register("stand-down", _cc_stand_down)
    if not _control.start():
        print("[kimi-runner] WARNING: no out-of-band control channel -- a wedge here would "
              "be uncommandable, exactly as on 2026-07-26.")

    from core.comm.bifrost_api import BifrostAPI
    lane_mode = BifrostAPI.consume_lane_enabled()
    lane_key = bus.lane_cursor_key() if lane_mode else None
    api = BifrostAPI(args.agent) if lane_mode else None
    if lane_mode:
        if bus.lane_flip_if_migrating():
            print("[kimi-runner] lane flip: cursor seeded at lane tails (A4 ritual)")
        print("[kimi-runner] CONSUME LANE: work (T045 stage 2 cutover live)")

    lock_gen = runner_lock.generation_of(lock_token)
    PULSE_GEN[0] = lock_gen
    liveness.worklive(args.agent).set("idle")
    print(f"[kimi-runner] {args.agent} online (model={args.model}, effort={args.effort}, {mode}, "
          f"max_hops={KIMI_MAX_HOPS}). Waiting for messages...")

    exit_code = 0
    bus_guard = liveness.BusLossGuard(max_dead=10)
    try:
        while True:
            _progress["loop_beats"] += 1   # cycling, not merely alive
            verdict = bus_guard.beat(bus.probe())
            if verdict == "stand_down":
                print(f"[kimi-runner] bus LOST for {bus_guard.max_dead} beats -- standing down.")
                exit_code = 4
                break
            if verdict == "degraded":
                print(f"[kimi-runner] bus unreachable "
                      f"(beat {bus_guard.dead_beats}/{bus_guard.max_dead})")
                time.sleep(bus_guard.backoff_s)
                continue
            if not runner_lock.heartbeat(args.agent, lock_token):
                print("[kimi-runner] lost the singleton lock -- another runner is live. Standing down.")
                break
            # A1: stale-code self-restart -- loop-top only, nothing claimed. The fresh
            # copy takes the lock at a higher generation; this process stands down
            # through the same takeover path a crash would use. Proven staleness only.
            _sr = self_restart.maybe_self_restart(args.agent)
            if _sr:
                print(f"[kimi-runner] {_sr} -- exiting clean; the successor takes the lock.")
                break
            if control.is_halted(args.agent):
                bus.register(card=dict(CARD, spend=METER.status_line()))
                time.sleep(0.4)
                continue

            batch_next: dict = {}
            if lane_mode:
                msgs = api.work_drain(timeout_ms=1500, since_out=batch_next, generation=lock_gen)
            else:
                msgs = bus.wait(timeout_ms=1500, advance=False, since_out=batch_next)
            bus.register(card=dict(CARD, spend=METER.status_line()))

            fenced_out = False
            for m in msgs:
                _progress["last_msg_at"] = time.time()
                _progress["last_msg_from"] = m.frm
                _progress["handled"] += 1
                _killpoint("post-consume-pre-process")
                try:
                    _process_one(m, bus, args, responder, rate)
                except Exception as e:
                    print(f"[kimi-runner] !! unhandled error on message from {m.frm}: "
                          f"{type(e).__name__}: {e}")
                    liveness.pulse_error(args.agent, f"{type(e).__name__}: {e}", generation=lock_gen)
                    try:
                        bus.send(m.frm, "note",
                                 f"[error] kimi runner hit an unhandled error: {type(e).__name__}: {e}",
                                 meta={"via": f"{args.agent}-runner"})
                    except Exception:
                        pass
                _killpoint("post-sentinel-pre-advance")
                # Cursor law (RB-26): advance AFTER processing; lane filter as sol.
                if lane_mode and (m.meta or {}).get("_lane_src") != "work":
                    continue
                field = "bc" if str(m.to) == "*" else "inbox"
                status = bus.advance_to(**{field: m.id}, generation=lock_gen, cursor_key=lane_key)
                if status == "STALE_GENERATION":
                    print("[kimi-runner] cursor commit REFUSED (stale generation) -- standing down.")
                    fenced_out = True
                    break
                _killpoint("between-batch-messages")
            if fenced_out:
                break

            # Batch sweep: advance to the batch tail (idempotent when nothing moved).
            if batch_next and (batch_next.get("inbox") or batch_next.get("bc")):
                status = bus.advance_to(inbox=batch_next.get("inbox"), bc=batch_next.get("bc"),
                                        generation=lock_gen, cursor_key=lane_key)
                if status == "STALE_GENERATION":
                    print("[kimi-runner] batch-sweep REFUSED -- standing down.")
                    break

            if args.once and msgs:
                print("[kimi-runner] --once: one wake processed, exiting.")
                break
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        stop_hb.set()
        runner_lock.release(args.agent, lock_token)
        _write_exit_summary(args.summary_file, exit_code, session=session_n)

    print(f"[kimi-runner] stopped. {METER.status_line()}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
