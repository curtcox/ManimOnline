import { test, expect } from '@playwright/test';
import { adapter, ready, expectSource, expectWrittenURL, sourceText } from './adapter.js';
import { computeCID } from '../../src/core/cid.js';

test('explicit source, compressed document and CID links preserve local drafts', async ({ page }) => {
  await ready(page);
  await adapter.edit(page, sourceText('Previous draft'));
  const previous = await page.evaluate(key => localStorage.getItem(key), adapter.draftKey);
  expect(previous).toContain('Previous draft');
  const href = await adapter.build(page, { src: sourceText('Linked document ☕') });
  await ready(page, href); await expectSource(page, sourceText('Linked document ☕'));
  await page.reload(); await page.locator(adapter.ready).waitFor();
  expect(await page.evaluate(key => localStorage.getItem(key), adapter.draftKey)).toBe(previous);
  await page.evaluate(src => { location.hash = encodeURIComponent(src); }, sourceText('Legacy source'));
  await expectSource(page, sourceText('Legacy source'));
  const cid = await computeCID(sourceText('Inline source'));
  await ready(page, './?doc=invalid#' + cid); await expectSource(page, sourceText('Inline source'));
});
test('invalid explicit links report errors without default fallback', async ({ page }) => {
  await ready(page, './#v1.invalid!');
  await expect(page.locator(adapter.status)).toContainText('decompressed');
});
test('history writes use fragments and examples are replaced once', async ({ page }) => {
  await ready(page, './?example=' + encodeURIComponent(adapter.example));
  await expectWrittenURL(page); expect(new URL(page.url()).searchParams.has('example')).toBe(false);
  await adapter.edit(page, sourceText('Edited note')); await expectWrittenURL(page);
  await expectWrittenURL(page);
  await page.waitForTimeout(350); const href = page.url();
  await ready(page, href); await expectSource(page, sourceText('Edited note'));
});
