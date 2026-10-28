"use client";

import { Handle, Position } from "@xyflow/react";

import type { NodeStatus, PositionedNode } from "../../core/types";
import type { NodeProps } from "@xyflow/react";

interface ActionNodeData {
  node: PositionedNode;
  status: NodeStatus;
  selected?: boolean;
}

const statusClasses: Record<NodeStatus, string> = {
  locked: "border-zinc-400 bg-zinc-100 text-zinc-500 opacity-50",
  available: "border-violet-500 bg-white text-zinc-900",
  in_progress: "border-violet-500 bg-white text-zinc-900",
  achieved: "border-violet-500 bg-white text-zinc-900",
};

export function ActionNode({ data }: NodeProps & { data: ActionNodeData }) {
  const { node, status, selected } = data;
  const selectedRing = selected ? "ring-2 ring-offset-2 ring-violet-600" : "";

  return (
    <div
      className={`w-[160px] rounded-full border-2 px-3 py-2 shadow-sm ${statusClasses[status]} ${selectedRing}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-zinc-400" />
      <div className="truncate text-center text-[12px] leading-tight font-medium">
        {node.title}
      </div>
      {node.kind && (
        <div className="mt-0.5 text-center text-[10px] text-zinc-500 capitalize">
          {node.kind}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-zinc-400"
      />
    </div>
  );
}
