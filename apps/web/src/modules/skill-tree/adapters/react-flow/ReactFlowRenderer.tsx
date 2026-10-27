"use client";

import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  useReactFlow,
  useStore,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useRef } from "react";

import { ActionNode } from "./ActionNode";
import { MilestoneNode } from "./MilestoneNode";

import type { SkillTreeRendererProps } from "../../core/renderer";
import type { Edge, Node } from "@xyflow/react";

const nodeTypes = {
  milestone_tier: MilestoneNode,
  action: ActionNode,
};

const FIT_VIEW_OPTIONS = { padding: 0.2 } as const;

function isHyperedgeId(id: string): boolean {
  return id.startsWith("hyper:");
}

/** Re-fit after the container leaves zero width, or when filters change. */
function FitViewWhenSized({ filterKey }: { filterKey: string }) {
  const { fitView } = useReactFlow();
  const width = useStore((s) => s.width);
  const height = useStore((s) => s.height);
  const hadSizeRef = useRef(false);
  const lastFilterRef = useRef(filterKey);

  useEffect(() => {
    const hasSize = width > 0 && height > 0;
    const filterChanged = lastFilterRef.current !== filterKey;
    lastFilterRef.current = filterKey;

    if (hasSize && (!hadSizeRef.current || filterChanged)) {
      requestAnimationFrame(() => {
        void fitView(FIT_VIEW_OPTIONS);
      });
    }
    hadSizeRef.current = hasSize;
  }, [width, height, fitView, filterKey]);

  return null;
}

function ReactFlowCanvas({
  layout,
  state,
  selectedNodeId,
  onNodeClick,
  onNodeHover,
  visibleNodeKinds,
}: SkillTreeRendererProps) {
  const kinds = visibleNodeKinds;

  const visibleNodes = useMemo(() => {
    if (!kinds || kinds.size === 0) return layout.nodes;
    return layout.nodes.filter((n) => kinds.has(n.type));
  }, [layout.nodes, kinds]);

  const visibleIds = useMemo(
    () => new Set(visibleNodes.map((n) => n.id)),
    [visibleNodes],
  );

  const filterKey = useMemo(() => {
    if (!kinds) return "all";
    return [...kinds].sort().join(",");
  }, [kinds]);

  const nodes: Node[] = useMemo(() => {
    const stackMeta = new Map<string, { index: number; size: number }>();
    const byChain = new Map<string, typeof visibleNodes>();
    for (const n of visibleNodes) {
      if (n.type !== "milestone_tier" || !n.chain) continue;
      const list = byChain.get(n.chain) ?? [];
      list.push(n);
      byChain.set(n.chain, list);
    }
    for (const peers of byChain.values()) {
      const sorted = [...peers].sort((a, b) => (a.tier ?? 0) - (b.tier ?? 0));
      sorted.forEach((peer, index) => {
        stackMeta.set(peer.id, { index, size: sorted.length });
      });
    }

    return visibleNodes.map((n) => {
      const nodeState = state[n.id];
      const meta = stackMeta.get(n.id);
      const selected = selectedNodeId === n.id;
      const zIndex = selected ? 1000 : (n.position.z ?? meta?.index ?? 0) + 1;

      return {
        id: n.id,
        type: n.type,
        position: { x: n.position.x, y: n.position.y },
        zIndex,
        draggable: false,
        selectable: true,
        data: {
          node: n,
          status: nodeState?.status ?? "locked",
          selected,
          progress: nodeState?.progress,
          stackIndex: meta?.index,
          stackSize: meta?.size,
        },
      };
    });
  }, [visibleNodes, state, selectedNodeId]);

  const edges: Edge[] = useMemo(() => {
    return layout.edges
      .filter((e) => visibleIds.has(e.from) && visibleIds.has(e.to))
      .map((e) => {
        const isHyper = isHyperedgeId(e.id);
        const isAccelerates = e.type === "accelerates";

        let strokeDasharray: string | undefined;
        if (isAccelerates) strokeDasharray = "6 4";
        else if (isHyper) strokeDasharray = "2 3";

        return {
          id: e.id,
          source: e.from,
          target: e.to,
          animated: isAccelerates,
          label: isHyper ? "requires all" : undefined,
          style: {
            strokeDasharray,
            stroke: isHyper ? "#a1a1aa" : isAccelerates ? "#8b5cf6" : "#71717a",
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 16,
            height: 16,
          },
        };
      });
  }, [layout.edges, visibleIds]);

  return (
    <div className="h-full w-full min-w-0">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        fitView
        fitViewOptions={FIT_VIEW_OPTIONS}
        minZoom={0.3}
        maxZoom={1.5}
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        onNodeMouseEnter={(_, node) => onNodeHover?.(node.id)}
        onNodeMouseLeave={() => onNodeHover?.(null)}
        proOptions={{ hideAttribution: true }}
        style={{ width: "100%", height: "100%" }}
      >
        <FitViewWhenSized filterKey={filterKey} />
        <Background gap={16} size={1} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable className="!bg-zinc-50" />
      </ReactFlow>
    </div>
  );
}

export function ReactFlowRenderer(props: SkillTreeRendererProps) {
  return <ReactFlowCanvas {...props} />;
}
