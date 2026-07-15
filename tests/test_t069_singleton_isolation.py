"""T069 PRE-REGISTERED ACCEPTANCE -- isolation-honoring, namespace-keyed singletons.

Root cause (found by suite ordering, 2026-07-15): event_log/event_query honor
_AISETUP_TEST_ISOLATED (fresh instance per call, never cache); get_agent_memory,
get_learning_store_instance, get_bus, and perspectives.reinforce.get do NOT -- the
first door-touch pins a singleton bound to whatever env was live, poisoning every
later consumer that expected isolation. get_bus additionally bakes BIFROST_NAMESPACE
at construction (the stale-ns class; expectations Fix A read env per-call for exactly
this reason). Daniel-directed root-cause fix -- no order notes, no conventions.

Every pin saves/restores the module cache it touches: a pin must never itself become
the poison it tests for.

Run: py -m pytest tests/test_t069_singleton_isolation.py -q
"""
import os
import sys

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_p1_agent_memory_isolated_is_fresh_per_call(monkeypatch):
    from core.learning import agent_memory as am
    monkeypatch.setenv("_AISETUP_TEST_ISOLATED", "1")
    saved = am._agent_memory
    try:
        a, b = am.get_agent_memory(), am.get_agent_memory()
        assert a is not b, "isolated mode must never serve a cached AgentMemory"
        assert am._agent_memory is saved, "isolated calls must not write the cache"
    finally:
        am._agent_memory = saved


def test_p2_learning_store_isolated_is_fresh_per_call(monkeypatch):
    from core.learning import learning_store as ls
    monkeypatch.setenv("_AISETUP_TEST_ISOLATED", "1")
    saved = ls._learning_store
    try:
        a, b = ls.get_learning_store_instance(), ls.get_learning_store_instance()
        assert a is not b, "isolated mode must never serve a cached LearningStore"
        assert ls._learning_store is saved, "isolated calls must not write the cache"
    finally:
        ls._learning_store = saved


def test_p3_get_bus_cache_keys_on_namespace(monkeypatch):
    from core.comm import bus as busmod
    monkeypatch.delenv("_AISETUP_TEST_ISOLATED", raising=False)
    added = []
    try:
        monkeypatch.setenv("BIFROST_NAMESPACE", "t069_ns_a")
        a = busmod.get_bus("t069agent")
        monkeypatch.setenv("BIFROST_NAMESPACE", "t069_ns_b")
        b = busmod.get_bus("t069agent")
        added = [k for k in busmod._INSTANCES if "t069agent" in str(k)]
        assert a.ns == "t069_ns_a" and b.ns == "t069_ns_b", \
            f"a namespace flip must never serve a stale-ns bus (got {a.ns!r}, {b.ns!r})"
        assert a is not b, "different namespaces are different buses"
    finally:
        for k in added:
            busmod._INSTANCES.pop(k, None)


def test_p4_get_bus_isolated_never_caches(monkeypatch):
    from core.comm import bus as busmod
    monkeypatch.setenv("_AISETUP_TEST_ISOLATED", "1")
    before = dict(busmod._INSTANCES)
    a, b = busmod.get_bus("t069iso"), busmod.get_bus("t069iso")
    assert a is not b, "isolated mode must never serve a cached Bus"
    assert busmod._INSTANCES == before, "isolated calls must not write the bus cache"


def test_p5_door_touch_cannot_pin_stores_for_isolated_consumers(monkeypatch):
    """The original coupling, in-process: a door touch (orientation header reads notes,
    ledger, constraints) must not pin store instances that later isolated consumers
    receive. Under the flag, consumers get fresh instances AFTER any door activity."""
    monkeypatch.setenv("_AISETUP_TEST_ISOLATED", "1")
    import agent_cli
    from core.learning import agent_memory as am
    saved = am._agent_memory
    try:
        agent_cli._orientation_header("claude")          # the door touch
        x, y = am.get_agent_memory(), am.get_agent_memory()
        assert x is not y and am._agent_memory is saved, \
            "a door touch pinned a store instance for isolated consumers"
    finally:
        am._agent_memory = saved


def test_p6_reinforce_isolated_is_fresh(monkeypatch):
    from core.perspectives import reinforce
    monkeypatch.setenv("_AISETUP_TEST_ISOLATED", "1")
    saved = reinforce._INSTANCE
    try:
        a, b = reinforce.get_reinforced_graph(), reinforce.get_reinforced_graph()
        assert a is not b, "isolated mode must never serve a cached ReinforcedGraph"
        assert reinforce._INSTANCE is saved
    finally:
        reinforce._INSTANCE = saved


def test_p7_canonical_singletons_unchanged(monkeypatch):
    """Production path untouched: without the flag, the lazy singleton caches exactly
    as before. Cache saved/restored so this pin cannot itself become the poison."""
    from core.learning import agent_memory as am
    monkeypatch.delenv("_AISETUP_TEST_ISOLATED", raising=False)
    saved = am._agent_memory
    try:
        am._agent_memory = None
        a, b = am.get_agent_memory(), am.get_agent_memory()
        assert a is b, "canonical mode must keep the singleton contract"
    finally:
        am._agent_memory = saved


def test_p8_existing_isolated_factories_unchanged(monkeypatch):
    """Non-regression: the three factories that established the pattern still honor it."""
    monkeypatch.setenv("_AISETUP_TEST_ISOLATED", "1")
    from core.events.event_log import get_event_log
    from core.events.event_query import get_event_query
    assert get_event_log() is not get_event_log()
    assert get_event_query() is not get_event_query()


def test_p9_census_all_store_binding_factories_honor_isolation(monkeypatch):
    """The canary (deepseek belt-verdict Part e): every KNOWN store/redis-binding factory
    returns fresh instances under the flag. A new offender joins this list or trips the
    check_boundaries singleton rule -- the class cannot silently return."""
    monkeypatch.setenv("_AISETUP_TEST_ISOLATED", "1")
    from core.learning.agent_memory import get_agent_memory
    from core.learning.learning_store import get_learning_store_instance
    from core.comm.bus import get_bus
    from core.perspectives.reinforce import get_reinforced_graph
    from core.events.event_log import get_event_log
    from core.events.event_query import get_event_query
    factories = [get_agent_memory, get_learning_store_instance,
                 lambda: get_bus("t069census"), get_reinforced_graph,
                 get_event_log, get_event_query]
    for f in factories:
        assert f() is not f(), f"{f} served a cached instance under isolation"


if __name__ == "__main__":
    print("Run via pytest: py -m pytest tests/test_t069_singleton_isolation.py -q")
