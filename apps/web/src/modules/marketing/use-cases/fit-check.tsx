"use client";

import { RotateCcw } from "lucide-react";
import { useState } from "react";

import { cn } from "@akashic-labs/ui";

import { fitQuestions } from "~/modules/marketing/content/use-cases";
import { HudFrame, HudLabel } from "~/modules/marketing/ui/hud";

type Answers = Partial<Record<(typeof fitQuestions)[number]["id"], boolean>>;

const verdicts = {
  strong: {
    label: "Built for accumulation",
    tone: "text-hud-cyan",
    body: "You want long-lived peers that inherit judgement, on your own machine. That is exactly the bet Aurora makes. Start with memory and recall, then add the bus when a second peer joins.",
  },
  partial: {
    label: "Worth a try",
    tone: "text-hud-gold",
    body: "Aurora will help with the memory, but the bus, trust ladder and coordination pay off when the same peers keep working. Start with one agent, then add a second and see whether the record earns its keep.",
  },
  weak: {
    label: "Probably not yet",
    tone: "text-white/70",
    body: "If your work is a series of one-off jobs for disposable workers, a queue of fresh agents is a better fit. Aurora is built for peers that stay and accumulate judgement. It is also local-first, so a hosted service with an SLA is not what it is.",
  },
} as const;

export const FitCheck = () => {
  const [answers, setAnswers] = useState<Answers>({});
  const answered = Object.keys(answers).length;
  const done = answered === fitQuestions.length;
  const score = fitQuestions.reduce((total, question) => {
    const answer = answers[question.id];
    if (answer === undefined) return total;
    return total + (answer ? question.yes : question.no);
  }, 0);
  const verdict =
    score >= 4
      ? verdicts.strong
      : score >= 1
        ? verdicts.partial
        : verdicts.weak;

  return (
    <HudFrame data-testid="fit-check" className="[--hud-cut:18px]">
      <div className="grid gap-px lg:grid-cols-[1.4fr_1fr]">
        <div className="flex flex-col gap-2 p-6 sm:p-8">
          <div className="mb-3 flex items-center justify-between">
            <HudLabel>Fit check</HudLabel>
            <span className="font-hud text-mk-faint text-[12px] tabular-nums">
              {answered} / {fitQuestions.length}
            </span>
          </div>
          {fitQuestions.map((question) => (
            <div
              key={question.id}
              className="flex flex-col gap-3 border-t border-white/[0.06] py-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <span className="text-[15.5px] text-white/90">
                {question.question}
              </span>
              <div className="flex shrink-0 gap-1.5">
                {[true, false].map((value) => (
                  <button
                    key={String(value)}
                    type="button"
                    aria-pressed={answers[question.id] === value}
                    onClick={() =>
                      setAnswers((current) => ({
                        ...current,
                        [question.id]: value,
                      }))
                    }
                    className={cn(
                      "font-hud h-8 w-14 text-[11px] font-semibold tracking-[0.14em] uppercase transition-colors [clip-path:polygon(6px_0,100%_0,calc(100%-6px)_100%,0_100%)]",
                      answers[question.id] === value
                        ? value
                          ? "bg-hud-cyan text-hud-ink"
                          : "bg-hud-gold text-hud-ink"
                        : "bg-white/[0.06] text-white/60 hover:bg-white/[0.12]",
                    )}
                  >
                    {value ? "Yes" : "No"}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="flex flex-col justify-between gap-6 border-white/[0.06] bg-black/30 p-6 max-lg:border-t sm:p-8 lg:border-l">
          {done ? (
            <div className="flex flex-col gap-4" aria-live="polite">
              <HudLabel tone="muted">Verdict</HudLabel>
              <span
                data-testid="fit-verdict"
                className={cn(
                  "font-hud text-3xl font-semibold uppercase",
                  verdict.tone,
                )}
              >
                {verdict.label}
              </span>
              <p className="text-[15px] leading-relaxed text-white/80">
                {verdict.body}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <HudLabel tone="muted">Verdict</HudLabel>
              <span className="font-hud text-3xl font-semibold text-white/45 uppercase">
                Answer all five
              </span>
              <p className="text-mk-faint text-[14.5px] leading-relaxed">
                Five questions, no email. We will tell you if Aurora is not the
                right tool.
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={() => setAnswers({})}
            className="text-mk-faint inline-flex w-fit items-center gap-1.5 text-[13px] hover:text-white"
          >
            <RotateCcw className="size-3.5" /> Start over
          </button>
        </div>
      </div>
    </HudFrame>
  );
};
