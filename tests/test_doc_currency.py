"""
P4 / T024 -- doc currency guard: stamped, tracked, no dead law.

Bar: the classifier accepts the three vocabularies in their real-world formatting variants
(bold, colons, trailing prose), rejects everything else as unstamped (strict vocabulary is
the point -- 'Status: execution plan' is how dead law hides), and requires a target on
superseded-by. Guard behavior pins run against a temp docs tree.

Run: py -m pytest tests/test_doc_currency.py -q
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_doc_currency as g


def _classify(tmp_path, head):
    p = tmp_path / "doc.md"
    p.write_text(head, encoding="utf-8")
    return g.classify(str(p))


def test_current_variants_parse(tmp_path):
    for head in ("# T\n\nStatus: current\n",
                 "# T\nStatus: current (plan awaiting picks)\n",
                 "# T\n**Status:** current\n",
                 "# T\nSTATUS: Current as of 2026-07\n"):
        verdict, _ = _classify(tmp_path, head)
        assert verdict == "current", head


def test_superseded_requires_target(tmp_path):
    v, target = _classify(tmp_path, "# T\nStatus: superseded-by docs/newer-plan.md\n")
    assert v == "superseded" and target == "docs/newer-plan.md"
    v, target = _classify(tmp_path, "# T\n**Status:** superseded-by: docs/x.md (see there)\n")
    assert v == "superseded" and target.startswith("docs/x.md")
    v, target = _classify(tmp_path, "# T\nStatus: superseded\n")
    assert v == "superseded" and target == "", "no target -> guard fails it upstream"


def test_historical_parses(tmp_path):
    v, _ = _classify(tmp_path, "# T\nStatus: historical (2026-07-05 lane-era snapshot)\n")
    assert v == "historical"


def test_vocabulary_is_strict(tmp_path):
    for head in ("# T\nStatus: execution plan\n",
                 "# T\nStatus: SETTLED -- full ACK\n",
                 "# T\nStatus: v2.1 LOCKED\n",
                 "# T\nno status here at all\n"):
        v, _ = _classify(tmp_path, head)
        assert v == "unstamped", head


def test_status_must_be_near_the_top(tmp_path):
    body = "# T\n" + "filler\n" * 20 + "Status: current\n"
    v, detail = _classify(tmp_path, body)
    assert v == "unstamped" and "first 12" in detail
