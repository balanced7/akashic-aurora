"""The /keylab/ hook for the VFX Bench (arsenal/keylab/webmount.py): it serves exactly the mount and what the mount
imports, and every one of those files exists and imports only files in the same allowlist."""
import re
from pathlib import Path

from arsenal.keylab.webmount import ALLOWED, keylab_route

REPO = Path(__file__).resolve().parent.parent


def test_each_allowed_name_maps_to_a_real_file():
    for name, rel in ALLOWED.items():
        assert keylab_route(f"/keylab/{name}") == rel
        assert (REPO / rel).is_file(), rel


def test_refuses_everything_else():
    for path in ["/keylab/", "/keylab/../scripts/bifrost_ui.py", "/keylab/keylab-mount.js/x", "/keylab/KEYLAB-MOUNT.JS",
                 "/keylab/params-ui.js", "/keylab/keylab-mount.mjs", "/keylab/%2e%2e/x.js", "/web/lib/keylab-mount.js",
                 "/keylab/keylab-mount.js?x=1", "", None, "/keylab/sub/keylab-client.js"]:
        assert keylab_route(path) is None, path


def test_the_mount_only_imports_what_the_route_serves():
    # a relative import the route would not serve is a module that fails to load on /vfx
    for rel in ALLOWED.values():
        text = (REPO / rel).read_text(encoding="utf-8")
        for spec in re.findall(r"""^\s*import\s[^;]*?from\s+["']([^"']+)["']""", text, re.M):
            assert spec.startswith("./"), f"{rel} imports {spec}"
            assert spec[2:] in ALLOWED, f"{rel} imports {spec}, which /keylab/ would not serve"
