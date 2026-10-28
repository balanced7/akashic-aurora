import type {
  SkillEdge,
  SkillGraph,
  SkillHyperedge,
  SkillNode,
  StateMap,
} from "./types";

function isAchieved(state: StateMap, nodeId: string): boolean {
  return state[nodeId]?.status === "achieved";
}

function chainPeers(graph: SkillGraph, node: SkillNode): SkillNode[] {
  if (!node.chain || node.tier == null) return [];
  return graph.nodes
    .filter(
      (n) =>
        n.type === "milestone_tier" &&
        n.chain === node.chain &&
        typeof n.tier === "number",
    )
    .sort((a, b) => (a.tier ?? 0) - (b.tier ?? 0));
}

/** True when all hard gates for this milestone are satisfied by achievements. */
function milestonePrerequisitesMet(
  graph: SkillGraph,
  node: SkillNode,
  achieved: StateMap,
): boolean {
  // Implicit chain order: tier N+1 needs tier N achieved
  if (node.chain && node.tier != null && node.tier > 1) {
    const peers = chainPeers(graph, node);
    const previous = peers.find((p) => p.tier === node.tier! - 1);
    if (previous && !isAchieved(achieved, previous.id)) {
      return false;
    }
  }

  // Binary prerequisite edges into this node
  for (const edge of graph.edges) {
    if (edge.type === "prerequisite" && edge.to === node.id) {
      if (!isAchieved(achieved, edge.from)) {
        return false;
      }
    }
  }

  // Hyperedge prerequisites where this node is a head
  for (const hyper of graph.hyperedges ?? []) {
    if (hyper.type !== "prerequisite") continue;
    if (!hyper.heads.includes(node.id)) continue;
    if (!hyper.tails.every((tailId) => isAchieved(achieved, tailId))) {
      return false;
    }
  }

  return true;
}

function evaluateMilestone(
  graph: SkillGraph,
  node: SkillNode,
  userState: StateMap,
): StateMap[string] {
  const user = userState[node.id];

  // Achieved is sticky — never downgrade
  if (user?.status === "achieved") {
    return {
      status: "achieved",
      achievedAt: user.achievedAt,
      progress: user.progress,
    };
  }

  if (!milestonePrerequisitesMet(graph, node, userState)) {
    return { status: "locked" };
  }

  if (user?.status === "in_progress") {
    return {
      status: "in_progress",
      progress: user.progress,
    };
  }

  return { status: "available" };
}

function evaluateAction(
  graph: SkillGraph,
  node: SkillNode,
  milestoneState: StateMap,
): StateMap[string] {
  const accelerateTargets = graph.edges
    .filter((e) => e.type === "accelerates" && e.from === node.id)
    .map((e) => e.to);

  if (accelerateTargets.length === 0) {
    // No targets: treat as available (informational action)
    return { status: "available" };
  }

  const anyTargetUnlocked = accelerateTargets.some((targetId) => {
    const status = milestoneState[targetId]?.status;
    return status != null && status !== "locked";
  });

  return { status: anyTargetUnlocked ? "available" : "locked" };
}

/**
 * Pure evaluation: merge user overrides with derived lock/available logic.
 * Returns a new StateMap; does not mutate inputs.
 */
export function evaluateState(
  graph: SkillGraph,
  userState: StateMap,
): StateMap {
  const result: StateMap = {};

  const milestones = graph.nodes.filter((n) => n.type === "milestone_tier");
  const actions = graph.nodes.filter((n) => n.type === "action");

  for (const node of milestones) {
    result[node.id] = evaluateMilestone(graph, node, userState);
  }

  for (const node of actions) {
    result[node.id] = evaluateAction(graph, node, result);
  }

  return result;
}

export function markAchieved(
  graph: SkillGraph,
  userState: StateMap,
  nodeId: string,
): StateMap {
  const node = graph.nodes.find((n) => n.id === nodeId);
  if (node?.type !== "milestone_tier") {
    return evaluateState(graph, userState);
  }

  const evaluated = evaluateState(graph, userState);
  if (evaluated[nodeId]?.status === "locked") {
    return evaluated;
  }

  const nextUser: StateMap = {
    ...userState,
    [nodeId]: {
      status: "achieved",
      achievedAt: new Date().toISOString(),
    },
  };

  return evaluateState(graph, nextUser);
}

export function markInProgress(
  graph: SkillGraph,
  userState: StateMap,
  nodeId: string,
  progress?: number,
): StateMap {
  const node = graph.nodes.find((n) => n.id === nodeId);
  if (node?.type !== "milestone_tier") {
    return evaluateState(graph, userState);
  }

  const evaluated = evaluateState(graph, userState);
  if (evaluated[nodeId]?.status === "locked") {
    return evaluated;
  }

  const nextUser: StateMap = {
    ...userState,
    [nodeId]: {
      status: "in_progress",
      progress,
    },
  };

  return evaluateState(graph, nextUser);
}

/** User overrides only (achieved / in_progress) — what we persist. */
export function extractUserOverrides(state: StateMap): StateMap {
  const overrides: StateMap = {};
  for (const [id, nodeState] of Object.entries(state)) {
    if (nodeState.status === "achieved" || nodeState.status === "in_progress") {
      overrides[id] = { ...nodeState };
    }
  }
  return overrides;
}

/** Helpers exported for tests / consumers that need graph edge lookups. */
export function getAcceleratesTargets(
  graph: SkillGraph,
  actionId: string,
): SkillEdge[] {
  return graph.edges.filter(
    (e) => e.type === "accelerates" && e.from === actionId,
  );
}

export function getHyperedgesForNode(
  graph: SkillGraph,
  nodeId: string,
): SkillHyperedge[] {
  return (graph.hyperedges ?? []).filter(
    (h) => h.heads.includes(nodeId) || h.tails.includes(nodeId),
  );
}
