"use client";

import { useEffect } from "react";

import type { BusMessage, Status } from "./bifrost";
import { useConsole } from "./store";

const STATUS_POLL_MS = 1200;

/** Wire the console to the bus: one SSE stream for messages, a status poll for presence/pause. */
export function useBus() {
  useEffect(() => {
    const { ingest, setConnected, setStatus } = useConsole.getState();

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
    const poll = async () => {
      try {
        const r = await fetch("/status", { cache: "no-store" });
        if (r.ok && alive) setStatus((await r.json()) as Status);
      } catch {
        // backend restarting; the next tick retries
      }
    };
    void poll();
    const timer = setInterval(poll, STATUS_POLL_MS);

    return () => {
      alive = false;
      clearInterval(timer);
      es.close();
    };
  }, []);
}
