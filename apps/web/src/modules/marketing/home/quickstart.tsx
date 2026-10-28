"use client";

import { useState } from "react";

import { cn } from "@akashic-labs/ui";

import { install } from "~/modules/marketing/content/aurora";
import { CopyButton } from "~/modules/marketing/ui/copy-button";

/** Install band from quickstart.mdx. Commands are copied exactly from the docs. */

const tabs = [
  { id: "agent", label: "Paste into your agent" },
  { id: "mac", label: "macOS / Linux" },
  { id: "windows", label: "Windows" },
] as const;

type TabId = (typeof tabs)[number]["id"];

const launchers = [
  {
    id: "claude",
    label: "Claude Code",
    wrap: (prompt: string) => `claude '${prompt}'`,
  },
  {
    id: "codex",
    label: "Codex",
    wrap: (prompt: string) => `codex '${prompt}'`,
  },
  {
    id: "gemini",
    label: "Gemini CLI",
    wrap: (prompt: string) => `gemini '${prompt}'`,
  },
  {
    id: "cursor",
    label: "Cursor",
    wrap: (prompt: string) => `cursor-agent '${prompt}'`,
  },
  {
    id: "opencode",
    label: "OpenCode",
    wrap: (prompt: string) => `opencode --prompt '${prompt}'`,
  },
] as const;

const prompt = install.agentPrompt.join("\n");

export const Quickstart = () => {
  const [tab, setTab] = useState<TabId>("agent");
  const [launcherId, setLauncherId] =
    useState<(typeof launchers)[number]["id"]>("claude");
  const launcher =
    launchers.find((item) => item.id === launcherId) ?? launchers[0];

  const code =
    tab === "agent"
      ? launcher.wrap(prompt)
      : tab === "mac"
        ? [install.uvMac, "", ...install.mac].join("\n")
        : [install.uvWindows, "", ...install.windows].join("\n");

  return (
    <div data-testid="quickstart" className="mk-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] px-3 py-2.5">
        <div role="tablist" aria-label="Install method" className="flex gap-1">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              onClick={() => setTab(item.id)}
              className={cn(
                "h-8 rounded-lg px-3 text-[13px] font-medium transition-colors",
                tab === item.id
                  ? "bg-white/[0.08] text-white"
                  : "text-white/50 hover:text-white",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
        <CopyButton text={code} />
      </div>

      {tab === "agent" && (
        <div className="flex flex-wrap gap-1.5 border-b border-white/[0.06] px-4 py-3">
          {launchers.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={launcherId === item.id}
              onClick={() => setLauncherId(item.id)}
              className={cn(
                "h-7 rounded-full border px-3 text-[12px] transition-colors",
                launcherId === item.id
                  ? "border-hud-cyan/40 bg-hud-cyan/10 text-hud-cyan"
                  : "border-white/[0.08] text-white/55 hover:text-white",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}

      <pre
        tabIndex={0}
        className="max-h-[380px] overflow-auto p-5 font-mono text-[12.5px] leading-6 text-white/85"
      >
        <code>
          {code.split("\n").map((line, index) => (
            <div
              key={index}
              className={cn(
                line.startsWith("aurora") && "text-white",
                !line && "h-6",
              )}
            >
              {line.startsWith("aurora") ||
              line.startsWith("git") ||
              line.startsWith("curl") ? (
                <>
                  <span className="text-hud-cyan select-none">$ </span>
                  {line}
                </>
              ) : (
                line
              )}
            </div>
          ))}
        </code>
      </pre>
      <div className="text-mk-faint border-t border-white/[0.06] px-5 py-3 text-[12.5px]">
        {tab === "agent"
          ? "Your agent clones Aurora, adds the aurora command and runs a first session. It asks before it runs anything."
          : "All you need is uv, which handles your Python environment. The alias lasts for this terminal session."}
      </div>
    </div>
  );
};
