const { test } = require('node:test');
const assert = require('node:assert/strict');

const row = (id = 'q01-01') => ({ id, title: 'Example', cid: id, payload: `payload for ${id}` });
const load = () => import('../video-series/tools/check-links.mjs');

test('checks 61 uploaded payloads plus inline content across two rate-limit resets', async () => {
  const { checkLinks } = await load();
  const rows = Array.from({ length: 61 }, (_, i) => row(`q${i}`));
  rows.push({ ...row('inline'), inline: true });
  const waits = [], logs = [], requests = [];
  let budget = 30;
  const result = await checkLinks(rows, {
    fetchLink: async (url, options) => {
      requests.push(url);
      assert.equal(options.cache, 'no-store');
      assert.ok(options.signal instanceof AbortSignal);
      if (!budget) return new Response('Rate limited', { status: 429, headers: { 'Retry-After': '60' } });
      budget--;
      return new Response(`payload for ${url.split('/').pop()}`);
    },
    wait: async delay => { waits.push(delay); budget = 30; },
    log: line => logs.push(line)
  });
  assert.deepEqual(result, { verified: 62, missing: 0, mismatched: 0, rateLimited: 0, errors: 0, unresolved: 0 });
  assert.deepEqual(waits, [60_000, 60_000]);
  assert.equal(requests.length, 63);
  assert.ok(logs.every(line => !line.includes('MISSING')));
  assert.equal(logs.filter(line => line.startsWith('WAIT')).length, 2);
  assert.equal(requests.filter(url => url.endsWith('/q30')).length, 2);
  assert.equal(requests.filter(url => url.endsWith('/q60')).length, 2);
});

test('distinguishes missing content, mismatches, server errors, and exhausted throttling', async () => {
  const { checkLinks } = await load();
  const responses = [new Response(null, { status: 404 }), new Response('wrong bytes'),
    new Response(null, { status: 503 }), new Response('Rate limited', { status: 429 })];
  const logs = [];
  const result = await checkLinks(responses.map((_, i) => row(String(i))), {
    fetchLink: async () => responses.shift(), maxRetries: 0, log: line => logs.push(line)
  });
  assert.deepEqual(result, { verified: 0, missing: 1, mismatched: 1, rateLimited: 1, errors: 1, unresolved: 4 });
  assert.equal(logs.filter(line => line.startsWith('MISSING')).length, 1);
  assert.ok(logs.some(line => line.includes('presence unconfirmed')));
  assert.ok(logs.some(line => line.startsWith('ERROR (HTTP 503)')));
});

test('honors an HTTP-date Retry-After and bounds retries with backoff when absent or invalid', async () => {
  const { checkLinks } = await load();
  const now = Date.parse('2026-10-17T12:00:00Z');
  for (const header of ['Sat, 17 Oct 2026 12:00:05 GMT', null, '', 'invalid']) {
    let requests = 0;
    const waits = [];
    const result = await checkLinks([row()], {
      fetchLink: async () => {
        requests++;
        return new Response('Rate limited', { status: 429, headers: header === null ? {} : { 'Retry-After': header } });
      },
      now: () => now, wait: async delay => waits.push(delay), log: () => {}
    });
    assert.equal(requests, 4);
    assert.deepEqual(waits, header?.startsWith('Sat') ? [5000, 5000, 5000] : [15_000, 30_000, 60_000]);
    assert.equal(result.rateLimited, 1);
    assert.equal(result.missing, 0);
    assert.equal(result.unresolved, 1);
  }
});

test('network and response-body errors stay errors, while inline payloads never fetch', async () => {
  const { checkLinks } = await load();
  let requests = 0;
  const result = await checkLinks([row('offline'), row('broken'), { ...row('inline'), inline: true }], {
    fetchLink: async () => {
      if (++requests === 1) throw new Error('Offline');
      return { status: 200, ok: true, text: async () => { throw new Error('Truncated body'); } };
    }, log: () => {}
  });
  assert.deepEqual(result, { verified: 1, missing: 0, mismatched: 0, rateLimited: 0, errors: 2, unresolved: 2 });
  assert.equal(requests, 2);
});
