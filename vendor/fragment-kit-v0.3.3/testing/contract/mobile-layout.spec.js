import { test, expect } from '@playwright/test';
import { adapter, ready, expectSource, expectWrittenURL } from './adapter.js';
test('360px layout has no overflow, uses tabs, and provides resource links with 44px targets', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 }); await ready(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.getByRole('tab', { name: adapter.tabs[0], exact: true })).toBeVisible();
  await page.getByRole('tab', { name: adapter.tabs[1], exact: true }).click(); await expect(page.locator(adapter.editor)).toBeHidden();
  await page.getByRole('tab', { name: adapter.tabs[0], exact: true }).click(); await expect(page.locator(adapter.editor)).toBeVisible();
  const targets = await page.locator('button:visible').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().height));
  expect(targets.every(height => height >= 44)).toBe(true);
  await adapter.openMore(page);
  for (const name of ['Docs ↗', 'Gallery ↗', 'GitHub ↗']) await expect(page.getByRole('dialog').getByRole('link', { name })).toBeVisible();
  const bounds = await page.getByRole('dialog').boundingBox(); expect(bounds.width).toBe(360); expect(bounds.height).toBe(640);
});
test('desktop header links and keyboard tab navigation remain accessible', async ({ page }) => {
  await page.setViewportSize({ width: 1200, height: 800 }); await ready(page);
  await expect(page.getByRole('navigation', { name: 'Resources' }).getByRole('link', { name: 'Docs ↗' })).toBeVisible();
  await page.setViewportSize({ width: 360, height: 640 });
  await page.getByRole('tab', { name: adapter.tabs[0], exact: true }).focus(); await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: adapter.tabs[1], exact: true })).toBeFocused();
});
