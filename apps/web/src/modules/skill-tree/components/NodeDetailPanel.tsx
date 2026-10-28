"use client";

import { Button } from "@akashic-labs/ui-web/button";

import { getAcceleratesTargets } from "../core/state-engine";
import { MilestoneMedia } from "../media/MilestoneMedia";

import type { SkillGraph, SkillNode, StateMap } from "../core/types";

interface NodeDetailPanelProps {
  graph: SkillGraph;
  state: StateMap;
  nodeId: string | null;
  onMarkAchieved: (nodeId: string) => void;
  onMarkInProgress: (nodeId: string) => void;
  onClose: () => void;
}

function findNode(graph: SkillGraph, nodeId: string): SkillNode | undefined {
  return graph.nodes.find((n) => n.id === nodeId);
}

export function NodeDetailPanel({
  graph,
  state,
  nodeId,
  onMarkAchieved,
  onMarkInProgress,
  onClose,
}: NodeDetailPanelProps) {
  if (!nodeId) {
    return (
      <aside className="flex w-80 max-w-sm shrink-0 flex-col border-l border-zinc-200 bg-white p-4 text-sm text-zinc-500">
        <p>Select a node to view details.</p>
      </aside>
    );
  }

  const node = findNode(graph, nodeId);
  if (!node) {
    return (
      <aside className="flex w-80 max-w-sm shrink-0 flex-col border-l border-zinc-200 bg-white p-4">
        <p className="text-sm text-zinc-500">Node not found.</p>
      </aside>
    );
  }

  const nodeState = state[nodeId];
  const status = nodeState?.status ?? "locked";
  const isLocked = status === "locked";
  const isMilestone = node.type === "milestone_tier";

  const accelerateTargets = isMilestone
    ? []
    : getAcceleratesTargets(graph, node.id).map((edge) => {
        const target = findNode(graph, edge.to);
        return {
          id: edge.to,
          title: target?.title ?? edge.to,
          weight: edge.weight,
        };
      });

  return (
    <aside className="flex w-80 max-w-sm shrink-0 flex-col gap-4 border-l border-zinc-200 bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium tracking-wide text-zinc-500 uppercase">
            {isMilestone ? "Milestone tier" : "Action"}
          </p>
          <h2 className="mt-1 text-lg font-semibold text-zinc-900">
            {node.title}
          </h2>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>

      {isMilestone && node.media && (
        <MilestoneMedia media={node.media} title={node.title} />
      )}

      <div className="rounded-md bg-zinc-50 px-3 py-2 text-sm">
        <span className="text-zinc-500">Status: </span>
        <span className="font-medium capitalize">
          {status.replace("_", " ")}
        </span>
        {nodeState?.progress != null && status === "in_progress" && (
          <span className="text-zinc-500">
            {" "}
            ({Math.round(nodeState.progress * 100)}%)
          </span>
        )}
      </div>

      {isMilestone ? (
        <dl className="space-y-3 text-sm">
          {node.chain && (
            <div>
              <dt className="text-zinc-500">Chain</dt>
              <dd className="font-medium text-zinc-800">{node.chain}</dd>
            </div>
          )}
          {node.tier != null && (
            <div>
              <dt className="text-zinc-500">Tier</dt>
              <dd className="font-medium text-zinc-800">{node.tier}</dd>
            </div>
          )}
          {node.rubric && (
            <div>
              <dt className="text-zinc-500">Rubric</dt>
              <dd className="text-zinc-800">{node.rubric}</dd>
            </div>
          )}
        </dl>
      ) : (
        <dl className="space-y-3 text-sm">
          {node.kind && (
            <div>
              <dt className="text-zinc-500">Kind</dt>
              <dd className="font-medium text-zinc-800 capitalize">
                {node.kind}
              </dd>
            </div>
          )}
          {node.cost && (
            <div>
              <dt className="text-zinc-500">Cost</dt>
              <dd className="text-zinc-800">
                {[
                  node.cost.time_min != null
                    ? `${node.cost.time_min} min`
                    : null,
                  node.cost.frequency,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </dd>
            </div>
          )}
          {node.evidence && (
            <div>
              <dt className="text-zinc-500">Evidence</dt>
              <dd className="font-medium text-zinc-800 capitalize">
                {node.evidence}
              </dd>
            </div>
          )}
          {accelerateTargets.length > 0 && (
            <div>
              <dt className="mb-1 text-zinc-500">Accelerates</dt>
              <dd>
                <ul className="list-inside list-disc space-y-1 text-zinc-800">
                  {accelerateTargets.map((t) => (
                    <li key={t.id}>
                      {t.title}
                      {t.weight != null ? ` (w=${t.weight})` : ""}
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
          )}
        </dl>
      )}

      {isMilestone && (
        <div className="mt-auto flex flex-col gap-2 pt-4">
          <Button
            variant="outline"
            disabled={isLocked || status === "achieved"}
            onClick={() => onMarkInProgress(node.id)}
          >
            Mark in progress
          </Button>
          <Button
            disabled={isLocked || status === "achieved"}
            onClick={() => onMarkAchieved(node.id)}
          >
            Mark achieved
          </Button>
        </div>
      )}

      {!isMilestone && isLocked && (
        <p className="mt-auto text-xs text-zinc-500">
          Locked until a connected milestone becomes available.
        </p>
      )}
    </aside>
  );
}
