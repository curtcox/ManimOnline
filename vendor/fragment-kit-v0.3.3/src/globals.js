import * as kit from './index.js';
/** Install after the app has supplied its DocumentType. No schema assumptions in the shim. */
export function installGlobals({ config, type, ...options }, target = globalThis) {
  const urlState = kit.createUrlState({ config, type, ...options });
  const HashBinDocuments = { ...urlState.documents,
    MAX_BYTES: config.maxBytes, bytes: kit.bytes, encode64: kit.encode64, decode64: kit.decode64,
    cidLength: kit.cidLength, isCID: kit.isCID, verify: kit.verify,
    cid: input => kit.cid(input, config.allowedHosts), link: urlState.link };
  const ShareLinks = {
    build({ url, compress, code, run, view, ...doc }) { return urlState.build({ src: doc.src ?? code, ...doc }, { url, run, view }); },
    parse(input) { const intent = urlState.parse(input); return intent.kind === 'none' ? null : intent.doc ? { ...intent, ...intent.doc } : intent; },
  };
  class AppHashBinStore extends kit.HashBinStore { constructor(options) { super({ config, type, ...options }); } }
  class AppHashBinPanel extends kit.HashBinPanel { constructor(options) { super({ urlState, ...options }); } }
  Object.assign(target, { FragmentKit: kit, HashBinDocuments, HashBinStore: AppHashBinStore,
    HashBinPanel: AppHashBinPanel, ShareLinks, ShareClient: kit.ShareClient, LocalDrafts: kit.LocalDrafts,
    RenderScheduler: kit.RenderScheduler, encodeQr: kit.encodeQr, qrSvg: kit.qrSvg, qrNotes: kit.qrNotes });
  return { urlState, HashBinDocuments, ShareLinks };
}
