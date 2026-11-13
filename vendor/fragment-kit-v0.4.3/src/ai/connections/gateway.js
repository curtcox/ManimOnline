import { endpoint, number } from '../data.js';
import { jsonResponse, readEvents, normalizeResult, requestOptions, usage } from '../drivers/http.js';
import { validateAnswers } from '../drivers/decisions.js';
export function gatewayConnection({ deployment, getAuthorization, fetchSource = globalThis.fetch }) {
  const base = endpoint(deployment.url);
  async function headers() {
    const value = await getAuthorization?.();
    if (typeof value !== 'string' || !value.trim() || /[\r\n]/.test(value)) throw new Error('Gateway needs short-lived authorization from this site.');
    return { Authorization: value };
  }
  return {
    connect() { throw new Error('Gateway authorization is supplied by this site.'); }, disconnect() {},
    async models({ signal } = {}) { const result = await jsonResponse(await fetchSource(new URL('v1/models', base), { headers: await headers(), signal, credentials: 'omit', redirect: 'error' })); if (!Array.isArray(result.models)) throw new Error('Gateway returned an invalid model list.'); return result.models; },
    async call(kind, request, model) {
      const started = performance.now(); let first, result;
      const { onText, signal, confirmedCost, ...body } = request;
      const response = await fetchSource(new URL(`v1/${kind}`, base), requestOptions({ ...body, stream: kind === 'generate' }, await headers(), signal));
      if (kind === 'generate') {
        await readEvents(response, (value, event) => {
          if (event === 'text') { if (typeof value.text !== 'string') throw new Error('Gateway sent an invalid text event.'); first ??= performance.now(); onText?.(value.text); }
          else if (event === 'result') { if (result) throw new Error('Gateway sent multiple results.'); result = value; }
          else if (event === 'error') throw new Error('Gateway could not complete the request.');
        }, { signal });
        if (!result) throw new Error('Gateway ended without a result.');
        return normalizeResult(result, { started, first, model: model.ref, provider: 'gateway', requireCost: true });
      }
      result = await jsonResponse(response);
      if (!usage(result.usage)) throw new Error('Gateway decisions require usage.'); number(result.cost, 'gateway cost');
      if (!['native', 'emulated'].includes(result.source)) throw new Error('Gateway returned an invalid decision source.');
      return { ...result, answers: validateAnswers(result.answers, request.questions, result.source) };
    },
  };
}
