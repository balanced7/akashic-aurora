import Link from 'next/link';
import { CoreParts } from '@/components/core-parts';

export default function HomePage() {
  return (
    <div className="flex flex-col justify-center text-center flex-1 gap-4 px-4">
      <h1 className="text-3xl font-bold">Akashic Aurora</h1>
      <p className="text-fd-muted-foreground">
        A shared memory for AI agents, and the wiring that lets them work together.
      </p>
      <CoreParts className="mx-auto w-full max-w-3xl" />
      <p className="flex gap-4 justify-center">
        <Link href="/docs/quickstart" className="font-medium underline">
          Quickstart
        </Link>
        <Link href="/docs/concepts" className="font-medium underline">
          Concepts
        </Link>
        <Link href="/docs/reference/glossary" className="font-medium underline">
          Glossary
        </Link>
      </p>
    </div>
  );
}
