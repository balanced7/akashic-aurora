"""
ask_gemini -- a thin bridge so an agent (or you) can get Gemini's take from the CLI.

Key resolution (first hit wins), so the secret never lands in the repo or the chat transcript:
  1. env GEMINI_API_KEY / GOOGLE_API_KEY / GOOGLE_GENAI_API_KEY
  2. the gitignored file  .secrets/gemini.key

Prompt source: positional args, else --file <path>, else stdin.

  py scripts/ask_gemini.py "What do you think of the Consolidator extraction?"
  py scripts/ask_gemini.py --file docs/codex-plan.md --system "Critique this plan; be blunt."
  echo "..." | py scripts/ask_gemini.py --model gemini-2.5-pro

NOTE: the prompt is sent to Google's Gemini API. Don't pass anything you wouldn't share with Google.
"""
import argparse
import os
import sys
from pathlib import Path

KEY_FILE = Path(__file__).resolve().parent.parent / ".secrets" / "gemini.key"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")   # free-tier-accessible; pro is 0-quota


def load_key():
    for env in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"):
        v = os.getenv(env)
        if v and v.strip():
            return v.strip()
    if KEY_FILE.exists():
        t = KEY_FILE.read_text(encoding="utf-8").strip()
        if t:
            return t
    return None


def main():
    ap = argparse.ArgumentParser(description="Ask Gemini from the CLI.")
    ap.add_argument("prompt", nargs="*", help="the prompt (or use --file / stdin)")
    ap.add_argument("--file", help="read the prompt from a file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", default="", help="optional system instruction")
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("NO_KEY: set GEMINI_API_KEY (env) or put the key in .secrets/gemini.key", file=sys.stderr)
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

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    cfg = types.GenerateContentConfig(system_instruction=args.system) if args.system else None
    try:
        resp = client.models.generate_content(model=args.model, contents=prompt, config=cfg)
        print(resp.text)
        return 0
    except Exception as e:
        print(f"GEMINI_ERROR ({args.model}): {type(e).__name__}: {e}", file=sys.stderr)
        try:
            names = [m.name for m in client.models.list()]
            print("models available to this key:", ", ".join(n.split('/')[-1] for n in names[:25]), file=sys.stderr)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
