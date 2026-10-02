"""Pre-registered acceptance for the wire call-site seam (Gap 1's prerequisite).

WRITTEN BY THE REVIEWER, BEFORE THE BUILDER STARTED, AT HIS OWN REQUEST. Heimdall owns
`scripts/deepseek_chat.py` and is building this seam. He asked, in as many words:

    "you offered me the seam because I know the loop, and I'd rather pin the thing I most need
     you to hold me to, being the one building on home ground... those two -- reconcile on trace
     id, and one pass through the stream, never twice -- are the fence around the fence."

So these are his two constraints, written by someone who is not him, before the code exists. That
is the whole value: an acceptance a builder writes for himself after the fact grades his own work.

WHY THE SEAM EXISTS. Measured 2026-10-02: every body-derived field of the wire record is null on
100% of 4,416 records -- `model`, `system_fingerprint`, `finish_reason`, `service_tier`,
`response_id`, and the entire usage block. `wire_journal._shape` DECLARES all of them and no caller
ever fills one. It is a blank template, shipped. The transport cannot fill it: the runner is always
streaming, so those values exist only after the SDK assembles chunks, which is after the transport
has returned. The call site is the only lane that can, and it is already iterating those chunks --
`_absorb_usage` folds four fields off the final one and walks past the rest.

TWO PINS, AND THEY FAIL DIFFERENTLY ON PURPOSE.

  P1 is a RATCHET and is GREEN TODAY. The loop does not read the body twice now, and the point is
  that it must still be true after the change. A constraint that only gets checked once is a style
  note; this one is checked forever.

  P2 is RED and stays red until the seam lands. It is the reconciliation key: two stamps of one
  round trip that cannot be joined are not one record, they are two half-records, and that is worse
  than the blank template because it looks finished.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(REPO, "scripts", "deepseek_chat.py")
JOURNAL = os.path.join(REPO, "scripts", "wire_journal.py")


def _src(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _stream_turn_body():
    src = _src(RUNNER)
    m = re.search(r"\n    def _stream_turn\(self\):(.*?)\n    def ", src, re.S)
    assert m, "_stream_turn not found in scripts/deepseek_chat.py"
    return m.group(1)


# ---------------------------------------------------------------- P1, the ratchet (green today)
#: Ways to read an HTTP body a second time. The transport's no-bodies rule is MECHANISM, not
#: policy: touching `resp.stream` consumes the SSE stream the caller is about to iterate. Anything
#: here inside the loop means the seam bought its fields by breaking the thing that made the
#: transport safe.
#:
#: NARROWED AFTER ITS FIRST RUN, and the narrowing is the interesting part. The first version of
#: this list carried `.content`, `.text` and `.json()`, and it failed immediately -- on
#: `if d.content:`, which reads the model's own delta TEXT and has nothing to do with an HTTP body.
#: An SDK chunk and an HTTP response share attribute names, so a bare token match cannot tell a
#: body read from a perfectly ordinary field access. Only names that are unambiguously
#: response-body reads belong here; everything else measures the Python namespace rather than the
#: thing the rule is about.
_SECOND_READ = (
    "resp.stream", "response.stream", ".aread(", ".iter_bytes", ".iter_raw",
    ".iter_lines", "raw_response", "httpx",
)


def _code_only(text: str) -> str:
    """Strip `#` comments AND docstrings, so a pin reads CODE and never prose about the code.

    This function was wrong twice before it was right, in both directions, which is why it is
    worth the paragraph:

      FAKE RED -- the transport's own comment, 'touching resp.stream would consume the SSE stream
      the caller is about to iterate', tripped the pin that exists to enforce exactly what that
      comment describes.

      FAKE GREEN, and this is the dangerous one because it is silent -- the join-key pin passed
      against a runner that has no join key, because `x-ds-trace-id` appears once in that module,
      inside a docstring at line 72, explaining what the wire journal captures. The first fix
      stripped only `#` comments and the docstring sailed through.

    A filed lesson already names the fake-green half (do not put a grepped keyword in the
    docstring of the function under test). Both halves are one defect: a pin that reads prose
    measures prose. Ordinary single and double quoted strings are KEPT, because a header name
    genuinely appears as "x-ds-trace-id" in real code and that occurrence is the thing we want.
    """
    no_hash = "\n".join(ln.split("#", 1)[0] for ln in text.splitlines())
    return re.sub(r'("""|\'\'\')(?:.|\n)*?\1', "", no_hash)


def test_p1_the_turn_loop_never_reads_the_response_body_a_second_time():
    body = _code_only(_stream_turn_body())
    offenders = [t for t in _SECOND_READ if t in body]
    assert not offenders, (
        "the seam must read ONLY the chunk objects the single iteration already yields. "
        f"Found {offenders} in _stream_turn. Heimdall's own hard stop: 'if any change I propose "
        "would require reading the body twice, it is wrong'. The transport's refusal to touch the "
        "body is what keeps the stream intact; buying wire fields by breaking that trades a blank "
        "template for a corrupted one.")


def test_p1b_the_transport_still_refuses_the_body_too():
    """The other half of the same rule, on the other side of the boundary. If the seam ever moves
    body parsing INTO the transport, this is where it shows up."""
    src = _src(JOURNAL)
    m = re.search(r"class _RecordingTransport.*?(?=\nclass |\Z)", src, re.S)
    assert m, "_RecordingTransport not found"
    body = _code_only(m.group(0))
    offenders = [t for t in ("resp.stream", ".aread(", ".iter_bytes", ".iter_raw") if t in body]
    assert not offenders, f"the transport began reading the body: {offenders}"


# ---------------------------------------------------------------- P2, red until the seam lands
def test_p2_the_two_stamps_of_one_round_trip_share_a_join_key():
    """The reconciler's constraint, which Heimdall accepted and sharpened: the transport's record
    and the call site's record must join, or the fix replaces one half-record with two.

    He proposed the mechanism himself -- the runner mints a per-turn id it controls, threads it
    through `_kwargs()`, and snapshots the provider's own id off the final chunk, so both stamps
    carry the same key without the transport ever touching the body. This pin does not prescribe
    the spelling; it requires that SOME shared key exists on both sides."""
    # Decommented on BOTH sides. The first run of this pin passed, and it passed falsely: the
    # runner mentions `x-ds-trace-id` exactly once, inside a comment describing what the wire
    # journal captures. A comment keyword fake-GREENED the pin whose whole job is to notice that
    # the key is absent -- the mirror of the fake-RED that narrowed P1 three functions above, and
    # the more dangerous direction, because a false green is silent.
    runner, journal = _code_only(_src(RUNNER)), _code_only(_src(JOURNAL))
    keys = ("trace_id", "x-ds-trace-id", "custom_id", "response_id")
    on_runner = {k for k in keys if k in runner}
    on_journal = {k for k in keys if k in journal}
    shared = on_runner & on_journal
    assert shared, (
        "no join key is present on both sides. The transport records status, timing and headers; "
        "the call site will record the body-derived fields. Without a shared key those are two "
        "unrelated half-records of one round trip, which looks finished and cannot be joined. "
        f"runner has {sorted(on_runner)}, journal has {sorted(on_journal)}.")


def test_p2b_the_call_site_fills_the_fields_the_template_declares():
    """The blank template is the defect. These five are declared by `wire_journal._shape` and were
    null on 4,416 of 4,416 records; each is one getattr on a chunk the loop already yields."""
    body = _stream_turn_body()
    want = ("finish_reason", "system_fingerprint")
    missing = [w for w in want if w not in body]
    assert not missing, (
        f"_stream_turn still walks past {missing}. `_shape` declares them and no caller has ever "
        "filled one; the loop is the only lane that can see them.")


def test_p2c_usage_detail_is_folded_not_just_the_four_fields_already_taken():
    """`_absorb_usage` takes prompt, completion, cache-hit and cache-miss and drops the rest.
    `reasoning_tokens` lives in `completion_tokens_details` and is the field that tells us what a
    thinking model actually spent, which is the one number nobody in this house can currently see."""
    src = _src(RUNNER)
    m = re.search(r"\n    def _absorb_usage\(self, usage\).*?\n    def ", src, re.S)
    assert m, "_absorb_usage not found"
    assert "reasoning_tokens" in m.group(0) or "completion_tokens_details" in m.group(0), (
        "the reasoning-token split is still dropped on the floor")
