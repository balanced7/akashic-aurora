"""Pin W12 (2026-07-18): the `wish` door appends an auto-numbered, attributed block to the
wishlist and echoes the W## back. Isolated via AKASHIC_WISHLIST_FILE; no git, no bus."""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(REPO, "agent_cli.py")

SEED = """# WISHLIST — test double

## Open

- [ ] W03 (07-18, seat-a) — an existing wish. Trigger: t. Land: l.
- [x] W07 (07-18, seat-b) — a folded one.

## Folded (exemplars)

- [x] W00a (07-18, kimi) — letters after numbers must not break numbering.

## Declined
"""


def _run(tmp, *argv):
    env = {**os.environ, "AKASHIC_WISHLIST_FILE": str(tmp)}
    return subprocess.run([sys.executable, CLI, "wish", *argv],
                          capture_output=True, text=True, timeout=30, env=env, cwd=REPO)


def test_wish_appends_numbered_attributed(tmp_path):
    f = tmp_path / "WL.md"
    f.write_text(SEED, encoding="utf-8")
    r = _run(f, "pin-seat", "a", "brand", "new", "wish", "--trigger", "it hurt", "--land", "T000")
    assert r.returncode == 0, r.stderr[:300]
    assert "filed W08" in r.stdout, f"expected next number 8 (max was 7): {r.stdout}"
    text = f.read_text(encoding="utf-8")
    assert "- [ ] W08" in text and "(07-" in text and "pin-seat" in text
    assert "a brand new wish" in text and "Trigger: it hurt." in text and "Land: T000." in text
    open_sec = text.split("## Folded")[0]
    assert "W08" in open_sec, "new wish must land in Open, above the Folded anchor"


def test_wish_numbering_increments_across_calls(tmp_path):
    f = tmp_path / "WL.md"
    f.write_text(SEED, encoding="utf-8")
    _run(f, "s1", "first")
    r2 = _run(f, "s2", "second")
    assert "filed W09" in r2.stdout, f"second wish must be W09: {r2.stdout}"


def test_wish_refuses_empty_and_missing(tmp_path):
    f = tmp_path / "WL.md"
    f.write_text(SEED, encoding="utf-8")
    assert _run(f, "seat").returncode == 2, "empty wish must refuse"
    assert _run(tmp_path / "absent.md", "seat", "x").returncode == 2, "missing ledger must refuse"


def test_wish_text_file_path(tmp_path):
    f = tmp_path / "WL.md"
    f.write_text(SEED, encoding="utf-8")
    body = tmp_path / "body.md"
    body.write_text("a wish with --flag-shaped prose (parens, colons: yes)", encoding="utf-8")
    r = _run(f, "seat", "--text-file", str(body))
    assert r.returncode == 0 and "filed W08" in r.stdout
    assert "--flag-shaped prose" in f.read_text(encoding="utf-8")
