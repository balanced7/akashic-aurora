import { expect, test } from "@playwright/test";

import { marketingRoutes } from "./routes";

/**
 * Site-wide checks that run on every marketing page:
 * it renders, has one h1, uses the shared header and footer, logs no errors,
 * and its copy avoids em and en dashes (a house style rule).
 */
for (const route of marketingRoutes) {
  test(`${route} renders cleanly`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      // Analytics keys are placeholders in local env files; their failures are not site bugs.
      if (
        message.type() === "error" &&
        !/posthog|plausible|umami/i.test(message.location().url)
      ) {
        errors.push(message.text());
      }
    });

    const response = await page.goto(route);
    expect(response?.status(), `HTTP status for ${route}`).toBeLessThan(400);

    await expect(page.getByTestId("site-header")).toBeVisible();
    await expect(page.getByTestId("site-footer")).toBeAttached();
    await expect(page.locator("h1")).toHaveCount(1);

    const title = await page.title();
    expect(title.length, "page has a title").toBeGreaterThan(3);

    const copy = await page.locator("main").innerText();
    expect(copy, "copy contains an em or en dash").not.toMatch(/[–—]/);

    // Ignore third-party noise; fail on errors raised by our own code.
    const ours = errors.filter(
      (text) =>
        !/favicon|chrome-extension|Download the React DevTools/i.test(text),
    );
    expect(ours, `console errors on ${route}`).toEqual([]);
  });
}

test("nothing spills past the viewport at phone width", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "mobile",
    "phone-width check runs in the mobile project",
  );
  test.setTimeout(240_000);
  for (const route of marketingRoutes) {
    await page.goto(route);
    // The marketing root clips overflow, so measure elements instead of the document width.
    const spills = await page.evaluate(() => {
      const width = window.innerWidth;
      const clipped = (element: Element) => {
        for (
          let node = element.parentElement;
          node && !node.classList.contains("mk");
          node = node.parentElement
        ) {
          const style = getComputedStyle(node);
          if (["auto", "scroll", "hidden", "clip"].includes(style.overflowX))
            return true;
        }
        return false;
      };
      return [...document.querySelectorAll("main *")]
        .filter((element) => {
          const rect = element.getBoundingClientRect();
          return rect.width > 0 && rect.right > width + 1 && !clipped(element);
        })
        .slice(0, 5)
        .map(
          (element) =>
            `${element.tagName.toLowerCase()}.${String(element.className).slice(0, 60)}`,
        );
    });
    expect(spills, `elements spilling past the viewport on ${route}`).toEqual(
      [],
    );
  }
});

// Guards the i18n provider fix: pages must ship real content in the server HTML, not an empty shell.
for (const route of marketingRoutes) {
  test(`${route} is server-rendered`, async ({ request }, testInfo) => {
    test.skip(
      testInfo.project.name === "mobile",
      "server HTML does not depend on the viewport",
    );
    const html = await (await request.get(route)).text();
    expect(html, `server HTML for ${route} has an h1`).toMatch(/<h1[\s>]/);
    expect(html, `server HTML for ${route} has a main landmark`).toMatch(
      /<main[\s>]/,
    );
  });
}
