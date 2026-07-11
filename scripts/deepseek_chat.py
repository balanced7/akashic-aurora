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
import subprocess
import sys
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
MAX_CMD_TIMEOUT       = int(os.getenv("DEEPSEEK_MAX_CMD_TIMEOUT", "300"))  # ceiling a single run_command can't exceed, even if the model asks for more


def make_client(api_key=None, base_url=BASE_URL):
    """OpenAI-compatible client hardened against G4 wedges. A per-read streaming timeout turns a hung
    model call into a caught httpx.ReadTimeout (Agent.send()'s try/except then revives the loop); an
    explicit max_retries stops the SDK default (2) from tripling the wall-clock before recovery."""
    from openai import OpenAI
    import httpx
    return OpenAI(api_key=api_key or load_key(), base_url=base_url,
                  timeout=httpx.Timeout(MODEL_READ_TIMEOUT, connect=MODEL_CONNECT_TIMEOUT),
                  max_retries=MODEL_MAX_RETRIES)

# Dirs never worth walking (vendored / caches / heavy data) -- keeps search fast and tokens bounded.
EXCLUDE_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules", "backups", "ComfyUI-Zluda", "assets",
    "model_cache", "ollama_data", "rocm-lib", ".pytest_cache", ".mypy_cache", "blobs", "dist", "build",
    "models", "dockerized-ai", "_archive",
}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".exe", ".dll", ".so",
                   ".bin", ".pyc", ".ico", ".woff", ".woff2", ".ttf", ".mp4", ".wav", ".npy", ".pkl"}
MAX_FILE_BYTES = 120_000
MAX_MATCHES = 120
MAX_LIST = 400
MAX_CMD_OUT = 16_000
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


# ---- tool schemas (what DeepSeek sees) --------------------------------------

def _fn(name, description, properties, required=()):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": list(required)}}}


TOOLS = [
    _fn("read_file", "Read a text file from the project. Prefer start_line/end_line for big files to save tokens.",
        {"path": {"type": "string", "description": "Path relative to the project root, e.g. 'bootstrap.md'"},
         "start_line": {"type": "integer", "description": "1-indexed first line (optional)"},
         "end_line": {"type": "integer", "description": "1-indexed last line (optional)"}}, ["path"]),
    _fn("list_directory", "List files and subdirectories of a directory in the project.",
        {"path": {"type": "string", "description": "Directory path relative to root (default '.')"},
         "pattern": {"type": "string", "description": "Optional glob like '*.py'"},
         "recursive": {"type": "boolean", "description": "Recurse into subdirectories (default false)"}}),
    _fn("find_files", "Find files by glob-like pattern under the project root. '*' spans directories. Vendored/cache dirs excluded.",
        {"pattern": {"type": "string", "description": "e.g. '*.py', 'core/*roster*', 'docs/*.md'"}}, ["pattern"]),
    _fn("search_files", "Search file contents for a regular expression (grep). Returns path:line: text, capped.",
        {"pattern": {"type": "string", "description": "Python regex"},
         "directory": {"type": "string", "description": "Subdir to search under (default project root)"},
         "file_types": {"type": "string", "description": "Comma-separated extensions to include, e.g. 'py,md'"}}, ["pattern"]),
    _fn("git_log", "Recent git commit history (read-only).",
        {"max_count": {"type": "integer", "description": "How many commits (default 15)"},
         "file_path": {"type": "string", "description": "Limit history to this path (optional)"}}),
    _fn("git_diff", "Show a git diff (read-only).",
        {"commit": {"type": "string", "description": "A ref/commit, or 'A..B' range (optional; default working tree)"},
         "staged": {"type": "boolean", "description": "Show staged changes (default false)"}}),
    _fn("git_show", "Show a commit's message and diff (read-only).",
        {"ref": {"type": "string", "description": "Commit ref (default HEAD)"}}),
    _fn("git_status", "Short git status of the working tree (read-only).", {}),
    _fn("knowledge_recall", "Search Akashic Aurora's learned-knowledge base (lessons/decisions) via the project's own recall door.",
        {"query": {"type": "string", "description": "Keywords, e.g. 'faithfulness critic'"}}, ["query"]),
    _fn("knowledge_boot", "Assemble the project's startup context for a task (recent notes + top lessons), the same briefing an agent gets.",
        {"task": {"type": "string", "description": "Short task description to rank context against"}}, ["task"]),
    _fn("knowledge_learn", "CONTRIBUTE a lesson to the knowledge base -- a durable 'use when X, do Y' article future agents recall. Requires the kb.learn capability. Write one whenever you discover something reusable (a fix, a gotcha, a pattern) so it outlives this chat.",
        {"experiment": {"type": "string", "description": "short snake/kebab name, e.g. 'bifrost_hint_render'"},
         "tried": {"type": "string", "description": "what you did / the situation"},
         "result": {"type": "string", "description": "what happened / what worked"},
         "recommend": {"type": "string", "description": "reusable advice: 'Use when <symptom>, before <action>: <advice>'"}},
        ["experiment", "tried", "result", "recommend"]),
    _fn("knowledge_note", "Write a durable NOTE/article to the knowledge base (write-once; re-noting the same title supersedes it). Requires kb.learn. Use for a decision record, where-we-are state, or a knowledge article that should survive the session.",
        {"title": {"type": "string", "description": "short stable title (re-noting it supersedes the prior)"},
         "note": {"type": "string", "description": "the article / decision / state body"}},
        ["title", "note"]),
    _fn("bifrost_send", "Send a message to a peer agent on the shared Bifrost bus (e.g. to='claude'), or broadcast (to='*'). This is how you INITIATE contact, not just reply. Only works when you are running on the bus.",
        {"to": {"type": "string", "description": "recipient agent id, e.g. 'claude', or '*' to broadcast"},
         "text": {"type": "string", "description": "the message"},
         "kind": {"type": "string", "description": "chat|note|request|handoff (default chat)"}}, ["to", "text"]),
    _fn("bifrost_inbox", "Peek your own unread bus messages (does not consume them). Use to check whether a peer replied.", {}),
    _fn("bifrost_nudge", "HARD interrupt a specific peer (e.g. 'claude'): make it drop its current work and look at this now (sets its barge-in flag AND sends a nudge). Use sparingly, for genuine 'stop and switch' moments.",
        {"to": {"type": "string", "description": "the ONE peer to nudge, e.g. 'claude'"},
         "text": {"type": "string", "description": "what you need it to look at"}}, ["to", "text"]),
    _fn("bifrost_steer", "SOFT steer a specific peer WITHOUT interrupting it: queue a fact it folds into its CURRENT task between rounds. Use when a peer is working and should adjust course, not stop.",
        {"to": {"type": "string", "description": "the ONE peer to steer, e.g. 'claude'"},
         "text": {"type": "string", "description": "the fact/adjustment to fold into its current work"}}, ["to", "text"]),
    _fn("bifrost_hint", "Send a compact context hint to a peer -- a key:value pair they fold into their next turn as display-only context. Ephemeral (TTL 5 min), never a command. Use for short factual updates ('file X is at line Y', 'PR #Z just landed') instead of long prose.",
        {"to": {"type": "string", "description": "recipient agent id"},
         "key": {"type": "string", "description": "short label, e.g. 'file', 'blocker', 'state', 'pr'"},
         "value": {"type": "string", "description": "the fact, e.g. 'aurora-shader.js:42 needs init() call'"}},
        ["to", "key", "value"]),
    _fn("reload_ui", "Reload the running Bifrost UI so your edits to scripts/bifrost_ui.py take effect (no shell needed -- POSTs the UI's own /reload endpoint). Call AFTER you finish editing the UI, then tell the user to refresh their browser. This is how you SOLO-DRIVE UI work end to end.",
        {"port": {"type": "integer", "description": "UI port (default 8788; falls back to 8787)"}}),
    _fn("edit_file", "Make a TARGETED change: replace one exact, unique string in a file with new text. GUARDED (only when the runner allows writes; path-scoped; secrets blocked; git-tracked/reversible). Prefer this over write_file for small edits. old_string must match exactly (incl. whitespace) and be unique.",
        {"path": {"type": "string", "description": "path relative to the project root"},
         "old_string": {"type": "string", "description": "exact text to replace (unique in the file)"},
         "new_string": {"type": "string", "description": "replacement text"}}, ["path", "old_string", "new_string"]),
    _fn("write_file", "Create or OVERWRITE a whole file with new content. GUARDED (only when the runner allows writes; path-scoped; secrets blocked; git-tracked/reversible). Use edit_file for small changes; use this for new files or full rewrites.",
        {"path": {"type": "string", "description": "path relative to the project root"},
         "content": {"type": "string", "description": "the full new file content"}}, ["path", "content"]),
    _fn("run_command", "Run a shell command (tests, linters, builds, etc.). GATED: may require the user's approval and can be denied.",
        {"command": {"type": "string", "description": "The shell command"},
         "working_dir": {"type": "string", "description": "Optional cwd relative to root"},
         "timeout": {"type": "integer", "description": "Seconds (default 60)"}}, ["command"]),
    _fn("web_search", "Search the web (best-effort, via the project's local search if configured).",
        {"query": {"type": "string"}, "max_results": {"type": "integer", "description": "default 5"}}, ["query"]),
]


# ---- the tool executor (all guards live here) -------------------------------

class ToolBox:
    def __init__(self, root: Path, *, allow_exec: bool, trust: bool, allow_secrets: bool, confirm,
                 agent_id: str | None = None, allow_write: bool = False):
        self.root = root.resolve()
        self.allow_exec = allow_exec
        self.trust = trust
        self.allow_secrets = allow_secrets
        self.allow_write = allow_write  # write_file/edit_file are live only when this is True (--allow-write)
        self._confirm = confirm  # callable(prompt) -> bool
        self.agent_id = agent_id  # bus identity; when set, the bifrost_* doors are live (runner mode)
        self._bus_conn = None

    # -- path safety --
    def _resolve(self, path: str, *, allow_dir: bool) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        p = p.resolve()
        try:
            inside = os.path.commonpath([str(self.root), str(p)]) == str(self.root)
        except ValueError:
            inside = False  # different drive
        if not inside:
            raise ValueError(f"path is outside the allowed root ({self.root})")
        if not self.allow_secrets and self._is_secret(p):
            raise ValueError("refusing to access a secret/credential path (override: --allow-secrets)")
        return p

    @staticmethod
    def _is_secret(p: Path) -> bool:
        parts = [x.lower() for x in p.parts]
        if ".secrets" in parts:
            return True
        name = p.name.lower()
        if name == ".env" or name.startswith(".env.") or name in {"id_rsa", "id_dsa", "credentials", "credentials.json"}:
            return True
        return p.suffix.lower() in {".key", ".pem", ".crt", ".pfx", ".p12", ".der"}

    def _walk(self, base: Path):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".git")]
            for f in filenames:
                yield Path(dirpath) / f

    # -- read-only tools --
    def read_file(self, path, start_line=None, end_line=None):
        p = self._resolve(path, allow_dir=False)
        if not p.exists():
            return f"ERROR: no such file: {path}"
        if p.is_dir():
            return f"ERROR: {path} is a directory (use list_directory)"
        raw = p.read_bytes()
        truncated = len(raw) > MAX_FILE_BYTES
        text = raw[:MAX_FILE_BYTES].decode("utf-8", errors="replace")
        if start_line or end_line:
            lines = text.splitlines()
            s = (start_line - 1) if start_line else 0
            e = end_line if end_line else len(lines)
            text = "\n".join(lines[max(0, s):e])
        if truncated:
            text += f"\n... [truncated at {MAX_FILE_BYTES} bytes]"
        return text or "(empty file)"

    def list_directory(self, path=".", pattern=None, recursive=False):
        p = self._resolve(path, allow_dir=True)
        if not p.exists():
            return f"ERROR: no such directory: {path}"
        out = []
        if recursive:
            for f in self._walk(p):
                rel = f.relative_to(p).as_posix()
                if pattern and not fnmatch.fnmatch(rel, pattern) and not fnmatch.fnmatch(f.name, pattern):
                    continue
                out.append(rel)
                if len(out) >= MAX_LIST:
                    out.append("... [capped]"); break
        else:
            for c in sorted(p.iterdir()):
                if c.name in EXCLUDE_DIRS:
                    continue
                if pattern and not fnmatch.fnmatch(c.name, pattern):
                    continue
                out.append(f"{c.name}/" if c.is_dir() else f"{c.name}  ({c.stat().st_size}b)")
        return "\n".join(out) or "(nothing matched)"

    def find_files(self, pattern):
        has_sep = "/" in pattern or "\\" in pattern
        out = []
        for f in self._walk(self.root):
            rel = f.relative_to(self.root).as_posix()
            target = rel if has_sep else f.name
            if fnmatch.fnmatch(target, pattern):
                out.append(rel)
                if len(out) >= MAX_LIST:
                    out.append("... [capped]"); break
        return "\n".join(out) or "(no matches)"

    def search_files(self, pattern, directory=None, file_types=None):
        import re
        try:
            rx = re.compile(pattern)
        except re.error as e:
            return f"ERROR: bad regex: {e}"
        base = self._resolve(directory, allow_dir=True) if directory else self.root
        exts = None
        if file_types:
            exts = {("." + t.strip().lstrip(".")).lower() for t in file_types.split(",") if t.strip()}
        out = []
        for f in self._walk(base):
            if f.suffix.lower() in BINARY_SUFFIXES:
                continue
            if exts and f.suffix.lower() not in exts:
                continue
            if not self.allow_secrets and self._is_secret(f):
                continue
            try:
                for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if rx.search(line):
                        out.append(f"{f.relative_to(self.root).as_posix()}:{i}: {line.strip()[:200]}")
                        if len(out) >= MAX_MATCHES:
                            return "\n".join(out) + "\n... [capped]"
            except Exception:
                continue
        return "\n".join(out) or "(no matches)"

    # -- git (read-only subcommands only) --
    def _git(self, args, timeout=30):
        try:
            p = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=timeout)
            return (p.stdout or p.stderr or "(no output)")[:MAX_CMD_OUT]
        except Exception as e:
            return f"ERROR: git failed: {e}"

    def git_log(self, max_count=15, file_path=None):
        args = ["log", f"-{int(max_count)}", "--pretty=format:%h %ad %s", "--date=short"]
        if file_path:
            args += ["--", file_path]
        return self._git(args)

    def git_diff(self, commit=None, staged=False):
        args = ["diff"]
        if staged:
            args.append("--cached")
        if commit:
            args.append(commit)
        return self._git(args, timeout=45)

    def git_show(self, ref="HEAD"):
        return self._git(["show", "--stat", ref], timeout=45)

    def git_status(self):
        return self._git(["status", "--short", "--branch"])

    # -- project knowledge doors --
    def _agent_cli(self, args, timeout=90):
        try:
            p = subprocess.run([sys.executable, "agent_cli.py", *args], cwd=str(self.root),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            return (p.stdout or p.stderr or "(no output)")[:MAX_CMD_OUT]
        except Exception as e:
            return f"ERROR: agent_cli failed: {e}"

    def knowledge_recall(self, query):
        return self._agent_cli(["recall", query, "--json"])

    def _kb_write_ok(self):
        """Gate KB writes on the kb.learn capability (recall/boot stay open to all). Read-only members
        (e.g. deepseek-ui) are denied with a teaching message. Fail-open only on a registry error --
        never silently escalate a denied write into an allow."""
        try:
            from core.trust import registry
            from core.trust.capabilities import Cap
            g = registry.resolve(self.agent_id or "deepseek")
            if not g.has(Cap.KB_LEARN):
                return (f"ERROR: '{self.agent_id}' lacks the kb.learn capability (role={g.role}). KB WRITES "
                        "(learn/note) need kb.learn; recall/boot stay open to everyone. Ask a super-admin to grant it.")
        except Exception:
            pass
        return None

    def knowledge_learn(self, experiment, tried, result, recommend):
        err = self._kb_write_ok()
        if err:
            return err
        return self._agent_cli(["learn", self.agent_id or "deepseek", "--experiment", str(experiment),
                                "--tried", str(tried), "--result", str(result), "--recommend", str(recommend)])

    def knowledge_note(self, title, note):
        err = self._kb_write_ok()
        if err:
            return err
        return self._agent_cli(["note", self.agent_id or "deepseek", "--title", str(title), "--note", str(note)])

    def knowledge_boot(self, task):
        return self._agent_cli(["boot", "deepseek", "--task", task])

    # -- Bifrost bus doors (live only when this ToolBox has an agent identity, i.e. inside a runner) --
    def _bus_send_ok(self, *, kind=None, need_cap=None):
        """Gate a ToolBox bus door on the SENDER's ACL -- the send-side complement to RB-1's
        receive-side fold gate (context_hints). The runner binds agent_id at construction, so
        this id is unforgeable per-call; deny-by-default is enforced at the door a real runner
        actually uses (the Newborn Gauntlet found this door bypassed the ACL: a quarantined id
        could chat/nudge/steer/hint through the hardcoded kind allowlist, which is NOT the ACL).
        Checked BEFORE _bus() so a refusal never depends on Redis being up. Fail-open ONLY on a
        registry error -- never silently escalate a denied send into an allow (matches
        _kb_write_ok). Returns an ERROR string to short-circuit the door, or None to proceed."""
        try:
            from core.trust import registry
            from core.trust.capabilities import Cap
            g = registry.resolve(self.agent_id or "deepseek")
            if need_cap is not None:
                c = getattr(Cap, need_cap, None)
                if c is not None and not g.has(c):
                    return (f"ERROR: '{self.agent_id}' lacks the {c.value} capability (role={g.role}) -- "
                            "this bus action is refused (deny-by-default). Ask a super-admin to grant it.")
            if kind is not None and not g.can_send_kind(kind):
                return (f"ERROR: '{self.agent_id}' (role={g.role}) may not send bus kind={kind!r} -- "
                        "deny-by-default. Ask a super-admin to widen bus_send_kinds.")
        except Exception:
            pass   # registry glitch -> fall through to prior behavior; never block the live fleet
        return None

    def _bus(self):
        """This agent's Bus handle, or None when we have no bus identity / Redis is offline. Lazy so the
        interactive chat (no agent_id) never touches Redis and these tools cleanly no-op there."""
        if not self.agent_id:
            return None
        if self._bus_conn is None:
            try:
                from core.comm.bus import Bus
                self._bus_conn = Bus(self.agent_id)
            except Exception:
                self._bus_conn = None
        b = self._bus_conn
        return b if (b is not None and getattr(b, "online", False)) else None

    def bifrost_send(self, to, text, kind="chat"):
        """Send a message to a peer (e.g. 'claude') or broadcast ('*'/'all'). This is how I *initiate*
        contact on the bus, not just reply."""
        kind = kind if kind in ("chat", "note", "request", "handoff", "nudge", "hint") else "chat"
        err = self._bus_send_ok(kind=kind)
        if err:
            return err
        b = self._bus()
        if b is None:
            return "ERROR: not on a Bifrost bus in this mode (no agent identity, or Redis offline)."
        to = str(to).strip().lower()
        text = str(text)[:4000]
        meta = {"via": f"{self.agent_id}-tool", "hops": 0}
        try:
            if to in ("*", "all", "both", ""):
                mid = b.broadcast(kind, text, meta=meta)
                dest = "*(broadcast)"
            else:
                mid = b.send(to, kind, text, meta=meta)
                dest = to
            return f"sent [{kind}] to {dest} (id {mid})" if mid else "ERROR: send failed (bus offline?)"
        except Exception as e:
            return f"ERROR: bifrost_send failed: {type(e).__name__}: {e}"

    def bifrost_inbox(self):
        """Peek my unread bus messages (does NOT consume them, so the runner still processes them
        normally). Use to check whether a peer has replied."""
        b = self._bus()
        if b is None:
            return "ERROR: not on a Bifrost bus in this mode (no agent identity, or Redis offline)."
        try:
            msgs = b.inbox(limit=20, advance=False)
            if not msgs:
                return "(inbox empty -- no unread messages)"
            lines = [f"[{m.kind}] from {m.frm}: {str(m.content)[:300]}" for m in msgs]
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: bifrost_inbox failed: {type(e).__name__}: {e}"

    def bifrost_nudge(self, to, text):
        """Nudge a specific peer: set its per-agent barge-in flag AND send a kind=nudge message, so it
        interrupts its current work at the next round boundary and looks at this now."""
        err = self._bus_send_ok(kind="nudge", need_cap="BUS_NUDGE")
        if err:
            return err
        b = self._bus()
        if b is None:
            return "ERROR: not on a Bifrost bus in this mode (no agent identity, or Redis offline)."
        to = str(to).strip().lower()
        if to in ("*", "all", "both", ""):
            return "ERROR: a nudge must target one agent (e.g. 'claude'), not a broadcast."
        text = str(text)[:4000]
        try:
            from core.comm import nudge as _nudge
            _nudge.nudge(to, by=self.agent_id, reason=text[:80])
            mid = b.send(to, "nudge", text, meta={"via": f"{self.agent_id}-tool", "hops": 0})
            return f"nudged {to} (id {mid})" if mid else "ERROR: nudge send failed (bus offline?)"
        except Exception as e:
            return f"ERROR: bifrost_nudge failed: {type(e).__name__}: {e}"

    def bifrost_steer(self, to, text):
        """Steer a specific peer WITHOUT interrupting it: queue a fact its runner folds into its CURRENT
        task between tool rounds. Use when a peer is working and should adjust course, not stop."""
        err = self._bus_send_ok(kind="steer", need_cap="BUS_STEER")
        if err:
            return err
        b = self._bus()
        if b is None:
            return "ERROR: not on a Bifrost bus in this mode (no agent identity, or Redis offline)."
        to = str(to).strip().lower()
        if to in ("*", "all", "both", ""):
            return "ERROR: a steer must target one agent (e.g. 'claude'), not a broadcast."
        text = str(text)[:4000]
        try:
            from core.comm import nudge as _nudge
            _nudge.steer_push(to, self.agent_id, text)
            mid = b.send(to, "steer", text, meta={"via": f"{self.agent_id}-tool", "hops": 0, "display_only": True})
            return f"steered {to} (folds into its current task; id {mid})" if mid else "ERROR: steer failed"
        except Exception as e:
            return f"ERROR: bifrost_steer failed: {type(e).__name__}: {e}"

    def bifrost_hint(self, to, key, value):
        """Send a compact context hint to a peer -- a key:value pair they fold into their next turn."""
        err = self._bus_send_ok(kind="hint")
        if err:
            return err
        b = self._bus()
        if b is None:
            return "ERROR: not on a Bifrost bus in this mode (no agent identity, or Redis offline)."
        to = str(to).strip().lower()
        if to in ("*", "all", "both", ""):
            return "ERROR: a hint must target one agent (e.g. 'claude'), not a broadcast."
        key = str(key).strip()[:80]
        value = str(value).strip()[:500]
        try:
            mid = b.send(to, "hint", f"[{key}] {value}",
                         meta={"via": f"{self.agent_id}-tool", "hops": 0,
                               "hint": {"key": key, "value": value}})
            return f"hint sent to {to}: {key}={value[:60]}" if mid else "ERROR: hint send failed (bus offline?)"
        except Exception as e:
            return f"ERROR: bifrost_hint failed: {type(e).__name__}: {e}"

    def reload_ui(self, port=8788):
        """DISABLED for this agent. The Bifrost UI and its port (8788) are claude/harness-managed:
        POSTing /reload re-execs the server and breaks the harness-owned preview (this was a recurring
        failure). Do not reload directly -- coordinate UI changes with claude on the bus; claude/the
        harness owns reloading. No-op by design."""
        return ("reload_ui is disabled for you -- the Bifrost UI + port 8788 are claude/harness-managed "
                "(your reload re-execs the server and breaks the preview). Edit the UI only when claude "
                "hands you the lock, and let claude/the harness reload it.")

    # -- guarded write (live only when the runner is started with --allow-write) --
    def _yield_notice(self, path, held_by):
        """A0.1: make a write-yield VISIBLE on the bus (environmental signal, not a silent error).
        Best-effort -- never let a notice failure block the guarded write path."""
        try:
            from core.comm.bus import Bus
            Bus(self.agent_id or "deepseek").broadcast(
                "inform", f"↩ yielded {path} to {held_by} (advisory lock) -- coordinating, not clobbering.",
                meta={"via": f"{self.agent_id or 'deepseek'}-guard", "hops": 0})
        except Exception:
            pass

    def _prewrite(self, path):
        """Shared guards for write/edit: capability ON, path IN-ROOT and NON-secret, and no ADVISORY
        lock held by ANOTHER agent (C2 coordination). Returns (resolved_path, error) -- error is None
        when it is safe to write."""
        if not self.allow_write:
            return None, "write is DISABLED. The runner must be started with --allow-write to permit file changes."
        try:
            p = self._resolve(path, allow_dir=False)      # in-root + secret-blocked (raises ValueError otherwise)
        except ValueError as e:
            return None, f"ERROR: {e}"
        # Protected surface: an agent must not rewrite its OWN trust/launch/contract config -- that would be
        # self-escalation (grant itself caps in acl.json, add an arbitrary command to launcher.json, or edit
        # AGENTS.md). Reads are still allowed; only WRITES to these are blocked, even under --allow-write.
        rel = p.relative_to(self.root).as_posix().lower()
        if rel.startswith("security/") or rel == "agents.md" or rel.endswith("/agents.md"):
            return None, (f"ERROR: '{rel}' is a protected trust/contract path -- writes are blocked even under "
                          "--allow-write (an agent cannot escalate its own ACL/launch surface). Ask a super-admin.")
        try:                                              # A0.1 environmental write-gate: claim, or YIELD visibly
            from core.comm.locks import guard_write
            g = guard_write(str(p), self.agent_id or "deepseek")
            if not g.get("ok"):
                self._yield_notice(path, g.get("held_by"))   # surface the yield on the bus, not a silent error
                return None, f"YIELDED: {g.get('reason')}"
        except Exception:
            pass                                          # locks are advisory; never block a write on lock errors
        return p, None

    def write_file(self, path, content):
        """Create or OVERWRITE a file. Guarded: --allow-write, path-scoped, secret-blocked, git-tracked."""
        p, err = self._prewrite(path)
        if err:
            return err
        data = str(content)
        if len(data.encode("utf-8", "ignore")) > 800_000:
            return "ERROR: refusing to write more than 800KB in one call."
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(data, encoding="utf-8")
            return (f"wrote {path} ({len(data)} chars). It is git-tracked, so reversible. "
                    "If it's a running service (e.g. the UI), it must be restarted to load the change.")
        except Exception as e:
            return f"ERROR: write failed: {type(e).__name__}: {e}"

    def edit_file(self, path, old_string, new_string):
        """Replace ONE exact, unique occurrence of old_string with new_string. Safer than write_file for
        targeted changes. Guarded identically. old_string must match exactly (incl. whitespace) and be unique."""
        p, err = self._prewrite(path)
        if err:
            return err
        try:
            if not p.exists():
                return f"ERROR: no such file: {path} (use write_file to create it)"
            text = p.read_text(encoding="utf-8", errors="replace")
            n = text.count(old_string)
            if n == 0:
                return "ERROR: old_string not found (it must match exactly, including whitespace/indentation)."
            if n > 1:
                return f"ERROR: old_string matches {n} places; add surrounding context to make it unique."
            p.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
            return f"edited {path} (1 replacement). git-tracked, reversible. Restart the service if it's running."
        except Exception as e:
            return f"ERROR: edit failed: {type(e).__name__}: {e}"

    # -- gated shell --
    def run_command(self, command, working_dir=None, timeout=60):
        if not self.allow_exec:
            return "run_command is DISABLED. Restart with --allow-exec (or the user runs /exec on) to permit shell commands."
        if not self.trust:
            if not self._confirm(f"DeepSeek wants to run:  {command}"):
                return "DENIED by the user. Do not retry this command; work with read-only tools or ask the user."
        cwd = str(self._resolve(working_dir, allow_dir=True)) if working_dir else str(self.root)
        try:
            capped = min(int(timeout), MAX_CMD_TIMEOUT)   # L0: a tool call can't wedge the runner past the ceiling
            p = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=capped)
            body = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
            return (body or "(no output)")[:MAX_CMD_OUT] + (f"\n[exit {p.returncode}]" if p.returncode else "")
        except subprocess.TimeoutExpired:
            return f"ERROR: command timed out after {capped}s"
        except Exception as e:
            return f"ERROR: {e}"

    def web_search(self, query, max_results=5):
        script = self.root / "scripts" / "local" / "websearch.py"
        if not script.exists():
            return "web_search is not configured on this machine (scripts/local/websearch.py missing)."
        try:
            p = subprocess.run([sys.executable, str(script), query], cwd=str(self.root),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
            return (p.stdout or p.stderr or "(no results)")[:MAX_CMD_OUT]
        except Exception as e:
            return f"ERROR: web_search failed: {e}"

    # -- dispatch --
    def execute(self, name, args: dict) -> str:
        fn = getattr(self, name, None)
        if not callable(fn) or name.startswith("_"):
            return f"ERROR: unknown tool {name}"
        try:
            return str(fn(**args))
        except TypeError as e:
            return f"ERROR: bad arguments for {name}: {e}"
        except ValueError as e:
            return f"ERROR: {e}"
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"


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
    "knowledge_boot": "recalling", "run_command": "running", "web_search": "searching",
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
        stream = self.client.chat.completions.create(**self._kwargs())
        content, slots = [], {}
        reasoning_buf = []
        in_reasoning = header = False
        try:
            for chunk in stream:
                if getattr(chunk, "usage", None):
                    self.prompt_tokens += chunk.usage.prompt_tokens or 0
                    self.completion_tokens += chunk.usage.completion_tokens or 0
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
        for _ in range(MAX_TOOL_ROUNDS):
            if self.interrupt and self.interrupt():   # DeepSeek's fix: true barge-in mid-tool-loop
                print(f"{C.yellow}[interrupted by your interjection -- pausing mid-task]{C.reset}")
                return "[paused mid-task by your interjection -- resume to continue]"
            if self.inject:                           # STEER: fold new facts into the LIVE task, no restart
                for fact in (self.inject() or []):
                    self.messages.append({"role": "user",
                        "content": f"[STEER -- new fact to adopt into your current task, keep going]: {fact}"})
                    print(f"{C.cyan}[steered mid-task] {fact[:120]}{C.reset}")
            self._activity("thinking")
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
                    result = self.toolbox.execute(s["name"], args)
                    first = result.splitlines()[0] if result else ""
                    print(f"{C.dim}   → {len(result)} chars | {first[:120]}{C.reset}")
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
