#!/usr/bin/env node
import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { args } from './lib.mjs';
import { createStorage } from '../src/core/storage.js';
import { createAi, runEval, createReport } from '../src/ai/index.js';
import { mockFetch } from '../testing/fixtures/mock-ai.mjs';
const options = args();
try {
  if (!options.adapter || !options.suite || !options.models || !options.output) throw new Error('Use --adapter <trusted module> --suite <JSON> --models <comma-separated refs> --output <report.json> [--mock | --live --budget <USD>].');
  const { type, config, models: suppliedModels = [] } = await import(pathToFileURL(path.resolve(options.adapter)));
  if (!options.mock && (!options.live || !Number.isFinite(Number(options.budget)) || Number(options.budget) <= 0)) throw new Error('Live evaluation requires --live and a positive --budget.');
  const models = [...(config.ai?.models ?? []), ...suppliedModels].map(m => options.mock ? {...m, prices:{input:0,output:0}} : m);
  const statePath = path.resolve(options.log ?? '.ai-local/ai-eval-state.json');
  fsSync.mkdirSync(path.dirname(statePath), {recursive:true});
  const state = fsSync.existsSync(statePath) ? JSON.parse(fsSync.readFileSync(statePath, 'utf8')) : {};
  const storage = createStorage({prefix: config.storagePrefix + '-ai-cli', storage:{ getItem:k=>state[k]??null, setItem(k,v){state[k]=v;fsSync.writeFileSync(statePath,JSON.stringify(state),{mode:0o600});},removeItem(k){delete state[k];fsSync.writeFileSync(statePath,JSON.stringify(state),{mode:0o600});} }});
  const budget = options.mock ? 0 : Number(options.budget), refs = options.models.split(',');
  const ai = await createAi({ config: { ...config, ai: { ...config.ai, deployments: { [config.canonicalOrigin]: { connection: 'direct' } }, budget: { total: budget, day: budget, month: budget } } }, href: config.canonicalOrigin, type, models, storage, ...(options.mock ? { fetchSource: mockFetch } : {}) });
  for (const model of await ai.models()) {
    ai.consent(model.destination);
    const route = model.ref.split(':')[0];
    const env = { openai: 'OPENAI_API_KEY', openrouter: 'OPENROUTER_API_KEY', anthropic: 'ANTHROPIC_API_KEY', gemini: 'GEMINI_API_KEY' }[route];
    if (env && refs.includes(model.ref)) ai.connect(route, options.mock ? 'mock-key' : process.env[env]);
  }
  const suite = await fs.readFile(options.suite, 'utf8');
  const result = await runEval({ ai, type, suite, models: refs, repeats: Number(options.repeats ?? 1), budget, storage });
  await fs.writeFile(options.output, JSON.stringify(createReport(result), null, 2) + '\n');
  console.log(JSON.stringify({ output: options.output, stopped: result.stopped, spent: result.spent, metrics: result.metrics })); ai.destroy();
} catch (error) { console.error(error.message); process.exitCode = 1; }
