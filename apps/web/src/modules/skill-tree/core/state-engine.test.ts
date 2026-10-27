import { describe, expect, it } from "vitest";

import { evaluateState, markAchieved, markInProgress } from "./state-engine";

import type { SkillGraph, StateMap } from "./types";

const graph: SkillGraph = {
  id: "test",
  domain: "test",
  title: "Test Graph",
  nodes: [
    {
      id: "fs.t1",
      type: "milestone_tier",
      domain: "test",
      chain: "fs",
      tier: 1,
      title: "Finger T1",
    },
    {
      id: "fs.t2",
      type: "milestone_tier",
      domain: "test",
      chain: "fs",
      tier: 2,
      title: "Finger T2",
    },
    {
      id: "fs.t3",
      type: "milestone_tier",
      domain: "test",
      chain: "fs",
      tier: 3,
      title: "Finger T3",
    },
    {
      id: "lp.t1",
      type: "milestone_tier",
      domain: "test",
      chain: "lp",
      tier: 1,
      title: "Leg T1",
    },
    {
      id: "lp.t2",
      type: "milestone_tier",
      domain: "test",
      chain: "lp",
      tier: 2,
      title: "Leg T2",
    },
    {
      id: "dyno.t1",
      type: "milestone_tier",
      domain: "test",
      chain: "dyno",
      tier: 1,
      title: "Dyno T1",
    },
    {
      id: "extra.t1",
      type: "milestone_tier",
      domain: "test",
      chain: "extra",
      tier: 1,
      title: "Extra gated by binary",
    },
    {
      id: "action.hang",
      type: "action",
      domain: "test",
      kind: "routine",
      title: "Hangboard",
    },
    {
      id: "action.locked_only",
      type: "action",
      domain: "test",
      kind: "drill",
      title: "Only accelerates locked",
    },
  ],
  edges: [
    {
      id: "e-bin",
      from: "fs.t2",
      to: "extra.t1",
      type: "prerequisite",
    },
    {
      id: "e-acc",
      from: "action.hang",
      to: "fs.t2",
      type: "accelerates",
      weight: 0.8,
    },
    {
      id: "e-acc-locked",
      from: "action.locked_only",
      to: "fs.t3",
      type: "accelerates",
      weight: 0.5,
    },
  ],
  hyperedges: [
    {
      id: "h-dyno",
      type: "prerequisite",
      tails: ["fs.t2", "lp.t2"],
      heads: ["dyno.t1"],
    },
  ],
};

describe("evaluateState — chain order", () => {
  it("keeps tier N+1 locked until tier N is achieved", () => {
    const state = evaluateState(graph, {});
    expect(state["fs.t1"]?.status).toBe("available");
    expect(state["fs.t2"]?.status).toBe("locked");
    expect(state["fs.t3"]?.status).toBe("locked");

    const afterT1 = markAchieved(graph, {}, "fs.t1");
    expect(afterT1["fs.t2"]?.status).toBe("available");
    expect(afterT1["fs.t3"]?.status).toBe("locked");

    const afterT2 = markAchieved(
      graph,
      { "fs.t1": { status: "achieved" } },
      "fs.t2",
    );
    expect(afterT2["fs.t3"]?.status).toBe("available");
  });
});

describe("evaluateState — binary prerequisite", () => {
  it("locks target until source is achieved", () => {
    const empty = evaluateState(graph, {});
    expect(empty["extra.t1"]?.status).toBe("locked");

    const withFsT2: StateMap = {
      "fs.t1": { status: "achieved" },
      "fs.t2": { status: "achieved" },
    };
    const unlocked = evaluateState(graph, withFsT2);
    expect(unlocked["extra.t1"]?.status).toBe("available");
  });
});

describe("evaluateState — hyperedge prerequisite", () => {
  it("keeps head locked until all tails are achieved", () => {
    const onlyFs: StateMap = {
      "fs.t1": { status: "achieved" },
      "fs.t2": { status: "achieved" },
      "lp.t1": { status: "achieved" },
    };
    expect(evaluateState(graph, onlyFs)["dyno.t1"]?.status).toBe("locked");

    const both: StateMap = {
      ...onlyFs,
      "lp.t2": { status: "achieved" },
    };
    expect(evaluateState(graph, both)["dyno.t1"]?.status).toBe("available");
  });
});

describe("evaluateState — achieved sticky", () => {
  it("never downgrades achieved on re-evaluation", () => {
    const user: StateMap = {
      "fs.t1": { status: "achieved", achievedAt: "2026-01-01T00:00:00.000Z" },
      "fs.t2": { status: "achieved", achievedAt: "2026-01-02T00:00:00.000Z" },
    };
    const state = evaluateState(graph, user);
    expect(state["fs.t1"]?.status).toBe("achieved");
    expect(state["fs.t2"]?.status).toBe("achieved");
    expect(state["fs.t1"]?.achievedAt).toBe("2026-01-01T00:00:00.000Z");
  });
});

describe("evaluateState — action availability", () => {
  it("makes action available when any accelerate target is unlocked", () => {
    const empty = evaluateState(graph, {});
    // fs.t2 is locked → hang action locked; fs.t3 locked → locked_only locked
    expect(empty["action.hang"]?.status).toBe("locked");
    expect(empty["action.locked_only"]?.status).toBe("locked");

    const afterT1 = markAchieved(graph, {}, "fs.t1");
    // fs.t2 now available → hang available; fs.t3 still locked
    expect(afterT1["action.hang"]?.status).toBe("available");
    expect(afterT1["action.locked_only"]?.status).toBe("locked");
  });

  it("never marks actions as achieved", () => {
    const state = evaluateState(graph, {
      "action.hang": { status: "achieved" },
    });
    expect(state["action.hang"]?.status).not.toBe("achieved");
  });
});

describe("markInProgress", () => {
  it("sets in_progress on available milestones", () => {
    const state = markInProgress(graph, {}, "fs.t1", 0.4);
    expect(state["fs.t1"]?.status).toBe("in_progress");
    expect(state["fs.t1"]?.progress).toBe(0.4);
  });

  it("does not unlock prerequisites via in_progress", () => {
    const state = markInProgress(graph, {}, "fs.t1", 0.5);
    expect(state["fs.t2"]?.status).toBe("locked");
  });
});
