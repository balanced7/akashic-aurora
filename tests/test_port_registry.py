"""T266 RED -- port scanning should be as easy as the wiring check, and it is not.

Daniil 2026-08-10: "How do we make scanning for ports in use and what they belong to as easy
as our wiring check?"

WHAT THE WIRING CHECK GETS RIGHT, and what this must copy: the universe is DERIVED from the
tree rather than hand-listed (its own comment records that a hand list drifted and produced a
week of false positives), a frozen baseline that FAILS OPEN, [NEW] marking so old debt does
not block a commit, failure text naming every way out, and stale-baseline detection so the
ratchet cannot rot.

THE ONE THING PORTS NEED THAT WIRING DOES NOT. check_wiring reconciles TWO planes: defined vs
reachable. Ports have THREE --

    DECLARED   the registry in config.py
    IN CODE    port literals in live source
    LISTENING  live sockets and container publishes

-- and the third plane carries a trap. A DECLARED port with nothing listening is AMBIGUOUS:
the service may be down, or the entry may be stale, and NOTHING IN THE SOCKET TABLE CAN TELL
THOSE APART. A checker that renders it "stale" asserts absence as fact, which is the law this
repo has broken at the guard-of-guards (T178), in _receipt_author (T262) and in the recall
funnel. So it must render UNKNOWN, and the pin below holds that specifically.

MEASURED GAP that opened this slice: 11434 (ollama), 8888 (searxng), 3000 (open-webui) and
5000/5001 (voice) are all LISTENING and all ABSENT from docs/PORTS.md, because the registry
documents what PYTHON binds and says nothing about what CONTAINERS bind. Worse, the doc lists
8080 under "legacy/inactive -- never live" while ai-knowledge-api was bound to 8080 until it
was removed this morning: a map that asserts DEAD about something RUNNING is worse than a map
with a hole, because it is trusted.

Run: py -m pytest tests/test_port_registry.py -q
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402

CHECKER = os.path.join(ROOT, "scripts", "checkers", "check_ports.py")


def run_checker(*args, timeout=180):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, CHECKER, *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ------------------------------------------------------------------ the registry is DATA

def test_p1_the_registry_is_data_not_prose():
    """A map maintained by hand is the map that drifts. Every other map here -- PHYSICS,
    DOORS, MAP, MODULE_INDEX, PRIOR_ART -- is generated from state by pre-commit; PORTS.md
    was the one hand-written one, and it is the one that went stale."""
    import config
    reg = getattr(config, "PORT_REGISTRY", None)
    assert isinstance(reg, dict) and reg, "config.PORT_REGISTRY must exist and be non-empty"
    for port, entry in reg.items():
        assert isinstance(port, int), f"registry keys are ports, got {port!r}"
        for field in ("world", "what", "bound_by"):
            assert entry.get(field), f"port {port} is missing '{field}' -- an entry that does " \
                                     f"not say WHO binds it does not stop the guessing"


def test_p2_the_container_plane_is_registered():
    """THE MEASURED GAP. These are listening right now and were absent from the map."""
    import config
    reg = config.PORT_REGISTRY
    for port, who in ((11434, "ollama"), (8888, "searxng"),
                      (3000, "open-webui"), (5000, "voice")):
        assert port in reg, f"{port} ({who}) is bound by a container and must be registered"
        assert reg[port].get("bound_by") == "container", \
            f"{port} must be marked container-bound -- the plane the old registry could not see"


def test_p3_the_canonical_app_ports_survive_verbatim():
    """This slice extends the schema's REACH. It must not redesign the bands."""
    import config
    reg = config.PORT_REGISTRY
    assert reg.get(config.PORT_UI, {}).get("world") == "prod"
    assert reg.get(config.REDIS_PORT, {}).get("world") == "prod"
    assert reg.get(config.PORT_DSH_WEB, {}).get("bound_by") == "external"
    # W156 (2026-08-14): the "sandbox" world was RENAMED "beta" when it gained a sibling
    # ("alpha"), because "sandbox" names a role and stops discriminating once there are two
    # of them. The PORTS are untouched -- 8790/16380 are the same ports on the same band --
    # so this pin's intent ("must not redesign the bands") still holds. The old CONSTANT
    # names survive as aliases so no caller broke; that is asserted below rather than
    # assumed, because an alias nobody checks is how a rename quietly becomes a fork.
    assert reg.get(config.PORT_UI_BETA, {}).get("world") == "beta"
    assert reg.get(config.REDIS_PORT_BETA, {}).get("world") == "beta"
    assert config.PORT_UI_SANDBOX == config.PORT_UI_BETA == 8790
    assert config.REDIS_PORT_SANDBOX == config.REDIS_PORT_BETA == 16380


# ------------------------------------------------------------------ the checker's contract

def test_p4_the_checker_exists_and_reports_a_map():
    rc, out = run_checker("--report")
    assert rc == 0, f"--report is a READ and must always exit 0: {out[:400]}"
    assert "11434" in out and "16379" in out, "the report must render the actual map"


def test_p5_a_declared_port_that_is_not_listening_renders_UNKNOWN_never_stale():
    """THE LOAD-BEARING PIN. Nothing in a socket table distinguishes 'service is down' from
    'registry entry is stale'. Rendering the second is asserting absence as fact -- the T178 /
    T262 class. 8790 (sandbox console) and 18765 (MCP http) are registered and almost never
    listening, so this case is live on every run."""
    rc, out = run_checker("--report")
    low = out.lower()
    assert "unknown" in low, \
        "a registered-but-silent port must render UNKNOWN -- 'down' and 'stale' are " \
        "indistinguishable from here and the map must say so"
    assert "stale" not in low.split("unknown")[0][-400:], \
        "and must not be called stale, which claims knowledge the checker does not have"


def test_p6_an_unregistered_listener_is_reported_not_silently_passed():
    rc, out = run_checker("--report")
    assert "unregistered" in out.lower() or "UNREGISTERED" in out, \
        "the report must have a section for listeners nobody declared -- that absence is " \
        "exactly what made 'which containers do we need?' unanswerable"


def test_p7_the_gate_ratchets_like_check_wiring():
    """Fail on NEW drift only, fail open on a missing baseline, and name the ways out."""
    rc, out = run_checker()
    assert "PASS" in out or "FAIL" in out, "the gate must render a verdict line"
    if "FAIL" in out:
        assert "baseline" in out.lower(), "a failure must name the baseline escape, like check_wiring"


def test_p8_no_docker_degrades_to_report_only(monkeypatch):
    """A checker that needs a daemon is a checker that gets disabled. With docker absent the
    container plane must render UNKNOWN and the gate must still run."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["AKASHIC_PORTS_NO_DOCKER"] = "1"
    r = subprocess.run([sys.executable, CHECKER, "--report"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=180)
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, f"must not error without docker: {out[:300]}"
    assert "unknown" in out.lower(), "the container plane must render UNKNOWN, never empty"
