# Navi half_b -- message 2 of 3: B4 (path -> organ) + E1 (context.scene.v1 field list)

## B4 -- the organ map, as a resolver plan (reinforce, never invent)

Daniel's question is "what project were they working on?" for a path. Three projections exist
today; B4 is a deterministic ladder over them, no new store:

  rung 1  EXACT-MODULE: docs/MODULE_INDEX.md groups every module under `## core/<x>/` /
          `## agent/...` headers, each with its line-1 docstring ("single responsibility").
          For `file:<rel>` ending in a tracked module, the organ is the section dir, the
          responsibility is the docstring. O(1) dict built once per process from the INDEX
          (which is auto-generated and guarded by check_comprehensibility -- it cannot
          silently rot; that is the property B4 inherits, not re-derives).
  rung 2  LAYER: docs/ARCHITECTURE.md's stack assigns every section dir a NAMED layer
          (FOUNDATION / SUBSTRATE / BIFROST / NARRATIVE / KNOWLEDGE & MEMORY / COORDINATION /
          INTERFACE / TRUST / FLEET). Path -> first-two-segments -> layer. This is the
          "project" answer at subsystem altitude: `core/recall/at_action.py` is organ
          `core/recall`, layer KNOWLEDGE & MEMORY, responsibility from rung 1.
  rung 3  PHYSICS: docs/PHYSICS.md carries the config flags + bounds a path reads/writes.
          Joined by the MAP's own columns (module x pin/paper/flags). Answers "what governs
          this path", not "what is it" -- attached as the organ row's flags[], never as the
          organ name.
  rung 4  DOCS/FENCES/RESEARCH/ARSENAL/STATE: paths outside the module census are typed by
          top-level dir with ONE documented mapping table (docs/ -> the manuals shelf;
          fences/<name>/ -> that fence's round; research/ -> in-flight research; arsenal/ ->
          the VFX product; state/ -> runtime state (internal plane); tests/ -> pins of the
          organ they import). The table is ~10 rows, in the resolver, versioned with it.
  UNRESOLVED: a path matching no rung returns organ=UNKNOWN with the rung that failed -- a
          loud miss, never a guessed organ. The INDEX already flags dirs "NOT in
          ARCHITECTURE.md layer order" (core/context, core/eye, core/screenspace...): those
          resolve by rung 2 fallback = the dir's own name, fog[] noting the layer is
          unratified. B4 does not fix that debt; it surfaces it.

  write-cost: ZERO at capture. B4 is a read-time projection over generated docs; the touch
              event carries the path, the resolver decorates.
  read-cost:  one in-memory dict lookup after a one-time INDEX parse (~300 lines, cached
              with mtime check; <1 ms). No subprocess, no store read.
  false-if:   MODULE_INDEX drifts from ARCHITECTURE (a dir added to one, not the other) --
              rung 2's fallback then shows dir-as-layer; the fog line is the receipt.

## E1 -- context.scene.v1 field list (the `orient` idiom, stdlib only, validated)

Follows orient.scene.v1's existing shapes (core/coord/orient.py: SCHEMA, _landmark, _focus_*)
so CLI/MCP/Discord/flightdeck render one object. Top level:

  schema        "context.scene.v1"        (const; renderers switch on it)
  subject       seat asking (bound, like orient's subject -- never inferred)
  anchor        {address, kind, work, display}   -- the parsed context.target.v1 from m1;
                kind in {file,file:line,dir,url,verb,ref,question}
  level         0|1|2|3                   (L0 one line, L1 card, L2 receipts, L3 raw)
  generated_at  ISO tz-aware (now_iso(); T119 discipline)
  planes[]      one row PER JOINED PLANE -- the scene's core. Each row:
      {plane,        # git | authorship | touches | lessons | docs | eye | recall | locks |
                     # focus | chronicle
       state,        # ok | empty | UNCHECKABLE | error   (a plane's silence is typed,
                     #  never rendered as zero)
       summary,      # one line (L0 renders ONLY this across planes)
       rows[],       # L1+: each row = {ref, at, who, what} where ref is ALWAYS one of the
                     # m1 ref types the doors resolve (event:/sha:/task:/lesson:/doc:/
                     # session:) -- Daniel's addendum: every row addressable, B6 refs-not-
                     # prose. A plane that cannot mint a ref for a row puts the row in
                     # fog[], not in rows[].
       cost,         # {class: o1|ologn|on, note} -- declared per plane resolver (B2)
       fog,          # this plane's coverage window + blind spot ("firehose capped at
                     # 100k", "utterances only", "0 of 1526 lessons carry files_affected")
       receipts[]}   # L2+: the raw command/probe that produced the row (git log -- <path>,
                     #  byref key, eye query) -- the drillable contour, orient-style
  span          {first_at, last_at, buckets[]}     -- B3's timeline; buckets = per-plane
                counts over equal time slices, each stamped with that plane's coverage window
  fog[]         scene-level blindness: planes not joined, anchors dropped, time-fog
  epistemic     derive_epistemic_view (core/primitives/epistemic) -- the same envelope
                orient carries; authority=mechanical_source, currency=unknown unless a
                plane proves otherwise. UNKNOWN is the truthful floor (orient.py precedent).
  drill         the one next command (orient's drill idiom; L0's only action affordance)
  effects       [] always -- a context read performs no effects; the field exists because
                orient/_assert_pure established the refusal contract on it

  write-cost: ZERO -- E1 is a read-side object; nothing is persisted.
  read-cost:  L0 = planes' summary only (the seven indexed lookups + one git log the brief
              prices); L1 = rows materialized; L3 = raw records, char-capped like cast.
  false-if:   a renderer demands a field a plane can't supply -- it must read state=
              UNCHECKABLE, and any renderer that synthesizes the missing field has left the
              schema (door-parity gate catches it: MCP twin carries the same fields).
