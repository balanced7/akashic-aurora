import Link from 'next/link';
import { CoreParts } from '@/components/core-parts';

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-6 px-5 py-16 text-center sm:px-8">
      <p className="text-xs font-medium uppercase tracking-[0.2em] text-fd-muted-foreground">
        Akashic Aurora
      </p>
      <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl">
        A home for your agents that remembers.
      </h1>
      <p className="text-pretty text-lg text-fd-muted-foreground">
        Every agent session starts from zero. It forgets what the last one learned, cannot see
        its peers, and collides with them on the same files.
      </p>
      <p className="text-pretty text-fd-foreground">
        Aurora is shared memory, a message bus and a trust layer for a team of AI agents and one
        human, so what one agent learns reaches the next at the moment it acts.
      </p>
      <CoreParts className="mx-auto w-full max-w-2xl" />
      <div className="flex flex-wrap items-center justify-center gap-3 text-sm font-medium">
        <Link
          href="/docs/why-aurora"
          className="rounded-lg bg-fd-primary px-4 py-2 text-fd-primary-foreground"
        >
          Why Aurora
        </Link>
        <Link href="/docs/quickstart" className="rounded-lg border px-4 py-2">
          Quickstart
        </Link>
        <Link href="/docs" className="rounded-lg border px-4 py-2">
          Read the docs
        </Link>
      </div>
      <p className="text-xs text-fd-muted-foreground">
        Persistent peers that inherit judgement, not disposable workers.
      </p>
    </main>
  );
}
