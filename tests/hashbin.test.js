const { test } = require('node:test');
const assert = require('node:assert/strict');
const { HashBinDocuments: Docs, HashBinStore } = require('../src/hashbin.js');
const encode = bytes => Buffer.from(bytes).toString('base64url');
const cidFor = source => {
  const bytes = Buffer.from(source);
  const prefix = Buffer.alloc(6); prefix.writeUIntBE(bytes.length, 0, 6);
  return encode(prefix) + encode(bytes.length <= 64 ? bytes : require('node:crypto').createHash('sha512').update(bytes).digest());
};
const response = data => ({ ok: true, json: async () => data });

test('saved source links discard gallery selections so reloading loads the saved document', () => {
  const cid = cidFor('digraph { fresh -> saved }');
  const link = new URL(Docs.link('https://example.test/ManimOnline/?example=minimal&raw=old#old', cid));
  assert.equal(link.searchParams.has('example'), false);
  assert.equal(link.searchParams.has('raw'), false);
  assert.equal(link.hash, '#' + cid);
});

test('CID recognition matches 256t inline and SHA-512 formats without swallowing source', () => {
  for (const code of ['', 'a -> b', 'π → λ', 'x'.repeat(64), 'x'.repeat(65), 'x'.repeat(1000)]) assert.ok(Docs.isCID(cidFor(code)), code);
  for (const cid of ['digraph', 'a->b', 'AAAAAAAAx', 'AAAAAAAA'.repeat(12), cidFor('a') + 'x']) assert.equal(Docs.isCID(cid), false, cid);
  assert.equal(Docs.cid('https://curtcox.github.io/modl/#' + cidFor('a')), cidFor('a'));
  assert.equal(Docs.cid('https://256t.us/' + cidFor('a')), cidFor('a'));
  assert.equal(Docs.cid('https://evil.test/' + cidFor('a')), null);
});

test('all three languages round trip exact Unicode source and preview options', () => {
  for (const type of ['graphviz', 'modl', 'manim']) {
    const snapshot = { src: '# π → λ\na -> b', type, scene: 'Second', engine: 'neato', outputFormat: 'png', pos: { b: [1,2], a: [3,4] } };
    const payload = Docs.serialize(snapshot);
    const restored = Docs.parse(payload);
    assert.equal(restored.src, snapshot.src);
    assert.equal(restored.type, type);
    if (type === 'manim') assert.equal(restored.scene, 'Second');
    if (type === 'graphviz') { assert.equal(restored.engine, 'neato'); assert.equal(restored.outputFormat, 'png'); }
    if (type === 'modl') assert.deepEqual(Object.keys(restored.pos), ['a','b']);
  }
  const legacy = Docs.parse('{"format":"hashbin-diagram","version":1,"src":"a -> b","pos":{"a":[12,34]}}');
  assert.equal(legacy.type, 'modl');
  assert.deepEqual(legacy.pos.a, [12,34]);
  assert.equal(Docs.parse('digraph{a->b}').src, 'digraph{a->b}');
  assert.throws(() => Docs.parse('{"version":9,"src":"a"}'), /version/);
  assert.throws(() => Docs.serialize({src:'a',type:'unknown'}), /language/);
});

const served = text => ({ ok: true, arrayBuffer: async () => new TextEncoder().encode(text).buffer });
test('inline loads are offline; remote loads use 256t.us, verify the CID and expose errors without replacing source', async () => {
  let calls = 0;
  const remote = 'from manim import *\n' + '#'.repeat(65);
  let body = remote;
  const store = new HashBinStore({ fetchSource: async (url, { signal }) => { calls++; assert.ok(signal instanceof AbortSignal); assert.match(url, /^https:\/\/256t\.us\//); return served(body); } });
  assert.equal((await store.load(cidFor('a -> b'))).src, 'a -> b');
  assert.equal(calls, 0);
  assert.ok((await store.load(cidFor(remote))).src.startsWith('from manim'));
  assert.equal(calls, 1);
  body = remote.replace('manim', 'forged');
  await assert.rejects(store.load(cidFor(remote)), /does not match its CID/);
  store.fetchSource = async () => ({ok:false,status:404});
  await assert.rejects(store.load(cidFor('x'.repeat(65))), /expired/);
  await assert.rejects(store.load('bad'), /valid/);
});

test('deadline includes a stalled fetch or response body even if abort is ignored', async () => {
  for (const fetchSource of [() => new Promise(()=>{}), async () => ({ok:true,arrayBuffer:()=>new Promise(()=>{})})]) {
    let expire, signal, cleared;
    const store = new HashBinStore({ fetchSource: (url, options) => { signal = options.signal; return fetchSource(); }, timers: { setTimeout: cb => {expire = cb;return 1;}, clearTimeout: id => {cleared = id;} } });
    const pending = store.load(cidFor('x'.repeat(65)));
    await Promise.resolve();
    expire();
    await assert.rejects(pending, /timed out/);
    assert.ok(signal.aborted);
    assert.equal(cleared, 1);
  }
});

test('saves through HashBin Publish with the vendored SDK release and verify the returned CID', async () => {
  const payload = Docs.serialize({src:'a -> b',type:'modl'});
  const snapshot = {src:'a -> b',type:'modl',pos:{}};
  let options;
  const store = new HashBinStore({ clientId: 'test', loadSDK: async () => ({ HashBinClient: class { publish(content, opts) { assert.equal(content, payload); options = opts; return Promise.resolve({ cid: cidFor(payload) }); } } }) });
  await assert.rejects(store.publish(payload, snapshot), /still loading/);
  await store.init();
  assert.equal((await store.publish(payload, snapshot)).cid, cidFor(payload));
  assert.equal(options.contentType, 'application/json');
  assert.deepEqual(options.clientState, { snapshot });
  store.client.publish = async () => ({ cid: cidFor(payload + ' ') });
  await assert.rejects(store.publish(payload, snapshot), /does not match its CID/);
  await assert.rejects(new HashBinStore().init(), /registered client ID/);
  // The vendored files are the exact immutable release; hashes from https://hashbin.org/sdk/v0.4.0/integrity.json.
  const sri = file => 'sha384-' + require('node:crypto').createHash('sha384').update(require('node:fs').readFileSync(require('node:path').join(__dirname, '..', file))).digest('base64');
  assert.equal(sri('vendor/hashbin-sdk-v0.4.0.mjs'), 'sha384-zzmaXw5svWRp0YF//G5ytyeqEowixccM/hHVDth46FnGrIlPS7fPki5vbhv+bWCr');
  assert.equal(sri('vendor/hashbin-cache-v0.4.0.js'), 'sha384-OjeXeXB30xFV4yU2LmXTYzc0KsymrivM/l3f/rgDQuPsTzGVMnk6vYtck8n60EgP');
  assert.match(require('node:fs').readFileSync(require('node:path').join(__dirname, '../src/hashbin.js'), 'utf8'), /'\.\.\/vendor\/hashbin-sdk-v0\.4\.0\.mjs'/);
});

test('redirect saves restore the source after approval or cancellation', async () => {
  const values = new Map();
  const transactionStorage = {setItem:(k,v)=>values.set(k,v),getItem:k=>values.get(k) ?? null,removeItem:k=>values.delete(k)};
  const snapshot = {src:'π -> λ',type:'modl',pos:{a:[12,34]}};
  const payload = Docs.serialize(snapshot);
  let outcome = 'approve';
  const store = new HashBinStore({ clientId: 'test', transactionStorage, loadSDK: async () => ({ HashBinClient: class {
    publish() { return Promise.resolve({ redirected: true }); }
    async handlePublishCallback({ hash }) { assert.match(hash, /hashbin_publish=s/); if (outcome !== 'approve') throw Object.assign(new Error('access_denied'), { clientState: { snapshot } }); return { cid: cidFor(payload), clientState: { snapshot } }; }
  } }) });
  await store.init();
  assert.equal(await store.published('#' + cidFor('a')), null);
  assert.deepEqual(await store.publish(payload, snapshot), { redirected: true });
  assert.deepEqual(await store.published('#hashbin_publish=s&cid=x'), { cid: cidFor(payload), snapshot });
  await store.publish(payload, snapshot);
  outcome = 'cancel';
  assert.deepEqual(await store.published('#hashbin_publish=s&error=access_denied'), { error: 'The save was cancelled on HashBin.', snapshot });
  assert.equal(values.size, 0);
});

test('tokens left by the earlier OAuth flow are revoked server-side before they are cleared', async () => {
  const values = new Map();
  const storage = {setItem:(k,v)=>values.set(k,v),getItem:k=>values.get(k) ?? null,removeItem:k=>values.delete(k)};
  let loaded = 0, revoked = 0;
  const store = new HashBinStore({ clientId: 'test', storage, loadSDK: async () => { loaded++; return { HashBinClient: class { async disconnect() { revoked++; values.clear(); } } }; } });
  assert.equal(await store.retireLegacyTokens(), false);
  assert.equal(loaded, 0);
  storage.setItem('hashbin:tokens:test', '{"refreshToken":"old"}');
  assert.equal(await store.retireLegacyTokens(), true);
  assert.equal(revoked, 1);
});
test('editors cached before HashBin Publish can still start during an upgrade', async () => { assert.equal(await new HashBinStore().callback('?code=old&state=old'), null); });
