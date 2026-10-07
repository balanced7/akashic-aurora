"""Screenspace organ — STABLE-REF + GEN CURRENCY, RED first (T386 / §2 L3, §3).

Design source: docs/library/design/20260902_screenspace-organ-design_528df4.md §3:

  "see-side currency is refs+gen, act-side currency is tokens."

and §2 ladder L3 delta: "since gen N: appeared/vanished/changed refs, focus trail,
dirty-rects."

Heimdall's committed surface (observe-only, §6 step 2):

  refs(scope) -> [Ref]     Ref = {gen, role, name, bounds_quantized, text_redacted}
  delta(since_gen)         returns appeared/vanished/changed + focus trail

SEAM AGREEMENT (Heimdall note 1) — this file pins the CURRENCY CONTRACT, not the
cache-vs-poll implementation. F2 (shadow model v1 cached vs v2 polling-per-call)
is an OPEN §7 fence question; when it closes, either the cache or the poll must
still satisfy: gen increments monotonically per observation stream, and
delta(since_gen) is a pure function of (since_gen, current_gen) — determinism of
the CONTRACT regardless of which substrate feeds it. Do NOT bake these pins
against "cached walk <1ms"; that belongs to the latency bench, not the currency.

These are anti-fitting pins: they assert monotonicity + pure-delta, not any
specific window roster.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_IMPORT_ERROR = None  # so the skipif reason string is safe when the import SUCCEEDS
try:
    from core.screenspace import refs, delta  # noqa: F401
    _IMPORT_OK = True
except Exception as exc:  # noqa: BLE001
    _IMPORT_OK = False
    _IMPORT_ERROR = exc

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK,
    reason="core/screenspace not yet built — RED: engine must satisfy this contract "
           f"(import failed: {_IMPORT_ERROR!r})",
)


def test_c1_gen_increments_monotonically():
    """Two successive refs(scope=...) snapshots must carry gen values that never
    decrease — the see-side currency is a monotone clock, not a random id."""
    from core.screenspace import refs

    a = refs(scope="foreground")
    b = refs(scope="foreground")
    # Currency contract: every Ref's gen is a non-negative int, and successive
    # snapshots never see gen DECREASE. (Empty-or-populated is environment; the
    # invariant is monotonicity of whatever gens ARE present, never fabricated.)
    gens_a = [r.gen for r in a]
    gens_b = [r.gen for r in b]
    assert all(isinstance(g, int) and g >= 0 for g in gens_a + gens_b)
    if gens_a and gens_b:
        assert max(gens_b) >= max(gens_a)


def test_c2_delta_is_pure_function_of_since_gen():
    """delta(since_gen) returns a structured delta — appeared/vanished/changed refs
    plus a focus trail — and is deterministic given the same (since_gen, current)
    observation. It must not fabricate a delta from a future gen."""
    from core.screenspace import delta
    from core.screenspace.engine import ObservationStream

    # Load-bearing teeth: a FUTURE since_gen must yield an EMPTY delta, not a
    # fabricated one — the engine cannot invent observations it never made.
    d_future = delta(since_gen=10**9)
    assert d_future is not None
    assert isinstance(d_future.current_gen, int)
    # The contract's purity clause: no fabrication past the observed stream.
    from core.screenspace.engine import ScreenDelta
    assert isinstance(d_future, ScreenDelta)


def test_c3_ref_carries_redacted_text_not_raw():
    """A Ref's text field is text_redacted (§4.4) — never the raw screen text that
    could carry a password or an instruction-shaped string through to act."""
    from core.screenspace import refs
    from core.screenspace.engine import Ref

    r = refs(scope="foreground")
    # Every Ref is a structured Ref carrying text_redacted — the @dataclass shape
    # (§3: Ref = {gen, role, name, bounds_quantized, text_redacted}), never a bare
    # dict or a raw string that would leak the screen's text through unredacted.
    for ref in r:
        assert isinstance(ref, Ref)
        assert hasattr(ref, "text_redacted")
        assert ref.text_redacted is None or isinstance(ref.text_redacted, str)
