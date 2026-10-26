import type { NextConfig } from "next";

/**
 * The Python console (scripts/bifrost_ui.py) stays the bus bridge; this app is only the face.
 * Every backend path is proxied to it, so the browser talks to one origin and the Python
 * routes stay the single source of truth for what the bus says.
 */
const BACKEND = process.env.BIFROST_API ?? "http://127.0.0.1:8787";

const PROXIED = [
  "/status",
  "/vitals",
  "/api/:path*",
  "/send",
  "/pause",
  "/resume",
  "/upload",
  "/negotiate",
  "/lib/run",
  "/launcher/:path*",
  "/episode/:path*",
  "/aurora-shader.js",
];

const config: NextConfig = {
  reactStrictMode: true,
  // The SSE stream (/events) is proxied by app/events/route.ts, not here: a rewrite may buffer.
  async rewrites() {
    return PROXIED.map((source) => ({ source, destination: `${BACKEND}${source}` }));
  },
};

export default config;
