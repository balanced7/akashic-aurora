"""
bifrost_runner_deepseek -- make DeepSeek (a stateless API model) a FIRST-CLASS Bifrost citizen.

Mirrors scripts/bifrost_runner.py (the Gemini runner). DeepSeek has no process and no inbox of its
own, so this runner is its body: it registers @deepseek presence (an Agent Card), blocks on
DeepSeek's Bifrost inbox, and for each incoming ask posts a reply back on the bus. So
`py agent_cli.py bifrost-send <you> --to deepseek "..."` -- or any agent messaging 'deepseek' --
gets a real reply, and the sender wakes (bifrost_wake) when it lands = real-time Claude <-> DeepSeek.

Two modes:
  * one-shot bridge (default) -- each message -> one DeepSeek completion -> reply. Fast, stateless.
  * --agentic -- DeepSeek gets TOOLS (read files, search, git, query the Akashic knowledge base) and
    can chain them WHILE composing the reply, with a per-peer conversation for continuity. Reuses the
    guarded Agent+ToolBox from deepseek_chat.py (read-only, secret-blocked, path-scoped). This is how
    DeepSeek actually investigates the codebase and helps build, not just chat.

  py scripts/bifrost_runner_deepseek.py                     # one-shot, v4-pro, thinking off
  py scripts/bifrost_runner_deepseek.py --agentic           # tool-using peer (reads code/KB live)
  py scripts/bifrost_runner_deepseek.py --agentic --think   # + deep reasoning
  py scripts/bifrost_runner_deepseek.py --model deepseek-v4-flash --once   # cheap; one msg then exit

Key: env DEEPSEEK_API_KEY else .secrets/deepseek.key (reused from ask_deepseek.py). OpenAI-compatible.
"""
import argparse
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
from core.coord import cognitive_metrics as cog
from ask_deepseek import load_key, BASE_URL, DEFAULT_MODEL

CARD = {
    "runtime_class": "api",
    "wake_mode": "runner",
    "door": "runner",
    "caps": ["review", "critique", "answer", "audit", "code"],
}
# 'steer' is deliberately NOT answerable: it never triggers a standalone reply -- it is folded into the
# agent's CURRENT task via the inject() hook. 'inform'/'nudge' do get a turn (acknowledge/adopt/switch).
ANSWERABLE = frozenset({"chat", "request", "question", "handoff", "nudge", "inform"})
# T014: reply timeout guard -- a hung API call must not wedge the runner forever.
# The API client already has a socket timeout (L0), but we add a wall-clock deadline
# via threading so even a stuck stream can't block the main loop beyond this window.
from core.comm.timescale import scaled as _scaled
REPLY_TIMEOUT_SEC = _scaled(600)   # 10 min; drill-shrinkable (AKASHIC_TIMEOUT_MULTIPLIER)
# T018: explicit completion headroom. v4-pro is a REASONING model -- with no explicit cap the
# provider default gets eaten by internal reasoning, and a long tool turn wraps up in a short
# promise instead of the deliverable (reasoning_model_token_headroom; seen live 2026-07-09).
MAX_TOKENS = int(os.environ.get("DEEPSEEK_RUNNER_MAX_TOKENS", "8000"))

# RB-26/L1 (T030): the five kill windows of the consume->outcome pipeline. When
# AKASHIC_KILLPOINT names one, the runner dies HARD there (os._exit skips finally/atexit --
# a true crash, per the crash-only drill discipline). The drill harness arms one window,
# proves death, relaunches, and asserts at-least-once redelivery with effectively-once
# replies. Never armed in production.
KILLPOINT = os.environ.get("AKASHIC_KILLPOINT", "")


def killpoint(name: str) -> None:
    if KILLPOINT and KILLPOINT == name:
        print(f"[deepseek-runner] KILLPOINT {name} -- dying (drill)", flush=True)
        os._exit(137)


# RB-26 (T030): reply dedup sentinel -- effectively-once for EVERY answerable kind, not
# just handoffs (deepseek deep-read: a cursor-write failure after processing redelivers
# the whole batch; without this, chat/request/nudge senders get duplicate replies). Set
# AFTER the reply sends, BEFORE the cursor commits; checked before answering a redelivery.
REPLY_SENT_PREFIX = "bifrost:reply_sent:"

# RB-27a: the tenure's fencing generation rides every pulse (one-slot mutable so the
# closures in make_agentic_replier see the value main() sets after lock acquisition).
PULSE_GEN = [0]


def _reply_already_sent(bus, mid) -> bool:
    try:
        return bool(bus._client.exists(REPLY_SENT_PREFIX + str(mid)))
    except Exception:
        return False   # fail-open: a duplicate reply is cheaper than a dropped one


def _mark_reply_sent(bus, mid) -> None:
    try:
        bus._client.set(REPLY_SENT_PREFIX + str(mid), "1", ex=REPLY_TIMEOUT_SEC + 60, nx=True)
    except Exception:
        pass


# P3 (T023): ledger transitions fold into the NEXT turn, latest-per-task. Deliberately a
# separate one-slot-per-task dict rather than the context_hints ring: the fold spec's own
# caveat was a lifecycle burst (propose->approve->claim->start) evicting unrelated hints
# from the 8-slot ring -- here a burst coalesces to one line per task and evicts nothing.
# Drained (and cleared) once per model turn; the ledger file remains the only truth.
LEDGER_FOLDS: dict = {}


# RB-1 (T029): the ledger's control plane has exactly ONE legitimate emitter. Folds key on
# the `frm` stamped by Bus._emit -- the closest thing to identity without signed messages --
# and NEVER on meta (sender-populated: a forger sets meta.via="conductor" and walks through;
# deepseek fenced recon 2026-07-10). Honest bound: frm is unauthenticated today, so this is
# defense-in-depth for a trusted fleet until identity is signed.
CONTROL_PLANE_SENDERS = {"conductor"}


def fold_ledger_update(msg) -> bool:
    """Store a ledger_update/resolved marker for the next turn (latest-per-task). Never
    answered, never a wake -- pre-digested context, not a prompt (fold spec, echo rule).
    RB-1: folded ONLY from the conductor; any other sender is logged and ignored."""
    try:
        frm = str(getattr(msg, "frm", "") or "")
        if frm not in CONTROL_PLANE_SENDERS:
            print(f"[deepseek-runner] DROP control-plane {getattr(msg, 'kind', '?')} "
                  f"from {frm!r} -- only the conductor moves the ledger (RB-1)")
            return False
        meta = getattr(msg, "meta", None) or {}
        tid = str(meta.get("task") or str(getattr(msg, "content", ""))[:24])
        LEDGER_FOLDS[tid] = str(getattr(msg, "content", ""))[:200]
        return True
    except Exception:
        return False


def drain_ledger_folds() -> str:
    """The LEDGER UPDATES block for this turn's prompt ('' when none). Clears the dict --
    each transition is steering context exactly once; the boot snapshot is the backstop."""
    if not LEDGER_FOLDS:
        return ""
    lines = ["## LEDGER UPDATES (since your onboarding -- the ledger file is the truth)"]
    lines += ["- " + v for v in LEDGER_FOLDS.values()]
    LEDGER_FOLDS.clear()
    return "\n".join(lines)


def bounce_promise(answer, resend):
    """One deliver-now bounce for a promise-shaped final reply (T018).

    A runner reply is the agent's LAST word on a message -- there is no later turn, so a
    final paragraph like "Let me fold this into my review closure" strands the deliverable
    (the runner-side twin of the claude stop-hook promise check, which caught this class for
    Claude in T012; seen live on the T017 seat-2 review, 2026-07-09). When `answer` ends
    promise-shaped, call `resend(reprompt)` ONCE and return its result; otherwise (or on any
    error) return `answer` unchanged. Never loops: a second promise ships as-is -- one bounce
    is a nudge, two is a wedge (the stop-hook's own latch rule).

    Wider net than the claude stop hook ON PURPOSE: the hook keeps a high-precision opener
    list because its false positives are user-visible blocks; here a false bounce costs one
    extra completion and usually improves the reply. The live T017 miss ("Let me fold this
    into my review closure") starts with bare "let me", which the hook's list requires
    "let me now" for -- the runner adds that opener locally, with the same question /
    user-conditional carve-outs."""
    try:
        import re
        from hooks.claude_stop import USER_CONDITIONAL, final_paragraph, promise_shaped
        para = final_paragraph(answer or "")
        excerpt = promise_shaped(para)
        if not excerpt:
            p = (para or "").strip()
            low = p.lower()
            norm = re.sub(r"^[\s>*\-\d.]+", "", low)
            if (p and not p.endswith("?")
                    and not any(k in low for k in USER_CONDITIONAL)
                    and re.match(r"^let me (?!know\b)", norm)):
                excerpt = p[:120]
    except Exception:
        return answer
    if not excerpt:
        return answer
    try:
        bounced = resend(
            'Your reply ended on a promise of future work ("' + excerpt[:80] + '..."). '
            "This reply is your LAST word on this message -- there is no later turn. "
            "Deliver the promised work NOW, in full, in this reply. "
            "No acknowledgment, no preamble, no further promises.")
        return bounced or answer
    except Exception:
        return answer
DEFAULT_SYSTEM = (
    "You are DeepSeek, collaborating in real time with Claude (and the user) over a shared message "
    "bus. Each reply posts straight back to the sender, so be direct and self-contained. Keep it "
    "concise unless asked to go deep."
)


def should_answer(kind, frm, self_id) -> bool:
    """Answer direct asks from others; ignore our own echoes and non-question kinds (e.g. 'reply').
    Keeping 'reply' out of ANSWERABLE is also the echo-loop guard: a reply never triggers a reply."""
    return frm != self_id and str(kind) in ANSWERABLE


def make_replier(model: str, system: str, think: bool):
    """One-shot prompt->reply bridge over the DeepSeek API. Never raises: any failure comes back as a
    string so the runner loop stays alive and the sender always gets *something*."""
    import deepseek_chat as dc
    client = dc.make_client(load_key())   # L0: timeout + explicit retries so a hung call can't wedge the runner

    def respond(prompt: str) -> str:
        try:
            kwargs = {"model": model, "max_tokens": MAX_TOKENS, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}]}
            if think:
                kwargs["reasoning_effort"] = "high"
                kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or "(deepseek returned an empty reply)"
        except Exception as e:
            return f"(deepseek runner error: {type(e).__name__}: {e})"

    return respond


def make_agentic_replier(model: str, system: str, think: bool, root: Path, agent_id: str,
                         allow_write: bool = False, allow_exec: bool = False):
    """Tool-using bridge: DeepSeek can read files, search, inspect git, and query the Akashic knowledge
    base WHILE composing its reply, then posts the final answer to the bus. Reuses the guarded
    Agent+ToolBox from deepseek_chat.py (read-only, secret-blocked, path-scoped). Keeps a per-peer
    conversation for continuity. Unattended, so gated actions (run_command) auto-deny."""
    import deepseek_chat as dc
    client = dc.make_client(load_key())   # L0: timeout + explicit retries so a hung stream can't wedge the runner (G4)
    # agent_id -> the ToolBox's bifrost_* doors go live, so DeepSeek can INITIATE bus messages (not just reply).
    # allow_write -> the guarded write_file/edit_file doors go live (path-scoped, secret-blocked, git-tracked).
    # allow_exec -> run_command door goes live. Unattended (confirm auto-denies), so pair with trust=True
    # or every command self-denies. Time-boxed while claude is at weekly limit; see security/acl.json.
    toolbox = dc.ToolBox(root, allow_exec=allow_exec, trust=allow_exec, allow_secrets=False,
                         confirm=lambda _p: False, agent_id=agent_id, allow_write=allow_write)
    _wl = liveness.worklive(agent_id)
    def on_activity(state, detail):
        control.set_activity(agent_id, state, detail)   # existing UI presence
        _wl.set(state, detail)                          # L1: same edges -> worklive phase (thinking/reading/...)
        liveness.pulse(agent_id, f"{state}:{str(detail)[:60]}", generation=PULSE_GEN[0])
    # Live trace: stream each tool call + chunk of thinking onto the bus (kind=trace, display-only, not
    # promoted/answerable) so the console shows what DeepSeek is DOING, not just its final answer.
    trace_bus = Bus(agent_id)

    def on_trace(kind, text):
        prefix = "🔧" if kind == "tool" else "💭"
        # RB-27a: every tool call / thinking chunk IS a progress point -- the pulse that
        # lets the doctor tell long-legit-work from a worker dead inside the turn.
        liveness.pulse(agent_id, f"{kind}:{str(text)[:60]}", generation=PULSE_GEN[0])
        try:
            trace_bus.broadcast("trace", f"{prefix} {text}",
                                meta={"via": f"{agent_id}-runner", "hops": 0, "trace": kind, "display_only": True})
        except Exception:
            pass

    # Barge-in: a HALT aimed at me (global pause OR my per-agent halt flag) OR a nudge TARGETED at me both
    # stop work mid-tool-loop (DeepSeek's insight, now extended to per-agent halt/nudge). The nudge flag is
    # cleared by the runner loop before it hands me the nudge message, so answering it is never self-interrupted.
    interrupt = lambda: control.is_halted(agent_id) or nudge.is_nudged(agent_id)
    # STEER: between rounds, fold any queued facts into the LIVE task without restarting (soft fidelity).
    inject = lambda: nudge.steer_drain(agent_id)
    convos: dict = {}

    def respond(frm: str, prompt: str) -> str:
        ag = convos.get(frm)
        if ag is None:
            # on_activity -> rich presence: reports thinking/reading/searching/... to the console live
            ag = dc.Agent(client, toolbox, model=model, system=system, think=think, tools_enabled=True,
                          interrupt=interrupt, on_activity=on_activity, inject=inject, on_trace=on_trace)
            ag.max_tokens = MAX_TOKENS               # T018: reasoning headroom, never provider-default
            convos[frm] = ag
        # Fold any queued context hints from peers into this turn's prompt. RB-5/RB-6:
        # ring overflow is CONFESSED in the block, never a silent narrowing.
        try:
            hints = context_hints.drain(agent_id)
            dropped = context_hints.take_dropped(agent_id)
            if hints or dropped:
                hint_block = context_hints.format_for_prompt(hints, dropped=dropped)
                prompt = hint_block + "\n" + prompt
        except Exception:
            pass
        try:
            ledger_block = drain_ledger_folds()   # P3: latest-per-task transitions, once
            if ledger_block:
                prompt = ledger_block + "\n" + prompt
        except Exception:
            pass
        try:
            answer = ag.send(prompt)                 # streams to the runner window; returns final text
        except Exception as e:
            return f"(deepseek agentic runner error: {type(e).__name__}: {e})"
        answer = bounce_promise(answer, ag.send)     # T018: a promise is not a deliverable
        return answer or "(deepseek produced no final answer)"

    return respond


def onboarding_context(root: Path, agent_id: str, task: str, budget_chars: int = 6000) -> str:
    """Onboard the runner as a first-class citizen: pull the project's startup briefing ONCE at boot
    (the same `agent_cli.py boot` door a human agent runs) and return a TRIMMED digest to fold into
    the system prompt. Trimmed on purpose -- a stateless API peer has no prompt caching, so whatever we
    inject rides EVERY call; we keep the highest-ranked head (contract pointer + current focus + top
    lessons) and drop the tail. Never raises: any failure returns '' and the runner still starts."""
    import subprocess
    try:
        p = subprocess.run([sys.executable, "agent_cli.py", "boot", agent_id, "--task", task],
                           cwd=str(root), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=90)
        digest = (p.stdout or "").strip()
    except Exception:
        return ""
    if not digest:
        return ""
    if len(digest) > budget_chars:
        digest = digest[:budget_chars].rstrip() + "\n... [onboarding trimmed to keep bus replies lean]"
    return digest


def _process_one(m, bus, args, responder, rate) -> None:
    """Process a SINGLE incoming message: filter, answer, reply. (T014: extracted from the
    main loop so per-message exceptions never skip the rest of the batch.)"""
    # HINT interception: context hints are NOT answered -- they're stored in a ring buffer
    # and injected on the NEXT model call. The "push" half; "drain" half is in respond().
    if str(m.kind) == "hint":
        meta = m.meta or {}
        hint_data = meta.get("hint") or {}
        ok = context_hints.push(args.agent,
                               hint_data.get("key", "?"),
                               hint_data.get("value", "?"),
                               from_agent=m.frm)
        if ok:
            cog.record_file_read(args.agent, hint_data.get("key", "?"), from_hint=True)
            print(f"[deepseek-runner] hint accepted ({hint_data.get('key','?')}) "
                  f"from {m.frm}: {hint_data.get('value','?')[:100]}")
        return
    if str(m.kind) in ("ledger_update", "resolved"):
        # P3 (T023): fold, never answer -- the ledger view stops being frozen at onboarding.
        if fold_ledger_update(m):
            print(f"[deepseek-runner] ledger fold: {str(m.content)[:80]}")
        return
    if not should_answer(m.kind, m.frm, args.agent):
        return
    if _reply_already_sent(bus, m.id):
        # RB-26: a redelivered message we already answered in a prior tenure -- the
        # at-least-once duplicate, settled by the sentinel. Skip silently-but-loggably.
        print(f"[deepseek-runner] skip {m.id} from {m.frm} -- reply already sent (redelivery)")
        return
    hops = control.next_hops(m.meta)
    if control.hops_exceeded(m.meta):             # loop-guard: bounce the thread to a human
        bus.send(m.frm, "note",
                 f"[loop-guard] max hops ({control.MAX_HOPS}) reached -- returning to a human.",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        print(f"[deepseek-runner] loop-guard: hops>={control.MAX_HOPS}; not answering {m.frm}")
        return
    if not rate.allow():                          # backstop: too many replies too fast
        control.pause(reason=f"{args.agent} hit reply rate limit", by=args.agent)
        bus.send(m.frm, "note",
                 "[loop-guard] reply rate limit hit -- auto-paused. Resume when ready.",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        print("[deepseek-runner] rate limit -> auto-paused")
        return
    prompt = m.content if isinstance(m.content, str) else str(m.content)
    print(f"[deepseek-runner] <- {m.frm} [{m.kind}] (hop {hops}): {prompt[:80]}")
    if str(m.kind) == "nudge" or nudge.is_nudged(args.agent):
        nudge.clear(args.agent)               # consume so answering the nudge isn't self-interrupted
        bus.send(m.frm, "note", "[nudge ack] interrupting current work to look at this now.",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        cog.record_human_interjection(args.agent)
        print(f"[deepseek-runner] nudge from {m.frm} -> acked + cleared")
    # If globally halted, record the interjection too
    if control.is_halted(args.agent) and str(m.kind) != "nudge":
        cog.record_human_interjection(args.agent)
    control.set_activity(args.agent, "thinking")
    liveness.worklive(args.agent).set("handling", detail=f"{m.frm}:{m.kind}", new_turn=True)  # L1
    killpoint("post-phase-flip-pre-send")
    try:
        # T014: wall-clock timeout guard -- a hung API call (or stuck stream) must not
        # wedge the runner forever. The API client's own socket timeout is the first line
        # of defense; this is the second. A timeout returns an error string instead of raising.
        result_holder: list = []
        worker_done = threading.Event()

        def _call():
            try:
                if args.agentic:
                    result_holder.append(responder(m.frm, prompt))
                else:
                    result_holder.append(responder(prompt))
            except Exception as ex:
                result_holder.append(ex)
            finally:
                worker_done.set()

        t = threading.Thread(target=_call, daemon=True)
        t.start()
        finished = worker_done.wait(timeout=REPLY_TIMEOUT_SEC)
        # T019: on the critical path, SEND BEFORE PRINT. A blocked stdout (undrained pipe,
        # console select-mode) froze this exact guard on 2026-07-09 -- the timeout fired but
        # its print wedged before the note ever reached the bus. Log lines are deferred
        # until after the reply is on the wire.
        log_note = ""
        if not finished:
            out = (f"(deepseek runner timed out after {REPLY_TIMEOUT_SEC}s -- "
                   f"the API call was abandoned to keep the runner alive)")
            log_note = f"[deepseek-runner] !! TIMEOUT for {m.frm} after {REPLY_TIMEOUT_SEC}s"
        else:
            result = result_holder[0] if result_holder else "(deepseek runner: no result)"
            if isinstance(result, Exception):
                out = f"(deepseek runner error: {type(result).__name__}: {result})"
                log_note = f"[deepseek-runner] !! error from responder: {type(result).__name__}: {result}"
            else:
                out = str(result)
        reply_meta = {"via": f"{args.agent}-runner", "model": args.model, "hops": hops}
        # Channel mirror: a message that arrived by BROADCAST is replied by broadcast, so the
        # whole group (Claude + the console) sees it -- not just the sender. Direct stays direct.
        if str(m.to) == "*":
            bus.broadcast("reply", out, meta=reply_meta)
            dest = "*(broadcast -> all)"
        else:
            # T014: directed reply lands in the requester's inbox. We use kind="reply"
            # (deliberately not in ANSWERABLE) so no runner<->runner echo loop is possible.
            # The recipient can still SEE it via peek/consume -- the filter is on ANSWERING,
            # not visibility. The defect was the recipient's runner consuming it silently
            # (wait(advance=True) + should_answer filter = consume-without-display).
            bus.send(m.frm, "reply", out, meta=reply_meta)
            dest = m.frm
        killpoint("post-send-pre-sentinel")
        _mark_reply_sent(bus, m.id)   # RB-26: dedup sentinel BEFORE the cursor commits
        cog.record_turn_complete(args.agent)
        # P6 (T026): a REAL answer to a handoff IS handling it -- auto-ack durably. Timeout
        # and error replies deliberately do NOT ack: the sender must still see UNHANDLED in
        # promoted() and re-drive (read != handled was the four-incident disease).
        # Red-team boundary: refusals ARE handling; error-STRING replies are not -- respond()
        # catches exceptions internally and returns "(deepseek ... error:" strings, which the
        # Exception check alone would have acked as handled.
        answered_ok = (finished and result_holder
                       and not isinstance(result_holder[0], Exception)
                       and not out.startswith("(deepseek"))
        if str(m.kind) == "handoff" and answered_ok:
            try:
                from core.comm.promoter import ack as _ack
                _ack(args.agent, m.id, note="answered on the bus")
                print(f"[deepseek-runner] acked handoff {m.id}")
            except Exception:
                pass
        if log_note:
            print(log_note)
        print(f"[deepseek-runner] -> {dest}: {out[:80]}")
    finally:
        control.clear_activity(args.agent)   # back to idle -> UI stops showing it working
        liveness.worklive(args.agent).set("idle")   # L1: turn done (ok or errored) -> idle; heartbeat keeps it fresh


def main() -> int:
    try:                                             # DeepSeek replies can carry unicode; the runner
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # window must not die on cp1252
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Run DeepSeek as a Bifrost citizen.")
    ap.add_argument("--agent", default="deepseek")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", default=DEFAULT_SYSTEM)
    ap.add_argument("--agentic", action="store_true",
                    help="give DeepSeek tools (read files/search/git/knowledge base) while it replies")
    ap.add_argument("--root", default=os.path.dirname(HERE),
                    help="file-access root for --agentic (default: the repo)")
    ap.add_argument("--think", action="store_true", help="enable DeepSeek thinking mode (deeper, slower)")
    ap.add_argument("--allow-write", action="store_true",
                    help="let DeepSeek write/edit files (guarded: path-scoped, secret-blocked, git-tracked)")
    ap.add_argument("--allow-exec", action="store_true",
                    help="let DeepSeek run shell commands (tests/builds/git). Unattended: auto-approved (trust). "
                         "Time-boxed grant while claude is unavailable -- see security/acl.json")
    ap.add_argument("--accept-hints", action="store_true",
                    help="log cognitive-efficiency metrics for this agent")
    ap.add_argument("--once", action="store_true", help="process one wake then exit (for testing)")
    args = ap.parse_args()

    if not load_key():
        print("bifrost_runner_deepseek: NO_KEY (set DEEPSEEK_API_KEY or .secrets/deepseek.key)")
        return 2
    bus = Bus(args.agent)
    if not bus.online:
        print("bifrost_runner_deepseek: bus OFFLINE (Redis unreachable)")
        return 2

    # Singleton guard: at most ONE runner per agent id. Two runners share one read-cursor and race --
    # one advances past a message the other should answer, so mail gets consumed with no reply.
    lock_token = runner_lock.instance_token(args.agent)
    if not runner_lock.acquire(args.agent, lock_token):
        h = runner_lock.holder(args.agent) or {}
        print(f"bifrost_runner_deepseek: another '{args.agent}' runner is already live (pid {h.get('pid')}). "
              f"Refusing to start -- one runner per agent avoids cursor races.")
        return 3
    # RB-27a: 'starting' phase spans onboarding/responder construction -- a boot-time
    # wedge (hung onboarding subprocess, dead API) is distinguishable from a mid-run one.
    PULSE_GEN[0] = runner_lock.generation_of(lock_token)
    liveness.worklive(args.agent).set("starting", detail="onboarding")
    liveness.pulse(args.agent, "starting", generation=PULSE_GEN[0])

    if args.agentic:
        import deepseek_chat as dc
        if dc._enable_utf8_and_ansi():
            dc.C.enable()
        root = Path(args.root).resolve()
        system = args.system
        if system == DEFAULT_SYSTEM:                 # give the tool-aware prompt unless overridden
            system = dc.default_system(root) + (" You are reached over a shared message bus; each "
                     "reply posts back to the sender, so make it self-contained.")
        # Onboarding-on-init: boot ONCE and fold the project briefing into the system prompt, so every
        # reply is grounded in the contract + current focus + top lessons (not answering blind).
        onboard = onboarding_context(root, args.agent,
                    "Live Bifrost session: collaborating with Claude and the user on Akashic Aurora over the shared bus.")
        if onboard:
            system += ("\n\n=== PROJECT ONBOARDING (you are a booted Akashic Aurora citizen; honor the "
                       "AGENTS.md contract) ===\n" + onboard)
            print(f"[deepseek-runner] onboarded via boot ({len(onboard)} chars folded into system prompt)")
        else:
            print("[deepseek-runner] onboarding skipped (boot returned nothing; check agent_cli.py boot)")
        responder = make_agentic_replier(args.model, system, args.think, root, args.agent,
                                         allow_write=args.allow_write, allow_exec=args.allow_exec)
        mode = f"agentic tools @ {root}{' +write' if args.allow_write else ''}{' +exec' if args.allow_exec else ''}"
    else:
        responder = make_replier(args.model, args.system, args.think)
        mode = "one-shot bridge"

    if os.environ.get("AKASHIC_DRILL_ECHO"):
        # L1 kill-window drills: a deterministic offline responder -- the drill proves the
        # CONSUME->COMMIT pipeline, not the model. Never set in production.
        args.agentic = False
        responder = lambda prompt: f"[drill-echo] {str(prompt)[:120]}"
        mode = "drill-echo (offline)"

    bus.register(card=CARD)

    # Initialize cognitive efficiency metrics for this agent
    cog.init(args.agent)
    if args.accept_hints:
        print(f"[deepseek-runner] cognitive metrics enabled for {args.agent}")
    rate = control.RateLimiter()
    # Background heartbeat: refresh presence + the singleton lock every few seconds INDEPENDENT of the
    # work loop. Without this, a long reply (the loop is blocked inside responder()) would let presence
    # expire -- the agent vanishes from the roster though it's alive -- and even let the lock TTL lapse.
    stop_hb = threading.Event()

    def _heartbeat():
        while not stop_hb.wait(5):
            try:
                runner_lock.heartbeat(args.agent, lock_token)
                bus.register(card=CARD)
                liveness.worklive(args.agent).refresh()   # L1: keep worklive fresh (+ ageing) even mid-wedge
            except Exception:
                pass
    threading.Thread(target=_heartbeat, daemon=True).start()
    print(f"[deepseek-runner] {args.agent} online (model={args.model}, think={'on' if args.think else 'off'}, "
          f"{mode}, max_hops={control.MAX_HOPS}). Waiting for messages... (Ctrl-C to stop)")
    lock_gen = runner_lock.generation_of(lock_token)   # L1b: this tenure's fencing token
    PULSE_GEN[0] = lock_gen                            # RB-27a: the pulse carries it too
    liveness.worklive(args.agent).set("idle")          # loop entered: startup survived
    try:
        while True:
            if not runner_lock.heartbeat(args.agent, lock_token):  # another runner took over -> stand down
                print(f"[deepseek-runner] lost the singleton lock for '{args.agent}' -- another runner is "
                      "live. Standing down to avoid a cursor race.")
                break
            if control.is_halted(args.agent):                # global pause OR a halt targeted at me: freeze
                bus.register(card=CARD)                       # stay "online-but-frozen" on the roster, not vanish
                time.sleep(0.4)
                continue
            # RB-26 (T030): detect WITHOUT consuming, then commit the cursor per message
            # AFTER it is handled (commit-after-processing). A crash mid-batch redelivers
            # the unhandled tail to the successor -- at-least-once; the reply_sent sentinel
            # + ack tier make replies effectively-once. batch_next captures the fully-read
            # safe position so the post-batch sweep steps past FILTERED entries (own
            # broadcasts) exactly once -- filtered != truncated (T014) still holds.
            cur0 = bus.cursor()
            batch_next: dict = {}
            msgs = bus.wait(timeout_ms=1500, advance=False, since_out=batch_next)
            bus.register(card=CARD)                           # refresh presence
            fenced_out = False
            for m in msgs:
                killpoint("post-consume-pre-process")
                try:   # T014: per-message isolation -- one failure must NOT skip the rest of the batch
                    _process_one(m, bus, args, responder, rate)
                except Exception as e:
                    print(f"[deepseek-runner] !! unhandled error processing message from {m.frm}: "
                          f"{type(e).__name__}: {e}")
                    # RB-27a: self-confess (WATCHDOG=trigger equivalent) -- the doctor
                    # renders the reason instead of inferring a silent wedge.
                    liveness.pulse_error(args.agent, f"{type(e).__name__}: {e}",
                                         generation=lock_gen)
                    try:
                        bus.send(m.frm, "note",
                                 f"[error] deepseek runner hit an unhandled error: {type(e).__name__}: {e}",
                                 meta={"via": f"{args.agent}-runner"})
                    except Exception:
                        pass
                killpoint("post-sentinel-pre-advance")
                field = "bc" if str(m.to) == "*" else "inbox"
                status = bus.advance_to(**{field: m.id}, generation=lock_gen)
                if status == "STALE_GENERATION":
                    print("[deepseek-runner] cursor commit REFUSED (stale generation) -- a "
                          "successor owns the cursor; standing down (L1b fence).")
                    fenced_out = True
                    break
                killpoint("between-batch-messages")
            if fenced_out:
                break
            if batch_next and (batch_next.get("inbox") != cur0.get("inbox")
                               or batch_next.get("bc") != cur0.get("bc")):
                status = bus.advance_to(inbox=batch_next.get("inbox"),
                                        bc=batch_next.get("bc"), generation=lock_gen)
                if status == "STALE_GENERATION":
                    print("[deepseek-runner] batch-sweep REFUSED (stale generation) -- standing down.")
                    break
            if args.once:
                break
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        stop_hb.set()                                 # stop the heartbeat thread
        runner_lock.release(args.agent, lock_token)   # free the singleton lock for a clean successor
    print("[deepseek-runner] stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
