"use client";

import { RotateCcw } from "lucide-react";
import { useEffect } from "react";

import { SignalLost } from "~/modules/marketing/ui/signal-lost";

export default function MarketingError({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <SignalLost
      code="Fail soft"
      title={
        <>
          Something broke.
          <br />
          <span className="text-mk-muted">The rest still works.</span>
        </>
      }
      description="A helper part failed, so this page carries on with less and says what it lost. Try again, or head somewhere that works."
      command="aurora status"
      output="UNAVAILABLE · this view failed to render; nothing in the record was lost"
      action={
        <button
          type="button"
          onClick={reset}
          className="inline-flex h-12 items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.06] px-5 text-[15px] font-medium text-white hover:bg-white/[0.12]"
        >
          <RotateCcw className="size-4" /> Try again
        </button>
      }
    />
  );
}
