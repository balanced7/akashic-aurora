"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { cn } from "@akashic-labs/ui";

import { loopSteps } from "~/modules/marketing/content/aurora";
import { Terminal } from "~/modules/marketing/ui/terminal";

export const LoopTabs = () => {
  const [activeId, setActiveId] = useState(loopSteps[0]?.id ?? "boot");
  const active = loopSteps.find((step) => step.id === activeId) ?? loopSteps[0];
  if (!active) return null;

  return (
    <div
      data-testid="loop-tabs"
      className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-10"
    >
      <div
        role="tablist"
        aria-label="The Aurora loop"
        className="flex flex-col gap-1"
      >
        {loopSteps.map((step, index) => {
          const isActive = step.id === activeId;
          return (
            <button
              key={step.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`loop-panel-${step.id}`}
              onClick={() => setActiveId(step.id)}
              className={cn(
                "group relative flex gap-4 rounded-2xl border p-4 text-left transition-colors sm:p-5",
                isActive
                  ? "border-white/[0.1] bg-white/[0.04]"
                  : "border-transparent hover:bg-white/[0.02]",
              )}
            >
              <span
                className={cn(
                  "font-hud mt-0.5 text-[13px] font-semibold tabular-nums transition-colors",
                  isActive ? "text-hud-gold" : "text-white/50",
                )}
              >
                0{index + 1}
              </span>
              <span className="flex flex-col gap-1">
                <span
                  className={cn(
                    "text-[17px] font-medium",
                    isActive ? "text-white" : "text-white/60",
                  )}
                >
                  {step.verb}
                  <span className="text-mk-faint font-normal">
                    {" "}
                    · {step.title}
                  </span>
                </span>
                <AnimatePresence initial={false}>
                  {isActive && (
                    <motion.span
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="text-mk-muted overflow-hidden text-[15px] leading-relaxed"
                    >
                      {step.body}
                    </motion.span>
                  )}
                </AnimatePresence>
              </span>
            </button>
          );
        })}
      </div>

      <div className="lg:sticky lg:top-28 lg:self-start">
        <AnimatePresence mode="wait">
          <motion.div
            key={active.id}
            id={`loop-panel-${active.id}`}
            role="tabpanel"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
          >
            <Terminal
              title={`aurora · ${active.verb.toLowerCase()}`}
              lines={[{ kind: "cmd", text: active.command }, ...active.output]}
              caret
            />
            <p className="text-mk-faint mt-3 text-[12.5px]">
              Output captured from a real Aurora sandbox run, or quoted from the
              docs.
            </p>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};
