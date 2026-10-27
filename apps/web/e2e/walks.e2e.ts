import { expect, test } from "@playwright/test";

const walks = [
  "/walks/walk-01-the-machine-refuses-to-wait",
  "/walks/walk-02-the-hostage-negotiations",
  "/walks/walk-03-the-rogues-gallery",
];

test.describe("forest walks", () => {
  test("the index lists every walk in series order", async ({ page }) => {
    await page.goto("/walks");
    const cards = page.getByTestId("walk-card");
    await expect(cards).toHaveCount(walks.length);
    for (const [index, href] of walks.entries()) {
      await expect(cards.nth(index)).toHaveAttribute("href", href);
    }
  });

  test("a walk links every section, its exam and its sources", async ({
    page,
  }, testInfo) => {
    await page.goto(walks[0] ?? "");
    await expect(page.getByTestId("walk-reading-time")).toContainText(
      "min read",
    );
    const body = page.getByTestId("walk-body");
    await expect(body.locator("h2#references + ol > li")).toHaveCount(91);
    await expect(body.locator("h2#teach-back-open")).toBeVisible();

    // Every section link points at a heading that exists.
    const nav =
      testInfo.project.name === "mobile"
        ? page.getByTestId("walk-toc")
        : page.getByRole("navigation", { name: "In this walk" }).last();
    if (testInfo.project.name === "mobile") {
      await nav.locator("summary").click();
    }
    const hrefs = await nav
      .getByRole("link")
      .evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    expect(hrefs.length).toBeGreaterThan(5);
    for (const href of hrefs) {
      await expect(page.locator(href ?? "")).toHaveCount(1);
    }
  });

  test("old akashiclabs.io links with a trailing slash still land", async ({
    page,
  }) => {
    for (const href of walks) {
      await page.goto(`${href}/`);
      await expect(page).toHaveURL(new RegExp(`${href}$`));
      await expect(page.getByTestId("page-title")).toBeVisible();
    }
  });

  test("walks link to the next and previous walk", async ({ page }) => {
    await page.goto(walks[1] ?? "");
    const more = page.getByRole("navigation", { name: "More walks" });
    await expect(more.getByRole("link")).toHaveCount(2);
    await more.getByRole("link", { name: /Walk 03/ }).click();
    await expect(page).toHaveURL(new RegExp(`${walks[2]}$`));
  });
});
