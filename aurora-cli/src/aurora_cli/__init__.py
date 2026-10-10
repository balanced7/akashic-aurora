"""aurora -- run Akashic Aurora from any terminal, without a checkout.

`aurora <verb> ...` is `uv run agent_cli.py <verb> ...` from the repo, made installable. See
launcher.py for how a call is routed, bundle.py for where the program and its state live.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("akashic-aurora-cli")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"
