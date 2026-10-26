import { expect, test } from "@playwright/test";

import { openConsole } from "./ready";

const chapter = {
  id: "ch_test",
  title: "",
  started: "2026-10-26T10:00:00+00:00",
  duration_seconds: 1500,
  beats_count: 4,
  suggestion: { title: "Port the launcher", reason: "topic shift", confidence: 0.72 },
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.removeItem("bifrost_epi_ignore"));
  await page.route("**/episode/current", (route) => route.fulfill({ json: { current_chapter: chapter } }));
});

test("a suggestion banner hides on Continue and the episode chip shows its age", async ({ page }) => {
  await openConsole(page);
  const banner = page.getByRole("status").filter({ hasText: "Suggested: end this episode" });
  await expect(banner).toContainText("Port the launcher");
  await expect(banner).toContainText("topic shift · 72%");
  await expect(page.getByRole("button", { name: /untitled episode\s*25m/ })).toBeVisible();
  await banner.getByRole("button", { name: "Continue" }).click();
  await expect(banner).toBeHidden();
});

test("ending an episode opens the draft and Accept sends the edited fields", async ({ page }) => {
  const accepted: unknown[] = [];
  await page.route("**/episode/close", (route) =>
    route.fulfill({ json: { draft: { chapter_id: "ch_test", title: "Draft title", description: "what", why: "because" } } }),
  );
  await page.route("**/episode/accept", async (route) => {
    accepted.push(route.request().postDataJSON());
    await route.fulfill({ json: { ok: true } });
  });
  await openConsole(page);
  await page.getByRole("button", { name: /untitled episode/ }).click();
  await page.getByRole("button", { name: "End episode" }).click();
  const title = page.getByLabel("Title");
  await expect(title).toHaveValue("Draft title");
  await page.screenshot({ path: "test-results/episode-1440.png" });
  await title.fill("Fleet and launcher ported");
  await page.getByRole("button", { name: "Accept", exact: true }).last().click();
  await expect
    .poll(() => accepted)
    .toEqual([{ chapter_id: "ch_test", title: "Fleet and launcher ported", description: "what", why: "because" }]);
});
