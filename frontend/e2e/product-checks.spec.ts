import { test, expect, Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { downloadRows } from "./helpers";

const result = (page: Page) =>
  page.getByRole("region", { name: "CDR product data checks" });
async function openChecks(page: Page) {
  await page.goto("/");
  await page.getByRole("tab", { name: "CDR product checks", exact: true }).click();
  await expect(page).toHaveURL(/#product-checks$/);
}
function stat(page: Page, label: string) {
  return result(page)
    .locator(".stats div")
    .filter({ has: page.locator("dt", { hasText: new RegExp(`^${label}$`) }) })
    .locator("dd");
}

test("uploaded sample products are checked, filtered and exported", async ({ page }) => {
  await openChecks(page);
  await page.getByRole("radio", { name: "Upload JSON", exact: true }).check();
  await page.getByLabel("CDR products JSON", { exact: true }).setInputFiles({
    name: "sample_cdr_products.json",
    mimeType: "application/json",
    buffer: await readFile("../samples/sample_cdr_products.json"),
  });
  const response = page.waitForResponse(
    (r) => r.url().endsWith("/api/product-checks/") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Run checks", exact: true }).click();
  expect((await response).status()).toBe(201);

  await expect(stat(page, "Products")).toHaveText("6");
  await expect(stat(page, "With errors")).toHaveText("5");
  await expect(stat(page, "Errors")).toHaveText("13");
  await expect(stat(page, "Warnings")).toHaveText("5");
  const issues = page.getByRole("table", { name: "Product issues" });
  await expect(issues.getByRole("row")).toHaveCount(19);
  await expect(issues).toContainText("The rate means 475.00%");
  await expect(issues).toContainText("DISCOUNT rates must be zero or positive");

  await page.getByRole("combobox", { name: "Show", exact: true }).selectOption("warning");
  await expect(issues.getByRole("row")).toHaveCount(6);

  const rows = await downloadRows(page);
  expect(rows).toHaveLength(19);
  expect(rows[0]).toEqual([
    "product_index", "product_id", "product_name", "rule_id",
    "severity", "field", "message", "value",
  ]);
  await expect(page.getByRole("table", { name: "Recent checks" })).toContainText(
    "sample_cdr_products.json",
  );
});

test("live check reads the data holder's public product APIs", async ({ page }) => {
  await openChecks(page);
  await page.getByRole("combobox", { name: "Data holder", exact: true }).selectOption("fixture");
  await page.getByRole("button", { name: "Run checks", exact: true }).click();
  await expect(stat(page, "Products")).toHaveText("2");
  await expect(stat(page, "Errors")).toHaveText("1");
  await expect(result(page)).toContainText("Get Products v5 · Get Product Detail v7");
  await expect(page.getByRole("table", { name: "Product issues" })).toContainText(
    "Fixture Percent Loan",
  );
});

test("invalid uploads show the API error and no result", async ({ page }) => {
  await openChecks(page);
  await page.getByRole("radio", { name: "Upload JSON", exact: true }).check();
  await page.getByLabel("CDR products JSON", { exact: true }).setInputFiles({
    name: "products.json",
    mimeType: "application/json",
    buffer: Buffer.from('{"data": {"products": []}}'),
  });
  await page.getByRole("button", { name: "Run checks", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("The JSON does not contain any products.");
  await expect(page.getByRole("table", { name: "Product issues" })).toHaveCount(0);
});
