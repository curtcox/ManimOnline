import { test, expect } from '@playwright/test';
import { adapter, ready, expectSource, expectWrittenURL, sourceText } from './adapter.js';
test('opening a URL and editing it retains earlier work for explicit recovery', async ({ page }) => {
  await ready(page); await adapter.edit(page, sourceText('Keep this draft'));
  const href = await adapter.build(page, { src: sourceText('URL document') });
  await ready(page, href); await adapter.edit(page, sourceText('New URL edit'));
  await adapter.openMore(page); await page.locator(adapter.resume).click();
  await expect(page.locator(adapter.drafts)).toBeVisible();
  const option = page.locator('#saved-work option').filter({ hasText: 'Keep this draft' });
  await page.locator('#saved-work').selectOption(await option.getAttribute('value'));
  await page.locator(adapter.restore).click(); await expectSource(page, sourceText('Keep this draft'));
});
