import { test, expect } from '@playwright/test';
import { adapter, ready, expectSource, expectWrittenURL, sourceText } from './adapter.js';

test('share dialog snapshots source, preserves run-on-open, and shortens through the mock provider', async ({ page, context }) => {
  await context.route('https://api.allorigins.win/**', route => route.fulfill({ json: { contents: 'https://is.gd/contract123', status: { http_code: 200 } } }));
  await ready(page); await adapter.edit(page, sourceText('Shared snapshot'));
  await page.locator(adapter.share).click(); await expect(page.locator(adapter.shareDialog)).toBeVisible();
  await page.locator('#share-run').uncheck();
  const href = await page.locator(adapter.shareLink).inputValue();
  expect(new URL(href).searchParams.get('run')).toBe('0'); expect(adapter.isWrittenURL ? adapter.isWrittenURL(href) : new URL(href).hash.startsWith('#v1.')).toBe(true);
  await page.getByRole('button', { name: 'Shorten link', exact: true }).click();
  await expect(page.locator(adapter.shareLink)).toHaveValue('https://is.gd/contract123');
  await ready(page, href); await expectSource(page, sourceText('Shared snapshot'));
});
test('shortener failure keeps the source URL ready to copy', async ({ page, context }) => {
  await context.route('https://api.allorigins.win/**', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await ready(page); await page.locator(adapter.share).click();
  const original = await page.locator(adapter.shareLink).inputValue();
  await page.getByRole('button', { name: 'Shorten link', exact: true }).click();
  await expect(page.locator(adapter.shareDialog)).toContainText('HTTP 503');
  await expect(page.locator(adapter.shareLink)).toHaveValue(original);
});
