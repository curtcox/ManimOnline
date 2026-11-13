import { test, expect } from '@playwright/test';
import { ready, adapter } from './adapter.js';
import { mockAiResponse } from '../fixtures/mock-ai.mjs';
async function connect(page) {
  await page.locator('.fk-more').click(); await page.getByRole('button', { name: 'AI settings', exact: true }).click();
  const settings = page.locator('#ai-settings');
  await settings.getByLabel('Provider', { exact: true }).selectOption('openai');
  await settings.getByLabel('API key', { exact: true }).fill('probe-ai-key-do-not-store'); await settings.getByRole('button', { name: 'Connect key', exact: true }).click();
  await settings.getByLabel('total spending cap').fill('1'); await settings.getByLabel('day spending cap').fill('1'); await settings.getByLabel('month spending cap').fill('1'); await settings.getByRole('button', { name: 'Set spending caps' }).click();
  await settings.getByRole('button', { name: 'Close', exact: true }).click(); await page.locator('#fk-more-drawer').getByRole('button', { name: 'Close', exact: true }).click();
}
test.beforeEach(async ({ context }) => {
  await context.route('https://api.openai.com/v1/chat/completions', async route => {
    const response = mockAiResponse(route.request().postDataJSON());
    await route.fulfill({ status: 200, contentType: response.headers.get('Content-Type'), body: await response.text() });
  });
});
test('AI proposes as text, accepts as an edit, undoes and keeps keys off app storage', async ({ page }) => {
  test.skip(Boolean(process.env.FRAGMENT_KIT_CONTRACT_CONFIG), 'Reference demo AI integration');
  await ready(page); await page.getByRole('tab', { name: 'Write', exact: true }).click(); await page.locator('#source').fill('Hello');
  await connect(page); await page.locator('#ask-open').click();
  await page.getByLabel('Change model').selectOption('openai:gpt-4.1-mini-2025-04-14');
  await page.getByLabel('Describe a change').fill('uppercase'); await page.getByLabel('Allow sending this document', { exact: true }).check();
  await page.locator('#ai-send').click(); await expect(page.locator('#ai-accept')).toBeVisible();
  await expect(page.locator('#source')).toHaveValue('Hello');
  await page.locator('#ai-accept').click(); await expect(page.locator('#source')).toHaveValue('HELLO');
  await page.getByRole('button', { name: 'Undo AI change' }).click(); await expect(page.locator('#source')).toHaveValue('Hello');
  const leaks = await page.evaluate(async () => {
    const probe = 'probe-ai-key-do-not-store', found = [];
    for (const [kind, storage] of [['local', localStorage], ['session', sessionStorage]]) for (let i = 0; i < storage.length; i++) { const k = storage.key(i); if ((k + storage.getItem(k)).includes(probe)) found.push(kind); }
    if ((location.href + JSON.stringify(history.state)).includes(probe)) found.push('url/history');
    for (const name of await caches.keys()) { const cache = await caches.open(name); for (const request of await cache.keys()) if ((await (await cache.match(request)).text()).includes(probe)) found.push('cache'); }
    for (const { name } of await indexedDB.databases()) {
      const db = await new Promise((resolve, reject) => { const req = indexedDB.open(name); req.onsuccess = () => resolve(req.result); req.onerror = reject; });
      for (const store of db.objectStoreNames) { const values = await new Promise((resolve, reject) => { const req = db.transaction(store).objectStore(store).getAll(); req.onsuccess = () => resolve(req.result); req.onerror = reject; }); if (JSON.stringify(values).includes(probe)) found.push('indexeddb'); }
      db.close();
    }
    return found;
  }); expect(leaks).toEqual([]);
});
test('paste handoff validates JSON and renders hostile output without HTML', async ({ page }) => {
  test.skip(Boolean(process.env.FRAGMENT_KIT_CONTRACT_CONFIG), 'Reference demo AI integration');
  await ready(page); await page.getByRole('tab', { name: 'Write', exact: true }).click(); await page.locator('#source').fill('Hello');
  await page.locator('#ask-open').click(); await page.getByLabel('Describe a change').fill('Make a greeting'); await page.getByRole('button', { name: 'Copy prompt', exact: true }).click();
  await page.getByLabel('Paste model reply').fill(JSON.stringify({ summary: '<img src=https://evil.example/track>', edits: [{ find: 'Hello', replace: 'Hi' }] }));
  await page.getByRole('button', { name: 'Review pasted reply' }).click(); await expect(page.locator('#ai-accept')).toBeVisible(); expect(await page.locator('#ask-panel img').count()).toBe(0);
  await page.getByRole('button', { name: 'Reject', exact: true }).click(); await expect(page.locator('#source')).toHaveValue('Hello');
});
test('Ask fits 360px and keeps keyboard tab controls usable', async ({ page }) => {
  test.skip(Boolean(process.env.FRAGMENT_KIT_CONTRACT_CONFIG), 'Reference demo AI integration');
  await page.setViewportSize({ width: 360, height: 720 }); await ready(page); await page.locator('#ask-open').click(); await expect(page.getByLabel('Describe a change')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
  await page.getByRole('tab', { name: 'Ask', exact: true }).focus(); await page.keyboard.press('Home'); await expect(page.getByRole('tab', { name: 'Write', exact: true })).toHaveAttribute('aria-selected', 'true');
});
test('invalid AI callbacks fail visibly without opening defaults or drafts',async({page})=>{
  test.skip(Boolean(process.env.FRAGMENT_KIT_CONTRACT_CONFIG),'Reference demo callback integration');
  await ready(page,'./?code=untrusted&state=untrusted');
  await expect(page.locator('#app-status')).toContainText('original popup');
  await expect(page.locator('#source')).toHaveValue('');
  expect(new URL(page.url()).searchParams.has('code')).toBe(false);
  await page.goto('./gallery.html?code=untrusted&state=untrusted');
  await expect(page.getByRole('status')).toContainText('original popup');
  await expect(page.locator('.fk-ai-panel')).toHaveCount(0);
  expect(new URL(page.url()).searchParams.has('code')).toBe(false);
});
test('gallery sample search opens the editor and makes no model call by default',async({page})=>{
  test.skip(Boolean(process.env.FRAGMENT_KIT_CONTRACT_CONFIG),'Reference demo gallery chooser');
  let calls=0;page.on('request',request=>{if(request.url().startsWith('https://api.openai.com/'))calls++;});
  await page.goto('./gallery.html');await page.getByLabel('What do you want to make?',{exact:true}).fill('unicode');await page.getByRole('button',{name:'Find a starting point'}).click();
  const link=page.locator('.fk-ai-panel a').first();await expect(link).toBeVisible();expect(new URL(await link.getAttribute('href')).pathname.endsWith('/demo/')).toBe(true);expect(calls).toBe(0);
  await page.getByRole('button',{name:'AI settings',exact:true}).click();
  await page.getByLabel('Model reference',{exact:true}).fill('openrouter:test-added');
  await page.getByRole('button',{name:'Add model',exact:true}).click();
  await expect(page.getByLabel('Sample chooser model').locator('option[value="openrouter:test-added"]')).toHaveCount(1);
});
