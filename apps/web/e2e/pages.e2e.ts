import { expect, test } from "@playwright/test";

test.describe("navigation", () => {
  test("desktop mega menu opens and routes to a pillar", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name === "mobile", "desktop navigation only");
    await page.goto("/");
    await page.getByRole("button", { name: "Product" }).click();
    await page
      .getByRole("link", { name: /Bifrost/ })
      .first()
      .click();
    await expect(page).toHaveURL(/\/aurora\/bus$/);
    await expect(page.getByTestId("page-title")).toContainText(
      "A message bus between agents",
    );
  });

  test("mobile menu lists every section", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile", "mobile navigation only");
    await page.goto("/");
    await page.getByRole("button", { name: "Open menu" }).click();
    for (const label of ["Knowledge", "Integrations", "Evidence", "Pricing"]) {
      await expect(
        page.getByRole("link", { name: label }).first(),
      ).toBeVisible();
    }
    await page.getByRole("link", { name: "Pricing" }).first().click();
    await expect(page).toHaveURL(/\/pricing$/);
  });
});

test.describe("integrations", () => {
  test("support matrix and per-harness pages agree with the docs", async ({
    page,
  }) => {
    await page.goto("/integrations");
    const matrix = page.getByTestId("support-matrix");
    await expect(matrix.getByRole("row")).toHaveCount(6);
    await page.goto("/integrations/cursor");
    await expect(
      page.getByText("aurora hooks install --scope user --harness cursor"),
    ).toBeVisible();
    await page.goto("/integrations/gemini-cli");
    await expect(page.getByText("Manual habit").first()).toBeVisible();
  });

  test("translation table filters by tool and query, and expands", async ({
    page,
  }) => {
    await page.goto("/integrations?tool=Cursor#translations");
    const table = page.getByTestId("translation-table");
    await expect(page.getByTestId("translation-count")).toContainText(
      "terms from Cursor",
    );
    await expect(table.locator("article")).toHaveCount(8);
    await page.getByTestId("translation-show-all").click();
    await expect
      .poll(async () => table.locator("article").count())
      .toBeGreaterThan(8);

    await page.goto("/integrations?tool=Codex&q=sandbox#translations");
    await expect(page.getByTestId("translation-count")).toContainText(
      'matching "sandbox"',
    );
    await expect(table.locator("article").first()).toContainText(/sandbox/i);
  });
});

test.describe("changelog", () => {
  test("months render with commit links, and the area filter narrows them", async ({
    page,
  }) => {
    await page.goto("/changelog");
    const months = page.getByTestId("changelog-month");
    const all = await months.count();
    expect(all).toBeGreaterThanOrEqual(5);
    await expect(
      months.first().locator('a[href*="/commit/"]').first(),
    ).toBeVisible();
    await page
      .getByRole("navigation", { name: "Filter by area" })
      .getByRole("link", { name: "Docs", exact: true })
      .click();
    await expect(page).toHaveURL(/area=Docs/);
    await expect(page.locator("article .hud-label").first()).toHaveText("Docs");
  });
});

test.describe("use cases", () => {
  test("fit check gives an honest verdict", async ({ page }) => {
    await page.goto("/use-cases");
    const fit = page.getByTestId("fit-check");
    const answer = async (index: number, value: "Yes" | "No") =>
      fit
        .locator("div.border-t")
        .nth(index)
        .getByRole("button", { name: value })
        .click();
    await answer(0, "Yes");
    await answer(1, "Yes");
    await answer(2, "Yes");
    await answer(3, "No");
    await answer(4, "No");
    await expect(page.getByTestId("fit-verdict")).toHaveText(
      "Built for accumulation",
    );
    await answer(3, "Yes");
    await answer(1, "No");
    await answer(2, "No");
    await expect(page.getByTestId("fit-verdict")).toHaveText(
      "Probably not yet",
    );
  });
});

test.describe("docs hub", () => {
  test("search narrows topics", async ({ page }) => {
    await page.goto("/docs");
    const before = await page.getByTestId("docs-section").count();
    expect(before).toBe(4);
    await page.getByLabel("Search docs topics").fill("handoff");
    await page.getByLabel("Search docs topics").press("Enter");
    await expect(page).toHaveURL(/q=handoff/);
    await expect(page.getByText("Hand off work")).toBeVisible();
    await expect(page.getByText("Memory settings")).toHaveCount(0);
  });
});

test.describe("honesty pages", () => {
  test("pricing says what is not offered", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page.getByTestId("plan-open-source")).toContainText("$0");
    await expect(page.getByTestId("plan-hosted")).toContainText("Not offered");
  });

  test("evidence lists counts with sources and the claims we do not make", async ({
    page,
  }) => {
    await page.goto("/evidence");
    const table = page.getByTestId("evidence-table");
    await expect(table).toContainText("uv run pytest --collect-only -q");
    await expect(page.getByText("Claims we do not make")).toBeVisible();
    await expect(page.getByText("Built, not wired").first()).toBeVisible();
  });

  test("open source shows the commit heatmap", async ({ page }) => {
    await page.goto("/open-source");
    await expect(
      page.getByTestId("commit-heatmap").locator("rect").first(),
    ).toBeAttached();
    await expect(page.getByTestId("repo-stats")).toBeVisible();
  });

  test("llms.txt serves markdown for agents", async ({ request }) => {
    const response = await request.get("/llms.txt");
    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toContain("text/markdown");
    const body = await response.text();
    expect(body).toContain("# Akashic Aurora");
    expect(body).toContain("Quickstart");
  });
});
