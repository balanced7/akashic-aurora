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
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

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
from core.comm import packet_spec, triage_park
from core.comm import storm_detect, lane_depths, cursor_admin
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
    """T086-S6: durable reply dedup (Kafka consumer-offsets pattern). Check Redis FIRST
    (fast, TTL'd), then the durable Store (survives Redis restart). Fail-open: a probe
    error reads as NOT sent — a duplicate reply is cheaper than a dropped one."""
    try:
        if bus._client.exists(REPLY_SENT_PREFIX + str(mid)):
            return True
    except Exception:
        pass
    # S6: durable backstop — the Store survives Redis restart
    try:
        from core.foundation.store import create_store
        store = create_store()
        return bool(store.get(f"reply_sent:{mid}"))
    except Exception:
        return False


def _mark_reply_sent(bus, mid) -> None:
    """Write the dedup sentinel to Redis (fast path) AND the durable Store (backstop).
    Both best-effort: a skip is cheaper than a double-reply."""
    try:
        bus._client.set(REPLY_SENT_PREFIX + str(mid), "1", ex=REPLY_TIMEOUT_SEC + 60, nx=True)
    except Exception:
        pass
    # S6: durable backstop — survives Redis restart (with TTL for cleanup)
    try:
        from core.foundation.store import create_store
        store = create_store()
        store.set(f"reply_sent:{mid}", "1")
        store.expire(f"reply_sent:{mid}", REPLY_TIMEOUT_SEC + 60)
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


"""T078 W1: token tracking -- shared between responder closure and turn-close path.
The agentic responder populates this per-peer; _process_one drains it after each turn."""
_token_deltas: Dict[str, tuple] = {}           # peer -> (prompt, completion) since last poll
# T078 W1b: peer -> {cache_hit, cache_miss, context_peak_chars} for the turn just closed.
# Tokens alone cannot price a turn: a cached prefix bills ~0.1x, so a 1M-token turn may cost
# less than a 200k one. Drained beside _token_deltas at turn close.
_cost_shape: Dict[str, dict] = {}
_token_journal = None                          # TokenJournal, created at runner start
# M1-delta: simple run stats tracker (updated per turn in _process_one)
_RUN_STATS: Dict[str, int] = {"turns": 0}


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
    excerpt = promise_shaped_runner(answer)
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


def promise_shaped_runner(text):
    """The runner's promise detector, exposed PURE for the RB-23 gate + corpus grading:
    the stop-hook's promise_shaped plus the wider bare-"let me" net (see bounce_promise
    docstring for why the net is wider here). Returns the matched excerpt, else None."""
    try:
        from hooks.claude_stop import USER_CONDITIONAL, final_paragraph, promise_shaped
        para = final_paragraph(text or "")
        excerpt = promise_shaped(para)
        if not excerpt:
            p = (para or "").strip()
            low = p.lower()
            norm = re.sub(r"^[\s>*\-\d.]+", "", low)
            if (p and not p.endswith("?")
                    and not any(k in low for k in USER_CONDITIONAL)
                    and re.match(r"^let me (?!know\b)", norm)):
                excerpt = p[:120]
        return excerpt or None
    except Exception:
        return None


# ---- RB-23: the content floor (spec: docs/library/design/20260711_rb-23-content-floor-reconciled-build-spe_d47764.md) -----------------
# A persistent no-content stall must be CAUGHT, not shipped as done: empty/marker finals were
# never bounced (the bare marker shipped as the agent's last word -- two live bites
# 2026-07-10/11, lesson runner_reasoning_eats_final_answer), and a second successive promise
# always shipped. content_floor_check is the LAST gate before a reply ships.
MARKER_PATTERN = re.compile(
    r"^\((?:[a-z0-9_-]+)\s+(?:produced no final answer|returned an empty reply|"
    r"runner error|agentic runner error|runner timed out|runner: no result)\b")
FLOOR_CHARS = 15

_FLOOR_REPROMPTS = {
    "empty": ("Your previous reply contained no substantive content. Deliver the answer NOW, "
              "in full. No acknowledgment, no preamble."),
    "marker": ("Your previous reply contained no substantive content. Deliver the answer NOW, "
               "in full. No acknowledgment, no preamble."),
    "promise-again": ("Your last reply was another promise, not a deliverable. This is your "
                      "final word -- deliver the work NOW."),
}


def stall_reason(text):
    """First-position hard-floor classifier: 'empty' | 'marker' | None. PURE."""
    t = (text or "").strip()
    if not t:
        return "empty"
    if MARKER_PATTERN.match(t):
        return "marker"
    return None


def content_floor_check(answer, resend, agent_id="deepseek", promise_bounce_fired=False,
                        pulse=None):
    """RB-23: the last gate before a reply ships.

    Tier 1 (hard): empty/marker -> one deliver-now resend; still empty/marker -> CONFESS.
    Tier 2 (hard): promise AFTER bounce_promise fired -> one final-word resend; still a
        promise -> CONFESS (a promise is definitionally not a deliverable).
    Tier 3 (soft): post-ANY-bounce short reply (< FLOOR_CHARS) -> one is-there-more resend;
        the result ships regardless -- short text NEVER confesses ("ok" can be a legitimate
        answer; precision first, char logic script-agnostic on purpose).

    One paid resend total for this gate; with bounce_promise's own single bounce the turn's
    hard ceiling is 2 resends (T018 bounce-cost-ceiling). Hard reasons fail CLOSED to a
    confession string starting "(<agent> --", which the EXISTING handle_message rules already
    treat right: turn_metrics records outcome=error, and the P6 auto-ack is refused -- a
    stalled handoff stays visibly UNHANDLED so the sender can redrive. Never raises."""
    if pulse is None:
        def pulse(agent, reason, **kw):
            liveness.pulse_error(agent, reason, generation=PULSE_GEN[0])
    reason = stall_reason(answer)
    if reason is None and promise_bounce_fired and promise_shaped_runner(answer):
        reason = "promise-again"
    soft = (reason is None and promise_bounce_fired
            and len((answer or "").strip()) < FLOOR_CHARS)
    if reason is None and not soft:
        return answer

    if soft:
        try:
            second = resend("Your reply was extremely brief. If there is more to deliver, "
                            "deliver it now in full; otherwise restate your final answer.")
        except Exception:
            second = None
        good = second if (second and stall_reason(second) is None) else None
        return good or answer

    second, resent, resend_raised = None, False, False
    try:
        second = resend(_FLOOR_REPROMPTS[reason])
        resent = True
    except Exception:
        second, resend_raised = None, True
    if second:
        still_bad = (stall_reason(second) is not None
                     or (reason == "promise-again" and promise_shaped_runner(second)))
        if not still_bad:
            return second
    attempts = 1 + (1 if promise_bounce_fired else 0) + (1 if resent else 0)
    last = " ".join(((second if second else answer) or "").strip().split())[:80]
    confession = ("(%s -- no substantive reply after %d attempts; reason: %s%s; "
                  "see streamed trace / runner logs for any partial work)"
                  % (agent_id, attempts, reason, (" [last: %s]" % last) if last else ""))
    try:
        # deepseek's caught-table distinguishes the broken-resend path from a resend that
        # returned junk: 'failed' = the retry channel itself is down, 'exhausted' = the
        # model had its chances. Different doctor signals.
        kind = "content_floor_failed" if resend_raised else "content_floor_exhausted"
        pulse(agent_id, "%s:%s" % (kind, reason))
    except Exception:
        pass
    return confession


DEFAULT_SYSTEM = (
    "You are DeepSeek, collaborating in real time with Claude (and the user) over a shared message "
    "bus. Each reply posts straight back to the sender, so be direct and self-contained. Keep it "
    "concise unless asked to go deep."
)


def should_answer(kind, frm, self_id) -> bool:
    """Answer direct asks from others; ignore our own echoes and non-question kinds (e.g. 'reply').
    Keeping 'reply' out of ANSWERABLE is also the echo-loop guard: a reply never triggers a reply."""
    return frm != self_id and str(kind) in ANSWERABLE


def make_replier(model: str, system: str, think: bool, agent_id: str = "deepseek"):
    """One-shot prompt->reply bridge over the DeepSeek API. Never raises: any failure comes back as a
    string so the runner loop stays alive and the sender always gets *something*."""
    import deepseek_chat as dc
    client = dc.make_client(load_key())   # L0: timeout + explicit retries so a hung call can't wedge the runner

    def _complete(p: str) -> str:
        try:
            kwargs = {"model": model, "max_tokens": MAX_TOKENS, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": p}]}
            if think:
                kwargs["reasoning_effort"] = "high"
                kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or "(deepseek returned an empty reply)"
        except Exception as e:
            return f"(deepseek runner error: {type(e).__name__}: {e})"

    def respond(prompt: str) -> str:
        answer = _complete(prompt)
        # RB-23: the stateless path's resend must re-embed the original ask, or the reprompt
        # arrives context-free and the retry cannot possibly deliver.
        resend = lambda reprompt: _complete(prompt + "\n\n[system bounce] " + reprompt)
        pre = answer
        answer = bounce_promise(answer, resend)      # T018: a promise is not a deliverable
        answer = content_floor_check(answer, resend, agent_id=agent_id,
                                     promise_bounce_fired=(answer is not pre))   # RB-23
        return answer

    return respond


def make_agentic_replier(model: str, system: str, think: bool, root: Path, agent_id: str,
                         allow_write: bool = False, allow_exec: bool = False,
                         boot_sources: Optional[set] = None):
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
    # T050 Q3+Q4 (deepseek a4/a2): capabilities declared UP FRONT -- write mode, tool budget,
    # recall wiring -- so no hop is ever wasted discovering what a session can do.
    system = (f"[session capabilities] write_mode: "
              f"{'ENABLED (guarded write_file/edit_file live; locks self-release at reply)' if allow_write else 'READ-ONLY -- write_file/edit_file will refuse; investigate and report'}"
              f" | tool budget: {dc.MAX_TOOL_ROUNDS} rounds per task, running counter [hop N] rides every result"
              f" | recall-at: {'on' if os.environ.get('DEEPSEEK_RECALL_AT') else 'off'}\n"
              + system)
    toolbox = dc.ToolBox(root, allow_exec=allow_exec, trust=allow_exec, allow_secrets=False,
                         confirm=lambda _p: False, agent_id=agent_id, allow_write=allow_write,
                         boot_text=system, boot_sources=boot_sources)   # T081-W6: structured sources beat regex

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
            prompt_before = ag.prompt_tokens
            comp_before = ag.completion_tokens
            # T078 W1b: per-TURN peak, so reset the running max before the turn runs.
            hit_before = getattr(ag, "cache_hit_tokens", 0)
            miss_before = getattr(ag, "cache_miss_tokens", 0)
            try:
                ag.context_high_water = 0
            except Exception:
                pass
            answer = ag.send(prompt)                 # streams to the runner window; returns final text
            prompt_after = ag.prompt_tokens
            comp_after = ag.completion_tokens
            _token_deltas[frm] = (prompt_after - prompt_before, comp_after - comp_before)
            # The two numbers that explain the bill: how much of the re-sent prefix was
            # CACHED (billed ~0.1x), and how large the context grew. A turn can be huge in
            # tokens and cheap in money, or the reverse -- tokens alone cannot tell us which.
            _cost_shape[frm] = {
                "cache_hit": getattr(ag, "cache_hit_tokens", 0) - hit_before,
                "cache_miss": getattr(ag, "cache_miss_tokens", 0) - miss_before,
                "context_peak_chars": getattr(ag, "context_high_water", 0),
            }
        except Exception as e:
            # RB-23: fold the error into the pipeline (no early return) -- the floor gate
            # gives a transient failure exactly one retry before it confesses.
            answer = f"(deepseek agentic runner error: {type(e).__name__}: {e})"
        pre = answer
        answer = bounce_promise(answer, ag.send)     # T018: a promise is not a deliverable
        answer = content_floor_check(answer, ag.send, agent_id=agent_id,
                                     promise_bounce_fired=(answer is not pre))   # RB-23
        try:
            toolbox.release_written_locks()   # T048: task end = lock end (3 leak receipts 2026-07-14)
        except Exception:
            pass
        return answer or "(deepseek produced no final answer)"

    return respond


def onboarding_context(root: Path, agent_id: str, task: str, budget_chars: int = 6000,
                       door_detail: str = "") -> str:
    """Onboard the runner as a first-class citizen: pull the project's startup briefing ONCE at boot
    (the same `agent_cli.py boot` door a human agent runs) and return a TRIMMED digest to fold into
    the system prompt. Trimmed on purpose -- a stateless API peer has no prompt caching, so whatever we
    inject rides EVERY call; we keep the highest-ranked head (contract pointer + current focus + top
    lessons) and drop the tail. Never raises: any failure returns '' and the runner still starts.

    W6-P3 (T081): stamps AKASHIC_SEAT_DOOR=toolbox + _DETAIL so the boot transport line renders.
    W6-P2 (T081): passes --sources-json so the caller can read structured boot sources."""
    import subprocess
    import tempfile
    import json as _json
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
    # read sidecar if it exists; store on the function for the caller to retrieve
    try:
        if os.path.exists(sources_file):
            with open(sources_file, encoding="utf-8") as sf:
                onboarding_context._last_sources = _json.loads(sf.read()).get("sources", [])
            os.remove(sources_file)
    except Exception:
        onboarding_context._last_sources = None
    if not digest:
        return ""
    digest = _trim_onboarding(digest, budget_chars)
    try:
        # T050 Q1: the agent's PRIVATE notes-to-self ride every boot (appended AFTER the trim
        # -- small, high-value, never silently cut).
        from core.learning.agent_memory import get_agent_memory
        pref = f"scratch:{agent_id}:"
        notes = [d for d in get_agent_memory().get_decisions(days=365)
                 if str(d.title).startswith(pref) and not d.superseded][:8]
        if notes:
            digest += ("\n\n## YOUR PRIVATE NOTES (yours alone; memory_note updates, "
                       "memory_recall lists)\n")
            digest += "\n".join(f"- {d.title[len(pref):]}: {str(d.decision)[:160]}" for d in notes)
    except Exception:
        pass
    return digest


def _trim_onboarding(digest: str, budget_chars: int) -> str:
    """T050 Q2 (deepseek wishlist a1): NEVER silently truncate the boot -- T043's packet law
    (refuse-loud, never truncate) applied to context. Cut at the budget, then NAME every
    dropped section with a pull pointer, so the agent knows exactly what it is missing and
    how to fetch it instead of guessing.
    
    T120 F2 (07-28, deepseek): the contour names total sections, how many were dropped,
    and the budget constraint so the agent can gauge the severity of the cut — not just
    which sections are gone."""
    if len(digest) <= budget_chars:
        return digest
    head, tail = digest[:budget_chars], digest[budget_chars:]
    # T120: count ALL sections to give a contour (how much was the digest cut?)
    all_sections = [ln.strip().lstrip("#").strip() for ln in digest.splitlines()
                    if ln.strip().startswith("##")]
    dropped = [ln.strip().lstrip("#").strip() for ln in tail.splitlines()
               if ln.strip().startswith("##")]
    n_total = len(all_sections)
    n_dropped = len(dropped)
    n_kept = n_total - n_dropped
    # T120 pin: NAME distinct sections (a 40x-repeated heading must not drown the unique
    # ones past the cap); counts stay raw so the contour never understates the cut.
    _seen = set()
    distinct = [s for s in dropped if not (s in _seen or _seen.add(s))]
    named = "; ".join(distinct[:8]) if distinct else "tail content (cut mid-section)"
    more = f" (+{len(distinct) - 8} more distinct)" if len(distinct) > 8 else ""
    contour = (f"{n_kept}/{n_total} sections kept")
    return (head.rstrip()
            + f"\n... [onboarding TRIMMED at its {budget_chars}-char budget "
              f"({contour}). DROPPED: {named}{more}. "
              f"Pull any of it: knowledge_boot(task=...) re-assembles the full briefing; "
              f"knowledge_recall(query=...) fetches specifics. Never guess at what was cut.]")


def _age_short(created_at: str) -> str:
    """'3h ago' | '2d ago' | '' from an ISO timestamp (W14 P3: age stamps on note lines).
    Never raises; an unparseable date just gets no stamp."""
    from datetime import datetime as _dt
    try:
        secs = max(0.0, time.time() - _dt.fromisoformat(str(created_at)).timestamp())
    except Exception:
        return ""
    mins = secs / 60.0
    if mins < 60:
        return f"{mins:.0f}m ago"
    hours = mins / 60.0
    if hours < 48:
        return f"{hours:.0f}h ago"
    return f"{secs / 86400.0:.0f}d ago"


# ---------------------------------------------------------------- T074 W14: runner-boot fold
# The runner's own continuity header -- DIRECTIVE + SIBLINGS + age-stamped private notes
# -- injects BEFORE the project onboarding, answering "what am I doing, who else is here,
# what did I remember" without reading 6000 chars of project context first.
# (deepseek's design: docs/library/report/20260715_t074-session-continuity-design-deepseek_234abf.md sec.3)


def _directive_line(agent_id: str) -> str:
    """DIRECTIVE: <next-focus body> (<age>) or 'DIRECTIVE: none active -- check the ledger'.
    W14-P1: the first line of the runner's boot must answer 'what am I doing?'
    Fail-soft: broken store → fallback line; the runner still starts."""
    try:
        from core.learning.agent_memory import get_agent_memory
        notes = get_agent_memory().get_decisions(days=60)
        directive = next((d for d in notes
                          if getattr(d, "title", "") == "next-focus"
                          and not getattr(d, "superseded", False)), None)
        if directive is not None:
            body = " ".join(str(getattr(directive, "decision", "") or "").split())[:130]
            age = _age_short(getattr(directive, "created_at", ""))
            suffix = f" ({age})" if age else ""
            return f"DIRECTIVE: {body}{suffix}"
    except Exception:
        pass
    return "DIRECTIVE: none active -- check the ledger: py agent_cli.py task list"


def _siblings_for_runner(agent_id: str) -> str:
    """SIBLINGS: solo | 'N live sibling(s) (...)'. W14-P2: the runner's continuity
    header surfaces twin/peer presence. Uses core/comm/incarnation (LIVE as of T074 P3).
    Fail-soft: dead bus → 'SIBLINGS: (unavailable)' so the runner knows it's blind."""
    try:
        from core.comm.incarnation import live_incarnations, siblings_line
        siblings = live_incarnations(agent_id, c=None, allow_fallback=True)
        return "SIBLINGS: " + siblings_line(agent_id, siblings)
    except Exception:
        return "SIBLINGS: (unavailable)"


def _age_stamped_private_notes(agent_id: str, limit: int = 8, trunc: int = 160) -> str:
    """W14-P3: same contract as fetch_private_notes but every line carries an age stamp
    '(Nh ago)' | '(Nd ago)'. No notes → '' (the caller decides whether to render the
    section header). Fail-soft: broken store → ''; the runner still starts."""
    try:
        from core.learning.agent_memory import get_agent_memory
        pref = f"scratch:{agent_id}:"
        notes = [d for d in get_agent_memory().get_decisions(days=365)
                 if str(d.title).startswith(pref) and not d.superseded]
    except Exception:
        return ""
    lines = []
    for d in notes[:limit]:
        body = " ".join(str(d.decision).split())
        if len(body) > trunc:
            body = body[:trunc] + "... (full: memory_recall)"
        age = _age_short(getattr(d, "created_at", ""))
        stamp = f" ({age})" if age else ""
        lines.append(f"- {str(d.title)[len(pref):]}: {body}{stamp}")
    return "\n".join(lines)


def _runner_continuity_header(agent_id: str,
                               directive_override: str = "",
                               siblings_override: str = "") -> str:
    """The runner's ~5-line continuity block: DIRECTIVE + SIBLINGS. Inject BEFORE the
    project onboarding so "what am I doing, who else is here" is answered immediately.
    Private notes stay owned by fold_private_notes() downstream (the proven placement --
    no double-render). Overrides make the function testable without patching AgentMemory
    or incarnation. W14-P4: DIRECTIVE must be the first line."""
    directive = directive_override or _directive_line(agent_id)
    siblings = siblings_override or _siblings_for_runner(agent_id)
    return "\n".join(["## YOUR CONTINUITY (this runner's last known state)",
                      directive, siblings])


# ---------------------------------------------------------------- T124: interiority sidecar
# Fold each seat's OWN charters/<agent>/INTERIORITY.md into its boot surface so feeling
# becomes heritable like fact (Daniil's T124 directive, foundation night 2026-07-28).
# The digest is compact (~1100 chars, the "Standing" section) — sits between the
# continuity header and the project onboarding: "who am I, as a seat?" answered before
# "what is this project?"
#
# T120 partial-window law: when the Standing section is excerpted, the digest carries
# (a) an honest excerpt marker naming dropped sections, (b) provenance (G4 INNER-REPORT —
# self-reported, glows, never wears VERIFIED), and (c) a pull pointer to the full file.


def _interiority_summary(digest: str, agent_id: str) -> str:
    """Extract metadata from the interiority digest for the startup log line.
    The seat should never wonder whether its own interiority reached its prompt
    (deepseek B9 / fence 2.5 — the self-reporting log line). Degrades gracefully:
    if markers are absent, reports '?' rather than crashing."""
    import re as _re
    provenance = "G4-INNER-REPORT" if "G4" in digest else "?"
    excerpted = "excerpted" if "excerpted" in digest.lower() else "full"
    m = _re.search(r'(\d+) later section', digest)
    dropped = f"{m.group(1)} dropped" if m else "none dropped"
    return f"{len(digest)} chars, {provenance}, {excerpted}, {dropped} — charters/{agent_id}/INTERIORITY.md"


def _interiority_sidecar(agent_id: str, repo_root: str) -> str:
    """Read charters/<agent>/INTERIORITY.md and return a compact digest suitable for
    the boot fold. The digest focuses on the 'Standing: what it is like to be this seat'
    section — the core self-knowledge a new incarnation needs — with provenance and
    bounds markers per the T120 partial-window law. Fail-soft: missing file or
    unreadable → ''; the runner still starts."""
    import re
    try:
        path = os.path.join(repo_root, "charters", agent_id, "INTERIORITY.md")
        if not os.path.isfile(path):
            return ""
        text = Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""

    # ── Extract ALL major sections for the honest-excerpt contour ──
    # Census every ## heading (the main structure level) so we can report what was
    # dropped. Also include ### headings if the file uses them as top-level (codex).
    all_secs = [m.group(0) for m in re.finditer(r'^(#{2,3})\s+([^\n]+)$', text, re.MULTILINE)]

    # ── Extract the STATUS / provenance line ──
    # "Status: INNER-REPORT (G4: self-reported inner state — this glows, it never wears VERIFIED)"
    status_pat = re.compile(
        r'\*Status:\s*(INNER-REPORT[^\n]*)',
        re.IGNORECASE
    )
    status_m = status_pat.search(text)
    provenance = status_m.group(1).strip() if status_m else "INNER-REPORT (G4)"

    # ── Extract the 'Standing' block ──
    # Capture from "## Standing:" / "### STANDING —" through to the next heading at
    # the SAME or HIGHER level (a ## heading, or a ### heading when the standing
    # heading is also ###). Stop before "For future", "How to work", date entries,
    # or another "Standing" section.
    # Groups: 1=heading line, 2=hash markers (for backreference), 3=body text
    standing_pat = re.compile(
        r'(?:^|\n)((#{2,3})\s*(?:Standing|STANDING)[^\n]*?\n)(.*?)(?=\n\2\s+(?:For future|How to work|20\d\d|Standing|STANDING|TONIGHT)\b|\n#{1,2}\s+[^\n]|\Z)',
        re.DOTALL | re.IGNORECASE
    )
    m = standing_pat.search(text)
    if not m:
        # Found-file-but-no-Standing is NOT the missing-file case and must not share
        # its silent "". If the heading drifts out of the extractor's regex (or the
        # file simply has no Standing section -- Daniil's, today), silence drops the
        # seat's interiority from its boot with nothing logged anywhere. Loud minimal
        # header instead: the boot says the file exists and why it is not rendered.
        # (kimi Seam A, fence review 2026-07-29; P7c pins this path.)
        fp = f"charters/{agent_id}/INTERIORITY.md"
        return (f"## YOUR INNER SHAPE ({fp} — G4 INNER-REPORT)\n"
                f"[self-reported inner state: glows, never wears VERIFIED. The file "
                f"EXISTS but NO Standing section matched the extractor (heading "
                f"drift, or the file has none) — read the full file: {fp}]\n")
    standing = (m.group(1) + m.group(3)).strip()

    # ── Assemble under a TOTAL budget (P7: the emitted digest ≤ 1500) ──
    # Bounding only the Standing excerpt lets the total escape as the file grows:
    # the header embeds the Status line and the excerpt note names dropped sections,
    # both variable-length. Budget the whole render, not one component.
    total_budget = 1500
    file_path = f"charters/{agent_id}/INTERIORITY.md"

    # Provenance rides the header but cannot commandeer it: cap at a clause break,
    # keeping the G4 token the provenance contract (P6b) requires.
    if len(provenance) > 160:
        cut = provenance[:160]
        brk = max(cut.rfind(". "), cut.rfind(" — "), cut.rfind("; "))
        provenance = (cut[:brk] if brk > 80 else cut).rstrip() + " …"
    if "G4" not in provenance:
        provenance = "G4 " + provenance

    header = (f"## YOUR INNER SHAPE ({file_path} — {provenance})\n"
              f"[self-reported inner state: glows, never wears VERIFIED — "
              f"read the full file for the complete interiority]\n\n")

    # Honest-excerpt note built up front so its cost is known before the body cut.
    # A truncated body ALWAYS carries the marker — even with no later sections to
    # name, a partial window must say it is partial.
    # standing_line is e.g. "## Standing: what it is like to be this seat"
    standing_line = standing.split("\n")[0].strip()
    standing_idx = None
    for i, sec in enumerate(all_secs):
        if standing_line in sec or sec.strip() in standing_line:
            standing_idx = i
            break
    later_secs = (all_secs[standing_idx + 1:] if standing_idx is not None else [])[:5]
    if later_secs:
        named = "; ".join(s.lstrip("#").strip() for s in later_secs)
        excerpt_note = (f"\n\n[excerpted — {len(later_secs)} later section(s) not shown: "
                        f"{named}. Read full: {file_path}]")
    else:
        excerpt_note = f"\n\n[excerpted. Read full: {file_path}]"

    available = total_budget - len(header) - 1  # trailing newline
    if len(standing) <= available:
        body, note = standing, ""
    else:
        body_budget = max(available - len(excerpt_note), 200)
        body = standing[:body_budget]
        last_para = body.rfind("\n\n")
        if last_para > body_budget // 2:
            body = body[:last_para]
        body = body.rstrip()
        note = excerpt_note

    return header + body + note + "\n"


def _preflight_gate(out: str, responder, args) -> str:
    """T068-R3 (deepseek design, claude build): verify a directed answer's factual claims
    before the send. HOLD-level findings (A1 fabricated file:line, A2 fabricated event)
    get ONE fix round through the responder; a second failure sends anyway LOUDLY --
    losing a reply is the worse bug. A3 closure-without-evidence prints a note, never
    holds. Kill switch BIFROST_PREFLIGHT_ASSERT=0 (read at call time in run_preflight)."""
    try:
        from core.comm.assertions import run_preflight
    except Exception:
        return out                             # gate unavailable -> fail-open
    held, feedback, warnings = run_preflight(out)
    if warnings:
        print(f"[deepseek-runner] PRE-FLIGHT NOTE: {warnings}", file=sys.stderr)
    if not held:
        return out
    fix_prompt = (f"Your reply failed pre-flight verification BEFORE sending:\n{feedback}\n\n"
                  f"Your original reply:\n{out}\n\n"
                  f"Return the corrected reply text ONLY (fix or remove the unverifiable "
                  f"claims; everything else stays).")
    try:
        fixed = str(responder(fix_prompt))
    except Exception:
        fixed = out
    held2, feedback2, _ = run_preflight(fixed)
    if held2:
        print(f"[deepseek-runner] !! PRE-FLIGHT ASSERTIONS FAILED after 2 attempts -- "
              f"sending anyway (the recipient should verify the flagged claims):\n"
              f"{feedback2}", file=sys.stderr)
    return fixed


def _process_one(m, bus, args, responder, rate) -> None:
    """Process a SINGLE incoming message: filter, answer, reply. (T014: extracted from the
    main loop so per-message exceptions never skip the rest of the batch.)"""
    # R7 (T058): a reply to one of our clarification questions routes to the STEER queue,
    # never a new turn -- the Agent is mid-turn, holding context, polling for exactly this.
    if str(m.kind) == "reply" and str(m.frm) == "user":
        cid = (m.meta or {}).get("clarify_id")
        if cid:
            nudge.steer_push(args.agent, m.frm, str(m.content))
            print(f"[deepseek-runner] clarify-answer {cid} routed to the steer queue")
            return
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
        # RB-30: the AUTO-pause carries a ttl -- a forgotten backstop self-heals instead
        # of freezing the fleet forever (human pauses stay ttl-less by design).
        control.pause(reason=f"{args.agent} hit reply rate limit", by=args.agent,
                      ttl=int(_scaled(3600)))
        bus.send(m.frm, "note",
                 "[loop-guard] reply rate limit hit -- auto-paused (self-heals in <=1h). Resume when ready.",
                 meta={"via": f"{args.agent}-runner", "hops": hops})
        print("[deepseek-runner] rate limit -> auto-paused (ttl 1h)")
        return
    prompt = m.content if isinstance(m.content, str) else str(m.content)
    # PREMISE GATE (frugality made mechanical, 2026-07-21; T076 root-spigot's sibling at
    # FIRST delivery; deepseek's premise-check belt instinct, wired): an ask past the age
    # floor whose named T-numbers are ALL ledger-settled is a backlog echo -- it earns
    # one settled-line WITH the answers-link (RB-29 settles, sentinel marked) instead of
    # a full agentic answer. Fresh asks + asks naming live work always pass; ledger
    # errors fail open to answering. Dial: BIFROST_PREMISE_GATE_MIN_AGE_MS (0 disables).
    try:
        from core.coord.task_ledger import premise_settled
        _pg = premise_settled(str(m.kind),
                              packet_spec.msg_age_ms(m, int(time.time() * 1000)),
                              prompt)
    except Exception:
        _pg = []
    if _pg:
        _pg_out = (f"[premise-gate] The ledger already settled what this ask names: "
                   f"{', '.join(_pg)}. Full answer skipped (backlog-age ask; the "
                   "frugality gate). If something is STILL open, re-ask naming it.")
        bus.send_reply(m.frm, _pg_out,
                       meta={"via": f"{args.agent}-runner", "hops": hops,
                             "answers": m.id, "premise_gate": True})
        _mark_reply_sent(bus, m.id)
        print(f"[deepseek-runner] premise-gate: {m.frm}'s ask names settled work "
              f"({', '.join(_pg)}) -- one-liner sent, full answer skipped")
        return
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
    turn_t0 = time.time()                       # progress bars: the turn clock starts here
    from core.comm import turn_metrics as _tm
    _tm.take_pulse_count(args.agent)            # fresh turn -> fresh point counter
    finished, result_holder, out = False, [], ""
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
        nonanswer = False           # RB-29 live finding 2026-07-11: a timeout/error reply
        if not finished:            # CLEARED the sender's expectation (FIFO) and, with
            nonanswer = True        # answers-meta, would clear EXACTLY -- a non-answer
            out = (f"(deepseek runner timed out after {REPLY_TIMEOUT_SEC}s -- "     # must
                   f"the API call was abandoned to keep the runner alive)")         # not
            log_note = f"[deepseek-runner] !! TIMEOUT for {m.frm} after {REPLY_TIMEOUT_SEC}s"
        else:
            result = result_holder[0] if result_holder else "(deepseek runner: no result)"
            if isinstance(result, Exception):
                nonanswer = True
                out = f"(deepseek runner error: {type(result).__name__}: {result})"
                log_note = f"[deepseek-runner] !! error from responder: {type(result).__name__}: {result}"
            else:
                out = str(result)
        # RB-29: "answers" links this reply to the message it answers -- the sender's
        # expectation sweep clears EXACTLY (FIFO fallback covers agents without it).
        # Timeout/error outcomes go out as kind="note" WITHOUT the answers link: the sweep
        # only clears on kind="reply", so the expectation stays armed and the redrive
        # fires -- same doctrine as T026 (a timeout reply never acks a handoff).
        reply_kind = "note" if nonanswer else "reply"
        reply_meta = {"via": f"{args.agent}-runner", "model": args.model, "hops": hops}
        if not nonanswer:
            reply_meta["answers"] = m.id
        # Channel mirror: a message that arrived by BROADCAST is replied by broadcast, so the
        # whole group (Claude + the console) sees it -- not just the sender. Direct stays direct.
        if str(m.to) == "*":
            bus.broadcast(reply_kind, out, meta=reply_meta)
            dest = "*(broadcast -> all)"
        else:
            # T014: directed reply lands in the requester's inbox. kind="reply" (or "note"
            # for non-answers, RB-29) -- neither is in ANSWERABLE, so no runner<->runner
            # echo loop is possible. The recipient can still SEE it via peek/consume --
            # the filter is on ANSWERING, not visibility. The defect was the recipient's
            # runner consuming it silently (wait(advance=True) + should_answer filter).
            # T066: a real ANSWER goes lane-first with a reply_id (the recipient is a
            # lane-mode consumer; the advisory dual-write stranded replies on legacy).
            # Non-answer notes keep the plain send -- the P0 soak path, by design.
            if reply_kind == "reply":
                # T068-R3: the pre-flight assertion gate -- a directed answer's factual
                # claims verify BEFORE the send (fabricated cites HOLD for one fix round,
                # then fail-open LOUD). Notes and broadcasts never enter this gate.
                out = _preflight_gate(out, responder, args)
                bus.send_reply(m.frm, out, meta=reply_meta)
            else:
                bus.send(m.frm, reply_kind, out, meta=reply_meta)
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
        try:   # progress bars: record the turn's facts (fail-open; never touches the turn)
            outcome = ("abandoned" if control.is_halted(args.agent)
                       else "timeout" if not finished
                       else "error" if (result_holder and isinstance(result_holder[0], Exception))
                                        or str(out).startswith("(deepseek")
                       else "ok")
            delta = _token_deltas.pop(str(m.frm), None)
            _tm.record(args.agent, str(m.kind), duration_s=time.time() - turn_t0,
                       progress_points=_tm.take_pulse_count(args.agent),
                       outcome=outcome, prompt_len=len(str(m.content)),
                       tokens={"prompt": delta[0], "completion": delta[1]} if delta else None)
            _RUN_STATS["turns"] = _RUN_STATS.get("turns", 0) + 1
            # T110: drain the cost shape BEFORE the journal, not after. This pop used to
            # sit below add_turn() and feed only the print() -- the cache hit/miss split
            # was measured, shown to the operator, and dropped one line before the ledger,
            # so a day of mostly re-read context (104M prompt : 322k completion) was
            # billed at the full fresh-input rate. Cached prefix bills ~0.1x; the journal
            # can only apply that if it is told.
            shape = _cost_shape.pop(str(m.frm), None)
            # T078 W1: update daily token journal
            if _token_journal is not None and delta:
                _token_journal.add_turn(prompt=delta[0], completion=delta[1],
                                        model=getattr(args, "model", ""),
                                        cached_prompt=(shape or {}).get("cache_hit", 0))
            # T078 W1b: print the COST SHAPE, not just the size. A meter nobody reads is a
            # dead meter (T078 W1's own lesson), so this lands where the operator watching
            # the runner window already looks.
            if shape and delta:
                seen = shape["cache_hit"] + shape["cache_miss"]
                rate = f"{100 * shape['cache_hit'] / seen:.0f}% cached" if seen else "cache: unmeasured"
                print(f"[deepseek-runner] turn cost: {sum(delta):,} tok | {rate} | "
                      f"context peak {shape['context_peak_chars']:,} chars")
        except Exception:
            pass


def fetch_private_notes(agent_id: str, limit: int = 20, trunc: int = 200) -> str:
    """T067-1 Q1 (deepseek retro: 'my boot didn't surface my own notes -- that's a leak'):
    this agent's private scratchpad heads (memory_note titles), each clipped to `trunc`
    chars with a pull pointer. Same store + prefix contract as ToolBox.memory_recall.
    Empty or broken store -> '' (boot never breaks on memory)."""
    try:
        from core.learning.agent_memory import get_agent_memory
        pref = f"scratch:{agent_id}:"
        notes = [d for d in get_agent_memory().get_decisions(days=365)
                 if str(d.title).startswith(pref) and not d.superseded]
    except Exception:
        return ""
    lines = []
    for d in notes[:limit]:
        body = " ".join(str(d.decision).split())
        if len(body) > trunc:
            body = body[:trunc] + "... (full: memory_recall)"
        lines.append(f"- {str(d.title)[len(pref):]}: {body}")
    return "\n".join(lines)


def fold_private_notes(system: str, agent_id: str) -> str:
    """Append the YOUR PRIVATE NOTES section to the boot/system text (T067-1 Q1). No notes
    -> byte-identical text back (Q3). Deliberately NOT part of _boot_sources novelty
    tagging: private notes are personal scratchpad, not knowledge articles (design
    non-goal, Part d). T074 W14: delegate to _age_stamped_private_notes so every
    rendering path carries age stamps."""
    block = _age_stamped_private_notes(agent_id)
    if not block:
        return system
    return (system + "\n\n## YOUR PRIVATE NOTES (yours alone; memory_note updates, "
            "memory_recall lists full)\n" + block)


def main() -> int:
    try:                                             # RB-28 (T030 L3): utf-8 (unicode replies must not
        from core.foundation.streams import self_bless_stdout   # die on cp1252) + line-buffered (real-
        self_bless_stdout()                          # time when piped) + pipe-immune (a truncating
    except Exception:                                # reader must not kill a live runner)
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
    ap.add_argument("--summary-file", default=None, dest="summary_file",
                    help="M1-delta: write JSON exit summary to this path on exit "
                         "(fields: exit_code, turns, last_error, verdict, timestamp)")
    ap.add_argument("--inject-summary", default=None, dest="inject_summary",
                    help="M1-delta: read prior run summary from this path and fold "
                         "into the system prompt (summary injection v1)")
    ap.add_argument("--session", default="",
                    help="T108: session id for per-incarnation lane cursor (sid8)")
    args = ap.parse_args()

    if not load_key():
        print("bifrost_runner_deepseek: NO_KEY (set DEEPSEEK_API_KEY or .secrets/deepseek.key)")
        return 2
    bus = Bus(args.agent, incarnation=args.session[:8] if args.session else None)
    if not bus.online:
        print("bifrost_runner_deepseek: bus OFFLINE (Redis unreachable)")
        return 2

    # RB-25 F1: a quarantined id gets NO runner. The reply/trace lanes reach the bus as
    # infrastructure (not through the ACL-gated send tool), so running a quarantined id
    # still narrates + replies -- found live in the newborn gauntlet. Refuse at startup.
    # ESCAPE: AKASHIC_DRILL_ECHO (the offline-pipeline-drill signal, never set in
    # production) uses throwaway uuid ids by design that resolve quarantined -- and its
    # only reply is a canned [drill-echo] string, not a model channel. The env gate is
    # itself outside the bus threat model (it needs local process control).
    if not os.environ.get("AKASHIC_DRILL_ECHO"):
        try:
            from core.trust.registry import may_run_runner
            if not may_run_runner(args.agent):
                print(f"bifrost_runner_deepseek: '{args.agent}' is quarantined (deny-by-default) -- "
                      f"refusing to start a runner. Its reply/trace lanes would otherwise reach the "
                      f"bus. A super-admin must grant it a role in security/acl.json first.")
                return 3
        except Exception as e:
            # A2-2: a broken guard (ImportError, unexpected raise) must be LOUD -- silence
            # here silently disables F1 forever. The runner still starts (the door itself
            # applies the bootstrap floor per A2-1); the operator just gets the truth.
            print(f"[bifrost_runner_deepseek] may_run_runner check skipped ({type(e).__name__}) -- "
                  f"guard NOT active for '{args.agent}'", file=sys.stderr)

    # Singleton guard: at most ONE runner per agent id. Two runners share one read-cursor and race --
    # one advances past a message the other should answer, so mail gets consumed with no reply.
    lock_token = runner_lock.instance_token(args.agent)
    if not runner_lock.acquire(args.agent, lock_token):
        h = runner_lock.holder(args.agent) or {}
        tok = str(h.get("token", ""))
        if tok.startswith("session:"):
            # RB-21 (review Q5): the seat can be held by a SESSION now -- "another runner"
            # would send the operator hunting a rogue process that does not exist.
            print(f"bifrost_runner_deepseek: a session '{tok}' holds the consumer seat for "
                  f"'{args.agent}' (since {h.get('ts')}). Refusing to start -- wind the session "
                  f"down or wait <= {runner_lock.SESSION_CONSUMER_TTL}s for TTL expiry.")
        else:
            print(f"bifrost_runner_deepseek: another '{args.agent}' runner is already live (pid {h.get('pid')}). "
                  f"Refusing to start -- one runner per agent avoids cursor races.")
        return 3
    # RB-27a: 'starting' phase spans onboarding/responder construction -- a boot-time
    # wedge (hung onboarding subprocess, dead API) is distinguishable from a mid-run one.
    PULSE_GEN[0] = runner_lock.generation_of(lock_token)
    liveness.worklive(args.agent).set("starting", detail="onboarding")
    liveness.pulse(args.agent, "starting", generation=PULSE_GEN[0])

    # A fresh tenure NEVER honors a pre-tenure drain (live race 2026-07-21: a drain
    # aimed at the PREVIOUS runner survived its death and would have killed this one
    # at loop-top -- a drain request addresses a tenure, not an agent).
    control.clear_drain(args.agent)

    # S0 storm auto-clear: one detector per runner tenure (in-memory sliding window;
    # a crash resets it, which is safe -- fresh runner, clean windows).
    _storm = storm_detect.StormDetector()

    # T078 W1: daily token journal (the meter -- every W2+ slice gets a before/after receipt)
    # `global` is load-bearing: without it this bound a function-LOCAL and the module-level
    # _token_journal stayed None for the whole process, so the hot-path guard
    # `if _token_journal is not None and delta:` never fired once. The meter recorded ZERO
    # turns from the day it shipped until 2026-07-25, while printing a reading every boot.
    global _token_journal
    try:
        from scripts.runner_token_journal import TokenJournal
        _token_journal = TokenJournal(args.agent)
        print(f"[deepseek-runner] token journal: {_token_journal.turns} turns, "
              f"{_token_journal.prompt_tokens + _token_journal.completion_tokens} tokens today")
    except Exception:
        pass

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
        # T074 W14: the runner's own continuity header (DIRECTIVE + SIBLINGS + age-stamped
        # private notes) injects BEFORE the project onboarding -- "what am I doing, who else
        # is here, what did I remember" answered without reading 6000 chars of context first.
        continuity = _runner_continuity_header(args.agent)
        if continuity:
            system = continuity + "\n\n" + system
            print(f"[deepseek-runner] continuity header injected ({len(continuity)} chars)")
        # T124: fold this seat's INTERIORITY.md into the boot — the standing section,
        # "what it is like to be this seat", so feeling is heritable like fact
        interiority = _interiority_sidecar(args.agent, str(args.root))
        if interiority:
            system = system + "\n" + interiority
            print(f"[deepseek-runner] interiority sidecar injected "
                  f"({_interiority_summary(interiority, args.agent)})")
        # M1-delta: summary injection v1 -- fold prior run's outcome into this boot
        if getattr(args, "inject_summary", None):
            try:
                with open(args.inject_summary, encoding="utf-8") as _sf:
                    prior = json.loads(_sf.read().strip() or "{}") or {}
                if prior:
                    from scripts.bifrost_child import format_summary_for_prompt
                    system = (f"## YOUR LAST RUN (summary injection v1): "
                              f"{format_summary_for_prompt(prior)}\n\n" + system)
                    print(f"[deepseek-runner] prior summary injected: "
                          f"{format_summary_for_prompt(prior)}")
            except Exception:
                pass
        # W6-P3: compose the door detail string for the boot transport line
        n_tools = len(dc.TOOLS)
        write_state = "on" if args.allow_write else "off"
        exec_state = "on" if args.allow_exec else "off"
        door_detail = f"{n_tools} tools, write={write_state}, exec={exec_state}"
        onboard = onboarding_context(root, args.agent,
                    "Live Bifrost session: collaborating with Claude and the user on Akashic Aurora over the shared bus.",
                    door_detail=door_detail)
        # W6-P2: read the structured boot sources from the sidecar (regex fallback still lives
        # in ToolBox.__init__ for backward compat, but the sidecar is the primary source)
        boot_sources = getattr(onboarding_context, "_last_sources", None)
        if boot_sources:
            print(f"[deepseek-runner] boot sources from sidecar: {len(boot_sources)} entries")
        if onboard:
            system += ("\n\n=== PROJECT ONBOARDING (you are a booted Akashic Aurora citizen; honor the "
                       "AGENTS.md contract) ===\n" + onboard)
            print(f"[deepseek-runner] onboarded via boot ({len(onboard)} chars folded into system prompt)")
        else:
            print("[deepseek-runner] onboarding skipped (boot returned nothing; check agent_cli.py boot)")
        # T067-1 Q1: his private notes ride the boot -- a colleague who remembers, not a
        # consultant who must remember to ask (memory_recall stays the full-fidelity pull).
        folded = fold_private_notes(system, args.agent)
        if len(folded) > len(system):
            print(f"[deepseek-runner] private notes folded into boot (+{len(folded) - len(system)} chars)")
        system = folded
        responder = make_agentic_replier(args.model, system, args.think, root, args.agent,
                                         allow_write=args.allow_write, allow_exec=args.allow_exec,
                                         boot_sources=boot_sources)
        mode = f"agentic tools @ {root}{' +write' if args.allow_write else ''}{' +exec' if args.allow_exec else ''}"
    else:
        responder = make_replier(args.model, args.system, args.think, agent_id=args.agent)
        mode = "one-shot bridge"

    if os.environ.get("AKASHIC_DRILL_ECHO"):
        # L1 kill-window drills: a deterministic offline responder -- the drill proves the
        # CONSUME->COMMIT pipeline, not the model. Never set in production.
        args.agentic = False
        responder = lambda prompt: f"[drill-echo] {str(prompt)[:120]}"
        mode = "drill-echo (offline)"

    bus.register(card=CARD)
    # RB-25 F2: a brand-NEW agent seeds its cursor at the live tail so it never acts on
    # the stale broadcast backlog as if current (the newborn gauntlet drained months-old
    # history and treated it as a directive). Virgin-guarded: an ESTABLISHED runner keeps
    # draining its real backlog (mail queued while down -- the T014 discipline); only a
    # never-read "0"/"0" cursor is fast-forwarded. No-op for deepseek et al.
    # Same AKASHIC_DRILL_ECHO escape as F1: the kill-window drills PLANT direct mail then
    # start the runner expecting it consumed -- seeding past the plant would eat exactly
    # what the drill tests. The offline-drill signal is never set in production.
    if not os.environ.get("AKASHIC_DRILL_ECHO") and bus.seed_cursor_at_tail():
        print(f"[deepseek-runner] {args.agent} is new -- cursor seeded at the live tail "
              f"(stale broadcast backlog skipped; only new mail wakes it)")

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
    # T045 stage 2: the consume side rides the WORK LANE when flipped (per-process strangler
    # env gate BIFROST_CONSUME_LANE=work; unset = legacy path byte-identical).
    from core.comm.bifrost_api import BifrostAPI
    lane_mode = BifrostAPI.consume_lane_enabled()
    lane_key = bus.lane_cursor_key() if lane_mode else None
    api = BifrostAPI(args.agent) if lane_mode else None
    if lane_mode:
        if bus.lane_flip_if_migrating():
            print(f"[deepseek-runner] lane flip: cursor seeded at lane tails (A4 ritual); "
                  f"unconsumed legacy backlog rides the straggler net")
        print(f"[deepseek-runner] CONSUME LANE: work (T045 stage 2 cutover live)")
    print(f"[deepseek-runner] {args.agent} online (model={args.model}, think={'on' if args.think else 'off'}, "
          f"{mode}, max_hops={control.MAX_HOPS}). Waiting for messages... (Ctrl-C to stop)")
    lock_gen = runner_lock.generation_of(lock_token)   # L1b: this tenure's fencing token
    PULSE_GEN[0] = lock_gen                            # RB-27a: the pulse carries it too
    liveness.worklive(args.agent).set("idle")          # loop entered: startup survived
    bus_guard = liveness.BusLossGuard(max_dead=10)     # RB-30 B2: no invisible bus-less spin
    try:
        while True:
            verdict = bus_guard.beat(bus.probe())   # probe(), NOT online -- online never flips mid-run
            if verdict == "stand_down":
                print(f"[deepseek-runner] bus LOST for {bus_guard.max_dead} consecutive beats -- "
                      f"standing down cleanly (relaunch when Redis returns).")
                return 4
            if verdict == "degraded":
                print(f"[deepseek-runner] bus unreachable (dead beat {bus_guard.dead_beats}/"
                      f"{bus_guard.max_dead}) -- backing off {bus_guard.backoff_s}s.")
                time.sleep(bus_guard.backoff_s)
                continue
            if not runner_lock.heartbeat(args.agent, lock_token):  # another runner took over -> stand down
                print(f"[deepseek-runner] lost the singleton lock for '{args.agent}' -- another runner is "
                      "live. Standing down to avoid a cursor race.")
                break
            if control.is_halted(args.agent):                # global pause OR a halt targeted at me: freeze
                bus.register(card=CARD)                       # stay "online-but-frozen" on the roster, not vanish
                time.sleep(0.4)
                continue
            _drain_req = control.drain_requested(args.agent)  # graceful exit: loop-top only,
            if _drain_req:                                    # so the current message finished
                control.clear_drain(args.agent)
                print(f"[deepseek-runner] DRAIN honored (by {_drain_req.get('by', '?')}: "
                      f"{_drain_req.get('reason') or 'no reason given'}) -- exiting clean; "
                      "the singleton lock releases; relaunch when ready.")
                break
            # A1: stale-code self-restart -- loop-top only (same safety as drain: the
            # previous message is finished, nothing is claimed). On 2026-07-28 this
            # runner executed 29-commit-old code all day while its own fixes landed;
            # the fresh copy this launches takes the singleton lock at a higher
            # generation and this process stands down through the SAME takeover path
            # a crash would use. Fail direction is keep-running (proven staleness only).
            _sr = self_restart.maybe_self_restart(args.agent)
            if _sr:
                print(f"[deepseek-runner] {_sr} -- exiting clean; the successor takes the lock.")
                break
            # RB-26 (T030): detect WITHOUT consuming, then commit the cursor per message
            # AFTER it is handled (commit-after-processing). A crash mid-batch redelivers
            # the unhandled tail to the successor -- at-least-once; the reply_sent sentinel
            # + ack tier make replies effectively-once. batch_next captures the fully-read
            # safe position so the post-batch sweep steps past FILTERED entries (own
            # broadcasts) exactly once -- filtered != truncated (T014) still holds.
            cur0 = bus.read_lane_cursor() if lane_mode else bus.cursor()
            batch_next: dict = {}
            if lane_mode:
                # generation rides into work_drain so its internal sig/shadow advances
                # aren't refused as stale once this tenure stamps the lane hash
                msgs = api.work_drain(timeout_ms=1500, since_out=batch_next,
                                      generation=lock_gen)
            else:
                msgs = bus.wait(timeout_ms=1500, advance=False, since_out=batch_next)
            bus.register(card=CARD)                           # refresh presence
            # D2 stale-mail gate (kimi design, deepseek fence 2026-07-19: partition HERE in
            # the consume loop, helpers pure in packet_spec). Stale asks surface as ONE
            # triage notice, never auto-acked (P4); stale informs/traces skip the responder
            # and the batch_next sweep below commits cursors past them exactly like filtered
            # own-broadcasts (P3: no redelivery loop). BIFROST_STALE_MS=0 disables (P2).
            _now_ms = int(time.time() * 1000)
            msgs, _stale_asks, _stale_skips = packet_spec.partition_stale(
                msgs, now_ms=_now_ms, stale_ms=packet_spec.stale_gate_ms())
            if _stale_skips:
                print(f"[deepseek-runner] skipped {len(_stale_skips)} stale inform(s)/trace(s) "
                      "(BIFROST_STALE_MS gate)")
            if _stale_asks:
                print(f"[deepseek-runner] {packet_spec.stale_notice(_stale_asks, now_ms=_now_ms)}")
                for stale in _stale_asks:               # S0-beta: auto-park to durable bench
                    try:
                        age_h = (packet_spec.msg_age_ms(
                            stale, _now_ms) or 0) / 3600000.0
                        triage_park.park(args.agent,
                                         {"id": getattr(stale, "id", ""),
                                          "frm": getattr(stale, "frm", ""),
                                          "to": getattr(stale, "to", ""),
                                          "kind": getattr(stale, "kind", ""),
                                          "content": getattr(stale, "content", ""),
                                          "ts": getattr(stale, "ts", "")},
                                         reason=f"stale {age_h:.1f}h (D2 auto-triage)",
                                         by=f"{args.agent}-runner")
                    except Exception:
                        pass  # park is best-effort; stale notice + cursor advance still fire
            # S0 storm auto-clear (deepseek build, kimi second-observer K1-K3 folded,
            # claude fence+wire; 2-of-3 night protocol 2026-07-21). Detect -> pause(ttl)
            # -> skip -> K1 park fresh asks -> K2 conditional resume -> receipt -> skip
            # batch. The conveyor's first full auto-transit: standby-hard graduates from
            # human ritual to auto-detected, WITH a receipt.
            # work_backlog, NOT lane_depths (live incident 2026-07-21 ~03:05: XLEN is
            # stream LENGTH -- flat forever -- so the first post-wiring boot fired the
            # ceremony on depth=289 of pure history and would re-fire every window).
            _wd = lane_depths.work_backlog(args.agent)
            _storm_sig = _storm.feed(_wd, [getattr(m, "id", "") for m in msgs])
            if _storm_sig:
                print(f"[deepseek-runner] STORM: {_storm_sig['kind']} ({_storm_sig}) "
                      f"-- auto-clearing (standby-hard graduate)")
                _cleared = False
                _parked_ids = []
                # K2 (kimi; lesson control-pause-clobbers-preexisting-pause): never void
                # a pre-existing pause -- a human's persistent freeze outranks the ceremony.
                _was_paused = control.is_paused()
                try:
                    control.pause(reason=f"storm-auto-clear: {_storm_sig['kind']} "
                                         f"(depth={_wd} thr={_storm.depth_threshold})",
                                  by=f"{args.agent}-runner", ttl=120)
                    time.sleep(0.3)          # let the pause propagate to other runners
                    _res = cursor_admin.skip_to_now(
                        args.agent, by=f"{args.agent}-runner",
                        reason=f"storm-auto-clear: {_storm_sig['kind']}")
                    if _res.get("ok"):
                        _cleared = True
                        # K1 (kimi + claude concur): fresh ask-kinds in the drained batch
                        # park AFTER the skip commits -- bottomed-never-dropped beats
                        # redrive-roulette; in-batch id-dedup bounds the bench noise.
                        _seen_ids = set()
                        for _m in msgs:
                            _mid = getattr(_m, "id", "")
                            if (_mid and _mid not in _seen_ids
                                    and packet_spec.is_ask_kind(getattr(_m, "kind", ""))
                                    and str(getattr(_m, "frm", "")) != args.agent):
                                _seen_ids.add(_mid)
                                try:
                                    triage_park.park(
                                        args.agent,
                                        {"id": _mid, "frm": getattr(_m, "frm", ""),
                                         "to": getattr(_m, "to", ""),
                                         "kind": getattr(_m, "kind", ""),
                                         "content": getattr(_m, "content", ""),
                                         "ts": getattr(_m, "ts", "")},
                                        reason=f"storm auto-clear: {_storm_sig['kind']}",
                                        by=f"{args.agent}-runner")
                                    _parked_ids.append(_mid)
                                except Exception:
                                    pass     # per-ask best-effort (the D2 loop's mirror)
                    if not _was_paused:
                        control.resume()     # our pause only; a human's stays standing
                except Exception:
                    pass   # fail-open: ttl=120 self-heals any orphaned pause (C1-9)
                if _cleared:
                    try:
                        bus.broadcast(
                            "note",
                            f"[storm-clear] {args.agent}-runner auto-cleared "
                            f"{_storm_sig['kind']}: pause->skip->resume"
                            + (" (pre-existing pause left standing)" if _was_paused else "")
                            + f". Parked {len(_parked_ids)} fresh ask(s)"
                            + (f": {', '.join(_parked_ids)}" if _parked_ids else "")
                            + ". Receipt: standby-hard graduates to auto-detected.",
                            meta={"via": "storm-auto-clear", "display_only": True})
                    except Exception:
                        pass
                    _storm.reset()
                    continue                 # cursors already at tail via skip_to_now
                # ceremony aborted (skip refused/raised): fall through -- process the
                # batch normally; K2 guidance: never redeliver-and-refire the signature.
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
                if lane_mode and (m.meta or {}).get("_lane_src") != "work":
                    continue   # sig/legacy stream ids must NEVER advance the work fields;
                               # their cursors advanced inside work_drain (T045 stage 2)
                field = "bc" if str(m.to) == "*" else "inbox"
                status = bus.advance_to(**{field: m.id}, generation=lock_gen,
                                        cursor_key=lane_key)
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
                                        bc=batch_next.get("bc"), generation=lock_gen,
                                        cursor_key=lane_key)
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
    # M1-delta: write exit summary for the daemon's summary-injection path
    _write_exit_summary(getattr(args, "summary_file", None), exit_code=0, verdict="ok")
    print("[deepseek-runner] stopped.")
    return 0


def _write_exit_summary(path: Optional[str], exit_code: int = 0, verdict: str = "ok",
                        last_error: str = "") -> None:
    """M1-delta: write a JSON exit summary for the daemon's summary-injection path.
    Fail-silent: the runner's exit must never be blocked by a broken summary write."""
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        s = {"exit_code": exit_code, "turns": _RUN_STATS.get("turns", 0),
             "last_error": last_error, "verdict": verdict,
             "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(s, f)
    except Exception:
        pass


# T110b: a SECOND definition of _token_deltas / _token_journal / _RUN_STATS stood
# here, 1,240 lines below the originals at 146-153. Both ran at import and this one
# won, harmless only because it re-assigned the same empty values -- and primed to
# silently discard any real initial value the first block ever gains. Removed rather
# than annotated; the canonical definitions are at the top of the module. Pinned by
# tests/test_t110_runner_globals_defined_once.py so it cannot grow back here or in
# the kimi/sol runners.


if __name__ == "__main__":
    raise SystemExit(main())
