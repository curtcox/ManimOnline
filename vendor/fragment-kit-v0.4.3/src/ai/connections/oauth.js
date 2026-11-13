import { encode64, bytes } from '../../core/bytes.js';
import { endpoint, string } from '../data.js';
import { jsonResponse, requestOptions } from '../drivers/http.js';
/** Call before parsing document URLs. No key travels through this callback. */
export function handleAiCallback({ window = globalThis.window } = {}) {
  const url = new URL(window.location.href);
  const denied = url.searchParams.has('error');
  if ((!url.searchParams.has('code') || !url.searchParams.has('state')) && !(denied && window.opener)) return false;
  const code = url.searchParams.get('code'), state = url.searchParams.get('state');
  for (const k of ['code', 'state', 'error', 'error_description']) url.searchParams.delete(k);
  window.history.replaceState(null, '', url.href);
  if (!denied) { string(code, 'authorization code', 8192); string(state, 'authorization state', 1024); }
  if (!window.opener) throw new Error('AI sign-in needs its original popup. Reopen sign-in from Ask.');
  window.opener.postMessage({ type: 'fragment-kit-ai-oauth', ...(denied ? {error:true} : {code,state}) }, url.origin); window.close(); return true;
}
/** Prepare PKCE before enabling Connect; start() must run synchronously in its click. */
export async function prepareOpenRouterSignIn({ callbackURL, connect, window = globalThis.window, fetchSource = globalThis.fetch, timeout = 600000 } = {}) {
  const callback = endpoint(callbackURL), verifier = encode64(crypto.getRandomValues(new Uint8Array(32))), state = encode64(crypto.getRandomValues(new Uint8Array(32)));
  const challenge = encode64(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes(verifier))));
  const url = new URL('https://openrouter.ai/auth');
  url.search = new URLSearchParams({ callback_url: callback.href, code_challenge: challenge, code_challenge_method: 'S256', state }).toString();
  let used = false;
  return { start() {
    if (used) throw new Error('Prepare a new sign-in before trying again.'); used = true;
    let popup;
    const result = new Promise((resolve, reject) => {
      const timer = setTimeout(() => finish(new Error('AI sign-in timed out. Try again.')), timeout);
      const finish = (error) => { clearTimeout(timer); window.removeEventListener('message', receive); popup?.close(); error ? reject(error) : resolve(); };
      const receive = async event => {
        if (event.origin !== callback.origin || event.source !== popup || event.data?.type !== 'fragment-kit-ai-oauth') return;
        if (event.data.error) { finish(new Error('AI sign-in was cancelled or denied. Try again.')); return; }
        if (event.data.state !== state) { finish(new Error('AI sign-in state did not match.')); return; }
        window.removeEventListener('message', receive);
        try {
          string(event.data.code, 'authorization code', 8192);
          const raw = await jsonResponse(await fetchSource('https://openrouter.ai/api/v1/auth/keys', requestOptions({ code: event.data.code, code_verifier: verifier, code_challenge_method: 'S256' }, {}, AbortSignal.timeout(20000))));
          string(raw.key, 'API key', 8192); connect('openrouter', raw.key); finish();
        } catch { finish(new Error('AI sign-in failed. Try again or paste your own key.')); }
      };
      window.addEventListener('message', receive);
      popup = window.open(url.href, '_blank', 'popup,width=560,height=720');
      if (!popup) finish(new Error('AI sign-in popup was blocked. Allow popups and try again.'));
    });
    return result;
  } };
}
