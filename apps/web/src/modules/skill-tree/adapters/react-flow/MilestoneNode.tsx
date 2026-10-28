"use client";

import { Handle, Position } from "@xyflow/react";

import { MilestoneMedia } from "../../media/MilestoneMedia";

import type { NodeStatus, PositionedNode } from "../../core/types";
import type { NodeProps } from "@xyflow/react";

interface MilestoneNodeData {
  node: PositionedNode;
  status: NodeStatus;
  selected?: boolean;
  progress?: number;
  stackIndex?: number;
  stackSize?: number;
}

const statusClasses: Record<NodeStatus, string> = {
  locked: "border-zinc-400 bg-zinc-100 text-zinc-500 opacity-60",
  available: "border-sky-500 bg-white text-zinc-900",
  in_progress: "border-amber-500 bg-amber-50 text-zinc-900",
  achieved: "border-emerald-600 bg-emerald-50 text-zinc-900",
};

export function MilestoneNode({
  data,
}: NodeProps & { data: MilestoneNodeData }) {
  const {
    node,
    status,
    selected,
    progress,
    stackIndex = 0,
    stackSize = 1,
  } = data;
  const selectedRing = selected ? "ring-2 ring-offset-2 ring-sky-600" : "";
  const isStacked = stackSize > 1;
  const isTopCard = stackIndex === stackSize - 1;

  return (
    <div
      className={`relative w-[180px] overflow-hidden rounded-lg border-2 ${statusClasses[status]} ${selectedRing} ${
        isStacked ? "shadow-md" : "shadow-sm"
      } ${isTopCard && isStacked ? "shadow-lg" : ""}`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-zinc-400"
        style={{ opacity: isStacked && stackIndex > 0 ? 0.35 : 1 }}
      />
      {node.media && (
        <MilestoneMedia
          media={node.media}
          title={node.title}
          compact
          className="rounded-none border-b border-black/5"
        />
      )}
      <div className="px-3 py-2">
        <div className="flex items-start justify-between gap-1">
          <div className="min-w-0">
            <div className="truncate text-[13px] leading-tight font-medium">
              {node.title}
            </div>
            {node.chain && node.tier != null && (
              <div className="mt-0.5 text-[10px] text-zinc-500">
                Tier {node.tier}
                {isStacked ? ` · ${stackIndex + 1}/${stackSize}` : ""}
              </div>
            )}
          </div>
          {status === "achieved" && (
            <span className="shrink-0 text-sm text-emerald-600" aria-hidden>
              ✓
            </span>
          )}
        </div>
        {status === "in_progress" && typeof progress === "number" && (
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-amber-200">
            <div
              className="h-full rounded-full bg-amber-500"
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-zinc-400"
        style={{ opacity: isStacked && !isTopCard ? 0.35 : 1 }}
      />
    </div>
  );
}
