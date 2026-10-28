"use client";

import { useEffect, useState } from "react";

import type { LayoutEngine } from "../core/layout-engine";
import type { SkillTreeRenderer } from "../core/renderer";
import type {
  LayoutResult,
  NodeKind,
  SkillGraph,
  StateMap,
} from "../core/types";

interface SkillTreeCanvasProps {
  graph: SkillGraph;
  state: StateMap;
  /** Swap DagreLayoutEngine without touching this component */
  layoutEngine: LayoutEngine;
  /** Swap ReactFlowRenderer without touching this component */
  Renderer: SkillTreeRenderer;
  selectedNodeId?: string | null;
  onNodeClick?: (nodeId: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
  visibleNodeKinds?: ReadonlySet<NodeKind>;
}

export function SkillTreeCanvas({
  graph,
  state,
  layoutEngine,
  Renderer,
  selectedNodeId,
  onNodeClick,
  onNodeHover,
  visibleNodeKinds,
}: SkillTreeCanvasProps) {
  const [layout, setLayout] = useState<LayoutResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.resolve(layoutEngine.layout(graph)).then((result) => {
      if (!cancelled) setLayout(result);
    });
    return () => {
      cancelled = true;
    };
  }, [graph, layoutEngine]);

  if (!layout) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-zinc-500">
        Laying out skill tree…
      </div>
    );
  }

  return (
    <Renderer
      layout={layout}
      state={state}
      selectedNodeId={selectedNodeId}
      onNodeClick={onNodeClick}
      onNodeHover={onNodeHover}
      visibleNodeKinds={visibleNodeKinds}
    />
  );
}
