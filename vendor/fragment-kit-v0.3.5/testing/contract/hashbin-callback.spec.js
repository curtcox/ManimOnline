import { test, expect } from '@playwright/test';
import { adapter, ready, expectSource, expectWrittenURL, sourceText, installHashBinMock } from './adapter.js';
import { mockHashBinSDK } from '../fixtures/mock-hashbin.mjs';
import { computeCID } from '../../src/core/cid.js';

test('empty client IDs explain saving setup', async ({ page, context }) => {
  await adapter.configureHashBin(context, '');
  await ready(page); await adapter.openMore(page); await page.locator('#hashbin-save').click();
  await expect(page.locator('#hashbin-message')).toContainText('registered client ID');
  await expect(page.locator('#hashbin-confirm')).toBeDisabled();
});

test('a slow HashBin load cannot replace a newer edit', async ({ page, context }) => {
  const payload = sourceText('A delayed saved note. '.repeat(10)), cid = await computeCID(payload);
  let release, requested;
  const started = new Promise(resolve => { requested = resolve; });
  const gate = new Promise(resolve => { release = resolve; });
  await context.route('https://256t.us/' + cid, async route => { requested(); await gate; await route.fulfill({ body: payload, contentType: 'text/plain' }); });
  await ready(page); await adapter.openMore(page);
  await page.locator('#hashbin-cid').fill(cid); await page.locator('#hashbin-load').click(); await started;
  await page.locator('#fk-more-drawer .fk-close').click();
  await adapter.edit(page, sourceText('A newer edit')); release();
  await expectSource(page, sourceText('A newer edit'));
  await page.waitForTimeout(100); await expectSource(page, sourceText('A newer edit'));
});
test('publish mock approves, cancels and restores redirect snapshots', async ({ page, context }) => {
  await installHashBinMock(context, mockHashBinSDK);
  await adapter.configureHashBin(context, 'contract-client');
  await ready(page); await adapter.edit(page, sourceText('Save this snapshot'));
  await adapter.openMore(page); await page.locator('#hashbin-save').click();
  await expect(page.locator('#hashbin-confirm')).toBeEnabled(); await page.locator('#hashbin-confirm').click();
  await expect(page.locator('#hashbin-message')).toContainText('Open saved source');
  expect(await page.evaluate(() => window.__publishEntered)).toBe(true);
  await page.locator('#hashbin-dialog .fk-close').click();
  await page.evaluate(() => { window.__publishMode = 'cancel'; });
  await page.locator('#hashbin-save').click(); await expect(page.locator('#hashbin-confirm')).toBeEnabled(); await page.locator('#hashbin-confirm').click();
  await expect(page.locator('#hashbin-message')).toContainText('cancelled');
  await page.locator('#hashbin-dialog .fk-close').click();
  await page.evaluate(() => { window.__publishMode = 'redirect'; });
  await page.locator('#hashbin-save').click(); await expect(page.locator('#hashbin-confirm')).toBeEnabled(); await page.locator('#hashbin-confirm').click();
  await expectSource(page, sourceText('Save this snapshot'));
  await expect(page).not.toHaveURL(/hashbin_publish=/);
});

test('a link too large for QR is replaced by the approved CID code', async ({ page, context }) => {
  await installHashBinMock(context, mockHashBinSDK);
  await adapter.configureHashBin(context, 'contract-client'); await ready(page);
  const source = sourceText(Array.from({ length: 2000 }, (_, index) => `${index.toString(36)}-${(index * 2654435761 >>> 0).toString(36)}`).join(' '));
  await adapter.edit(page, source); await page.locator(adapter.qr).click();
  await page.getByRole('button', { name: 'Save to HashBin for a scannable link', exact: true }).click();
  await expect(page.locator('#hashbin-confirm')).toBeEnabled(); await page.locator('#hashbin-confirm').click();
  await expect(page.locator(adapter.qrDialog)).toBeVisible();
  await expect(page.locator('#qr-code svg')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save to HashBin for a scannable link', exact: true })).toBeHidden();
});
