import { computeCID } from '../../core/cid.js';
import { createBudget } from '../budget.js';
import { changePrompt } from '../prompts.js';
import { applyOutput } from '../change/apply.js';
import { parseSuite, validateReferences } from './suite.js';
import { checkDocument, changedRatio } from './checks.js';
import { probabilityMetrics, metrics } from './metrics.js';
import { number, sha256, parseData, abort } from '../data.js';
export async function runEval({ ai, type, suite: input, models, repeats = 1, budget = 0, signal, onProgress = () => {}, storage, maxTokens = 2048 } = {}) {
  const suite = parseSuite(input, type); await validateReferences(suite, type);
  number(repeats, 'repeats', { min: 1, max: 100, integer: true });
  if (!Array.isArray(models) || models.length < 1 || models.length > 4 || new Set(models).size !== models.length || models.some(m => typeof m !== 'string' || m.startsWith('paste:'))) throw new Error('Choose 1–4 automated models. Paste comparisons run one request at a time.');
  const suiteCID = await computeCID(JSON.stringify(suite)), cap = createBudget({ total: budget }), results = [];
  let stopped = null;
  // Sequential execution is a bounded concurrency of one, including browser models.
  outer: for (const model of models) for (const c of suite.cases) for (let repeat = 0; repeat < repeats; repeat++) {
    if (signal?.aborted) { stopped = 'cancelled'; break outer; }
    const prompt = c.kind === 'change' ? await changePrompt({ type, snapshot: c.base, request: c.request }) : { promptHash: await sha256('fragment-kit-decide-v1'), messages: [{ role: 'user', content: JSON.stringify({ state: c.state, questions: { answer: c.question } }) }] };
    const key = `ai:eval:${suiteCID}:${c.id}:${model}:${repeat}:${prompt.promptHash}:${maxTokens}`;
    const cached = storage?.getItem(key);
    if (cached) { results.push(parseData(cached, 65536)); onProgress({ completed: results.length, cached: true }); continue; }
    let reservation;
    try { reservation = cap.reserve(ai.estimate({ model, capability: c.kind === 'change' ? 'generate' : 'decide', messages: prompt.messages, maxTokens })); }
    catch { stopped = 'budget'; break outer; }
    const entry = { case: c.id, requestedModel: model, repeat, promptHash: prompt.promptHash, private: c.private === true, success: false, valid: false, cost: null };
    let phase = 'request';
    try {
      const result = c.kind === 'change' ? await ai.generate({ model, messages: prompt.messages, maxTokens, signal }) : await ai.decide({ model, state: c.state, questions: { answer: c.question }, maxTokens, signal });
      Object.assign(entry, { model: result.model, provider: result.provider, usage: result.usage, cost: result.cost, timing: result.timing });
      if (result.cost != null) reservation.settle(result.cost);
      phase = 'validation';
      if (c.kind === 'change') {
        const doc = applyOutput({ type, snapshot: c.base, output: result.json ?? result.text }); entry.valid = true;
        const checked = await checkDocument({ type, base: c.base, document: doc, checks: c.checks, signal });
        entry.success = checked.pass; entry.checks = checked.checks; entry.changedRatio = changedRatio(c.base.src, doc.src); entry.outputHash = await sha256(JSON.stringify(doc));
      } else {
        const answer = result.answers.answer; entry.valid = !answer.refusal; entry.success = c.expected.includes(answer.choice); entry.source = result.source;
        entry.answer = answer.choice ?? null; entry.top2 = answer.probabilities ? Object.entries(answer.probabilities).sort((a,b) => b[1]-a[1]).slice(0,2).some(([id]) => c.expected.includes(id)) : null;
        Object.assign(entry, result.source === 'native' ? probabilityMetrics(answer.probabilities, c.expected[0]) : { brier: null, logLoss: null });
      }
      if (!entry.success) entry.failure = entry.valid ? 'checks' : 'refusal';
    } catch (error) { if (signal?.aborted) { stopped = 'cancelled'; break outer; } entry.failure = error.code ?? (phase === 'request' ? 'request' : 'invalid-output'); }
    abort(signal); results.push(entry); storage?.setItem(key, JSON.stringify(entry)); onProgress({ completed: results.length, result: entry });
  }
  return { suiteCID, parameters: {maxTokens, repeats}, results, metrics: metrics(results), stopped, spent: cap.spent().total };
}
