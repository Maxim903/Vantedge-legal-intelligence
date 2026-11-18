import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export async function assertAccessibility(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
  expect(
    results.incomplete.filter((result) => result.id === "color-contrast"),
  ).toEqual([]);
}

export async function assertAccessibilityBothThemes(page: Page) {
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await assertAccessibility(page);
  }
  await page.emulateMedia({ colorScheme: "light" });
}
