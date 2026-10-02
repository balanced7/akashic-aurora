"""G5 latent fix (IC-0023): gen_prior_art_register, run as a script, names the same launcher that
check_comprehensibility renders in-process -- otherwise the doc it regenerates reads as stale."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_prior_art_script_run_names_the_in_process_launcher(tmp_path):
    from core.paths import python_launcher

    gen_dir = ROOT / "scripts" / "generators"
    # cwd outside the repo: like `python scripts/generators/gen_prior_art_register.py`, only the
    # generator's own directory is importable
    code = f"import sys; sys.path.insert(0, {str(gen_dir)!r}); import gen_prior_art_register as g; print(g._pyl())"
    r = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == python_launcher()
