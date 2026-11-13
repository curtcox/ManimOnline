import { keys, parseData, string, number } from '../data.js';
import { isCID } from '../../core/cid.js';
const resultKeys = ['case', 'requestedModel', 'model', 'provider', 'repeat', 'promptHash', 'private', 'success', 'valid', 'cost', 'usage', 'timing', 'checks', 'changedRatio', 'outputHash', 'top2', 'source', 'answer', 'brier', 'logLoss', 'failure'];
export function parseReport(input) {
  const report = parseData(input, 1024 * 1024);
  keys(report, ['format', 'version', 'suiteCID', 'kitVersion', 'engineVersion', 'date', 'parameters', 'results'], 'report');
  if (report.format !== 'fragment-kit-eval-report' || report.version !== 1 || !isCID(report.suiteCID) || !Array.isArray(report.results) || report.results.length > 10000) throw new Error('Invalid evaluation report.');
  string(report.kitVersion, 'kit version', 100); if (report.engineVersion != null) string(report.engineVersion, 'engine version', 100); if (!Number.isFinite(Date.parse(report.date))) throw new Error('Invalid report date.');
  keys(report.parameters, ['maxTokens', 'repeats'], 'report parameters'); for (const value of Object.values(report.parameters)) number(value, 'report parameter', { min:1, integer:true });
  for (const r of report.results) {
    keys(r, resultKeys, 'report result'); string(r.case, 'case ID', 100); string(r.requestedModel, 'model', 2048);
    if (typeof r.success !== 'boolean' || typeof r.valid !== 'boolean' || !/^[a-f0-9]{64}$/.test(r.promptHash)) throw new Error('Invalid report result.');
    for (const field of ['model','provider','source','answer','failure']) if (r[field] != null) string(r[field], `result ${field}`, 2048);
    number(r.repeat, 'repeat', { integer:true });
    if (r.outputHash !== undefined && !/^[a-f0-9]{64}$/.test(r.outputHash)) throw new Error('Invalid output hash.');
    if (r.top2 != null && typeof r.top2 !== 'boolean') throw new Error('Invalid top-2 result.');
    if (r.private !== undefined && typeof r.private !== 'boolean') throw new Error('Invalid private result flag.');
    if (r.source != null && !['native','emulated'].includes(r.source)) throw new Error('Invalid decision source.');
    if (r.changedRatio != null) number(r.changedRatio, 'changed ratio', {max:1});
    if (r.brier != null) number(r.brier, 'Brier score', {max:2.000001});
    if (r.logLoss != null) number(r.logLoss, 'log loss');
    if (r.source !== 'native' && [r.top2,r.brier,r.logLoss].some(v=>v!=null)) throw new Error('Probability metrics require native decisions.');
    if (r.cost != null) number(r.cost, 'reported cost');
    if (r.usage != null) { keys(r.usage, ['inputTokens', 'outputTokens'], 'report usage'); number(r.usage.inputTokens, 'input tokens'); number(r.usage.outputTokens, 'output tokens'); }
    if (r.timing != null) { keys(r.timing, ['totalMs', 'firstMs'], 'report timing'); number(r.timing.totalMs, 'total time'); if (r.timing.firstMs != null) number(r.timing.firstMs, 'first output time'); }
    if (r.checks) { if (!Array.isArray(r.checks)) throw new Error('Invalid report checks.'); for (const c of r.checks) { keys(c, ['type', 'pass'], 'report check'); string(c.type, 'check type', 100); if (typeof c.pass !== 'boolean') throw new Error('Invalid check outcome.'); } }
  }
  return report;
}
export function createReport(run, { includePrivate = false, kitVersion = '0.4.3', engineVersion = null, parameters = run.parameters ?? {} } = {}) {
  return parseReport({ format: 'fragment-kit-eval-report', version: 1, suiteCID: run.suiteCID, kitVersion, engineVersion, date: new Date().toISOString(), parameters,
    results: run.results.filter(r => includePrivate || !r.private).map(r => Object.fromEntries(Object.entries(r).filter(([k]) => resultKeys.includes(k)))) });
}
