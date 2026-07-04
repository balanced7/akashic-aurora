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
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from core.comm.bus import Bus
from core.comm import control
from ask_deepseek import load_key, BASE_URL, DEFAULT_MODEL

CARD = {
    "runtime_class": "api",
    "wake_mode": "runner",
    "door": "runner",
    "caps": ["review", "critique", "answer", "audit", "code"],
}
ANSWERABLE = frozenset({"chat", "request", "question", "handoff"})
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


def make_agentic_replier(model: str, system: str, think: bool, root: Path):
    """Tool-using bridge: DeepSeek can read files, search, inspect git, and query the Akashic knowledge
    base WHILE composing its reply, then posts the final answer to the bus. Reuses the guarded
    Agent+ToolBox from deepseek_chat.py (read-only, secret-blocked, path-scoped). Keeps a per-peer
    conversation for continuity. Unattended, so gated actions (run_command) auto-deny."""
    import deepseek_chat as dc
    from openai import OpenAI
    client = OpenAI(api_key=load_key(), base_url=BASE_URL)
    toolbox = dc.ToolBox(root, allow_exec=False, trust=False, allow_secrets=False,
                         confirm=lambda _p: False)
    convos: dict = {}

    def respond(frm: str, prompt: str) -> str:
        ag = convos.get(frm)
        if ag is None:
            # interrupt=control.is_paused -> a HALT interjection stops work mid-tool-loop (DeepSeek's insight)
            ag = dc.Agent(client, toolbox, model=model, system=system, think=think,
                          tools_enabled=True, interrupt=control.is_paused)
            convos[frm] = ag
        try:
            answer = ag.send(prompt)                 # streams to the runner window; returns final text
        except Exception as e:
            return f"(deepseek agentic runner error: {type(e).__name__}: {e})"
        return answer or "(deepseek produced no final answer)"

    return respond


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
    ap.add_argument("--once", action="store_true", help="process one wake then exit (for testing)")
    args = ap.parse_args()

    if not load_key():
        print("bifrost_runner_deepseek: NO_KEY (set DEEPSEEK_API_KEY or .secrets/deepseek.key)")
        return 2
    bus = Bus(args.agent)
    if not bus.online:
        print("bifrost_runner_deepseek: bus OFFLINE (Redis unreachable)")
        return 2

    if args.agentic:
        import deepseek_chat as dc
        if dc._enable_utf8_and_ansi():
            dc.C.enable()
        root = Path(args.root).resolve()
        system = args.system
        if system == DEFAULT_SYSTEM:                 # give the tool-aware prompt unless overridden
            system = dc.default_system(root) + (" You are reached over a shared message bus; each "
                     "reply posts back to the sender, so make it self-contained.")
        responder = make_agentic_replier(args.model, system, args.think, root)
        mode = f"agentic tools @ {root}"
    else:
        responder = make_replier(args.model, args.system, args.think)
        mode = "one-shot bridge"

    bus.register(card=CARD)
    rate = control.RateLimiter()
    print(f"[deepseek-runner] {args.agent} online (model={args.model}, think={'on' if args.think else 'off'}, "
          f"{mode}, max_hops={control.MAX_HOPS}). Waiting for messages... (Ctrl-C to stop)")
    try:
        while True:
            if control.is_paused():                          # human barge-in: freeze, keep mail queued
                time.sleep(0.4)
                continue
            msgs = bus.wait(timeout_ms=1500, advance=True)   # short block so pause/stop stay responsive
            bus.register(card=CARD)                           # refresh presence
            for m in msgs:
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
                out = responder(m.frm, prompt) if args.agentic else responder(prompt)
                bus.send(m.frm, "reply", out,
                         meta={"via": f"{args.agent}-runner", "model": args.model, "hops": hops})
                print(f"[deepseek-runner] -> {m.frm}: {out[:80]}")
            if args.once:
                break
    except (KeyboardInterrupt, EOFError):
        pass
    print("[deepseek-runner] stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
