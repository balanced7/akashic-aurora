"""Which verbs are shaped so that nobody outside them can check whether they answer.

    py scripts/dawe_census.py                 # agent_cli.py
    py scripts/dawe_census.py path/to/file.py

Named for the bar this house adopted 2026-08-13, from the Clarke & Dawe Glenn Stevens
sketches: "I'll respond, Brian; whether that constitutes an answer in your terms is another
matter." A response that is not an answer is a defect.

It reports VERIFIABILITY, never quality, and it is a CENSUS rather than a gate -- a structural
predictor has no business failing a commit until a human has hand-checked its false-positive
rate. On the day it earns a threshold it can become a ratchet.

Run against agent_cli.py on 2026-08-14 it came back clean, which disproved the prediction that
motivated building it -- see tests/test_w164_dawe_census.py::test_d8.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.coord import dawe_census as D                          # noqa: E402
from core.paths import repo_root                                 # noqa: E402


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else repo_root() / "agent_cli.py"
    if not target.exists():
        print(f"no such file: {target}")
        return 2
    src = target.read_text(encoding="utf-8", errors="replace")
    print(f"# {target}")
    print(D.render(D.survey(src)))
    print()
    print(D.render_import_guards(D.survey_import_guards(src)))
    return 0                    # a census REPORTS; exit 0 always, so it can never gate


if __name__ == "__main__":
    raise SystemExit(main())
