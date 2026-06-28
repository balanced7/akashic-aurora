"""
gemini_web -- ask Gemini through the FREE web surfaces (not API quota).

Modes:
  gemini   -> gemini.google.com chat (frontier model in the web UI)
  ai_mode  -> Google Search AI Mode (?udm=50)
  both     -> run gemini then ai_mode, labeled (like ask_panel.py)
  api      -> fallback to scripts/ask_gemini.py (uses API key / free-tier API)

Auth: we CANNOT inject your Google account credentials or reuse your main Chrome
profile (Google blocks automating the default profile). Instead:
  1. Run once:  py scripts/gemini_web.py --login
  2. Sign in manually in the browser window with your Google account
  3. Session cookies persist in .secrets/gemini_web_profile/ (gitignored)

  py scripts/gemini_web.py "Critique this design" --mode gemini
  py scripts/gemini_web.py "What are the risks?" --mode ai_mode
  echo "..." | py scripts/gemini_web.py --mode both --system "Be blunt."

Requires: pip install playwright && playwright install chrome
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".secrets" / "gemini_web_profile"
DEFAULT_TIMEOUT_MS = int(os.getenv("GEMINI_WEB_TIMEOUT_MS", "120000"))


def _prompt_from_args(args) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.prompt:
        return " ".join(args.prompt)
    return sys.stdin.read()


def _needs_playwright() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _install_hint() -> str:
    return (
        "PLAYWRIGHT_MISSING: run once:\n"
        "  py -m pip install playwright\n"
        "  py -m playwright install chrome"
    )


def _compose_prompt(prompt: str, system: str) -> str:
    prompt = (prompt or "").strip()
    system = (system or "").strip()
    if not system:
        return prompt
    return f"{system.strip()}\n\n---\n\n{prompt}"


def _launch_context(headless: bool):
    from playwright.sync_api import sync_playwright

    PROFILE.mkdir(parents=True, exist_ok=True)
    pw = sync_playwright().start()
    try:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=headless,
            no_viewport=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
    except Exception:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            headless=headless,
            no_viewport=True,
        )
    ctx._akashic_pw = pw  # keep playwright alive until context closes
    return ctx


def _close_context(ctx) -> None:
    pw = getattr(ctx, "_akashic_pw", None)
    try:
        ctx.close()
    finally:
        if pw is not None:
            pw.stop()


def _looks_logged_out(page) -> bool:
    url = (page.url or "").lower()
    if "accounts.google.com" in url or "ServiceLogin" in url:
        return True
    for sel in (
        'a[href*="accounts.google.com"]',
        'button:has-text("Sign in")',
        '[aria-label="Sign in"]',
    ):
        try:
            if page.locator(sel).first.is_visible(timeout=800):
                return True
        except Exception:
            pass
    return False


def _login_hint() -> str:
    return (
        "LOGIN_REQUIRED: no saved Google session for the web UI.\n"
        "Run once (browser opens — sign in as your Google account):\n"
        "  py scripts/gemini_web.py --login\n"
        f"Profile dir: {PROFILE}"
    )


def _find_input(page):
    candidates = [
        'div[contenteditable="true"][aria-label*="Enter"]',
        'div[contenteditable="true"]',
        'textarea[aria-label*="Enter"]',
        'textarea',
        '[role="textbox"]',
        '.ql-editor',
    ]
    for sel in candidates:
        loc = page.locator(sel).last
        try:
            if loc.count() and loc.is_visible(timeout=1500):
                return loc
        except Exception:
            continue
    return None


def _extract_latest_model_text(page) -> str:
    selectors = [
        "message-content",
        '[data-message-author-role="model"]',
        '[data-testid="model-response"]',
        '.model-response-text',
        '.markdown',
        "p[data-path-to-node]",
    ]
    for sel in selectors:
        loc = page.locator(sel)
        try:
            n = loc.count()
            if n:
                txt = loc.nth(n - 1).inner_text(timeout=3000).strip()
                if txt:
                    return txt
        except Exception:
            continue
    return ""


def _ask_gemini_chat(page, prompt: str, timeout_ms: int) -> str:
    page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(1500)
    if _looks_logged_out(page):
        return _login_hint()

    inp = _find_input(page)
    if inp is None:
        return "GEMINI_WEB_ERROR: could not find chat input (UI may have changed). Try --login or --headed."

    before = _extract_latest_model_text(page)
    inp.click(timeout=5000)
    page.keyboard.type(prompt, delay=8)
    page.keyboard.press("Enter")

    deadline = time.time() + (timeout_ms / 1000.0)
    last = ""
    while time.time() < deadline:
        page.wait_for_timeout(1200)
        cur = _extract_latest_model_text(page)
        if cur and cur != before:
            last = cur
            page.wait_for_timeout(1800)
            newer = _extract_latest_model_text(page)
            if newer and len(newer) >= len(last):
                last = newer
            if last == _extract_latest_model_text(page):
                break
    return last or "GEMINI_WEB_ERROR: no response text captured (timeout or selector drift). Try --headed."


def _ask_ai_mode(page, prompt: str, timeout_ms: int) -> str:
    q = urllib.parse.quote_plus(prompt[:1500])
    url = f"https://www.google.com/search?q={q}&udm=50&hl=en"
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(2500)
    if _looks_logged_out(page):
        return _login_hint()

    selectors = [
        '[data-subtree="aim"]',
        '[data-aim-timestamp]',
        '.AIrHhb',
        '.WaaZC',
        '.model-response-text',
        '[data-message-author-role="model"]',
        '#search div[lang]',
    ]
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        for sel in selectors:
            loc = page.locator(sel)
            try:
                if loc.count():
                    txt = loc.first.inner_text(timeout=2000).strip()
                    if txt and len(txt) > 40:
                        return txt
            except Exception:
                continue
        page.wait_for_timeout(1500)
    body = ""
    try:
        body = page.locator("body").inner_text(timeout=3000)
    except Exception:
        pass
    if "AI Mode" in body or "Generative AI" in body:
        return body[:4000]
    return "AI_MODE_ERROR: no AI Mode answer captured (region/login/UI drift). Try --login or --headed."


def _ask_via_api(prompt: str, system: str) -> str:
    cmd = [sys.executable, str(ROOT / "scripts" / "ask_gemini.py")]
    if system:
        cmd += ["--system", system]
    cmd.append(prompt)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = (p.stdout or p.stderr or "").strip()
    return out or f"API_ERROR: exit {p.returncode}"


def _ask_web(mode: str, prompt: str, *, headed: bool, timeout_ms: int) -> str:
    if not _needs_playwright():
        return _install_hint()
    ctx = _launch_context(headless=not headed)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if mode == "gemini":
            return _ask_gemini_chat(page, prompt, timeout_ms)
        if mode == "ai_mode":
            return _ask_ai_mode(page, prompt, timeout_ms)
        return f"UNKNOWN_MODE: {mode}"
    finally:
        _close_context(ctx)


def cmd_login(headed: bool = True) -> int:
    if not _needs_playwright():
        print(_install_hint(), file=sys.stderr)
        return 2
    print(f"Opening browser for one-time Google login.\nProfile: {PROFILE}")
    print("Sign in as your Google account (or whichever account you want).")
    print("Visit Gemini + Google, then close the browser window when done.\n")
    ctx = _launch_context(headless=not headed)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        page.goto("https://www.google.com/search?q=hello&udm=50&hl=en", wait_until="domcontentloaded")
        print("Browser ready. Close the browser window when finished signing in.")
        input("Press Enter here after you close the browser...")
    finally:
        _close_context(ctx)
    print("Login profile saved.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Ask Gemini via web UI (free) or API fallback.")
    ap.add_argument("prompt", nargs="*", help="prompt text (or --file / stdin)")
    ap.add_argument("--file")
    ap.add_argument("--mode", default="gemini", choices=("gemini", "ai_mode", "both", "api"))
    ap.add_argument("--system", default="")
    ap.add_argument("--headed", action="store_true", help="show browser (debug / CAPTCHA)")
    ap.add_argument("--login", action="store_true", help="one-time Google login setup")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_MS, help="ms")
    args = ap.parse_args()

    if args.login:
        return cmd_login(headed=True)

    prompt = _compose_prompt(_prompt_from_args(args), args.system)
    if not prompt.strip():
        print("NO_PROMPT: pass text, --file, or pipe via stdin", file=sys.stderr)
        return 2

    if args.mode == "api":
        print(_ask_via_api(prompt, ""))
        return 0

    if args.mode == "both":
        g = _ask_web("gemini", prompt, headed=args.headed, timeout_ms=args.timeout)
        a = _ask_web("ai_mode", prompt, headed=args.headed, timeout_ms=args.timeout)
        print(f"========================= GEMINI (web) =========================\n{g}")
        print(f"\n========================= GOOGLE AI MODE =========================\n{a}")
        return 0

    print(_ask_web(args.mode, prompt, headed=args.headed, timeout_ms=args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
