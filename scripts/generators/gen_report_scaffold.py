"""gen_report_scaffold -- emit a visual-report scaffold with the design kit inlined.

Daniil 2026-08-10, after three artifact reports in two days: "Is there a way to verbify it so
that it is easier for you to make these?"

WHAT THIS HANDS OVER IS A SYSTEM, NOT A DOCUMENT, and that is the design constraint rather
than a caveat. The three reports that produced design/report-kit.css needed three different
SHAPES -- a retrospective, a set of decision forks, a reconciliation built around a
contradiction -- and the thing worth reproducing was the FIT. A generator that emitted a
fixed document would flatten exactly that, and the artifact-design guidance warns against
templated output in the same words. So this emits tokens, primitives, and a crib of what each
primitive is FOR; the composition is written fresh every time.

THE KIT IS INLINED, NEVER LINKED. Published artifacts run under a CSP that blocks every
external host, so a <link> would silently fall back to unstyled -- the worst failure mode,
because it looks like a styling mistake rather than a blocked request. Inlining at emit time
also means the kit lives in ONE file: improving the palette improves every future report
instead of forking a fourth variant.

Run:  py scripts/generators/gen_report_scaffold.py --title "..." --out <path.html>
      py scripts/generators/gen_report_scaffold.py --crib     # just the primitive reference
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KIT = os.path.join(ROOT, "design", "report-kit.css")

#: Every primitive the kit defines, and WHAT IT IS FOR. The purpose matters more than the
#: class name: a primitive used off-purpose is how a design system becomes wallpaper. A pin
#: checks this list against the kit, so a new primitive cannot ship undocumented.
CRIB = [
    ("header / .eyebrow / h1 / .standfirst",
     "Opening. The standfirst is a serif thesis sentence, not a summary."),
    ("hr.rule",
     "Section break carrying the project's own colours. Use 2-4 times, never between every section."),
    (".tiles > .tile > .v + .k",
     "3-6 headline NUMBERS. Never prose. Digits are tabular by default."),
    (".card[.go|.hold|.stop] > .head + .paths > .path > .plabel[.a|.b] + .ptext, then .rec",
     "A DECISION WITH REAL COSTS ON BOTH SIDES. .plabel.a names the path you lean toward, "
     ".plabel.b the one you do not; .rec carries the recommendation. If one path is obviously "
     "wrong it is rhetoric wearing a choice's clothes -- use .rows instead."),
    (".timeline > .tl > .when + .what",
     "ONLY when order carries information the reader needs. Not decoration for a list."),
    (".versus > .side  (+ .synth)",
     "A GENUINE DISAGREEMENT, both sides stated fairly. NOT a pro/con list. Pair with "
     ".synth when a reconciliation exists."),
    ("blockquote > mark + .who",
     "Someone's words verbatim. mark highlights the phrase that actually matters."),
    (".rows > .row > .rt + .rd",
     "A flat list where each item has a label and a consequence."),
    (".scroll > table  (td.n, .v.ok/.no/.cl/.mo)",
     "Comparison. Wide content scrolls ITSELF so the page never scrolls sideways."),
    ("--go / --hold / --stop",
     "SEMANTIC colour: cheap / needs judgement / costs either way. Never decoration."),
    ("--aurora",
     "The accent. Structure and emphasis only -- it must never carry status."),
]


def crib_text(prefix="  "):
    out = []
    for cls, why in CRIB:
        out.append(f"{prefix}{cls}")
        out.append(f"{prefix}    {why}")
    return "\n".join(out)


def render(title: str, eyebrow: str) -> str:
    try:
        kit = open(KIT, encoding="utf-8").read()
    except Exception as e:
        print(f"FAIL: cannot read {os.path.relpath(KIT, ROOT)}: {e}", file=sys.stderr)
        raise SystemExit(1)
    return f"""<title>{title}</title>

<style>
{kit}</style>

<!-- ============================================================================
     PRIMITIVES AVAILABLE. Compose freely -- this is a system, not a template, and
     the shape should fit THIS report rather than the last one.

{crib_text("     ")}

     RULES THAT ARE NOT NEGOTIABLE:
       * Every number verified against the tree before it goes in.
       * A finding that failed states that it failed, in the same voice as one that passed.
       * Semantic colour carries meaning; --aurora carries none.
     ============================================================================ -->

<div class="wrap">

<header>
  <div class="eyebrow">{eyebrow}</div>
  <h1>REPLACE: the thesis, as a sentence a reader could disagree with.</h1>
  <p class="standfirst">REPLACE: what this document is for, and what it will cost the reader
  to read it.</p>
</header>

<hr class="rule">

<section>
  <h2>Replace this section label</h2>
  <p class="prose">Compose from the primitives above. Delete this scaffold comment block and
  every placeholder before publishing.</p>
</section>

<footer>
  REPLACE: provenance. Where the numbers came from, and the commit or atom that holds the
  full record.
</footer>

</div>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="", help="the <title>: names the tab and the gallery card")
    ap.add_argument("--eyebrow", default="Akashic Aurora", help="the small mono line above the headline")
    ap.add_argument("--out", default="", help="write here instead of stdout")
    ap.add_argument("--crib", action="store_true", help="print the primitive reference and exit")
    a = ap.parse_args()

    if a.crib:
        print("report-kit primitives:\n")
        print(crib_text())
        return 0
    if not a.title:
        print("FAIL: --title is required (it names the browser tab and the gallery card)",
              file=sys.stderr)
        return 2

    html = render(a.title, a.eyebrow)
    if not a.out:
        print(html)
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {a.out} ({len(html)} chars, kit inlined)\n"
          f"compose it, then publish with the Artifact tool.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
