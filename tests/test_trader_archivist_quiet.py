"""The daily archivist must not need a visible console to leave a receipt."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_archivist_records_output_and_errors_without_console(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "trader_archivist_quiet_test", ROOT / "scripts" / "trader_archivist.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    original_out, original_err = sys.stdout, sys.stderr
    try:
        sys.stdout = None
        sys.stderr = None
        log_path = module.configure_background_stdio()
        assert sys.stdout is sys.stderr
        print("ARCHIVIST_STARTUP_RECEIPT", flush=True)
        print("ARCHIVIST_ERROR_RECEIPT", file=sys.stderr, flush=True)
    finally:
        stream = sys.stdout
        sys.stdout, sys.stderr = original_out, original_err
        if stream is not None and stream is not original_out:
            stream.close()
    body = log_path.read_text(encoding="utf-8")
    assert "ARCHIVIST_STARTUP_RECEIPT" in body
    assert "ARCHIVIST_ERROR_RECEIPT" in body
