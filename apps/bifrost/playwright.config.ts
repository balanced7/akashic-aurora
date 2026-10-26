import { defineConfig, devices } from "@playwright/test";

/**
 * Runs against a live console backend (scripts/bifrost_ui.py on 8787, or BIFROST_API).
 * Sends are intercepted in the tests, so nothing reaches the real bus.
 */
export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8789",
    viewport: { width: 1440, height: 900 },
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: {
    command: "pnpm start",
    url: "http://127.0.0.1:8789",
    reuseExistingServer: true,
  },
});
