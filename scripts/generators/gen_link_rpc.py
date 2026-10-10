"""gen_link_rpc -- regenerate core/link/rpc_types.py from aurora-linkd's OpenRPC contract.

The contract between Python and the fleet-link daemon is the method table in
aurora-rs/linkd/src/rpc.rs. `aurora-linkd openrpc` prints it; aurora-rs/linkd/openrpc.json is the
checked-in copy (a Rust test keeps it current). This turns that file into typed parameter dicts and
the METHODS table the client checks every call against, so a renamed or removed parameter fails at
the call site rather than as a remote error.

Run:  uv run scripts/generators/gen_link_rpc.py            # writes core/link/rpc_types.py
      uv run scripts/generators/gen_link_rpc.py --check    # exit 1 if stale
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "aurora-rs" / "linkd" / "openrpc.json"
OUT = ROOT / "core" / "link" / "rpc_types.py"

_PY = {"string": "str", "integer": "int", "boolean": "bool", "object": "dict[str, Any]", "array": "list[Any]"}


def _class_name(method: str) -> str:
    return "".join(part.capitalize() for part in method.replace(".", "_").split("_")) + "Params"


def _tuple(items: tuple[str, ...]) -> str:
    inner = ", ".join(json.dumps(x) for x in items)
    return f"({inner},)" if len(items) == 1 else f"({inner})"


def render(spec: dict) -> str:
    lines = [
        '"""rpc_types -- GENERATED from aurora-rs/linkd/openrpc.json by scripts/generators/gen_link_rpc.py.',
        "",
        "Do not edit by hand: change the method table in aurora-rs/linkd/src/rpc.rs, regenerate",
        "openrpc.json (`cargo run -p aurora-linkd -- openrpc`), then rerun the generator.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any, NotRequired, TypedDict",
        "",
        f'CONTRACT_VERSION = "{spec["info"]["version"]}"',
        "",
    ]
    table = []
    network = []
    for m in spec["methods"]:
        name = m["name"]
        cls = _class_name(name)
        lines += ["", f"class {cls}(TypedDict):", f'    """{m["summary"]}"""']
        if m["params"]:
            lines.append("")
        for p in m["params"]:
            t = _PY.get(p["schema"].get("type", ""), "Any")
            lines.append(f"    {p['name']}: {t if p['required'] else f'NotRequired[{t}]'}")
        lines.append("")
        req = tuple(p["name"] for p in m["params"] if p["required"])
        opt = tuple(p["name"] for p in m["params"] if not p["required"])
        table.append(f"    {json.dumps(name)}: ({_tuple(req)}, {_tuple(opt)}),")
        if m.get("x-network"):
            network.append(name)
    lines += [
        "",
        "#: method -> (required parameters, optional parameters)",
        "METHODS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {",
        *table,
        "}",
        "",
        "#: Methods an offline daemon refuses: they need `aurora link serve`.",
        f"NETWORK: frozenset[str] = frozenset({json.dumps(sorted(network))})",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if rpc_types.py is stale")
    a = ap.parse_args(argv)
    text = render(json.loads(SPEC.read_text(encoding="utf-8")))
    if a.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"{OUT.relative_to(ROOT)} is stale: run scripts/generators/gen_link_rpc.py")
            return 1
        print(f"{OUT.relative_to(ROOT)} is current")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
