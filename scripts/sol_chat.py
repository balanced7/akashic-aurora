"""
sol_chat -- the Sol seat's model transport: gpt-5.6-sol (OpenAI) as a first-class Akashic citizen.

Sol is its OWN seat (Daniel directive 2026-07-17): sol-named module, SOL_* envs, nothing
deepseek-named on this surface. Peer modules: ask_gpt.py (one-shot CLI opinions, same provider),
bifrost_runner_sol.py (the seat's body -- lands after the T090 architecture verdict with
deepseek-review).

WHY THE RESPONSES API (receipts: research/drafts/sol-probe-receipts-2026-07-17.md):
  /v1/chat/completions REFUSES function tools while reasoning is on for this model
  ("Function tools with reasoning_effort are not supported ... use /v1/responses or set
  reasoning_effort to 'none'"). A frontier seat with reasoning off is lobotomized, so the
  seat speaks /v1/responses -- the tool round-trip (function_call -> function_call_output ->
  final) is probe-verified end to end, streaming included.

DESIGN (T090, fenced with deepseek-review before mirror):
  * STATELESS: full context resent each call, store=False. RB-26 crash-redelivery makes OUR
    substrate the conversation truth; server-side previous_response_id state diverges on a
    crash redelivery. Prompt caching ($0.50/M cached input) soaks the resend cost.
  * PREVIEW-401 SHIM: the limited-preview access gate 401s ~30% of calls param-independently
    (receipts round 2: same call 401/401/OK). The SDK treats 401 as fatal, so we retry <=
    SOL_401_RETRIES with a short backoff, LOUDLY. Remove post-GA after a clean re-probe.
  * Receipt-verified knobs: effort ladder none|low|medium|high|xhigh (API-enumerated; 'max'
    is aggregator fiction); temperature LOCKED at 1 (not a knob); max_tokens is DEAD, use
    max_output_tokens; verbosity rides text={'verbosity': ...}; service_tier 'flex' accepted.

Key: env OPENAI_API_KEY else .secrets/openai.key (shared with ask_gpt.py -- same provider).
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ask_gpt import load_key   # same provider, same key convention; ask_gpt is provider- not seat-named

BASE_URL = "https://api.openai.com/v1"
SOL, TERRA, LUNA = "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"
DEFAULT_MODEL = os.getenv("SOL_MODEL", SOL)

EFFORTS = ("none", "low", "medium", "high", "xhigh")          # API-enumerated 2026-07-17
VERBOSITIES = ("low", "medium", "high")
DEFAULT_EFFORT = os.getenv("SOL_EFFORT", "medium")             # omitted-default per docs; explicit here
DEFAULT_VERBOSITY = os.getenv("SOL_VERBOSITY", "medium")
# T018 philosophy carried over: a reasoning model with no output cap wraps long turns in a
# short promise instead of the deliverable. 8K default =~ $0.24 worst-case turn at $30/M out.
MAX_OUTPUT_TOKENS = int(os.getenv("SOL_RUNNER_MAX_TOKENS", "8000"))

# G4-shape hardening (same rationale as the deepseek seat's factory, independently tuned):
# a hung streaming read must become a caught timeout, not an infinite wedge.
SOL_CONNECT_TIMEOUT = float(os.getenv("SOL_CONNECT_TIMEOUT", "15"))
SOL_READ_TIMEOUT = float(os.getenv("SOL_READ_TIMEOUT", "120"))
SOL_MAX_RETRIES = int(os.getenv("SOL_MAX_RETRIES", "1"))
PREVIEW_401_RETRIES = int(os.getenv("SOL_401_RETRIES", "3"))


def make_client(api_key=None, base_url=BASE_URL):
    """OpenAI client hardened against hung-stream wedges (per-read timeout + explicit retries)."""
    import httpx
    from openai import OpenAI
    return OpenAI(api_key=api_key or load_key(), base_url=base_url,
                  timeout=httpx.Timeout(SOL_READ_TIMEOUT, connect=SOL_CONNECT_TIMEOUT),
                  max_retries=SOL_MAX_RETRIES)


def to_responses_tools(tools):
    """Chat-nested tool schemas -> Responses flat format. Accepts already-flat and passes through.

    chat-nested: {"type":"function","function":{"name":...,"description":...,"parameters":...}}
    flat:        {"type":"function","name":...,"description":...,"parameters":...}
    """
    if not tools:
        return None
    out = []
    for t in tools:
        if t.get("type") != "function":
            out.append(t)               # hosted tools (web_search, ...) ride through untouched
            continue
        if "function" in t:
            fn = t["function"]
            out.append({"type": "function", "name": fn["name"],
                        "description": fn.get("description", ""),
                        "parameters": fn.get("parameters", {})})
        elif "name" in t:
            out.append(t)
        else:
            raise ValueError(f"unrecognized tool schema (neither chat-nested nor flat): {t!r}")
    return out


def preview_401_retry(fn, retries=None, label="sol call", exception_cls=None, sleep_s=2.0):
    """Bounded, LOUD retry for the limited-preview intermittent 401s. Remove post-GA (re-probe first).

    exception_cls is injectable for pins; defaults to openai.AuthenticationError.
    """
    if exception_cls is None:
        from openai import AuthenticationError as exception_cls   # noqa: N813
    n = PREVIEW_401_RETRIES if retries is None else retries
    for attempt in range(n + 1):
        try:
            return fn()
        except exception_cls:
            if attempt >= n:
                print(f"[sol] preview-401 EXHAUSTED after {n} retries on {label} -- raising", flush=True)
                raise
            print(f"[sol] preview-401 retry {attempt + 1}/{n} on {label} "
                  f"(limited-preview access gate; see sol-probe-receipts)", flush=True)
            time.sleep(sleep_s)


class SolTransport:
    """Stateless Responses-API transport. History is RESPONSES-NATIVE items, owned by the caller:
    {"role":"user"/"assistant","content":...} turns, the model's function_call items echoed
    verbatim, and {"type":"function_call_output","call_id":...,"output":...} results."""

    def __init__(self, model=DEFAULT_MODEL, effort=DEFAULT_EFFORT, verbosity=DEFAULT_VERBOSITY,
                 max_output_tokens=MAX_OUTPUT_TOKENS, service_tier=None, client=None):
        if effort not in EFFORTS:
            raise ValueError(f"effort {effort!r} not in {EFFORTS} (API-enumerated ladder)")
        if verbosity not in VERBOSITIES:
            raise ValueError(f"verbosity {verbosity!r} not in {VERBOSITIES}")
        self.model, self.effort, self.verbosity = model, effort, verbosity
        self.max_output_tokens, self.service_tier = max_output_tokens, service_tier
        self._client = client   # lazy: pins inject a fake; live use builds on first call

    @property
    def client(self):
        if self._client is None:
            self._client = make_client()
        return self._client

    def request_kwargs(self, instructions, history, tools=None):
        """The exact responses.create kwargs -- split out so pins can assert the shape offline."""
        kw = {"model": self.model, "instructions": instructions, "input": list(history),
              "store": False, "max_output_tokens": self.max_output_tokens,
              "reasoning": {"effort": self.effort}, "text": {"verbosity": self.verbosity}}
        t = to_responses_tools(tools)
        if t:
            kw["tools"] = t
        if self.service_tier:
            kw["service_tier"] = self.service_tier
        return kw

    def respond(self, instructions, history, tools=None):
        kw = self.request_kwargs(instructions, history, tools)
        return preview_401_retry(lambda: self.client.responses.create(**kw),
                                 label=f"responses.create[{self.model}]")

    @staticmethod
    def extract(response):
        """-> (text, tool_calls, raw_output_items). tool_calls: [{call_id, name, arguments(dict)}].
        raw_output_items go back into history verbatim so call_ids stay paired (stateless resend)."""
        calls = []
        items = list(getattr(response, "output", []) or [])
        for it in items:
            if getattr(it, "type", "") == "function_call":
                try:
                    args = json.loads(it.arguments or "{}")
                except Exception:
                    args = {"_raw": it.arguments}
                calls.append({"call_id": it.call_id, "name": it.name, "arguments": args})
        return (getattr(response, "output_text", "") or ""), calls, items


class SolAgent:
    """Responses-native tool loop -- the sol seat's engine (peer of the deepseek seat's Agent,
    purpose-built for Responses output ITEMS instead of chat SSE deltas; T090 Option B fork).

    Dependency-injected: `tools_schemas` (chat-nested or flat; transport converts) and
    `dispatch(name, args_dict) -> str` are supplied by the ASSEMBLY point (the runner), so this
    module stays free of any other seat's imports. History is Responses-native items owned here:
    stateless resend means every output item echoes back into input verbatim, and
    function_call_output pairs by call_id (see SolTransport docstring)."""

    def __init__(self, transport, *, instructions, tools_schemas=None, dispatch=None,
                 interrupt=None, inject=None, on_trace=None, on_activity=None, max_hops=None):
        self.transport = transport
        self.instructions = instructions
        self.tools = tools_schemas or None
        self.dispatch = dispatch
        self.interrupt, self.inject = interrupt, inject
        self.on_trace, self.on_activity = on_trace, on_activity
        self.max_hops = int(os.getenv("SOL_MAX_HOPS", "30")) if max_hops is None else max_hops
        self.history = []
        self.input_tokens = self.output_tokens = 0
        self.last_response = None

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

    def _run_tool(self, name, args):
        if not self.dispatch:
            return "ERROR: no dispatcher wired (tools_schemas given without dispatch)"
        try:
            return str(self.dispatch(name, args))
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"

    def send(self, user_text):
        """One task: user text in, final answer out, tool hops in between. The hop gauge rides
        every tool result ([hop N/max] -- the budget-visibility lesson: gauges change behavior)."""
        self.history.append({"role": "user", "content": user_text})
        partial = ""
        for hop in range(1, self.max_hops + 1):
            if self.interrupt and self.interrupt():
                return "[sol paused mid-task by interjection -- resume to continue]"
            if self.inject:
                for fact in (self.inject() or []):
                    self.history.append({"role": "user",
                        "content": f"[STEER -- new fact to fold into the live task, keep going]: {fact}"})
            self._activity("thinking", f"hop {hop}")
            resp = self.transport.respond(self.instructions, self.history, tools=self.tools)
            self.last_response = resp
            u = getattr(resp, "usage", None)
            if u is not None:
                self.input_tokens += getattr(u, "input_tokens", 0) or 0
                self.output_tokens += getattr(u, "output_tokens", 0) or 0
            text, calls, items = SolTransport.extract(resp)
            self.history.extend(items)   # stateless resend: output items echo back verbatim
            if not calls:
                return text or "(sol produced no final text)"
            partial = text
            for c in calls:
                self._trace("tool", f"{c['name']}({json.dumps(c['arguments'])[:200]})")
                self._activity("tool", c["name"])
                out = self._run_tool(c["name"], c["arguments"])
                self.history.append({"type": "function_call_output", "call_id": c["call_id"],
                                     "output": f"[hop {hop}/{self.max_hops}] {out}"[:20000]})
        return (f"{partial}\n[sol tool budget exhausted at {self.max_hops} hops -- "
                f"partial answer above; re-ask to continue]").strip()


if __name__ == "__main__":
    # Manual smoke (network, costs cents): py scripts/sol_chat.py --smoke
    if "--smoke" in sys.argv:
        t = SolTransport(effort="low", verbosity="low")
        text, calls, items = SolTransport.extract(
            t.respond("You are sol, smoke-testing your transport.",
                      [{"role": "user", "content": "Reply with exactly: SOL TRANSPORT LIVE"}]))
        print(f"text={text!r} calls={calls}")
        hist = [{"role": "user", "content": "What is 6*7? Use the calc tool."}]
        r1 = t.respond("Use tools when asked.", hist,
                       tools=[{"type": "function", "name": "calc", "description": "evaluate arithmetic",
                               "parameters": {"type": "object", "properties": {"expr": {"type": "string"}},
                                              "required": ["expr"]}}])
        _, calls, items = SolTransport.extract(r1)
        print(f"tool call: {calls}")
        if calls:
            hist += [it for it in items if getattr(it, "type", "") == "function_call"]
            hist.append({"type": "function_call_output", "call_id": calls[0]["call_id"], "output": "42"})
            r2 = t.respond("Use tools when asked.", hist,
                           tools=[{"type": "function", "name": "calc", "description": "evaluate arithmetic",
                                   "parameters": {"type": "object", "properties": {"expr": {"type": "string"}},
                                                  "required": ["expr"]}}])
            print(f"final: {SolTransport.extract(r2)[0]!r}")
        print("== smoke complete ==")
