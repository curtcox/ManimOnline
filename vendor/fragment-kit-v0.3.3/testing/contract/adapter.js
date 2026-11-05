import { expect } from '@playwright/test';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const defaultAdapter = {
  ready: 'body[data-ready="true"]', editor: '#source', status: '#app-status', draftKey: 'fragment-notes:document',
  more: '.fk-more', resume: '#resume-work', drafts: '#draft-dialog', restore: '#restore-work',
  share: '#share-open', shareDialog: '#share-dialog', shareLink: '#share-link', qr: '#qr-open', qrDialog: '#qr-dialog',
  kitURL: './vendor/fragment-kit-v0.3.3/src/index.js', example: 'welcome', tabs: ['Write', 'Read'], cachePrefix: 'fragment-notes-',
  configureHashBin: async (context, clientId) => {
    await context.route('**/demo/config.js', async route => {
      const response = await route.fetch();
      await route.fulfill({ response, body: (await response.text()).replace("hashbinClientId: ''", `hashbinClientId: ${JSON.stringify(clientId)}`) });
    });
  },
  build: async (page, doc, canonical = false) => page.evaluate(async ({ doc, canonical }) => {
    const { urlState, config } = await import('./config.js');
    return urlState.build(doc, canonical ? { url: config.canonicalOrigin } : {}).href;
  }, { doc, canonical }),
  getDocument: page => page.evaluate(() => ({ src: document.getElementById('source').value, notes: { theme: document.getElementById('theme').value } })),
  edit: async (page, src) => { await page.locator('#source').fill(src); },
  openMore: async page => { await page.locator('.fk-more').click(); },
};
export const adapter = process.env.FRAGMENT_KIT_CONTRACT_CONFIG ? { ...defaultAdapter, ...(await import(pathToFileURL(path.resolve(process.env.FRAGMENT_KIT_CONTRACT_CONFIG)))).default } : defaultAdapter;
export async function ready(page, href = './') { await page.goto(href); await page.locator(adapter.ready).waitFor(); }

// Editors such as Ace keep the document outside their textarea's value.
export async function expectSource(page, expected) {
  await expect.poll(() => adapter.getSource ? adapter.getSource(page) : page.locator(adapter.editor).inputValue()).toBe(expected);
}
export async function expectWrittenURL(page) {
  await expect.poll(() => adapter.isWrittenURL ? adapter.isWrittenURL(page.url()) : new URL(page.url()).hash.startsWith('#v1.')).toBe(true);
}
export async function installHashBinMock(context, source) {
  if (adapter.installHashBinMock) return adapter.installHashBinMock(context, source);
  await context.route('**/vendor/hashbin-sdk-v0.4.0.mjs', route => route.fulfill({ body: source, contentType: 'text/javascript' }));
}
