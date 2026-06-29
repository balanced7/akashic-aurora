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

Default automation uses invisible mode (real Chrome off-screen, passes AI Mode gates).
Use --headed only for login/debug. bifrost_runner keeps one warm invisible browser.

Requires: pip install playwright && playwright install chrome
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".secrets" / "gemini_web_profile"
DEFAULT_TIMEOUT_MS = int(os.getenv("GEMINI_WEB_TIMEOUT_MS", "120000"))

BrowserMode = Literal["visible", "invisible", "headless"]
Engine = Literal["playwright", "patchright"]

# Playwright leaks automation unless we strip flags + init scripts. AI Mode still needs a
# real Chrome renderer (headless=new is gated) — invisible mode runs headed Chrome off-screen.
STEALTH_CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--no-first-run",
    "--no-default-browser-check",
    "--exclude-switches=enable-automation",
    "--disable-features=IsolateOrigins,site-per-process,AutomationControlled",
]

# Headed Chrome parked off-screen: passes AI Mode bot checks without flashing on screen.
INVISIBLE_CHROME_ARGS = [
    "--window-position=-24000,-24000",
    "--window-size=800,600",
    "--start-minimized",
]

# Strip Playwright bindings that Google's bot checks look for (isPlaywright signatures).
_ARTIFACT_STRIP_SCRIPT = """
(() => {
  const scrub = (root) => {
    for (const key of Object.getOwnPropertyNames(root)) {
      if (/^(?:__)?(?:pw|playwright)/i.test(key) || /^pw/i.test(key)) {
        try { delete root[key]; } catch {}
      }
    }
    try {
      Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true,
      });
    } catch {}
    if (!window.chrome) {
      window.chrome = { runtime: {} };
    }
  };
  scrub(window);
})();
"""

_STEALTH = None
_POOL_LOCK = threading.Lock()
_POOL: dict = {"ctx": None, "browser_mode": None, "stealth": None, "engine": None}


def _resolve_engine(engine: str | None = None) -> Engine:
    raw = (engine or os.getenv("GEMINI_WEB_ENGINE", "playwright")).strip().lower()
    if raw in ("patchright", "patch"):
        return "patchright"
    return "playwright"


def _sync_playwright_factory(engine: Engine):
    if engine == "patchright":
        from patchright.sync_api import sync_playwright

        return sync_playwright
    from playwright.sync_api import sync_playwright

    return sync_playwright


def _get_stealth():
    global _STEALTH
    if _STEALTH is not None:
        return _STEALTH
    try:
        from playwright_stealth import Stealth

        # Real Chrome already has genuine UA/GPU/plugins — only patch automation leaks.
        _STEALTH = Stealth(
            navigator_user_agent=False,
            navigator_user_agent_data=False,
            navigator_platform=False,
            webgl_vendor=False,
            navigator_webdriver=True,
            chrome_runtime=True,
        )
    except ImportError:
        _STEALTH = False
    return _STEALTH


def _env_browser_mode() -> BrowserMode | None:
    raw = os.getenv("GEMINI_WEB_BROWSER", "").strip().lower()
    if raw in ("visible", "headed", "show"):
        return "visible"
    if raw in ("invisible", "hidden", "stealth-window"):
        return "invisible"
    if raw == "headless":
        return "headless"
    legacy = os.getenv("GEMINI_WEB_HEADED", "").strip().lower()
    if legacy in ("1", "true", "yes", "on"):
        return "visible"
    if legacy in ("0", "false", "no", "off"):
        return "invisible"
    return None


def _resolve_browser_mode(
    mode: str,
    headed: bool,
    headless: bool,
    *,
    for_login: bool = False,
) -> BrowserMode:
    if for_login:
        return "visible"
    if headless:
        return "headless"
    if headed:
        return "visible"
    env = _env_browser_mode()
    if env is not None:
        return env
    # Default: invisible headed Chrome (real renderer, no on-screen flash).
    return "invisible"


def _resolve_stealth(stealth: bool, no_stealth: bool) -> bool:
    if no_stealth:
        return False
    if stealth:
        return True
    raw = os.getenv("GEMINI_WEB_STEALTH", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


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
        pass
    try:
        import patchright  # noqa: F401
        return True
    except ImportError:
        return False


def _install_hint() -> str:
    return (
        "BROWSER_DRIVER_MISSING: run once:\n"
        "  py -m pip install playwright patchright playwright-stealth\n"
        "  py -m playwright install chrome\n"
        "  py -m patchright install chrome"
    )


def _compose_prompt(prompt: str, system: str) -> str:
    prompt = (prompt or "").strip()
    system = (system or "").strip()
    if not system:
        return prompt
    return f"{system.strip()}\n\n---\n\n{prompt}"


def _launch_context(browser_mode: BrowserMode, stealth: bool = True, engine: Engine = "playwright"):
    sync_playwright = _sync_playwright_factory(engine)
    PROFILE.mkdir(parents=True, exist_ok=True)
    pw = sync_playwright().start()
    chrome_args = list(STEALTH_CHROME_ARGS)
    if browser_mode == "invisible":
        chrome_args.extend(INVISIBLE_CHROME_ARGS)

    launch_kwargs = {
        "user_data_dir": str(PROFILE),
        "headless": browser_mode == "headless",
        "locale": "en-US",
        "timezone_id": os.getenv("GEMINI_WEB_TZ", "America/New_York"),
        "ignore_default_args": ["--enable-automation"],
        "args": chrome_args,
    }
    if browser_mode == "headless":
        launch_kwargs["viewport"] = {"width": 1920, "height": 1080}
    else:
        launch_kwargs["no_viewport"] = True

    # Patched Chromium hides headless markers; system Chrome headless still leaks HeadlessChrome.
    use_chrome_channel = browser_mode != "headless"
    if engine == "patchright" and os.getenv("GEMINI_WEB_PATCHRIGHT_CHANNEL", "").strip() in ("1", "true", "yes"):
        use_chrome_channel = True
    try:
        if use_chrome_channel:
            ctx = pw.chromium.launch_persistent_context(
                channel="chrome",
                **launch_kwargs,
            )
        else:
            ctx = pw.chromium.launch_persistent_context(**launch_kwargs)
    except Exception as chrome_err:
        if browser_mode in ("invisible", "visible"):
            raise RuntimeError(
                "REAL_CHROME_REQUIRED: Google Chrome must be available for invisible/visible mode. "
                "Close other gemini_web/bifrost_runner instances if the profile is locked. "
                f"({chrome_err})"
            ) from chrome_err
        try:
            ctx = pw.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as fallback_err:
            raise RuntimeError(
                f"Could not launch {engine} context (chrome channel and bundled both failed). "
                f"chrome: {chrome_err}; fallback: {fallback_err}"
            ) from fallback_err

    if stealth and engine == "playwright":
        ctx.add_init_script(_ARTIFACT_STRIP_SCRIPT)
        stealth_obj = _get_stealth()
        if stealth_obj:
            stealth_obj.apply_stealth_sync(ctx)
    elif stealth:
        # Patchright patches CDP at driver level; still strip Playwright-ish window keys.
        ctx.add_init_script(_ARTIFACT_STRIP_SCRIPT)

    ctx._akashic_pw = pw  # keep playwright/patchright alive until context closes
    ctx._akashic_browser_mode = browser_mode
    ctx._akashic_engine = engine
    return ctx


def close_browser_pool() -> None:
    """Release the warm browser used by bifrost_runner (safe to call repeatedly)."""
    with _POOL_LOCK:
        ctx = _POOL.get("ctx")
        if ctx is not None:
            _close_context(ctx)
        _POOL["ctx"] = None
        _POOL["browser_mode"] = None
        _POOL["stealth"] = None
        _POOL["engine"] = None


def _acquire_context(
    browser_mode: BrowserMode,
    stealth: bool,
    reuse_browser: bool,
    engine: Engine = "playwright",
) -> tuple[object, bool]:
    """Return (context, should_close_after_use)."""
    with _POOL_LOCK:
        if reuse_browser and _POOL["ctx"] is not None:
            if (
                _POOL["browser_mode"] == browser_mode
                and _POOL["stealth"] == stealth
                and _POOL["engine"] == engine
            ):
                return _POOL["ctx"], False
            _close_context(_POOL["ctx"])
            _POOL["ctx"] = None

        ctx = _launch_context(browser_mode, stealth=stealth, engine=engine)
        if reuse_browser:
            _POOL["ctx"] = ctx
            _POOL["browser_mode"] = browser_mode
            _POOL["stealth"] = stealth
            _POOL["engine"] = engine
            return ctx, False
        return ctx, True


def _close_context(ctx) -> None:
    pw = getattr(ctx, "_akashic_pw", None)
    try:
        ctx.close()
    finally:
        if pw is not None:
            pw.stop()


def _looks_logged_out(page, surface: str = "gemini") -> bool:
    url = (page.url or "").lower()
    if "accounts.google.com" in url or "ServiceLogin" in url:
        return True
    # Google Search often shows a header Sign in even when the session is valid.
    if surface == "search":
        return False
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


def _extract_ai_mode_response(page, prompt: str) -> str:
    selectors = [
        "[data-subtree='aim']",
        "[data-aim-timestamp]",
        ".AIrHhb",
        ".WaaZC",
        ".model-response-text",
        '[data-message-author-role="model"]',
        "#search div[lang]",
    ]
    for sel in selectors:
        loc = page.locator(sel)
        try:
            if loc.count():
                txt = loc.first.inner_text(timeout=2000).strip()
                if txt and len(txt) >= 3 and prompt[:30] not in txt:
                    return txt
        except Exception:
            continue

    try:
        body = page.locator("body").inner_text(timeout=3000)
    except Exception:
        return ""

    if "You said:" in body:
        chunk = body.split("You said:", 1)[-1]
        if prompt.strip() in chunk:
            chunk = chunk.split(prompt.strip(), 1)[-1]
        for marker in (
            "AI Mode response is ready",
            "Footer Links",
            "People also ask",
            "Quora",
            "Learn more",
            "Skip to main content",
            "Wikipedia",
            "If you are exploring",
            "If you'd like to explore",
        ):
            if marker in chunk:
                chunk = chunk.split(marker, 1)[0]
        chunk = chunk.replace("\u200b", "").strip()
        lines = []
        for ln in chunk.splitlines():
            stripped = ln.strip()
            if stripped in ("+1", "+2", "+3", "+4", "+5", "+6", "+7", "+8"):
                continue
            lines.append(ln)
        chunk = "\n".join(lines).strip()
        if len(chunk) >= 3:
            return chunk

    if "AI Mode is not currently available" in body:
        return (
            "AI_MODE_UNAVAILABLE: Google AI Mode is not enabled for this account, "
            "region, or device. Try --mode gemini (gemini.google.com) instead."
        )
    return ""


def _warm_google_session(page, timeout_ms: int) -> None:
    """Land on google.com like a normal tab before AI Mode (less bot-like than cold ?udm=50)."""
    try:
        page.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(900)
    except Exception:
        pass


def _ask_ai_mode(page, prompt: str, timeout_ms: int) -> str:
    _warm_google_session(page, timeout_ms)
    q = urllib.parse.quote_plus(prompt[:1500])
    url = f"https://www.google.com/search?q={q}&udm=50&hl=en"
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(2500)
    if _looks_logged_out(page, surface="search"):
        return _login_hint()

    body = ""
    try:
        body = page.locator("body").inner_text(timeout=3000)
    except Exception:
        pass
    if "AI Mode is not currently available" in body:
        return (
            "AI_MODE_UNAVAILABLE: Google AI Mode is not enabled for this account, "
            "region, or device. Use --mode gemini (gemini.google.com) instead."
        )

    deadline = time.time() + (timeout_ms / 1000.0)
    last = ""
    while time.time() < deadline:
        txt = _extract_ai_mode_response(page, prompt)
        if txt and not txt.startswith("AI_MODE_UNAVAILABLE"):
            if txt == last and len(txt) >= 3:
                return txt
            last = txt
        page.wait_for_timeout(1500)
    txt = _extract_ai_mode_response(page, prompt)
    if txt:
        return txt
    return "AI_MODE_ERROR: no AI Mode answer captured (region/login/UI drift). Try --login or --headed."


def _ask_via_api(prompt: str, system: str) -> str:
    cmd = [sys.executable, str(ROOT / "scripts" / "ask_gemini.py")]
    if system:
        cmd += ["--system", system]
    cmd.append(prompt)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = (p.stdout or p.stderr or "").strip()
    return out or f"API_ERROR: exit {p.returncode}"


def ask_web_message(
    prompt: str,
    mode: str = "gemini",
    system: str = "",
    *,
    browser_mode: BrowserMode | None = None,
    headed: bool = False,
    headless: bool = False,
    stealth: bool = True,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    reuse_browser: bool = False,
    engine: Engine | None = None,
) -> str:
    """Ask Gemini via the web UI. Default browser_mode=invisible (off-screen real Chrome)."""
    if not _needs_playwright():
        return _install_hint()
    composed = _compose_prompt(prompt, system)
    if not composed.strip():
        return "NO_PROMPT: empty prompt"
    resolved_engine = engine or _resolve_engine()
    resolved_mode = browser_mode or _resolve_browser_mode(mode, headed, headless)
    use_stealth = _resolve_stealth(stealth, no_stealth=False)
    ctx, should_close = _acquire_context(
        resolved_mode, use_stealth, reuse_browser, engine=resolved_engine,
    )
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if mode == "gemini":
            return _ask_gemini_chat(page, composed, timeout_ms)
        if mode == "ai_mode":
            return _ask_ai_mode(page, composed, timeout_ms)
        return f"UNKNOWN_MODE: {mode}"
    finally:
        if should_close:
            _close_context(ctx)


def _ask_web(
    mode: str,
    prompt: str,
    *,
    headed: bool,
    headless: bool,
    stealth: bool,
    timeout_ms: int,
    engine: Engine | None = None,
) -> str:
    return ask_web_message(
        prompt,
        mode=mode,
        browser_mode=_resolve_browser_mode(mode, headed, headless),
        headed=headed,
        headless=headless,
        stealth=stealth,
        timeout_ms=timeout_ms,
        reuse_browser=False,
        engine=engine,
    )


def cmd_probe(
    headed: bool,
    headless: bool,
    stealth: bool,
    timeout_ms: int,
    engine: Engine | None = None,
) -> int:
    if not _needs_playwright():
        print(_install_hint(), file=sys.stderr)
        return 2
    resolved_engine = engine or _resolve_engine()
    browser_mode = _resolve_browser_mode("ai_mode", headed, headless)
    ctx = _launch_context(browser_mode, stealth=stealth, engine=resolved_engine)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(1200)
        webdriver = page.evaluate("() => navigator.webdriver")
        ua = page.evaluate("() => navigator.userAgent")
        print(f"engine={resolved_engine} browser_mode={browser_mode} stealth={stealth}")
        print(f"navigator.webdriver={webdriver!r}")
        print(f"userAgent={ua[:100]}...")
        page.goto(
            "https://www.google.com/search?q=hello&udm=50&hl=en",
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
        page.wait_for_timeout(3000)
        body = page.locator("body").inner_text(timeout=5000)
        if "AI Mode is not currently available" in body:
            print("AI_MODE_GATE: unavailable message still shown")
            print(body[:600])
        elif "Meet AI Mode" in body or "udm=50" in page.url:
            print("AI_MODE_GATE: page loaded — checking for answer surface...")
            print(body[:600])
        else:
            print("AI_MODE_GATE: unknown state")
            print(body[:600])
    finally:
        _close_context(ctx)
    return 0


def cmd_login(headed: bool = True, stealth: bool = True) -> int:
    if not _needs_playwright():
        print(_install_hint(), file=sys.stderr)
        return 2
    print(f"Opening browser for one-time Google login.\nProfile: {PROFILE}")
    print("Sign in as your Google account (or whichever account you want).")
    print("Visit Gemini + Google, then close the browser window when done.\n")
    ctx = _launch_context("visible", stealth=stealth)
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
    ap.add_argument("--headed", action="store_true", help="show browser window (debug / login-style)")
    ap.add_argument("--headless", action="store_true", help="force headless (AI Mode may be gated)")
    ap.add_argument(
        "--stealth",
        action="store_true",
        help="apply stealth patches (default on; use --no-stealth to disable)",
    )
    ap.add_argument("--no-stealth", action="store_true", help="disable stealth patches (debug)")
    ap.add_argument("--login", action="store_true", help="one-time Google login setup")
    ap.add_argument("--probe", action="store_true", help="print AI Mode gate diagnostics (no prompt needed)")
    ap.add_argument(
        "--engine",
        choices=("playwright", "patchright"),
        default=None,
        help="automation driver (patchright = patched Playwright, better headless stealth)",
    )
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_MS, help="ms")
    args = ap.parse_args()
    resolved_engine = _resolve_engine(args.engine)

    if args.login:
        return cmd_login(headed=True, stealth=_resolve_stealth(args.stealth, args.no_stealth))

    if args.probe:
        return cmd_probe(
            headed=args.headed,
            headless=args.headless,
            stealth=_resolve_stealth(args.stealth, args.no_stealth),
            timeout_ms=min(args.timeout, 60000),
            engine=resolved_engine,
        )

    prompt = _compose_prompt(_prompt_from_args(args), args.system)
    if not prompt.strip():
        print("NO_PROMPT: pass text, --file, or pipe via stdin", file=sys.stderr)
        return 2

    stealth_on = _resolve_stealth(args.stealth, args.no_stealth)
    browser_mode = _resolve_browser_mode(args.mode, args.headed, args.headless)

    if args.mode == "api":
        print(_ask_via_api(prompt, ""))
        return 0

    if args.mode == "both":
        g = _ask_web(
            "gemini",
            prompt,
            headed=args.headed,
            headless=args.headless,
            stealth=stealth_on,
            timeout_ms=args.timeout,
            engine=resolved_engine,
        )
        a = _ask_web(
            "ai_mode",
            prompt,
            headed=args.headed,
            headless=args.headless,
            stealth=stealth_on,
            timeout_ms=args.timeout,
            engine=resolved_engine,
        )
        print(f"========================= GEMINI (web) =========================\n{g}")
        print(f"\n========================= GOOGLE AI MODE =========================\n{a}")
        print(
            f"\n[engine={resolved_engine}, stealth={stealth_on}, browser_mode={browser_mode}]",
            file=sys.stderr,
        )
        return 0

    print(
        _ask_web(
            args.mode,
            prompt,
            headed=args.headed,
            headless=args.headless,
            stealth=stealth_on,
            timeout_ms=args.timeout,
            engine=resolved_engine,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
