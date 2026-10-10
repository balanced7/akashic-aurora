import { cn } from '@/lib/cn';

// One icon per concept section. The key is the section's folder under content/docs/concepts.
export const auroraIcons = {
  foundations: 'Foundations',
  memory: 'Memory and recall',
  bifrost: 'Bifrost',
  coordination: 'Coordination',
  narrative: 'Story and context',
  method: 'The method',
  tools: 'House tools',
} as const;

export type AuroraIconName = keyof typeof auroraIcons;

export function isAuroraIcon(name: string | undefined): name is AuroraIconName {
  return name !== undefined && Object.hasOwn(auroraIcons, name);
}

// Plain <img> on purpose: each SVG keeps its own gradient ids, so many copies on one page never clash.
export function AuroraIcon({
  name,
  size = 24,
  className,
}: {
  name: AuroraIconName;
  size?: number;
  className?: string;
}) {
  return (
    <img
      src={`/icons/aurora/${name}.svg`}
      alt=""
      aria-hidden
      width={size}
      height={size}
      draggable={false}
      className={cn('shrink-0 select-none', className)}
    />
  );
}

// The section a docs page belongs to, if it sits under concepts/<section>.
export function sectionOf(slugs: string[]): AuroraIconName | undefined {
  const [root, section] = slugs;
  return root === 'concepts' && isAuroraIcon(section) ? section : undefined;
}
