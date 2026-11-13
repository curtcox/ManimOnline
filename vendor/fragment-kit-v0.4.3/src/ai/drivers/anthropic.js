import { jsonResponse, readEvents, normalizeResult, requestOptions } from './http.js';
export function anthropicDriver({ fetchSource = globalThis.fetch } = {}) {
  return { async generate(request, key, model) {
    const started = performance.now(); let first;
    const body = { model: model.ref.split(':').slice(1).join(':'), max_tokens: request.maxTokens, system: request.messages.filter(m => m.role === 'system').map(m => m.content).join('\n'), messages: request.messages.filter(m => m.role !== 'system'), stream: Boolean(request.onText) };
    const response = await fetchSource('https://api.anthropic.com/v1/messages', requestOptions(body, { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true' }, request.signal));
    let result;
    if (body.stream) {
      result = { text: '', usage: {} };
      await readEvents(response, chunk => {
        if (chunk.type === 'error') throw new Error('Anthropic could not complete the stream. Try again.');
        if (chunk.type === 'message_start') { result.model = 'anthropic:' + chunk.message.model; result.usage = { ...chunk.message.usage }; }
        if (chunk.type === 'content_block_delta' && chunk.delta?.type === 'text_delta') { first ??= performance.now(); result.text += chunk.delta.text; request.onText(chunk.delta.text); }
        if (chunk.type === 'message_delta') { Object.assign(result.usage, chunk.usage); result.finish = chunk.delta.stop_reason; }
      }, request);
    } else {
      const raw = await jsonResponse(response);
      if (!Array.isArray(raw.content)) throw new Error('Anthropic returned an invalid response.');
      result = { text: raw.content.filter(p => p.type === 'text').map(p => p.text).join(''), usage: raw.usage, model: 'anthropic:' + raw.model, finish: raw.stop_reason };
    }
    return normalizeResult(result, { model: model.ref, provider: 'anthropic', started, first, prices: model.prices });
  } };
}
