"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  evaluateState,
  extractUserOverrides,
  markAchieved,
  markInProgress,
} from "../core/state-engine";

import type { SkillGraph, StateMap } from "../core/types";

const STORAGE_PREFIX = "skill-tree-state:";

function storageKey(graphId: string): string {
  return `${STORAGE_PREFIX}${graphId}`;
}

function loadOverrides(graphId: string): StateMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(storageKey(graphId));
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? (parsed as StateMap) : {};
  } catch {
    return {};
  }
}

function saveOverrides(graphId: string, overrides: StateMap): void {
  if (typeof window === "undefined") return;
  try {
    const key = storageKey(graphId);
    if (Object.keys(overrides).length === 0) {
      window.localStorage.removeItem(key);
      return;
    }
    window.localStorage.setItem(key, JSON.stringify(overrides));
  } catch {
    // ignore quota / private mode
  }
}

export function useSkillTreeState(graph: SkillGraph) {
  const [userState, setUserState] = useState<StateMap>({});
  const [hydrated, setHydrated] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setUserState(loadOverrides(graph.id));
    setHydrated(true);
  }, [graph.id]);

  useEffect(() => {
    if (!hydrated) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      saveOverrides(graph.id, extractUserOverrides(userState));
    }, 300);
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
  }, [userState, graph.id, hydrated]);

  const state = useMemo(
    () => evaluateState(graph, userState),
    [graph, userState],
  );

  const markNodeAchieved = useCallback(
    (nodeId: string) => {
      setUserState((prev) =>
        extractUserOverrides(markAchieved(graph, prev, nodeId)),
      );
    },
    [graph],
  );

  const markNodeInProgress = useCallback(
    (nodeId: string, progress?: number) => {
      setUserState((prev) =>
        extractUserOverrides(markInProgress(graph, prev, nodeId, progress)),
      );
    },
    [graph],
  );

  const resetState = useCallback(() => {
    setUserState({});
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(storageKey(graph.id));
    }
  }, [graph.id]);

  return {
    state,
    userState,
    hydrated,
    markNodeAchieved,
    markNodeInProgress,
    resetState,
  };
}
