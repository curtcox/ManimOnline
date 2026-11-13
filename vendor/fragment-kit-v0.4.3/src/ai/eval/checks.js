import { keys, pointer, string, number } from '../data.js';
export function validateCheck(check) {
  keys(check, ['type', 'text', 'pattern', 'path', 'value', 'fields', 'ratio', 'name', 'expected'], 'check');
  if (!['valid', 'contains', 'notContains', 'regex', 'fieldEquals', 'unchangedFields', 'maxChangedRatio', 'site'].includes(check.type)) throw new Error('Unknown evaluation check.');
  if (['contains', 'notContains'].includes(check.type)) string(check.text, 'check text');
  if (check.type === 'regex') {
    string(check.pattern, 'pattern', 256);
    // No repetitions, grouping, backreferences or lookaround from untrusted suites.
    if (/[()*+?{}]|\\[1-9]/.test(check.pattern)) throw new Error('Evaluation regex supports no repetition or grouping. Use a site check.');
    new RegExp(check.pattern, 'u');
  }
  if (check.type === 'fieldEquals') string(check.path, 'field path');
  if (check.type === 'unchangedFields' && (!Array.isArray(check.fields) || check.fields.length > 100 || check.fields.some(f => typeof f !== 'string' || !f.startsWith('/')))) throw new Error('Invalid unchanged fields.');
  if (check.type === 'maxChangedRatio') number(check.ratio, 'changed ratio', { max: 1 });
  if (check.type === 'site') string(check.name, 'site check name', 100);
  return check;
}
export function changedRatio(a, b) {
  let start = 0, end = 0;
  while (start < Math.min(a.length, b.length) && a[start] === b[start]) start++;
  while (end < Math.min(a.length, b.length) - start && a[a.length - end - 1] === b[b.length - end - 1]) end++;
  return (Math.max(a.length, b.length) - start - end) / Math.max(1, a.length, b.length);
}
export async function checkDocument({ type, base, document, checks, signal }) {
  const results = [];
  for (const check of checks) {
    signal?.throwIfAborted(); validateCheck(check); let pass;
    switch (check.type) {
      case 'valid': pass = true; break;
      case 'contains': pass = document.src.includes(check.text); break;
      case 'notContains': pass = !document.src.includes(check.text); break;
      case 'regex': pass = new RegExp(check.pattern, 'u').test(document.src); break;
      case 'fieldEquals': pass = JSON.stringify(pointer(document, check.path).value) === JSON.stringify(check.value); break;
      case 'unchangedFields': pass = check.fields.every(path => JSON.stringify(pointer(document, path).value) === JSON.stringify(pointer(base, path).value)); break;
      case 'maxChangedRatio': pass = changedRatio(base.src, document.src) <= check.ratio; break;
      case 'site': {
        const fn = type.ai?.checks?.[check.name]; if (typeof fn !== 'function' || !Object.hasOwn(type.ai.checks, check.name)) throw new Error('Unknown site evaluation check.');
        pass = (await fn({ base: structuredClone(base), document: structuredClone(document), expected: check.expected, signal })) === true; break;
      }
    }
    results.push({ type: check.type, pass });
  }
  return { pass: results.every(r => r.pass), checks: results };
}
