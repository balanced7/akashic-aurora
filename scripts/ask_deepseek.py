"""
ask_deepseek -- a thin bridge so an agent (or you) can get DeepSeek's take from the CLI.
Mirror of scripts/ask_gemini.py / scripts/ask_gpt.py.

Key resolution (first hit wins; the secret never lands in the repo or chat transcript):
  1. env DEEPSEEK_API_KEY
  2. the gitignored file  .secrets/deepseek.key

Prompt source: positional args, else --file <path>, else stdin.

  py scripts/ask_deepseek.py "Critique the Consolidator extraction."
  py scripts/ask_deepseek.py --file docs/codex-plan.md --system "Be a blunt staff engineer."
  py scripts/ask_deepseek.py --model deepseek-reasoner "Prove this is correct."

NOTE: the prompt is sent to DeepSeek's API (pay-as-you-go -- real cost, usually cents). Don't pass
anything you wouldn't share with DeepSeek. DeepSeek's API is OpenAI-compatible, so this reuses the
`openai` client pointed at DeepSeek's base_url.
"""
import argparse
import os
import sys
from pathlib import Path

KEY_FILE = Path(__file__).resolve().parent.parent / ".secrets" / "deepseek.key"
BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")   # smartest (1M ctx); v4-flash = cheaper/faster
# NB: deepseek-chat / deepseek-reasoner are deprecated 2026-07-24 -- v4-pro / v4-flash are the live models.


def load_key():
    v = os.getenv("DEEPSEEK_API_KEY")
    if v and v.strip():
        return v.strip()
    if KEY_FILE.exists():
        t = KEY_FILE.read_text(encoding="utf-8").strip()
        if t:
            return t
    return None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console defaults to cp1252
    ap = argparse.ArgumentParser(description="Ask DeepSeek from the CLI.")
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", default="")
    ap.add_argument("--max-tokens", type=int, default=None)
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("NO_KEY: set DEEPSEEK_API_KEY (env) or put the key in .secrets/deepseek.key", file=sys.stderr)
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

    from deepseek_chat import make_client
    client = make_client(key)   # L0: timeout + explicit retries (shared hardened factory)
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": prompt})
    try:
        kwargs = {"model": args.model, "messages": messages}
        if args.max_tokens:
            kwargs["max_tokens"] = args.max_tokens
        resp = client.chat.completions.create(**kwargs)
        print(resp.choices[0].message.content)
        return 0
    except Exception as e:
        print(f"DEEPSEEK_ERROR ({args.model}): {type(e).__name__}: {e}", file=sys.stderr)
        try:
            names = [m.id for m in client.models.list().data]
            print("models available to this key:", ", ".join(sorted(names)[:30]), file=sys.stderr)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
