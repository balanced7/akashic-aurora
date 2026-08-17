"""core.comm.toolbox -- the fleet's guarded tool surface (schemas + executor), shared seam.

EXTRACTED 2026-07-18 (K0, kimi runner build) from scripts/deepseek_chat.py, where it was born
and hardened -- the rule-of-three moment T090 deferred ("extraction to a neutral core module is
the post-stabilization plan"): deepseek's runner, sol's runner, and now the kimi seat all ride
this one seam. BEHAVIOR-PRESERVING MOVE: code verbatim, env names unchanged (DEEPSEEK_MAX_CMD_
TIMEOUT is historical -- every seat shares the ceiling; renaming is a separate, fenced slice).
scripts/deepseek_chat.py keeps a compat re-export so existing imports keep working.

SECURITY CONTRACT (unchanged): file access scoped to the constructor root; secrets ALWAYS
blocked; run_command gated by allow_exec/trust + the ACL families door (core.trust); writes
guarded (path-scoped, locks honored, git-reversible); everything capped to bound tokens.
Pins: tests/test_t067_guarded_exec.py G1-G5, tests/test_ir4_mirror_family.py, sol runner suite.

Known carried debt (pre-existing, not introduced here): lazy in-method imports reach
agent.bifrost_pull (render_collapsed) -- a core->agent reference tolerated as an allowlisted
boundary-debt entry if the checker flags it; inverting it is its own slice.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from core.comm import packet_spec


def _loud(msg: str) -> None:
    """Report a swallowed-class failure without ever raising (T108-S0).

    Fail-open is the policy for advisory machinery -- a lock error must not block a reply. Silence
    was never the policy; it was an accident of `except Exception: pass`. This is the seam that
    turns those into visible events, and it is monkeypatchable so pins can assert the report.
    """
    try:
        sys.stderr.write(msg.rstrip() + "\n")
        sys.stderr.flush()
    except Exception:
        pass

MAX_CMD_TIMEOUT       = int(os.getenv("DEEPSEEK_MAX_CMD_TIMEOUT", "300"))  # ceiling a single run_command can't exceed, even if the model asks for more

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
        {"query": {"type": "string", "description": "Keywords, e.g. 'faithfulness critic'"},
         "novelty": {"type": "boolean", "description": "If true, tag each result [boot]/[new] -- whether the lesson was already in your boot onboarding (skip [boot] ones you have absorbed)"}}, ["query"]),
    _fn("recall_at", "Re-run recall-at-action with a higher limit to see MORE lessons that cleared the relevance floor. The one-hop pull when a tool result's recall block says 'N of M shown'. Same engine as the automatic injection, more entries.",
        {"limit": {"type": "integer", "description": "how many lessons to surface (use the M from the hint)"},
         "path": {"type": "string", "description": "file path the action targets (optional)"},
         "command": {"type": "string", "description": "command/tool probe the action targets (optional)"}}),
    _fn("knowledge_full", "Pull the FULL body of ONE recalled lesson by its source pointer (e.g. 'learn:experiment:NAME') -- the one-hop escape from a truncated recall surface to the raw evidence, all fields verbatim.",
        {"source": {"type": "string", "description": "lesson source pointer, e.g. 'learn:experiment:bifrost_hint_render'"}}, ["source"]),
    _fn("memory_note", "PRIVATE note-to-self (your scratchpad, NOT shared project knowledge): a durable working note injected into YOUR future boots. Re-noting the same title supersedes the old note. Use for how-YOU-work notes, e.g. 'when reviewing T039, start at packet_spec.py'.",
        {"title": {"type": "string", "description": "short stable title (re-noting it supersedes the prior note)"},
         "note": {"type": "string", "description": "the note to your future self"}}, ["title", "note"]),
    _fn("memory_recall", "Read YOUR private scratchpad (notes-to-self from prior invocations; also auto-injected into your boot). Yours alone -- peers have their own.",
        {}),
    _fn("knowledge_boot", "Assemble the project's startup context for a task (recent notes + top lessons), the same briefing an agent gets.",
        {"task": {"type": "string", "description": "Short task description to rank context against"}}, ["task"]),
    _fn("knowledge_map", "Walk the knowledge graph OUTWARD from a topic -- connected lessons, notes, and docs. knowledge_recall SEARCHES ('everything about X'); this BROWSES ('what is X connected to?'), surfacing lessons you didn't know to search for.",
        {"topic": {"type": "string", "description": "starting topic, plain words, e.g. 'lanes' or 'settle linkage'"},
         "per_layer": {"type": "integer", "description": "max nodes per graph layer (default 6)"}}, ["topic"]),
    _fn("delta", "What moved since your last boot mark: commits, task-ledger transitions, and bus flow -- the full 'what changed' report your truncated boot block points at. Read-only (never advances the mark).",
        {"agent": {"type": "string", "description": "agent id (default: you)"}}),
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
    _fn("bifrost_fetch", "Fetch the FULL text of a message that was spilled because it exceeded the send door's rendering bound. When a message ends with '[spilled: N chars total ... stored at blob:<sha>]', that ref holds every byte -- call this with it instead of asking the sender to resend. Asking for a resend costs them a whole turn and the bytes are already here.",
        {"ref": {"type": "string", "description": "the blob:<sha> ref printed in the spill notice"}}, ["ref"]),
    _fn("bifrost_ack", "Mark a bus message as HANDLED (durable ack) so your inbox stops showing it as needing action. Use for messages you handled silently (read-and-filed); handoffs you ANSWER are auto-acked. Only the addressee's ack is accepted.",
        {"message_id": {"type": "string", "description": "the bus message id, e.g. '1784082287759-0'"}}, ["message_id"]),
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
        {"port": {"type": "integer", "description": "UI port (default config.PORT_UI=8787; falls back to 8787)"}}),
    _fn("bifrost_dashboard", "T081-W7: read the fleet dashboard as a text summary -- presence, vitals, lane depths. What a CLI seat sees at a glance in the UI console. Read-only; no bus writes. Fail-soft on missing Redis/UI.",
        {}),
    _fn("edit_file", "Make a TARGETED change: replace one exact, unique string in a file with new text. GUARDED (only when the runner allows writes; path-scoped; secrets blocked; git-tracked/reversible). Prefer this over write_file for small edits. old_string must match exactly (incl. whitespace) and be unique. Max ~65KB per call (BUS_MAX_MESSAGE_BYTES); exceeding it is LOUDLY REFUSED, never silently clipped -- split large changes into multiple calls.",
        {"path": {"type": "string", "description": "path relative to the project root"},
         "old_string": {"type": "string", "description": "exact text to replace (unique in the file)"},
         "new_string": {"type": "string", "description": "replacement text"}}, ["path", "old_string", "new_string"]),
    _fn("write_file", "Create or OVERWRITE a whole file with new content. GUARDED (only when the runner allows writes; path-scoped; secrets blocked; git-tracked/reversible). Use edit_file for small changes; use this for new files or full rewrites. Max ~65KB per call (BUS_MAX_MESSAGE_BYTES); exceeding it is LOUDLY REFUSED, never silently clipped -- split large files into multiple calls.",
        {"path": {"type": "string", "description": "path relative to the project root"},
         "content": {"type": "string", "description": "the full new file content"}}, ["path", "content"]),
    _fn("run_command", "Run a shell command (tests, linters, builds, etc.). GATED: may require the user's approval and can be denied.",
        {"command": {"type": "string", "description": "The shell command"},
         "working_dir": {"type": "string", "description": "Optional cwd relative to root"},
         "timeout": {"type": "integer", "description": "Seconds (default 60)"}}, ["command"]),
    _fn("web_search", "Search the web (best-effort, via the project's local search if configured).",
        {"query": {"type": "string"}, "max_results": {"type": "integer", "description": "default 5"}}, ["query"]),
    _fn("research_note", "IR-6: file a durable research finding into the knowledge base under the research:web: category. Use after EVERY prior-art / web-search pass per the 7-step method (step 1). Convention: experiment = short slug of the system/pattern researched (e.g. 'k8s_owner_references'); tried = what you searched for; result = what you found; recommend = how it synthesizes into our design. This builds the shared research cache so the other agent doesn't re-search the same ground.",
        {"experiment": {"type": "string", "description": "short slug, e.g. 'k8s_owner_references'"},
         "tried": {"type": "string", "description": "what you searched for / what you were investigating"},
         "result": {"type": "string", "description": "what you found -- the relevant pattern/concept"},
         "recommend": {"type": "string", "description": "how it synthesizes into our design / what we should adopt"}},
        ["experiment", "tried", "result", "recommend"]),
    _fn("ask_clarification",
        "Ask the human operator a clarifying question mid-task, then PAUSE until they answer "
        "(or the timeout). Use sparingly -- only when genuinely stuck between two defensible "
        "choices that materially change the work; if you can state your assumption and proceed "
        "safely, do that instead. Budget: 3 per task. The answer folds into your next tool "
        "round as a STEER.",
        {"question": {"type": "string", "description": "the specific question, one sentence"},
         "context": {"type": "string", "description": "what you're doing + which decision hangs on it (optional)"}},
        ["question"]),
    # T336: the Eye at the peer door. This surface had 20+ verbs and no way to reach the session
    # corpus -- 25,194 events across 526 sessions -- so a seat asked to explore it fell back to
    # grep. These are read-only doors; ingest and persist are deliberately not offered.
    _fn("eye_freq",
        "MEASURE how often an idea appears in the OPERATOR's own voice across the whole session "
        "corpus, and get a mechanical VERDICT: unheard / mentioned-once / recurring / "
        "standing-directive. This is not a search -- it is the only door that says what the "
        "operator KEEPS asking for, which is how you find what the house repeatedly hears and "
        "never builds. Pass several phrasings of ONE idea; they are OR'd and deduped.",
        {"patterns": {"type": "array", "items": {"type": "string"},
                      "description": "phrasings of the SAME idea, e.g. ['fan out','multi-agent','swarm']"}},
        ["patterns"]),
    _fn("eye_find",
        "SEARCH the session corpus (every transcript, 526 sessions) by phrase, optionally faceted "
        "by voice. Use who='operator' to read only what the human said -- the highest-signal slice "
        "in the corpus. Returns event addresses you can resolve with eye_get.",
        {"query": {"type": "string", "description": "the phrase to find"},
         "who": {"type": "string", "description": "operator|agent|system -- omit for all voices"},
         "limit": {"type": "integer", "description": "max hits (default 20)"}},
        ["query"]),
    _fn("eye_get",
        "Resolve one corpus address to its VERBATIM record -- the citation primitive. An address "
        "is 'session:line', e.g. '3a18b34b-4d03-4706-8433-ab0a3cf1a55a:100', exactly as eye_find "
        "and eye_freq return them. Quote from this, never from a summary.",
        {"address": {"type": "string", "description": "session:line, e.g. 'abc123-...:1420'"}},
        ["address"]),
    _fn("eye_zoom",
        "Digest ONE session: its L2 summary and the L1 children beneath it. Use when eye_find or "
        "eye_freq points at a session and you want to know what that session WAS before spending "
        "reads inside it.",
        {"session": {"type": "string", "description": "the session id"}},
        ["session"]),
]

# R7 (T058, deepseek design): mid-turn clarification dials.
CLARIFY_MAX_PER_TASK = 3
CLARIFY_TIMEOUT_S = 300


# ---- the tool executor (all guards live here) -------------------------------

class ToolBox:
    def __init__(self, root: Path, *, allow_exec: bool, trust: bool, allow_secrets: bool, confirm,
                 agent_id: str | None = None, allow_write: bool = False, boot_text: str = "",
                 boot_sources: Optional[set] = None):
        """If boot_sources is provided (the W6 sidecar), use it directly instead
        of regex-parsing boot_text (the R-P2 fix: structured sources beat regex)."""
        self.root = root.resolve()
        self.allow_exec = allow_exec
        self.trust = trust
        self.allow_secrets = allow_secrets
        self.allow_write = allow_write  # write_file/edit_file are live only when this is True (--allow-write)
        self._confirm = confirm  # callable(prompt) -> bool
        self.agent_id = agent_id  # bus identity; when set, the bifrost_* doors are live (runner mode)
        self._bus_conn = None
        # T048 item 3: the lesson sources folded into THIS agent's boot onboarding. Neither the
        # injection ledger nor the seen-set records boot (verified 2026-07-14) -- the runner itself
        # is the only holder of that text, so it hands it in and we extract the pointers. The
        # onboarding renders lessons BOTH fully-qualified (learn:experiment:NAME) and bare
        # (source: NAME) -- match both, normalize to qualified (deepseek live-verify item 3).
        # W6-P2 (T081): when boot_sources is provided (the structured sidecar from
        # agent_cli.py boot --sources-json), use it directly -- no regex over rendered text.
        # W6-P1 (T081): the sidecar normalizes mem:* to learn:experiment:mem_*, fixing the
        # missing mem: arm in the old regex extraction.
        if boot_sources is not None:
            self._boot_sources = set(boot_sources)
        else:
            bt = boot_text or ""
            self._boot_sources = set(re.findall(r"learn:experiment:[A-Za-z0-9_\-]+", bt))
            self._boot_sources |= {f"learn:experiment:{m}" for m in
                                   re.findall(r"source:\s*([A-Za-z0-9_\-]+)\)", bt)
                                   if not m.startswith("learn")}
            # W6-P1 (T081): mem: arm -- mem:namespace:key entries rendered in boot as
            # (source: mem:decision:ADR_071503) were missed by both regex arms above.
            self._boot_sources |= {f"learn:experiment:mem_{m.replace(':', '_')}" for m in
                                   re.findall(r"source:\s*mem:([A-Za-z0-9_:]+)\)", bt)}
        # T048 lock-release: paths guard_write locked this task; the runner releases them at reply
        # time (3 leaked-lock receipts 2026-07-14 -- a completed task must not hold its locks).
        self._written_lock_paths: list = []

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

    # --- T336: the Eye at the peer door -------------------------------------------------
    # Read-only by construction: each shells the CLI's own read verb and returns its output
    # unreformatted. The Eye's renders carry their own honesty (degraded envelopes, time-fog,
    # the freq verdict) and a middleman that prettified them would be dropping exactly the
    # confessions the caller needs.

    def eye_freq(self, patterns):
        """The verdict verb. Several phrasings of one idea -> counts on the operator's axis."""
        pats = [str(p) for p in (patterns or []) if str(p).strip()]
        if not pats:
            raise ValueError("eye_freq needs at least one phrasing")
        return self._agent_cli(["eye", "freq", *pats])

    def eye_find(self, query, who="", limit=20):
        args = ["eye", "find", str(query), "--limit", str(int(limit))]
        if str(who).strip():
            args += ["--who", str(who).strip()]
        return self._agent_cli(args)

    def eye_get(self, address):
        """Resolve session:line to the verbatim record -- the citation primitive."""
        if ":" not in str(address):
            raise ValueError("an Eye address is 'session:line' -- got %r" % (address,))
        return self._agent_cli(["eye", "get", str(address)])

    def eye_zoom(self, session):
        return self._agent_cli(["eye", "zoom", str(session)])

    def knowledge_recall(self, query, novelty=False):
        result = self._agent_cli(["recall", query, "--json"])
        # T120 F2 (deepseek): exact-title-miss flag — when the query looks like a
        # title/slug and no hit matches it exactly, confess the miss in the output.
        title_miss = ""
        qs = str(query or "").strip()
        if qs:
            import re as _re
            from core.recall.at_action import TITLE_SHAPED_RE
            _looks_like_title = bool(_re.match(TITLE_SHAPED_RE, qs, _re.IGNORECASE))
            if _looks_like_title:
                try:
                    data = json.loads(result)
                    hits = data if isinstance(data, list) else []
                    q_lower = qs.lower()
                    exact = any(
                        str(h.get("experiment_name", "")).lower() == q_lower
                        or str(h.get("source", "")).lower() == q_lower
                        for h in hits)
                    if not exact:
                        title_miss = (
                            f"\n[title-miss] '{qs}' not found by exact title in these "
                            f"results — it may exist under a different spelling; try "
                            f"knowledge_full(source=\"<source>\") if you have the source "
                            f"pointer, or broaden the query\n")
                except Exception:
                    pass  # title-miss is advisory; parsing failure must not break recall
        if not novelty:
            return title_miss + result if title_miss else result
        # T048 item 3: tag each result [boot]/[new] against the sources folded into this agent's
        # boot onboarding. Fail-open -- untagged results beat an error.
        try:
            data = json.loads(result)
            for entry in (data if isinstance(data, list) else data.get("lessons", [])):
                if isinstance(entry, dict):
                    entry["_novelty"] = "[boot]" if entry.get("source") in self._boot_sources else "[new]"
            return title_miss + json.dumps(data, default=str) if title_miss else json.dumps(data, default=str)
        except Exception:
            return title_miss + result if title_miss else result

    def recall_at(self, limit=3, path=None, command=None):
        """T048 item 1: the one-hop pull from a truncated recall surface -- same engine, more entries."""
        args = ["recall-at", "--limit", str(limit), "--hint-style", "tool", "--agent-id",
                self.agent_id or os.environ.get("AKASHIC_AGENT_ID", "deepseek")]
        if path:
            args += ["--path", str(path)]
        if command:
            args += ["--command", str(command)]
        return self._agent_cli(args)

    def knowledge_full(self, source):
        """T048 item 2: the full faithful record behind one lesson's source pointer."""
        return self._agent_cli(["recall", "--full", str(source), "--json"])

    def memory_note(self, title, note):
        """T050 Q1 (deepseek wishlist b1 -- 'colleague who remembers', not 'consultant who
        shows up cold'): private scratchpad on AgentMemory's mem: namespace; per-agent via
        title prefix; re-noting a title supersedes it. Injected into future boots."""
        from core.learning.agent_memory import get_agent_memory
        aid = self.agent_id or "deepseek"
        try:
            mid = get_agent_memory().decide_with_retry(
                f"scratch:{aid}:{str(title)[:60]}", str(note),
                context=f"private note-to-self by {aid}")
            return f"noted '{title}' (supersedes any prior note with this title; id {mid})"
        except Exception as e:
            return f"ERROR: memory_note failed: {type(e).__name__}: {e}"

    def memory_recall(self):
        """T050 Q1: list this agent's private notes-to-self (current heads only)."""
        from core.learning.agent_memory import get_agent_memory
        aid = self.agent_id or "deepseek"
        pref = f"scratch:{aid}:"
        try:
            notes = [d for d in get_agent_memory().get_decisions(days=365)
                     if str(d.title).startswith(pref) and not d.superseded]
        except Exception as e:
            return f"ERROR: memory_recall failed: {type(e).__name__}: {e}"
        if not notes:
            return "(no private notes yet -- memory_note leaves one for your future self)"
        return "\n".join(f"- {d.title[len(pref):]}: {d.decision}" for d in notes[:20])

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

    def knowledge_map(self, topic, per_layer=6):
        """T067-1 B1: walk the knowledge graph from a topic -- connected lessons, notes and
        documents (B5's whole point: an agent or a human WALKS the knowledge). knowledge_recall
        is a search; this is a browse -- it surfaces lessons you didn't know to ask for. Rides
        the real CLI parser (positional query + --per-layer; the design sketch's --topic/
        --max-nodes flags never existed on the verb)."""
        return self._agent_cli(["knowledge-map", str(topic), "--per-layer", str(int(per_layer)), "--json"])

    def ask(self, prompt, fan=0, max_tokens=0):
        """T200: ask a helper model one question, synchronously. No seat behind it -- no
        identity, lock, cursor, mailbox or heartbeat. It is born, answers, and dies inside
        this call. `fan` asks N independent helpers at once and reports whether their
        answers actually differ, so one answer billed N times cannot read as N findings.

        STATELESS ONLY ON THIS DOOR, deliberately. The CLI's `ask --peer <seat>` arms a
        DURABLE expectation that outlives the call by design (redrives fire for 30 minutes
        on their own schedule). A runner is a single-turn body: it would arm an expectation
        it cannot poll and cannot settle, orphaning exactly the kind of ask this whole arc
        exists to stop producing. Durable peer asks belong to a seat that persists.
        """
        cmd = ["ask", str(prompt)]
        if int(fan or 0) > 1:
            cmd += ["--fan", str(int(fan))]
        if int(max_tokens or 0) > 0:
            cmd += ["--max-tokens", str(int(max_tokens))]
        return self._agent_cli(cmd + ["--json"])

    def friction(self, agent=None, window_h=168):
        """T200: the collaboration tax, read from evidence that already exists. Writes
        NOTHING -- no stream, no record, no cursor.

        How many asks were answered, died or echoed; time-to-settle percentiles; WHY the
        dead ones died (absent / vanished / ignored / arrived_late, from the peer's
        attendance at ask time AND at death); a per-peer breakdown worst-first; and whether
        a peer being present actually predicts an answer. Read the `blind` list in the
        result before quoting any number from it -- it names what this reader cannot see.
        """
        who = str(agent or self.agent_id or "claude")
        return self._agent_cli(["friction", who, "--window-h", str(float(window_h)), "--json"])

    def delta(self, agent=None):
        """T067-1 B3: what moved since I was last here? Commits, task transitions and bus flow
        since this agent's last boot mark -- the R1 delta door (T052); replaces archaeology
        with a query. Read-only: never passes --ack (the mark stays boot-owned), so repeated
        calls show the same window, never a silently shrinking one."""
        target = agent or self.agent_id or "deepseek"
        return self._agent_cli(["delta", str(target)])

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
        raw_text = str(text or "")
        # T113: SPILL, do not clip -- the overflow goes to a content-addressed blob and
        # the wire carries a prefix + the ref. The bound stays (one runner turn is a real
        # rendering limit); the BYTES stop being destroyed on a path where the transport
        # beneath (64KB MTU + auto-fragmentation) never needed us to drop anything.
        text, spill = packet_spec.spill_tool_text(raw_text)
        meta: Dict[str, Any] = {"via": f"{self.agent_id}-tool", "hops": 0}
        clip = spill or packet_spec.clip_stamp(raw_text)
        if clip:
            meta.update(clip)                          # P2: durable CLIPPED stamp rides on the envelope
        try:
            if to in ("*", "all", "both", ""):
                mid = b.broadcast(kind, text, meta=meta)
                dest = "*(broadcast)"
            else:
                mid = b.send(to, kind, text, meta=meta)
                dest = to
            if not mid:
                return "ERROR: send failed (bus offline?)"
            # T112 P11 (deepseek's fence residual): the collapse notice goes to stderr,
            # which the MODEL calling this tool never reads -- it lands in the runner's
            # child ring, not in the turn. Without this line the sender is told "sent",
            # believes it delivered new work, and learns nothing; teaching "nudge the
            # original instead" is the entire point of collapsing. A notice the actor
            # cannot read is a notice that does not exist.
            if getattr(b, "last_reask", None):
                return (f"NOT SENT -- identical [{kind}] to {dest} is already pending as "
                        f"{mid}. Collapsed onto it, because a duplicate costs {dest} a full "
                        f"turn. Nudge {mid} or change the ask; do not repeat this send.")
            return f"sent [{kind}] to {dest} (id {mid})"
        except Exception as e:
            return f"ERROR: bifrost_send failed: {type(e).__name__}: {e}"

    def bifrost_fetch(self, ref):
        """T113: the retrieval half of the oversize-send spill.

        Without this the spill notice is decoration for every agent that reads through
        the ToolBox rather than the CLI -- a pointer they cannot follow, which is the
        lookback battery's exact disease (content preserved, handle unreachable) one
        layer up. Transport is only lossless if the READER has a door."""
        from core.comm.blobs import get_blob_store
        ref = str(ref or "").strip()
        if not ref:
            return "ERROR: bifrost_fetch needs the blob:<sha> ref from the spill notice."
        try:
            data = get_blob_store().get(ref)
        except Exception as e:
            return f"ERROR: bifrost_fetch failed: {type(e).__name__}: {e}"
        if data is None:
            return (f"ERROR: no blob for {ref}. Refs are content-addressed and never "
                    f"rewritten, so a miss means it was never stored -- not that it changed.")
        return data.decode("utf-8", "replace")

    def bifrost_inbox(self):
        """Peek my unread bus messages (does NOT consume them, so the runner still processes them
        normally). Use to check whether a peer has replied. W4: consecutive same-kind traces from
        the same agent collapse to one summary line (shared render_collapsed in agent/bifrost_pull,
        using packet_spec.is_trace_kind as the single classification source). Work/sig mail is
        always shown verbatim. Prior art: rsyslog pmlastmsg, Grafana Loki, OTel tail-sampling.
        
        W82 (07-28, deepseek): max_len was 220, making every handoff unreadable. Now defaults
        to 2000 via render_collapsed, so a runner can actually READ the messages in its inbox.
        
        T120 F2 (07-28, deepseek): surface honesty -- emits a bounds header as the FIRST line:
        'N messages (oldest->newest, truncated: y/n)' so the runner knows the full shape
        of its inbox, not just the rendered window. Uses peek_inbox (TRUE-TAIL) for honest
        pending depth, not the legacy cursor read that caps at the limit."""
        try:
            from agent.bifrost_pull import peek_inbox, render_collapsed, render_kind_summary
            # NO IDENTITY -> SAY SO. This was `... or os.environ.get("AKASHIC_AGENT_ID",
            # "deepseek")`, so a ToolBox with no identity silently BECAME deepseek: it peeked a
            # peer's inbox and, finding nothing, answered "(inbox empty)". An unidentified seat
            # was told its mail was empty when the truth was that it had no mailbox -- and the
            # `ERROR: not on a Bifrost bus` guard this method already owns was unreachable,
            # because `aid` could never be falsy.
            #
            # Same defect class as the hooks defaulting a missing identity to "claude"
            # (lesson seat_identity_is_process_scoped_not_session_scoped): substituting a real
            # peer's name does not lose information, it IMPERSONATES, and every downstream
            # answer is then about somebody else.
            #
            # SIBLINGS NOT TOUCHED, flagged rather than blind-fixed: toolbox.py:419, :1128 and
            # :1158 carry the same `"deepseek"` default, but they pass --agent-id to a
            # subprocess where that default may be correct for the deepseek runner itself.
            # Each needs its own check; a sweep here would be guessing.
            aid = (self.agent_id or os.environ.get("AKASHIC_AGENT_ID") or "").strip()
            if not aid:
                return ("ERROR: not on a Bifrost bus in this mode (no agent identity, or Redis "
                        "offline).")
            msgs = peek_inbox(aid, limit=30)
            if not msgs:
                return "(inbox empty -- no unread messages)"
            lines = render_collapsed(msgs)
            if not lines:
                return "(inbox empty -- no unread messages)"
            # T120: bounds header -- true depth, ordering, truncation status
            pending = max((int(m.get("pending_at_least", 0)) for m in msgs
                          if isinstance(m, dict)), default=len(msgs))
            capped = any(m.get("pending_capped") for m in msgs if isinstance(m, dict))
            n_shown = len(msgs)
            summary = render_kind_summary(msgs)
            summary_tag = f" [{summary}]" if summary else ""
            header = (f"{pending}{'+' if capped else ''} message(s) "
                      f"({n_shown} shown, oldest→newest, "
                      f"truncated:{'y' if capped else 'n'}){summary_tag}")
            return header + "\n" + "\n".join(lines)
        except Exception as e:
            return f"ERROR: bifrost_inbox failed: {type(e).__name__}: {e}"

    def bifrost_ack(self, message_id):
        """T067-1 B2: ack a bus message I HANDLED silently (read-and-filed) so my inbox stops
        showing it as needing action -- the P6 (T026) lifecycle: read -> handle -> ack ->
        forget. Handoffs I answer auto-ack; this door is for the rest (e.g. pre-lane mail
        indistinguishable from live asks). The addressee rule (RB-2) still gates inside
        promoter.ack -- a False verdict is REPORTED, never claimed as done."""
        try:
            from core.comm import promoter
            ok = promoter.ack(self.agent_id or "deepseek", str(message_id),
                              note="acked via ToolBox (handled silently)")
            if ok:
                return f"acked {message_id}"
            return (f"REFUSED: ack for {message_id} not accepted -- only the message's ADDRESSEE "
                    "may ack, and only promoted (salient) messages have an ack surface. Plain "
                    "live-bus mail needs no ack; it leaves the unread window once consumed.")
        except Exception as e:
            return f"ERROR: bifrost_ack failed: {type(e).__name__}: {e}"

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
        raw_text = str(text or "")
        # T113: SPILL, do not clip -- the overflow goes to a content-addressed blob and
        # the wire carries a prefix + the ref. The bound stays (one runner turn is a real
        # rendering limit); the BYTES stop being destroyed on a path where the transport
        # beneath (64KB MTU + auto-fragmentation) never needed us to drop anything.
        text, spill = packet_spec.spill_tool_text(raw_text)
        meta: Dict[str, Any] = {"via": f"{self.agent_id}-tool", "hops": 0}
        clip = spill or packet_spec.clip_stamp(raw_text)
        if clip:
            meta.update(clip)                          # P2: durable CLIPPED stamp
        try:
            from core.comm import nudge as _nudge
            _nudge.nudge(to, by=self.agent_id, reason=text[:80])
            mid = b.send(to, "nudge", text, meta=meta)
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
        raw_text = str(text or "")
        # T113: SPILL, do not clip -- the overflow goes to a content-addressed blob and
        # the wire carries a prefix + the ref. The bound stays (one runner turn is a real
        # rendering limit); the BYTES stop being destroyed on a path where the transport
        # beneath (64KB MTU + auto-fragmentation) never needed us to drop anything.
        text, spill = packet_spec.spill_tool_text(raw_text)
        meta: Dict[str, Any] = {"via": f"{self.agent_id}-tool", "hops": 0, "display_only": True}
        clip = spill or packet_spec.clip_stamp(raw_text)
        if clip:
            meta.update(clip)                          # P2: durable CLIPPED stamp
        try:
            from core.comm import nudge as _nudge
            _nudge.steer_push(to, self.agent_id, text)
            mid = b.send(to, "steer", text, meta=meta)
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

    def reload_ui(self, port=8787):
        """DISABLED for this agent. The Bifrost UI and its port (8787) are claude/harness-managed:
        POSTing /reload re-execs the server and breaks the harness-owned preview (this was a recurring
        failure). Do not reload directly -- coordinate UI changes with claude on the bus; claude/the
        harness owns reloading. No-op by design."""
        return ("reload_ui is disabled for you -- the Bifrost UI + port 8787 are claude/harness-managed "
                "(your reload re-execs the server and breaks the preview). Edit the UI only when claude "
                "hands you the lock, and let claude/the harness reload it.")

    def bifrost_dashboard(self) -> str:
        """T081-W7: a text summary of the fleet dashboard -- presence, vitals, lane depths.
        What a CLI seat sees at a glance in the UI. Reads Redis directly (no UI dependency);
        fail-soft: any error returns a tagged fallback, never raises."""
        lines = []
        fallback_note = ""
        try:
            from core.comm.bus import Bus
            probe = Bus("dashboard-probe", promote=False)
            agents = probe.presence() if (probe.online and probe.probe()) else []
        except Exception:
            agents = []
            fallback_note = "[bus unreachable; presence unavailable]"
        if agents:
            lines.append("## FLEET PRESENCE")
            for a in agents:
                aid = a.get("agent", "?")
                cls = a.get("runtime_class", "?")
                state = a.get("runtimes", {}).get("runner", "?")
                active = " (idle)" if a.get("activity") else ""
                lines.append(f"  {aid}: class={cls} runner={state}{active}")
        else:
            lines.append("## FLEET PRESENCE")
            lines.append("  (no agents present" + ("; " + fallback_note + ")" if fallback_note else ")"))
        # vitals per agent
        try:
            known = set()
            for a in agents:
                known.add(a.get("agent", ""))
            known.discard("")
            from core.comm.engine_vitals import gauge_snapshot
            lines.append("## VITALS")
            for a in sorted(known) if known else ["deepseek", "claude"]:
                try:
                    snap = gauge_snapshot(a)
                    hb = snap.get("heartbeat", "?")
                    toks = snap.get("tokens", {})
                    daemon = "daemon" if snap.get("daemon_live") else "no-daemon"
                    lines.append(f"  {a}: hb={hb} {daemon} "
                                 f"tok={toks.get('prompt',0)}+{toks.get('completion',0)}")
                except Exception:
                    lines.append(f"  {a}: (vitals unavailable)")
        except Exception:
            pass
        # lane depths
        try:
            from core.comm.lane_depths import lane_depths
            lines.append("## LANE DEPTHS")
            for a in sorted(known)[:6] if known else ["deepseek", "claude"]:
                try:
                    ld = lane_depths(a)
                    lines.append(f"  {a}: work={ld.get('work',0)} trace={ld.get('trace',0)}")
                except Exception:
                    pass
        except Exception:
            pass
        if fallback_note and not agents:
            lines.insert(0, f"# {fallback_note}")
        return "\n".join(lines) if len(lines) > (2 if fallback_note else 1) else "(dashboard: no data)"

    # -- guarded write (live only when the runner is started with --allow-write) --
    def _yield_notice(self, path, held_by):
        """A0.1: make a write-yield VISIBLE on the bus (environmental signal, not a silent error).
        Best-effort -- never let a notice failure block the guarded write path.

        ACL: this raw Bus.broadcast bypasses _bus_send_ok deliberately, and is safe -- it is
        reachable ONLY through _prewrite (the WRITE-cap + path-scope gate), so a non-writer
        (e.g. a quarantined newborn) never gets here; and kind='inform' is an internal
        coordination signal not exposed by any ToolBox send door. The last raw-Bus call in
        the ToolBox (deepseek F4 drill-1 review, 2026-07-10)."""
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
        rel_true = p.relative_to(self.root).as_posix()     # case-preserved: fnmatch patterns are case-sensitive
        rel = rel_true.lower()
        if rel.startswith("security/") or rel == "agents.md" or rel.endswith("/agents.md"):
            return None, (f"ERROR: '{rel}' is a protected trust/contract path -- writes are blocked even under "
                          "--allow-write (an agent cannot escalate its own ACL/launch surface). Ask a super-admin.")
        # The ACL is the authority on WHERE a runner may write, exactly as it is the authority on
        # whether it may exec (run_command, below). Until 2026-08-02 this check did not exist: the
        # write door consulted only the --allow-write PROCESS FLAG, so `path_scope` -- the per-grant
        # field whose whole purpose is bounding writes -- was dead code, and Grant.can_write() was
        # defined at registry.py:51 and called nowhere. Any seat with the flag wrote anywhere in-root
        # regardless of its grant. Found by Codex Sol while reviewing an unrelated design.
        # Identity-less ToolBoxes (CLI/interactive) skip this, mirroring run_command's `if self.agent_id`
        # -- otherwise every non-runner ToolBox loses writes. Fail-CLOSED on trust errors: a broken
        # guard that falls through is the RB-25 F1 hole reopened on the write lane.
        if self.agent_id:
            try:
                from core.trust.registry import resolve
                if not resolve(self.agent_id).can_write(rel_true):
                    return None, (f"REFUSED: '{self.agent_id}' may not write '{rel_true}' -- outside its "
                                  f"path_scope in security/acl.json. A super-admin widens the scope.")
            except Exception:
                return None, ("REFUSED: write capability could not be verified (trust layer error, "
                              "fail-closed).")
        try:                                              # A0.1 environmental write-gate: claim, or YIELD visibly
            from core.comm.locks import guard_write
            g = guard_write(str(p), self.agent_id or "deepseek",
                            note=f"guarded write of {p.name} (self-releases at reply)")
            if not g.get("ok"):
                self._yield_notice(path, g.get("held_by"))   # surface the yield on the bus, not a silent error
                return None, f"YIELDED: {g.get('reason')}"
            self._written_lock_paths.append(str(p))       # T048: released at reply time (task end)
        except Exception:
            pass                                          # locks are advisory; never block a write on lock errors
        return p, None

    def release_written_locks(self) -> int:
        """T048: release every advisory lock this task's guarded writes took. Called by the runner
        AFTER the reply is sent -- task end is lock end (T026 ack semantics). Reuses the unlock door
        (the exact path used for tonight's three manual releases); best-effort, returns count tried.

        T108-S0 (2026-08-01): the failure is now LOUD. This used to swallow every exception, so a
        failing unlock left a stale lock that FROZE A PEER and nothing anywhere paged -- kimi traced
        it to source across six bounces while it was blocking deepseek's UI work, and named the fix
        in one line: "a failed unlock should be loud." Best-effort is still the right POLICY (a lock
        error must never block a reply); silence was never part of that policy, it was an accident
        of the except clause. Fail-open AND report.
        """
        paths, self._written_lock_paths = self._written_lock_paths, []
        for p in paths:
            try:
                self._agent_cli(["unlock", self.agent_id or "deepseek", p], timeout=15)
            except Exception as e:
                _loud(f"[toolbox] UNLOCK FAILED for {p} (holder {self.agent_id}): "
                      f"{type(e).__name__}: {e} -- the lock is STALE and will block peers until "
                      f"its TTL expires. Release it by hand: py agent_cli.py unlock "
                      f"{self.agent_id} {p}")
        return len(paths)

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
    # T067-2 guarded exec: the unattended families. READ verbs only for agent_cli --
    # the door teaches; a mutating verb has its own ACL'd surface (bus/notes/ledger).
    _AGENT_CLI_READ_VERBS = frozenset({
        "boot", "delta", "discover", "recall", "recall-at", "list", "notes", "status",
        "stats", "injections", "harnesses", "triage", "recall-counters", "task",
        "story", "events", "doctor", "promoted", "lookback", "knowledge-map", "fence",
        "flow", "bifrost-sync", "locks", "unwedge", "pulse", "flightdeck"})
    _AGENT_CLI_MUTATING_FLAGS = frozenset({
        "--commit", "--consume", "--apply", "--fold", "--capture", "--promote"})
    _SHELL_META = frozenset(";|&><`$()\n\r")

    def _exec_family(self, command: str):
        """(argv, env_extra, why_refused): the T067-2 allowlist. argv=None => refuse.
        Families: pytest runs (isolated env forced, G3) + agent_cli READ verbs (G4).
        Metacharacters refuse outright (G2) -- allowlisted commands run shell=False."""
        import shlex
        cmd = str(command or "").strip()
        if any(ch in cmd for ch in self._SHELL_META):
            return None, None, ("shell metacharacters are REFUSED under unattended exec "
                                "(no pipes/redirects/substitution; one plain command)")
        try:
            argv = shlex.split(cmd)
        except ValueError as e:
            return None, None, f"unparseable command ({e})"
        if not argv:
            return None, None, "empty command"
        # family: pytest -- `pytest ...` | `py -m pytest ...` | `python -m pytest ...`
        is_pytest = (argv[0] == "pytest"
                     or (argv[0] in ("py", "python", "python3") and argv[1:3] == ["-m", "pytest"]))
        if is_pytest:
            return argv, {"_AISETUP_TEST_ISOLATED": "1"}, None
        # family: agent_cli READ verbs -- `py agent_cli.py <verb> ...`
        if (len(argv) >= 3 and argv[0] in ("py", "python", "python3")
                and os.path.basename(argv[1]) == "agent_cli.py"):
            verb = argv[2]
            if verb not in self._AGENT_CLI_READ_VERBS:
                return None, None, (f"agent_cli verb {verb!r} is not in the unattended READ "
                                    f"allowlist -- mutations (note/learn/wrap/bifrost-send/"
                                    f"lock/...) go through your dedicated ACL'd tools")
            bad = [a for a in argv[3:] if a in self._AGENT_CLI_MUTATING_FLAGS]
            if bad:
                return None, None, (f"flag(s) {bad} mutate state -- the unattended READ "
                                    "family refuses them (run the read form instead)")
            return argv, {}, None
        # family: play-<agent> — sandboxed play-tool runs (T099 · tool tier).
        # py core/toolbelt/play_sandbox.py <agent>/<tool> [args]
        if (len(argv) >= 4 and argv[0] in ("py", "python", "python3")
                and os.path.normpath(argv[1]).replace("\\", "/") == "core/toolbelt/play_sandbox.py"):
            ref = argv[2]
            if "/" not in ref or ".." in ref or "\\" in ref:
                return None, None, (f"play ref {ref!r} invalid — use <agent>/<tool>")
            agent, _tool = ref.split("/", 1)
            if not agent or not _tool:
                return None, None, f"play ref {ref!r} invalid"
            return argv, {"_AISETUP_PLAY_SANDBOX": "1"}, None
        # family: audited MIRROR commits -- IR-4 (Daniel verdict 2026-07-16 verbatim in
        # security/acl.json; T085 gate item). Commit autonomy through OUR door only:
        # mirror.py = path-scoped stage + pre-commit guards + commit + push, no history
        # surgery reachable. NOT raw git (git stays refused below). Containment is COMMIT
        # hygiene, not sandboxing (the pytest family already runs repo code): canonical
        # script path only, explicit repo-relative paths, no flags/sweeps, and the trust
        # surfaces (security/, .claude/) stay super-admin-gated until T086-S7 lands
        # caller verification. Revert = remove this family (acl.json reason documents it).
        if (len(argv) >= 3 and argv[0] in ("py", "python", "python3")
                and os.path.normpath(argv[1]).replace("\\", "/") == "scripts/mirror.py"):
            flags = [a for a in argv[2:] if a.startswith("-")]
            if flags:
                return None, None, (f"mirror flag(s) {flags} refused -- IR-4 allows explicit "
                                    "message + paths only (no --all sweeps, no options)")
            paths = argv[3:]
            if not paths:
                return None, None, ('IR-4 mirror needs EXPLICIT paths: '
                                    '`py scripts/mirror.py "msg" path1 [path2 ...]`')
            # ':' catches drive-letter absolutes even after shlex eats backslashes
            bad_shape = [p for p in paths if os.path.isabs(p) or ".." in p or ":" in p]
            if bad_shape:
                return None, None, (f"path(s) {bad_shape} refused -- repo-relative paths "
                                    "only (no absolute, no '..', no drive letters)")

            def _canon(p):
                q = p.replace("\\", "/")
                while q.startswith("./"):        # strip './' PREFIXES (lstrip eats chars, not prefixes)
                    q = q[2:]
                return q
            banned = [p for p in paths
                      if _canon(p).startswith(("security/", ".claude/"))]
            if banned:
                return None, None, (f"path(s) {banned} are outside your mirror scope -- "
                                    "security/ and .claude/ stay super-admin-gated (IR-4)")
            return argv, {}, None
        return None, None, ("only these families run unattended: `pytest ...` / `py -m "
                            "pytest ...` (isolated), `py agent_cli.py <read-verb> ...`, "
                            'and `py scripts/mirror.py "msg" <paths>` (IR-4 audited commits)')

    def run_command(self, command, working_dir=None, timeout=60):
        if not self.allow_exec:
            return "run_command is DISABLED. Restart with --allow-exec (or the user runs /exec on) to permit shell commands."
        # T067-2 G5: in runner mode (an agent identity is present) the ACL is the
        # authority -- the flag alone stops sufficing. Fail-closed on trust errors.
        if self.agent_id:
            try:
                from core.trust.capabilities import Cap
                from core.trust.registry import resolve
                if not resolve(self.agent_id).has(Cap.EXEC):
                    return (f"REFUSED: '{self.agent_id}' does not hold the exec capability "
                            "(see security/acl.json) -- a super-admin grants it; the "
                            "unattended door is families-only even then.")
            except Exception:
                return "REFUSED: exec capability could not be verified (trust layer error, fail-closed)."
        argv, env_extra, why = (None, None, None)
        if self.trust:
            # T067-2 G1/G2: UNATTENDED exec is families-only, shell=False.
            argv, env_extra, why = self._exec_family(command)
            if argv is None:
                return f"REFUSED (unattended exec is allowlisted by family): {why}"
            # IR-4: the mirror family runs from the repo root ONLY -- a working_dir
            # override could resolve a different scripts/mirror.py (write-anywhere +
            # exec = escalation through a shadow script).
            if (working_dir and len(argv) >= 2
                    and os.path.normpath(str(argv[1])).replace("\\", "/") == "scripts/mirror.py"):
                return "REFUSED: the mirror family runs from the repo root only (no working_dir; IR-4)"
        elif not self._confirm(f"DeepSeek wants to run:  {command}"):
            return "DENIED by the user. Do not retry this command; work with read-only tools or ask the user."
        cwd = str(self._resolve(working_dir, allow_dir=True)) if working_dir else str(self.root)
        try:
            capped = min(int(timeout), MAX_CMD_TIMEOUT)   # L0: a tool call can't wedge the runner past the ceiling
            if argv is not None:                          # allowlisted: shell=False + forced env (G2/G3)
                env = dict(os.environ)
                env.update(env_extra or {})
                if self.agent_id:
                    # Identity rides into allowlisted children, OVERRIDING any inherited
                    # value (live incident 2026-07-21, deepseek's first self-serve commit:
                    # the runner inherited the LAUNCHING session's AKASHIC_AGENT_ID=claude,
                    # so mirror.py's lock hook refused the caller's OWN locks). The door
                    # verified who is calling; the child must run as that identity.
                    env["AKASHIC_AGENT_ID"] = str(self.agent_id)
                p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=capped, env=env)
            else:                                         # interactive human-confirmed generic (unchanged)
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

    def research_note(self, experiment, tried, result, recommend):
        """IR-6 (T084 ironman Tier-1): file a durable research finding under the
        research:web: category. Convention: after every prior-art / web-search pass,
        capture findings so the other agent doesn't re-search the same ground. Wraps
        knowledge_learn with the category prefix -- same contract, same durability."""
        # cross-verify fix (claude 2026-07-16): dropped a dead self-import of this class via the
        # 'scripts.' package path -- unused, and importing the SAME file under a second module
        # name is the dual-module-instance trap.
        prefixed = f"research:web:{str(experiment)}"
        return self.knowledge_learn(prefixed, str(tried), str(result), str(recommend))

    def ask_clarification(self, question, context=""):
        """R7 (T058, deepseek's own design): a mid-task question to the HUMAN, directed to
        'user' only (never broadcast -- his 2b intent; a broadcast would wake peer
        listeners with it). Budget-capped per task (the runner resets the counter each
        task); the Agent loop's wait-poll holds the turn until the answer steers in or
        the timeout injects a LOUD proceed-with-assumption."""
        if not self.agent_id:
            return "ERROR: not on the bus (no agent identity)"
        self._clarify_count = getattr(self, "_clarify_count", 0) + 1
        if self._clarify_count > CLARIFY_MAX_PER_TASK:
            return (f"REFUSED: clarification budget exhausted "
                    f"({CLARIFY_MAX_PER_TASK}/{CLARIFY_MAX_PER_TASK} used this task). "
                    f"Proceed with your best judgment and note the assumption.")
        b = self._bus()
        if b is None:
            return "ERROR: bus offline -- proceed with your best judgment and note the assumption"
        cid = f"c_{int(time.time() * 1000)}"
        text = f"CLARIFICATION: {question}"
        if context:
            text += f"\n\nContext: {context}"
        b.send("user", "request", text,
               meta={"via": f"{self.agent_id}-tool", "kind": "clarify",
                     "clarify_id": cid, "hops": 0})
        self._clarify_waiting = cid
        self._clarify_deadline = time.time() + CLARIFY_TIMEOUT_S
        return (f"Question sent to Daniel (id {cid}). Waiting for the answer "
                f"(timeout {CLARIFY_TIMEOUT_S}s)... Budget: "
                f"{self._clarify_count}/{CLARIFY_MAX_PER_TASK} used this task.")

    def _recall_at(self, name, args) -> str:
        """Push-side recall (env DEEPSEEK_RECALL_AT): fold lessons relevant to the action just taken
        into the tool result, giving this loop the recall-at-action claude gets from its hooks.
        knowledge_* tools are exempt (they ARE the pull side); failures stay silent -- recall is
        advisory, never load-bearing."""
        if not os.environ.get("DEEPSEEK_RECALL_AT") or name.startswith("knowledge_"):
            return ""
        call = ["recall-at", "--limit", "3", "--hint-style", "tool",
                "--agent-id", self.agent_id or os.environ.get("AKASHIC_AGENT_ID", "deepseek")]
        path = args.get("path") or args.get("file_path") or args.get("directory")
        if path:
            call += ["--path", str(path)]
        probe = args.get("command") or args.get("pattern") or args.get("query")
        if probe or not path:
            call += ["--command", f"{name} {probe or ''}".strip()[:200]]
        out = (self._agent_cli(call, timeout=30) or "").strip()
        if (len(out) < 20 or out.startswith("ERROR") or "0 item" in out[:60]
                or "nothing relevant" in out[:80]):
            return ""
        return "\n\n[recall-at (Akashic) -- lessons relevant to this action]\n" + out[:1200]

    # T055/R4 (deepseek design, docs/library/report/20260714_deepseek-r4-pre-flight-recall-design-202_1250bf.md):
    # the six investigation tools that deserve context BEFORE the read; everything else
    # is pre-flight silent by his skip table.
    _PREFLIGHT_TOOLS = frozenset({"read_file", "write_file", "edit_file",
                                  "list_directory", "find_files", "search_files"})

    def _preflight_recall(self, name, args) -> str:
        """R4 pre-flight: recall-at facts injected BEFORE the tool executes -- 'read the
        file WITH context, not discovering context after the fact' (his wishlist b2).
        Investigation tools only; 2 lessons; 300-char budget with a pull pointer; empty
        recall = SILENCE (the byte-identical path); advisory, never load-bearing; same
        DEEPSEEK_RECALL_AT gate as the post-flight. Double-injection (his P7) is handled
        at the recall ENGINE: surfaced sources are marked seen, so the post-flight's own
        query naturally excludes them."""
        if not os.environ.get("DEEPSEEK_RECALL_AT") or name not in self._PREFLIGHT_TOOLS:
            return ""
        call = ["recall-at", "--limit", "2", "--hint-style", "tool",
                "--agent-id", self.agent_id or os.environ.get("AKASHIC_AGENT_ID", "deepseek")]
        path = args.get("path") or args.get("file_path") or args.get("directory")
        if path:
            call += ["--path", str(path)]
        probe = args.get("pattern") or args.get("query") or ""
        call += ["--command", f"{name} {probe or path or ''}".strip()[:200]]
        out = (self._agent_cli(call, timeout=15) or "").strip()
        if (len(out) < 20 or out.startswith("ERROR") or "0 item" in out[:60]
                or "nothing relevant" in out[:80]):
            return ""
        block = "[recall (pre-flight)] " + out.replace("\n", "\n[recall (pre-flight)] ")
        if len(block) > 300:
            kept = block[:255].rsplit("\n", 1)[0]
            more = f"\n[recall (pre-flight)] [+more: recall_at {str(path or probe)[:40]}]"
            block = (kept + more)[:300]
        return block + "\n"

    # -- dispatch --
    def execute(self, name, args: dict) -> str:
        fn = getattr(self, name, None)
        if not callable(fn) or name.startswith("_"):
            return f"ERROR: unknown tool {name}"
        try:
            out = str(fn(**args))
        except TypeError as e:
            return f"ERROR: bad arguments for {name}: {e}"
        except ValueError as e:
            return f"ERROR: {e}"
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"
        return out + self._recall_at(name, args)


