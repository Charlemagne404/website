const AxeBuilder = require("@axe-core/playwright").default;
const { test, expect } = require("@playwright/test");

test("homepage exposes production metadata", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/Introduktion \| Tullinge gymnasium datorklubb/);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "http://127.0.0.1:4173/");
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute(
    "content",
    /Introduktion \| Tullinge gymnasium datorklubb/
  );
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", "summary_large_image");
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute(
    "content",
    "http://127.0.0.1:4173/static/social-preview.svg"
  );
  const structuredData = await page.locator('script[type="application/ld+json"]').textContent();
  expect(structuredData).toContain("schema.org");

  await page.locator('a[href="#bli-medlem"]').first().click();
  await expect(page).toHaveURL(/#bli-medlem$/);
});

test("homepage passes core accessibility checks on mobile", async ({ browser }) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 }
  });
  const page = await context.newPage();

  await page.goto("/");
  await page.getByRole("button", { name: /öppna meny/i }).click();
  await expect(page.locator("#sidebar")).toHaveClass(/is-open/);

  const accessibilityScanResults = await new AxeBuilder({ page })
    .exclude(".video-frame iframe")
    .analyze();

  const seriousViolations = accessibilityScanResults.violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact)
  );

  expect(seriousViolations).toEqual([]);
  await context.close();
});
