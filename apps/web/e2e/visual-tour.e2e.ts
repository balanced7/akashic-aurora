import { test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";

import { marketingRoutes } from "./routes";

/**
 * Saves full-page screenshots of every marketing route for design review.
 * Tagged @visual and skipped by default. Run with: E2E_VISUAL=1 playwright test --grep @visual
 */
const SCREEN_DIR = path.join(import.meta.dirname, ".screens");

// SwiftShader caps textures at 8192px, which wraps tall full-page captures. Canvases are hidden
// below anyway, so the tour runs on the default renderer.
test.use({ launchOptions: { args: ["--no-sandbox"] } });

for (const route of marketingRoutes) {
  test(`capture ${route}`, { tag: "@visual" }, async ({ page }, testInfo) => {
    mkdirSync(SCREEN_DIR, { recursive: true });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(route, { waitUntil: "networkidle" });
    // Trigger whileInView reveals before the full-page capture.
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 600) {
        window.scrollTo(0, y);
        await new Promise((resolve) => setTimeout(resolve, 60));
      }
      window.scrollTo(0, 0);
    });
    // Lazy 3D scenes mount once scrolled near; give them a beat to draw.
    if (await page.getByTestId("constellation").count()) {
      await page.getByTestId("constellation").scrollIntoViewIfNeeded();
      await page
        .getByTestId("constellation")
        .locator("canvas")
        .waitFor({ timeout: 20_000 });
      await page.waitForTimeout(1500);
      await page.evaluate(() => window.scrollTo(0, 0));
    }
    await page.waitForTimeout(400);
    // Stitched full-page captures scramble live WebGL canvases, so hide them; the CSS backdrops stay.
    await page.addStyleTag({
      content: "canvas { visibility: hidden !important; }",
    });
    const name =
      route === "/" ? "home" : route.replaceAll("/", "_").replace(/^_/, "");
    await page.screenshot({
      path: path.join(SCREEN_DIR, `${testInfo.project.name}-${name}.png`),
      fullPage: true,
    });
  });
}
