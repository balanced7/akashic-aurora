"""T110 -- THE COST METER MUST NOT LIE ACROSS PROVIDERS. RED first (M3).

FOUND 2026-07-28 while verifying Sol's model-router blocker (that half was already
fixed at 81eab72). The live journals on disk say it plainly:

    state/runner_kimi_2026-07-28.json
      {"model": "kimi-k3", ..., "cost_est": 9.076}

Nine dollars and seven cents, computed by applying DEEPSEEK's price list to
MOONSHOT's tokens. TokenJournal.total_cost_est() hardcodes $0.55/M prompt +
$2.19/M completion -- v4-pro's rates, documented as such in its own docstring --
and every agent's journal runs through it. kimi's and sol's cost lines have never
been anything but DeepSeek prices wearing another provider's model name.

Three defects stack, and they push the number in OPPOSITE directions, so no
scale factor can rescue it:

  1. CROSS-PROVIDER PRICING. One table, applied to all. `to_dict()` even
     defaults an unknown model to the string "deepseek-v4-pro" -- the meter
     does not merely guess the price, it MISREPORTS THE MODEL.

  2. FIRST MODEL OF THE DAY PINS FOREVER. `if model and not self.model` --
     an agent that switches models mid-day (the whole point of the routing
     slice this meter is supposed to feed) reports the day under whichever
     model happened to run first.

  3. CACHE HITS BILLED AT FULL FRESH-INPUT PRICE. The sharpest one: the runner
     ALREADY MEASURES the split (T078 W1b, bifrost_runner_deepseek.py:470 --
     `cache_hit`/`cache_miss` per turn) and PRINTS it to the console, then drops
     it one line before add_turn(). Today's deepseek journal is 104M prompt
     tokens against 322k completion -- a 323:1 ratio that is mostly re-read
     context, priced as if every token were fresh.

WHY THIS IS NOT A COSMETIC CONSTANT. Sol's routing proposal (42884bc) names raw
provider/model usage as a PREREQUISITE for automatic admission; the tempo
doctrine routes by cost; Daniel's standing token-frugality directive makes cost
a feature. All three read this meter. And the one ground truth we have -- the
observed kimi spend during the overnight poison loop -- disagrees with what the
meter recorded for that day by a multiple, in the direction that says "cheap".
A meter that reads low on the expensive lane is how a router learns the wrong
lane is cheap.

THE DESIGN THESE PINS ENCODE: price what we can source, and make what we cannot
source VISIBLE rather than plausible. An unpriced model must never be silently
absorbed at some other vendor's rate -- M10's refusal is the precedent (never
widen a definition until the instrument flatters you). Unpriced tokens are
counted, labelled, and surfaced so the gap is fillable.

  P1  A NON-DEEPSEEK MODEL IS NEVER DEEPSEEK-PRICED.
  P2  AN UNPRICED MODEL IS LOUD, NOT ZERO: tokens counted and reported.
  P3  THE MODEL NAME IS NEVER FABRICATED (no "deepseek-v4-pro" default).
  P4  A SECOND MODEL IN THE SAME DAY IS RECORDED, not swallowed by the first.
  P5  CACHED PROMPT TOKENS COST LESS THAN FRESH ONES.
  P6  LEGACY JOURNALS ON DISK STILL LOAD (the real files have the flat shape).
  P7  THE AGENT DEFAULT IS EXPLICIT AND NARROW -- it resolves deepseek's own
      unlabelled turns and MUST NOT catch anyone else.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.runner_token_journal import TokenJournal


# --------------------------------------------------------------- P1 cross-provider
def test_p1_a_non_deepseek_model_is_never_deepseek_priced(tmp_path):
    """The live defect, reproduced from the real journal shape."""
    k = TokenJournal("kimi", journal_dir=str(tmp_path))
    k.add_turn(prompt=15_960_666, completion=135_810, model="kimi-k3")

    deepseek_price = 15_960_666 / 1e6 * 0.55 + 135_810 / 1e6 * 2.19
    assert abs(k.total_cost_est() - deepseek_price) > 0.01, (
        f"CROSS-PROVIDER PRICING: kimi's tokens cost ${k.total_cost_est():.3f}, which is "
        f"exactly DeepSeek's v4-pro table (${deepseek_price:.3f}) applied to Moonshot's "
        f"tokens. This is the number on Daniel's dashboard today. Either price kimi-k3 at "
        f"a sourced kimi rate or report it UNPRICED -- but a confident wrong number is "
        f"worse than a visible gap, because a router will believe it.")


# --------------------------------------------------------------- P2 unpriced is loud
def test_p2_an_unpriced_model_is_loud_not_zero(tmp_path):
    """Refusing to guess must not read as 'this was free'. The tokens are real."""
    j = TokenJournal("kimi", journal_dir=str(tmp_path))
    j.add_turn(prompt=1_000_000, completion=100_000, model="kimi-k3")
    d = j.to_dict()

    assert d.get("unpriced_tokens", 0) == 1_100_000, (
        f"SILENT GAP: 1.1M tokens we cannot price must be COUNTED and REPORTED as "
        f"unpriced, not quietly dropped to a $0 line that reads as free usage. "
        f"to_dict()={d}")
    assert "kimi-k3" in str(d.get("unpriced_models", "")), (
        f"UNNAMED GAP: the unpriced bucket must name WHICH model it could not price, "
        f"or nobody can fill the rate in. to_dict()={d}")


# --------------------------------------------------------------- P3 no fabricated model
def test_p3_the_model_name_is_never_fabricated(tmp_path):
    """`"model": self.model or "deepseek-v4-pro"` -- the meter asserted a vendor it
    was never told about. Unknown must render as unknown."""
    j = TokenJournal("sol", journal_dir=str(tmp_path))
    j.add_turn(prompt=1000, completion=100)          # no model passed
    assert "deepseek" not in str(j.to_dict().get("model", "")).lower(), (
        f"FABRICATED MODEL: an unlabelled turn on agent 'sol' was reported as "
        f"model={j.to_dict().get('model')!r}. The meter invented a vendor. "
        f"An unknown model must SAY unknown.")


# --------------------------------------------------------------- P4 model switching
def test_p4_a_second_model_in_the_same_day_is_recorded(tmp_path):
    """`if model and not self.model` pins the first model for the whole day --
    directly defeating the routing slice this meter exists to feed."""
    j = TokenJournal("deepseek", journal_dir=str(tmp_path))
    j.add_turn(prompt=1_000_000, completion=10_000, model="deepseek-v4-pro")
    j.add_turn(prompt=1_000_000, completion=10_000, model="deepseek-v4-flash")

    models = j.to_dict().get("models") or {}
    assert "deepseek-v4-flash" in models, (
        f"MODEL SWITCH SWALLOWED: the day ran two models and the journal reports "
        f"only the first. A cost meter that cannot see the cheap lane cannot show "
        f"that routing to it worked. models={models}")
    assert models.get("deepseek-v4-flash", {}).get("prompt") == 1_000_000, (
        f"per-model attribution must carry the tokens, not just the name: {models}")


# --------------------------------------------------------------- P5 cache split
def test_p5_cached_prompt_tokens_cost_less_than_fresh(tmp_path):
    """The runner measures cache_hit/cache_miss per turn and throws it away one
    line before the ledger. Cached input is roughly a tenth the price; today the
    meter bills 104M mostly-cached prompt tokens at full fresh rate."""
    fresh = TokenJournal("deepseek", journal_dir=str(tmp_path / "a"))
    fresh.add_turn(prompt=1_000_000, completion=0,
                   model="deepseek-v4-pro", cached_prompt=0)

    cached = TokenJournal("deepseek", journal_dir=str(tmp_path / "b"))
    cached.add_turn(prompt=1_000_000, completion=0,
                    model="deepseek-v4-pro", cached_prompt=1_000_000)

    assert cached.total_cost_est() < fresh.total_cost_est(), (
        f"CACHE BLINDNESS: 1M fully-cached prompt tokens (${cached.total_cost_est():.3f}) "
        f"must cost less than 1M fresh ones (${fresh.total_cost_est():.3f}). The split "
        f"is ALREADY MEASURED at the call site and discarded; today's 323:1 "
        f"prompt:completion ratio is mostly re-read context billed as new.")


# --------------------------------------------------------------- P6 legacy on-disk shape
def test_p6_legacy_journals_on_disk_still_load(tmp_path):
    """The real files have the flat pre-T110 shape. A meter that forgets today's
    spend on upgrade is its own defect."""
    j = TokenJournal("deepseek", journal_dir=str(tmp_path))
    legacy = {"agent": "deepseek", "date": j.today(), "turns": 128,
              "prompt_tokens": 104_040_915, "completion_tokens": 321_757,
              "total_tokens": 104_362_672, "model": "deepseek-v4-pro",
              "cost_est": 57.927}
    with open(j._path, "w", encoding="utf-8") as f:
        json.dump(legacy, f)

    reloaded = TokenJournal("deepseek", journal_dir=str(tmp_path))
    assert reloaded.turns == 128, f"legacy turns lost: {reloaded.to_dict()}"
    assert reloaded.prompt_tokens == 104_040_915, "legacy prompt tokens lost"
    assert reloaded.total_cost_est() > 0, (
        "a legacy journal carrying a known model must still price -- upgrading the "
        "meter must not blank the day it inherits")


# --------------------------------------------------------------- P7 narrow agent default
def test_p7_the_agent_default_is_explicit_and_narrow(tmp_path):
    """deepseek's own unlabelled turns may resolve to its default model (that is
    stated metadata, not a guess). The SAME fallback must not reach kimi -- that
    is precisely the bug, one layer down."""
    ds = TokenJournal("deepseek", journal_dir=str(tmp_path / "d"))
    ds.add_turn(prompt=500_000, completion=250_000)      # unlabelled, deepseek's own
    assert ds.total_cost_est() > 0.5, (
        "deepseek's unlabelled turns must still price via its EXPLICIT agent default "
        "(this also keeps the pre-existing T078 W1 pin honest)")

    km = TokenJournal("kimi", journal_dir=str(tmp_path / "k"))
    km.add_turn(prompt=500_000, completion=250_000)      # unlabelled, NOT deepseek's
    assert km.to_dict().get("unpriced_tokens", 0) == 750_000, (
        f"FALLBACK TOO WIDE: kimi's unlabelled turns fell through to a priced default. "
        f"The agent default must be a per-agent statement of fact, never a catch-all -- "
        f"a catch-all is how the original defect was written. to_dict()={km.to_dict()}")
