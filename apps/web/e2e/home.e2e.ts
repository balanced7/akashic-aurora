import { expect, test } from "@playwright/test";

test.describe("home page", () => {
  test("hero states the product and links to the quickstart and repo", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByTestId("hero-title")).toContainText("A home for");
    await expect(page.getByTestId("hero-title")).toContainText(
      "One that remembers.",
    );
    await expect(
      page.getByRole("link", { name: /Get started in two minutes/ }),
    ).toHaveAttribute("href", /\/docs\/quickstart$/);
    await expect(
      page.getByRole("link", { name: /Star on GitHub/ }),
    ).toHaveAttribute("href", "https://github.com/balanced7/akashic-aurora");
  });

  test("fleet console plays the recall loop to flip credit", async ({
    page,
  }) => {
    await page.goto("/");
    const console_ = page.getByTestId("fleet-console");
    await expect(console_).toBeVisible();
    await expect(console_.getByText("Lesson surfaced")).toBeVisible({
      timeout: 25_000,
    });
    await expect(console_.getByText(/flip credit \+1/)).toBeVisible({
      timeout: 25_000,
    });
  });

  test("loop replay shows the lesson crossing from Claude Code to Codex", async ({
    page,
  }) => {
    await page.goto("/");
    const replay = page.getByTestId("loop-replay");
    await replay.scrollIntoViewIfNeeded();
    await expect(replay.getByText("helped +1")).toBeVisible({
      timeout: 40_000,
    });
    await expect(replay.getByRole("button", { name: "Replay" })).toBeVisible();
  });

  test("how-it-works tabs swap the terminal", async ({ page }) => {
    await page.goto("/how-it-works");
    const tabs = page.getByTestId("loop-tabs");
    await tabs.scrollIntoViewIfNeeded();
    await tabs.getByRole("tab", { name: /Credit/ }).click();
    await expect(tabs.getByRole("tabpanel")).toContainText("recall-feedback");
    await tabs.getByRole("tab", { name: /Hand off/ }).click();
    await expect(tabs.getByRole("tabpanel")).toContainText(
      "will surface this as its briefing",
    );
  });

  test("recall scoreboard shows three lessons, or silence", async ({
    page,
  }) => {
    await page.goto("/");
    const board = page.getByTestId("recall-scoreboard");
    await board.scrollIntoViewIfNeeded();
    await expect(board).toContainText("3 / 3 max");
    await board.getByRole("tab", { name: "Nothing fits" }).click();
    await expect(board).toContainText("silence beats a weak hint");
    await expect(board).toContainText("0 / 3 max");
  });

  test("quickstart offers agent launchers and the exact commands", async ({
    page,
    context,
  }) => {
    await context
      .grantPermissions(["clipboard-read", "clipboard-write"])
      .catch(() => undefined);
    await page.goto("/");
    const quickstart = page.getByTestId("quickstart");
    await quickstart.scrollIntoViewIfNeeded();
    await expect(quickstart).toContainText(
      "claude 'Set up Akashic Aurora for me",
    );
    await quickstart.getByRole("button", { name: "Codex" }).click();
    await expect(quickstart).toContainText(
      "codex 'Set up Akashic Aurora for me",
    );
    await quickstart.getByRole("tab", { name: "macOS / Linux" }).click();
    await expect(quickstart).toContainText(
      "alias aurora='uv run -p 3.12 agent_cli.py'",
    );
    await quickstart.getByRole("tab", { name: "Windows" }).click();
    await expect(quickstart).toContainText(
      "function aurora { uv run -p 3.12 agent_cli.py @args }",
    );
  });

  test("FAQ answers open natively", async ({ page }) => {
    await page.goto("/");
    const faq = page.getByTestId("faq");
    await faq.getByText("Do I need to run Redis?").click();
    await expect(
      faq.getByText(/Aurora starts a small embedded one/),
    ).toBeVisible();
  });
});
