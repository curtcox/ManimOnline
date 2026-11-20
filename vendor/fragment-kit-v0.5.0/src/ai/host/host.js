import { prepareOpenRouterSignIn, handleAiCallback } from '../connections/oauth.js';
import { createAi } from '../client.js';
import { installAiHost } from './protocol.js';
import { createStorage } from '../../core/storage.js';
import { element } from '../../ui/dialog.js';
import { endpoint, sha256 } from '../data.js';
import { jsonResponse } from '../drivers/http.js';
const status = document.getElementById('host-status'), controls = document.getElementById('host-controls');
const noopType = { type: 'ai-host', normalize: value => value };
try {
  if (!handleAiCallback()) {
  const config = await jsonResponse(await fetch(new URL('../../../ai-host.config.json', import.meta.url)), 65536);
  const here = new URL(location.href), app = here.searchParams.get('app');
  const prefixFor = async origin => `${config.storagePrefix}-${(await sha256(origin)).slice(0, 24)}`;
  function credentialForm(onConnect, origin) {
    document.getElementById('host-app').textContent = `Allow AI requests from ${origin}. Prompts go to the selected provider. Each app has its own consent and budget.`;
    const route = element('select', null, { 'aria-label': 'Provider' });
    for (const value of config.routes.filter(r => ['openai', 'openrouter', 'anthropic', 'gemini'].includes(r))) route.append(element('option', value, { value }));
    const key = element('input', null, { type: 'password', autocomplete: 'off', 'aria-label': 'API key' });
    const remember = element('input', null, { type: 'checkbox', 'aria-label': 'Remember key on this AI host' });
    const rememberLabel = element('label', ' Remember this key on the separate AI host for this app. Host scripts can read remembered keys.'); rememberLabel.prepend(remember);
    const cap = element('input', null, { type: 'number', min: '0', step: '.01', value: '0', 'aria-label': 'App spending cap (USD)' });
    const approve = element('button', 'Allow this app and connect', { type: 'button' });
    approve.onclick = () => {
      const value = key.value; key.value = '';
      if (!value || !Number.isFinite(Number(cap.value)) || Number(cap.value) < 0) { status.textContent = 'Enter your key and a valid spending cap.'; return; }
      onConnect({ route: route.value, key: value, cap: Number(cap.value), remember: remember.checked });
    };
    const signIn=element('button','Sign in with OpenRouter',{type:'button'}); signIn.disabled=true;
    let oauth;
    if(config.routes.includes('openrouter')) {
      const callback=new URL(location.href);callback.search=callback.hash='';
      void prepareOpenRouterSignIn({callbackURL:callback.href,connect:(route,key)=>onConnect({route,key,cap:Number(cap.value),remember:remember.checked})}).then(prepared=>{oauth=prepared;signIn.disabled=false;});
      signIn.onclick=()=>{if(!Number.isFinite(Number(cap.value))||Number(cap.value)<0){status.textContent='Enter a valid spending cap.';return;}signIn.disabled=true;oauth.start().catch(()=>{status.textContent='Sign-in failed or was cancelled. Reopen the connection window to try again.';});};
    }
    controls.replaceChildren(element('p', 'Keys are kept for this session on this separate origin. Nothing is stored on the app origin.'), route, key, element('label', 'Maximum spend for this app (USD)'), cap, rememberLabel, approve);
    if(config.routes.includes('openrouter'))controls.append(signIn);
  }
  if (window.parent === window && app) {
    if (!config.allowedOrigins.includes(app) || !window.opener || endpoint(app).origin !== app) throw new Error('This app is not allowed to use this AI host.');
    // The opener is the host iframe, never the embedding app. Send credentials only over a direct same-origin port.
    const nonce = here.searchParams.get('session');
    credentialForm(async credentials => {
      const storage = createStorage({ prefix: await prefixFor(app) });
      const name = `ai:connection:${credentials.route}`;
      try { if (credentials.remember) storage.setItem(name, JSON.stringify(credentials)); else storage.removeItem(name); } catch { status.textContent = 'Storage is unavailable. The key will be shared with the host frame for this session only.'; }
      const channel = new MessageChannel();
      channel.port1.onmessage = event => { if (event.data === 'ready') { channel.port1.postMessage(credentials); channel.port1.close(); window.close(); } };
      window.opener.postMessage({ type: 'fragment-kit-ai-host-credentials', nonce }, here.origin, [channel.port2]);
    }, app);
  } else if (window.parent !== window) {
    const approvedModels = new Map();
    installAiHost({ authorizeDownload: (origin, cid) => approvedModels.get(origin)?.has(cid) === true, onModel: ({ ai, origin, cid, manifest, bytes }) => {
      const info = element('p', `${manifest.name}: ${bytes} bytes; licence ${manifest.license.id} (${manifest.license.url}); source ${manifest.source}; memory ${manifest.requires.memoryBytes} bytes; mirrors ${JSON.stringify(manifest.mirrors)}. Hash verification proves unchanged bytes, not model quality.`);
      const approve = element('button', 'Approve and download this model on the AI host', { type: 'button' });
      approve.onclick = async () => { try { await ai.downloadModel(cid, { consent: true }); const approved = approvedModels.get(origin) ?? new Set(); approved.add(cid); approvedModels.set(origin, approved); ai.consent('This device'); status.textContent = 'Verified model downloaded on the host. Return to the app.'; } catch (error) { status.textContent = error.message; } }; controls.append(info, approve);
    }, allowedOrigins: config.allowedOrigins, createClient: async origin => {
      const prefix = await prefixFor(origin);
      const ai = await createAi({ config: { name: config.name, canonicalOrigin: here.origin + '/', storagePrefix: prefix, ai: { deployments: { [here.origin + '/']: { connection: 'direct' } }, routes: config.routes, models: config.models, budget: { total: 0, day: 0, month: 0 } } }, type: noopType, storage: createStorage({ prefix }) });
      const storage = createStorage({ prefix });
      for (const route of config.routes) {
        const raw = storage.getItem(`ai:connection:${route}`); if (!raw) continue;
        try { const saved = JSON.parse(raw); ai.connect(route, saved.key); ai.budget.configure({ total: saved.cap, day: saved.cap, month: saved.cap }); for (const model of await ai.models()) if (model.ref.startsWith(route + ':')) ai.consent(model.destination); } catch { storage.removeItem(`ai:connection:${route}`); }
      }
      return ai;
    }, onConnection: ({ ai, origin }) => {
      let popup, nonce;
      const button = element('button', 'Connect on AI host', { type: 'button' });
      button.onclick = () => {
        nonce = crypto.randomUUID(); const url = new URL(location.href); url.search = new URLSearchParams({ app: origin, session: nonce }).toString();
        popup = window.open(url.href, '_blank', 'popup,width=560,height=720');
        status.textContent = popup ? 'Connect in the host window, then return to the app.' : 'Allow popups and try again.';
      };
      const forget = element('button', 'Forget this app on the AI host', { type: 'button' });
      forget.onclick = async () => { ai.disconnect(); const storage = createStorage({ prefix: await prefixFor(origin) }); for (const route of config.routes) storage.removeItem(`ai:connection:${route}`); approvedModels.delete(origin); status.textContent = 'App credentials and consent removed from this host.'; };
      controls.replaceChildren(button, forget); document.getElementById('host-app').textContent = `Connection for ${origin}`;
      window.addEventListener('message', event => {
        if (event.origin !== here.origin || event.source !== popup || event.data?.type !== 'fragment-kit-ai-host-credentials' || event.data.nonce !== nonce || event.ports.length !== 1) return;
        const port = event.ports[0]; nonce = null;
        port.onmessage = async message => {
          try {
            const { route, key, cap } = message.data; ai.connect(route, key); ai.budget.configure({ total: cap, day: cap, month: cap });
            for (const model of await ai.models()) if (model.ref.startsWith(route + ':')) ai.consent(model.destination);
            status.textContent = 'Connected for this app and session. Return to Ask to send your request.';
          } catch { status.textContent = 'Connection failed. Try again.'; } finally { port.close(); }
        }; port.postMessage('ready');
      });
    } });
  } else status.textContent = 'Open AI settings from an allowed app to connect.';
  }
} catch (error) { status.textContent = error.message; }
