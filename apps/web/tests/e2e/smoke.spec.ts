import { expect, test } from "@playwright/test";

test.describe("Smoke Test", () => {
  test("opens on the hero with no horizontal scroll", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: /Grow more/ })).toBeVisible();

    const hasNoHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth <= window.innerWidth;
    });

    expect(hasNoHorizontalScroll).toBe(true);
  });
});
