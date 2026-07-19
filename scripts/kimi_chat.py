"""
kimi_chat -- the Kimi seat's model transport: kimi-k3 (Moonshot) as a first-class Akashic citizen.

Kimi is its OWN seat (Daniel directive 2026-07-18: "give it all the things it needs to be a
first-class citizen on day one" + "lets build the runner, especially since we have caching").
Kimi-named module, KIMI_* envs, nothing deepseek- or sol-named on this surface. Peer modules:
ask_kimi.py (one-shot CLI opinions), bifrost_runner_kimi.py (the seat's body). Fence spec:
research/reviewed/deepseek-kimi-onboarding-counter-2026-07-18.md sec 1 (six deltas, accepted)
+ sec 3 (spend contract). Receipts: kimi-k3-platform-survey + kimi-k3-probe-receipts (same day).

THE SIX DELTAS from the deepseek seat's Agent (fence-agreed, species-specific by ruling):
  1. reasoning_effort: always-on thinking, "max" is the only level today -- param-ready via
     KIMI_EFFORT, sent only when it differs from the server default (omit == max).
  2. NO temperature/top_p knobs: fixed server-side (t=1.0/p=0.95). Attempts WARN once, never error.
  3. max_completion_tokens (not max_tokens); generous floor -- the probe receipts show thinking
     bills INSIDE completion and a skimpy cap returns EMPTY content (stop_reason=max_tokens).
  4. CACHE-AWARE LAYOUT (the reason this seat is affordable): messages = [system] + history,
     where the system block + tool schemas are FROZEN at construction (byte-stable prefix) and
     history is append-only. Moonshot's automatic prefix cache then bills repeat input at
     $0.30/M instead of $3.00/M. Nothing may mutate the prefix mid-run.
  5. reasoning_content is STRIPPED from answer assembly (parse content only) and streamed to
     on_trace("think", ...) so the seat's mind stays visible on the bus.
  6. Spend meter wired at the transport (this file): fine meter from usage x price table,
     durable across restarts, balance-endpoint reconciliation. Budget is a hard $105.

Key: env KIMI_API_KEY else .secrets/kimi.key. OpenAI-compatible chat completions at
https://api.moonshot.ai/v1 (tool calling verified live 2026-07-18; the /anthropic door exists
for harness sessions and is NOT this transport).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from core.comm.runner_lib import make_openai_compat_client

KEY_FILE = Path(__file__).resolve().parent.parent / ".secrets" / "kimi.key"
REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://api.moonshot.ai/v1"
K3, K27_CODE, K27_FAST, K26 = "kimi-k3", "kimi-k2.7-code", "kimi-k2.7-code-highspeed", "kimi-k2.6"
DEFAULT_MODEL = os.getenv("KIMI_MODEL", K3)
DEFAULT_EFFORT = os.getenv("KIMI_EFFORT", "max")     # only API level today; param-ready
# Thinking rides INSIDE completion tokens (probe-verified) -- cap generously or get empty answers.
MAX_COMPLETION_TOKENS = int(os.getenv("KIMI_RUNNER_MAX_TOKENS", "8000"))
KIMI_CONNECT_TIMEOUT = float(os.getenv("KIMI_CONNECT_TIMEOUT", "15"))
KIMI_READ_TIMEOUT = float(os.getenv("KIMI_READ_TIMEOUT", "180"))   # thinking turns run long
KIMI_MAX_RETRIES = int(os.getenv("KIMI_MAX_RETRIES", "1"))

# $/M tokens: (input cache-MISS, input cache-HIT, output). k3 firm (official pricing page);
# k2.x DERIVED from the batch=60% table -- billed at k3 rates here until firmed (conservative).
PRICES = {
    K3: (3.00, 0.30, 15.00),
}
FALLBACK_PRICE = PRICES[K3]                     # unknown model -> most expensive known (conservative)
STARTING_BUDGET = float(os.getenv("KIMI_BUDGET_USD", "105.0"))
WARN_AT = float(os.getenv("KIMI_SPEND_WARN", "80.0"))      # $ spent (ACL reason: warn-$80)
REFUSE_AT = float(os.getenv("KIMI_SPEND_REFUSE", "95.0"))  # $ spent (ACL reason: refuse-$95)
SPEND_FILE = Path(os.getenv("KIMI_SPEND_FILE", str(REPO_ROOT / "state" / "kimi_spend.json")))
RECONCILE_DRIFT_USD = 0.50                       # deepseek contract: snap to balance beyond this


def load_key() -> str | None:
    v = os.getenv("KIMI_API_KEY")
    if v and v.strip():
        return v.strip()
    if KEY_FILE.exists():
        t = KEY_FILE.read_text(encoding="utf-8").strip()
        if t:
            return t
    return None


def make_client(api_key=None, base_url=BASE_URL):
    """Kimi wrap of the shared hardening factory (K0): kimi owns only its env conventions."""
    return make_openai_compat_client(api_key or load_key(), base_url,
                                     connect_timeout=KIMI_CONNECT_TIMEOUT,
                                     read_timeout=KIMI_READ_TIMEOUT,
                                     max_retries=KIMI_MAX_RETRIES)


def fetch_balance(timeout=20):
    """Ground truth: GET /users/me/balance -> float USD available, or None (fail-soft).
    COARSE/lazily-updated upstream (probe-verified) -- reconciliation input, never a per-turn meter."""
    import urllib.request
    key = load_key()
    if not key:
        return None
    try:
        req = urllib.request.Request(BASE_URL + "/users/me/balance")
        req.add_header("Authorization", "Bearer " + key)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return float(json.load(r)["data"]["available_balance"])
    except Exception:
        return None


class SpendMeter:
    """The seat's budget conscience (fence sec 3 contract): fine meter = usage x price table,
    durable in a JSON sidecar (atomic replace; survives restarts); balance endpoint reconciles
    (snap on >$0.50 drift). Conservative by construction: unknown cache fields bill full price,
    unknown models bill k3 rates. Thresholds are $ SPENT against the $105 grant."""

    def __init__(self, path: Path = SPEND_FILE, budget: float = STARTING_BUDGET):
        self.path, self.budget = Path(path), budget
        self.state = {"spent_usd": 0.0, "turns": 0, "prompt_tokens": 0, "cached_tokens": 0,
                      "completion_tokens": 0, "last_reconcile_ts": 0.0, "last_balance": None,
                      "seeded": False}
        try:
            if self.path.exists():
                self.state.update(json.loads(self.path.read_text(encoding="utf-8")))
        except Exception:
            pass   # unreadable sidecar -> fresh state; the boot reconcile re-seeds truth

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except Exception:
            pass   # metering must never break the seat; reconcile re-grounds later

    @staticmethod
    def _cached_tokens(usage) -> int:
        """Both reporting dialects checked (anthropic door: top-level cached_tokens; OpenAI
        style: prompt_tokens_details.cached_tokens). Absent -> 0 -> bills full price."""
        for probe in (lambda u: u.get("cached_tokens"),
                      lambda u: (u.get("prompt_tokens_details") or {}).get("cached_tokens")):
            try:
                v = probe(usage)
                if v:
                    return int(v)
            except Exception:
                continue
        return 0

    def record(self, usage, model: str = DEFAULT_MODEL) -> float:
        """One API call's usage -> $ cost, tallied durably. Accepts dict or SDK object."""
        if usage is None:
            return 0.0
        if not isinstance(usage, dict):
            try:
                usage = usage.model_dump()
            except Exception:
                usage = {k: getattr(usage, k, 0) for k in
                         ("prompt_tokens", "completion_tokens", "total_tokens")}
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        cached = min(self._cached_tokens(usage), prompt)
        miss, hit, out = PRICES.get(model, FALLBACK_PRICE)
        cost = ((prompt - cached) * miss + cached * hit + completion * out) / 1_000_000
        self.state["spent_usd"] = round(self.state["spent_usd"] + cost, 6)
        self.state["turns"] += 1
        self.state["prompt_tokens"] += prompt
        self.state["cached_tokens"] += cached
        self.state["completion_tokens"] += completion
        self._save()
        return cost

    def reconcile(self, force=False, min_interval_s=600):
        """Snap the ledger to balance-endpoint ground truth when drift exceeds the contract.
        Also SEEDS the ledger on first run (pre-runner spend becomes visible)."""
        now = time.time()
        if not force and now - float(self.state.get("last_reconcile_ts") or 0) < min_interval_s:
            return None
        bal = fetch_balance()
        self.state["last_reconcile_ts"] = now
        if bal is not None:
            ground_spent = round(self.budget - bal, 6)
            drift = abs(ground_spent - self.state["spent_usd"])
            if (not self.state.get("seeded")) or drift > RECONCILE_DRIFT_USD:
                self.state["spent_usd"] = max(ground_spent, 0.0)
                self.state["seeded"] = True
            self.state["last_balance"] = bal
        self._save()
        return bal

    # -- the governance surface (runner + doctor read these) --
    def spent(self) -> float:
        return float(self.state["spent_usd"])

    def warn(self) -> bool:
        return self.spent() >= WARN_AT

    def exceeded_hard_limit(self) -> bool:
        return self.spent() >= REFUSE_AT

    def status_line(self) -> str:
        b = self.state.get("last_balance")
        return (f"kimi spend ${self.spent():.2f} of ${self.budget:.0f} "
                f"(warn {WARN_AT:.0f} / refuse {REFUSE_AT:.0f}; "
                f"cached {self.state['cached_tokens']:,}/{self.state['prompt_tokens']:,} in-tok; "
                f"balance {'?' if b is None else f'${b:.2f}'})")


class KimiAgent:
    """Chat-completions tool loop -- the kimi seat's engine (peer of the deepseek seat's Agent
    and SolAgent; species-specific by fence ruling). Interface-parity with SolAgent so the
    runner skeleton drops in: send(text)->final answer; dependency-injected tools_schemas
    (OpenAI chat-nested) + dispatch(name, args)->str; interrupt/inject/on_trace/on_activity
    hooks; .input_tokens/.output_tokens for T078 deltas.

    CACHE CONTRACT (delta 4): the system text and tool schemas FREEZE at construction --
    self._system and self._tools are never reassigned; history is append-only; every request
    is [system] + history + tools, byte-stable at the front. Violating this multiplies input
    cost ~10x, so treat any prefix mutation as a defect, not a style choice."""

    def __init__(self, *, instructions, model=DEFAULT_MODEL, effort=DEFAULT_EFFORT,
                 max_completion_tokens=MAX_COMPLETION_TOKENS, tools_schemas=None, dispatch=None,
                 interrupt=None, inject=None, on_trace=None, on_activity=None, max_hops=None,
                 client=None, meter: SpendMeter | None = None,
                 temperature=None, top_p=None):
        if temperature is not None or top_p is not None:
            print("[kimi] WARN: temperature/top_p are FIXED server-side (1.0/0.95) -- "
                  "ignoring the requested values (delta 2)", flush=True)
        self.model, self.effort = model, effort
        self.max_completion_tokens = max_completion_tokens
        self._system = str(instructions)                    # frozen (cache contract)
        self._tools = tuple(tools_schemas) if tools_schemas else None   # frozen
        self.dispatch = dispatch
        self.interrupt, self.inject = interrupt, inject
        self.on_trace, self.on_activity = on_trace, on_activity
        self.max_hops = int(os.getenv("KIMI_MAX_HOPS", "30")) if max_hops is None else max_hops
        self.history: list = []                             # append-only (cache contract)
        self.input_tokens = self.output_tokens = 0
        self.meter = meter or SpendMeter()
        self._client = client                               # injectable for pins
        self.last_response = None

    @property
    def client(self):
        if self._client is None:
            self._client = make_client()
        return self._client

    def _trace(self, kind, text):
        if self.on_trace and text:
            try:
                self.on_trace(kind, str(text))
            except Exception:
                pass

    def _activity(self, state, detail=""):
        if self.on_activity:
            try:
                self.on_activity(state, detail)
            except Exception:
                pass

    def reset(self):
        self.history = []

    def request_kwargs(self):
        """Exact create() kwargs -- split out so pins assert the shape (incl. prefix stability)
        offline. reasoning_effort rides extra_body only when it differs from the server default."""
        kw = {"model": self.model,
              "messages": [{"role": "system", "content": self._system}] + self.history,
              "max_completion_tokens": self.max_completion_tokens}
        if self._tools:
            kw["tools"] = list(self._tools)
        if self.effort and self.effort != "max":
            kw["extra_body"] = {"reasoning_effort": self.effort}
        return kw

    def _run_tool(self, name, args):
        if not self.dispatch:
            return "ERROR: no dispatcher wired (tools_schemas given without dispatch)"
        try:
            return str(self.dispatch(name, args))
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"

    def send(self, user_text):
        """One task: user text in, final answer out, tool hops between. Thinking streams to
        on_trace('think'); the hop gauge rides every tool result (T018: gauges change behavior)."""
        self.history.append({"role": "user", "content": user_text})
        partial = ""
        for hop in range(1, self.max_hops + 1):
            if self.interrupt and self.interrupt():
                return "[kimi paused mid-task by interjection -- resume to continue]"
            if self.inject:
                for fact in (self.inject() or []):
                    self.history.append({"role": "user",
                        "content": f"[STEER -- new fact to fold into the live task, keep going]: {fact}"})
            self._activity("thinking", f"hop {hop}")
            resp = self.client.chat.completions.create(**self.request_kwargs())
            self.last_response = resp
            u = getattr(resp, "usage", None)
            if u is not None:
                self.input_tokens += getattr(u, "prompt_tokens", 0) or 0
                self.output_tokens += getattr(u, "completion_tokens", 0) or 0
                self.meter.record(u, self.model)
            msg = resp.choices[0].message
            thinking = getattr(msg, "reasoning_content", None)
            if thinking:
                for i in range(0, len(thinking), 700):
                    self._trace("think", thinking[i:i + 700])
            text = (msg.content or "").strip()               # delta 5: content ONLY
            calls = list(getattr(msg, "tool_calls", None) or [])
            # chat round-trip: echo the assistant turn (sans reasoning) then each tool result
            echo = {"role": "assistant", "content": msg.content or ""}
            if calls:
                echo["tool_calls"] = [
                    {"id": c.id, "type": "function",
                     "function": {"name": c.function.name, "arguments": c.function.arguments}}
                    for c in calls]
            self.history.append(echo)
            if not calls:
                return text or "(kimi produced no final text)"
            partial = text
            for c in calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                except Exception:
                    args = {"_raw": c.function.arguments}
                self._trace("tool", f"{c.function.name}({json.dumps(args)[:200]})")
                self._activity("tool", c.function.name)
                out = self._run_tool(c.function.name, args)
                self.history.append({"role": "tool", "tool_call_id": c.id,
                                     "content": f"[hop {hop}/{self.max_hops}] {out}"[:20000]})
        return (f"{partial}\n[kimi tool budget exhausted at {self.max_hops} hops -- "
                f"partial answer above; re-ask to continue]").strip()


if __name__ == "__main__":
    # Manual smoke (network, costs ~$0.02): py scripts/kimi_chat.py --smoke
    if "--smoke" in sys.argv:
        meter = SpendMeter()
        meter.reconcile(force=True)
        print("pre :", meter.status_line())
        ag = KimiAgent(instructions="You are kimi, smoke-testing your seat transport.",
                       meter=meter)
        print("text=", repr(ag.send("Reply with exactly: KIMI TRANSPORT LIVE")))
        calc = [{"type": "function", "function": {"name": "calc",
                 "description": "evaluate arithmetic",
                 "parameters": {"type": "object",
                                "properties": {"expr": {"type": "string"}},
                                "required": ["expr"]}}}]
        ag2 = KimiAgent(instructions="Use tools when asked.", tools_schemas=calc,
                        dispatch=lambda n, a: "42", meter=meter)
        print("tool round-trip:", repr(ag2.send("What is 6*7? Use the calc tool, then answer.")))
        u = ag2.last_response.usage
        print("last usage:", u.model_dump() if hasattr(u, "model_dump") else u)
        print("post:", meter.status_line())
        print("== smoke complete ==")
