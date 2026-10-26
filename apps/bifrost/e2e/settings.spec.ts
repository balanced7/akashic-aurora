import { expect, test } from "@playwright/test";

import { openConsole } from "./ready";

test("settings set narration fleet-wide and keep presentation choices across a reload", async ({ page }) => {
  const narration: unknown[] = [];
  await page.route("**/narration", async (route) => {
    narration.push(route.request().postDataJSON());
    await route.fulfill({ json: { ok: true, level: "full" } });
  });
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("seeded")) {
      localStorage.removeItem("bifrost.prefs");
      sessionStorage.setItem("seeded", "1");
    }
  });
  await openConsole(page);

  await page.locator("header").getByRole("button", { name: "Settings" }).click();
  const sheet = page.getByRole("dialog", { name: "Settings" });
  await sheet.getByRole("radiogroup", { name: "Narration" }).getByRole("radio", { name: "full" }).click();
  await expect.poll(() => narration).toEqual([{ level: "full" }]);

  await sheet.getByRole("radiogroup", { name: "Traces" }).getByRole("radio", { name: "expanded" }).click();
  await sheet.getByRole("switch", { name: "Activity strip" }).click();
  await expect(sheet.getByRole("switch", { name: "Activity strip" })).toHaveAttribute("aria-checked", "false");
  await page.screenshot({ path: "test-results/settings-1440.png" });

  await page.reload();
  await openConsole(page);
  await page.locator("header").getByRole("button", { name: "Settings" }).click();
  await expect(sheet.getByRole("radiogroup", { name: "Traces" }).getByRole("radio", { name: "expanded" })).toHaveAttribute("aria-checked", "true");
  await expect(sheet.getByRole("switch", { name: "Activity strip" })).toHaveAttribute("aria-checked", "false");
});
