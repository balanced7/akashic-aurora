"""
deepseek_chat -- an interactive, TOOL-USING conversation with DeepSeek, in its own window.

This is not a chat wrapper: DeepSeek gets a real agentic loop. It can read your files, list and
search the tree, inspect git history, and query Akashic Aurora's own knowledge base -- then chain
those calls (read -> search -> read -> synthesize) with no paste-back, exactly like a code agent.
It holds the full conversation, so you can follow up and it remembers the thread.

  py scripts/deepseek_chat.py                        # agentic, deepseek-v4-pro, thinking on
  py scripts/deepseek_chat.py --allow-exec           # also let DeepSeek run shell cmds (per-call y/N)
  py scripts/deepseek_chat.py --trust                # full autonomy: shell/exec auto-approved
  py scripts/deepseek_chat.py --root E:\\AI-Setup --no-think

Key: env DEEPSEEK_API_KEY, else the gitignored .secrets/deepseek.key. OpenAI-compatible API, so this
uses the `openai` client pointed at api.deepseek.com. deepseek-v4-pro = smartest (1M context).

TOOLS exposed to DeepSeek (read-only ones run automatically; the loop chains them):
  read_file · list_directory · find_files · search_files · git_log · git_diff · git_show ·
  git_status · knowledge_recall · knowledge_boot · run_command(gated) · web_search(best-effort)

SAFETY (a remote model is driving your machine -- guards live in this harness, not in the prompt):
  * File access is scoped to --root (default: this repo). Paths outside it are refused.
  * Secrets are ALWAYS blocked: .secrets/, *.key/*.pem/*.crt, .env, id_rsa, credentials
    (override only with --allow-secrets, which you should almost never do).
  * run_command is OFF unless --allow-exec; then each command needs your [y/N] -- unless --trust.
  * Everything is capped (file bytes, match counts, tool rounds) to bound tokens/cost.

In-chat commands:
  /exit /quit        end          /reset            clear thread (keep system prompt)
  /system <text>     set system   /think [on|off]   toggle reasoning display
  /model <name>      v4-pro|v4-flash                /tools [on|off]   toggle tool use
  /trust [on|off]    auto-approve shell/exec        /exec [on|off]    enable/disable run_command
  /root [<path>]     show/set file-access root      /temp <float>     sampling temperature
  /max <int>         max output tokens              /json [on|off]    JSON response mode (tools off)
  /paste             multi-line input (end: /end)   /save|/load <p>   persist the conversation
  /tokens            usage this session             /help             this list

NOTE: everything (files, command output, KB results) is sent to DeepSeek's API. Don't widen --root or
--allow-secrets over anything you would not share with DeepSeek.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

KEY_FILE = Path(__file__).resolve().parent.parent / ".secrets" / "deepseek.key"
REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://api.deepseek.com"
PRO, FLASH = "deepseek-v4-pro", "deepseek-v4-flash"

# --- G4 hardening (L0): a hung streaming read must become a caught timeout, not an infinite wedge.
# A per-read timeout aborts pre-data AND mid-stream stalls (verified: tests/manual/l0_timeout_probe.py);
# the Agent.send() try/except then revives the loop. Tunable via env.
MODEL_CONNECT_TIMEOUT = float(os.getenv("DEEPSEEK_CONNECT_TIMEOUT", "15"))
MODEL_READ_TIMEOUT    = float(os.getenv("DEEPSEEK_READ_TIMEOUT", "120"))   # per-chunk read gap; healthy streams beat it, a stall trips it
MODEL_MAX_RETRIES     = int(os.getenv("DEEPSEEK_MAX_RETRIES", "1"))        # explicit: the SDK default (2) would ~3x the wall-clock before a wedge surfaces


def make_client(api_key=None, base_url=BASE_URL):
    """OpenAI-compatible client hardened against G4 wedges. A per-read streaming timeout turns a hung
    model call into a caught httpx.ReadTimeout (Agent.send()'s try/except then revives the loop); an
    explicit max_retries stops the SDK default (2) from tripling the wall-clock before recovery."""
    from openai import OpenAI
    import httpx
    return OpenAI(api_key=api_key or load_key(), base_url=base_url,
                  timeout=httpx.Timeout(MODEL_READ_TIMEOUT, connect=MODEL_CONNECT_TIMEOUT),
                  max_retries=MODEL_MAX_RETRIES)

# ---- tool surface + guarded executor: EXTRACTED to core/comm/toolbox.py (K0 2026-07-18,
# rule-of-three: the deepseek, sol, and kimi seats share one seam). Behavior-preserving move;
# these names re-export here so existing imports keep working. Canonical: core.comm.toolbox.
_HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(_HERE))
from core.comm.toolbox import (   # noqa: F401,E402  (compat re-export)
    MAX_CMD_TIMEOUT, EXCLUDE_DIRS, BINARY_SUFFIXES, MAX_FILE_BYTES, MAX_MATCHES,
    MAX_LIST, MAX_CMD_OUT, CLARIFY_MAX_PER_TASK, CLARIFY_TIMEOUT_S, _fn, TOOLS, ToolBox,
)
# CLARIFY_TIMEOUT_S was missing from this list while the clarification-TIMEOUT branch below
# uses it -- so the runner died with a NameError precisely when a clarification went
# unanswered (2026-08-01, two attempts, mid-battery). The happy path never touches the name;
# tests/test_deepseek_chat_imports.py now AST-checks the whole re-export against usage so the
# NEXT drifted constant fails in CI instead of in a live turn.

MAX_TOOL_ROUNDS = 30


# ---- terminal helpers -------------------------------------------------------

def _enable_utf8_and_ansi() -> bool:
    for stream in (sys.stdout, sys.stdin, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        color = sys.stdout.isatty()
    except Exception:
        color = False
    if color and os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        except Exception:
            color = False
    return color


class C:
    dim = grey = cyan = green = yellow = red = bold = reset = ""

    @classmethod
    def enable(cls):
        cls.dim = "\033[2m"; cls.grey = "\033[90m"; cls.cyan = "\033[36m"; cls.green = "\033[32m"
        cls.yellow = "\033[33m"; cls.red = "\033[31m"; cls.bold = "\033[1m"; cls.reset = "\033[0m"


def load_key() -> str | None:
    v = os.getenv("DEEPSEEK_API_KEY")
    if v and v.strip():
        return v.strip()
    if KEY_FILE.exists():
        t = KEY_FILE.read_text(encoding="utf-8").strip()
        if t:
            return t
    return None


# ---- the agent (conversation + tool loop) -----------------------------------

def default_system(root: Path) -> str:
    return (
        "You are DeepSeek, operating as an agentic technical partner with LIVE access to a software "
        f"project via tools. Project root: {root}. Investigate proactively -- call read_file, "
        "list_directory, find_files, search_files, git_* and knowledge_recall/knowledge_boot yourself; "
        "never ask the user to paste a file you can read. knowledge_recall/knowledge_boot query the "
        "project's own Akashic Aurora knowledge base (lessons, notes, assembled context). run_command "
        "is gated -- it may need the user's approval and can be denied, so prefer read-only tools and "
        "propose shell only when needed. Secrets/credentials are blocked by design; don't try to read "
        "them. Chain tools until you can answer, then be specific and cite exact files and line numbers."
    )


_TOOL_STATE = {
    "read_file": "reading", "list_directory": "reading", "find_files": "searching",
    "search_files": "searching", "git_log": "inspecting", "git_diff": "inspecting",
    "git_show": "inspecting", "git_status": "inspecting", "knowledge_recall": "recalling",
    "knowledge_boot": "recalling", "recall_at": "recalling", "knowledge_full": "recalling",
    "memory_note": "recalling", "memory_recall": "recalling",
    "knowledge_map": "recalling", "delta": "recalling",
    "run_command": "running", "web_search": "searching",
}


def _tool_activity(name, args):
    """(state, short-detail) for the rich-presence indicator, from a tool call."""
    state = _TOOL_STATE.get(name, "working")
    d = (args.get("path") or args.get("pattern") or args.get("query")
         or args.get("command") or args.get("task") or args.get("directory") or "")
    return state, str(d)[:80]


class Agent:
    def __init__(self, client, toolbox: ToolBox, *, model, system, think, tools_enabled,
                 interrupt=None, on_activity=None, inject=None, on_trace=None, agent_id=None):
        self.client = client
        self.toolbox = toolbox
        self.model = model
        self.think = think
        self.tools_enabled = tools_enabled
        self.interrupt = interrupt         # optional () -> bool; checked between rounds for true barge-in
        self.on_activity = on_activity     # optional (state, detail) -> None; reports activity (rich presence)
        self.inject = inject               # optional () -> list[str]; steering facts to fold in mid-task
        self.on_trace = on_trace           # optional (kind, text) -> None; streams tool calls + thinking out
        self.agent_id = agent_id           # optional str; when set, cognitive metrics are recorded
        self.temperature = None
        self.max_tokens = None
        self.json_mode = False
        self.messages = [{"role": "system", "content": system}]
        self.prompt_tokens = self.completion_tokens = 0
        # T078 W1b -- meter the things that actually drive cost.
        # Measured 2026-07-25: 309 deepseek turns / 393M tokens, worst turn 11.4M over 127
        # hops. The driver is that `messages` is never trimmed and tool results append raw
        # (MAX_FILE_BYTES=120_000), so one big read is re-sent every remaining hop. Before
        # compacting anything we need to know how much of that re-send is CACHED -- DeepSeek
        # bills a cached prefix at roughly 0.1x, so the raw token count can overstate real
        # spend by up to 10x. Meters before levers (T078 R1).
        self.cache_hit_tokens = self.cache_miss_tokens = 0
        self.context_high_water = 0

    def _absorb_usage(self, usage) -> None:
        """Fold one usage report into the session counters. Never raises.

        The cache split is optional by provider, so its absence degrades to 0 rather than
        breaking accounting -- an exception here would silently cost us the whole meter,
        which is how T078-W1 spent weeks reporting zero.
        """
        try:
            self.prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self.completion_tokens += getattr(usage, "completion_tokens", 0) or 0
            self.cache_hit_tokens += getattr(usage, "prompt_cache_hit_tokens", 0) or 0
            self.cache_miss_tokens += getattr(usage, "prompt_cache_miss_tokens", 0) or 0
        except Exception:
            pass

    def cache_rate(self):
        """Fraction of prompt tokens served from cache, or None when unmeasured.

        None, never 0.0: 'no cache data' and 'nothing was cached' are different facts, and
        collapsing them is how a dead meter reads as a real reading.
        """
        seen = self.cache_hit_tokens + self.cache_miss_tokens
        return (self.cache_hit_tokens / seen) if seen else None

    def _mark_context(self) -> int:
        """Sample the live context size; keep the per-turn peak. Cheap, called per hop.

        This is the number the cost is quadratic in -- a runaway turn is visible here while
        it runs, instead of only in a turn_metrics row 575 seconds later.
        """
        try:
            size = sum(len(str(m.get("content") or "")) for m in self.messages)
            if size > self.context_high_water:
                self.context_high_water = size
            return size
        except Exception:
            return 0

    def _activity(self, state, detail=""):
        if self.on_activity:
            try:
                self.on_activity(state, detail)
            except Exception:
                pass

    def _trace(self, kind, text):
        """Stream a step (a tool call, or a chunk of thinking) OUT of the loop -- the runner posts these
        to the bus so the console shows DeepSeek's live reasoning + tool use, not just the final answer."""
        if self.on_trace and text:
            try:
                self.on_trace(kind, str(text))
            except Exception:
                pass

    def reset(self):
        self.messages = self.messages[:1] if self.messages[:1] and self.messages[0]["role"] == "system" else []

    def set_system(self, text):
        self.messages = [{"role": "system", "content": text}]

    def _kwargs(self):
        k = {"model": self.model, "messages": self.messages,
             "stream": True, "stream_options": {"include_usage": True}}
        if self.tools_enabled:
            k["tools"] = TOOLS
            k["tool_choice"] = "auto"
        k["extra_body"] = {"thinking": {"type": "enabled" if self.think else "disabled"}}
        if self.think:
            k["reasoning_effort"] = "high"
        if self.temperature is not None:
            k["temperature"] = self.temperature
        if self.max_tokens:
            k["max_tokens"] = self.max_tokens
        if self.json_mode and not self.tools_enabled:
            k["response_format"] = {"type": "json_object"}
        return k

    def _stream_turn(self):
        """One model turn, streamed. Prints reasoning (dim) + answer (green); accumulates tool calls.
        Returns (content_text, tool_calls) where tool_calls is a list of {id,name,arguments}."""
        # P-S1-5 (kimi O1b): the blocking model call is its OWN phase. A hang before the first
        # token (C1-8: create() never returns, so no tool round fires to bump the pulse) surfaces
        # as 'calling-model' aged -> legibly 'hung in the API call' (P-S1-0 renders it at 150s).
        # Flip to 'thinking' the instant the stream yields, so a normal call never lingers here.
        self._activity("calling-model", self.model)
        stream = self.client.chat.completions.create(**self._kwargs())
        content, slots = [], {}
        reasoning_buf = []
        in_reasoning = header = streaming = False
        try:
            for chunk in stream:
                if not streaming:                 # first token/data -> the call is live; thinking now
                    self._activity("thinking")
                    streaming = True
                if getattr(chunk, "usage", None):
                    self._absorb_usage(chunk.usage)
                if not chunk.choices:
                    continue
                d = chunk.choices[0].delta
                r = getattr(d, "reasoning_content", None)
                if r is None and getattr(d, "model_extra", None):
                    r = d.model_extra.get("reasoning_content")
                if r and self.think:
                    if not in_reasoning:
                        print(f"{C.grey}💭 ", end="", flush=True); in_reasoning = True
                    print(f"{C.grey}{r}", end="", flush=True)
                    reasoning_buf.append(r)
                if d.content:
                    if in_reasoning:
                        print(C.reset); in_reasoning = False
                    if not header:
                        print(f"{C.green}{C.bold}DeepSeek:{C.reset} ", end="", flush=True); header = True
                    print(d.content, end="", flush=True); content.append(d.content)
                if d.tool_calls:
                    for tc in d.tool_calls:
                        s = slots.setdefault(tc.index, {"id": None, "name": "", "arguments": ""})
                        if tc.id:
                            s["id"] = tc.id
                        if tc.function and tc.function.name:
                            s["name"] += tc.function.name
                        if tc.function and tc.function.arguments:
                            s["arguments"] += tc.function.arguments
        finally:
            if in_reasoning or header:
                print(C.reset)
        if reasoning_buf:                                  # surface a compact 'thinking' trace to the console
            self._trace("thinking", "".join(reasoning_buf)[:500])
        return "".join(content), [slots[i] for i in sorted(slots)]

    def send(self, user_text):
        self.messages.append({"role": "user", "content": user_text})
        if getattr(self, "toolbox", None) is not None:
            self.toolbox._clarify_count = 0   # R7 P2: the budget is per-task (per ask)
        for _round in range(MAX_TOOL_ROUNDS):
            # Sample BEFORE the call: this is the context this hop is about to re-send, and
            # it is the quantity the whole cost is quadratic in.
            self._mark_context()
            if self.interrupt and self.interrupt():   # DeepSeek's fix: true barge-in mid-tool-loop
                print(f"{C.yellow}[interrupted by your interjection -- pausing mid-task]{C.reset}")
                return "[paused mid-task by your interjection -- resume to continue]"
            if self.inject:                           # STEER: fold new facts into the LIVE task, no restart
                for fact in (self.inject() or []):
                    self.messages.append({"role": "user",
                        "content": f"[STEER -- new fact to adopt into your current task, keep going]: {fact}"})
                    print(f"{C.cyan}[steered mid-task] {fact[:120]}{C.reset}")
            # R7 (T058): a pending clarification HOLDS this turn -- poll the steer queue
            # (the runner routes the user's answer onto it) until it folds or the deadline
            # injects a LOUD proceed-with-assumption. Context stays intact (his P7).
            tb = getattr(self, "toolbox", None)
            if tb is not None and getattr(tb, "_clarify_waiting", None):
                cid = tb._clarify_waiting
                while time.time() < getattr(tb, "_clarify_deadline", 0):
                    got = (self.inject() or []) if self.inject else []
                    if got:
                        for fact in got:
                            self.messages.append({"role": "user",
                                "content": f"[STEER -- answer to your clarification ({cid})]: {fact}"})
                            print(f"{C.cyan}[clarify-answer folded] {str(fact)[:120]}{C.reset}")
                        tb._clarify_waiting = None
                        break
                    self._activity("awaiting-clarification")
                    time.sleep(2)
                if getattr(tb, "_clarify_waiting", None):
                    tb._clarify_waiting = None
                    self.messages.append({"role": "user", "content":
                        f"[CLARIFICATION TIMEOUT ({cid}) -- no answer within {CLARIFY_TIMEOUT_S}s. "
                        "Proceed with your best judgment and state your assumption LOUDLY: "
                        "'I'm assuming X; if that's wrong, steer me.']"})
                    print(f"{C.yellow}[clarify timeout {cid} -- proceeding with assumption]{C.reset}")
            # P-S1-5: the turn's phase is now owned by _stream_turn ('calling-model' before the
            # blocking create(), then 'thinking' on the first token) -- so the API wait is legible.
            try:
                content, tool_calls = self._stream_turn()
            except Exception as e:
                print(f"{C.red}DEEPSEEK_ERROR ({self.model}): {type(e).__name__}: {e}{C.reset}")
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
                return ""
            if tool_calls:
                self.messages.append({"role": "assistant", "content": content or None, "tool_calls": [
                    {"id": s["id"], "type": "function",
                     "function": {"name": s["name"], "arguments": s["arguments"] or "{}"}} for s in tool_calls]})
                for s in tool_calls:
                    try:
                        args = json.loads(s["arguments"] or "{}")
                    except Exception:
                        args = {}
                    shown = ", ".join(f"{k}={v!r}" for k, v in args.items())
                    print(f"{C.yellow}🔧 {s['name']}({shown[:160]}){C.reset}")
                    self._trace("tool", f"{s['name']}({shown[:140]})")
                    self._activity(*_tool_activity(s["name"], args))
                    from core.comm import packet_spec as _ps    # T043 pin 8: MTU gate at the bite site
                    _ok, _refusal = _ps.tool_args_within_mtu(s["name"], args)
                    if not _ok:
                        print(f"{C.red}   ⛔ {_refusal}{C.reset}")
                        result = _refusal    # the tool result the model sees -- refuse loud, never a silent clip
                    else:
                        # T055/R4: pre-flight recall rides the FRONT of the tool result
                        # (his P1 -- the model reads the file WITH context). Fail-silent.
                        try:
                            _pre = self.toolbox._preflight_recall(s["name"], args)
                        except Exception:
                            _pre = ""
                        result = self.toolbox.execute(s["name"], args)
                        if _pre:
                            result = _pre + result
                    first = result.splitlines()[0] if result else ""
                    print(f"{C.dim}   → {len(result)} chars | {first[:120]}{C.reset}")
                    # T050 Q4 (deepseek a2 -- 'blind agents are conservative agents'): every
                    # tool result carries the running hop count + the round budget, so the
                    # agent paces with open eyes instead of hoarding hops on anxiety.
                    self._hops = getattr(self, "_hops", 0) + 1
                    result = f"{result}\n[hop {self._hops} | tool-round {_round + 1}/{MAX_TOOL_ROUNDS}]"
                    self.messages.append({"role": "tool", "tool_call_id": s["id"], "content": result})
                continue
            if content:
                self.messages.append({"role": "assistant", "content": content})
            return content
        print(f"{C.red}[stopped: hit {MAX_TOOL_ROUNDS} tool rounds]{C.reset}")
        return ""

    def save(self, path):
        Path(path).write_text(json.dumps({"model": self.model, "think": self.think,
            "tools_enabled": self.tools_enabled, "messages": self.messages}, indent=2, ensure_ascii=False),
            encoding="utf-8")

    def load(self, path):
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        self.messages = doc.get("messages", self.messages)
        self.model = doc.get("model", self.model)
        self.think = doc.get("think", self.think)
        self.tools_enabled = doc.get("tools_enabled", self.tools_enabled)


# ---- commands + REPL --------------------------------------------------------

HELP = __doc__.split("In-chat commands:", 1)[1].split("NOTE:", 1)[0].rstrip()


def read_paste():
    print(f"{C.dim}(multi-line -- type /end on its own line to send){C.reset}")
    lines = []
    while True:
        try:
            ln = input()
        except EOFError:
            break
        if ln.strip() == "/end":
            break
        lines.append(ln)
    return "\n".join(lines)


def handle_command(ag: Agent, raw) -> bool:
    parts = raw.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    tb = ag.toolbox
    if cmd in ("/exit", "/quit"):
        return False
    if cmd == "/help":
        print(f"{C.cyan}Commands:{C.reset}\n{HELP}")
    elif cmd == "/reset":
        ag.reset(); print(f"{C.dim}thread cleared{C.reset}")
    elif cmd == "/system":
        (ag.set_system(arg), print(f"{C.dim}system set; thread reset{C.reset}")) if arg else print(f"{C.yellow}usage: /system <text>{C.reset}")
    elif cmd == "/think":
        ag.think = {"on": True, "off": False}.get(arg.lower(), not ag.think); print(f"{C.dim}thinking: {'on' if ag.think else 'off'}{C.reset}")
    elif cmd == "/tools":
        ag.tools_enabled = {"on": True, "off": False}.get(arg.lower(), not ag.tools_enabled); print(f"{C.dim}tools: {'on' if ag.tools_enabled else 'off'}{C.reset}")
    elif cmd == "/trust":
        tb.trust = {"on": True, "off": False}.get(arg.lower(), not tb.trust)
        if tb.trust:
            tb.allow_exec = True
        print(f"{C.yellow}trust: {'ON -- shell/exec auto-approved' if tb.trust else 'off'}{C.reset}")
    elif cmd == "/exec":
        tb.allow_exec = {"on": True, "off": False}.get(arg.lower(), not tb.allow_exec); print(f"{C.dim}run_command: {'enabled' if tb.allow_exec else 'disabled'}{C.reset}")
    elif cmd == "/root":
        if arg:
            tb.root = Path(arg).resolve(); print(f"{C.dim}root -> {tb.root}{C.reset}")
        else:
            print(f"{C.dim}root = {tb.root}{C.reset}")
    elif cmd == "/model":
        (setattr(ag, "model", arg), print(f"{C.dim}model -> {arg}{C.reset}")) if arg in (PRO, FLASH) else print(f"{C.yellow}usage: /model {PRO}|{FLASH}{C.reset}")
    elif cmd == "/temp":
        try:
            ag.temperature = float(arg); print(f"{C.dim}temperature -> {ag.temperature}{C.reset}")
        except ValueError:
            print(f"{C.yellow}usage: /temp <float>{C.reset}")
    elif cmd == "/max":
        try:
            ag.max_tokens = int(arg); print(f"{C.dim}max_tokens -> {ag.max_tokens}{C.reset}")
        except ValueError:
            print(f"{C.yellow}usage: /max <int>{C.reset}")
    elif cmd == "/json":
        ag.json_mode = {"on": True, "off": False}.get(arg.lower(), not ag.json_mode); print(f"{C.dim}json mode: {'on (tools off)' if ag.json_mode else 'off'}{C.reset}")
    elif cmd == "/tokens":
        print(f"{C.dim}prompt {ag.prompt_tokens} + completion {ag.completion_tokens} = {ag.prompt_tokens + ag.completion_tokens}{C.reset}")
    elif cmd == "/save":
        try:
            ag.save(arg); print(f"{C.dim}saved -> {arg}{C.reset}")
        except Exception as e:
            print(f"{C.yellow}save failed: {e}{C.reset}")
    elif cmd == "/load":
        try:
            ag.load(arg); print(f"{C.dim}loaded {len(ag.messages)} msgs{C.reset}")
        except Exception as e:
            print(f"{C.yellow}load failed: {e}{C.reset}")
    elif cmd == "/paste":
        text = read_paste()
        if text.strip():
            ag.send(text)
    else:
        print(f"{C.yellow}unknown {cmd} -- /help{C.reset}")
    return True


def main() -> int:
    if _enable_utf8_and_ansi():
        C.enable()
    ap = argparse.ArgumentParser(description="Interactive tool-using DeepSeek chat.")
    ap.add_argument("--model", default=PRO)
    ap.add_argument("--system", default=None)
    ap.add_argument("--root", default=str(REPO_ROOT), help="file-access root (default: this repo)")
    ap.add_argument("--no-think", action="store_true")
    ap.add_argument("--no-tools", action="store_true", help="start as a plain chat (no tool use)")
    ap.add_argument("--allow-exec", action="store_true", help="permit run_command (still per-call y/N unless --trust)")
    ap.add_argument("--trust", action="store_true", help="auto-approve shell/exec (full autonomy)")
    ap.add_argument("--allow-secrets", action="store_true", help="DANGER: allow reading .secrets/*.key/.env")
    ap.add_argument("--load")
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("NO_KEY: set DEEPSEEK_API_KEY or put it in .secrets/deepseek.key", file=sys.stderr); return 2
    try:
        from openai import OpenAI
    except Exception:
        print("MISSING_DEP: py -m pip install openai", file=sys.stderr); return 2

    root = Path(args.root).resolve()

    def confirm(prompt):
        try:
            return input(f"{C.yellow}{prompt}\n  approve? [y/N] {C.reset}").strip().lower() in ("y", "yes")
        except EOFError:
            return False

    toolbox = ToolBox(root, allow_exec=(args.allow_exec or args.trust), trust=args.trust,
                      allow_secrets=args.allow_secrets, confirm=confirm)
    client = make_client(key)   # L0: hardened against hung-stream wedges (timeout + explicit retries)
    agent = Agent(client, toolbox, model=args.model, system=(args.system or default_system(root)),
                  think=not args.no_think, tools_enabled=not args.no_tools)
    if args.load:
        try:
            agent.load(args.load)
        except Exception as e:
            print(f"{C.yellow}load failed: {e}{C.reset}")

    print(f"{C.cyan}{C.bold}DeepSeek agent{C.reset}  {C.dim}model={agent.model} · tools={'on' if agent.tools_enabled else 'off'} · "
          f"think={'on' if agent.think else 'off'} · root={root}{C.reset}")
    print(f"{C.dim}exec={'on' if toolbox.allow_exec else 'off'}"
          f"{' · TRUST(auto-approve)' if toolbox.trust else ''} · /help for commands, /exit to quit{C.reset}")

    while True:
        try:
            line = input(f"{C.cyan}you>{C.reset} ")
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not line.strip():
            continue
        if line.lstrip().startswith("/"):
            if not handle_command(agent, line):
                break
            continue
        try:
            agent.send(line)
        except KeyboardInterrupt:
            print(f"\n{C.yellow}[turn interrupted]{C.reset}")

    print(f"{C.dim}bye -- {agent.prompt_tokens + agent.completion_tokens} tokens this session{C.reset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
