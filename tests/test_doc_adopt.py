"""`doc adopt` -- the missing half of the birth door.

THE GAP (live, 2026-07-31): since the P3 flip (2026-07-23) rule-13 REFUSES all new loose
`research/*.md`, and the boot whisper still tells every seat "research/** persists by doctrine".
Seats -- especially the ones whose ACL has no exec and who therefore cannot commit at all --
keep filing positions there. Ten such peer positions were stranded on one day: written, real,
uncommittable, and one clobber from gone.

`doc new` mints an atom from a body you hand it. There was no way to bring an EXISTING loose
file through the door, so the only sanctioned path for rescuing another seat's filed work was
to retype or hand-copy it. That is the work->record handoff the design capture named UNOWNED,
and it was unowned because it was also IMPOSSIBLE.

`doc adopt <path>` closes it: read the file, infer what can be inferred, mint it as a typed
atom with authorship, and DO NOT touch the original. Non-destructive by construction -- an
adopt that deleted its source would be a Scribe that can lose work, which is the opposite of
the point.

These pins cover the pure inference; the live drain of the ten stranded positions is the
integration proof.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agent_cli  # noqa: E402


class Args:
    """Minimal stand-in for argparse.Namespace."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


# ---------------------------------------------------------------- title inference

@pytest.mark.parametrize("stem,expected", [
    ("buffer-authority-codex-position-2026-07-31", "buffer-authority-codex-position"),
    ("t125-newcomer-lookups-cursor-grok", "t125-newcomer-lookups-cursor-grok"),
    ("20260731_some_capture", "some-capture"),
    ("Mixed Case Name", "mixed-case-name"),
])
def test_p1_title_is_slugged_and_dates_stripped(stem, expected):
    """A filename is a title with punctuation and a date bolted on. Strip both."""
    assert agent_cli._adopt_title(stem) == expected


def test_p2_title_never_returns_empty():
    """A file named only with a date must still get a usable title, not ''."""
    out = agent_cli._adopt_title("2026-07-31")
    assert out and out.strip("-"), f"degenerate title: {out!r}"


# ---------------------------------------------------------------- type inference

@pytest.mark.parametrize("stem,expected", [
    ("buffer-round-reconciliation", "design"),
    ("buffer-authority-codex-position", "report"),
    ("t095-m1-contract-review-codex", "report"),
    ("inhabitant-synthesis-codex-order-verdict", "ruling"),
    ("design-conversation-2026-07-31", "chronicle"),
    ("something-with-no-hint", "report"),
])
def test_p3_type_inferred_from_the_name(stem, expected):
    assert agent_cli._adopt_type(stem) == expected


# ---------------------------------------------------------------- seat inference

def test_p4_seats_inferred_from_filename():
    """Peer positions are named after their author far more often than not."""
    assert "kimi" in agent_cli._adopt_seats("t095-m1-cross-steer-kimi-2026-07-31")
    assert "codex" in agent_cli._adopt_seats("buffer-authority-codex-position-2026-07-31")


def test_p5_seat_inference_handles_hyphenated_ids():
    """cursor_grok appears in filenames as cursor-grok; the underscore id must still match."""
    got = agent_cli._adopt_seats("t125-newcomer-lookups-cursor-grok")
    assert "cursor_grok" in got, f"hyphenated seat id not resolved: {got!r}"


def test_p6_no_seat_in_name_yields_empty_not_a_guess():
    """Silence beats a wrong author stamp -- attribution is not a place to be creative."""
    assert agent_cli._adopt_seats("arch-truth-crossreview-2026-07-31") == ""


# ---------------------------------------------------------------- door behaviour

def test_p7_adopt_refuses_a_missing_file_loudly(capsys):
    rc = agent_cli.cmd_doc(Args(sub="adopt", path="research/in-flight/no-such-file.md"))
    assert rc == 2
    assert "REFUSED" in capsys.readouterr().out


def test_p8_adopt_refuses_with_no_path(capsys):
    rc = agent_cli.cmd_doc(Args(sub="adopt", path=""))
    assert rc == 2
    assert "REFUSED" in capsys.readouterr().out


def test_p9_adopt_is_non_destructive(tmp_path, monkeypatch, capsys):
    """THE invariant. The source file must survive adoption untouched."""
    src = tmp_path / "peer-position-kimi-2026-07-31.md"
    original = "# a peer's filed position\n\nbody text that must not be rewritten\n"
    src.write_text(original, encoding="utf-8")

    minted = {}

    class FakeFam:
        def __init__(self, *a, **kw):
            pass

        def mint(self, typ, title, body, **kw):
            minted.update(typ=typ, title=title, body=body, seats=kw.get("seats"))
            return {"id": "art_test", "header": {"body_type": "markdown"}}

    import core.library.atoms as _atoms
    import core.library.projection as _proj
    monkeypatch.setattr(_atoms, "AtomFamily", FakeFam)
    monkeypatch.setattr(_proj, "render_atom",
                        lambda atom, repo_root=None: os.path.join(ROOT, "docs", "library",
                                                                  "report", "x.md"))

    rc = agent_cli.cmd_doc(Args(sub="adopt", path=str(src)))
    assert rc == 0, capsys.readouterr().out
    assert src.exists(), "adopt DELETED its source -- a Scribe that can lose work"
    assert src.read_text(encoding="utf-8") == original, "adopt REWROTE its source"
    assert minted["body"] == original, "the author's bytes must reach the atom unmodified"
    assert "kimi" in (minted["seats"] or []), "authorship lost in adoption"
