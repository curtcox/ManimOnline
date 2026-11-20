import { parseData, keys, string } from '../data.js';
import { validateQuestions } from '../drivers/decisions.js';
import { validateDocument } from '../change/apply.js';
import { validateCheck, checkDocument } from './checks.js';
export function parseSuite(input, type) {
  const suite = parseData(input, 1024 * 1024);
  keys(suite, ['format', 'version', 'app', 'cases'], 'suite');
  if (suite.format !== 'fragment-kit-eval-suite' || suite.version !== 1 || suite.app !== type.type || !Array.isArray(suite.cases) || !suite.cases.length || suite.cases.length > 1000) throw new Error('Invalid evaluation suite.');
  const ids = new Set();
  for (const c of suite.cases) {
    keys(c, ['id', 'kind', 'base', 'request', 'checks', 'reference', 'question', 'state', 'expected', 'private'], 'case');
    string(c.id, 'case ID', 100); if (ids.has(c.id)) throw new Error('Duplicate evaluation case.'); ids.add(c.id);
    if (c.private !== undefined && typeof c.private !== 'boolean') throw new Error('Invalid private case flag.');
    if (c.kind === 'change') {
      c.base = validateDocument(type, c.base); string(c.request, 'case request');
      if (!Array.isArray(c.checks) || !c.checks.length || c.checks.length > 100) throw new Error('Expected bounded checks.'); c.checks.forEach(validateCheck);
      keys(c.reference, ['good', 'bad'], 'references');
      c.reference.good = validateDocument(type, c.reference.good);
      // Bad references may deliberately fail the adapter.
      if (!c.reference.bad || typeof c.reference.bad.src !== 'string') throw new Error('Missing bad reference.');
    } else if (c.kind === 'decision') {
      validateQuestions({ answer: c.question });
      if (c.question.type !== 'choice' || !Array.isArray(c.expected) || !c.expected.length || c.expected.some(id => !Object.hasOwn(c.question.criteria, id))) throw new Error('Decision cases require known choice IDs.');
    } else throw new Error('Unknown evaluation case kind.');
  }
  return suite;
}
export async function validateReferences(suite, type) {
  for (const c of suite.cases.filter(c => c.kind === 'change')) {
    const good = await checkDocument({ type, base: c.base, document: validateDocument(type, c.reference.good), checks: c.checks });
    if (!good.pass) throw new Error(`Good reference fails: ${c.id}.`);
    let badPass = false;
    try { badPass = (await checkDocument({ type, base: c.base, document: validateDocument(type, c.reference.bad), checks: c.checks })).pass; } catch { /* A structurally invalid bad reference correctly fails. */ }
    if (badPass) throw new Error(`Bad reference passes: ${c.id}.`);
  }
}
