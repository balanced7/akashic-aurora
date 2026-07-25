"""Pins: the runner must meter what actually drives its cost -- cache split and context size.

WHY THIS EXISTS
---------------
2026-07-25, from turn_metrics (all-time): deepseek 309 turns / 393,247,762 tokens
(avg 1,272,646 per turn); worst single turn 11,439,058 tokens across 127 hops in 575s;
133 of 309 turns over 1M. Meanwhile recall injections cost ~18k tokens per 24h -- three
orders of magnitude smaller. The burn is the agentic loop, not the memory layer.

Mechanism, confirmed in code: `self.messages` is never trimmed (only reset wholesale), and
tool results are appended RAW with MAX_FILE_BYTES=120_000. So one large read early in a turn
is re-sent on every subsequent hop -- quadratic in hops.

We are NOT fixing that here. `meters before levers` (T078 R1): DeepSeek bills a cached prompt
prefix at roughly 0.1x, so the token counts above may overstate real cost by up to 10x, and we
currently record NO cache split at all. Compacting before we can read the cache rate would be
tuning against arithmetic instead of evidence -- Daniel's call, 2026-07-25.

So these pins cover the METER only:
  - the cache hit/miss split is accumulated when the provider reports it;
  - a provider that omits those fields must not break accounting (fail-soft);
  - the context high-water mark per turn is observable, so a runaway turn is visible WHILE
    it runs rather than 575 seconds later.

And one guard learned the hard way today: T078-W1's TokenJournal shipped unit-green and never
recorded a single turn in production, because nothing pinned that a runner actually reached
it. So the last pin here asserts the counters are wired to the real accumulation path.
"""
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CHAT_SRC = (ROOT / "scripts" / "deepseek_chat.py").read_text(encoding="utf-8")


class _Usage:
    def __init__(self, p, c, hit=None, miss=None):
        self.prompt_tokens = p
        self.completion_tokens = c
        if hit is not None:
            self.prompt_cache_hit_tokens = hit
        if miss is not None:
            self.prompt_cache_miss_tokens = miss


def _agent():
    """A bare Agent instance without running __init__ (no API key, no network)."""
    import deepseek_chat as dc
    a = dc.Agent.__new__(dc.Agent)
    a.prompt_tokens = a.completion_tokens = 0
    a.cache_hit_tokens = a.cache_miss_tokens = 0
    a.context_high_water = 0
    a.messages = [{"role": "system", "content": "s"}]
    return a


def test_cache_split_is_accumulated_when_the_provider_reports_it():
    a = _agent()
    a._absorb_usage(_Usage(1000, 200, hit=900, miss=100))
    a._absorb_usage(_Usage(1000, 200, hit=950, miss=50))
    assert a.prompt_tokens == 2000
    assert a.completion_tokens == 400
    assert a.cache_hit_tokens == 1850, "cached prefix tokens must accumulate -- they bill ~0.1x"
    assert a.cache_miss_tokens == 150


def test_missing_cache_fields_do_not_break_accounting():
    """Not every provider reports a cache split. Absence must degrade, never raise."""
    a = _agent()
    a._absorb_usage(_Usage(500, 100))
    assert a.prompt_tokens == 500 and a.completion_tokens == 100
    assert a.cache_hit_tokens == 0 and a.cache_miss_tokens == 0


def test_cache_rate_is_reportable_and_safe_at_zero():
    a = _agent()
    assert a.cache_rate() is None, "no data must report None, never a fake 0%"
    a._absorb_usage(_Usage(1000, 10, hit=800, miss=200))
    assert abs(a.cache_rate() - 0.8) < 1e-6


def test_context_high_water_tracks_the_real_driver():
    """The cost driver is how much context each hop re-sends, not the turn's token total."""
    a = _agent()
    a.messages.append({"role": "tool", "content": "x" * 40_000})
    a._mark_context()
    first = a.context_high_water
    assert first > 30_000, f"high-water should reflect the appended payload, got {first}"
    a.messages.append({"role": "tool", "content": "y" * 5})
    a._mark_context()
    assert a.context_high_water >= first, "high-water must never go down within a turn"


def test_meter_is_wired_to_the_streaming_usage_path():
    """T078-W1's lesson: a meter nothing calls is indistinguishable from a dead one."""
    tree = ast.parse(CHAT_SRC)
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in ("_absorb_usage", "_mark_context")
    ]
    names = {c.func.attr for c in calls}
    assert "_absorb_usage" in names, "usage is parsed but _absorb_usage is never called"
    assert "_mark_context" in names, "context high-water is defined but never sampled"
