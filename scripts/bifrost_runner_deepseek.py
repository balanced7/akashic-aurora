"""
bifrost_runner_deepseek -- make DeepSeek (a stateless API model) a FIRST-CLASS Bifrost citizen.

Mirrors scripts/bifrost_runner.py (the Gemini runner). DeepSeek has no process and no inbox of its
own, so this runner is its body: it registers @deepseek presence (an Agent Card), blocks on
DeepSeek's Bifrost inbox, and for each incoming ask calls the DeepSeek API and posts the reply back
on the bus. So `py agent_cli.py bifrost-send <you> --to deepseek "..."` -- or any agent messaging
'deepseek' -- gets a real reply on the bus, and the sender wakes (bifrost_wake) when it lands.
That is the real-time Claude <-> DeepSeek loop.

  py scripts/bifrost_runner_deepseek.py                     # v4-pro, thinking off (snappy)
  py scripts/bifrost_runner_deepseek.py --think             # v4-pro with reasoning (deeper, slower)
  py scripts/bifrost_runner_deepseek.py --model deepseek-v4-flash --once   # cheap; one msg then exit

Key: env DEEPSEEK_API_KEY else .secrets/deepseek.key (reused from ask_deepseek.py). OpenAI-compatible.
This is the stateless one-shot bridge (Slice 1). A stateful, tool-using runner (DeepSeek reads
files/KB WHILE collaborating) is the follow-on slice built on scripts/deepseek_chat.py.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from core.comm.bus import Bus
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
    """Answer direct asks from others; ignore our own echoes and non-question kinds (e.g. 'reply')."""
    return frm != self_id and str(kind) in ANSWERABLE


def make_replier(model: str, system: str, think: bool):
    """Build a one-shot prompt->reply bridge over the DeepSeek API. Never raises: any failure comes
    back as a string so the runner loop stays alive and the sender always gets *something*."""
    from openai import OpenAI
    client = OpenAI(api_key=load_key(), base_url=BASE_URL)

    def reply(prompt: str) -> str:
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

    return reply


def main() -> int:
    ap = argparse.ArgumentParser(description="Run DeepSeek as a Bifrost citizen.")
    ap.add_argument("--agent", default="deepseek")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", default=DEFAULT_SYSTEM)
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
    bus.register(card=CARD)
    reply = make_replier(args.model, args.system, args.think)
    print(f"[deepseek-runner] {args.agent} online (model={args.model}, think={'on' if args.think else 'off'}). "
          f"Waiting for messages... (Ctrl-C to stop)")
    try:
        while True:
            msgs = bus.wait(timeout_ms=0, advance=True)  # block until a message, then CONSUME it
            bus.register(card=CARD)                       # refresh presence
            for m in msgs:
                if not should_answer(m.kind, m.frm, args.agent):
                    continue
                prompt = m.content if isinstance(m.content, str) else str(m.content)
                print(f"[deepseek-runner] <- {m.frm} [{m.kind}]: {prompt[:80]}")
                out = reply(prompt)
                bus.send(m.frm, "reply", out, meta={"via": f"{args.agent}-runner", "model": args.model})
                print(f"[deepseek-runner] -> {m.frm}: {out[:80]}")
            if args.once:
                break
    except (KeyboardInterrupt, EOFError):
        pass
    print("[deepseek-runner] stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
