"""T312 RED pins -- `ask` must resolve a VENDOR from the model, not assume DeepSeek.

Run: py tests/test_t312_ask_vendor_resolution.py   (or via pytest)

WHY. `ask` shipped DeepSeek-only: one module-level BASE_URL, one `_load_key()` that reads
DEEPSEEK_API_KEY / .secrets/deepseek.key, and one hardcoded `max_tokens` cap parameter. Kimi has
been a first-class citizen since 2026-07-18 -- its own transport (scripts/kimi_chat.py), its own
one-shot CLI (scripts/ask_kimi.py), its own runner seat, an API key and a reconciled spend meter
-- and none of it is reachable through the door. `--model` overrides the model NAME while the
endpoint and credential stay DeepSeek's, so `ask --model kimi-k3` sends a Moonshot model id to
api.deepseek.com.

The cost of that is not convenience. Every `--fan` is N branches against ONE model family, which
lesson `fan_agreement_is_correlated_sampling_not_n_version` names precisely: same model, same
prompt, same evidence is one measurement taken N times. Cross-vendor fan is the point.

TWO CONSTRAINTS THE CODE ITSELF IMPOSES, both encoded as pins here:

  1. `max_completion_tokens`, NOT `max_tokens`. kimi_chat delta 3, probe-verified: thinking bills
     INSIDE completion, and a skimpy cap returns EMPTY content with stop_reason=max_tokens rather
     than an error. A naive vendor swap fails silently, which is the worst failure available.

  2. core must not reach into scripts/ for a credential. `_load_key`'s own docstring says so
     ("Resolved HERE so core does not have to reach into scripts for a credential"). So the kimi
     conventions are MIRRORED in core, never imported from scripts/kimi_chat.py. Pin 5 enforces it.

The DeepSeek path must not move a millimetre -- that is the real risk of this slice, and pins 2
and 3 are the ones that must STAY green rather than go green.
"""
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _vendor_for(model):
    try:
        from core.comm.ask import _vendor_for as f
    except ImportError as e:
        raise AssertionError(
            f"core.comm.ask._vendor_for does not exist yet -- T312 is unbuilt ({e})")
    return f(model)


def test_kimi_model_resolves_the_moonshot_vendor():
    v = _vendor_for("kimi-k3")
    assert "moonshot" in (v.get("base_url") or ""), \
        f"kimi-k3 must resolve the Moonshot endpoint, got {v.get('base_url')!r}"
    assert v.get("key_env") == "KIMI_API_KEY", \
        f"kimi must use its own credential env, got {v.get('key_env')!r}"
    assert "kimi" in (v.get("key_file") or ""), \
        f"kimi must use its own key file, got {v.get('key_file')!r}"


def test_kimi_uses_max_completion_tokens_not_max_tokens():
    """kimi_chat delta 3. Getting this wrong returns EMPTY content, not an error."""
    v = _vendor_for("kimi-k3")
    assert v.get("cap_param") == "max_completion_tokens", (
        f"kimi caps completion with max_completion_tokens, got {v.get('cap_param')!r}. "
        "Sending max_tokens to this vendor fails SILENTLY with empty content.")


def test_deepseek_path_is_unchanged():
    """MUST STAY GREEN. The existing door is the thing at risk here, not the new one."""
    from core.comm.ask import BASE_URL
    for model in ("deepseek-v4-pro", "deepseek-v4-flash"):
        v = _vendor_for(model)
        assert v.get("base_url") == BASE_URL, \
            f"{model} must keep the module BASE_URL, got {v.get('base_url')!r}"
        assert v.get("cap_param") == "max_tokens", \
            f"{model} must keep max_tokens, got {v.get('cap_param')!r}"
        assert v.get("key_env") == "DEEPSEEK_API_KEY"


def test_unknown_and_default_models_fall_back_to_deepseek():
    """MUST STAY GREEN. An unrecognised model must not become a silent no-vendor."""
    from core.comm.ask import BASE_URL, DEFAULT_MODEL
    for model in (DEFAULT_MODEL, "some-model-we-have-never-heard-of", "", None):
        v = _vendor_for(model)
        assert v.get("base_url") == BASE_URL, \
            f"{model!r} must fall back to the DeepSeek default, got {v.get('base_url')!r}"


def test_kimi_cap_floor_is_applied():
    """Thinking bills inside completion; a caller passing a small cap would get EMPTY content.
    The floor must be a property of the vendor, so the door cannot be misused into silence."""
    v = _vendor_for("kimi-k3")
    floor = v.get("min_cap") or 0
    assert floor >= 4000, (
        f"kimi needs a generous completion floor, got {floor}. kimi_chat sets 8000 and its "
        "probe receipts show a skimpy cap returns empty content.")
    assert (_vendor_for("deepseek-v4-pro").get("min_cap") or 0) == 0, \
        "the DeepSeek path must not acquire a floor it never had"


def test_kimi_carries_a_longer_read_timeout():
    """Found by USE, not by reading. The 6-second toy prompt that proved routing works was too
    easy to expose this; the first real analytical brief timed out. Thinking is always on at max
    effort on kimi, so runner_lib's 120s default is short -- kimi_chat sets 180 with the comment
    'thinking turns run long', and that is the value taken here rather than an invented one."""
    v = _vendor_for("kimi-k3")
    rt = float(v.get("read_timeout") or 0)
    assert rt >= 180, (
        f"kimi needs a read timeout of at least 180s, got {rt}. runner_lib defaults to 120, "
        "which times out a normal analytical turn on this vendor.")
    assert not _vendor_for("deepseek-v4-pro").get("read_timeout"), \
        "the DeepSeek path must keep runner_lib's default, not acquire kimi's"


def test_core_does_not_import_scripts_for_credentials():
    """The boundary _load_key's docstring states. Mirrored conventions, never a scripts import."""
    import inspect
    from core.comm import ask as ask_mod
    src = inspect.getsource(ask_mod)
    for bad in ("scripts.kimi_chat", "from kimi_chat", "import kimi_chat"):
        assert bad not in src, (
            f"core/comm/ask.py must not import {bad} -- core does not reach into scripts for a "
            "credential (see _load_key's docstring); mirror the convention instead")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"  FAIL  {name}\n        {e}")
    print(f"\n{failures} failing pin(s) -- RED is expected before T312 is built.")
    sys.exit(1 if failures else 0)
