import { test, expect } from '@playwright/test';
import { adapter, ready, expectSource, expectWrittenURL } from './adapter.js';

test('generated QR image decodes and loads the linked note through the upload path', async ({ page }) => {
  await ready(page);
  const href = await adapter.build(page, { src: 'Scanned note ☕' }, true);
  const image = await page.evaluate(async ({ href, kitURL }) => {
    const { encodeQr, qrPng } = await import(kitURL);
    const blob = await qrPng(encodeQr(href));
    return Array.from(new Uint8Array(await blob.arrayBuffer()));
  }, { href, kitURL: adapter.kitURL });
  await page.locator(adapter.qr).click();
  await page.locator('#qr-image').setInputFiles({ name: 'note.png', mimeType: 'image/png', buffer: Buffer.from(image) });
  await expect(page.locator(adapter.qrDialog)).toBeHidden();
  await expectSource(page, 'Scanned note ☕');
});
test('camera permission is deferred, a fake camera frame decodes, and tracks stop on close', async ({ page }) => {
  await ready(page);
  const href = await adapter.build(page, { src: 'Camera note' }, true);
  await page.evaluate(async ({ href, kitURL }) => {
    const { encodeQr, QrScanner } = await import(kitURL);
    const qr = encodeQr(href), canvas = document.createElement('canvas');
    canvas.width = canvas.height = (qr.size + 8) * 6;
    const ctx = canvas.getContext('2d'); ctx.fillStyle = 'white'; ctx.fillRect(0, 0, canvas.width, canvas.height); ctx.fillStyle = 'black';
    qr.modules.forEach((row, y) => row.forEach((dark, x) => { if (dark) ctx.fillRect((x + 4) * 6, (y + 4) * 6, 6, 6); }));
    window.cameraRequests = 0; window.cameraStopped = false;
    // Feed real QR pixels through the camera's frame path in every engine. Native
    // captureStream support differs, so keep acquisition deterministic and record cleanup.
    const nativeFrame = QrScanner.prototype.frame;
    QrScanner.prototype.frame = function() { return nativeFrame.call(this, canvas, null); };
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: async () => {
      window.cameraRequests++; return new MediaStream();
    } } });
    HTMLMediaElement.prototype.play = async function() {};
    MediaStream.prototype.getTracks = () => [{ stop() { window.cameraStopped = true; } }];
  }, { href, kitURL: adapter.kitURL });
  await page.locator(adapter.qr).click(); expect(await page.evaluate(() => window.cameraRequests)).toBe(0);
  await page.locator('#qr-scan').click();
  await expectSource(page, 'Camera note');
  expect(await page.evaluate(() => window.cameraRequests)).toBe(1);
  expect(await page.evaluate(() => window.cameraStopped)).toBe(true);
});
test('scanning arbitrary text never navigates', async ({ page }) => {
  await ready(page);
  const image = await page.evaluate(async kitURL => {
    const { encodeQr, qrPng } = await import(kitURL);
    return Array.from(new Uint8Array(await (await qrPng(encodeQr('javascript:alert(1)'))).arrayBuffer()));
  }, adapter.kitURL);
  await page.locator(adapter.qr).click();
  await page.locator('#qr-image').setInputFiles({ name: 'text.png', mimeType: 'image/png', buffer: Buffer.from(image) });
  await expect(page.locator(adapter.qrDialog).getByRole('button', { name: 'Copy text', exact: true })).toBeVisible();
  await expect(page.locator('.fk-scanned')).toContainText('javascript:alert(1)');
});
