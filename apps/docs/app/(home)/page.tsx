import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="flex flex-col justify-center text-center flex-1">
      <h1 className="text-2xl font-bold mb-4">Hello World</h1>
      <p>
        You can open{' '}
        <Link href="/docs/quickstart" className="font-medium underline">
          Quickstart
        </Link>{' '}
        and see the documentation.
      </p>
    </div>
  );
}
