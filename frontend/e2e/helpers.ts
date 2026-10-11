import { test, expect, Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { parse } from "csv-parse/sync";

export const csv =
  'id,marker,note\n1,TOKEN-12,"hello, world"\n2,unchanged,plain\n3,,empty\n';
export async function upload(page: Page, data = csv, name = "synthetic.csv") {
  await page
    .locator("input[type=file]")
    .setInputFiles({ name, mimeType: "text/csv", buffer: Buffer.from(data) });
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/files/upload/"),
  );
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  return await (await response).json();
}
export async function downloadRows(page: Page) {
  const pending = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download CSV" }).click();
  const download = await pending;
  expect(await download.failure()).toBeNull();
  const bytes = await readFile((await download.path())!);
  await test
    .info()
    .attach("download.csv", { body: bytes, contentType: "text/csv" });
  return parse(bytes, { bom: true });
}
