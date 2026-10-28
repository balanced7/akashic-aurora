import path from "node:path";

import type { NextConfig } from "next";

import env from "./env.config";

const INTERNAL_PACKAGES = [
  "@akashic-labs/analytics-web",
  "@akashic-labs/api",
  "@akashic-labs/auth",
  "@akashic-labs/billing",
  "@akashic-labs/cms",
  "@akashic-labs/email",
  "@akashic-labs/db",
  "@akashic-labs/i18n",
  "@akashic-labs/shared",
  "@akashic-labs/storage",
  "@akashic-labs/ui",
  "@akashic-labs/ui-web",
];

const config: NextConfig = {
  reactStrictMode: true,
  turbopack: {
    /** Pin the monorepo root so nested git worktrees resolve their own packages */
    root: path.join(import.meta.dirname, "../.."),
    rules: {
      "*.svg": {
        loaders: ["@svgr/webpack"],
        as: "*.js",
      },
    },
  },

  images: {
    remotePatterns: [
      {
        hostname: "images.unsplash.com",
      },
    ],
  },

  /** Enables hot reloading for local packages without a build step */
  transpilePackages: INTERNAL_PACKAGES,
  experimental: {
    optimizePackageImports: INTERNAL_PACKAGES,
  },
};

const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: env.ANALYZE,
});

export default withBundleAnalyzer(config);
