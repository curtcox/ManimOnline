import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
for (const mode of ['direct', 'gateway', 'host']) test(`${mode} supports the same propose/review/apply/undo boundary`, async ({ page, context }) => {
  test.skip(Boolean(process.env.FRAGMENT_KIT_CONTRACT_CONFIG), 'Standalone AI connection contract');
  await context.route('**/testing/fixtures/ai-live.html', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>AI connections</title>' }));
  const result = { text: JSON.stringify({ summary: 'Greet', edits: [{ find: 'Hello', replace: 'Hi' }] }), model: 'openai:resolved', provider: 'mock', usage: { inputTokens: 10, outputTokens: 10 }, cost: 0, finish: 'stop', timing: { totalMs: 1, firstMs: 1 } };
  await context.route('https://api.openai.com/v1/chat/completions', route => route.fulfill({ json: { model: 'resolved', choices: [{ message: { content: result.text }, finish_reason: 'stop' }], usage: { prompt_tokens: 10, completion_tokens: 10 } } }));
  await context.route('https://gateway.example/v1/generate', route => route.fulfill({ contentType: 'text/event-stream', body: `event: result\ndata: ${JSON.stringify(result)}\n\n` }));
  await context.route('https://ai.example/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/v1/host.html') return route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Mock AI host</title><script type="module" src="/mock-host.js"></script>' });
    if (url.pathname === '/mock-host.js') return route.fulfill({ contentType: 'text/javascript', body: `import {installAiHost} from '/src/ai/host/protocol.js'; installAiHost({allowedOrigins:[${JSON.stringify(new URL(test.info().project.use.baseURL ?? 'http://127.0.0.1:8000').origin)}],createClient:async()=>({models:async()=>[],generate:async()=>(${JSON.stringify(result)}),destroy(){}})});` });
    const file = path.resolve('.' + url.pathname); if (!file.startsWith(path.resolve('src') + path.sep)) return route.abort();
    return route.fulfill({ contentType: 'text/javascript', body: await fs.readFile(file, 'utf8') });
  });
  await page.goto('/testing/fixtures/ai-live.html');
  const outcome = await page.evaluate(async ({ mode }) => {
    const { createAi, createChangeRequests } = await import('/src/ai/index.js');
    const type = { type: 'notes', normalize: v => ({ src: v.src }) }, model = { ref: 'openai:mock', capabilities: ['generate'], pinned: true, destination: 'Test provider', prices: { input: 0, output: 0 } };
    const ai = await createAi({ config: { name: 'AI contract', canonicalOrigin: location.origin + '/', storagePrefix: 'fk-ai-contract', ai: { deployments: { [location.origin + '/']: { connection: mode, ...(mode === 'host' ? { host: 'https://ai.example/v1/' } : mode === 'gateway' ? { url: 'https://gateway.example/' } : {}) } }, routes: ['openai'], models: [model] } }, type, getAuthorization: () => 'Bearer test-short-lived' });
    if (mode === 'direct') ai.connect('openai', 'test-memory-only'); ai.consent('Test provider');
    let document = { src: 'Hello' };
    const change = createChangeRequests({ ai, type, getSnapshot: () => document, getFingerprint: () => document.src, onApply: d => { document = d; } });
    const proposal = await change.propose({ request: 'Greet', model: model.ref }), before = document.src;
    change.apply(proposal); const accepted = document.src; change.undo(); ai.destroy(); return { before, accepted, undone: document.src };
  }, { mode }); expect(outcome).toEqual({ before: 'Hello', accepted: 'Hi', undone: 'Hello' });
});

test('real host popup passes a key only to its same-origin frame', async ({ page, context }) => {
  test.skip(Boolean(process.env.FRAGMENT_KIT_CONTRACT_CONFIG), 'Standalone AI host credential contract');
  const appOrigin = 'http://127.0.0.1:8000';
  const model = { ref: 'openai:mock', capabilities: ['generate'], destination: 'OpenAI', pinned: true, prices: { input: 0, output: 0 } };
  await context.route('**/testing/fixtures/ai-live.html', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Host credential contract</title><link rel="stylesheet" href="/src/ui/kit.css">' }));
  await context.route('https://ai.example/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/ai-host.config.json') return route.fulfill({ json: { name: 'Test AI host', storagePrefix: 'fk-ai-host-test', allowedOrigins: [appOrigin], routes: ['openai'], models: [model] } });
    if (url.pathname === '/v1/host.html') { const html = (await fs.readFile('src/ai/host/host.html', 'utf8')).replace('src="host.js"', 'src="/src/ai/host/host.js"').replace('href="../../ui/kit.css"','href="/src/ui/kit.css"').replace('href="../ui/ai.css"','href="/src/ai/ui/ai.css"'); return route.fulfill({ contentType: 'text/html', body: html }); }
    const file = path.resolve('.' + url.pathname); if (!['src','vendor'].some(folder => file.startsWith(path.resolve(folder) + path.sep))) return route.abort();
    return route.fulfill({ contentType: file.endsWith('.css') ? 'text/css' : 'text/javascript', body: await fs.readFile(file) });
  });
  await context.route('https://api.openai.com/v1/chat/completions', route => route.fulfill({ json: { model: 'resolved', choices: [{ message: { content: 'Hello' }, finish_reason: 'stop' }], usage: { prompt_tokens: 5, completion_tokens: 1 } } }));
  await page.goto('/testing/fixtures/ai-live.html');
  await page.evaluate(async model => {
    const { createAi, createAiSettings } = await import('/src/ai/index.js');
    window.testAi = await createAi({ config: { name: 'Test', storagePrefix: 'fk-ai-parent', canonicalOrigin: location.origin + '/', ai: { deployments: { [location.origin + '/']: { connection: 'host', host: 'https://ai.example/v1/' } }, routes: ['openai'], models: [model] } }, type: { type: 'test', normalize: v => v } });
    createAiSettings({ai: window.testAi, container: document.body}); window.testAi.consent('OpenAI');
  }, model);
  await page.getByRole('button', { name: 'AI settings', exact: true }).click();
  await page.getByRole('button', { name: 'Open AI host', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'AI host connection', exact: true })).toBeVisible();
  const host = page.frameLocator('iframe[title="AI connection"]');
  const popupEvent = context.waitForEvent('page'); await host.getByRole('button', { name: 'Connect on AI host', exact: true }).click(); const popup = await popupEvent;
  await popup.getByLabel('Provider', { exact: true }).selectOption('openai'); await popup.getByLabel('API key', { exact: true }).fill('host-probe-secret');
  await popup.getByRole('button', { name: 'Allow this app and connect', exact: true }).click();
  await expect(host.getByRole('status')).toContainText('Connected for this app');
  const result = await page.evaluate(async () => { const result = await window.testAi.generate({ model: 'openai:mock', messages: [{ role: 'user', content: 'Hi' }], maxTokens: 5 }); return { text: result.text, stored: JSON.stringify({ ...localStorage, ...sessionStorage }).includes('host-probe-secret') }; });
  expect(result).toEqual({ text: 'Hello', stored: false });
});
