import { test, expect } from '@playwright/test';
import { adapter, ready, expectSource, expectWrittenURL } from './adapter.js';
import { offlineServer } from '../fixtures/offline-server.mjs';
test.use({ serviceWorkers: 'allow' });
test.setTimeout(120000);

test('atomic install, offline reload, corrupt-cache detection and repair', async ({ page, context }) => {
  await ready(page);
  await expect(page.locator('#offline-status')).toHaveText('Available offline', { timeout: 60000 });
  await page.reload(); await page.locator(adapter.ready).waitFor();
  await context.setOffline(true); await page.reload(); await page.locator(adapter.ready).waitFor();
  expect((await adapter.getDocument(page)).src).not.toBe('');
  await context.setOffline(false);
  await page.evaluate(async ({ cachePrefix, asset }) => {
    const name = (await caches.keys()).find(name => name.startsWith(cachePrefix));
    const cache = await caches.open(name); await cache.put(new URL(asset, location.href), new Response('tampered'));
  }, { cachePrefix: adapter.cachePrefix, asset: adapter.offlineAsset ?? 'style.css' });
  const status = await page.evaluate(async kitURL => {
    const { OfflineClient } = await import(kitURL);
    return new OfflineClient().status();
  }, adapter.kitURL);
  expect(status.ready).toBe(false);
  await adapter.openMore(page); await page.locator('#offline-repair').click();
  await expect.poll(() => page.evaluate(async kitURL => {
    const { OfflineClient } = await import(kitURL);
    return (await new OfflineClient().status()).ready;
  }, adapter.kitURL), {timeout:60000}).toBe(true);
  await expect(page.locator('#offline-status')).toHaveText('Available offline', { timeout: 60000 });
});

test('a real deployment update waits for activation and a failed repair keeps the installed copy', async ({ page, context }) => {
  const fixture = await offlineServer();
  try {
    await page.goto(fixture.url); await expect(page.locator('#status')).toHaveText('Ready');
    await page.reload(); await expect(page.locator('#status')).toHaveText('Ready');
    expect(await page.evaluate(() => fetch('value.txt').then(response => response.text()))).toBe('version 1');
    fixture.update();
    await page.evaluate(async () => { await window.client.update(); });
    await page.waitForFunction(() => Boolean(window.client.registration.waiting));
    expect(await page.evaluate(() => fetch('value.txt').then(response => response.text()))).toBe('version 1');
    await page.evaluate(() => new Promise(resolve => {
      navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true }); window.client.activateUpdate();
    }));
    expect(await page.evaluate(() => fetch('value.txt').then(response => response.text()))).toBe('version 2');
    fixture.corrupt(true);
    expect((await page.evaluate(() => window.client.repair())).ready).toBe(false);
    await context.setOffline(true);
    expect(await page.evaluate(() => fetch('value.txt').then(response => response.text()))).toBe('version 2');
    await context.setOffline(false); fixture.corrupt(false);
    expect((await page.evaluate(() => window.client.repair())).ready).toBe(true);
  } finally { await context.setOffline(false); await fixture.close(); }
});
