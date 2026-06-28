"""
ask_panel -- fan ONE question out to the frontier-model panel (Gemini + GPT) and print each
reply verbatim, labeled. Claude (the calling agent) reads both and synthesizes -> a 3-way collab.

  py scripts/ask_panel.py --system "Blunt pre-build review." --file design.md
  echo "Is this over-engineered?" | py scripts/ask_panel.py

Each model is reached through its own bridge (ask_gemini.py / ask_gpt.py), so key handling and
model selection stay in one place per provider. A provider with no key just prints its NO_KEY
notice and the panel continues with whoever is available.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PANEL = [("GEMINI", "ask_gemini.py"), ("GPT", "ask_gpt.py")]


def run(script: str, prompt: str, system: str, model: str):
    cmd = [sys.executable, str(HERE / script)]
    if system:
        cmd += ["--system", system]
    if model:
        cmd += ["--model", model]
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=180)
        return (p.stdout.strip() or p.stderr.strip() or "(no output)")
    except Exception as e:
        return f"(panel error: {type(e).__name__}: {e})"


def main():
    ap = argparse.ArgumentParser(description="Ask the Gemini+GPT panel one question.")
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--system", default="")
    ap.add_argument("--gemini-model", default="")
    ap.add_argument("--gpt-model", default="")
    args = ap.parse_args()

    if args.file:
        prompt = Path(args.file).read_text(encoding="utf-8")
    elif args.prompt:
        prompt = " ".join(args.prompt)
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        print("NO_PROMPT", file=sys.stderr)
        return 2

    models = {"ask_gemini.py": args.gemini_model, "ask_gpt.py": args.gpt_model}
    for label, script in PANEL:
        print(f"\n========================= {label} =========================")
        print(run(script, prompt, args.system, models[script]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
