"""PRE-REGISTERED ACCEPTANCE (T149) -- stdout must not claim a send that did not happen.

SEASON 0. Verified 2026-08-04 by sending an identical body twice and capturing both streams:

    stderr: [re-ask] identical request to t147probe already pending as 1785818090897-0
            (1800s window) -- collapsed, not re-sent.
    stdout: [bifrost-send] -> t147probe [request] (id 1785818090897-0)

Both lines are from the SAME call. The stderr line is correct, accurate, and names the remedy. The
stdout line is indistinguishable from a successful send -- same shape, same id, no hint that
anything was suppressed. The two streams contradict each other, and the one that lies is the
default channel that scripts, pipes and logs keep.

WHY THIS IS A SEASON-0 ITEM AND NOT A COSMETIC ONE. Season 1 wants twenty seats driven by
orchestration, and orchestration reads stdout. An operator loop that sends, sees the arrow line,
and moves on will believe every brief landed. I believed it three times in one night -- each of my
sends was piped through `| tail -1`, which is exactly what a script does.

THE COLLAPSE LOGIC IS NOT THE DEFECT AND IS NOT TOUCHED. It is well built: the P6 strand guard
refuses to collapse onto an original the recipient can no longer see, and deliberate system
re-delivery (redrive_of, rehomed_from, original_mid) is already exempt. The bus even publishes the
verdict -- `last_reask` is set on collapse and reset per send. Only the rendering ignores it.

I ALSO CORRECT MYSELF. W124 called this a "silent no-op". It is not silent; I was not reading
stderr. W127 is that correction. The lesson it lands on is
`a_warning_needs_a_channel_the_reader_actually_has`, in its nastiest form: the warning HAD a
channel, and a louder line on a better channel said the opposite.

  C1  a first send prints the normal arrow line
  C2  an identical second send prints COLLAPSED on STDOUT, not the arrow line
  C3  the collapsed line names the id it collapsed onto  (so the operator can nudge it)
  C4  stderr keeps its existing notice                    (no signal is removed, only added)

Run: py -m pytest tests/test_t149_send_stdout_tells_the_truth.py -q
"""
import os
import subprocess
import sys
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TO = f"t149probe{uuid.uuid4().hex[:6]}"


def _send(body_path):
    """Run the real CLI door and return (stdout, stderr) separately."""
    p = subprocess.run(
        [sys.executable, "agent_cli.py", "bifrost-send", "claude", "--to", TO,
         "--kind", "request", "--text-file", str(body_path)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120)
    return p.stdout or "", p.stderr or ""


@pytest.fixture(scope="module")
def sends(tmp_path_factory):
    from core.comm import bus as B
    if B.Bus("claude")._client is None:
        pytest.skip("redis unavailable")
    body = tmp_path_factory.mktemp("t149") / "b.txt"
    body.write_text("T149 probe: identical body, sent twice.\n", encoding="utf-8")
    first = _send(body)
    second = _send(body)
    return first, second


def test_c1_a_first_send_prints_the_arrow_line(sends):
    (out1, _e1), _second = sends
    assert "[bifrost-send] ->" in out1, f"a genuine send stopped announcing itself:\n{out1}"


def test_c2_an_identical_resend_says_collapsed_on_stdout(sends):
    _first, (out2, _e2) = sends
    assert "COLLAPSED" in out2.upper(), (
        "stdout still renders a collapsed re-ask as a successful send -- an orchestration loop "
        f"reading stdout believes the brief landed:\n{out2}")
    assert "[bifrost-send] ->" not in out2, (
        f"the arrow line must not appear when nothing was sent:\n{out2}")


def test_c3_the_collapsed_line_names_the_id_it_collapsed_onto(sends):
    (out1, _e1), (out2, _e2) = sends
    import re
    m = re.search(r"\(id (\S+?)\)", out1)
    assert m, f"could not read the original id from the first send:\n{out1}"
    assert m.group(1) in out2, (
        f"the collapsed line must name {m.group(1)} so the operator can nudge it:\n{out2}")


def test_c4_stderr_keeps_its_existing_notice(sends):
    """The fix ADDS honesty to stdout; it must not remove the stderr notice, which is the one
    that explains WHY and names the remedy."""
    _first, (_o2, err2) = sends
    assert "re-ask" in err2.lower(), f"the explanatory stderr notice was lost:\n{err2}"
