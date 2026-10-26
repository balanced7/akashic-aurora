import { type Page, expect } from "@playwright/test";

/** Open the console and wait until it is hydrated and has read fleet status (Pause enables). */
export async function openConsole(page: Page) {
  await page.goto("/");
  await expect(page.getByRole("button", { name: /^(Pause|Resume)$/ })).toBeEnabled({ timeout: 15_000 });
}
