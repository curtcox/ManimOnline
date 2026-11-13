#!/usr/bin/env node
// Manual only. Never invoked by npm test or CI; no provider response bodies are logged.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium, firefox, webkit } from '@playwright/test';
import { args } from './lib.mjs';
import { serve } from './serve.mjs';
import { createBudget, estimateCost } from '../src/ai/budget.js';
const opts = args(), root = fileURLToPath(new URL('../', import.meta.url));
const approved = Number(opts.budget);
if (!Number.isFinite(approved) || approved <= 0 || approved > 10 || !process.env.OPENAI_API_KEY) throw new Error('Use a securely loaded OPENAI_API_KEY and --budget <USD, at most 10>.');
const folder = path.join(root, '.ai-local'); fs.mkdirSync(folder, { recursive: true, mode: 0o700 });
const ledgerPath = path.join(folder, 'live-budget.json');
const storage = { getItem: () => fs.existsSync(ledgerPath) ? fs.readFileSync(ledgerPath, 'utf8') : null, setItem: (_key, data) => fs.writeFileSync(ledgerPath, data, { mode: 0o600 }) };
const budget = createBudget({ total: approved, storage }), records = [];
const prices = { input: .4, output: 1.6 }, model = 'openai:gpt-4.1-mini-2025-04-14';
const { server, url } = await serve({ root, port: 0 });
try {
  for (const name of (opts.browsers ?? 'chromium,firefox,webkit').split(',')) {
    const launcher = { chromium, firefox, webkit }[name]; if (!launcher) throw new Error('Unknown browser.');
    let browser;
    try { browser = await launcher.launch(); } catch { records.push({ browser: name, ran: false, result: 'launch-failed' }); continue; }
    try {
      const page = await browser.newPage(); await page.goto(url + 'testing/fixtures/ai-live.html');
      for (const stream of [false, true]) {
        const messages = [{ role: 'system', content: 'Return only JSON {"summary":"Uppercase greeting","edits":[{"find":"Hello","replace":"HELLO"}]}.' }, { role: 'user', content: 'Change this synthetic note to uppercase: Hello' }];
        const estimate = estimateCost({ messages, maxTokens: 256, prices }), reservation = budget.reserve(estimate);
        let result;
        try {
          result = await page.evaluate(async ({ key, model, prices, stream, messages }) => {
            const { createAi, applyOutput } = await import('/src/ai/index.js');
            const type = { type: 'test', normalize: v => { if (typeof v.src !== 'string') throw new Error('Invalid'); return { src: v.src }; } };
            const ai = await createAi({ config: { name: 'Fragment Kit manual test', storagePrefix: 'fragment-kit-manual', canonicalOrigin: location.origin + '/', ai: { deployments: { [location.origin + '/']: { connection: 'direct' } }, routes: ['openai'], budget: { total: 1 }, models: [{ ref: model, capabilities: ['generate'], pinned: true, destination: 'OpenAI', prices }] } }, type });
            ai.connect('openai', key); ai.consent('OpenAI'); let chunks = 0;
            try {
              const result = await ai.generate({ model, messages, maxTokens: 256, ...(stream ? { onText: () => { chunks++; } } : {}) });
              const doc = applyOutput({ type, snapshot: { src: 'Hello' }, output: result.json });
              return { success: doc.src === 'HELLO', model: result.model, usage: result.usage, cost: result.cost, timing: result.timing, chunks };
            } finally { ai.destroy(); }
          }, { key: process.env.OPENAI_API_KEY, model, prices, stream, messages });
          if (result.cost != null) reservation.settle(result.cost);
        } catch { result = { success: false, result: 'request-or-validation-failed', reservedCost: estimate }; }
        records.push({ browser: name, ran: true, stream, ...result });
      }
    } finally { await browser.close(); }
  }
} finally { await new Promise(resolve => server.close(resolve)); }
const evidence = { date: new Date().toISOString(), approvedCap: approved, spentOrReserved: budget.spent().total, prices, pricingSource: 'https://developers.openai.com/api/docs/models/gpt-4.1-mini', records };
const output = opts.output ?? path.join(folder, 'live-evidence.json'); fs.writeFileSync(output, JSON.stringify(evidence, null, 2) + '\n'); console.log(JSON.stringify(evidence, null, 2));
