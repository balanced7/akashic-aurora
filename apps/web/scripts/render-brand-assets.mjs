#!/usr/bin/env node
/**
 * Renders the Open Graph image and app icons from the HTML templates in scripts/brand.
 * Usage: node scripts/render-brand-assets.mjs   (needs network for Google Fonts)
 */
import { chromium } from "playwright-core";
import path from "node:path";

const root = path.join(import.meta.dirname, "..");
const browser = await chromium.launch({ args: ["--no-sandbox"] });

const render = async (template, output, width, height, transparent = false) => {
  const page = await browser.newPage({
    viewport: { width, height },
    deviceScaleFactor: 1,
  });
  await page.goto(`file://${path.join(root, "scripts/brand", template)}`, {
    waitUntil: "networkidle",
  });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: path.join(root, output),
    omitBackground: transparent,
  });
  await page.close();
  console.log(`wrote ${output}`);
};

await render("og.html", "src/app/opengraph-image.png", 1200, 630);
await render("icon.html", "src/app/icon.png", 512, 512, true);
await render("icon.html", "src/app/apple-icon.png", 512, 512, true);
await browser.close();
