import { string } from './data.js';
export async function chooseSample({ ai, catalog, request, model, signal, confirmedCost, limit = 20 }) {
  string(request, 'sample request');
  if (!Array.isArray(catalog) || catalog.length > 10000 || !Number.isInteger(limit) || limit < 2 || limit > 100) throw new Error('Invalid sample catalog or limit.');
  const terms = request.toLowerCase().split(/\W+/).filter(Boolean);
  const entries = catalog.map(entry => {
    string(entry.id, 'sample ID', 100); string(entry.title, 'sample title');
    return { id: entry.id, title: entry.title, description: entry.description ?? '', tags: entry.tags ?? [], useCases: entry.useCases ?? [] };
  });
  if (new Set(entries.map(e => e.id)).size !== entries.length) throw new Error('Duplicate sample ID.');
  const narrowed = entries.map(entry => ({ ...entry, score: terms.reduce((n, t) => n + (JSON.stringify(entry).toLowerCase().includes(t) ? 1 : 0), 0) })).sort((a, b) => b.score - a.score).slice(0, limit);
  if (!ai || !model || narrowed.length < 2) return narrowed.map(({ score, ...entry }) => ({ ...entry, probability: null, source: 'search' }));
  const options = Object.fromEntries(narrowed.map(({ score, ...entry }) => [entry.id, JSON.stringify(entry)]));
  const result = await ai.decide({ model, state: request, questions: { sample: { type: 'choice', instructions: 'Which sample best matches this request?', criteria: options } }, signal, confirmedCost });
  const answer = result.answers.sample;
  return narrowed.map(({ score, ...entry }) => ({ ...entry, probability: answer.probabilities?.[entry.id] ?? null, selected: answer.choice === entry.id, source: result.source })).sort((a, b) => (b.probability ?? Number(b.selected)) - (a.probability ?? Number(a.selected)));
}
