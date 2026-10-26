import { expect, test } from "@playwright/test";

import { openConsole } from "./ready";

test("the rail shows the fleet, and a side room switches the stream and the send target", async ({ page }) => {
  await page.route("**/api/channels", (route) =>
    route.fulfill({
      json: {
        channels: [
          { ns: "bifrost", is_default: true, count: 2, agents: ["claude", "deepseek"] },
          { ns: "design", is_default: false, count: 1, agents: ["deepseek"] },
        ],
        default: "bifrost",
      },
    }),
  );
  const streams: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/events")) streams.push(new URL(r.url()).search);
  });
  const sent: unknown[] = [];
  await page.route("**/send", async (route) => {
    sent.push(route.request().postDataJSON());
    await route.fulfill({ json: { ok: true, to: "deepseek" } });
  });

  await openConsole(page);
  const rail = page.getByRole("complementary", { name: "Fleet rail" });
  await expect(rail.getByRole("heading", { name: /Now/ })).toBeVisible();
  await expect(rail.getByText("seats beating")).toBeVisible();
  await page.screenshot({ path: "test-results/rail-1440.png" });

  await rail.getByRole("button", { name: /^design/ }).click();
  await expect(page.getByText("In room design.")).toBeVisible();
  await expect.poll(() => streams).toContain("?ns=design");

  await page.getByRole("button", { name: /^Recipients:/ }).click();
  await page.getByRole("menuitemcheckbox", { name: /deepseek/ }).click();
  await page.keyboard.press("Escape");
  await page.getByRole("textbox").fill("hello design");
  await page.getByRole("textbox").press("Enter");
  await expect.poll(() => sent).toEqual([expect.objectContaining({ text: "hello design", to: "deepseek", ns: "design" })]);

  await page.getByRole("button", { name: "Back to bifrost" }).click();
  await expect(page.getByText("In room design.")).toBeHidden();
});
