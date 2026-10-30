"""_legacy -- every extracted verb, re-exported under its ORIGINAL `cmd_*` name.

THE COMPAT CONTRACT, in one file.

A verb body moving out of `agent_cli.py` must not change a single name that anything outside this
package resolves. Four kinds of outside, all real:

  * OUT-OF-TREE: `agent/harness/dsh_plugin/bridge.py` does `import agent_cli` and then
    `agent_cli._recent_commits(...)`, `agent_cli.write_last_session_draft(...)`,
    `agent_cli.last_session_draft_path()`. That plugin is DEPLOYED to a home directory, so a
    version skew here is not a compile error in this repo -- it is silence at the one seam where
    the two halves of the deployment meet. The out-of-tree position (2026-09-17): "fail-open on
    the work path, fail-LOUD on the boundary."
  * THE HOOKS: `agent/harness/hooks/*.py` and `scripts/hooks/*.py` import `agent_cli`; so do the
    seat runners and `ai_setup_mcp.py`.
  * THE PINS: `tests/test_w084_*` and friends assert `parsed.fn is agent_cli.cmd_<verb>`. That is
    identity, not just presence -- so this module must export the very object `build_parser` binds,
    which it does, because `agent_cli` imports these names and feeds them to `set_defaults`.
  * THE CHECKERS: `check_unbound_names` resolves names in `agent_cli.py` statically; an imported
    `cmd_*` is bound, so the move is invisible to it in the good way.

So: nothing in this file does work. It is a list of aliases, kept boring on purpose, and it is the
one place to look when asking "what did the extraction promise to keep".
"""
from verbs.groups.coord.scene import cmd_orient  # noqa: F401

__all__ = [
    "cmd_orient",
]
