import { commands } from "~/modules/marketing/content/aurora";
import { HudLabel } from "~/modules/marketing/ui/hud";

import type { CommandRef } from "~/modules/marketing/content/aurora";

const groups: CommandRef["group"][] = [
  "Start",
  "Memory",
  "Bifrost",
  "Coordination",
  "Story",
  "Tools",
];

/** From reference/commands.mdx. Descriptions are condensed from its tables. */
export const CommandReference = () => (
  <div
    data-testid="command-reference"
    className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
  >
    {groups.map((group) => (
      <div key={group} className="mk-card flex flex-col gap-1 p-5">
        <HudLabel tone="cyan" className="mb-3 text-[10px]">
          {group}
        </HudLabel>
        {commands
          .filter((command) => command.group === group)
          .map((command) => (
            <div
              key={command.verb}
              className="flex flex-col gap-0.5 border-t border-white/[0.05] py-2.5 first:border-t-0"
            >
              <code className="font-mono text-[12.5px] text-white">
                aurora {command.verb}
              </code>
              <span className="text-mk-faint text-[13px] leading-snug">
                {command.does}
              </span>
            </div>
          ))}
      </div>
    ))}
  </div>
);
