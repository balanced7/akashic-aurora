"""
ask_gpt -- a thin bridge so an agent (or you) can get OpenAI/GPT's take from the CLI.
Mirror of scripts/ask_gemini.py.

Key resolution (first hit wins; the secret never lands in the repo or chat transcript):
  1. env OPENAI_API_KEY
  2. the gitignored file  .secrets/openai.key

Prompt source: positional args, else --file <path>, else stdin.

  py scripts/ask_gpt.py "Critique the Consolidator extraction."
  py scripts/ask_gpt.py --file docs/codex-plan.md --system "Be a blunt staff engineer."

NOTE: the prompt is sent to OpenAI's API (pay-as-you-go -- real cost, usually cents). Don't pass
anything you wouldn't share with OpenAI.
"""
import argparse
import os
import sys
from pathlib import Path

KEY_FILE = Path(__file__).resolve().parent.parent / ".secrets" / "openai.key"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")


def load_key():
    v = os.getenv("OPENAI_API_KEY")
    if v and v.strip():
        return v.strip()
    if KEY_FILE.exists():
        t = KEY_FILE.read_text(encoding="utf-8").strip()
        if t:
            return t
    return None


def main():
    ap = argparse.ArgumentParser(description="Ask GPT from the CLI.")
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", default="")
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("NO_KEY: set OPENAI_API_KEY (env) or put the key in .secrets/openai.key", file=sys.stderr)
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

    from openai import OpenAI
    client = OpenAI(api_key=key)
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = client.chat.completions.create(model=args.model, messages=messages)
        print(resp.choices[0].message.content)
        return 0
    except Exception as e:
        print(f"GPT_ERROR ({args.model}): {type(e).__name__}: {e}", file=sys.stderr)
        try:
            names = [m.id for m in client.models.list().data]
            print("models available to this key:", ", ".join(sorted(names)[:30]), file=sys.stderr)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
