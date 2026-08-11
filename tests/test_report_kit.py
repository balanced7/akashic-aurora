"""T275 -- the report kit is a SYSTEM, and these pins hold the properties that make it one.

Daniil 2026-08-10: "Is there a way to verbify it so that it is easier for you to make these?"

The temptation with a request like this is a document template. The pins below exist to keep
it from becoming one, and to hold the two properties that would fail SILENTLY:

  P1  THE KIT INLINES, NEVER LINKS. Published artifacts run under a CSP blocking every
      external host, so a <link> falls back to unstyled -- and that failure looks like a
      styling mistake rather than a blocked request, which is why it needs a pin rather than
      a comment.
  P4  EVERY PRIMITIVE IS DOCUMENTED. Checked against the kit itself, so a new primitive
      cannot ship without saying what it is FOR. A primitive used off-purpose is how a
      design system becomes wallpaper.

Run: py -m pytest tests/test_report_kit.py -q
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

GEN = os.path.join(ROOT, "scripts", "generators", "gen_report_scaffold.py")
KIT = os.path.join(ROOT, "design", "report-kit.css")


def gen(*args, timeout=90):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, GEN, *args], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def test_p1_the_kit_is_inlined_and_nothing_is_fetched():
    rc, out = gen("--title", "Pin Report")
    assert rc == 0, out
    assert "<style>" in out and "--aurora" in out, "the kit must be INLINED in the scaffold"
    # STRIP COMMENTS FIRST. The first draft of this pin matched the kit's own comment
    # explaining why we never <link> -- it flagged the WARNING as the violation, which is
    # location-matching rather than meaning-matching, the same error check_ports v1 made.
    live = re.sub(r"/\*.*?\*/", "", out, flags=re.S)          # css comments
    live = re.sub(r"<!--.*?-->", "", live, flags=re.S)        # html comments
    for external in ("<link", "http://", "https://", "@import", "url("):
        assert external not in live, \
            f"a published artifact blocks every external host -- found {external!r} in LIVE " \
            f"markup, which would fall back to unstyled and look like a styling bug"


def test_p2_both_themes_are_defined_and_the_override_wins_both_ways():
    css = open(KIT, encoding="utf-8").read()
    assert "prefers-color-scheme: light" in css, "the OS signal must be honoured"
    assert ':root[data-theme="dark"]' in css and ':root[data-theme="light"]' in css, \
        "the viewer's toggle must be able to win in BOTH directions, not just one"
    # Components must style through tokens, never inside the media query -- otherwise the
    # data-theme override cannot reach them.
    media = css.split("@media (prefers-color-scheme: light)", 1)[1].split("}\n}", 1)[0]
    assert ".card" not in media and ".tile" not in media, \
        "components must style through TOKENS; redefining them inside the media query makes " \
        "the data-theme override unreachable"


def test_p3_the_kit_lives_in_exactly_one_file():
    """An improvement to the palette must propagate, not fork into a fourth variant."""
    hits = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if any(x in dirpath for x in ("_archive", "ComfyUI-Zluda", ".git", "node_modules")):
            continue
        for f in filenames:
            if f.endswith(".css") and "report-kit" in f:
                hits.append(os.path.join(dirpath, f))
    assert len(hits) == 1, f"the kit must have exactly one home, found: {hits}"


def test_p4_every_primitive_in_the_kit_is_documented_in_the_crib():
    """THE PIN THAT KEEPS IT A SYSTEM. A primitive nobody documented is a primitive whose
    PURPOSE is unknown, and purpose is what stops it becoming decoration."""
    rc, crib = gen("--crib")
    assert rc == 0, crib
    css = open(KIT, encoding="utf-8").read()
    # Structural class selectors the kit defines (skip state/modifier and element helpers).
    defined = set(re.findall(r"^\.([a-z][a-z0-9-]+)\s*(?:\{|,)", css, re.M))
    skip = {"go", "hold", "stop", "num", "prose", "wrap", "ok", "no", "cl", "mo", "a", "b",
            "scroll", "v", "n", "rule"}
    for cls in sorted(defined - skip):
        assert cls in crib, \
            f"'.{cls}' is defined in the kit but absent from the crib -- every primitive " \
            f"must say what it is FOR, or it becomes decoration"


def test_p5_an_empty_scaffold_is_still_valid_html():
    rc, out = gen("--title", "Empty")
    assert rc == 0
    assert out.count("<div class=\"wrap\">") == 1 and out.rstrip().endswith("</div>")
    assert "<title>Empty</title>" in out, "the title names the tab and the gallery card"
    for tag in ("<!doctype", "<html", "<head>", "<body>"):
        assert tag not in out.lower(), \
            f"the publisher supplies the skeleton -- {tag} would be nested inside it"


def test_p6_a_missing_title_refuses_loudly():
    rc, out = gen()
    assert rc != 0, "a scaffold with no title would publish as an unnamed gallery card"
    assert "title" in out.lower()


def test_p7_the_scaffold_says_it_is_a_system_not_a_template():
    """The instruction that keeps the next report from copying the last one's shape."""
    rc, out = gen("--title", "Shape")
    assert "system, not a template" in out.lower()
    assert "verified against the tree" in out.lower(), \
        "the numbers rule must ride the scaffold, where it is read at composing time"
