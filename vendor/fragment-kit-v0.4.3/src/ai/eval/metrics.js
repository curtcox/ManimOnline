export function wilson(success, n, z = 1.96) {
  if (!n) return { low: 0, high: 1 };
  const p = success / n, d = 1 + z * z / n, center = (p + z * z / (2 * n)) / d, radius = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return { low: Math.max(0, center - radius), high: Math.min(1, center + radius) };
}
export function probabilityMetrics(probabilities, expected) {
  if (!probabilities) return { brier: null, logLoss: null };
  return { brier: Object.entries(probabilities).reduce((sum, [id, p]) => sum + (p - Number(id === expected)) ** 2, 0), logLoss: -Math.log(Math.max(1e-15, probabilities[expected] ?? 0)) };
}
export function metrics(results) {
  const models = [...new Set(results.map(r => r.requestedModel))];
  const rows = models.map(model => {
    const entries = results.filter(r => r.requestedModel === model), n = entries.length, successes = entries.filter(r => r.success).length;
    const cost = entries.reduce((sum, r) => sum + (r.cost ?? 0), 0), costsKnown = entries.every(r => r.cost != null);
    const groups = [...new Set(entries.map(r => r.case))].map(id => entries.filter(r => r.case === id));
    const agreements = groups.filter(g => g.length > 1).map(g => { const values = g.map(r => r.outputHash ?? r.answer ?? r.failure); return Math.max(...[...new Set(values)].map(v => values.filter(x => x === v).length)) / values.length; });
    const native = entries.filter(r => r.source === 'native' && r.brier != null);
    return { model, n, successes, successRate: successes / n, interval: wilson(successes, n), validRate: entries.filter(r => r.valid).length / n,
      cost: costsKnown ? cost : null, costPerSuccess: costsKnown && successes ? cost / successes : null,
      refusalRate: entries.filter(r => r.failure === 'refusal').length / n,
      repeatAgreement: agreements.length ? agreements.reduce((a,b) => a+b,0) / agreements.length : null,
      top2: entries.some(r => r.top2 != null) ? entries.filter(r => r.top2 === true).length / entries.filter(r => r.top2 != null).length : null,
      changedRatio: entries.some(r => r.changedRatio != null) ? entries.filter(r => r.changedRatio != null).reduce((a,r) => a+r.changedRatio,0) / entries.filter(r => r.changedRatio != null).length : null,
      totalMs: entries.reduce((sum, r) => sum + (r.timing?.totalMs ?? 0), 0) / n,
      brier: native.length ? native.reduce((sum, r) => sum + r.brier, 0) / native.length : null,
      logLoss: native.length ? native.reduce((sum, r) => sum + r.logLoss, 0) / native.length : null,
      failures: Object.fromEntries([...new Set(entries.filter(r => r.failure).map(r => r.failure))].map(f => [f, entries.filter(r => r.failure === f).length])),
    };
  }).sort((a, b) => b.successRate - a.successRate || (a.costPerSuccess ?? Infinity) - (b.costPerSuccess ?? Infinity));
  return { rows, best: rows.length > 1 && rows.slice(1).every(r => rows[0].interval.low > r.interval.high) ? rows[0].model : null, conclusion: rows.length < 2 ? 'Add another model to compare.' : rows.slice(1).every(r => rows[0].interval.low > r.interval.high) ? 'Success intervals separate.' : 'Not enough evidence to separate these models.' };
}
