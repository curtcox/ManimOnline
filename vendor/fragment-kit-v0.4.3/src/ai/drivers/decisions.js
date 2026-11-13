import { MAX_BYTES } from '../../core/bytes.js';
import { keys, object, string, number, parseData, endpoint } from '../data.js';
import { jsonResponse, requestOptions, usage } from './http.js';
export function validateQuestions(input) {
  const questions = parseData(input, MAX_BYTES); object(questions, 'questions');
  if (!Object.keys(questions).length || Object.keys(questions).length > 100) throw new Error('Expected 1–100 questions.');
  for (const [name, q] of Object.entries(questions)) {
    if (!/^[\w-]{1,100}$/.test(name) || ['__proto__', 'constructor', 'prototype'].includes(name)) throw new Error('Invalid question name.');
    keys(q, ['type', 'instructions', 'criteria'], 'question'); string(q.instructions, 'question instructions');
    if (!['choice', 'score', 'noul', 'box'].includes(q.type)) throw new Error('Unknown decision question type.');
    if (q.type === 'score') {
      if (!Array.isArray(q.criteria) || q.criteria.length < 2 || q.criteria.length > 10) throw new Error('Score needs 2–10 ordered criteria.');
      q.criteria.forEach(v => string(v, 'score criterion'));
    } else if (q.type === 'choice' || (q.type === 'noul' && q.criteria !== undefined)) {
      object(q.criteria, 'question criteria'); const names = Object.keys(q.criteria);
      if (names.length < 2 || names.length > 100 || names.some(n => ['__proto__', 'constructor', 'prototype'].includes(n))) throw new Error('Expected 2–100 named criteria.');
      if (q.type === 'noul' && (names.length !== 2 || !names.includes('true') || !names.includes('false'))) throw new Error('Noul requires true and false criteria.');
      Object.values(q.criteria).forEach(v => string(v, 'criterion description'));
    } else if (q.criteria !== undefined) throw new Error('Unexpected box criteria.');
  }
  return questions;
}
export function validateAnswers(input, questions, source) {
  const answers = parseData(input, MAX_BYTES); object(answers, 'answers');
  if (Object.keys(answers).length !== Object.keys(questions).length || Object.keys(answers).some(k => !Object.hasOwn(questions, k))) throw new Error('Decision answers do not match questions.');
  for (const [name, a] of Object.entries(answers)) {
    keys(a, ['type', 'choice', 'score', 'noul', 'box', 'probabilities', 'confidence', 'legend', 'refusal'], 'answer'); const q = questions[name];
    if (a.type !== q.type) throw new Error('Decision answer type mismatch.');
    if (a.refusal) { string(a.refusal, 'refusal'); a.probabilities = null; continue; }
    if (q.type === 'choice') { if (typeof a.choice !== 'string' || !Object.hasOwn(q.criteria, a.choice)) throw new Error('Decision returned an unknown option.'); }
    else if (q.type === 'score') number(a.score, 'score answer', { max: q.criteria.length - 1 });
    else if (q.type === 'noul') number(a.noul, 'noul answer', { max: 1 });
    else {
      keys(a.box,['top','bottom','left','right'],'box');
      for(const key of ['top','bottom','left','right'])number(a.box[key],'box coordinate',{max:1});
      if (a.box.left > a.box.right || a.box.top > a.box.bottom) throw new Error('Invalid box bounds.');
    }
    if(a.confidence !== undefined)number(a.confidence,'confidence',{max:1});
    if (source === 'emulated') { a.probabilities = null; delete a.confidence; }
    else if (a.probabilities == null && ['choice','score'].includes(q.type)) throw new Error('Native decisions require probabilities.');
    else if (a.probabilities != null) {
      object(a.probabilities, 'probabilities');
      const expected = q.type === 'choice' ? Object.keys(q.criteria) : q.type === 'score' ? q.criteria.map((_, i) => String(i)) : ['true', 'false'];
      if (Object.keys(a.probabilities).length !== expected.length || expected.some(k => !Object.hasOwn(a.probabilities, k))) throw new Error('Invalid probability options.');
      Object.values(a.probabilities).forEach(v => number(v, 'probability', { max: 1 }));
      if (Math.abs(Object.values(a.probabilities).reduce((a, b) => a + b, 0) - 1) > .01) throw new Error('Probabilities must sum to one.');
    }
  }
  return answers;
}
export function decisionDriver({ route = 'openrouter', baseURL, fetchSource = globalThis.fetch } = {}) {
  const url = route === 'openrouter' ? 'https://openrouter.ai/api/alpha/decisions' : new URL('decisions', endpoint(baseURL)).href;
  return { async decide(request, key, model) {
    const started = performance.now();
    const raw = await jsonResponse(await fetchSource(url, requestOptions({ model: model.ref.slice(model.ref.indexOf(':') + 1), state: request.state, questions: request.questions, max_tokens: request.maxTokens }, key ? { Authorization: `Bearer ${key}` } : {}, request.signal)));
    const used = usage(raw.usage), cost = raw.cost ?? raw.usage?.cost ?? (used && model.prices ? (used.inputTokens * model.prices.input + used.outputTokens * model.prices.output) / 1e6 : null);
    if (cost !== null) number(cost, 'decision cost');
    return { answers: validateAnswers(raw.answers, request.questions, 'native'), usage: used, cost, timing: { totalMs: performance.now() - started, firstMs: null }, model: `${route}:${raw.model ?? model.ref.slice(model.ref.indexOf(':') + 1)}`, provider: raw.provider ?? route, source: 'native' };
  } };
}
