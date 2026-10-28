import type { LayoutResult, SkillGraph } from "./types";

/** A LayoutEngine's only job is graph → positions. No DOM, no rendering libs. */
export interface LayoutEngine {
  readonly name: string;
  layout(
    graph: SkillGraph,
    options?: Record<string, unknown>,
  ): Promise<LayoutResult> | LayoutResult;
}
