import { setTimeout as sleep } from 'node:timers/promises';

// HTTP 429 describes the request budget, not whether the payload was uploaded.
export async function checkLinks(rows, {
  fetchLink = globalThis.fetch,
  wait = sleep,
  log = console.log,
  now = Date.now,
  maxRetries = 3
} = {}) {
  const totals = { verified: 0, missing: 0, mismatched: 0, rateLimited: 0, errors: 0 };
  for (const row of rows) {
    if (row.inline) {
      totals.verified++;
      log(`ok       ${row.id} inline`);
      continue;
    }
    try {
      let response;
      for (let attempt = 0; ; attempt++) {
        response = await fetchLink(`https://256t.us/${row.cid}`, {
          cache: 'no-store', signal: AbortSignal.timeout(30_000)
        });
        if (response.status !== 429 || attempt >= maxRetries) break;
        // Consume the error body before waiting, releasing the connection.
        await response.text();
        const retryAfter = response.headers.get('retry-after');
        const seconds = retryAfter === null || retryAfter.trim() === '' ? NaN : Number(retryAfter);
        const date = Date.parse(retryAfter);
        const delay = Number.isFinite(seconds) && seconds >= 0
          ? seconds * 1000
          : Number.isFinite(date) ? date - now() : 15_000 * 2 ** attempt;
        // Without a usable Retry-After, back off 15, 30, then 60 s: together longer than the
        // host's one-minute window (30 requests per IP), so the last retry starts a fresh one.
        const milliseconds = Math.max(1000, delay);
        log(`WAIT     ${row.id} rate limited; retrying in ${Math.ceil(milliseconds / 1000)}s (${attempt + 1}/${maxRetries})`);
        await wait(milliseconds);
      }
      if (!response.ok) await response.text();
      let status;
      if (response.ok) {
        const matches = await response.text() === row.payload;
        status = matches ? 'ok' : 'MISMATCH';
        totals[matches ? 'verified' : 'mismatched']++;
      } else if (response.status === 404) {
        status = 'MISSING (HTTP 404)';
        totals.missing++;
      } else if (response.status === 429) {
        status = 'RATE LIMITED (HTTP 429; presence unconfirmed)';
        totals.rateLimited++;
      } else {
        status = `ERROR (HTTP ${response.status})`;
        totals.errors++;
      }
      log(`${status.padEnd(8)} ${row.id} ${row.title}`);
    } catch (error) {
      totals.errors++;
      log(`ERROR    ${row.id} ${error.message}`);
    }
  }
  const unresolved = totals.missing + totals.mismatched + totals.rateLimited + totals.errors;
  log(`\n${totals.verified}/${rows.length} QR links verified; ${totals.missing} missing, ${totals.mismatched} mismatched, ${totals.rateLimited} rate limited, ${totals.errors} errors`);
  return { ...totals, unresolved };
}
