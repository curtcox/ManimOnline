import { jsonResponse, readEvents, normalizeResult, requestOptions } from './http.js';
import { endpoint } from '../data.js';
export function compatibleDriver({ baseURL, provider, fetchSource = globalThis.fetch, title = '' }) {
  const base = endpoint(baseURL); if (!base.pathname.endsWith('/')) throw new Error('AI base URL must end in /.');
  return { async generate(request, key, model) {
    const started = performance.now(); let first, result;
    const headers = { ...(key ? { Authorization: `Bearer ${key}` } : {}), ...(provider === 'openrouter' ? { 'X-Title': title } : {}) };
    const body = { model: model.ref.slice(model.ref.indexOf(':') + 1), messages: request.messages, max_completion_tokens: request.maxTokens, stream: Boolean(request.onText) };
    if (provider !== 'openai') { body.max_tokens = body.max_completion_tokens; delete body.max_completion_tokens; }
    if (request.schema) body.response_format = { type: 'json_schema', json_schema: { name: 'response', strict: true, schema: request.schema } };
    if (body.stream) body.stream_options = { include_usage: true };
    const response = await fetchSource(new URL('chat/completions', base).href, requestOptions(body, headers, request.signal));
    if (body.stream) {
      result = { text: '', model: model.ref };
      await readEvents(response, chunk => {
        if (chunk.error) throw new Error('The provider could not complete the stream. Try another model.');
        const delta = chunk.choices?.[0]?.delta?.content;
        if (typeof delta === 'string') { first ??= performance.now(); result.text += delta; request.onText(delta); }
        if (chunk.usage) result.usage = chunk.usage;
        if (chunk.model) result.model = `${provider}:${chunk.model}`;
        if (chunk.provider) result.provider = chunk.provider;
        if (chunk.choices?.[0]?.finish_reason) result.finish = chunk.choices[0].finish_reason;
      }, request);
      if (!result.usage) throw new Error('AI stream ended without usage. Its cost reservation has been retained.');
    } else {
      const raw = await jsonResponse(response);
      if (raw.error || typeof raw.choices?.[0]?.message?.content !== 'string') throw new Error('The provider returned an invalid response.');
      result = { text: raw.choices[0].message.content, usage: raw.usage, finish: raw.choices[0].finish_reason, model: `${provider}:${raw.model ?? body.model}`, provider: raw.provider };
    }
    return normalizeResult(result, { model: model.ref, provider, started, first, prices: model.prices });
  } };
}
