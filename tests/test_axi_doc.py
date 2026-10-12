"""Pins for `doc` after the AXI conversion: the mint receipt and the refusals, as an agent sees
them. The atom family and the projection renderer are faked, so nothing is written to the store
or to docs/library.

Run: uv run pytest tests/test_axi_doc.py -q
"""

import argparse
from pathlib import Path

import pytest

import agent_cli
import core.library.atoms as atoms_mod
import core.library.projection as projection_mod
from core.library import taxonomy

ROOT = Path(agent_cli.__file__).resolve().parent


class _Family:
    def __init__(self, *a, **kw):
        pass

    def mint(self, typ, title, body, **kw):
        return {"id": f"art_20261012_{title}_abc123", "header": {"body_type": "markdown"}, "body_type_source": "auto"}


@pytest.fixture
def fakes(monkeypatch):
    monkeypatch.setattr(atoms_mod, "AtomFamily", _Family)
    monkeypatch.setattr(projection_mod, "render_atom", lambda atom, repo_root: str(ROOT / "docs/library/report/x.md"))
    monkeypatch.setattr(taxonomy, "classify", lambda text: [])
    monkeypatch.setattr(agent_cli, "_ledger_claim_arc", lambda seat: None)
    monkeypatch.setattr("core.foundation.store.create_store", lambda: None)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _doc(capsys, sub="new", **kw):
    ns = argparse.Namespace(sub=sub, type="", title="", arc="", seats="", body="", body_file="", category=None,
                            draft=False, gist="", body_type="", from_bus="", cite=None)  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_doc(ns)
    cap = capsys.readouterr()
    return code, cap.out + cap.err


def test_a_mint_is_a_receipt_with_each_stamp_and_its_source(fakes, capsys):
    code, text = _doc(capsys, type="report", title="probe", seats="bench", body="hello")
    assert code == 0
    assert "atom: art_20261012_probe_abc123\ntype: report\nstatus: current" in text
    assert "arc_source: (none inferable)" in text
    assert "projection: docs/library/report/x.md" in text
    assert "doc arc art_20261012_probe_abc123 <label>" in text


def test_missing_type_names_the_atom_types(fakes, capsys):
    code, text = _doc(capsys, title="probe")
    assert code == 2
    assert "code: USAGE" in text
    assert "atom_types[8]: contract,map,design,brief,report,chronicle,ledger,ruling" in text


def test_bare_doc_is_a_usage_error_not_a_traceback(fakes, capsys):
    code, text = _doc(capsys, sub=None)
    assert code == 2
    assert "new, adopt or arc" in text


def test_adopt_of_a_missing_file_is_not_found(fakes, capsys, tmp_path):
    code, text = _doc(capsys, sub="adopt", path=str(tmp_path / "nope.md"))
    assert code == 2
    assert "code: NOT_FOUND" in text
