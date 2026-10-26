"use client";

import { ActivityStrip } from "~/components/activity-strip";
import { AuroraBackground } from "~/components/aurora";
import { PauseBanner, ThreadBanner } from "~/components/banners";
import { Composer } from "~/components/composer";
import { Header } from "~/components/header";
import { MessageLog } from "~/components/message-log";
import { useConsole } from "~/lib/store";
import { useBus } from "~/lib/use-bus";

export function Console() {
  useBus();
  const thread = useConsole((s) => s.thread);
  return (
    <>
      <AuroraBackground />
      <main className="relative z-0 mx-auto flex h-dvh w-[min(1180px,96vw)] max-w-full flex-col min-[1500px]:w-[min(1400px,92vw)]">
        <Header />
        <PauseBanner />
        <ThreadBanner />
        {/* keyed on the thread so switching views resets the history window */}
        <MessageLog key={thread} />
        <ActivityStrip />
        <Composer />
      </main>
    </>
  );
}
