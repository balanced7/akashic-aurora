"""arsenal.present -- the presentation primitive family (present.scene.v1).

Why this package exists. On 2026-09-28 Daniel asked, of the Mail-and-Wake deck, for two things
verbatim: "I want complex things to be macroable, adaptive, expressive and easy to use" and
"make these primitives be a part of a family. design them such that we can keep layouts while
swapping the presentation format (pdf, video, ui element, 3d render, 3d visualization etc)".
A deck is therefore not a pile of HTML. It is a SCENE: atoms with structured payloads, placed
into named regions of a template, measured in logical canvas units (1920x1080), coloured and
sized by token ROLE. The slides page is one projection of that scene; a PDF, a video, an
embeddable panel, a three.js space and a 3D visualisation are others, and each names what it
preserves and what it drops per atom kind before it runs.

Precedents this extends (a fourth use, not a fourth idiom):
  * core/coord/orient.py:6-7 -- "a single scene model that CLI, MCP, ToolBox, Discord, or a
    future visual world can render without deriving a second version of state";
    SCHEMA = "orient.scene.v1" (:24), render_orientation() is its CLI projection (:328).
  * arsenal/__init__.py:9-10 -- arsenal.graph/v0 and arsenal.module/v0; typed ports in
    arsenal/mediatypes.py PORT_TYPES; manifests validated by arsenal/registry.py:21; the
    contract fences/media-arsenal-contract/reconciliation.md sections 4.2-4.6 ("a mismatch
    refuses at connect time", "every run is a take", "a module without a receipt is presumed
    broken").
  * arsenal/web/lib/flow/README.md:3-6 -- "renderer-independent" primitives with "No Three.js
    imports, DOM, global timers"; a renderer may animate what the primitive computes.

Layout of the package:
  scene.py      load / validate / lint / coverage, and the constants TEMPLATES, ATOM_KINDS,
                TOKEN_ROLES.  Stdlib only; no arsenal.* imports; no renderer knowledge.
  __main__.py   `py -m arsenal.present check <scene.json>` and `... targets [--scene ...]`.
  Render targets are arsenal.module/v0 manifests in arsenal/modules/present.*.json; the
  family spec is docs/presentation-primitives.md.
"""

from __future__ import annotations

SCHEMA = "present.scene.v1"

from .scene import (  # noqa: E402  (re-exported for convenience; scene.py stays standalone)
    ATOM_KINDS,
    TEMPLATES,
    TOKEN_ROLES,
    coverage,
    lint,
    load,
    used_kinds,
    validate,
)

__all__ = ["SCHEMA", "ATOM_KINDS", "TEMPLATES", "TOKEN_ROLES", "coverage", "lint", "load", "used_kinds", "validate"]
