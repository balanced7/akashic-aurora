import Link from 'next/link';
import { Card } from 'fumadocs-ui/components/card';
import { AuroraIcon, auroraIcons, type AuroraIconName } from './aurora-icon';
import { cn } from '@/lib/cn';

const sections = Object.keys(auroraIcons) as AuroraIconName[];

const hrefOf = (section: AuroraIconName) => `/docs/concepts/${section}`;

// A strip of every core part, each icon linking to its section.
export function CoreParts({ className }: { className?: string }) {
  return (
    <nav
      aria-label="Core parts of Aurora"
      className={cn('not-prose my-6 grid grid-cols-4 gap-2 sm:grid-cols-7', className)}
    >
      {sections.map((section) => (
        <Link
          key={section}
          href={hrefOf(section)}
          className="group flex flex-col items-center gap-2 rounded-xl p-2 text-center text-xs font-medium text-fd-muted-foreground transition-colors hover:bg-fd-accent hover:text-fd-accent-foreground"
        >
          <AuroraIcon
            name={section}
            size={44}
            className="transition-transform group-hover:-translate-y-0.5 group-hover:scale-105"
          />
          {auroraIcons[section]}
        </Link>
      ))}
    </nav>
  );
}

// A card for one concept section, with its icon beside the title.
export function SectionCard({
  section,
  description,
}: {
  section: AuroraIconName;
  description: string;
}) {
  return (
    <Card
      href={hrefOf(section)}
      title={
        <span className="flex items-center gap-2.5">
          <AuroraIcon name={section} size={28} />
          {auroraIcons[section]}
        </span>
      }
      description={description}
    />
  );
}
