"""T263 RED -- the CLI send door does not spill, so a long DIRECTED message loses its body.

MEASURED BEFORE THIS FILE, with a controlled test on the live bus (2026-08-09):

    claude -> claude   (what T222's pin exercises)  bifrost-fetch RESOLVES, full body
    claude -> deepseek (what real work does)        "no blob or bus message", BOTH ends

deepseek hit it live: it could not read the callsign brief I sent, called bifrost_fetch,
got nothing, and answered a stale backlog item instead.

ROOT CAUSE, traced rather than guessed: `packet_spec.spill_tool_text` has exactly three
callers and all three are in `core/comm/toolbox.py`. The TOOL door spills an oversize body
to a content-addressed blob and hands back `blob:<sha>`, which resolves from anywhere. The
CLI door never spills, so the render clips and `bifrost_pull.clip_pointer` falls back to a
STREAM-ID pointer -- an address that only resolves from a stream the reader can already
read. The sender therefore cannot verify its own send, which is how this survived: the one
person positioned to notice is the one person the pointer never worked for.

WHY THE EXISTING PINS ALL PASS WHILE THIS IS BROKEN, which is the part worth keeping:
T113's pins cover `spill_tool_text` itself (the function is correct). T222's pin covers the
RESOLVER, on a SELF-ADDRESSED send -- the single address space where a stream id resolves.
Two green pin sets, one hole between them, and it is a door-parity gap on the MESSAGE plane
rather than the verb plane: the capability exists and one of two doors is wired to it.

Run: py -m pytest tests/test_cli_send_spills.py -q
"""
import os
import re
import sys
import subprocess

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed (child inherits via env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402

# Comfortably over the tool door's rendering bound, so the spill path must engage.
BIG = "THE-BODY " + ("x" * 40000) + " END-MARKER"


def run(*args, timeout=180):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def _send_big_to(peer, tmp_path):
    f = tmp_path / "big.txt"
    f.write_text(BIG, encoding="utf-8")
    rc, out, err = run("bifrost-send", "claude", "--to", peer, "--kind", "note",
                       "--text-file", str(f))
    assert rc == 0, f"send failed: {err or out}"
    return out + err


def test_p1_a_long_body_sent_to_a_PEER_is_fetchable_by_the_sender(tmp_path):
    """THE HEADLINE PIN, and the exact case measured broken.

    The sender must be able to retrieve what it just sent to someone else. Today the render
    mints a stream id addressed to the RECIPIENT's stream, so the sender -- the only party
    who can compare sent-vs-received -- is the one party who cannot read it back.
    """
    sent = _send_big_to("deepseek", tmp_path)

    # The ref must come from THE SEND ITSELF. An earlier draft of this pin looked in the
    # sender's own inbox and failed -- correctly: the message is on the RECIPIENT's stream,
    # which is the whole defect. The sender learning the address at send time is the fix,
    # not a convenience: it is the only moment the sender can still act on it.
    m = re.search(r"(blob:[0-9a-f]{6,})", sent)
    assert m, ("the send door must advertise a CONTENT-ADDRESSED ref for an oversize body, "
               "TO THE SENDER, at send time -- a stream id is an address only the recipient "
               f"can resolve. Door said: {sent[:300]!r}")
    ref = m.group(1)

    rc, got, err = run("bifrost-fetch", "--get", ref)
    assert rc == 0, f"the advertised ref must resolve for the SENDER: {err or got}"
    assert "END-MARKER" in got, \
        "the resolved body must be the WHOLE body -- a pointer to a prefix is still a loss"


def test_p2_the_pointer_minted_is_content_addressed_not_a_stream_id(tmp_path):
    """A stream id is an address in a space only one reader can reach. A blob sha is an
    address in a space everyone can reach. The distinction is the whole defect."""
    from core.comm import packet_spec
    text, meta = packet_spec.spill_tool_text(BIG)
    assert meta.get("spill_ref", "").startswith("blob:"), \
        "spill must produce a content-addressed ref (this half already worked -- T113)"
    assert "bifrost-fetch --get blob:" in text, \
        "and the confession must name the door that resolves it"


def test_p3_a_short_body_is_byte_identical_to_today(tmp_path):
    """The spill must engage ONLY above the bound. Every ordinary message is unchanged."""
    from core.comm import packet_spec
    small = "a short note that fits comfortably"
    text, meta = packet_spec.spill_tool_text(small)
    assert text == small and meta == {}, "under the bound, nothing may change"


def test_p4_the_cli_door_actually_calls_the_spill(tmp_path):
    """STRUCTURAL, and it is the pin that would have caught this class before it shipped.

    The defect was never in spill_tool_text -- that function is correct and pinned. It was
    that ONE OF TWO SEND DOORS never called it. So the pin asserts the WIRING, not the
    mechanism: the same lesson as `a_pin_that_supplies_its_own_input_tests_the_mechanism_not
    _the_wiring`, applied to a door instead of an argument.
    """
    import ast
    src = open(os.path.join(ROOT, "agent_cli.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "cmd_bifrost_send"), None)
    assert fn is not None, "cmd_bifrost_send must exist for this pin to mean anything"
    called = {n.func.attr for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "spill_tool_text" in called, \
        "the CLI send door must route an oversize body through the SAME spill the tool " \
        "door uses -- otherwise the capability exists and only one door has it"
