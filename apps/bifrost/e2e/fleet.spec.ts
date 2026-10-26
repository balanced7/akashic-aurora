import { expect, test } from "@playwright/test";

import { openConsole } from "./ready";

test("the fleet panel shows the world, engine room and floor from the live backend", async ({ page }) => {
  await openConsole(page);
  await page.getByRole("button", { name: /^Fleet/ }).click();
  const sheet = page.getByRole("dialog", { name: "Fleet" });
  await expect(sheet).toBeVisible();
  await expect(sheet.getByRole("heading", { name: /World/ })).toBeVisible();
  await expect(sheet.getByRole("heading", { name: /Engine room/ })).toBeVisible();
  await expect(sheet.getByRole("heading", { name: /Floor/ })).toBeVisible();
  // the bounds line always renders, whatever it says: a reading or an honest "blind"
  await expect(sheet.getByTestId("world-bounds")).not.toBeEmpty();
  await page.waitForTimeout(400); // let the slide-in settle for the screenshot
  await page.screenshot({ path: "test-results/fleet-1440.png" });
});
