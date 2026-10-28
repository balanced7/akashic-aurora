"use client";

import dynamic from "next/dynamic";

const SkillTreeApp = dynamic(
  () => import("./SkillTreeApp").then((m) => m.SkillTreeApp),
  {
    ssr: false,
    loading: () => (
      <div className="flex min-h-[600px] w-full min-w-0 items-center justify-center self-stretch text-sm text-zinc-500">
        Loading skill tree…
      </div>
    ),
  },
);

export function SkillTreeAppLoader() {
  return (
    <div className="flex w-full min-w-0 flex-1 flex-col self-stretch">
      <SkillTreeApp />
    </div>
  );
}
