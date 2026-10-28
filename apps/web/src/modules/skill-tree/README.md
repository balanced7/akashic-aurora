# Skill Tree module

Climbing skill-tree viewer embedded in the web dashboard. Architecture follows
the Skill Tree MVP Spec: bipartite content graph, pure state engine, swappable
layout + renderer seams.

## Run

From repo root:

```bash
bun install
bun run with-env bun run --filter web dev
```

Open: `http://localhost:3090/en/dashboard/skill-trees`

Tests:

```bash
bun run --filter web test
```

## Architecture (three seams)

```
SkillGraph + StateMap
        │
        ▼
  LayoutEngine.layout(graph) → LayoutResult   ← swappable (Dagre today)
        │
        ▼
  <Renderer layout={…} state={…} />           ← swappable (React Flow today)
```

1. **`core/`** — types, `evaluateState`, layout/renderer interfaces. Zero imports
   from adapters, `@xyflow/react`, `dagre`, or Next.js.
2. **`adapters/dagre-layout-engine.ts`** — only file that imports `dagre`.
3. **`adapters/react-flow/`** — only place that imports `@xyflow/react`.

`SkillTreeCanvas` receives `layoutEngine` + `Renderer` via props.

## Add a domain

1. Drop a JSON file matching `SkillGraph` into `data/`.
2. Import it and pass as `graph` to `<SkillTreeApp graph={…} />`.

## Swap renderer

```tsx
<SkillTreeCanvas
  layoutEngine={new DagreLayoutEngine()}
  Renderer={MyRenderer}  // implements SkillTreeRendererProps
  …
/>
```

## Specs

- Skill Tree MVP Spec (knowledge repo)
- Skill Tree Data Model / Visualization decision docs
