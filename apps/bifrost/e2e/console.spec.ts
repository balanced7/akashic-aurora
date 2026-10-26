import { expect, test } from "@playwright/test";

import { openConsole } from "./ready";

test("streams the live bus and shows who is online", async ({ page }) => {
  await openConsole(page);
  await expect(page.getByRole("status")).toHaveText("connected");
  await expect(page.getByRole("button", { name: /claude/i }).first()).toBeVisible();
  // the backfill lands, then the log renders at least one row
  await expect(page.locator("[aria-busy=false]")).toBeVisible();
  await expect(page.getByText("Connecting to the bus…")).toHaveCount(0);
  await page.screenshot({ path: "test-results/console-1440.png" });
});

test("a broadcast needs a second Enter, and the send carries text, target and fidelity", async ({ page }) => {
  const sent: unknown[] = [];
  await page.route("**/send", async (route) => {
    sent.push(route.request().postDataJSON());
    await route.fulfill({ json: { ok: true, intent: "inform", to: "all" } });
  });
  await openConsole(page);
  const box = page.getByRole("textbox", { name: "Message" });
  await box.fill("hello fleet");
  await box.press("Enter");
  await expect(page.getByText(/Press Enter again to send/)).toBeVisible();
  expect(sent).toHaveLength(0);
  await box.press("Enter");
  await expect.poll(() => sent).toEqual([{ text: "hello fleet", to: "all", fidelity: "inform" }]);
  await expect(box).toHaveValue("");
});

test("steer refuses a broadcast and goes to exactly one picked seat", async ({ page }) => {
  const sent: { to: string; fidelity: string }[] = [];
  await page.route("**/send", async (route) => {
    sent.push(route.request().postDataJSON());
    await route.fulfill({ json: { ok: true, msg: "steered claude" } });
  });
  await openConsole(page);
  await page.getByRole("radio", { name: "Steer" }).click();
  const box = page.getByRole("textbox", { name: "Message" });
  await box.fill("fold this in");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/Pick one agent to steer/)).toBeVisible();

  await page.getByRole("button", { name: /^Recipients:/ }).click();
  await page.getByRole("menuitemcheckbox", { name: /claude/i }).click();
  await page.keyboard.press("Escape");
  await box.press("Enter");
  await expect.poll(() => sent).toEqual([{ text: "fold this in", to: "claude", fidelity: "steer" }]);
});
