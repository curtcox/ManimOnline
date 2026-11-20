import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import { adapter, ready, expectSource, sourceText, installHashBinMock } from './adapter.js';
import { mockHashBinSDK } from '../fixtures/mock-hashbin.mjs';

// An unbound Save opens Save as…; later saves use the dedicated button.
const saveAs = async (page, name, via = adapter.librarySaveAs) => {
  await page.locator(via).click();
  await expect(page.locator('#library-save-as-dialog')).toBeVisible();
  if (name !== undefined) await page.locator(adapter.saveAsName).fill(name);
  await page.locator(adapter.saveAsConfirm).click();
};

test('save, save-as, existing names and history persist across reload', async ({ page }) => {
  await ready(page);
  await adapter.edit(page, sourceText('First note'));
  await saveAs(page, 'My note', adapter.librarySave);
  await expect(page.locator(adapter.libraryStatus)).toContainText('Saved as “My note”');
  await adapter.edit(page, sourceText('First note v2'));
  await expect(page.locator(adapter.libraryStatus)).toContainText('Unsaved changes to “My note”');
  await page.locator(adapter.librarySave).click();
  await expect(page.locator(adapter.libraryStatus)).toContainText('Saved to “My note”');
  // An existing name, even with different case, offers an append instead of overwriting.
  await adapter.edit(page, sourceText('First note v3'));
  await saveAs(page, 'my NOTE');
  await page.getByRole('button', { name: /Add revision to/ }).click();
  await expect(page.locator(adapter.libraryStatus)).toContainText('Saved to “My note”');
  await ready(page);
  await page.locator(adapter.libraryOpen).click();
  const card = page.locator('#library-list .fk-entries .fk-entry', { hasText: 'My note' });
  await expect(card).toContainText('3 revisions');
  await card.getByRole('button', { name: 'History', exact: true }).click();
  const rows = page.locator('#library-list > .fk-entry');
  await expect(rows).toHaveCount(3);
  await rows.last().getByRole('button', { name: 'Open', exact: true }).click();
  await expectSource(page, sourceText('First note'));
  await expect(page.locator(adapter.libraryStatus)).toContainText('Opened “My note”');
  // Saving after loading an old revision branches from it.
  await adapter.edit(page, sourceText('Branched edit'));
  await page.locator(adapter.librarySave).click();
  await page.locator(adapter.libraryOpen).click();
  await page.locator('#library-list .fk-entries .fk-entry', { hasText: 'My note' }).getByRole('button', { name: 'History', exact: true }).click();
  await expect(page.locator('#library-list > .fk-entry')).toHaveCount(4);
});

test('a library export downloads and imports into a fresh browser profile', async ({ page, browser }) => {
  await ready(page);
  await adapter.edit(page, sourceText('Portable note'));
  await saveAs(page, 'Portable');
  await page.locator(adapter.libraryOpen).click();
  await page.locator('#library-export-open').click();
  const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#library-export-download').click()]);
  const file = await download.path(); const payload = await fs.readFile(file, 'utf8');
  expect(payload).toContain('fragment-kit-library'); expect(payload).toContain('Portable');
  const fresh = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const other = await fresh.newPage();
  try {
    await ready(other);
    await other.locator(adapter.libraryOpen).click();
    await other.locator('#library-import-open').click();
    await other.locator('#library-import-file').setInputFiles(file);
    await other.locator('#library-import-preview').click();
    const row = other.locator('#library-import-dialog .fk-entry', { hasText: 'Portable' });
    await expect(row).toContainText('New');
    await other.locator('#library-import-commit').click();
    await expect(other.locator('#library-import-status')).toContainText('Imported 1 document');
    await other.locator('#library-import-dialog .fk-close').click();
    const imported = other.locator('#library-list .fk-entries .fk-entry', { hasText: 'Portable' });
    await expect(imported).toContainText('1 revision');
    await imported.getByRole('button', { name: 'Open', exact: true }).click();
    await expectSource(other, sourceText('Portable note'));
  } finally { await fresh.close(); }
});

test('import previews conflicts and applies merge and copy decisions', async ({ page }) => {
  await ready(page);
  await adapter.edit(page, sourceText('Local v1'));
  await saveAs(page, 'Doc');
  await page.locator(adapter.libraryOpen).click();
  await page.locator('#library-export-open').click();
  const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#library-export-download').click()]);
  const file = await download.path();
  await page.locator('#library-export-dialog .fk-close').click();
  await page.locator('#library-dialog .fk-close').click();
  await adapter.edit(page, sourceText('Local v2 diverged'));
  await page.locator(adapter.librarySave).click();
  await page.locator(adapter.libraryOpen).click();
  await page.locator('#library-import-open').click();
  await page.locator('#library-import-file').setInputFiles(file);
  await page.locator('#library-import-preview').click();
  const row = page.locator('#library-import-dialog .fk-entry').filter({ hasText: 'Conflicts' });
  await row.locator('select').selectOption('copy');
  await page.locator('#library-import-commit').click();
  await expect(page.locator('#library-import-status')).toContainText('Imported 1 document');
  await page.locator('#library-import-dialog .fk-close').click();
  await expect(page.locator('#library-list .fk-entries')).toContainText('Doc (imported)');
  // The unchanged local document is untouched.
  const localDoc = page.locator('#library-list .fk-entries .fk-entry').filter({ has: page.locator('strong').getByText('Doc', { exact: true }) });
  await localDoc.getByRole('button', { name: 'Open', exact: true }).click();
  await expectSource(page, sourceText('Local v2 diverged'));
});

test('two tabs see each other’s saves and a moved head offers a branch', async ({ page, context }) => {
  await ready(page);
  await adapter.edit(page, sourceText('Shared v1'));
  await saveAs(page, 'Shared');
  const second = await context.newPage(); await ready(second);
  await second.locator(adapter.libraryOpen).click();
  await second.locator('#library-list .fk-entries .fk-entry', { hasText: 'Shared' }).getByRole('button', { name: 'Open', exact: true }).click();
  await expectSource(second, sourceText('Shared v1'));
  await adapter.edit(second, sourceText('Shared v2'));
  await second.locator(adapter.librarySave).click();
  await expect(second.locator(adapter.libraryStatus)).toContainText('Saved to “Shared”');
  // The first tab still holds the old head; saving offers Save anyway.
  await adapter.edit(page, sourceText('First tab edit'));
  await page.locator(adapter.librarySave).click();
  const dialog = page.getByRole('dialog', { name: 'Saved elsewhere' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Save anyway', exact: true }).click();
  await expect(page.locator(adapter.libraryStatus)).toContainText('Saved to “Shared”');
  await second.locator(adapter.libraryOpen).click();
  await second.locator('#library-list .fk-entries .fk-entry', { hasText: 'Shared' }).getByRole('button', { name: 'History', exact: true }).click();
  await expect(second.locator('#library-list > .fk-entry')).toHaveCount(3);
});

test('explicit URL loads win over the library and names stay out of URLs and storage', async ({ page }) => {
  await ready(page);
  await adapter.edit(page, sourceText('Library note'));
  await saveAs(page, 'S3cret-N4me');
  const href = await adapter.build(page, { src: sourceText('URL document'), notes: { theme: 'paper' } });
  await ready(page, href);
  await expectSource(page, sourceText('URL document'));
  expect(page.url()).not.toContain('S3cret-N4me');
  const storage = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }));
  expect(storage).not.toContain('S3cret-N4me');
  // The URL load was recorded; its content does not match the saved revision.
  await page.locator(adapter.libraryOpen).click();
  await expect(page.locator('#library-list .fk-recent')).toContainText('URL document');
  await expect(page.locator('#library-list .fk-entries .fk-entry', { hasText: 'S3cret-N4me' })).toBeVisible();
  await page.locator('#library-clear-recent').click();
  await expect(page.locator('#library-list .fk-recent')).not.toContainText('URL document');
});

test('a draft can be saved into the library', async ({ page }) => {
  await ready(page);
  await adapter.edit(page, sourceText('Draft to keep'));
  await page.locator(adapter.libraryOpen).click();
  await page.locator('.fk-drafts').getByRole('button', { name: /Save draft/ }).click();
  await expect(page.locator('#library-save-as-dialog')).toBeVisible();
  await page.locator(adapter.saveAsConfirm).click();
  await expect(page.locator(adapter.libraryStatus)).toContainText('Saved as “Draft to keep”');
  await page.locator('#library-dialog .fk-close').click();
  await page.locator(adapter.libraryOpen).click();
  await expect(page.locator('#library-list .fk-entries')).toContainText('Draft to keep');
});

test('HashBin publishes a library export and a stored revision through the mock', async ({ page, context }) => {
  await installHashBinMock(context, mockHashBinSDK);
  await adapter.configureHashBin(context, 'contract-client');
  await ready(page);
  await adapter.edit(page, sourceText('Publishable note'));
  await saveAs(page, 'Pub');
  // Export publish: arm, then approve in the click.
  await page.locator(adapter.libraryOpen).click();
  await page.locator('#library-export-open').click();
  await page.locator('#library-export-publish').click();
  await expect(page.locator('#library-export-publish')).toHaveText('Approve on HashBin');
  await page.locator('#library-export-publish').click();
  await expect(page.locator(adapter.libraryStatus)).toContainText('Library exported to HashBin');
  expect(await page.evaluate(() => window.__publishEntered)).toBe(true);
  await page.locator('#library-export-dialog .fk-close').click();
  // Revision publish: arm, then approve; the revision is marked published.
  await page.locator('#library-list .fk-entries .fk-entry', { hasText: 'Pub' }).getByRole('button', { name: 'History', exact: true }).click();
  await page.locator('#library-list > .fk-entry').getByRole('button', { name: 'Publish to 256t', exact: true }).click();
  const approve = page.locator('#library-list > .fk-entry').getByRole('button', { name: 'Approve on HashBin', exact: true });
  await expect(approve).toBeEnabled();
  await approve.click();
  await expect(page.locator(adapter.libraryStatus)).toContainText('Revision saved to HashBin');
  await expect(page.locator('#library-list > .fk-entry .fk-badge', { hasText: 'published' })).toBeVisible();
});

test('a redirect detached publish restores the editor and marks the library export', async ({ page, context }) => {
  await installHashBinMock(context, mockHashBinSDK);
  await adapter.configureHashBin(context, 'contract-client');
  await ready(page);
  await adapter.edit(page, sourceText('Redirect note'));
  await saveAs(page, 'Red');
  await page.evaluate(() => { window.__publishMode = 'redirect'; });
  await page.locator(adapter.libraryOpen).click();
  await page.locator('#library-export-open').click();
  await page.locator('#library-export-publish').click();
  await expect(page.locator('#library-export-publish')).toHaveText('Approve on HashBin');
  await page.locator('#library-export-publish').click();
  await expect(page.locator(adapter.libraryStatus)).toContainText('Library exported to HashBin');
  await expect(page).not.toHaveURL(/hashbin_publish=/);
  await expectSource(page, sourceText('Redirect note'));
});

test('a full browser reports the quota error and keeps the editor document', async ({ page, context, browserName }) => {
  test.skip(browserName !== 'chromium', 'the quota override needs Chromium CDP');
  await ready(page);
  const session = await context.newCDPSession(page);
  await session.send('Storage.overrideQuotaForOrigin', { origin: new URL(page.url()).origin, quotaSize: 64 * 1024 });
  const text = Array.from({ length: 30000 }, () => Math.random().toString(36).slice(2, 10)).join(' ');
  await adapter.edit(page, sourceText(text));
  await saveAs(page, 'Too big');
  await expect(page.locator('#library-save-as-status')).toContainText('out of space');
  await page.locator('#library-save-as-dialog .fk-close').click();
  await expectSource(page, sourceText(text));
});
