import { AiError } from '../errors.js';
import { readResponse, text, MAX_BYTES, bounded } from '../../core/bytes.js';
import { abort, number, string } from '../data.js';
export async function jsonResponse(response, maxBytes = MAX_BYTES) {
  if (!response.ok) {
    await response.body?.cancel();
    const action = response.status === 401 || response.status === 403 ? 'Reconnect with a valid key.' : response.status === 402 ? 'Add credit or choose another route.' : response.status === 429 ? 'Wait and try again.' : 'Try again or choose paste handoff.';
    throw new AiError(({401:'authorization',403:'authorization',402:'credit',429:'rate-limit',404:'model-unavailable',413:'size'})[response.status] ?? 'provider', `AI request failed (HTTP ${response.status}). ${action}`, {status:response.status});
  }
  return JSON.parse(text(await readResponse(response, maxBytes)));
}
/** Bounded SSE decoder, including CRLF and UTF-8 sequences split across chunks. */
export async function readEvents(response, onEvent, { signal, maxBytes = MAX_BYTES } = {}) {
  if (!response.ok) return jsonResponse(response, maxBytes);
  const reader = response.body.getReader(), decoder = new TextDecoder('utf-8', { fatal: true });
  let buffer = '', size = 0;
  function consume(final = false) {
    let match;
    while ((match = /\r?\n\r?\n/.exec(buffer))) {
      const block = buffer.slice(0, match.index); buffer = buffer.slice(match.index + match[0].length);
      const lines = block.split(/\r?\n/), data = lines.filter(l => l.startsWith('data:')).map(l => l.slice(5).replace(/^ /, '')).join('\n');
      if (data && data !== '[DONE]') onEvent(JSON.parse(data), lines.find(l => l.startsWith('event:'))?.slice(6).trim() ?? 'message');
    }
    if (final && buffer.trim() && !buffer.trim().startsWith(':')) throw new Error('AI stream ended with an incomplete event.');
  }
  const stop = () => { void reader.cancel().catch(() => {}); };
  signal?.addEventListener('abort', stop, { once: true });
  try {
    while (true) {
      abort(signal); const { value, done } = await reader.read(); abort(signal);
      if (done) break;
      size += value.byteLength; if (size > maxBytes) throw new Error('AI stream exceeds the byte limit.');
      buffer += decoder.decode(value, { stream: true }); consume();
    }
    buffer += decoder.decode(); consume(true);
  } finally { signal?.removeEventListener('abort', stop); await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
export function usage(value) {
  if (!value) return null;
  return { inputTokens: number(value.inputTokens ?? value.prompt_tokens ?? value.input_tokens, 'input usage'), outputTokens: number(value.outputTokens ?? value.completion_tokens ?? value.output_tokens, 'output usage') };
}
export function normalizeResult(value, { model, provider, started, first, prices, maxBytes = MAX_BYTES, requireCost = false } = {}) {
  const content = bounded(value.text ?? '', maxBytes); if (typeof content !== 'string') throw new Error('AI output must be text.');
  const used = usage(value.usage);
  let cost = value.cost ?? value.usage?.cost ?? (used && prices ? (used.inputTokens * prices.input + used.outputTokens * prices.output) / 1e6 : null);
  if (requireCost && (cost === null || !used)) throw new Error('Gateway results require usage and cost.');
  if (cost !== null) cost = number(cost, 'actual cost');
  let json = null; try { json = JSON.parse(content); } catch { /* Ordinary generation may return text. */ }
  return { text: content, json, usage: used, cost, finish: value.finish ?? 'stop', timing: { totalMs: performance.now() - started, firstMs: first == null ? null : first - started }, model: string(value.model ?? model, 'resolved model'), provider: value.provider ?? provider };
}
export function requestOptions(body, headers, signal) {
  return { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body), signal, credentials: 'omit', redirect: 'error', referrerPolicy: 'no-referrer' };
}
