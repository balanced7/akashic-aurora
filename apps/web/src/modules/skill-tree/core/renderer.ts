import type { LayoutResult, NodeKind, StateMap } from "./types";
import type { ComponentType } from "react";

export interface SkillTreeRendererProps {
  layout: LayoutResult;
  state: StateMap;
  selectedNodeId?: string | null;
  onNodeClick?: (nodeId: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
  /** When set, only these node kinds are drawn (edges require both ends). */
  visibleNodeKinds?: ReadonlySet<NodeKind>;
}

export type SkillTreeRenderer = ComponentType<SkillTreeRendererProps>;
