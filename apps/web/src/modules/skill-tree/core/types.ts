// Core graph model. Nothing in this file knows about react-flow, dagre,
// react-three-fiber, or any other library — that's the point.

export type NodeKind = "milestone_tier" | "action";

export type ActionKind =
  | "routine"
  | "drill"
  | "environment"
  | "equipment"
  | "resource";

export type EdgeKind =
  | "prerequisite"
  | "accelerates"
  | "alternative_to"
  | "synergizes_with"
  | "unlocks";

export type HyperedgeKind = "prerequisite" | "co_requisite" | "conflict";

export type NodeStatus = "locked" | "available" | "in_progress" | "achieved";

export interface SkillNodeMedia {
  /** Poster / still — always preferred as fallback */
  image: string;
  /** Optional demo clip; UI falls back to `image` on error or if omitted */
  video?: string;
  alt?: string;
}

export interface SkillNode {
  id: string;
  type: NodeKind;
  domain: string;
  title: string;
  /** milestone_tier only */
  chain?: string;
  tier?: number;
  rubric?: string;
  /** Demo visual for milestone tiers (and optionally actions later) */
  media?: SkillNodeMedia;
  /** action only */
  kind?: ActionKind;
  cost?: { time_min?: number; frequency?: string };
  evidence?: "strong" | "moderate" | "anecdotal";
}

export interface SkillEdge {
  id: string;
  from: string;
  to: string;
  type: EdgeKind;
  /** Efficacy/strength, primarily meaningful on "accelerates" edges */
  weight?: number;
}

export interface SkillHyperedge {
  id: string;
  type: HyperedgeKind;
  tails: string[];
  heads: string[];
}

export interface SkillGraph {
  id: string;
  domain: string;
  title: string;
  nodes: SkillNode[];
  edges: SkillEdge[];
  hyperedges?: SkillHyperedge[];
}

export interface NodeState {
  status: NodeStatus;
  achievedAt?: string;
  progress?: number;
}

export type StateMap = Record<string, NodeState>;

export interface Point {
  x: number;
  y: number;
  z?: number;
}

export interface PositionedNode extends SkillNode {
  position: Point;
}

export interface LayoutResult {
  nodes: PositionedNode[];
  edges: SkillEdge[];
  hyperedges: SkillHyperedge[];
  bounds: { width: number; height: number };
}
