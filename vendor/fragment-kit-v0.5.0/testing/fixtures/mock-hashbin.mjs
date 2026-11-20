import { computeCID } from '../../src/core/cid.js';
/** Inject as a module route. Uses the real CID implementation copied into the mock. */
export const mockHashBinSDK = `
async function cid(text) {
  const bytes = new TextEncoder().encode(text), prefix = new Uint8Array(6);
  let length = bytes.length;
  for (let i = 5; i >= 0; i--) { prefix[i] = length % 256; length = Math.floor(length / 256); }
  const encode = value => btoa(String.fromCharCode(...value)).replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');
  return encode(prefix) + encode(bytes.length <= 64 ? bytes : new Uint8Array(await crypto.subtle.digest('SHA-512', bytes)));
}
export class HashBinClient {
  constructor(options) { this.options = options; }
  publish(content, {clientState}) {
    window.__publishEntered = true;
    if (window.__publishMode === 'cancel') return Promise.reject(new Error('access_denied'));
    if (window.__publishMode === 'closed') return Promise.reject(new Error('Publish window closed.'));
    return cid(content).then(value => {
      if (window.__publishMode === 'redirect') {
        this.options.transactionStorage.setItem('mock-publish', JSON.stringify({cid:value,clientState}));
        location.hash = 'hashbin_publish=mock'; return {redirected:true};
      }
      return {cid:value};
    });
  }
  async handlePublishCallback() { const value = JSON.parse(this.options.transactionStorage.getItem('mock-publish')); this.options.transactionStorage.removeItem('mock-publish'); return value; }
}`;
export function mockContent(payload) { return computeCID(payload).then(cid => ({ cid, payload })); }
