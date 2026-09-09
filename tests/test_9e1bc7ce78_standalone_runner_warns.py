"""9e1bc7ce78 -- a standalone (daemon-less) runner must say so LOUDLY at startup.

Defer [9e1bc7ce78] (claude, 2026-08-26): Heimdall's Discord went silent while every
liveness signal stayed green. The finder's literal claim -- "a standalone runner takes
the bifrost:daemon:<agent> lock" -- is wrong at the code layer: runners hold
bifrost:runner:<agent> only, and the refusal he quoted ("M1-P11 coexistence -- no steal")
is the daemon's FLAGLESS alpha path, which takes runner_lock DIRECTLY and therefore
refuses under a bare runner. With --spawn-runner the daemon holds ITS OWN lock and goes
W102-idle under a bare runner instead. So the incident = bare runners + a daemon relaunched
without the mode flag, and the two residues still live at HEAD are:

  (1) a bare runner starts SILENT: nothing tells the operator the seat is running without
      its daemon's services (discord outbound pump election, runner supervision/respawn +
      circuit breaker, presence-card runner-down visibility) -- an absence that reads as
      normal, the 2026-08-26 class;
  (2) three hints still advertise the flagless launch that refuses: doctor's services
      drill, the daemon's own usage text, and the stop-hook nag (whose promised service,
      consume_rearms, runs ONLY under --manage-listener).

Pins:
  P1  daemon_state.standalone_warning(agent, c=fake, ns=...) -> LOUD text naming discord and
      the flagged relaunch when <ns>:daemon:<agent> is absent; None when the key exists;
      a kimi hint carries --runner-script (the daemon's default is the deepseek script --
      RECOVERY.md landmine daemon_spawn_runner_hardcodes_deepseek_script).
  P2  wiring: both bare-launchable runners call it, AFTER runner_lock acquisition (a
      refused runner must not warn about being standalone). Source-level, per the house
      lesson that a pin supplying its own input tests the mechanism, not the wiring.
  P3  doctor's daemon service finding carries the mode flags in its drill.
  P4  the daemon's usage text advertises no flagless launch for a real seat (the t075drill
      hatch is a deliberate alpha drill and stays).
  P5  the stop-hook nag names --manage-listener, the only mode that consumes rearms.

Run: py -m pytest tests/test_9e1bc7ce78_standalone_runner_warns.py -q -p no:cacheprovider
(no live Redis needed; doctor's probes are fail-open and known_agents is patched out)
"""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import daemon_state as ds  # noqa: E402


class FakeRedis:
    def __init__(self):
        self.kv = {}

    def set(self, k, v, ex=None, nx=False):
        if nx and k in self.kv:
            return None
        self.kv[k] = v
        return True

    def get(self, k):
        return self.kv.get(k)

    def delete(self, k):
        self.kv.pop(k, None)

    def exists(self, k):
        return 1 if k in self.kv else 0


def _src(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------- P1
def test_p1_absent_daemon_key_yields_loud_text_naming_pump_and_flagged_relaunch():
    fn = getattr(ds, "standalone_warning", None)
    assert callable(fn), "P1: daemon_state.standalone_warning does not exist yet"
    text = fn("deepseek", c=FakeRedis(), ns="bifrost")
    assert text, "P1: no <ns>:daemon:<agent> key -> the runner must be told it is standalone"
    assert "discord" in text.lower(), "P1: the warning must NAME the outbound pump it is not hosting"
    assert "--agent deepseek --spawn-runner" in text, \
        "P1: the relaunch hint must carry the mode flag (flagless = alpha = refuses under this runner)"


def test_p1_present_daemon_key_yields_none():
    fn = getattr(ds, "standalone_warning", None)
    assert callable(fn), "P1: daemon_state.standalone_warning does not exist yet"
    c = FakeRedis()
    c.set("bifrost:daemon:deepseek", "{}")
    assert fn("deepseek", c=c, ns="bifrost") is None, \
        "P1: a live daemon means the runner is a managed child (or coexisting) -- no warning"


def test_p1_kimi_hint_names_its_own_runner_script():
    fn = getattr(ds, "standalone_warning", None)
    assert callable(fn), "P1: daemon_state.standalone_warning does not exist yet"
    text = fn("kimi", c=FakeRedis(), ns="bifrost", runner_script="bifrost_runner_kimi.py")
    assert text and "--runner-script bifrost_runner_kimi.py" in text, \
        "P1: a kimi relaunch without --runner-script spawns the DEEPSEEK runner (daemon default)"


# --------------------------------------------------------------- P2
@pytest.mark.parametrize("runner", ["scripts/bifrost_runner_deepseek.py",
                                    "scripts/bifrost_runner_kimi.py"])
def test_p2_bare_launchable_runners_call_the_warning_after_lock_acquisition(runner):
    src = _src(runner)
    assert "standalone_warning" in src, f"P2: {runner} never asks whether its daemon is live"
    assert src.index("standalone_warning") > src.index("acquire_waiting("), \
        f"P2: {runner} must warn AFTER holding runner_lock -- a refused runner is not standalone"


# --------------------------------------------------------------- P3
def test_p3_doctor_daemon_drill_carries_the_mode_flags(monkeypatch):
    from core.comm import doctor
    monkeypatch.setattr(doctor, "known_agents", lambda: [])       # no live daemon -> DOWN
    daemon = [f for f in doctor.examine_services() if f.get("agent") == "daemon"]
    assert daemon, "P3: examine_services must still report the daemon service"
    f = daemon[0]
    assert f["state"] == "service_down"
    assert "--spawn-runner" in f["drill"], \
        "P3: a doctor-following operator lands in the alpha refusal without the mode flag"
    assert "--manage-listener" in f["drill"], \
        "P3: claude's daemon is a listener-manager (revive DAEMON_MODE); say so in the drill"


# --------------------------------------------------------------- P4
def test_p4_daemon_usage_advertises_no_flagless_launch_for_a_real_seat():
    src = _src("scripts/bifrost_daemon.py")
    doc = src.split('"""', 2)[1]
    usage = re.findall(r"py scripts/bifrost_daemon\.py --agent (\S+)([^\n#]*)", doc)
    assert usage, "P4: the module docstring lost its usage lines"
    real = [(a, rest) for a, rest in usage if not a.endswith("drill")]
    assert real, "P4: the usage must show at least one real seat"
    for agent, rest in real:
        assert "--spawn-runner" in rest or "--manage-listener" in rest, \
            f"P4: usage advertises a flagless (alpha) launch for {agent}: it refuses under a bare runner"


# --------------------------------------------------------------- P5
def test_p5_stop_hook_nag_names_the_listener_manager_mode(tmp_path):
    v = ds.stop_hook_wake_verdict("claude", "aaaabbbb-1111-2222-3333-444455556666",
                                  c=FakeRedis(), ns="bifrost", tmp=str(tmp_path))
    assert v["pass"] is False and v.get("nag")
    assert "--manage-listener" in v["line"], \
        "P5: the nag prescribes a mode that cannot consume rearms (manage_listener only)"
