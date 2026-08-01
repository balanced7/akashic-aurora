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


# --- the ledger must not corrupt itself silently -------------------------------------------
# Measured 2026-08-01: docs/WISHLIST.md carries 128 blocks but a highest id of W114 -- 14 ids
# (W00, W57..W69) each appear TWICE, so any citation of "W58" is ambiguous. max(nums)+1 can
# never collide against a CORRECT read, so these came from STALE reads: two seats each filed a
# batch against different versions of the file. The door then wrote the duplicate without
# noticing, because it checks nothing after allocating. This is Daniil's standing capture
# mechanism ("append the moment friction is felt; never delete") quietly corrupting itself.

DUPED = """# WISHLIST — test double

## Open

- [ ] W03 (07-18, seat-a) — an existing wish. Trigger: t. Land: l.
- [ ] W04 (07-21, seat-a) — first of a colliding batch.
- [ ] W04 (07-24, seat-b) — same id, different day, different content.

## Folded (exemplars)

## Declined
"""


def test_wish_reports_a_collided_ledger_instead_of_extending_it_silently(tmp_path):
    """A ledger with duplicate ids must be REPORTED. It still files -- a no-ceremony capture
    door that refuses is worse than an ambiguous id -- but it may not stay quiet about it."""
    p = tmp_path / "WISHLIST.md"
    p.write_text(DUPED, encoding="utf-8")
    r = _run(p, "claude", "a new wish")
    out = (r.stdout or "") + (r.stderr or "")
    assert "W04" in out and ("collid" in out.lower() or "duplicate" in out.lower()), (
        "the door appended to a ledger whose id space is already corrupt and said nothing:\n" + out
    )


def test_wish_never_reuses_an_existing_id(tmp_path):
    """Whatever id is allocated must not already exist in the file."""
    import re
    p = tmp_path / "WISHLIST.md"
    p.write_text(SEED, encoding="utf-8")
    before = set(re.findall(r"- \[[ x~]\] W(\d+)", p.read_text(encoding="utf-8")))
    r = _run(p, "claude", "another wish")
    assert r.returncode == 0, r.stdout + r.stderr
    m = re.search(r"filed W(\d+)", r.stdout or "")
    assert m, "no filed-id echoed: " + (r.stdout or "")
    assert m.group(1) not in before, f"allocated W{m.group(1)} which already existed"
