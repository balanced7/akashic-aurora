"""T416 pins -- a retired world must fail FAST and must not be lied about.

MEASURED 2026-09-27, minutes after alpha (16381) and beta (16380) were stopped. The consolidation
itself was clean; it exposed two defects that had been free while those ports answered:

  1. A 48-SECOND STALL. agent_cli._boot_world_line() built a raw
     `redis.Redis(host=..., port=..., socket_timeout=2)` with NO socket_connect_timeout and handed
     it to core.world_seed.read_manifest, bypassing this repo's own
     core.foundation.redis_connection.probe_redis_reachable. `socket_timeout=2` does not bound a
     CONNECT: on this Windows host the OS retransmits SYN across ::1 then 127.0.0.1 and stalls
     ~48.98s before raising -- which redis_connection.py:8-12 documents in advance. The repo's own
     probe answers the same question in 1.03s.

     The suite CONCEALED it. tests/test_w156_world_resolution.py was green at exit 0 while paying
     97.40s + 97.18s + 48.58s in three tests, against 0.01s for the prod case. 243 of its 246
     seconds were this stall, reported as a pass.

  2. AN ABSENCE THAT BECAME A VERDICT. read_manifest caught every exception and returned None, so
     None meant both "I read the store, no manifest" and "I could not reach the store". The
     caller's honest branch -- "origin unknown -- the seed manifest could not be read" -- was
     therefore UNREACHABLE, and the boot line fell through to asserting the positive instead:
     "origin unrecorded -- no seed manifest, so this memory is either native or was copied in by
     hand". Unverified provenance stated as fact, after 48 seconds of not reaching the store.

After: 1.03s, and the line says the manifest could not be read.

These are the same defect class one layer apart -- a guard opted out of, and an error swallowed --
and both were invisible until two of three worlds went away.
"""

import os
import sys
import tempfile
import time

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEAD_PORT = 16381  # alpha, retired 2026-09-27
BUDGET_S = 15.0  # generous: the fix measures 1.03s, the defect measured 48.98s


def test_read_manifest_raises_on_an_unreachable_store():
    """UNREACHABLE IS NOT ABSENT. If this returns None again, every caller loses the ability to
    tell 'no manifest' from 'no store', and the honest branch upstream goes dead silently.

    Uses a client that RAISES rather than a real dead port, and that is not laziness: the first
    version of this pin dialled retired 16381 and took 48.09 SECONDS -- it paid the exact stall it
    exists to prove fixed, in a file whose next docstring warns against doing that. The contract
    under test is "does read_manifest let an exception from client.get() escape", and a raising
    double states that contract exactly. The real-network path is still covered end to end by
    test_a_dead_world_boot_line_is_fast, which measures 1.03s.
    """
    import redis

    from core.world_seed import read_manifest

    class Unreachable:
        def get(self, _key):
            raise redis.exceptions.ConnectionError("Error 10061 connecting to localhost:16381")

    try:
        read_manifest(Unreachable())
    except redis.exceptions.ConnectionError:
        return  # raising IS the contract
    raise AssertionError(
        "read_manifest swallowed a ConnectionError instead of letting it escape -- "
        "'no manifest' and 'no store' are indistinguishable again"
    )


def test_read_manifest_returns_none_for_a_reachable_store_with_no_manifest():
    """The other half, and the reason this is not just 'raise on everything': a store that WAS
    read and holds nothing must still answer None. A fake client proves the branch without needing
    a second live world -- the only thing being pinned here is the distinction itself."""
    from core.world_seed import read_manifest

    class Reachable:
        def get(self, _key):
            return None

    assert read_manifest(Reachable()) is None


def test_read_manifest_tolerates_an_unparseable_manifest():
    """Present but corrupt is a third case and must not raise -- the caller should see 'no
    manifest', not 'no store'."""
    from core.world_seed import read_manifest

    class Garbage:
        def get(self, _key):
            return b"{not json"

    assert read_manifest(Garbage()) is None


def test_a_dead_world_boot_line_is_fast():
    """THE 48-SECOND PIN. Bounded generously, because the point is the ORDER OF MAGNITUDE: the
    defect was 48.98s and the fix is 1.03s, so a 15s budget cannot flake on a slow host and cannot
    pass if the preflight is removed."""
    import agent_cli
    from core import world as world_mod

    prev = os.environ.get("AKASHIC_WORLD")
    os.environ["AKASHIC_WORLD"] = "alpha"
    world_mod._cached = None
    try:
        started = time.perf_counter()
        line = agent_cli._boot_world_line()
        elapsed = time.perf_counter() - started
    finally:
        if prev is None:
            os.environ.pop("AKASHIC_WORLD", None)
        else:
            os.environ["AKASHIC_WORLD"] = prev
        world_mod._cached = None

    assert line, "the twin world rendered no line at all"
    assert elapsed < BUDGET_S, (
        f"a dead-world boot line took {elapsed:.1f}s (budget {BUDGET_S}s). The raw redis client "
        f"has stopped paying the fail-fast probe -- socket_timeout does NOT bound a connect."
    )


def test_a_dead_world_boot_line_never_asserts_provenance_it_could_not_verify():
    """The honesty half. When the store is unreachable the line must say so, and must NOT claim
    the memory is 'either native or was copied in by hand' -- that is a statement about lineage
    made without reading the manifest."""
    import agent_cli
    from core import world as world_mod

    prev = os.environ.get("AKASHIC_WORLD")
    os.environ["AKASHIC_WORLD"] = "alpha"
    world_mod._cached = None
    try:
        line = agent_cli._boot_world_line()
    finally:
        if prev is None:
            os.environ.pop("AKASHIC_WORLD", None)
        else:
            os.environ["AKASHIC_WORLD"] = prev
        world_mod._cached = None

    assert "could not be read" in line, f"an unreachable store did not produce the honest line: {line!r}"
    assert "either native or" not in line, f"the line asserts provenance it never verified: {line!r}"


def test_the_repo_probe_is_faster_than_a_raw_connect_and_that_is_why_it_exists():
    """The measurement the fix rests on, kept live so the rationale does not rot into folklore.
    Only the PROBE is asserted -- a raw connect is deliberately not timed here, because doing so
    would make this test pay the 48s stall it exists to document."""
    from core.foundation.redis_connection import probe_redis_reachable

    started = time.perf_counter()
    reachable = probe_redis_reachable("localhost", DEAD_PORT)
    elapsed = time.perf_counter() - started
    assert reachable is False, f"port {DEAD_PORT} answered; this pin assumes it stays retired"
    assert elapsed < 5.0, f"the fail-fast probe took {elapsed:.1f}s; it is no longer fail-fast"


def test_both_raw_client_sites_now_preflight():
    """Structural, because the defect was a call site opting OUT of a primitive the repo already
    owned. Two sites built that raw client; both must preflight, and a third would be caught here
    only if it is added to this list -- so the list is named in the failure message."""
    import re
    from pathlib import Path

    for rel in ("agent_cli.py", "scripts/world_fidelity.py"):
        src = Path(ROOT, rel).read_text(encoding="utf-8")
        for match in re.finditer(r"read_manifest\(", src):
            window = src[max(0, match.start() - 1200) : match.start()]
            if "def read_manifest" in window:
                continue
            assert "probe_redis_reachable" in window, (
                f"{rel} calls read_manifest without a reachability preflight -- that site will "
                f"pay a ~49s SYN stall against a retired world"
            )
