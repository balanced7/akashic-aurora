import { expect, test } from "@playwright/test";

import type { Page } from "@playwright/test";

/** Mean of a canvas's channel values, so two reads tell whether the field moved. */
const snapshot = (page: Page, index: number) =>
  page
    .locator("[data-testid=shader-background] canvas")
    .nth(index)
    .evaluate((canvas: HTMLCanvasElement) => {
      const context = canvas.getContext("2d");
      if (!context) return -1;
      const { data } = context.getImageData(0, 0, canvas.width, canvas.height);
      let sum = 0;
      for (const value of data) sum += value;
      return sum / data.length;
    });

test.describe("shader backgrounds", () => {
  test("mount on every section that asks for one and animate", async ({
    page,
  }) => {
    await page.goto("/");
    const canvases = page.locator("[data-testid=shader-background] canvas");
    expect(await canvases.count()).toBeGreaterThan(5);
    await expect(canvases.first()).toHaveAttribute("data-state", "live");
    const before = await snapshot(page, 0);
    await page.waitForTimeout(1000);
    expect(await snapshot(page, 0)).not.toEqual(before);
  });

  test("hold a still frame under reduced motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    const canvas = page
      .locator("[data-testid=shader-background] canvas")
      .first();
    await expect(canvas).toHaveAttribute("data-state", "live");
    const before = await snapshot(page, 0);
    await page.waitForTimeout(1000);
    expect(await snapshot(page, 0)).toEqual(before);
  });

  test("keep content sections dark enough for muted text", async ({ page }) => {
    await page.goto("/how-it-works");
    const backgrounds = page.locator(
      "section:not(:first-of-type) [data-testid=shader-background] canvas",
    );
    const count = await backgrounds.count();
    expect(count).toBeGreaterThan(0);
    for (let index = 0; index < count; index += 1) {
      const canvas = backgrounds.nth(index);
      await canvas.scrollIntoViewIfNeeded();
      await expect(canvas).toHaveAttribute("data-state", "live");
      // The 95th percentile relative luminance: muted copy (white at 62%) keeps 4.5:1 up to ~0.04.
      const luminance = await canvas.evaluate((element: HTMLCanvasElement) => {
        const context = element.getContext("2d");
        if (!context) return 1;
        const { data } = context.getImageData(
          0,
          0,
          element.width,
          element.height,
        );
        const linear = (value: number) => {
          const v = value / 255;
          return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
        };
        const values: number[] = [];
        for (let i = 0; i < data.length; i += 16)
          values.push(
            0.2126 * linear(data[i] ?? 0) +
              0.7152 * linear(data[i + 1] ?? 0) +
              0.0722 * linear(data[i + 2] ?? 0),
          );
        values.sort((a, b) => a - b);
        return values[Math.floor(values.length * 0.95)] ?? 1;
      });
      expect(luminance, `background ${index}`).toBeLessThan(0.04);
    }
  });

  test("fall back to the CSS gradient when the context is lost", async ({
    page,
  }) => {
    // Keep a handle on the shared WebGL context so the test can lose it.
    await page.addInitScript(() => {
      // Called below with the canvas as `this`, so the unbound reference is safe.
      // eslint-disable-next-line @typescript-eslint/unbound-method
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (
        this: HTMLCanvasElement,
        ...args: Parameters<typeof original>
      ) {
        const context = original.apply(this, args);
        if (args[0] === "webgl")
          (window as unknown as { __gl?: unknown }).__gl = context;
        return context;
      } as typeof original;
    });
    await page.goto("/");
    const canvas = page
      .locator("[data-testid=shader-background] canvas")
      .first();
    await expect(canvas).toHaveAttribute("data-state", "live");
    // A lost context answers getExtension with null, so take the extension while it is live.
    await page.evaluate(() => {
      const scope = window as unknown as {
        __gl: WebGLRenderingContext;
        __lose?: WEBGL_lose_context | null;
      };
      scope.__lose = scope.__gl.getExtension("WEBGL_lose_context");
    });
    const lose = (method: "loseContext" | "restoreContext") =>
      page.evaluate((name) => {
        (window as unknown as { __lose: WEBGL_lose_context }).__lose[name]();
      }, method);
    await lose("loseContext");
    await expect(canvas).toHaveAttribute("data-state", "fallback");
    await lose("restoreContext");
    await expect(canvas).toHaveAttribute("data-state", "live");
  });
});
