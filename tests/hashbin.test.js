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

test('inline loads are offline; remote loads use 256t.us and expose errors without replacing source', async () => {
  let calls = 0;
  const store = new HashBinStore({ fetchSource: async (url, { signal }) => { calls++; assert.ok(signal instanceof AbortSignal); assert.match(url, /^https:\/\/256t\.us\//); return {ok:true,text:async()=> 'from manim import *\n' + '#'.repeat(65)}; } });
  assert.equal((await store.load(cidFor('a -> b'))).src, 'a -> b');
  assert.equal(calls, 0);
  assert.ok((await store.load(cidFor('x'.repeat(65)))).src.startsWith('from manim'));
  assert.equal(calls, 1);
  store.fetchSource = async () => ({ok:false,status:404});
  await assert.rejects(store.load(cidFor('x'.repeat(65))), /expired/);
  await assert.rejects(store.load('bad'), /valid/);
});

test('deadline includes a stalled fetch or response body even if abort is ignored', async () => {
  for (const fetchSource of [() => new Promise(()=>{}), async () => ({ok:true,text:()=>new Promise(()=>{})})]) {
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

test('quote and upload use authenticated endpoints, multipart JSON and validated CIDs', async () => {
  const payload = Docs.serialize({src:'a -> b',type:'modl'});
  const cid = cidFor(payload);
  const calls = [];
  const store = new HashBinStore({fetchSource: async (url, options) => {
    assert.equal(url, 'https://hashbin.org/api/payments/calculate');
    assert.equal(JSON.parse(options.body).retention_months, 2);
    return response({cost_cents:3});
  }});
  let renewals = 0;
  let tokens = {refreshToken:'hidden',accessToken:'hidden',expiresAt:0};
  store.oauth = { getTokens:()=>tokens, refreshAccessToken:async()=>{renewals++;tokens.expiresAt = Date.now()+100000;}, authorizedFetch:async(path, options) => {
    calls.push(path);
    if (path.endsWith('settings')) return response({default_retention_months:'2'});
    if (path.endsWith('balance')) return response({balance_cents:100});
    assert.equal(path, '/api/content');
    assert.equal(await options.body.get('content').text(), payload);
    assert.equal(options.body.get('content').type, 'application/json');
    return response({cid});
  }};
  assert.deepEqual(await store.quote(payload), {months:2,cost:3,balance:100,size:Buffer.byteLength(payload)});
  assert.equal((await store.save(payload)).cid, cid);
  assert.equal(renewals, 1);
  assert.deepEqual(calls, ['/api/account/settings','/api/balance','/api/content']);
});

test('sign-in preserves the latest source and restores it after success or denial', async () => {
  const values = new Map();
  const transactionStorage = {setItem:(k,v)=>values.set(k,v),getItem:k=>values.get(k),removeItem:k=>values.delete(k)};
  const store = new HashBinStore({transactionStorage});
  let callbackSearch;
  store.oauth = { authorize:async()=>({state:'random-state',url:'https://hashbin.org/oauth/authorize'}),handleCallback:async({search})=>{callbackSearch=search;} };
  const snapshot = {src:'π -> λ',type:'modl',pos:{a:[12,34]}};
  assert.equal(await store.connect(snapshot), 'https://hashbin.org/oauth/authorize');
  const success = await store.callback('?code=code&state=random-state');
  assert.deepEqual(success.snapshot, snapshot);
  assert.ok(success.connected);
  assert.ok(callbackSearch.includes('code=code'));
  await store.connect(snapshot);
  const denied = await store.callback('?error=access_denied&state=random-state');
  assert.deepEqual(denied.snapshot, snapshot);
  assert.match(denied.error, /not approved/);
  assert.equal(values.size, 0);
  assert.match((await store.callback('?code=code&state=missing')).error, /restored/);
});
