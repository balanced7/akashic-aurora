# Akashic Labs website (`apps/web`)

The public Akashic Labs website: a Next.js App Router app. Its marketing pages (home, Aurora,
how it works, use cases, pricing and the rest) are in `src/app/[locale]/(marketing)`, and their
copy is in `src/modules/marketing/content`. It uses the packages in `../../packages` and the
shared config in `../../config`. All of them are members of the repo's bun workspace.

This is the canonical copy of the site. The older copy in the `mono` repository is no longer
maintained.

## Run it

```bash
bun install                           # from the repo root
cp apps/web/.env.example apps/web/.env.local
bun run --filter web dev              # http://localhost:3090
```

`.env.example` lists every variable the env schema (`env.config.ts`) reads. Its placeholders are
enough for the marketing pages. Auth, billing, email and the dashboard need real values, and
those also need Postgres at `DATABASE_URL`.

## Check and build

```bash
bun run --filter web lint
bun run --filter web typecheck
bun run --filter web test             # vitest
bun run --filter web build            # next build (turbo builds the packages it depends on first)
bun run --filter web start            # serve the production build on http://localhost:3000
```

CI's `web` job runs format, lint, typecheck, test and build for the whole JS workspace on every
push and pull request.

## Deploy

The site deploys to Vercel. Nothing in CI deploys it.

1. Create a Vercel project from this repository and set **Root Directory** to `apps/web`. Vercel
   finds `bun.lock` at the repo root and installs with bun. The default Next.js build works as is.
2. In the project's environment variables, set the production values of the variables in
   `.env.example` that you use. At least set `NEXT_PUBLIC_URL` to the public URL,
   `NEXT_PUBLIC_PRODUCT_NAME` and `CONTACT_EMAIL`, plus a real `BETTER_AUTH_SECRET`
   (`openssl rand -base64 32`) and `DATABASE_URL`.
3. Deploy from a linked checkout with `vercel deploy --prod`, or turn on the Vercel git
   integration so that `master` deploys to production.
