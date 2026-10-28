import {
  Bricolage_Grotesque,
  Chakra_Petch,
  Figtree,
  JetBrains_Mono,
} from "next/font/google";

import { cn } from "@akashic-labs/ui";

import { buildSearchIndex } from "~/modules/marketing/content/search-index";
import { CommandPaletteProvider } from "~/modules/marketing/layout/command-palette";
import { SiteFooter } from "~/modules/marketing/layout/site-footer";
import { SiteHeader } from "~/modules/marketing/layout/site-header";
import { SpotlightTracker } from "~/modules/marketing/ui/spotlight";

const display = Figtree({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mk-display",
  weight: ["400", "500", "600", "700"],
});

/** One distinctive display face, used decisively for headlines across its full weight range. */
const heading = Bricolage_Grotesque({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mk-heading",
  axes: ["opsz"],
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mk-mono",
});

const hud = Chakra_Petch({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mk-hud",
  weight: ["500", "600", "700"],
});

/** Fonts, the .mk root, the command palette, header and footer. Shared by the layout and the root 404. */
export const MarketingShell = ({
  locale,
  children,
}: {
  locale: string;
  children: React.ReactNode;
}) => {
  const index = buildSearchIndex(locale);

  return (
    <div
      className={cn(
        "mk min-h-screen w-full overflow-x-clip antialiased",
        display.variable,
        heading.variable,
        mono.variable,
        hud.variable,
      )}
    >
      <CommandPaletteProvider index={index}>
        <SpotlightTracker />
        <SiteHeader />
        <main className="w-full">{children}</main>
        <SiteFooter />
      </CommandPaletteProvider>
    </div>
  );
};
