"""
bifrost_runner -- make a stateless API model (Gemini) a FIRST-CLASS Bifrost citizen.

The wake adapter for the "API" agent class. A stateless model has no process and no inbox of its
own, so this runner is its body: it registers presence (with an Agent Card), blocks on the agent's
Bifrost inbox, and for each incoming message calls the provider bridge (scripts/ask_gemini.py) and
posts the reply back on the bus. So `@gemini ...` in the console -- or any agent sending to 'gemini'
-- gets a real reply on the bus, with no MCP and no key beyond the bridge's. Degrades gracefully:
if the provider is down (Gemini free-tier 503/quota), it posts the error as the reply rather than
crashing.

  py scripts/bifrost_runner.py                         # the gemini runner (Ctrl-C to stop)
  py scripts/bifrost_runner.py --model gemini-2.5-flash-lite --system "Be concise."
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from core.comm.bus import Bus

CARD = {"runtime_class": "api", "wake_mode": "runner", "door": "runner",
        "caps": ["review", "critique", "answer"]}
ANSWERABLE = frozenset({"chat", "request", "question", "handoff"})


def should_answer(kind: str, frm: str, self_id: str) -> bool:
    """Answer direct asks from others; ignore our own echoes and non-question kinds."""
    return frm != self_id and str(kind) in ANSWERABLE


def provider_reply(prompt: str, model: str, system: str) -> str:
    """Call the Gemini bridge as a subprocess (reuses its key handling + model fallback)."""
    cmd = [sys.executable, os.path.join(HERE, "ask_gemini.py"), "--model", model]
    if system:
        cmd += ["--system", system]
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=120)
        return (p.stdout.strip() or p.stderr.strip() or "(no output from provider)")
    except Exception as e:
        return f"(runner error calling provider: {type(e).__name__}: {e})"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run an API model as a Bifrost citizen.")
    ap.add_argument("--agent", default="gemini")
    ap.add_argument("--model", default="gemini-2.5-flash-lite")
    ap.add_argument("--system", default="You are Gemini, collaborating with Claude and Cursor over a shared bus. Be concise and direct.")
    ap.add_argument("--once", action="store_true", help="process one wake then exit (for testing)")
    args = ap.parse_args()

    bus = Bus(args.agent)
    if not bus.online:
        print("bifrost_runner: bus OFFLINE (Redis unreachable)")
        return 2
    bus.register(card=CARD)
    print(f"[runner] {args.agent} online as {CARD['runtime_class']}/{CARD['wake_mode']} "
          f"(model={args.model}). Waiting for messages... (Ctrl-C to stop)")
    try:
        while True:
            msgs = bus.wait(timeout_ms=0, advance=True)   # block until a message, then CONSUME it
            bus.register(card=CARD)                       # refresh presence
            for m in msgs:
                if not should_answer(m.kind, m.frm, args.agent):
                    continue
                prompt = m.content if isinstance(m.content, str) else str(m.content)
                print(f"[runner] <- {m.frm} [{m.kind}]: {prompt[:80]}")
                reply = provider_reply(prompt, args.model, args.system)
                bus.send(m.frm, "reply", reply, meta={"via": f"{args.agent}-runner", "model": args.model})
                print(f"[runner] -> {m.frm}: {reply[:80]}")
            if args.once:
                break
    except (KeyboardInterrupt, EOFError):
        pass
    print("[runner] stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
