"""
bifrost_runner -- make a stateless model (Gemini) a FIRST-CLASS Bifrost citizen.

The wake adapter for API/web agent classes. A stateless model has no process and no inbox of its
own, so this runner is its body: it registers presence (with an Agent Card), blocks on the agent's
Bifrost inbox, and for each incoming message calls a provider bridge and posts the reply back on
the bus. So `@gemini ...` in the console -- or any agent sending to 'gemini' -- gets a real reply
on the bus. Degrades gracefully: web-first auto mode falls back to the API bridge on web errors.

  py scripts/bifrost_runner.py                         # web-first runner (Ctrl-C to stop)
  py scripts/bifrost_runner.py --provider api          # API only (ask_gemini.py)
  py scripts/bifrost_runner.py --provider web          # free web UI only (gemini_web.py)
  py scripts/bifrost_runner.py --model gemini-2.5-flash-lite --system "Be concise."
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from core.comm.bus import Bus

CARD_API = {
    "runtime_class": "api",
    "wake_mode": "runner",
    "door": "runner",
    "caps": ["review", "critique", "answer"],
}
CARD_WEB = {
    "runtime_class": "web",
    "wake_mode": "runner",
    "door": "runner",
    "caps": ["review", "critique", "answer", "web-ui"],
}
CARD = CARD_API  # backward compat for tests
ANSWERABLE = frozenset({"chat", "request", "question", "handoff"})
WEB_FAIL_MARKERS = (
    "LOGIN_REQUIRED",
    "GEMINI_WEB_ERROR",
    "AI_MODE_ERROR",
    "PLAYWRIGHT_MISSING",
    "UNKNOWN_MODE",
)


def should_answer(kind: str, frm: str, self_id: str) -> bool:
    """Answer direct asks from others; ignore our own echoes and non-question kinds."""
    return frm != self_id and str(kind) in ANSWERABLE


def _run_bridge(script: str, prompt: str, extra_args: list[str], timeout: int = 180) -> str:
    cmd = [sys.executable, os.path.join(HERE, script)] + extra_args
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
        return (p.stdout.strip() or p.stderr.strip() or "(no output from provider)")
    except Exception as e:
        return f"(runner error calling {script}: {type(e).__name__}: {e})"


def web_failed(text: str) -> bool:
    return any(m in text for m in WEB_FAIL_MARKERS)


def provider_reply_api(prompt: str, model: str, system: str) -> str:
    """Call the Gemini API bridge as a subprocess."""
    args = ["--model", model]
    if system:
        args += ["--system", system]
    return _run_bridge("ask_gemini.py", prompt, args, timeout=120)


def provider_reply_web(prompt: str, system: str, web_mode: str = "gemini") -> str:
    """Call the free Gemini web UI bridge as a subprocess."""
    args = ["--mode", web_mode]
    if system:
        args += ["--system", system]
    return _run_bridge("gemini_web.py", prompt, args, timeout=180)


def provider_reply(
    prompt: str,
    model: str,
    system: str,
    provider: str = "auto",
    web_mode: str = "gemini",
) -> str:
    """Resolve a prompt via web, API, or web-first auto fallback."""
    if provider == "api":
        return provider_reply_api(prompt, model, system)
    if provider == "web":
        return provider_reply_web(prompt, system, web_mode=web_mode)
    web_out = provider_reply_web(prompt, system, web_mode=web_mode)
    if not web_failed(web_out):
        return web_out
    api_out = provider_reply_api(prompt, model, system)
    if api_out.startswith("NO_KEY") or api_out.startswith("GEMINI_ERROR"):
        return f"{web_out}\n\n--- API fallback also failed ---\n{api_out}"
    return api_out


def card_for(provider: str) -> dict:
    if provider == "web":
        return dict(CARD_WEB)
    if provider == "api":
        return dict(CARD_API)
    return dict(CARD_WEB)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run an API model as a Bifrost citizen.")
    ap.add_argument("--agent", default="gemini")
    ap.add_argument("--model", default="gemini-2.5-flash-lite")
    ap.add_argument(
        "--provider",
        default="auto",
        choices=("auto", "web", "api"),
        help="auto=web then API fallback; web=free UI; api=API key bridge",
    )
    ap.add_argument(
        "--web-mode",
        default="gemini",
        choices=("gemini", "ai_mode"),
        help="web surface when provider is web or auto",
    )
    ap.add_argument("--system", default="You are Gemini, collaborating with Claude and Cursor over a shared bus. Be concise and direct.")
    ap.add_argument("--once", action="store_true", help="process one wake then exit (for testing)")
    args = ap.parse_args()

    card = card_for(args.provider)
    bus = Bus(args.agent)
    if not bus.online:
        print("bifrost_runner: bus OFFLINE (Redis unreachable)")
        return 2
    bus.register(card=card)
    print(
        f"[runner] {args.agent} online as {card['runtime_class']}/{card['wake_mode']} "
        f"(provider={args.provider}, model={args.model}). Waiting for messages... (Ctrl-C to stop)"
    )
    try:
        while True:
            msgs = bus.wait(timeout_ms=0, advance=True)   # block until a message, then CONSUME it
            bus.register(card=card)                       # refresh presence
            for m in msgs:
                if not should_answer(m.kind, m.frm, args.agent):
                    continue
                prompt = m.content if isinstance(m.content, str) else str(m.content)
                print(f"[runner] <- {m.frm} [{m.kind}]: {prompt[:80]}")
                reply = provider_reply(
                    prompt,
                    args.model,
                    args.system,
                    provider=args.provider,
                    web_mode=args.web_mode,
                )
                bus.send(
                    m.frm,
                    "reply",
                    reply,
                    meta={
                        "via": f"{args.agent}-runner",
                        "model": args.model,
                        "provider": args.provider,
                    },
                )
                print(f"[runner] -> {m.frm}: {reply[:80]}")
            if args.once:
                break
    except (KeyboardInterrupt, EOFError):
        pass
    print("[runner] stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
