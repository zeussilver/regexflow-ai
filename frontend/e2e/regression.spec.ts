import { test, expect, Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { parse } from 'csv-parse/sync';

const csv = 'id,marker,note\n1,TOKEN-12,"hello, world"\n2,unchanged,plain\n3,,empty\n';
export async function upload(page: Page, data = csv, name = 'synthetic.csv') {
  await page.locator('input[type=file]').setInputFiles({ name, mimeType: 'text/csv', buffer: Buffer.from(data) });
  const response = page.waitForResponse(r => r.url().endsWith('/files/upload/'));
  await page.getByRole('button', { name: 'Upload', exact: true }).click();
  return await (await response).json();
}
async function generate(page: Page) {
  await page.getByRole('combobox', { name: 'Target column', exact: true }).selectOption('marker');
  await page.getByLabel('Pattern description').fill('Match synthetic TOKEN markers');
  const response = page.waitForResponse(r => r.url().endsWith('/regex/generate/'));
  await page.getByRole('button', { name: 'Generate Regex', exact: true }).click();
  return await response;
}
async function replace(page: Page, value = 'DONE') {
  await page.getByLabel('Replacement value').fill(value);
  await page.getByRole('button', { name: 'Apply Replacement', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Download CSV' })).toBeVisible();
}
export async function downloadRows(page: Page) {
  const pending = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download CSV' }).click();
  const download = await pending;
  expect(await download.failure()).toBeNull();
  const bytes = await readFile((await download.path())!);
  await test.info().attach('download.csv', { body: bytes, contentType: 'text/csv' });
  return parse(bytes, { bom: true });
}
test.beforeEach(async ({ page, request }) => {
  await request.post('http://127.0.0.1:8766/reset', { data: { mode: 'normal' } });
  await page.goto('/');
});
test('upload, original preview, model rule, replacement and exact CSV download', async ({ page, request }) => {
  await upload(page);
  await expect(page.getByRole('table').first().getByRole('row')).toHaveCount(4);
  await expect(page.getByRole('table').first()).toContainText('TOKEN-12');
  expect((await generate(page)).status()).toBe(200);
  await replace(page);
  expect(await downloadRows(page)).toEqual(parse(csv.replace('TOKEN-12', 'DONE')));
  expect((await (await request.get('http://127.0.0.1:8766/state')).json()).calls).toBe(1);
});
for (const [name, data, error] of [['empty.csv', '', 'The uploaded file is empty.'], ['unsupported.txt', 'hello', 'Only CSV and XLSX files are supported.']]) {
  test(`invalid upload clears a previous success: ${name}`, async ({ page }) => {
    await upload(page); await generate(page); await replace(page);
    const result = await upload(page, data, name);
    expect(result.error.message).toBe(error);
    await expect(page.getByText(error, { exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'No file loaded' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Download CSV' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Apply Replacement', exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Generate Regex', exact: true })).toBeDisabled();
  });
}
for (const [mode, code, status] of [['invalid-json', 'LLM_INVALID_JSON', 502], ['invalid-regex', 'REGEX_COMPILE_ERROR', 400], ['503', 'LLM_API_ERROR', 502]] as const) {
  test(`model failure clears old success and allows retry: ${mode}`, async ({ page, request }) => {
    await upload(page); await generate(page); await replace(page);
    await request.post('http://127.0.0.1:8766/reset', { data: { mode } });
    const response = await generate(page); expect(response.status()).toBe(status);
    const result = await response.json(); expect(result.error.code).toBe(code);
    await expect(page.getByText(result.error.message, { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Download CSV' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Apply Replacement', exact: true })).toHaveCount(0);
    expect((await (await request.get('http://127.0.0.1:8766/state')).json()).calls).toBe(1);
    await request.post('http://127.0.0.1:8766/reset', { data: { mode: 'normal' } });
    expect((await generate(page)).status()).toBe(200); await replace(page);
    expect(await downloadRows(page)).toEqual(parse(csv.replace('TOKEN-12', 'DONE')));
  });
}
test('full data integrity beyond 50 rows and repeat processing from original bytes', async ({ page, request }) => {
  const input = 'id,marker,note\n' + Array.from({ length: 63 }, (_, i) => `${i},${i % 3 === 0 ? `TOKEN-${i}` : i % 3 === 1 ? 'unchanged' : ''},"text, ${i}"\n`).join('');
  const file = await upload(page, input);
  const originalPath = `../.e2e-runtime/media/uploads/${file.file_id}.csv`;
  expect(await readFile(originalPath, 'utf8')).toBe(input);
  await expect(page.getByRole('table').first().getByRole('row')).toHaveCount(51);
  await generate(page);
  for (const value of ['DONE', 'AGAIN']) {
    await replace(page, value);
    const rows = await downloadRows(page);
    expect(rows).toEqual(parse(input.replace(/TOKEN-\d+/g, value)));
    expect(rows).toHaveLength(64);
    expect(await readFile(originalPath, 'utf8')).toBe(input);
  }
  expect((await (await request.get('http://127.0.0.1:8766/state')).json()).calls).toBe(1);
});
