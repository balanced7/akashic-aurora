"use client";

import { Settings } from "lucide-react";
import type { ReactNode } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import { Section, Sheet, SheetContent, SheetTrigger } from "~/components/ui/sheet";
import { type Status } from "~/lib/bifrost";
import { usePrefs } from "~/lib/prefs";
import { useConsole } from "~/lib/store";
import { cn, postJson } from "~/lib/utils";

const NARRATION = {
  off: "silent",
  key: "decision points only",
  full: "stream all reasoning",
} as const;
type Narration = keyof typeof NARRATION;

/** Presentation choices for this browser, plus the one fleet-wide dial: claude's narration. */
export function SettingsPanel() {
  const p = usePrefs();
  const narration = useConsole((s) => s.status?.narration) as Narration | undefined;

  async function setNarration(level: Narration) {
    try {
      const r = await postJson<{ ok?: boolean; error?: string }>("/narration", { level });
      if (!r.ok) throw new Error(r.error);
      // reflect it now rather than on the next status poll
      const s = useConsole.getState().status;
      if (s) useConsole.getState().setStatus({ ...s, narration: level } satisfies Status);
      toast.success(`Narration: ${level}`);
    } catch {
      toast.error("Could not set narration. Is the bus offline?");
    }
  }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button size="icon" variant="ghost" title="Settings">
          <Settings />
          <span className="sr-only">Settings</span>
        </Button>
      </SheetTrigger>
      <SheetContent title="Settings" description="Presentation is kept in this browser; narration applies to the fleet.">
        <Section title="Narration" hint="claude's reasoning visibility, for everyone">
          <Segmented
            label="Narration"
            value={narration ?? "key"}
            options={Object.keys(NARRATION) as Narration[]}
            onChange={(v) => void setNarration(v)}
          />
          <p className="mt-1.5 text-xs text-faint">{NARRATION[narration ?? "key"]}</p>
        </Section>
        <Section title="Traces" hint="agent tool-use cards">
          <Segmented
            label="Traces"
            value={p.tracesExpanded ? "expanded" : "collapsed"}
            options={["expanded", "collapsed"]}
            onChange={(v) => p.set({ tracesExpanded: v === "expanded" })}
          />
        </Section>
        <Section title="Activity strip" hint="who is doing what, above the composer">
          <Toggle on={p.activityStrip} onChange={(activityStrip) => p.set({ activityStrip })} label="Activity strip" />
        </Section>
        <Section title="Aurora" hint="animated WebGL2 background">
          <Toggle on={p.aurora} onChange={(aurora) => p.set({ aurora })} label="Aurora background" />
          {p.aurora && (
            <div className="mt-3 space-y-2">
              <Slider label="Drift speed" min={0.25} max={2} step={0.05} value={p.auroraSpeed} unit="×" onChange={(auroraSpeed) => p.set({ auroraSpeed })} />
              <Slider label="Intensity" min={0.2} max={1.5} step={0.05} value={p.auroraIntensity} onChange={(auroraIntensity) => p.set({ auroraIntensity })} />
            </div>
          )}
        </Section>
      </SheetContent>
    </Sheet>
  );
}

function Segmented<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: T[]; onChange: (v: T) => void }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex gap-0.5 rounded-lg border border-border bg-panel2/60 p-0.5">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          role="radio"
          aria-checked={o === value}
          onClick={() => onChange(o)}
          className={cn(
            "h-7 cursor-pointer rounded-md px-3 text-xs font-semibold text-muted capitalize hover:text-text",
            o === value && "bg-accent/15 text-accent",
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      className={cn("relative h-5 w-9 cursor-pointer rounded-full border transition", on ? "border-accent/50 bg-accent/30" : "border-border bg-panel2")}
    >
      <span className={cn("absolute top-0.5 left-0.5 size-3.5 rounded-full transition", on ? "translate-x-4 bg-accent" : "bg-muted")} />
    </button>
  );
}

function Slider({
  label,
  unit = "",
  value,
  onChange,
  ...range
}: {
  label: string;
  unit?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}): ReactNode {
  return (
    <label className="flex items-center gap-3 text-xs text-muted">
      <span className="w-20 shrink-0">{label}</span>
      <input type="range" {...range} value={value} onChange={(e) => onChange(parseFloat(e.target.value))} className="flex-1 accent-accent" />
      <span className="w-10 text-right text-faint tabular-nums">
        {value.toFixed(2)}
        {unit}
      </span>
    </label>
  );
}
