"use client";

import { useEffect } from "react";

import type { BusMessage } from "./bifrost";
import { type Floor, type Now, type World, useFleet } from "./fleet";
import { useConsole } from "./store";
import { single } from "./utils";

/** /api/now is the hot path (presence, pause, vitals); world and floor change slowly. */
const NOW_POLL_MS = 2000;
const WORLD_POLL_MS = 5000;

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(path, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return (await r.json()) as T;
}

/** Wire the console to the bus: one SSE stream for messages, polls for fleet state. */
export function useBus() {
  useEffect(() => {
    const { ingest, setConnected, setStatus } = useConsole.getState();
    const fleet = useFleet.getState();

    const es = new EventSource("/events");
    es.onopen = () => setConnected(true);
    es.onmessage = (e) => {
      try {
        ingest(JSON.parse(e.data) as BusMessage);
      } catch {
        // a malformed frame is dropped; the stream itself stays up
      }
    };
    // EventSource reconnects on its own; this only drives the connection dot.
    es.onerror = () => setConnected(false);

    let alive = true;
    const pollNow = single(async () => {
      try {
        const now = await getJson<Now>("/api/now");
        if (!alive) return;
        setStatus(now.status);
        fleet.set({ now });
      } catch {
        // backend restarting; the next tick retries
      }
    });
    // A failed world/floor poll must look BLIND, never like a stale healthy reading.
    const pollWorld = single(async () => {
      const [world, floor] = await Promise.all([
        getJson<World>("/api/world").catch(
          (): World => ({ ok: false, agents: [], bounds: "roster unavailable (poll failed): cannot say who is online" }),
        ),
        getJson<Floor>("/api/floor").catch(
          (): Floor => ({ ok: false, entries: [], legend: "floor unavailable (poll failed): cannot see the floor" }),
        ),
      ]);
      if (alive) fleet.set({ world, floor });
    });
    void pollNow();
    void pollWorld();
    const t1 = setInterval(pollNow, NOW_POLL_MS);
    const t2 = setInterval(pollWorld, WORLD_POLL_MS);

    return () => {
      alive = false;
      clearInterval(t1);
      clearInterval(t2);
      es.close();
    };
  }, []);
}
