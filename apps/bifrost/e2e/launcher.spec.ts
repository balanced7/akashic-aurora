import { expect, test } from "@playwright/test";

import { openConsole } from "./ready";

test("the launcher lists runners and kill needs a second click", async ({ page }) => {
  const kills: unknown[] = [];
  // Fixture rows: the real launcher would start and stop seats.
  await page.route("**/launcher/status", (route) =>
    route.fulfill({
      json: [
        { tag: "deepseek", agent_id: "deepseek", description: "DeepSeek API peer", enabled: true, status: "running", pid: 4242, exit_code: null, exit_reason: "", auto_revive: false, liveness: { phase: "thinking", stuck_seconds: 12, turn: 3, wedged: false } },
        { tag: "claude_headless", agent_id: "claude_headless", description: "Claude headless one-shot", enabled: false, status: "never_launched", pid: 0, exit_code: null, exit_reason: "", auto_revive: false, liveness: null },
      ],
    }),
  );
  await page.route("**/launcher/kill", async (route) => {
    kills.push(route.request().postDataJSON());
    await route.fulfill({ json: { ok: true } });
  });

  await openConsole(page);
  await page.getByRole("button", { name: "Agents" }).click();
  const sheet = page.getByRole("dialog", { name: "Agents" });
  await expect(sheet.getByText("1 of 2 runners running")).toBeVisible();
  await expect(sheet.getByText("thinking · 12s")).toBeVisible();

  const rows = sheet.getByRole("listitem");
  await expect(rows.nth(1).getByRole("button", { name: "Launch" })).toBeDisabled();

  await rows.first().getByRole("button", { name: "Kill" }).click();
  expect(kills).toEqual([]);
  await rows.first().getByRole("button", { name: "Click again to kill" }).click();
  await expect.poll(() => kills).toEqual([{ agent_id: "deepseek" }]);
  await page.screenshot({ path: "test-results/launcher-1440.png" });
});
