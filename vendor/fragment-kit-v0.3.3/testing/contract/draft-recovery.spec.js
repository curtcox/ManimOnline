import { test, expect } from '@playwright/test';
import { adapter, ready, expectSource, expectWrittenURL } from './adapter.js';
test('opening a URL and editing it retains earlier work for explicit recovery', async ({ page }) => {
  await ready(page); await adapter.edit(page, 'Keep this draft');
  const href = await adapter.build(page, { src: 'URL document' });
  await ready(page, href); await adapter.edit(page, 'New URL edit');
  await adapter.openMore(page); await page.locator(adapter.resume).click();
  await expect(page.locator(adapter.drafts)).toBeVisible();
  const option = page.locator('#saved-work option').filter({ hasText: 'Keep this draft' });
  await page.locator('#saved-work').selectOption(await option.getAttribute('value'));
  await page.locator(adapter.restore).click(); await expectSource(page, 'Keep this draft');
});
