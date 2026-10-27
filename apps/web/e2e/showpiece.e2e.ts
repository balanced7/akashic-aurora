import { expect, test } from "@playwright/test";

test.describe("showpiece features", () => {
  test("hero aurora shader draws a live frame", async ({ page }) => {
    await page.goto("/");
    const canvas = page
      .getByTestId("hero")
      .locator("[data-preset=aurora] canvas");
    await expect(canvas).toHaveAttribute("data-state", "live");
    const size = await canvas.evaluate(
      (element: HTMLCanvasElement) => element.width * element.height,
    );
    expect(size).toBeGreaterThan(1000);
  });

  test("constellation renders and streams learn and recall events", async ({
    page,
  }, testInfo) => {
    await page.goto("/");
    const section = page.getByTestId("constellation");
    await section.scrollIntoViewIfNeeded();
    await expect(section.locator("canvas")).toBeVisible({ timeout: 20_000 });
    await expect(section.getByText("Claude Code").first()).toBeAttached();
    // The event feed is a desktop panel; phones get the scene and legend only.
    if (testInfo.project.name === "mobile") return;
    const feed = page.getByTestId("constellation-feed");
    await expect(feed.locator("li").first()).toBeVisible({ timeout: 20_000 });
  });

  test("command palette searches and navigates", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name === "mobile",
      "keyboard shortcut is a desktop affordance",
    );
    await page.goto("/pricing", { waitUntil: "networkidle" });
    // The shortcut listener attaches on hydration.
    await expect(page.getByTestId("search-trigger")).toBeVisible();
    await page.keyboard.press("Control+k");
    const palette = page.getByTestId("command-palette");
    await expect(palette).toBeVisible();
    await palette.getByLabel("Search").fill("bifrost");
    await expect(palette.getByRole("option").first()).toContainText("Bifrost");
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/aurora\/bus$/);
    await expect(palette).toBeHidden();
  });

  test("search button opens the palette on any width", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("search-trigger").click();
    await expect(page.getByTestId("command-palette")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("command-palette")).toBeHidden();
  });

  test("playground learns a lesson, recalls it, and stays silent when nothing fits", async ({
    page,
  }) => {
    await page.goto("/");
    const playground = page.getByTestId("playground");
    await playground.scrollIntoViewIfNeeded();
    const input = playground.getByLabel("Aurora command");
    await input.fill(
      'aurora learn me --experiment deploy-cache --recommend "Use when a deploy is stale, before you retry: purge the cdn cache."',
    );
    await input.press("Enter");
    await expect(playground).toContainText(
      "[OK] recorded lesson 'deploy-cache'",
    );
    await input.fill('aurora recall-at --command "retry the stale deploy"');
    await input.press("Enter");
    await expect(playground).toContainText("purge the cdn cache");
    await input.fill("aurora recall-at --path docs/brand/palette.md");
    await input.press("Enter");
    await expect(playground).toContainText("silence beats a weak hint");
  });

  test("unknown pages get the branded 404 inside the site chrome", async ({
    page,
  }) => {
    const response = await page.goto("/definitely-not-a-page");
    expect(response?.status()).toBe(404);
    await expect(page.getByTestId("signal-lost")).toContainText(
      "Nothing at this address.",
    );
    await expect(page.getByTestId("site-header")).toBeVisible();
  });

  test("pillar pages show their crest", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name === "mobile",
      "the hero crest is desktop only",
    );
    await page.goto("/aurora/knowledge");
    await expect(page.getByTestId("pillar-crest").first()).toBeVisible();
  });

  test("blog posts show reading progress", async ({ page }) => {
    await page.goto("/blog/silence-beats-a-weak-hint");
    await expect(page.getByTestId("reading-progress")).toBeAttached();
  });
});

test("pages advertise their own social card, and it renders", async ({
  page,
  request,
}, testInfo) => {
  test.skip(
    testInfo.project.name === "mobile",
    "metadata does not depend on the viewport",
  );
  await page.goto("/aurora/bus");
  const ogImage = await page
    .locator('meta[property="og:image"]')
    .getAttribute("content");
  expect(ogImage).toContain("/api/og?");
  expect(ogImage).toContain("eyebrow=Bifrost");
  const card = await request.get(
    new URL(ogImage ?? "", "http://x").pathname +
      new URL(ogImage ?? "", "http://x").search,
  );
  expect(card.status()).toBe(200);
  expect(card.headers()["content-type"]).toContain("image/png");
});

test("public pages never ask the auth API for a session", async ({ page }) => {
  // A session fetch on every page view burns the auth rate limit for anonymous visitors.
  const authCalls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/auth/")) authCalls.push(request.url());
  });
  for (const route of ["/", "/pricing", "/blog"]) {
    await page.goto(route, { waitUntil: "networkidle" });
  }
  expect(authCalls).toEqual([]);
});

test("hero copies the agent setup prompt", async ({
  page,
  context,
}, testInfo) => {
  test.skip(
    testInfo.project.name === "mobile",
    "clipboard permissions are desktop-only in this setup",
  );
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("/");
  const setup = page.getByTestId("hero-setup");
  await setup.click();
  await expect(setup).toContainText("Copied");
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toContain("Set up Akashic Aurora for me");
  expect(copied).toContain("aurora recall first_try");
});
