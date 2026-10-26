import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  // Pages that moved, so old links keep working.
  async redirects() {
    const moved = ['fleet-and-residents', 'charters-and-briefs', 'trust', 'doors'].map((page) => ({
      source: `/docs/concepts/coordination/${page}`,
      destination: `/docs/concepts/fleet/${page}`,
      permanent: true,
    }));
    return [
      ...moved,
      {
        source: '/docs/concepts/bifrost/seats',
        destination: '/docs/concepts/fleet/seats',
        permanent: true,
      },
    ];
  },
};

export default withMDX(config);
