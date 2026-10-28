"use client";

import { useEffect, useMemo, useState } from "react";

import { cn } from "@akashic-labs/ui";
import { Button } from "@akashic-labs/ui-web/button";

import { DagreLayoutEngine } from "../adapters/dagre-layout-engine";
import { ReactFlowRenderer } from "../adapters/react-flow/ReactFlowRenderer";
import climbingData from "../data/climbing.json";
import { useSkillTreeState } from "../hooks/useSkillTreeState";

import { NodeDetailPanel } from "./NodeDetailPanel";
import { SkillTreeCanvas } from "./SkillTreeCanvas";

import type { NodeKind, SkillGraph } from "../core/types";

const climbingGraph = climbingData as SkillGraph;

const KIND_TOGGLES: { kind: NodeKind; label: string }[] = [
  { kind: "milestone_tier", label: "Milestones" },
  { kind: "action", label: "Actions" },
];

export function SkillTreeApp({
  graph = climbingGraph,
}: {
  graph?: SkillGraph;
}) {
  const layoutEngine = useMemo(() => new DagreLayoutEngine(), []);
  const { state, hydrated, markNodeAchieved, markNodeInProgress, resetState } =
    useSkillTreeState(graph);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [visibleKinds, setVisibleKinds] = useState<Set<NodeKind>>(
    () => new Set<NodeKind>(["milestone_tier", "action"]),
  );

  // Clear selection when the selected node is filtered out.
  useEffect(() => {
    if (!selectedNodeId) return;
    const node = graph.nodes.find((n) => n.id === selectedNodeId);
    if (node && !visibleKinds.has(node.type)) {
      setSelectedNodeId(null);
    }
  }, [graph.nodes, selectedNodeId, visibleKinds]);

  function toggleKind(kind: NodeKind) {
    setVisibleKinds((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) {
        if (next.size <= 1) return prev; // keep at least one kind visible
        next.delete(kind);
      } else {
        next.add(kind);
      }
      return next;
    });
  }

  return (
    <div className="flex min-h-[600px] w-full min-w-0 flex-1 flex-col gap-3 self-stretch">
      <div className="flex w-full flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-zinc-900">
            {graph.title}
          </h2>
          <p className="text-sm text-zinc-500 capitalize">{graph.domain}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div
            className="flex items-center gap-1 rounded-lg border border-zinc-200 bg-white p-1"
            role="group"
            aria-label="Show node types"
          >
            {KIND_TOGGLES.map(({ kind, label }) => {
              const active = visibleKinds.has(kind);
              return (
                <button
                  key={kind}
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleKind(kind)}
                  className={cn(
                    "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                    active
                      ? "bg-zinc-900 text-white"
                      : "text-zinc-600 hover:bg-zinc-100",
                  )}
                >
                  {label}
                </button>
              );
            })}
          </div>
          <Button variant="outline" size="sm" onClick={resetState}>
            Reset progress
          </Button>
        </div>
      </div>

      <div className="flex min-h-[600px] w-full min-w-0 flex-1 overflow-hidden rounded-xl border border-zinc-200 bg-zinc-50">
        <div className="relative min-h-[600px] min-w-0 flex-1">
          {hydrated ? (
            <SkillTreeCanvas
              graph={graph}
              state={state}
              layoutEngine={layoutEngine}
              Renderer={ReactFlowRenderer}
              selectedNodeId={selectedNodeId}
              onNodeClick={setSelectedNodeId}
              visibleNodeKinds={visibleKinds}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-zinc-500">
              Loading progress…
            </div>
          )}
        </div>
        <NodeDetailPanel
          graph={graph}
          state={state}
          nodeId={selectedNodeId}
          onMarkAchieved={markNodeAchieved}
          onMarkInProgress={(id) => markNodeInProgress(id)}
          onClose={() => setSelectedNodeId(null)}
        />
      </div>
    </div>
  );
}
