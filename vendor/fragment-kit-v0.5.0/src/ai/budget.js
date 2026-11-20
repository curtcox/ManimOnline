import { bytes } from '../core/bytes.js';
import { number, parseData, keys } from './data.js';
export function estimateCost({ messages, maxTokens, prices, confirmedCost }) {
  number(maxTokens, 'maxTokens', { min: 1, max: 1000000, integer: true });
  if (!prices) {
    if (confirmedCost === undefined) throw new Error('Price is unknown. Confirm a maximum cost before sending.');
    return number(confirmedCost, 'confirmed cost', { min: 0.000001 });
  }
  number(prices.input, 'input price'); number(prices.output, 'output price');
  // A UTF-8 byte per token plus generous message framing is deliberately conservative.
  return ((bytes(JSON.stringify(messages)).length + 1024) * prices.input + maxTokens * prices.output) / 1e6;
}
export function createBudget({ total = 0, day = total, month = total, storage, now = () => new Date() } = {}) {
  const caps = { total, day, month }; Object.values(caps).forEach(n => number(n, 'budget'));
  let records = [];
  if (storage) {
    const raw = storage.getItem('ai:budget');
    if (raw !== null) {
      const parsed = parseData(raw, 1024 * 1024);
      if (!Array.isArray(parsed) || parsed.length > 10000) throw new Error('Invalid AI budget ledger.');
      records = parsed.map(r => { keys(r, ['date', 'cost'], 'ledger'); if (!/^\d{4}-\d{2}-\d{2}$/.test(r.date)) throw new Error('Invalid ledger date.'); number(r.cost, 'ledger cost'); return r; });
    }
  }
  const persist = () => { if (storage) storage.setItem('ai:budget', JSON.stringify(records)); };
  const date = () => now().toISOString().slice(0, 10);
  const spent = () => Object.fromEntries(Object.keys(caps).map(period => [period, records.filter(r => period === 'total' || r.date.slice(0, period === 'day' ? 10 : 7) === date().slice(0, period === 'day' ? 10 : 7)).reduce((n, r) => n + r.cost, 0)]));
  return Object.freeze({ get caps() { return Object.freeze({ ...caps }); }, spent,
    configure(next) {
      keys(next, ['total', 'day', 'month'], 'budget');
      for (const period of Object.keys(caps)) number(next[period], 'budget');
      Object.assign(caps, next);
    },
    reserve(cost) {
      number(cost, 'estimated cost');
      if (records.length >= 10000) throw new Error('AI budget ledger is full. Export it before starting another ledger.');
      const used = spent();
      if (Object.keys(caps).some(p => used[p] + cost > caps[p] + 1e-12)) throw new Error('AI budget reached. Increase the cap or wait for it to reset.');
      const record = { date: date(), cost }; records.push(record);
      try { persist(); } catch (error) { records.pop(); throw error; }
      let settled = false;
      return { settle(actual) {
        if (settled) throw new Error('Budget reservation already settled.');
        number(actual, 'actual cost');
        // Retain the conservative reservation if persistence fails.
        const previous = record.cost; record.cost = actual;
        try { persist(); settled = true; } catch (error) { record.cost = previous; throw error; }
      } };
    },
  });
}
