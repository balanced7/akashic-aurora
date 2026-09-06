"""RED pins for per-turn Codex wake usage accounting.

The App Server's ``ThreadTokenUsage.total`` is cumulative across the resumed
thread.  Treating it as the cost of the current Discord wake inflated one live
Sunshine turn from 1,624,125 tokens across eight model steps to 633,667,134.
The adapter must derive a turn-local total from the ``last`` sample emitted for
each model step while retaining the thread cumulative value under its true name.
"""
from __future__ import annotations

from agent.harness.codex_app_server import summarize_turn_usage
from agent.harness.codex_bifrost_wake import _usage_accounting


def _tokens(*, input_tokens: int, cached: int, output: int) -> dict:
    return {
        "inputTokens": input_tokens,
        "cachedInputTokens": cached,
        "cacheWriteInputTokens": 0,
        "outputTokens": output,
        "reasoningOutputTokens": output // 2,
        "totalTokens": input_tokens + output,
    }


def test_thread_cumulative_usage_never_masquerades_as_one_wake_turn():
    first_last = _tokens(input_tokens=199_076, cached=0, output=692)
    second_last = _tokens(input_tokens=199_815, cached=198_912, output=367)
    samples = [
        {
            "last": first_last,
            "total": _tokens(input_tokens=630_000_000, cached=600_000_000,
                             output=2_000_000),
            "modelContextWindow": 258_400,
        },
        {
            "last": second_last,
            "total": _tokens(input_tokens=630_199_815, cached=600_198_912,
                             output=2_000_367),
            "modelContextWindow": 258_400,
        },
    ]

    usage = summarize_turn_usage(samples)
    assert usage["last"] == second_last
    assert usage["total"] == samples[-1]["total"], (
        "the raw protocol cumulative remains available for thread-lifetime telemetry"
    )
    assert usage["turnTotal"] == {
        key: first_last[key] + second_last[key] for key in first_last
    }
    assert usage["modelSteps"] == 2

    accounting = _usage_accounting(usage)
    assert accounting["accounting_basis"] == "summed_model_steps"
    assert accounting["turn_total"] == usage["turnTotal"]
    assert accounting["thread_cumulative_total"] == usage["total"]
    assert accounting["final_model_step"] == second_last
    assert accounting["model_steps"] == 2
    assert accounting["multi_step"] is True


def test_legacy_sample_falls_back_to_last_not_thread_lifetime_total():
    last = _tokens(input_tokens=126_163, cached=0, output=101)
    thread_total = _tokens(
        input_tokens=480_668_728,
        cached=467_127_936,
        output=1_738_108,
    )

    accounting = _usage_accounting({"last": last, "total": thread_total})

    assert accounting["accounting_basis"] == "final_model_step_fallback"
    assert accounting["turn_total"] == last
    assert accounting["thread_cumulative_total"] == thread_total
    assert accounting["turn_total"]["totalTokens"] == 126_264
    assert accounting["turn_total"]["totalTokens"] != 482_406_836
