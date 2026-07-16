"""runner_token_journal -- daily token-count ledger (T078 W1: C6 meter).

One JSON file per agent per day: state/runner_<agent>_<YYYY-MM-DD>.json.
The runner adds each turn's prompt+completion tokens; the doctor reads it.
Crossing midnight: a new day creates a fresh file; yesterday's persists.

T056 JOIN: the data source is turn_metrics.record's `tokens` kwarg, already
wired on the hot path -- attribute_turn() HINCRBYs each turn's token counts
into the task-cost accumulator per owner-matched active task. This journal is
the DAILY AGGREGATE for the doctor dashboard line (per-task costs live in the
accumulator and finalize at task DONE).

COST ESTIMATE: DeepSeek pricing as of 2026-07 is v4-pro ~$0.55/M input +
~$2.19/M output; v4-flash ~$0.14/M input + ~$0.56/M output. The journal tracks
total tokens, not per-model -- the cost line uses a blended estimate for the
default mix (mostly v4-pro). Honest: this is a DASHBOARD, not a billing ledger.
"""
from __future__ import annotations

import json
import os
import time
from typing import Dict, Optional


class TokenJournal:
    """Daily cumulative token count for one agent. Thread-safe enough: the runner
    is single-threaded per turn-close (the record path runs in the main loop)."""

    def __init__(self, agent: str, journal_dir: Optional[str] = None):
        self._agent = str(agent)
        base = journal_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "state")
        os.makedirs(base, exist_ok=True)
        self._base = base
        self.turns: int = 0
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.model: str = ""
        self._load()

    # -- public ----------------------------------------------------------

    def add_turn(self, prompt: int = 0, completion: int = 0, model: str = "") -> None:
        self.turns += 1
        self.prompt_tokens += max(0, int(prompt or 0))
        self.completion_tokens += max(0, int(completion or 0))
        if model and not self.model:
            self.model = str(model)
        self._save()

    def total_cost_est(self) -> float:
        """Blended v4-pro estimate: ~$0.55/M prompt + ~$2.19/M completion.
        Honest: this is an ESTIMATE, not a billing record. v4-flash is ~10x cheaper
        and mixes in when the routing slice (W2) lands -- the estimate overstates
        cost for flash turns (conservative, the right direction for a dashboard)."""
        prompt_cost = self.prompt_tokens / 1_000_000 * 0.55
        completion_cost = self.completion_tokens / 1_000_000 * 2.19
        return round(prompt_cost + completion_cost, 3)

    def today(self) -> str:
        return time.strftime("%Y-%m-%d")

    @property
    def _path(self) -> str:
        """Derived PER CALL from today() (deepseek's date-crossing finding,
        2026-07-15 night): a journal constructed before midnight must write
        today's file after midnight -- one date source, path and stamp can
        never split. A day boundary mid-process starts a fresh day file;
        counters reset at the next _load() of the new path."""
        return os.path.join(self._base, f"runner_{self._agent}_{self.today()}.json")

    def to_dict(self) -> Dict:
        return {
            "agent": self._agent,
            "date": self.today(),
            "turns": self.turns,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "model": self.model or "deepseek-v4-pro",
            "cost_est": self.total_cost_est(),
        }

    # -- internal ----------------------------------------------------------

    def _load(self) -> None:
        try:
            if not os.path.exists(self._path):
                return
            with open(self._path, encoding="utf-8") as f:
                data = json.loads(f.read().strip() or "{}") or {}
            if data.get("date") != self.today():
                return  # yesterday's file, don't load
            self.turns = int(data.get("turns", 0) or 0)
            self.prompt_tokens = int(data.get("prompt_tokens", 0) or 0)
            self.completion_tokens = int(data.get("completion_tokens", 0) or 0)
            self.model = str(data.get("model") or "")
        except Exception:
            pass

    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f)
        except Exception:
            pass
