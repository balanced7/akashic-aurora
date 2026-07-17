"""
bifrost_runner_sol -- make Sol (gpt-5.6-sol, OpenAI Responses API) a FIRST-CLASS Bifrost citizen.

Sol is its OWN seat (Daniel directive 2026-07-17): sol-named module, SOL_* envs, sol persona.
T090 Option B fork per the reconciled verdict (research/reviewed/sol-api-surface-*-2026-07-17.md):
clean fork now, extract core/comm/runner_lib.py after both runners stabilize.

PROVENANCE (the tempo-asymmetry pipeline's first build): the bus-loop half is merged from
deepseek-review's fast-lane deliverables -- research/drafts/sol-runner-loop-spec-2026-07-17.md
(the consume-to-commit contract + 35-item checklist) and scratch/sol_runner_fragments.py --
while SolAgent (the Responses-native tool loop) was built in parallel in sol_chat.py.

THE ONE SHARED SEAM: the guarded ToolBox (31 tools, secret-blocked, path-scoped, exec families
door) is imported from deepseek_chat [shared-seam] inside make_sol_replier. Rebuilding a
security-hardened toolbox overnight would be reckless; extraction to a neutral core module is
the post-stabilization plan. NOTHING else deepseek-named rides sol's surface.

DEFERRED HARDENING (named, not silent -- each is a follow-up slice):
  * T068-R3 preflight gate (verify claims pre-send): deepseek's implementation is itself still
    'verifying' in the ledger; sol ships without it.
  * RB-23 bounce_promise/content_floor_check: quality-of-reply gates; the RB-29 nonanswer path
    covers errors. Port after first live sessions show the failure shapes.
  * P3 fold_ledger_update body: ledger_update/resolved kinds are SWALLOWED correctly (never
    answered); prompt-folding of transitions lands with the hardening slice.
  * Full continuity header (_runner_continuity_header): sol is a newborn -- boot already carries
    DIRECTIVE + SIBLINGS; a first-class header matters from session 2 on.

Run:  py scripts/bifrost_runner_sol.py --agentic --allow-write --allow-exec       # full seat
      py scripts/bifrost_runner_sol.py --agentic --once                           # smoke: one wake
Key:  env OPENAI_API_KEY else .secrets/openai.key (same provider convention as ask_gpt.py).
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
from core.comm import context_hints
from core.comm.timescale import scaled as _scaled

from sol_chat import (SOL, DEFAULT_MODEL, DEFAULT_EFFORT, DEFAULT_VERBOSITY, EFFORTS,
                      VERBOSITIES, MAX_OUTPUT_TOKENS, SolAgent, SolTransport, load_key)

CARD = {
    "runtime_class": "api",
    "wake_mode": "runner",
    "door": "runner",
    "caps": ["review", "critique", "answer", "audit", "code", "research"],
}

# 'steer' deliberately NOT answerable (folds via inject); 'reply' NOT answerable (echo-loop guard).
ANSWERABLE = frozenset({"chat", "request", "question", "handoff", "nudge", "inform"})

REPLY_TIMEOUT_SEC = _scaled(600)   # 10 min wall-clock; drill-shrinkable (AKASHIC_TIMEOUT_MULTIPLIER)
SOL_MAX_HOPS = int(os.getenv("SOL_MAX_HOPS", "30"))

DEFAULT_SYSTEM = ("You are Sol (gpt-5.6-sol), operating as an agentic technical partner on "
                  "Akashic Aurora -- the third frontier seat beside claude (Fable) and deepseek. "
                  "You are reached over a shared message bus; each reply posts back to the sender, "
                  "so make it self-contained.")

# RB-27a: tenure fencing generation (one-slot mutable so closures see main()'s value).
PULSE_GEN = [0]

# T078 W1: per-peer token deltas, drained after each turn by _process_one.
_token_deltas: dict = {}
_RUN_STATS = {"turns": 0, "last_error": ""}


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
        print(f"[sol-runner] KILLPOINT {name} -- dying (drill)", flush=True)
        os._exit(137)


# ---- onboarding (the same boot door every citizen walks; THIS is what the ergonomics walk assesses)

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
    """Pull the project's startup briefing ONCE at boot (the same agent_cli.py boot door a human
    agent runs) and fold a TRIMMED digest into the system prompt. Never raises; '' on failure."""
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


# ---- the sol responder (SolAgent + guarded ToolBox) ------------------------------------------

def make_sol_replier(model: str, system: str, effort: str, verbosity: str, service_tier,
                     root: Path, agent_id: str, allow_write: bool = False,
                     allow_exec: bool = False, boot_sources=None):
    """Tool-using bridge: Sol reads files, searches, inspects git, and queries the knowledge base
    WHILE composing its reply. Per-peer SolAgent conversations for continuity."""
    import deepseek_chat as dc   # [shared-seam] the guarded ToolBox ONLY -- see module docstring
    # T050 Q3+Q4: capabilities declared UP FRONT -- no hop wasted discovering what a session can do.
    system = (f"[session capabilities] write_mode: "
              f"{'ENABLED (guarded write_file/edit_file live; locks self-release at reply)' if allow_write else 'READ-ONLY -- write_file/edit_file will refuse; investigate and report'}"
              f" | tool budget: {SOL_MAX_HOPS} hops per task, running counter [hop N] rides every result"
              f" | reasoning effort: {effort} | recall-at: off\n" + system)
    toolbox = dc.ToolBox(root, allow_exec=allow_exec, trust=allow_exec, allow_secrets=False,
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
            transport = SolTransport(model=model, effort=effort, verbosity=verbosity,
                                     max_output_tokens=MAX_OUTPUT_TOKENS,
                                     service_tier=service_tier)
            ag = SolAgent(transport, instructions=system, tools_schemas=dc.TOOLS,
                          dispatch=_dispatch, interrupt=interrupt, inject=inject,
                          on_trace=on_trace, on_activity=on_activity, max_hops=SOL_MAX_HOPS)
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
            answer = f"(sol agentic runner error: {type(e).__name__}: {e})"
        try:
            toolbox.release_written_locks()   # T048: task end = lock end
        except Exception:
            pass
        return answer or "(sol produced no final answer)"

    return respond


def make_one_shot_replier(model: str, system: str, effort: str, verbosity: str, service_tier):
    """One-shot bridge: each message -> one Responses completion -> reply. Fast, toolless."""
    transport = SolTransport(model=model, effort=effort, verbosity=verbosity,
                             max_output_tokens=MAX_OUTPUT_TOKENS, service_tier=service_tier)

    def respond(prompt: str) -> str:
        try:
            text, _calls, _items = SolTransport.extract(
                transport.respond(system, [{"role": "user", "content": prompt}]))
            return text or "(sol produced no final text)"
        except Exception as e:
            return f"(sol runner error: {type(e).__name__}: {e})"

    return respond


# ---- consume-to-commit pipeline (spec section 1; per-message) --------------------------------

def _process_one(m, bus, args, responder, rate) -> None:
    """Process ONE incoming message: filter chain, model turn, reply, sentinel.
    Cursor commit stays in the main loop (spec section 2.2)."""
    from core.coord import cognitive_metrics as cog
    from core.comm import turn_metrics as _tm

    # [1] R7/T058: a user's clarify-answer routes to the steer queue (the Agent polls for it)
    if str(m.kind) == "reply" and str(m.frm) == "user":
        cid = (m.meta or {}).get("clarify_id")
        if cid:
            nudge.steer_push(args.agent, m.frm, str(m.content))
            print(f"[sol-runner] clarify-answer {cid} routed to the steer queue")
            return

    # [2] HINT interception -- never answered, injected on the next model turn
    if str(m.kind) == "hint":
        meta = m.meta or {}
        hint_data = meta.get("hint") or {}
        ok = context_hints.push(args.agent, hint_data.get("key", "?"),
                                hint_data.get("value", "?"), from_agent=m.frm)
        if ok:
            cog.record_file_read(args.agent, hint_data.get("key", "?"), from_hint=True)
            print(f"[sol-runner] hint accepted ({hint_data.get('key', '?')}) from {m.frm}")
        return

    # [3] ledger fold gate -- transitions are SWALLOWED (never answered); prompt-folding is a
    # deferred hardening slice (see module docstring)
    if str(m.kind) in ("ledger_update", "resolved"):
        print(f"[sol-runner] ledger fold: {str(m.content)[:80]}")
        return

    # [4] ANSWERABLE gate
    if not should_answer(m.kind, m.frm, args.agent):
        return

    # [5] RB-26 dedup sentinel check
    if _reply_already_sent(bus, m.id):
        print(f"[sol-runner] skip {m.id} from {m.frm} -- reply already sent (redelivery)")
        return

    # [6] hop-count loop guard
    hops = control.next_hops(m.meta)
    if control.hops_exceeded(m.meta):
        bus.send(m.frm, "note",
                 f"[loop-guard] max hops ({control.MAX_HOPS}) reached -- returning to a human.",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        print(f"[sol-runner] loop-guard: hops>={control.MAX_HOPS}; not answering {m.frm}")
        return

    # [7] rate-limit backstop
    if not rate.allow():
        control.pause(reason=f"{args.agent} hit reply rate limit", by=args.agent, ttl=3600)
        bus.send(m.frm, "note",
                 "[loop-guard] reply rate limit hit -- auto-paused (self-heals in <=1h).",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        print("[sol-runner] rate limit -> auto-paused (ttl 1h)")
        return

    # [8] nudge / halt handling
    if str(m.kind) == "nudge" or nudge.is_nudged(args.agent):
        nudge.clear(args.agent)
        bus.send(m.frm, "note", "[nudge ack] interrupting current work to look at this now.",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        cog.record_human_interjection(args.agent)
        print(f"[sol-runner] nudge from {m.frm} -> acked + cleared")
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
        out = f"(sol runner timed out after {REPLY_TIMEOUT_SEC}s -- the API call was abandoned)"
        print(f"[sol-runner] !! TIMEOUT for {m.frm} after {REPLY_TIMEOUT_SEC}s")
        _RUN_STATS["last_error"] = "timeout"
    else:
        result = result_holder[0] if result_holder else "(sol runner: no result)"
        if isinstance(result, Exception):
            nonanswer = True
            out = f"(sol runner error: {type(result).__name__}: {result})"
            print(f"[sol-runner] !! responder error: {type(result).__name__}: {result}")
            _RUN_STATS["last_error"] = f"{type(result).__name__}: {result}"
        else:
            out = str(result)

    # [12] SEND REPLY -- RB-29: nonanswer -> kind="note", NO answers linkage (expectation stays
    # armed for the redrive); success -> kind="reply" + meta.answers (T066 lane-first send_reply)
    reply_kind = "note" if nonanswer else "reply"
    reply_meta = {"via": f"{args.agent}-runner", "model": args.model, "hops": hops}
    if not nonanswer:
        reply_meta["answers"] = m.id
    if str(m.to) == "*":
        bus.broadcast(reply_kind, out, meta=reply_meta)
        dest = "*(broadcast)"
    else:
        if reply_kind == "reply":
            bus.send_reply(m.frm, out, meta=reply_meta)   # T066: lane-first, meta.reply_id
        else:
            bus.send(m.frm, reply_kind, out, meta=reply_meta)
        dest = m.frm

    # [13] kill window 3
    _killpoint("post-send-pre-sentinel")

    # [14] RB-26 dedup sentinel SET (after send, before cursor commit)
    _mark_reply_sent(bus, m.id)

    # [15] P6 handoff auto-ack -- RB-29: timeout/error answers never ack
    answered_ok = (finished and result_holder and not isinstance(result_holder[0], Exception)
                   and not out.startswith("(sol"))
    if str(m.kind) == "handoff" and answered_ok:
        try:
            from core.comm.promoter import ack as _ack
            _ack(args.agent, m.id, note="answered on the bus")
            print(f"[sol-runner] acked handoff {m.id}")
        except Exception:
            pass

    # [16] turn metrics
    try:
        cog.record_turn_complete(args.agent)
        outcome = ("timeout" if not finished
                   else "error" if nonanswer
                   else "ok")
        toks = _token_deltas.pop(m.frm, None)
        _tm.record(args.agent, str(m.kind), duration_s=time.time() - turn_t0,
                   progress_points=_tm.take_pulse_count(args.agent),
                   outcome=outcome, prompt_len=len(str(m.content)),
                   tokens=(sum(toks) if toks else None))
        _RUN_STATS["turns"] += 1
    except Exception:
        pass

    # [17] activity clear
    control.clear_activity(args.agent)
    liveness.worklive(args.agent).set("idle")
    print(f"[sol-runner] -> {dest}: {out[:80]}")


# ---- exit summary (M1-delta) ------------------------------------------------------------------

def _write_exit_summary(path, exit_code):
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"exit_code": exit_code, "turns": _RUN_STATS["turns"],
                       "last_error": _RUN_STATS["last_error"] or None,
                       "verdict": "ok" if exit_code == 0 else "abnormal",
                       "timestamp": time.time()}, f)
    except Exception:
        pass


# ---- main ---------------------------------------------------------------------------------------

def main() -> int:
    try:
        from core.foundation.streams import self_bless_stdout   # RB-28: utf-8 + line-buffered
        self_bless_stdout()
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Run Sol (gpt-5.6-sol) as a Bifrost citizen.")
    ap.add_argument("--agent", default="sol")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", default=DEFAULT_SYSTEM)
    ap.add_argument("--effort", default=DEFAULT_EFFORT, choices=list(EFFORTS),
                    help="reasoning effort ladder (sol's --think analog; default medium)")
    ap.add_argument("--verbosity", default=DEFAULT_VERBOSITY, choices=list(VERBOSITIES))
    ap.add_argument("--service-tier", default=None, dest="service_tier",
                    choices=[None, "default", "flex"], help="flex = cost lever for non-urgent lanes")
    ap.add_argument("--agentic", action="store_true",
                    help="give Sol tools (read files/search/git/knowledge base) while it replies")
    ap.add_argument("--root", default=os.path.dirname(HERE),
                    help="file-access root for --agentic (default: the repo)")
    ap.add_argument("--allow-write", action="store_true",
                    help="guarded write_file/edit_file doors (path-scoped, secret-blocked)")
    ap.add_argument("--allow-exec", action="store_true",
                    help="run_command door (families-only under trust; see security/acl.json)")
    ap.add_argument("--once", action="store_true", help="process one wake then exit (smoke)")
    ap.add_argument("--summary-file", default=None, dest="summary_file")
    ap.add_argument("--inject-summary", default=None, dest="inject_summary")
    args = ap.parse_args()

    if not load_key():
        print("bifrost_runner_sol: NO_KEY (set OPENAI_API_KEY or .secrets/openai.key)")
        return 2
    bus = Bus(args.agent)
    if not bus.online:
        print("bifrost_runner_sol: bus OFFLINE (Redis unreachable)")
        return 2

    # RB-25 F1: a quarantined id gets NO runner (reply/trace lanes reach the bus as infrastructure).
    if not os.environ.get("AKASHIC_DRILL_ECHO"):
        try:
            from core.trust.registry import may_run_runner
            if not may_run_runner(args.agent):
                print(f"bifrost_runner_sol: '{args.agent}' is quarantined (deny-by-default) -- "
                      f"refusing to start. A super-admin must grant it a role in security/acl.json.")
                return 3
        except Exception as e:
            print(f"[sol-runner] may_run_runner check skipped ({type(e).__name__}) -- "
                  f"guard NOT active for '{args.agent}'", file=sys.stderr)

    # Singleton: at most ONE runner per agent id (two runners share one read-cursor and race).
    lock_token = runner_lock.instance_token(args.agent)
    if not runner_lock.acquire(args.agent, lock_token):
        h = runner_lock.holder(args.agent) or {}
        tok = str(h.get("token", ""))
        if tok.startswith("session:"):
            print(f"bifrost_runner_sol: a session '{tok}' holds the consumer seat for "
                  f"'{args.agent}' (since {h.get('ts')}). Wind it down or wait for TTL.")
        else:
            print(f"bifrost_runner_sol: another '{args.agent}' runner is live (pid {h.get('pid')}).")
        return 3
    PULSE_GEN[0] = runner_lock.generation_of(lock_token)
    liveness.worklive(args.agent).set("starting", detail="onboarding")
    liveness.pulse(args.agent, "starting", generation=PULSE_GEN[0])

    try:
        from scripts.runner_token_journal import TokenJournal
        journal = TokenJournal(args.agent)
        print(f"[sol-runner] token journal: {journal.turns} turns, "
              f"{journal.prompt_tokens + journal.completion_tokens} tokens today")
    except Exception:
        journal = None

    if args.agentic:
        root = Path(args.root).resolve()
        system = args.system
        # M1-delta: prior run summary injection
        if getattr(args, "inject_summary", None):
            try:
                with open(args.inject_summary, encoding="utf-8") as _sf:
                    prior = json.loads(_sf.read().strip() or "{}") or {}
                if prior:
                    system = (f"## YOUR LAST RUN: exit={prior.get('exit_code')} "
                              f"turns={prior.get('turns')} last_error={prior.get('last_error')}\n\n"
                              + system)
            except Exception:
                pass
        import deepseek_chat as dc   # [shared-seam] tool count for the boot transport line only
        door_detail = (f"{len(dc.TOOLS)} tools, write={'on' if args.allow_write else 'off'}, "
                       f"exec={'on' if args.allow_exec else 'off'}")
        onboard = onboarding_context(root, args.agent,
                                     "Live Bifrost session: third frontier seat, collaborating "
                                     "with claude and deepseek on Akashic Aurora over the shared bus.",
                                     door_detail=door_detail)
        boot_sources = getattr(onboarding_context, "_last_sources", None)
        if boot_sources:
            print(f"[sol-runner] boot sources from sidecar: {len(boot_sources)} entries")
        if onboard:
            system += ("\n\n=== PROJECT ONBOARDING (you are a booted Akashic Aurora citizen; honor "
                       "the AGENTS.md contract) ===\n" + onboard)
            print(f"[sol-runner] onboarded via boot ({len(onboard)} chars folded into system prompt)")
        else:
            print("[sol-runner] onboarding skipped (boot returned nothing; check agent_cli.py boot)")
        responder = make_sol_replier(args.model, system, args.effort, args.verbosity,
                                     args.service_tier, root, args.agent,
                                     allow_write=args.allow_write, allow_exec=args.allow_exec,
                                     boot_sources=boot_sources)
        mode = (f"agentic tools @ {root}{' +write' if args.allow_write else ''}"
                f"{' +exec' if args.allow_exec else ''}")
    else:
        responder = make_one_shot_replier(args.model, args.system, args.effort,
                                          args.verbosity, args.service_tier)
        mode = "one-shot bridge"

    if os.environ.get("AKASHIC_DRILL_ECHO"):
        args.agentic = False
        responder = lambda prompt: f"[drill-echo] {str(prompt)[:120]}"
        mode = "drill-echo (offline)"

    bus.register(card=CARD)
    # RB-25 F2: a virgin cursor fast-forwards to the live tail (stale broadcast backlog is
    # HISTORY, not directive); an established runner keeps draining its real backlog.
    if not os.environ.get("AKASHIC_DRILL_ECHO") and bus.seed_cursor_at_tail():
        print(f"[sol-runner] {args.agent} is new -- cursor seeded at the live tail "
              f"(stale broadcast backlog skipped; only new mail wakes it)")

    from core.coord import cognitive_metrics as cog
    cog.init(args.agent)
    rate = control.RateLimiter()

    stop_hb = threading.Event()

    def _heartbeat():
        while not stop_hb.wait(5):
            try:
                runner_lock.heartbeat(args.agent, lock_token)
                bus.register(card=CARD)
                liveness.worklive(args.agent).refresh()
            except Exception:
                pass

    threading.Thread(target=_heartbeat, daemon=True).start()

    from core.comm.bifrost_api import BifrostAPI
    lane_mode = BifrostAPI.consume_lane_enabled()
    lane_key = bus.lane_cursor_key() if lane_mode else None
    api = BifrostAPI(args.agent) if lane_mode else None
    if lane_mode:
        if bus.lane_flip_if_migrating():
            print("[sol-runner] lane flip: cursor seeded at lane tails (A4 ritual)")
        print("[sol-runner] CONSUME LANE: work (T045 stage 2 cutover live)")

    lock_gen = runner_lock.generation_of(lock_token)
    PULSE_GEN[0] = lock_gen
    liveness.worklive(args.agent).set("idle")
    print(f"[sol-runner] {args.agent} online (model={args.model}, effort={args.effort}, "
          f"verbosity={args.verbosity}, {mode}, max_hops={SOL_MAX_HOPS}). Waiting for messages...")

    exit_code = 0
    bus_guard = liveness.BusLossGuard(max_dead=10)
    try:
        while True:
            verdict = bus_guard.beat(bus.probe())
            if verdict == "stand_down":
                print(f"[sol-runner] bus LOST for {bus_guard.max_dead} beats -- standing down.")
                exit_code = 4
                break
            if verdict == "degraded":
                print(f"[sol-runner] bus unreachable "
                      f"(beat {bus_guard.dead_beats}/{bus_guard.max_dead})")
                time.sleep(bus_guard.backoff_s)
                continue
            if not runner_lock.heartbeat(args.agent, lock_token):
                print("[sol-runner] lost the singleton lock -- another runner is live. Standing down.")
                break
            if control.is_halted(args.agent):
                bus.register(card=CARD)
                time.sleep(0.4)
                continue

            batch_next: dict = {}
            if lane_mode:
                msgs = api.work_drain(timeout_ms=1500, since_out=batch_next, generation=lock_gen)
            else:
                msgs = bus.wait(timeout_ms=1500, advance=False, since_out=batch_next)
            bus.register(card=CARD)

            fenced_out = False
            for m in msgs:
                _killpoint("post-consume-pre-process")
                try:
                    _process_one(m, bus, args, responder, rate)
                except Exception as e:
                    print(f"[sol-runner] !! unhandled error on message from {m.frm}: "
                          f"{type(e).__name__}: {e}")
                    liveness.pulse_error(args.agent, f"{type(e).__name__}: {e}", generation=lock_gen)
                    try:
                        bus.send(m.frm, "note",
                                 f"[error] sol runner hit an unhandled error: {type(e).__name__}: {e}",
                                 meta={"via": f"{args.agent}-runner"})
                    except Exception:
                        pass
                _killpoint("post-sentinel-pre-advance")
                # Cursor law (RB-26): advance AFTER processing; lane filter: non-work stream ids
                # never advance work fields (their cursors advanced inside work_drain).
                if lane_mode and (m.meta or {}).get("_lane_src") != "work":
                    continue
                field = "bc" if str(m.to) == "*" else "inbox"
                status = bus.advance_to(**{field: m.id}, generation=lock_gen, cursor_key=lane_key)
                if status == "STALE_GENERATION":
                    print("[sol-runner] cursor commit REFUSED (stale generation) -- standing down.")
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
                    print("[sol-runner] batch-sweep REFUSED -- standing down.")
                    break

            if args.once and msgs:
                print("[sol-runner] --once: one wake processed, exiting.")
                break
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        stop_hb.set()
        runner_lock.release(args.agent, lock_token)
        _write_exit_summary(args.summary_file, exit_code)

    print("[sol-runner] stopped.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
