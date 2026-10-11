import { test, expect, Page, APIRequestContext } from "@playwright/test";
import { rename, writeFile, unlink, readFile } from "node:fs/promises";
import { parse } from "csv-parse/sync";
import { upload, downloadRows } from "./helpers";

const phoneCsv =
  'id,phone,note\n1,0412 345 678,"first, synthetic"\n2,invalid,keep\n3,,empty\n';
const secondCsv =
  'phone,extra\n0412 345 678,"second, file"\ninvalid,keep\n,empty\n';
const savedPanel = (page: Page) =>
  page.getByRole("region", { name: "Saved phone rules" });
async function createThroughUI(
  page: Page,
  request: APIRequestContext,
  name: string,
) {
  await upload(page, phoneCsv, "phones.csv");
  await page
    .getByRole("tab", { name: "Phone Normalization", exact: true })
    .click();
  const phone = page.getByRole("region", {
    name: "Phone normalization",
    exact: true,
  });
  await phone
    .getByRole("combobox", { name: "Target column", exact: true })
    .selectOption("phone");
  await phone.getByRole("button", { name: "Normalize", exact: true }).click();
  await expect(page.getByRole("link", { name: "Download CSV" })).toBeVisible();
  expect(
    (await (await request.get("http://127.0.0.1:8766/state")).json()).calls,
  ).toBe(1);
  await savedPanel(page)
    .getByRole("textbox", { name: "Rule name", exact: true })
    .fill(name);
  const saved = page.waitForResponse(
    (r) => r.url().endsWith("/api/rules/") && r.request().method() === "POST",
  );
  await savedPanel(page)
    .getByRole("button", { name: "Save phone rule", exact: true })
    .click();
  const response = await saved;
  expect(response.status()).toBe(201);
  const version = await response.json();
  await expect(savedPanel(page).getByRole("status")).toContainText(
    `Saved ${name} v1`,
  );
  await request.post("http://127.0.0.1:8766/reset", { data: { mode: "503" } });
  return version;
}
async function choose(page: Page, version: string) {
  const select = savedPanel(page).getByRole("combobox", {
    name: "Saved rule version",
  });
  await expect(select.locator(`option[value="${version}"]`)).toHaveCount(1);
  await select.selectOption(version);
}
async function preview(page: Page) {
  await savedPanel(page)
    .getByRole("button", { name: "Preview saved rule", exact: true })
    .click();
  await expect(
    savedPanel(page).getByRole("heading", { name: "Confirm phone preview" }),
  ).toBeVisible();
}
async function execute(page: Page) {
  const response = page.waitForResponse((r) => r.url().endsWith("/execute/"));
  await savedPanel(page)
    .getByRole("button", { name: "Confirm and execute" })
    .click();
  return await response;
}
test.beforeEach(async ({ page, request }) => {
  await request.post("http://127.0.0.1:8766/reset", {
    data: { mode: "normal" },
  });
  await page.goto("/");
});
test.afterEach(async ({ request }) => {
  // Once saved, preview / new versions / execution must work with a rejecting model.
  expect(
    (await (await request.get("http://127.0.0.1:8766/state")).json()).calls,
  ).toBe(0);
});

test("save, refresh, reuse another schema, exact downloads and immutable old version", async ({
  page,
  request,
}) => {
  const v1 = await createThroughUI(page, request, "Reusable AU phones");
  await page.reload();
  await choose(page, v1.version_id);
  await expect(
    savedPanel(page).getByRole("button", { name: "Preview saved rule" }),
  ).toBeDisabled();
  const file = await upload(page, secondCsv, "second.csv");
  await choose(page, v1.version_id);
  await preview(page);
  const table = savedPanel(page).getByRole("table", {
    name: "Saved rule before and after",
  });
  await expect(table.getByRole("row")).toHaveCount(4);
  await expect(table.getByRole("row").nth(1)).toContainText("0412 345 678");
  await expect(table.getByRole("row").nth(1)).toContainText("+61412345678");
  const screenshot = test.info().outputPath("phone-rule-preview.png");
  await savedPanel(page).screenshot({ path: screenshot });
  await test.info().attach("Phone rule preview", { path: screenshot, contentType: "image/png" });
  expect((await execute(page)).status()).toBe(200);
  expect(await downloadRows(page)).toEqual(
    parse(secondCsv.replace("0412 345 678", "+61412345678")),
  );
  await expect(
    savedPanel(page).getByRole("list", { name: "Execution history" }),
  ).toContainText("succeeded");
  expect(
    await readFile(`../.e2e-runtime/media/uploads/${file.file_id}.csv`, "utf8"),
  ).toBe(secondCsv);

  await savedPanel(page)
    .getByText("Create a new immutable version", { exact: true })
    .click();
  await savedPanel(page)
    .getByRole("combobox", { name: "Version format" })
    .selectOption("NATIONAL");
  const nextResponse = page.waitForResponse((r) =>
    r.url().endsWith("/versions/"),
  );
  await savedPanel(page)
    .getByRole("button", { name: "Save new version" })
    .click();
  const v2 = await (await nextResponse).json();
  expect(v2.version).toBe(2);
  expect(v2.rule_id).toBe(v1.rule_id);
  await expect(
    savedPanel(page).getByText("Selected v2:", { exact: false }),
  ).toContainText("NATIONAL");
  await preview(page);
  await choose(page, v1.version_id);
  await expect(
    savedPanel(page).getByRole("button", { name: "Confirm and execute" }),
  ).toHaveCount(0);
  await preview(page);
  expect((await execute(page)).status()).toBe(200);
  expect(await downloadRows(page)).toEqual(
    parse(secondCsv.replace("0412 345 678", "+61412345678")),
  );
  const listed = (
    await (await request.get("http://127.0.0.1:8765/api/rules/")).json()
  ).rules;
  expect(
    listed.find((r: { version_id: string }) => r.version_id === v1.version_id),
  ).toEqual(v1);

  await preview(page);
  await page
    .locator("input[type=file]")
    .setInputFiles({
      name: "selection.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("different\nmissing target\n"),
    });
  await expect(
    savedPanel(page).getByRole("button", { name: "Confirm and execute" }),
  ).toHaveCount(0);
  await upload(page, "different\nmissing target\n", "missing.csv");
  await expect(
    savedPanel(page).getByRole("button", { name: "Confirm and execute" }),
  ).toHaveCount(0);
  await choose(page, v1.version_id);
  await savedPanel(page)
    .getByRole("button", { name: "Preview saved rule" })
    .click();
  await expect(
    savedPanel(page).getByText(
      "The rule's target column is missing from the input file.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Download CSV" })).toHaveCount(0);
});

test("real output filesystem failure produces failed history, no download, then recovery", async ({
  page,
  request,
}) => {
  const rule = await createThroughUI(page, request, "Failure recovery phones");
  await upload(page, secondCsv, "failure.csv");
  await choose(page, rule.version_id);
  await preview(page);
  expect((await execute(page)).status()).toBe(200);
  await expect(page.getByRole("link", { name: "Download CSV" })).toBeVisible();
  await preview(page); // Must clear the previous successful download.
  const directory = "../.e2e-runtime/media/processed";
  await rename(directory, `${directory}-held`);
  await writeFile(directory, "synthetic output failure");
  try {
    const response = await execute(page);
    expect(response.status()).toBe(500);
    const body = await response.json();
    expect(body.error.code).toBe("OUTPUT_SAVE_FAILED");
    expect(body.execution.status).toBe("failed");
    expect(body.execution.output_file_id).toBeNull();
    await expect(
      savedPanel(page).getByText(
        "The output could not be saved. Preview and try again.",
        { exact: true },
      ),
    ).toBeVisible();
    await expect(
      savedPanel(page).getByRole("list", { name: "Execution history" }),
    ).toContainText("failed");
    await expect(page.getByRole("link", { name: "Download CSV" })).toHaveCount(
      0,
    );
  } finally {
    await unlink(directory);
    await rename(`${directory}-held`, directory);
  }
  await preview(page);
  expect((await execute(page)).status()).toBe(200);
  expect(await downloadRows(page)).toEqual(
    parse(secondCsv.replace("0412 345 678", "+61412345678")),
  );
});

test("changed input invalidates confirmation and records controlled failure", async ({
  page,
  request,
}) => {
  const rule = await createThroughUI(page, request, "Content-bound phones");
  const file = await upload(page, secondCsv, "content.csv");
  await choose(page, rule.version_id);
  await preview(page);
  await writeFile(
    `../.e2e-runtime/media/uploads/${file.file_id}.csv`,
    secondCsv + "invalid,new row\n",
  );
  const response = await execute(page);
  expect(response.status()).toBe(400);
  expect((await response.json()).error.code).toBe("FILE_CHANGED");
  await expect(
    savedPanel(page).getByRole("list", { name: "Execution history" }),
  ).toContainText("FILE_CHANGED");
  await expect(page.getByRole("link", { name: "Download CSV" })).toHaveCount(0);
  await expect(
    savedPanel(page).getByRole("button", { name: "Confirm and execute" }),
  ).toHaveCount(0);
});
