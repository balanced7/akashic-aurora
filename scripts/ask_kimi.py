"""
ask_kimi -- a thin bridge so an agent (or you) can get Kimi's take from the CLI.
Mirror of scripts/ask_deepseek.py / ask_gpt.py / ask_gemini.py (the fleet's ask-door pattern).

Key resolution (the secret never lands in the repo or chat transcript):
  1. env KIMI_API_KEY
  2. the gitignored file .secrets/kimi.key

Prompt source: positional args, else --file <path>, else stdin.

  py scripts/ask_kimi.py "Critique this design."
  py scripts/ask_kimi.py --file docs/library/design/20260709_the-codex-a-self-curating-knowledge-laye_302fc9.md --system "Be a blunt staff engineer."
  py scripts/ask_kimi.py --model kimi-k2.6 --max-tokens 2000 "Quick take?"

NOTE: pay-as-you-go against the seat's $105 grant; every call is METERED into the shared
spend ledger (state/kimi_spend.json) alongside the runner's spend. Thinking is always on and
bills as output -- the default max-tokens leaves headroom (a skimpy cap returns EMPTY content).
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from kimi_chat import DEFAULT_MODEL, SpendMeter, load_key, make_client


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console cp1252 guard
    ap = argparse.ArgumentParser(description="Ask Kimi from the CLI.")
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", default="")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--show-thinking", action="store_true",
                    help="print reasoning_content to stderr before the answer")
    args = ap.parse_args()

    if not load_key():
        print("NO_KEY: set KIMI_API_KEY (env) or put the key in .secrets/kimi.key", file=sys.stderr)
        return 2
    if args.file:
        prompt = Path(args.file).read_text(encoding="utf-8")
    elif args.prompt:
        prompt = " ".join(args.prompt)
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        print("NO_PROMPT: pass text, --file, or pipe via stdin", file=sys.stderr)
        return 2

    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": prompt})
    meter = SpendMeter()
    try:
        resp = make_client().chat.completions.create(
            model=args.model, messages=messages, max_completion_tokens=args.max_tokens)
        cost = meter.record(getattr(resp, "usage", None), args.model)
        msg = resp.choices[0].message
        if args.show_thinking and getattr(msg, "reasoning_content", None):
            print(f"[thinking]\n{msg.reasoning_content}\n[/thinking]", file=sys.stderr)
        print(msg.content or "(no content -- raise --max-tokens; thinking may have consumed the cap)")
        print(f"[ask_kimi] ${cost:.4f} this call | {meter.status_line()}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"KIMI_ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
