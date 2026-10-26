"use client";

import { DoorOpen, Lock, Pause } from "lucide-react";

import { Button } from "~/components/ui/button";
import { displayName } from "~/lib/bifrost";
import { DEFAULT_ROOM, useConsole } from "~/lib/store";

export function PauseBanner() {
  const status = useConsole((s) => s.status);
  if (!status?.paused) return null;
  const { by, reason } = status.pause ?? {};
  return (
    <div role="alert" className="mx-3 mt-3 flex items-center gap-2 rounded-xl border border-amber/30 bg-amber/10 px-4 py-2 text-[13px] text-amber">
      <Pause className="size-4 shrink-0" />
      <span>
        Paused{by && <> by <b>{by}</b></>}
        {reason && <> ({reason})</>}. The agents are frozen. Type below to interject, then Resume.
      </span>
    </div>
  );
}

export function ThreadBanner() {
  const thread = useConsole((s) => s.thread);
  const residents = useConsole((s) => s.status?.residents);
  const setThread = useConsole((s) => s.setThread);
  if (!thread) return null;
  return (
    <div className="mx-5 mt-3 flex items-center justify-between gap-3 rounded-xl border border-accent/30 bg-accent/10 px-3.5 py-2 text-[13px] font-semibold">
      <span className="flex items-center gap-2">
        <Lock className="size-3.5 text-accent" />
        Talking with {displayName(thread, residents)}
      </span>
      <Button size="sm" onClick={() => setThread("")}>
        Show all
      </Button>
    </div>
  );
}

/** Shown while a side room is on screen, so a message is never sent to the wrong conversation. */
export function RoomBanner() {
  const room = useConsole((s) => s.room);
  const setRoom = useConsole((s) => s.setRoom);
  if (room === DEFAULT_ROOM) return null;
  return (
    <div className="mx-5 mt-3 flex items-center justify-between gap-3 rounded-xl border border-accent2/30 bg-accent2/10 px-3.5 py-2 text-[13px] font-semibold">
      <span className="flex items-center gap-2">
        <DoorOpen className="size-3.5 text-accent2" />
        In room {room}. Messages you send go to this room.
      </span>
      <Button size="sm" onClick={() => setRoom(DEFAULT_ROOM)}>
        Back to {DEFAULT_ROOM}
      </Button>
    </div>
  );
}
