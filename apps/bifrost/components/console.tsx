"use client";

import { useEffect } from "react";

import { ActivityStrip } from "~/components/activity-strip";
import { AuroraBackground } from "~/components/aurora";
import { PauseBanner, RoomBanner, ThreadBanner } from "~/components/banners";
import { Composer } from "~/components/composer";
import { EpisodeBanner, useEpisodePoll } from "~/components/episode";
import { Header } from "~/components/header";
import { MessageLog } from "~/components/message-log";
import { Rail } from "~/components/rail";
import { usePrefs } from "~/lib/prefs";
import { useConsole } from "~/lib/store";
import { useBus } from "~/lib/use-bus";

export function Console() {
  useBus();
  useEffect(() => void usePrefs.persist.rehydrate(), []);
  useEpisodePoll();
  const thread = useConsole((s) => s.thread);
  const room = useConsole((s) => s.room);
  return (
    <>
      <AuroraBackground />
      <main className="relative z-0 mx-auto flex h-dvh w-[min(1180px,96vw)] max-w-full flex-col xl:w-[min(1440px,96vw)] min-[1700px]:w-[min(1600px,92vw)]">
        <Header />
        <PauseBanner />
        <RoomBanner />
        <ThreadBanner />
        <EpisodeBanner />
        {/* keyed on room and thread so switching views resets the history window */}
        <div className="flex min-h-0 flex-1">
          <div className="flex min-w-0 flex-1 flex-col">
            <MessageLog key={`${room}/${thread}`} />
          </div>
          <Rail />
        </div>
        <ActivityStrip />
        <Composer />
      </main>
    </>
  );
}
