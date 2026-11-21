import { expect, test } from "@playwright/test";

test.describe("Smoke Test", () => {
  test("renders FARMLINK and has no horizontal scroll", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("FARMLINK")).toBeVisible();

    const hasNoHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth <= window.innerWidth;
    });

    expect(hasNoHorizontalScroll).toBe(true);
  });
});
