"""
ask_gemini_vision -- send an image file to Gemini for description/analysis.
Thin wrapper over ask_gemini.py's key resolution + the Gemini SDK's vision support.

  py scripts/ask_gemini_vision.py dropbox/image.png "Describe this UI screenshot in detail"
"""
import argparse
import base64
import os
import sys
from pathlib import Path

KEY_FILE = Path(__file__).resolve().parent.parent / ".secrets" / "gemini.key"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


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
    ap = argparse.ArgumentParser(description="Ask Gemini to describe an image.")
    ap.add_argument("image", help="path to the image file (png, jpg, webp, etc.)")
    ap.add_argument("prompt", nargs="*", default=["Describe this image in detail."],
                    help="prompt for the vision model")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--system", default="", help="optional system instruction")
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("NO_KEY: set GEMINI_API_KEY (env) or put the key in .secrets/gemini.key", file=sys.stderr)
        return 2

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"NO_FILE: {img_path} not found", file=sys.stderr)
        return 2

    prompt = " ".join(args.prompt) if args.prompt else "Describe this image in detail."

    # Read and encode the image
    data = img_path.read_bytes()
    ext = img_path.suffix.lower().lstrip(".")
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp"}
    mime = mime_map.get(ext, "image/png")
    b64 = base64.b64encode(data).decode("ascii")

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    cfg = types.GenerateContentConfig(system_instruction=args.system) if args.system else None

    parts = [
        types.Part.from_text(text=prompt),
        types.Part.from_bytes(data=b64, mime_type=mime),
    ]
    try:
        resp = client.models.generate_content(model=args.model, contents=parts, config=cfg)
        print(resp.text)
        return 0
    except Exception as e:
        print(f"GEMINI_ERROR ({args.model}): {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
