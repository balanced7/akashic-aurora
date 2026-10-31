"""arsenal.panel.audit -- the append-only record of what the phone asked for, and what was done.

WHY THIS IS NOT OPTIONAL. Every action available here starts or stops something on Daniel's desktop,
and the request arrives from a phone over a tailnet. When the question is "why did the VJ engine stop
at 23:40", the answer must be a FILE, not a recollection -- and it must be a file that the panel itself
cannot rewrite. So:

  * ONE JSON OBJECT PER LINE, appended (`open(path, "a")`), flushed and fsync'd, never rewritten,
    never rotated by this module, never truncated. A reader can tail it; a `grep` can reconstruct the
    whole history.
  * REFUSALS ARE RECORDED TOO, with the reason. A refusal is the interesting one: it is where a bug in
    the allowlist, a stale confirm token, or someone else's script hitting the port would show up, and
    an audit that only records successes is a receipt for the actions you already know about.
  * NO SECRETS, NO ARGV. The service id, the verb, the decision, the state and the elapsed time. The
    command a service runs is in `local/phone-panel.json`, not in a log that might get pasted into a
    chat.

FAIL-SOFT ON WRITE, LOUD ON READ. An audit write that raises must not take the action down with it
(the action already happened), but it must never be silently skipped either: the write returns a
reason and the API reports `audit: "<reason>"` alongside the result. A silent audit gap is the exact
shape this house has paid for before -- a record that claims completeness while its coverage is
partial is worse than an admitted hole.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional


class AuditLog:
    """An append-only JSONL file of panel decisions."""

    def __init__(self, path: str, *, fsync: bool = True) -> None:
        self.path = path
        self.fsync = fsync

    # ------------------------------------------------------------------------------ write
    def write(self, record: Dict[str, Any]) -> str:
        """Append ONE decision. Returns "" on success, or a reason it could not be written."""
        row = dict(record)
        row.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()))
        row["epoch"] = round(time.time(), 3)
        line = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if "\n" in line:                                  # json.dumps escapes newlines; belt and braces
            line = line.replace("\n", " ")
        try:
            parent = os.path.dirname(os.path.abspath(self.path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(line + "\n")
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())
            return ""
        except Exception as exc:
            return f"the audit line could not be written: {type(exc).__name__}: {exc}"

    # ------------------------------------------------------------------------------ read
    def tail(self, limit: int = 20) -> List[Dict[str, Any]]:
        """The last `limit` records, newest last. Unreadable lines are skipped, not fatal."""
        out: List[Dict[str, Any]] = []
        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
        except FileNotFoundError:
            return []
        except Exception:
            return out[-limit:]
        return out[-limit:]
