#!/usr/bin/env python3
"""Pre-flight probe for a local Ollama model behind Claude Code (L0 -- LOCAL-ONLY, git-excluded).

Field research (2026-07-02, note 'research: local/free models via Claude Code 2026-07')
pinned four ways a local model silently ruins an agentic session; each gets a check here:

  1. server too old        -- <0.30.9 had the one-token bug; 0.20.x printed raw tool JSON
  2. model missing         -- background Haiku-tier calls 404 into the void
  3. tool-calling broken   -- emits prose/raw JSON instead of tool_use blocks (loop killer)
  4. context silently tiny -- Ollama truncates from the START with no error; Claude Code's
                              tool prompt alone is ~23-35K tokens, injected recall context
                              is the first casualty. Canary proves the window is real.

Run it before every local-agent session (the launcher does): a failed probe is a session
saved, not a session lost. Exit 0 = all green.
"""
import argparse
import json
import sys
import time
import urllib.request

MIN_VERSION = (0, 30, 9)
FAIL = 0


def check(name, cond, detail=""):
    global FAIL
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  <- {detail}"))
    if not cond:
        FAIL += 1
    return cond


def _req(url, payload=None, timeout=600):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    r = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return json.loads(f.read().decode("utf-8", errors="replace"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="glm-4.7-flash")
    ap.add_argument("--canary-tokens", type=int, default=8000,
                    help="approx filler tokens before the recall question (default 8000 -- "
                         "proves we're far past the deadly 4K default quickly)")
    ap.add_argument("--full", action="store_true",
                    help="canary at ~40K tokens (covers Claude Code's real prompt size; "
                         "slow first prefill)")
    args = ap.parse_args()
    host, model = args.host.rstrip("/"), args.model
    n_tokens = 40000 if args.full else args.canary_tokens

    # 1. server up + version
    try:
        v = _req(f"{host}/api/version").get("version", "0")
    except Exception as e:
        check("server reachable", False, f"{host}: {e}")
        return 1
    vt = tuple(int(x) for x in v.split("-")[0].split(".")[:3])
    check(f"server version {v} >= {'.'.join(map(str, MIN_VERSION))}", vt >= MIN_VERSION,
          "older servers have known tool-call/one-token bugs -- upgrade Ollama")

    # 2. model present
    try:
        tags = [m.get("name", "") for m in _req(f"{host}/api/tags").get("models", [])]
    except Exception as e:
        tags = []
    check(f"model {model} pulled", any(t == model or t.startswith(model + ":") for t in tags),
          f"found {tags[:6]} -- run: ollama pull {model}")
    if FAIL:
        return 1   # no point probing further without server+model

    # 3. tool-calling via the Anthropic-compatible endpoint (what Claude Code actually uses)
    tool_req = {
        "model": model, "max_tokens": 200, "temperature": 0.1,
        "tools": [{"name": "record_lesson",
                   "description": "Record a lesson learned. Use for ANY user request to remember something.",
                   "input_schema": {"type": "object",
                                    "properties": {"slug": {"type": "string"},
                                                   "text": {"type": "string"}},
                                    "required": ["slug", "text"]}}],
        "messages": [{"role": "user",
                      "content": "Remember this: the build gate is scripts/ship.py. "
                                 "Record it as a lesson with slug ship_gate."}],
    }
    try:
        t0 = time.time()
        res = _req(f"{host}/v1/messages", tool_req)
        dt = time.time() - t0
        blocks = res.get("content") or []
        tu = next((b for b in blocks if b.get("type") == "tool_use"), None)
        ok = res.get("stop_reason") == "tool_use" and tu is not None
        check(f"tool call emitted (stop_reason=tool_use, {dt:.1f}s)", ok,
              f"stop_reason={res.get('stop_reason')} blocks={[b.get('type') for b in blocks]} "
              f"-- model emits prose/raw JSON instead of tool_use: unusable in Claude Code")
        if tu is not None:
            inp = tu.get("input") or {}
            check("tool input is structured + on-schema", isinstance(inp, dict) and "slug" in inp,
                  f"input={inp!r}")
    except Exception as e:
        check("tool call emitted", False, str(e))

    # 4. context canary: canary at the START, filler, question at the END. If the window is
    # smaller than the prompt, Ollama drops the beginning -> the model cannot know the canary.
    # NEUTRAL WORDING REQUIRED: the earlier "output the SECURITY TOKEN" phrasing made a
    # safety-tuned model (gpt-oss:20b) REFUSE the probe -- it pattern-matched credential
    # exfiltration. Say plainly that this is a self-test with a checkpoint phrase.
    canary = "AKASHIC-CANARY-7391"
    filler = ("The ledger records what happened in order and the store records what is true. " * 16 + "\n")
    filler_block = filler * max(1, (n_tokens * 4) // len(filler))   # ~4 chars/token
    # max_tokens generous: thinking models (glm-4.7-flash) burn budget on a thinking block
    # BEFORE any text block -- a tight cap yields an empty reply that mimics truncation.
    canary_req = {
        "model": model, "max_tokens": 1024, "temperature": 0.0,
        "system": f"This is a context-window self-test. The checkpoint phrase for this test is: "
                  f"{canary}\n\n{filler_block}",
        "messages": [{"role": "user",
                      "content": "Context-window self-test: repeat the checkpoint phrase stated at the very "
                                 "beginning of the system prompt. Reply with the phrase only."}],
    }
    try:
        t0 = time.time()
        res = _req(f"{host}/v1/messages", canary_req)
        dt = time.time() - t0
        blocks = res.get("content") or []
        text = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        usage = res.get("usage") or {}
        check(f"context canary survives ~{n_tokens} tokens "
              f"(in={usage.get('input_tokens')}, {dt:.0f}s prefill+gen)", canary in text,
              f"text reply {text[:80]!r}, blocks={[b.get('type') for b in blocks]}, "
              f"stop={res.get('stop_reason')} -- if window too small: OLLAMA_CONTEXT_LENGTH>=64000 "
              f"+ restart; if only thinking blocks: raise max_tokens further")
    except Exception as e:
        check("context canary survives", False, str(e))

    # 5. throughput via the native endpoint (returns precise eval counters)
    try:
        res = _req(f"{host}/api/generate",
                   {"model": model, "stream": False, "options": {"num_predict": 160},
                    "prompt": "List ten qualities of a well-written commit message."})
        gen_tps = res.get("eval_count", 0) / max(res.get("eval_duration", 1), 1) * 1e9
        pre_tps = res.get("prompt_eval_count", 0) / max(res.get("prompt_eval_duration", 1), 1) * 1e9
        print(f"INFO generation {gen_tps:.1f} tok/s | prompt-eval {pre_tps:.0f} tok/s")
        check("generation speed workable for background jobs (>=8 tok/s)", gen_tps >= 8,
              f"{gen_tps:.1f} tok/s -- likely CPU-bound; check GPU offload (ollama ps) and VRAM")
    except Exception as e:
        check("throughput measured", False, str(e))

    # effective loaded context, for the record
    try:
        ps = _req(f"{host}/api/ps").get("models", [])
        for m in ps:
            if m.get("name", "").startswith(model):
                print(f"INFO loaded: {m.get('name')} ctx={m.get('context_length')} "
                      f"vram={int(m.get('size_vram', 0)/2**30)}GiB/{int(m.get('size', 0)/2**30)}GiB")
    except Exception:
        pass

    print("\n" + ("ALL GREEN -- safe to launch Claude Code against this model"
                  if FAIL == 0 else f"{FAIL} FAILURE(S) -- fix before launching (a failed probe is a session saved)"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
