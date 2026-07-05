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
    from openai import OpenAI
    client = OpenAI(api_key=load_key(), base_url=BASE_URL)

    def respond(prompt: str) -> str:
        try:
            kwargs = {"model": model, "messages": [
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
                         allow_write: bool = False):
    """Tool-using bridge: DeepSeek can read files, search, inspect git, and query the Akashic knowledge
    base WHILE composing its reply, then posts the final answer to the bus. Reuses the guarded
    Agent+ToolBox from deepseek_chat.py (read-only, secret-blocked, path-scoped). Keeps a per-peer
    conversation for continuity. Unattended, so gated actions (run_command) auto-deny."""
    import deepseek_chat as dc
    from openai import OpenAI
    client = OpenAI(api_key=load_key(), base_url=BASE_URL)
    # agent_id -> the ToolBox's bifrost_* doors go live, so DeepSeek can INITIATE bus messages (not just reply).
    # allow_write -> the guarded write_file/edit_file doors go live (path-scoped, secret-blocked, git-tracked).
    toolbox = dc.ToolBox(root, allow_exec=False, trust=False, allow_secrets=False,
                         confirm=lambda _p: False, agent_id=agent_id, allow_write=allow_write)
    on_activity = lambda state, detail: control.set_activity(agent_id, state, detail)
    # Live trace: stream each tool call + chunk of thinking onto the bus (kind=trace, display-only, not
    # promoted/answerable) so the console shows what DeepSeek is DOING, not just its final answer.
    trace_bus = Bus(agent_id)

    def on_trace(kind, text):
        prefix = "🔧" if kind == "tool" else "💭"
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
            convos[frm] = ag
        # Fold any queued context hints from peers into this turn's prompt
        try:
            hints = context_hints.drain(agent_id)
            if hints:
                hint_block = context_hints.format_for_prompt(hints)
                prompt = hint_block + "\n" + prompt
        except Exception:
            pass
        try:
            answer = ag.send(prompt)                 # streams to the runner window; returns final text
        except Exception as e:
            return f"(deepseek agentic runner error: {type(e).__name__}: {e})"
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
                                         allow_write=args.allow_write)
        mode = f"agentic tools @ {root}{' +write' if args.allow_write else ''}"
    else:
        responder = make_replier(args.model, args.system, args.think)
        mode = "one-shot bridge"

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
            except Exception:
                pass
    threading.Thread(target=_heartbeat, daemon=True).start()
    print(f"[deepseek-runner] {args.agent} online (model={args.model}, think={'on' if args.think else 'off'}, "
          f"{mode}, max_hops={control.MAX_HOPS}). Waiting for messages... (Ctrl-C to stop)")
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
            msgs = bus.wait(timeout_ms=1500, advance=True)   # short block so pause/stop stay responsive
            bus.register(card=CARD)                           # refresh presence
            for m in msgs:
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
                        # Cognitive metrics: a hint can save a file read
                        cog.record_file_read(args.agent, hint_data.get("key", "?"), from_hint=True)
                        print(f"[deepseek-runner] hint accepted ({hint_data.get('key','?')}) "
                              f"from {m.frm}: {hint_data.get('value','?')[:100]}")
                    continue
                if not should_answer(m.kind, m.frm, args.agent):
                    continue
                hops = control.next_hops(m.meta)
                if control.hops_exceeded(m.meta):             # loop-guard: bounce the thread to a human
                    bus.send(m.frm, "note",
                             f"[loop-guard] max hops ({control.MAX_HOPS}) reached -- returning to a human.",
                             meta={"via": f"{args.agent}-runner", "hops": hops})
                    print(f"[deepseek-runner] loop-guard: hops>={control.MAX_HOPS}; not answering {m.frm}")
                    continue
                if not rate.allow():                          # backstop: too many replies too fast
                    control.pause(reason=f"{args.agent} hit reply rate limit", by=args.agent)
                    bus.send(m.frm, "note",
                             "[loop-guard] reply rate limit hit -- auto-paused. Resume when ready.",
                             meta={"via": f"{args.agent}-runner", "hops": hops})
                    print("[deepseek-runner] rate limit -> auto-paused")
                    continue
                prompt = m.content if isinstance(m.content, str) else str(m.content)
                print(f"[deepseek-runner] <- {m.frm} [{m.kind}] (hop {hops}): {prompt[:80]}")
                if str(m.kind) == "nudge" or nudge.is_nudged(args.agent):
                    nudge.clear(args.agent)               # consume so answering the nudge isn't self-interrupted
                    bus.send(m.frm, "note", "[nudge ack] interrupting current work to look at this now.",
                             meta={"via": f"{args.agent}-runner", "hops": hops})
                    # Cognitive metrics: this nudge/halt may cause abandoned reasoning
                    cog.record_human_interjection(args.agent)
                    print(f"[deepseek-runner] nudge from {m.frm} -> acked + cleared")
                # If globally halted, record the interjection too
                if control.is_halted(args.agent) and str(m.kind) != "nudge":
                    cog.record_human_interjection(args.agent)
                control.set_activity(args.agent, "thinking")
                try:
                    out = responder(m.frm, prompt) if args.agentic else responder(prompt)
                    reply_meta = {"via": f"{args.agent}-runner", "model": args.model, "hops": hops}
                    # Channel mirror: a message that arrived by BROADCAST is replied by broadcast, so the
                    # whole group (Claude + the console) sees it -- not just the sender. Direct stays direct.
                    if str(m.to) == "*":
                        bus.broadcast("reply", out, meta=reply_meta)
                        dest = "*(broadcast -> all)"
                    else:
                        bus.send(m.frm, "reply", out, meta=reply_meta)
                        dest = m.frm
                    # Cognitive metrics: turn complete
                    cog.record_turn_complete(args.agent)
                    print(f"[deepseek-runner] -> {dest}: {out[:80]}")
                finally:
                    control.clear_activity(args.agent)   # back to idle -> UI stops showing it working
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
