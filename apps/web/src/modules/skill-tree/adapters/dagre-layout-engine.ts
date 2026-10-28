import dagre from "dagre";

import type { LayoutEngine } from "../core/layout-engine";
import type {
  LayoutResult,
  PositionedNode,
  SkillEdge,
  SkillGraph,
  SkillHyperedge,
  SkillNode,
} from "../core/types";

const MILESTONE_WIDTH = 180;
/** Card with 3:2 media strip (~120px) + title row */
const MILESTONE_HEIGHT = 172;
const ACTION_WIDTH = 160;
const ACTION_HEIGHT = 60;

/** Stagger between tiers in the same chain — readable card-stack peek. */
const STACK_OFFSET_X = 10;
const STACK_OFFSET_Y = 28;

/**
 * Expand hyperedges into synthetic binary edges for layout ranking only.
 * Does not mutate the content graph.
 */
function expandHyperedgesForLayout(hyperedges: SkillHyperedge[]): SkillEdge[] {
  const synthetic: SkillEdge[] = [];
  for (const hyper of hyperedges) {
    if (hyper.type !== "prerequisite") continue;
    for (const tail of hyper.tails) {
      for (const head of hyper.heads) {
        synthetic.push({
          id: `layout:${hyper.id}:${tail}->${head}`,
          from: tail,
          to: head,
          type: "prerequisite",
        });
      }
    }
  }
  return synthetic;
}

/**
 * Edges used for visual rendering of hyperedge relationships
 * (one dotted edge per tail→head pair).
 */
export function hyperedgeRenderEdges(
  hyperedges: SkillHyperedge[],
): SkillEdge[] {
  const edges: SkillEdge[] = [];
  for (const hyper of hyperedges) {
    for (const tail of hyper.tails) {
      for (const head of hyper.heads) {
        edges.push({
          id: `hyper:${hyper.id}:${tail}->${head}`,
          from: tail,
          to: head,
          type: "prerequisite",
        });
      }
    }
  }
  return edges;
}

function groupChains(nodes: SkillNode[]): Map<string, SkillNode[]> {
  const byChain = new Map<string, SkillNode[]>();
  for (const node of nodes) {
    if (node.type !== "milestone_tier" || !node.chain || node.tier == null) {
      continue;
    }
    const list = byChain.get(node.chain) ?? [];
    list.push(node);
    byChain.set(node.chain, list);
  }
  for (const [chain, peers] of byChain) {
    byChain.set(
      chain,
      [...peers].sort((a, b) => (a.tier ?? 0) - (b.tier ?? 0)),
    );
  }
  return byChain;
}

/** Map every node id → layout representative (lowest tier for chains). */
function buildRepresentatives(
  nodes: SkillNode[],
  byChain: Map<string, SkillNode[]>,
): Map<string, string> {
  const rep = new Map<string, string>();
  for (const node of nodes) {
    if (node.chain) {
      const peers = byChain.get(node.chain);
      rep.set(node.id, peers?.[0]?.id ?? node.id);
    } else {
      rep.set(node.id, node.id);
    }
  }
  return rep;
}

export class DagreLayoutEngine implements LayoutEngine {
  readonly name = "dagre";

  layout(graph: SkillGraph): LayoutResult {
    const byChain = groupChains(graph.nodes);
    const representativeOf = buildRepresentatives(graph.nodes, byChain);
    const representativeIds = new Set(representativeOf.values());

    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: "TB", nodesep: 64, ranksep: 100 });
    g.setDefaultEdgeLabel(() => ({}));

    // One dagre node per chain (sized for the full stack) + each action.
    for (const nodeId of representativeIds) {
      const node = graph.nodes.find((n) => n.id === nodeId);
      if (!node) continue;

      if (node.type === "action") {
        g.setNode(nodeId, { width: ACTION_WIDTH, height: ACTION_HEIGHT });
        continue;
      }

      const peers = node.chain ? byChain.get(node.chain) : [node];
      const stackCount = Math.max(1, peers?.length ?? 1);
      g.setNode(nodeId, {
        width: MILESTONE_WIDTH + (stackCount - 1) * STACK_OFFSET_X,
        height: MILESTONE_HEIGHT + (stackCount - 1) * STACK_OFFSET_Y,
      });
    }

    const hyperedges = graph.hyperedges ?? [];
    const rankingEdges: SkillEdge[] = [
      ...graph.edges.filter((e) => e.type === "prerequisite"),
      ...expandHyperedgesForLayout(hyperedges),
    ];

    // Rank only between chain stacks / actions — never within a chain.
    for (const edge of rankingEdges) {
      const from = representativeOf.get(edge.from) ?? edge.from;
      const to = representativeOf.get(edge.to) ?? edge.to;
      if (from === to) continue;
      if (g.hasNode(from) && g.hasNode(to) && !g.hasEdge(from, to)) {
        g.setEdge(from, to);
      }
    }

    dagre.layout(g);

    const positioned: PositionedNode[] = [];

    for (const node of graph.nodes) {
      if (node.type === "action") {
        const pos = nodeCenter(g, node.id);
        positioned.push({
          ...node,
          position: {
            x: pos.x - ACTION_WIDTH / 2,
            y: pos.y - ACTION_HEIGHT / 2,
          },
        });
        continue;
      }

      if (node.chain) {
        // Placed below with the rest of the chain.
        continue;
      }

      // Milestone without a chain — treat as a single card.
      const pos = nodeCenter(g, node.id);
      positioned.push({
        ...node,
        position: {
          x: pos.x - MILESTONE_WIDTH / 2,
          y: pos.y - MILESTONE_HEIGHT / 2,
          z: 1,
        },
      });
    }

    for (const peers of byChain.values()) {
      const repId = peers[0]?.id;
      if (!repId) continue;
      const pos = nodeCenter(g, repId);
      const stackCount = peers.length;
      const stackWidth = MILESTONE_WIDTH + (stackCount - 1) * STACK_OFFSET_X;
      const stackHeight = MILESTONE_HEIGHT + (stackCount - 1) * STACK_OFFSET_Y;
      const originX = pos.x - stackWidth / 2;
      const originY = pos.y - stackHeight / 2;

      peers.forEach((peer, index) => {
        positioned.push({
          ...peer,
          position: {
            x: originX + index * STACK_OFFSET_X,
            y: originY + index * STACK_OFFSET_Y,
            // Higher tiers paint on top of the stack.
            z: index + 1,
          },
        });
      });
    }

    const width =
      Math.max(
        0,
        ...positioned.map(
          (n) =>
            n.position.x +
            (n.type === "action" ? ACTION_WIDTH : MILESTONE_WIDTH),
        ),
      ) + 40;
    const height =
      Math.max(
        0,
        ...positioned.map(
          (n) =>
            n.position.y +
            (n.type === "action" ? ACTION_HEIGHT : MILESTONE_HEIGHT),
        ),
      ) + 40;

    const chainOf = new Map<string, string>();
    for (const node of graph.nodes) {
      if (node.chain) {
        chainOf.set(node.id, node.chain);
      }
    }

    // Hide redundant intra-chain prerequisite edges — the stack implies order.
    const contentEdges = graph.edges.filter((e) => {
      if (e.type !== "prerequisite") return true;
      const fromChain = chainOf.get(e.from);
      const toChain = chainOf.get(e.to);
      return !(fromChain && toChain && fromChain === toChain);
    });

    const renderEdges: SkillEdge[] = [
      ...contentEdges,
      ...hyperedgeRenderEdges(hyperedges),
    ];

    return {
      nodes: positioned,
      edges: renderEdges,
      hyperedges,
      bounds: { width, height },
    };
  }
}

/** dagre types `node()` as always present, but it returns undefined for an id it never laid out. */
function nodeCenter(
  g: dagre.graphlib.Graph,
  id: string,
): { x: number; y: number } {
  return g.hasNode(id) ? g.node(id) : { x: 0, y: 0 };
}
