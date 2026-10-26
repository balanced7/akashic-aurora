import { create } from "zustand";

import { type BusMessage, type Fidelity, type Status, isBookkeeping, msgKey } from "./bifrost";

/** The main conversation's namespace (the backend's BIFROST_NAMESPACE default). */
export const DEFAULT_ROOM = "bifrost";

/** Session buffer ceiling. The log renders a window over it; this only bounds memory. */
const MAX_MESSAGES = 5000;

type ConsoleState = {
  messages: BusMessage[];
  seen: Set<string>;
  bookkeeping: { count: number; last: string };
  ready: boolean;
  connected: boolean;
  status: Status | null;
  recipients: string[]; // ["all"] = broadcast
  fidelity: Fidelity;
  thread: string; // "" = everyone
  /** The bus namespace on screen; a room is a namespace (/api/channels). */
  room: string;

  ingest: (m: BusMessage) => void;
  setConnected: (v: boolean) => void;
  setStatus: (s: Status) => void;
  setRecipients: (ids: string[]) => void;
  toggleRecipient: (id: string, additive: boolean) => void;
  setFidelity: (f: Fidelity) => void;
  setThread: (peer: string) => void;
  setRoom: (ns: string) => void;
};

export const useConsole = create<ConsoleState>((set, get) => ({
  messages: [],
  seen: new Set(),
  bookkeeping: { count: 0, last: "" },
  ready: false,
  connected: false,
  status: null,
  recipients: ["all"],
  fidelity: "inform",
  thread: "",
  room: DEFAULT_ROOM,

  ingest: (m) => {
    if (m.kind === "_ready") return set({ ready: true });
    const { seen } = get();
    const key = msgKey(m);
    if (seen.has(key)) return;
    seen.add(key);
    if (isBookkeeping(m)) {
      const last = `${m.from ?? ""} ${m.kind ?? ""}`;
      return set((s) => ({ bookkeeping: { count: s.bookkeeping.count + 1, last } }));
    }
    set((s) => {
      const messages = [...s.messages, m];
      return { messages: messages.length > MAX_MESSAGES ? messages.slice(-MAX_MESSAGES) : messages };
    });
  },
  setConnected: (connected) => set({ connected }),
  setStatus: (status) => set({ status }),
  setRecipients: (ids) => set({ recipients: ids.length ? ids : ["all"] }),
  // Plain click toggles one seat; shift/ctrl/meta-click adds to a multi-select and never
  // collapses it to empty.
  toggleRecipient: (id, additive) =>
    set((s) => {
      if (id === "all") return { recipients: ["all"] };
      const cur = s.recipients.filter((x) => x !== "all");
      if (!additive) return { recipients: cur.length === 1 && cur[0] === id ? ["all"] : [id] };
      const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id];
      return { recipients: next.length ? next : s.recipients };
    }),
  setFidelity: (fidelity) => set({ fidelity }),
  setThread: (thread) => set(thread ? { thread, recipients: [thread] } : { thread }),
  // A new room is a new conversation: drop the old feed; the stream backfills the new one.
  setRoom: (room) =>
    set((s) =>
      room === s.room
        ? {}
        : { room, messages: [], seen: new Set(), bookkeeping: { count: 0, last: "" }, ready: false, thread: "", recipients: ["all"] },
    ),
}));

/** Who can be messaged: ACL-registered seats united with whoever is online, minus the operator. */
export function rosterOf(status: Status | null): string[] {
  if (!status) return [];
  const online = (status.agents ?? []).map((a) => a.agent).filter(Boolean);
  return [...new Set([...(status.known ?? []), ...online])].filter((a) => a !== "user");
}
