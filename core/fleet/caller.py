"""The direct caller -- one-shot invocation of a local model for a BOUNDED subtask.

Semantic Relationship: FleetCaller invokes Model (Ollama /api/generate).

The only way to run a local model used to be launching a full Claude Code session -- right for
multi-step work, absurd for "summarize this" / "classify this" / "extract these fields". This is the
missing primitive: call(tag, prompt) -> text. Composing a few of these is how the pool gets stronger
per GB (draft-then-verify, classify->route->specialist; see docs/library/design/20260709_fleet-dispatch-an-intelligent-easy-struc_303d15.md).

stdlib-only (urllib + json). Hermetic under test: `opener` is injectable, so no network is touched.
Unlike the fail-soft READS in roster, a call RAISES on failure -- a subtask that asks for a result must
never get a silent "" it could mistake for the answer.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from core.fleet import model_roster as roster


class FleetCallError(RuntimeError):
    """A local-model call failed (network, HTTP, bad response, or empty generation). Carried to the
    door, which prints it cleanly -- a visible failure, never a silent empty string."""


# Ollama's default context is 4K under <24GB VRAM and silently truncates from the START of the prompt.
# When a tag isn't in the roster we still want a safe floor rather than that trap.
_CTX_FLOOR = 32000


def call(tag: str, prompt: str, *, system: Optional[str] = None, max_tokens: int = 512,
         temperature: float = 0.2, fmt: Any = None, timeout: float = 120.0,
         host: Optional[str] = None, opener: Any = None) -> str:
    """Run `prompt` through the local model `tag` and return its text.

    - num_ctx is pinned from the roster spec (falls back to a safe floor) so even a one-shot call
      inherits the truncation defense an agentic session gets.
    - temperature defaults to 0.2 (higher -> malformed output on small models).
    - fmt="json" sets Ollama's `format` for constrained JSON (small models emit 0% USABLE json under
      naive prompting -- R013 finding 7); fmt may also be a JSON-schema dict for stricter grammars.
    - opener is injectable (default urllib.request.urlopen) so tests stay hermetic.
    Raises FleetCallError on any failure."""
    if not tag or not prompt:
        raise FleetCallError("call needs a model tag and a non-empty prompt")
    spec = roster.get(tag) or {}
    resolved_host = host or spec.get("host") or roster.default_host()
    num_ctx = int(spec.get("context") or _CTX_FLOOR)

    options = {"temperature": float(temperature), "num_ctx": num_ctx, "num_predict": int(max_tokens)}
    payload: dict = {"model": tag, "prompt": prompt, "stream": False, "options": options}
    if system:
        payload["system"] = system
    if fmt is not None:
        payload["format"] = fmt   # "json" or a JSON-schema dict, per Ollama's structured-output API

    url = resolved_host.rstrip("/") + "/api/generate"
    try:
        import urllib.request
        opener = opener or urllib.request.urlopen
        req = urllib.request.Request(
            url, method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with opener(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except Exception as e:
        raise FleetCallError(f"call to {tag} at {url} failed: {e}") from e

    try:
        data = json.loads(body)
    except Exception as e:
        raise FleetCallError(f"call to {tag} returned non-JSON: {body[:200]!r}") from e

    text = data.get("response")
    if text is None:
        # Ollama surfaces model/loading errors in an 'error' field with HTTP 200.
        err = data.get("error")
        raise FleetCallError(f"call to {tag} returned no 'response'"
                             + (f" (ollama error: {err})" if err else f": {str(data)[:200]}"))
    return text
