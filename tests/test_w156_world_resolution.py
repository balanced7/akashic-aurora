"""W156 pins: which Aurora you are standing in is DERIVED, not configured.

Daniil, 2026-08-14 (verbatim): "we will need separate redis, separate other things on
different ports so it is literally a second akashic aurora, then we will see some
interesting interactions between basically two institutions and collections of shared
memories."

THE DEFECT THIS CLOSES (measured 2026-08-14, before a line was written):

    A clone of Aurora is not a second Aurora. It is a second BODY wired to the SAME BRAIN.

    E:/AI-Setup-Alpha, freshly cloned at HEAD, resolved:
        repo_root  -> E:\\AI-Setup-Alpha     (correct -- core/paths.py earns this)
        REDIS_PORT -> 16379                  (PROD, 19,850 live keys)
        PORT_UI    -> 8787                   (PROD console)
    So every write from the "sandbox" lands in production's memory.

    The July 2026 sandbox "solved" this by editing `REDIS_PORT` on line 20 of config.py --
    a TRACKED file. That is why it sat frozen at a 2026-07-05 baseline for 40 days: its
    isolation mechanism IS a permanent merge conflict on the most-imported file in the repo.
    Refreshing it means re-fighting the edit that makes it a sandbox at all.

    THE LAW: an environment whose isolation lives in a tracked file cannot be refreshed
    without surrendering its isolation.

WHY THIS SHAPE. core/paths.py already solved this exact class one level down, and wrote the
doctrine at the top of the file: "CONFIGURATION YOU MUST REMEMBER IS NOT PORTABILITY. It is a
hardcoded path with an extra step." It derived the repo ROOT from where the code is standing.
It never generalised to the WORLD. This slice applies that module's own doctrine one level up.

THE DAWE TEST (the architecture bar Daniil adopted 2026-08-13, from the Clarke & Dawe Glenn
Stevens sketches -- "I'll respond, Brian; whether that constitutes an answer in your terms is
another matter"): a RESPONSE that is not an ANSWER is a defect. config.PORT_REGISTRY already
carries a `world` field on every port -- and NOTHING reads its value to make a runtime
decision (readers: config.py, check_ports.py, gen_ports.py, test_port_registry.py -- all of
which either define it, render it to docs, or validate its schema). It is documentation
wearing the costume of configuration. These pins make `world` answer.
"""
import os

import pytest

from core import world as W


# --------------------------------------------------------------------------
# S1 -- the world is DERIVED from where you stand, with nothing to remember
# --------------------------------------------------------------------------

def test_s1_prod_root_resolves_prod(tmp_path):
    w = W.resolve(root=tmp_path / "AI-Setup", env={})
    assert w.name == "prod"
    assert w.source == "derived"


def test_s1b_alpha_root_resolves_alpha(tmp_path):
    w = W.resolve(root=tmp_path / "AI-Setup-Alpha", env={})
    assert w.name == "alpha"
    assert w.source == "derived"


def test_s1c_beta_root_resolves_beta(tmp_path):
    w = W.resolve(root=tmp_path / "AI-Setup-Beta", env={})
    assert w.name == "beta"
    assert w.source == "derived"


def test_s1d_suffix_match_is_case_insensitive_and_ignores_separator(tmp_path):
    """A human clones to -alpha, -ALPHA or _Alpha. The world is the same world;
    a case-sensitive match here would silently hand them UNKNOWN (or worse, prod)."""
    for leaf in ("AI-Setup-alpha", "AI-Setup-ALPHA", "AI-Setup_Alpha"):
        assert W.resolve(root=tmp_path / leaf, env={}).name == "alpha", leaf


# --------------------------------------------------------------------------
# S2 -- THE CRITICAL PIN: an unrecognised root must NEVER become prod
# --------------------------------------------------------------------------

def test_s2_unknown_root_is_unknown_not_prod(tmp_path):
    """The whole point. A stray clone that silently answers "prod" is how a
    sandbox eats production. UNKNOWN is a real state, not a fallback to the
    most dangerous world in the house."""
    w = W.resolve(root=tmp_path / "some-random-checkout", env={})
    assert w.name == "unknown"
    assert w.name != "prod"


def test_s2b_unknown_permits_reads_and_refuses_writes(tmp_path):
    """Honest middle: a fresh clone on a new machine must still be able to boot,
    read and orient -- refusing everything is maddening and gets disabled. Writes
    are where the damage lives, so writes are what UNKNOWN refuses.

    There is no `may_read` to assert. It existed, and check_wiring flagged it as a
    public function nothing calls; it returned a constant True, which made this pair
    look symmetrically enforced when only the write half ever was. Reading is not a
    permission here -- it is the absence of a refusal, and the pin says so by
    resolving without raising."""
    w = W.resolve(root=tmp_path / "mystery", env={})
    assert w.may_write is False
    assert not hasattr(w, "may_read"), "decoration came back; it is not an enforced half"


def test_s2c_the_refusal_teaches_the_one_command_that_fixes_it(tmp_path):
    """Dawe Test on our own error path: a refusal that states the problem without
    stating the remedy is a response, not an answer."""
    w = W.resolve(root=tmp_path / "mystery", env={})
    with pytest.raises(W.WorldRefusal) as e:
        w.assert_may_write()
    msg = str(e.value)
    assert ".aurora-world" in msg          # names the marker
    assert "alpha" in msg and "prod" in msg  # names the legal values


# --------------------------------------------------------------------------
# S3 -- the marker file wins, and it is UNTRACKED so refresh cannot break it
# --------------------------------------------------------------------------

def test_s3_marker_file_beats_the_directory_heuristic(tmp_path):
    """The portable declaration. A checkout named anything at all can say what it
    is -- which is what makes this work on a second machine, per the core/paths.py
    lesson that an absolute-path heuristic is a machine-specific assumption."""
    root = tmp_path / "wherever"
    root.mkdir()
    (root / ".aurora-world").write_text("beta\n", encoding="utf-8")
    w = W.resolve(root=root, env={})
    assert w.name == "beta"
    assert w.source == "marker"


def test_s3b_marker_is_gitignored_so_isolation_never_rides_a_merge(tmp_path):
    """THE ANTI-ROT PIN, and the reason this slice exists at all. The July sandbox
    put its isolation in tracked config.py and could never be refreshed. The marker
    must be ignored by git, or we have rebuilt the same trap with a new filename."""
    from core.paths import repo_root
    gitignore = (repo_root() / ".gitignore").read_text(encoding="utf-8", errors="replace")
    assert ".aurora-world" in gitignore


def test_s3c_a_malformed_marker_is_unknown_never_a_guess(tmp_path):
    root = tmp_path / "wherever"
    root.mkdir()
    (root / ".aurora-world").write_text("prodd\n", encoding="utf-8")
    w = W.resolve(root=root, env={})
    assert w.name == "unknown"
    assert "prodd" in w.why      # says what it found, not just that it failed


# --------------------------------------------------------------------------
# S4 -- env override exists, and is never REQUIRED (the core/paths.py doctrine)
# --------------------------------------------------------------------------

def test_s4_env_override_wins_over_everything(tmp_path):
    root = tmp_path / "AI-Setup-Alpha"
    root.mkdir()
    (root / ".aurora-world").write_text("beta\n", encoding="utf-8")
    w = W.resolve(root=root, env={"AKASHIC_WORLD": "prod"})
    assert w.name == "prod"
    assert w.source == "override"


def test_s4b_a_bogus_override_refuses_rather_than_falling_through(tmp_path):
    """An explicit wrong answer is a different failure from no answer. Falling
    through to the heuristic would silently ignore what the operator typed."""
    w = W.resolve(root=tmp_path / "AI-Setup-Alpha", env={"AKASHIC_WORLD": "staging"})
    assert w.name == "unknown"
    assert "staging" in w.why


# --------------------------------------------------------------------------
# S5 -- each world resolves DISTINCT endpoints (the isolation, as data)
# --------------------------------------------------------------------------

def test_s5_every_world_has_a_distinct_redis_port():
    ports = {n: W.WORLDS[n].redis_port for n in ("prod", "beta", "alpha")}
    assert len(set(ports.values())) == 3, ports
    assert ports["prod"] == 16379      # the live master, unchanged forever


def test_s5b_every_world_has_a_distinct_ui_port():
    ui = {n: W.WORLDS[n].ui_port for n in ("prod", "beta", "alpha")}
    assert len(set(ui.values())) == 3, ui
    assert ui["prod"] == 8787          # the canonical console, per the 8787/8788 arc


def test_s5c_ui_ports_stay_inside_their_declared_bands():
    """config.PORT_BANDS is the house law for what a port's digits mean. A world
    whose console escapes its band makes the digits lie."""
    import config
    for name in ("prod", "beta", "alpha"):
        port = W.WORLDS[name].ui_port
        band = next((w for lo, hi, w in config.PORT_BANDS if lo <= port <= hi), None)
        assert band is not None, f"{name} ui_port {port} is in no declared band"


def test_s5d_unknown_world_has_no_endpoint_at_all(tmp_path):
    """Not a placeholder port, not prod's port -- none. A world that cannot say
    where it lives must not hand out an address."""
    w = W.resolve(root=tmp_path / "mystery", env={})
    assert w.redis_port is None
    with pytest.raises(W.WorldRefusal):
        w.redis_endpoint()


# --------------------------------------------------------------------------
# S6 -- the cross-world guard (belt; the separate Redis INSTANCE is the firewall)
# --------------------------------------------------------------------------

def test_s6_guard_refuses_a_foreign_worlds_port(tmp_path):
    """deepseek's fence, 2026-08-14: this guard is belt-and-suspenders, NOT the
    primary defense -- the firewall is a physically separate Redis instance. The
    belt exists because the code's DEFAULT resolution is what actually failed:
    a clone dialled 16379 by constant, and no amount of physical separation helps
    when the door is dialled correctly to the wrong house."""
    alpha = W.resolve(root=tmp_path / "AI-Setup-Alpha", env={})
    with pytest.raises(W.WorldRefusal) as e:
        alpha.assert_owns_port(16379)
    assert "prod" in str(e.value) and "alpha" in str(e.value)


def test_s6b_guard_allows_its_own_port(tmp_path):
    alpha = W.resolve(root=tmp_path / "AI-Setup-Alpha", env={})
    alpha.assert_owns_port(16381)      # must not raise


def test_s6c_guard_names_the_port_owner_not_just_no(tmp_path):
    """Dawe Test again: 'refused' is a response. 'refused because 16379 belongs to
    prod and you are alpha' is an answer."""
    alpha = W.resolve(root=tmp_path / "AI-Setup-Alpha", env={})
    with pytest.raises(W.WorldRefusal) as e:
        alpha.assert_owns_port(16380)
    assert "beta" in str(e.value)


# --------------------------------------------------------------------------
# S7 -- byte-identical config.py, different world (the refresh property)
# --------------------------------------------------------------------------

def test_s7_isolation_survives_a_byte_identical_config(tmp_path):
    """THE PROPERTY THAT MAKES REFRESH FREE. The July sandbox could not have passed
    this: its world lived in config.py, so an identical config.py meant an identical
    world. Here the world is a function of the CHECKOUT, so prod and alpha can ship
    the same tracked bytes and still be different institutions."""
    a = tmp_path / "AI-Setup-Alpha"
    p = tmp_path / "AI-Setup"
    for r in (a, p):
        r.mkdir()
    # No marker, no env, no per-checkout edit of any tracked file.
    assert W.resolve(root=a, env={}).redis_port != W.resolve(root=p, env={}).redis_port


# --------------------------------------------------------------------------
# S9 -- the boot line: silent in prod, loud in a twin
# --------------------------------------------------------------------------

def _world_line(monkeypatch, world):
    import agent_cli
    from core import world as _w
    monkeypatch.setenv("AKASHIC_WORLD", world)
    monkeypatch.setattr(_w, "_cached", None, raising=False)
    return agent_cli._boot_world_line()


def test_s9_silent_in_prod(monkeypatch):
    """The no-regression pin, and the reason this organ costs the T022 head-16 contract
    nothing: prod is what every seat already assumes, so saying it is pure noise in the
    one place the header is most contested."""
    assert _world_line(monkeypatch, "prod") == ""


def test_s9b_loud_in_a_twin(monkeypatch):
    for name, port in (("alpha", "16381"), ("beta", "16380")):
        line = _world_line(monkeypatch, name)
        assert line.startswith("# WORLD:")
        assert name.upper() in line and "NOT prod" in line
        assert port in line


def test_s9c_the_twin_line_warns_that_memory_was_INHERITED(monkeypatch):
    """The fact that makes a twin dangerous to read: it was SEEDED from prod, so its boot
    renders prod's directive, prod's ledger and prod's lessons. Every orientation line is
    inherited and therefore indistinguishable from the real thing unless this says so."""
    line = _world_line(monkeypatch, "alpha")
    assert "SEEDED" in line and "diverged" in line


def test_s9d_unknown_says_writes_are_refused_and_how_to_fix_it(monkeypatch):
    line = _world_line(monkeypatch, "not-a-world")
    assert "UNKNOWN" in line and "REFUSED" in line and ".aurora-world" in line


def test_s9e_the_line_is_exactly_one_line(monkeypatch):
    """W146/S7 family: a header organ that emits a newline fractures the head format."""
    for name in ("alpha", "beta", "not-a-world"):
        assert "\n" not in _world_line(monkeypatch, name)


def test_s8_resolution_reports_its_own_provenance(tmp_path):
    """Every resolution says HOW it decided. A world that cannot be asked why it
    thinks it is prod is exactly the Glenn Stevens this slice was named after."""
    for root, env, src in (
        (tmp_path / "AI-Setup-Alpha", {}, "derived"),
        (tmp_path / "AI-Setup-Alpha", {"AKASHIC_WORLD": "beta"}, "override"),
        (tmp_path / "nope", {}, "unresolved"),
    ):
        w = W.resolve(root=root, env=env)
        assert w.source == src
        assert w.why, "a resolution with no reason is a response, not an answer"
