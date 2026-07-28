"""runner_token_journal -- daily token-count ledger (T078 W1: C6 meter).

One JSON file per agent per day: state/runner_<agent>_<YYYY-MM-DD>.json.
The runner adds each turn's prompt+completion tokens; the doctor reads it.
Crossing midnight: a new day creates a fresh file; yesterday's persists.

T056 JOIN: the data source is turn_metrics.record's `tokens` kwarg, already
wired on the hot path -- attribute_turn() HINCRBYs each turn's token counts
into the task-cost accumulator per owner-matched active task. This journal is
the DAILY AGGREGATE for the doctor dashboard line (per-task costs live in the
accumulator and finalize at task DONE).

T110 (2026-07-28) -- WHAT THIS METER MAY AND MAY NOT SAY.
Until T110 this file held ONE hardcoded price pair -- DeepSeek v4-pro's
$0.55/M + $2.19/M -- and ran EVERY agent's tokens through it. kimi's live
journal read {"model": "kimi-k3", "cost_est": 9.076}: DeepSeek's price list
applied to Moonshot's tokens, with "deepseek-v4-pro" written into kimi's own
file as the default model name. It did not merely guess the price; it
misreported the vendor. Three defects stacked and pushed the number in
OPPOSITE directions, so no scale factor could rescue it: cross-provider
pricing, first-model-of-the-day pinned forever, and cache hits billed at the
full fresh-input rate.

The rule this file now follows: PRICE WHAT WE CAN SOURCE, AND MAKE WHAT WE
CANNOT SOURCE VISIBLE RATHER THAN PLAUSIBLE. A model absent from PRICES is
counted in full, named in `unpriced_models`, and excluded from `cost_est` --
never absorbed at another vendor's rate. A visible gap is fillable; a
confident wrong number gets believed, and this meter feeds the cost-routing
work (Sol's admission proposal 42884bc names raw provider/model usage as a
prerequisite).

Still honest about what it is: a DASHBOARD, not a billing ledger. Rates carry
`as_of` and are estimates. When the dashboard and the invoice disagree, the
invoice is right and the table needs an edit.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------- price table
#
# One entry per model we can actually source a rate for. USD per 1M tokens.
# `cached_prompt` is the discounted rate for prompt tokens served from the
# provider's context cache -- the runner already measures the hit/miss split
# per turn (T078 W1b, bifrost_runner_deepseek.py:470); before T110 it printed
# that split to the console and dropped it one line before this ledger, so a
# 323:1 prompt:completion day of mostly re-read context was billed as new.
#
# ADDING A MODEL: put the vendor's published rate here with `as_of` and
# `source`. Do NOT approximate one vendor with another's number -- an absent
# entry is a designed, visible state, and the unpriced line on the doctor
# dashboard exists to ask for exactly this edit.
PRICES: Dict[str, Dict[str, Any]] = {
    "deepseek-v4-pro": {
        "prompt": 0.55, "cached_prompt": 0.055, "completion": 2.19,
        "as_of": "2026-07", "source": "T078 W1 docstring, carried forward",
    },
    "deepseek-v4-flash": {
        "prompt": 0.14, "cached_prompt": 0.014, "completion": 0.56,
        "as_of": "2026-07", "source": "T078 W1 docstring, carried forward",
    },
}

# Which model an agent's UNLABELLED turns belong to. This is a per-agent
# statement of fact ("the deepseek runner calls deepseek models"), NOT a
# fallback: an agent absent from this map stays unpriced. A catch-all default
# is how the original defect was written -- kimi's turns reached DeepSeek's
# table through exactly that door.
AGENT_DEFAULT_MODEL: Dict[str, str] = {
    "deepseek": "deepseek-v4-pro",
}

UNKNOWN_MODEL = "unknown"


def price_of(model: str) -> Optional[Dict[str, Any]]:
    """The rate card for `model`, or None if we cannot source one. None is a
    legitimate answer and callers must RENDER it, never substitute."""
    return PRICES.get(str(model or "").strip())


class TokenJournal:
    """Daily cumulative token count for one agent, attributed per model.
    Thread-safe enough: the runner is single-threaded per turn-close (the
    record path runs in the main loop)."""

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
        self.cached_prompt_tokens: int = 0
        self.model: str = ""                       # first seen; kept for compat
        # model -> {turns, prompt, cached_prompt, completion}
        self.models: Dict[str, Dict[str, int]] = {}
        self._load()

    # -- public ----------------------------------------------------------

    def add_turn(self, prompt: int = 0, completion: int = 0, model: str = "",
                 cached_prompt: int = 0) -> None:
        """Record one turn. `cached_prompt` is the SUBSET of `prompt` served
        from cache (the shape every provider reports it in), so it is never
        added to the total -- only repriced."""
        p = max(0, int(prompt or 0))
        c = max(0, int(completion or 0))
        cached = min(p, max(0, int(cached_prompt or 0)))

        self.turns += 1
        self.prompt_tokens += p
        self.completion_tokens += c
        self.cached_prompt_tokens += cached
        if model and not self.model:
            self.model = str(model)

        bucket = self.models.setdefault(
            self._resolve_model(model),
            {"turns": 0, "prompt": 0, "cached_prompt": 0, "completion": 0})
        bucket["turns"] += 1
        bucket["prompt"] += p
        bucket["cached_prompt"] += cached
        bucket["completion"] += c
        self._save()

    def total_cost_est(self) -> float:
        """Sum of the PRICED buckets only. Tokens we cannot source a rate for
        are excluded here and surfaced by unpriced_tokens() -- pricing them at
        some other vendor's rate is the defect this meter was built to stop."""
        total = 0.0
        for model, b in self.models.items():
            rate = price_of(model)
            if rate is None:
                continue
            cached = min(b.get("cached_prompt", 0), b.get("prompt", 0))
            fresh = b.get("prompt", 0) - cached
            total += fresh / 1_000_000 * rate["prompt"]
            total += cached / 1_000_000 * rate.get("cached_prompt", rate["prompt"])
            total += b.get("completion", 0) / 1_000_000 * rate["completion"]
        return round(total, 3)

    def unpriced_tokens(self) -> int:
        """Real tokens we deliberately refuse to price. Counted, never hidden."""
        return sum(b.get("prompt", 0) + b.get("completion", 0)
                   for model, b in self.models.items() if price_of(model) is None)

    def unpriced_models(self) -> List[str]:
        """Which models the rate table is missing -- the shopping list for
        whoever fills it in."""
        return sorted(m for m in self.models if price_of(m) is None)

    def dominant_model(self) -> str:
        """The model carrying the most tokens today. Never invents a name: an
        empty journal reports UNKNOWN_MODEL, not a vendor."""
        if not self.models:
            return UNKNOWN_MODEL
        return max(self.models.items(),
                   key=lambda kv: kv[1].get("prompt", 0) + kv[1].get("completion", 0))[0]

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
        # Every pre-T110 key is preserved so existing readers keep working; the
        # new keys are additive. `model` no longer falls back to a vendor name
        # we were never told -- it reports the dominant model or UNKNOWN.
        return {
            "agent": self._agent,
            "date": self.today(),
            "turns": self.turns,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cached_prompt_tokens": self.cached_prompt_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "model": self.dominant_model(),
            "models": self.models,
            "cost_est": self.total_cost_est(),
            "unpriced_tokens": self.unpriced_tokens(),
            "unpriced_models": self.unpriced_models(),
        }

    # -- internal ----------------------------------------------------------

    def _resolve_model(self, model: str) -> str:
        """Turn-level label first, then the agent's DECLARED default, then
        UNKNOWN. Each step is a statement someone made; none is a guess."""
        name = str(model or "").strip()
        if name:
            return name
        return AGENT_DEFAULT_MODEL.get(self._agent, UNKNOWN_MODEL)

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
            self.cached_prompt_tokens = int(data.get("cached_prompt_tokens", 0) or 0)
            self.model = str(data.get("model") or "")
            models = data.get("models")
            if isinstance(models, dict) and models:
                self.models = {
                    str(k): {"turns": int(v.get("turns", 0) or 0),
                             "prompt": int(v.get("prompt", 0) or 0),
                             "cached_prompt": int(v.get("cached_prompt", 0) or 0),
                             "completion": int(v.get("completion", 0) or 0)}
                    for k, v in models.items() if isinstance(v, dict)}
            elif self.turns:
                # PRE-T110 FLAT FILE. The real journals on disk have this shape
                # and today's spend is inside one of them -- reconstruct a single
                # bucket from the flat counters so upgrading the meter never
                # blanks the day it inherits. An unlabelled legacy file resolves
                # through the same narrow agent default as a live turn, so a
                # legacy kimi file does NOT acquire DeepSeek's rate on the way in.
                self.models = {self._resolve_model(self.model): {
                    "turns": self.turns, "prompt": self.prompt_tokens,
                    "cached_prompt": self.cached_prompt_tokens,
                    "completion": self.completion_tokens}}
        except Exception:
            pass

    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f)
        except Exception:
            pass
