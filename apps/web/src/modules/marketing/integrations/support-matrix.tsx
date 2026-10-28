import { Check, Minus } from "lucide-react";
import Link from "next/link";

import { cn } from "@akashic-labs/ui";

import { integrations } from "~/modules/marketing/content/integrations";
import { routes } from "~/modules/marketing/content/site";

import type { Support } from "~/modules/marketing/content/integrations";

const columns = [
  { key: "setup", label: "One-paste setup" },
  { key: "hooks", label: "Recall hooks" },
  { key: "mcp", label: "MCP tools" },
  { key: "seat", label: "Seat on the bus" },
] as const;

const Cell = ({ value }: { value: Support }) => {
  if (value === "yes")
    return (
      <Check className="text-hud-cyan mx-auto size-4" aria-label="Documented" />
    );
  if (value === "manual")
    return (
      <span className="text-hud-gold font-mono text-[11px]">manual habit</span>
    );
  return (
    <Minus
      className="mx-auto size-4 text-white/45"
      aria-label="Not documented"
    />
  );
};

/** Integration depth, per what the docs state. A dash means the docs say nothing yet, not "never". */
export const SupportMatrix = () => (
  <div className="relative">
    <div
      data-testid="support-matrix"
      className="overflow-x-auto rounded-[22px] border border-white/[0.08]"
    >
      <table className="w-full min-w-[640px] text-[14.5px]">
        <thead className="text-mk-faint bg-white/[0.02] text-[12px]">
          <tr>
            <th className="px-6 py-3 text-left font-medium">Harness</th>
            {columns.map((column) => (
              <th
                key={column.key}
                className="px-4 py-3 text-center font-medium"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.06]">
          {integrations.map((integration) => (
            <tr
              key={integration.slug}
              className="transition-colors hover:bg-white/[0.02]"
            >
              <td className="px-6 py-4">
                <Link
                  href={`${routes.integrations}/${integration.slug}`}
                  className="font-medium text-white hover:underline"
                >
                  {integration.name}
                </Link>
              </td>
              {columns.map((column) => (
                <td key={column.key} className={cn("px-4 py-4 text-center")}>
                  <Cell value={integration[column.key]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-mk-faint border-t border-white/[0.06] px-6 py-3 text-[12.5px]">
        A dash means the docs do not document it yet. It does not mean never.
      </p>
    </div>
    <span
      aria-hidden
      className="pointer-events-none absolute inset-y-0 right-0 w-10 rounded-r-[22px] bg-gradient-to-l from-[#050505] to-transparent sm:hidden"
    />
    <p className="text-mk-faint mt-2 text-[12px] sm:hidden">
      Swipe the table sideways for the last columns.
    </p>
  </div>
);
